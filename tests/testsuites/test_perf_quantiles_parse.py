"""性能 CSV 解析：可选 p95/p99 字段测试。"""

from __future__ import annotations

from vllm_cibench.testsuites.perf import parse_perf_csv


def test_parse_perf_with_quantiles():
    csv = (
        "concurrency,input_len,output_len,latency_p50_ms,latency_p95_ms,latency_p99_ms,throughput_rps\n"
        "1,128,128,40,80,100,10\n"
        "2,128,128,60,120,140,20\n"
    )
    out = parse_perf_csv(csv)
    assert out[0]["latency_p95_ms"] == 80.0 and out[0]["latency_p99_ms"] == 100.0
    assert out[1]["latency_p95_ms"] == 120.0 and out[1]["latency_p99_ms"] == 140.0


def test_parse_perf_without_quantiles():
    csv = (
        "concurrency,input_len,output_len,latency_p50_ms,throughput_rps\n"
        "1,128,128,40,10\n"
        "2,128,128,60,20\n"
    )
    out = parse_perf_csv(csv)
    assert "latency_p95_ms" not in out[0] and "latency_p99_ms" not in out[0]
