"""
PySide6版本的登录对话框组件
"""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QPushButton, QMessageBox, QFrame
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from typing import Callable, Optional, Tuple


class LoginDialog(QDialog):
    """登录对话框组件"""
    
    def __init__(self, parent=None, login_callback: Callable[[str, str], bool] = None):
        """
        初始化登录对话框
        
        Args:
            parent: 父窗口
            login_callback: 登录回调函数，接收用户名和密码，返回登录是否成功
        """
        super().__init__(parent)
        self.login_callback = login_callback
        self.result = None
        
        self.setup_ui()
        
    def setup_ui(self):
        """设置界面"""
        self.setWindowTitle("用户登录")
        self.setFixedSize(350, 220)
        self.setModal(True)
        
        # 主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(25, 25, 25, 25)
        main_layout.setSpacing(15)
        
        # 标题
        title_label = QLabel("用户登录")
        title_label.setAlignment(Qt.AlignCenter)
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title_label.setFont(title_font)
        main_layout.addWidget(title_label)
        
        # 用户名
        username_label = QLabel("用户名:")
        username_label.setFont(QFont("Microsoft YaHei UI", 10))
        main_layout.addWidget(username_label)
        
        self.username_edit = QLineEdit()
        self.username_edit.setFont(QFont("Microsoft YaHei UI", 10))
        self.username_edit.setMinimumHeight(32)
        self.username_edit.setPlaceholderText("请输入用户名")
        main_layout.addWidget(self.username_edit)
        
        # 密码
        password_label = QLabel("密码:")
        password_label.setFont(QFont("Microsoft YaHei UI", 10))
        main_layout.addWidget(password_label)
        
        self.password_edit = QLineEdit()
        self.password_edit.setFont(QFont("Microsoft YaHei UI", 10))
        self.password_edit.setMinimumHeight(32)
        self.password_edit.setEchoMode(QLineEdit.Password)
        self.password_edit.setPlaceholderText("请输入密码")
        main_layout.addWidget(self.password_edit)
        
        # 按钮
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.setMinimumSize(80, 32)
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)
        
        self.login_btn = QPushButton("登录")
        self.login_btn.setMinimumSize(80, 32)
        self.login_btn.setObjectName("primary_button")
        self.login_btn.clicked.connect(self.handle_login)
        button_layout.addWidget(self.login_btn)
        
        main_layout.addLayout(button_layout)
        
        # 设置默认焦点
        self.username_edit.setFocus()
        
        # 绑定回车键
        self.username_edit.returnPressed.connect(self.password_edit.setFocus)
        self.password_edit.returnPressed.connect(self.handle_login)
    
    def handle_login(self):
        """处理登录"""
        username = self.username_edit.text().strip()
        password = self.password_edit.text().strip()
        
        if not username or not password:
            QMessageBox.warning(self, "警告", "请输入用户名和密码！")
            return
        
        try:
            if self.login_callback:
                success = self.login_callback(username, password)
                if success:
                    self.result = (username, password)
                    self.accept()
            else:
                # 如果没有回调函数，直接返回结果
                self.result = (username, password)
                self.accept()
        except Exception as e:
            QMessageBox.critical(self, "登录失败", f"登录时发生错误: {str(e)}")
    
    def get_result(self) -> Optional[Tuple[str, str]]:
        """获取登录结果"""
        return self.result


def show_login_dialog(parent=None, login_callback: Callable[[str, str], bool] = None) -> Optional[Tuple[str, str]]:
    """
    显示登录对话框的便捷函数
    
    Args:
        parent: 父窗口
        login_callback: 登录回调函数
        
    Returns:
        如果登录成功返回 (username, password)，否则返回 None
    """
    dialog = LoginDialog(parent, login_callback)
    if dialog.exec() == QDialog.Accepted:
        return dialog.get_result()
    return None