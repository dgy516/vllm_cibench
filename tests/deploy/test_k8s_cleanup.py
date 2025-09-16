"""K8s 清理钩子（编排结束后的可选清理）测试。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

import vllm_cibench.orchestrators.run_pipeline as rp
from vllm_cibench.config import Scenario


class _Calls:
    def __init__(self) -> None:
        self.cmds: list[list[str]] = []


def test_k8s_cleanup_invoked(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """在 k8s 场景下，当提供删除 YAML 时，应调用 kubectl delete。"""

    # 构造 k8s 混合场景
    s = Scenario(
        id="k8s_x",
        mode="k8s-hybrid",
        served_model_name="m",
        model="M",
        quant="w8a8",
        raw={
            "k8s": {"namespace": "default", "service_name": "infer-vllm"},
        },
    )

    # 伪造场景查找
    monkeypatch.setattr(
        rp,
        "_find_scenario",
        lambda root, sid: s,
    )

    # 避免真实探活
    monkeypatch.setattr(
        rp,
        "_discover_and_wait",
        lambda base, sc, timeout_s=60.0: "http://127.0.0.1:9000/v1",
    )
    # 跳过 matrix 计划解析（直接返回空计划）
    monkeypatch.setattr(rp, "resolve_plan", lambda m, sid, rt: {})
    monkeypatch.setattr(
        rp,
        "run_smoke_suite",
        lambda base_url, model: {"choices": [{"message": {"content": "ok"}}]},
    )

    # 写入临时 YAML 并通过环境变量声明清理
    yml = tmp_path / "del.yaml"
    yml.write_text("apiVersion: v1\nkind: List\nitems: []\n", encoding="utf-8")
    monkeypatch.setenv("VLLM_CIBENCH_K8S_DELETE_YAML", str(yml))

    # 捕获 subprocess.run 调用
    calls = _Calls()

    def fake_run(cmd: list[str], check: bool = False, **_: Any):  # type: ignore[override]
        calls.cmds.append(list(map(str, cmd)))

        class _R:
            returncode = 0

        return _R()

    monkeypatch.setattr("subprocess.run", fake_run)

    # 执行一次编排（dry-run 跳过推送）
    res = rp.execute(
        scenario_id="k8s_x",
        run_type="pr",
        root=str(Path.cwd()),
        timeout_s=0.1,
        dry_run=True,
    )
    assert res.get("functional") in {"ok", "failed", "skipped"}
    # 断言触发了 kubectl delete 调用
    assert any(cmd[:2] == ["kubectl", "delete"] for cmd in calls.cmds)
