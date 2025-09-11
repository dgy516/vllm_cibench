# 需求规格说明书（vLLM CI Bench / ST 套件）

本文档系统化记录本项目的需求、参考资料与双方确认的决策，供后续设计、开发与变更管理使用。

## 1. 范围与目标
- 目标：构建面向 vLLM 的系统测试（ST）与持续集成（CI）套件，覆盖以下完整流程：
  1) 启动 vLLM 服务（本地或 K8s，混合/PD 分离）
  2) 执行功能性测试（OpenAI 接口）
  3) 执行性能 Benchmark（PR 与每日分档）
  4) 执行精度 Benchmark（PR 与每日分档）
  5) 将每日数据推送到 Prometheus Pushgateway
  6) 在 Grafana 展示每日的性能、精度与功能性结果
- PR 流水线：执行全流程但不推送指标；需保留 CSV/日志等产物。
- 失败策略：失败继续（不中断后续阶段与其他场景）。

## 2. 启动与部署要求
- 启动方式：
  - 本地启动：通过配置参数启动 OpenAI 兼容服务（参考 vLLM 文档：https://docs.vllm.ai/en/v0.9.0/serving/openai_compatible_server.html）。
  - K8s 启动：支持混合部署与 PD 分离部署，访问方式为 NodePort；健康检查路径统一为 `/health`；最大启动等待 20 分钟；每个测试场景完成后必须清理资源与日志归档。
- YAML 生成与集成：部署 YAML 由用户预先提供（测试中使用 mock 方式），本仓库不内置生成脚本。
- K8s 上下文：默认 namespace `default`，支持在配置中指定 `kubeconfig/context/namespace`。
- 端口与基础 URL：
  - K8s：通过 `service_name(+port_name=http)` 解析 NodePort，若缺失则使用配置中的 `node_port`；以 `http://<NodeIP>:<NodePort>/v1` 访问。
  - 本地：由场景配置提供 `base_url`（如 `http://127.0.0.1:9000/v1`）。
- 参考命令（混合部署 YAML 生成，仅作为参考，不由本仓库执行）：
  - 单机场景（Qwen3-32B, Snt9b23, 副本数2）：
    ```bash
    python3 gen_single_role_deploy_kubeinfer_yaml.py \
        --replicas=2 \
        --image-name="ascend_vllm:latest" \
        --resource-cpu="22" \
        --resource-mem="120Gi" \
        --resource-npu="2" \
        --mount-path=/mnt/deepseek \
        --script-path=/mnt/deepseek/deploy \
        --parameters="--extra-env-vars='DISABLE_QWEN_DP_PROJ=1,ENABLE_QWEN_HYPERDRIVE_OPT=1,ENABLE_QWEN_MICROBATCH=1,VLLM_ALLOW_LONG_MAX_MODEL_LEN=1' \
                      --model=/mnt/deepseek/model/qwen3-32b \
                      --served-model-name=qwen3-32b \
                      --max-model-len=65536 \
                      --max-num-seqs=120 \
                      --tensor-parallel-size=2 \
                      --gpu-memory-utilization=0.95 \
                      --no-enable-prefix-caching \
                      --additional-config='{\"ascend_turbo_graph_config\": {\"enabled\": true}, \"ascend_scheduler_config\": {\"enabled\": true}}'"
    ```
  - 多机场景（Qwen3-235B-A22B, Snt9b, role-size=2, 16卡）：
    ```bash
    python3 gen_single_role_deploy_kubeinfer_yaml.py \
        --replicas=2 \
        --role-size=2 \
        --image-name="ascend_vllm:latest" \
        --resource-cpu="175" \
        --resource-mem="700Gi" \
        --resource-npu="8" \
        --mount-path=/mnt/deepseek \
        --script-path=/mnt/deepseek/deploy \
        --parameters="--extra-env-vars='VLLM_ALLOW_LONG_MAX_MODEL_LEN=1' \
                      --model=/mnt/deepseek/model/qwen3-235b-a22b \
                      --served-model-name=qwen3-235b-a22b \
                      --max-model-len=65536 \
                      --max-num-seqs=120 \
                      --tensor-parallel-size=16 \
                      --gpu-memory-utilization=0.95 \
                      --no-enable-prefix-caching \
                      --additional-config='{\"ascend_turbo_graph_config\": {\"enabled\": true}, \"ascend_scheduler_config\": {\"enabled\": true}}'"
    ```
  - 部署与查询：
    ```bash
    kubectl apply -f infer_vllm_kubeinfer.yaml
    kubectl get po | grep infer
    kubectl get svc
    ```
  - API 测试：
    ```bash
    curl -ik -H 'Content-Type: application/json' \
      -d '{"messages":[{"role":"user","content":"hello"}],"model":"qwen","temperature":0.6,"max_tokens":1024}' \
      -X POST http://${CLUSTER-IP}:9000/v1/chat/completions
    ```
