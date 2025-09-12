"""Pushgateway 指标发布工具。

仅在每日任务（run_type=daily）且仓库为主仓库时才会推送指标；
PR 或 fork 情况下直接跳过。读取环境变量 `PROM_PUSHGATEWAY_URL`
或函数入参作为 Pushgateway 地址。
"""

from __future__ import annotations

import os
from typing import Dict, Iterable, Mapping, Optional

from prometheus_client import (  # type: ignore[import-not-found]
    CollectorRegistry,
    Gauge,
    push_to_gateway,
)


def build_registry(metrics: Mapping[str, float]) -> CollectorRegistry:
    """构建 Prometheus `CollectorRegistry` 并写入指标。

    参数:
        metrics: 指标名到数值的映射，例如 {"ci_perf_throughput_rps_avg": 12.3}。

    返回值:
        CollectorRegistry: 已填充数据的注册表，可用于推送。

    副作用:
        无。
    """

    reg = CollectorRegistry()
    for name, val in metrics.items():
        g = Gauge(name, f"{name}", registry=reg)
        g.set(float(val))
    return reg


def metrics_from_perf_records(
    records: Iterable[Mapping[str, float]],
) -> Dict[str, float]:
    """从性能明细记录聚合出便于展示的指标。

    参数:
        records: 形如 [{"throughput_rps": 12.3, "latency_p50_ms": 50.5}, ...]。

    返回值:
        dict: 包含均值等聚合结果的指标，例如：
            - ci_perf_throughput_rps_avg
            - ci_perf_latency_p50_ms_avg

    副作用:
        无。
    """

    thr = []
    p50 = []
    for r in records:
        if "throughput_rps" in r:
            thr.append(float(r["throughput_rps"]))
        if "latency_p50_ms" in r:
            p50.append(float(r["latency_p50_ms"]))
    out: Dict[str, float] = {}
    if thr:
        out["ci_perf_throughput_rps_avg"] = sum(thr) / len(thr)
    if p50:
        out["ci_perf_latency_p50_ms_avg"] = sum(p50) / len(p50)
    return out


def push_metrics(
    job: str,
    metrics: Mapping[str, float],
    labels: Optional[Mapping[str, str]] = None,
    *,
    gateway_url: Optional[str] = None,
    run_type: str = "pr",
    dry_run: bool = False,
) -> bool:
    """向 Pushgateway 推送指标（仅在 daily 时启用）。

    参数:
        job: Job 名称（Prometheus Pushgateway 概念）。
        metrics: 指标名到数值的映射。
        labels: 作为 `grouping_key` 的标签（例如 {model, quant, scenario}）。
        gateway_url: 覆盖默认环境变量 `PROM_PUSHGATEWAY_URL`。
        run_type: 运行类型，只有 `daily` 时才推送；其它值直接跳过并返回 False。
        dry_run: 若为 True，则跳过推送（用于调试或手动触发）。

    返回值:
        bool: True 表示已尝试推送（并认为成功），False 表示跳过推送。

    副作用:
        可能发起网络请求到 Pushgateway；异常将被吞掉并返回 False。
    """

    if run_type != "daily" or dry_run:
        return False

    url = gateway_url or os.environ.get("PROM_PUSHGATEWAY_URL")
    if not url:
        return False

    repo = os.environ.get("GITHUB_REPOSITORY", "")
    if repo and repo != "dgy516/vllm_cibench":
        return False

    try:
        reg = build_registry(metrics)
        grouping = dict(labels or {})
        push_to_gateway(url, job=job, registry=reg, grouping_key=grouping)
        return True
    except Exception:
        return False
