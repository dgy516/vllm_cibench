"""配置 Schema/加载器 的单元测试。"""

from __future__ import annotations

from pathlib import Path

import pytest

from vllm_cibench.config_loader import (
    ValidationReport,
    load_matrix_strict,
    load_scenarios_strict,
    validate_all,
)


def test_validate_repo_configs_ok(tmp_path: Path):
    """对仓库现有配置做一轮严格校验应通过。"""

    root = Path.cwd()
    rep = validate_all(root)
    assert isinstance(rep, ValidationReport)
    assert rep.scenarios >= 1 and rep.matrix_keys >= 1 and rep.providers >= 1


def test_scenarios_forbid_extra_fields(tmp_path: Path):
    """场景文件包含未知字段时应报错（extra=forbid）。"""

    yml = tmp_path / "scenarios"
    yml.mkdir(parents=True)
    p = yml / "s.yaml"
    p.write_text(
        """
id: s1
mode: local
served_model_name: m
model: M
quant: w8a8
base_url: http://127.0.0.1:9000/v1
unknown: 1
""",
        encoding="utf-8",
    )
    with pytest.raises(Exception):
        _ = load_scenarios_strict(yml)


def test_matrix_min_shape(tmp_path: Path):
    """matrix.yaml 顶层必须为 {<scenario>: {pr:..., daily:...}}。"""

    p = tmp_path / "matrix.yaml"
    p.write_text(
        """
s1:
  pr: {functional: all, perf: true, accuracy: true}
  daily: {functional: all, perf: true, accuracy: false}
""",
        encoding="utf-8",
    )
    mx = load_matrix_strict(p)
    assert set(mx.keys()) == {"s1"}
