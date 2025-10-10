"""
添加弹窗组件
包含添加一级分类、二级分类、话术内容等功能，支持权限控制
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
    level_one_category_added_signal = Signal(str, str)  # 话术类型名, 一级分类名
    level_two_category_added_signal: Signal = Signal(str, str, str)  # 话术类型名, 一级分类名, 二级分类名
    content_added_signal = Signal(str, str, str, str)  # 话术类型名, 一级分类名, 二级分类名, 话术内容

    # 编辑信号定义
    level_one_category_edited_signal = Signal(str, str, str)  # 话术类型名, 旧分类名, 新分类名
    level_two_category_edited_signal = Signal(str, str, str, str)  # 话术类型名, 分类名, 旧二级分类名, 新二级分类名
    content_edited_signal = Signal(str, str, str, str, str)  # 话术类型名, 分类名, 二级分类名,旧话术内容, 新话术内容

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
        self.edit_type = None  # 'primary', 'level_one_category', 'level_two_category'
        self.add_type = None  # 'primary', 'level_one_category', 'level_two_category'
        self.old_value = None
        self.tab_type_id = 0
        self.tab_type_name = None
        self.level_one_category_id = 0
        self.level_one_category_name = None
        self.level_two_category_id = 0
        self.level_two_category_name = None
        self.script_id = 0
        self.script_content = None

        # Tab数据结构
        self.current_type_tab_name = ""
        self.current_type_tab_id = 0
        self.current_level_one_category_name = ""
        self.current_level_one_category_id = 0
        self.current_level_two_category_name = ""
        self.current_level_two_category_id = 0

        # 当前选中Tab数据
        self.current_type_tab_data = {}
        self.current_level_one_category_data = {}
        self.current_level_two_category_data = []

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

        # 添加一级分类单选项
        self.add_level_one_category_radio = QRadioButton("一级分类")
        self.add_level_one_category_radio.setChecked(True)
        self.type_button_group.addButton(self.add_level_one_category_radio, 0)
        type_layout.addWidget(self.add_level_one_category_radio)

        # 添加二级分类单选项
        self.add_level_two_category_radio: QRadioButton = QRadioButton("二级分类")
        self.type_button_group.addButton(self.add_level_two_category_radio, 1)
        type_layout.addWidget(self.add_level_two_category_radio)

        # 添加话术内容单选项
        self.add_content_radio = QRadioButton("话术内容")
        self.type_button_group.addButton(self.add_content_radio, 2)
        type_layout.addWidget(self.add_content_radio)

        # 添加弹性空间
        type_layout.addStretch()

        form_layout.addRow("添加类型:", type_widget)

        if self.edit_mode:
            self.hide_label_by_text('添加类型:')
            self.add_level_one_category_radio.setVisible(False)
            self.add_level_two_category_radio.setVisible(False)
            self.add_content_radio.setVisible(False)

        # 话术类型选择
        self.script_type_combo = QComboBox()
        self.update_script_type_combo()
        form_layout.addRow("选择话术类型:", self.script_type_combo)

        # 话术一级分类选择
        self.level_one_category_combo = QComboBox()
        form_layout.addRow("选择一级分类:", self.level_one_category_combo)

        # 话术二级分类选择
        self.level_two_category_combo = QComboBox()
        form_layout.addRow("选择二级分类:", self.level_two_category_combo)

        # 分类名称输入
        self.level_one_category_input = QLineEdit()
        self.level_one_category_input.setPlaceholderText("请输入一级分类名称...")
        form_layout.addRow("一级分类名称:", self.level_one_category_input)

        # 二级分类名称输入
        self.level_two_category_input = QLineEdit()
        self.level_two_category_input.setPlaceholderText("请输入二级分类名称...")
        form_layout.addRow("二级分类名称:", self.level_two_category_input)

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
        self.script_type_combo.currentTextChanged.connect(self.update_level_one_category_combo)
        self.level_one_category_combo.currentTextChanged.connect(self.update_level_two_category_combo)

        # 按钮点击
        self.cancel_btn.clicked.connect(self.reject)
        self.confirm_btn.clicked.connect(self.on_confirm)

    # def update_ui_permissions(self):
    #     """根据权限更新UI"""
    #     # 根据用户权限禁用相应的选项
    #     if not self.user_permissions.get('add_secondary_tab', True):
    #         self.add_level_one_category_radio.setEnabled(False)
    #         self.add_level_one_category_radio.setToolTip("您没有添加一级分类的权限")

    #     if not self.user_permissions.get('add_category', True):
    #         self.add_level_two_category_radio.setEnabled(False)
    #         self.add_level_two_category_radio.setToolTip("您没有添加二级分类的权限")

    #     if not self.user_permissions.get('add_script', True):
    #         self.add_content_radio.setEnabled(False)
    #         self.add_content_radio.setToolTip("您没有添加话术内容的权限")

    #     # 如果没有任何权限，选择第一个可用的选项
    #     if not self.add_level_one_category_radio.isEnabled():
    #         if self.add_level_two_category_radio.isEnabled():
    #             self.add_level_two_category_radio.setChecked(True)
    #         elif self.add_content_radio.isEnabled():
    #             self.add_content_radio.setChecked(True)

    def on_type_changed(self, button):
        """添加类型变化"""
        # 只有在不是设置默认值时才标记为用户触发
        if not getattr(self, '_setting_defaults', False):
            self._user_triggered_change = True

        add_type = self.type_button_group.id(button)

        # 根据类型显示/隐藏相应的输入控件
        if add_type == 0:  # 添加一级分类
            # 隐藏不需要的控件
            self.level_one_category_combo.setVisible(False)
            self.level_two_category_combo.setVisible(False)
            self.level_two_category_input.setVisible(False)
            self.content_input.setVisible(False)

            # 隐藏对应的标签
            self.hide_label_by_text("选择一级分类:")
            self.hide_label_by_text("选择二级分类:")
            self.hide_label_by_text("二级分类名称:")
            self.hide_label_by_text("话术内容:")

            # 显示需要的控件
            self.script_type_combo.setVisible(True)
            self.level_one_category_input.setVisible(True)

            # 显示对应的标签
            self.show_label_by_text("选择话术类型:")
            self.show_label_by_text("一级分类名称:")

        elif add_type == 1:  # 添加二级分类
            # 隐藏不需要的控件
            self.level_two_category_combo.setVisible(False)
            self.content_input.setVisible(False)
            self.level_one_category_input.setVisible(False)

            # 隐藏对应的标签
            self.hide_label_by_text("选择二级分类:")
            self.hide_label_by_text("一级分类名称:")
            self.hide_label_by_text("话术内容:")

            # 显示需要的控件
            self.script_type_combo.setVisible(True)
            self.level_one_category_combo.setVisible(True)
            self.level_two_category_input.setVisible(True)

            # 显示对应的标签
            self.show_label_by_text("选择话术类型:")
            self.show_label_by_text("选择一级分类:")
            self.show_label_by_text("二级分类名称:")

            # 只在用户手动切换类型且不是设置默认值时才触发数据更新
            if (self._user_triggered_change and not getattr(self, '_setting_defaults', False)):
                self.update_level_one_category_combo(self.script_type_combo.currentText())

        elif add_type == 2:  # 添加话术内容
            # 隐藏不需要的控件
            self.level_one_category_input.setVisible(False)
            self.level_two_category_input.setVisible(False)

            # 隐藏不需要的标签
            self.hide_label_by_text("一级分类名称:")
            self.hide_label_by_text("二级分类名称:")

            # 显示需要的控件
            self.script_type_combo.setVisible(True)
            self.level_one_category_combo.setVisible(True)
            self.level_two_category_combo.setVisible(True)
            self.content_input.setVisible(True)

            # 显示需要的标签
            self.show_label_by_text("选择话术类型:")
            self.show_label_by_text("选择一级分类:")
            self.show_label_by_text("选择二级分类:")
            self.show_label_by_text("话术内容:")

            # 只在用户手动切换类型且不是设置默认值时才触发数据更新
            if (self._user_triggered_change and not getattr(self, '_setting_defaults', False)):
                self.update_level_one_category_combo(self.script_type_combo.currentText())

    """更新话术类型下拉框 已梳理"""

    def update_script_type_combo(self):
        self.script_type_combo.clear()
        if self.scripts_data:
            for tab_type_data in self.scripts_data:
                self.script_type_combo.addItem(tab_type_data['name'], tab_type_data['type_id'])

    def update_level_one_category_combo(self, tab_type_name: str):
        """更新一级分类下拉框"""
        self.level_one_category_combo.clear()

        print('tab_type_name', tab_type_name)
        tab_type_id = self.script_type_combo.currentData()
        result = list(filter(lambda item: item['type_id'] == tab_type_id,
                             self.scripts_data))
        print('result', result)
        if len(result) > 0:
            self.current_type_tab_id = result[0]['type_id']
            self.current_type_tab_data = result[0]
            for level_one_category_data in result[0]['data']:
                self.level_one_category_combo.addItem(level_one_category_data['name'],
                                                      level_one_category_data['level_one_category_id'])

    def update_level_two_category_combo(self, level_one_category_name: int, tab_type_id: Optional[int] = 0):
        self.level_two_category_combo.clear()

        if tab_type_id == 0:
            script_type_name = self.script_type_combo.currentText()
        """更新二级分类下拉框"""
        level_one_category_id = self.level_one_category_combo.currentData()

        result = list(filter(lambda item: item['level_one_category_id'] == level_one_category_id,
                             self.current_type_tab_data['data']))
        if len(result) > 0:
            self.current_level_one_category_id = result[0]['level_one_category_id']
            self.current_level_one_category_data = result[0]
            for level_two_category_data in result[0]['data']:
                self.level_two_category_combo.addItem(level_two_category_data['name'],
                                                      level_two_category_data['level_two_category_id'])

    def on_confirm(self):
        """确认添加或编辑"""
        if self.edit_mode:
            self.handle_edit_confirm()
        else:
            self.handle_add_confirm()

    def handle_add_confirm(self):
        """处理添加确认"""
        add_type = self.type_button_group.checkedId()
        script_type_name = self.script_type_combo.currentText()
        name = None

        # 根据不同编辑类型，取相应组件的值
        if add_type == 0:
            name = self.level_one_category_input.text().strip()
        elif add_type == 1:
            name = self.level_two_category_input.text().strip()

        # 基本验证
        if not script_type_name:
            QMessageBox.warning(self, "警告", "请选择话术类型！")
            return

        # 只有在添加一级分类或二级分类时才需要名称
        if add_type in [0, 1] and not name:
            QMessageBox.warning(self, "警告", "请输入名称！")
            return

        try:
            if add_type == 0:
                # 添加一级分类
                # 检查是否已存在
                if name in self.scripts_data.get(script_type_name, {}):
                    QMessageBox.warning(self, "警告", f"一级分类 '{name}' 已存在！")
                    return

                self.level_one_category_added_signal.emit(script_type_name, name)

            elif add_type == 1:
                # 添加二级分类

                level_one_category_id = self.level_one_category_combo.currentText()

                if not level_one_category_id:
                    QMessageBox.warning(self, "警告", "请选择一级分类！")
                    return

                # 检查是否已存在
                if name in self.scripts_data[script_type_name][level_one_category_id]:
                    QMessageBox.warning(self, "警告", f"二级分类 '{name}' 已存在！")
                    return

                self.title_added_signal.emit(script_type_name, level_one_category_id, name)

            elif add_type == 2:
                # 添加话术内容

                level_one_category_id = self.level_one_category_combo.currentText()
                level_two_category_id = self.level_two_category_combo.currentText()
                content = self.content_input.toPlainText().strip()

                if not level_one_category_id:
                    QMessageBox.warning(self, "警告", "请选择一级分类！")
                    return

                if not level_two_category_id:
                    QMessageBox.warning(self, "警告", "请选择二级分类！")
                    return

                if not content:
                    QMessageBox.warning(self, "警告", "请输入话术内容！")
                    return

                # 检查是否已存在
                if content in self.scripts_data[script_type_name][level_one_category_id][level_two_category_id]:
                    QMessageBox.warning(self, "警告", f"话术内容 '{name}' 已存在！")
                    return

                self.content_added_signal.emit(script_type_name, level_one_category_id, level_two_category_id, content)

            # 成功添加后关闭对话框
            self.accept()

        except Exception as e:
            QMessageBox.critical(self, "错误", f"添加失败：{str(e)}")

    def handle_edit_confirm(self):
        """处理编辑确认"""
        new_value = None

        # 根据不同编辑类型，取相应组件的值
        if self.edit_type == 'level_one_category':
            new_value = self.level_one_category_input.text().strip()
        elif self.edit_type == 'level_two_category':
            new_value = self.level_two_category_input.text().strip()
        elif self.edit_type == 'script':
            new_value = self.content_input.toPlainText().strip()

        # 只有在添加一级分类或二级分类时才需要名称
        if self.edit_type in ['level_one_category', 'level_two_category'] and not new_value:
            QMessageBox.warning(self, "警告", "请输入名称！")
            return
        elif self.edit_type == 'script' and not new_value:
            QMessageBox.warning(self, "警告", "请输入话术内容！")
            return

        if new_value == self.old_value:
            QMessageBox.information(self, "提示", "内容没有变化！")
            return

        try:
            if self.edit_type == 'level_one_category':
                # 编辑二级分类
                if new_value in self.scripts_data.get(self.tab_type_id, {}):
                    QMessageBox.warning(self, "警告", f"一级分类 '{new_value}' 已存在！")
                    return
                self.category_edited_signal.emit(self.tab_type_id, self.old_value, new_value)

            elif self.edit_type == 'level_two_category':
                # 编辑二级分类
                if new_value in self.scripts_data[self.tab_type_id][self.level_one_category_id]:
                    QMessageBox.warning(self, "警告", f"二级分类 '{new_value}' 已存在！")
                    return
                self.title_edited_signal.emit(self.tab_type_id, self.level_one_category_id, self.old_value, new_value)

            elif self.edit_type == 'script':
                # 编辑话术内容
                if new_value in self.scripts_data[self.tab_type_id][self.level_one_category_id][
                    self.level_two_category_id]:
                    QMessageBox.warning(self, "警告", f"话术 '{new_value}' 已存在！")
                    return
                self.content_edited_signal.emit(self.tab_type_id, self.level_one_category_id,
                                                self.level_two_category_id, self.old_value,
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
        if default_type == 'level_one_category':  # 一级分类
            self.add_level_one_category_radio.setChecked(True)
        elif default_type == 'level_two_category':  # 二级分类
            self.add_level_two_category_radio.setChecked(True)
        elif default_type == 'script':  # 话术内容
            self.add_content_radio.setChecked(True)

        # 只更新UI显示，不触发数据重置
        self._update_ui_visibility_only()

    def _update_ui_visibility_only(self):
        """只更新UI显示状态，不触发数据重置"""
        add_type = self.type_button_group.checkedId()

        # 根据类型显示/隐藏相应的输入控件
        if add_type == 0:  # 添加一级分类
            # 隐藏不需要的控件
            self.level_one_category_combo.setVisible(False)
            self.level_two_category_combo.setVisible(False)
            self.content_input.setVisible(False)
            self.level_two_category_input.setVisible(False)

            # 隐藏对应的标签
            self.hide_label_by_text("选择一级分类:")
            self.hide_label_by_text("选择二级分类:")
            self.hide_label_by_text("话术内容:")
            self.hide_label_by_text("二级分类名称:")

        elif add_type == 1:  # 添加二级分类
            # 隐藏不需要的控件
            self.level_two_category_combo.setVisible(False)
            self.content_input.setVisible(False)
            self.level_one_category_input.setVisible(False)

            # 隐藏对应的标签
            self.hide_label_by_text("选择二级分类:")
            self.hide_label_by_text("话术内容:")
            self.hide_label_by_text("一级分类名称:")

        elif add_type == 2:  # 添加话术内容
            # 隐藏不需要的控件
            self.level_one_category_input.setVisible(False)
            self.level_two_category_input.setVisible(False)

            # 隐藏不需要的标签
            self.hide_label_by_text("一级分类名称:")
            self.hide_label_by_text("二级分类名称:")

    def showEvent(self, event):
        """显示事件"""
        super().showEvent(event)

        # 只有在没有设置默认值的情况下才更新下拉框数据
        if not getattr(self, '_defaults_set', False):
            print("showEvent: 更新下拉框数据")
            self.update_script_type_combo()
        else:
            print("showEvent: 跳过下拉框数据更新，因为已设置默认值")

    def set_add_mode(self, add_type: str, tab_type_id: int = 0, level_one_category_id: int = 0,
                     level_two_category_id: int = 0):
        """设置新增模式"""

        self.add_type = add_type
        self.tab_type_id = tab_type_id
        self.level_one_category_id = level_one_category_id
        self.level_two_category_id = level_two_category_id

        # 设置添加类型('level_one_category', 'level_two_category', 'script')
        self.set_default_type(add_type)
        if add_type != 'script':
            self.hide_label_by_text('添加类型:')
            self.add_level_one_category_radio.setVisible(False)
            self.add_level_two_category_radio.setVisible(False)
            self.add_content_radio.setVisible(False)

        # 根据编辑类型设置UI
        if add_type == 'level_one_category':
            # 添加一级分类
            # 更新窗口标题和按钮文本
            self.setWindowTitle("新增一级分类")
            self.set_default_values(tab_type_id)
        elif add_type == 'level_two_category':
            # 新增二级分类
            # 更新窗口标题和按钮文本
            self.setWindowTitle("新增二级分类")
            self.set_default_values(tab_type_id, level_one_category_id)

        elif add_type == 'script':
            # 新增话术内容
            # 更新窗口标题和按钮文本
            self.setWindowTitle("新增话术内容")
            self.set_default_values(tab_type_id, level_one_category_id, level_two_category_id)

    def set_edit_mode(self, edit_type: str, old_value: str, tab_type_id: int = 0, level_one_category_id: int = 0,
                      level_two_category_id: int = 0, script_id: int = 0):
        """设置编辑模式

        Args:
            edit_type: 编辑类型 ('level_one_category', 'level_two_category', 'script')
            old_value: 旧值
            tab_type_id: 话术类型ID
            level_one_category_id: 一级分类名
            level_two_category_id: 二级分类名
        """
        self.edit_mode = True
        self.edit_type = edit_type
        self.old_value = old_value
        self.tab_type_id = tab_type_id
        self.level_one_category_id = level_one_category_id
        self.level_two_category_id = level_two_category_id
        self.script_id = script_id

        # 设置添加类型('level_one_category', 'level_two_category', 'script')
        self.set_default_type(edit_type)

        # 根据编辑类型设置UI
        if edit_type == 'level_one_category':
            # 编辑一级分类
            # 更新窗口标题
            self.setWindowTitle("修改一级分类名称")
            self.set_default_values(tab_type_id, level_one_category_id, old_value)
            # self.script_type_combo.setEnabled(True)

        elif edit_type == 'level_two_category':
            # 编辑二级分类
            # 更新窗口标题
            self.setWindowTitle("修改二级分类名称")
            self.set_default_values(tab_type_id, level_one_category_id, level_two_category_id, old_value)
            # self.script_type_combo.setEnabled(True)
            # self.level_one_category_combo.setEnabled(True)

        elif edit_type == 'script':
            # 编辑话术内容
            # 更新窗口标题
            self.setWindowTitle("修改话术内容")
            self.set_default_values(tab_type_id, level_one_category_id, level_two_category_id, script_id, old_value)
            # self.script_type_combo.setEnabled(True)
            # self.level_one_category_combo.setEnabled(True)
            # self.level_two_category_combo.setEnabled(True)

    def set_default_values(self, tab_type_id: int = 0, level_one_category_id: int = 0, level_two_category_id: int = 0,
                           script_id: int = 0, script_content: str = None):
        """设置默认值"""
        try:
            # 标记正在设置默认值
            self._setting_defaults = True

            # 首先确保下拉框数据已加载
            self.update_script_type_combo()

            # 设置话术类型默认值
            for script_type_data in self.scripts_data:
                if script_type_data['type_id'] == tab_type_id:
                    script_type_index = self.script_type_combo.findData(tab_type_id)
                    if script_type_index >= 0:
                        if self.edit_mode:
                            self.level_one_category_input.setText(level_one_category_id)
                        else:
                            self.script_type_combo.setCurrentIndex(index)
                            # 手动触发信号更新下级下拉框
                            self.update_level_one_category_combo(tab_type_id)

                        # 设置分类默认值
                        if level_one_category_id and level_one_category_id in self.scripts_data[tab_type_id]:
                            category_index = self.level_one_category_combo.findText(level_one_category_id)
                            if category_index >= 0:
                                if self.edit_mode:
                                    self.level_two_category_input.setText(level_two_category_id)
                                else:
                                    self.level_one_category_combo.setCurrentIndex(category_index)
                                    # 手动触发信号更新下级下拉框
                                    self.update_level_two_category_combo(level_one_category_id, tab_type_id)

                                # 设置二级分类默认值
                                if level_two_category_id and level_two_category_id in self.scripts_data[tab_type_id][
                                    level_one_category_id]:
                                    title_index = self.level_two_category_combo.findText(level_two_category_id)
                                    if title_index > 0:
                                        if self.edit_mode:
                                            self.content_input.setPlainText(script_content)
                                        else:
                                            self.level_two_category_combo.setCurrentIndex(title_index)

            # 标记默认值设置完成
            self._setting_defaults = False
            self._defaults_set = True

        except Exception as e:
            print(f"❌ 设置默认值失败: {e}")
            import traceback
            traceback.print_exc()
            self._setting_defaults = False

    # <============================处理基础数据方法==============================>
    def update_current_script_type_tab_data(self, data):
        '''更新当前选中的话术类型数据'''
        self.current_type_tab_name = data['name']
        self.current_type_tab_id = data['type_id']
        self.current_type_tab_data = data.copy()

    def update_current_level_one_category_tab_data(self, data):
        '''更新当前选中的一级分类数据'''
        self.current_level_one_category_name = data['name']
        self.current_level_one_category_id = data['level_one_category_id']
        self.current_level_one_category_data = data.copy()
        # 更新二级分类数据
        self.update_level_two_category_tab_data(data['data'])

    def update_level_two_category_tab_data(self, data):
        '''更新当前选中的二级分类数据'''
        self.current_level_two_category_data = data

    def update_current_script_type_data_dict(self, data):
        '''更新话术类型dict数据'''
        self.primary_tab_dict = {}
        for tab_data in data:
            dict = {
                'name': tab_data['name'],
                'type_id': tab_data['type_id']
            }
            self.primary_tab_dict[tab_data['type_id']] = dict
        print('self.primary_tab_dict====================>', self.primary_tab_dict)

    def update_current_level_one_category_dict(self, data):
        '''更新一级分类dict数据'''
        self.level_one_category_dict = {}
        for level_one_category_data in data:
            dict = {
                'name': level_one_category_data['name'],
                'type_id': level_one_category_data['type_id'],
                'level_one_category_id': level_one_category_data['level_one_category_id']
            }
            self.level_one_category_dict[level_one_category_data['level_one_category_id']] = dict
        print('self.level_one_category_dict====================>', self.level_one_category_dict)

    def update_level_two_category_data_dict(self, data):
        '''更新二级分类dict数据'''
        self.level_two_category_dict = {}
        for level_two_category_data in data:
            dict = {
                'name': level_two_category_data['name'],
                'type_id': level_two_category_data['type_id'],
                'level_one_category_id': level_two_category_data['level_one_category_id'],
                'level_two_category_id': level_two_category_data['level_two_category_id']
            }
            self.level_two_category_dict[level_two_category_data['level_two_category_id']] = dict
        print('self.level_two_category_dict====================>', self.level_two_category_dict)
