#!/usr/bin/env python3
"""
闲鱼API操作封装
使用存储在 .credentials 中的Cookie进行操作
"""
import os
import sys
import json
import requests
from pathlib import Path
from typing import Optional, Dict, Any

class XianyuAPI:
    """闲鱼API客户端"""
    
    def __init__(self):
        self.cookie = self._load_cookie()
        self.headers = {
            'Cookie': self.cookie,
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
            'Referer': 'https://www.goofish.com/',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        }
    
    def _load_cookie(self) -> str:
        """从 .credentials 读取Cookie"""
        cred_path = Path(__file__).parent.parent / '.credentials'
        
        if not cred_path.exists():
            raise FileNotFoundError("❌ .credentials 文件不存在")
        
        with open(cred_path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.startswith('XIANYU_COOKIE='):
                    return line.split('=', 1)[1].strip()
        
        raise ValueError("❌ 未找到 XIANYU_COOKIE")
    
    def get_user_info(self) -> Optional[Dict[str, Any]]:
        """获取当前用户信息"""
        # 从Cookie提取用户信息
        info = {}
        
        if 'tracknick=' in self.cookie:
            info['nickname'] = self.cookie.split('tracknick=')[1].split(';')[0]
        
        if 'unb=' in self.cookie:
            info['user_id'] = self.cookie.split('unb=')[1].split(';')[0]
        
        return info if info else None
    
    def search_items(self, keyword: str, page: int = 1) -> Optional[Dict[str, Any]]:
        """搜索商品
        
        Args:
            keyword: 搜索关键词
            page: 页码（从1开始）
        
        Returns:
            搜索结果字典
        """
        url = 'https://www.goofish.com/search'
        params = {
            'q': keyword,
            'page': page,
        }
        
        try:
            response = requests.get(url, headers=self.headers, params=params, timeout=10)
            if response.status_code == 200:
                return {'status': 'success', 'html': response.text}
            else:
                return {'status': 'error', 'code': response.status_code}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}
    
    def get_item_detail(self, item_id: str) -> Optional[Dict[str, Any]]:
        """获取商品详情
        
        Args:
            item_id: 商品ID
        
        Returns:
            商品详情字典
        """
        url = f'https://www.goofish.com/item?id={item_id}'
        
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            if response.status_code == 200:
                return {'status': 'success', 'html': response.text}
            else:
                return {'status': 'error', 'code': response.status_code}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}
    
    def publish_item(self, title: str, price: float, desc: str, 
                     images: list, category: str = '') -> Dict[str, Any]:
        """发布商品（需要进一步实现具体API）
        
        Args:
            title: 商品标题
            price: 价格
            desc: 描述
            images: 图片URL列表
            category: 分类
        
        Returns:
            发布结果
        """
        # TODO: 实现发布逻辑
        return {
            'status': 'not_implemented',
            'message': '发布功能需要进一步分析闲鱼API'
        }


def _mask_identifier(value: str) -> str:
    """Mask account identifiers before printing them to shared terminals/logs."""
    if len(value) <= 2:
        return "*" * len(value)
    if len(value) <= 6:
        return f"{value[0]}***{value[-1]}"
    return f"{value[:2]}***{value[-2:]}"

def main():
    """命令行测试"""
    print("=" * 50)
    print("闲鱼API客户端")
    print("=" * 50)
    
    try:
        client = XianyuAPI()
        print("✅ Cookie加载成功")
        
        # 获取用户信息
        user_info = client.get_user_info()
        if user_info:
            print(f"\n👤 当前用户:")
            for key, value in user_info.items():
                print(f"   {key}: {_mask_identifier(str(value))}")
        
        print("\n📝 Cookie已就绪，可以进行后续操作")
        print("\n使用示例:")
        print("  from scripts.xianyu_api import XianyuAPI")
        print("  client = XianyuAPI()")
        print("  result = client.search_items('iPhone')")
        
    except Exception as e:
        print(f"❌ 初始化失败: {str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    main()
