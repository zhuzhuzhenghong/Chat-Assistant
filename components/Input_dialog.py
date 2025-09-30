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

class ChineseInputDialog:
    """中文输入对话框"""
    def __init__(self, parent, title, prompt, initial_value="", multiline=False):
        self.result = None
        self.multiline = multiline
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(title)

        if multiline:
            self.dialog.geometry("450x300")
        else:
            self.dialog.geometry("350x150")

        self.dialog.resizable(False, False)
        self.dialog.transient(parent)
        self.dialog.grab_set()

        # 居中显示
        self.dialog.geometry("+%d+%d" % (
            parent.winfo_rootx() + 50,
            parent.winfo_rooty() + 50
        ))

        # 创建界面
        main_frame = ttk.Frame(self.dialog, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 提示文字
        ttk.Label(main_frame, text=prompt, font=("微软雅黑", 10)).pack(pady=(0, 15))

        if multiline:
            # 多行输入框
            text_frame = ttk.Frame(main_frame)
            text_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 20))

            self.text_widget = tk.Text(text_frame, font=("微软雅黑", 10), height=8, wrap=tk.WORD)
            scrollbar = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, command=self.text_widget.yview)
            self.text_widget.configure(yscrollcommand=scrollbar.set)

            self.text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

            if initial_value:
                self.text_widget.insert(tk.END, initial_value)
                self.text_widget.tag_add(tk.SEL, "1.0", tk.END)

            self.text_widget.focus()
        else:
            # 单行输入框
            self.entry_var = tk.StringVar(value=initial_value)
            self.entry = ttk.Entry(main_frame, textvariable=self.entry_var, font=("微软雅黑", 10))
            self.entry.pack(fill=tk.X, pady=(0, 20))
            self.entry.focus()
            self.entry.select_range(0, tk.END)

        # 按钮
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X)

        ttk.Button(button_frame, text="确定", command=self.ok_clicked).pack(side=tk.RIGHT, padx=(5, 0))
        ttk.Button(button_frame, text="取消", command=self.cancel_clicked).pack(side=tk.RIGHT)

        # 绑定快捷键
        if not multiline:
            self.dialog.bind('<Return>', lambda e: self.ok_clicked())
        self.dialog.bind('<Escape>', lambda e: self.cancel_clicked())
        self.dialog.bind('<Control-Return>', lambda e: self.ok_clicked())

    def ok_clicked(self):
        if self.multiline:
            self.result = self.text_widget.get("1.0", tk.END).strip()
        else:
            self.result = self.entry_var.get().strip()
        self.dialog.destroy()

    def cancel_clicked(self):
        self.result = None
        self.dialog.destroy()

    def show(self):
        self.dialog.wait_window()
        return self.result