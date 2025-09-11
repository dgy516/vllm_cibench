## 变更内容（必填）
- [ ] 功能/修复说明：
- [ ] 受影响模块：
- [ ] 相关场景/配置（如有）：

## 复现实验与验证（必填）
- 复现实验命令：
  - 计划查看：`python -m vllm_cibench.run --scenario <id> --run-type pr`
  - 编排运行：`python -m vllm_cibench.run run --scenario <id> --run-type pr --dry-run`
  - 批量运行：`python -m vllm_cibench.run run-matrix --run-type pr --dry-run`
- 单元/系统测试：`pytest -q -m "not slow"`

## 性能变更（如适用）
- [ ] 本次改动涉及性能路径
- 对比摘要：
  - 变更前：
  - 变更后：
  - 说明：指标由 CSV → `metrics/rename.py` 规范化；仅 daily 推送

## 指标与可观测性（如适用）
- [ ] 仅在 daily 任务推送到 Pushgateway（需 `PROM_PUSHGATEWAY_URL`）
- 标签维度：model/quant/scenario

## 兼容性与风险
- 兼容性：
- 风险点与回滚策略：`git revert <merge-commit>`

## 清单（必填）
- [ ] 代码风格：`ruff/black/isort` 通过
- [ ] 类型检查：`mypy` 通过
- [ ] 测试通过：`pytest -q -m "not slow"`
- [ ] 文档/中文注释完善
