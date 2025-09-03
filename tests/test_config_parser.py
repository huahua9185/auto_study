"""
测试配置文件解析器
"""

import pytest
import os
import yaml
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
from src.auto_study.config.config_parser import ConfigParser


class TestConfigParser:
    """配置文件解析器测试"""
    
    @pytest.fixture
    def parser(self):
        """创建配置解析器实例"""
        return ConfigParser()
    
    @pytest.fixture
    def temp_config_file(self):
        """创建临时配置文件"""
        config_data = {
            'database': {
                'host': 'localhost',
                'port': 5432,
                'password': 'secret_password'
            },
            'api': {
                'url': '${API_URL:http://localhost:8000}',
                'key': 'api_secret',
                'timeout': '${TIMEOUT:30}'
            },
            'debug': '${DEBUG:false}'
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            yaml.dump(config_data, f)
            temp_file_path = f.name
        
        yield temp_file_path
        
        # 清理
        os.unlink(temp_file_path)
    
    def test_load_config_success(self, parser, temp_config_file):
        """测试成功加载配置文件"""
        config = parser.load_config(temp_config_file)
        
        assert isinstance(config, dict)
        assert 'database' in config
        assert 'api' in config
        assert config['database']['host'] == 'localhost'
        assert config['database']['port'] == 5432
    
    def test_load_config_file_not_found(self, parser):
        """测试加载不存在的配置文件"""
        with pytest.raises(FileNotFoundError):
            parser.load_config('nonexistent_file.yml')
    
    def test_load_config_invalid_yaml(self, parser):
        """测试加载无效YAML文件"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            f.write('invalid: yaml: content: [')  # 无效YAML
            temp_file_path = f.name
        
        try:
            with pytest.raises(yaml.YAMLError):
                parser.load_config(temp_file_path)
        finally:
            os.unlink(temp_file_path)
    
    def test_load_empty_config_file(self, parser):
        """测试加载空配置文件"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            f.write('')  # 空文件
            temp_file_path = f.name
        
        try:
            config = parser.load_config(temp_file_path)
            assert config == {}
        finally:
            os.unlink(temp_file_path)
    
    @patch.dict(os.environ, {
        'API_URL': 'https://api.example.com',
        'DEBUG': 'true',
        'TIMEOUT': '60'
    })
    def test_replace_env_vars(self, parser, temp_config_file):
        """测试环境变量替换"""
        config = parser.load_config(temp_config_file)
        
        # 环境变量应该被替换
        assert config['api']['url'] == 'https://api.example.com'
        assert config['debug'] == 'true'
        assert config['api']['timeout'] == '60'
    
    def test_replace_env_vars_with_defaults(self, parser, temp_config_file):
        """测试环境变量默认值"""
        # 不设置环境变量，应该使用默认值
        with patch.dict(os.environ, {}, clear=True):
            config = parser.load_config(temp_config_file)
            
            assert config['api']['url'] == 'http://localhost:8000'
            assert config['debug'] == 'false'
            assert config['api']['timeout'] == '30'
    
    def test_decrypt_sensitive_fields(self, parser):
        """测试敏感字段解密"""
        # 创建包含加密字段的配置
        config_data = {
            'database': {
                'password': 'encrypted:test_encrypted_password'
            },
            'api': {
                'key': 'encrypted:test_encrypted_key',
                'url': 'http://example.com'  # 非敏感字段
            }
        }
        
        # Mock加密管理器
        mock_encryption_manager = MagicMock()
        mock_encryption_manager.decrypt.side_effect = lambda x: f"decrypted_{x}"
        parser.encryption_manager = mock_encryption_manager
        
        result = parser._decrypt_sensitive_fields(config_data)
        
        # 验证敏感字段被解密
        assert result['database']['password'] == 'decrypted_test_encrypted_password'
        assert result['api']['key'] == 'decrypted_test_encrypted_key'
        assert result['api']['url'] == 'http://example.com'  # 非敏感字段不变
    
    def test_encrypt_sensitive_fields(self, parser):
        """测试敏感字段加密"""
        config_data = {
            'database': {
                'password': 'plain_password'
            },
            'api': {
                'key': 'plain_api_key',
                'url': 'http://example.com'  # 非敏感字段
            }
        }
        
        # Mock加密管理器
        mock_encryption_manager = MagicMock()
        mock_encryption_manager.encrypt.side_effect = lambda x: f"encrypted_{x}"
        mock_encryption_manager.is_encrypted.return_value = False
        parser.encryption_manager = mock_encryption_manager
        
        result = parser._encrypt_sensitive_fields(config_data)
        
        # 验证敏感字段被加密
        assert result['database']['password'] == 'encrypted:encrypted_plain_password'
        assert result['api']['key'] == 'encrypted:encrypted_plain_api_key'
        assert result['api']['url'] == 'http://example.com'  # 非敏感字段不变
    
    def test_is_sensitive_key(self, parser):
        """测试敏感键检测"""
        # 敏感键
        assert parser._is_sensitive_key('password')
        assert parser._is_sensitive_key('PASSWORD')
        assert parser._is_sensitive_key('api_key')
        assert parser._is_sensitive_key('secret')
        assert parser._is_sensitive_key('token')
        assert parser._is_sensitive_key('user_password')
        
        # 非敏感键
        assert not parser._is_sensitive_key('username')
        assert not parser._is_sensitive_key('host')
        assert not parser._is_sensitive_key('port')
        assert not parser._is_sensitive_key('url')
    
    def test_save_config(self, parser):
        """测试保存配置"""
        config_data = {
            'username': 'test_user',  # 非敏感字段
            'nested': {
                'host': 'localhost'  # 非敏感字段
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            temp_file_path = f.name
        
        try:
            parser.save_config(config_data, temp_file_path)
            
            # 验证文件存在
            assert os.path.exists(temp_file_path)
            
            # 验证内容正确（非敏感字段不会被加密）
            with open(temp_file_path, 'r') as f:
                saved_data = yaml.safe_load(f)
            
            assert saved_data['username'] == 'test_user'
            assert saved_data['nested']['host'] == 'localhost'
        finally:
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
    
    def test_merge_configs(self, parser):
        """测试配置合并"""
        config1 = {
            'a': 1,
            'b': {
                'x': 10,
                'y': 20
            },
            'c': [1, 2, 3]
        }
        
        config2 = {
            'a': 2,  # 覆盖
            'b': {
                'x': 30,  # 覆盖
                'z': 40   # 新增
            },
            'd': 4  # 新增
        }
        
        config3 = {
            'b': {
                'x': 50  # 再次覆盖
            },
            'e': 5
        }
        
        merged = parser.merge_configs(config1, config2, config3)
        
        assert merged['a'] == 2
        assert merged['b']['x'] == 50
        assert merged['b']['y'] == 20
        assert merged['b']['z'] == 40
        assert merged['c'] == [1, 2, 3]
        assert merged['d'] == 4
        assert merged['e'] == 5
    
    def test_deep_merge(self, parser):
        """测试深度合并"""
        base = {
            'level1': {
                'level2': {
                    'keep': 'original',
                    'override': 'old_value'
                }
            }
        }
        
        override = {
            'level1': {
                'level2': {
                    'override': 'new_value',
                    'new_key': 'new_value'
                }
            }
        }
        
        result = parser._deep_merge(base, override)
        
        assert result['level1']['level2']['keep'] == 'original'
        assert result['level1']['level2']['override'] == 'new_value'
        assert result['level1']['level2']['new_key'] == 'new_value'
    
    def test_replace_env_vars_complex_cases(self, parser):
        """测试复杂的环境变量替换情况"""
        test_cases = [
            ('${VAR1}', {'VAR1': 'value1'}, 'value1'),
            ('${VAR2:default}', {}, 'default'),
            ('prefix_${VAR3}_suffix', {'VAR3': 'middle'}, 'prefix_middle_suffix'),
            ('${MISSING_VAR}', {}, '${MISSING_VAR}'),  # 缺失变量保持原样
            ('no_vars_here', {}, 'no_vars_here'),
        ]
        
        for input_str, env_vars, expected in test_cases:
            with patch.dict(os.environ, env_vars, clear=True):
                result = parser._replace_env_vars_in_string(input_str)
                assert result == expected, f"Input: {input_str}, Expected: {expected}, Got: {result}"
    
    def test_get_config_diff(self, parser):
        """测试配置差异比较"""
        config1 = {
            'keep': 'same',
            'change': 'old_value',
            'remove': 'will_be_removed',
            'nested': {
                'keep': 'same',
                'change': 'old_nested'
            }
        }
        
        config2 = {
            'keep': 'same',
            'change': 'new_value',
            'add': 'new_value',
            'nested': {
                'keep': 'same',
                'change': 'new_nested',
                'add_nested': 'new_nested_value'
            }
        }
        
        diff = parser.get_config_diff(config1, config2)
        
        # 验证新增
        assert 'add' in diff['added']
        assert 'nested.add_nested' in diff['added']
        
        # 验证删除
        assert 'remove' in diff['removed']
        
        # 验证修改
        assert 'change' in diff['changed']
        assert 'nested.change' in diff['changed']
        assert diff['changed']['change']['old'] == 'old_value'
        assert diff['changed']['change']['new'] == 'new_value'