"""Kubernetes 资源发现与探活工具。

提供：
- 读取 kube 配置并创建 CoreV1Api 客户端
- 基于 Service 名称与端口名解析 NodePort
- 获取任意节点的 InternalIP
- 组合得到服务的基础 URL，并进行健康探活
"""

from __future__ import annotations

from typing import Any, Optional

from ...clients.http import wait_for_http


def create_core_v1_api(incluster: bool = False) -> Any:
    """创建 `CoreV1Api` 客户端。

    参数:
        incluster: 是否使用 in-cluster 配置；为 False 时使用本地 kubeconfig。

    返回值:
        kubernetes.client.CoreV1Api 实例。

    副作用:
        读取 kube 配置文件或集群内服务帐号配置。
    """

    # 延迟导入以便测试时可 monkeypatch
    from kubernetes import client, config  # type: ignore[import-untyped]

    if incluster:
        config.load_incluster_config()
    else:
        config.load_kube_config()
    return client.CoreV1Api()


def _get_node_internal_ip(api: Any) -> str:
    """获取任一节点的 InternalIP。

    参数:
        api: CoreV1Api 实例。

    返回值:
        str: 节点 InternalIP。

    副作用:
        调用 K8s API `list_node`。
    """

    try:
        nodes = api.list_node().items
    except Exception as exc:  # pragma: no cover - K8s 客户端异常
        raise RuntimeError("failed to list nodes") from exc
    for n in nodes:
        addrs = getattr(n.status, "addresses", [])
        for addr in addrs:
            a_type = getattr(addr, "type", None) or addr.get("type")
            a_val = getattr(addr, "address", None) or addr.get("address")
            if a_type == "InternalIP" and a_val:
                return str(a_val)
    raise RuntimeError("No node InternalIP found")


def _get_service_node_port(
    api: Any, namespace: str, service_name: str, port_name: str
) -> int:
    """读取 Service 的指定端口名对应的 NodePort。

    参数:
        api: CoreV1Api 实例。
        namespace: 命名空间。
        service_name: Service 名称。
        port_name: 端口名（如 `http`）。

    返回值:
        int: NodePort 数值。

    副作用:
        调用 K8s API `read_namespaced_service`。
    """

    try:
        svc = api.read_namespaced_service(name=service_name, namespace=namespace)
    except Exception as exc:  # pragma: no cover - K8s 客户端异常
        raise RuntimeError(f"Service not found: {namespace}/{service_name}") from exc
    ports = getattr(svc.spec, "ports", []) or []
    for p in ports:
        pname = getattr(p, "name", None) or getattr(p, "port_name", None)
        nport = getattr(p, "node_port", None) or getattr(p, "nodePort", None)
        if pname == port_name and nport:
            return int(nport)
    raise RuntimeError(
        f"port name '{port_name}' not found in service {namespace}/{service_name}"
    )


def discover_service_base_url(
    namespace: str,
    service_name: str,
    port_name: str = "http",
    path_prefix: str = "/v1",
    incluster: bool = False,
    node_port: Optional[int] = None,
) -> str:
    """发现 K8s Service 的可访问基础 URL（NodeIP:NodePort）。

    参数:
        namespace: 命名空间。
        service_name: Service 名称。
        port_name: Service 暴露的端口名（默认 `http`）。
        path_prefix: 路径前缀，默认 `/v1`。
        incluster: 是否使用容器内配置。

    返回值:
        str: 形如 `http://<node_ip>:<node_port><path_prefix>`。

    副作用:
        调用 K8s API 进行资源查询。
    """

    api = create_core_v1_api(incluster=incluster)
    node_ip = _get_node_internal_ip(api)
    if node_port is None:
        node_port = _get_service_node_port(api, namespace, service_name, port_name)
    prefix = path_prefix if path_prefix.startswith("/") else f"/{path_prefix}"
    return f"http://{node_ip}:{int(node_port)}{prefix}"


def wait_k8s_service_ready(
    namespace: str,
    service_name: str,
    port_name: str = "http",
    path_prefix: str = "/v1",
    timeout_s: float = 60.0,
    interval_s: float = 1.0,
    incluster: bool = False,
    node_port: Optional[int] = None,
) -> bool:
    """等待 K8s Service 就绪（HTTP 200）。

    参数:
        namespace: 命名空间。
        service_name: Service 名称。
        port_name: Service 暴露的端口名（默认 `http`）。
        path_prefix: 路径前缀，默认 `/v1`。
        timeout_s: 总超时（秒）。
        interval_s: 轮询间隔（秒）。
        incluster: 是否使用容器内配置。

    返回值:
        bool: 在超时前返回 200 则 True，否则 False。

    副作用:
        调用 K8s API 与发起 HTTP 请求。
    """

    url = discover_service_base_url(
        namespace=namespace,
        service_name=service_name,
        port_name=port_name,
        path_prefix=path_prefix,
        incluster=incluster,
        node_port=node_port,
    )
    attempts = max(1, int(timeout_s / max(0.001, interval_s)))
    return wait_for_http(url, timeout_s=interval_s, max_attempts=attempts)
