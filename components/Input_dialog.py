"""
PySide6版本的输入对话框组件
"""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QTextEdit, QPushButton, QFrame
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from typing import Optional


class ChineseInputDialog(QDialog):
    """中文输入对话框"""
    
    def __init__(self, parent=None, title="输入", prompt="请输入内容:", 
                 initial_value="", multiline=False):
        """
        初始化输入对话框
        
        Args:
            parent: 父窗口
            title: 对话框标题
            prompt: 提示文字
            initial_value: 初始值
            multiline: 是否多行输入
        """
        super().__init__(parent)
        self.result = None
        self.multiline = multiline
        
        self.setup_ui(title, prompt, initial_value)
        
    def setup_ui(self, title: str, prompt: str, initial_value: str):
        """设置界面"""
        self.setWindowTitle(title)
        self.setModal(True)
        
        if self.multiline:
            self.setFixedSize(450, 300)
        else:
            self.setFixedSize(350, 150)
        
        # 主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)
        
        # 提示文字
        prompt_label = QLabel(prompt)
        prompt_label.setFont(QFont("Microsoft YaHei UI", 10))
        main_layout.addWidget(prompt_label)
        
        if self.multiline:
            # 多行输入框
            self.text_edit = QTextEdit()
            self.text_edit.setFont(QFont("Microsoft YaHei UI", 10))
            self.text_edit.setMinimumHeight(150)
            if initial_value:
                self.text_edit.setPlainText(initial_value)
                self.text_edit.selectAll()
            self.text_edit.setFocus()
            main_layout.addWidget(self.text_edit)
        else:
            # 单行输入框
            self.line_edit = QLineEdit()
            self.line_edit.setFont(QFont("Microsoft YaHei UI", 10))
            self.line_edit.setMinimumHeight(32)
            if initial_value:
                self.line_edit.setText(initial_value)
                self.line_edit.selectAll()
            self.line_edit.setFocus()
            main_layout.addWidget(self.line_edit)
        
        # 按钮
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        cancel_btn = QPushButton("取消")
        cancel_btn.setMinimumSize(80, 32)
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        ok_btn = QPushButton("确定")
        ok_btn.setMinimumSize(80, 32)
        ok_btn.setObjectName("primary_button")
        ok_btn.clicked.connect(self.handle_ok)
        button_layout.addWidget(ok_btn)
        
        main_layout.addLayout(button_layout)
        
        # 绑定快捷键
        if not self.multiline:
            self.line_edit.returnPressed.connect(self.handle_ok)
    
    def handle_ok(self):
        """处理确定按钮"""
        if self.multiline:
            self.result = self.text_edit.toPlainText().strip()
        else:
            self.result = self.line_edit.text().strip()
        
        self.accept()
    
    def get_result(self) -> Optional[str]:
        """获取输入结果"""
        return self.result
    
    def show(self) -> Optional[str]:
        """显示对话框并返回结果"""
        if self.exec() == QDialog.Accepted:
            return self.get_result()
        return None


def ask_string(parent=None, title="输入", prompt="请输入内容:", 
               initial_value="", multiline=False) -> Optional[str]:
    """
    显示输入对话框的便捷函数
    
    Args:
        parent: 父窗口
        title: 对话框标题
        prompt: 提示文字
        initial_value: 初始值
        multiline: 是否多行输入
        
    Returns:
        用户输入的字符串，如果取消则返回None
    """
    dialog = ChineseInputDialog(parent, title, prompt, initial_value, multiline)
    return dialog.show()