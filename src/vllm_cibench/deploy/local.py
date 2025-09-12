"""本地部署启动与探活。"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Dict, List, Optional

from ..clients.http import wait_for_http, wait_for_ready
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


def wait_service_ready(
    scenario: Scenario,
    timeout_seconds: Optional[int] = None,
    headers: Optional[Dict[str, str]] = None,
) -> bool:
    """等待本地服务就绪。

    参数:
        scenario: 场景对象。
        timeout_seconds: 最大等待时长（秒），缺省读取场景中
            `startup_timeout_seconds`，若未配置则使用 60。
        headers: 探活请求的额外 HTTP 头。

    返回值:
        bool: 服务在超时前就绪返回 True，否则 False。

    副作用:
        网络探测，内部调用 `wait_for_ready`。
    """

    url = scenario_base_url(scenario)
    timeout = timeout_seconds or int(scenario.raw.get("startup_timeout_seconds", 60))
    return wait_for_ready(url, timeout_seconds=timeout, headers=headers)


def start_local(
    script: Path = Path("scripts/start_local.sh"),
    health_url: str = "http://localhost:8000/health",
    timeout_s: float = 1.0,
    max_attempts: int = 5,
) -> subprocess.Popen:
    """启动本地服务并等待健康检查成功。

    参数:
        script: 启动脚本路径，默认 `scripts/start_local.sh`。
        health_url: 健康检查地址。
        timeout_s: 单次请求超时时间（秒）。
        max_attempts: 最大重试次数。

    返回值:
        subprocess.Popen: 启动的子进程对象。

    副作用:
        创建子进程并进行网络探活，失败时终止子进程并抛出异常。
    """

    proc = subprocess.Popen(
        ["bash", str(script)], stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    ok = wait_for_http(health_url, timeout_s=timeout_s, max_attempts=max_attempts)
    if not ok:
        proc.terminate()
        raise RuntimeError("service failed health check")
    return proc
