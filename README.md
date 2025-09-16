# vLLM CI Bench

最小化的 vLLM CI 与 Benchmark 套件，提供场景编排、功能/性能测试与指标推送能力。

## 安装

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
```

## CLI 使用

### 计划 (plan)

```bash
python -m vllm_cibench.run plan --scenario local_single_qwen3-32b_guided_w8a8 --run-type pr
```

### 运行单场景 (run)

```bash
python -m vllm_cibench.run run --scenario local_single_qwen3-32b_guided_w8a8 --run-type pr --dry-run
```

- `--run-type`: `pr` 或 `daily`，决定功能/性能/精度阶段与指标推送。
- `--dry-run`: 强制跳过指标推送，便于本地调试。

### 批量运行矩阵 (run-matrix)

```bash
python -m vllm_cibench.run run-matrix --run-type pr --dry-run
```

读取 `configs/matrix.yaml` 中的场景并逐一执行。

### 启用功能性套件（针对 vLLM 服务）

默认仅运行冒烟（smoke）用例。要运行更全面的功能/边界用例，可启用功能性套件：

方式一（推荐，避免改库内文件）：

```bash
# 指向示例配置（或你自己的配置）
export VLLM_CIBENCH_FUNCTIONAL_CONFIG=$(pwd)/configs/tests/functional_example.yaml
python -m vllm_cibench.run run --scenario local_single_qwen3-32b_guided_w8a8 --run-type pr --dry-run
```

你也可以使用为不同模型准备的专用配置：

```bash
# Qwen3-32B 专用覆盖
export VLLM_CIBENCH_FUNCTIONAL_CONFIG=$(pwd)/configs/tests/functional_qwen3-32b.yaml
python -m vllm_cibench.run run --scenario local_single_qwen3-32b_guided_w8a8 --run-type pr --dry-run

# DeepSeek-R1 专用覆盖（如有对应场景）
export VLLM_CIBENCH_FUNCTIONAL_CONFIG=$(pwd)/configs/tests/functional_deepseek-r1.yaml
python -m vllm_cibench.run run --scenario k8s_pd_deepseek-r1_2p1d_reasoning_w8a8 --run-type pr --dry-run
```

方式二（修改仓库默认配置）：

```bash
# 将 configs/tests/functional.yaml 中的 suite 设为 true 并填入 cases/matrices/negative
python -m vllm_cibench.run run --scenario <sid> --run-type pr --dry-run
```

套件执行结果会附加到输出 JSON 的 `functional_report` 字段中，包含：

- `summary`: `{total, passed, failed}`
- `results`: `[ {id, ok, error, payload}, ... ]`

配置格式说明可参考 `configs/tests/functional_example.yaml` 中的 cases/matrices/negative 示例。

能力跳过（capability-aware skipping）：
- 在配置中通过 `capabilities: [...]` 声明服务已支持的能力，或设置环境变量：
  `export VLLM_CIBENCH_CAPABILITIES="chat.tools,chat.response_format.json_schema,completions.suffix"`
- 运行时，若某用例标注了 `required_capabilities` 而服务未声明该能力，且 `skip_if_unsupported=true`，
  则该用例被标记为 `skipped`，不会当作失败统计；报告 `summary` 含 `skipped` 字段。

### 独立运行功能性套件（不走编排）

若只需对接一个服务端点，可直接运行独立 CLI：

```bash
python -m vllm_cibench.run run-functional \
  --base-url http://127.0.0.1:9000/v1 \
  --model qwen3-32b \
  --config ./configs/tests/functional_qwen3-32b.yaml
```

输出仅包含功能性报告 `{chat, completions}`，不包含性能/推送等编排行为。

## 指标推送

性能阶段仅在 `run-type=daily` 且设置 `PROM_PUSHGATEWAY_URL` 时推送指标：

```bash
export PROM_PUSHGATEWAY_URL=http://pushgw:9091
python -m vllm_cibench.run run --scenario local_single_qwen3-32b_guided_w8a8 --run-type daily
```

使用 `--dry-run` 或未设置 `PROM_PUSHGATEWAY_URL` 时不会推送。

## 精度与阈值

编排会根据 `configs/tests/accuracy.yaml` 执行最小化精度评测（默认任务 `gpqa`），并在输出中附带：

- `accuracy`: `{task, score, correct, total, ok}`
- 通过 `min_score` 判定是否通过（`ok=true/false`）；`min_score=0` 表示不启用阈值。

可用环境变量覆盖精度配置路径，便于在 CI/本地动态调整：

```bash
export VLLM_CIBENCH_ACCURACY_CONFIG=$(pwd)/my_accuracy.yaml
python -m vllm_cibench.run run --scenario local_single_qwen3-32b_guided_w8a8 --run-type pr --dry-run
```

## 脚本

- 部署到 K8s：

  ```bash
  scripts/deploy_k8s.sh -f configs/deploy/infer_vllm_kubeinfer.yaml --wait 30
  ```

  该脚本封装最小化的 `kubectl apply`，并提供简单的等待提示；更复杂的就绪性/探活请使用编排 CLI。

- 从性能 CSV 聚合并推送指标：

  ```bash
  scripts/collect_and_push.sh \
    --csv ./artifacts/perf.csv \
    --run-type daily \
    --label model=Qwen3-32B --label quant=w8a8 --label scenario=local_single \
    --gateway-url http://pushgw:9091
  ```

  注意：仅 `run-type=daily` 且已设置 `PROM_PUSHGATEWAY_URL`（或传入 `--gateway-url`）时会推送；在 fork 或非主仓库会自动跳过推送。

### K8s 场景清理（可选）

- 在编排结束后，如果提供了删除 YAML，将尝试 `kubectl delete -f` 清理资源：

  - 场景内配置：`raw.k8s_delete_yaml: ./configs/deploy/infer_vllm_kubeinfer.yaml`
  - 或环境变量：`export VLLM_CIBENCH_K8S_DELETE_YAML=$(pwd)/configs/deploy/infer_vllm_kubeinfer.yaml`

- 命名空间取自场景 `raw.k8s.namespace`，删除失败会被忽略（不影响主流程）。

## 开发与调试

```bash
pytest -q -m "not slow"      # 运行单元/系统测试
ruff check src tests         # 代码风格检查
mypy src                     # 类型检查
```

本地端到端调试可使用 `--dry-run` 跳过推送。CI 中复现实验需与上述命令保持一致。

### 贡献与分支策略

- 禁止直接 push 到 `main` 分支，必须通过 Pull Request 合并。
- 安装预推送钩子（客户端防误推）：

  ```bash
  ln -sf ../../hooks/pre-push .git/hooks/pre-push
  ```

- 服务器侧有保护工作流：若检测到直接 push 到 `main`，工作流会失败作为稽核提示。
