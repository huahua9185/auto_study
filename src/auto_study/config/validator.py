"""
配置验证器

提供配置的结构验证、类型检查、约束验证等功能
"""

import re
from typing import Any, Dict, List, Optional, Union, Callable, Type
from enum import Enum
from ..utils.logger import logger


class ValidationLevel(Enum):
    """验证级别"""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class ValidationResult:
    """验证结果"""
    
    def __init__(self):
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.info: List[str] = []
    
    def add_error(self, message: str) -> None:
        """添加错误"""
        self.errors.append(message)
    
    def add_warning(self, message: str) -> None:
        """添加警告"""
        self.warnings.append(message)
    
    def add_info(self, message: str) -> None:
        """添加信息"""
        self.info.append(message)
    
    def is_valid(self) -> bool:
        """是否验证通过（无错误）"""
        return len(self.errors) == 0
    
    def get_all_messages(self) -> List[str]:
        """获取所有消息"""
        messages = []
        for error in self.errors:
            messages.append(f"ERROR: {error}")
        for warning in self.warnings:
            messages.append(f"WARNING: {warning}")
        for info in self.info:
            messages.append(f"INFO: {info}")
        return messages


class ConfigValidator:
    """配置验证器"""
    
    def __init__(self):
        self.validators: Dict[str, Callable] = {
            '__type__': self._validate_type,
            'type': self._validate_type,
            'required': self._validate_required,
            'min': self._validate_min,
            'max': self._validate_max,
            'min_length': self._validate_min_length,
            'max_length': self._validate_max_length,
            'pattern': self._validate_pattern,
            'choices': self._validate_choices,
            'range': self._validate_range,
            'url': self._validate_url,
            'email': self._validate_email,
            'port': self._validate_port,
            'directory': self._validate_directory,
            'file': self._validate_file,
            'custom': self._validate_custom
        }
    
    def validate(self, config: Dict[str, Any], schema: Dict[str, Any]) -> ValidationResult:
        """
        验证配置
        
        Args:
            config: 要验证的配置
            schema: 验证模式
            
        Returns:
            验证结果
        """
        result = ValidationResult()
        self._validate_recursive(config, schema, result, "")
        return result
    
    def _validate_recursive(self, data: Any, schema: Any, result: ValidationResult, path: str) -> None:
        """
        递归验证配置
        
        Args:
            data: 要验证的数据
            schema: 验证模式
            result: 验证结果
            path: 当前路径
        """
        if isinstance(schema, dict):
            if '__type__' in schema:
                # 基本类型验证
                self._validate_field(data, schema, result, path)
            else:
                # 对象验证
                if not isinstance(data, dict):
                    result.add_error(f"{path}: 期望字典类型，实际为 {type(data).__name__}")
                    return
                
                # 验证必需字段
                required_fields = schema.get('__required__', [])
                for field in required_fields:
                    if field not in data:
                        result.add_error(f"{path}.{field}: 必需字段缺失")
                
                # 验证各字段
                for key, value_schema in schema.items():
                    if key.startswith('__'):  # 元数据键
                        continue
                    
                    current_path = f"{path}.{key}" if path else key
                    
                    if key in data:
                        self._validate_recursive(data[key], value_schema, result, current_path)
                    elif key not in required_fields:
                        # 可选字段，检查是否有默认值
                        if isinstance(value_schema, dict) and '__default__' in value_schema:
                            result.add_info(f"{current_path}: 使用默认值 {value_schema['__default__']}")
        
        elif isinstance(schema, list) and len(schema) > 0:
            # 数组验证
            if not isinstance(data, list):
                result.add_error(f"{path}: 期望列表类型，实际为 {type(data).__name__}")
                return
            
            item_schema = schema[0]
            for i, item in enumerate(data):
                self._validate_recursive(item, item_schema, result, f"{path}[{i}]")
    
    def _validate_field(self, value: Any, schema: Dict[str, Any], result: ValidationResult, path: str) -> None:
        """
        验证单个字段
        
        Args:
            value: 要验证的值
            schema: 字段模式
            result: 验证结果
            path: 字段路径
        """
        for rule_name, rule_value in schema.items():
            if rule_name.startswith('__') and rule_name not in ['__type__']:
                continue
            
            if rule_name in self.validators:
                try:
                    self.validators[rule_name](value, rule_value, result, path)
                except Exception as e:
                    result.add_error(f"{path}: 验证规则 {rule_name} 执行失败: {e}")
    
    def _validate_type(self, value: Any, expected_type: Union[Type, str], result: ValidationResult, path: str) -> None:
        """验证类型"""
        if isinstance(expected_type, str):
            type_map = {
                'str': str,
                'int': int,
                'float': float,
                'bool': bool,
                'list': list,
                'dict': dict,
                'any': object
            }
            expected_type = type_map.get(expected_type, str)
        
        if expected_type == object:  # any type
            return
        
        if not isinstance(value, expected_type):
            result.add_error(f"{path}: 期望 {expected_type.__name__} 类型，实际为 {type(value).__name__}")
    
    def _validate_required(self, value: Any, is_required: bool, result: ValidationResult, path: str) -> None:
        """验证必需字段"""
        if is_required and (value is None or value == ""):
            result.add_error(f"{path}: 必需字段不能为空")
    
    def _validate_min(self, value: Any, min_value: Union[int, float], result: ValidationResult, path: str) -> None:
        """验证最小值"""
        if isinstance(value, (int, float)) and value < min_value:
            result.add_error(f"{path}: 值 {value} 小于最小值 {min_value}")
    
    def _validate_max(self, value: Any, max_value: Union[int, float], result: ValidationResult, path: str) -> None:
        """验证最大值"""
        if isinstance(value, (int, float)) and value > max_value:
            result.add_error(f"{path}: 值 {value} 大于最大值 {max_value}")
    
    def _validate_min_length(self, value: Any, min_length: int, result: ValidationResult, path: str) -> None:
        """验证最小长度"""
        if hasattr(value, '__len__') and len(value) < min_length:
            result.add_error(f"{path}: 长度 {len(value)} 小于最小长度 {min_length}")
    
    def _validate_max_length(self, value: Any, max_length: int, result: ValidationResult, path: str) -> None:
        """验证最大长度"""
        if hasattr(value, '__len__') and len(value) > max_length:
            result.add_error(f"{path}: 长度 {len(value)} 大于最大长度 {max_length}")
    
    def _validate_pattern(self, value: Any, pattern: str, result: ValidationResult, path: str) -> None:
        """验证正则表达式模式"""
        if isinstance(value, str):
            if not re.match(pattern, value):
                result.add_error(f"{path}: 值 '{value}' 不匹配模式 '{pattern}'")
    
    def _validate_choices(self, value: Any, choices: List[Any], result: ValidationResult, path: str) -> None:
        """验证选择值"""
        if value not in choices:
            result.add_error(f"{path}: 值 '{value}' 不在允许的选择中: {choices}")
    
    def _validate_range(self, value: Any, range_spec: tuple, result: ValidationResult, path: str) -> None:
        """验证范围"""
        if isinstance(value, (int, float)) and len(range_spec) == 2:
            min_val, max_val = range_spec
            if not (min_val <= value <= max_val):
                result.add_error(f"{path}: 值 {value} 不在范围 [{min_val}, {max_val}] 内")
    
    def _validate_url(self, value: Any, is_url: bool, result: ValidationResult, path: str) -> None:
        """验证URL格式"""
        if is_url and isinstance(value, str):
            url_pattern = re.compile(
                r'^https?://'  # http:// or https://
                r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
                r'localhost|'  # localhost...
                r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
                r'(?::\d+)?'  # optional port
                r'(?:/?|[/?]\S+)$', re.IGNORECASE)
            
            if not url_pattern.match(value):
                result.add_error(f"{path}: 无效的URL格式: {value}")
    
    def _validate_email(self, value: Any, is_email: bool, result: ValidationResult, path: str) -> None:
        """验证邮箱格式"""
        if is_email and isinstance(value, str):
            email_pattern = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
            if not email_pattern.match(value):
                result.add_error(f"{path}: 无效的邮箱格式: {value}")
    
    def _validate_port(self, value: Any, is_port: bool, result: ValidationResult, path: str) -> None:
        """验证端口号"""
        if is_port and isinstance(value, int):
            if not (1 <= value <= 65535):
                result.add_error(f"{path}: 无效的端口号: {value}")
    
    def _validate_directory(self, value: Any, is_directory: bool, result: ValidationResult, path: str) -> None:
        """验证目录路径"""
        if is_directory and isinstance(value, str):
            from pathlib import Path
            if not Path(value).is_dir():
                result.add_warning(f"{path}: 目录不存在: {value}")
    
    def _validate_file(self, value: Any, is_file: bool, result: ValidationResult, path: str) -> None:
        """验证文件路径"""
        if is_file and isinstance(value, str):
            from pathlib import Path
            if not Path(value).is_file():
                result.add_warning(f"{path}: 文件不存在: {value}")
    
    def _validate_custom(self, value: Any, validator_func: Callable, result: ValidationResult, path: str) -> None:
        """自定义验证"""
        try:
            error_message = validator_func(value)
            if error_message:
                result.add_error(f"{path}: {error_message}")
        except Exception as e:
            result.add_error(f"{path}: 自定义验证失败: {e}")


