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
    run_type: str = "pr", *, root: Optional[str] = None, timeout_s: float = 60.0
) -> Dict[str, object]:
    """执行 matrix 中的所有场景，返回结果映射。

    参数:
        run_type: 运行类型（pr/daily）。
        root: 仓库根路径，默认 CWD。
        timeout_s: 探活最大等待时长（秒），会传递给单场景执行函数。

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
            scenario_id=sid, run_type=run_type, root=str(base), timeout_s=timeout_s
        )
    return results
