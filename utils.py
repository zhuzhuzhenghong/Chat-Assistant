import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import json
import os
import pyautogui
import time
import pyperclip
import win32gui
import win32con
from threading import Timer, Thread
from components.Input_dialog import ChineseInputDialog


def ask_string(parent, title, prompt, initial_value="", multiline=False):
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
    # self.config_data = {}
    # # "send_mode": "直接发送",
    # # "always_on_top": true,
    # # "api_base_url": "http://localhost:8000/api",
    # # "current_user_id": null,
    # # "is_logged_in": false
    return scripts_data
