"""
学习自动化核心

实现视频学习的智能控制，包括播放控制、进度监控、异常处理和断点续播
"""

import json
import asyncio
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Callable, Dict, Any
from dataclasses import dataclass
from enum import Enum

from ..utils.logger import logger


class PlaybackStatus(Enum):
    """播放状态枚举"""
    STOPPED = "stopped"
    PLAYING = "playing"
    PAUSED = "paused"
    BUFFERING = "buffering"
    ERROR = "error"
    COMPLETED = "completed"


class LearningMode(Enum):
    """学习模式"""
    NORMAL = "normal"    # 正常学习模式
    FAST = "fast"        # 快速学习模式


@dataclass
class PlaybackState:
    """播放状态数据模型"""
    course_id: str
    video_id: str = ""
    position: float = 0.0  # 播放位置(秒)
    duration: float = 0.0  # 视频总时长(秒)
    status: PlaybackStatus = PlaybackStatus.STOPPED
    completed: bool = False
    last_played: Optional[datetime] = None
    play_count: int = 0
    error_count: int = 0
    session_id: str = ""
    
    @property
    def progress(self) -> float:
        """计算播放进度百分比"""
        if self.duration == 0:
            return 0.0
        return (self.position / self.duration) * 100.0
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        data = {
            "course_id": self.course_id,
            "video_id": self.video_id,
            "position": self.position,
            "duration": self.duration,
            "status": self.status.value,
            "completed": self.completed,
            "last_played": self.last_played.isoformat() if self.last_played else None,
            "play_count": self.play_count,
            "error_count": self.error_count,
            "session_id": self.session_id
        }
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PlaybackState":
        """从字典创建对象"""
        last_played = None
        if data.get("last_played"):
            last_played = datetime.fromisoformat(data["last_played"])
        
        return cls(
            course_id=data["course_id"],
            video_id=data.get("video_id", ""),
            position=data.get("position", 0.0),
            duration=data.get("duration", 0.0),
            status=PlaybackStatus(data.get("status", "stopped")),
            completed=data.get("completed", False),
            last_played=last_played,
            play_count=data.get("play_count", 0),
            error_count=data.get("error_count", 0),
            session_id=data.get("session_id", "")
        )


@dataclass
class LearningSession:
    """学习会话数据"""
    course_id: str
    mode: LearningMode
    session_id: str = ""
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    total_time: float = 0.0
    videos_completed: int = 0
    errors: List[str] = None
    progress_snapshots: List[Dict] = None
    
    def __post_init__(self):
        """初始化后处理"""
        if not self.session_id:
            self.session_id = str(uuid.uuid4())
        if self.start_time is None:
            self.start_time = datetime.now()
        if self.errors is None:
            self.errors = []
        if self.progress_snapshots is None:
            self.progress_snapshots = []
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "course_id": self.course_id,
            "mode": self.mode.value,
            "session_id": self.session_id,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "total_time": self.total_time,
            "videos_completed": self.videos_completed,
            "errors": self.errors,
            "progress_snapshots": self.progress_snapshots
        }


