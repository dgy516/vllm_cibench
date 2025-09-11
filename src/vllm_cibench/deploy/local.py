"""本地部署工具（骨架）。

提供启动命令拼装与服务就绪等待等最小能力。
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List

from ..clients.http import wait_for_ready
from ..config import Scenario


def build_start_command(
    scenario: Scenario, project_root: Path | None = None
) -> List[str]:
    """构建本地启动命令（不执行）。

    参数:
        scenario: 场景对象，读取模型名/量化与可选 args。
        project_root: 项目根目录（用于定位脚本），缺省使用 CWD。

    返回值:
        List[str]: 形如 ["bash", "scripts/start_local.sh", "--model", ..., "--quant", ...]。

    副作用:
        无；仅进行字符串拼装。
    """

    root = project_root or Path.cwd()
    script = root / "scripts" / "start_local.sh"
    cmd = [
        "bash",
        str(script),
        "--model",
        scenario.served_model_name,
        "--quant",
        scenario.quant,
    ]
    args: Dict[str, object] = scenario.raw.get("args", {}) or {}
    for k, v in args.items():
        cmd.extend([f"--{k.replace('_', '-')}", str(v)])
    return cmd


def scenario_base_url(scenario: Scenario) -> str:
    """获取场景的基础 URL（本地模式直接从 YAML 读取）。

    参数:
        scenario: 场景对象。

    返回值:
        str: 形如 "http://127.0.0.1:9000/v1" 的地址。

    副作用:
        无。
    """

    base_url = scenario.raw.get("base_url")
    if not base_url:
        raise KeyError("scenario missing 'base_url'")
    return str(base_url)


def wait_service_ready(scenario: Scenario, timeout_seconds: int = 60) -> bool:
    """等待本地服务就绪。

    参数:
        scenario: 场景对象。
        timeout_seconds: 最大等待时长（秒）。

    返回值:
        bool: 服务在超时前就绪返回 True，否则 False。

    副作用:
        网络探测，内部调用 `wait_for_ready`。
    """

    url = scenario_base_url(scenario)
    return wait_for_ready(url, timeout_seconds=timeout_seconds)
