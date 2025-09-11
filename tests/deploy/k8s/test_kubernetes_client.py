"""K8s 资源发现与探活单元测试（基于 mock）。"""

from __future__ import annotations

from types import SimpleNamespace as NS

import pytest

import vllm_cibench.deploy.k8s.kubernetes_client as kc


class FakeCoreV1Api:
    def __init__(self, node_ip: str = "10.0.0.1", node_port: int = 30000):
        self._node_ip = node_ip
        self._node_port = node_port

    # Simulate list_node return
    def list_node(self):  # pragma: no cover - trivial glue
        addr = NS(type="InternalIP", address=self._node_ip)
        node = NS(status=NS(addresses=[addr]))
        return NS(items=[node])

    # Simulate read_namespaced_service
    def read_namespaced_service(
        self, name: str, namespace: str
    ):  # pragma: no cover - trivial glue
        port = NS(name="http", node_port=self._node_port)
        spec = NS(ports=[port])
        return NS(spec=spec)


def test_discover_service_base_url(monkeypatch: pytest.MonkeyPatch):
    """应能从 K8s 资源解析出 http://<node_ip>:<node_port>/v1。"""

    monkeypatch.setattr(
        kc, "create_core_v1_api", lambda incluster=False: FakeCoreV1Api()
    )
    url = kc.discover_service_base_url(
        namespace="default",
        service_name="infer-vllm",
        port_name="http",
        path_prefix="/v1",
    )
    assert url == "http://10.0.0.1:30000/v1"


def test_wait_k8s_service_ready(monkeypatch: pytest.MonkeyPatch):
    """探活逻辑应调用 wait_for_http 并返回其结果。"""

    monkeypatch.setattr(
        kc, "create_core_v1_api", lambda incluster=False: FakeCoreV1Api()
    )
    called = {"url": None}

    def fake_wait(url: str, timeout_s: float, max_attempts: int) -> bool:
        called["url"] = url
        return True

    monkeypatch.setattr(kc, "wait_for_http", fake_wait)
    ok = kc.wait_k8s_service_ready(
        "default", "infer-vllm", port_name="http", path_prefix="/v1"
    )
    assert ok is True
    assert called["url"] == "http://10.0.0.1:30000/v1"
