# TODO（分阶段任务与验收标准）

## 配置与加载
- [ ] 定义配置 Schema（scenarios/tests/matrix/providers），实现 `ConfigLoader`
  - 验收：非法字段/缺失项给出清晰错误；支持默认值；文档化字段含义
- [ ] `configs/matrix.yaml` 跑通：按场景与 run_type 选择子集或全量
  - 验收：未配置场景默认运行全部功能 + 对应 perf/accuracy 档位

## 启动与健康
- [ ] `ServiceLauncher`（本地/K8s NodePort）与 `/health` 健康检查
  - 验收：重试与指数退避；最大等待 20 分钟；失败时记录并跳过后续阶段但继续其他场景
- [ ] 场景级清理（停止本地进程 / `kubectl delete -f`）与日志归档
  - 验收：`artifacts/logs/service_*.log` 生成完整

## 功能测试（OpenAI 接口）
- [ ] 用例套件：`chat_core`、`completions_core`、`params_boundary`、`function_call`、`guided`、`reasoning`
  - 验收：覆盖非流式与流式、多轮对话；参数与边界；能力探测后对不支持参数跳过
- [ ] Guided Decoding（`response_format`/`json_schema`）与 Function Call（tools/tool_choice）
  - 验收：最小示例稳定通过；中文/英文混合输入通过
- [ ] Reasoning 断言（`choices[0].message.reasoning_content` 或配置回退键）
  - 验收：断言字段存在且非空（或按场景放宽）

## 性能（mock acs-bench）
- [ ] 并发执行器（threading-pool，climb 模式）与请求生成（中英混合；固定 seed）
  - 验收：可配置并发/长度/epochs/warmup/num_requests；PR/每日档位可切换
- [ ] 统计与 CSV 产出（requests_*、summary_*）
  - 验收：包含 P75/P90/P95/P99/AVG/MAX、QPS、失败率；定义与设计一致
- [ ] 服务器侧指标占位（不可得时填 -1）
  - 验收：字段齐全且单位为秒

## 精度（Simple-evals）
- [ ] 适配 GPQA（PR=debug，每日=全量），解析 JSON/HTML 生成 score
  - 验收：产物保存至 `artifacts/accuracy/{scenario}/{ts}/`；得分成功解析
- [x] 阈值与 CI 策略（代码端已支持 `min_score` 判定与 `ok` 标记；CI 门禁在 workflow 中实现）
  - 验收：PR 低于阈值失败；每日仅告警

## 指标转换与推送（Prom）
- [ ] CSV→Prom 映射与单位规范（前缀可为空）
  - 验收：时间统一秒、吞吐/QPS/比率符合命名规范；分位数标签 `{quantile=…}`
- [ ] Pushgateway 客户端（仅每日推送）
  - 验收：`PROM_PUSHGATEWAY_URL` 可配置；标签齐全；返回码校验与重试
- [ ] 功能性指标：`functional_pass_ratio` 与单用例 `functional_case_pass{suite,case_id}`（每日）
  - 验收：Grafana 可表格显示绿/红

## Grafana
- [ ] 参数化 Dashboard JSON（变量含 `metric_prefix` 与 `quantile`）
  - 验收：导入后可切换模型/量化/场景并对比 0d/-1d/-7d

## CI 工作流
- [x] 每日工作流：continue-on-error 执行矩阵；Gate 判定 functional/accuracy；上传产物（30 天）
  - 验收：Gate 生效，失败时工作流红；产物保留 30 天
- [ ] PR 工作流：如需 Gate，可在 smoke 上增加必需门（当前仅上传 artifacts，14 天保留）
  - 验收：Performance 与最近一次 daily 基线比对门禁：TTFT/E2E P99 回归>10% 失败、QPS 下降>5% 失败、Fail Rate >5% 失败
- [x] 归档与保留策略（PR:14 天、每日:30 天）
  - 验收：artifacts 中 CSV/JSON/HTML/日志/命令快照齐全

## 场景与样例配置
- [ ] 首批场景与量化变体（待补充具体 ID 与参数）
  - 验收：至少 3 个场景（本地 single、K8s hybrid、K8s PD）能完整跑通

## 质量与规范
- [ ] mypy 严格、ruff/black 一致性、覆盖率 ≥85%、函数中文注释、模块化
  - 验收：CI 绿；PR 模板包含场景/命令/指标对比
