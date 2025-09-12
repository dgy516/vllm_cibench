"""run_matrix 批量执行测试。"""

from __future__ import annotations

from pathlib import Path

import vllm_cibench.orchestrators.run_matrix as rm


def test_execute_matrix_calls_pipeline(monkeypatch):
    """应按 matrix 中的所有场景调用 run_pipeline.execute 并传递超时时长。"""

    called = []

    def fake_execute(
        *, scenario_id: str, run_type: str, root: str, timeout_s: float = 60.0
    ):
        called.append((scenario_id, run_type, timeout_s))
        return {"scenario": scenario_id, "ok": True}

    monkeypatch.setattr(rm.run_pipeline, "execute", fake_execute)
    out = rm.execute_matrix(run_type="pr", root=str(Path.cwd()), timeout_s=1.5)
    # 仓库 matrix.yaml 目前包含三个示例场景，确保至少调用一次
    assert isinstance(out, dict) and len(out) >= 1
    assert all(rt == "pr" for _, rt, _ in called)
    assert all(ts == 1.5 for _, _, ts in called)
