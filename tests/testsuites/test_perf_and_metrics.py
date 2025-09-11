# isort: skip_file
"""性能与指标名映射的单元测试。"""

from __future__ import annotations

from vllm_cibench.metrics.rename import DEFAULT_MAPPING, rename_record_keys
from vllm_cibench.testsuites.perf import (
    PerfResult,
    gen_mock_csv,
    parse_perf_csv,
)


def test_perf_csv_and_rename():
    """生成 CSV → 解析 → 指标键重命名，最终键名满足 Prometheus 规范。"""

    rows = [
        PerfResult(
            concurrency=1,
            input_len=128,
            output_len=128,
            latency_p50_ms=50.5,
            throughput_rps=12.3,
        )
    ]
    csv_text = gen_mock_csv(rows)
    parsed = parse_perf_csv(csv_text)
    assert parsed and parsed[0]["throughput_rps"] == 12.3

    renamed = rename_record_keys(parsed[0], DEFAULT_MAPPING)
    assert "throughput_requests_per_second" in renamed
    assert "latency_p50_milliseconds" in renamed
