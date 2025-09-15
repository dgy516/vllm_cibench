# isort: skip_file
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

# isort: off
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple, cast
from vllm_cibench.clients.openai_client import OpenAICompatClient

# isort: on

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
        required_capabilities: 该用例所需能力列表（如 "chat.logprobs"）。
        skip_if_unsupported: 当缺少能力时是否跳过此用例（默认 True）。

    返回值:
        无，作为输入配置模型使用。

    副作用:
        无。
    """

    id: str
    messages: List[Mapping[str, Any]]
    params: Mapping[str, Any]
    expect_error: Optional[bool] = None
    required_capabilities: Optional[Sequence[str]] = None
    skip_if_unsupported: bool = True


@dataclass
class CompletionCase:
    """Completions 用例描述。

    参数:
        id: 用例标识。
        prompt: 提示词。
        params: 额外请求参数（如 n/logprobs/top_logprobs/stream 等）。
        expect_error: 期望错误（同 ChatCase）。
        required_capabilities: 该用例所需能力列表（如 "completions.suffix"）。
        skip_if_unsupported: 当缺少能力时是否跳过此用例（默认 True）。
    """

    id: str
    prompt: str
    params: Mapping[str, Any]
    expect_error: Optional[bool] = None
    required_capabilities: Optional[Sequence[str]] = None
    skip_if_unsupported: bool = True


SuiteResult = Dict[str, Any]


def _ok(payload: Any) -> SuiteResult:
    return {"ok": True, "error": None, "payload": payload}


def _err(msg: str) -> SuiteResult:
    return {"ok": False, "error": msg, "payload": None}


def _as_list(v: Any) -> List[Any]:
    if v is None:
        return []
    if isinstance(v, list):
        return v
    return [v]


def _boundary_values(values: Iterable[Any]) -> List[Any]:
    """返回边界值组合：取列表的第一个与最后一个，避免笛卡尔积爆炸。

    参数:
        values: 候选值序列。

    返回值:
        列表：去重后的首尾两个值（如仅一个则返回一个）。
    """

    vals = list(values)
    if not vals:
        return []
    if len(vals) == 1:
        return [vals[0]]
    return [vals[0], vals[-1]]


def build_cases_from_config(
    data: Mapping[str, Any]
) -> Tuple[List[ChatCase], List[CompletionCase]]:
    """从配置字典构建 Chat/Completions 用例列表（含边界与负路径）。

    配置示例（参考 configs/tests/functional.yaml）：
        suite: true
        cases:
          - id: chat_basic
            type: chat
            messages: [...]
            params: {temperature: 0}
          - id: comp_basic
            type: completions
            prompt: "Hello"
            params: {max_tokens: 8}
        matrices:
          chat:
            - id_prefix: chat_bounds
              messages: [...]
              params_grid:
                temperature: [0.0, 1.0]
                top_p: [0.0, 1.0]
                top_k: [1, 8]
              expect_error: false
        negative:
          chat:
            - id_prefix: chat_invalid
              messages: [...]
              params_list:
                - {top_p: 1.5}
              expect_error: true
          completions:
            - id_prefix: comp_invalid
              prompt: "hi"
              params_list:
                - {logprobs: true, top_logprobs: 0}
              expect_error: true

    参数:
        data: 配置字典。

    返回值:
        (chat_cases, completion_cases)
    """

    chat_cases: List[ChatCase] = []
    comp_cases: List[CompletionCase] = []

    # 1) 显式 cases
    for item in _as_list(data.get("cases")):
        t = str(item.get("type", "")).lower()
        cid = str(item.get("id", t or "case"))
        if t == "chat":
            chat_cases.append(
                ChatCase(
                    id=cid,
                    messages=list(item.get("messages", []) or []),
                    params=dict(item.get("params", {}) or {}),
                    expect_error=item.get("expect_error"),
                    required_capabilities=list(
                        item.get("required_capabilities", []) or []
                    )
                    or None,
                    skip_if_unsupported=bool(item.get("skip_if_unsupported", True)),
                )
            )
        elif t in ("completion", "completions"):
            comp_cases.append(
                CompletionCase(
                    id=cid,
                    prompt=str(item.get("prompt", "")),
                    params=dict(item.get("params", {}) or {}),
                    expect_error=item.get("expect_error"),
                    required_capabilities=list(
                        item.get("required_capabilities", []) or []
                    )
                    or None,
                    skip_if_unsupported=bool(item.get("skip_if_unsupported", True)),
                )
            )

    # 2) 边界矩阵（不做全笛卡尔，仅取每个维度的首尾）
    matrices = data.get("matrices", {}) or {}
    for entry in _as_list(matrices.get("chat")):
        prefix = str(entry.get("id_prefix", "chat_bounds"))
        messages = list(entry.get("messages", []) or [])
        grid: Mapping[str, Any] = entry.get("params_grid", {}) or {}
        expect_error = bool(entry.get("expect_error", False))
        req_caps = list(entry.get("required_capabilities", []) or []) or None
        skip_unsupported = bool(entry.get("skip_if_unsupported", True))
        for k, vals in grid.items():
            for v in _boundary_values(_as_list(vals)):
                cid = f"{prefix}_{k}_{str(v).replace(' ', '_')}"
                chat_cases.append(
                    ChatCase(
                        id=cid,
                        messages=messages,
                        params={k: v},
                        expect_error=expect_error,
                        required_capabilities=req_caps,
                        skip_if_unsupported=skip_unsupported,
                    )
                )
    for entry in _as_list(matrices.get("completions")):
        prefix = str(entry.get("id_prefix", "comp_bounds"))
        prompt = str(entry.get("prompt", "Hello"))
        cgrid: Mapping[str, Any] = entry.get("params_grid", {}) or {}
        expect_error = bool(entry.get("expect_error", False))
        req_caps_c = list(entry.get("required_capabilities", []) or []) or None
        skip_unsupported_c = bool(entry.get("skip_if_unsupported", True))
        for k, vals in cgrid.items():
            for v in _boundary_values(_as_list(vals)):
                cid = f"{prefix}_{k}_{str(v).replace(' ', '_')}"
                comp_cases.append(
                    CompletionCase(
                        id=cid,
                        prompt=prompt,
                        params={k: v},
                        expect_error=expect_error,
                        required_capabilities=req_caps_c,
                        skip_if_unsupported=skip_unsupported_c,
                    )
                )

    # 3) 负路径
    negative = data.get("negative", {}) or {}
    for entry in _as_list(negative.get("chat")):
        prefix = str(entry.get("id_prefix", "chat_neg"))
        messages = list(entry.get("messages", []) or [])
        req_caps = list(entry.get("required_capabilities", []) or []) or None
        skip_unsupported = bool(entry.get("skip_if_unsupported", True))
        for idx, params in enumerate(_as_list(entry.get("params_list"))):
            cid = f"{prefix}_{idx}"
            chat_cases.append(
                ChatCase(
                    id=cid,
                    messages=messages,
                    params=dict(params or {}),
                    expect_error=True,
                    required_capabilities=req_caps,
                    skip_if_unsupported=skip_unsupported,
                )
            )
    for entry in _as_list(negative.get("completions")):
        prefix = str(entry.get("id_prefix", "comp_neg"))
        prompt = str(entry.get("prompt", "Hello"))
        req_caps_c = list(entry.get("required_capabilities", []) or []) or None
        skip_unsupported_c = bool(entry.get("skip_if_unsupported", True))
        for idx, params in enumerate(_as_list(entry.get("params_list"))):
            cid = f"{prefix}_{idx}"
            comp_cases.append(
                CompletionCase(
                    id=cid,
                    prompt=prompt,
                    params=dict(params or {}),
                    expect_error=True,
                    required_capabilities=req_caps_c,
                    skip_if_unsupported=skip_unsupported_c,
                )
            )

    return chat_cases, comp_cases


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
    capabilities: Optional[Sequence[str]] = None,
) -> Dict[str, Any]:
    """批量执行 Chat 用例并汇总结果（支持能力跳过）。

    参数:
        base_url: 服务基础 URL。
        model: 模型名。
        cases: ChatCase 序列。
        api_key: 可选 API Key。
        capabilities: 服务已支持的能力列表（如 ["chat.logprobs"])；
            若用例声明了 `required_capabilities` 且不被包含，且 `skip_if_unsupported=True`，
            则该用例标记为 skipped 而不执行网络请求。

    返回值:
        dict: {summary: {total, passed, failed, skipped}, results: [{id, ok, skipped, error}...]}

    副作用:
        真实网络请求（对未跳过的用例）。
    """

    results: List[Dict[str, Any]] = []
    passed = 0
    skipped = 0
    caps = set(capabilities or [])
    for c in cases:
        reqs = set(c.required_capabilities or [])
        if c.skip_if_unsupported and reqs and not reqs.issubset(caps):
            results.append(
                {
                    "id": c.id,
                    "ok": False,
                    "skipped": True,
                    "error": None,
                    "payload": None,
                    "missing_capabilities": sorted(reqs - caps),
                }
            )
            skipped += 1
            continue
        r = run_chat_case(base_url, model, c, api_key=api_key)
        results.append({"id": c.id, "skipped": False, **r})
        if r["ok"]:
            passed += 1
    return {
        "summary": {
            "total": len(cases),
            "passed": passed,
            "failed": len(cases) - passed - skipped,
            "skipped": skipped,
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
    capabilities: Optional[Sequence[str]] = None,
) -> Dict[str, Any]:
    """批量执行 Completions 用例并汇总结果（支持能力跳过）。

    参数:
        base_url: 服务基础 URL。
        model: 模型名。
        cases: CompletionCase 序列。
        api_key: 可选 API Key。
        capabilities: 服务能力列表（如 ["completions.suffix"]）。

    返回值:
        dict: {summary: {total, passed, failed, skipped}, results: [...]}。

    副作用:
        真实网络请求（对未跳过的用例）。
    """

    results: List[Dict[str, Any]] = []
    passed = 0
    skipped = 0
    caps = set(capabilities or [])
    for c in cases:
        reqs = set(c.required_capabilities or [])
        if c.skip_if_unsupported and reqs and not reqs.issubset(caps):
            results.append(
                {
                    "id": c.id,
                    "ok": False,
                    "skipped": True,
                    "error": None,
                    "payload": None,
                    "missing_capabilities": sorted(reqs - caps),
                }
            )
            skipped += 1
            continue
        r = run_completions_case(base_url, model, c, api_key=api_key)
        results.append({"id": c.id, "skipped": False, **r})
        if r["ok"]:
            passed += 1
    return {
        "summary": {
            "total": len(cases),
            "passed": passed,
            "failed": len(cases) - passed - skipped,
            "skipped": skipped,
        },
        "results": results,
    }
