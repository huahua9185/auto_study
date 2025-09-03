"""
测试配置验证器
"""

import pytest
from src.auto_study.config.validator import (
    ConfigValidator, ValidationResult, ValidationLevel,
    create_auto_study_schema, validator
)


class TestValidationResult:
    """验证结果测试"""
    
    def test_validation_result_init(self):
        """测试验证结果初始化"""
        result = ValidationResult()
        
        assert len(result.errors) == 0
        assert len(result.warnings) == 0
        assert len(result.info) == 0
        assert result.is_valid() is True
    
    def test_add_messages(self):
        """测试添加消息"""
        result = ValidationResult()
        
        result.add_error("错误消息")
        result.add_warning("警告消息")
        result.add_info("信息消息")
        
        assert len(result.errors) == 1
        assert len(result.warnings) == 1
        assert len(result.info) == 1
        assert result.is_valid() is False  # 有错误
    
    def test_get_all_messages(self):
        """测试获取所有消息"""
        result = ValidationResult()
        
        result.add_error("错误消息")
        result.add_warning("警告消息")
        result.add_info("信息消息")
        
        messages = result.get_all_messages()
        
        assert len(messages) == 3
        assert "ERROR: 错误消息" in messages
        assert "WARNING: 警告消息" in messages
        assert "INFO: 信息消息" in messages


