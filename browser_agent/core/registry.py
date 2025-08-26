"""
动作注册表与元数据:
- 以 name 作为键注册动作函数
- 绑定 params_model (Pydantic v2) 用于参数校验
- 提供 validate_spec() 在执行前做强校验
"""
# @file purpose: Provide action registry, metadata, and spec validation.

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Dict, Optional, Tuple, Type

from pydantic import BaseModel, TypeAdapter, ValidationError

from .action import ActionSpec

# 动作函数的标准签名（异步）
ActionFn = Callable[..., Awaitable[Any]]


@dataclass(frozen=True)
class ActionMeta:
    """动作元信息：名称 + 绑定的入参模型（可选）"""

    name: str
    params_model: Optional[Type[BaseModel]] = None


# 全局注册表：动作实现 & 元数据
_REGISTRY: Dict[str, ActionFn] = {}
_META: Dict[str, ActionMeta] = {}


def action(
    name: str, *, params_model: Optional[Type[BaseModel]] = None
) -> Callable[[ActionFn], ActionFn]:
    """
    装饰器：注册动作函数及其参数模型。
    用法示例（等你实现动作时用）：
        @action("open_url", params_model=OpenUrlParams)
        async def open_url(...): ...
    """

    def deco(fn: ActionFn) -> ActionFn:
        _REGISTRY[name] = fn
        _META[name] = ActionMeta(name=name, params_model=params_model)
        return fn

    return deco


def register(name: str, fn: ActionFn, *, params_model: Optional[Type[BaseModel]] = None) -> None:
    """非装饰器形式注册，便于动态装配或测试。"""
    _REGISTRY[name] = fn
    _META[name] = ActionMeta(name=name, params_model=params_model)


def get_action(name: str) -> ActionFn:
    try:
        return _REGISTRY[name]
    except KeyError as e:
        raise KeyError(f"Action not registered: {name}") from e


def get_meta(name: str) -> ActionMeta:
    try:
        return _META[name]
    except KeyError as e:
        raise KeyError(f"Action not registered (no metadata): {name}") from e


def list_actions() -> Dict[str, ActionMeta]:
    """返回一个浅拷贝，便于调试/展示。"""
    return dict(_META)


def validate_spec(spec: ActionSpec) -> Tuple[ActionMeta, Optional[BaseModel]]:
    """
    在执行前对 ActionSpec 做强校验：
    1) 动作是否已注册（否则 KeyError）
    2) 若绑定了 params_model，则用其校验 args（失败抛 ValidationError）
    3) 成功时返回 (ActionMeta, 已解析的 params_model 实例 | None)
    """
    meta = get_meta(spec.name)

    if meta.params_model is None:
        # 未声明参数模型：允许任意 args（或你也可改成必须为空）
        return meta, None

    adapter = TypeAdapter(meta.params_model)  # v2 推荐的校验入口
    params_obj = adapter.validate_python(spec.args)
    return meta, params_obj


# 仅用于测试：重置注册表
def _reset_registry_for_tests() -> None:
    _REGISTRY.clear()
    _META.clear()
