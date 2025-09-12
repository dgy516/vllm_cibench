"""极简 Typer 替代实现。"""

from __future__ import annotations

from typing import Any, Callable, Optional


class BadParameter(Exception):
    """参数错误异常。"""


class Context:
    """命令上下文，仅保留 `invoked_subcommand` 属性。"""

    def __init__(self) -> None:
        self.invoked_subcommand: Optional[str] = None


def Option(default: Any, *_args: Any, **_kwargs: Any) -> Any:
    """返回默认值的占位实现。"""

    return default


def echo(text: str) -> None:
    """打印文本到标准输出。"""

    print(text)


class Typer:
    """最小化 Typer 应用对象。"""

    def __init__(self, help: str | None = None) -> None:
        self.help = help

    def __call__(self, *_args: Any, **_kw: Any) -> None:
        """调用应用时不执行任何操作。"""

        return None

    def callback(
        self, **_kw: Any
    ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        """装饰器占位实现。"""

        def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
            return fn

        return decorator

    def command(
        self, name: str | None = None
    ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        """注册命令的装饰器占位实现。"""

        def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
            return fn

        return decorator
