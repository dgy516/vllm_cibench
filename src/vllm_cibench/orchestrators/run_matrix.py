"""按 matrix.yaml 批量执行场景编排。"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Iterable, Optional

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
    run_type: str = "pr", *, root: Optional[str] = None, dry_run: bool = False
) -> Dict[str, object]:
    """执行 matrix 中的所有场景，返回结果映射。

    参数:
        run_type: 运行类型（pr/daily）。
        root: 仓库根路径，默认 CWD。
        dry_run: 若为 True，则不会在 daily 运行时推送指标。

    返回值:
        dict: {scenario_id: result_dict}

    副作用:
        对每个场景调用 `run_pipeline.execute`，可能进行探活；在测试中可 monkeypatch。
    """

    base = Path(root) if root else Path.cwd()
    matrix = load_matrix(base / "configs" / "matrix.yaml")
    results: Dict[str, object] = {}
    for sid in scenarios_from_matrix(matrix):
        results[sid] = run_pipeline.execute(
            scenario_id=sid, run_type=run_type, root=str(base), dry_run=dry_run
        )
    return results
