"""性能执行器（最小实现，面向 vLLM OpenAI 兼容服务）。

提供面向 `/v1/chat/completions` 的并发请求执行与统计：
- 生成固定长度的提示词（中英混合文本），
- 以指定并发数与请求数发起请求，
- 统计 P50/P75/P90/P95/P99/AVG、QPS、失败率，
- 产出与 `testsuites/perf.py` 兼容（超集）的 CSV 表头：
  `concurrency,input_len,output_len,latency_p50_ms,throughput_rps`。

注意：
- 本模块仅作为“真实服务”性能试跑的最小实现；CI 默认仍走 mock 路径，
  编排中仅在外部显式启用时才会调用真实执行器。
"""

from __future__ import annotations

import csv
import io
import statistics
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from vllm_cibench.clients.openai_client import OpenAICompatClient


def make_prompt(length: int) -> str:
    """生成近似给定长度的中英混合提示词。

    参数:
        length: 期望字符长度。

    返回值:
        str: 由若干段文本拼接而成，长度接近 `length`。
    """

    unit = (
        "vLLM is a fast and flexible LLM serving engine. "
        "它支持OpenAI兼容接口与多种推理配置。 "
    )
    buf: List[str] = []
    while sum(len(x) for x in buf) < max(1, length):
        buf.append(unit)
    text = "".join(buf)
    return text[:length]


def _percentile(values: Sequence[float], pct: float) -> float:
    """计算百分位数（最小实现）。

    参数:
        values: 数值序列（毫秒）。
        pct: 百分位（0-100）。

    返回值:
        float: 近似百分位数。
    """

    if not values:
        return 0.0
    vs = sorted(values)
    k = (pct / 100.0) * (len(vs) - 1)
    f = int(k)
    c = min(f + 1, len(vs) - 1)
    if f == c:
        return float(vs[f])
    d0 = vs[f] * (c - k)
    d1 = vs[c] * (k - f)
    return float(d0 + d1)


def compute_summary(
    latencies_ms: Sequence[float], duration_s: float, total: int
) -> Dict[str, float]:
    """根据请求耗时与总时长汇总指标。

    参数:
        latencies_ms: 每次请求的时延（毫秒）。
        duration_s: 本轮测量的总用时（秒）。
        total: 请求总数（用于 QPS 计算）。

    返回值:
        dict: 包含分位数与吞吐等聚合值。
    """

    if total <= 0 or duration_s <= 0:
        return {
            "latency_p50_ms": 0.0,
            "latency_p75_ms": 0.0,
            "latency_p90_ms": 0.0,
            "latency_p95_ms": 0.0,
            "latency_p99_ms": 0.0,
            "latency_avg_ms": 0.0,
            "throughput_rps": 0.0,
        }
    p50 = _percentile(latencies_ms, 50)
    p75 = _percentile(latencies_ms, 75)
    p90 = _percentile(latencies_ms, 90)
    p95 = _percentile(latencies_ms, 95)
    p99 = _percentile(latencies_ms, 99)
    avg = statistics.fmean(latencies_ms) if latencies_ms else 0.0
    qps = float(total) / float(duration_s)
    return {
        "latency_p50_ms": float(p50),
        "latency_p75_ms": float(p75),
        "latency_p90_ms": float(p90),
        "latency_p95_ms": float(p95),
        "latency_p99_ms": float(p99),
        "latency_avg_ms": float(avg),
        "throughput_rps": float(qps),
    }


def _do_chat_request(
    client: OpenAICompatClient,
    model: str,
    messages: Sequence[Mapping[str, Any]],
    params: Mapping[str, Any],
    out_lat_ms: List[float],
    out_fail: List[int],
    lock: threading.Lock,
) -> None:
    """执行单个 chat 请求并记录耗时/失败计数。

    参数:
        client: OpenAI 客户端。
        model: 模型名。
        messages: 消息数组。
        params: 额外参数。
        out_lat_ms: 用于收集耗时（毫秒）的列表（线程共享）。
        out_fail: 用于收集失败计数的列表（线程共享，元素为 0/1）。
        lock: 线程锁，保护共享写入。
    """

    t0 = time.monotonic()
    try:
        _ = client.chat_completions(
            model=model, messages=list(messages), **dict(params)
        )
        ok = True
    except Exception:
        ok = False
    dt_ms = (time.monotonic() - t0) * 1000.0
    with lock:
        if ok:
            out_lat_ms.append(dt_ms)
        else:
            out_fail.append(1)


