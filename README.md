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

