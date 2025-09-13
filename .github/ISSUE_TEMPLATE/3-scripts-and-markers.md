---
name: "chore: Scripts & Pytest Markers"
about: "Add scripts/deploy_k8s.sh, scripts/collect_and_push.sh and register pytest markers"
title: "chore(scripts,tests): add deployment scripts and pytest markers"
labels: ["chore", "testing", "scripts"]
assignees: []
---

## 背景
仓库约定存在 `scripts/deploy_k8s.sh`、`scripts/collect_and_push.sh` 与测试 markers，但尚未补齐，影响运维与测试分类执行。

## 目标
- 提供 K8s 部署与指标收集推送脚本（与 Python 编排逻辑对齐、保留 `--dry-run`）。
- 为现有测试添加 markers，并在 `pytest.ini` 注册，支持按子集执行。

## 详细需求
- 脚本
  - `scripts/deploy_k8s.sh`：接收 `-f <yaml>`，执行 `kubectl apply -f`，打印 Service 访问提示。
  - `scripts/collect_and_push.sh`：读取性能 CSV 或通过 `python -m` 方式聚合，并在 `run_type=daily` 且配置 `PROM_PUSHGATEWAY_URL` 时推送。
  - 两个脚本均提供 `-h/--help`，失败返回非零退出码。
- 测试标记
  - 为 tests 添加 `@pytest.mark.functional` / `perf` / `accuracy` / `integration` / `slow`。
  - 在 `pytest.ini` 注册这些 markers 的说明。

## 修改点（文件/代码）
- `scripts/deploy_k8s.sh`、`scripts/collect_and_push.sh`（新增，可含占位实现）。
- 各测试文件头部添加合适的 markers。
- `pytest.ini` 新增 markers 声明。

## 测试与验证
- `bash scripts/deploy_k8s.sh -h` / `bash scripts/collect_and_push.sh -h` 正常输出帮助。
- `pytest -m functional` / `pytest -m perf` 能筛选子集。

## 验收标准
- 脚本具备基础参数校验与帮助输出，markers 分类执行可用。

## 参考实现要点（指导 Codex Cloud）
- 脚本尽量保持幂等与安全（`set -euo pipefail`），并在 CI 中仅 smoke 其 `-h`。
- markers 添加不改变现有断言逻辑，仅做分类标签。

