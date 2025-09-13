---
name: "feat: Functional Coverage + Param Validation"
about: "Expand VLLM feature tests for chat/completions and add parameter validity tests"
title: "feat(functional,validation): expand coverage for chat/completions and add param validation"
labels: ["feat", "functional", "validation", "testing"]
assignees: []
---

## 背景
现有功能性测试覆盖了基础 chat、部分流式/工具/JSON schema 等，但仍有大量 VLLM 参数与场景未覆盖，且缺少系统性的参数合法性（类型/边界）测试。

## 目标
- 扩展功能测试：覆盖 chat/completions 端点的大部分常用/边界参数与组合场景。
- 新增参数合法性测试：对类型错误、越界取值的 4xx 响应及错误消息传播进行断言。
- 所有用例均使用 `requests-mock` 或 `monkeypatch`，不依赖真实网络。

## 详细需求
1) 客户端能力
   - 在 `src/vllm_cibench/clients/openai_client.py` 新增 `completions()` 方法，接口风格与 `chat_completions()` 一致，支持 `stream` 与 `logprobs/top_logprobs`（若 stream=false）。
   - 在 `src/vllm_cibench/testsuites/functional.py` 新增或重构公共调用函数：`run_basic_completion()`，以及共享断言工具。

2) Chat 端点覆盖（tests/testsuites/test_functional_chat_ext.py）
   - multi-turn 与 system 提示；`n` 多样本返回。
   - 流式（SSE）：chunk 结构、`[DONE]` 终止。
   - response_format：`json_object`、`json_schema`（含 schema 校验）。
   - Tools/Function call：`tool_choice=none/auto/required`、按函数名强制调用；并行多 `tool_calls`。
   - 采样与约束：`temperature/top_p/top_k` 极值；`stop`/`stop_token_ids`；`logit_bias`；`presence_penalty`、`frequency_penalty`；`seed`；`max_tokens`；（若支持）`use_beam_search`、`length_penalty`、`early_stopping`。

3) Completions 端点覆盖（tests/testsuites/test_functional_completions.py）
   - `prompt`/`suffix`/`echo`；`n` 多样本；`logprobs`/`top_logprobs`；`best_of`（若服务支持）。

4) 参数合法性（tests/testsuites/test_functional_params_negative.py）
   - 类型错误：布尔/字符串/列表互换导致的 400/422；
   - 越界值：`top_p<0或>1`、`temperature<0`、`top_k<0`、`n<=0`、`max_tokens<0`、penalty 超范围等；
   - 断言：客户端抛出 `requests.HTTPError` 或返回体包含错误消息，确保错误传播链条正确。

5) 配置与标记
   - 为新增用例添加 `@pytest.mark.functional` 标记；在 `pytest.ini` 注册（若尚未）。
   - （可选）`configs/tests/functional.yaml` 添加开关项，以便在编排中选择子集参数覆盖。

## 修改点（文件/代码）
- `src/vllm_cibench/clients/openai_client.py`：新增 `completions()`；
- `src/vllm_cibench/testsuites/functional.py`：新增 `run_basic_completion()` 与通用断言；
- `tests/testsuites/test_functional_chat_ext.py`、`test_functional_completions.py`、`test_functional_params_negative.py`（新增）；
- （可选）`configs/tests/functional.yaml`（新增）；`pytest.ini` 注册 markers。

## 测试用例（必须）
- 正常路径：chat/completions 各参数与典型组合；
- 负路径：参数类型/范围非法返回 4xx；
- 流式：SSE 分块解析与结束标志；
- `n`/多样本一致性、`logprobs` 结构完整性（当请求时）。

## 命令与验证
- `pytest -q -m "functional"`
- `pytest -q` 全量；CI 时长控制在可接受范围。

## 验收标准
- 新增功能性用例数 ≥20；整体覆盖率维持 ≥85%。
- 关键参数的非法输入路径被覆盖并断言错误传播行为。

## 参考实现要点（指导 Codex Cloud）
- 始终以 `requests-mock` 截获 HTTP，断言请求体参数与响应解析。
- 对 4xx 使用 `requests_mock.post(..., status_code=400, json={"error":{...}})` 并 `resp.raise_for_status()` 触发异常路径测试。
- 流式用 `content=` 伪造 `text/event-stream`，包含多条 `data:` 与最终 `[DONE]` 行。

