"""
添加弹窗组件
包含添加话术分类、话术标题、话术内容等功能，支持权限控制
"""

import os
from tkinter import N
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel,
    QPushButton, QLineEdit, QTextEdit, QComboBox, QGroupBox,
    QButtonGroup, QRadioButton, QCheckBox, QMessageBox, QFrame, QWidget
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from typing import Dict, List, Optional, Any


class AddDialog(QDialog):
    """添加/编辑内容弹窗"""

    # 信号定义
    category_added_signal = Signal(str, str)  # 话术类型名, 话术分类名
    title_added_signal: Signal = Signal(str, str, str)  # 话术类型名, 话术分类名, 话术标题名
    content_added_signal = Signal(str, str, str, str)  # 话术类型名, 话术分类名, 话术标题名, 话术内容

    # 编辑信号定义
    category_edited_signal = Signal(str, str, str)  # 话术类型名, 旧分类名, 新分类名
    title_edited_signal = Signal(str, str, str, str)  # 话术类型名, 分类名, 旧标题名, 新标题名
    content_edited_signal = Signal(str, str, str, str, str)  # 话术类型名, 分类名, 标题名,旧话术内容, 新话术内容

    def __init__(self, scripts_data: Dict[str, Any], user_permissions: Dict[str, bool] = None, parent=None,
                 edit_mode=False):
        super().__init__(parent)
        self.scripts_data = scripts_data
        # self.user_permissions = user_permissions or {
        #     'add_secondary_tab': True,
        #     'add_category': True,
        #     'add_script': True
        # }

        # 编辑模式相关属性
        self.edit_mode = edit_mode
        self.edit_type = None  # 'primary', 'category', 'title'
        self.add_type = None  # 'primary', 'category', 'title'
        self.old_value = None
        self.primary_type = None
        self.category_name = None
        self.title_name = None
        self.script_content = None

        # 初始化标志
        self._user_triggered_change = False
        self._setting_defaults = False  # 新增：标记是否正在设置默认值
        self._defaults_set = False  # 新增：标记默认值是否已设置

        self.setup_ui()
        self.setup_connections()
        # self.update_ui_permissions()

    def setup_ui(self):
        """设置UI界面"""
        title = "新增"
        self.setWindowTitle(title)
        self.setModal(False)  # 设置为非模态对话框，允许操作主窗口
        self.setFixedSize(500, 600)

        # 设置窗口标志，使其保持在前台但不阻塞主窗口
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.WindowStaysOnTopHint)

        # 加载样式表
        self.load_stylesheet()

        # 主布局
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(10, 10, 10, 10)

        # 内容输入区域（包含添加类型选择）
        self.create_content_area(main_layout)

        # 按钮区域
        self.create_button_area(main_layout)

    def create_content_area(self, parent_layout):
        """创建内容输入区域"""
        # 直接创建表单布局，不使用QGroupBox容器
        form_widget = QWidget()
        parent_layout.addWidget(form_widget)

        form_layout = QFormLayout(form_widget)
        form_layout.setSpacing(10)
        form_layout.setContentsMargins(10, 10, 10, 10)
        # 添加类型选择（水平布局的单选按钮）
        type_widget = QWidget()
        type_layout = QHBoxLayout(type_widget)
        type_layout.setContentsMargins(0, 0, 0, 0)
        type_layout.setSpacing(20)

        # 单选按钮组
        self.type_button_group = QButtonGroup()

        # 添加话术分类单选项
        self.add_category_radio = QRadioButton("话术分类")
        self.add_category_radio.setChecked(True)
        self.type_button_group.addButton(self.add_category_radio, 0)
        type_layout.addWidget(self.add_category_radio)

        # 添加话术标题单选项
        self.add_title_radio: QRadioButton = QRadioButton("话术标题")
        self.type_button_group.addButton(self.add_title_radio, 1)
        type_layout.addWidget(self.add_title_radio)

        # 添加话术内容单选项
        self.add_content_radio = QRadioButton("话术内容")
        self.type_button_group.addButton(self.add_content_radio, 2)
        type_layout.addWidget(self.add_content_radio)

        # 添加弹性空间
        type_layout.addStretch()

        form_layout.addRow("添加类型:", type_widget)

        if self.edit_mode:
            self.hide_label_by_text('添加类型:')
            self.add_category_radio.setVisible(False)
            self.add_title_radio.setVisible(False)
            self.add_content_radio.setVisible(False)

        # 话术类型选择
        self.primary_combo = QComboBox()
        self.update_script_type_combo()
        form_layout.addRow("选择话术类型:", self.primary_combo)

        # 话术分类选择
        self.category_combo = QComboBox()
        form_layout.addRow("选择话术分类:", self.category_combo)

        # 话术标题选择
        self.title_combo = QComboBox()
        form_layout.addRow("选择话术标题:", self.title_combo)

        # 分类名称输入
        self.category_name_input = QLineEdit()
        self.category_name_input.setPlaceholderText("请输入分类名称...")
        form_layout.addRow("分类名称:", self.category_name_input)

        # 标题名称输入
        self.title_name_input = QLineEdit()
        self.title_name_input.setPlaceholderText("请输入标题名称...")
        form_layout.addRow("标题名称:", self.title_name_input)

        # 话术内容输入
        self.content_input = QTextEdit()
        self.content_input.setMinimumHeight(120)
        self.content_input.setPlaceholderText("请输入话术内容...")
        form_layout.addRow("话术内容:", self.content_input)

    def create_button_area(self, parent_layout):
        """创建按钮区域"""
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)

        # 添加弹性空间
        button_layout.addStretch()

        # 取消按钮
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.setObjectName("cancel_btn")
        self.cancel_btn.setMinimumSize(60, 20)
        button_layout.addWidget(self.cancel_btn)

        # 确认按钮
        confirm_text = "确认"
        self.confirm_btn = QPushButton(confirm_text)
        self.confirm_btn.setObjectName("confirm_btn")
        self.cancel_btn.setMinimumSize(60, 20)
        button_layout.addWidget(self.confirm_btn)

        parent_layout.addLayout(button_layout)

    def load_stylesheet(self):
        """加载样式表"""
        try:
            qss_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "styles", "add_dialog.qss")
            if os.path.exists(qss_path):
                with open(qss_path, 'r', encoding='utf-8') as f:
                    self.setStyleSheet(f.read())
        except Exception as e:
            print(f"加载添加弹窗样式表失败: {e}")

    def setup_connections(self):
        """设置信号连接"""
        # 类型选择变化
        self.type_button_group.buttonClicked.connect(self.on_type_changed)

        # 下拉框变化
        self.primary_combo.currentTextChanged.connect(self.update_category_combo)
        self.category_combo.currentTextChanged.connect(self.update_title_combo)

        # 按钮点击
        self.cancel_btn.clicked.connect(self.reject)
        self.confirm_btn.clicked.connect(self.on_confirm)

    # def update_ui_permissions(self):
    #     """根据权限更新UI"""
    #     # 根据用户权限禁用相应的选项
    #     if not self.user_permissions.get('add_secondary_tab', True):
    #         self.add_category_radio.setEnabled(False)
    #         self.add_category_radio.setToolTip("您没有添加话术分类的权限")

    #     if not self.user_permissions.get('add_category', True):
    #         self.add_title_radio.setEnabled(False)
    #         self.add_title_radio.setToolTip("您没有添加话术标题的权限")

    #     if not self.user_permissions.get('add_script', True):
    #         self.add_content_radio.setEnabled(False)
    #         self.add_content_radio.setToolTip("您没有添加话术内容的权限")

    #     # 如果没有任何权限，选择第一个可用的选项
    #     if not self.add_category_radio.isEnabled():
    #         if self.add_title_radio.isEnabled():
    #             self.add_title_radio.setChecked(True)
    #         elif self.add_content_radio.isEnabled():
    #             self.add_content_radio.setChecked(True)

    def on_type_changed(self, button):
        """添加类型变化"""
        # 只有在不是设置默认值时才标记为用户触发
        if not getattr(self, '_setting_defaults', False):
            self._user_triggered_change = True

        add_type = self.type_button_group.id(button)

        # 根据类型显示/隐藏相应的输入控件
        if add_type == 0:  # 添加话术分类
            # 隐藏不需要的控件
            self.category_combo.setVisible(False)
            self.title_combo.setVisible(False)
            self.title_name_input.setVisible(False)
            self.content_input.setVisible(False)

            # 隐藏对应的标签
            self.hide_label_by_text("选择话术分类:")
            self.hide_label_by_text("选择话术标题:")
            self.hide_label_by_text("标题名称:")
            self.hide_label_by_text("话术内容:")

            # 显示需要的控件
            self.primary_combo.setVisible(True)
            self.category_name_input.setVisible(True)

            # 显示对应的标签
            self.show_label_by_text("选择话术类型:")
            self.show_label_by_text("分类名称:")

        elif add_type == 1:  # 添加话术标题
            # 隐藏不需要的控件
            self.title_combo.setVisible(False)
            self.content_input.setVisible(False)
            self.category_name_input.setVisible(False)

            # 隐藏对应的标签
            self.hide_label_by_text("选择话术标题:")
            self.hide_label_by_text("分类名称:")
            self.hide_label_by_text("话术内容:")

            # 显示需要的控件
            self.primary_combo.setVisible(True)
            self.category_combo.setVisible(True)
            self.title_name_input.setVisible(True)

            # 显示对应的标签
            self.show_label_by_text("选择话术类型:")
            self.show_label_by_text("选择话术分类:")
            self.show_label_by_text("标题名称:")

            # 只在用户手动切换类型且不是设置默认值时才触发数据更新
            if (self._user_triggered_change and not getattr(self, '_setting_defaults', False)):
                self.update_category_combo(self.primary_combo.currentText())

        elif add_type == 2:  # 添加话术内容
            # 隐藏不需要的控件
            self.category_name_input.setVisible(False)
            self.title_name_input.setVisible(False)

            # 隐藏不需要的标签
            self.hide_label_by_text("分类名称:")
            self.hide_label_by_text("标题名称:")

            # 显示需要的控件
            self.primary_combo.setVisible(True)
            self.category_combo.setVisible(True)
            self.title_combo.setVisible(True)
            self.content_input.setVisible(True)

            # 显示需要的标签
            self.show_label_by_text("选择话术类型:")
            self.show_label_by_text("选择话术分类:")
            self.show_label_by_text("选择话术标题:")
            self.show_label_by_text("话术内容:")

            # 只在用户手动切换类型且不是设置默认值时才触发数据更新
            if (self._user_triggered_change and not getattr(self, '_setting_defaults', False)):
                self.update_category_combo(self.primary_combo.currentText())

    """更新话术类型下拉框 已梳理"""

    def update_script_type_combo(self):
        self.primary_combo.clear()
        if self.scripts_data:
            self.primary_combo.addItems(list(self.scripts_data.keys()))

    def update_category_combo(self, script_type_name: str):
        """更新话术分类下拉框"""
        self.category_combo.clear()
        if script_type_name and script_type_name in self.scripts_data:
            categorys = list(self.scripts_data[script_type_name].keys())
            self.category_combo.addItems(categorys)

    def update_title_combo(self, category_name: str, script_type_name: Optional[str] = None):
        if script_type_name is None:
            script_type_name = self.primary_combo.currentText()
        """更新话术标题下拉框"""
        self.title_combo.clear()
        if category_name in self.scripts_data[script_type_name]:
            titles = list(self.scripts_data[script_type_name][category_name].keys())
            self.title_combo.addItems(titles)

    def on_confirm(self):
        """确认添加或编辑"""
        if self.edit_mode:
            self.handle_edit_confirm()
        else:
            self.handle_add_confirm()

    def handle_add_confirm(self):
        """处理添加确认"""
        add_type = self.type_button_group.checkedId()
        script_type_name = self.primary_combo.currentText()
        name = None

        # 根据不同编辑类型，取相应组件的值
        if add_type == 0:
            name = self.category_name_input.text().strip()
        elif add_type == 1:
            name = self.title_name_input.text().strip()

        # 基本验证
        if not script_type_name:
            QMessageBox.warning(self, "警告", "请选择话术类型！")
            return

        # 只有在添加话术分类或话术标题时才需要名称
        if add_type in [0, 1] and not name:
            QMessageBox.warning(self, "警告", "请输入名称！")
            return

        try:
            if add_type == 0:
                # 添加话术分类
                # 检查是否已存在
                if name in self.scripts_data.get(script_type_name, {}):
                    QMessageBox.warning(self, "警告", f"话术分类 '{name}' 已存在！")
                    return

                self.category_added_signal.emit(script_type_name, name)

            elif add_type == 1:
                # 添加话术标题

                category_name = self.category_combo.currentText()

                if not category_name:
                    QMessageBox.warning(self, "警告", "请选择话术分类！")
                    return

                # 检查是否已存在
                if name in self.scripts_data[script_type_name][category_name]:
                    QMessageBox.warning(self, "警告", f"话术标题 '{name}' 已存在！")
                    return

                self.title_added_signal.emit(script_type_name, category_name, name)

            elif add_type == 2:
                # 添加话术内容

                category_name = self.category_combo.currentText()
                title_name = self.title_combo.currentText()
                content = self.content_input.toPlainText().strip()

                if not category_name:
                    QMessageBox.warning(self, "警告", "请选择话术分类！")
                    return

                if not title_name:
                    QMessageBox.warning(self, "警告", "请选择话术标题！")
                    return

                if not content:
                    QMessageBox.warning(self, "警告", "请输入话术内容！")
                    return

                # 检查是否已存在
                if content in self.scripts_data[script_type_name][category_name][title_name]:
                    QMessageBox.warning(self, "警告", f"话术内容 '{name}' 已存在！")
                    return

                self.content_added_signal.emit(script_type_name, category_name, title_name, content)

            # 成功添加后关闭对话框
            self.accept()

        except Exception as e:
            QMessageBox.critical(self, "错误", f"添加失败：{str(e)}")

    def handle_edit_confirm(self):
        """处理编辑确认"""
        new_value = None

        # 根据不同编辑类型，取相应组件的值
        if self.edit_type == 'category':
            new_value = self.category_name_input.text().strip()
        elif self.edit_type == 'title':
            new_value = self.title_name_input.text().strip()
        elif self.edit_type == 'script':
            new_value = self.content_input.toPlainText().strip()

        # 只有在添加话术分类或话术标题时才需要名称
        if self.edit_type in ['category', 'title'] and not new_value:
            QMessageBox.warning(self, "警告", "请输入名称！")
            return
        elif self.edit_type == 'script' and not new_value:
            QMessageBox.warning(self, "警告", "请输入话术内容！")
            return

        if new_value == self.old_value:
            QMessageBox.information(self, "提示", "内容没有变化！")
            return

        try:
            if self.edit_type == 'category':
                # 编辑话术标题
                if new_value in self.scripts_data.get(self.primary_type, {}):
                    QMessageBox.warning(self, "警告", f"话术分类 '{new_value}' 已存在！")
                    return
                self.category_edited_signal.emit(self.primary_type, self.old_value, new_value)

            elif self.edit_type == 'title':
                # 编辑话术标题
                if new_value in self.scripts_data[self.primary_type][self.category_name]:
                    QMessageBox.warning(self, "警告", f"话术标题 '{new_value}' 已存在！")
                    return
                self.title_edited_signal.emit(self.primary_type, self.category_name, self.old_value, new_value)

            elif self.edit_type == 'script':
                # 编辑话术内容
                if new_value in self.scripts_data[self.primary_type][self.category_name][self.title_name]:
                    QMessageBox.warning(self, "警告", f"话术 '{new_value}' 已存在！")
                    return
                self.content_edited_signal.emit(self.primary_type, self.category_name, self.title_name, self.old_value,
                                                new_value)

            # 成功编辑后关闭对话框
            self.accept()

        except Exception as e:
            QMessageBox.critical(self, "错误", f"编辑失败：{str(e)}")

    # def set_user_permissions(self, permissions: Dict[str, bool]):
    #     """设置用户权限"""
    #     self.user_permissions = permissions
    #     self.update_ui_permissions()

    def hide_label_by_text(self, label_text: str):
        """根据文本隐藏标签"""
        labels = self.findChildren(QLabel)
        for label in labels:
            if label.text() == label_text:
                label.setVisible(False)
                break

    def show_label_by_text(self, label_text: str):
        """根据文本显示标签"""
        labels = self.findChildren(QLabel)
        for label in labels:
            if label.text() == label_text:
                label.setVisible(True)
                break

    def set_default_type(self, default_type: str):
        """设置默认添加类型"""
        if default_type == 'category':  # 话术分类
            self.add_category_radio.setChecked(True)
        elif default_type == 'title':  # 话术标题
            self.add_title_radio.setChecked(True)
        elif default_type == 'script':  # 话术内容
            self.add_content_radio.setChecked(True)

        # 只更新UI显示，不触发数据重置
        self._update_ui_visibility_only()

    def _update_ui_visibility_only(self):
        """只更新UI显示状态，不触发数据重置"""
        add_type = self.type_button_group.checkedId()

        # 根据类型显示/隐藏相应的输入控件
        if add_type == 0:  # 添加话术分类
            # 隐藏不需要的控件
            self.category_combo.setVisible(False)
            self.title_combo.setVisible(False)
            self.content_input.setVisible(False)
            self.title_name_input.setVisible(False)

            # 隐藏对应的标签
            self.hide_label_by_text("选择话术分类:")
            self.hide_label_by_text("选择话术标题:")
            self.hide_label_by_text("话术内容:")
            self.hide_label_by_text("标题名称:")

        elif add_type == 1:  # 添加话术标题
            # 隐藏不需要的控件
            self.title_combo.setVisible(False)
            self.content_input.setVisible(False)
            self.category_name_input.setVisible(False)

            # 隐藏对应的标签
            self.hide_label_by_text("选择话术标题:")
            self.hide_label_by_text("话术内容:")
            self.hide_label_by_text("分类名称:")

        elif add_type == 2:  # 添加话术内容
            # 隐藏不需要的控件
            self.category_name_input.setVisible(False)
            self.title_name_input.setVisible(False)

            # 隐藏不需要的标签
            self.hide_label_by_text("分类名称:")
            self.hide_label_by_text("标题名称:")

    def showEvent(self, event):
        """显示事件"""
        super().showEvent(event)

        # 只有在没有设置默认值的情况下才更新下拉框数据
        if not getattr(self, '_defaults_set', False):
            print("showEvent: 更新下拉框数据")
            self.update_script_type_combo()
        else:
            print("showEvent: 跳过下拉框数据更新，因为已设置默认值")

    def set_add_mode(self, add_type: str, tab_type_id: int = 0, level_one_category: int = 0,
                     level_two_category: int = 0):
        """设置新增模式"""

        self.add_type = add_type
        self.primary_type = primary_type
        self.category_name = category_name
        self.title_name = title_name
        self.script_content = script_content

        # 设置添加类型('category', 'title', 'script')
        self.set_default_type(add_type)
        if add_type != 'script':
            self.hide_label_by_text('添加类型:')
            self.add_category_radio.setVisible(False)
            self.add_title_radio.setVisible(False)
            self.add_content_radio.setVisible(False)

        # 根据编辑类型设置UI    
        if add_type == 'category':
            # 添加话术分类
            # 更新窗口标题和按钮文本
            self.setWindowTitle("新增话术分类")
            self.set_default_values(primary_type)
        elif add_type == 'title':
            # 新增话术标题
            # 更新窗口标题和按钮文本
            self.setWindowTitle("新增话术标题")
            self.set_default_values(primary_type, category_name)

        elif add_type == 'script':
            # 新增话术内容
            # 更新窗口标题和按钮文本
            self.setWindowTitle("新增话术内容")
            self.set_default_values(primary_type, category_name, title_name)

    def set_edit_mode(self, edit_type: str, old_value: str, tab_type_id: int = 0, level_one_category: int = 0,
                      level_two_category: int = 0, script_id: int = 0):
        """设置编辑模式
        
        Args:
            edit_type: 编辑类型 ('category', 'title', 'script')
            old_value: 旧值
            primary_type: 话术类型名
            category_name: 话术分类名
            title_name: 话术标题名
        """
        self.edit_mode = True
        self.edit_type = edit_type
        self.old_value = old_value
        self.primary_type = primary_type
        self.category_name = category_name
        self.title_name = title_name

        # 设置添加类型('category', 'title', 'script')
        self.set_default_type(edit_type)

        # 根据编辑类型设置UI    
        if edit_type == 'category':
            # 编辑话术分类
            # 更新窗口标题
            self.setWindowTitle("修改话术分类名称")
            self.set_default_values(primary_type, old_value)
            # self.primary_combo.setEnabled(True)

        elif edit_type == 'title':
            # 编辑话术标题
            # 更新窗口标题
            self.setWindowTitle("修改话术标题名称")
            self.set_default_values(primary_type, category_name, old_value)
            # self.primary_combo.setEnabled(True)
            # self.category_combo.setEnabled(True)

        elif edit_type == 'script':
            # 编辑话术内容
            # 更新窗口标题
            self.setWindowTitle("修改话术内容")
            self.set_default_values(primary_type, category_name, title_name, old_value)
            # self.primary_combo.setEnabled(True)
            # self.category_combo.setEnabled(True)
            # self.title_combo.setEnabled(True)

    def set_default_values(self, primary_type: str = None, category_name: str = None, title_name: str = None,
                           script_content: str = None):
        """设置默认值"""
        try:
            # 标记正在设置默认值
            self._setting_defaults = True

            # 首先确保下拉框数据已加载
            self.update_script_type_combo()

            # 设置话术类型默认值
            if primary_type and primary_type in self.scripts_data:
                index = self.primary_combo.findText(primary_type)
                if index >= 0:

                    if self.edit_mode:
                        self.category_name_input.setText(category_name)
                    else:
                        self.primary_combo.setCurrentIndex(index)
                        # 手动触发信号更新下级下拉框
                        self.update_category_combo(primary_type)

                    # 设置分类默认值
                    if category_name and category_name in self.scripts_data[primary_type]:
                        category_index = self.category_combo.findText(category_name)
                        if category_index >= 0:
                            if self.edit_mode:
                                self.title_name_input.setText(title_name)
                            else:
                                self.category_combo.setCurrentIndex(category_index)
                                # 手动触发信号更新下级下拉框
                                self.update_title_combo(category_name, primary_type)

                            # 设置标题默认值
                            if title_name and title_name in self.scripts_data[primary_type][category_name]:
                                title_index = self.title_combo.findText(title_name)
                                if title_index > 0:
                                    if self.edit_mode:
                                        self.content_input.setPlainText(script_content)
                                    else:
                                        self.title_combo.setCurrentIndex(title_index)

            # 标记默认值设置完成
            self._setting_defaults = False
            self._defaults_set = True

        except Exception as e:
            print(f"❌ 设置默认值失败: {e}")
            import traceback
            traceback.print_exc()
            self._setting_defaults = False
