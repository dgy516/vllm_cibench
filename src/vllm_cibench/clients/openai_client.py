"""OpenAI 兼容客户端封装。

使用 `requests` 以 OpenAI 兼容的 REST 方式访问 `/v1/chat/completions` 等端点，
便于在单元测试中通过 `requests-mock` 进行模拟，不依赖官方 SDK 的 httpx 传输。
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Optional, cast

import requests


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

        url = f"{self.base_url.rstrip('/')}/chat/completions"
        payload: Dict[str, Any] = {"model": model, "messages": messages}
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
