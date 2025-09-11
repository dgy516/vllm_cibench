"""按 matrix.yaml 批量执行场景编排。"""

from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Dict, Iterable, Optional, Tuple

from vllm_cibench.config import load_matrix
from vllm_cibench.orchestrators import run_pipeline


def scenarios_from_matrix(matrix: Dict[str, object]) -> Iterable[str]:
    """从 matrix 配置中提取场景 ID 列表。

    参数:
        matrix: `load_matrix` 返回的字典（键为场景 id）。

    返回值:
        Iterable[str]: 场景 id 列表。

    副作用:
        无。
    """

    return list(matrix.keys())


def execute_matrix(
    run_type: str = "pr",
    *,
    root: Optional[str] = None,
    dry_run: bool = False,
    concurrency: int = 1,
    per_scenario_timeout_s: float = 60.0,
    tolerate_failures: bool = True,
) -> Dict[str, object]:
    """执行 matrix 中的所有场景，返回结果映射。

    参数:
        run_type: 运行类型（pr/daily）。
        root: 仓库根路径，默认 CWD。

    返回值:
        dict: {scenario_id: result_dict}

    副作用:
        对每个场景调用 `run_pipeline.execute`，可能进行探活；在测试中可 monkeypatch。
    """

    base = Path(root) if root else Path.cwd()
    matrix = load_matrix(base / "configs" / "matrix.yaml")
    results: Dict[str, object] = {}

    scenario_ids = list(scenarios_from_matrix(matrix))
    start = time.time()
    errors: Dict[str, str] = {}

    def _task(sid: str) -> Tuple[str, object]:
        try:
            res = run_pipeline.execute(
                scenario_id=sid,
                run_type=run_type,
                root=str(base),
                dry_run=dry_run,
                timeout_s=per_scenario_timeout_s,
            )
            return sid, res
        except Exception as e:  # pragma: no cover - 异常路径在并发下较难覆盖
            if not tolerate_failures:
                raise
            errors[sid] = str(e)
            return sid, {"scenario": sid, "error": str(e)}

    if concurrency <= 1:
        for sid in scenario_ids:
            k, v = _task(sid)
            results[k] = v
    else:
        with ThreadPoolExecutor(max_workers=max(1, concurrency)) as ex:
            futures = {ex.submit(_task, sid): sid for sid in scenario_ids}
            for fut in as_completed(futures):
                sid = futures[fut]
                try:
                    k, v = fut.result()
                except Exception as e:  # pragma: no cover
                    if not tolerate_failures:
                        raise
                    errors[sid] = str(e)
                    k, v = sid, {"scenario": sid, "error": str(e)}
                results[k] = v

    elapsed = time.time() - start
    success = sum(
        1 for sid in scenario_ids if sid in results and "error" not in results[sid]
    )
    failed = len(scenario_ids) - success
    return {
        "results": results,
        "summary": {
            "total": len(scenario_ids),
            "success": success,
            "failed": failed,
            "errors": errors,
            "elapsed_s": round(elapsed, 3),
            "run_type": run_type,
            "dry_run": dry_run,
            "concurrency": concurrency,
        },
    }