def create_auto_study_schema() -> Dict[str, Any]:
    """
    创建自动学习系统的配置模式
    
    Returns:
        配置验证模式
    """
    return {
        '__required__': ['browser', 'login', 'system'],
        
        'browser': {
            '__required__': ['headless'],
            'headless': {'__type__': 'bool'},
            'width': {'__type__': 'int', 'min': 800, 'max': 3840, '__default__': 1920},
            'height': {'__type__': 'int', 'min': 600, 'max': 2160, '__default__': 1080},
            'timeout': {'__type__': 'int', 'min': 1000, 'max': 120000, '__default__': 30000},
            'user_agent': {'__type__': 'str', 'min_length': 10}
        },
        
        'login': {
            '__required__': ['max_retries'],
            'max_retries': {'__type__': 'int', 'min': 1, 'max': 10},
            'retry_delay': {'__type__': 'int', 'min': 1, 'max': 60, '__default__': 5},
            'captcha_timeout': {'__type__': 'int', 'min': 10, 'max': 120, '__default__': 30}
        },
        
        'learning': {
            'check_interval': {'__type__': 'int', 'min': 5, 'max': 300, '__default__': 30},
            'human_behavior': {'__type__': 'bool', '__default__': True},
            'auto_handle_popups': {'__type__': 'bool', '__default__': True},
            'max_learning_time': {'__type__': 'int', 'min': 3600, '__default__': 28800}  # 1-8小时
        },
        
        'system': {
            '__required__': ['log_level'],
            'log_level': {
                '__type__': 'str',
                'choices': ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
            },
            'log_file': {'__type__': 'str', '__default__': 'logs/auto_study.log'},
            'data_dir': {'__type__': 'str', '__default__': 'data'},
            'max_log_size': {'__type__': 'int', 'min': 1048576, '__default__': 10485760},  # 1MB-默认10MB
            'backup_count': {'__type__': 'int', 'min': 1, 'max': 20, '__default__': 5}
        },
        
        'credentials': {
            'username': {'__type__': 'str', 'min_length': 1},
            'password': {'__type__': 'str', 'min_length': 1}
        },
        
        'site': {
            'url': {'__type__': 'str', 'url': True, '__default__': 'https://edu.nxgbjy.org.cn'},
            'login_url': {'__type__': 'str', 'url': True},
            'courses_url': {'__type__': 'str', 'url': True}
        }
    }


# 全局验证器实例
validator = ConfigValidator()