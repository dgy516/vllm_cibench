"""run_pipeline 性能阶段：real 模式接线测试（mock 网络）。"""

from __future__ import annotations

from pathlib import Path

import pytest

import vllm_cibench.orchestrators.run_pipeline as rp


@pytest.mark.perf
def test_execute_perf_real_mode_monkeypatched(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    # 避免真实探活
    monkeypatch.setattr(rp, "_discover_and_wait", lambda base, s, timeout_s=60.0: "http://127.0.0.1:9000/v1")
    monkeypatch.setattr(rp, "run_smoke_suite", lambda base_url, model: {"choices": [{"message": {"content": "ok"}}]})
    monkeypatch.setattr(rp, "push_metrics", lambda *a, **kw: False)
    # 伪造 run_profile_to_csv 返回的 CSV 文本
    csv_text = "\n".join(
        [
            "concurrency,input_len,output_len,latency_p50_ms,throughput_rps",
            "1,128,128,50.0,10.0",
            "2,128,128,60.0,20.0",
        ]
    )
    monkeypatch.setattr(rp, "run_profile_to_csv", lambda *a, **k: csv_text)

    # 开启 real 模式
    monkeypatch.setenv("VLLM_CIBENCH_PERF_MODE", "real")
    res = rp.execute(
        scenario_id="local_single_qwen3-32b_guided_w8a8",
        run_type="pr",
        root=str(Path.cwd()),
        timeout_s=0.1,
        dry_run=True,
    )
    assert res["perf_metrics"].get("mode") == "real"
    assert "ci_perf_throughput_rps_avg" in res["perf_metrics"]