- 参考命令（PD 分离部署 YAML 生成，仅参考）：
  - Snt9b23（2P1D, DeepSeek-R1, 副本数2）：
    ```bash
    python3 gen_pd_deploy_kubeinfer_yaml.py \
        --num-roles=3 \
        --replicas=2 \
        --image-name="ascend_vllm:A3.6" \
        --mount-path=/data \
        --script-path=/data/deploy \
        --common-params="--tmpfs-path=/data/tmpfs_model/deepseek-r1 \
                         --enable-fusion-spec=1 \
                         --vllm-log-path=/data/vllm_log \
                         --extra-env-vars='LLM_WAITING_OUT=3600,DEFAULT_MAX_TOKENS=32768' \
                         --model=/data/model/deepseek-r1 \
                         --served-model-name=deepseek-r1 \
                         --max-model-len=65536 \
                         --gpu-memory-utilization=0.91 \
                         --num-scheduler-steps=1 \
                         --multi-step-stream-outputs=true \
                         --disable-async-output-proc" \
        --scheduler-params="--max-num-seqs=256 --enable-reasoning --reasoning-parser=deepseek_r1" \
        --prefill-params="--max-num-seqs=24 --tokenizer-pool-size=8 --enforce-eager --enable-prefix-caching" \
        --decode-params="--max-num-seqs=24 --preemption-mode=swap --swap-space=16"
    ```
  - Snt9b（2P1D, DeepSeek-R1, 副本数2）：
    ```bash
    python3 gen_pd_deploy_kubeinfer_yaml.py \
        --device-type=A2 \
        --num-roles=3 \
        --replicas=2 \
        --image-name="ascend_vllm:A3.6" \
        --mount-path=/data \
        --script-path=/data/deploy \
        --common-params="--tmpfs-path=/data/tmpfs_model/deepseek-r1 \
                         --enable-fusion-spec=1 \
                         --vllm-log-path=/data/vllm_log \
                         --extra-env-vars='LLM_WAITING_OUT=3600,DEFAULT_MAX_TOKENS=32768' \
                         --model=/data/model/deepseek-r1 \
                         --served-model-name=deepseek-r1 \
                         --max-model-len=65536 \
                         --gpu-memory-utilization=0.95 \
                         --num-scheduler-steps=1 \
                         --multi-step-stream-outputs=true \
                         --disable-async-output-proc" \
        --scheduler-params="--max-num-seqs=4 --enable-reasoning --reasoning-parser=deepseek_r1" \
        --prefill-params="--max-num-seqs=8 --num_gpu_blocks_override=512 --enforce-eager --enable-prefix-caching" \
        --decode-params="--max-num-seqs=16 --num_gpu_blocks_override=2200 --preemption-mode=swap --swap-space=24"
    ```
  - 部署/查询/测试 API：与混合部署一致，模型名称改为 `deepseek-r1`。