class VideoController:
    """视频播放控制器"""
    
    def __init__(self, page):
        """初始化视频控制器"""
        self.page = page
    
    async def detect_video_player(self) -> bool:
        """检测视频播放器"""
        try:
            # 尝试JavaScript检测
            result = await self.page.evaluate("""
                () => {
                    const videos = document.querySelectorAll('video');
                    return videos.length > 0;
                }
            """)
            if result:
                return True
        except:
            pass
        
        # 尝试UI元素检测
        try:
            selectors = ['video', '.video-player', '.player', '#player']
            for selector in selectors:
                locator = self.page.locator(selector)
                if await locator.count() > 0:
                    return True
        except:
            pass
        
        return False
    
    async def play(self) -> bool:
        """播放视频"""
        # 尝试JavaScript播放
        try:
            result = await self.page.evaluate("""
                () => {
                    const videos = document.querySelectorAll('video');
                    if (videos.length > 0) {
                        videos[0].play();
                        return true;
                    }
                    return false;
                }
            """)
            if result:
                # 验证播放状态
                await asyncio.sleep(0.5)
                is_playing = await self.is_playing()
                if is_playing:
                    return True
        except:
            pass
        
        # 尝试UI按钮点击
        try:
            play_selectors = ['.play-button', '.btn-play', 'button[title*="播放"]', 'button[title*="Play"]']
            for selector in play_selectors:
                locator = self.page.locator(selector)
                if await locator.count() > 0:
                    await locator.click()
                    await asyncio.sleep(0.5)
                    is_playing = await self.is_playing()
                    if is_playing:
                        return True
        except:
            pass
        
        # 尝试键盘快捷键
        try:
            await self.page.keyboard.press('Space')
            await asyncio.sleep(0.5)
            is_playing = await self.is_playing()
            return is_playing
        except:
            pass
        
        return False
    
    async def pause(self) -> bool:
        """暂停视频"""
        try:
            result = await self.page.evaluate("""
                () => {
                    const videos = document.querySelectorAll('video');
                    if (videos.length > 0) {
                        videos[0].pause();
                        return true;
                    }
                    return false;
                }
            """)
            return result
        except:
            return False
    
    async def get_current_time(self) -> float:
        """获取当前播放时间"""
        try:
            result = await self.page.evaluate("""
                () => {
                    const videos = document.querySelectorAll('video');
                    if (videos.length > 0) {
                        return videos[0].currentTime;
                    }
                    return 0;
                }
            """)
            return float(result)
        except:
            return 0.0
    
    async def get_duration(self) -> float:
        """获取视频总时长"""
        try:
            result = await self.page.evaluate("""
                () => {
                    const videos = document.querySelectorAll('video');
                    if (videos.length > 0) {
                        return videos[0].duration;
                    }
                    return 0;
                }
            """)
            return float(result)
        except:
            return 0.0
    
    async def seek_to(self, position: float) -> bool:
        """跳转到指定位置"""
        try:
            result = await self.page.evaluate(f"""
                (position) => {{
                    const videos = document.querySelectorAll('video');
                    if (videos.length > 0) {{
                        videos[0].currentTime = position;
                        return true;
                    }}
                    return false;
                }}
            """, position)
            return result
        except:
            return False
    
    async def is_playing(self) -> bool:
        """检测是否正在播放"""
        try:
            result = await self.page.evaluate("""
                () => {
                    const videos = document.querySelectorAll('video');
                    if (videos.length > 0) {
                        return !videos[0].paused;
                    }
                    return false;
                }
            """)
            return result
        except:
            return False
    
    async def is_ended(self) -> bool:
        """检测是否播放结束"""
        try:
            result = await self.page.evaluate("""
                () => {
                    const videos = document.querySelectorAll('video');
                    if (videos.length > 0) {
                        return videos[0].ended;
                    }
                    return false;
                }
            """)
            return result
        except:
            return False
    
    async def get_playback_status(self) -> PlaybackStatus:
        """获取播放状态"""
        try:
            is_ended = await self.is_ended()
            if is_ended:
                return PlaybackStatus.COMPLETED
            
            is_playing = await self.is_playing()
            if is_playing:
                return PlaybackStatus.PLAYING
            else:
                return PlaybackStatus.PAUSED
        except:
            return PlaybackStatus.ERROR


class ProgressMonitor:
    """进度监控器"""
    
    def __init__(self, video_controller: VideoController, check_interval: float = 1.0):
        """初始化进度监控器"""
        self.video_controller = video_controller
        self.check_interval = check_interval
        self.is_monitoring = False
        self.callbacks: List[Callable] = []
        self._monitor_task = None
        self._last_position = 0.0
        self._stuck_count = 0
    
    def add_progress_callback(self, callback: Callable):
        """添加进度回调"""
        self.callbacks.append(callback)
    
    def remove_progress_callback(self, callback: Callable):
        """移除进度回调"""
        if callback in self.callbacks:
            self.callbacks.remove(callback)
    
    async def start_monitoring(self):
        """开始监控"""
        if self.is_monitoring:
            return
        
        self.is_monitoring = True
        self._monitor_task = asyncio.create_task(self._monitor_progress())
    
    async def stop_monitoring(self):
        """停止监控"""
        self.is_monitoring = False
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
    
    async def _monitor_progress(self):
        """监控进度的内部方法"""
        while self.is_monitoring:
            try:
                position = await self.video_controller.get_current_time()
                duration = await self.video_controller.get_duration()
                status = await self.video_controller.get_playback_status()
                
                # 检测播放卡死
                if position == self._last_position and status == PlaybackStatus.PLAYING:
                    self._stuck_count += 1
                else:
                    self._stuck_count = 0
                    self._last_position = position
                
                # 计算进度百分比
                progress = (position / duration * 100.0) if duration > 0 else 0.0
                
                # 调用回调函数
                for callback in self.callbacks:
                    try:
                        callback(position, duration, status, progress)
                    except Exception as e:
                        logger.error(f"进度回调执行失败: {e}")
                
                await asyncio.sleep(self.check_interval)
                
            except Exception as e:
                logger.error(f"进度监控错误: {e}")
                await asyncio.sleep(self.check_interval)


