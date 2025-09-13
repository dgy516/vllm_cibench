"""Accuracy 从 samples_file 加载样本的测试。"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from vllm_cibench.testsuites.accuracy import run_accuracy


@pytest.mark.accuracy
def test_run_accuracy_from_samples_file(tmp_path: Path, requests_mock):
    base = "http://example.com/v1"
    url = base + "/chat/completions"
    # 第一次答对，第二次答错
    ok = {"choices": [{"message": {"content": "B"}}]}
    bad = {"choices": [{"message": {"content": "X"}}]}
    requests_mock.post(
        url, [{"json": ok, "status_code": 200}, {"json": bad, "status_code": 200}]
    )

    samples = [
        {"question": "Pick B", "choices": ["A", "B"], "answer": "B"},
        {"question": "Pick C", "choices": ["B", "C"], "answer": "C"},
    ]
    f = tmp_path / "samples.json"
    f.write_text(json.dumps(samples), encoding="utf-8")

    out = run_accuracy(base_url=base, model="dummy", cfg={"samples_file": str(f)})
    assert out["total"] == 2
    assert out["correct"] == 1
