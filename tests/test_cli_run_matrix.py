"""CLI run-matrix 子命令测试。"""

from __future__ import annotations

import json
from typing import Any, Dict

from typer.testing import CliRunner

from vllm_cibench.run import app


def test_cli_run_matrix_dry_run(monkeypatch) -> None:
    """校验 run-matrix 子命令在 dry-run 下返回 JSON。"""

    def fake_execute_matrix(*_args: Any, **_kwargs: Any) -> Dict[str, str]:
        return {"dummy": "ok"}

    monkeypatch.setattr(
        "vllm_cibench.orchestrators.run_matrix.execute_matrix", fake_execute_matrix
    )

    runner = CliRunner()
    result = runner.invoke(app, ["run-matrix", "--dry-run"])
    assert result.exit_code == 0, result.output
    obj = json.loads(result.stdout.strip())
    assert obj == {"dummy": "ok"}


def test_cli_run_matrix_with_timeout(monkeypatch) -> None:
    """校验 run-matrix 支持 --timeout 参数并透传。"""

    cap = {"timeout": None}

    def fake_execute_matrix(*_args: Any, **_kwargs: Any) -> Dict[str, str]:
        cap["timeout"] = _kwargs.get("timeout_s")
        return {"dummy": "ok"}

    monkeypatch.setattr(
        "vllm_cibench.orchestrators.run_matrix.execute_matrix", fake_execute_matrix
    )

    runner = CliRunner()
    result = runner.invoke(app, ["run-matrix", "--dry-run", "--timeout", "0.2"])
    assert result.exit_code == 0, result.output
    obj = json.loads(result.stdout.strip())
    assert obj == {"dummy": "ok"}
    assert cap["timeout"] == 0.2