## 3. 配置与场景矩阵
- 目录建议：
  - `configs/scenarios/`：场景定义（mode: local|k8s-hybrid|k8s-pd；model；served_model_name；quant: w8a8|w4a8|none；features: guided_decoding/function_call…；k8s: service_name/node_port/namespace；PD: scheduler/prefill/decode 参数）。
  - `configs/tests/functional/`：按套件定义参数与边界集合（chat_core、completions_core、params_boundary、function_call、guided、reasoning…）。
  - `configs/tests/perf/profiles/`：`pr.yaml`、`daily.yaml`（并发、input/output 长度、epochs、warmup、num_requests、control_method=climb）。
  - `configs/tests/accuracy/`：Simple-evals 的 `pr.yaml`（debug）与 `daily.yaml`（全量）。
  - `configs/matrix.yaml`：场景 → {pr,daily} → 各阶段开关与功能用例子集（默认 all）。
  - `configs/providers.yaml`：兼容 acs-bench 格式 `id,name,api_key,base_url,model_name,model_category`。
- 默认行为：未在矩阵中指定子集时，运行该场景的全部功能用例 + 对应 PR/每日的性能与精度配置。
- 首批场景清单：待补充（命名建议：`local_single_qwen3-32b_guided_w8a8`、`k8s_hybrid_qwen3-32b_tp2_w4a8`、`k8s_pd_deepseek-r1_2p1d_reasoning_w8a8` 等）。

## 4. 功能性测试要求（OpenAI 接口）
- 接口范围：覆盖 `/v1/chat/completions` 与 `/v1/completions`，非流式与流式均覆盖；需要多轮对话用例（含 `system/assistant` 历史）。
- 参数覆盖（含边界）：
  - `max_tokens`: [1, 128, 16384]
  - `temperature`: [0.0, 0.6, 1.0]
  - `top_p`: [0.0, 0.1, 1.0]
  - `top_k`: [1, 50]（如不支持则能力探测后跳过）
  - `stop`: 单/多字符串、含 Unicode
  - `presence_penalty`/`frequency_penalty`: [-2.0, 0.0, 2.0]（不支持则跳过）
  - `seed`: 固定若干值验证可重复性（非流式）
  - `stream`: [false, true]（含 `chunk_size` 可配）
  - 其他：`logprobs`/`logit_bias`（不支持则跳过）
- Guided Decoding：采用 OpenAI `response_format` 字段：
  - JSON 模式示例：
    ```json
    {
      "messages": [{"role": "user", "content": "请返回一个含 name/age 的 JSON"}],
      "model": "<served-model-name>",
      "response_format": {"type": "json_object"},
      "temperature": 0.6,
      "max_tokens": 1024
    }
    ```
  - JSON Schema 模式：`{"type":"json_schema","json_schema":{...}}`（Schema 在测试配置中提供）。
- Function Call：采用 OpenAI `tools`/`tool_choice` 语义；覆盖 `auto/required/指定函数名` 三类选择；使用 1–2 个简单函数用于验证。
- Reasoning：需要断言推理轨迹字段（默认 `choices[0].message.reasoning_content`，可通过配置提供备选键名），允许为空与否由场景配置决定。
- 错误与边界：超出上下文、非法或冲突参数应返回 4xx；对“服务不支持”的参数，能力探测后跳过而非判失败。
- 稳定性与超时：带 `seed` 的非流式期望完全一致；流式允许小幅差异；单请求超时 120s，可重试 2 次；建议包含中英文混合样例。

## 5. 性能测试要求（mock acs-bench）
- 工具行为：mock 工具进行真实并发调用 OpenAI chat/completions 接口，采集时序与 token 统计并生成 CSV（非纯模拟）。
- 并发后端：默认 `threading-pool`（暂不要求 `processing-pool/pd_dynamic`）。
- 输入数据：内置随机文本（中英混合）生成指定 `input_length` 的 prompts；随机种子固定以保证可复现；默认采用流式请求。
- 默认参数档（可在配置中调整）：
  - PR 档：`concurrency=[1,2,4]`；`input_len=[128,2048]`；`output_len=[128,1024]`；`warmup=1`；`epochs=1`；`num_requests=concurrency×16`；`backend=openai-chat`；`control_method=climb`。
  - 每日档：`concurrency=[1,2,4,8,16]`；`input_len=[128,512,2048,4096]`；`output_len=[128,1024,4096]`；`warmup=2`；`epochs=3`；`num_requests=concurrency×32`；`control_method=climb`（`growth_rate=2, growth_interval_ms=5000, init_concurrency=1` 建议值）。
