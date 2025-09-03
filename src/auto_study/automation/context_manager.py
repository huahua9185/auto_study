"""
上下文持久化管理器

负责浏览器上下文状态的保存和恢复
包括Cookies、LocalStorage、SessionStorage等数据的持久化
"""

import json
import time
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
from playwright.sync_api import BrowserContext, Page

from ..utils.logger import logger
from ..config.config_manager import ConfigManager


class ContextManager:
    """上下文持久化管理器"""
    
    def __init__(self, config_manager: Optional[ConfigManager] = None, data_dir: Optional[Union[str, Path]] = None):
        """
        初始化上下文管理器
        
        Args:
            config_manager: 配置管理器实例
            data_dir: 数据存储目录
        """
        self.config_manager = config_manager or ConfigManager()
        self.config = self.config_manager.get_config()
        
        # 数据目录设置
        if data_dir:
            self._data_dir = Path(data_dir)
        else:
            self._data_dir = Path(self.config.get('system', {}).get('data_dir', 'data'))
        
        self._context_dir = self._data_dir / 'browser_contexts'
        self._context_dir.mkdir(parents=True, exist_ok=True)
        
        # 默认上下文名称
        self._default_context_name = 'default'
    
    def save_context_state(self, context: BrowserContext, context_name: str = None) -> bool:
        """
        保存浏览器上下文状态
        
        Args:
            context: 浏览器上下文
            context_name: 上下文名称，默认使用default
            
        Returns:
            保存是否成功
        """
        context_name = context_name or self._default_context_name
        
        try:
            # 创建上下文目录
            context_path = self._context_dir / context_name
            context_path.mkdir(parents=True, exist_ok=True)
            
            # 保存cookies
            self._save_cookies(context, context_path)
            
            # 保存storage状态
            self._save_storage_state(context, context_path)
            
            # 保存上下文元信息
            self._save_context_metadata(context, context_path)
            
            logger.info(f"上下文状态保存成功: {context_name}")
            return True
            
        except Exception as e:
            logger.error(f"保存上下文状态失败: {e}")
            return False
    
    def load_context_state(self, context: BrowserContext, context_name: str = None) -> bool:
        """
        加载浏览器上下文状态
        
        Args:
            context: 浏览器上下文
            context_name: 上下文名称，默认使用default
            
        Returns:
            加载是否成功
        """
        context_name = context_name or self._default_context_name
        context_path = self._context_dir / context_name
        
        if not context_path.exists():
            logger.info(f"上下文状态不存在: {context_name}")
            return False
        
        try:
            # 加载cookies
            self._load_cookies(context, context_path)
            
            # 加载storage状态
            self._load_storage_state(context, context_path)
            
            logger.info(f"上下文状态加载成功: {context_name}")
            return True
            
        except Exception as e:
            logger.error(f"加载上下文状态失败: {e}")
            return False
    
    def _save_cookies(self, context: BrowserContext, context_path: Path) -> None:
        """
        保存Cookies
        
        Args:
            context: 浏览器上下文
            context_path: 上下文存储路径
        """
        try:
            cookies = context.cookies()
            cookies_file = context_path / 'cookies.json'
            
            # 添加保存时间戳
            cookies_data = {
                'timestamp': int(time.time()),
                'cookies': cookies
            }
            
            with open(cookies_file, 'w', encoding='utf-8') as f:
                json.dump(cookies_data, f, indent=2, ensure_ascii=False)
            
            logger.debug(f"Cookies保存成功，共 {len(cookies)} 个")
            
        except Exception as e:
            logger.error(f"保存Cookies失败: {e}")
            raise
    
    def _load_cookies(self, context: BrowserContext, context_path: Path) -> None:
        """
        加载Cookies
        
        Args:
            context: 浏览器上下文
            context_path: 上下文存储路径
        """
        try:
            cookies_file = context_path / 'cookies.json'
            
            if not cookies_file.exists():
                logger.debug("Cookies文件不存在")
                return
            
            with open(cookies_file, 'r', encoding='utf-8') as f:
                cookies_data = json.load(f)
            
            cookies = cookies_data.get('cookies', [])
            
            # 过滤过期的cookies
            current_time = int(time.time())
            valid_cookies = []
            
            for cookie in cookies:
                # 检查是否有过期时间
                if 'expires' in cookie and cookie['expires'] != -1:
                    if cookie['expires'] < current_time:
                        continue
                
                valid_cookies.append(cookie)
            
            # 添加cookies到上下文
            if valid_cookies:
                context.add_cookies(valid_cookies)
                logger.debug(f"Cookies加载成功，共 {len(valid_cookies)} 个")
            else:
                logger.debug("没有有效的Cookies需要加载")
            
        except Exception as e:
            logger.error(f"加载Cookies失败: {e}")
            raise
    
    def _save_storage_state(self, context: BrowserContext, context_path: Path) -> None:
        """
        保存Storage状态（LocalStorage和SessionStorage）
        
        Args:
            context: 浏览器上下文
            context_path: 上下文存储路径
        """
        try:
            # 获取所有页面
            pages = context.pages
            if not pages:
                logger.debug("没有活动页面，跳过Storage保存")
                return
            
            storage_data = {}
            
            for i, page in enumerate(pages):
                try:
                    url = page.url
                    if not url or url == 'about:blank':
                        continue
                    
                    # 获取LocalStorage
                    local_storage = page.evaluate("""
                        () => {
                            const storage = {};
                            for (let i = 0; i < localStorage.length; i++) {
                                const key = localStorage.key(i);
                                storage[key] = localStorage.getItem(key);
                            }
                            return storage;
                        }
                    """)
                    
                    # 获取SessionStorage
                    session_storage = page.evaluate("""
                        () => {
                            const storage = {};
                            for (let i = 0; i < sessionStorage.length; i++) {
                                const key = sessionStorage.key(i);
                                storage[key] = sessionStorage.getItem(key);
                            }
                            return storage;
                        }
                    """)
                    
                    if local_storage or session_storage:
                        storage_data[url] = {
                            'localStorage': local_storage,
                            'sessionStorage': session_storage
                        }
                
                except Exception as e:
                    logger.warning(f"获取页面 {i} 的Storage失败: {e}")
                    continue
            
            # 保存Storage数据
            if storage_data:
                storage_file = context_path / 'storage.json'
                storage_content = {
                    'timestamp': int(time.time()),
                    'storage': storage_data
                }
                
                with open(storage_file, 'w', encoding='utf-8') as f:
                    json.dump(storage_content, f, indent=2, ensure_ascii=False)
                
                logger.debug(f"Storage状态保存成功，共 {len(storage_data)} 个页面")
            else:
                logger.debug("没有Storage数据需要保存")
            
        except Exception as e:
            logger.error(f"保存Storage状态失败: {e}")
            raise
    
    def _load_storage_state(self, context: BrowserContext, context_path: Path) -> None:
        """
        加载Storage状态
        
        Args:
            context: 浏览器上下文
            context_path: 上下文存储路径
        """
        try:
            storage_file = context_path / 'storage.json'
            
            if not storage_file.exists():
                logger.debug("Storage文件不存在")
                return
            
            with open(storage_file, 'r', encoding='utf-8') as f:
                storage_content = json.load(f)
            
            storage_data = storage_content.get('storage', {})
            
            # Storage数据将在访问对应URL时恢复
            # 这里只是保存引用，实际恢复需要在页面加载时进行
            context._stored_storage = storage_data
            logger.debug(f"Storage状态加载成功，共 {len(storage_data)} 个页面")
            
        except Exception as e:
            logger.error(f"加载Storage状态失败: {e}")
            raise
    
    def restore_page_storage(self, page: Page, url: str = None) -> None:
        """
        恢复页面的Storage状态
        
        Args:
            page: 页面对象
            url: 页面URL，默认使用当前页面URL
        """
        try:
            url = url or page.url
            if not url or url == 'about:blank':
                return
            
            # 获取保存的Storage数据
            context = page.context
            stored_storage = getattr(context, '_stored_storage', {})
            
            # 查找匹配的Storage数据
            page_storage = None
            for stored_url, storage_data in stored_storage.items():
                if self._url_matches(url, stored_url):
                    page_storage = storage_data
                    break
            
            if not page_storage:
                logger.debug(f"没有找到URL {url} 的Storage数据")
                return
            
            # 恢复LocalStorage
            local_storage = page_storage.get('localStorage', {})
            if local_storage:
                page.evaluate("""
                    (storage) => {
                        for (const [key, value] of Object.entries(storage)) {
                            localStorage.setItem(key, value);
                        }
                    }
                """, local_storage)
            
            # 恢复SessionStorage
            session_storage = page_storage.get('sessionStorage', {})
            if session_storage:
                page.evaluate("""
                    (storage) => {
                        for (const [key, value] of Object.entries(storage)) {
                            sessionStorage.setItem(key, value);
                        }
                    }
                """, session_storage)
            
            logger.debug(f"页面Storage恢复成功: {url}")
            
        except Exception as e:
            logger.error(f"恢复页面Storage失败: {e}")
    
    def _url_matches(self, current_url: str, stored_url: str) -> bool:
        """
        检查URL是否匹配
        
        Args:
            current_url: 当前URL
            stored_url: 存储的URL
            
        Returns:
            是否匹配
        """
        try:
            from urllib.parse import urlparse
            
            current_parsed = urlparse(current_url)
            stored_parsed = urlparse(stored_url)
            
            # 比较域名和路径
            return (current_parsed.netloc == stored_parsed.netloc and
                    current_parsed.path == stored_parsed.path)
        except:
            # 简单字符串比较
            return current_url == stored_url
    
    def _save_context_metadata(self, context: BrowserContext, context_path: Path) -> None:
        """
        保存上下文元信息
        
        Args:
            context: 浏览器上下文
            context_path: 上下文存储路径
        """
        try:
            metadata = {
                'timestamp': int(time.time()),
                'pages_count': len(context.pages),
                'user_agent': context.pages[0].evaluate('navigator.userAgent') if context.pages else None,
                'viewport': context.pages[0].viewport_size if context.pages else None
            }
            
            metadata_file = context_path / 'metadata.json'
            with open(metadata_file, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)
            
            logger.debug("上下文元信息保存成功")
            
        except Exception as e:
            logger.error(f"保存上下文元信息失败: {e}")
    
    def list_saved_contexts(self) -> List[str]:
        """
        列出所有已保存的上下文
        
        Returns:
            上下文名称列表
        """
        try:
            contexts = []
            for context_dir in self._context_dir.iterdir():
                if context_dir.is_dir():
                    contexts.append(context_dir.name)
            
            return sorted(contexts)
            
        except Exception as e:
            logger.error(f"列出保存的上下文失败: {e}")
            return []
    
    def delete_context_state(self, context_name: str) -> bool:
        """
        删除保存的上下文状态
        
        Args:
            context_name: 上下文名称
            
        Returns:
            删除是否成功
        """
        try:
            context_path = self._context_dir / context_name
            
            if not context_path.exists():
                logger.warning(f"上下文状态不存在: {context_name}")
                return False
            
            # 删除目录及所有文件
            import shutil
            shutil.rmtree(context_path)
            
            logger.info(f"上下文状态删除成功: {context_name}")
            return True
            
        except Exception as e:
            logger.error(f"删除上下文状态失败: {e}")
            return False
    
    def get_context_info(self, context_name: str) -> Optional[Dict[str, Any]]:
        """
        获取上下文信息
        
        Args:
            context_name: 上下文名称
            
        Returns:
            上下文信息字典
        """
        try:
            context_path = self._context_dir / context_name
            
            if not context_path.exists():
                return None
            
            info = {
                'name': context_name,
                'path': str(context_path)
            }
            
            # 读取元信息
            metadata_file = context_path / 'metadata.json'
            if metadata_file.exists():
                with open(metadata_file, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
                info.update(metadata)
            
            # 统计文件信息
            files = list(context_path.glob('*'))
            info['files'] = [f.name for f in files]
            info['files_count'] = len(files)
            
            # 统计Cookies数量
            cookies_file = context_path / 'cookies.json'
            if cookies_file.exists():
                with open(cookies_file, 'r', encoding='utf-8') as f:
                    cookies_data = json.load(f)
                info['cookies_count'] = len(cookies_data.get('cookies', []))
            
            # 统计Storage数量
            storage_file = context_path / 'storage.json'
            if storage_file.exists():
                with open(storage_file, 'r', encoding='utf-8') as f:
                    storage_data = json.load(f)
                info['storage_pages_count'] = len(storage_data.get('storage', {}))
            
            return info
            
        except Exception as e:
            logger.error(f"获取上下文信息失败: {e}")
            return None
    
    def cleanup_expired_contexts(self, max_age_days: int = 30) -> int:
        """
        清理过期的上下文状态
        
        Args:
            max_age_days: 最大保存天数
            
        Returns:
            清理的上下文数量
        """
        try:
            current_time = int(time.time())
            max_age_seconds = max_age_days * 24 * 60 * 60
            cleaned_count = 0
            
            for context_dir in self._context_dir.iterdir():
                if not context_dir.is_dir():
                    continue
                
                # 检查元信息文件的时间戳
                metadata_file = context_dir / 'metadata.json'
                if metadata_file.exists():
                    try:
                        with open(metadata_file, 'r', encoding='utf-8') as f:
                            metadata = json.load(f)
                        
                        timestamp = metadata.get('timestamp', 0)
                        if current_time - timestamp > max_age_seconds:
                            import shutil
                            shutil.rmtree(context_dir)
                            cleaned_count += 1
                            logger.info(f"清理过期上下文: {context_dir.name}")
                    
                    except Exception as e:
                        logger.warning(f"检查上下文 {context_dir.name} 时间戳失败: {e}")
            
            logger.info(f"上下文清理完成，共清理 {cleaned_count} 个")
            return cleaned_count
            
        except Exception as e:
            logger.error(f"清理过期上下文失败: {e}")
            return 0