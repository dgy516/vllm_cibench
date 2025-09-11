"""K8s Hybrid 部署适配（通过 NodePort 直连）。

基于场景配置中的 `k8s.{namespace, service_name, port_name}` 字段，
发现可访问的 `base_url` 并进行健康探活。
"""

from __future__ import annotations

from typing import Dict, Tuple

from ...config import Scenario
from .kubernetes_client import discover_service_base_url, wait_k8s_service_ready


def _k8s_params_from_scenario(s: Scenario) -> Tuple[str, str, str, str]:
    """从场景对象提取 K8s 必需参数。

    参数:
        s: `Scenario` 对象，`raw.k8s` 中包含 `namespace/service_name/port_name`。

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
        raise KeyError("scenario.k8s.service_name is required for k8s-hybrid mode")
    return namespace, service_name, port_name, path_prefix


def discover_base_url(s: Scenario, incluster: bool = False) -> str:
    """根据场景发现可访问的基础 URL。

    参数:
        s: 场景对象。
        incluster: 是否使用集群内配置。

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
    """等待服务就绪（HTTP 200）。

    参数:
        s: 场景对象。
        timeout_s: 总超时（秒）。
        interval_s: 轮询间隔（秒）。
        incluster: 是否使用集群内配置。

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
