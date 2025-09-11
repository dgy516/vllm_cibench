"""本地部署启动与探活。"""

from __future__ import annotations

import subprocess
from pathlib import Path

from vllm_cibench.clients.http import wait_for_http


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
