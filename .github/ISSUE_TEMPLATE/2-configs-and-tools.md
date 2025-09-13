---
name: "feat: Configs (tests/deploy) & Tools"
about: "Add configs/tests, configs/deploy, and tools scripts (acs_bench_mock, metrics_rename, gen_*_yaml)"
title: "feat(configs,tools): add tests/deploy configs and CLI tools"
labels: ["feat", "config", "tools"]
assignees: []
---

## 背景
当前仓库使用内置最小实现，但未提供独立的 `configs/tests/`、`configs/deploy/` 与 `tools/` 目录与脚本，影响复用与可操作性。

## 目标
- 提供标准化的测试/部署配置目录与示例。
- 提供独立工具脚本：
  - `tools/acs_bench_mock.py` 生成性能 CSV（与 `testsuites/perf.py` 字段一致）。
  - `tools/metrics_rename.py` 将 CSV/JSON 字段名映射为 Prometheus 规范。
  - `tools/gen_*_yaml` 生成场景/测试 YAML 的脚手架。

## 详细需求
- 目录与文件
  - `configs/tests/functional.yaml`：chat/completions 参数覆盖开关（如 `response_format`/`tools`）。
  - `configs/tests/perf.yaml`：并发/输入/输出长度矩阵与运行轮次。
  - `configs/tests/accuracy.yaml`：与 Accuracy Issue 同步（默认 GPQA）。
  - `configs/deploy/infer_vllm_kubeinfer.yaml`：K8s Service/Deployment 示例。
- 工具脚本（Python CLI）
  - `tools/acs_bench_mock.py`: `--concurrency 1,2 --input-len 128 --output-len 128 --out out.csv`
  - `tools/metrics_rename.py`: `--in out.csv --fmt csv --out out_renamed.csv`
  - `tools/gen_scenario_yaml.py`: 根据参数生成 `configs/scenarios/*.yaml`。

## 修改点（文件/代码）
- 新增上述目录与脚本；工具可复用现有模块函数（如 `metrics/rename.py` 与 `testsuites/perf.py`）。
- `README.md`：补充使用示例与命令。

## 测试用例（必须）
- 为工具脚本新增最小单测：参数解析、文件产生、与模块函数一致性。
- `pytest -q -m "not slow"` 全绿。

## 命令与验证
- `python tools/acs_bench_mock.py --concurrency 1 --input-len 128 --output-len 128 --out /tmp/p.csv`
- `python tools/metrics_rename.py --in /tmp/p.csv --fmt csv --out /tmp/p2.csv`

## 验收标准
- 生成文件字段与 `testsuites/perf.py`、`metrics/rename.py` 严格对齐。
- 文档与示例完整可执行。

## 参考实现要点（指导 Codex Cloud）
- 使用 `argparse`；主逻辑委托到现有模块函数，脚本仅做 I/O 与参数解析。
- 注意 CSV UTF-8 与换行符处理（`newline=''`）。

