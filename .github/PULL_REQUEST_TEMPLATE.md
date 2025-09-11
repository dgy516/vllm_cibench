## 概述
- 变更目的：
- 关联 Issue：
- 变更类型：docs / config / ci / other

## 变更内容
- 文档：是否更新 DESIGN/DEVELOPMENT/REQUIREMENTS/TODO？
- 配置：是否修改/新增 configs/*（providers/scenarios/profiles/matrix）？
- CI：是否修改 .github/workflows？

## 验证
- YAML 通过 yamllint 校验
- 关键路径存在性检查通过（CI 自动执行）
- 本地自查（若适用）：
  ```bash
  yamllint -c .yamllint.yaml .
  ```

## 清单
- [ ] 变更符合 AGENTS.md（Repository Guidelines）
- [ ] 文档已更新或确认无需更新
- [ ] 无敏感信息（密钥/地址）被提交

