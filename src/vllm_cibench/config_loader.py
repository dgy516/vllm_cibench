"""配置 Schema 与加载器（严格校验）。

使用 Pydantic 定义 `scenarios/tests/matrix/providers` 的最小 Schema，
提供加载与校验函数，捕获未知字段与缺失项，并给出清晰错误。

注意：此模块不替换现有轻量 `config.py` 行为，仅作为严格校验工具；
在编排或 CI 中可按需启用。
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Mapping, MutableMapping, Optional

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError


def _read_yaml(path: Path) -> Dict[str, Any]:
    """读取 YAML 文件为字典。

    参数:
        path: YAML 文件路径。

    返回值:
        dict: 解析后的字典（空文件返回空字典）。

    副作用:
        文件 IO；错误由调用方处理。
    """

    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return dict(data or {})


class ScenarioSchema(BaseModel):
    """场景文件 Schema（最小字段 + 禁止未知键）。

    参数:
        id: 场景 ID。
        mode: 运行模式（local/k8s-hybrid/k8s-pd）。
        served_model_name: 服务对外模型名。
        model: 逻辑模型标识。
        quant: 量化档位。
        base_url: 本地模式需要的基础 URL（可选）。
        features: 能力标记。
        k8s: K8s 相关配置（任意键，保留以兼容）。
        pd: PD 模式参数（兼容保留）。
        startup_timeout_seconds: 启动超时（秒）。
        env: 环境变量映射。
        args: 启动参数映射。
    """

    model_config = ConfigDict(extra="forbid")

    id: str
    mode: str
    served_model_name: str
    model: str
    quant: str
    base_url: Optional[str] = None
    features: Mapping[str, bool] = Field(default_factory=dict)
    k8s: Mapping[str, Any] | None = None
    pd: Mapping[str, Any] | None = None
    startup_timeout_seconds: Optional[int] = None
    env: Mapping[str, str] = Field(default_factory=dict)
    args: Mapping[str, Any] = Field(default_factory=dict)


class PlanSchema(BaseModel):
    """单个运行类型的计划。

    参数:
        functional: 可为 "all"/bool/list（最小放宽）。
        perf: 是否启用性能。
        accuracy: 是否启用精度。
    """

    model_config = ConfigDict(extra="forbid")

    functional: Any
    perf: bool
    accuracy: bool


class RunTypesSchema(BaseModel):
    """场景在 PR/Daily 下的计划。"""

    model_config = ConfigDict(extra="forbid")

    pr: PlanSchema
    daily: PlanSchema


class ProviderItem(BaseModel):
    """Provider 条目。"""

    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    api_key: str
    base_url: str
    model_name: str
    model_category: str


class ProvidersSchema(BaseModel):
    """providers.yaml Schema。"""

    model_config = ConfigDict(extra="forbid")

    providers: List[ProviderItem]


class FunctionalConfigSchema(BaseModel):
    """功能套件配置（最小字段）。

    参数:
        enabled: 开关（默认 True）。
        suite: 是否启用批量用例（默认 False）。
        functional_metrics: 指标配置（支持 per_case）。
        capabilities: 已支持能力列表（用于按能力跳过）。
        cases/matrices/negative: 放宽为映射/列表，留给执行器处理具体校验。
    """

    model_config = ConfigDict(extra="forbid")

    enabled: bool = True
    suite: bool = False
    functional_metrics: Mapping[str, Any] = Field(default_factory=dict)
    capabilities: List[str] = Field(default_factory=list)
    cases: List[Mapping[str, Any]] = Field(default_factory=list)
    matrices: Mapping[str, Any] = Field(default_factory=dict)
    negative: Mapping[str, Any] = Field(default_factory=dict)


def load_scenarios_strict(dir_path: Path) -> List[ScenarioSchema]:
    """严格加载并校验场景目录。

    参数:
        dir_path: `configs/scenarios` 目录。

    返回值:
        List[ScenarioSchema]: 通过校验的场景列表。

    副作用:
        文件 IO；发现校验错误将抛出 ValidationError。
    """

    out: List[ScenarioSchema] = []
    for yml in sorted(dir_path.glob("*.yaml")):
        data = _read_yaml(yml)
        out.append(ScenarioSchema(**data))
    return out


def load_matrix_strict(path: Path) -> Mapping[str, RunTypesSchema]:
    """严格加载 matrix.yaml（动态键 → RunTypesSchema）。

    参数:
        path: 矩阵文件路径。

    返回值:
        映射：场景 ID → RunTypesSchema。
    """

    data = _read_yaml(path)
    result: Dict[str, RunTypesSchema] = {}
    for sid, item in (data or {}).items():
        if not isinstance(item, MutableMapping):
            raise ValidationError(
                [
                    {
                        "loc": (sid,),
                        "msg": "must be a mapping with keys 'pr' and 'daily'",
                        "type": "type_error",
                    }
                ],
                RunTypesSchema,
            )
        result[str(sid)] = RunTypesSchema(**dict(item))
    return result


def load_functional_config_strict(path: Path) -> FunctionalConfigSchema:
    """严格加载功能套件配置。"""

    data = _read_yaml(path)
    return FunctionalConfigSchema(**data)


def load_providers_strict(path: Path) -> ProvidersSchema:
    """严格加载 providers.yaml。"""

    data = _read_yaml(path)
    return ProvidersSchema(**data)


@dataclass
class ValidationReport:
    """校验报告。"""

    scenarios: int
    matrix_keys: int
    functional_ok: bool
    providers: int


def validate_all(root: Path) -> ValidationReport:
    """对仓库内关键配置做一轮严格校验并返回概览。

    参数:
        root: 仓库根目录。

    返回值:
        ValidationReport: 包含对象数量与是否通过的概要。
    """

    sdir = root / "configs" / "scenarios"
    scenarios = load_scenarios_strict(sdir)
    matrix = load_matrix_strict(root / "configs" / "matrix.yaml")
    # 功能配置：若不存在则记为 False；存在且通过则 True
    func_path = root / "configs" / "tests" / "functional.yaml"
    functional_ok = False
    if func_path.exists():
        _ = load_functional_config_strict(func_path)
        functional_ok = True
    providers = load_providers_strict(root / "configs" / "providers.yaml")
    return ValidationReport(
        scenarios=len(scenarios),
        matrix_keys=len(matrix),
        functional_ok=functional_ok,
        providers=len(providers.providers),
    )

