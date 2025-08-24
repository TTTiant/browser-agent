"""最小化测试：验证包能被导入，CLI 可运行（占位用）。"""
# @file purpose: Minimal smoke test.


def test_imports() -> None:
    import browser_agent.core.action as action  # noqa: F401
    import browser_agent.core.settings as settings  # noqa: F401
    import browser_agent.io.playwright_driver as driver  # noqa: F401


def test_true() -> None:
    assert True
