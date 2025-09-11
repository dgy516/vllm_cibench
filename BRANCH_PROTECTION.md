# GitHub 分支保护建议
在 GitHub → Settings → Branches 添加规则（main）：
- Require a pull request before merging ✅
- Require status checks to pass ✅  （勾选：ci / lint、ci / typecheck、ci / test）
- Require linear history ✅（或要求 Rebase & Merge）
- Restrict who can push ✅（仅机器人/管理员）
- 可选：Require approvals（配合 CODEOWNERS）