- providers.yaml：复用 acs-bench 结构：
  ```yaml
  providers:
    - id: 'ascend-vllm'
      name: 'ascend-vllm'
      api_key: 'EMPTY'
      base_url: 'http://服务端IP:端口/v1'
      model_name: 'Qwen3-32b'
      model_category: 'Qwen3-32b'
  ```
- CSV 输出（要求包含以下表头）：
  `Execution_Time,Input_Length,Output_Length,Concurrency,Total_Token_Throughput(tokens/s),Output_Token_Throughput(tokens/s),TP75_TTFT(s),TP90_TTFT(s),TP95_TTFT(s),TP99_TTFT(s),MAX_TTFT(s),AVG_TTFT(s),TP75_TPOT(s),TP90_TPOT(s),TP95_TPOT(s),TP99_TPOT(s),MAX_TPOT(s),AVG_TPOT(s),TP90_TPOT_SEC(s),TP95_TPOT_SEC(s),TP99_TPOT_SEC(s),MAX_TPOT_SEC(s),AVG_TPOT_SEC(s),TP90_TIME_BETWEEN_FIRST_AND_SECOND_TOKEN(s),TP95_TIME_BETWEEN_FIRST_AND_SECOND_TOKEN(s),TP99_TIME_BETWEEN_FIRST_AND_SECOND_TOKEN(s),MIN_TIME_BETWEEN_FIRST_AND_SECOND_TOKEN(s),MAX_TIME_BETWEEN_FIRST_AND_SECOND_TOKEN(s),AVG_TIME_BETWEEN_FIRST_AND_SECOND_TOKEN(s),TP75_E2E(s),TP90_E2E(s),TP95_E2E(s),TP99_E2E(s),MAX_E2E(s),AVG_E2E(s),Total_Time(s),QPS,Fail_Rate,Backend,Temperature,Top_K,Top_P,Control_Method,Growth_Rate,Rounds,Num_Prompts,Provider,TP90_COMPLETION_TOKENS,TP95_COMPLETION_TOKENS,TP99_COMPLETION_TOKENS,MIN_COMPLETION_TOKENS,AVG_COMPLETION_TOKENS,AVG_REASONING_TOKENS,AVG_CONTENT_TOKENS,AVG_PROMPT_TOKENS,TP75_SERVER_TTFT(ms),TP90_SERVER_TTFT(ms),TP95_SERVER_TTFT(ms),TP99_SERVER_TTFT(ms),MAX_SERVER_TTFT(ms),AVG_SERVER_TTFT(ms),TP75_SERVER_TPOT(ms),TP90_SERVER_TPOT(ms),TP95_SERVER_TPOT(ms),TP99_SERVER_TPOT(ms),MAX_SERVER_TPOT(ms),AVG_SERVER_TPOT(ms),TP75_SERVER_E2E(ms),TP90_SERVER_E2E(ms),TP95_SERVER_E2E(ms),TP99_SERVER_E2E(ms),MAX_SERVER_E2E(ms),AVG_SERVER_E2E(ms),TP90_SPEC_ACCEPT_RATE,TP95_SPEC_ACCEPT_RATE,TP99_SPEC_ACCEPT_RATE,MIN_SPEC_ACCEPT_RATE,MAX_SPEC_ACCEPT_RATE,AVG_SPEC_ACCEPT_RATE`
- 指标定义：
  - Throughput：
    - Total_Token_Throughput = Σ(prompt_tokens+completion_tokens) / wall_time
    - Output_Token_Throughput = Σ(completion_tokens) / wall_time
  - TTFT：请求开始到首个 token 到达（流式优先）。
  - TPOT：相邻输出 token 的时间间隔分布；`TPxx_TPOT_SEC(s)` 中 `TPxx` 取 Pxx（如 TP99=P99）。
  - E2E：请求开始到响应完成。
  - QPS：已完成请求数 / wall_time；Fail_Rate：失败请求占比。
  - 服务器侧 TP*_SERVER_* 与 SPEC_ACCEPT_RATE：若不可采集则填 -1。
