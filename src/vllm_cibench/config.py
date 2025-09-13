"""配置加载与数据模型。

提供从 YAML 文件加载场景与测试配置的基础工具。

参数:
    无显式入参，模块函数各自接收文件路径。

返回值:
    见各函数中文 Docstring 说明。

副作用:
    仅进行文件读取与反序列化，无外部系统交互。
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, cast

import yaml


@dataclass
class Scenario:
    """场景配置模型（最小字段）。

    属性:
        id: 场景唯一标识，与文件内 `id` 字段一致。
        mode: 运行模式（如 `local`/`k8s-hybrid`/`k8s-pd`）。
        served_model_name: 服务对外模型名（如 `qwen3-32b`）。
        model: 逻辑模型标识（如 `Qwen3-32B`）。
        quant: 量化档位（如 `w8a8`）。
        raw: 原始 YAML 内容字典，便于后续扩展。
    """

    id: str
    mode: str
    served_model_name: str
    model: str
    quant: str
    raw: Dict[str, Any]


def _read_yaml(path: Path) -> Dict[str, Any]:
    """读取 YAML 文件为字典。

    参数:
        path: YAML 文件路径。

    返回值:
        dict: 解析后的字典。

    副作用:
        文件 IO 读取；若文件不存在会抛出异常。
    """

    with path.open("r", encoding="utf-8") as f:
        loaded = yaml.safe_load(f) or {}
    return cast(Dict[str, Any], loaded)


def load_matrix(path: Path) -> Dict[str, Any]:
    """加载矩阵配置 `configs/matrix.yaml`。

    参数:
        path: 矩阵文件路径。

    返回值:
        dict: 键为场景 id，值为 `{pr: {...}, daily: {...}}` 配置。
    """

    return _read_yaml(path)


def list_scenarios(dir_path: Path) -> List[Scenario]:
    """扫描场景目录返回场景列表。

    参数:
        dir_path: `configs/scenarios/` 目录路径。

    返回值:
        List[Scenario]: 解析后的最小场景对象列表。
    """

    scenarios: List[Scenario] = []
    for yml in sorted(dir_path.glob("*.yaml")):
        data = _read_yaml(yml)
        scenarios.append(
            Scenario(
                id=str(data.get("id")),
                mode=str(data.get("mode")),
                served_model_name=str(data.get("served_model_name")),
                model=str(data.get("model")),
                quant=str(data.get("quant")),
                raw=data,
            )
        )
    return scenarios


@dataclass
class ScenarioRegistry:
    """场景注册表，按 id 存取场景。"""

    mapping: Dict[str, Scenario]

    @classmethod
    def from_dir(cls, dir_path: Path) -> "ScenarioRegistry":
        """从目录构建注册表。

        参数:
            dir_path: `configs/scenarios/` 目录路径。

        返回值:
            ScenarioRegistry: 包含所有场景的注册表。

        副作用:
            读取文件系统。
        """

        scenarios = list_scenarios(dir_path)
        return cls({s.id: s for s in scenarios})

    def get(self, scenario_id: str) -> Scenario:
        """按 id 获取场景，若不存在则抛出 KeyError。

        参数:
            scenario_id: 场景 id。

        返回值:
            Scenario: 匹配的场景对象。

        副作用:
            无。
        """

        if scenario_id not in self.mapping:
            raise KeyError(f"scenario not found: {scenario_id}")
        return self.mapping[scenario_id]


def resolve_plan(
    matrix: Dict[str, Any], scenario_id: str, run_type: str
) -> Dict[str, Any]:
    """根据矩阵解析某场景在指定运行类型下的计划。

    参数:
        matrix: 矩阵配置（来自 `load_matrix`）。
        scenario_id: 场景 id。
        run_type: 运行类型，`pr` 或 `daily`。

    返回值:
        dict: 形如 `{"functional": "all"|list, "perf": bool, "accuracy": bool}`。

    副作用:
        无。
    """

    entry = matrix.get(scenario_id)
    if not entry:
        raise KeyError(f"scenario not found in matrix: {scenario_id}")
    rt = entry.get(run_type)
    if not rt:
        raise KeyError(f"run_type not found for scenario '{scenario_id}': {run_type}")
    return cast(Dict[str, Any], rt)
