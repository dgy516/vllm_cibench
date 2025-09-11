"""HTTP 客户端与健康检查工具。

提供基础的 GET 请求、带重试的探活与等待服务就绪工具。
"""

from __future__ import annotations

import json
import time
from typing import Any, Dict, Optional, Tuple

import requests


def http_get(
    url: str,
    timeout: float = 5.0,
    headers: Optional[Dict[str, str]] = None,
    expect_json: bool = False,
) -> Tuple[int, Any]:
    """发送 GET 请求。

    参数:
        url: 目标 URL。
        timeout: 超时时间（秒）。
        headers: 额外请求头。
        expect_json: 是否期望 JSON 响应，若为真则解析 JSON。

    返回值:
        (status_code, body): 若 `expect_json=True` 则 body 为解析后的对象，否则为字符串。

    副作用:
        网络请求；可能抛出 `requests.RequestException`。
    """

    resp = requests.get(url, timeout=timeout, headers=headers)
    if expect_json:
        try:
            return resp.status_code, resp.json()
        except json.JSONDecodeError:
            return resp.status_code, resp.text
    return resp.status_code, resp.text


def wait_for_ready(
    url: str,
    timeout_seconds: int = 60,
    interval_seconds: float = 1.0,
    success_status: int = 200,
) -> bool:
    """轮询等待目标 URL 就绪（返回期望状态码）。

    参数:
        url: 探测 URL（例如服务的 `/v1/models` 或根路径）。
        timeout_seconds: 总等待时长上限（秒）。
        interval_seconds: 轮询间隔（秒）。
        success_status: 视为就绪的状态码（默认 200）。

    返回值:
        bool: 在超时前就绪返回 True，否则 False。

    副作用:
        周期性网络请求与 `time.sleep` 调用。
    """

    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        try:
            code, _ = http_get(url, timeout=min(interval_seconds * 2, 5.0))
            if code == success_status:
                return True
        except requests.RequestException:
            # 网络异常时忽略并重试
            pass
        time.sleep(interval_seconds)
    # 超时，若最后一次有异常，仅用于调试（不抛出）
    return False