- Prom 转换：字段名转为 Prometheus 规范（小写+下划线+单位后缀），时间统一为秒，分位数字段输出为 `{quantile="0.75|0.9|0.95|0.99"}` 标签。
- PR 性能门禁（相对最近一次 daily 基线，同场景/组合）：
  - TTFT/E2E P99 回归 >10% 失败；QPS 下降 >5% 失败；Fail Rate >5% 失败。

> 参考工具 acs-bench（供环境具备时采用）：安装与使用、providers.yaml、数据集生成、`prof` 压测与爬坡模式的详细参数与产物规则均以提供的参考说明为准。

## 6. 精度测试要求
- 工具选型：首期使用 Simple-evals 进行在线评测（默认数据集 GPQA），后续在配置中保留 OpenCompass/MME 的扩展位。
- Simple-evals：
  - 环境：
    ```bash
    conda create -n accuracy --clone python-3.11.10
    conda activate accuracy
    cd xxx/simple_evals
    bash build.sh
    ```
  - 运行：
    - Debug（PR）：
      ```bash
      python simple_evals.py --model $model --dataset gpqa \
        --served-model-name $served_model_name \
        --url http://localhost:$port/v1 \
        --max-tokens 128 --temperature 0.6 --num-threads 32 --debug
      ```
    - 全量（每日）：
      ```bash
      python simple_evals.py --model $model --dataset gpqa \
        --served-model-name $served_model_name \
        --url http://localhost:$port/v1 \
        --max-tokens 16384 --temperature 0.6 --num-threads 32
      ```
  - 参数：`model`、`dataset(mmlu|gpqa|mgsm|drop|humaneval)`、`served_model_name`、`url(…/v1)`、`max-tokens`、`temperature`、`num-threads`、`debug`。
  - 结果：在 results/ 下输出 `{dataset}_{model}_{ts}.json/html`，JSON 记录分数。
- OpenCompass（备用）：
  - 环境：
    ```bash
    conda create --name opencompass python=3.10 -y
    conda activate opencompass
    git clone https://github.com/open-compass/opencompass
    cd opencompass && pip install -e .
    wget https://github.com/open-compass/opencompass/releases/download/0.2.2.rc1/OpenCompassData-core-20240207.zip
    unzip OpenCompassData-core-20240207.zip -d data/
    ```
  - 列表查看：`python tools/list_configs.py [PATTERN…]`
  - 示例配置与运行：参考提供的 `examples/example.py`（OpenAI 类型、`openai_api_base` 指向服务地址）。
- MME（多模态备用）：提供数据集路径、脚本 `MME.sh`、必要环境变量（`MODEL_PATH/MME_PATH/MODEL_TYPE/OUTPUT_NAME/ASCEND_RT_VISIBLE_DEVICES` 等）。

## 7. 指标上传（Prometheus）与展示（Grafana）
- Pushgateway：通过配置指定 `PROM_PUSHGATEWAY_URL`；仅每日推送（PR 不推送）。
- 指标前缀：可配置；配置为空则不使用前缀。
- 统一标签：`model`(served-model-name), `quant`(w8a8|w4a8|none), `scenario`, `run_type`(pr|daily), `commit`, `branch`, `run_id`, `backend`, `dataset`, `input_len`, `output_len`, `concurrency`, `control_method`(climb), `growth_rate`。
- 单位：所有时间统一转换为秒（CSV 中 ms 字段先转秒）。
- 功能性指标：
  - 汇总：`functional_pass_ratio`、`functional_cases_total`、`functional_cases_failed`（按 `suite` 标签）。
  - 单用例：每日推送 `functional_case_pass{suite,case_id}=0|1`，供 Grafana 表格绿/红展示（PR 不推送）。
