"""K8s PD（Pipeline/Prefill/Decode 分离）部署适配。

从场景配置中解析 PD 专属参数（scheduler/prefill/decode），
并基于统一的 Service 发现逻辑获取对外 `base_url` 与探活能力。
"""

from __future__ import annotations

# isort: skip_file

from typing import Dict, Tuple

from ...config import Scenario
from .kubernetes_client import discover_service_base_url, wait_k8s_service_ready


def _k8s_params_from_scenario(s: Scenario) -> Tuple[str, str, str, str]:
    """提取用于服务发现的 K8s 参数。

    参数:
        s: 场景对象，`raw.k8s` 中包含 `namespace/service_name/port_name`。

    返回值:
        (namespace, service_name, port_name, path_prefix)

    副作用:
        无。
    """

    k8s: Dict[str, object] = s.raw.get("k8s", {}) or {}
    namespace = str(k8s.get("namespace", "default"))
    service_name = str(k8s.get("service_name"))
    port_name = str(k8s.get("port_name", "http"))
    path_prefix = str(s.raw.get("base_path", "/v1"))
    if not service_name:
        raise KeyError("scenario.k8s.service_name is required for k8s-pd mode")
    return namespace, service_name, port_name, path_prefix


def _pd_params_from_scenario(s: Scenario) -> Dict[str, str]:
    """提取 PD 参数（scheduler/prefill/decode）。

    参数:
        s: 场景对象，`raw.pd` 中包含三段参数字符串。

    返回值:
        dict: {'scheduler_params': str, 'prefill_params': str, 'decode_params': str}

    副作用:
        无。
    """

    pd_cfg: Dict[str, object] = s.raw.get("pd", {}) or {}
    out = {
        "scheduler_params": str(pd_cfg.get("scheduler_params", "")),
        "prefill_params": str(pd_cfg.get("prefill_params", "")),
        "decode_params": str(pd_cfg.get("decode_params", "")),
    }
    return out


def build_pd_args(s: Scenario) -> Dict[str, str]:
    """返回 PD 模式的三段参数，供启动/文档化使用。

    参数:
        s: 场景对象。

    返回值:
        dict: 同 `_pd_params_from_scenario` 的输出。

    副作用:
        无。
    """

    return _pd_params_from_scenario(s)


def discover_base_url(s: Scenario, incluster: bool = False) -> str:
    """根据场景发现可访问的基础 URL（NodePort + InternalIP）。

    参数:
        s: 场景对象。
        incluster: 是否使用容器内配置。

    返回值:
        str: 形如 `http://<node_ip>:<node_port>/v1`。

    副作用:
        调用 K8s API 进行资源发现。
    """

    ns, svc, port, prefix = _k8s_params_from_scenario(s)
    return discover_service_base_url(
        namespace=ns,
        service_name=svc,
        port_name=port,
        path_prefix=prefix,
        incluster=incluster,
    )


def wait_ready(
    s: Scenario,
    timeout_s: float = 60.0,
    interval_s: float = 1.0,
    incluster: bool = False,
) -> bool:
    """等待 PD 服务就绪（HTTP 200）。

    参数:
        s: 场景对象。
        timeout_s: 总超时（秒）。
        interval_s: 轮询间隔（秒）。
        incluster: 是否使用容器内配置。

    返回值:
        bool: 就绪返回 True；否则 False。

    副作用:
        调用 K8s API 与 HTTP 探活。
    """

    ns, svc, port, prefix = _k8s_params_from_scenario(s)
    return wait_k8s_service_ready(
        namespace=ns,
        service_name=svc,
        port_name=port,
        path_prefix=prefix,
        timeout_s=timeout_s,
        interval_s=interval_s,
        incluster=incluster,
    )
