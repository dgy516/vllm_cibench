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

方式二（修改仓库默认配置）：

```bash
# 将 configs/tests/functional.yaml 中的 suite 设为 true 并填入 cases/matrices/negative
python -m vllm_cibench.run run --scenario <sid> --run-type pr --dry-run
```

套件执行结果会附加到输出 JSON 的 `functional_report` 字段中，包含：

- `summary`: `{total, passed, failed}`
- `results`: `[ {id, ok, error, payload}, ... ]`

配置格式说明可参考 `configs/tests/functional_example.yaml` 中的 cases/matrices/negative 示例。

## 指标推送

性能阶段仅在 `run-type=daily` 且设置 `PROM_PUSHGATEWAY_URL` 时推送指标：

```bash
export PROM_PUSHGATEWAY_URL=http://pushgw:9091
python -m vllm_cibench.run run --scenario local_single_qwen3-32b_guided_w8a8 --run-type daily
```

使用 `--dry-run` 或未设置 `PROM_PUSHGATEWAY_URL` 时不会推送。

## 开发与调试

```bash
pytest -q -m "not slow"      # 运行单元/系统测试
ruff check src tests         # 代码风格检查
mypy src                     # 类型检查
```

本地端到端调试可使用 `--dry-run` 跳过推送。CI 中复现实验需与上述命令保持一致。
