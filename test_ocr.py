#!/usr/bin/env python3
"""
验证码OCR测试脚本
"""

import asyncio
import sys
from pathlib import Path

# 添加项目路径到Python路径
sys.path.insert(0, str(Path(__file__).parent / "src"))

# 应用PIL兼容性补丁
from auto_study.utils.pil_compatibility import patch_ddddocr_compatibility
patch_ddddocr_compatibility()

from playwright.async_api import async_playwright
import ddddocr

async def test_captcha_ocr():
    """测试验证码OCR功能"""
    try:
        print("🔍 测试验证码OCR功能...")
        
        # 初始化OCR
        print("初始化OCR...")
        ocr = ddddocr.DdddOcr()
        print("✅ OCR初始化成功")
        
        # 启动浏览器
        print("启动浏览器...")
        playwright = await async_playwright().start()
        browser = await playwright.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        
        # 访问登录页面
        login_url = "https://edu.nxgbjy.org.cn/nxxzxy/index.html#/rolling_news?id=notice"
        print(f"访问页面: {login_url}")
        await page.goto(login_url)
        await asyncio.sleep(5)  # 等待页面加载
        
        # 查找验证码
        print("查找验证码图片...")
        captcha_selectors = [
            'img.image[src*="auth_code"]',
            'img[src*="captcha"]', 
            'img[src*="verify"]',
            'img[alt*="验证"]'
        ]
        
        captcha_img = None
        for selector in captcha_selectors:
            try:
                elem = await page.query_selector(selector)
                if elem and await elem.is_visible():
                    captcha_img = elem
                    print(f"✅ 找到验证码图片: {selector}")
                    break
            except:
                continue
        
        if not captcha_img:
            print("❌ 未找到验证码图片")
            await browser.close()
            await playwright.stop()
            return
            
        # 截取验证码
        print("截取验证码图片...")
        captcha_bytes = await captcha_img.screenshot()
        print(f"截图大小: {len(captcha_bytes)} 字节")
        
        # 保存验证码图片用于调试
        with open("captcha_debug.png", "wb") as f:
            f.write(captcha_bytes)
        print("验证码图片已保存为 captcha_debug.png")
        
        # OCR识别
        print("开始OCR识别...")
        try:
            captcha_text = ocr.classification(captcha_bytes)
            print(f"✅ OCR识别结果: '{captcha_text}'")
            print(f"识别结果长度: {len(captcha_text)}")
            print(f"识别结果类型: {type(captcha_text)}")
            
            # 验证结果
            if captcha_text and len(captcha_text) > 0:
                print("✅ OCR功能正常!")
            else:
                print("⚠️  OCR识别结果为空")
                
        except Exception as ocr_error:
            print(f"❌ OCR识别失败: {ocr_error}")
            import traceback
            traceback.print_exc()
        
        # 等待几秒钟查看结果
        await asyncio.sleep(3)
        
        await page.close()
        await context.close()
        await browser.close()
        await playwright.stop()
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_captcha_ocr())