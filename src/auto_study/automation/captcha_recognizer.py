"""
验证码识别器

使用ddddocr进行验证码识别，支持图片预处理和多种识别策略
"""

import io
import base64
import time
from typing import Optional, Union, Dict, Any, Tuple
from pathlib import Path
from PIL import Image, ImageEnhance, ImageFilter
import ddddocr

from ..utils.logger import logger


class CaptchaRecognizer:
    """验证码识别器"""
    
    def __init__(self, model_type: str = 'common'):
        """
        初始化验证码识别器
        
        Args:
            model_type: 模型类型 ('common', 'number', 'letter')
        """
        self.model_type = model_type
        self._ocr = None
        self._init_ocr()
        
        # 识别统计
        self._recognition_stats = {
            'total_attempts': 0,
            'successful_recognitions': 0,
            'failed_recognitions': 0,
            'average_confidence': 0.0
        }
        
        # 预处理配置
        self._preprocess_config = {
            'enhance_contrast': True,
            'enhance_sharpness': True,
            'remove_noise': True,
            'binarization': False,  # 二值化可能对某些验证码有害
            'resize_factor': 1.0
        }
    
    def _init_ocr(self) -> None:
        """初始化OCR引擎"""
        try:
            # 所有模型类型都使用默认初始化
            self._ocr = ddddocr.DdddOcr()
            
            logger.info(f"验证码识别器初始化成功，模型类型: {self.model_type}")
            
        except Exception as e:
            logger.error(f"验证码识别器初始化失败: {e}")
            raise
    
    def preprocess_image(self, image: Union[bytes, Image.Image, str, Path]) -> Image.Image:
        """
        预处理验证码图片
        
        Args:
            image: 图片数据（字节、PIL图像、base64字符串或文件路径）
            
        Returns:
            预处理后的PIL图像
        """
        try:
            # 转换为PIL图像
            pil_image = self._convert_to_pil(image)
            
            # 应用预处理
            processed_image = pil_image.copy()
            
            # 调整大小
            if self._preprocess_config['resize_factor'] != 1.0:
                width, height = processed_image.size
                new_width = int(width * self._preprocess_config['resize_factor'])
                new_height = int(height * self._preprocess_config['resize_factor'])
                processed_image = processed_image.resize((new_width, new_height), Image.LANCZOS)
            
            # 增强对比度
            if self._preprocess_config['enhance_contrast']:
                enhancer = ImageEnhance.Contrast(processed_image)
                processed_image = enhancer.enhance(1.5)  # 增强50%的对比度
            
            # 增强锐度
            if self._preprocess_config['enhance_sharpness']:
                enhancer = ImageEnhance.Sharpness(processed_image)
                processed_image = enhancer.enhance(2.0)  # 增强锐度
            
            # 去除噪声
            if self._preprocess_config['remove_noise']:
                processed_image = processed_image.filter(ImageFilter.MedianFilter(size=3))
            
            # 二值化处理（可选）
            if self._preprocess_config['binarization']:
                processed_image = processed_image.convert('L')  # 转为灰度
                # 简单阈值二值化
                processed_image = processed_image.point(lambda x: 0 if x < 128 else 255, '1')
            
            logger.debug("验证码图片预处理完成")
            return processed_image
            
        except Exception as e:
            logger.error(f"验证码图片预处理失败: {e}")
            raise
    
    def _convert_to_pil(self, image: Union[bytes, Image.Image, str, Path]) -> Image.Image:
        """
        将各种格式转换为PIL图像
        
        Args:
            image: 图片数据
            
        Returns:
            PIL图像对象
        """
        if isinstance(image, Image.Image):
            return image
        
        elif isinstance(image, bytes):
            return Image.open(io.BytesIO(image))
        
        elif isinstance(image, str):
            # 检查是否是base64编码
            if image.startswith('data:image/'):
                # 处理data URL格式
                header, data = image.split(',', 1)
                image_bytes = base64.b64decode(data)
                return Image.open(io.BytesIO(image_bytes))
            elif len(image) > 100 and image.isascii():
                # 可能是base64字符串
                try:
                    image_bytes = base64.b64decode(image)
                    return Image.open(io.BytesIO(image_bytes))
                except:
                    pass
            
            # 作为文件路径处理
            return Image.open(image)
        
        elif isinstance(image, Path):
            return Image.open(image)
        
        else:
            raise ValueError(f"不支持的图片格式类型: {type(image)}")
    
    def recognize(self, 
                 image: Union[bytes, Image.Image, str, Path],
                 preprocess: bool = True,
                 max_attempts: int = 3) -> Optional[str]:
        """
        识别验证码
        
        Args:
            image: 验证码图片
            preprocess: 是否进行预处理
            max_attempts: 最大尝试次数
            
        Returns:
            识别结果字符串，失败返回None
        """
        self._recognition_stats['total_attempts'] += 1
        
        try:
            # 预处理图片
            if preprocess:
                processed_image = self.preprocess_image(image)
            else:
                processed_image = self._convert_to_pil(image)
            
            # 多次尝试识别
            best_result = None
            best_confidence = 0.0
            
            for attempt in range(max_attempts):
                try:
                    # 转换为字节数据
                    img_bytes = self._pil_to_bytes(processed_image)
                    
                    # 执行识别
                    result = self._ocr.classification(img_bytes)
                    
                    if result and isinstance(result, str):
                        # 清理结果
                        cleaned_result = self._clean_result(result)
                        
                        if cleaned_result:
                            # 计算置信度（简单启发式）
                            confidence = self._calculate_confidence(cleaned_result, processed_image)
                            
                            if confidence > best_confidence:
                                best_result = cleaned_result
                                best_confidence = confidence
                            
                            logger.debug(f"识别尝试 {attempt + 1}: '{cleaned_result}', 置信度: {confidence:.2f}")
                            
                            # 如果置信度很高，直接返回
                            if confidence > 0.8:
                                break
                    
                except Exception as e:
                    logger.warning(f"识别尝试 {attempt + 1} 失败: {e}")
                    continue
            
            if best_result:
                self._recognition_stats['successful_recognitions'] += 1
                # 更新平均置信度
                total_success = self._recognition_stats['successful_recognitions']
                current_avg = self._recognition_stats['average_confidence']
                self._recognition_stats['average_confidence'] = (
                    (current_avg * (total_success - 1) + best_confidence) / total_success
                )
                
                logger.info(f"验证码识别成功: '{best_result}', 置信度: {best_confidence:.2f}")
                return best_result
            else:
                self._recognition_stats['failed_recognitions'] += 1
                logger.warning("验证码识别失败")
                return None
                
        except Exception as e:
            self._recognition_stats['failed_recognitions'] += 1
            logger.error(f"验证码识别过程出错: {e}")
            return None
    
    def _pil_to_bytes(self, image: Image.Image) -> bytes:
        """将PIL图像转换为字节数据"""
        img_bytes = io.BytesIO()
        image.save(img_bytes, format='PNG')
        return img_bytes.getvalue()
    
    def _clean_result(self, result: str) -> str:
        """
        清理识别结果
        
        Args:
            result: 原始识别结果
            
        Returns:
            清理后的结果
        """
        if not result:
            return ""
        
        # 移除空白字符
        cleaned = result.strip()
        
        # 移除常见的误识别字符
        cleaned = cleaned.replace(' ', '')  # 移除空格
        cleaned = cleaned.replace('\n', '')  # 移除换行
        cleaned = cleaned.replace('\t', '')  # 移除制表符
        
        # 根据模型类型进行特定清理
        if self.model_type == 'number':
            # 只保留数字
            cleaned = ''.join(c for c in cleaned if c.isdigit())
        elif self.model_type == 'letter':
            # 只保留字母
            cleaned = ''.join(c for c in cleaned if c.isalpha())
        else:
            # 通用清理：移除特殊字符
            cleaned = ''.join(c for c in cleaned if c.isalnum())
        
        return cleaned
    
    def _calculate_confidence(self, result: str, image: Image.Image) -> float:
        """
        计算识别置信度（简单启发式方法）
        
        Args:
            result: 识别结果
            image: 原始图片
            
        Returns:
            置信度分数 (0.0-1.0)
        """
        confidence = 0.5  # 基础置信度
        
        # 长度检查
        if 3 <= len(result) <= 6:
            confidence += 0.2
        elif len(result) < 3 or len(result) > 8:
            confidence -= 0.3
        
        # 字符类型一致性检查
        if self.model_type == 'number' and result.isdigit():
            confidence += 0.2
        elif self.model_type == 'letter' and result.isalpha():
            confidence += 0.2
        elif result.isalnum():
            confidence += 0.1
        
        # 常见验证码长度检查
        if len(result) == 4:  # 最常见的验证码长度
            confidence += 0.1
        
        # 图片尺寸检查
        width, height = image.size
        if 50 <= width <= 200 and 20 <= height <= 60:
            confidence += 0.1
        
        return max(0.0, min(1.0, confidence))
    
    def batch_recognize(self, 
                       images: list,
                       preprocess: bool = True,
                       max_attempts: int = 3) -> Dict[int, Optional[str]]:
        """
        批量识别验证码
        
        Args:
            images: 图片列表
            preprocess: 是否预处理
            max_attempts: 每张图片的最大尝试次数
            
        Returns:
            索引到识别结果的映射
        """
        results = {}
        
        for idx, image in enumerate(images):
            logger.info(f"正在识别第 {idx + 1}/{len(images)} 张验证码")
            result = self.recognize(image, preprocess, max_attempts)
            results[idx] = result
            
            # 短暂延迟避免过度占用CPU
            time.sleep(0.1)
        
        return results
    
    def save_failed_image(self, image: Union[bytes, Image.Image, str, Path], 
                         save_dir: Union[str, Path] = None) -> Optional[Path]:
        """
        保存识别失败的图片用于分析
        
        Args:
            image: 失败的图片
            save_dir: 保存目录
            
        Returns:
            保存的文件路径
        """
        try:
            if save_dir is None:
                save_dir = Path('data/failed_captchas')
            else:
                save_dir = Path(save_dir)
            
            save_dir.mkdir(parents=True, exist_ok=True)
            
            # 生成唯一文件名
            timestamp = int(time.time())
            filename = f"failed_captcha_{timestamp}.png"
            filepath = save_dir / filename
            
            # 转换并保存图片
            pil_image = self._convert_to_pil(image)
            pil_image.save(filepath, format='PNG')
            
            logger.info(f"失败验证码图片已保存: {filepath}")
            return filepath
            
        except Exception as e:
            logger.error(f"保存失败验证码图片出错: {e}")
            return None
    
    def update_preprocess_config(self, **kwargs) -> None:
        """
        更新预处理配置
        
        Args:
            **kwargs: 预处理参数
        """
        for key, value in kwargs.items():
            if key in self._preprocess_config:
                self._preprocess_config[key] = value
                logger.info(f"预处理配置更新: {key} = {value}")
            else:
                logger.warning(f"未知的预处理参数: {key}")
    
    def get_recognition_stats(self) -> Dict[str, Any]:
        """
        获取识别统计信息
        
        Returns:
            统计信息字典
        """
        stats = self._recognition_stats.copy()
        
        # 计算成功率
        if stats['total_attempts'] > 0:
            stats['success_rate'] = stats['successful_recognitions'] / stats['total_attempts']
        else:
            stats['success_rate'] = 0.0
        
        return stats
    
    def reset_stats(self) -> None:
        """重置统计信息"""
        self._recognition_stats = {
            'total_attempts': 0,
            'successful_recognitions': 0,
            'failed_recognitions': 0,
            'average_confidence': 0.0
        }
        logger.info("验证码识别统计信息已重置")
    
    def test_recognition(self, test_image_path: Union[str, Path]) -> Dict[str, Any]:
        """
        测试识别功能
        
        Args:
            test_image_path: 测试图片路径
            
        Returns:
            测试结果
        """
        try:
            start_time = time.time()
            
            # 执行识别
            result = self.recognize(test_image_path, preprocess=True, max_attempts=1)
            
            end_time = time.time()
            recognition_time = end_time - start_time
            
            # 获取图片信息
            image = self._convert_to_pil(test_image_path)
            width, height = image.size
            
            test_result = {
                'image_path': str(test_image_path),
                'image_size': f"{width}x{height}",
                'recognition_result': result,
                'recognition_time': f"{recognition_time:.3f}s",
                'success': result is not None,
                'model_type': self.model_type
            }
            
            logger.info(f"测试识别完成: {test_result}")
            return test_result
            
        except Exception as e:
            logger.error(f"测试识别失败: {e}")
            return {
                'image_path': str(test_image_path),
                'error': str(e),
                'success': False
            }


# 创建默认识别器实例
default_recognizer = CaptchaRecognizer()
number_recognizer = CaptchaRecognizer('number')


def recognize_captcha(image: Union[bytes, Image.Image, str, Path], 
                     model_type: str = 'common',
                     preprocess: bool = True) -> Optional[str]:
    """
    便捷的验证码识别函数
    
    Args:
        image: 验证码图片
        model_type: 模型类型
        preprocess: 是否预处理
        
    Returns:
        识别结果
    """
    if model_type == 'number':
        recognizer = number_recognizer
    else:
        recognizer = default_recognizer
    
    return recognizer.recognize(image, preprocess=preprocess)