class LearningAutomator:
    """学习自动化器"""
    
    def __init__(self, page, anti_detection=None, data_dir: Path = None):
        """初始化学习自动化器"""
        self.page = page
        self.anti_detection = anti_detection
        self.data_dir = data_dir or Path.cwd() / "data"
        
        # 创建数据目录
        self.playback_dir = self.data_dir / "playback"
        self.sessions_dir = self.data_dir / "sessions"
        self.playback_dir.mkdir(parents=True, exist_ok=True)
        self.sessions_dir.mkdir(parents=True, exist_ok=True)
        
        # 初始化组件
        self.video_controller = VideoController(page)
        self.progress_monitor = ProgressMonitor(self.video_controller)
        
        # 会话状态
        self.current_session: Optional[LearningSession] = None
        self.playback_state: Optional[PlaybackState] = None
    
    def _save_playback_state(self, state: PlaybackState):
        """保存播放状态"""
        try:
            file_path = self.playback_dir / f"{state.course_id}.json"
            temp_path = file_path.with_suffix('.json.tmp')
            
            # 原子写入
            with open(temp_path, 'w', encoding='utf-8') as f:
                json.dump(state.to_dict(), f, ensure_ascii=False, indent=2)
            
            temp_path.rename(file_path)
            logger.debug(f"播放状态已保存: {file_path}")
            
        except Exception as e:
            logger.error(f"保存播放状态失败: {e}")
    
    def _load_playback_state(self, course_id: str) -> Optional[PlaybackState]:
        """加载播放状态"""
        try:
            file_path = self.playback_dir / f"{course_id}.json"
            if not file_path.exists():
                return None
            
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            return PlaybackState.from_dict(data)
            
        except Exception as e:
            logger.error(f"加载播放状态失败: {e}")
            return None
    
    def _save_learning_session(self, session: LearningSession):
        """保存学习会话"""
        try:
            file_path = self.sessions_dir / f"{session.session_id}.json"
            temp_path = file_path.with_suffix('.json.tmp')
            
            # 原子写入
            with open(temp_path, 'w', encoding='utf-8') as f:
                json.dump(session.to_dict(), f, ensure_ascii=False, indent=2)
            
            temp_path.rename(file_path)
            logger.debug(f"学习会话已保存: {file_path}")
            
        except Exception as e:
            logger.error(f"保存学习会话失败: {e}")
    
    def _load_learning_session(self, session_id: str) -> Optional[LearningSession]:
        """加载学习会话"""
        try:
            file_path = self.sessions_dir / f"{session_id}.json"
            if not file_path.exists():
                return None
            
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 重新创建会话对象
            session = LearningSession(
                course_id=data["course_id"],
                mode=LearningMode(data["mode"])
            )
            session.session_id = data["session_id"]
            session.start_time = datetime.fromisoformat(data["start_time"]) if data.get("start_time") else None
            session.end_time = datetime.fromisoformat(data["end_time"]) if data.get("end_time") else None
            session.total_time = data.get("total_time", 0.0)
            session.videos_completed = data.get("videos_completed", 0)
            session.errors = data.get("errors", [])
            session.progress_snapshots = data.get("progress_snapshots", [])
            
            return session
            
        except Exception as e:
            logger.error(f"加载学习会话失败: {e}")
            return None
    
    async def start_video_learning(self, course_id: str, resume: bool = True, mode: LearningMode = LearningMode.NORMAL) -> bool:
        """开始视频学习"""
        try:
            # 检查是否已有活动会话
            if self.current_session is not None:
                logger.warning("已有活动学习会话，无法开始新的学习")
                return False
            
            # 检测视频播放器
            has_player = await self.video_controller.detect_video_player()
            if not has_player:
                logger.error("未检测到视频播放器")
                return False
            
            # 创建新的学习会话
            self.current_session = LearningSession(course_id=course_id, mode=mode)
            
            # 尝试加载已保存的播放状态
            if resume:
                saved_state = self._load_playback_state(course_id)
                if saved_state:
                    self.playback_state = saved_state
                    self.playback_state.session_id = self.current_session.session_id
                    
                    # 跳转到断点位置
                    if self.playback_state.position > 0:
                        await self.video_controller.seek_to(self.playback_state.position)
                        logger.info(f"已跳转到断点位置: {self.playback_state.position}秒")
                else:
                    # 创建新的播放状态
                    self.playback_state = PlaybackState(
                        course_id=course_id,
                        session_id=self.current_session.session_id
                    )
            else:
                # 创建新的播放状态
                self.playback_state = PlaybackState(
                    course_id=course_id,
                    session_id=self.current_session.session_id
                )
            
            # 开始播放
            play_success = await self.video_controller.play()
            if not play_success:
                logger.error("播放视频失败")
                self.current_session = None
                self.playback_state = None
                return False
            
            # 获取视频信息
            duration = await self.video_controller.get_duration()
            current_time = await self.video_controller.get_current_time()
            
            # 更新播放状态
            self.playback_state.duration = duration
            self.playback_state.position = current_time
            self.playback_state.status = PlaybackStatus.PLAYING
            self.playback_state.last_played = datetime.now()
            self.playback_state.play_count += 1
            
            # 设置播放速度（快速模式）
            if mode == LearningMode.FAST:
                try:
                    await self.page.evaluate("""
                        () => {
                            const videos = document.querySelectorAll('video');
                            if (videos.length > 0) {
                                videos[0].playbackRate = 2.0;
                            }
                        }
                    """)
                except:
                    pass
            
            # 反检测延迟
            if self.anti_detection:
                await self.anti_detection.random_delay(0.5, 2.0)
            
            logger.info(f"开始学习课程: {course_id}, 模式: {mode.value}")
            return True
            
        except Exception as e:
            logger.error(f"开始视频学习失败: {e}")
            self.current_session = None
            self.playback_state = None
            return False
    
    async def pause_learning(self) -> bool:
        """暂停学习"""
        if not self.current_session or not self.playback_state:
            return False
        
        try:
            success = await self.video_controller.pause()
            if success:
                # 更新播放位置
                current_time = await self.video_controller.get_current_time()
                self.playback_state.position = current_time
                self.playback_state.status = PlaybackStatus.PAUSED
                
                # 保存状态
                self._save_playback_state(self.playback_state)
                
                logger.info("学习已暂停")
                return True
            
        except Exception as e:
            logger.error(f"暂停学习失败: {e}")
        
        return False
    
    async def resume_learning(self) -> bool:
        """恢复学习"""
        if not self.current_session or not self.playback_state:
            return False
        
        try:
            success = await self.video_controller.play()
            if success:
                # 更新播放位置和状态
                current_time = await self.video_controller.get_current_time()
                self.playback_state.position = current_time
                self.playback_state.status = PlaybackStatus.PLAYING
                
                logger.info("学习已恢复")
                return True
            
        except Exception as e:
            logger.error(f"恢复学习失败: {e}")
        
        return False
    
    async def stop_learning(self):
        """停止学习"""
        if not self.current_session:
            return
        
        try:
            # 停止进度监控
            await self.progress_monitor.stop_monitoring()
            
            # 暂停视频
            await self.video_controller.pause()
            
            # 更新最终状态
            if self.playback_state:
                current_time = await self.video_controller.get_current_time()
                self.playback_state.position = current_time
                self.playback_state.status = PlaybackStatus.STOPPED
                self._save_playback_state(self.playback_state)
            
            # 完成会话
            self.current_session.end_time = datetime.now()
            self._save_learning_session(self.current_session)
            
            logger.info("学习已停止")
            
        except Exception as e:
            logger.error(f"停止学习失败: {e}")
    
    def _handle_playback_error(self, error_type: str, error_message: str) -> str:
        """处理播放错误"""
        if self.playback_state:
            self.playback_state.error_count += 1
        
        if self.current_session:
            error_info = f"{error_type}: {error_message}"
            self.current_session.errors.append(error_info)
        
        # 根据错误类型决定恢复策略
        if error_type == "network_error":
            return "refresh_page"
        elif error_type == "playback_stuck":
            return "restart_playback"
        elif error_type == "buffering_timeout":
            return "wait_and_retry"
        else:
            return "log_and_skip"
    
    def get_learning_statistics(self) -> Dict[str, Any]:
        """获取学习统计"""
        stats = {
            "current_session": self.current_session.to_dict() if self.current_session else None,
            "playback_state": self.playback_state.to_dict() if self.playback_state else None,
            "total_learning_time": self.current_session.total_time if self.current_session else 0,
            "videos_completed": self.current_session.videos_completed if self.current_session else 0,
            "error_count": self.playback_state.error_count if self.playback_state else 0,
            "session_errors": self.current_session.errors if self.current_session else []
        }
        return stats
    
    def add_progress_callback(self, callback: Callable):
        """添加进度回调"""
        self.progress_monitor.add_progress_callback(callback)
    
    async def cleanup(self):
        """清理资源"""
        await self.progress_monitor.stop_monitoring()
        
        if self.current_session:
            self.current_session.end_time = datetime.now()
            self._save_learning_session(self.current_session)