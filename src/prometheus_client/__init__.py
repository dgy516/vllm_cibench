"""Prometheus 客户端最小实现。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Mapping


@dataclass
class CollectorRegistry:
    """简单的指标注册表。"""

    metrics: Dict[str, float] = field(default_factory=dict)


@dataclass
class Gauge:
    """可设置数值的 Gauge 指标。"""

    name: str
    documentation: str
    registry: CollectorRegistry

    def set(self, value: float) -> None:
        """记录指标值。"""

        self.registry.metrics[self.name] = float(value)


def push_to_gateway(
    url: str, job: str, registry: CollectorRegistry, grouping_key: Mapping[str, str]
) -> None:  # noqa: D401
    """伪造的推送函数，实际不执行网络请求。"""

    return None
