### 目标
- [ ] 本 PR 的范围清晰、粒度可评审
- [ ] 本地 `pytest` 全绿；CI 全绿
- [ ] 已在提交后使用 `gh pr view` 或 GitHub 网页确认 PR 存在，并在相关 Issue/沟通中回贴 PR 链接（若被自动合并也需贴链接并说明）
- [ ] 提交前已将工作分支 `rebase` 到最新目标分支（如 `origin/main`），并本地解决冲突 + 通过 `pytest`/`ruff`/`black`/`isort`/`mypy --strict`

### TDD 证明
- [ ] 先提交了测试（使本地/CI 变红）
- [ ] 再提交实现（使本地/CI 变绿）

### 风险/回滚
- [ ] 若上线异常，执行 `git revert <merge-commit>` 回滚
