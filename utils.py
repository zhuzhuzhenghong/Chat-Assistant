import json
import os
from components.Input_dialog import ChineseInputDialog
import threading

json_file_lock = threading.Lock()


def ask_string(parent, title , prompt, initial_value="", multiline=False):
    """显示中文输入对话框"""
    dialog = ChineseInputDialog(parent, title, prompt, initial_value, multiline)
    return dialog.show()


def init_scripts_data():
    """初始化默认话术数据"""
    scripts_data = {
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
    if not os.path.exists('scripts.json'):
        with json_file_lock:
            with open('scripts.json', 'w', encoding='utf-8') as f:
                json.dump(scripts_data, f, ensure_ascii=False, indent=2)

    return scripts_data


def init_config_data():
    """初始化默认配置数据"""
    config = {
        "send_mode": "直接发送",
        "always_on_top": True,
        "api_base_url": "http://localhost:8000/api",
        "current_user_id": None,
        "is_logged_in": False
    }
    if not os.path.exists('config.json'):
        with json_file_lock:
            with open('config.json', 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)

    return config
