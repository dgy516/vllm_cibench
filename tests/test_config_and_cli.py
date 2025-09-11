"""配置与 CLI 的基础测试。

覆盖:
- list_scenarios 列表长度与包含的 id
- resolve_plan 从 matrix.yaml 获取到期望键
- Typer CLI plan 子命令输出 JSON 的关键字段
"""

import json
from pathlib import Path

import pytest

try:
    from typer.testing import CliRunner
except ModuleNotFoundError:  # pragma: no cover - 环境缺少 typer 时跳过 CLI 测试
    CliRunner = None

try:  # pragma: no cover - 环境缺少 PyYAML 时整体跳过
    import yaml  # type: ignore[import-untyped]  # noqa: F401
except ModuleNotFoundError:
    yaml = None

if yaml is None:  # pragma: no cover - 缺少依赖时跳过整个模块
    pytest.skip("PyYAML not installed", allow_module_level=True)

from vllm_cibench.config import (
    ScenarioRegistry,
    list_scenarios,
    load_matrix,
    resolve_plan,
)
from vllm_cibench.run import app

pytestmark = pytest.mark.skipif(CliRunner is None, reason="typer not installed")


def test_list_scenarios_ids(tmp_path: Path):
    """校验场景目录能正确解析出示例场景 id。"""

    scenarios = list_scenarios(Path("configs/scenarios"))
    ids = {s.id for s in scenarios}
    # 仓库当前包含 3 个示例场景
    assert {
        "local_single_qwen3-32b_guided_w8a8",
        "k8s_hybrid_qwen3-32b_tp2_w4a8",
        "k8s_pd_deepseek-r1_2p1d_reasoning_w8a8",
    }.issubset(ids)


@pytest.mark.parametrize(
    "scenario_id",
    [
        "local_single_qwen3-32b_guided_w8a8",
        "k8s_hybrid_qwen3-32b_tp2_w4a8",
        "k8s_pd_deepseek-r1_2p1d_reasoning_w8a8",
    ],
)
def test_resolve_plan_from_matrix(scenario_id: str):
    """校验从 matrix.yaml 解析到 PR 类型的计划字段。"""

    matrix = load_matrix(Path("configs/matrix.yaml"))
    plan = resolve_plan(matrix, scenario_id, "pr")
    assert set(plan.keys()) == {"functional", "perf", "accuracy"}


@pytest.mark.skipif(CliRunner is None, reason="typer not installed")
def test_cli_plan_json_output():
    """通过 Typer CLI 校验 JSON 输出包含关键字段。"""

    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "--scenario",
            "local_single_qwen3-32b_guided_w8a8",
            "--run-type",
            "pr",
            "--root",
            str(Path.cwd()),
        ],
    )
    assert result.exit_code == 0, result.output
    obj = json.loads(result.stdout.strip())
    assert obj["scenario"] == "local_single_qwen3-32b_guided_w8a8"
    assert obj["run_type"] == "pr"
    assert set(obj["plan"].keys()) == {"functional", "perf", "accuracy"}


def test_scenario_registry_get():
    """校验 ScenarioRegistry 能获取场景并对未知 id 抛错。"""

    registry = ScenarioRegistry.from_dir(Path("configs/scenarios"))
    scenario = registry.get("local_single_qwen3-32b_guided_w8a8")
    assert scenario.mode == "local"
    with pytest.raises(KeyError):
        registry.get("not_exists")
