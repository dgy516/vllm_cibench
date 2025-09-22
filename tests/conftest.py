"""测试全局配置与模拟工具。

将 `src` 目录加入 `sys.path`，以便在未打包安装时可直接导入包；
同时提供自定义的 `requests_mock` fixture，用于在单测中模拟 OpenAI SDK 的
`chat.completions.create` 调用，保持历史断言逻辑不变。
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from typing import Any, Dict, Iterable, Iterator, List, Mapping, MutableMapping, Optional, Tuple

import pytest
import requests
import requests_mock as requests_mock_lib

from pathlib import Path

SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from vllm_cibench.clients.openai_client import OpenAICompatClient  # noqa: E402


@dataclass
class _RegisteredResponse:
    """记录通过 `requests_mock.post` 注册的响应。"""

    json_body: Any
    content: Optional[bytes]
    status_code: int
    headers: Optional[Mapping[str, str]]

    @classmethod
    def from_kwargs(cls, kwargs: MutableMapping[str, Any]) -> "_RegisteredResponse":
        """将 `requests_mock.post` 的关键字参数转为内部结构。

        参数:
            kwargs: 注册 mock 时传入的关键字参数。

        返回值:
            _RegisteredResponse: 归一化后的响应配置。

        副作用:
            无。
        """

        raw = kwargs.get("content")
        if isinstance(raw, str):
            content = raw.encode()
        else:
            content = raw
        status = int(kwargs.get("status_code", 200))
        return cls(
            json_body=kwargs.get("json"),
            content=content,
            status_code=status,
            headers=kwargs.get("headers"),
        )


@dataclass
class _RequestRecord:
    """仿照 `requests_mock` 的请求记录对象。"""

    method: str
    url: str
    body: Optional[Dict[str, Any]]

    def json(self) -> Optional[Dict[str, Any]]:
        """返回请求体（dict），用于测试中的断言。

        参数:
            无。

        返回值:
            Optional[Dict[str, Any]]: 若存在请求体则返回字典，否则返回 None。

        副作用:
            无。
        """

        return self.body

    @property
    def text(self) -> str:
        """返回 JSON 序列化后的请求体，保持历史断言兼容。"""

        if self.body is None:
            return ""
        return json.dumps(self.body, ensure_ascii=False, default=str)


class _FakeModel:
    """简单的 Pydantic 模型替身，仅实现 `model_dump`。"""

    def __init__(self, payload: Dict[str, Any]):
        self._payload = payload

    def model_dump(self) -> Dict[str, Any]:
        """返回底层字典。

        参数:
            无。

        返回值:
            Dict[str, Any]: 复制后的响应字典。

        副作用:
            无。
        """

        return self._payload


class _FakeStream:
    """模拟 `openai.Stream`，支持迭代 chunk。"""

    def __init__(self, chunks: Iterable[Dict[str, Any]]):
        self._chunks = [_FakeModel(dict(chunk)) for chunk in chunks]

    def __iter__(self) -> Iterator[_FakeModel]:
        """返回迭代器以遍历 chunk。

        参数:
            无。

        返回值:
            Iterator[_FakeModel]: 逐个产出 chunk 的迭代器。

        副作用:
            无。
        """

        return iter(self._chunks)

    def close(self) -> None:
        """与真实对象保持接口一致（此处无操作）。

        参数:
            无。

        返回值:
            None。

        副作用:
            无。
        """

        return None


class _FakeChatCompletions:
    """基于注册响应的 `chat.completions.create` 替身。"""

    def __init__(self, owner: "_FakeOpenAI") -> None:
        """保存上层客户端引用。

        参数:
            owner: 假 OpenAI 客户端。

        返回值:
            None。

        副作用:
            无。
        """

        self._owner = owner

    def create(self, **payload: Any) -> Any:
        """返回预注册的响应或触发 HTTPError。

        参数:
            payload: OpenAI SDK `create` 的关键字参数。

        返回值:
            Any: 假响应对象或流，行为与真实 SDK 对齐。

        副作用:
            记录请求历史，更新响应队列。
        """

        url = f"{self._owner.base_url}/chat/completions"
        body = {key: value for key, value in payload.items()}
        record = _RequestRecord("POST", url, body)
        self._owner.wrapper.register_request(record)

        response = self._owner.wrapper.next_response("POST", url)
        if response.status_code >= 400:
            err = requests.HTTPError(f"{response.status_code} error")
            err.response = _FakeResponse(response.status_code, response.json_body)
            raise err

        if body.get("stream"):
            chunks = _parse_stream_chunks(response.content)
            return _FakeStream(chunks)

        payload_dict = dict(response.json_body or {})
        return _FakeModel(payload_dict)


class _FakeChat:
    """封装 chat 子资源。"""

    def __init__(self, owner: "_FakeOpenAI") -> None:
        self.completions = _FakeChatCompletions(owner)


class _FakeOpenAI:
    """用于测试的 OpenAI 客户端替身。"""

    def __init__(
        self,
        wrapper: "_RequestsMockWrapper",
        *,
        base_url: Any,
        api_key: Optional[str],
        default_headers: Optional[Mapping[str, str]],
    ) -> None:
        """保存 OpenAI 客户端初始化参数。

        参数:
            wrapper: 外层 mock 包装器。
            base_url: 服务基础 URL。
            api_key: API 密钥（可为 None）。
            default_headers: 额外请求头。

        返回值:
            None。

        副作用:
            构造 chat 子资源。
        """

        self.wrapper = wrapper
        self.base_url = str(base_url).rstrip("/")
        self.api_key = api_key
        self.default_headers = dict(default_headers or {})
        self.chat = _FakeChat(self)


class _FakeResponse:
    """requests.HTTPError.response 的最小实现。"""

    def __init__(self, status_code: int, json_body: Any) -> None:
        """保存错误响应信息。

        参数:
            status_code: HTTP 状态码。
            json_body: 原始响应体。

        返回值:
            None。

        副作用:
            无。
        """

        self.status_code = status_code
        self._json_body = json_body
        self.text = (
            json.dumps(json_body, ensure_ascii=False, default=str)
            if json_body is not None
            else ""
        )

    def json(self) -> Any:
        """返回响应体。

        参数:
            无。

        返回值:
            Any: 原始 JSON 数据。

        副作用:
            无。
        """

        return self._json_body


class _RequestsMockWrapper:
    """封装真实 `requests_mock.Mocker`，并追加 OpenAI stub 行为。"""

    def __init__(self, mock: requests_mock_lib.Mocker, monkeypatch: pytest.MonkeyPatch):
        """初始化包装器并替换 OpenAI 客户端工厂。

        参数:
            mock: 真实的 requests-mock 对象。
            monkeypatch: pytest 的 monkeypatch 工具。

        返回值:
            None。

        副作用:
            修改 `OpenAICompatClient._client_factory`。
        """

        self._mock = mock
        self._history: List[_RequestRecord] = []
        self._responses: Dict[Tuple[str, str], List[_RegisteredResponse]] = {}

        def _factory(
            *,
            base_url: Any,
            api_key: Optional[str],
            default_headers: Optional[Mapping[str, str]] = None,
        ) -> _FakeOpenAI:
            return _FakeOpenAI(
                self,
                base_url=base_url,
                api_key=api_key,
                default_headers=default_headers,
            )

        monkeypatch.setattr(OpenAICompatClient, "_client_factory", staticmethod(_factory))

    def register_request(self, record: _RequestRecord) -> None:
        """记录一次 OpenAI chat 请求。

        参数:
            record: 需记录的请求体。

        返回值:
            None。

        副作用:
            更新内部历史列表。
        """

        self._history.append(record)

    def next_response(self, method: str, url: str) -> _RegisteredResponse:
        """按注册顺序返回下一条响应配置。

        参数:
            method: HTTP 方法名。
            url: 完整请求 URL。

        返回值:
            _RegisteredResponse: 下一条预注册响应。

        副作用:
            从队列中弹出该响应。
        """

        key = (method.upper(), url)
        queue = self._responses.get(key)
        if not queue:
            raise AssertionError(f"no registered response for {method} {url}")
        return queue.pop(0)

    @property
    def request_history(self) -> List[_RequestRecord]:
        """合并 OpenAI 模拟记录与真实 HTTP 请求记录。

        参数:
            无。

        返回值:
            List[_RequestRecord]: 历史请求列表（包含真实与模拟请求）。

        副作用:
            无。
        """

        return self._history + list(self._mock.request_history)

    def post(self, url: str, *args: Any, **kwargs: Any):
        """记录响应后转发给真实 mocker。

        参数:
            url: 注册的目标 URL。
            *args: 位置参数，透传给真实 mocker。
            **kwargs: 关键字参数，透传并用于记录响应。

        返回值:
            Any: 真实 mocker 的返回值。

        副作用:
            更新响应队列。
        """

        key = ("POST", url)
        entries: List[_RegisteredResponse] = []
        if args and isinstance(args[0], list):
            for item in args[0]:
                if isinstance(item, Mapping):
                    entries.append(_RegisteredResponse.from_kwargs(dict(item)))
        else:
            entries.append(_RegisteredResponse.from_kwargs(dict(kwargs)))
        self._responses.setdefault(key, []).extend(entries)
        return self._mock.post(url, *args, **kwargs)

    def __getattr__(self, item: str):
        """其他属性透传至真实 mocker。

        参数:
            item: 访问的属性名。

        返回值:
            Any: 真实 mocker 对应属性。

        副作用:
            无。
        """

        return getattr(self._mock, item)


def _parse_stream_chunks(raw: Optional[bytes]) -> List[Dict[str, Any]]:
    """解析 SSE 字符串，返回 chunk 列表。

    参数:
        raw: SSE 数据的原始字节串。

    返回值:
        List[Dict[str, Any]]: 解析后的 chunk 列表。

    副作用:
        无。
    """

    if not raw:
        return []
    text = raw.decode("utf-8")
    chunks: List[Dict[str, Any]] = []
    for line in text.splitlines():
        if not line:
            continue
        if not line.startswith("data:"):
            continue
        data = line[len("data:") :].strip()
        if data == "[DONE]":
            break
        chunks.append(json.loads(data))
    return chunks


@pytest.fixture
def requests_mock(monkeypatch: pytest.MonkeyPatch):
    """提供与 `requests_mock` 插件兼容的接口，并注入 OpenAI stub。

    参数:
        monkeypatch: pytest 提供的 patch 工具，用于替换客户端工厂。

    返回值:
        _RequestsMockWrapper: 兼容历史测试的 mock 对象。

    副作用:
        动态修改 `OpenAICompatClient` 的客户端工厂。
    """

    with requests_mock_lib.Mocker() as real_mock:
        wrapper = _RequestsMockWrapper(real_mock, monkeypatch)
        yield wrapper
