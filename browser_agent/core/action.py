"""
定义动作层的数据契约与执行结果。
- ActionResult: 统一结构化返回（是否入记忆、是否成功、错误信息等）
- ActionSpec: 供 Planner 产出的“下一步动作”规范（name + args）
"""
# @file purpose: Define action data contracts.

from typing import Any

from pydantic import BaseModel, Field


class ActionResult(BaseModel):
    extracted_content: Any | None = Field(
        default=None, description="Structured output for reasoning."
    )
    include_in_memory: bool = Field(
        default=False, description="Whether to store into short-term memory."
    )
    success: bool = Field(default=True, description="Whether the action succeeded.")
    error: str | None = Field(default=None, description="Error message if failed.")


class ActionSpec(BaseModel):
    name: str = Field(..., description="Registered action name.")
    args: dict[str, Any] = Field(
        default_factory=dict, description="Validated parameters for the action."
    )
