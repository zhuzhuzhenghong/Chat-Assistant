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

def ask_string(parent, title, prompt, initial_value="", multiline=False):
    """显示中文输入对话框"""
    dialog = ChineseInputDialog(parent, title, prompt, initial_value, multiline)
    return dialog.show()

class AssistantOptimized:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("聚雍宝")
        self.root.geometry("380x700")
        self.root.resizable(True, True)
        
        # 核心数据
        self.data_file = "scripts.json"
        
        # Tab数据结构 - 先设置默认值
        self.current_primary_tab = "公司话术"
        self.current_secondary_tab = "常用"
        
        # 初始化Tab数据结构
        self.init_tab_structure()
        
        # 加载数据（这会更新tab_data和当前Tab设置）
        self.scripts = self.load_scripts()
        
        # 目标窗口跟踪
        self.target_window = None
        self.target_title = "无"
        self.monitoring = True
        self.my_window_handle = None
        self.is_locked = False
        
        # 发送模式配置
        self.send_mode = "直接发送"  # 默认模式
        self.always_on_top = True  # 默认置顶
        self.config_file = "config.json"
        self.load_config()
        
        # 创建界面
        self.create_widgets()
        # 根据配置设置窗口置顶状态
        self.root.attributes('-topmost', self.always_on_top)
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # 启动监控
        self.root.after(500, self.init_monitoring)
    
    def init_tab_structure(self):
        """初始化Tab数据结构"""
        if not hasattr(self, 'tab_data') or not self.tab_data:
            self.tab_data = {
                "公司话术": {
                    "常用": {},
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
    
    def load_scripts(self):
        """加载话术数据"""
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # 检查是否是新的Tab结构
                    if isinstance(data, dict) and any(key in data for key in ["公司话术", "小组话术", "私人话术"]):
                        self.tab_data = data
                        # 确保当前Tab存在
                        if self.current_primary_tab not in self.tab_data:
                            self.current_primary_tab = list(self.tab_data.keys())[0]
                        if self.current_secondary_tab not in self.tab_data[self.current_primary_tab]:
                            self.current_secondary_tab = list(self.tab_data[self.current_primary_tab].keys())[0]
                        # 返回当前选中Tab的数据
                        return self.get_current_tab_data()
                    else:
                        # 旧格式数据，迁移到新结构
                        self.migrate_old_data(data)
                        return self.get_current_tab_data()
            except Exception as e:
                print(f"加载数据失败: {e}")
        
        # 默认数据
        default_data = {
            "问候语": [
                "您好，很高兴为您服务！",
                "欢迎咨询，请问有什么可以帮助您的吗？",
                "您好，我是客服小助手，有什么问题可以随时问我哦~"
            ],
            "常见问题": [
                "请稍等，我帮您查询一下相关信息",
                "这个问题我需要为您详细解答一下",
                "根据您的情况，我建议您这样处理",
                "如果还有其他问题，请随时联系我们"
            ],
            "快捷回复": [
                "好的，明白了",
                "收到，正在处理",
                "稍等一下",
                "没问题",
                "可以的",
                "👍"
            ],
            "结束语": [
                "感谢您的咨询，祝您生活愉快！",
                "如果没有其他问题，本次服务就到这里了，谢谢！",
                "很高兴为您服务，期待下次为您提供帮助"
            ]
        }
        
        # 初始化Tab结构并设置默认数据
        self.init_tab_structure()
        self.tab_data["公司话术"]["常用"] = default_data
        return default_data
    
    def migrate_old_data(self, old_data):
        """迁移旧数据到新Tab结构"""
        self.init_tab_structure()
        self.tab_data["公司话术"]["常用"] = old_data
    
    def get_current_tab_data(self):
        """获取当前选中Tab的数据"""
        if hasattr(self, 'tab_data'):
            return self.tab_data.get(self.current_primary_tab, {}).get(self.current_secondary_tab, {})
        return {}
    
    def save_scripts(self):
        """保存话术数据"""
        try:
            # 保存当前Tab的数据
            if hasattr(self, 'tab_data'):
                self.tab_data[self.current_primary_tab][self.current_secondary_tab] = self.scripts
                with open(self.data_file, 'w', encoding='utf-8') as f:
                    json.dump(self.tab_data, f, ensure_ascii=False, indent=2)
        except:
            pass
    
    def load_config(self):
        """加载配置"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    self.send_mode = config.get('send_mode', '直接发送')
                    self.always_on_top = config.get('always_on_top', True)
            except:
                pass
    
    def save_config(self):
        """保存配置"""
        try:
            config = {
                'send_mode': self.send_mode,
                'always_on_top': self.always_on_top
            }
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
        except:
            pass
    
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
            if len(display_title) > 25:
                display_title = display_title[:25] + "..."
            
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
        if hasattr(self, 'tab_data') and self.tab_data:
            for tab_name in self.tab_data.keys():
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
        secondary_tab_frame = ttk.LabelFrame(main_frame, text="二级分类", padding="5")
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
        search_frame = ttk.LabelFrame(main_frame, text="搜索话术", padding="5")
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
        
        # 设置按钮（右下角）
        settings_btn = ttk.Button(status_frame, text="⚙️", width=4)
        settings_btn.grid(row=0, column=1, sticky="e")
        settings_btn.bind('<Button-1>', self.show_context_menu)
        
        # 存储原始数据用于搜索
        self.filtered_scripts = self.scripts.copy()
        
        # 初始化Tab显示 - 确保选中正确的Tab
        if hasattr(self, 'tab_data') and self.tab_data:
            # 选中当前的一级Tab
            for i, tab_name in enumerate(self.tab_data.keys()):
                if tab_name == self.current_primary_tab:
                    self.primary_notebook.select(i)
                    break
        
        self.update_secondary_tabs()
        self.update_tree()
    
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
        new_name = ask_string(self.root, "修改名称", "请输入新的分类名称:", old_name)
        if new_name and new_name.strip() and new_name != old_name:
            new_name = new_name.strip()
            if new_name not in self.tab_data[self.current_primary_tab]:
                # 更新数据结构
                self.tab_data[self.current_primary_tab][new_name] = self.tab_data[self.current_primary_tab].pop(old_name)
                
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
        if len(self.tab_data[self.current_primary_tab]) <= 1:
            messagebox.showwarning("警告", "至少需要保留一个二级分类！")
            return
        
        if messagebox.askyesno("确认删除", f"确定要删除二级分类 '{tab_name}' 及其所有话术吗？", 
                              icon='question', default='no'):
            try:
                # 从数据结构中删除
                if tab_name in self.tab_data[self.current_primary_tab]:
                    del self.tab_data[self.current_primary_tab][tab_name]
                
                # 如果删除的是当前Tab，切换到第一个Tab
                if self.current_secondary_tab == tab_name:
                    if self.tab_data[self.current_primary_tab]:
                        first_secondary = list(self.tab_data[self.current_primary_tab].keys())[0]
                        self.current_secondary_tab = first_secondary
                        self.load_current_tab_data()
                
                # 更新界面
                self.update_secondary_tabs()
                self.save_scripts()
                self.status_var.set(f"已删除二级分类: {tab_name}")
            except Exception as e:
                messagebox.showerror("错误", f"删除失败: {str(e)}")
                self.status_var.set(f"删除失败: {str(e)}")
    
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
        category = ask_string(self.root, "添加分类", "请输入分类名称:")
        if category and category.strip():
            category = category.strip()
            if category not in self.scripts:
                # 只添加到当前scripts，保存时会同步到tab_data
                self.scripts[category] = []
                # 保存数据
                self.save_scripts()
                # 更新过滤数据
                self.filtered_scripts = self.scripts.copy()
                # 更新界面
                self.update_tree()
                self.status_var.set(f"已添加分类: {category}")
            else:
                messagebox.showwarning("警告", "分类已存在！")
    
    def add_script(self):
        """添加话术"""
        # 获取选中的分类
        selection = self.tree.selection()
        category = None
        
        if selection:
            item = selection[0]
            # 如果选中的是话术，获取其父分类
            parent = self.tree.parent(item)
            if parent:
                category_text = self.tree.item(parent, "text")
                category = category_text
            else:
                # 选中的是分类
                category_text = self.tree.item(item, "text")
                category = category_text
        
        if not category:
            # 如果没有选中，让用户选择分类
            categories = list(self.scripts.keys())
            if not categories:
                messagebox.showwarning("警告", "请先添加分类！")
                return
            
            category = ask_string(self.root, "选择分类", f"请输入分类名称（现有分类: {', '.join(categories)}）:")
            if not category or category not in self.scripts:
                messagebox.showwarning("警告", "请输入有效的分类名称！")
                return
        
        script = ask_string(self.root, "添加话术", f"请输入话术内容（分类: {category}）:", "", True)
        if script and script.strip():
            # 只添加到当前scripts，保存时会同步到tab_data
            self.scripts[category].append(script.strip())
            # 保存数据
            self.save_scripts()
            # 更新过滤数据
            self.filtered_scripts = self.scripts.copy()
            # 更新界面
            self.update_tree()
            self.status_var.set(f"已添加话术到 {category}")
    
    def add_script_to_category(self, item):
        """向指定分类添加话术"""
        # 获取分类名称
        category_text = self.tree.item(item, "text")
        category = category_text.replace("📁 ", "")
        
        # 确保分类存在，如果不存在则创建
        if category not in self.scripts:
            self.scripts[category] = []
        
        script = ask_string(self.root, "添加话术", f"请输入话术内容（分类: {category}）:", "", True)
        if script and script.strip():
            # 添加到当前scripts
            self.scripts[category].append(script.strip())
            # 保存数据
            self.save_scripts()
            # 更新过滤数据
            self.filtered_scripts = self.scripts.copy()
            # 更新界面
            self.update_tree()
            self.status_var.set(f"✅ 已添加话术到 {category}")
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
            new_script = ask_string(self.root, "编辑话术", "请修改话术内容:", old_script, True)
            if new_script and new_script.strip():
                # 找到对应的分类和索引
                parent = self.tree.parent(item)
                category_text = self.tree.item(parent, "text")
                category = category_text.replace("📁 ", "")
                
                # 找到话术在列表中的索引
                try:
                    index = self.scripts[category].index(old_script)
                    # 只更新当前scripts，保存时会同步到tab_data
                    self.scripts[category][index] = new_script.strip()
                    # 保存数据
                    self.save_scripts()
                    # 更新过滤数据
                    self.filtered_scripts = self.scripts.copy()
                    # 更新界面
                    self.update_tree()
                    self.status_var.set("话术已更新")
                except ValueError:
                    messagebox.showerror("错误", "找不到要编辑的话术！")
        else:
            # 编辑分类
            item_text = self.tree.item(item, "text")
            old_category = item_text
            new_category = ask_string(self.root, "编辑分类", "请修改分类名称:", old_category)
            if new_category and new_category.strip() and new_category != old_category:
                new_category = new_category.strip()
                if new_category not in self.scripts:
                    # 只重命名当前scripts，保存时会同步到tab_data
                    self.scripts[new_category] = self.scripts.pop(old_category)
                    # 保存数据
                    self.save_scripts()
                    # 更新过滤数据
                    self.filtered_scripts = self.scripts.copy()
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
                    # 只从当前scripts删除，保存时会同步到tab_data
                    self.scripts[category].remove(script)
                    # 保存数据
                    self.save_scripts()
                    # 更新过滤数据
                    self.filtered_scripts = self.scripts.copy()
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
                # 只从当前scripts删除，保存时会同步到tab_data
                del self.scripts[category]
                # 保存数据
                self.save_scripts()
                # 更新过滤数据
                self.filtered_scripts = self.scripts.copy()
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
                time.sleep(0.5)
            
            # 只粘贴文本，不发送
            pyperclip.copy(text)
            time.sleep(0.1)
            pyautogui.hotkey('ctrl', 'v')
            
            self.status_var.set("已添加到输入框")
            
        except Exception as e:
            self.status_var.set(f"添加失败: {str(e)}")
    
    def test_send(self):
        """测试发送"""
        test_text = "聚雍宝测试 ✓"
        
        if self.send_mode == "添加到剪贴板":
            pyperclip.copy(test_text)
            self.status_var.set("✅ 测试文本已复制到剪贴板")
        elif self.send_mode == "添加到输入框":
            if not self.target_window:
                messagebox.showwarning("警告", "没有检测到目标窗口！")
                return
            self.paste_to_input(test_text)
        else:  # 直接发送
            if not self.target_window:
                messagebox.showwarning("警告", "没有检测到目标窗口！")
                return
            self.send_text_direct(test_text)
    
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
                time.sleep(0.3)  # 最小必要延时确保窗口激活
            
            # 发送文本
            pyperclip.copy(text)
            time.sleep(0.1)
            pyautogui.hotkey('ctrl', 'v')
            
            # 直接发送模式自动回车
            time.sleep(0.1)
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
    
    def toggle_always_on_top(self):
        """切换窗口置顶状态"""
        self.always_on_top = not self.always_on_top
        self.root.attributes('-topmost', self.always_on_top)
        self.save_config()
        
        status_text = "窗口已置顶" if self.always_on_top else "窗口已取消置顶"
        self.status_var.set(status_text)
    
    def on_topmost_changed(self):
        """置顶勾选框变化事件"""
        self.always_on_top = self.topmost_var.get()
        self.root.attributes('-topmost', self.always_on_top)
        self.save_config()
        
        status_text = "✅ 窗口已置顶" if self.always_on_top else "✅ 窗口已取消置顶"
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
            self.filtered_scripts = self.scripts.copy()
        else:
            # 搜索所有Tab中包含关键词的话术
            search_text = search_text.lower()
            self.filtered_scripts = {}
            
            # 遍历所有Tab的数据
            for primary_tab, secondary_tabs in self.tab_data.items():
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
        self.filtered_scripts = self.scripts.copy()
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
                self.current_secondary_tab = list(self.tab_data[selected_tab].keys())[0]
                
                # 更新二级Tab和数据
                self.update_secondary_tabs()
                self.load_current_tab_data()
        except:
            pass
    

    
    def update_secondary_tabs(self):
        """更新二级Tab按钮"""
        # 清空现有的二级Tab按钮
        for widget in self.secondary_buttons_frame.winfo_children():
            widget.destroy()
        self.secondary_tab_buttons.clear()
        
        # 添加当前一级Tab对应的二级Tab按钮
        if self.current_primary_tab in self.tab_data:
            row = 0
            col = 0
            max_cols = 5  # 每行最多5个按钮，避免过于拥挤
            
            for tab_name in self.tab_data[self.current_primary_tab].keys():
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
    
    def select_secondary_tab(self, tab_name):
        """选择二级Tab"""
        if tab_name != self.current_secondary_tab:
            # 保存当前数据
            self.save_scripts()
            
            # 切换到新Tab
            self.current_secondary_tab = tab_name
            self.load_current_tab_data()
            
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
    
    def load_current_tab_data(self):
        """加载当前Tab的数据"""
        self.scripts = self.get_current_tab_data()
        self.filtered_scripts = self.scripts.copy()
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
        tab_name = ask_string(self.root, "新增一级分类", "请输入分类名称:")
        if tab_name and tab_name.strip():
            tab_name = tab_name.strip()
            if tab_name not in self.tab_data:
                # 保存当前Tab数据
                self.save_scripts()
                
                # 添加到数据结构
                self.tab_data[tab_name] = {"默认": {}}
                
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
                self.load_current_tab_data()
                self.save_scripts()
                self.status_var.set(f"已添加一级分类: {tab_name}")
            else:
                messagebox.showwarning("警告", "分类名称已存在！")
    
    def add_secondary_tab(self):
        """添加二级Tab"""
        tab_name = ask_string(self.root, "新增二级分类", f"请输入分类名称（所属: {self.current_primary_tab}）:")
        if tab_name and tab_name.strip():
            tab_name = tab_name.strip()
            if tab_name not in self.tab_data[self.current_primary_tab]:
                # 添加到数据结构
                self.tab_data[self.current_primary_tab][tab_name] = {}
                
                # 切换到新Tab
                self.current_secondary_tab = tab_name
                
                # 重新更新二级Tab按钮
                self.update_secondary_tabs()
                self.load_current_tab_data()
                self.save_scripts()
                self.status_var.set(f"已添加二级分类: {tab_name}")
            else:
                messagebox.showwarning("警告", "分类名称已存在！")
    
    def show_primary_tab_menu(self, event):
        """显示一级Tab右键菜单"""
        try:
            # 获取点击的Tab
            clicked_tab = self.primary_notebook.identify("tab", event.x, event.y)
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
        except:
            pass
    
    def show_secondary_tab_menu(self, event):
        """显示二级Tab右键菜单"""
        try:
            # 获取点击的Tab
            clicked_tab = self.secondary_notebook.identify("tab", event.x, event.y)
            if clicked_tab == "":
                return
            
            tab_text = self.secondary_notebook.tab(clicked_tab, "text")
            
            # 创建右键菜单
            context_menu = tk.Menu(self.root, tearoff=0)
            context_menu.add_command(label="修改名称", 
                                   command=lambda: self.rename_secondary_tab(clicked_tab, tab_text))
            context_menu.add_command(label="删除分类", 
                                   command=lambda: self.delete_secondary_tab(clicked_tab, tab_text))
            
            # 显示菜单
            context_menu.tk_popup(event.x_root, event.y_root)
        except:
            pass
    
    def rename_primary_tab(self, tab_index, old_name):
        """重命名一级Tab"""
        new_name = ask_string(self.root, "修改名称", "请输入新的分类名称:", old_name)
        if new_name and new_name.strip() and new_name != old_name:
            new_name = new_name.strip()
            if new_name not in self.tab_data:
                # 更新数据结构
                self.tab_data[new_name] = self.tab_data.pop(old_name)
                
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
    
    def rename_secondary_tab(self, tab_index, old_name):
        """重命名二级Tab"""
        new_name = ask_string(self.root, "修改名称", "请输入新的分类名称:", old_name)
        if new_name and new_name.strip() and new_name != old_name:
            new_name = new_name.strip()
            if new_name not in self.tab_data[self.current_primary_tab]:
                # 更新数据结构
                self.tab_data[self.current_primary_tab][new_name] = self.tab_data[self.current_primary_tab].pop(old_name)
                
                # 更新界面
                self.secondary_notebook.tab(tab_index, text=new_name)
                
                # 更新当前Tab名称
                if self.current_secondary_tab == old_name:
                    self.current_secondary_tab = new_name
                
                self.save_scripts()
                self.status_var.set(f"✅ 已重命名: {old_name} → {new_name}")
            else:
                messagebox.showwarning("警告", "分类名称已存在！")
    
    def delete_primary_tab(self, tab_index, tab_name):
        """删除一级Tab"""
        if len(self.tab_data) <= 1:
            messagebox.showwarning("警告", "至少需要保留一个一级分类！")
            return
        
        if messagebox.askyesno("确认删除", f"确定要删除一级分类 '{tab_name}' 及其所有数据吗？", 
                              icon='question', default='no'):
            try:
                # 从数据结构中删除
                if tab_name in self.tab_data:
                    del self.tab_data[tab_name]
                if tab_name in self.primary_tabs:
                    del self.primary_tabs[tab_name]
                
                # 从界面中删除
                self.primary_notebook.forget(tab_index)
                
                # 切换到第一个Tab
                if self.tab_data:
                    first_tab = list(self.tab_data.keys())[0]
                    self.current_primary_tab = first_tab
                    self.current_secondary_tab = list(self.tab_data[first_tab].keys())[0]
                    self.update_secondary_tabs()
                    self.load_current_tab_data()
                
                self.save_scripts()
                self.status_var.set(f"已删除一级分类: {tab_name}")
            except Exception as e:
                messagebox.showerror("错误", f"删除失败: {str(e)}")
                self.status_var.set(f"❌ 删除失败: {str(e)}")
    
    def delete_secondary_tab(self, tab_index, tab_name):
        """删除二级Tab"""
        if len(self.tab_data[self.current_primary_tab]) <= 1:
            messagebox.showwarning("警告", "至少需要保留一个二级分类！")
            return
        
        if messagebox.askyesno("确认删除", f"确定要删除二级分类 '{tab_name}' 及其所有话术吗？", 
                              icon='question', default='no'):
            try:
                # 从数据结构中删除
                if tab_name in self.tab_data[self.current_primary_tab]:
                    del self.tab_data[self.current_primary_tab][tab_name]
                
                # 从界面中删除
                self.secondary_notebook.forget(tab_index)
                
                # 切换到第一个二级Tab
                if self.tab_data[self.current_primary_tab]:
                    first_secondary = list(self.tab_data[self.current_primary_tab].keys())[0]
                    self.current_secondary_tab = first_secondary
                    self.load_current_tab_data()
                
                self.save_scripts()
                self.status_var.set(f"✅ 已删除二级分类: {tab_name}")
            except Exception as e:
                messagebox.showerror("错误", f"删除失败: {str(e)}")
                self.status_var.set(f"❌ 删除失败: {str(e)}")
    
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