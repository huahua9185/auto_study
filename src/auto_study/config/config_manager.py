"""
配置管理器

统一的配置管理，支持多环境配置、热重载、配置验证等功能
"""

import os
import threading
import time
from typing import Any, Dict, List, Optional, Callable
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from ..utils.logger import logger
from .config_parser import ConfigParser
from .encryption import get_encryption_manager


class ConfigFileHandler(FileSystemEventHandler):
    """配置文件监控处理器"""
    
    def __init__(self, config_manager: 'ConfigManager'):
        self.config_manager = config_manager
    
    def on_modified(self, event):
        if not event.is_directory and event.src_path.endswith(('.yml', '.yaml')):
            logger.info(f"检测到配置文件变化: {event.src_path}")
            self.config_manager.reload_config()


class ConfigManager:
    """配置管理器"""
    
    def __init__(self, config_dir: str = "config"):
        self.config_dir = Path(config_dir)
        self.parser = ConfigParser()
        self.encryption_manager = get_encryption_manager()
        
        # 配置缓存
        self._config_cache: Dict[str, Any] = {}
        self._config_lock = threading.RLock()
        self._last_reload_time = 0
        
        # 环境相关
        self.environment = os.getenv('AUTO_STUDY_ENV', 'development')
        
        # 配置文件路径
        self.default_config_path = self.config_dir / "default.yml"
        self.env_config_path = self.config_dir / f"{self.environment}.yml"
        self.local_config_path = self.config_dir / "local.yml"
        
        # 热重载相关
        self._observer = None
        self._reload_callbacks: List[Callable[[Dict[str, Any]], None]] = []
        
        # 初始化
        self._ensure_config_dir()
        self.load_config()
    
    def _ensure_config_dir(self) -> None:
        """确保配置目录存在"""
        self.config_dir.mkdir(parents=True, exist_ok=True)
    
    def load_config(self) -> Dict[str, Any]:
        """
        加载配置
        
        Returns:
            合并后的配置字典
        """
        with self._config_lock:
            try:
                configs = []
                
                # 1. 加载默认配置
                if self.default_config_path.exists():
                    default_config = self.parser.load_config(self.default_config_path)
                    configs.append(default_config)
                    logger.debug(f"已加载默认配置: {self.default_config_path}")
                
                # 2. 加载环境配置
                if self.env_config_path.exists():
                    env_config = self.parser.load_config(self.env_config_path)
                    configs.append(env_config)
                    logger.debug(f"已加载环境配置: {self.env_config_path}")
                
                # 3. 加载本地配置（不提交到版本控制）
                if self.local_config_path.exists():
                    local_config = self.parser.load_config(self.local_config_path)
                    configs.append(local_config)
                    logger.debug(f"已加载本地配置: {self.local_config_path}")
                
                # 4. 合并配置
                if configs:
                    self._config_cache = self.parser.merge_configs(*configs)
                else:
                    self._config_cache = {}
                    logger.warning("未找到任何配置文件")
                
                # 5. 应用环境变量覆盖
                self._apply_env_overrides()
                
                self._last_reload_time = time.time()
                logger.info(f"配置加载完成，环境: {self.environment}")
                
                return self._config_cache.copy()
                
            except Exception as e:
                logger.error(f"加载配置失败: {e}")
                raise
    
    def reload_config(self) -> Dict[str, Any]:
        """
        重新加载配置
        
        Returns:
            重新加载后的配置字典
        """
        logger.info("重新加载配置...")
        old_config = self._config_cache.copy()
        new_config = self.load_config()
        
        # 比较配置差异
        diff = self.parser.get_config_diff(old_config, new_config)
        if any(diff.values()):
            logger.info("配置已更新")
            logger.debug(f"配置差异: {diff}")
            
            # 通知回调函数
            self._notify_reload_callbacks(new_config)
        else:
            logger.debug("配置无变化")
        
        return new_config
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        获取配置值
        
        Args:
            key: 配置键，支持点号分隔的路径 (如 'database.host')
            default: 默认值
            
        Returns:
            配置值
        """
        with self._config_lock:
            keys = key.split('.')
            value = self._config_cache
            
            for k in keys:
                if isinstance(value, dict) and k in value:
                    value = value[k]
                else:
                    return default
            
            return value
    
    def set(self, key: str, value: Any, save_to_file: bool = False) -> None:
        """
        设置配置值
        
        Args:
            key: 配置键
            value: 配置值
            save_to_file: 是否保存到文件
        """
        with self._config_lock:
            keys = key.split('.')
            config = self._config_cache
            
            # 导航到父级
            for k in keys[:-1]:
                if k not in config:
                    config[k] = {}
                config = config[k]
            
            # 设置值
            config[keys[-1]] = value
            
            if save_to_file:
                self.save_config()
    
    def save_config(self, config_path: Optional[Path] = None) -> None:
        """
        保存配置到文件
        
        Args:
            config_path: 配置文件路径，默认为本地配置文件
        """
        if config_path is None:
            config_path = self.local_config_path
        
        with self._config_lock:
            self.parser.save_config(self._config_cache, config_path)
    
    def _apply_env_overrides(self) -> None:
        """应用环境变量覆盖"""
        # 支持形如 AUTO_STUDY_DATABASE_HOST 的环境变量
        prefix = "AUTO_STUDY_"
        
        for env_var, value in os.environ.items():
            if env_var.startswith(prefix):
                # 移除前缀并转换为配置键
                config_key = env_var[len(prefix):].lower().replace('_', '.')
                
                # 类型转换
                converted_value = self._convert_env_value(value)
                
                self.set(config_key, converted_value)
                logger.debug(f"环境变量覆盖: {config_key} = {converted_value}")
    
    def _convert_env_value(self, value: str) -> Any:
        """转换环境变量值类型"""
        # 尝试转换为布尔值
        if value.lower() in ('true', 'yes', '1', 'on'):
            return True
        elif value.lower() in ('false', 'no', '0', 'off'):
            return False
        
        # 尝试转换为数字
        try:
            if '.' in value:
                return float(value)
            else:
                return int(value)
        except ValueError:
            pass
        
        # 返回字符串
        return value
    
    def enable_hot_reload(self) -> None:
        """启用热重载"""
        if self._observer is not None:
            logger.warning("热重载已启用")
            return
        
        self._observer = Observer()
        event_handler = ConfigFileHandler(self)
        
        # 监控配置目录
        self._observer.schedule(
            event_handler,
            str(self.config_dir),
            recursive=False
        )
        
        self._observer.start()
        logger.info("配置热重载已启用")
    
    def disable_hot_reload(self) -> None:
        """禁用热重载"""
        if self._observer is not None:
            self._observer.stop()
            self._observer.join()
            self._observer = None
            logger.info("配置热重载已禁用")
    
    def add_reload_callback(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        """
        添加配置重载回调
        
        Args:
            callback: 回调函数，接收新配置作为参数
        """
        self._reload_callbacks.append(callback)
    
    def remove_reload_callback(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        """
        移除配置重载回调
        
        Args:
            callback: 要移除的回调函数
        """
        if callback in self._reload_callbacks:
            self._reload_callbacks.remove(callback)
    
    def _notify_reload_callbacks(self, new_config: Dict[str, Any]) -> None:
        """通知所有重载回调"""
        for callback in self._reload_callbacks:
            try:
                callback(new_config)
            except Exception as e:
                logger.error(f"配置重载回调执行失败: {e}")
    
    def get_all_config(self) -> Dict[str, Any]:
        """
        获取所有配置
        
        Returns:
            完整配置字典的副本
        """
        with self._config_lock:
            return self._config_cache.copy()
    
    def get_config(self) -> Dict[str, Any]:
        """
        获取所有配置（get_all_config的别名）
        
        Returns:
            完整配置字典的副本
        """
        return self.get_all_config()
    
    def get_environment(self) -> str:
        """
        获取当前环境
        
        Returns:
            环境名称
        """
        return self.environment
    
    def set_environment(self, environment: str) -> None:
        """
        设置环境并重新加载配置
        
        Args:
            environment: 环境名称
        """
        if self.environment != environment:
            self.environment = environment
            self.env_config_path = self.config_dir / f"{environment}.yml"
            os.environ['AUTO_STUDY_ENV'] = environment
            self.reload_config()
            logger.info(f"环境已切换到: {environment}")
    
    def validate_config(self, schema: Dict[str, Any]) -> List[str]:
        """
        验证当前配置
        
        Args:
            schema: 配置模式
            
        Returns:
            验证错误列表
        """
        with self._config_lock:
            return self.parser.validate_config_structure(self._config_cache, schema)
    
    def export_config(self, output_path: Path, include_sensitive: bool = False) -> None:
        """
        导出配置到文件
        
        Args:
            output_path: 输出文件路径
            include_sensitive: 是否包含敏感信息
        """
        with self._config_lock:
            config = self._config_cache.copy()
            
            if not include_sensitive:
                config = self._mask_sensitive_fields(config)
            
            self.parser.save_config(config, output_path)
            logger.info(f"配置已导出到: {output_path}")
    
    def _mask_sensitive_fields(self, data: Any) -> Any:
        """
        掩码敏感字段
        
        Args:
            data: 要处理的数据
            
        Returns:
            处理后的数据
        """
        if isinstance(data, dict):
            result = {}
            for key, value in data.items():
                if self.parser._is_sensitive_key(key):
                    result[key] = "***MASKED***"
                else:
                    result[key] = self._mask_sensitive_fields(value)
            return result
        elif isinstance(data, list):
            return [self._mask_sensitive_fields(item) for item in data]
        else:
            return data
    
    def get_config_info(self) -> Dict[str, Any]:
        """
        获取配置信息
        
        Returns:
            配置元信息
        """
        return {
            'environment': self.environment,
            'config_dir': str(self.config_dir),
            'last_reload_time': self._last_reload_time,
            'hot_reload_enabled': self._observer is not None,
            'config_files': {
                'default': self.default_config_path.exists(),
                'environment': self.env_config_path.exists(),
                'local': self.local_config_path.exists()
            }
        }
    
    def __del__(self):
        """清理资源"""
        self.disable_hot_reload()


# 全局配置管理器实例
_config_manager = None


def get_config_manager(config_dir: str = "config") -> ConfigManager:
    """
    获取全局配置管理器实例
    
    Args:
        config_dir: 配置目录路径
        
    Returns:
        配置管理器实例
    """
    global _config_manager
    
    if _config_manager is None:
        _config_manager = ConfigManager(config_dir)
    
    return _config_manager