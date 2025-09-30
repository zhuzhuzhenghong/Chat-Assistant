import json
import os
import re
from typing import Dict, List, Optional, Any
import threading
from urllib3 import request
from api_manager import APIManager
import datetime
import utils

json_file_lock = threading.Lock()


class DataAdapter:
    """数据适配器 - 用户登录后获取云端数据，获取不到则使用默认数据"""

    def __init__(self, api_manager: Optional[APIManager] = None,
                 script_file: str = "scripts.json", config_file: str = "config.json", user_id: str = "default"):
        self.api_manager = api_manager
        self.scripts_file = script_file
        self.config_file = config_file
        self.user_id = user_id

        # 用户数据结构（只包含话术数据）
        self.user_data = {
            "user_id": user_id,
            "scripts_data": {},
            "last_updated": None
        }

        # 本地配置（不通过API同步）
        self.config_data = {}

        # 初始化数据
        self.load_user_data()

    def load_user_data(self):
        """加载用户数据：优先云端，获取不到则使用默认数据"""
        # 如果有API管理器，尝试获取云端数据
        if self.api_manager:
            try:
                response = self.api_manager.get_user_data(self.user_id)
                if response.code == 200:
                    self.script_data = response.script_data
                    self.config_data = response.script_data
                    print(f"已加载用户 {self.user_id} 的云端数据")
                    with json_file_lock:  # 自动管理锁的获取/释放
                        with open(self.script_file, 'w', encoding='utf-8') as f:
                            json.dump(self.script_data, f, ensure_ascii=False, indent=2)

                        with open(self.config_file, 'w', encoding='utf-8') as f:
                            json.dump(self.config_data, f, ensure_ascii=False, indent=2)
                    return True
                else:
                    print(f"云端无用户 {self.user_id} 的数据，使用默认数据")
                    return False
            except Exception as e:
                print(f"获取云端数据失败，使用默认数据: {e}")
                return False
        else:
            # 获取不到云端数据，使用默认数据
            self.init_default_data()
            print(f"已为用户 {self.user_id} 初始化默认数据")

    def init_default_data(self):
        """初始化默认数据"""
        self.user_data["scripts_data"] = utils.init_scripts_data()
        self.config_data = {}
        # "send_mode": "直接发送",
        # "always_on_top": true,
        # "api_base_url": "http://localhost:8000/api",
        # "current_user_id": null,
        # "is_logged_in": false

    def push_local_scripts_data(self,data) -> bool:
        """话术数据上传到云端"""
        if data:
            self.user_data.update(data)

        # 更新时间戳
        # self.user_data["last_updated"] = datetime.datetime.now().isoformat()

        # 保存到云端
        if self.api_manager:
            try:
                response = self.api_manager.save_user_data(self.user_data, self.user_id)
                if response.code == 200:
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

    def push_local_config_data(self,data: Dict[str, Any] = None) -> bool:
        """配置数据上传到云端"""
        if data:
            self.config_data.update(config)

        # 更新时间戳
        # self.user_data["last_updated"] = datetime.datetime.now().isoformat()

        # 保存到云端
        if self.api_manager:
            try:
                response = self.api_manager.save_user_data(self.user_data, self.user_id)
                if response.code == 200:
                    print(f"配置数据已保存到云端 (用户: {self.user_id})")
                    return True
                else:
                    print(f"配置数据保存到云端失败 (用户: {self.user_id})")
                    return False
            except Exception as e:
                print(f"配置数据保存到云端时发生错误: {e}")
                return False
        else:
            print("未配置API管理器，无法保存到云端")
            return False

    # ==================== 核心数据操作 ====================


    def get_scripts_data(self) -> Dict[str, Any]:
        """获取话术数据"""
        return self.user_data.get("scripts_data", {})

    def get_config(self) -> Dict[str, Any]:
        """获取配置数据"""
        return self.config_data.copy()

    # ==================== 数据导入导出 ====================

    def import_data_from_dict(self, data: Dict[str, Any]) -> bool:
        """从字典导入数据"""
        try:
            if "scripts_data" in data:
                # 新格式数据
                self.user_data["scripts_data"] = data["scripts_data"]
            else:
                # 旧格式数据，直接作为scripts_data
                self.user_data["scripts_data"] = data

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
        return self.user_data.copy()

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
                self.user_data, file_path, file_format, self.user_id
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
                self.user_data = cloud_data
                print(f"已加载用户 {self.user_id} 的云端数据")
                return True
            else:
                print(f"云端无用户 {self.user_id} 的数据")
                return False
        except Exception as e:
            print(f"刷新云端数据失败: {e}")
            return False
