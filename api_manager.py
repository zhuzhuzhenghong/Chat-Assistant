import requests
import json
from typing import Dict, List, Optional, Any

class APIManager:
    """API管理类，处理所有与后端接口的交互"""
    
    def __init__(self, base_url: str = "http://localhost:8000/api"):
        self.base_url = base_url
        self.session = requests.Session()
        # 可以在这里设置默认的headers，如认证信息
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
    
    def _make_request(self, method: str, url: str, data: Optional[Dict] = None) -> Dict[str, Any]:
        """统一的请求处理方法"""
        url = f"{self.base_url}/{url.lstrip('/')}"
        
        try:
            if method.upper() == 'GET':
                response = self.session.get(url, params=data)
            elif method.upper() == 'POST':
                response = self.session.post(url, json=data)
            elif method.upper() == 'PUT':
                response = self.session.put(url, json=data)
            elif method.upper() == 'DELETE':
                response = self.session.delete(url, json=data)
            else:
                raise ValueError(f"不支持的HTTP方法: {method}")
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            # 这里可以添加更详细的错误处理
            raise Exception(f"API请求失败: {str(e)}")
    
    # ==================== 一级Tab操作 ====================
    
    def get_primary_tabs(self) -> List[str]:
        """获取所有一级Tab"""
        result = self._make_request('GET', '/tabs/primary')
        return result.get('tabs', [])
    
    def create_primary_tab(self, tab_name: str) -> bool:
        """创建一级Tab"""
        data = {'tab_name': tab_name}
        result = self._make_request('POST', '/tabs/primary', data)
        return result.get('success', False)
    
    def update_primary_tab(self, old_name: str, new_name: str) -> bool:
        """更新一级Tab名称"""
        data = {'old_name': old_name, 'new_name': new_name}
        result = self._make_request('PUT', '/tabs/primary', data)
        return result.get('success', False)
    
    def delete_primary_tab(self, tab_name: str) -> bool:
        """删除一级Tab"""
        data = {'tab_name': tab_name}
        result = self._make_request('DELETE', '/tabs/primary', data)
        return result.get('success', False)
    
    # ==================== 二级Tab操作 ====================
    
    def get_secondary_tabs(self, primary_tab: str) -> List[str]:
        """获取指定一级Tab下的所有二级Tab"""
        result = self._make_request('GET', f'/tabs/secondary/{primary_tab}')
        return result.get('tabs', [])
    
    def create_secondary_tab(self, primary_tab: str, tab_name: str) -> bool:
        """创建二级Tab"""
        data = {'primary_tab': primary_tab, 'tab_name': tab_name}
        result = self._make_request('POST', '/tabs/secondary', data)
        return result.get('success', False)
    
    def update_secondary_tab(self, primary_tab: str, old_name: str, new_name: str) -> bool:
        """更新二级Tab名称"""
        data = {'primary_tab': primary_tab, 'old_name': old_name, 'new_name': new_name}
        result = self._make_request('PUT', '/tabs/secondary', data)
        return result.get('success', False)
    
    def delete_secondary_tab(self, primary_tab: str, tab_name: str) -> bool:
        """删除二级Tab"""
        data = {'primary_tab': primary_tab, 'tab_name': tab_name}
        result = self._make_request('DELETE', '/tabs/secondary', data)
        return result.get('success', False)
    
    # ==================== 话术分类操作 ====================
    
    def get_categories(self, primary_tab: str, secondary_tab: str) -> List[str]:
        """获取指定Tab下的所有话术分类"""
        result = self._make_request('GET', f'/categories/{primary_tab}/{secondary_tab}')
        return result.get('categories', [])
    
    def create_category(self, primary_tab: str, secondary_tab: str, category_name: str) -> bool:
        """创建话术分类"""
        data = {
            'primary_tab': primary_tab,
            'secondary_tab': secondary_tab,
            'category_name': category_name
        }
        result = self._make_request('POST', '/categories', data)
        return result.get('success', False)
    
    def update_category(self, primary_tab: str, secondary_tab: str, old_name: str, new_name: str) -> bool:
        """更新话术分类名称"""
        data = {
            'primary_tab': primary_tab,
            'secondary_tab': secondary_tab,
            'old_name': old_name,
            'new_name': new_name
        }
        result = self._make_request('PUT', '/categories', data)
        return result.get('success', False)
    
    def delete_category(self, primary_tab: str, secondary_tab: str, category_name: str) -> bool:
        """删除话术分类"""
        data = {
            'primary_tab': primary_tab,
            'secondary_tab': secondary_tab,
            'category_name': category_name
        }
        result = self._make_request('DELETE', '/categories', data)
        return result.get('success', False)
    
    # ==================== 话术内容操作 ====================
    
    def get_scripts(self, primary_tab: str, secondary_tab: str, category: str) -> List[str]:
        """获取指定分类下的所有话术"""
        result = self._make_request('GET', f'/scripts/{primary_tab}/{secondary_tab}/{category}')
        return result.get('scripts', [])
    
    def get_all_scripts(self, primary_tab: str, secondary_tab: str) -> Dict[str, List[str]]:
        """获取指定Tab下的所有话术数据"""
        result = self._make_request('GET', f'/scripts/{primary_tab}/{secondary_tab}')
        return result.get('data', {})
    
    def create_script(self, primary_tab: str, secondary_tab: str, category: str, script_content: str) -> bool:
        """创建话术"""
        data = {
            'primary_tab': primary_tab,
            'secondary_tab': secondary_tab,
            'category': category,
            'script_content': script_content
        }
        result = self._make_request('POST', '/scripts', data)
        return result.get('success', False)
    
    def update_script(self, primary_tab: str, secondary_tab: str, category: str, 
                     old_content: str, new_content: str) -> bool:
        """更新话术内容"""
        data = {
            'primary_tab': primary_tab,
            'secondary_tab': secondary_tab,
            'category': category,
            'old_content': old_content,
            'new_content': new_content
        }
        result = self._make_request('PUT', '/scripts', data)
        return result.get('success', False)
    
    def delete_script(self, primary_tab: str, secondary_tab: str, category: str, script_content: str) -> bool:
        """删除话术"""
        data = {
            'primary_tab': primary_tab,
            'secondary_tab': secondary_tab,
            'category': category,
            'script_content': script_content
        }
        result = self._make_request('DELETE', '/scripts', data)
        return result.get('success', False)
    
    # ==================== 搜索操作 ====================
    
    def search_scripts(self, keyword: str, primary_tab: Optional[str] = None) -> Dict[str, Any]:
        """搜索话术"""
        data = {'keyword': keyword}
        if primary_tab:
            data['primary_tab'] = primary_tab
        
        result = self._make_request('POST', '/scripts/search', data)
        return result.get('results', {})
    
    # ==================== 配置操作 ====================
    
    def get_config(self) -> Dict[str, Any]:
        """获取用户配置"""
        result = self._make_request('GET', '/config')
        return result.get('config', {})
    
    def update_config(self, config: Dict[str, Any]) -> bool:
        """更新用户配置"""
        result = self._make_request('PUT', '/config', config)
        return result.get('success', False)
    
    # ==================== 批量操作 ====================
    
    def batch_import_scripts(self, primary_tab: str, secondary_tab: str, 
                           scripts_data: Dict[str, List[str]]) -> bool:
        """批量导入话术数据"""
        data = {
            'primary_tab': primary_tab,
            'secondary_tab': secondary_tab,
            'scripts_data': scripts_data
        }
        result = self._make_request('POST', '/scripts/batch_import', data)
        return result.get('success', False)
    
    def export_all_data(self) -> Dict[str, Any]:
        """导出所有数据"""
        result = self._make_request('GET', '/export/all')
        return result.get('data', {})