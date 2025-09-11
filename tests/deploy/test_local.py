"""本地部署骨架测试。"""

from pathlib import Path

from vllm_cibench.config import list_scenarios
from vllm_cibench.deploy.local import build_start_command, scenario_base_url


def test_build_start_command_and_base_url():
    """校验命令拼装包含模型与量化参数，且能取到 base_url。"""

    scenario = next(
        s for s in list_scenarios(Path("configs/scenarios")) if s.mode == "local"
    )
    cmd = build_start_command(scenario, project_root=Path.cwd())
    assert "scripts/start_local.sh" in cmd[1]
    assert "--model" in cmd and scenario.served_model_name in cmd
    assert "--quant" in cmd and scenario.quant in cmd

    url = scenario_base_url(scenario)
    assert url.startswith("http://") or url.startswith("https://")