- Grafana 展示：
  - Dashboard 名称“vLLM CI Bench”，默认时间范围最近 7 天，仅展示 `run_type=daily`。
  - 变量：`model, quant, scenario, dataset, concurrency, input_len, output_len, backend, quantile(0.75/0.9/0.95/0.99), metric_prefix`。
  - 对比：使用 time shift 展示 Today / -1d / -7d 对比曲线。
  - 面板：性能（TTFT/E2E/吞吐/QPS）、精度（总分趋势）、功能（汇总 + 单用例表格，1=绿，0=红）。

## 8. CI 策略与运行
- 触发：
  - PR：目标分支 `main`；默认跑本地场景（如矩阵指定亦可运行 K8s 场景）。
  - 每日：`main` 分支，按 Asia/Shanghai 时区，每日 UTC 00:00 运行（定时任务）。
- 阶段顺序：`lint → typecheck → unit → functional → perf → accuracy → 汇总产物`；失败继续。
- 必需门（PR 必须为绿）：
  - Lint / Typecheck / Unit / Functional 必须通过；
  - Accuracy：低于阈值视为失败；
  - Performance：与最近一次 daily 基线对比，TTFT/E2E P99 回归>10% 失败、QPS 下降>5% 失败、Fail Rate >5% 失败。
- 产物与保留：归档 `artifacts/`（CSV/JSON/HTML/日志/命令快照）；PR 14 天、每日 30 天。
- 资源与超时：
  - 作业超时：PR 60 分钟、每日 6 小时（可配）
  - 单阶段：functional 30 分钟、perf 60 分钟、accuracy 90 分钟（每日可放宽）
- 日志脱敏：屏蔽 URL/API Key/Token 等敏感信息。

## 9. 量化与模型
- 量化类型：`W8A8`、`W4A8`（以及 `none`）。
- 模型标识：使用 `served_model_name` 作为指标与展示的主标识；可保留 `model_raw` 以存储内部名称。

## 10. 开发原则与质量
- 开发模式：严格 TDD，先写测试再开发；所有测试通过后提交到本地，再以 PR 形式提交到远端 GitHub；GitHub CI 变绿后方可合入。
- 注释与可维护性：代码须具备详细中文注释（每个函数必须有注释/Docstring），模块化设计，便于扩展与维护。
- 工具链与质量门槛：Python 3.11（兼容 3.10）；`pytest/black/ruff/mypy(strict)`；覆盖率 ≥85%。

## 11. 讨论确认纪要（变更记录）
- 高层流程确认：流程顺序如 1 节；PR 产物保留；失败继续。
- 启动与部署：YAML 由用户预先提供并在测试中 mock；K8s 使用 NodePort；健康检查 `/health`；本地通过配置提供 base_url；等待 20 分钟；每场景结束清理；日志归档；失败继续的边界可配置，默认继续。
- 配置与场景矩阵：采用 `configs/…` 目录；`configs/matrix.yaml` 定义场景与用例子集；默认运行全部功能用例；量化为 W8A8/W4A8（以及 none）。
- 功能性测试：覆盖 chat/completions、非流式/流式、多轮；参数与边界覆盖；Guided Decoding 使用 OpenAI `response_format`；Function Call 使用 OpenAI tools；Reasoning 需要断言；其余如上。
- 性能测试：增加 P99；`TPxx_TPOT_SEC(s)` 中 TPxx 表示 Pxx；PR 与每日默认均使用 climb 模式；其余默认档位如 5 节；仅每日推送指标；PR 产物保留。
- 精度测试：使用 Simple-evals 测试 GPQA；PR 用 debug，小样本；每日全量；其他数据集可由配置指定。
- 指标上传：Pushgateway 通过配置指定地址；功能性通过情况也需上传（每日汇总与单用例）。
- Grafana 展示：按模型/量化对比，展示 Today/前一天/前 7 天；功能表格绿/红；变量含 `metric_prefix`，可为空。
- CI 与触发：Runner—PR 默认 local（矩阵可指定 K8s），每日 K8s；Performance 纳入 PR 必需门并设置回归阈值；每日任务 Asia/Shanghai，UTC 00:00；其余如 8 节。