def run_openai_chat_batch(
    base_url: str,
    model: str,
    *,
    prompt_len: int,
    n_requests: int,
    concurrency: int,
    temperature: float = 0.0,
    timeout_s: float = 30.0,
    api_key: Optional[str] = None,
) -> Tuple[List[float], int, float]:
    """对 chat 端点执行一批请求并返回测量结果。

    参数:
        base_url: 服务基础 URL（/v1）。
        model: 模型名。
        prompt_len: 输入提示长度（字符）。
        n_requests: 请求总数。
        concurrency: 并发度（线程数）。
        temperature: 采样温度。
        timeout_s: 单请求超时时间（秒）。
        api_key: 可选 API Key。

    返回值:
        (latencies_ms, fail_count, duration_s)
    """

    client = OpenAICompatClient(base_url=base_url, api_key=api_key)
    messages: Sequence[Mapping[str, Any]] = (
        {"role": "user", "content": make_prompt(prompt_len)},
    )
    params = {"temperature": temperature}
    lat_ms: List[float] = []
    fail: List[int] = []
    lock = threading.Lock()
    t0 = time.monotonic()
    with ThreadPoolExecutor(max_workers=max(1, concurrency)) as ex:
        futs = [
            ex.submit(
                _do_chat_request,
                client,
                model,
                messages,
                params,
                lat_ms,
                fail,
                lock,
            )
            for _ in range(max(1, n_requests))
        ]
        for _ in as_completed(futs):
            pass
    duration_s = time.monotonic() - t0
    return lat_ms, len(fail), float(duration_s)


@dataclass
class PerfProfile:
    """性能档位（最小字段）。

    属性:
        concurrency: 并发列表。
        input_length: 输入长度候选列表（字符级）。
        output_length: 输出长度候选列表（token 级估计，当前仅占位）。
        num_requests_per_concurrency: 每个并发下请求数量。
        warmup: 预热批次数（不计入统计）。
        epochs: 重复测量轮数（取平均）。
        temperature: 采样温度。
    """

    concurrency: List[int]
    input_length: List[int]
    output_length: List[int]
    num_requests_per_concurrency: int
    warmup: int = 1
    epochs: int = 1
    temperature: float = 0.0


def run_profile_to_csv(
    base_url: str,
    model: str,
    profile: PerfProfile,
    *,
    api_key: Optional[str] = None,
) -> str:
    """按给定档位执行并返回 CSV 文本（与 mock CSV 结构兼容）。

    参数:
        base_url: 服务基础 URL。
        model: 模型名。
        profile: 档位配置对象。
        api_key: 可选 API Key。

    返回值:
        str: 包含表头的 CSV 文本。
    """

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(
        [
            "concurrency",
            "input_len",
            "output_len",
            "latency_p50_ms",
            "throughput_rps",
        ]
    )
    in_len = profile.input_length[0] if profile.input_length else 128
    out_len = profile.output_length[0] if profile.output_length else 128

    for c in profile.concurrency:
        # 预热
        for _ in range(max(0, profile.warmup)):
            _ = run_openai_chat_batch(
                base_url,
                model,
                prompt_len=in_len,
                n_requests=min(2, profile.num_requests_per_concurrency),
                concurrency=max(1, min(c, 4)),  # 预热限速
                temperature=profile.temperature,
                api_key=api_key,
            )

        # 多 epoch 测量，聚合为均值
        agg_lat_ms: List[float] = []
        total_reqs = 0
        total_duration = 0.0
        for _ in range(max(1, profile.epochs)):
            lat_ms, fail_count, dur = run_openai_chat_batch(
                base_url,
                model,
                prompt_len=in_len,
                n_requests=profile.num_requests_per_concurrency,
                concurrency=c,
                temperature=profile.temperature,
                api_key=api_key,
            )
            agg_lat_ms.extend(lat_ms)
            total_reqs += profile.num_requests_per_concurrency
            total_duration += dur

        if total_reqs <= 0 or total_duration <= 0:
            p50 = 0.0
            thr = 0.0
        else:
            summary = compute_summary(agg_lat_ms, total_duration, total_reqs)
            p50 = summary["latency_p50_ms"]
            thr = summary["throughput_rps"]
        writer.writerow([c, in_len, out_len, f"{p50:.3f}", f"{thr:.3f}"])

    return buf.getvalue()
