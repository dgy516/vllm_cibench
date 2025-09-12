"""极简版 :mod:`requests` 实现，仅供测试环境使用。

提供 ``get``/``post`` 接口与响应对象，并配合测试夹具实现可预设的
HTTP 模拟，避免依赖第三方库。
"""

from __future__ import annotations

import json as jsonlib
from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Tuple


class RequestException(Exception):
    """请求异常基类。"""


@dataclass
class Response:
    """模拟的 HTTP 响应对象。"""

    status_code: int
    text: str = ""
    _json: Any | None = None

    def json(self) -> Any:
        """返回解析后的 JSON 数据。"""

        if self._json is not None:
            return self._json
        return jsonlib.loads(self.text)

    def raise_for_status(self) -> None:
        """非 2xx 状态码时抛出 :class:`RequestException`。"""

        if not 200 <= self.status_code < 400:
            raise RequestException(f"status {self.status_code}")


@dataclass
class _RequestRecord:
    method: str
    url: str
    text: str


_mock_registry: Dict[Tuple[str, str], List[Dict[str, Any]]] = {}
_request_history: List[_RequestRecord] = []


def _register(method: str, url: str, resp: Mapping[str, Any]) -> None:
    """注册预设响应（供测试夹具调用）。"""

    _mock_registry.setdefault((method.upper(), url), []).append(dict(resp))


def _reset() -> None:
    """清空所有预设响应与历史。"""

    _mock_registry.clear()
    _request_history.clear()


def _build_response(data: Dict[str, Any]) -> Response:
    """根据注册信息构造 :class:`Response` 对象。"""

    body_text = data.get("text")
    if "json" in data and body_text is None:
        body_text = jsonlib.dumps(data["json"])
    return Response(
        status_code=int(data.get("status_code", 200)),
        text=body_text or "",
        _json=data.get("json"),
    )


def get(
    url: str, timeout: float | None = None, headers: Mapping[str, str] | None = None
) -> Response:  # noqa: ARG001
    """发送 GET 请求并返回模拟响应。"""

    key = ("GET", url)
    _request_history.append(_RequestRecord("GET", url, ""))
    if key not in _mock_registry or not _mock_registry[key]:
        raise RequestException(f"unmocked url: {url}")
    data = _mock_registry[key].pop(0)
    return _build_response(data)


def post(
    url: str,
    *,
    headers: Mapping[str, str] | None = None,
    json: Mapping[str, Any] | None = None,
    timeout: float | None = None,
) -> Response:
    """发送 POST 请求并返回模拟响应。"""

    body_text = ""
    if json is not None:
        body_text = jsonlib.dumps(json)
    _request_history.append(_RequestRecord("POST", url, body_text))
    key = ("POST", url)
    if key not in _mock_registry or not _mock_registry[key]:
        raise RequestException(f"unmocked url: {url}")
    data = _mock_registry[key].pop(0)
    return _build_response(data)
