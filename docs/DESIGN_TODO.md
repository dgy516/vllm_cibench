# 设计指导书 TODO（vLLM CI Bench 后续工作）

本文件列出当前仓库尚未覆盖或需要完善的功能，并拆分为可独立提交的 PR/Issue。每一项包含范围、验收标准、修改点、测试与验证命令，便于 Codex Cloud 或贡献者直接跟进实现。

## 里程碑 M1：打通 Accuracy 流程（GPQA as default）

- 范围
  - 新增 `accuracy` 执行器：默认集成 Simple-Evals 的 GPQA（可配置），以 OpenAI 兼容 REST 调用待测服务，统计分数与失败样本。
  - 在 `run_pipeline.execute` 中串联 `accuracy` 阶段：当 `matrix.yaml` 对应场景 `accuracy: true` 时执行。
  - 结果汇总到 `run`/`run-matrix` 的 JSON 输出中（字段示例：`{"accuracy": {"task": "gpqa", "score": 0.52}}`）。
- 修改点
  - `src/vllm_cibench/testsuites/accuracy.py`（新文件）：实现 `run_accuracy(base_url, model, cfg)` 最小版本（允许 mock/子集评测）。
  - `src/vllm_cibench/orchestrators/run_pipeline.py`：在 perf 后追加 accuracy；`result["accuracy"]` 字段落盘。
  - `configs/tests/accuracy.yaml`（新文件）：默认任务 GPQA，允许切换数据集与 provider。
  - `README.md`：补充 accuracy 相关说明与示例命令。
- 验收标准
  - 单元/系统测试覆盖率保持 ≥85%。
  - `python -m vllm_cibench.run run --scenario <任一场景> --run-type pr --dry-run` 输出包含 `accuracy` 字段（在测试中可使用 mock）。
- 测试与验证
  - `pytest -q -m "not slow"`
  - `python -m vllm_cibench.run plan --scenario local_single_qwen3-32b_guided_w8a8 --run-type pr`
  - `python -m vllm_cibench.run run --scenario local_single_qwen3-32b_guided_w8a8 --run-type pr --dry-run`

## 里程碑 M2：完善配置与工具目录（configs/tests、configs/deploy、tools/）

- 范围
  - 新增 `configs/tests/`：拆分功能/性能/精度套件参数（例如 chat 输入模版、响应格式校验开关、perf 并发/长度矩阵、accuracy 数据集选择）。
  - 新增 `configs/deploy/`：提供 K8s 示例（`infer_vllm_kubeinfer.yaml`）与本地启动示意参数。
  - 新增 `tools/`：
    - `acs_bench_mock.py`：命令行输出带表头的 CSV（与 `testsuites/perf.py` 字段对齐）。
    - `metrics_rename.py`：读取 CSV/JSON，输出 Prometheus 规范键名（复用 `metrics/rename.py`）。
    - `gen_*_yaml`：生成场景/测试样例 YAML 的脚手架。
- 修改点
  - `README.md`：文档链接与使用示例。
- 验收标准
  - 本地可运行工具脚本并生成示例输出；对应最小单元测试覆盖基本 I/O。

## 里程碑 M3：脚本与测试标记（scripts/*、pytest markers）

- 范围
  - 新增 `scripts/deploy_k8s.sh`：对 `configs/deploy/*.yaml` 执行 `kubectl apply` 与简单探活提示。
  - 新增 `scripts/collect_and_push.sh`：从性能 CSV 聚合并调用 Python API 推送（保留 `--dry-run`），与 Pushgateway 条件一致。
  - 为现有测试添加 markers：`functional`、`perf`、`accuracy`、`integration`、`slow`；在 `pytest.ini` 注册。
- 验收标准
  - `pytest -m functional`、`pytest -m perf` 等子集可运行。
  - 脚本具备帮助信息与失败退出码。

## 里程碑 M4：类型与风格（mypy --strict、ruff）

- 范围
  - 修复 `mypy --strict src` 报告的问题（返回值/参数注解、移除无用 ignore）。
  - CI 中开启 `ruff check` 与 `mypy`（作为非阻断可先 WARNING，再逐步提升为必过）。
- 参考当前 mypy 报告（需修复示例）
  - `config.py`: `Unused "type: ignore"`、`no-any-return`。
  - `metrics/pushgateway.py`: `Unused "type: ignore"`。
  - `clients/*`: `Unused "type: ignore"`、`no-any-return`。
  - `deploy/local.py`: `Popen` 类型参数。
  - `deploy/k8s/kubernetes_client.py`: 缺少返回/参数注解。
  - `run.py`: `Unused "type: ignore"`。
- 验收标准
  - `mypy --strict src` 0 error（或在 PR1 降低为最小可用集）。

---

## 里程碑 M5：功能性覆盖与参数合法性验证（Functional + Param Validation）

- 范围
  - 扩展 OpenAI 兼容功能用例覆盖：chat/completions 端点更全面参数与组合场景。
  - 参数合法性验证：类型与取值边界（含负值、超上限、空/None、错误类型）。
  - 新增 `OpenAICompatClient.completions()`；新增 `run_basic_completion()`（或统一封装）。
  - 测试用例全部使用 `requests-mock`，不依赖真实网络；对非法参数以 mock 400/422 响应覆盖错误路径。