class TestConfigValidator:
    """配置验证器测试"""
    
    @pytest.fixture
    def validator_instance(self):
        """创建验证器实例"""
        return ConfigValidator()
    
    def test_validate_type_success(self, validator_instance):
        """测试类型验证成功"""
        schema = {
            'name': {'__type__': 'str'},
            'age': {'__type__': 'int'},
            'active': {'__type__': 'bool'},
            'items': {'__type__': 'list'},
            'config': {'__type__': 'dict'}
        }
        
        config = {
            'name': 'test',
            'age': 25,
            'active': True,
            'items': [1, 2, 3],
            'config': {'key': 'value'}
        }
        
        result = validator_instance.validate(config, schema)
        assert result.is_valid()
    
    def test_validate_type_failure(self, validator_instance):
        """测试类型验证失败"""
        schema = {
            'name': {'__type__': 'str'},
            'age': {'__type__': 'int'}
        }
        
        config = {
            'name': 123,  # 错误类型
            'age': 'not_a_number'  # 错误类型
        }
        
        result = validator_instance.validate(config, schema)
        assert not result.is_valid()
        assert len(result.errors) == 2
    
    def test_validate_required_fields(self, validator_instance):
        """测试必需字段验证"""
        schema = {
            '__required__': ['name', 'email'],
            'name': {'__type__': 'str'},
            'email': {'__type__': 'str'},
            'optional': {'__type__': 'str'}
        }
        
        # 缺少必需字段
        config = {
            'name': 'test'
            # 缺少 email
        }
        
        result = validator_instance.validate(config, schema)
        assert not result.is_valid()
        assert any('email' in error and '必需字段缺失' in error for error in result.errors)
    
    def test_validate_min_max_values(self, validator_instance):
        """测试最小最大值验证"""
        schema = {
            'score': {'__type__': 'int', 'min': 0, 'max': 100},
            'temperature': {'__type__': 'float', 'min': -273.15}
        }
        
        # 有效配置
        valid_config = {
            'score': 85,
            'temperature': 23.5
        }
        
        result = validator_instance.validate(valid_config, schema)
        assert result.is_valid()
        
        # 无效配置
        invalid_config = {
            'score': 150,  # 超出最大值
            'temperature': -300.0  # 低于最小值
        }
        
        result = validator_instance.validate(invalid_config, schema)
        assert not result.is_valid()
        assert len(result.errors) == 2
    
    def test_validate_string_length(self, validator_instance):
        """测试字符串长度验证"""
        schema = {
            'username': {'__type__': 'str', 'min_length': 3, 'max_length': 20},
            'description': {'__type__': 'str', 'max_length': 100}
        }
        
        # 有效配置
        valid_config = {
            'username': 'testuser',
            'description': '这是一个测试描述'
        }
        
        result = validator_instance.validate(valid_config, schema)
        assert result.is_valid()
        
        # 无效配置
        invalid_config = {
            'username': 'ab',  # 太短
            'description': 'x' * 101  # 太长
        }
        
        result = validator_instance.validate(invalid_config, schema)
        assert not result.is_valid()
        assert len(result.errors) == 2
    
    def test_validate_pattern(self, validator_instance):
        """测试正则表达式验证"""
        schema = {
            'email': {'__type__': 'str', 'pattern': r'^[^@]+@[^@]+\.[^@]+$'},
            'phone': {'__type__': 'str', 'pattern': r'^\d{11}$'}
        }
        
        # 有效配置
        valid_config = {
            'email': 'test@example.com',
            'phone': '13800138000'
        }
        
        result = validator_instance.validate(valid_config, schema)
        assert result.is_valid()
        
        # 无效配置
        invalid_config = {
            'email': 'invalid-email',
            'phone': '138001380001'  # 12位数字
        }
        
        result = validator_instance.validate(invalid_config, schema)
        assert not result.is_valid()
        assert len(result.errors) == 2
    
    def test_validate_choices(self, validator_instance):
        """测试选择值验证"""
        schema = {
            'level': {'__type__': 'str', 'choices': ['DEBUG', 'INFO', 'WARNING', 'ERROR']},
            'priority': {'__type__': 'int', 'choices': [1, 2, 3, 4, 5]}
        }
        
        # 有效配置
        valid_config = {
            'level': 'INFO',
            'priority': 3
        }
        
        result = validator_instance.validate(valid_config, schema)
        assert result.is_valid()
        
        # 无效配置
        invalid_config = {
            'level': 'TRACE',  # 不在选择中
            'priority': 10     # 不在选择中
        }
        
        result = validator_instance.validate(invalid_config, schema)
        assert not result.is_valid()
        assert len(result.errors) == 2
    
    def test_validate_range(self, validator_instance):
        """测试范围验证"""
        schema = {
            'percentage': {'__type__': 'float', 'range': (0.0, 100.0)},
            'port': {'__type__': 'int', 'range': (1, 65535)}
        }
        
        # 有效配置
        valid_config = {
            'percentage': 85.5,
            'port': 8080
        }
        
        result = validator_instance.validate(valid_config, schema)
        assert result.is_valid()
        
        # 无效配置
        invalid_config = {
            'percentage': 150.0,  # 超出范围
            'port': 70000         # 超出范围
        }
        
        result = validator_instance.validate(invalid_config, schema)
        assert not result.is_valid()
        assert len(result.errors) == 2
    
    def test_validate_url(self, validator_instance):
        """测试URL验证"""
        schema = {
            'website': {'__type__': 'str', 'url': True},
            'api_endpoint': {'__type__': 'str', 'url': True}
        }
        
        # 有效配置
        valid_config = {
            'website': 'https://example.com',
            'api_endpoint': 'http://localhost:8000/api'
        }
        
        result = validator_instance.validate(valid_config, schema)
        assert result.is_valid()
        
        # 无效配置
        invalid_config = {
            'website': 'not-a-url',
            'api_endpoint': 'ftp://invalid-protocol.com'
        }
        
        result = validator_instance.validate(invalid_config, schema)
        assert not result.is_valid()
        assert len(result.errors) >= 1  # 至少一个URL格式错误
    
    def test_validate_email(self, validator_instance):
        """测试邮箱验证"""
        schema = {
            'contact_email': {'__type__': 'str', 'email': True}
        }
        
        # 有效配置
        valid_config = {
            'contact_email': 'test@example.com'
        }
        
        result = validator_instance.validate(valid_config, schema)
        assert result.is_valid()
        
        # 无效配置
        invalid_config = {
            'contact_email': 'invalid-email-format'
        }
        
        result = validator_instance.validate(invalid_config, schema)
        assert not result.is_valid()
        assert len(result.errors) == 1
    
    def test_validate_port(self, validator_instance):
        """测试端口验证"""
        schema = {
            'server_port': {'__type__': 'int', 'port': True}
        }
        
        # 有效配置
        valid_config = {
            'server_port': 8080
        }
        
        result = validator_instance.validate(valid_config, schema)
        assert result.is_valid()
        
        # 无效配置
        invalid_config = {
            'server_port': 70000  # 超出端口范围
        }
        
        result = validator_instance.validate(invalid_config, schema)
        assert not result.is_valid()
        assert len(result.errors) == 1
    
    def test_validate_nested_objects(self, validator_instance):
        """测试嵌套对象验证"""
        schema = {
            'database': {
                '__required__': ['host', 'port'],
                'host': {'__type__': 'str'},
                'port': {'__type__': 'int', 'range': (1, 65535)},
                'username': {'__type__': 'str'},
                'password': {'__type__': 'str', 'min_length': 6}
            }
        }
        
        # 有效配置
        valid_config = {
            'database': {
                'host': 'localhost',
                'port': 5432,
                'username': 'admin',
                'password': 'secret123'
            }
        }
        
        result = validator_instance.validate(valid_config, schema)
        assert result.is_valid()
        
        # 无效配置
        invalid_config = {
            'database': {
                'host': 'localhost',
                # 缺少必需的 port
                'password': '123'  # 太短
            }
        }
        
        result = validator_instance.validate(invalid_config, schema)
        assert not result.is_valid()
        assert len(result.errors) == 2  # 缺少port + 密码太短
    
    def test_validate_arrays(self, validator_instance):
        """测试数组验证"""
        schema = {
            'servers': [{
                '__required__': ['name', 'host'],
                'name': {'__type__': 'str'},
                'host': {'__type__': 'str'},
                'port': {'__type__': 'int', '__default__': 80}
            }]
        }
        
        # 有效配置
        valid_config = {
            'servers': [
                {'name': 'web1', 'host': 'web1.example.com', 'port': 80},
                {'name': 'web2', 'host': 'web2.example.com'}
            ]
        }
        
        result = validator_instance.validate(valid_config, schema)
        assert result.is_valid()
        
        # 无效配置
        invalid_config = {
            'servers': [
                {'name': 'web1'},  # 缺少必需的host
                {'name': 123, 'host': 'web2.example.com'}  # name类型错误
            ]
        }
        
        result = validator_instance.validate(invalid_config, schema)
        assert not result.is_valid()
        assert len(result.errors) == 2
    
    def test_custom_validation(self, validator_instance):
        """测试自定义验证"""
        def validate_even_number(value):
            if isinstance(value, int) and value % 2 != 0:
                return "数值必须是偶数"
            return None
        
        schema = {
            'even_number': {'__type__': 'int', 'custom': validate_even_number}
        }
        
        # 有效配置
        valid_config = {'even_number': 42}
        result = validator_instance.validate(valid_config, schema)
        assert result.is_valid()
        
        # 无效配置
        invalid_config = {'even_number': 43}
        result = validator_instance.validate(invalid_config, schema)
        assert not result.is_valid()
        assert "偶数" in result.errors[0]


