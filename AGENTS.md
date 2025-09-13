# Repository Guidelines

This repo hosts the ST (system tests) and CI suite for vLLM: start service (local or Kubernetes in hybrid/PD-separated modes), run functional tests, performance benchmarks, and accuracy checks, then push daily metrics to Prometheus Pushgateway for Grafana.

## Project Structure & Organization
- `src/vllm_cibench/` orchestrators, deploy runners (local/k8s), testers (functional/perf/accuracy), metrics/publishers.
- `configs/deploy/` service configs per scenario (local, k8s-hybrid, k8s-pd).
- `configs/tests/` functional suites (chat, completions) and perf/accuracy knobs.
- `configs/scenarios/` high-level scenario files enabling features（guided decoding、function call、单卡/多卡等）。
- `configs/matrix.yaml` map scenarios → test subsets（默认 all）。
- `tools/` `acs_bench_mock.py`、`metrics_rename.py`、`gen_*_yaml` helpers。
- `tests/` mirrors `src/` with markers: `functional`, `perf`, `accuracy`, `integration`, `slow`。
- `scripts/` `start_local.sh`、`deploy_k8s.sh`、`collect_and_push.sh`。

## Build, Test, Develop
- venv: `python3 -m venv .venv && source .venv/bin/activate`
- install: `pip install -r requirements-dev.txt`
- unit/system tests: `pytest -q -m "not slow"`
- plan single scenario: `python -m vllm_cibench.run plan --scenario local_single_qwen3-32b_guided_w8a8 --run-type pr`
- run single scenario (dry): `python -m vllm_cibench.run run --scenario local_single_qwen3-32b_guided_w8a8 --run-type pr --dry-run`
- run matrix: `python -m vllm_cibench.run run-matrix --run-type pr --dry-run`
- metrics push occurs only when `run_type=daily` and `PROM_PUSHGATEWAY_URL` is set; use `--dry-run` to skip push during local debug or CI reproduction
- k8s deploy: `kubectl apply -f configs/deploy/infer_vllm_kubeinfer.yaml`; probe: `curl http://$IP:9000/v1/chat/completions`

## Style & Naming
- Python 3.10+; `black`, `ruff`, `mypy` on `src/`。
- 4-space indent; `snake_case`/`PascalCase`/`UPPER_SNAKE`。
- 每个函数必须包含中文注释/Docstring，说明参数、返回值与副作用。

## Testing Guidelines（TDD）
- 先写测试（≥85% 覆盖率）。
- Functional：仅用 OpenAI 兼容的 chat/completions，覆盖 vLLM 支持参数与边界值。
- Performance：使用 `tools/acs_bench_mock.py` 生成必需表头的 CSV，随后用 `metrics_rename.py` 转为 Prometheus 规范指标名。
- Accuracy：默认 Simple-evals 的 GPQA；数据集与工具可在配置中切换。

## Metrics, Prometheus, Grafana
- 仅每日跑的数据推送到 Pushgateway（PR 跑不推送）；设置 `PROM_PUSHGATEWAY_URL`。
- Grafana：对比 today/−1d/−7d，按模型与量化维度分面；功能性结果以表格展示（通过=绿色，失败=红色）。

## Commits & PRs
- Conventional Commits：`feat|fix|perf|test|docs|chore`。
- PR 必须包含：场景与变更的配置、复现实验命令、（如涉性能）前后对比摘要；CI 变绿后方可合入。

### PR 提交与可见性校验（强制要求）
- 提交 PR 后，必须当场校验 GitHub 上是否真实存在，并记录链接：
  - 使用命令确认：`gh pr view <number> --json url,state` 或 `gh pr list --state open`；
  - 在交互中回贴 PR 链接，且在对应 Issue 中新增一条评论包含 PR 链接（便于稽核）。
- 若仓库有自动合并或机器人操作导致 PR 立即合并，请立刻在沟通中标注“已合并”并贴链接；如需继续提交，请新开分支与 PR，并再次完成上述校验与回贴。
- 如需避免过早合并，应将 PR 设为 Draft 或移除自动合并标签，待评审通过后再转为 Ready。
