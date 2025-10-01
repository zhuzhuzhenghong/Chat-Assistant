import tkinter as tk
from tkinter import ttk, messagebox
from typing import Callable, Optional, Tuple


class LoginDialog:
    """登录对话框组件"""
    
    def __init__(self, parent: tk.Tk, login_callback: Callable[[str, str], bool]):
        """
        初始化登录对话框
        
        Args:
            parent: 父窗口
            login_callback: 登录回调函数，接收用户名和密码，返回登录是否成功
        """
        self.parent = parent
        self.login_callback = login_callback
        self.dialog = None
        self.username_var = None
        self.password_var = None
        self.result = None
        
    def show(self) -> Optional[Tuple[str, str]]:
        """
        显示登录对话框
        
        Returns:
            如果登录成功返回 (username, password)，否则返回 None
        """
        # 创建登录对话框
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title("用户登录")
        self.dialog.geometry("350x220")
        self.dialog.resizable(False, False)
        self.dialog.transient(self.parent)
        self.dialog.grab_set()
        
        # 居中显示
        self.dialog.geometry("+%d+%d" % (
            self.parent.winfo_rootx() + 50,
            self.parent.winfo_rooty() + 50
        ))
        
        # 创建界面
        self._create_widgets()
        
        # 等待对话框关闭
        self.dialog.wait_window()
        
        return self.result
    
    def _create_widgets(self):
        """创建对话框界面"""
        # 主框架
        main_frame = ttk.Frame(self.dialog, padding="25")
        main_frame.pack(fill=tk.BOTH, expand=True)
        main_frame.columnconfigure(1, weight=1)
        
        # 用户名
        ttk.Label(main_frame, text="用户名:", font=("微软雅黑", 10)).grid(
            row=0, column=0, sticky="w", pady=(0, 8)
        )
        self.username_var = tk.StringVar()
        username_entry = ttk.Entry(
            main_frame, 
            textvariable=self.username_var, 
            font=("微软雅黑", 10), 
            width=25
        )
        username_entry.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 15))
        username_entry.focus()
        
        # 密码
        ttk.Label(main_frame, text="密码:", font=("微软雅黑", 10)).grid(
            row=2, column=0, sticky="w", pady=(0, 8)
        )
        self.password_var = tk.StringVar()
        password_entry = ttk.Entry(
            main_frame, 
            textvariable=self.password_var, 
            show="*", 
            font=("微软雅黑", 10), 
            width=25
        )
        password_entry.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(0, 25))
        
        # 按钮框架
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=4, column=0, columnspan=2, sticky="ew")
        button_frame.columnconfigure(0, weight=1)
        button_frame.columnconfigure(1, weight=1)
        
        # 取消按钮
        cancel_btn = ttk.Button(
            button_frame, 
            text="取消", 
            command=self._on_cancel, 
            width=10
        )
        cancel_btn.grid(row=0, column=0, padx=(0, 10), sticky="e")
        
        # 登录按钮
        login_btn = ttk.Button(
            button_frame, 
            text="登录", 
            command=self._on_login, 
            width=10
        )
        login_btn.grid(row=0, column=1, sticky="e")
        
        # 绑定键盘事件
        if self.dialog:
            self.dialog.bind('<Return>', lambda e: self._on_login())
            self.dialog.bind('<Escape>', lambda e: self._on_cancel())
    
    def _on_login(self):
        """处理登录按钮点击"""
        if not self.username_var or not self.password_var:
            return
            
        username = self.username_var.get().strip()
        password = self.password_var.get().strip()
        
        if not username or not password:
            messagebox.showwarning("警告", "请输入用户名和密码！")
            return
        
        try:
            # 调用登录回调函数
            success = self.login_callback(username, password)
            if success:
                self.result = (username, password)
                if self.dialog:
                    self.dialog.destroy()
            # 如果登录失败，回调函数应该已经显示了错误消息
        except Exception as e:
            messagebox.showerror("登录失败", f"登录时发生错误: {str(e)}")
    
    def _on_cancel(self):
        """处理取消按钮点击"""
        self.result = None
        if self.dialog:
            self.dialog.destroy()


def show_login_dialog(parent: tk.Tk, login_callback: Callable[[str, str], bool]) -> Optional[Tuple[str, str]]:
    """
    显示登录对话框的便捷函数
    
    Args:
        parent: 父窗口
        login_callback: 登录回调函数
        
    Returns:
        如果登录成功返回 (username, password)，否则返回 None
    """
    dialog = LoginDialog(parent, login_callback)
    return dialog.show()