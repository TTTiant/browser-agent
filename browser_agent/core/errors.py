"""
定义项目级异常类型，统一错误语义与捕获边界。
- BrowserAgentError: 所有自定义异常的基类
- ActionExecutionError: 动作执行期错误（元素缺失、超时、脚本异常等）
- PolicyViolationError: 策略/白名单/权限相关错误
- TimeoutError: 统一的超时异常（避免混用内置 TimeoutError）
"""
# @file purpose: Define error taxonomy for browser-agent.


class BrowserAgentError(Exception):
    """Base class for all custom errors in browser-agent."""


class ActionExecutionError(BrowserAgentError):
    """Raised when an action fails to execute."""


class PolicyViolationError(BrowserAgentError):
    """Raised when a policy/allowlist/rate-limit is violated."""


class TimeoutError(BrowserAgentError):
    """Raised on operation timeout within the agent."""
