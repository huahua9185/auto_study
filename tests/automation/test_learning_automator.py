"""
学习自动化器测试模块

测试视频学习控制功能，包括：
- 视频播放控制 
- 进度监控
- 异常处理和恢复
- 断点续播功能
- 会话管理
"""

import pytest
import asyncio
import json
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch, call
from datetime import datetime, timedelta

from src.auto_study.automation.learning_automator import (
    LearningAutomator, VideoController, ProgressMonitor,
    PlaybackState, PlaybackStatus, LearningMode, LearningSession
)


class TestPlaybackState:
    """播放状态数据类测试"""
    
    def test_playback_state_creation(self):
        """测试播放状态创建"""
        state = PlaybackState(course_id="course_001")
        
        assert state.course_id == "course_001"
        assert state.video_id == ""
        assert state.position == 0.0
        assert state.duration == 0.0
        assert state.status == PlaybackStatus.STOPPED
        assert state.completed is False
        assert state.last_played is None
        assert state.play_count == 0
        assert state.error_count == 0
        assert state.session_id == ""
    
    def test_playback_state_to_dict(self):
        """测试播放状态序列化"""
        now = datetime.now()
        state = PlaybackState(
            course_id="course_001",
            video_id="video_001",
            position=120.5,
            duration=600.0,
            status=PlaybackStatus.PLAYING,
            completed=False,
            last_played=now,
            play_count=3,
            error_count=1,
            session_id="session_123"
        )
        
        data = state.to_dict()
        
        assert data["course_id"] == "course_001"
        assert data["video_id"] == "video_001"
        assert data["position"] == 120.5
        assert data["duration"] == 600.0
        assert data["status"] == "playing"
        assert data["completed"] is False
        assert data["last_played"] == now.isoformat()
        assert data["play_count"] == 3
        assert data["error_count"] == 1
        assert data["session_id"] == "session_123"
    
    def test_playback_state_from_dict(self):
        """测试播放状态反序列化"""
        now = datetime.now()
        data = {
            "course_id": "course_001",
            "video_id": "video_001", 
            "position": 120.5,
            "duration": 600.0,
            "status": "paused",
            "completed": False,
            "last_played": now.isoformat(),
            "play_count": 3,
            "error_count": 1,
            "session_id": "session_123"
        }
        
        state = PlaybackState.from_dict(data)
        
        assert state.course_id == "course_001"
        assert state.video_id == "video_001"
        assert state.position == 120.5
        assert state.duration == 600.0
        assert state.status == PlaybackStatus.PAUSED
        assert state.completed is False
        assert abs((state.last_played - now).total_seconds()) < 1
        assert state.play_count == 3
        assert state.error_count == 1
        assert state.session_id == "session_123"
    
    def test_playback_state_progress_calculation(self):
        """测试进度计算"""
        state = PlaybackState(course_id="course_001", position=30.0, duration=120.0)
        assert state.progress == 25.0
        
        # 测试边界情况
        state.duration = 0.0
        assert state.progress == 0.0


class TestLearningSession:
    """学习会话测试"""
    
    def test_learning_session_creation(self):
        """测试学习会话创建"""
        session = LearningSession(course_id="course_001", mode=LearningMode.NORMAL)
        
        assert session.course_id == "course_001"
        assert session.mode == LearningMode.NORMAL
        assert isinstance(session.session_id, str)
        assert len(session.session_id) == 36  # UUID长度
        assert isinstance(session.start_time, datetime)
        assert session.end_time is None
        assert session.total_time == 0.0
        assert session.videos_completed == 0
        assert session.errors == []
        assert session.progress_snapshots == []
    
    def test_learning_session_to_dict(self):
        """测试会话序列化"""
        session = LearningSession(course_id="course_001", mode=LearningMode.FAST)
        session.end_time = datetime.now()
        session.total_time = 3600.0
        session.videos_completed = 5
        session.errors = ["网络错误", "播放卡死"]
        
        data = session.to_dict()
        
        assert data["course_id"] == "course_001"
        assert data["mode"] == "fast"
        assert data["session_id"] == session.session_id
        assert "start_time" in data
        assert "end_time" in data
        assert data["total_time"] == 3600.0
        assert data["videos_completed"] == 5
        assert data["errors"] == ["网络错误", "播放卡死"]
        assert data["progress_snapshots"] == []


