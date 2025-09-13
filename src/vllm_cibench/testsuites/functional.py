"""功能测试执行器（OpenAI 兼容）。

提供最小化的功能性冒烟测试：向 `/v1/chat/completions` 发送请求并校验结构。
"""

from __future__ import annotations

from typing import Any, Dict, List, Mapping, Optional, cast

from vllm_cibench.clients.openai_client import OpenAICompatClient


def run_basic_chat(
    client: OpenAICompatClient,
    model: str,
    messages: List[Mapping[str, Any]],
    **params: Any,
) -> Dict[str, Any] | List[Dict[str, Any]]:
    """运行最小 Chat Completions 请求并返回响应。

    参数:
        client: OpenAI 兼容客户端。
        model: 模型名。
        messages: OpenAI 消息数组。
        params: 其他请求参数（如 temperature/top_p/stream 等）。

    返回值:
        当 `stream=False` 时返回单个 JSON 响应；当 `stream=True` 时返
        回按顺序排列的 chunk 列表。

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
    out = run_basic_chat(client, model, messages, temperature=0)
    return cast(Dict[str, Any], out)


def get_reasoning(out: Mapping[str, Any], key: str = "reasoning_content") -> str:
    """从响应中提取推理内容。

    参数:
        out: `/v1/chat/completions` 的响应体。
        key: 推理字段键名，默认 ``reasoning_content``。

    返回值:
        str: 推理内容字符串。

    副作用:
        无。

    异常:
        KeyError: 当响应缺少目标字段时抛出。
    """

    choices = out.get("choices")
    if not choices:
        raise KeyError("choices missing in response")
    message = choices[0].get("message", {})
    if key not in message:
        raise KeyError(f"reasoning key not found: {key}")
    return str(message[key])


def run_basic_completion(
    base_url: str,
    model: str,
    prompt: str,
    api_key: Optional[str] = None,
    **params: Any,
) -> Dict[str, Any] | List[Dict[str, Any]]:
    """执行基础文本补全（/v1/completions）。

    参数:
        base_url: 服务基础 URL，例如 `http://127.0.0.1:9000/v1`。
        model: 模型名。
        prompt: 文本补全提示词。
        api_key: 可选 API Key。
        params: 其他请求参数（如 temperature/top_p/stream 等）。

    返回值:
        当 `stream=False` 时返回单个 JSON 响应；当 `stream=True` 时返
        回按顺序排列的 chunk 列表。

    副作用:
        发起网络请求。
    """

    client = OpenAICompatClient(base_url=base_url, api_key=api_key)
    return client.completions(model=model, prompt=prompt, **params)
