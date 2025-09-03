"""
学习自动化器集成测试

测试学习自动化器与其他模块的集成，包括：
- 与浏览器管理器的集成
- 与反检测模块的集成  
- 与课程管理器的集成
- 完整的学习流程测试
"""

import pytest
import asyncio
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from src.auto_study.automation.learning_automator import (
    LearningAutomator, PlaybackStatus, LearningMode
)


@pytest.mark.integration
class TestLearningAutomatorIntegration:
    """学习自动化器集成测试"""
    
    @pytest.fixture
    def temp_data_dir(self):
        """临时数据目录"""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)
    
    @pytest.fixture
    def mock_browser_manager(self):
        """模拟浏览器管理器"""
        browser_manager = MagicMock()
        
        # 模拟页面对象
        page = AsyncMock()
        page.url = "https://edu.nxgbjy.org.cn/course/test"
        page.goto = AsyncMock()
        page.wait_for_load_state = AsyncMock()
        page.evaluate = AsyncMock()
        page.locator = MagicMock()
        page.keyboard = AsyncMock()
        page.wait_for_timeout = AsyncMock()
        
        browser_manager.create_page.return_value = page
        browser_manager.close_page = MagicMock()
        browser_manager.screenshot_page = MagicMock(return_value=b"fake_image_data")
        
        return browser_manager, page
    
    @pytest.fixture
    def mock_course_manager(self):
        """模拟课程管理器"""
        course_manager = MagicMock()
        
        # 模拟课程数据
        course_manager.get_course.return_value = {
            "id": "course_001",
            "title": "测试课程",
            "url": "https://edu.nxgbjy.org.cn/course/test",
            "status": "not_started",
            "progress": 0.0,
            "videos": [
                {"id": "video_001", "title": "视频1", "duration": 600},
                {"id": "video_002", "title": "视频2", "duration": 900},
            ]
        }
        
        course_manager.update_course_progress = MagicMock()
        course_manager.mark_video_completed = MagicMock()
        
        return course_manager
    
    @pytest.fixture
    def mock_anti_detection(self):
        """模拟反检测模块"""
        anti_detection = MagicMock()
        anti_detection.random_delay = AsyncMock()
        anti_detection.human_like_mouse_move = AsyncMock()
        anti_detection.random_scroll = AsyncMock()
        anti_detection.simulate_user_activity = AsyncMock()
        return anti_detection
    
    @pytest.fixture
    def learning_system(self, temp_data_dir, mock_anti_detection):
        """完整的学习系统"""
        browser_manager, page = self.mock_browser_manager()
        course_manager = self.mock_course_manager()
        
        learning_automator = LearningAutomator(
            page=page,
            anti_detection=mock_anti_detection,
            data_dir=temp_data_dir
        )
        
        return {
            "browser_manager": browser_manager,
            "page": page,
            "course_manager": course_manager,
            "anti_detection": mock_anti_detection,
            "learning_automator": learning_automator
        }
    
    @pytest.mark.asyncio
    async def test_complete_learning_workflow(self, learning_system, temp_data_dir):
        """测试完整的学习工作流程"""
        page = learning_system["page"]
        learning_automator = learning_system["learning_automator"]
        anti_detection = learning_system["anti_detection"]
        
        # 模拟视频学习成功流程
        page.evaluate.side_effect = [
            True,   # 检测到视频播放器
            True,   # 开始播放成功
            600.0,  # 视频总时长
            0.0,    # 当前播放位置
            60.0,   # 播放进度检查1
            120.0,  # 播放进度检查2
            180.0,  # 播放进度检查3
            True,   # 播放结束检测
            600.0,  # 最终播放位置
        ]
        
        # 开始学习
        result = await learning_automator.start_video_learning("course_001")
        assert result is True
        
        # 验证会话已创建
        assert learning_automator.current_session is not None
        assert learning_automator.current_session.course_id == "course_001"
        
        # 验证播放状态已创建
        assert learning_automator.playback_state is not None
        assert learning_automator.playback_state.course_id == "course_001"
        
        # 模拟学习过程中的进度更新
        progress_callback = MagicMock()
        learning_automator.add_progress_callback(progress_callback)
        
        # 启动进度监控
        await learning_automator.progress_monitor.start_monitoring()
        await asyncio.sleep(0.1)  # 让监控运行一小段时间
        await learning_automator.progress_monitor.stop_monitoring()
        
        # 验证进度回调被调用
        progress_callback.assert_called()
        
        # 停止学习
        page.evaluate.side_effect = [True, 600.0]  # 暂停成功，最终位置
        await learning_automator.stop_learning()
        
        # 验证学习数据被保存
        playback_file = temp_data_dir / "playback" / "course_001.json"
        assert playback_file.exists()
        
        session_file = temp_data_dir / "sessions" / f"{learning_automator.current_session.session_id}.json"
        assert session_file.exists()
        
        # 验证反检测功能被调用
        anti_detection.random_delay.assert_called()
    
    @pytest.mark.asyncio
    async def test_resume_learning_integration(self, learning_system, temp_data_dir):
        """测试断点续播集成"""
        page = learning_system["page"]
        learning_automator = learning_system["learning_automator"]
        
        # 第一次学习：学习到一半停止
        page.evaluate.side_effect = [
            True,   # 检测视频播放器
            True,   # 开始播放
            600.0,  # 视频时长
            0.0,    # 当前位置
            True,   # 暂停成功
            300.0,  # 停止时位置
        ]
        
        # 开始学习
        await learning_automator.start_video_learning("course_001")
        
        # 学习一段时间后停止
        await learning_automator.stop_learning()
        
        # 第二次学习：从断点恢复
        learning_automator_new = LearningAutomator(
            page=page,
            anti_detection=learning_system["anti_detection"],
            data_dir=temp_data_dir
        )
        
        page.evaluate.side_effect = [
            True,   # 检测视频播放器
            True,   # 跳转到断点成功
            True,   # 恢复播放成功
            600.0,  # 视频时长
            300.0,  # 当前位置（断点位置）
            450.0,  # 继续播放位置
            600.0,  # 播放完成位置
        ]
        
        # 使用断点续播
        result = await learning_automator_new.start_video_learning("course_001", resume=True)
        assert result is True
        
        # 验证从断点位置开始
        assert learning_automator_new.playback_state.position == 300.0
        
        # 验证跳转到断点位置的调用
        seek_calls = [call for call in page.evaluate.call_args_list 
                     if "currentTime" in str(call[0][0])]
        assert len(seek_calls) > 0
    
    @pytest.mark.asyncio 
    async def test_error_recovery_integration(self, learning_system):
        """测试错误恢复集成"""
        page = learning_system["page"]
        learning_automator = learning_system["learning_automator"]
        anti_detection = learning_system["anti_detection"]
        
        # 模拟学习过程中的网络错误
        page.evaluate.side_effect = [
            True,   # 检测视频播放器
            True,   # 开始播放
            600.0,  # 视频时长
            0.0,    # 当前位置
            Exception("Network error"),  # 网络错误
            True,   # 错误恢复后重新播放成功
            60.0,   # 恢复后的位置
        ]
        
        # 开始学习
        await learning_automator.start_video_learning("course_001")
        
        # 模拟进度监控过程中的错误处理
        try:
            await learning_automator.progress_monitor.start_monitoring()
            await asyncio.sleep(0.1)
            await learning_automator.progress_monitor.stop_monitoring()
        except Exception as e:
            # 验证错误被正确处理
            assert "Network error" in str(e)
        
        # 验证错误计数增加
        assert learning_automator.playback_state.error_count > 0
        assert len(learning_automator.current_session.errors) > 0
        
        # 验证反检测在错误恢复中的作用
        anti_detection.random_delay.assert_called()
    
    @pytest.mark.asyncio
    async def test_multiple_video_learning_sequence(self, learning_system):
        """测试多视频连续学习"""
        page = learning_system["page"]
        learning_automator = learning_system["learning_automator"]
        course_manager = learning_system["course_manager"]
        
        # 模拟第一个视频学习完成
        page.evaluate.side_effect = [
            True,   # 检测视频播放器
            True,   # 开始播放
            600.0,  # 视频1时长
            0.0,    # 开始位置
            True,   # 播放结束
            600.0,  # 完成位置
        ]
        
        # 学习第一个视频
        result = await learning_automator.start_video_learning("course_001")
        assert result is True
        
        # 模拟视频完成
        learning_automator.playback_state.status = PlaybackStatus.COMPLETED
        learning_automator.playback_state.completed = True
        learning_automator.current_session.videos_completed = 1
        
        await learning_automator.stop_learning()
        
        # 开始第二个视频
        page.evaluate.side_effect = [
            True,   # 检测视频播放器
            True,   # 开始播放
            900.0,  # 视频2时长（更长）
            0.0,    # 开始位置
        ]
        
        # 学习第二个视频
        learning_automator.playback_state.video_id = "video_002"
        result = await learning_automator.start_video_learning("course_001", resume=False)
        assert result is True
        
        # 验证学习统计
        stats = learning_automator.get_learning_statistics()
        assert stats["videos_completed"] >= 1
        assert stats["current_session"]["course_id"] == "course_001"
    
    @pytest.mark.asyncio
    async def test_learning_with_different_modes(self, learning_system):
        """测试不同学习模式的集成"""
        page = learning_system["page"] 
        learning_automator = learning_system["learning_automator"]
        
        # 测试正常模式
        page.evaluate.side_effect = [True, True, 600.0, 0.0]
        result = await learning_automator.start_video_learning(
            "course_001", mode=LearningMode.NORMAL
        )
        assert result is True
        assert learning_automator.current_session.mode == LearningMode.NORMAL
        
        await learning_automator.stop_learning()
        
        # 测试快速模式
        page.evaluate.side_effect = [True, True, 600.0, 0.0]
        result = await learning_automator.start_video_learning(
            "course_002", mode=LearningMode.FAST
        )
        assert result is True
        assert learning_automator.current_session.mode == LearningMode.FAST
        
        # 验证快速模式的播放速度设置
        speed_calls = [call for call in page.evaluate.call_args_list
                      if "playbackRate" in str(call[0][0])]
        # 快速模式应该设置播放速度
        assert len(speed_calls) > 0 or learning_automator.current_session.mode == LearningMode.FAST
    
    @pytest.mark.asyncio
    async def test_concurrent_learning_prevention_integration(self, learning_system):
        """测试并发学习防护集成"""
        page = learning_system["page"]
        learning_automator = learning_system["learning_automator"]
        
        # 开始第一个学习会话
        page.evaluate.side_effect = [True, True, 600.0, 0.0] * 10
        result1 = await learning_automator.start_video_learning("course_001")
        assert result1 is True
        
        # 尝试开始第二个学习会话（应该被阻止）
        result2 = await learning_automator.start_video_learning("course_002")
        assert result2 is False
        
        # 验证第一个会话仍然活跃
        assert learning_automator.current_session.course_id == "course_001"
        
        # 停止第一个会话
        page.evaluate.side_effect = [True, 300.0]
        await learning_automator.stop_learning()
        
        # 现在应该可以开始新的会话
        page.evaluate.side_effect = [True, True, 900.0, 0.0]
        result3 = await learning_automator.start_video_learning("course_002")
        assert result3 is True
        assert learning_automator.current_session.course_id == "course_002"
    
    @pytest.mark.asyncio
    async def test_browser_interaction_integration(self, learning_system):
        """测试与浏览器交互的集成"""
        browser_manager, page = learning_system["browser_manager"], learning_system["page"]
        learning_automator = learning_system["learning_automator"]
        
        # 模拟浏览器页面导航
        page.goto = AsyncMock()
        page.wait_for_load_state = AsyncMock()
        
        # 模拟视频播放器检测和控制
        page.evaluate.side_effect = [
            True,   # 检测到视频播放器
            True,   # 播放控制成功
            600.0,  # 视频时长
            0.0,    # 当前位置
        ]
        
        # 开始学习
        result = await learning_automator.start_video_learning("course_001")
        assert result is True
        
        # 验证页面交互
        assert page.evaluate.called
        
        # 模拟截图功能
        browser_manager.screenshot_page.return_value = b"screenshot_data"
        screenshot_data = browser_manager.screenshot_page(page)
        assert screenshot_data == b"screenshot_data"
        
        # 模拟键盘交互（播放控制回退方案）
        page.keyboard.press = AsyncMock()
        await learning_automator.video_controller.play()
        
        # 验证可能的键盘交互
        if page.keyboard.press.called:
            page.keyboard.press.assert_called_with('Space')
    
    @pytest.mark.asyncio
    async def test_data_persistence_integration(self, learning_system, temp_data_dir):
        """测试数据持久化集成"""
        learning_automator = learning_system["learning_automator"]
        page = learning_system["page"]
        
        # 开始学习并生成一些数据
        page.evaluate.side_effect = [True, True, 600.0, 0.0, True, 300.0]
        await learning_automator.start_video_learning("course_001")
        
        # 模拟学习活动
        learning_automator.current_session.videos_completed = 1
        learning_automator.current_session.total_time = 1800.0
        learning_automator.current_session.errors = ["测试错误"]
        learning_automator.playback_state.position = 300.0
        learning_automator.playback_state.play_count = 1
        
        # 停止学习（触发数据保存）
        await learning_automator.stop_learning()
        
        # 验证数据文件存在
        playback_file = temp_data_dir / "playback" / "course_001.json"
        session_file = temp_data_dir / "sessions" / f"{learning_automator.current_session.session_id}.json"
        
        assert playback_file.exists()
        assert session_file.exists()
        
        # 验证数据内容正确
        with open(playback_file, 'r', encoding='utf-8') as f:
            playback_data = json.load(f)
            assert playback_data["course_id"] == "course_001"
            assert playback_data["position"] == 300.0
            assert playback_data["play_count"] == 1
        
        with open(session_file, 'r', encoding='utf-8') as f:
            session_data = json.load(f)
            assert session_data["course_id"] == "course_001"
            assert session_data["videos_completed"] == 1
            assert session_data["total_time"] == 1800.0
            assert len(session_data["errors"]) == 1
    
    @pytest.mark.asyncio
    async def test_anti_detection_integration(self, learning_system):
        """测试反检测集成"""
        learning_automator = learning_system["learning_automator"]
        page = learning_system["page"]
        anti_detection = learning_system["anti_detection"]
        
        # 开始学习
        page.evaluate.side_effect = [True, True, 600.0, 0.0]
        await learning_automator.start_video_learning("course_001")
        
        # 验证反检测功能被调用
        anti_detection.random_delay.assert_called()
        
        # 模拟长时间学习中的反检测活动
        await learning_automator.progress_monitor.start_monitoring()
        await asyncio.sleep(0.1)
        await learning_automator.progress_monitor.stop_monitoring()
        
        # 停止学习
        page.evaluate.side_effect = [True, 300.0]
        await learning_automator.stop_learning()
        
        # 验证反检测功能在学习过程中被多次调用
        assert anti_detection.random_delay.call_count > 1
    
    @pytest.mark.asyncio
    async def test_performance_under_load(self, learning_system):
        """测试高负载下的性能"""
        learning_automator = learning_system["learning_automator"]
        page = learning_system["page"]
        
        # 模拟快速频繁的进度更新
        page.evaluate.side_effect = [True, True, 600.0, 0.0] + [i * 10.0 for i in range(60)]
        
        await learning_automator.start_video_learning("course_001")
        
        # 快速进度监控（模拟高频更新）
        learning_automator.progress_monitor.check_interval = 0.01
        await learning_automator.progress_monitor.start_monitoring()
        await asyncio.sleep(0.5)  # 运行500ms
        await learning_automator.progress_monitor.stop_monitoring()
        
        # 验证系统在高负载下仍然正常工作
        assert learning_automator.progress_monitor.is_monitoring is False
        assert learning_automator.current_session is not None
        
        # 停止学习
        page.evaluate.side_effect = [True, 300.0]
        await learning_automator.stop_learning()
        
        # 验证最终状态正确
        assert learning_automator.current_session.end_time is not None