"""
定义项目级异常类型，统一错误语义与捕获边界。
- BrowserAgentError: 所有自定义异常的基类
- ActionExecutionError: 动作执行期错误（元素缺失、超时、脚本异常等）
- PolicyViolationError: 策略/白名单/权限相关错误
- TimeoutError: 统一的超时异常（避免混用内置 TimeoutError）
"""
# @file purpose: Define error taxonomy for browser-agent.

from typing import Any


class BrowserAgentError(Exception):
    """Base class for all custom errors in browser-agent."""


class ActionExecutionError(BrowserAgentError):
    """
    Raised when an action fails to execute.
    动作执行期错误（元素缺失、超时、脚本异常等）。
    统一封装上下文，便于 CLI/编排层打印一致的信息与诊断。
    """

    def __init__(
        self,
        action: str,
        message: str,
        *,
        selector: str | None = None,
        url: str | None = None,
        details: dict[str, Any] | None = None,
        cause: BaseException | None = None,
    ) -> None:
        super().__init__(message)
        self.action: str = action
        self.selector: str | None = selector
        self.url: str | None = url
        self.details: dict[str, Any] = details or {}
        self.cause: BaseException | None = cause

    def __str__(self) -> str:
        parts = [f"[{self.action}] {super().__str__()}"]
        if self.selector:
            parts.append(f"selector={self.selector}")
        if self.url:
            parts.append(f"url={self.url}")
        if self.details:
            # 简单序列化 details，避免过长
            kv = ", ".join(f"{k}={v!r}" for k, v in self.details.items())
            parts.append(f"details={{ {kv} }}")
        return " | ".join(parts)


class PolicyViolationError(BrowserAgentError):
    """Raised when a policy/allowlist/rate-limit is violated."""


class TimeoutError(BrowserAgentError):
    """Raised on operation timeout within the agent."""
