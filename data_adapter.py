import json
import os
from typing import Dict, List, Optional, Any
from api_manager import APIManager

class DataAdapter:
    """数据适配器，统一处理本地文件和API两种数据源"""
    
    def __init__(self, use_api: bool = False, api_manager: Optional[APIManager] = None, 
                 data_file: str = "scripts.json"):
        self.use_api = use_api
        self.api_manager = api_manager
        self.data_file = data_file
        
        # 本地数据缓存
        self._local_data = {}
        
        if not self.use_api:
            self._load_local_data()
    
    def _load_local_data(self):
        """加载本地数据"""
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    self._local_data = json.load(f)
            except Exception as e:
                print(f"加载本地数据失败: {e}")
                self._local_data = {}
    
    def _save_local_data(self):
        """保存本地数据"""
        try:
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(self._local_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存本地数据失败: {e}")
    
    # ==================== 一级Tab操作 ====================
    
    def get_primary_tabs(self) -> List[str]:
        """获取所有一级Tab"""
        if self.use_api and self.api_manager:
            return self.api_manager.get_primary_tabs()
        else:
            return list(self._local_data.keys())
    
    def create_primary_tab(self, tab_name: str) -> bool:
        """创建一级Tab"""
        if self.use_api and self.api_manager:
            return self.api_manager.create_primary_tab(tab_name)
        else:
            if tab_name not in self._local_data:
                self._local_data[tab_name] = {}
                self._save_local_data()
                return True
            return False
    
    def update_primary_tab(self, old_name: str, new_name: str) -> bool:
        """更新一级Tab名称"""
        if self.use_api and self.api_manager:
            return self.api_manager.update_primary_tab(old_name, new_name)
        else:
            if old_name in self._local_data and new_name not in self._local_data:
                self._local_data[new_name] = self._local_data.pop(old_name)
                self._save_local_data()
                return True
            return False
    
    def delete_primary_tab(self, tab_name: str) -> bool:
        """删除一级Tab"""
        if self.use_api and self.api_manager:
            return self.api_manager.delete_primary_tab(tab_name)
        else:
            if tab_name in self._local_data:
                del self._local_data[tab_name]
                self._save_local_data()
                return True
            return False
    
    # ==================== 二级Tab操作 ====================
    
    def get_secondary_tabs(self, primary_tab: str) -> List[str]:
        """获取指定一级Tab下的所有二级Tab"""
        if self.use_api and self.api_manager:
            return self.api_manager.get_secondary_tabs(primary_tab)
        else:
            return list(self._local_data.get(primary_tab, {}).keys())
    
    def create_secondary_tab(self, primary_tab: str, tab_name: str) -> bool:
        """创建二级Tab"""
        if self.use_api and self.api_manager:
            return self.api_manager.create_secondary_tab(primary_tab, tab_name)
        else:
            if primary_tab in self._local_data:
                if tab_name not in self._local_data[primary_tab]:
                    self._local_data[primary_tab][tab_name] = {}
                    self._save_local_data()
                    return True
            return False
    
    def update_secondary_tab(self, primary_tab: str, old_name: str, new_name: str) -> bool:
        """更新二级Tab名称"""
        if self.use_api and self.api_manager:
            return self.api_manager.update_secondary_tab(primary_tab, old_name, new_name)
        else:
            if (primary_tab in self._local_data and 
                old_name in self._local_data[primary_tab] and 
                new_name not in self._local_data[primary_tab]):
                self._local_data[primary_tab][new_name] = self._local_data[primary_tab].pop(old_name)
                self._save_local_data()
                return True
            return False
    
    def delete_secondary_tab(self, primary_tab: str, tab_name: str) -> bool:
        """删除二级Tab"""
        if self.use_api and self.api_manager:
            return self.api_manager.delete_secondary_tab(primary_tab, tab_name)
        else:
            if primary_tab in self._local_data and tab_name in self._local_data[primary_tab]:
                del self._local_data[primary_tab][tab_name]
                self._save_local_data()
                return True
            return False
    
    # ==================== 话术分类操作 ====================
    
    def get_categories(self, primary_tab: str, secondary_tab: str) -> List[str]:
        """获取指定Tab下的所有话术分类"""
        if self.use_api and self.api_manager:
            return self.api_manager.get_categories(primary_tab, secondary_tab)
        else:
            return list(self._local_data.get(primary_tab, {}).get(secondary_tab, {}).keys())
    
    def create_category(self, primary_tab: str, secondary_tab: str, category_name: str) -> bool:
        """创建话术分类"""
        if self.use_api and self.api_manager:
            return self.api_manager.create_category(primary_tab, secondary_tab, category_name)
        else:
            if (primary_tab in self._local_data and 
                secondary_tab in self._local_data[primary_tab]):
                if category_name not in self._local_data[primary_tab][secondary_tab]:
                    self._local_data[primary_tab][secondary_tab][category_name] = []
                    self._save_local_data()
                    return True
            return False
    
    def update_category(self, primary_tab: str, secondary_tab: str, old_name: str, new_name: str) -> bool:
        """更新话术分类名称"""
        if self.use_api and self.api_manager:
            return self.api_manager.update_category(primary_tab, secondary_tab, old_name, new_name)
        else:
            tab_data = self._local_data.get(primary_tab, {}).get(secondary_tab, {})
            if old_name in tab_data and new_name not in tab_data:
                tab_data[new_name] = tab_data.pop(old_name)
                self._save_local_data()
                return True
            return False
    
    def delete_category(self, primary_tab: str, secondary_tab: str, category_name: str) -> bool:
        """删除话术分类"""
        if self.use_api and self.api_manager:
            return self.api_manager.delete_category(primary_tab, secondary_tab, category_name)
        else:
            tab_data = self._local_data.get(primary_tab, {}).get(secondary_tab, {})
            if category_name in tab_data:
                del tab_data[category_name]
                self._save_local_data()
                return True
            return False
    
    # ==================== 话术内容操作 ====================
    
    def get_scripts(self, primary_tab: str, secondary_tab: str, category: str) -> List[str]:
        """获取指定分类下的所有话术"""
        if self.use_api and self.api_manager:
            return self.api_manager.get_scripts(primary_tab, secondary_tab, category)
        else:
            return self._local_data.get(primary_tab, {}).get(secondary_tab, {}).get(category, [])
    
    def get_all_scripts(self, primary_tab: str, secondary_tab: str) -> Dict[str, List[str]]:
        """获取指定Tab下的所有话术数据"""
        if self.use_api and self.api_manager:
            return self.api_manager.get_all_scripts(primary_tab, secondary_tab)
        else:
            return self._local_data.get(primary_tab, {}).get(secondary_tab, {})
    
    def create_script(self, primary_tab: str, secondary_tab: str, category: str, script_content: str) -> bool:
        """创建话术"""
        if self.use_api and self.api_manager:
            return self.api_manager.create_script(primary_tab, secondary_tab, category, script_content)
        else:
            scripts = self._local_data.get(primary_tab, {}).get(secondary_tab, {}).get(category, [])
            if script_content not in scripts:
                scripts.append(script_content)
                # 确保路径存在
                if primary_tab not in self._local_data:
                    self._local_data[primary_tab] = {}
                if secondary_tab not in self._local_data[primary_tab]:
                    self._local_data[primary_tab][secondary_tab] = {}
                if category not in self._local_data[primary_tab][secondary_tab]:
                    self._local_data[primary_tab][secondary_tab][category] = []
                
                self._local_data[primary_tab][secondary_tab][category] = scripts
                self._save_local_data()
                return True
            return False
    
    def update_script(self, primary_tab: str, secondary_tab: str, category: str, 
                     old_content: str, new_content: str) -> bool:
        """更新话术内容"""
        if self.use_api and self.api_manager:
            return self.api_manager.update_script(primary_tab, secondary_tab, category, old_content, new_content)
        else:
            scripts = self._local_data.get(primary_tab, {}).get(secondary_tab, {}).get(category, [])
            if old_content in scripts and new_content not in scripts:
                index = scripts.index(old_content)
                scripts[index] = new_content
                self._save_local_data()
                return True
            return False
    
    def delete_script(self, primary_tab: str, secondary_tab: str, category: str, script_content: str) -> bool:
        """删除话术"""
        if self.use_api and self.api_manager:
            return self.api_manager.delete_script(primary_tab, secondary_tab, category, script_content)
        else:
            scripts = self._local_data.get(primary_tab, {}).get(secondary_tab, {}).get(category, [])
            if script_content in scripts:
                scripts.remove(script_content)
                self._save_local_data()
                return True
            return False
    
    # ==================== 搜索操作 ====================
    
    def search_scripts(self, keyword: str, primary_tab: Optional[str] = None) -> Dict[str, Any]:
        """搜索话术"""
        if self.use_api and self.api_manager:
            return self.api_manager.search_scripts(keyword, primary_tab)
        else:
            results = {}
            search_data = self._local_data
            
            if primary_tab and primary_tab in search_data:
                search_data = {primary_tab: search_data[primary_tab]}
            
            for p_tab, p_data in search_data.items():
                for s_tab, s_data in p_data.items():
                    for category, scripts in s_data.items():
                        matching_scripts = [script for script in scripts if keyword.lower() in script.lower()]
                        if matching_scripts:
                            tab_key = f"{p_tab}-{s_tab}"
                            if tab_key not in results:
                                results[tab_key] = {}
                            results[tab_key][category] = matching_scripts
            
            return results
    
    # ==================== 数据同步 ====================
    
    def sync_data(self, tab_data: Dict[str, Any]):
        """同步数据到本地缓存"""
        if not self.use_api:
            self._local_data = tab_data
            self._save_local_data()
    
    def get_full_data(self) -> Dict[str, Any]:
        """获取完整数据"""
        if self.use_api and self.api_manager:
            return self.api_manager.export_all_data()
        else:
            return self._local_data