class TestVideoController:
    """视频控制器测试"""
    
    @pytest.fixture
    def mock_page(self):
        """模拟页面对象"""
        page = AsyncMock()
        page.url = "https://edu.nxgbjy.org.cn/course/test"
        page.evaluate = AsyncMock()
        page.locator = MagicMock()
        page.keyboard = AsyncMock()
        page.wait_for_timeout = AsyncMock()
        return page
    
    @pytest.fixture
    def video_controller(self, mock_page):
        """创建视频控制器"""
        return VideoController(mock_page)
    
    @pytest.mark.asyncio
    async def test_detect_video_player_javascript(self, video_controller, mock_page):
        """测试通过JavaScript检测视频播放器"""
        # 模拟找到video元素
        mock_page.evaluate.return_value = True
        
        result = await video_controller.detect_video_player()
        
        assert result is True
        mock_page.evaluate.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_detect_video_player_ui_elements(self, video_controller, mock_page):
        """测试通过UI元素检测视频播放器"""
        # JavaScript检测失败
        mock_page.evaluate.return_value = False
        
        # UI元素检测成功
        mock_locator = MagicMock()
        mock_locator.count = AsyncMock(return_value=1)
        mock_page.locator.return_value = mock_locator
        
        result = await video_controller.detect_video_player()
        
        assert result is True
        mock_page.locator.assert_called()
    
    @pytest.mark.asyncio
    async def test_detect_video_player_not_found(self, video_controller, mock_page):
        """测试视频播放器未找到"""
        mock_page.evaluate.return_value = False
        
        mock_locator = MagicMock()
        mock_locator.count = AsyncMock(return_value=0)
        mock_page.locator.return_value = mock_locator
        
        result = await video_controller.detect_video_player()
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_play_video_javascript_success(self, video_controller, mock_page):
        """测试通过JavaScript播放视频成功"""
        mock_page.evaluate.return_value = True
        
        result = await video_controller.play()
        
        assert result is True
        # 验证调用了JavaScript播放方法
        mock_page.evaluate.assert_called()
    
    @pytest.mark.asyncio
    async def test_play_video_ui_fallback(self, video_controller, mock_page):
        """测试播放视频UI按钮回退方案"""
        # JavaScript播放失败
        mock_page.evaluate.side_effect = [False, True]  # 第二次evaluate用于检测播放状态
        
        # UI按钮点击成功
        mock_locator = MagicMock()
        mock_locator.count = AsyncMock(return_value=1)
        mock_locator.click = AsyncMock()
        mock_page.locator.return_value = mock_locator
        
        result = await video_controller.play()
        
        assert result is True
        mock_locator.click.assert_called()
    
    @pytest.mark.asyncio
    async def test_play_video_keyboard_fallback(self, video_controller, mock_page):
        """测试播放视频键盘回退方案"""
        # JavaScript和UI按钮都失败
        mock_page.evaluate.side_effect = [False, False, True]  # 最后一次用于验证播放状态
        
        mock_locator = MagicMock()
        mock_locator.count = AsyncMock(return_value=0)
        mock_page.locator.return_value = mock_locator
        
        result = await video_controller.play()
        
        assert result is True
        # 验证按下了空格键
        mock_page.keyboard.press.assert_called_with('Space')
    
    @pytest.mark.asyncio
    async def test_pause_video(self, video_controller, mock_page):
        """测试暂停视频"""
        mock_page.evaluate.return_value = True
        
        result = await video_controller.pause()
        
        assert result is True
        mock_page.evaluate.assert_called()
    
    @pytest.mark.asyncio
    async def test_get_current_time(self, video_controller, mock_page):
        """测试获取当前播放时间"""
        mock_page.evaluate.return_value = 120.5
        
        current_time = await video_controller.get_current_time()
        
        assert current_time == 120.5
    
    @pytest.mark.asyncio
    async def test_get_duration(self, video_controller, mock_page):
        """测试获取视频总时长"""
        mock_page.evaluate.return_value = 600.0
        
        duration = await video_controller.get_duration()
        
        assert duration == 600.0
    
    @pytest.mark.asyncio
    async def test_seek_to_position(self, video_controller, mock_page):
        """测试跳转到指定位置"""
        mock_page.evaluate.return_value = True
        
        result = await video_controller.seek_to(120.0)
        
        assert result is True
        # 验证JavaScript调用参数
        call_args = mock_page.evaluate.call_args[0][0]
        assert "120" in call_args
    
    @pytest.mark.asyncio
    async def test_is_playing_detection(self, video_controller, mock_page):
        """测试播放状态检测"""
        # 测试正在播放
        mock_page.evaluate.return_value = True
        is_playing = await video_controller.is_playing()
        assert is_playing is True
        
        # 测试未播放
        mock_page.evaluate.return_value = False
        is_playing = await video_controller.is_playing()
        assert is_playing is False
    
    @pytest.mark.asyncio
    async def test_is_ended_detection(self, video_controller, mock_page):
        """测试播放结束检测"""
        mock_page.evaluate.return_value = True
        is_ended = await video_controller.is_ended()
        assert is_ended is True
    
    @pytest.mark.asyncio
    async def test_get_playback_status(self, video_controller, mock_page):
        """测试获取播放状态"""
        # 模拟正在播放状态
        mock_page.evaluate.side_effect = [False, True, False]  # ended, playing, paused
        
        status = await video_controller.get_playback_status()
        assert status == PlaybackStatus.PLAYING


