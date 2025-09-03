"""
测试加密工具模块
"""

import pytest
import os
import tempfile
from unittest.mock import patch, mock_open
from src.auto_study.config.encryption import EncryptionManager, get_encryption_manager


class TestEncryptionManager:
    """加密管理器测试"""
    
    @pytest.fixture
    def encryption_manager(self):
        """创建测试用加密管理器"""
        return EncryptionManager("test_master_key_12345")
    
    def test_encryption_manager_init(self, encryption_manager):
        """测试加密管理器初始化"""
        assert encryption_manager._master_key == "test_master_key_12345"
        assert encryption_manager._fernet is not None
    
    def test_encrypt_decrypt_string(self, encryption_manager):
        """测试字符串加密解密"""
        original_text = "这是一个测试密码"
        
        # 加密
        encrypted = encryption_manager.encrypt(original_text)
        assert encrypted != original_text
        assert isinstance(encrypted, str)
        
        # 解密
        decrypted = encryption_manager.decrypt(encrypted)
        assert decrypted == original_text
    
    def test_encrypt_decrypt_bytes(self, encryption_manager):
        """测试字节数据加密解密"""
        original_bytes = b"test password bytes"
        
        # 加密
        encrypted = encryption_manager.encrypt(original_bytes)
        assert encrypted != original_bytes.decode()
        assert isinstance(encrypted, str)
        
        # 解密
        decrypted = encryption_manager.decrypt(encrypted)
        assert decrypted == original_bytes.decode()
    
    def test_encrypt_dict_sensitive_fields(self, encryption_manager):
        """测试字典敏感字段加密"""
        original_dict = {
            "username": "test_user",
            "password": "secret_password",
            "api_key": "secret_api_key",
            "normal_field": "normal_value"
        }
        
        sensitive_keys = ["password", "api_key"]
        
        # 加密
        encrypted_dict = encryption_manager.encrypt_dict(original_dict, sensitive_keys)
        
        # 验证敏感字段被加密
        assert encrypted_dict["username"] == "test_user"  # 非敏感字段不变
        assert encrypted_dict["normal_field"] == "normal_value"
        assert encrypted_dict["password"].startswith("encrypted:")
        assert encrypted_dict["api_key"].startswith("encrypted:")
        assert encrypted_dict["password"] != "secret_password"
        assert encrypted_dict["api_key"] != "secret_api_key"
    
    def test_decrypt_dict_sensitive_fields(self, encryption_manager):
        """测试字典敏感字段解密"""
        # 先加密
        original_dict = {
            "username": "test_user",
            "password": "secret_password",
            "api_key": "secret_api_key"
        }
        
        sensitive_keys = ["password", "api_key"]
        encrypted_dict = encryption_manager.encrypt_dict(original_dict, sensitive_keys)
        
        # 解密
        decrypted_dict = encryption_manager.decrypt_dict(encrypted_dict, sensitive_keys)
        
        # 验证解密结果
        assert decrypted_dict == original_dict
    
    def test_nested_dict_encryption(self, encryption_manager):
        """测试嵌套字典加密"""
        original_dict = {
            "database": {
                "host": "localhost",
                "password": "db_password",
                "config": {
                    "secret": "nested_secret"
                }
            },
            "api": {
                "key": "api_secret"
            }
        }
        
        sensitive_keys = ["password", "secret", "key"]
        
        # 加密
        encrypted_dict = encryption_manager.encrypt_dict(original_dict, sensitive_keys)
        
        # 验证嵌套加密
        assert encrypted_dict["database"]["host"] == "localhost"  # 非敏感字段不变
        assert encrypted_dict["database"]["password"].startswith("encrypted:")
        assert encrypted_dict["database"]["config"]["secret"].startswith("encrypted:")
        assert encrypted_dict["api"]["key"].startswith("encrypted:")
        
        # 解密验证
        decrypted_dict = encryption_manager.decrypt_dict(encrypted_dict, sensitive_keys)
        assert decrypted_dict == original_dict
    
    def test_is_encrypted(self, encryption_manager):
        """测试加密检查"""
        # 普通字符串
        assert not encryption_manager.is_encrypted("normal_string")
        assert not encryption_manager.is_encrypted("encrypted_but_no_prefix")
        
        # 加密字符串
        assert encryption_manager.is_encrypted("encrypted:abcd1234")
        assert encryption_manager.is_encrypted("encrypted:")
    
    def test_verify_key(self, encryption_manager):
        """测试密钥验证"""
        assert encryption_manager.verify_key() is True
    
    def test_invalid_decryption(self, encryption_manager):
        """测试无效解密"""
        with pytest.raises(Exception):
            encryption_manager.decrypt("invalid_encrypted_data")
    
    def test_master_key_from_env(self):
        """测试从环境变量获取主密钥"""
        test_key = "env_master_key_12345"
        
        with patch.dict(os.environ, {'AUTO_STUDY_MASTER_KEY': test_key}):
            manager = EncryptionManager()
            assert manager._master_key == test_key
    
    @patch('builtins.open', new_callable=mock_open, read_data='file_master_key_12345')
    @patch('os.path.exists', return_value=True)
    def test_master_key_from_file(self, mock_exists, mock_file):
        """测试从文件获取主密钥"""
        with patch.dict(os.environ, {}, clear=True):
            manager = EncryptionManager()
            assert manager._master_key == 'file_master_key_12345'
    
    @patch('os.path.exists', return_value=False)
    @patch('builtins.open', new_callable=mock_open)
    @patch('os.chmod')
    @patch('os.urandom', return_value=b'random_bytes_for_testing_key_')
    def test_generate_new_master_key(self, mock_urandom, mock_chmod, mock_file, mock_exists):
        """测试生成新主密钥"""
        with patch.dict(os.environ, {}, clear=True):
            manager = EncryptionManager()
            
            # 验证文件写入调用
            mock_file.assert_called()
            mock_chmod.assert_called_once()
            
            # 验证密钥已设置
            assert manager._master_key is not None
            assert len(manager._master_key) > 0
    
    def test_rotate_key(self, encryption_manager):
        """测试密钥轮换"""
        old_key = encryption_manager._master_key
        new_key = "new_master_key_67890"
        
        # 先加密一些数据
        test_data = "test_data_for_rotation"
        encrypted_with_old_key = encryption_manager.encrypt(test_data)
        
        with patch('builtins.open', new_callable=mock_open), \
             patch('os.chmod'):
            # 轮换密钥
            encryption_manager.rotate_key(new_key)
            
            # 验证新密钥
            assert encryption_manager._master_key == new_key
            
            # 新密钥应该能正常工作
            new_encrypted = encryption_manager.encrypt(test_data)
            new_decrypted = encryption_manager.decrypt(new_encrypted)
            assert new_decrypted == test_data
    
    @patch('builtins.open', side_effect=Exception("写入失败"))
    def test_rotate_key_failure(self, mock_file, encryption_manager):
        """测试密钥轮换失败"""
        old_key = encryption_manager._master_key
        new_key = "new_key_that_fails"
        
        # 轮换应该失败
        with pytest.raises(Exception):
            encryption_manager.rotate_key(new_key)
        
        # 密钥应该恢复到原来的值
        assert encryption_manager._master_key == old_key
    
    def test_encryption_different_managers(self):
        """测试不同管理器实例的加密兼容性"""
        key = "shared_master_key_12345"
        
        manager1 = EncryptionManager(key)
        manager2 = EncryptionManager(key)
        
        test_data = "cross_manager_test"
        
        # 管理器1加密
        encrypted = manager1.encrypt(test_data)
        
        # 管理器2解密
        decrypted = manager2.decrypt(encrypted)
        
        assert decrypted == test_data


class TestGlobalEncryptionManager:
    """全局加密管理器测试"""
    
    def test_get_encryption_manager_singleton(self):
        """测试全局加密管理器单例模式"""
        # 重置全局实例
        import src.auto_study.config.encryption as enc_module
        enc_module._encryption_manager = None
        
        manager1 = get_encryption_manager("test_key_123")
        manager2 = get_encryption_manager("different_key")  # 应该被忽略
        
        # 应该是同一个实例
        assert manager1 is manager2
        assert manager1._master_key == "test_key_123"
    
    def test_convenience_functions(self):
        """测试便捷函数"""
        from src.auto_study.config.encryption import encrypt_sensitive_data, decrypt_sensitive_data
        
        # 重置全局实例
        import src.auto_study.config.encryption as enc_module
        enc_module._encryption_manager = None
        
        test_data = "convenience_function_test"
        
        # 加密
        encrypted = encrypt_sensitive_data(test_data)
        assert encrypted != test_data
        
        # 解密
        decrypted = decrypt_sensitive_data(encrypted)
        assert decrypted == test_data