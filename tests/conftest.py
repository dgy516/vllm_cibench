"""测试全局配置与辅助 fixture。

将 `src` 目录加入 `sys.path`，以便在未打包安装时可直接导入包，
同时提供简易版的 ``requests_mock`` fixture 以脱离第三方库依赖。
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Dict, Iterator

import pytest

# 将 ``src`` 目录加入 ``sys.path``，便于测试直接导入包
SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

import requests  # noqa: E402  导入位于 ``src`` 的极简实现


class _RequestMocker:
    """记录并返回预设响应的轻量 Mock 工具。

    属性:
        request_history: 已收到的请求记录列表，供断言使用。
    """

    def __init__(self) -> None:
        """初始化，引用请求历史。"""

        self.request_history = requests._request_history

    def get(self, url: str, responses=None, **kw: Dict) -> None:  # type: ignore[override]
        """注册 GET 响应，可接受单个或序列。"""

        if responses is not None and not isinstance(responses, dict):
            for r in responses:
                requests._register("GET", url, r)
        else:
            data = responses or kw
            requests._register("GET", url, data)

    def post(self, url: str, responses=None, **kw: Dict) -> None:  # type: ignore[override]
        """注册 POST 响应，可接受单个或序列。"""

        if responses is not None and not isinstance(responses, dict):
            for r in responses:
                requests._register("POST", url, r)
        else:
            data = responses or kw
            requests._register("POST", url, data)


@pytest.fixture
def requests_mock() -> Iterator[_RequestMocker]:
    """提供极简 ``requests_mock`` 实现。

    在每个测试前后清理注册表，确保互不影响。
    """

    requests._reset()
    mocker = _RequestMocker()
    yield mocker
    requests._reset()
