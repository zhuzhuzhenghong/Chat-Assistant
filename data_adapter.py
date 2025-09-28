import json
import os
import re
from typing import Dict, List, Optional, Any

from urllib3 import request
from api_manager import APIManager

class DataAdapter:
    """数据适配器 - 用户登录后获取云端数据，获取不到则使用默认数据"""
    
    def __init__(self, api_manager: Optional[APIManager] = None, 
                 data_file: str = "scripts.json", user_id: str = "default"):
        self.api_manager = api_manager
        self.data_file = data_file
        self.user_id = user_id
        
        # 用户数据结构（只包含话术数据）
        self._user_data = {
            "user_id": user_id,
            "scripts_data": {},
            "last_updated": None
        }
        
        # 本地配置（不通过API同步）
        self._local_config = {
            "send_mode": "直接发送",
            "always_on_top": True,
            "current_primary_tab": "公司话术",
            "current_secondary_tab": "常用"
        }
        
        # 初始化数据
        self._load_user_data()
    
    def _load_user_data(self):
        """加载用户数据：优先云端，获取不到则使用默认数据"""
        # 如果有API管理器，尝试获取云端数据
        if self.api_manager:
            try:
                cloud_data = self.api_manager.get_user_data(self.user_id)
                if cloud_data and "scripts_data" in cloud_data:
                    self._user_data = cloud_data
                    print(f"已加载用户 {self.user_id} 的云端数据")
                    return
                else:
                    print(f"云端无用户 {self.user_id} 的数据，使用默认数据")
            except Exception as e:
                print(f"获取云端数据失败，使用默认数据: {e}")
        
        # 获取不到云端数据，使用默认数据
        self._init_default_data()
        print(f"已为用户 {self.user_id} 初始化默认数据")
    
    def _load_local_data(self):
        """加载本地数据"""
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    local_data = json.load(f)
                    
                # 兼容旧格式数据
                if isinstance(local_data, dict) and "scripts_data" not in local_data:
                    # 旧格式：直接是Tab数据
                    self._user_data["scripts_data"] = local_data
                else:
                    # 新格式：完整用户数据
                    self._user_data.update(local_data)
                    # 提取本地配置
                    if "config" in local_data:
                        self._local_config.update(local_data["config"])
                    
            except Exception as e:
                print(f"加载本地数据失败: {e}")
                self._init_default_data()
        else:
            self._init_default_data()
    
    def _save_local_data(self):
        """保存本地数据"""
        try:
            # 合并用户数据和本地配置一起保存到本地文件
            save_data = self._user_data.copy()
            save_data["config"] = self._local_config
            
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(save_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存本地数据失败: {e}")
    
    def _init_default_data(self):
        """初始化默认数据"""
        self._user_data["scripts_data"] = {
            "公司话术": {
                "常用": {
                    "问候语": [
                        "您好，很高兴为您服务！",
                        "欢迎咨询，请问有什么可以帮助您的吗？"
                    ],
                    "结束语": [
                        "感谢您的咨询，祝您生活愉快！",
                        "如果没有其他问题，本次服务就到这里了，谢谢！"
                    ]
                },
                "产品介绍": {},
                "售后服务": {}
            },
            "小组话术": {
                "日常": {},
                "专业": {},
                "紧急": {}
            },
            "私人话术": {
                "个人": {},
                "备用": {},
                "临时": {}
            }
        }
    
    # ==================== 核心数据操作 ====================
    
    def get_full_data(self) -> Dict[str, Any]:
        """获取完整用户数据"""
        return self._user_data.copy()
    
    def get_scripts_data(self) -> Dict[str, Any]:
        """获取话术数据部分"""
        return self._user_data.get("scripts_data", {})
    
    def get_config(self) -> Dict[str, Any]:
        """获取配置数据（本地配置，不通过API同步）"""
        return self._local_config.copy()
    
    def save_full_data(self, data: Dict[str, Any] = None) -> bool:
        """保存完整数据到云端"""
        if data:
            self._user_data.update(data)
        
        # 更新时间戳
        import datetime
        self._user_data["last_updated"] = datetime.datetime.now().isoformat()
        
        # 保存到云端
        if self.api_manager:
            try:
                success = self.api_manager.save_user_data(self._user_data, self.user_id)
                if success:
                    print(f"数据已保存到云端 (用户: {self.user_id})")
                    return True
                else:
                    print(f"保存到云端失败 (用户: {self.user_id})")
                    return False
            except Exception as e:
                print(f"保存到云端时发生错误: {e}")
                return False
        else:
            print("未配置API管理器，无法保存到云端")
            return False
    
    def update_config(self, config: Dict[str, Any]) -> bool:
        """更新配置（仅本地保存，不同步到云端）"""
        self._local_config.update(config)
        self._save_local_data()
        return True
    
    # ==================== 话术操作 ====================
    
    def add_category(self, primary_tab: str, secondary_tab: str, category_name: str) -> bool:
        """添加话术分类"""
        tab_data = self.get_tab_data(primary_tab, secondary_tab)
        if category_name not in tab_data:
            tab_data[category_name] = []
            return self.update_tab_data(primary_tab, secondary_tab, tab_data)
        return False
    
    def add_script(self, primary_tab: str, secondary_tab: str, category: str, script_content: str) -> bool:
        """添加话术"""
        tab_data = self.get_tab_data(primary_tab, secondary_tab)
        if category not in tab_data:
            tab_data[category] = []
        
        if script_content not in tab_data[category]:
            tab_data[category].append(script_content)
            return self.update_tab_data(primary_tab, secondary_tab, tab_data)
        return False
    
    def update_script(self, primary_tab: str, secondary_tab: str, category: str, 
                     old_content: str, new_content: str) -> bool:
        """更新话术"""
        tab_data = self.get_tab_data(primary_tab, secondary_tab)
        if category in tab_data and old_content in tab_data[category]:
            index = tab_data[category].index(old_content)
            tab_data[category][index] = new_content
            return self.update_tab_data(primary_tab, secondary_tab, tab_data)
        return False
    
    def delete_script(self, primary_tab: str, secondary_tab: str, category: str, script_content: str) -> bool:
        """删除话术"""
        tab_data = self.get_tab_data(primary_tab, secondary_tab)
        if category in tab_data and script_content in tab_data[category]:
            tab_data[category].remove(script_content)
            return self.update_tab_data(primary_tab, secondary_tab, tab_data)
        return False
    
    def rename_category(self, primary_tab: str, secondary_tab: str, old_name: str, new_name: str) -> bool:
        """重命名话术分类"""
        tab_data = self.get_tab_data(primary_tab, secondary_tab)
        if old_name in tab_data and new_name not in tab_data:
            tab_data[new_name] = tab_data.pop(old_name)
            return self.update_tab_data(primary_tab, secondary_tab, tab_data)
        return False
    
    def delete_category(self, primary_tab: str, secondary_tab: str, category_name: str) -> bool:
        """删除话术分类"""
        tab_data = self.get_tab_data(primary_tab, secondary_tab)
        if category_name in tab_data:
            del tab_data[category_name]
            return self.update_tab_data(primary_tab, secondary_tab, tab_data)
        return False
    
    # ==================== 搜索操作 ====================
    
    def search_scripts(self, keyword: str, scope: str = "all") -> Dict[str, Any]:
        """搜索话术"""
        results = {}
        scripts_data = self._user_data.get("scripts_data", {})
        
        for primary_tab, primary_data in scripts_data.items():
            if scope != "all" and scope != primary_tab:
                continue
                
            for secondary_tab, secondary_data in primary_data.items():
                for category, scripts in secondary_data.items():
                    matching_scripts = [script for script in scripts 
                                      if keyword.lower() in script.lower()]
                    if matching_scripts:
                        display_key = f"[{primary_tab}-{secondary_tab}] {category}"
                        results[display_key] = matching_scripts
        
        return {"results": results, "total_count": sum(len(scripts) for scripts in results.values())}
    
    # ==================== 数据导入导出 ====================
    
    def import_data_from_dict(self, data: Dict[str, Any]) -> bool:
        """从字典导入数据"""
        try:
            if "scripts_data" in data:
                # 新格式数据
                self._user_data["scripts_data"] = data["scripts_data"]
            else:
                # 旧格式数据，直接作为scripts_data
                self._user_data["scripts_data"] = data
            
            # 保存到云端
            success = self.save_full_data()
            if success:
                print(f"数据导入成功，已保存到云端")
            else:
                print(f"数据导入成功，但保存到云端失败")
            return True
            
        except Exception as e:
            print(f"数据导入失败: {e}")
            return False
    
    def export_data_to_dict(self) -> Dict[str, Any]:
        """导出数据为字典"""
        return self._user_data.copy()
    
    def import_data_from_file(self, file_path: str) -> bool:
        """从文件导入数据（通过后端处理格式转换）"""
        if not self.api_manager:
            print("未配置API管理器，无法导入文件")
            return False
        
        try:
            # 通过API上传文件并转换为JSON格式
            converted_data = self.api_manager.upload_and_convert_file(file_path, self.user_id)
            if converted_data:
                return self.import_data_from_dict(converted_data)
            else:
                print("文件转换失败，请检查文件格式")
                return False
        except Exception as e:
            print(f"从文件导入数据失败: {e}")
            return False
    
    def export_data_to_file(self, file_path: str, file_format: str = "json") -> bool:
        """导出数据到文件（通过后端处理格式转换）"""
        if not self.api_manager:
            print("未配置API管理器，无法导出文件")
            return False
        
        try:
            # 通过API导出并转换文件格式
            success = self.api_manager.export_and_convert_data(
                self._user_data, file_path, file_format, self.user_id
            )
            if success:
                print(f"数据已导出到文件: {file_path}")
                return True
            else:
                print("文件导出失败")
                return False
        except Exception as e:
            print(f"导出数据到文件失败: {e}")
            return False
    
    def refresh_from_cloud(self) -> bool:
        """刷新云端数据"""
        if not self.api_manager:
            print("未配置API管理器，无法刷新云端数据")
            return False
        
        try:
            cloud_data = self.api_manager.get_user_data(self.user_id)
            if cloud_data and "scripts_data" in cloud_data:
                self._user_data = cloud_data
                print(f"已加载用户 {self.user_id} 的云端数据")
                return True
            else:
                print(f"云端无用户 {self.user_id} 的数据")
                return False
        except Exception as e:
            print(f"刷新云端数据失败: {e}")
            return False