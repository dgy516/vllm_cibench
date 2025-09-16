"""K8s 资源清理工具。

提供基于 `kubectl delete -f` 的最小化清理能力，便于在编排结束后
按场景释放已部署的资源（可选行为）。
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Optional


def delete_resources(yaml_path: Path, namespace: Optional[str] = None) -> bool:
    """删除指定 YAML 中定义的 K8s 资源。

    参数:
        yaml_path: 资源定义的 YAML 文件路径。
        namespace: 可选命名空间；不提供则遵循 YAML 中配置。

    返回值:
        bool: True 表示删除命令已执行（不保证资源实际存在）；失败返回 False。

    副作用:
        调用 `kubectl delete`；若 `kubectl` 不存在或删除失败，将捕获异常并返回 False。
    """

    try:
        if not yaml_path.exists():
            return False
        cmd = ["kubectl", "delete", "-f", str(yaml_path)]
        if namespace:
            cmd = ["kubectl", "delete", "-n", str(namespace), "-f", str(yaml_path)]
        subprocess.run(cmd, check=False)
        return True
    except Exception:
        return False
