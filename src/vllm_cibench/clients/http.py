"""简单的 HTTP 工具。"""

from __future__ import annotations

import time

import requests  # type: ignore[import-untyped]


def wait_for_http(url: str, timeout_s: float = 1.0, max_attempts: int = 5) -> bool:
    """轮询等待 HTTP 服务返回 200。

    参数:
        url: 健康检查的完整 URL。
        timeout_s: 单次请求的超时时间（秒）。
        max_attempts: 最大重试次数。

    返回值:
        bool: 成功返回 True，超过重试次数仍失败返回 False。

    副作用:
        发起网络请求并 sleep。
    """

    for _ in range(max_attempts):
        try:
            resp = requests.get(url, timeout=timeout_s)
            if resp.status_code == 200:
                return True
        except Exception:
            pass
        time.sleep(timeout_s)
    return False
