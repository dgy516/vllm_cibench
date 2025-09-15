# GitHub 分支保护建议
强制策略：禁止直接 push 到 main，必须通过 PR 合并。

在 GitHub → Settings → Branches 添加规则（main）：
- Require a pull request before merging ✅
- Require status checks to pass ✅  （勾选：ci / lint、ci / typecheck、ci / test）
- Require linear history ✅（或要求 Rebase & Merge）
- Restrict who can push ✅（仅机器人/管理员；个人仓库受限，建议迁移到组织仓库以启用）
- 可选：Require approvals（配合 CODEOWNERS）

仓库内已补充：
- 客户端预防：`hooks/pre-push` 会拒绝向 `main` 的 push（需开发者安装到 `.git/hooks/`）。
- 服务器稽核：`.github/workflows/protect-main.yml` 会在 main 上的直接 push 失败（PR 合并除外）。