- 覆盖点建议（不局限于此）
  - Chat 端点：
    - 基本/多轮对话、`system` 提示、`n` 多样本。
    - 流式（SSE）chunk 结构与 `[DONE]` 终止。
    - `response_format`：`json_object`、`json_schema`（schema 验证）。
    - Tools/Function call：`tool_choice=none/auto/required`、按函数名指定、并行多 tool_calls。
    - Reasoning：`reasoning=True` 字段解析已覆盖，补充边界（无字段/空值）。
    - 采样与约束：`temperature/top_p/top_k` 极值、`stop`/`stop_token_ids`、`logit_bias`、`presence_penalty`、`frequency_penalty`、`seed`、`max_tokens`、`use_beam_search`、`length_penalty`、`early_stopping`（若服务支持）。
  - Completions 端点：
    - `prompt`/`suffix`/`echo`、`n`、`logprobs`/`top_logprobs`、`best_of`（若支持）。
  - 参数合法性（统一分组断言 400）：
    - 类型错误：字符串传布尔、列表传整型等。
    - 取值越界：`top_p<0或>1`、`temperature<0`、`top_k<0`、`n<=0`、`max_tokens<0`、penalty 超范围等。

- 修改点
  - `src/vllm_cibench/clients/openai_client.py`：新增 `completions()`。
  - `src/vllm_cibench/testsuites/functional.py`：新增/重构 `run_basic_completion()` 与公共断言。
  - `tests/testsuites/`：新增 `test_functional_completions.py`、`test_functional_params_negative.py` 等。
  -（可选）`configs/tests/functional.yaml`：开关与样例参数集。

- 验收标准
  - 新增用例数 ≥20，覆盖上述大部分维度；整体覆盖率保持 ≥85%。
  - 非法参数路径以 mock 400 响应覆盖（断言错误码/错误消息传播）。

- 测试与验证
    - `pytest -q -m "functional"`（添加 markers 后）。
    - `pytest -q` 全绿；CI 时长可控。

## 里程碑 M6：vLLM 功能性套件（src/testsuites）与编排接入

- 范围
  - 在 `src/vllm_cibench/testsuites/functional.py` 中实现面向 vLLM 服务的功能套件：
    - ChatCase/CompletionCase 数据模型；
    - `run_chat_case`/`run_completions_case` 单用例执行，支持 stream/tools/response_format 等参数与 expect_error 负路径；
    - `run_chat_suite`/`run_completions_suite` 批量执行并产出 `{summary, results}`；
    - `build_cases_from_config(data)` 从 YAML 构建用例（cases/matrices/negative），对边界矩阵仅取首尾值避免笛卡尔爆炸。
  - 在 `orchestrators/run_pipeline.execute` 中集成功能套件（保持 smoke 判定），
    当 `configs/tests/functional.yaml: suite=true` 或通过 `VLLM_CIBENCH_FUNCTIONAL_CONFIG` 指向自定义文件时，
    执行套件并在输出 JSON 的 `functional_report` 字段返回结果。
  - 清理 `tests/testsuites/` 下与本项目无关的功能场景测试样例，避免与面向 vLLM 的功能套件混淆。
- 验收
  - 默认不启用套件（suite=false），仅跑 smoke；启用后能在 `functional_report` 中看到 `{summary, results}`。
  - README 增加启用说明与 `functional_example.yaml` 示例文件。

## 里程碑 M7：功能性结果转指标（Prometheus，可选）

- 范围
  - 在 `run_pipeline.execute` 中将 `functional_report` 汇总为指标：
    - `ci_functional_total`、`ci_functional_passed`、`ci_functional_failed`、`ci_functional_pass_rate`。
  - 与性能指标相同：仅在 `run_type=daily` 且非 `--dry-run` 时推送；标签沿用 `{model, quant, scenario}`。
- 验收
  - 本地在 daily + 非 dry-run 且设置 `PROM_PUSHGATEWAY_URL` 时可观察到推送；PR 流程不推送。

## PR 切分建议（每 PR 控制粒度，可评审）

1) feat(accuracy): add accuracy runner and pipeline wiring
   - 仅新增 `testsuites/accuracy.py` 与 `run_pipeline` 串联、最小配置与测试。
2) feat(configs/tools): add configs/tests/*, configs/deploy/*, tools/*
   - 仅新增目录与工具脚本+对应单测，不改核心逻辑。
3) chore(scripts/markers): add scripts/* and pytest markers
   - 仅新增脚本与测试标记、pytest.ini 注册。
4) chore(types): fix mypy --strict issues and enable lint in CI
   - 仅类型与风格修复，CI 工作流补充检查环节。

## 验证与回归

- 核心命令
  - `python -m vllm_cibench.run plan --scenario <s> --run-type pr`
  - `python -m vllm_cibench.run run --scenario <s> --run-type pr --dry-run`
  - `python -m vllm_cibench.run run-matrix --run-type pr --dry-run`
- Pushgateway（仅 daily 且设置 URL）
  - `export PROM_PUSHGATEWAY_URL=http://pushgw:9091`
  - `python -m vllm_cibench.run run --scenario <s> --run-type daily`（或 `--dry-run`）