---
本文档将随需求变更持续更新，并作为系统设计与实现的重要依据。

## 附录 A：acs-bench 参数参考（结构化）

本附录将参考内容整理为结构化参数表，便于查阅与对照。本仓库首期实现 mock 版（真实并发采集），参数命名与口径尽量对齐 acs-bench，具体以工具实际实现为准。

### A.1 数据集生成（generate dataset）

| 参数 | 长名 | 类型 | 必选 | 说明 |
|---|---|---|---|---|
| -dt | --dataset-type | String | 否 | 数据集来源类型，默认 random；可选 random、LongBench 等 |
| -i | --input-path | String | 否 | 用于筛选的数据集路径；random 模式下可省略 |
| -mt | --modal-type | String | 否 | 多模态类型，默认 text；可选 text、image-text |
| -cfg | --config-option | String | 否 | 多模态配置，形如 KEY:VALUE，可多次提供；常用 image_height、image_width |
| -o | --output-path | String | 是 | 输出目录，生成的数据集将保存于该目录下 |
| -il | --input-length | Int | 是 | 每个 prompt 的长度 |
| -pl | --prefix-length | Int | 否 | 公共前缀长度，仅在 random 模式生效，默认 0 |
| -n | --num-requests | Int | 是 | 生成的 prompt 个数 |
| -t | --tokenizer | String | 是 | tokenizer 路径（本地或 HF 模型路径） |
| -rv | --revision | String | 否 | HF 分支，默认 master |
| -ra | --range-ratio-above | Float | 否 | 长度上浮比例，默认 0.0，范围 [0,1] |
| -rb | --range-ratio-below | Float | 否 | 长度下潜比例，默认 0.0，范围 [0,1] |
| --seed | --random-seed | Int | 否 | 随机种子 |
| -trc | --trust-remote-code | Bool | 否 | 信任远端代码（HF 路径时生效），默认 False |

注意：`--input-length` 与 `--num-requests` 仅支持单值；需生成对应长度的数据集以匹配性能测试。

### A.2 性能测试（prof）Dataset Options

| 参数 | 长名 | 类型 | 必选 | 说明 |
|---|---|---|---|---|
| -dt | --dataset-type | String | 否 | 数据集类型，默认 custom |
| -cfg | --config-option | String | 否 | 多模态配置，KEY:VALUE，可多次 |
| -mt | --modal-type | String | 否 | 多模态类型，默认 text；可选 text、image-text |
| -i | --input-path | String | 是 | 已生成的数据集路径 |
| -il | --input-length | Int | 是 | 指定自定义数据集长度；可多组 |
| -n | --num-requests | Int | 是 | 请求个数；可多组，与并发组数相关 |
| -t | --tokenizer | String | 否 | tokenizer 路径（本地或 HF） |
| -rv | --revision | String | 否 | HF 分支，默认 master |
| --seed | --random-seed | Int | 否 | 随机种子 |
| -trc | --trust-remote-code | Bool | 否 | 信任远端代码（HF 路径时生效），默认 False |

### A.3 性能测试（prof）Concurrency Options

| 参数 | 长名 | 类型 | 必选 | 说明 |
|---|---|---|---|---|
| -c | --concurrency | Int | 否 | 最大并发，默认 1；可多组 |
| -nc | --num-process | Int | 否 | 进程数（processing-pool 专用），默认 [1]，须 ≤ min(concurrency, init_concurrency) |
| -r | --request-rate | Float | 否 | 到达速率，默认 INF（同时到达） |
| -rm | --request-mode | String | 否 | 请求模式：normal 或 pd_dynamic；pd_dynamic 仅支持 threading-pool/asyncio |
| -pc | --prefill-concurrency | Int | 否 | PD 分离场景 prefill 最大并发，默认等于 concurrency |
| -dc | --decoder-concurrency | Int | 否 | PD 分离场景 decode 最大并发，默认等于 concurrency |
| -burst | --burstiness | Float | 否 | 突发因子（request_rate≠inf 时生效），默认 1.0 |
| -cb | --concurrency-backend | Str | 否 | 并发后端：threading-pool（默认）/asyncio/processing-pool |
| -ub | --use-climb | Bool | 否 | 是否开启爬坡模式，默认 False |
| -gr | --growth-rate | Int | 否 | 每次爬坡的并发增量，默认 0 |
| -gi | --growth-interval | Float | 否 | 每次爬坡间隔（ms），默认 1000 |
| -ic | --init-concurrency | Int | 否 | 初始并发（爬坡模式），默认等于 concurrency；可多组 |
| -cm | --climb-mode | String | 否 | 爬坡策略：static（默认）或 linear |

