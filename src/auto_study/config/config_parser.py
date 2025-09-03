"""
配置文件解析器

支持YAML配置文件解析、环境变量替换、配置合并等功能
"""

import os
import re
import yaml
from typing import Any, Dict, List, Optional, Union
from pathlib import Path
from ..utils.logger import logger
from .encryption import get_encryption_manager


class ConfigParser:
    """配置文件解析器"""
    
    def __init__(self):
        self.encryption_manager = get_encryption_manager()
        self._env_var_pattern = re.compile(r'\$\{([^}]+)\}')
        
        # 敏感字段列表
        self.sensitive_keys = [
            'password', 'pwd', 'secret', 'key', 'token', 'api_key',
            'access_key', 'private_key', 'credential', 'auth'
        ]
    
    def load_config(self, config_path: Union[str, Path]) -> Dict[str, Any]:
        """
        加载配置文件
        
        Args:
            config_path: 配置文件路径
            
        Returns:
            解析后的配置字典
        """
        config_path = Path(config_path)
        
        if not config_path.exists():
            raise FileNotFoundError(f"配置文件不存在: {config_path}")
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                raw_config = yaml.safe_load(f)
            
            if raw_config is None:
                raw_config = {}
            
            # 环境变量替换
            config = self._replace_env_vars(raw_config)
            
            # 解密敏感字段
            config = self._decrypt_sensitive_fields(config)
            
            logger.info(f"成功加载配置文件: {config_path}")
            return config
            
        except yaml.YAMLError as e:
            logger.error(f"YAML解析错误: {e}")
            raise
        except Exception as e:
            logger.error(f"加载配置文件失败: {e}")
            raise
    
    def save_config(self, config: Dict[str, Any], config_path: Union[str, Path]) -> None:
        """
        保存配置到文件
        
        Args:
            config: 配置字典
            config_path: 配置文件路径
        """
        config_path = Path(config_path)
        
        try:
            # 加密敏感字段
            encrypted_config = self._encrypt_sensitive_fields(config)
            
            # 确保目录存在
            config_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(config_path, 'w', encoding='utf-8') as f:
                yaml.dump(
                    encrypted_config,
                    f,
                    default_flow_style=False,
                    allow_unicode=True,
                    indent=2,
                    sort_keys=False
                )
            
            logger.info(f"配置文件已保存: {config_path}")
            
        except Exception as e:
            logger.error(f"保存配置文件失败: {e}")
            raise
    
    def merge_configs(self, *configs: Dict[str, Any]) -> Dict[str, Any]:
        """
        合并多个配置字典
        
        Args:
            configs: 要合并的配置字典列表
            
        Returns:
            合并后的配置字典
        """
        result = {}
        
        for config in configs:
            if not isinstance(config, dict):
                continue
            result = self._deep_merge(result, config)
        
        return result
    
    def _deep_merge(self, base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """
        深度合并两个字典
        
        Args:
            base: 基础字典
            override: 覆盖字典
            
        Returns:
            合并后的字典
        """
        result = base.copy()
        
        for key, value in override.items():
            if (key in result and 
                isinstance(result[key], dict) and 
                isinstance(value, dict)):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        
        return result
    
    def _replace_env_vars(self, data: Any) -> Any:
        """
        替换配置中的环境变量
        
        Args:
            data: 要处理的数据
            
        Returns:
            处理后的数据
        """
        if isinstance(data, str):
            return self._replace_env_vars_in_string(data)
        elif isinstance(data, dict):
            return {key: self._replace_env_vars(value) for key, value in data.items()}
        elif isinstance(data, list):
            return [self._replace_env_vars(item) for item in data]
        else:
            return data
    
    def _replace_env_vars_in_string(self, text: str) -> str:
        """
        替换字符串中的环境变量
        
        Args:
            text: 包含环境变量的字符串
            
        Returns:
            替换后的字符串
        """
        def replace_match(match):
            var_name = match.group(1)
            
            # 支持默认值语法: ${VAR_NAME:default_value}
            if ':' in var_name:
                var_name, default_value = var_name.split(':', 1)
                return os.getenv(var_name, default_value)
            else:
                return os.getenv(var_name, match.group(0))  # 如果变量不存在，保持原样
        
        return self._env_var_pattern.sub(replace_match, text)
    
    def _encrypt_sensitive_fields(self, data: Any) -> Any:
        """
        加密敏感字段
        
        Args:
            data: 要处理的数据
            
        Returns:
            处理后的数据
        """
        if isinstance(data, dict):
            result = {}
            for key, value in data.items():
                if self._is_sensitive_key(key) and isinstance(value, str):
                    if not self.encryption_manager.is_encrypted(value):
                        result[key] = f"encrypted:{self.encryption_manager.encrypt(value)}"
                    else:
                        result[key] = value
                else:
                    result[key] = self._encrypt_sensitive_fields(value)
            return result
        elif isinstance(data, list):
            return [self._encrypt_sensitive_fields(item) for item in data]
        else:
            return data
    
    def _decrypt_sensitive_fields(self, data: Any) -> Any:
        """
        解密敏感字段
        
        Args:
            data: 要处理的数据
            
        Returns:
            处理后的数据
        """
        if isinstance(data, dict):
            result = {}
            for key, value in data.items():
                if (self._is_sensitive_key(key) and 
                    isinstance(value, str) and 
                    value.startswith("encrypted:")):
                    encrypted_value = value[10:]  # 移除 "encrypted:" 前缀
                    try:
                        result[key] = self.encryption_manager.decrypt(encrypted_value)
                    except Exception as e:
                        logger.error(f"解密字段 {key} 失败: {e}")
                        result[key] = value
                else:
                    result[key] = self._decrypt_sensitive_fields(value)
            return result
        elif isinstance(data, list):
            return [self._decrypt_sensitive_fields(item) for item in data]
        else:
            return data
    
    def _is_sensitive_key(self, key: str) -> bool:
        """
        检查键是否为敏感字段
        
        Args:
            key: 要检查的键
            
        Returns:
            是敏感字段返回True
        """
        key_lower = key.lower()
        return any(sensitive in key_lower for sensitive in self.sensitive_keys)
    
    def validate_config_structure(self, config: Dict[str, Any], schema: Dict[str, Any]) -> List[str]:
        """
        验证配置结构
        
        Args:
            config: 要验证的配置
            schema: 配置模式
            
        Returns:
            验证错误列表
        """
        errors = []
        
        def validate_recursive(data: Any, schema_data: Any, path: str = ""):
            if isinstance(schema_data, dict):
                if not isinstance(data, dict):
                    errors.append(f"{path}: 期望字典类型")
                    return
                
                for key, value_schema in schema_data.items():
                    current_path = f"{path}.{key}" if path else key
                    
                    if key.startswith('__'):  # 元数据键
                        continue
                    
                    required = schema_data.get('__required__', [])
                    if key in required and key not in data:
                        errors.append(f"{current_path}: 必需字段缺失")
                        continue
                    
                    if key in data:
                        validate_recursive(data[key], value_schema, current_path)
            
            elif isinstance(schema_data, list) and len(schema_data) > 0:
                if not isinstance(data, list):
                    errors.append(f"{path}: 期望列表类型")
                    return
                
                item_schema = schema_data[0]
                for i, item in enumerate(data):
                    validate_recursive(item, item_schema, f"{path}[{i}]")
            
            elif isinstance(schema_data, type):
                if not isinstance(data, schema_data):
                    errors.append(f"{path}: 期望 {schema_data.__name__} 类型")
        
        validate_recursive(config, schema)
        return errors
    
    def get_config_diff(self, config1: Dict[str, Any], config2: Dict[str, Any]) -> Dict[str, Any]:
        """
        比较两个配置的差异
        
        Args:
            config1: 配置1
            config2: 配置2
            
        Returns:
            差异字典
        """
        diff = {
            'added': {},
            'removed': {},
            'changed': {}
        }
        
        def compare_recursive(data1: Any, data2: Any, path: str = ""):
            if isinstance(data1, dict) and isinstance(data2, dict):
                # 检查新增的键
                for key in data2:
                    if key not in data1:
                        current_path = f"{path}.{key}" if path else key
                        diff['added'][current_path] = data2[key]
                
                # 检查删除的键
                for key in data1:
                    if key not in data2:
                        current_path = f"{path}.{key}" if path else key
                        diff['removed'][current_path] = data1[key]
                
                # 检查修改的键
                for key in data1:
                    if key in data2:
                        current_path = f"{path}.{key}" if path else key
                        if data1[key] != data2[key]:
                            if isinstance(data1[key], dict) and isinstance(data2[key], dict):
                                compare_recursive(data1[key], data2[key], current_path)
                            else:
                                diff['changed'][current_path] = {
                                    'old': data1[key],
                                    'new': data2[key]
                                }
            else:
                if data1 != data2:
                    diff['changed'][path or 'root'] = {
                        'old': data1,
                        'new': data2
                    }
        
        compare_recursive(config1, config2)
        return diff