class TestProgressMonitor:
    """进度监控器测试"""
    
    @pytest.fixture
    def mock_video_controller(self):
        """模拟视频控制器"""
        controller = AsyncMock()
        controller.get_current_time = AsyncMock(return_value=60.0)
        controller.get_duration = AsyncMock(return_value=300.0)
        controller.is_playing = AsyncMock(return_value=True)
        controller.is_ended = AsyncMock(return_value=False)
        controller.get_playback_status = AsyncMock(return_value=PlaybackStatus.PLAYING)
        return controller
    
    @pytest.fixture
    def progress_monitor(self, mock_video_controller):
        """创建进度监控器"""
        return ProgressMonitor(mock_video_controller, check_interval=0.1)  # 快速测试
    
    @pytest.mark.asyncio
    async def test_progress_monitor_init(self, progress_monitor):
        """测试进度监控器初始化"""
        assert progress_monitor.video_controller is not None
        assert progress_monitor.check_interval == 0.1
        assert progress_monitor.is_monitoring is False
        assert progress_monitor.callbacks == []
        assert progress_monitor._last_position == 0.0
        assert progress_monitor._stuck_count == 0
    
    def test_add_progress_callback(self, progress_monitor):
        """测试添加进度回调"""
        callback = MagicMock()
        progress_monitor.add_progress_callback(callback)
        
        assert len(progress_monitor.callbacks) == 1
        assert callback in progress_monitor.callbacks
    
    def test_remove_progress_callback(self, progress_monitor):
        """测试移除进度回调"""
        callback = MagicMock()
        progress_monitor.add_progress_callback(callback)
        progress_monitor.remove_progress_callback(callback)
        
        assert len(progress_monitor.callbacks) == 0
        assert callback not in progress_monitor.callbacks
    
    @pytest.mark.asyncio
    async def test_start_monitoring(self, progress_monitor, mock_video_controller):
        """测试开始监控"""
        # 启动监控
        await progress_monitor.start_monitoring()
        
        # 等待一小段时间让监控运行
        await asyncio.sleep(0.2)
        
        assert progress_monitor.is_monitoring is True
        
        # 验证视频控制器被调用
        mock_video_controller.get_current_time.assert_called()
        mock_video_controller.get_duration.assert_called()
        mock_video_controller.get_playback_status.assert_called()
        
        # 停止监控
        await progress_monitor.stop_monitoring()
    
    @pytest.mark.asyncio
    async def test_stop_monitoring(self, progress_monitor):
        """测试停止监控"""
        await progress_monitor.start_monitoring()
        await progress_monitor.stop_monitoring()
        
        assert progress_monitor.is_monitoring is False
    
    @pytest.mark.asyncio
    async def test_progress_callback_triggered(self, progress_monitor, mock_video_controller):
        """测试进度回调触发"""
        callback = MagicMock()
        progress_monitor.add_progress_callback(callback)
        
        # 启动监控
        await progress_monitor.start_monitoring()
        await asyncio.sleep(0.2)
        await progress_monitor.stop_monitoring()
        
        # 验证回调被调用
        callback.assert_called()
        
        # 检查回调参数
        call_args = callback.call_args[0]
        assert len(call_args) == 4  # position, duration, status, progress
        position, duration, status, progress = call_args
        assert position == 60.0
        assert duration == 300.0
        assert status == PlaybackStatus.PLAYING
        assert progress == 20.0  # 60/300 * 100
    
    @pytest.mark.asyncio
    async def test_stuck_detection(self, progress_monitor, mock_video_controller):
        """测试播放卡死检测"""
        # 模拟播放位置不变
        mock_video_controller.get_current_time.return_value = 60.0
        mock_video_controller.is_playing.return_value = True
        
        callback = MagicMock()
        progress_monitor.add_progress_callback(callback)
        
        # 启动监控，让它运行足够长时间触发卡死检测
        await progress_monitor.start_monitoring()
        await asyncio.sleep(1.0)  # 运行1秒
        await progress_monitor.stop_monitoring()
        
        # 检查是否检测到卡死
        assert progress_monitor._stuck_count > 0
    
    @pytest.mark.asyncio
    async def test_completion_detection(self, progress_monitor, mock_video_controller):
        """测试播放完成检测"""
        # 模拟视频播放完成
        mock_video_controller.is_ended.return_value = True
        mock_video_controller.get_playback_status.return_value = PlaybackStatus.COMPLETED
        
        callback = MagicMock()
        progress_monitor.add_progress_callback(callback)
        
        await progress_monitor.start_monitoring()
        await asyncio.sleep(0.2)
        await progress_monitor.stop_monitoring()
        
        # 验证状态为完成
        call_args = callback.call_args[0]
        status = call_args[2]
        assert status == PlaybackStatus.COMPLETED


