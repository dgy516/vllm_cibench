"""编排器（run_pipeline）单元测试。"""

from __future__ import annotations

from pathlib import Path

import pytest

import vllm_cibench.orchestrators.run_pipeline as rp


def test_execute_pr_flow_monkeypatched(monkeypatch: pytest.MonkeyPatch):
    """PR 流程：应运行探活/功能/性能，但不推送指标。"""

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
    monkeypatch.setattr(rp, "push_metrics", lambda *a, **kw: False)

    # 使用仓库自带的 local 场景
    res = rp.execute(
        scenario_id="local_single_qwen3-32b_guided_w8a8",
        run_type="pr",
        root=str(Path.cwd()),
        timeout_s=0.1,
    )
    assert res["functional"] == "ok"
    assert res["pushed"] is False
    assert "ci_perf_throughput_rps_avg" in res["perf_metrics"]


def test_execute_daily_push(monkeypatch: pytest.MonkeyPatch):
    """Daily 流程：应触发 push_metrics。"""

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
    called = {"flag": False}

    def fake_push(*a, **kw):
        called["flag"] = True
        return True

    monkeypatch.setattr(rp, "push_metrics", fake_push)
    res = rp.execute(
        scenario_id="local_single_qwen3-32b_guided_w8a8",
        run_type="daily",
        root=str(Path.cwd()),
        timeout_s=0.1,
    )
    assert called["flag"] is True
    assert res["pushed"] is True


def test_execute_daily_dry_run(monkeypatch: pytest.MonkeyPatch):
    """dry_run=True 时即便 daily 也不应推送。"""

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
    called = {"flag": False}

    def fake_push(*a, **kw):
        called["flag"] = True
        return True

    monkeypatch.setattr(rp, "push_metrics", fake_push)
    res = rp.execute(
        scenario_id="local_single_qwen3-32b_guided_w8a8",
        run_type="daily",
        root=str(Path.cwd()),
        timeout_s=0.1,
        dry_run=True,
    )
    assert called["flag"] is False
    assert res["pushed"] is False