### A.4 性能测试（prof）Metrics Options

| 参数 | 长名 | 类型 | 必选 | 说明 |
|---|---|---|---|---|
| -g | --goodput | String | 否 | 服务 SLO；示例 `-g ttft:50 -g e2e:1000`（单位 ms） |
| -bi | --bucket-interval | Float | 否 | 实时采样间隔（ms），用于动态统计 |

### A.5 性能测试（prof）Serving Options

| 参数 | 长名 | 类型 | 必选 | 说明 |
|---|---|---|---|---|
| -b | --backend | String | 否 | 接口类型：openai 或 openai-chat（默认） |
| -p | --provider | String | 是 | provider 配置文件路径 |
| -pid | --provider-id | String | 否 | 指定 provider id（多配置时） |
| -ol | --output-length | Int | 是 | 输出 token 长度；可多组 |
| -ra | --range-ratio-above | Float | 否 | 输出长度上浮比例，默认 0.0 |
| -rb | --range-ratio-below | Float | 否 | 输出长度下潜比例，默认 0.0（类型以工具实现为准） |
| -w | --warmup | Int | 否 | 预热请求数，默认 0 |
| -e | --epochs | Int | 否 | 每组并发的重复次数，默认 1 |
| -tk | --top-k | Int | 否 | Top-k 采样，默认 8（仅 openai 接口类型生效） |
| -tp | --top-p | Float | 否 | Top-p 采样，默认 1.0（仅 openai 接口类型生效） |
| -temper | --temperature | Float | 否 | Temperature，默认 0.6 |
| -cs | --chunk-size | Int | 否 | 流式 chunk 大小，默认 1024 |
| -usd | --use-spec-decode | Bool | 否 | 是否开启投机推理，默认 False |
| -nst | --num-spec-tokens | Int | 否 | 投机推理 token 数，默认 -1 |
| -umar | --use-mtp-accept-rate | Bool | 否 | 计算接受率时是否忽略模型自生 token，默认 True |
| -nss | --num-scheduler-steps | Int | 否 | multi-step 大小，默认 1 |
| -timeout | --timeout | Float | 否 | 请求超时时间（s），默认 1000 |
| -ie | --ignore-eos | Bool | 否 | 是否忽略 EOS，默认 True |
| -cus | --continuous-usage-stats | Bool | 否 | 流式返回是否包含 usage 信息，默认 True |
| -pf | --profile | Bool | 否 | 采集服务端 Service Profiler，默认 False（warmup 不采集） |
| -pl | --profile-level | String | 否 | Service Profiler 级别，默认 Level0 |
| -trace | --trace | Bool | 否 | 是否开启并发过程跟踪，默认 False |
| -s | --benchmark-save-path | String | 否 | 产物保存目录，默认 ./benchmark_output |

提示：`--concurrency/--init-concurrency/--num-requests/--input-length/--output-length/--config-option` 支持以英文逗号分隔（无空格）或重复指定多次；`--input-length` 必须与已生成的数据集长度匹配。

### A.6 产物说明（与 acs-bench 对齐）

- 请求详情：`requests_{provider}_{dataset_type}_{control_method}_concurrency{N}_{concurrency_backend}_input{L}_output{M}_{time}.csv`
- 汇总指标：`summary_{provider}_{control_method}_{concurrency_backend}_{time}.csv`

本仓库 mock 版将保留上述命名结构，另提供 Prom 友好格式与 Pushgateway 推送（仅每日）。
