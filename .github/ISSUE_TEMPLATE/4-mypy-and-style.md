---
name: "chore: mypy --strict & ruff"
about: "Fix typing issues, remove unused ignores, enable ruff/mypy checks in CI"
title: "chore(types,lint): fix mypy --strict and enable ruff/mypy in CI"
labels: ["chore", "types", "lint"]
assignees: []
---

## 背景
`mypy --strict src` 报告若干问题；目前 CI 未强制运行 `ruff`/`mypy`。需分阶段修复并在 CI 中启用检查。

## 目标
- 修复 `mypy --strict src` 报告，使其 0 error（或第一阶段将少量模块降级为宽松模式并标注 TODO）。
- CI 中增加 `ruff check` 与 `mypy` 步骤（可先设为 non-blocking，后续提升为必过）。

## 详细需求
- 修复点（示例，需逐项清理）：
  - `src/vllm_cibench/config.py`: 移除 `Unused "type: ignore"`、补齐 `no-any-return` 的返回类型。
  - `src/vllm_cibench/metrics/pushgateway.py`: 移除 `Unused "type: ignore"`。
  - `src/vllm_cibench/clients/openai_client.py`: 移除 `Unused "type: ignore"`，为 `chat_completions` 补齐精确返回类型。
  - `src/vllm_cibench/clients/http.py`: 移除 `Unused "type: ignore"`。
  - `src/vllm_cibench/deploy/local.py`: 为 `subprocess.Popen[...]` 增加类型参数。
  - `src/vllm_cibench/deploy/k8s/kubernetes_client.py`: 为函数添加返回/参数注解；清理 `Unused "type: ignore"`。
  - `src/vllm_cibench/run.py`: 移除 `Unused "type: ignore"`。
- CI 修改
  - 更新 `.github/workflows/ci.yml`：新增 `ruff check` 与 `mypy` 两步（可与 `pytest` 并行）。

## 测试与验证
- 本地：`ruff check src tests`、`mypy --hide-error-context --strict src`。
- CI：PR 中看到新步骤结果且通过。

## 验收标准
- 本地与 CI 的 `ruff`/`mypy` 均无 error（或按阶段目标）。

## 参考实现要点（指导 Codex Cloud）
- 合理引入 `typing` 与 `typing_extensions`；为外部库对象添加最小 `Any` 包裹以过渡。
- 优先删除多余 `type: ignore`，避免 suppress 真实问题。

