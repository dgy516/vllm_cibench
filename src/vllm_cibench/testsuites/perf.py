"""性能测试执行器（最小管道）。

提供生成/解析基准 CSV 及结构化指标的最小实现，便于在 CI 中做单元验证。
"""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List


@dataclass
class PerfResult:
    """性能结果数据模型（最小字段）。

    属性:
        concurrency: 并发数。
        input_len: 输入长度。
        output_len: 输出长度。
        latency_p50_ms: P50 时延（毫秒）。
        throughput_rps: 吞吐（requests/s）。
    """

    concurrency: int
    input_len: int
    output_len: int
    latency_p50_ms: float
    throughput_rps: float


def gen_mock_csv(rows: Iterable[PerfResult]) -> str:
    """生成带表头的 CSV 文本（用于 mock 性能结果）。

    参数:
        rows: `PerfResult` 列表或迭代器。

    返回值:
        str: CSV 文本，首行包含表头。

    副作用:
        无；仅在内存中生成文本。
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
    for r in rows:
        writer.writerow(
            [
                r.concurrency,
                r.input_len,
                r.output_len,
                r.latency_p50_ms,
                r.throughput_rps,
            ]
        )
    return buf.getvalue()


def parse_perf_csv(csv_text: str) -> List[Dict[str, Any]]:
    """解析 CSV 文本为字典列表。

    参数:
        csv_text: 字符串形式的 CSV 内容。

    返回值:
        List[Dict[str, Any]]: 每行一个字典，键来自表头，值做基本类型转换。

    副作用:
        无。
    """

    out: List[Dict[str, Any]] = []
    reader = csv.DictReader(io.StringIO(csv_text))
    for row in reader:
        item: Dict[str, Any] = {
            "concurrency": int(row["concurrency"]),
            "input_len": int(row["input_len"]),
            "output_len": int(row["output_len"]),
            "latency_p50_ms": float(row["latency_p50_ms"]),
            "throughput_rps": float(row["throughput_rps"]),
        }
        # 可选分位：latency_p95_ms / latency_p99_ms
        if "latency_p95_ms" in row and row["latency_p95_ms"] not in (None, ""):
            try:
                item["latency_p95_ms"] = float(row["latency_p95_ms"])
            except Exception:
                pass
        if "latency_p99_ms" in row and row["latency_p99_ms"] not in (None, ""):
            try:
                item["latency_p99_ms"] = float(row["latency_p99_ms"])
            except Exception:
                pass
        out.append(item)
    return out
