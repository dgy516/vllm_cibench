"""极简 YAML 解析器。

仅支持键值对与缩进表示的嵌套字典，满足仓库配置文件的需求。"""

from __future__ import annotations

from typing import Any, Dict, Iterable, Tuple


def _parse_scalar(val: str) -> Any:
    """解析单个标量。"""

    import json

    val = val.strip()
    if not val:
        return ""
    try:
        return json.loads(val)
    except Exception:
        return val


def safe_load(stream: Iterable[str] | str) -> Dict[str, Any]:
    """解析简单 YAML 为字典。

    参数:
        stream: 字符串或可迭代文本行。

    返回值:
        dict: 解析后的字典结构。

    副作用:
        无。
    """

    if isinstance(stream, str):
        lines = stream.splitlines()
    else:
        lines = list(stream)

    root: Dict[str, Any] = {}
    stack: list[Tuple[int, Dict[str, Any]]] = [(0, root)]

    for raw in lines:
        line = raw.rstrip()
        if not line or line.lstrip().startswith("#"):
            continue
        indent = len(line) - len(line.lstrip())
        key, _, val_part = line.lstrip().partition(":")
        key = key.strip()
        val_part = val_part.strip()
        while indent < stack[-1][0]:
            stack.pop()
        current = stack[-1][1]
        if not val_part:
            new_dict: Dict[str, Any] = {}
            current[key] = new_dict
            stack.append((indent + 2, new_dict))
        else:
            current[key] = _parse_scalar(val_part)
    return root