class TestLearningAutomator:
    """学习自动化器测试"""
    
    @pytest.fixture
    def temp_data_dir(self):
        """临时数据目录"""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)
    
    @pytest.fixture
    def mock_page(self):
        """模拟页面对象"""
        page = AsyncMock()
        page.url = "https://edu.nxgbjy.org.cn/course/test"
        page.goto = AsyncMock()
        page.wait_for_load_state = AsyncMock()
        page.evaluate = AsyncMock()
        page.locator = MagicMock()
        page.keyboard = AsyncMock()
        return page
    
    @pytest.fixture
    def mock_anti_detection(self):
        """模拟反检测模块"""
        anti_detection = MagicMock()
        anti_detection.random_delay = AsyncMock()
        anti_detection.human_like_mouse_move = AsyncMock()
        anti_detection.random_scroll = AsyncMock()
        return anti_detection
    
    @pytest.fixture
    def learning_automator(self, mock_page, mock_anti_detection, temp_data_dir):
        """创建学习自动化器"""
        return LearningAutomator(
            page=mock_page,
            anti_detection=mock_anti_detection,
            data_dir=temp_data_dir
        )
    
    def test_learning_automator_init(self, learning_automator, temp_data_dir):
        """测试学习自动化器初始化"""
        assert learning_automator.page is not None
        assert learning_automator.anti_detection is not None
        assert learning_automator.data_dir == temp_data_dir
        assert learning_automator.video_controller is not None
        assert learning_automator.progress_monitor is not None
        assert learning_automator.current_session is None
        assert learning_automator.playback_state is None
        
        # 检查数据目录结构
        assert (temp_data_dir / "playback").exists()
        assert (temp_data_dir / "sessions").exists()
    
    def test_save_and_load_playback_state(self, learning_automator, temp_data_dir):
        """测试播放状态保存和加载"""
        # 创建播放状态
        state = PlaybackState(
            course_id="course_001",
            video_id="video_001",
            position=120.0,
            duration=600.0,
            status=PlaybackStatus.PAUSED
        )
        
        # 保存状态
        learning_automator._save_playback_state(state)
        
        # 验证文件被创建
        state_file = temp_data_dir / "playback" / "course_001.json"
        assert state_file.exists()
        
        # 加载状态
        loaded_state = learning_automator._load_playback_state("course_001")
        
        assert loaded_state.course_id == "course_001"
        assert loaded_state.video_id == "video_001"
        assert loaded_state.position == 120.0
        assert loaded_state.duration == 600.0
        assert loaded_state.status == PlaybackStatus.PAUSED
    
    def test_load_nonexistent_playback_state(self, learning_automator):
        """测试加载不存在的播放状态"""
        state = learning_automator._load_playback_state("nonexistent_course")
        assert state is None
    
    def test_save_and_load_learning_session(self, learning_automator, temp_data_dir):
        """测试学习会话保存和加载"""
        # 创建学习会话
        session = LearningSession(course_id="course_001", mode=LearningMode.NORMAL)
        session.videos_completed = 3
        session.total_time = 1800.0
        
        # 保存会话
        learning_automator._save_learning_session(session)
        
        # 验证文件被创建
        session_file = temp_data_dir / "sessions" / f"{session.session_id}.json"
        assert session_file.exists()
        
        # 加载会话
        loaded_session = learning_automator._load_learning_session(session.session_id)
        
        assert loaded_session.course_id == "course_001"
        assert loaded_session.mode == LearningMode.NORMAL
        assert loaded_session.videos_completed == 3
        assert loaded_session.total_time == 1800.0
    
    @pytest.mark.asyncio
    async def test_start_video_learning_new_course(self, learning_automator, mock_page):
        """测试开始新课程学习"""
        # 模拟视频检测和播放成功
        mock_page.evaluate.side_effect = [
            True,  # 检测到视频播放器
            True,  # 播放成功
            600.0,  # 视频时长
            0.0    # 当前播放位置
        ]
        
        result = await learning_automator.start_video_learning("course_001", resume=False)
        
        assert result is True
        assert learning_automator.current_session is not None
        assert learning_automator.current_session.course_id == "course_001"
        assert learning_automator.playback_state is not None
        assert learning_automator.playback_state.course_id == "course_001"
    
    @pytest.mark.asyncio
    async def test_start_video_learning_with_resume(self, learning_automator, mock_page, temp_data_dir):
        """测试断点续播学习"""
        # 先创建一个保存的播放状态
        saved_state = PlaybackState(
            course_id="course_001",
            video_id="video_001",
            position=120.0,
            duration=600.0,
            status=PlaybackStatus.PAUSED
        )
        learning_automator._save_playback_state(saved_state)
        
        # 模拟视频控制成功
        mock_page.evaluate.side_effect = [
            True,  # 检测到视频播放器
            True,  # 跳转到断点位置成功
            True,  # 播放成功
            600.0, # 视频时长
            120.0  # 当前播放位置
        ]
        
        result = await learning_automator.start_video_learning("course_001", resume=True)
        
        assert result is True
        assert learning_automator.playback_state.position == 120.0
        
        # 验证跳转到断点位置
        call_args_list = mock_page.evaluate.call_args_list
        seek_call = None
        for call in call_args_list:
            if "currentTime" in str(call[0][0]):
                seek_call = call
                break
        assert seek_call is not None
    
    @pytest.mark.asyncio
    async def test_start_video_learning_no_video_player(self, learning_automator, mock_page):
        """测试未检测到视频播放器"""
        # 模拟未检测到视频播放器
        mock_page.evaluate.return_value = False
        mock_locator = MagicMock()
        mock_locator.count = AsyncMock(return_value=0)
        mock_page.locator.return_value = mock_locator
        
        result = await learning_automator.start_video_learning("course_001")
        
        assert result is False
        assert learning_automator.current_session is None
        assert learning_automator.playback_state is None
    
    @pytest.mark.asyncio
    async def test_pause_learning(self, learning_automator, mock_page):
        """测试暂停学习"""
        # 先开始学习
        mock_page.evaluate.side_effect = [True, True, 600.0, 60.0]  # 初始设置
        await learning_automator.start_video_learning("course_001")
        
        # 重置mock以便测试暂停
        mock_page.evaluate.side_effect = [True, 120.0]  # 暂停成功, 当前位置
        
        result = await learning_automator.pause_learning()
        
        assert result is True
        assert learning_automator.playback_state.status == PlaybackStatus.PAUSED
    
    @pytest.mark.asyncio
    async def test_resume_learning(self, learning_automator, mock_page):
        """测试恢复学习"""
        # 先开始学习并暂停
        mock_page.evaluate.side_effect = [True, True, 600.0, 60.0]
        await learning_automator.start_video_learning("course_001")
        
        mock_page.evaluate.side_effect = [True, 120.0]
        await learning_automator.pause_learning()
        
        # 测试恢复
        mock_page.evaluate.side_effect = [True, 120.0]  # 播放成功, 当前位置
        
        result = await learning_automator.resume_learning()
        
        assert result is True
        assert learning_automator.playback_state.status == PlaybackStatus.PLAYING
    
    @pytest.mark.asyncio
    async def test_stop_learning(self, learning_automator, mock_page):
        """测试停止学习"""
        # 先开始学习
        mock_page.evaluate.side_effect = [True, True, 600.0, 60.0]
        await learning_automator.start_video_learning("course_001")
        
        # 重置mock以便测试停止
        mock_page.evaluate.side_effect = [True, 180.0]  # 暂停成功, 最终位置
        
        await learning_automator.stop_learning()
        
        assert learning_automator.current_session.end_time is not None
        assert learning_automator.playback_state.status == PlaybackStatus.STOPPED
    
    def test_handle_network_error_recovery(self, learning_automator):
        """测试网络错误恢复"""
        # 创建网络错误
        error = Exception("Network timeout")
        
        recovery_action = learning_automator._handle_playback_error("network_error", str(error))
        
        # 网络错误应该触发页面刷新恢复
        assert recovery_action == "refresh_page"
    
    def test_handle_playback_stuck_recovery(self, learning_automator):
        """测试播放卡死恢复"""
        recovery_action = learning_automator._handle_playback_error("playback_stuck", "播放位置长时间未变化")
        
        # 播放卡死应该触发重新播放
        assert recovery_action == "restart_playback"
    
    def test_handle_buffering_timeout_recovery(self, learning_automator):
        """测试缓冲超时恢复"""
        recovery_action = learning_automator._handle_playback_error("buffering_timeout", "缓冲超时")
        
        # 缓冲超时应该触发等待重试
        assert recovery_action == "wait_and_retry"
    
    def test_handle_unknown_error_recovery(self, learning_automator):
        """测试未知错误处理"""
        recovery_action = learning_automator._handle_playback_error("unknown_error", "未知错误")
        
        # 未知错误应该记录并跳过
        assert recovery_action == "log_and_skip"
    
    def test_get_learning_statistics_no_session(self, learning_automator):
        """测试获取学习统计（无会话）"""
        stats = learning_automator.get_learning_statistics()
        
        assert stats["current_session"] is None
        assert stats["playback_state"] is None
        assert stats["total_learning_time"] == 0
        assert stats["videos_completed"] == 0
        assert stats["error_count"] == 0
    
    @pytest.mark.asyncio
    async def test_get_learning_statistics_with_session(self, learning_automator, mock_page):
        """测试获取学习统计（有会话）"""
        # 开始学习会话
        mock_page.evaluate.side_effect = [True, True, 600.0, 180.0]
        await learning_automator.start_video_learning("course_001")
        
        # 模拟一些学习活动
        learning_automator.current_session.videos_completed = 2
        learning_automator.current_session.total_time = 1800.0
        learning_automator.current_session.errors = ["网络错误"]
        learning_automator.playback_state.error_count = 1
        
        stats = learning_automator.get_learning_statistics()
        
        assert stats["current_session"]["course_id"] == "course_001"
        assert stats["playback_state"]["course_id"] == "course_001"
        assert stats["total_learning_time"] == 1800.0
        assert stats["videos_completed"] == 2
        assert stats["error_count"] == 1
        assert len(stats["session_errors"]) == 1
    
    @pytest.mark.asyncio
    async def test_learning_mode_normal(self, learning_automator, mock_page):
        """测试正常学习模式"""
        mock_page.evaluate.side_effect = [True, True, 600.0, 0.0]
        
        result = await learning_automator.start_video_learning(
            "course_001", mode=LearningMode.NORMAL
        )
        
        assert result is True
        assert learning_automator.current_session.mode == LearningMode.NORMAL
    
    @pytest.mark.asyncio
    async def test_learning_mode_fast(self, learning_automator, mock_page):
        """测试快速学习模式"""
        mock_page.evaluate.side_effect = [True, True, 600.0, 0.0]
        
        result = await learning_automator.start_video_learning(
            "course_001", mode=LearningMode.FAST
        )
        
        assert result is True
        assert learning_automator.current_session.mode == LearningMode.FAST
        
        # 快速模式应该调整播放速度
        # 验证播放速度设置调用
        speed_call = None
        for call in mock_page.evaluate.call_args_list:
            if "playbackRate" in str(call[0][0]):
                speed_call = call
                break
        # 在这个测试中，可能需要调整mock设置来验证播放速度调用
    
    @pytest.mark.asyncio
    async def test_concurrent_learning_prevention(self, learning_automator, mock_page):
        """测试防止并发学习"""
        # 开始第一个学习会话
        mock_page.evaluate.side_effect = [True, True, 600.0, 0.0] * 10
        await learning_automator.start_video_learning("course_001")
        
        # 尝试开始第二个学习会话
        result = await learning_automator.start_video_learning("course_002")
        
        # 应该失败，因为已经有活动会话
        assert result is False
        assert learning_automator.current_session.course_id == "course_001"
    
    def test_progress_callback_integration(self, learning_automator):
        """测试进度回调集成"""
        callback_called = False
        callback_args = None
        
        def progress_callback(position, duration, status, progress):
            nonlocal callback_called, callback_args
            callback_called = True
            callback_args = (position, duration, status, progress)
        
        # 添加进度回调
        learning_automator.add_progress_callback(progress_callback)
        
        # 验证回调已添加
        assert len(learning_automator.progress_monitor.callbacks) == 1
        
        # 模拟进度更新
        learning_automator.progress_monitor.callbacks[0](120.0, 600.0, PlaybackStatus.PLAYING, 20.0)
        
        assert callback_called is True
        assert callback_args == (120.0, 600.0, PlaybackStatus.PLAYING, 20.0)
    
    @pytest.mark.asyncio
    async def test_error_recovery_workflow(self, learning_automator, mock_page):
        """测试错误恢复工作流"""
        # 开始学习
        mock_page.evaluate.side_effect = [True, True, 600.0, 60.0]
        await learning_automator.start_video_learning("course_001")
        
        # 模拟错误和恢复
        learning_automator.playback_state.error_count = 0
        
        # 触发网络错误
        learning_automator._handle_playback_error("network_error", "Connection timeout")
        
        assert learning_automator.playback_state.error_count == 1
        assert len(learning_automator.current_session.errors) == 1
        assert "network_error" in learning_automator.current_session.errors[0]
    
    def test_data_persistence_atomic_operations(self, learning_automator, temp_data_dir):
        """测试数据持久化的原子操作"""
        # 创建播放状态
        state = PlaybackState(course_id="course_001", position=120.0)
        
        # 保存状态
        learning_automator._save_playback_state(state)
        
        # 验证临时文件不存在（原子操作完成）
        temp_file = temp_data_dir / "playback" / "course_001.json.tmp"
        assert not temp_file.exists()
        
        # 验证目标文件存在
        target_file = temp_data_dir / "playback" / "course_001.json"
        assert target_file.exists()
    
    @pytest.mark.asyncio
    async def test_cleanup_on_exit(self, learning_automator, mock_page):
        """测试退出时的资源清理"""
        # 开始学习
        mock_page.evaluate.side_effect = [True, True, 600.0, 60.0]
        await learning_automator.start_video_learning("course_001")
        
        # 手动触发清理
        await learning_automator.cleanup()
        
        # 验证进度监控已停止
        assert learning_automator.progress_monitor.is_monitoring is False
        
        # 验证会话已保存并清理
        assert learning_automator.current_session.end_time is not None