#!/usr/bin/env python3
"""
URL查找脚本

自动探测目标网站的登录页面和课程页面URL
"""

import asyncio
import re
import sys
from pathlib import Path
from urllib.parse import urljoin, urlparse
from typing import List, Dict, Optional, Set

# 添加项目路径到Python路径
sys.path.insert(0, str(Path(__file__).parent / "src"))

from playwright.async_api import async_playwright
from src.auto_study.utils.logger import logger


class URLFinder:
    """URL查找器"""
    
    def __init__(self, base_url: str = "https://edu.nxgbjy.org.cn"):
        self.base_url = base_url
        self.browser = None
        self.context = None
        self.page = None
        
        # 常见的登录页面标识
        self.login_indicators = [
            'login', '登录', '登陆', 'signin', 'sign-in', 
            'user/login', 'auth/login', 'account/login',
            'member/login', 'student/login', 'index.html'
        ]
        
        # 常见的课程页面标识
        self.course_indicators = [
            'course', 'courses', '课程', 'study', 'learning',
            'class', 'classes', 'lesson', 'lessons',
            'education', 'training', 'module', 'modules'
        ]
        
        # 已访问的URL，避免重复
        self.visited_urls: Set[str] = set()
        
    async def start_browser(self):
        """启动浏览器"""
        try:
            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.launch(
                headless=False,  # 显示浏览器以便观察
                slow_mo=100,     # 慢动作便于观察
                args=[
                    '--no-sandbox',
                    '--disable-blink-features=AutomationControlled',
                    '--disable-web-security'
                ]
            )
            
            self.context = await self.browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )
            
            self.page = await self.context.new_page()
            logger.info("浏览器启动成功")
            
        except Exception as e:
            logger.error(f"浏览器启动失败: {e}")
            raise
    
    async def close_browser(self):
        """关闭浏览器"""
        try:
            if self.page:
                await self.page.close()
            if self.context:
                await self.context.close()
            if self.browser:
                await self.browser.close()
            if hasattr(self, 'playwright'):
                await self.playwright.stop()
            logger.info("浏览器关闭完成")
        except Exception as e:
            logger.error(f"关闭浏览器失败: {e}")
    
    async def get_page_links(self, url: str) -> List[Dict[str, str]]:
        """获取页面中的所有链接"""
        try:
            logger.info(f"访问页面: {url}")
            await self.page.goto(url, wait_until='networkidle')
            await asyncio.sleep(2)  # 等待页面完全加载
            
            # 获取所有链接
            links = await self.page.evaluate("""
                () => {
                    const links = [];
                    const elements = document.querySelectorAll('a[href], button[onclick], div[onclick]');
                    
                    elements.forEach(el => {
                        let href = el.href || '';
                        let text = el.textContent?.trim() || '';
                        let onclick = el.getAttribute('onclick') || '';
                        
                        // 处理onclick中的链接
                        if (onclick) {
                            const urlMatch = onclick.match(/['"]([^'"]*\.html?)['"]/) || 
                                           onclick.match(/location\.href\s*=\s*['"]([^'"]*)['"]/);
                            if (urlMatch) {
                                href = urlMatch[1];
                            }
                        }
                        
                        if (href && text) {
                            links.push({
                                href: href,
                                text: text,
                                tag: el.tagName.toLowerCase(),
                                onclick: onclick
                            });
                        }
                    });
                    
                    return links;
                }
            """)
            
            logger.info(f"找到 {len(links)} 个链接")
            return links
            
        except Exception as e:
            logger.error(f"获取页面链接失败 {url}: {e}")
            return []
    
    def normalize_url(self, url: str, base_url: str) -> str:
        """规范化URL"""
        if not url:
            return ""
        
        # 处理相对路径
        if url.startswith('//'):
            return f"https:{url}"
        elif url.startswith('/'):
            return urljoin(base_url, url)
        elif not url.startswith(('http://', 'https://')):
            return urljoin(base_url, url)
        
        return url
    
    def is_login_url(self, url: str, text: str) -> bool:
        """判断是否是登录URL"""
        url_lower = url.lower()
        text_lower = text.lower()
        
        return any(indicator in url_lower or indicator in text_lower 
                  for indicator in self.login_indicators)
    
    def is_course_url(self, url: str, text: str) -> bool:
        """判断是否是课程URL"""
        url_lower = url.lower()
        text_lower = text.lower()
        
        return any(indicator in url_lower or indicator in text_lower 
                  for indicator in self.course_indicators)
    
    async def find_urls(self) -> Dict[str, List[Dict[str, str]]]:
        """查找登录和课程URL"""
        results = {
            'login_urls': [],
            'course_urls': [],
            'all_urls': []
        }
        
        try:
            # 首先访问主页
            logger.info(f"开始分析网站: {self.base_url}")
            main_links = await self.get_page_links(self.base_url)
            
            # 分析主页链接
            for link in main_links:
                href = self.normalize_url(link['href'], self.base_url)
                if not href or href in self.visited_urls:
                    continue
                
                self.visited_urls.add(href)
                text = link['text']
                
                url_info = {
                    'url': href,
                    'text': text,
                    'found_on': self.base_url,
                    'tag': link.get('tag', 'a'),
                    'onclick': link.get('onclick', '')
                }
                
                results['all_urls'].append(url_info)
                
                # 判断URL类型
                if self.is_login_url(href, text):
                    results['login_urls'].append(url_info)
                    logger.info(f"🔐 发现登录链接: {text} -> {href}")
                
                if self.is_course_url(href, text):
                    results['course_urls'].append(url_info)
                    logger.info(f"📚 发现课程链接: {text} -> {href}")
            
            # 尝试访问一些常见的登录页面路径
            common_login_paths = [
                '/login', '/login.html', '/user/login', '/auth/login',
                '/nxxzxy/index.html', '/student/login', '/member/login'
            ]
            
            for path in common_login_paths:
                test_url = urljoin(self.base_url, path)
                if test_url not in self.visited_urls:
                    try:
                        await self.page.goto(test_url, timeout=10000)
                        if self.page.url != test_url:
                            # 发生了重定向
                            logger.info(f"🔄 {test_url} 重定向到: {self.page.url}")
                            url_info = {
                                'url': self.page.url,
                                'text': f'重定向自 {path}',
                                'found_on': test_url,
                                'tag': 'redirect'
                            }
                            results['login_urls'].append(url_info)
                        else:
                            # 页面存在
                            logger.info(f"✅ 找到登录页面: {test_url}")
                            url_info = {
                                'url': test_url,
                                'text': f'直接访问 {path}',
                                'found_on': self.base_url,
                                'tag': 'direct'
                            }
                            results['login_urls'].append(url_info)
                        
                        self.visited_urls.add(test_url)
                        
                    except Exception as e:
                        logger.debug(f"无法访问 {test_url}: {e}")
            
            return results
            
        except Exception as e:
            logger.error(f"查找URL失败: {e}")
            return results
    
    def print_results(self, results: Dict[str, List[Dict[str, str]]]):
        """打印结果"""
        print("\n" + "="*80)
        print("🔍 URL 查找结果")
        print("="*80)
        
        print(f"\n🔐 登录页面候选 ({len(results['login_urls'])} 个):")
        print("-" * 50)
        for i, url_info in enumerate(results['login_urls'], 1):
            print(f"{i}. {url_info['text']}")
            print(f"   URL: {url_info['url']}")
            print(f"   发现于: {url_info['found_on']}")
            if url_info.get('onclick'):
                print(f"   点击事件: {url_info['onclick'][:100]}...")
            print()
        
        print(f"\n📚 课程页面候选 ({len(results['course_urls'])} 个):")
        print("-" * 50)
        for i, url_info in enumerate(results['course_urls'], 1):
            print(f"{i}. {url_info['text']}")
            print(f"   URL: {url_info['url']}")
            print(f"   发现于: {url_info['found_on']}")
            if url_info.get('onclick'):
                print(f"   点击事件: {url_info['onclick'][:100]}...")
            print()
        
        print(f"\n📋 所有发现的链接 ({len(results['all_urls'])} 个):")
        print("-" * 50)
        for i, url_info in enumerate(results['all_urls'], 1):
            print(f"{i:2d}. {url_info['text'][:30]:<30} -> {url_info['url']}")
        
        # 生成配置建议
        print(f"\n⚙️  配置文件建议:")
        print("-" * 50)
        
        if results['login_urls']:
            best_login = results['login_urls'][0]['url']
            print(f"login_url: \"{best_login}\"")
        
        if results['course_urls']:
            best_course = results['course_urls'][0]['url']
            print(f"courses_url: \"{best_course}\"")
        
        if not results['login_urls']:
            print("⚠️  未找到明显的登录页面，可能需要手动检查")
        
        if not results['course_urls']:
            print("⚠️  未找到明显的课程页面，可能需要登录后才能访问")


async def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="查找网站的登录和课程URL")
    parser.add_argument("--url", type=str, default="https://edu.nxgbjy.org.cn", 
                       help="目标网站URL (默认: https://edu.nxgbjy.org.cn)")
    parser.add_argument("--headless", action="store_true", 
                       help="无头模式运行")
    
    args = parser.parse_args()
    
    finder = URLFinder(args.url)
    
    try:
        await finder.start_browser()
        results = await finder.find_urls()
        finder.print_results(results)
        
        # 等待用户查看结果
        if not args.headless:
            input("\n按回车键关闭浏览器...")
        
    except KeyboardInterrupt:
        print("\n用户中断操作")
    except Exception as e:
        logger.error(f"脚本执行失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await finder.close_browser()


if __name__ == "__main__":
    asyncio.run(main())