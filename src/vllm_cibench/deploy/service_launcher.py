"""服务启动器（本地自动启动 + 探活 + 清理 + 日志归档）。

提供一个最小可用的本地服务启动与健康检查工具：
- 使用项目脚本 `scripts/start_local.sh` 启动待测服务；
- 采用指数退避的健康检查，最大等待默认 20 分钟；
- 将 stdout/stderr 重定向至 `artifacts/logs/service_*.log`；
- 支持上下文管理协议，确保异常时也能清理子进程。

默认不启用，需在场景或环境变量开启：
- 场景 `raw.autostart: true`，或环境变量 `VLLM_CIBENCH_AUTOSTART=true`。
"""

from __future__ import annotations

import os
import subprocess
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from ..config import Scenario
from .local import build_start_command, scenario_base_url
from ..clients.http import http_get


def _exp_backoff_wait(
    url: str,
    *,
    max_wait_seconds: int = 1200,
    success_status: int = 200,
    headers: Optional[Dict[str, str]] = None,
) -> bool:
    """指数退避等待服务就绪。

    参数:
        url: 健康/探活 URL。
        max_wait_seconds: 最大等待时长（秒），默认 1200（20 分钟）。
        success_status: 视为就绪的状态码。
        headers: 可选请求头。

    返回值:
        bool: 在时限内就绪返回 True，否则 False。
    """

    deadline = time.time() + max_wait_seconds
    sleep_s = 1.0
    while time.time() < deadline:
        try:
            code, _ = http_get(url, timeout=min(sleep_s, 5.0), headers=headers)
            if code == success_status:
                return True
        except Exception:
            pass
        time.sleep(sleep_s)
        sleep_s = min(sleep_s * 2.0, 30.0)
    return False


@dataclass
class ServiceLauncher:
    """本地服务启动器。

    属性:
        scenario: 场景对象。
        project_root: 项目根目录。
        logs_dir: 日志目录，默认 `artifacts/logs`。
        proc: 子进程对象（启动后赋值）。
        log_path: 日志文件路径（启动后赋值）。
    """

    scenario: Scenario
    project_root: Path
    logs_dir: Path
    proc: Optional[subprocess.Popen[Any]] = None
    log_path: Optional[Path] = None

    def start(self) -> None:
        """启动本地服务并将输出重定向到日志文件。

        参数:
            无。

        返回值:
            无。

        副作用:
            创建子进程与日志文件。
        """

        self.logs_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
        log_name = f"service_{self.scenario.id}_{ts}.log"
        self.log_path = self.logs_dir / log_name
        cmd = build_start_command(self.scenario, self.project_root)
        # 以追加模式记录，便于多次启动也能写入同一文件（按时间戳区分）
        log_fp = self.log_path.open("a", encoding="utf-8")
        self.proc = subprocess.Popen(cmd, stdout=log_fp, stderr=subprocess.STDOUT)

    def wait_ready(self, max_wait_seconds: int = 1200) -> bool:
        """指数退避等待服务就绪。

        参数:
            max_wait_seconds: 最大等待时长（秒）。

        返回值:
            bool: True 表示就绪；False 表示超过时限仍未就绪。
        """

        base_url = scenario_base_url(self.scenario)
        # 常见可用健康端点：/v1/models 或根路径。此处尝试 /v1/models。
        health_url = f"{base_url.rstrip('/')}/models"
        return _exp_backoff_wait(health_url, max_wait_seconds=max_wait_seconds)

    def stop(self) -> None:
        """停止子进程（若仍存活）。"""

        if self.proc and self.proc.poll() is None:
            try:
                self.proc.terminate()
            except Exception:
                pass

    # 上下文管理支持
    def __enter__(self) -> "ServiceLauncher":
        return self

    def __exit__(
        self,
        exc_type: object | None,
        exc: object | None,
        tb: object | None,
    ) -> None:
        """上下文退出时停止子进程。"""
        self.stop()


def autostart_enabled(scenario: Scenario) -> bool:
    """判断是否启用自动启动。

    参数:
        scenario: 场景对象。

    返回值:
        bool: True 表示开启；默认 False。
    """

    if str(os.environ.get("VLLM_CIBENCH_AUTOSTART", "")).lower() in {"1", "true", "yes"}:
        return True
    raw = scenario.raw or {}
    return bool(raw.get("autostart", False))