class TestAutoStudySchema:
    """自动学习系统配置模式测试"""
    
    def test_create_auto_study_schema(self):
        """测试创建自动学习系统配置模式"""
        schema = create_auto_study_schema()
        
        # 验证顶级字段
        assert '__required__' in schema
        assert 'browser' in schema['__required__']
        assert 'login' in schema['__required__']
        assert 'system' in schema['__required__']
        
        # 验证浏览器配置
        assert 'browser' in schema
        assert 'headless' in schema['browser']['__required__']
    
    def test_validate_auto_study_config_valid(self):
        """测试有效的自动学习配置"""
        schema = create_auto_study_schema()
        
        valid_config = {
            'browser': {
                'headless': False,
                'width': 1920,
                'height': 1080
            },
            'login': {
                'max_retries': 3
            },
            'system': {
                'log_level': 'INFO'
            }
        }
        
        result = validator.validate(valid_config, schema)
        assert result.is_valid()
    
    def test_validate_auto_study_config_invalid(self):
        """测试无效的自动学习配置"""
        schema = create_auto_study_schema()
        
        invalid_config = {
            'browser': {
                'headless': 'not_a_boolean',  # 错误类型
                'width': 50  # 低于最小值
            },
            'login': {
                'max_retries': 0  # 低于最小值
            },
            'system': {
                'log_level': 'INVALID_LEVEL'  # 不在选择中
            }
        }
        
        result = validator.validate(invalid_config, schema)
        assert not result.is_valid()
        assert len(result.errors) > 0