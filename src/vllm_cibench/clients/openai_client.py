"""OpenAI 兼容客户端封装。

依赖官方 `openai` SDK 的 `OpenAI.chat.completions.create` 接口发起请求，
避免重复实现 HTTP 逻辑，同时保持对 stream 与非 stream 模式的兼容行为。
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Callable, ClassVar, Dict, Iterable, List, Mapping, Optional, cast

import requests

from openai import (
    APIConnectionError,
    APITimeoutError,
    APIStatusError,
    OpenAI,
    OpenAIError,
)

from openai.types.chat import ChatCompletionChunk


@dataclass
class OpenAICompatClient:
    """OpenAI 兼容客户端。

    参数:
        base_url: 服务基础 URL，例如 `http://127.0.0.1:9000/v1`。
        api_key: 认证用 API Key（可选）。
        default_headers: 默认请求头（可选）。

    返回值:
        客户端实例，可调用 `chat_completions` 等方法。

    副作用:
        无；仅保存配置，实际网络请求在方法调用时执行。
    """

    base_url: str
    api_key: Optional[str] = None
    default_headers: Optional[Mapping[str, str]] = None

    _client_factory: ClassVar[
        Callable[..., OpenAI]
    ] = OpenAI  # 允许在测试中替换
    _client: OpenAI = field(init=False, repr=False)

    def __post_init__(self) -> None:
        """初始化内部 OpenAI 客户端。

        参数:
            无（使用 dataclass 字段作为输入）。

        返回值:
            None。

        副作用:
            根据初始化参数构造并缓存 `_client` 实例。
        """

        headers = dict(self.default_headers) if self.default_headers else None
        self._client = self._client_factory(
            api_key=self.api_key or "EMPTY",
            base_url=self.base_url,
            default_headers=headers,
        )

    def _headers(self, extra: Optional[Mapping[str, str]] = None) -> Dict[str, str]:
        """构造请求头。

        参数:
            extra: 额外的请求头。

        返回值:
            dict: 合并后的请求头，包含 `Authorization`（如提供了 api_key）。

        副作用:
            无。
        """

        headers: Dict[str, str] = {
            "Content-Type": "application/json",
        }
        if self.default_headers:
            headers.update(dict(self.default_headers))
        if extra:
            headers.update(dict(extra))
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    @staticmethod
    def _dump_openai_payload(payload: Any) -> Dict[str, Any]:
        """将 OpenAI SDK 返回对象转换为原始 dict。

        参数:
            payload: `openai` SDK 返回的对象或其替身。

        返回值:
            dict: 兼容 JSON 的基础字典。

        副作用:
            无。
        """

        if isinstance(payload, dict):
            return payload
        if hasattr(payload, "model_dump"):
            return cast(Dict[str, Any], payload.model_dump())
        raise TypeError(f"unsupported payload type: {type(payload)!r}")

    def chat_completions(
        self,
        model: str,
        messages: List[Mapping[str, Any]],
        **params: Any,
    ) -> Dict[str, Any] | List[Dict[str, Any]]:
        """调用 `/v1/chat/completions` 端点。

        参数:
            model: 模型名。
            messages: OpenAI 格式的消息数组。
            params: 其他可选参数（如 temperature/top_p/stream 等）。

        返回值:
            当 `stream=False` 时返回单个 JSON 响应；当 `stream=True` 时返
            回按顺序排列的 chunk 列表。

        副作用:
            发起网络请求；可能抛出 `requests.RequestException`。
        """

        payload: Dict[str, Any] = {"model": model, "messages": messages}
        payload.update(params)
        stream = bool(params.get("stream"))

        try:
            result = self._client.chat.completions.create(**payload)
        except APIStatusError as err:
            raise requests.HTTPError(str(err)) from err
        except (APIConnectionError, APITimeoutError, OpenAIError) as err:
            raise requests.RequestException(str(err)) from err

        if not stream:
            return self._dump_openai_payload(result)

        chunks: List[Dict[str, Any]] = []
        iterator: Iterable[ChatCompletionChunk] = cast(Iterable[ChatCompletionChunk], result)
        try:
            for chunk in iterator:
                chunks.append(self._dump_openai_payload(chunk))
        finally:
            close = getattr(result, "close", None)
            if callable(close):
                close()
        return chunks

    def completions(
        self,
        model: str,
        prompt: str,
        **params: Any,
    ) -> Dict[str, Any] | List[Dict[str, Any]]:
        """调用 `/v1/completions` 端点。

        参数:
            model: 模型名。
            prompt: 文本补全提示。
            params: 其他可选参数（如 temperature/top_p/top_k/stream 等）。

        返回值:
            当 `stream=False` 时返回单个 JSON 响应；当 `stream=True` 时返
            回按顺序排列的 chunk 列表。

        副作用:
            发起网络请求；可能抛出 `requests.RequestException` 或 `HTTPError`。
        """

        url = f"{self.base_url.rstrip('/')}/completions"
        payload: Dict[str, Any] = {"model": model, "prompt": prompt}
        payload.update(params)
        stream = bool(params.get("stream"))
        resp = requests.post(
            url,
            headers=self._headers(),
            json=payload,
            timeout=30,
            stream=stream,
        )
        resp.raise_for_status()
        if not stream:
            return cast(Dict[str, Any], resp.json())

        chunks: List[Dict[str, Any]] = []
        for line in resp.iter_lines():
            if not line:
                continue
            if line.startswith(b"data:"):
                data = line[len(b"data:") :].strip()
                if data == b"[DONE]":
                    break
                chunks.append(json.loads(data))
        return chunks
