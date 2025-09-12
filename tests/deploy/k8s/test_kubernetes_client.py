"""K8s 资源发现与探活单元测试（基于 mock）。"""

from __future__ import annotations

from types import SimpleNamespace as NS
from typing import Dict

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
    called: Dict[str, str] = {"url": ""}

    def fake_wait(url: str, timeout_s: float, max_attempts: int) -> bool:
        called["url"] = url
        return True

    monkeypatch.setattr(kc, "wait_for_http", fake_wait)
    ok = kc.wait_k8s_service_ready(
        "default", "infer-vllm", port_name="http", path_prefix="/v1"
    )
    assert ok is True
    assert called["url"] == "http://10.0.0.1:30000/v1"


def test_discover_with_node_port_override(monkeypatch: pytest.MonkeyPatch):
    """显式 node_port 时不应调用 Service 端口解析。"""

    monkeypatch.setattr(
        kc, "create_core_v1_api", lambda incluster=False: FakeCoreV1Api()
    )
    called = {"svc": 0}

    def fake_get_port(*_a, **_kw):
        called["svc"] += 1
        return 30000

    monkeypatch.setattr(kc, "_get_service_node_port", fake_get_port)
    url = kc.discover_service_base_url(
        namespace="default",
        service_name="infer-vllm",
        node_port=31000,
    )
    assert url == "http://10.0.0.1:31000/v1"
    assert called["svc"] == 0


class NoServiceApi(FakeCoreV1Api):
    def read_namespaced_service(self, name: str, namespace: str):  # pragma: no cover
        raise Exception("not found")


def test_service_missing(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        kc, "create_core_v1_api", lambda incluster=False: NoServiceApi()
    )
    with pytest.raises(RuntimeError, match="Service not found"):
        kc.discover_service_base_url("d", "svc")


class PortMismatchApi(FakeCoreV1Api):
    def read_namespaced_service(self, name: str, namespace: str):  # pragma: no cover
        port = NS(name="metrics", node_port=30000)
        spec = NS(ports=[port])
        return NS(spec=spec)


def test_port_name_mismatch(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        kc, "create_core_v1_api", lambda incluster=False: PortMismatchApi()
    )
    with pytest.raises(RuntimeError, match="port name 'http' not found"):
        kc.discover_service_base_url("d", "svc", port_name="http")


class NoNodeApi(FakeCoreV1Api):
    def list_node(self):  # pragma: no cover
        return NS(items=[])


def test_no_node(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(kc, "create_core_v1_api", lambda incluster=False: NoNodeApi())
    with pytest.raises(RuntimeError, match="No node InternalIP found"):
        kc.discover_service_base_url("d", "svc")
