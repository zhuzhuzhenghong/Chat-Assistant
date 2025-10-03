"""
添加弹窗组件
包含添加话术分类、话术标题、话术内容等功能，支持权限控制
"""

import os
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel, 
    QPushButton, QLineEdit, QTextEdit, QComboBox, QGroupBox,
    QButtonGroup, QRadioButton, QCheckBox, QMessageBox, QFrame, QWidget
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from typing import Dict, List, Optional, Any


class AddDialog(QDialog):
    """添加内容弹窗"""
    
    # 信号定义
    category_added_signal = Signal(str, str)  # 话术类型名, 话术分类名
    title_added_signal: Signal = Signal(str, str, str)  # 话术类型名, 话术分类名, 话术标题名
    content_added_signal = Signal(str, str, str, str)  # 话术类型名, 话术分类名, 话术标题名, 话术内容
    
    def __init__(self, scripts_data: Dict[str, Any], user_permissions: Dict[str, bool] = None, parent=None):
        super().__init__(parent)
        self.scripts_data = scripts_data
        self.user_permissions = user_permissions or {
            'add_secondary_tab': True,
            'add_category': True,
            'add_script': True
        }
        
        # 初始化标志
        self._user_triggered_change = False
        self._setting_defaults = False  # 新增：标记是否正在设置默认值
        self._defaults_set = False      # 新增：标记默认值是否已设置
        
        self.setup_ui()
        self.setup_connections()
        self.update_ui_permissions()
        
    def setup_ui(self):
        """设置UI界面"""
        self.setWindowTitle("添加内容")
        self.setModal(False)  # 设置为非模态对话框，允许操作主窗口
        self.setFixedSize(500, 600)
        
        # 设置窗口标志，使其保持在前台但不阻塞主窗口
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.WindowStaysOnTopHint)
        
        # 加载样式表
        self.load_stylesheet()
        
        # 主布局
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
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
        form_layout.setSpacing(15)
        form_layout.setContentsMargins(20, 10, 20, 10)
        
        # 添加类型选择（水平布局的单选按钮）
        type_widget = QWidget()
        type_layout = QHBoxLayout(type_widget)
        type_layout.setContentsMargins(0, 0, 0, 0)
        type_layout.setSpacing(20)
        
        # 单选按钮组
        self.type_button_group = QButtonGroup()
        
        # 添加话术分类
        self.add_category_radio = QRadioButton("话术分类")
        self.add_category_radio.setChecked(True)
        self.type_button_group.addButton(self.add_category_radio, 0)
        type_layout.addWidget(self.add_category_radio)
        
        # 添加话术标题
        self.add_title_radio = QRadioButton("话术标题")
        self.type_button_group.addButton(self.add_title_radio, 1)
        type_layout.addWidget(self.add_title_radio)
        
        # 添加话术内容
        self.add_content_radio = QRadioButton("话术内容")
        self.type_button_group.addButton(self.add_content_radio, 2)
        type_layout.addWidget(self.add_content_radio)
        
        # 添加弹性空间
        type_layout.addStretch()
        
        form_layout.addRow("添加类型:", type_widget)
        
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
        
        # 名称输入
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("请输入名称...")
        form_layout.addRow("名称:", self.name_input)
        
        # 话术内容输入
        self.content_input = QTextEdit()
        self.content_input.setMinimumHeight(120)
        self.content_input.setPlaceholderText("请输入话术内容...")
        form_layout.addRow("话术内容:", self.content_input)
        

        
    def create_button_area(self, parent_layout):
        """创建按钮区域"""
        button_layout = QHBoxLayout()
        button_layout.setSpacing(15)
        
        # 添加弹性空间
        button_layout.addStretch()
        
        # 取消按钮
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.setObjectName("cancel_btn")
        self.cancel_btn.setMinimumSize(60, 20)
        button_layout.addWidget(self.cancel_btn)
        
        # 确认按钮
        self.confirm_btn = QPushButton("确认添加")
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
        self.primary_combo.currentTextChanged.connect(self.on_script_type_changed)
        self.category_combo.currentTextChanged.connect(self.on_category_changed)
        
        # 按钮点击
        self.cancel_btn.clicked.connect(self.reject)
        self.confirm_btn.clicked.connect(self.on_confirm)
        
    def update_ui_permissions(self):
        """根据权限更新UI"""
        # 根据用户权限禁用相应的选项
        if not self.user_permissions.get('add_secondary_tab', True):
            self.add_category_radio.setEnabled(False)
            self.add_category_radio.setToolTip("您没有添加话术分类的权限")
            
        if not self.user_permissions.get('add_category', True):
            self.add_title_radio.setEnabled(False)
            self.add_title_radio.setToolTip("您没有添加话术标题的权限")
            
        if not self.user_permissions.get('add_script', True):
            self.add_content_radio.setEnabled(False)
            self.add_content_radio.setToolTip("您没有添加话术内容的权限")
            
        # 如果没有任何权限，选择第一个可用的选项
        if not self.add_category_radio.isEnabled():
            if self.add_title_radio.isEnabled():
                self.add_title_radio.setChecked(True)
            elif self.add_content_radio.isEnabled():
                self.add_content_radio.setChecked(True)
                
    def update_script_type_combo(self):
        """更新话术类型下拉框"""
        self.primary_combo.clear()
        if self.scripts_data:
            self.primary_combo.addItems(list(self.scripts_data.keys()))
            
    def on_script_type_changed(self, script_type_name: str):
        """话术类型选择变化"""
        self.update_category_combo(script_type_name)
        
    def update_category_combo(self, script_type_name: str):
        """更新话术分类下拉框"""
        self.category_combo.clear()
        if script_type_name and script_type_name in self.scripts_data:
            self.category_combo.addItems(list(self.scripts_data[script_type_name].keys()))
            
    def on_category_changed(self, category_name: str):
        """话术分类选择变化"""
        script_type_name = self.primary_combo.currentText()
        self.update_title_combo(script_type_name, category_name)
        
    def update_title_combo(self, script_type_name: str, category_name: str):
        """更新话术标题下拉框"""
        self.title_combo.clear()
        if (script_type_name and category_name and 
            script_type_name in self.scripts_data and 
            category_name in self.scripts_data[script_type_name]):
            script_titles = list(self.scripts_data[script_type_name][category_name].keys())
            self.title_combo.addItems(script_titles)
            
    def on_type_changed(self, button):
        """添加类型变化"""
        # 只有在不是设置默认值时才标记为用户触发
        if not getattr(self, '_setting_defaults', False):
            self._user_triggered_change = True
        
        add_type = self.type_button_group.id(button)
        
        print(f"on_type_changed: add_type={add_type}, _setting_defaults={getattr(self, '_setting_defaults', False)}")
        
        # 根据类型显示/隐藏相应的输入控件
        if add_type == 0:  # 添加话术分类
            # 隐藏不需要的控件
            self.category_combo.setVisible(False)
            self.title_combo.setVisible(False)
            self.content_input.setVisible(False)
            
            # 隐藏对应的标签
            self.hide_label_by_text("选择话术分类:")
            self.hide_label_by_text("选择话术标题:")
            self.hide_label_by_text("话术内容:")
            
            # 显示需要的控件
            self.primary_combo.setVisible(True)
            self.name_input.setVisible(True)
            
            # 显示对应的标签
            self.show_label_by_text("选择话术类型:")
            self.show_label_by_text("名称:")
            
            self.name_input.setPlaceholderText("请输入话术分类名称...")
            
        elif add_type == 1:  # 添加话术标题
            # 隐藏不需要的控件
            self.title_combo.setVisible(False)
            self.content_input.setVisible(False)
            
            # 隐藏对应的标签
            self.hide_label_by_text("选择话术标题:")
            self.hide_label_by_text("话术内容:")
            
            # 显示需要的控件
            self.primary_combo.setVisible(True)
            self.category_combo.setVisible(True)
            self.name_input.setVisible(True)
            
            # 显示对应的标签
            self.show_label_by_text("选择话术类型:")
            self.show_label_by_text("选择话术分类:")
            self.show_label_by_text("名称:")
            
            self.name_input.setPlaceholderText("请输入话术标题名称...")
            
            # 只在用户手动切换类型且不是设置默认值时才触发数据更新
            if (self._user_triggered_change and not getattr(self, '_setting_defaults', False)):
                self.on_script_type_changed(self.primary_combo.currentText())
            
        elif add_type == 2:  # 添加话术内容
            # 显示需要的控件
            self.primary_combo.setVisible(True)
            self.category_combo.setVisible(True)
            self.title_combo.setVisible(True)
            self.content_input.setVisible(True)
            
            # 隐藏不需要的控件
            self.name_input.setVisible(False)
            
            # 显示需要的标签
            self.show_label_by_text("选择话术类型:")
            self.show_label_by_text("选择话术分类:")
            self.show_label_by_text("选择话术标题:")
            self.show_label_by_text("话术内容:")
            
            # 隐藏不需要的标签
            self.hide_label_by_text("名称:")
            
            # 只在用户手动切换类型且不是设置默认值时才触发数据更新
            if (self._user_triggered_change and not getattr(self, '_setting_defaults', False)):
                self.on_script_type_changed(self.primary_combo.currentText())
            
    def on_confirm(self):
        """确认添加"""
        add_type = self.type_button_group.checkedId()
        script_type_name = self.primary_combo.currentText()
        name = self.name_input.text().strip()
        
        # 基本验证
        if not script_type_name:
            QMessageBox.warning(self, "警告", "请选择话术类型！")
            return
            
        # 只有在添加话术分类或话术标题时才需要名称
        if add_type in [0, 1] and not name:
            QMessageBox.warning(self, "警告", "请输入名称！")
            return
            
        try:
            if add_type == 0:  # 添加话术分类
                if not self.user_permissions.get('add_secondary_tab', True):
                    QMessageBox.warning(self, "权限不足", "您没有添加话术分类的权限！")
                    return
                    
                # 检查是否已存在
                if name in self.scripts_data.get(script_type_name, {}):
                    QMessageBox.warning(self, "警告", f"话术分类 '{name}' 已存在！")
                    return
                    
                self.category_added_signal.emit(script_type_name, name)
                
            elif add_type == 1:  # 添加话术标题
                if not self.user_permissions.get('add_category', True):
                    QMessageBox.warning(self, "权限不足", "您没有添加话术标题的权限！")
                    return
                    
                category_name = self.category_combo.currentText()
                if not category_name:
                    QMessageBox.warning(self, "警告", "请选择话术分类！")
                    return
                    
                # 检查是否已存在
                if (category_name in self.scripts_data.get(script_type_name, {}) and
                    name in self.scripts_data[script_type_name][category_name]):
                    QMessageBox.warning(self, "警告", f"话术标题 '{name}' 已存在！")
                    return
                    
                self.title_added_signal.emit(script_type_name, category_name, name)
                
            elif add_type == 2:  # 添加话术内容
                if not self.user_permissions.get('add_script', True):
                    QMessageBox.warning(self, "权限不足", "您没有添加话术内容的权限！")
                    return
                    
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
                    
                self.content_added_signal.emit(script_type_name, category_name, title_name, content)
                
            # 成功添加后关闭对话框
            self.accept()
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"添加失败：{str(e)}")
            

        
    def set_user_permissions(self, permissions: Dict[str, bool]):
        """设置用户权限"""
        self.user_permissions = permissions
        self.update_ui_permissions()
        
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
                    
    def set_default_type(self, default_type: int):
        """设置默认添加类型"""
        if default_type == 0:  # 话术分类
            self.add_category_radio.setChecked(True)
        elif default_type == 1:  # 话术标题
            self.add_title_radio.setChecked(True)
        elif default_type == 2:  # 话术内容
            self.add_content_radio.setChecked(True)
        
        # 只更新UI显示，不触发数据重置
        self._update_ui_visibility_only()
        
    def set_default_values(self, script_type: str = None, category: str = None, title: str = None):
        """设置默认值"""
        try:
            print(f"🔍 set_default_values 被调用: script_type={script_type}, category={category}, title={title}")
            
            # 标记正在设置默认值
            self._setting_defaults = True
            
            # 首先确保下拉框数据已加载
            self.update_script_type_combo()
            print(f"🔍 话术类型下拉框选项: {[self.primary_combo.itemText(i) for i in range(self.primary_combo.count())]}")
            
            # 设置话术类型默认值
            if script_type and script_type in self.scripts_data:
                index = self.primary_combo.findText(script_type)
                print(f"🔍 话术类型 '{script_type}' 在下拉框中的索引: {index}")
                if index >= 0:
                    self.primary_combo.setCurrentIndex(index)
                    # 手动触发信号更新下级下拉框
                    self.update_category_combo(script_type)
                    print(f"✅ 已设置话术类型为: {script_type}")
                    
                    # 设置分类默认值
                    if category and category in self.scripts_data[script_type]:
                        category_index = self.category_combo.findText(category)
                        print(f"🔍 话术分类 '{category}' 在下拉框中的索引: {category_index}")
                        if category_index >= 0:
                            self.category_combo.setCurrentIndex(category_index)
                            # 手动触发信号更新下级下拉框
                            self.update_title_combo(script_type, category)
                            print(f"✅ 已设置话术分类为: {category}")
                            
                            # 设置标题默认值
                            if title and title in self.scripts_data[script_type][category]:
                                title_index = self.title_combo.findText(title)
                                print(f"🔍 话术标题 '{title}' 在下拉框中的索引: {title_index}")
                                if title_index >= 0:
                                    self.title_combo.setCurrentIndex(title_index)
                                    print(f"✅ 已设置话术标题为: {title}")
                                else:
                                    print(f"❌ 话术标题 '{title}' 在下拉框中未找到")
                            else:
                                print(f"🔍 没有提供话术标题或话术标题不存在: title={title}")
                        else:
                            print(f"❌ 话术分类 '{category}' 在下拉框中未找到")
                    else:
                        print(f"🔍 没有提供话术分类或话术分类不存在: category={category}")
                else:
                    print(f"❌ 话术类型 '{script_type}' 在下拉框中未找到")
            else:
                print(f"🔍 没有提供话术类型或话术类型不存在: script_type={script_type}")
            
            # 标记默认值设置完成
            self._setting_defaults = False
            self._defaults_set = True
            print("✅ 默认值设置完成")
                        
        except Exception as e:
            print(f"❌ 设置默认值失败: {e}")
            import traceback
            traceback.print_exc()
            self._setting_defaults = False
    

        
    def _update_ui_visibility_only(self):
        """只更新UI显示状态，不触发数据重置"""
        add_type = self.type_button_group.checkedId()
        
        # 根据类型显示/隐藏相应的输入控件
        if add_type == 0:  # 添加话术分类
            # 隐藏不需要的控件
            self.category_combo.setVisible(False)
            self.title_combo.setVisible(False)
            self.content_input.setVisible(False)
            
            # 隐藏对应的标签
            self.hide_label_by_text("选择话术分类:")
            self.hide_label_by_text("选择话术标题:")
            self.hide_label_by_text("话术内容:")
            
            # 显示需要的控件
            self.primary_combo.setVisible(True)
            self.name_input.setVisible(True)
            
            # 显示对应的标签
            self.show_label_by_text("选择话术类型:")
            self.show_label_by_text("名称:")
            
            self.name_input.setPlaceholderText("请输入话术分类名称...")
            
        elif add_type == 1:  # 添加话术标题
            # 隐藏不需要的控件
            self.title_combo.setVisible(False)
            self.content_input.setVisible(False)
            
            # 隐藏对应的标签
            self.hide_label_by_text("选择话术标题:")
            self.hide_label_by_text("话术内容:")
            
            # 显示需要的控件
            self.primary_combo.setVisible(True)
            self.category_combo.setVisible(True)
            self.name_input.setVisible(True)
            
            # 显示对应的标签
            self.show_label_by_text("选择话术类型:")
            self.show_label_by_text("选择话术分类:")
            self.show_label_by_text("名称:")
            
            self.name_input.setPlaceholderText("请输入话术标题名称...")
            
        elif add_type == 2:  # 添加话术内容
            # 显示需要的控件
            self.primary_combo.setVisible(True)
            self.category_combo.setVisible(True)
            self.title_combo.setVisible(True)
            self.content_input.setVisible(True)
            
            # 隐藏不需要的控件
            self.name_input.setVisible(False)
            
            # 显示需要的标签
            self.show_label_by_text("选择话术类型:")
            self.show_label_by_text("选择话术分类:")
            self.show_label_by_text("选择话术标题:")
            self.show_label_by_text("话术内容:")
            
            # 隐藏不需要的标签
            self.hide_label_by_text("名称:")
    
    def showEvent(self, event):
        """显示事件"""
        super().showEvent(event)
        
        # 只有在没有设置默认值的情况下才更新下拉框数据
        if not getattr(self, '_defaults_set', False):
            print("showEvent: 更新下拉框数据")
            self.update_script_type_combo()
        else:
            print("showEvent: 跳过下拉框数据更新，因为已设置默认值")
        
        # 初始化UI状态（但不触发数据重置）
        self._update_ui_visibility_only()
        
        print(f"showEvent: _defaults_set={getattr(self, '_defaults_set', False)}")