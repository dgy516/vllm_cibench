---
name: "feat: Accuracy Pipeline (GPQA)"
about: "Add accuracy executor (GPQA default), wire into run_pipeline, config + tests"
title: "feat(accuracy): add GPQA accuracy runner and pipeline integration"
labels: ["feat", "accuracy", "good first issue"]
assignees: []
---

## 背景
当前 `matrix.yaml` 已包含 `accuracy` 开关，但 `run_pipeline.execute` 尚未执行精度评测阶段。需要新增 `testsuites/accuracy.py`，默认集成 Simple-Evals 的 GPQA（可替换/扩展），并将结果汇总至 CLI 输出。

## 目标
- 在 `run_pipeline.execute` 中，当某场景 `accuracy: true` 时执行精度评测。
- 输出结构包含：
  ```json
  {
    "accuracy": {"task": "gpqa", "score": 0.52, "total": 100, "correct": 52}
  }
  ```
- 可在测试环境以 mock 方式最小化运行，避免外网依赖。

## 详细需求
- 新增模块 `src/vllm_cibench/testsuites/accuracy.py`：
  - 函数：`run_accuracy(base_url: str, model: str, cfg: Mapping[str, Any]) -> Dict[str, Any]`
  - 约定字段：`{"task": str, "score": float, "correct": int, "total": int}`
  - 允许通过 `cfg` 切换任务（默认 `gpqa`），并支持 provider/api_key 注入（从 `configs/tests/accuracy.yaml` 读取）。
- 修改 `src/vllm_cibench/orchestrators/run_pipeline.py`：
  - 解析 `matrix` 计划后，在 perf 之后追加 accuracy 阶段，异常时 `result["accuracy"] = {"error": str}`。
- 新增配置文件 `configs/tests/accuracy.yaml`：
  - 默认：`task: gpqa`，`dataset_split: validation[:100]`（示例），`max_samples: 100`，`scoring: exact_match`。
  - 允许 `provider`/`api_key_env` 字段（例如 `PROM_*` or `OPENAI_API_KEY`）。

## 修改点（文件/代码）
- `src/vllm_cibench/testsuites/accuracy.py`（新增）
- `src/vllm_cibench/orchestrators/run_pipeline.py`
- `configs/tests/accuracy.yaml`（新增）
- `README.md`（命令示例与说明）

## 测试用例（必须）
- 新增 `tests/testsuites/test_accuracy.py`：
  - mock HTTP 调用，`run_accuracy()` 返回固定分数结构。
  - 覆盖异常路径（网络失败、空样本）。
- 修改 `tests/orchestrators/test_run_pipeline.py`：
  - monkeypatch `run_accuracy`，设置 `matrix` 为 `accuracy: true`，断言 `result["accuracy"]` 存在。

## 命令与验证
- `pytest -q -m "not slow"`
- `python -m vllm_cibench.run run --scenario local_single_qwen3-32b_guided_w8a8 --run-type pr --dry-run`

## 验收标准
- 上述命令可见 `accuracy` 字段，单测全绿，覆盖率保持 ≥85%。

## 参考实现要点（指导 Codex Cloud）
- 复用 `OpenAICompatClient` 调用 `/v1/chat/completions`；评测时构造若干选择题 prompt，对比期望答案计算分数。
- 允许 `cfg.get("max_samples", N)` 控制评测样本数，保障 CI 快速。
- 结果结构需可 JSON 序列化并稳定。

