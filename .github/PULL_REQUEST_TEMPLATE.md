## 概述
- 目的与动机：
- 关联 Issue：
- 变更类型：feat / fix / perf / refactor / test / docs / chore

## 场景与配置
- 受影响场景（scenario_id）：
- 配置改动（如有）：
  - configs/scenarios/…：
  - configs/tests/perf/profiles/…：
  - configs/tests/accuracy/…：
  - configs/matrix.yaml：

## 复现实验命令（示例）
功能性（OpenAI 接口）：
```bash
# chat/completions 示例
curl -sS -H 'Content-Type: application/json' -d '{"messages":[{"role":"user","content":"hello"}],"model":"<served-model-name>","temperature":0.6,"max_tokens":256}' http://<HOST>:<PORT>/v1/chat/completions | jq .
```

性能（mock acs-bench，按 profiles 执行）示例：
```bash
# 仅示意，实际以工具入口/配置为准
python tools/acs_bench_mock.py --provider configs/providers.yaml --profile configs/tests/perf/profiles/pr.yaml --scenario <scenario_id>
```

精度（Simple-evals, GPQA）：
```bash
python simple_evals.py --model <MODEL> --dataset gpqa \
  --served-model-name <served-model-name> --url http://<HOST>:<PORT>/v1 \
  --max-tokens 16384 --temperature 0.6 --num-threads 32 --debug
```

## 指标前后对比（如涉性能/精度）
- TTFT P99：before → after
- E2E P99：before → after
- QPS：before → after
- Fail Rate：before → after
- Accuracy（GPQA）：before → after

## 清单
- [ ] 遵循 TDD（先测后码），全部测试通过
- [ ] 代码中文注释完整（函数注释/Docstring）
- [ ] 文档已更新（如适用）：AGENTS.md / docs/*
- [ ] PR 产物可复现（命令与配置齐备）

