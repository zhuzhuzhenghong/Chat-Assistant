import json
import os
from typing import Dict, Optional, Any, List, Tuple
import threading
from utils.api_manager import APIManager
import utils.utils as utils
import utils.constants as constants

json_file_lock = threading.Lock()


class DataAdapter:
    """数据适配器 - 用户登录后获取云端数据，获取不到则使用默认数据
    扩展：引入“四表分离 + 子集索引”的内存结构，保留树形持久化不变。
    """

    def __init__(self, api_manager: Optional[APIManager] = None):
        self.api_manager = api_manager
        self.scripts_file = constants.real_scripts_rel_path
        self.config_file = constants.real_config_rel_path
        # 索引缓存文件（与树保持同步）
        self.index_file = constants.index_file
        # 用户ID：后端返回的整型ID；默认 0，避免 None 参与类型检查
        self.user_id: Optional[int] = 0

        # 持久化用的树形数据（真源）
        self.scripts_data: List[Dict[str, Any]] = []

        # 本地配置（不通过API同步）
        self.config_data: Dict[str, Any] = {}

        # 内存扁平“分表”
        self.all_type_id_list: List[int] = []
        self.all_type_data_list: List[Dict[str, Any]] = []
        self.all_level_one_data_list: List[Dict[str, Any]] = []
        self.all_level_two_data_list: List[Dict[str, Any]] = []
        self.all_script_data_list: List[Dict[str, Any]] = []

        # ById 映射
        self.type_data_ById: Dict[int, Dict[str, Any]] = {}
        self.level_one_data_ById: Dict[int, Dict[str, Any]] = {}
        self.level_two_data_ById: Dict[int, Dict[str, Any]] = {}
        self.script_data_ById: Dict[int, Dict[str, Any]] = {}

        # children 索引（保序）
        self.type_children_idList_byIds: Dict[int, List[int]] = {}
        self.level_one_children_idList_byIds: Dict[Tuple[int, int], List[int]] = {}
        self.level_two_children_idList_byIds: Dict[Tuple[int, int, int], List[int]] = {}

        # ById 映射 数据下标
        self.type_index_list_ById: Dict[int, List[int]] = {}
        self.level_one_index_list_ById: Dict[int, List[int]] = {}
        self.level_two_index_list_ById: Dict[int, List[int]] = {}
        self.script_index_list_ById: Dict[int, List[int]] = {}

        # 初始化数据
        self.init_data()

    def init_data(self):
        """初始化数据"""
        self.load_user_data()
        # 优先加载索引缓存，加速启动；失败则从树重建索引
        loaded = self.load_index_cache()
        if not loaded:
            self.rebuild_indexes()
        else:
            # 索引缓存已加载，刷新缓存以确保与当前树一致
            self.save_index_cache()

    # ==================== 核心数据本地操作 ====================

    def get_local_data(self):
        self.get_local_scripts_data()
        self.get_local_config_data()

    def get_local_scripts_data(self):
        """读取本地话术数据（树形）"""
        if os.path.exists(self.scripts_file):
            with open(self.scripts_file, 'r', encoding='utf-8') as f:
                self.scripts_data = json.load(f)
        else:
            self.scripts_data = utils.init_scripts_data()

        # 每次读取后重建索引
        self.rebuild_indexes()

    def get_local_config_data(self) -> Dict[str, Any]:
        """读取本地配置数据"""
        if os.path.exists(self.config_file):
            with open(self.config_file, 'r', encoding='utf-8') as f:
                self.config_data = json.load(f)
        else:
            self.config_data = utils.init_config_data()
        return self.config_data

    def save_local_scripts_data(self) -> bool:
        """将话术保存到本地json文件"""
        try:
            # 用户数据保存到本地文件
            with json_file_lock:
                with open(self.scripts_file, 'w', encoding='utf-8') as f:
                    json.dump(self.scripts_data, f, ensure_ascii=False, indent=2)

            # 保存后可按需重建索引，确保与树一致
            self.rebuild_indexes()
            return True
        except Exception as e:
            print(f"保存本地数据失败: {e}")
            return False

    def save_local_config_data(self, config) -> bool:
        """将配置保存到本地json文件"""
        try:
            self.config_data = config
            # 本地配置保存到本地文件
            with json_file_lock:
                with open(self.config_file, 'w', encoding='utf-8') as f:
                    json.dump(self.config_data, f, ensure_ascii=False, indent=2)

            return True
        except Exception as e:
            print(f"保存本地数据失败: {e}")
            return False

    # ==================== 索引构建（四表 + 子集索引） ====================
    def rebuild_indexes(self):
        """从树形 scripts_data 重建四表与索引"""
        self._clear_indexes()
        self._build_from_tree(self.scripts_data)

    def _clear_indexes(self):
        list = [
            'all_type_id_list', 'all_type_data_list', 'all_level_one_data_list',
            'all_level_two_data_list', 'all_script_data_list', 'type_data_ById',
            'level_one_data_ById', 'level_two_data_ById', 'script_data_ById',
            'type_children_idList_byIds', 'level_one_children_idList_byIds', 'level_two_children_idList_byIds',
            'type_index_list_ById', 'level_one_index_list_ById', 'level_two_index_list_ById', 'script_index_list_ById'
        ]
        for attr in list:
            getattr(self, attr).clear()

    def _build_from_tree(self, tree: List[Dict[str, Any]]):
        """将树形数据打平成四表，并构建 ById 与 children 索引"""
        if not isinstance(tree, list):
            return
        for type_index, type_data in enumerate(tree):
            type_id = type_data.get('id')
            if not isinstance(type_id, int):
                continue
            name = type_data.get('name', '')
            # type
            type_rec = {'id': type_id, 'name': name}
            self.all_type_id_list.append(type_id)
            self.all_type_data_list.append(type_rec)
            self.type_data_ById[type_id] = type_rec
            self.type_children_idList_byIds.setdefault(type_id, [])
            self.type_index_list_ById[type_id] = [type_index]
            for level_one_index, level_one_data in enumerate(type_data.get('data', [])):
                level_one_id = level_one_data.get('id')
                if not isinstance(level_one_id, int):
                    continue
                level_one_name = level_one_data.get('name', '')
                level_one_rec = {'id': level_one_id, 'name': level_one_name, 'typeId': type_id}
                self.all_level_one_data_list.append(level_one_rec)
                self.level_one_data_ById[level_one_id] = level_one_rec
                children_level_one_ids = self.type_children_idList_byIds.get(type_id)
                if not isinstance(children_level_one_ids, list):
                    children_level_one_ids = []
                    self.type_children_idList_byIds[type_id] = children_level_one_ids
                children_level_one_ids.append(level_one_id)
                self.level_one_children_idList_byIds.setdefault((type_id, level_one_id), [])
                self.level_one_index_list_ById[level_one_id] = [type_index, level_one_index]

                for level_two_index, level_two_data in enumerate(level_one_data.get('data', [])):
                    level_two_id = level_two_data.get('id')
                    level_two_name = level_two_data.get('name', '')
                    level_two_rec = {'id': level_two_id, 'name': level_two_name, 'typeId': type_id,
                                     'levelOneId': level_one_id}
                    self.all_level_two_data_list.append(level_two_rec)
                    self.level_two_data_ById[level_two_id] = level_two_rec
                    children_level_two_ids = self.level_one_children_idList_byIds.get((type_id, level_one_id))
                    if not isinstance(children_level_two_ids, list):
                        children_level_two_ids = []
                        self.level_one_children_idList_byIds[(type_id, level_one_id)] = children_level_two_ids
                    children_level_two_ids.append(level_two_id)
                    self.level_two_children_idList_byIds.setdefault((type_id, level_one_id, level_two_id), [])
                    self.level_two_index_list_ById[level_two_id] = [type_index, level_one_index, level_two_index]

                    for script_index, script in enumerate(level_two_data.get('data', [])):
                        script_id = script.get('id')
                        script_title = script.get('title', '')
                        script_content = script.get('content', '')
                        script_rec = {
                            'id': script_id,
                            'title': script_title,
                            'content': script_content,
                            'typeId': type_id,
                            'levelOneId': level_one_id,
                            'levelTwoId': level_two_id
                        }
                        self.all_script_data_list.append(script_rec)
                        self.script_data_ById[script_id] = script_rec
                        children_script_ids = self.level_two_children_idList_byIds.get(
                            (type_id, level_one_id, level_two_id))
                        if not isinstance(children_script_ids, list):
                            children_script_ids = []
                            self.level_two_children_idList_byIds[
                                (type_id, level_one_id, level_two_id)] = children_script_ids
                        children_script_ids.append(script_id)
                        self.script_index_list_ById[script_id] = [type_index, level_one_index, level_two_index,
                                                                  script_index]
        # 同步索引缓存，确保与树一致
        self.save_index_cache()

    # ==================== 便捷 getter（避免层层遍历） ====================

    def get_scripts_data(self) -> List[Dict[str, Any]]:
        """获取话术数据（树形）"""
        return self.scripts_data

    def get_config_data(self) -> Dict[str, Any]:
        """获取配置数据"""
        return self.config_data

    def get_type_data(self, type_id: int) -> Optional[Dict[str, Any]]:
        if type_id:
            return self.type_data_ById.get(type_id)

    def get_level_one_data(self, level_one_id: int) -> Optional[Dict[str, Any]]:
        if level_one_id:
            return self.level_one_data_ById.get(level_one_id)

    def get_level_two_data(self, level_two_id: int) -> Optional[Dict[str, Any]]:
        if level_two_id:
            return self.level_two_data_ById.get(level_two_id)

    def get_script_data(self, script_id: int) -> Optional[Dict[str, Any]]:
        if script_id:
            return self.script_data_ById.get(script_id)

    # 子集列举（保序）
    def get_type_list(self) -> List[Dict[str, Any]]:
        return [self.level_one_data_ById[i] for i in self.all_type_id_list if i in self.level_one_data_ById]

    def get_level_one_list(self, type_id: int) -> List[Dict[str, Any]]:
        if type_id:
            ids = self.type_children_idList_byIds.get(type_id, [])
            return [self.level_one_data_ById[i] for i in ids if i in self.level_one_data_ById]

    def get_level_two_list(self, type_id: int, level_one_id: int) -> List[Dict[str, Any]]:
        if type_id and level_one_id:
            ids = self.level_one_children_idList_byIds.get((type_id, level_one_id), [])
            return [self.level_two_data_ById[i] for i in ids if i in self.level_two_data_ById]

    def get_script_list(self, type_id: int, level_one_id: int, level_two_id: int) -> List[Dict[str, Any]]:
        if type_id and level_one_id and level_two_id:
            ids = self.level_two_children_idList_byIds.get((type_id, level_one_id, level_two_id), [])
            return [self.script_data_ById[i] for i in ids if i in self.script_data_ById]

    def get_type_index(self, type_id) -> List[int]:
        if type_id:
            return self.type_index_list_ById.get(type_id)

    def get_level_one_index(self, level_one_id) -> List[int]:
        if level_one_id:
            return self.level_one_index_list_ById.get(level_one_id)

    def get_level_two_index(self, level_two_id) -> List[int]:
        if level_two_id:
            return self.level_two_index_list_ById.get(level_two_id)

    def get_script_index(self, script_id) -> List[int]:
        if script_id:
            return self.script_index_list_ById.get(script_id)

    def get_tree_scripts_data(self, type_id, level_one_id) -> list:
        """获取当前选中Tab的数据（通过索引构建 UI 所需的 title 列表）"""
        if not type_id or not level_one_id:
            return []
        # 取二级分类
        level_two_list = self.get_level_two_list(type_id, level_one_id)
        titles = []
        for level_two in level_two_list:
            level_two_id = level_two['id']
            # 取脚本
            scripts_list = self.get_script_list(type_id, level_one_id, level_two_id)
            # 组装为 UI 需要的结构
            title_node = {
                'name': level_two['name'],
                'id': level_two_id,
                'data': [
                    {
                        'content': script['content'],
                        'title': script.get('title', ''),
                        'id': script['id']
                    } for script in scripts_list
                ]
            }
            titles.append(title_node)
        # 更新当前二级分类缓存与返回
        return titles

    # ==================== 索引缓存（与树保持一致） ====================
    def save_index_cache(self) -> bool:
        """将当前四表与 children 索引保存为缓存 index.json"""
        try:
            children_by_type = {str(k): v[:] for k, v in self.type_children_idList_byIds.items()}
            children_by_level_one = {f"{k[0]}:{k[1]}": v[:] for k, v in self.level_one_children_idList_byIds.items()}
            children_by_level_two = {f"{k[0]}:{k[1]}:{k[2]}": v[:] for k, v in
                                     self.level_two_children_idList_byIds.items()}
            cache = {
                "all_type_data_list": self.all_type_data_list[:],
                "all_level_one_data_list": self.all_level_one_data_list[:],
                "all_level_two_data_list": self.all_level_two_data_list[:],
                "scripts": self.all_script_data_list[:],
                "children_by_type": children_by_type,
                "children_by_level_one": children_by_level_one,
                "children_by_level_two": children_by_level_two
            }
            with json_file_lock:
                with open(self.index_file, 'w', encoding='utf-8') as f:
                    json.dump(cache, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"保存索引缓存失败: {e}")
            return False

    def load_index_cache(self) -> bool:
        """加载索引缓存 index.json 到内存索引（不修改树）"""
        if not os.path.exists(self.index_file):
            return False
        try:
            with open(self.index_file, 'r', encoding='utf-8') as f:
                cache = json.load(f)

            # 还原四表
            self.all_type_data_list = list(cache.get("all_type_data_list", []))
            self.all_level_one_data_list = list(cache.get("all_level_one_data_list", []))
            self.all_level_two_data_list = list(cache.get("all_level_two_data_list", []))
            self.all_script_data_list = list(cache.get("scripts", []))
            # 重建 ById
            self.type_data_ById = {t["id"]: t for t in self.all_type_data_list if isinstance(t.get("id"), int)}

            self.level_one_data_ById = {l1["id"]: l1 for l1 in self.all_level_one_data_list if
                                        isinstance(l1.get("id"), int)}

            self.level_two_data_ById = {l2["id"]: l2 for l2 in self.all_level_two_data_list if
                                        isinstance(l2.get("id"), int)}

            self.script_data_ById = {s["id"]: s for s in self.all_script_data_list if isinstance(s.get("id"), int)}

            # 还原 children（反序列化字符串键）
            self.type_children_idList_byIds = {int(k): list(v) for k, v in cache.get("children_by_type", {}).items() if
                                               k.isdigit()}

            self.level_one_children_idList_byIds = {}
            for k, v in cache.get("children_by_level_one", {}).items():
                try:
                    t, l1 = k.split(":")
                    self.level_one_children_idList_byIds[(int(t), int(l1))] = list(v)
                except Exception:
                    continue

            self.level_two_children_idList_byIds = {}
            for k, v in cache.get("children_by_level_two", {}).items():
                try:
                    t, l1, l2 = k.split(":")
                    self.level_two_children_idList_byIds[(int(t), int(l1), int(l2))] = list(v)
                except Exception:
                    continue

            return True
        except Exception as e:
            print(f"加载索引缓存失败: {e}")
            return False

    # ==================== CRUD（四表分离 + 子集索引） ====================

    # 新增
    def add_type(self, name: str, type_id: int) -> Optional[int]:
        pass

    def add_level_one(self, type_id: int, name: str) -> bool:
        index_list = self.get_type_index(type_id)
        if len(index_list):
            type_index = index_list[0]
            new_level_one = {
                "id": utils.generate_id(),
                "name": name,
                "data": []
            }
            self.scripts_data[type_index]['data'].append(new_level_one)
            self.save_local_scripts_data()
            return True
        return False

    def add_level_two(self, level_one_id: int, name: str) -> bool:
        index_list = self.get_level_one_index(level_one_id)
        if len(index_list):
            type_index = index_list[0]
            level_one_index = index_list[1]
            new_level_two = {
                "id": utils.generate_id(),
                "name": name,
                "data": []
            }
            self.scripts_data[type_index]['data'][level_one_index]['data'].append(new_level_two)
            self.save_local_scripts_data()
            return True
        return False

    def add_script(self, level_two_id: int, title: str, content: str, ) -> bool:
        index_list = self.get_level_two_index(level_two_id)
        if len(index_list):
            type_index = index_list[0]
            level_one_index = index_list[1]
            level_two_index = index_list[2]
            new_script = {
                "id": utils.generate_id(),
                "content": content,
                "title": title
            }
            self.scripts_data[type_index]['data'][level_one_index]['data'][level_two_index]['data'].append(new_script)
            self.save_local_scripts_data()
            return True
        return False

    # 编辑
    def edit_type_name(self, type_id: int, name: str) -> bool:
        pass

    def edit_level_one_name(self, level_one_id: int, name: str) -> bool:
        index_list = self.get_level_one_index(level_one_id)
        if len(index_list) > 0:
            type_index = index_list[0]
            level_one_index = index_list[1]
            self.scripts_data[type_index]['data'][level_one_index]['name'] = name
            self.save_local_scripts_data()
            return True
        return False

    def edit_level_two_name(self, level_two_id: int, name: str) -> bool:
        index_list = self.get_level_two_index(level_two_id)
        if len(index_list) > 0:
            type_index = index_list[0]
            level_one_index = index_list[1]
            level_two_index = index_list[2]
            self.scripts_data[type_index]['data'][level_one_index]['data'][level_two_index]['name'] = name
            self.save_local_scripts_data()
            return True
        return False

    def edit_script(self, script_id: int, title: Optional[str] = None, content: Optional[str] = None) -> bool:
        index_list = self.get_script_index(script_id)
        if len(index_list) > 0:
            type_index = index_list[0]
            level_one_index = index_list[1]
            level_two_index = index_list[2]
            script_index = index_list[3]
            self.scripts_data[type_index]['data'][level_one_index]['data'][level_two_index]['data'][script_index][
                'content'] = content
            self.scripts_data[type_index]['data'][level_one_index]['data'][level_two_index]['data'][script_index][
                'title'] = title
            self.save_local_scripts_data()
            return True
        return False

    # 删除
    def delete_type(self, type_id: int) -> bool:
        pass

    def delete_level_one(self, level_one_id: int) -> bool:
        index_list = self.get_level_one_index(level_one_id)
        if len(index_list) > 0:
            type_index = index_list[0]
            level_one_index = index_list[1]
            del self.scripts_data[type_index]['data'][level_one_index]
            self.save_local_scripts_data()
            return True
        return False

    def delete_level_two(self, level_two_id: int) -> bool:
        index_list = self.get_level_two_index(level_two_id)
        if len(index_list) > 0:
            type_index = index_list[0]
            level_one_index = index_list[1]
            level_two_index = index_list[2]
            del self.scripts_data[type_index]['data'][level_one_index]['data'][level_two_index]
            self.save_local_scripts_data()
            return True
        return False

    def delete_script(self, script_id: int) -> bool:
        index_list = self.get_script_index(script_id)
        if len(index_list) > 0:
            type_index = index_list[0]
            level_one_index = index_list[1]
            level_two_index = index_list[2]
            script_index = index_list[3]
            del self.scripts_data[type_index]['data'][level_one_index]['data'][level_two_index]['data'][script_index]
            self.save_local_scripts_data()
            return True
        return False

    # ==================== 核心数据云端操作操作 ====================
    def load_user_data(self):
        """加载用户数据：优先云端，获取不到则使用默认数据"""
        # 如果有API管理器，尝试获取云端数据
        if self.api_manager:
            try:
                response = self.api_manager.get_user_data(self.user_id or 0)
                if response.get('code') == 200:
                    scripts_data = response.get('scripts_data', [])
                    if isinstance(scripts_data, list):
                        self.scripts_data = scripts_data
                    else:
                        self.scripts_data = scripts_data

                    # self.config_data = response.get('config_data', {})

                    with json_file_lock:  # 自动管理锁的获取/释放
                        with open(self.scripts_file, 'w', encoding='utf-8') as f:
                            json.dump(self.scripts_data, f, ensure_ascii=False, indent=2)

                        # with open(self.config_file, 'w', encoding='utf-8') as f:
                        #     json.dump(self.config_data, f, ensure_ascii=False, indent=2)
                    # 云端拉取后重建索引
                    self.rebuild_indexes()
                else:
                    print(f"云端无用户 {self.user_id} 的数据，使用默认数据")
            except Exception as e:
                print(f"获取云端数据失败，使用本地数据: {e}")
                self.get_local_data()
        else:
            # 获取不到云端数据，使用本地数据
            self.get_local_data()
            # print(f"已为用户 {self.user_id} 初始化默认数据")

    def push_local_scripts_data(self, data: Optional[List[Dict[str, Any]]] = None) -> bool:
        """话术数据上传到云端"""
        if isinstance(data, list):
            self.scripts_data = data

        # 保存到云端
        if self.api_manager:
            try:
                payload = {"scripts_data": self.scripts_data}
                response = self.api_manager.save_user_data(payload, self.user_id or 0)
                if response.get('code') == 200:
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

    def push_local_config_data(self, data: Optional[Dict[str, Any]] = None) -> bool:
        """配置数据上传到云端"""
        if data:
            self.config_data = data

        # 保存到云端
        if self.api_manager:
            try:
                payload = {"config_data": self.config_data}
                response = self.api_manager.save_user_data(payload, self.user_id or 0)
                if response.get('code') == 200:
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
