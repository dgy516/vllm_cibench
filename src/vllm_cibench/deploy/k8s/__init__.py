"""Kubernetes 部署与探活适配层。"""

from __future__ import annotations

from typing import Dict, Optional, Tuple

from ...config import Scenario


def k8s_params_from_scenario(
    s: Scenario,
) -> Tuple[str, str, str, str, Optional[int]]:
    """从场景提取 K8s 访问所需参数。"

    参数:
        s: 场景对象，``raw.k8s`` 中包含 ``namespace``/``service_name``/``port_name``/``node_port``。

    返回值:
        Tuple[str, str, str, str, Optional[int]]: ``(namespace, service_name, port_name, path_prefix, node_port)``。

    副作用:
        无。
    """

    k8s: Dict[str, object] = s.raw.get("k8s", {}) or {}
    namespace = str(k8s.get("namespace", "default"))
    service_name = str(k8s.get("service_name"))
    port_name = str(k8s.get("port_name", "http"))
    node_port_val = k8s.get("node_port")
    node_port = int(node_port_val) if isinstance(node_port_val, (int, str)) else None
    path_prefix = str(s.raw.get("base_path", "/v1"))
    if not service_name:
        raise KeyError("scenario.k8s.service_name is required for k8s modes")
    return namespace, service_name, port_name, path_prefix, node_port
