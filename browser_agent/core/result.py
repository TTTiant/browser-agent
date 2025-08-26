"""
结构化的动作返回值，用于向上层（编排/CLI）汇报执行结果。
"""
# @file purpose: Define ActionResult model for action outputs.

from __future__ import annotations

from typing import Any, Optional
from pydantic import BaseModel, Field


class ActionResult(BaseModel):
    """
    统一的动作返回值：
    - ok: 是否成功
    - extracted_content: 动作抽取到的文本（仅 extract_text 用，其他动作通常为 None）
    - include_in_memory: 是否建议把 extracted_content 写入记忆/上下文
    - meta: 其它诊断信息（耗时/selector/URL/截图路径等），便于日志与回放
    """

    ok: bool = True
    extracted_content: Optional[str] = None
    include_in_memory: bool = False
    meta: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def success(cls, **meta: Any) -> "ActionResult":
        return cls(ok=True, meta=meta)

    @classmethod
    def failure(cls, **meta: Any) -> "ActionResult":
        return cls(ok=False, meta=meta)
