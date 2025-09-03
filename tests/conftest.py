"""
pytest配置和共享fixture
"""

import pytest
import asyncio
import os
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock


@pytest.fixture(scope="session")
def event_loop():
    """创建事件循环"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_page():
    """模拟Playwright页面对象"""
    page = AsyncMock()
    page.url = "https://edu.nxgbjy.org.cn"
    page.title.return_value = "测试页面"
    page.goto = AsyncMock()
    page.wait_for_load_state = AsyncMock()
    page.fill = AsyncMock()
    page.click = AsyncMock()
    page.locator = MagicMock()
    page.screenshot = AsyncMock()
    page.content = AsyncMock(return_value="<html></html>")
    page.mouse = AsyncMock()
    page.keyboard = AsyncMock()
    page.viewport_size = AsyncMock(return_value={'width': 1920, 'height': 1080})
    
    return page


@pytest.fixture
def mock_browser():
    """模拟浏览器对象"""
    browser = AsyncMock()
    browser.new_context = AsyncMock()
    browser.close = AsyncMock()
    return browser


@pytest.fixture
def mock_context():
    """模拟浏览器上下文"""
    context = AsyncMock()
    context.new_page = AsyncMock()
    context.close = AsyncMock()
    return context


@pytest.fixture
def test_data_dir(tmp_path):
    """临时测试数据目录"""
    data_dir = tmp_path / "test_data"
    data_dir.mkdir()
    return data_dir


@pytest.fixture
def sample_course():
    """示例课程数据"""
    from src.auto_study.automation.course_manager import Course
    
    return Course(
        id="test_course_001",
        title="测试课程",
        status="not_started",
        progress=0.0,
        duration=60,
        url="https://edu.nxgbjy.org.cn/course/test_course_001",
        is_required=True
    )


@pytest.fixture
def sample_courses():
    """示例课程列表"""
    from src.auto_study.automation.course_manager import Course
    
    return [
        Course(
            id="course_001",
            title="必修课程1",
            status="not_started",
            progress=0.0,
            duration=60,
            url="https://edu.nxgbjy.org.cn/course/course_001",
            is_required=True
        ),
        Course(
            id="course_002",
            title="选修课程1",
            status="in_progress",
            progress=50.0,
            duration=90,
            url="https://edu.nxgbjy.org.cn/course/course_002",
            is_required=False
        ),
        Course(
            id="course_003",
            title="已完成课程",
            status="completed",
            progress=100.0,
            duration=120,
            url="https://edu.nxgbjy.org.cn/course/course_003",
            is_required=False
        )
    ]


@pytest.fixture
def mock_settings():
    """模拟设置"""
    settings = MagicMock()
    settings.browser.headless = True
    settings.browser.width = 1920
    settings.browser.height = 1080
    settings.login.max_retries = 3
    settings.login.retry_delay = 1
    settings.learning.check_interval = 10
    settings.system.log_level = "DEBUG"
    settings.get_user_credentials.return_value = ("test_user", "test_pass")
    settings.validate_config.return_value = True
    return settings


@pytest.fixture(autouse=True)
def clean_test_files():
    """自动清理测试文件"""
    yield
    # 测试后清理
    test_files = [
        "test_courses.json",
        "test_log.log",
        "test_screenshot.png"
    ]
    
    for file in test_files:
        if os.path.exists(file):
            os.remove(file)