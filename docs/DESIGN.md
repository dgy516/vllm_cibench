# 设计文档（vLLM CI Bench / ST 套件）

## 背景与目标
- 目标：构建 vLLM 的系统测试（ST）与 CI 基准套件，覆盖启动→功能→性能→精度→（每日）指标推送→Grafana 展示的完整流程。
- PR 与每日：
  - PR 执行全流程但不向 Pushgateway 推送；需要保留 CSV/日志为构建产物。
  - 每日运行全量矩阵并推送指标，用于仪表盘对比。
- 失败策略：失败继续（不中断剩余阶段/场景），最终状态由“必需门”决定。

## 总体流程
1) 启动服务：本地或 K8s（混合、PD 分离）；健康检查 `/health`；超时≤20 分钟；场景结束后清理。
2) 功能测试：OpenAI 兼容接口（chat/completions），多轮与流式覆盖，参数/边界与能力探测。
3) 性能基准：mock acs-bench 真并发压测（默认流式、threading-pool、climb 模式），输出请求明细与汇总 CSV，统计 P75/P90/P95/P99/AVG/MAX。
4) 精度评测：Simple-evals（默认 GPQA），PR=debug 小样本；每日=全量。
5) 指标推送：仅每日将 Prom 规范指标推送至 Pushgateway（前缀可配置，空为无前缀）。
6) Grafana 展示：按模型/量化分面，对比今天/-1d/-7d；功能用例表格（绿=通过，红=失败）。

## 架构与模块
- ServiceLauncher：
  - 本地：读取场景配置启动 OpenAI 兼容服务；K8s：使用 NodePort 直连（不使用 port-forward）。
  - 健康检查：`/health`；重试与指数退避；最大等待 20 分钟。
  - 清理：每个场景结束后停止/删除（K8s 使用 `kubectl delete -f`）。
- ConfigLoader / ScenarioRegistry：
  - 读取 `configs/scenarios/*.yaml`、`configs/tests/*`、`configs/matrix.yaml`、`configs/providers.yaml`。
  - 量化 `quant ∈ {w8a8, w4a8, none}`；本仓库测试用例中如需 env 注入通过配置 `env` 字段。
  - YAML 生成脚本不内置，测试使用 mock；用户预先提供部署 YAML（如 `infer_vllm_kubeinfer.yaml`）。
- FunctionalRunner：
  - 覆盖 `/v1/chat/completions` 与 `/v1/completions`，非流式与流式；多轮对话覆盖。
  - 参数覆盖：`max_tokens, temperature, top_p, top_k, stop, presence_penalty, frequency_penalty, seed, stream, chunk_size…`；不支持参数通过能力探测后跳过。
  - Guided Decoding：OpenAI `response_format`（json/json_schema）；Function Call：OpenAI tools/tool_choice；Reasoning：断言 `choices[0].message.reasoning_content`（可配置回退键）。
- PerfRunner（acs_bench_mock）：
  - 后端 `threading-pool` 真并发；默认流式；PR/每日均使用 climb 模式（`growth_rate` 等从配置读取）。
  - 输出：requests_* 明细与 summary_* 汇总 CSV；计算吞吐、TTFT/TPOT/E2E 的 P75/90/95/99/AVG/MAX、QPS、失败率等。
- AccuracyRunner（simple-evals）：
  - 默认 GPQA；PR 用 debug 小样本；每日全量；解析 JSON 得分。
- MetricsConverter & PushgatewayClient：
  - CSV→Prom：单位统一为秒；分位数用 `{quantile=\"0.75|0.9|0.95|0.99\"}`；前缀 `metric_prefix` 可为空。
  - 标签：`model, quant, scenario, run_type, commit, branch, run_id, backend, dataset, input_len, output_len, concurrency, control_method, growth_rate`。

## 配置与矩阵
- 目录：
  - `configs/scenarios/`：场景（本地/k8s-hybrid/k8s-pd）、模型、served_model_name、量化、特性开关、K8s service_name/node_port/namespace、PD 三角色参数等。
  - `configs/tests/functional/`：按套件拆分（chat_core/completions_core/params_boundary/function_call/guided/reasoning…）。
  - `configs/tests/perf/profiles/`：PR 与每日档（并发/长度/epochs/warmup/num_requests/控制模式）。
  - `configs/tests/accuracy/`：PR=debug、每日=全量；默认 `simple-evals+gpqa`。
  - `configs/matrix.yaml`：按场景与 `run_type ∈ {pr,daily}` 指定各阶段是否启用与功能用例子集（默认 all）。
  - `configs/providers.yaml`：兼容 acs-bench 格式 `id,name,api_key,base_url,model_name,…`。

