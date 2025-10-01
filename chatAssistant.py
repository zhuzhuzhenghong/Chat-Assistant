from typing import Any


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
from api_manager import APIManager
from data_adapter import DataAdapter
from components.Login_dialog import show_login_dialog
import utils


class AssistantOptimized:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("聚雍宝")
        self.root.geometry("380x700")
        self.root.resizable(True, True)

        # 话术数据文件
        self.script_file = "scripts.json"

        # Tab数据结构 - 先设置默认值
        self.current_primary_tab = "公司话术"
        self.current_secondary_tab = "常用"

        # 目标窗口跟踪
        self.target_window = None
        self.target_title = "无"
        self.monitoring = True
        self.my_window_handle = None
        self.is_locked = False

        # 发送模式配置
        self.send_mode = "直接发送"  # 默认模式
        self.always_on_top = True  # 默认置顶

        # 用户登录状态
        self.password = ""
        self.username = ""
        self.current_user_id = None
        self.is_logged_in = False

        # 初始化组件
        self.api_manager = None
        self.data_adapter = None
        self.config_file = "config.json"
        # self.load_config()

        # # 初始化Tab数据结构
        # self.init_tab_structure()

        # 加载数据（这会更新scripts_data和当前Tab设置）
        self.scripts_data = {}
        self.current_scripts_data = {}

        # 初始化数据适配器
        self.init_data_adapter()

        # 初始化API管理器
        self.init_APIManager()

        # 创建界面
        self.create_widgets()
        # 根据配置设置窗口置顶状态
        self.root.attributes('-topmost', self.always_on_top)
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        # 启动监控
        self.root.after(500, self.init_monitoring)

    def init_data_adapter(self):
        """初始化数据适配器"""
        try:
            # 未登录状态下，不传递api_manager，避免请求云端数据
            self.data_adapter = DataAdapter(
                api_manager=None,  # 未登录时不使用API
                script_file=self.script_file,
                config_file=self.config_file,
                user_id=0
            )
            print("数据适配器初始化成功")
        except Exception as e:
            print(f"数据适配器初始化失败: {e}")
        finally:
            # 从数据适配器加载数据
            self.load_data_from_adapter()

    def init_APIManager(self):
        try:
            # 初始化API管理器（但不立即连接）
            self.api_manager = APIManager()
            print("API管理器初始化成功")
        except Exception as e:
            print(f"API管理器初始化失败: {e}")
    
    def refresh_all_ui(self):
        """刷新所有界面元素"""
        self.load_data_from_adapter()
        self.update_primary_tabs()    # 重新渲染一级菜单
        self.update_secondary_tabs()  # 更新二级菜单
        self.update_tree()           # 更新话术列表

    def load_data_from_adapter(self):
        """从数据适配器加载数据"""
        if self.data_adapter:
            # 获取完整的话术数据结构
            scripts_data = self.data_adapter.get_scripts_data()
            if scripts_data:
                self.scripts_data = self.data_adapter.get_scripts_data()
                # 确保当前Tab存在
                if self.current_primary_tab not in self.scripts_data:
                    self.current_primary_tab = list(self.scripts_data.keys())[0]
                if self.current_secondary_tab not in self.scripts_data[self.current_primary_tab]:
                    self.current_secondary_tab = list(self.scripts_data[self.current_primary_tab].keys())[0]
            else:
                # 如果没有数据，使用默认结构
                self.init_tab_structure()

            # 加载本地配置
            config = self.data_adapter.get_config_data()
            if config:
                self.send_mode = config.get('send_mode', self.send_mode)
                self.always_on_top = config.get('always_on_top', self.always_on_top)
                # self.current_primary_tab = config.get('current_primary_tab', self.current_primary_tab)
                # self.current_secondary_tab = config.get('current_secondary_tab', self.current_secondary_tab)

            # 返回当前选中Tab的数据
            self.current_scripts_data = self.get_current_scripts_data()
        else:
            # 如果没有数据适配器，使用默认数据
            self.init_tab_structure()
            self.current_scripts_data = self.get_current_scripts_data()

    def update_primary_tabs(self):
        """更新一级Tab按钮"""
        # 清空现有的一级Tab
        for tab_id in self.primary_notebook.tabs():
            self.primary_notebook.forget(tab_id)
        self.primary_tabs.clear()
        
        # 根据当前数据重新创建一级Tab
        if hasattr(self, 'scripts_data') and self.scripts_data:
            for tab_name in self.scripts_data.keys():
                tab_frame = ttk.Frame(self.primary_notebook)
                self.primary_tabs[tab_name] = tab_frame
                self.primary_notebook.add(tab_frame, text=tab_name)
        else:
            # 如果没有数据，创建默认Tab
            for tab_name in ["公司话术", "小组话术", "私人话术"]:
                tab_frame = ttk.Frame(self.primary_notebook)
                self.primary_tabs[tab_name] = tab_frame
                self.primary_notebook.add(tab_frame, text=tab_name)
        
        # 确保当前Tab设置正确
        if hasattr(self, 'scripts_data') and self.scripts_data:
            # 如果当前Tab不存在于新数据中，选择第一个Tab
            if self.current_primary_tab not in self.scripts_data:
                self.current_primary_tab = list(self.scripts_data.keys())[0]
            
            # 确保当前二级Tab也存在
            if self.current_secondary_tab not in self.scripts_data[self.current_primary_tab]:
                self.current_secondary_tab = list(self.scripts_data[self.current_primary_tab].keys())[0]
            
            # 选中正确的一级Tab
            for i, tab_name in enumerate(self.scripts_data.keys()):
                if tab_name == self.current_primary_tab:
                    self.primary_notebook.select(i)
                    break
        self.load_current_scripts_data()

    def update_secondary_tabs(self):
        """更新二级Tab按钮"""
        # 清空现有的二级Tab按钮
        for widget in self.secondary_buttons_frame.winfo_children():
            widget.destroy()
        self.secondary_tab_buttons.clear()

        # 添加当前一级Tab对应的二级Tab按钮
        if self.current_primary_tab in self.scripts_data:
            row = 0
            col = 0
            max_cols = 4  # 每行最多4个按钮，让Tab显示更多文字

            for tab_name in self.scripts_data[self.current_primary_tab].keys():
                # 创建按钮样式
                is_current = (tab_name == self.current_secondary_tab)

                btn = ttk.Button(
                    self.secondary_buttons_frame,
                    text=tab_name,
                    command=lambda name=tab_name: self.select_secondary_tab(name),
                    style='Selected.TButton' if is_current else 'TButton',
                    takefocus=False  # 防止按钮获得焦点
                )

                btn.grid(row=row, column=col, padx=3, pady=3, sticky="ew")
                btn.bind("<Button-3>", lambda e, name=tab_name: self.show_secondary_tab_context_menu(e, name))

                self.secondary_tab_buttons[tab_name] = btn

                col += 1
                if col >= max_cols:
                    col = 0
                    row += 1

            # 配置列权重以实现均匀分布
            current_row_cols = col if col > 0 else max_cols
            for i in range(max_cols):
                self.secondary_buttons_frame.columnconfigure(i, weight=1)

    def update_tree(self):
        """更新树形列表"""
        # 清空树形控件
        for item in self.tree.get_children():
            self.tree.delete(item)

        # 添加分类和话术
        for category, scripts in self.filtered_scripts.items():
            # 显示所有分类，包括空分类
            category_id = self.tree.insert("", "end", text=f"📁 {category}", open=True)

            # 添加话术节点
            if scripts:  # 如果有话术才添加话术节点
                for script in scripts:
                    # 限制显示长度
                    display_text = script if len(script) <= 50 else script[:50] + "..."
                    self.tree.insert(category_id, "end", text=f"💬 {display_text}", values=(script,))

    def init_tab_structure(self):
        """初始化Tab数据结构"""
        if not hasattr(self, 'scripts_data') or not self.scripts_data:
            self.scripts_data = utils.init_scripts_data()

    # def load_scripts_data(self):
    #     """加载话术数据（兼容旧版本）"""
    #     return self.load_data_from_adapter()

    # def migrate_old_data(self, old_data):
    #     """迁移旧数据到新Tab结构"""
    #     self.init_tab_structure()
    #     self.scripts_data["公司话术"]["常用"] = old_data

    def get_current_scripts_data(self):
        """获取当前选中Tab的数据"""
        if hasattr(self, 'scripts_data'):
            return self.scripts_data.get(self.current_primary_tab, {}).get(self.current_secondary_tab, {})
        return {}

    def save_scripts(self):
        """保存话术数据"""
        try:
            if hasattr(self, 'scripts_data') and self.data_adapter:
                # 保存当前Tab的数据到scripts_data
                self.scripts_data[self.current_primary_tab][self.current_secondary_tab] = self.current_scripts_data

                # 只保存到本地，不自动同步云端
                # 更新数据适配器中的数据
                # self.data_adapter.user_data["user_id"] = self.current_user_id or "default"
                self.data_adapter.scripts_data = self.scripts_data
                # 保存到本地文件
                self.data_adapter.save_local_scripts_data()

        except Exception as e:
            print(f"保存数据失败: {e}")

    def save_config(self):
        """保存配置数据"""
        try:
            config = {
                'send_mode': self.send_mode,
                'always_on_top': self.always_on_top,
                'current_user_id': self.current_user_id,
                'is_logged_in': self.is_logged_in
            }
            self.data_adapter.save_local_config_data(config)
        except Exception as e:
            print('保存配置到本地报错', e)

    def init_monitoring(self):
        """初始化监控"""

        # 获取自己的窗口句柄
        def find_my_window(hwnd, param):
            try:
                if win32gui.IsWindowVisible(hwnd):
                    title = win32gui.GetWindowText(hwnd)
                    if "聚雍宝" in title:
                        self.my_window_handle = hwnd
                        return False
            except:
                pass
            return True

        win32gui.EnumWindows(find_my_window, None)

        # 启动监控线程
        Thread(target=self.monitor_windows, daemon=True).start()

    def monitor_windows(self):
        """监控窗口焦点"""
        while self.monitoring:
            try:
                # 如果已锁定，跳过监控
                if self.is_locked:
                    time.sleep(0.5)
                    continue

                current_window = win32gui.GetForegroundWindow()

                # 忽略自己的窗口
                if current_window and current_window != self.my_window_handle:
                    try:
                        title = win32gui.GetWindowText(current_window)
                        if title and title.strip() and current_window != self.target_window:
                            # 过滤掉客服宝相关窗口
                            if "聚雍宝" not in title:
                                self.target_window = current_window
                                self.target_title = title.strip()
                                self.root.after(0, self.update_target_display)
                    except:
                        pass

                time.sleep(0.5)
            except:
                time.sleep(1)

    def update_target_display(self):
        """更新目标显示"""
        if hasattr(self, 'target_var'):
            display_title = self.target_title
            if len(display_title) > 10:
                display_title = display_title[:10] + "..."

            lock_status = "锁定" if self.is_locked else ""
            prefix = f"[{lock_status}] " if lock_status else ""
            self.target_var.set(f"{prefix}目标: {display_title}")

    def create_widgets(self):
        """创建界面"""
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky="nsew")

        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(4, weight=1)

        # 目标窗口
        target_frame = ttk.LabelFrame(main_frame, text="当前目标", padding="5")
        target_frame.grid(row=0, column=0, columnspan=3, sticky="ew", pady=(0, 10))

        self.target_var = tk.StringVar(value="目标: 无")
        ttk.Label(target_frame, textvariable=self.target_var,
                  font=("微软雅黑", 10), foreground="blue").pack(side=tk.LEFT)

        # 右侧按钮组
        button_group = ttk.Frame(target_frame)
        button_group.pack(side=tk.RIGHT)

        # 置顶勾选框
        self.topmost_var = tk.BooleanVar(value=self.always_on_top)
        topmost_checkbox = ttk.Checkbutton(button_group, text="置顶",
                                           variable=self.topmost_var,
                                           command=self.on_topmost_changed)
        topmost_checkbox.pack(side=tk.RIGHT, padx=(0, 10))

        # 锁定勾选框
        self.lock_var = tk.BooleanVar(value=self.is_locked)
        lock_checkbox = ttk.Checkbutton(button_group, text="锁定",
                                        variable=self.lock_var,
                                        command=self.on_lock_changed)
        lock_checkbox.pack(side=tk.RIGHT, padx=(0, 5))

        # 一级Tab
        primary_tab_frame = ttk.Frame(main_frame)
        primary_tab_frame.grid(row=1, column=0, columnspan=3, sticky="ew", pady=(5, 0))
        primary_tab_frame.columnconfigure(0, weight=1)

        self.primary_notebook = ttk.Notebook(primary_tab_frame)
        self.primary_notebook.grid(row=0, column=0, sticky="w")  # 改为左对齐

        # 配置Notebook样式以支持滚动
        style = ttk.Style()
        style.configure('TNotebook', tabposition='n')
        style.configure('TNotebook.Tab', padding=[6, 3])

        # 配置二级Tab按钮样式
        style.configure('Selected.TButton', relief='sunken', background='lightblue', focuscolor='none')
        style.configure('TButton', focuscolor='none')

        # 一级Tab添加按钮 - 紧贴在Notebook右侧
        primary_add_btn = ttk.Button(primary_tab_frame, text="+", width=3,
                                     command=self.add_primary_tab)
        primary_add_btn.grid(row=0, column=1, padx=(2, 0), sticky="w")

        # 创建一级Tab页面 - 根据实际数据创建
        self.primary_tabs = {}
        if hasattr(self, 'scripts_data') and self.scripts_data:
            for tab_name in self.scripts_data.keys():
                tab_frame = ttk.Frame(self.primary_notebook)
                self.primary_tabs[tab_name] = tab_frame
                self.primary_notebook.add(tab_frame, text=tab_name)
        else:
            # 如果没有数据，创建默认Tab
            for tab_name in ["公司话术", "小组话术", "私人话术"]:
                tab_frame = ttk.Frame(self.primary_notebook)
                self.primary_tabs[tab_name] = tab_frame
                self.primary_notebook.add(tab_frame, text=tab_name)

        # 绑定一级Tab事件
        self.primary_notebook.bind("<<NotebookTabChanged>>", self.on_primary_tab_changed)
        self.primary_notebook.bind("<Button-3>", self.show_primary_tab_menu)
        # 绑定鼠标滚轮事件实现Tab滚动
        self.primary_notebook.bind("<MouseWheel>", self.on_primary_tab_scroll)
        self.primary_notebook.bind("<Button-4>", self.on_primary_tab_scroll)
        self.primary_notebook.bind("<Button-5>", self.on_primary_tab_scroll)

        # 二级Tab - 使用按钮组实现换行显示
        secondary_tab_frame = ttk.LabelFrame(main_frame, text="类别", padding="5")
        secondary_tab_frame.grid(row=2, column=0, columnspan=3, sticky="ew", pady=(5, 0))
        secondary_tab_frame.columnconfigure(0, weight=1)

        # 直接创建按钮容器，支持换行
        self.secondary_buttons_frame = ttk.Frame(secondary_tab_frame)
        self.secondary_buttons_frame.grid(row=0, column=0, sticky="ew", padx=(0, 5))

        # 存储二级Tab按钮
        self.secondary_tab_buttons = {}

        # 二级Tab添加按钮
        secondary_add_btn = ttk.Button(secondary_tab_frame, text="+", width=3,
                                       command=self.add_secondary_tab)
        secondary_add_btn.grid(row=0, column=1, padx=(5, 0), sticky="n")

        # 操作按钮（移到二级Tab下方）
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=3, column=0, columnspan=3, sticky="w", pady=(5, 0))

        # 左对齐布局：添加话术标题按钮 -> 双击话术提示
        ttk.Button(button_frame, text="添加话术标题", command=self.add_category).pack(side=tk.LEFT, padx=(0, 10))

        # 动态显示双击话术提示和发送模式
        self.tip_var = tk.StringVar()
        self.update_tip_text()
        ttk.Label(button_frame, textvariable=self.tip_var,
                  font=("微软雅黑", 9), foreground="green").pack(side=tk.LEFT, padx=(0, 10))

        # 话术树形列表
        list_frame = ttk.Frame(main_frame)
        list_frame.grid(row=4, column=0, columnspan=3, sticky="nsew", pady=(5, 0))
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)

        # 创建树形控件
        self.tree = ttk.Treeview(list_frame, show="tree", height=12)
        self.tree.grid(row=0, column=0, sticky="nsew")

        # 滚动条
        tree_scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.tree.yview)
        tree_scrollbar.grid(row=0, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=tree_scrollbar.set)

        # 双击发送话术
        self.tree.bind('<Double-Button-1>', self.on_tree_double_click)
        # 右键菜单
        self.tree.bind('<Button-3>', self.show_script_menu)

        # 搜索框
        search_frame = ttk.LabelFrame(main_frame, text="搜索", padding="5")
        search_frame.grid(row=5, column=0, columnspan=3, sticky="ew", pady=(10, 0))
        search_frame.columnconfigure(1, weight=1)

        ttk.Label(search_frame, text="搜索").grid(row=0, column=0, padx=(0, 5))
        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(search_frame, textvariable=self.search_var)
        self.search_entry.grid(row=0, column=1, sticky="ew", padx=(0, 5))
        self.search_var.trace('w', self.on_search_change)

        # 添加占位符效果
        self.search_placeholder = "输入关键词搜索所有话术..."
        self.search_entry.insert(0, self.search_placeholder)
        self.search_entry.config(foreground='gray')
        self.search_entry.bind('<FocusIn>', self.on_search_focus_in)
        self.search_entry.bind('<FocusOut>', self.on_search_focus_out)

        ttk.Button(search_frame, text="清空", command=self.clear_search, width=6).grid(row=0, column=2)

        # 发送设置变量
        self.mode_var = tk.StringVar(value=self.send_mode)
        self.delay_var = tk.StringVar(value="0")
        self.auto_send_var = tk.BooleanVar(value=False)

        # 状态栏和设置按钮
        status_frame = ttk.Frame(main_frame)
        status_frame.grid(row=6, column=0, columnspan=3, sticky="ew", pady=(10, 0))
        status_frame.columnconfigure(0, weight=1)

        self.status_var = tk.StringVar(value="就绪")
        ttk.Label(status_frame, textvariable=self.status_var,
                  relief=tk.SUNKEN).grid(row=0, column=0, sticky="ew", padx=(0, 5))

        # 登录状态和设置按钮
        button_group = ttk.Frame(status_frame)
        button_group.grid(row=0, column=1, sticky="e")

        # 登录按钮
        self.login_btn = ttk.Button(button_group, text="登录", width=6, command=self.show_login_dialog)
        self.login_btn.pack(side=tk.LEFT, padx=(0, 5))

        # 设置按钮
        settings_btn = ttk.Button(button_group, text="⚙️", width=4)
        settings_btn.pack(side=tk.LEFT)
        settings_btn.bind('<Button-1>', self.show_context_menu)

        # 更新登录状态显示
        self.update_login_status()

        # 存储原始数据用于搜索
        self.filtered_scripts = self.current_scripts_data.copy()

        # 初始化Tab显示 - 确保选中正确的Tab
        if hasattr(self, 'scripts_data') and self.scripts_data:
            # 选中当前的一级Tab
            for i, tab_name in enumerate(self.scripts_data.keys()):
                if tab_name == self.current_primary_tab:
                    self.primary_notebook.select(i)
                    break

        self.update_secondary_tabs()
        self.update_tree()

    def show_script_management_menu(self, event):
        """显示话术管理菜单"""
        # 创建话术管理菜单
        management_menu = tk.Menu(self.root, tearoff=0)

        # 只添加话术标题功能
        management_menu.add_command(label="添加一级菜单", command=self.add_category)
        management_menu.add_command(label="编辑菜单名称", command=self.edit_item)
        management_menu.add_command(label="删除一级菜单", command=self.delete_item)
        # 显示菜单
        try:
            management_menu.tk_popup(event.x_root, event.y_root)
        finally:
            management_menu.grab_release()

    def show_script_menu(self, event):
        """显示话术右键菜单"""
        # 获取点击的项目
        item = self.tree.identify_row(event.y)
        if not item:
            return

        # 选中该项目
        self.tree.selection_set(item)

        # 创建右键菜单
        context_menu = tk.Menu(self.root, tearoff=0)

        # 检查是否是话术节点
        values = self.tree.item(item, "values")
        if values:
            # 话术节点菜单
            context_menu.add_command(label="编辑", command=self.edit_item)
            context_menu.add_command(label="删除", command=self.delete_item)
        else:
            # 分类节点菜单
            context_menu.add_command(label="添加话术", command=lambda: self.add_script_to_category(item))
            context_menu.add_separator()
            context_menu.add_command(label="编辑", command=self.edit_item)
            context_menu.add_command(label="删除", command=self.delete_item)

        # 显示菜单
        try:
            context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            context_menu.grab_release()

    def rename_secondary_tab_by_name(self, old_name):
        """通过名称重命名二级Tab"""
        new_name = utils.ask_string(self.root, "修改名称", "请输入新的分类名称:", old_name)
        if new_name and new_name.strip() and new_name != old_name:
            new_name = new_name.strip()
            if new_name not in self.scripts_data[self.current_primary_tab]:
                # 更新数据结构
                self.scripts_data[self.current_primary_tab][new_name] = self.scripts_data[self.current_primary_tab].pop(
                    old_name)

                # 更新当前Tab名称
                if self.current_secondary_tab == old_name:
                    self.current_secondary_tab = new_name

                # 更新界面
                self.update_secondary_tabs()
                self.save_scripts()
                self.status_var.set(f"已重命名: {old_name} → {new_name}")
            else:
                messagebox.showwarning("警告", "分类名称已存在！")

    def delete_secondary_tab_by_name(self, tab_name):
        """通过名称删除二级Tab"""
        if len(self.scripts_data[self.current_primary_tab]) <= 1:
            messagebox.showwarning("警告", "至少需要保留一个二级分类！")
            return

        if messagebox.askyesno("确认删除", f"确定要删除二级分类 '{tab_name}' 及其所有话术吗？",
                               icon='question', default='no'):
            try:
                # 从数据结构中删除
                if tab_name in self.scripts_data[self.current_primary_tab]:
                    del self.scripts_data[self.current_primary_tab][tab_name]

                # 如果删除的是当前Tab，切换到第一个Tab
                if self.current_secondary_tab == tab_name:
                    if self.scripts_data[self.current_primary_tab]:
                        first_secondary = list(self.scripts_data[self.current_primary_tab].keys())[0]
                        self.current_secondary_tab = first_secondary
                        self.load_current_scripts_data()

                # 更新界面
                self.update_secondary_tabs()
                self.save_scripts()
                self.status_var.set(f"已删除二级分类: {tab_name}")
            except Exception as e:
                messagebox.showerror("错误", f"删除失败: {str(e)}")
                self.status_var.set(f"删除失败: {str(e)}")

    def on_tree_double_click(self, event):
        """树形控件双击事件"""
        selection = self.tree.selection()
        if not selection:
            return

        item = selection[0]
        # 检查是否是话术节点（有values）
        values = self.tree.item(item, "values")
        if values:
            # 这是话术节点，发送话术
            script = values[0]
            self.send_script_text(script)
        else:
            # 这是分类节点，展开/折叠
            current_state = self.tree.item(item, "open")
            self.tree.item(item, open=not current_state)

    def send_script_text(self, script):
        """发送指定的话术文本"""
        if self.send_mode == "添加到剪贴板":
            # 直接复制到剪贴板
            pyperclip.copy(script)
            self.status_var.set("已复制到剪贴板")
            return
        elif self.send_mode == "添加到输入框":
            # 只粘贴到输入框，不发送
            if not self.target_window:
                messagebox.showwarning("警告", "没有检测到目标窗口！")
                return

            try:
                delay = float(self.delay_var.get())
            except:
                delay = 0.8

            self.status_var.set(f"{delay}秒后添加到输入框...")

            if delay > 0:
                Timer(delay, lambda: self.paste_to_input(script)).start()
            else:
                self.paste_to_input(script)
        else:  # 直接发送
            if not self.target_window:
                messagebox.showwarning("警告", "没有检测到目标窗口！")
                return

            # 直接发送，不使用延时
            self.status_var.set("正在发送...")
            self.send_text_direct(script)

    def add_category(self):
        """添加分类"""
        category = utils.ask_string(self.root, "添加分类", "请输入分类名称:")
        if category and category.strip():
            category = category.strip()
            if category not in self.current_scripts_data:
                # 只添加到当前scripts，保存时会同步到scripts_data
                self.current_scripts_data[category] = []
                # 保存数据
                self.save_scripts()
                # 更新过滤数据
                self.filtered_scripts = self.current_scripts_data.copy()
                # 更新界面
                self.update_tree()
                self.status_var.set(f"已添加分类: {category}")
            else:
                messagebox.showwarning("警告", "分类已存在！")

    # def add_script(self):
    #     """添加话术"""
    #     # 获取选中的分类
    #     selection = self.tree.selection()
    #     category = None
    #
    #     if selection:
    #         item = selection[0]
    #         # 如果选中的是话术，获取其父分类
    #         parent = self.tree.parent(item)
    #         if parent:
    #             category_text = self.tree.item(parent, "text")
    #             category = category_text
    #         else:
    #             # 选中的是分类
    #             category_text = self.tree.item(item, "text")
    #             category = category_text
    #
    #     if not category:
    #         # 如果没有选中，让用户选择分类
    #         categories = list(self.current_scripts_data.keys())
    #         if not categories:
    #             messagebox.showwarning("警告", "请先添加分类！")
    #             return
    #
    #         category = utils.ask_string(self.root, "选择分类", f"请输入分类名称（现有分类: {', '.join(categories)}）:")
    #         if not category or category not in self.current_scripts_data:
    #             messagebox.showwarning("警告", "请输入有效的分类名称！")
    #             return
    #
    #     script = utils.ask_string(self.root, "添加话术", f"请输入话术内容（分类: {category}）:", "", True)
    #     if script and script.strip():
    #         # 只添加到当前scripts，保存时会同步到scripts_data
    #         self.current_scripts_data[category].append(script.strip())
    #         # 保存数据
    #         self.save_scripts()
    #         # 更新过滤数据
    #         self.filtered_scripts = self.current_scripts_data.copy()
    #         # 更新界面
    #         self.update_tree()
    #         self.status_var.set(f"已添加话术到 {category}")

    def add_script_to_category(self, item):
        """向指定分类添加话术"""
        # 获取分类名称
        category_text = self.tree.item(item, "text")
        category = category_text.replace("📁 ", "")

        # 确保分类存在，如果不存在则创建
        if category not in self.current_scripts_data:
            self.current_scripts_data[category] = []

        script = utils.ask_string(self.root, "添加话术", f"请输入话术内容（分类: {category}）:", "", True)
        if script and script.strip():
            # 添加到当前scripts
            self.current_scripts_data[category].append(script.strip())
            # 保存数据
            self.save_scripts()
            # 更新过滤数据
            self.filtered_scripts = self.current_scripts_data.copy()
            # 更新界面
            self.update_tree()
            self.status_var.set(f"✅ 已添加话术到 {category}")

    def edit_item(self):
        """编辑选中项"""
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("警告", "请先选择要编辑的项目！")
            return

        item = selection[0]
        values = self.tree.item(item, "values")

        if values:
            # 编辑话术
            old_script = values[0]
            new_script = utils.ask_string(self.root, "编辑话术", "请修改话术内容:", old_script, True)
            if new_script and new_script.strip():
                # 找到对应的分类和索引
                parent = self.tree.parent(item)
                category_text = self.tree.item(parent, "text")
                category = category_text.replace("📁 ", "")

                # 找到话术在列表中的索引
                try:
                    index = self.current_scripts_data[category].index(old_script)
                    # 只更新当前scripts，保存时会同步到scripts_data
                    self.current_scripts_data[category][index] = new_script.strip()
                    # 保存数据
                    self.save_scripts()
                    # 更新过滤数据
                    self.filtered_scripts = self.current_scripts_data.copy()
                    # 更新界面
                    self.update_tree()
                    self.status_var.set("话术已更新")
                except ValueError:
                    messagebox.showerror("错误", "找不到要编辑的话术！")
        else:
            # 编辑分类
            item_text = self.tree.item(item, "text")
            item_text = item_text.replace("📁 ", "")
            old_category = item_text
            new_category = utils.ask_string(self.root, "编辑分类", "请修改分类名称:", old_category)
            if new_category and new_category.strip() and new_category != old_category:
                new_category = new_category.strip()
                if new_category not in self.current_scripts_data:
                    # 只重命名当前scripts，保存时会同步到scripts_data
                    self.current_scripts_data[new_category] = self.current_scripts_data.pop(old_category)
                    # 保存数据
                    self.save_scripts()
                    # 更新过滤数据
                    self.filtered_scripts = self.current_scripts_data.copy()
                    # 更新界面
                    self.update_tree()
                    self.status_var.set(f"✅ 分类已重命名: {old_category} → {new_category}")
                else:
                    messagebox.showwarning("警告", "分类名称已存在！")

    def delete_item(self):
        """删除选中项"""
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("警告", "请先选择要删除的项目！")
            return

        item = selection[0]
        values = self.tree.item(item, "values")

        if values:
            # 删除话术
            script = values[0]
            if messagebox.askyesno("确认删除", f"确定要删除话术:\n{script}",
                                   icon='question', default='no'):
                # 找到对应的分类
                parent = self.tree.parent(item)
                category_text = self.tree.item(parent, "text")
                category = category_text.replace("📁 ", "")

                # 从列表中删除
                try:
                    # 只从当前scripts删除，保存时会同步到scripts_data
                    self.current_scripts_data[category].remove(script)
                    # 保存数据
                    self.save_scripts()
                    # 更新过滤数据
                    self.filtered_scripts = self.current_scripts_data.copy()
                    # 更新界面
                    self.update_tree()
                    self.status_var.set("✅ 话术已删除")
                except ValueError:
                    messagebox.showerror("错误", "找不到要删除的话术！")
        else:
            # 删除分类
            item_text = self.tree.item(item, "text")
            category = item_text.replace("📁 ", "")
            if messagebox.askyesno("确认删除", f"确定要删除分类 '{category}' 及其所有话术吗？",
                                   icon='question', default='no'):
                # 只从当前scripts删除，保存时会同步到scripts_data
                del self.current_scripts_data[category]
                # 保存数据
                self.save_scripts()
                # 更新过滤数据
                self.filtered_scripts = self.current_scripts_data.copy()
                # 更新界面
                self.update_tree()
                self.status_var.set(f"已删除分类: {category}")

    def paste_to_input(self, text):
        """只粘贴到输入框，不发送"""
        try:
            # 检查窗口是否存在
            if self.target_window and not win32gui.IsWindow(self.target_window):
                self.status_var.set("目标窗口已关闭")
                return

            # 激活目标窗口
            if self.target_window:
                win32gui.ShowWindow(self.target_window, win32con.SW_RESTORE)
                win32gui.SetForegroundWindow(self.target_window)
                # time.sleep(0.5)

            # 只粘贴文本，不发送
            pyperclip.copy(text)
            # time.sleep(0.1)
            pyautogui.hotkey('ctrl', 'v')

            self.status_var.set("已添加到输入框")

        except Exception as e:
            self.status_var.set(f"添加失败: {str(e)}")

    # def test_send(self):
    #     """测试发送"""
    #     test_text = "聚雍宝测试 ✓"
    #
    #     if self.send_mode == "添加到剪贴板":
    #         pyperclip.copy(test_text)
    #         self.status_var.set("✅ 测试文本已复制到剪贴板")
    #     elif self.send_mode == "添加到输入框":
    #         if not self.target_window:
    #             messagebox.showwarning("警告", "没有检测到目标窗口！")
    #             return
    #         self.paste_to_input(test_text)
    #     else:  # 直接发送
    #         if not self.target_window:
    #             messagebox.showwarning("警告", "没有检测到目标窗口！")
    #             return
    #         self.send_text_direct(test_text)

    def send_text_direct(self, text):
        """直接发送文本到目标窗口（无延时，自动回车）"""
        try:
            # 检查窗口是否存在
            if self.target_window and not win32gui.IsWindow(self.target_window):
                self.status_var.set("❌ 目标窗口已关闭")
                return

            # 激活目标窗口
            if self.target_window:
                win32gui.ShowWindow(self.target_window, win32con.SW_RESTORE)
                win32gui.SetForegroundWindow(self.target_window)
                time.sleep(0.2)  # 最小必要延时确保窗口激活

            # 发送文本
            pyperclip.copy(text)
            # time.sleep(0.1)
            pyautogui.hotkey('ctrl', 'v')

            # 直接发送模式自动回车
            # time.sleep(0.1)
            pyautogui.press('enter')

            self.status_var.set("已直接发送")

        except Exception as e:
            self.status_var.set(f"发送失败: {str(e)}")

    def toggle_lock(self):
        """切换锁定状态"""
        if not self.target_window:
            messagebox.showwarning("警告", "没有检测到目标窗口！")
            return

        self.is_locked = not self.is_locked
        self.lock_var.set(self.is_locked)

        if self.is_locked:
            self.status_var.set(f"已锁定目标: {self.target_title}")
        else:
            self.status_var.set("🔓 已解锁，恢复自动检测")

        self.update_target_display()

    def show_context_menu(self, event):
        """显示右键菜单式设置"""
        context_menu = tk.Menu(self.root, tearoff=0)

        # 创建发送模式子菜单
        send_mode_menu = tk.Menu(context_menu, tearoff=0)

        # 添加发送模式选项到子菜单
        modes = [
            ("添加到剪贴板", "添加到剪贴板"),
            ("添加到输入框", "添加到输入框"),
            ("直接发送", "直接发送")
        ]

        for display_text, mode_value in modes:
            # 当前模式显示勾选标记
            text = f"✓ {display_text}" if self.send_mode == mode_value else f"   {display_text}"
            send_mode_menu.add_command(
                label=text,
                command=lambda m=mode_value: self.set_send_mode(m)
            )

        # 将子菜单添加到主菜单
        context_menu.add_cascade(label="发送模式", menu=send_mode_menu)

        context_menu.add_separator()

        # 添加数据管理选项
        context_menu.add_command(label="导入数据", command=self.import_data)
        context_menu.add_command(label="导出数据", command=self.export_data)

        # 添加云端数据管理选项
        if self.is_logged_in:
            context_menu.add_separator()
            context_menu.add_command(label="上传数据", command=self.upload_data_to_cloud)
            context_menu.add_command(label="拉取数据", command=self.download_data_from_cloud)

        # 显示菜单
        try:
            context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            context_menu.grab_release()

    def update_tip_text(self):
        """更新提示文字"""
        mode_text = {
            "添加到剪贴板": "复制到剪贴板",
            "添加到输入框": "添加到输入框",
            "直接发送": "直接发送"
        }
        tip = f"双击话术 → {mode_text.get(self.send_mode, self.send_mode)}"
        if hasattr(self, 'tip_var'):
            self.tip_var.set(tip)

    def set_send_mode(self, mode):
        """设置发送模式"""
        self.send_mode = mode
        self.mode_var.set(mode)
        self.save_config()
        self.update_tip_text()
        self.status_var.set(f"发送模式: {mode}")

    # def toggle_always_on_top(self):
    #     """切换窗口置顶状态"""
    #     self.always_on_top = not self.always_on_top
    #     self.root.attributes('-topmost', self.always_on_top)
    #     self.save_config()
    #
    #     status_text = "窗口已置顶" if self.always_on_top else "窗口已取消置顶"
    #     self.status_var.set(status_text)

    def on_topmost_changed(self):
        """置顶勾选框变化事件"""
        self.always_on_top = self.topmost_var.get()
        self.root.attributes('-topmost', self.always_on_top)
        self.save_config()

        status_text = "窗口已置顶" if self.always_on_top else "窗口已取消置顶"
        self.status_var.set(status_text)

    def on_lock_changed(self):
        """锁定勾选框变化事件"""
        self.is_locked = self.lock_var.get()

        if self.is_locked:
            if not self.target_window:
                # 如果没有目标窗口，取消锁定
                self.lock_var.set(False)
                self.is_locked = False
                messagebox.showwarning("警告", "没有检测到目标窗口！")
                return
            self.status_var.set(f"🔒 已锁定目标: {self.target_title}")
        else:
            self.status_var.set("🔓 已解锁，恢复自动检测")

        self.update_target_display()

    def on_search_focus_in(self, event):
        """搜索框获得焦点"""
        if self.search_entry.get() == self.search_placeholder:
            self.search_entry.delete(0, tk.END)
            self.search_entry.config(foreground='black')

    def on_search_focus_out(self, event):
        """搜索框失去焦点"""
        if not self.search_entry.get():
            self.search_entry.insert(0, self.search_placeholder)
            self.search_entry.config(foreground='gray')

    def on_search_change(self, *args):
        """搜索内容变化时的处理"""
        search_text = self.search_var.get().strip()

        # 如果是占位符文本，不进行搜索
        if search_text == self.search_placeholder or not search_text:
            # 如果搜索框为空，显示当前Tab的所有话术
            self.filtered_scripts = self.current_scripts_data.copy()
        else:
            # 搜索所有Tab中包含关键词的话术
            search_text = search_text.lower()
            self.filtered_scripts = {}

            # 遍历所有Tab的数据
            for primary_tab, secondary_tabs in self.scripts_data.items():
                for secondary_tab, categories in secondary_tabs.items():
                    for category, scripts in categories.items():
                        filtered_scripts = [script for script in scripts
                                            if search_text in script.lower()]
                        if filtered_scripts:
                            # 创建带Tab信息的分类名称
                            display_category = f"[{primary_tab}-{secondary_tab}] {category}"
                            self.filtered_scripts[display_category] = filtered_scripts

        self.update_tree()

    def clear_search(self):
        """清空搜索"""
        self.search_entry.delete(0, tk.END)
        self.search_entry.insert(0, self.search_placeholder)
        self.search_entry.config(foreground='gray')
        # 恢复到当前Tab的数据显示
        self.filtered_scripts = self.current_scripts_data.copy()
        self.update_tree()

    def on_primary_tab_changed(self, event):
        """一级Tab切换事件"""
        try:
            selected_tab = event.widget.tab('current')['text']
            if selected_tab != self.current_primary_tab:
                # 保存当前数据
                self.save_scripts()

                # 切换到新Tab
                self.current_primary_tab = selected_tab
                self.current_secondary_tab = list(self.scripts_data[selected_tab].keys())[0]

                # 更新二级Tab和数据
                self.update_secondary_tabs()
                self.load_current_scripts_data()
        except:
            pass

    def select_secondary_tab(self, tab_name):
        """选择二级Tab"""
        if tab_name != self.current_secondary_tab:
            # 保存当前数据
            self.save_scripts()

            # 切换到新Tab
            self.current_secondary_tab = tab_name
            self.load_current_scripts_data()

            # 更新按钮样式
            self.update_secondary_tab_styles()

    def update_secondary_tab_styles(self):
        """更新二级Tab按钮样式"""
        for tab_name, btn in self.secondary_tab_buttons.items():
            if tab_name == self.current_secondary_tab:
                btn.configure(style='Selected.TButton')
            else:
                btn.configure(style='TButton')

    def show_secondary_tab_context_menu(self, event, tab_name):
        """显示二级Tab右键菜单"""
        context_menu = tk.Menu(self.root, tearoff=0)
        context_menu.add_command(label="修改名称",
                                 command=lambda: self.rename_secondary_tab_by_name(tab_name))
        context_menu.add_command(label="删除分类",
                                 command=lambda: self.delete_secondary_tab_by_name(tab_name))

        # 显示菜单
        try:
            context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            context_menu.grab_release()

    def load_current_scripts_data(self):
        """加载当前Tab的数据"""
        self.current_scripts_data = self.get_current_scripts_data()
        self.filtered_scripts = self.current_scripts_data.copy()
        self.update_tree()

        # 清空搜索
        if hasattr(self, 'search_entry'):
            self.search_entry.delete(0, tk.END)
            self.search_entry.insert(0, self.search_placeholder)
            self.search_entry.config(foreground='gray')

    def on_primary_tab_scroll(self, event):
        """处理一级Tab的滚轮滚动事件"""
        try:
            # 获取当前选中的Tab索引
            current_index = self.primary_notebook.index('current')
            total_tabs = len(self.primary_notebook.tabs())

            if total_tabs <= 1:
                return

            # 根据滚动方向切换Tab
            if event.delta > 0 or event.num == 4:  # 向上滚动
                new_index = (current_index - 1) % total_tabs
            else:  # 向下滚动
                new_index = (current_index + 1) % total_tabs

            # 切换到新Tab
            self.primary_notebook.select(new_index)
        except:
            pass

    def add_primary_tab(self):
        """添加一级Tab"""
        tab_name = utils.ask_string(self.root, "新增一级分类", "请输入分类名称:")
        if tab_name and tab_name.strip():
            tab_name = tab_name.strip()
            if tab_name not in self.scripts_data:
                # 保存当前Tab数据
                self.save_scripts()

                # 添加到数据结构
                self.scripts_data[tab_name] = {"默认": {}}

                # 添加到界面
                tab_frame = ttk.Frame(self.primary_notebook)
                self.primary_tabs[tab_name] = tab_frame
                self.primary_notebook.add(tab_frame, text=tab_name)

                # 切换到新Tab
                self.current_primary_tab = tab_name
                self.current_secondary_tab = "默认"

                # 选择新添加的Tab
                self.primary_notebook.select(tab_frame)

                # 更新界面
                self.update_secondary_tabs()
                self.load_current_scripts_data()
                self.save_scripts()
                self.status_var.set(f"已添加一级分类: {tab_name}")
            else:
                messagebox.showwarning("警告", "分类名称已存在！")

    def add_secondary_tab(self):
        """添加二级Tab"""
        tab_name = utils.ask_string(self.root, "新增二级分类", f"请输入分类名称（所属: {self.current_primary_tab}）:")
        if tab_name and tab_name.strip():
            tab_name = tab_name.strip()
            if tab_name not in self.scripts_data[self.current_primary_tab]:
                # 添加到数据结构
                self.scripts_data[self.current_primary_tab][tab_name] = {}

                # 切换到新Tab
                self.current_secondary_tab = tab_name

                # 重新更新二级Tab按钮
                self.update_secondary_tabs()
                self.load_current_scripts_data()
                self.save_scripts()
                self.status_var.set(f"已添加二级分类: {tab_name}")
            else:
                messagebox.showwarning("警告", "分类名称已存在！")

    def show_primary_tab_menu(self, event):
        """显示一级Tab右键菜单"""
        print("No tab clicked", event.x, event.y)
        try:
            # 获取点击的Tab
            clicked_tab = self.primary_notebook.tk.call(self.primary_notebook._w, "identify", "tab", event.x, event.y)
            if clicked_tab == "":
                return

            tab_text = self.primary_notebook.tab(clicked_tab, "text")

            # 创建右键菜单
            context_menu = tk.Menu(self.root, tearoff=0)
            context_menu.add_command(label="修改名称",
                                     command=lambda: self.rename_primary_tab(clicked_tab, tab_text))
            context_menu.add_command(label="删除分类",
                                     command=lambda: self.delete_primary_tab(clicked_tab, tab_text))

            # 显示菜单
            context_menu.tk_popup(event.x_root, event.y_root)
        except Exception as e:
            print('e', e)

    def rename_primary_tab(self, tab_index, old_name):
        """重命名一级Tab"""
        new_name = utils.ask_string(self.root, "修改名称", "请输入新的分类名称:", old_name)
        if new_name and new_name.strip() and new_name != old_name:
            new_name = new_name.strip()
            if new_name not in self.scripts_data:
                # 更新数据结构
                self.scripts_data[new_name] = self.scripts_data.pop(old_name)

                # 更新界面
                self.primary_notebook.tab(tab_index, text=new_name)

                # 更新当前Tab名称
                if self.current_primary_tab == old_name:
                    self.current_primary_tab = new_name

                # 更新tabs字典
                self.primary_tabs[new_name] = self.primary_tabs.pop(old_name)

                self.save_scripts()
                self.status_var.set(f"✅ 已重命名: {old_name} → {new_name}")
            else:
                messagebox.showwarning("警告", "分类名称已存在！")

    def delete_primary_tab(self, tab_index, tab_name):
        """删除一级Tab"""
        if len(self.scripts_data) <= 1:
            messagebox.showwarning("警告", "至少需要保留一个一级分类！")
            return

        if messagebox.askyesno("确认删除", f"确定要删除一级分类 '{tab_name}' 及其所有数据吗？",
                               icon='question', default='no'):
            try:
                # 从数据结构中删除
                if tab_name in self.scripts_data:
                    del self.scripts_data[tab_name]
                if tab_name in self.primary_tabs:
                    del self.primary_tabs[tab_name]

                # 从界面中删除
                self.primary_notebook.forget(tab_index)

                # 切换到第一个Tab
                if self.scripts_data:
                    first_tab = list(self.scripts_data.keys())[0]
                    self.current_primary_tab = first_tab
                    self.current_secondary_tab = list(self.scripts_data[first_tab].keys())[0]
                    self.update_secondary_tabs()
                    self.load_current_scripts_data()

                self.save_scripts()
                self.status_var.set(f"已删除一级分类: {tab_name}")
            except Exception as e:
                messagebox.showerror("错误", f"删除失败: {str(e)}")
                self.status_var.set(f"❌ 删除失败: {str(e)}")

    # ==================== 用户登录/登出 ====================
    def show_login_dialog(self):
        """显示登录对话框"""
        if self.is_logged_in:
            # 如果已登录，显示登出选项
            if messagebox.askyesno("登出确认", f"当前用户: {self.current_user_id}确定要登出吗？"):
                self.logout_user()
            return

        # 显示登录对话框
        result = show_login_dialog(self.root, self._handle_login)
        
    def _handle_login(self, username: str, password: str) -> bool:
        """处理登录逻辑"""
        try:
            # 检查API管理器是否可用
            if not self.api_manager:
                messagebox.showerror("登录失败", "API服务不可用")
                return False

            # 调用API登录
            result = self.api_manager.login(username, password)
            if result.get('success'):
                self.current_user_id = result.get('user_id') or username
                self.is_logged_in = True

                # 同步云端数据
                self.sync_cloud_data()

                # 保存配置
                self.save_config()

                # 更新界面
                self.update_login_status()

                messagebox.showinfo("登录成功", f"欢迎回来，{username}！")
                return True
            else:
                messagebox.showerror("登录失败", result.get('message', '用户名或密码错误'))
                return False
        except Exception as e:
            messagebox.showerror("登录失败", f"登录时发生错误: {str(e)}")
            return False

    def logout_user(self):
        """用户登出"""
        try:
            if self.api_manager:
                self.api_manager.logout()

            self.current_user_id = None
            self.is_logged_in = False

            # 重新初始化数据适配器为默认用户
            self.data_adapter = DataAdapter(
                api_manager=self.api_manager,
                script_file=self.script_file,
                config_file=self.config_file,
                user_id=0
            )

            # 重新渲染页面数据
            self.refresh_all_ui()
            self.update_login_status()

            # 保存配置
            self.save_config()

            self.status_var.set("已登出")
        except Exception as e:
            messagebox.showerror("登出失败", f"登出时发生错误: {str(e)}")

    def update_login_status(self):
        """更新登录状态显示"""
        if self.is_logged_in and self.current_user_id:
            self.login_btn.configure(text=f"用户:{self.current_user_id[:6]}...")
        else:
            self.login_btn.configure(text="登录")
    # ==================== 数据更新 ====================
    def upload_data_to_cloud(self):
        """手动上传数据到云端"""
        try:
            if not self.is_logged_in or not self.current_user_id:
                messagebox.showwarning("警告", "请先登录后再上传数据！")
                return

            if not self.api_manager:
                messagebox.showerror("错误", "API服务不可用")
                return

            # 确认上传
            confirm_msg = "确定要将本地数据上传到云端吗？\
这将覆盖云端的现有数据。"
            if not messagebox.askyesno("确认上传", confirm_msg):
                return

            # 启用API功能
            self.data_adapter.api_manager = self.api_manager
            self.data_adapter.user_id = self.current_user_id

            # # 准备上传数据
            # full_data = {
            #     "user_id": self.current_user_id,
            #     "scripts_data":
            # }

            # 上传到云端
            success = self.data_adapter.push_local_scripts_data(data=self.scripts_data)
            if success:
                messagebox.showinfo("上传成功", "数据已成功上传到云端！")  # type: ignore
                self.status_var.set("数据上传成功")
            else:
                messagebox.showerror("上传失败", "数据上传失败，请稍后重试")  # type: ignore
                self.status_var.set("数据上传失败")

        except Exception as e:
            messagebox.showerror("上传失败", f"上传时发生错误: {str(e)}")  # type: ignore
            self.status_var.set(f"上传失败: {str(e)}")

    def download_data_from_cloud(self):
        """手动从云端下载数据"""
        try:
            if not self.is_logged_in or not self.current_user_id:
                messagebox.showwarning("警告", "请先登录后再下载数据！")
                return

            if not self.api_manager:
                messagebox.showerror("错误", "API服务不可用")
                return

            # 确认下载
            if not messagebox.askyesno("确认下载", "确定要从云端下载数据吗？\
这将覆盖本地的现有数据。"):
                return

            # # 启用API功能
            # self.data_adapter.api_manager = self.api_manager
            # self.data_adapter.user_id = self.current_user_id

            # 从云端下载数据
            success = self.data_adapter.load_user_data()
            if success:
                # 刷新所有界面元素
                self.refresh_all_ui()

                messagebox.showinfo("下载成功", "数据已成功从云端下载！")
                self.status_var.set("数据下载成功")
            else:
                messagebox.showwarning("下载失败", "云端暂无数据或下载失败")
                self.status_var.set("云端暂无数据")
        except Exception as e:
            messagebox.showerror("下载失败", f"下载时发生错误: {str(e)}")
            self.status_var.set(f"下载失败: {str(e)}")

    def sync_cloud_data(self):
        """同步云端数据（登录时自动调用）"""
        try:
            if not self.is_logged_in or not self.current_user_id:
                print("用户未登录，无法同步云端数据")
                return False

            if self.data_adapter:
                # 登录后启用API功能
                self.data_adapter.api_manager = self.api_manager
                self.data_adapter.user_id = self.current_user_id

                # 刷新云端数据
                success = self.data_adapter.load_user_data()
                if success:
                    # 刷新所有界面元素
                    self.refresh_all_ui()

                    self.status_var.set("云端数据同步成功")
                    return True
                else:
                    self.status_var.set("使用默认数据")
                    return False
        except Exception as e:
            print(f"同步云端数据失败: {e}")
            self.status_var.set("数据同步失败，使用本地数据")
            return False

    def import_data(self):
        """导入数据"""
        from tkinter import filedialog

        file_path = filedialog.askopenfilename(
            title="选择要导入的文件",
            filetypes=[
                ("Excel文件", "*.xlsx *.xls"),
                ("CSV文件", "*.csv"),
                ("JSON文件", "*.json"),
                ("所有文件", "*.*")
            ]
        )

        if file_path and self.data_adapter:
            try:
                success = self.data_adapter.import_data_from_file(file_path)
                if success:
                    # 刷新所有界面元素
                    self.refresh_all_ui()
                    messagebox.showinfo("导入成功", "数据导入成功！")
                else:
                    messagebox.showerror("导入失败", "数据导入失败，请检查文件格式！")
            except Exception as e:
                messagebox.showerror("导入失败", f"导入时发生错误: {str(e)}")

    def export_data(self):
        """导出数据"""
        from tkinter import filedialog

        file_path = filedialog.asksaveasfilename(
            title="选择导出位置",
            defaultextension=".xlsx",
            filetypes=[
                ("Excel文件", "*.xlsx"),
                ("CSV文件", "*.csv"),
                ("JSON文件", "*.json")
            ]
        )

        if file_path and self.data_adapter:
            try:
                # 根据文件扩展名确定格式
                if file_path.endswith('.xlsx') or file_path.endswith('.xls'):
                    file_format = "excel"
                elif file_path.endswith('.csv'):
                    file_format = "csv"
                else:
                    file_format = "json"

                success = self.data_adapter.export_data_to_file(file_path, file_format)
                if success:
                    messagebox.showinfo("导出成功", f"数据已导出到: {file_path}")
                else:
                    messagebox.showerror("导出失败", "数据导出失败！")
            except Exception as e:
                messagebox.showerror("导出失败", f"导出时发生错误: {str(e)}")

    def on_closing(self):
        """关闭程序"""
        self.monitoring = False
        self.save_scripts()
        self.save_config()
        self.root.destroy()

    def run(self):
        """运行程序"""
        self.root.mainloop()


if __name__ == "__main__":
    try:
        app = AssistantOptimized()
        app.run()
    except Exception as e:
        print(f"程序启动失败: {e}")
        input("按回车键退出...")
