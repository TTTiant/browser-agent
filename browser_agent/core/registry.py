"""
简单动作注册表与装饰器，供上层统一调度。
"""
# @file purpose: Provide action registry and decorator.

from collections.abc import Awaitable, Callable
from typing import Any

ActionFn = Callable[..., Awaitable[Any]]
_REGISTRY: dict[str, ActionFn] = {}


def action(name: str) -> Callable[[ActionFn], ActionFn]:
    def deco(fn: ActionFn) -> ActionFn:
        _REGISTRY[name] = fn
        return fn

    return deco


def get_action(name: str) -> ActionFn:
    try:
        return _REGISTRY[name]
    except KeyError as err:
        raise KeyError(f"Action not registered: {name}") from err
