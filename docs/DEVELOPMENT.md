# 开发文档（vLLM CI Bench / ST 套件）

## 环境与工具
- Python 3.11（兼容 3.10）；建议使用 venv：`python3 -m venv .venv && source .venv/bin/activate`
- 依赖工具：`pytest`、`black`、`ruff`、`mypy`（严格模式）；覆盖率 ≥85%
- 安全：不提交任何密钥；如需 Pushgateway，使用环境变量 `PROM_PUSHGATEWAY_URL`

### 代码风格与校验
- 推荐使用 `ruff`、`black` 在本地进行格式与静态检查（非强制）。
- CI 已包含 YAML 语法/风格检查与仓库结构检查；必要时可扩展更多校验。

### 保护分支与合并策略（严格禁止直推 main）
- main 为保护分支：禁止直接 push，必须新建分支→创建 PR→CI 全绿→合并。
- 请在仓库 Settings → Branches 新建规则（分支名 `main`）：
  - Require a pull request before merging（至少 1 名 Reviewer）
  - Require status checks to pass before merging（选择本仓库 CI 任务）
  - Require branches to be up to date before merging（建议开启）
  - Include administrators（建议开启，管理员也需走 PR）
  - Do not allow bypass: 关闭 Allow force pushes / Allow deletions
  - Restrict who can push to matching branches（可选：不配置任何直推主体）

## 目录结构（建议）
- `src/vllm_cibench/`：launcher、runners（functional/perf/accuracy）、metrics、config loader
- `configs/`：
  - `scenarios/`：场景（本地/k8s-hybrid/k8s-pd）与量化（w8a8/w4a8/none）、特性开关与 K8s 端点
  - `tests/functional/`：`chat_core`、`completions_core`、`params_boundary`、`function_call`、`guided`、`reasoning` 等
  - `tests/perf/profiles/`：`pr.yaml`、`daily.yaml`（并发/长度/epochs/warmup/num_requests/控制模式）
  - `tests/accuracy/`：`pr.yaml`（debug）、`daily.yaml`（全量）
  - `matrix.yaml`：按场景与 `run_type ∈ {pr,daily}` 指定启用阶段与功能子集
  - `providers.yaml`：`id,name,api_key,base_url,model_name,model_category`
- `artifacts/`：`logs/`、`perf/`、`accuracy/` 等构建产物
- `docs/`：本开发/设计/TODO 文档

## 运行方式（TDD 优先）
- 先写测试用例（单测/集成/系统），再实现代码；提交前确保全部通过并满足覆盖率
- 场景执行顺序：启动→功能→性能→精度→（每日）推送；失败继续，最后汇总
- PR：默认本地场景；产物保留，不推送指标；性能/精度为精简档（但性能纳入必需门，按基线比对）
- 每日：K8s 全量矩阵；推送指标并用于 Grafana 展示
- CLI：
  - `python -m vllm_cibench.run run --scenario <id> --run-type pr --timeout 60` 执行单场景编排，可自定义探活等待时长。
  - `python -m vllm_cibench.run run-matrix --run-type pr --timeout 60` 批量执行 `configs/matrix.yaml` 中的所有场景，同样支持自定义探活等待时长。

## 功能测试要点
- 覆盖 `/v1/chat/completions` 与 `/v1/completions`；非流式与流式均覆盖；多轮对话（含 `system/assistant` 历史）
- 参数与边界：`max_tokens, temperature, top_p, top_k, stop, presence_penalty, frequency_penalty, seed, stream, chunk_size…`
- Guided Decoding：OpenAI `response_format`（支持 `json` 与 `json_schema`）；Function Call：OpenAI `tools/tool_choice`
- Reasoning：断言 `choices[0].message.reasoning_content`（或配置回退键）；单请求超时 120s，可重试 2 次

## 性能测试要点（acs_bench_mock）
- 真并发压测，默认后端 `threading-pool`、默认流式、默认 climb 模式；固定 seed 确保可复现
- 输出 CSV：requests_* 明细与 summary_* 汇总；统计 P75/P90/P95/P99/AVG/MAX、QPS、失败率等
- PR 与每日参数档位在 `configs/tests/perf/profiles/` 配置；providers.yaml 提供 base_url 与模型名

## 精度测试要点（Simple-evals）
- 默认数据集 `gpqa`；PR 使用 debug，小样本快速校验；每日全量
- 参数默认：`max_tokens=16384, temperature=0.6, num_threads=32`；单请求超时建议 300s
- 产物：JSON 分数与 HTML 详情保存到 `artifacts/accuracy/{scenario_id}/{ts}/`

## 指标与推送
- CSV→Prom 转换：统一单位为秒；分位数 `{quantile=\"0.75|0.9|0.95|0.99\"}`；前缀 `metric_prefix` 可为空
- 标签：`model, quant, scenario, run_type, commit, branch, run_id, backend, dataset, input_len, output_len, concurrency, control_method, growth_rate`
- 仅每日推送到 Pushgateway；PR 不推送；功能性每日推送单用例（用于表格绿/红）

## CI 策略
- 阶段：lint → typecheck → unit → functional → perf → accuracy → 汇总；失败继续
- 必需门（PR）：Lint/Type/Unit/Functional 必须通过；Accuracy 低于阈值失败；Performance 与最近一次 daily 基线对比：TTFT/E2E P99 回归>10% 失败、QPS 下降>5% 失败、Fail Rate >5% 失败
- 计划任务：Asia/Shanghai；UTC 00:00 运行；产物保留期：PR 14 天、每日 30 天

提示：请依赖 GitHub 的 Branch protection 规则实现从源头阻断直推。本仓库不再提供额外的守卫 Action（Action 无法在 push 前阻断）。

## 注意事项
- K8s 访问使用 NodePort（`service_name(+port_name=http)` 优先解析；否则使用配置中的 `node_port`）
- YAML 生成脚本不内置，测试使用 mock；用户预先准备 `infer_vllm_kubeinfer.yaml`
- 所有函数需中文注释（参数/返回/副作用），模块化设计，避免隐藏全局状态