## 指标与推送（Prometheus）
- 前缀：`metric_prefix` 可配置，空表示不加前缀。
- 性能：
  - 吞吐：`*_total_token_throughput_tokens_per_second`、`*_output_token_throughput_tokens_per_second`、`*_requests_per_second`。
  - TTFT/TPOT/E2E：`*_seconds{quantile=\"0.75|0.9|0.95|0.99\"}`、`*_avg_seconds`、`*_max_seconds`；首二 token 间隔同上并含 `min`。
  - 失败：`*_failure_ratio`、高失败率 `*_high_failure_ratio`（>20%）。
  - 服务器侧：如可解析，使用 `*_server_*`。
- 功能：
  - 汇总：`functional_pass_ratio`、`functional_cases_total`、`functional_cases_failed`（按 `suite` 标签）。
  - 单用例：每日推送 `functional_case_pass{suite,case_id}=0|1`。
- 精度：
  - 总分：`accuracy_score{dataset=…}`；可选 `accuracy_subscore{section=…}`。
- Pushgateway：仅每日推送；`job=vllm_cibench`、`instance=<hostname>`。

## Grafana 展示
- Dashboard：vLLM CI Bench（仅 run_type=daily），时间范围最近 7 天；变量：`model, quant, scenario, dataset, concurrency, input_len, output_len, backend, quantile, metric_prefix`。
- 对比：同面板 0d/-1d/-7d 时移曲线。
- 面板：TTFT/E2E/吞吐/QPS 折线；精度曲线；功能性用例表（值 1=绿，0=红）。
- 阈值配色：默认不内置阈值（可后续按需加入）。

## CI 与门禁
- 触发：PR（默认本地场景；矩阵可指定 K8s）与每日（K8s 全量）。
- 阶段：lint → typecheck → unit → functional → perf → accuracy → 汇总产物；失败继续。
- 必需门（PR 必需为绿）：
  - Lint/Type/Unit/Functional 必须通过；Accuracy 低于阈值失败。
  - Performance 与基线（最近一次 daily，同场景/组合）对比：TTFT/E2E P99 回归>10% 失败；QPS 下降>5% 失败；Fail Rate >5% 失败。每日仅告警。
- 定时：每日 Asia/Shanghai；UTC 00:00 运行。产物保留：PR 14 天、每日 30 天。

## 需求对齐纪要（讨论过程）
- 高层流程：顺序如上；PR 产物保留；失败继续。
- 启动部署：
  - YAML 由用户预先提供，测试使用 mock；K8s 使用 NodePort；`/health` 健康检查；本地端口与 base_url 由场景配置；等待 20 分钟；每场景结束清理；日志归档。
- 配置与矩阵：
  - 采用 `configs/…` 目录；`configs/matrix.yaml` 映射场景→用例子集（默认 all）；量化仅 W8A8 与 W4A8（以及 none）。
- 功能性测试：
  - 覆盖 chat/completions、非流式/流式、多轮；参数与边界覆盖；不支持参数跳过；Guided Decoding 用 OpenAI `response_format`（含 `json_schema`）；Function Call 用 OpenAI tools；Reasoning 需要单独断言。
- 性能测试（mock acs-bench）：
  - 真并发、默认流式、threading-pool、climb 模式；数据为随机文本（中英混合）；固定 seed；保留 requests/summary CSV；计算 P75/90/95/99/AVG/MAX；包含 P99；`TPxx`=Pxx；服务器侧指标不可得时置 -1；仅每日推送，PR 保留产物。
- 精度测试（Simple-evals）：
  - 默认 GPQA；PR 用 debug；每日全量；超时建议单请求 300s；Prom 仅每日推送 `accuracy_score`。
- Prom & 指标：
  - 前缀可配置（空为无前缀）；统一标签如上；仅每日推送；功能性每日推送单用例指标。
- Grafana：
  - Dashboard 变量包含 `metric_prefix/quantile`；today/-1d/-7d 对比；功能表格绿/红；阈值配色默认不启用。
- CI：
  - PR Runner 默认 local，矩阵可指定 K8s；每日 K8s；Performance 纳入 PR 必需门并设置回归阈值；每日 Asia/Shanghai，UTC 00:00。

