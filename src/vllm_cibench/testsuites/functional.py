"""功能测试执行器（OpenAI 兼容）。

在最小冒烟能力基础上，提供更通用的用例执行接口：
- 定义 `ChatCase` / `CompletionCase` 数据模型；
- 提供 `run_chat_case` / `run_completions_case` 单用例执行；
- 提供 `run_chat_suite` / `run_completions_suite` 批量执行并汇总。

注：此处面向真实 vLLM 服务的功能覆盖；项目自身的单元测试请仍放在
`tests/` 目录，通过 `requests-mock` 等方式隔离网络。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Optional, Sequence, cast

from vllm_cibench.clients.openai_client import OpenAICompatClient

# ============================
# 数据模型与结果结构
# ============================


@dataclass
class ChatCase:
    """Chat 用例描述。

    参数:
        id: 用例标识。
        messages: OpenAI 兼容消息数组。
        params: 额外请求参数（如 stream/tools/response_format 等）。
        expect_error: 期望出现错误（可选）。为 True 时表示任意 HTTPError
            都视为通过；为 False/None 时表示应成功（2xx）。

    返回值:
        无，作为输入配置模型使用。

    副作用:
        无。
    """

    id: str
    messages: List[Mapping[str, Any]]
    params: Mapping[str, Any]
    expect_error: Optional[bool] = None


@dataclass
class CompletionCase:
    """Completions 用例描述。

    参数:
        id: 用例标识。
        prompt: 提示词。
        params: 额外请求参数（如 n/logprobs/top_logprobs/stream 等）。
        expect_error: 期望错误（同 ChatCase）。
    """

    id: str
    prompt: str
    params: Mapping[str, Any]
    expect_error: Optional[bool] = None


SuiteResult = Dict[str, Any]


def _ok(payload: Any) -> SuiteResult:
    return {"ok": True, "error": None, "payload": payload}


def _err(msg: str) -> SuiteResult:
    return {"ok": False, "error": msg, "payload": None}


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


def run_chat_case(
    base_url: str,
    model: str,
    case: ChatCase,
    *,
    api_key: Optional[str] = None,
) -> SuiteResult:
    """执行单个 Chat 用例（支持 stream 与参数扩展）。

    参数:
        base_url: 服务基础 URL。
        model: 模型名。
        case: ChatCase 用例。
        api_key: 可选 API Key。

    返回值:
        dict: {ok: bool, error: Optional[str], payload: Any}。

    副作用:
        真实网络请求；HTTPError 将被捕获转为 error。
    """

    client = OpenAICompatClient(base_url=base_url, api_key=api_key)
    try:
        out = client.chat_completions(
            model=model, messages=case.messages, **dict(case.params)
        )
        if case.expect_error:
            return _err("expected error but got success")
        return _ok(out)
    except Exception as exc:  # requests.HTTPError 等
        if case.expect_error:
            return _ok({"exception": str(exc)})
        return _err(str(exc))


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


def run_chat_suite(
    base_url: str,
    model: str,
    cases: Sequence[ChatCase],
    *,
    api_key: Optional[str] = None,
) -> Dict[str, Any]:
    """批量执行 Chat 用例并汇总结果。

    参数:
        base_url: 服务基础 URL。
        model: 模型名。
        cases: ChatCase 序列。
        api_key: 可选 API Key。

    返回值:
        dict: {summary: {total, passed, failed}, results: [{id, ok, error}...]}

    副作用:
        真实网络请求。
    """

    results: List[Dict[str, Any]] = []
    passed = 0
    for c in cases:
        r = run_chat_case(base_url, model, c, api_key=api_key)
        results.append({"id": c.id, **r})
        if r["ok"]:
            passed += 1
    return {
        "summary": {
            "total": len(cases),
            "passed": passed,
            "failed": len(cases) - passed,
        },
        "results": results,
    }


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


def run_completions_case(
    base_url: str,
    model: str,
    case: CompletionCase,
    *,
    api_key: Optional[str] = None,
) -> SuiteResult:
    """执行单个 Completions 用例。

    参数:
        base_url: 服务基础 URL。
        model: 模型名。
        case: CompletionCase 用例。
        api_key: 可选 API Key。

    返回值:
        dict: {ok: bool, error: Optional[str], payload: Any}。

    副作用:
        真实网络请求；HTTPError 将被捕获转为 error。
    """

    client = OpenAICompatClient(base_url=base_url, api_key=api_key)
    try:
        out = client.completions(model=model, prompt=case.prompt, **dict(case.params))
        if case.expect_error:
            return _err("expected error but got success")
        return _ok(out)
    except Exception as exc:
        if case.expect_error:
            return _ok({"exception": str(exc)})
        return _err(str(exc))


def run_completions_suite(
    base_url: str,
    model: str,
    cases: Sequence[CompletionCase],
    *,
    api_key: Optional[str] = None,
) -> Dict[str, Any]:
    """批量执行 Completions 用例并汇总结果。"""

    results: List[Dict[str, Any]] = []
    passed = 0
    for c in cases:
        r = run_completions_case(base_url, model, c, api_key=api_key)
        results.append({"id": c.id, **r})
        if r["ok"]:
            passed += 1
    return {
        "summary": {
            "total": len(cases),
            "passed": passed,
            "failed": len(cases) - passed,
        },
        "results": results,
    }
