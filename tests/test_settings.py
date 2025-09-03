"""
测试系统设置配置
"""

import os
import pytest
from unittest.mock import patch, mock_open
from src.auto_study.config.settings import Settings, BrowserConfig, LoginConfig, LearningConfig, SystemConfig


class TestBrowserConfig:
    """浏览器配置测试"""
    
    def test_browser_config_defaults(self):
        """测试浏览器配置默认值"""
        config = BrowserConfig()
        
        assert config.headless is False
        assert config.width == 1920
        assert config.height == 1080
        assert "Chrome/120.0.0.0" in config.user_agent
        assert config.timeout == 30000


class TestLoginConfig:
    """登录配置测试"""
    
    def test_login_config_defaults(self):
        """测试登录配置默认值"""
        config = LoginConfig()
        
        assert config.max_retries == 3
        assert config.retry_delay == 5
        assert config.captcha_timeout == 30


class TestLearningConfig:
    """学习配置测试"""
    
    def test_learning_config_defaults(self):
        """测试学习配置默认值"""
        config = LearningConfig()
        
        assert config.check_interval == 30
        assert config.human_behavior is True
        assert config.auto_handle_popups is True
        assert config.max_learning_time == 8 * 60 * 60


class TestSystemConfig:
    """系统配置测试"""
    
    def test_system_config_defaults(self):
        """测试系统配置默认值"""
        config = SystemConfig()
        
        assert config.log_level == "INFO"
        assert config.log_file == "logs/auto_study.log"
        assert config.data_dir == "data"
        assert config.max_log_size == 10 * 1024 * 1024
        assert config.backup_count == 5


class TestSettings:
    """设置管理器测试"""
    
    def test_settings_init(self):
        """测试设置初始化"""
        settings = Settings()
        
        assert isinstance(settings.browser, BrowserConfig)
        assert isinstance(settings.login, LoginConfig)
        assert isinstance(settings.learning, LearningConfig)
        assert isinstance(settings.system, SystemConfig)
        
        assert settings.site_url == "https://edu.nxgbjy.org.cn"
        assert settings.login_url == "https://edu.nxgbjy.org.cn/login"
        assert settings.courses_url == "https://edu.nxgbjy.org.cn/courses"
    
    @patch.dict(os.environ, {
        'BROWSER_HEADLESS': 'true',
        'BROWSER_WIDTH': '1366',
        'BROWSER_HEIGHT': '768',
        'LOGIN_MAX_RETRIES': '5',
        'LOGIN_RETRY_DELAY': '3',
        'LEARNING_CHECK_INTERVAL': '45',
        'LEARNING_HUMAN_BEHAVIOR': 'false',
        'LOG_LEVEL': 'DEBUG',
        'LOG_FILE': 'custom.log'
    })
    def test_update_from_env(self):
        """测试从环境变量更新配置"""
        settings = Settings()
        
        # 浏览器配置
        assert settings.browser.headless is True
        assert settings.browser.width == 1366
        assert settings.browser.height == 768
        
        # 登录配置
        assert settings.login.max_retries == 5
        assert settings.login.retry_delay == 3
        
        # 学习配置
        assert settings.learning.check_interval == 45
        assert settings.learning.human_behavior is False
        
        # 系统配置
        assert settings.system.log_level == "DEBUG"
        assert settings.system.log_file == "custom.log"
    
    @patch.dict(os.environ, {
        'USERNAME': 'test_user',
        'PASSWORD': 'test_pass'
    })
    def test_get_user_credentials(self):
        """测试获取用户凭据"""
        settings = Settings()
        
        username, password = settings.get_user_credentials()
        
        assert username == 'test_user'
        assert password == 'test_pass'
    
    def test_get_user_credentials_empty(self):
        """测试获取空的用户凭据"""
        with patch.dict(os.environ, {}, clear=True):
            settings = Settings()
            
            username, password = settings.get_user_credentials()
            
            assert username is None
            assert password is None
    
    @patch('os.makedirs')
    @patch.dict(os.environ, {
        'USERNAME': 'test_user',
        'PASSWORD': 'test_pass'
    })
    def test_validate_config_success(self, mock_makedirs):
        """测试配置验证成功"""
        settings = Settings()
        
        result = settings.validate_config()
        
        assert result is True
        # 验证目录创建调用
        mock_makedirs.assert_any_call(settings.system.data_dir, exist_ok=True)
        mock_makedirs.assert_any_call('logs', exist_ok=True)  # log_file的目录
    
    @patch('os.makedirs')
    def test_validate_config_no_credentials(self, mock_makedirs):
        """测试配置验证失败 - 无凭据"""
        with patch.dict(os.environ, {}, clear=True):
            settings = Settings()
            
            result = settings.validate_config()
            
            assert result is False
    
    @patch('os.makedirs', side_effect=Exception("权限错误"))
    @patch.dict(os.environ, {
        'USERNAME': 'test_user',
        'PASSWORD': 'test_pass'
    })
    def test_validate_config_mkdir_error(self, mock_makedirs):
        """测试配置验证失败 - 目录创建错误"""
        settings = Settings()
        
        result = settings.validate_config()
        
        assert result is False
    
    def test_to_dict(self):
        """测试转换为字典"""
        settings = Settings()
        
        config_dict = settings.to_dict()
        
        # 验证字典结构
        assert 'browser' in config_dict
        assert 'login' in config_dict
        assert 'learning' in config_dict
        assert 'system' in config_dict
        
        # 验证浏览器配置
        browser_config = config_dict['browser']
        assert 'headless' in browser_config
        assert 'width' in browser_config
        assert 'height' in browser_config
        assert 'user_agent' in browser_config
        assert 'timeout' in browser_config
        
        # 验证登录配置
        login_config = config_dict['login']
        assert 'max_retries' in login_config
        assert 'retry_delay' in login_config
        assert 'captcha_timeout' in login_config
        
        # 验证学习配置
        learning_config = config_dict['learning']
        assert 'check_interval' in learning_config
        assert 'human_behavior' in learning_config
        assert 'auto_handle_popups' in learning_config
        assert 'max_learning_time' in learning_config
        
        # 验证系统配置
        system_config = config_dict['system']
        assert 'log_level' in system_config
        assert 'log_file' in system_config
        assert 'data_dir' in system_config
        assert 'max_log_size' in system_config
        assert 'backup_count' in system_config
    
    @patch('pathlib.Path.exists')
    @patch('dotenv.load_dotenv')
    def test_load_config_with_env_file(self, mock_load_dotenv, mock_exists):
        """测试加载.env文件"""
        mock_exists.return_value = True
        
        settings = Settings()
        
        mock_load_dotenv.assert_called_once()
    
    @patch('pathlib.Path.exists')
    @patch('dotenv.load_dotenv')
    def test_load_config_without_env_file(self, mock_load_dotenv, mock_exists):
        """测试无.env文件时的加载"""
        mock_exists.return_value = False
        
        settings = Settings()
        
        mock_load_dotenv.assert_not_called()
    
    @patch('dotenv.load_dotenv', side_effect=Exception("加载错误"))
    def test_load_config_error_handling(self, mock_load_dotenv):
        """测试配置加载错误处理"""
        # 应该不抛出异常，正常创建设置对象
        settings = Settings()
        
        assert isinstance(settings, Settings)
        assert isinstance(settings.browser, BrowserConfig)