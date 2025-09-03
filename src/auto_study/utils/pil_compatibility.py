"""
PIL兼容性补丁

解决ddddocr与新版本PIL的兼容性问题
"""

from PIL import Image
import sys

def patch_pil_compatibility():
    """为PIL添加兼容性补丁，解决ANTIALIAS属性问题"""
    if not hasattr(Image, 'ANTIALIAS'):
        # 在新版本PIL中，ANTIALIAS被移除，使用LANCZOS作为替代
        Image.ANTIALIAS = Image.LANCZOS
        print("✅ PIL兼容性补丁已应用：ANTIALIAS -> LANCZOS")

def patch_ddddocr_compatibility():
    """修复ddddocr库的PIL兼容性问题"""
    try:
        # 确保PIL兼容性
        patch_pil_compatibility()
        
        # 检查ddddocr是否已导入
        if 'ddddocr' in sys.modules:
            print("⚠️  ddddocr已导入，补丁可能无效。请在导入ddddocr前调用此函数。")
        
        return True
        
    except Exception as e:
        print(f"❌ PIL兼容性补丁应用失败: {e}")
        return False

if __name__ == "__main__":
    # 测试补丁
    print("🔧 测试PIL兼容性补丁...")
    patch_ddddocr_compatibility()
    
    # 验证ANTIALIAS属性
    if hasattr(Image, 'ANTIALIAS'):
        print(f"✅ ANTIALIAS属性可用，值为: {Image.ANTIALIAS}")
    else:
        print("❌ ANTIALIAS属性仍不可用")