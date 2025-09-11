"""功能测试执行器（OpenAI 兼容）。

提供最小化的功能性冒烟测试：向 `/v1/chat/completions` 发送请求并校验结构。
"""

from __future__ import annotations

from typing import Any, Dict, List, Mapping, Optional

from vllm_cibench.clients.openai_client import OpenAICompatClient


def run_basic_chat(
    client: OpenAICompatClient,
    model: str,
    messages: List[Mapping[str, Any]],
    **params: Any,
) -> Dict[str, Any]:
    """运行最小 Chat Completions 请求并返回响应。

    参数:
        client: OpenAI 兼容客户端。
        model: 模型名。
        messages: OpenAI 消息数组。
        params: 其他请求参数（如 temperature/top_p 等）。

    返回值:
        dict: 接口返回的 JSON 响应。

    副作用:
        发起网络请求。
    """

    return client.chat_completions(model=model, messages=messages, **params)


def run_smoke_suite(
    base_url: str,
    model: str,
    api_key: Optional[str] = None,
) -> Dict[str, Any]:
    """执行基础冒烟套件（单次请求）。

    参数:
        base_url: 服务基础 URL，例如 `http://127.0.0.1:9000/v1`。
        model: 模型名。
        api_key: 可选 API Key。

    返回值:
        dict: 响应体，调用者可进一步断言字段。

    副作用:
        发起网络请求。
    """

    client = OpenAICompatClient(base_url=base_url, api_key=api_key)
    messages: List[Mapping[str, Any]] = [
        {"role": "user", "content": "Say hello in one word."}
    ]
    return run_basic_chat(client, model, messages, temperature=0)
