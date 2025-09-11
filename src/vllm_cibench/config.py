"""
配置加载与校验模块

中文注释约定：
- 所有公共函数提供参数、返回值与异常说明。

注意：仅包含纯解析与校验逻辑，不涉及网络/进程操作，便于单元测试。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Tuple

import yaml


SUPPORTED_QUANT = {"w8a8", "w4a8", "none"}
SUPPORTED_MODES = {"local", "k8s-hybrid", "k8s-pd"}


@dataclass
class Provider:
    """服务提供方配置（兼容 acs-bench 的 providers.yaml）。

    属性:
        id: 提供方标识（可选）。
        name: 提供方名称（可选）。
        api_key: 访问凭证（本项目默认 EMPTY）。
        base_url: 基础URL，形如 http://<IP>:<PORT>/v1。
        model_name: 启动服务时的模型名（通常等于 served-model-name）。
        model_category: 模型类别（可选）。
    """

    id: Optional[str] = None
    name: Optional[str] = None
    api_key: Optional[str] = None
    base_url: str = ""
    model_name: str = ""
    model_category: Optional[str] = None


@dataclass
class Scenario:
    """测试场景配置。

    属性:
        id: 场景ID，唯一。
        mode: 启动模式：local / k8s-hybrid / k8s-pd。
        model: 模型显示名。
        served_model_name: 服务暴露名称（用于 OpenAI 请求的 model 字段）。
        quant: 量化类型：w8a8 / w4a8 / none。
        features: 特性开关，例如 guided_decoding、function_call、reasoning。
        base_url: 本地模式直接提供；k8s 模式可留空，由外部解析 NodePort 后生成。
        k8s: k8s 相关配置字典。
        pd: PD 分离部署参数字典（scheduler/prefill/decode 等）。
        startup_timeout_seconds: 启动等待超时（秒）。
        env: 需要注入的环境变量。
        args: 启动参数（键值），仅描述用途，不执行。
    """

    id: str
    mode: str
    model: str
    served_model_name: str
    quant: str
    features: Dict[str, Any] = field(default_factory=dict)
    base_url: Optional[str] = None
    k8s: Dict[str, Any] = field(default_factory=dict)
    pd: Dict[str, Any] = field(default_factory=dict)
    startup_timeout_seconds: int = 1200
    env: Dict[str, str] = field(default_factory=dict)
    args: Dict[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        """校验场景配置是否合法。

        异常:
            ValueError: 当字段不合法或缺失时抛出。
        """

        if self.mode not in SUPPORTED_MODES:
            raise ValueError(f"scenario[{self.id}] mode must be one of {SUPPORTED_MODES}, got {self.mode}")
        if self.quant not in SUPPORTED_QUANT:
            raise ValueError(f"scenario[{self.id}] quant must be one of {SUPPORTED_QUANT}, got {self.quant}")
        if self.mode == "local" and not self.base_url:
            # 本地模式需提供 base_url，以便测试直接访问
            raise ValueError(f"scenario[{self.id}] local mode requires base_url")
        if self.mode != "local" and not self.k8s:
            # k8s 模式需提供 k8s 字段
            raise ValueError(f"scenario[{self.id}] {self.mode} requires k8s section")


@dataclass
class PerfProfile:
    """性能档位配置（PR / Daily）。

    属性:
        profile: 档位名称（pr/daily）。
        control_method: 控制方式，默认 climb。
        growth_rate: 爬坡增长步长。
        growth_interval_ms: 爬坡时间间隔（毫秒）。
        init_concurrency: 初始并发。
        backend: 接口类型 openai-chat（默认）。
        temperature/top_k/top_p: 采样相关默认值。
        warmup/epochs: 预热与轮次。
        concurrency/input_length/output_length: 取值列表。
        num_requests_per_concurrency: 每个并发的请求个数（倍数）。
    """

    profile: str
    control_method: str = "climb"
    growth_rate: int = 2
    growth_interval_ms: int = 5000
    init_concurrency: int = 1
    backend: str = "openai-chat"
    temperature: float = 0.6
    top_k: int = 8
    top_p: float = 1.0
    warmup: int = 0
    epochs: int = 1
    concurrency: List[int] = field(default_factory=lambda: [1])
    input_length: List[int] = field(default_factory=lambda: [128])
    output_length: List[int] = field(default_factory=lambda: [128])
    num_requests_per_concurrency: int = 16


@dataclass
class AccuracyProfile:
    """精度评测配置（Simple-evals）。

    属性:
        run_type: pr/daily。
        tool: 使用工具：simple-evals。
        dataset: 默认 gpqa。
        debug: PR 小样本模式。
        max_tokens/temperature/num_threads: 运行参数。
    """

    run_type: str
    tool: str = "simple-evals"
    dataset: str = "gpqa"
    debug: bool = False
    max_tokens: int = 16384
    temperature: float = 0.6
    num_threads: int = 32


def _load_yaml(path: Path) -> Any:
    """加载 YAML 文件。

    参数:
        path: 文件路径。
    返回:
        解析后的 Python 对象。
    """

    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_providers(path: Path) -> List[Provider]:
    """加载 providers.yaml（兼容 acs-bench）。

    参数:
        path: providers.yaml 路径。
    返回:
        Provider 列表。
    异常:
        ValueError: providers 为空或缺失必要字段。
    """

    data = _load_yaml(path) or {}
    providers: List[Provider] = []
    for item in (data.get("providers") or []):
        base_url = (item or {}).get("base_url")
        model_name = (item or {}).get("model_name")
        if not base_url or not model_name:
            raise ValueError("providers.yaml requires base_url and model_name for each provider")
        providers.append(
            Provider(
                id=item.get("id"),
                name=item.get("name"),
                api_key=item.get("api_key"),
                base_url=base_url,
                model_name=model_name,
                model_category=item.get("model_category"),
            )
        )
    if not providers:
        raise ValueError("providers.yaml contains no providers")
    return providers


def load_scenario(path: Path) -> Scenario:
    """加载单个场景配置。

    参数:
        path: 场景 YAML 路径。
    返回:
        解析并校验后的 Scenario 实例。
    """

    data = _load_yaml(path) or {}
    sc = Scenario(
        id=data["id"],
        mode=data["mode"],
        model=data["model"],
        served_model_name=data["served_model_name"],
        quant=data.get("quant", "none").lower(),
        features=data.get("features") or {},
        base_url=data.get("base_url"),
        k8s=data.get("k8s") or {},
        pd=data.get("pd") or {},
        startup_timeout_seconds=int(data.get("startup_timeout_seconds", 1200)),
        env=(data.get("env") or {}),
        args=(data.get("args") or {}),
    )
    sc.validate()
    return sc


def load_perf_profile(path: Path) -> PerfProfile:
    """加载性能档位配置。

    参数:
        path: YAML 路径。
    返回:
        PerfProfile 实例。
    """

    data = _load_yaml(path) or {}
    return PerfProfile(
        profile=data.get("profile", "pr"),
        control_method=data.get("control_method", "climb"),
        growth_rate=int(data.get("growth_rate", 2)),
        growth_interval_ms=int(data.get("growth_interval_ms", 5000)),
        init_concurrency=int(data.get("init_concurrency", 1)),
        backend=data.get("backend", "openai-chat"),
        temperature=float(data.get("temperature", 0.6)),
        top_k=int(data.get("top_k", 8)),
        top_p=float(data.get("top_p", 1.0)),
        warmup=int(data.get("warmup", 0)),
        epochs=int(data.get("epochs", 1)),
        concurrency=[int(x) for x in (data.get("concurrency") or [1])],
        input_length=[int(x) for x in (data.get("input_length") or [128])],
        output_length=[int(x) for x in (data.get("output_length") or [128])],
        num_requests_per_concurrency=int(data.get("num_requests_per_concurrency", 16)),
    )


def load_accuracy_profile(path: Path) -> AccuracyProfile:
    """加载精度档位配置。

    参数:
        path: YAML 路径。
    返回:
        AccuracyProfile 实例。
    """

    data = _load_yaml(path) or {}
    return AccuracyProfile(
        run_type=data.get("run_type", "pr"),
        tool=data.get("tool", "simple-evals"),
        dataset=data.get("dataset", "gpqa"),
        debug=bool(data.get("debug", False)),
        max_tokens=int(data.get("max_tokens", 16384)),
        temperature=float(data.get("temperature", 0.6)),
        num_threads=int(data.get("num_threads", 32)),
    )


def load_matrix(path: Path) -> Mapping[str, Mapping[str, Dict[str, Any]]]:
    """加载场景-用例矩阵配置。

    参数:
        path: YAML 路径。
    返回:
        dict 映射：scenario_id -> { run_type -> { functional/perf/accuracy } }。
    """

    data = _load_yaml(path) or {}
    return data


def select_for_run(
    matrix: Mapping[str, Mapping[str, Dict[str, Any]]],
    scenario_id: str,
    run_type: str,
) -> Dict[str, Any]:
    """根据矩阵选择某场景在给定运行类型下的测试范围。

    参数:
        matrix: 矩阵配置。
        scenario_id: 场景ID。
        run_type: 运行类型：pr/daily。
    返回:
        dict: { functional: list|"all", perf: bool, accuracy: bool }。
    说明:
        若矩阵未包含该场景/运行类型，默认 functional=all, perf=true, accuracy=true。
    """

    by_scn = matrix.get(scenario_id, {})
    by_type = by_scn.get(run_type, {})
    functional = by_type.get("functional", "all")
    perf = bool(by_type.get("perf", True))
    accuracy = bool(by_type.get("accuracy", True))
    return {"functional": functional, "perf": perf, "accuracy": accuracy}


def discover_scenarios(dir_path: Path) -> List[Path]:
    """扫描目录下的所有场景 YAML 文件。

    参数:
        dir_path: 目录路径。
    返回:
        场景文件路径列表，按文件名排序。
    """

    files = sorted([p for p in dir_path.glob("*.yaml") if p.is_file()])
    return files

