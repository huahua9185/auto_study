"""
加密工具模块

提供敏感信息的AES加密和解密功能
"""

import os
import base64
from typing import Union, Optional
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from ..utils.logger import logger


class EncryptionManager:
    """加密管理器"""
    
    def __init__(self, master_key: Optional[str] = None):
        """
        初始化加密管理器
        
        Args:
            master_key: 主密钥，如果未提供则使用环境变量或生成
        """
        self._fernet = None
        self._master_key = master_key or self._get_or_create_master_key()
        self._initialize_fernet()
    
    def _get_or_create_master_key(self) -> str:
        """获取或创建主密钥"""
        # 首先尝试从环境变量获取
        master_key = os.getenv('AUTO_STUDY_MASTER_KEY')
        if master_key:
            return master_key
        
        # 尝试从密钥文件读取
        key_file = '.auto_study_key'
        if os.path.exists(key_file):
            try:
                with open(key_file, 'r') as f:
                    return f.read().strip()
            except Exception as e:
                logger.warning(f"无法读取密钥文件: {e}")
        
        # 生成新的主密钥
        master_key = base64.urlsafe_b64encode(os.urandom(32)).decode()
        
        # 保存到文件
        try:
            with open(key_file, 'w') as f:
                f.write(master_key)
            os.chmod(key_file, 0o600)  # 仅所有者可读写
            logger.info("已生成新的主密钥")
        except Exception as e:
            logger.warning(f"无法保存密钥文件: {e}")
        
        return master_key
    
    def _initialize_fernet(self) -> None:
        """初始化Fernet加密器"""
        try:
            # 使用PBKDF2从主密钥派生密钥
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=b'auto_study_salt',  # 固定盐值
                iterations=100000,
            )
            key = base64.urlsafe_b64encode(
                kdf.derive(self._master_key.encode())
            )
            self._fernet = Fernet(key)
        except Exception as e:
            logger.error(f"初始化加密器失败: {e}")
            raise
    
    def encrypt(self, data: Union[str, bytes]) -> str:
        """
        加密数据
        
        Args:
            data: 要加密的数据
            
        Returns:
            加密后的base64编码字符串
        """
        try:
            if isinstance(data, str):
                data = data.encode('utf-8')
            
            encrypted_data = self._fernet.encrypt(data)
            return base64.urlsafe_b64encode(encrypted_data).decode('utf-8')
            
        except Exception as e:
            logger.error(f"数据加密失败: {e}")
            raise
    
    def decrypt(self, encrypted_data: str) -> str:
        """
        解密数据
        
        Args:
            encrypted_data: 加密的base64字符串
            
        Returns:
            解密后的原始字符串
        """
        try:
            encrypted_bytes = base64.urlsafe_b64decode(encrypted_data.encode('utf-8'))
            decrypted_bytes = self._fernet.decrypt(encrypted_bytes)
            return decrypted_bytes.decode('utf-8')
            
        except Exception as e:
            logger.error(f"数据解密失败: {e}")
            raise
    
    def encrypt_dict(self, data: dict, sensitive_keys: list[str]) -> dict:
        """
        加密字典中的敏感字段
        
        Args:
            data: 要处理的字典
            sensitive_keys: 需要加密的键列表
            
        Returns:
            处理后的字典，敏感字段被加密
        """
        result = {}
        
        for key, value in data.items():
            if key in sensitive_keys and isinstance(value, str):
                result[key] = f"encrypted:{self.encrypt(value)}"
            elif isinstance(value, dict):
                result[key] = self.encrypt_dict(value, sensitive_keys)
            else:
                result[key] = value
        
        return result
    
    def decrypt_dict(self, data: dict, sensitive_keys: list[str]) -> dict:
        """
        解密字典中的敏感字段
        
        Args:
            data: 要处理的字典
            sensitive_keys: 需要解密的键列表
            
        Returns:
            处理后的字典，敏感字段被解密
        """
        result = {}
        
        for key, value in data.items():
            if (key in sensitive_keys and 
                isinstance(value, str) and 
                value.startswith("encrypted:")):
                encrypted_value = value[10:]  # 移除 "encrypted:" 前缀
                result[key] = self.decrypt(encrypted_value)
            elif isinstance(value, dict):
                result[key] = self.decrypt_dict(value, sensitive_keys)
            else:
                result[key] = value
        
        return result
    
    def is_encrypted(self, value: str) -> bool:
        """
        检查值是否已加密
        
        Args:
            value: 要检查的值
            
        Returns:
            如果值已加密返回True
        """
        return isinstance(value, str) and value.startswith("encrypted:")
    
    def rotate_key(self, new_master_key: str) -> None:
        """
        轮换主密钥
        
        Args:
            new_master_key: 新的主密钥
        """
        old_master_key = self._master_key
        old_fernet = self._fernet
        
        # 设置新密钥
        self._master_key = new_master_key
        self._initialize_fernet()
        
        # 保存新密钥到文件
        key_file = '.auto_study_key'
        try:
            with open(key_file, 'w') as f:
                f.write(new_master_key)
            os.chmod(key_file, 0o600)
            logger.info("主密钥已轮换")
        except Exception as e:
            # 恢复旧密钥
            self._master_key = old_master_key
            self._fernet = old_fernet
            logger.error(f"密钥轮换失败: {e}")
            raise
    
    def verify_key(self) -> bool:
        """
        验证密钥是否有效
        
        Returns:
            密钥有效返回True
        """
        try:
            test_data = "test_encryption"
            encrypted = self.encrypt(test_data)
            decrypted = self.decrypt(encrypted)
            return decrypted == test_data
        except Exception:
            return False


# 全局加密管理器实例
_encryption_manager = None


def get_encryption_manager(master_key: Optional[str] = None) -> EncryptionManager:
    """
    获取全局加密管理器实例
    
    Args:
        master_key: 主密钥（仅首次调用时有效）
        
    Returns:
        加密管理器实例
    """
    global _encryption_manager
    
    if _encryption_manager is None:
        _encryption_manager = EncryptionManager(master_key)
    
    return _encryption_manager


def encrypt_sensitive_data(data: str) -> str:
    """
    加密敏感数据的便捷函数
    
    Args:
        data: 要加密的数据
        
    Returns:
        加密后的数据
    """
    return get_encryption_manager().encrypt(data)


def decrypt_sensitive_data(encrypted_data: str) -> str:
    """
    解密敏感数据的便捷函数
    
    Args:
        encrypted_data: 加密的数据
        
    Returns:
        解密后的数据
    """
    return get_encryption_manager().decrypt(encrypted_data)