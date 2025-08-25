"""
入参模型: 定义基础五个动作的 Pydantic v2 参数约束。
Why: 在 LLM → 执行器 的边界先做强校验, 拦截坏数据, 统一错误结构。
包含:
- OpenUrlParams { url: AnyHttpUrl }
- WaitForParams { selector: NonEmptyStr, timeout_ms?: TimeoutMs<=60000 }
- ClickParams { selector: NonEmptyStr }
- TypeParams { selector: NonEmptyStr, text: TextLimited<=4000 }
- ExtractTextParams { selector: NonEmptyStr }
"""
# @file purpose: Define parameter schemas for core actions using Pydantic v2.

from typing import Annotated

from pydantic import AnyHttpUrl, BaseModel, Field

# 辅助约束类型
NonEmptyStr = Annotated[str, Field(min_length=1, strip_whitespace=True)]
TimeoutMs = Annotated[int, Field(gt=0, le=60_000)]
TextLimited = Annotated[str, Field(max_length=4000)]


class OpenUrlParams(BaseModel):
    """Parameters for open_url action."""

    url: AnyHttpUrl


class WaitForParams(BaseModel):
    """Parameters for wait_for action."""

    selector: NonEmptyStr
    timeout_ms: TimeoutMs | None = 10_000


class ClickParams(BaseModel):
    """Parameters for click action."""

    selector: NonEmptyStr


class TypeParams(BaseModel):
    """Parameters for type action."""

    selector: NonEmptyStr
    text: TextLimited


class ExtractTextParams(BaseModel):
    """Parameters for extract_text action."""

    selector: NonEmptyStr
