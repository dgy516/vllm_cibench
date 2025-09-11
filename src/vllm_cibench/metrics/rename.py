"""指标名规范化（Prometheus 友好）。

将通用列名映射到 Prometheus 规范的指标名，便于后续 Pushgateway 发布。
"""

from __future__ import annotations

from typing import Dict, Mapping

DEFAULT_MAPPING: Mapping[str, str] = {
    "latency_p50_ms": "latency_p50_milliseconds",
    "throughput_rps": "throughput_requests_per_second",
}


def rename_record_keys(
    record: Mapping[str, object], mapping: Mapping[str, str] | None = None
) -> Dict[str, object]:
    """对单条记录的键进行重命名。

    参数:
        record: 原始记录字典。
        mapping: 键名映射（原名 -> 目标名）；缺省使用 `DEFAULT_MAPPING`。

    返回值:
        dict: 新的记录字典，包含替换后的键名。

    副作用:
        无；返回新字典，不修改输入。
    """

    mp = mapping or DEFAULT_MAPPING
    out: Dict[str, object] = {}
    for k, v in record.items():
        out[mp.get(k, k)] = v
    return out
