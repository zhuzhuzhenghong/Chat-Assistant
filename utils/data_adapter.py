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
        self.index_file = os.path.join(os.path.dirname(self.scripts_file), 'index.json')
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
        print('loaded',loaded)
        if not loaded:
            self.rebuild_indexes()
        else:
            # 索引缓存已加载，刷新缓存以确保与当前树一致
            self.save_index_cache()

    # ==================== 核心数据本地操作 ====================
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

    def get_local_data(self):
        self.get_local_scripts_data()
        self.get_local_config_data()

    def save_local_scripts_data(self) -> bool:
        """将话术保存到本地json文件"""
        try:
            # 用户数据保存到本地文件
            with json_file_lock:
                with open(self.scripts_file, 'w', encoding='utf-8') as f:
                    json.dump(self.scripts_data, f, ensure_ascii=False, indent=2)
            # 同步索引缓存，确保与树一致
            self.save_index_cache()
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

    def set_data_structure(self, data: Any) -> List[Dict[str, Any]]:
        script_data: List[Dict[str, Any]] = []
        # 兼容 dict 或 list 的输入
        normalized: List[Dict[str, Any]] = []
        if isinstance(data, list):
            normalized = data
        elif isinstance(data, dict):
            inner = data.get('data')
            normalized = inner if isinstance(inner, list) else [data]
        else:
            normalized = []
        for type in (normalized or []):
            # print('type', type)
            type_dict: Dict[str, Any] = {
                "name": type.get('name', ''),
                "script_type_id": type.get('id', 0),
                "data": []
            }
            for category in type.get('data', []):
                level_one_category_dict = {
                    "name": category.get('name', ''),
                    "script_type_id": type.get('id', 0),
                    "level_one_category_id": category.get('id', 0),
                    "data": []
                }
                for title in category.get('data', []):
                    level_two_category_dict = {
                        "name": title.get('name', ''),
                        "script_type_id": type.get('id', 0),
                        "level_one_category_id": category.get('id', 0),
                        "level_two_category_id": title.get('id', 0),
                        "data": []
                    }
                    for script in title.get('data', []):
                        script_dict = {
                            "content": script.get('content', ''),
                            "title": script.get('title', ''),
                            "script_type_id": type.get('id', 0),
                            "level_one_category_id": category.get('id', 0),
                            "level_two_category_id": title.get('id', 0),
                            "script_id": script.get('id', 0)
                        }
                        level_two_category_dict["data"].append(script_dict)
                    level_one_category_dict['data'].append(level_two_category_dict)
                type_dict['data'].append(level_one_category_dict)
            script_data.append(type_dict)
        return script_data

    # ==================== 索引构建（四表 + 子集索引） ====================
    def rebuild_indexes(self):
        """从树形 scripts_data 重建四表与索引"""
        self._clear_indexes()
        self._build_from_tree(self.scripts_data)

    def _clear_indexes(self):
        self.all_type_id_list.clear()

        self.all_type_data_list.clear()
        self.all_level_one_data_list.clear()
        self.all_level_two_data_list.clear()
        self.all_script_data_list.clear()

        self.type_data_ById.clear()
        self.level_one_data_ById.clear()
        self.level_two_data_ById.clear()
        self.script_data_ById.clear()

        self.type_children_idList_byIds.clear()
        self.level_one_children_idList_byIds.clear()
        self.level_two_children_idList_byIds.clear()

        self.type_index_list_ById.clear()
        self.level_one_index_list_ById.clear()
        self.level_two_index_list_ById.clear()
        self.script_index_list_ById.clear()

    def _build_from_tree(self, tree: List[Dict[str, Any]]):
        """将树形数据打平成四表，并构建 ById 与 children 索引"""
        if not isinstance(tree, list):
            return
        for type_index, type_data in enumerate(tree):
            type_id = type_data.get('script_type_id')
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
                level_one_id = level_one_data.get('level_one_category_id')
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
                    level_two_id = level_two_data.get('level_two_category_id')
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
                    self.level_two_index_list_ById[level_two_index] = [type_index, level_one_index, level_two_index]

                    for script_index, script in enumerate(level_two_data.get('data', [])):
                        script_id = script.get('script_id')
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
                        self.script_index_list_ById[script_index] = [type_index, level_one_index, level_two_index,
                                                                     script_index]

    # 便捷 getter（避免层层遍历）
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
            return self.script_index_list_ById.get(type_id)

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

    # 可选：将分表导出为树（若未来切换以分表为真源时使用）
    def export_tree(self) -> List[Dict[str, Any]]:
        """将当前分表按 children 索引合成为树形"""
        tree: List[Dict[str, Any]] = []
        for t in self.all_type_data_list:
            type_id = t['id']
            type_node = {'name': t['name'], 'script_type_id': type_id, 'data': []}
            for level_one_id in self.type_children_idList_byIds.get(type_id, []):
                l1 = self.level_one_data_ById.get(level_one_id)
                if not l1:
                    continue
                level_one_node = {
                    'name': l1['name'],
                    'script_type_id': type_id,
                    'level_one_category_id': l1['id'],
                    'data': []
                }
                for level_two_id in self.level_one_children_idList_byIds.get((type_id, level_one_id), []):
                    l2 = self.level_two_data_ById.get(level_two_id)
                    if not l2:
                        continue
                    level_two_node = {
                        'name': l2['name'],
                        'script_type_id': type_id,
                        'level_one_category_id': level_one_id,
                        'level_two_category_id': l2['id'],
                        'data': []
                    }
                    for sid in self.level_two_children_idList_byIds.get((type_id, level_one_id, level_two_id), []):
                        sc = self.script_data_ById.get(sid)
                        if not sc:
                            continue
                        sc_node = {
                            'content': sc['content'],
                            'title': sc.get('title', ''),
                            'script_type_id': type_id,
                            'level_one_category_id': level_one_id,
                            'level_two_category_id': level_two_id,
                            'script_id': sc['id']
                        }
                        level_two_node['data'].append(sc_node)
                    level_one_node['data'].append(level_two_node)
                type_node['data'].append(level_one_node)
            tree.append(type_node)
        return tree

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

    # ==================== CRUD（四表分离 + 子集索引，自动合成树并保存） ====================

    def _rebuild_and_persist(self, persist: bool = True) -> None:
        """从分表导出树，写入 self.scripts_data，并可选择保存到文件"""
        self.scripts_data = self.export_tree()
        if persist:
            self.save_local_scripts_data()

    # 新增
    def add_type(self, name: str, type_id: int, persist: bool = True) -> Optional[int]:
        if not isinstance(type_id, int):
            return None
        if type_id in self.type_data_ById:
            return None
        rec = {'id': type_id, 'name': name}
        self.all_type_data_list.append(rec)
        self.type_data_ById[type_id] = rec
        self.type_children_idList_byIds.setdefault(type_id, [])
        self._rebuild_and_persist(persist)
        return type_id

    def add_level_one(self, type_id: int, name: str, level_one_id: int, persist: bool = True) -> Optional[int]:
        if type_id not in self.type_data_ById:
            return None
        if not isinstance(level_one_id, int):
            return None
        if level_one_id in self.level_one_data_ById:
            return None
        rec = {'id': level_one_id, 'name': name, 'typeId': type_id}
        self.all_level_one_data_list.append(rec)
        self.level_one_data_ById[level_one_id] = rec
        children_level_one_ids = self.type_children_idList_byIds.get(type_id)
        if not isinstance(children_level_one_ids, list):
            children_level_one_ids = []
            self.type_children_idList_byIds[type_id] = children_level_one_ids
        children_level_one_ids.append(level_one_id)
        self.level_one_children_idList_byIds.setdefault((type_id, level_one_id), [])
        self._rebuild_and_persist(persist)
        return level_one_id

    def add_level_two(self, type_id: int, level_one_id: int, name: str, level_two_id: int, persist: bool = True) -> \
            Optional[int]:
        if level_one_id not in self.level_one_data_ById:
            return None
        if not isinstance(level_two_id, int):
            return None
        if level_two_id in self.level_two_data_ById:
            return None
        rec = {'id': level_two_id, 'name': name, 'typeId': type_id, 'levelOneId': level_one_id}
        self.all_level_two_data_list.append(rec)
        self.level_two_data_ById[level_two_id] = rec
        children_level_two_ids = self.level_one_children_idList_byIds.get((type_id, level_one_id))
        if not isinstance(children_level_two_ids, list):
            children_level_two_ids = []
            self.level_one_children_idList_byIds[(type_id, level_one_id)] = children_level_two_ids
        children_level_two_ids.append(level_two_id)
        self.level_two_children_idList_byIds.setdefault((type_id, level_one_id, level_two_id), [])
        self._rebuild_and_persist(persist)
        return level_two_id

    def add_script(self, type_id: int, level_one_id: int, level_two_id: int, title: str, content: str, script_id: int,
                   persist: bool = True) -> Optional[int]:
        if level_two_id not in self.level_two_data_ById:
            return None
        if not isinstance(script_id, int):
            return None
        if script_id in self.script_data_ById:
            return None
        rec = {'id': script_id, 'title': title, 'content': content, 'typeId': type_id, 'levelOneId': level_one_id,
               'levelTwoId': level_two_id}
        self.all_script_data_list.append(rec)
        self.script_data_ById[script_id] = rec
        children_script_ids = self.level_two_children_idList_byIds.get((type_id, level_one_id, level_two_id))
        if not isinstance(children_script_ids, list):
            children_script_ids = []
            self.level_two_children_idList_byIds[(type_id, level_one_id, level_two_id)] = children_script_ids
        children_script_ids.append(script_id)
        self._rebuild_and_persist(persist)
        return script_id

    # 编辑
    def edit_type_name(self, type_id: int, name: str, persist: bool = True) -> bool:
        rec = self.type_data_ById.get(type_id)
        if not rec:
            return False
        rec['name'] = name
        self._rebuild_and_persist(persist)
        return True

    def edit_level_one_name(self, level_one_id: int, name: str, persist: bool = True) -> bool:
        rec = self.level_one_data_ById.get(level_one_id)
        if not rec:
            return False
        rec['name'] = name
        self._rebuild_and_persist(persist)
        return True

    def edit_level_two_name(self, level_two_id: int, name: str, persist: bool = True) -> bool:
        rec = self.level_two_data_ById.get(level_two_id)
        if not rec:
            return False
        rec['name'] = name
        self._rebuild_and_persist(persist)
        return True

    def edit_script(self, script_id: int, title: Optional[str] = None, content: Optional[str] = None,
                    persist: bool = True) -> bool:
        rec = self.script_data_ById.get(script_id)
        if not rec:
            return False
        if title is not None:
            rec['title'] = title
        if content is not None:
            rec['content'] = content
        self._rebuild_and_persist(persist)
        return True

    # 删除
    def delete_type(self, type_id: int, persist: bool = True) -> bool:
        t = self.type_data_ById.pop(type_id, None)
        if not t:
            return False
        # 删除其一级分类
        for level_one_id in list(self.type_children_idList_byIds.get(type_id, [])):
            self.delete_level_one(level_one_id, persist=False)
        self.type_children_idList_byIds.pop(type_id, None)
        # 从列表移除
        self.all_type_data_list = [x for x in self.all_type_data_list if x['id'] != type_id]
        self._rebuild_and_persist(persist)
        return True

    def delete_level_one(self, level_one_id: int, persist: bool = True) -> bool:
        index_list = self.level_one_index_list_ById(level_one_id)
        if len(index_list) > 0:
            type_index = index_list[0]
            level_one_index = index_list[1]
            del self.scripts_data[type_index]['data'][level_one_index]
        # lo = self.level_one_data_ById.pop(level_one_id, None)
        # if not lo:
        #     return False
        # # 删除其二级分类
        # k1 = (lo['typeId'], level_one_id)
        # for level_two_id in list(self.level_one_children_idList_byIds.get(k1, [])):
        #     self.delete_level_two(level_two_id, persist=False)
        # self.level_one_children_idList_byIds.pop(k1, None)
        # # 从列表与父索引移除
        # self.all_level_one_data_list = [x for x in self.all_level_one_data_list if x['id'] != level_one_id]
        # if lo['typeId'] in self.type_children_idList_byIds:
        #     self.type_children_idList_byIds[lo['typeId']] = [i for i in self.type_children_idList_byIds[lo['typeId']] if
        #                                                      i != level_one_id]
        # self._rebuild_and_persist(persist)
        return True

    def delete_level_two(self, level_two_id: int, persist: bool = True) -> bool:
        lt = self.level_two_data_ById.pop(level_two_id, None)
        if not lt:
            return False
        # 删除其脚本
        key = (lt['typeId'], lt['levelOneId'], level_two_id)
        for sid in list(self.level_two_children_idList_byIds.get(key, [])):
            self.delete_script(sid, persist=False)
        self.level_two_children_idList_byIds.pop(key, None)
        # 从列表与父索引移除
        self.all_level_two_data_list = [x for x in self.all_level_two_data_list if x['id'] != level_two_id]
        k1 = (lt['typeId'], lt['levelOneId'])
        if k1 in self.level_one_children_idList_byIds:
            self.level_one_children_idList_byIds[k1] = [i for i in self.level_one_children_idList_byIds[k1] if
                                                        i != level_two_id]
        self._rebuild_and_persist(persist)
        return True

    def delete_script(self, script_id: int, persist: bool = True) -> bool:
        sc = self.script_data_ById.pop(script_id, None)
        if not sc:
            return False
        # 从列表移除
        self.all_script_data_list = [x for x in self.all_script_data_list if x['id'] != script_id]
        key = (sc['typeId'], sc['levelOneId'], sc['levelTwoId'])
        if key in self.level_two_children_idList_byIds:
            self.level_two_children_idList_byIds[key] = [i for i in self.level_two_children_idList_byIds[key] if
                                                         i != script_id]
        self._rebuild_and_persist(persist)
        return True

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
                        self.scripts_data = self.set_data_structure(scripts_data)

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

    # ==================== 获取核心数据操作 ====================

    def get_scripts_data(self) -> List[Dict[str, Any]]:
        """获取话术数据（树形）"""
        return self.scripts_data

    def get_config_data(self) -> Dict[str, Any]:
        """获取配置数据"""
        return self.get_local_config_data()

    def refresh_from_cloud(self) -> bool:
        """刷新云端数据"""
        if not self.api_manager:
            print("未配置API管理器，无法刷新云端数据")
            return False

        try:
            cloud_data = self.api_manager.get_user_data(self.user_id or 0)
            if cloud_data and "scripts_data" in cloud_data:
                scripts_tree = cloud_data["scripts_data"]
                if isinstance(scripts_tree, list):
                    self.scripts_data = scripts_tree
                    self.rebuild_indexes()
                    print(f"已加载用户 {self.user_id} 的云端数据")
                    return True
                else:
                    print("云端 scripts_data 结构非法")
                    return False
            else:
                print(f"云端无用户 {self.user_id} 的数据")
                return False
        except Exception as e:
            print(f"刷新云端数据失败: {e}")
            return False
