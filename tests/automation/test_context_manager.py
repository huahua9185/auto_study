"""
测试上下文持久化管理器
"""

import pytest
import json
import tempfile
import time
from pathlib import Path
from unittest.mock import Mock

from src.auto_study.automation.context_manager import ContextManager
from src.auto_study.config.config_manager import ConfigManager


class TestContextManager:
    """上下文持久化管理器测试"""
    
    @pytest.fixture
    def temp_data_dir(self):
        """创建临时数据目录"""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir
    
    @pytest.fixture
    def mock_config_manager(self, temp_data_dir):
        """Mock配置管理器"""
        config_manager = Mock(spec=ConfigManager)
        config_manager.get_config.return_value = {
            'system': {
                'data_dir': temp_data_dir
            }
        }
        return config_manager
    
    @pytest.fixture
    def context_manager(self, mock_config_manager):
        """创建上下文管理器实例"""
        return ContextManager(mock_config_manager)
    
    @pytest.fixture
    def mock_browser_context(self):
        """Mock浏览器上下文"""
        context = Mock()
        context.cookies.return_value = [
            {
                'name': 'test_cookie',
                'value': 'test_value',
                'domain': 'example.com',
                'path': '/',
                'expires': int(time.time()) + 3600  # 1小时后过期
            },
            {
                'name': 'session_cookie', 
                'value': 'session_value',
                'domain': 'example.com',
                'path': '/'
                # 没有过期时间（会话cookie）
            }
        ]
        
        # Mock页面
        mock_page = Mock()
        mock_page.url = 'https://example.com/test'
        mock_page.evaluate.side_effect = [
            {'key1': 'localStorage_value1', 'key2': 'localStorage_value2'},  # localStorage
            {'session_key': 'sessionStorage_value'}  # sessionStorage
        ]
        context.pages = [mock_page]
        
        return context
    
    @pytest.fixture  
    def mock_page(self):
        """Mock页面对象"""
        page = Mock()
        page.url = 'https://example.com/test'
        page.context = Mock()
        return page
    
    def test_context_manager_init(self, context_manager, temp_data_dir):
        """测试上下文管理器初始化"""
        assert context_manager.config_manager is not None
        assert context_manager.config is not None
        assert context_manager._default_context_name == 'default'
        
        # 检查目录创建
        expected_context_dir = Path(temp_data_dir) / 'browser_contexts'
        assert expected_context_dir.exists()
        assert context_manager._context_dir == expected_context_dir
    
    def test_save_context_state(self, context_manager, mock_browser_context):
        """测试保存上下文状态"""
        result = context_manager.save_context_state(mock_browser_context, 'test_context')
        
        assert result is True
        
        # 检查文件是否创建
        context_path = context_manager._context_dir / 'test_context'
        assert context_path.exists()
        assert (context_path / 'cookies.json').exists()
        assert (context_path / 'storage.json').exists()
        assert (context_path / 'metadata.json').exists()
    
    def test_save_cookies(self, context_manager, mock_browser_context):
        """测试保存Cookies"""
        context_path = context_manager._context_dir / 'test_context'
        context_path.mkdir(parents=True, exist_ok=True)
        
        context_manager._save_cookies(mock_browser_context, context_path)
        
        cookies_file = context_path / 'cookies.json'
        assert cookies_file.exists()
        
        with open(cookies_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        assert 'timestamp' in data
        assert 'cookies' in data
        assert len(data['cookies']) == 2
        assert data['cookies'][0]['name'] == 'test_cookie'
        assert data['cookies'][1]['name'] == 'session_cookie'
    
    def test_load_cookies(self, context_manager, mock_browser_context):
        """测试加载Cookies"""
        context_path = context_manager._context_dir / 'test_context'
        context_path.mkdir(parents=True, exist_ok=True)
        
        # 先保存cookies
        context_manager._save_cookies(mock_browser_context, context_path)
        
        # 创建新的mock上下文来加载cookies
        new_context = Mock()
        new_context.add_cookies = Mock()
        
        # 加载cookies
        context_manager._load_cookies(new_context, context_path)
        
        # 验证add_cookies被调用
        new_context.add_cookies.assert_called_once()
        added_cookies = new_context.add_cookies.call_args[0][0]
        assert len(added_cookies) >= 1  # 可能有过期的cookies被过滤
    
    def test_save_storage_state(self, context_manager, mock_browser_context):
        """测试保存Storage状态"""
        context_path = context_manager._context_dir / 'test_context'
        context_path.mkdir(parents=True, exist_ok=True)
        
        context_manager._save_storage_state(mock_browser_context, context_path)
        
        storage_file = context_path / 'storage.json'
        assert storage_file.exists()
        
        with open(storage_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        assert 'timestamp' in data
        assert 'storage' in data
        assert 'https://example.com/test' in data['storage']
        
        page_storage = data['storage']['https://example.com/test']
        assert 'localStorage' in page_storage
        assert 'sessionStorage' in page_storage
        assert page_storage['localStorage']['key1'] == 'localStorage_value1'
        assert page_storage['sessionStorage']['session_key'] == 'sessionStorage_value'
    
    def test_load_storage_state(self, context_manager):
        """测试加载Storage状态"""
        context_path = context_manager._context_dir / 'test_context'
        context_path.mkdir(parents=True, exist_ok=True)
        
        # 创建测试storage数据
        storage_data = {
            'timestamp': int(time.time()),
            'storage': {
                'https://example.com/test': {
                    'localStorage': {'key1': 'value1'},
                    'sessionStorage': {'session_key': 'session_value'}
                }
            }
        }
        
        storage_file = context_path / 'storage.json'
        with open(storage_file, 'w', encoding='utf-8') as f:
            json.dump(storage_data, f)
        
        # Mock上下文
        mock_context = Mock()
        
        # 加载storage状态
        context_manager._load_storage_state(mock_context, context_path)
        
        # 检查storage数据被保存到上下文
        assert hasattr(mock_context, '_stored_storage')
        assert 'https://example.com/test' in mock_context._stored_storage
    
    def test_restore_page_storage(self, context_manager, mock_page):
        """测试恢复页面Storage"""
        # 准备mock上下文的storage数据
        mock_page.context._stored_storage = {
            'https://example.com/test': {
                'localStorage': {'key1': 'value1', 'key2': 'value2'},
                'sessionStorage': {'session_key': 'session_value'}
            }
        }
        
        # 恢复storage
        context_manager.restore_page_storage(mock_page)
        
        # 验证evaluate被调用来恢复localStorage和sessionStorage
        assert mock_page.evaluate.call_count == 2
    
    def test_url_matches(self, context_manager):
        """测试URL匹配"""
        # 完全匹配
        assert context_manager._url_matches(
            'https://example.com/test',
            'https://example.com/test'
        ) is True
        
        # 不匹配
        assert context_manager._url_matches(
            'https://example.com/test1', 
            'https://example.com/test2'
        ) is False
        
        # 域名不同
        assert context_manager._url_matches(
            'https://example.com/test',
            'https://other.com/test'
        ) is False
    
    def test_save_context_metadata(self, context_manager, mock_browser_context):
        """测试保存上下文元信息"""
        context_path = context_manager._context_dir / 'test_context'
        context_path.mkdir(parents=True, exist_ok=True)
        
        # 设置页面的evaluate返回值
        mock_browser_context.pages[0].evaluate.return_value = 'Mozilla/5.0 Test Agent'
        mock_browser_context.pages[0].viewport_size = {'width': 1280, 'height': 720}
        
        context_manager._save_context_metadata(mock_browser_context, context_path)
        
        metadata_file = context_path / 'metadata.json'
        assert metadata_file.exists()
        
        with open(metadata_file, 'r', encoding='utf-8') as f:
            metadata = json.load(f)
        
        assert 'timestamp' in metadata
        assert 'pages_count' in metadata
        assert metadata['pages_count'] == 1
        assert metadata['user_agent'] == 'Mozilla/5.0 Test Agent'
        assert metadata['viewport']['width'] == 1280
    
    def test_list_saved_contexts(self, context_manager):
        """测试列出保存的上下文"""
        # 创建一些测试上下文目录
        contexts = ['context1', 'context2', 'context3']
        for ctx_name in contexts:
            ctx_path = context_manager._context_dir / ctx_name
            ctx_path.mkdir(parents=True, exist_ok=True)
        
        # 创建一个文件（应该被忽略）
        (context_manager._context_dir / 'not_a_dir.txt').touch()
        
        saved_contexts = context_manager.list_saved_contexts()
        
        assert len(saved_contexts) == 3
        assert all(ctx in saved_contexts for ctx in contexts)
        assert saved_contexts == sorted(contexts)
    
    def test_delete_context_state(self, context_manager, mock_browser_context):
        """测试删除上下文状态"""
        # 先保存一个上下文
        context_manager.save_context_state(mock_browser_context, 'test_delete')
        
        context_path = context_manager._context_dir / 'test_delete'
        assert context_path.exists()
        
        # 删除上下文
        result = context_manager.delete_context_state('test_delete')
        assert result is True
        assert not context_path.exists()
        
        # 尝试删除不存在的上下文
        result = context_manager.delete_context_state('non_existent')
        assert result is False
    
    def test_get_context_info(self, context_manager, mock_browser_context):
        """测试获取上下文信息"""
        # 保存一个上下文
        context_manager.save_context_state(mock_browser_context, 'test_info')
        
        # 获取上下文信息
        info = context_manager.get_context_info('test_info')
        
        assert info is not None
        assert info['name'] == 'test_info'
        assert 'path' in info
        assert 'timestamp' in info
        assert 'files' in info
        assert 'files_count' in info
        assert info['files_count'] >= 3  # cookies, storage, metadata
        assert 'cookies_count' in info
        assert 'storage_pages_count' in info
        
        # 获取不存在的上下文信息
        info = context_manager.get_context_info('non_existent')
        assert info is None
    
    def test_cleanup_expired_contexts(self, context_manager):
        """测试清理过期上下文"""
        # 创建一个当前上下文
        current_ctx_path = context_manager._context_dir / 'current_context'
        current_ctx_path.mkdir(parents=True, exist_ok=True)
        
        current_metadata = {
            'timestamp': int(time.time()),  # 当前时间
            'pages_count': 1
        }
        
        with open(current_ctx_path / 'metadata.json', 'w') as f:
            json.dump(current_metadata, f)
        
        # 创建一个过期上下文
        expired_ctx_path = context_manager._context_dir / 'expired_context'
        expired_ctx_path.mkdir(parents=True, exist_ok=True)
        
        expired_metadata = {
            'timestamp': int(time.time()) - (35 * 24 * 60 * 60),  # 35天前
            'pages_count': 1
        }
        
        with open(expired_ctx_path / 'metadata.json', 'w') as f:
            json.dump(expired_metadata, f)
        
        # 清理过期上下文（30天）
        cleaned_count = context_manager.cleanup_expired_contexts(max_age_days=30)
        
        assert cleaned_count == 1
        assert current_ctx_path.exists()
        assert not expired_ctx_path.exists()
    
    def test_load_context_state_success(self, context_manager, mock_browser_context):
        """测试成功加载上下文状态"""
        # 先保存上下文状态
        context_manager.save_context_state(mock_browser_context, 'test_load')
        
        # 创建新的mock上下文进行加载
        new_context = Mock()
        new_context.add_cookies = Mock()
        
        # 加载上下文状态
        result = context_manager.load_context_state(new_context, 'test_load')
        
        assert result is True
        new_context.add_cookies.assert_called()
    
    def test_load_context_state_not_exists(self, context_manager):
        """测试加载不存在的上下文状态"""
        mock_context = Mock()
        
        result = context_manager.load_context_state(mock_context, 'non_existent')
        
        assert result is False
    
    def test_default_context_name(self, context_manager, mock_browser_context):
        """测试默认上下文名称"""
        # 不指定名称保存
        result = context_manager.save_context_state(mock_browser_context)
        assert result is True
        
        # 检查默认名称目录是否创建
        default_path = context_manager._context_dir / 'default'
        assert default_path.exists()
        
        # 不指定名称加载
        new_context = Mock()
        new_context.add_cookies = Mock()
        
        result = context_manager.load_context_state(new_context)
        assert result is True
    
    def test_empty_pages_handling(self, context_manager):
        """测试空页面列表的处理"""
        mock_context = Mock()
        mock_context.pages = []  # 空页面列表
        
        context_path = context_manager._context_dir / 'empty_pages'
        context_path.mkdir(parents=True, exist_ok=True)
        
        # 应该能正常处理空页面列表
        context_manager._save_storage_state(mock_context, context_path)
        
        # 检查没有创建storage文件
        storage_file = context_path / 'storage.json'
        assert not storage_file.exists()
    
    def test_invalid_page_url_handling(self, context_manager):
        """测试无效页面URL的处理"""
        mock_context = Mock()
        mock_page = Mock()
        mock_page.url = 'about:blank'  # 无效URL
        mock_context.pages = [mock_page]
        
        context_path = context_manager._context_dir / 'invalid_url'
        context_path.mkdir(parents=True, exist_ok=True)
        
        # 应该能正常处理无效URL
        context_manager._save_storage_state(mock_context, context_path)
        
        # 可能没有创建storage文件，或者创建了空的storage文件
        storage_file = context_path / 'storage.json'
        if storage_file.exists():
            with open(storage_file, 'r') as f:
                data = json.load(f)
            # 如果文件存在，storage应该为空
            assert len(data.get('storage', {})) == 0