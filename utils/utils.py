import json
import os
from components.Input_dialog import ChineseInputDialog
import threading
import utils.constants as constants
import uuid
import time
import random

json_file_lock = threading.Lock()


def init_scripts_data():
    """初始化默认话术数据"""
    default_scripts_abs_path = os.path.join(constants.file_abs_path, constants.default_scripts_rel_path)
    with json_file_lock:
        with open(default_scripts_abs_path, 'r', encoding='utf-8') as f:
            scripts_data = json.load(f)
    return scripts_data


def init_config_data():
    """初始化默认配置数据"""
    default_config_abs_path = os.path.join(constants.file_abs_path, constants.default_config_rel_path)
    with json_file_lock:
        with open(default_config_abs_path, 'r', encoding='utf-8') as f:
            config_data = json.load(f)
    return config_data


def generate_id():
    return int(time.time())
