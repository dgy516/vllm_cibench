"""Accuracy 产物落地测试。"""

from __future__ import annotations

from pathlib import Path

import pytest

import vllm_cibench.orchestrators.run_pipeline as rp


@pytest.mark.accuracy
def test_accuracy_artifacts_written(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # 避免真实探活
    monkeypatch.setattr(
        rp,
        "_discover_and_wait",
        lambda base, s, timeout_s=60.0: "http://127.0.0.1:9000/v1",
    )
    monkeypatch.setattr(
        rp,
        "run_smoke_suite",
        lambda base_url, model: {"choices": [{"message": {"content": "ok"}}]},
    )
    # 固定精度结果
    monkeypatch.setattr(
        rp,
        "run_accuracy",
        lambda base_url, model, cfg=None: {
            "task": "gpqa",
            "score": 0.5,
            "correct": 1,
            "total": 2,
        },
    )
    root = str(Path.cwd())
    res = rp.execute(
        scenario_id="local_single_qwen3-32b_guided_w8a8",
        run_type="pr",
        root=root,
        timeout_s=0.1,
        dry_run=True,
    )
    # 检查 artifacts 路径与文件
    acc_dir = Path(res.get("artifacts", {}).get("accuracy_dir", ""))
    assert acc_dir.exists() and (acc_dir / "result.json").exists()
