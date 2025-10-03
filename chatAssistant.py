"""
聚雍宝 - PySide6版本
智能客服助手 - 现代化界面版本
"""
import sys
import os
import json
import time
import threading
from pathlib import Path
from typing import Dict, Any, Optional

# PySide6 imports
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QGridLayout, QLabel, QPushButton, QLineEdit, QTextEdit, QTreeWidget, 
    QTreeWidgetItem, QGroupBox, QCheckBox, QComboBox, QFrame, QSplitter,
    QScrollArea, QTabWidget, QStatusBar, QMenuBar, QMenu, QMessageBox,
    QDialog, QDialogButtonBox, QProgressBar, QSpacerItem, QSizePolicy
)
from PySide6.QtCore import (
    Qt, QTimer, QThread, QObject, Signal, QSize, QPropertyAnimation, 
    QEasingCurve, QRect, QPoint
)
from PySide6.QtGui import (
    QFont, QIcon, QPalette, QColor, QPixmap, QPainter, QBrush, 
    QLinearGradient, QAction, QKeySequence, QCursor
)

# 导入原有模块
import pyautogui
import pyperclip
import win32gui
import win32con
from api_manager import APIManager
from data_adapter import DataAdapter
import utils

# 导入样式和主题管理器
from styles.style_manager import style_manager
from styles.theme_manager import theme_manager

# 导入窗口吸附管理器
from window_dock_manager import WindowDockManager

# 导入自定义标题栏
from components.custom_title_bar import CustomTitleBar

# 导入添加弹窗
from components.add_dialog import AddDialog

"""窗口监控线程"""
class WindowMonitor(QThread):

    window_changed = Signal(int, str)  # 窗口句柄, 窗口标题
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.monitoring = True
        self.is_locked = False
        self.my_window_handle = None
        
    def run(self):
        """监控线程主循环"""
        while self.monitoring:
            try:
                if self.is_locked:
                    self.msleep(500)
                    continue
                    
                current_window = win32gui.GetForegroundWindow()
                
                if current_window and current_window != self.my_window_handle:
                    try:
                        title = win32gui.GetWindowText(current_window)
                        if title and title.strip() and "聚雍宝" not in title:
                            self.window_changed.emit(current_window, title.strip())
                    except:
                        pass
                        
                self.msleep(500)
            except Exception as e:
                print('监控线程主循环报错',e)
                self.msleep(1000)
    
    def stop_monitoring(self):
        """停止监控"""
        self.monitoring = False
        self.quit()
        self.wait()

"""现代化按钮组件"""
class ModernButton(QPushButton):

    def __init__(self, text="", button_type="default", parent=None):
        super().__init__(text, parent)
        self.button_type = button_type
        self.setup_style()
        
    def setup_style(self):
        """设置按钮样式"""
        self.setObjectName(f"{self.button_type}_button")
        
        # 设置最小尺寸
        if self.button_type == "small":
            self.setMinimumSize(50, 20)
            self.setMaximumSize(80, 24)
        else:
            self.setMinimumSize(80, 32)


class ModernTabButton(QPushButton):
    """现代化Tab按钮"""
    
    def __init__(self, text="", is_selected=False, parent=None):
        super().__init__(text, parent)
        self.is_selected = is_selected
        self.setup_style()
        
    def setup_style(self):
        """设置Tab按钮样式"""
        if self.is_selected:
            self.setObjectName("tab_button_selected")
        else:
            self.setObjectName("tab_button")
            
    def set_selected(self, selected: bool):
        """设置选中状态"""
        self.is_selected = selected
        self.setup_style()
        # 强制刷新样式
        self.style().unpolish(self)
        self.style().polish(self)
        self.update()


class SearchLineEdit(QLineEdit):
    """带占位符的搜索框"""
    
    def __init__(self, placeholder="", parent=None):
        super().__init__(parent)
        self.placeholder_text = placeholder
        self.setPlaceholderText(placeholder)
        
        # 设置样式
        self.setMinimumHeight(28)  # 减小高度使其更紧凑
        self.setMaximumHeight(32)  # 设置最大高度


class ModernTreeWidget(QTreeWidget):
    """现代化树形控件"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_style()
        
    def setup_style(self):
        """设置树形控件样式"""
        self.setHeaderHidden(True)
        self.setRootIsDecorated(True)
        self.setAlternatingRowColors(True)
        self.setIndentation(20)
        self.setMinimumHeight(200)
        # 设置更紧凑的行高
        self.setUniformRowHeights(True)
        # 去除顶部空白
        self.setContentsMargins(0, 0, 0, 0)
        self.setViewportMargins(0, 0, 0, 0)


class AssistantMainWindow(QMainWindow):
    """主窗口类"""
    
    def __init__(self):
        super().__init__()
        
        # 初始化拖拽相关属性
        self.drag_position = None
        self.resize_direction = None
        self.resize_margin = 8  # 边缘调整大小的区域宽度
        self.resize_start_pos = None
        self.resize_start_geometry = None
        
        # 初始化数据
        self.init_data()
        
        # 设置窗口
        self.setup_window()
        
        # 创建界面
        self.create_ui()
        
        # 初始化监控
        self.init_monitoring()
        
        # 初始化吸附管理器
        self.init_dock_manager()
        
        # 加载数据
        self.load_initial_data()
        
        # # 确保背景渐变生效（在所有初始化完成后）
        # QTimer.singleShot(100, self.apply_background_gradient)
        
    def init_data(self):
        """初始化数据变量"""
        # 话术数据文件
        self.script_file = "scripts.json"
        self.config_file = "config.json"
        
        # Tab数据结构
        self.current_primary_tab = "公司话术"
        self.current_secondary_tab = "常用"
        
        # 窗口跟踪
        self.target_window = None
        self.target_title = "无"
        self.is_locked = False
        
        # 发送模式配置
        self.send_mode = "直接发送"
        self.always_on_top = True
        self.position_locked = False
        
        # 吸附功能
        self.dock_enabled = False
        self.dock_gap = 1
        
        # 用户登录状态
        self.current_user_id = None
        self.is_logged_in = False
        
        # 数据结构
        self.scripts_data = {}
        self.current_scripts_data = {}
        self.filtered_scripts = {}
        
        # 组件
        self.api_manager = None
        self.data_adapter = None
        self.window_monitor = None
        self.dock_manager = None
        
        # UI组件引用
        self.primary_tabs = {}
        self.secondary_tab_buttons = {}
        
        # 吸附功能配置
        self.dock_enabled = False
        self.dock_gap = 1
        
    def setup_window(self):
        """设置窗口属性"""
        self.setWindowTitle("聚雍宝")
        self.setMinimumSize(300, 500)
        
        # 设置无边框窗口
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.resize(300, 700)
        
        # 设置窗口图标（如果有的话）
        # self.setWindowIcon(QIcon("styles/icons/app_icon.png"))
        
        # # 直接设置主窗口背景渐变
        # self.setStyleSheet("""
        #     QMainWindow {
        #         background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        #                     stop:0 #a1c4fd, stop:1 #c2e9ff);
        #         border-radius: 12px;
        #     }
        # """)
        
        # 设置窗口置顶
        if self.always_on_top:
            self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)
    
    # def apply_background_gradient(self):
    #     """应用背景渐变（确保在所有样式加载后执行）"""
    #     gradient_style = """
    #         QMainWindow {
    #             background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
    #                         stop:0 #a1c4fd, stop:1 #c2e9ff);
    #             border-radius: 12px;
    #         }
    #         QWidget#main_frame {
    #             background: transparent;
    #             border: none;
    #         }
    #     """
    #     self.setStyleSheet(gradient_style)
    #     print("✅ 背景渐变已应用")
    
    def create_ui(self):
        """创建用户界面"""
        # 创建中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        central_widget.setObjectName("main_frame")
        
        # 设置中央部件为透明，显示主窗口背景
        central_widget.setStyleSheet("""
            QWidget#main_frame {
                background: transparent;
                border: none;
            }
        """)
        
        # 主布局
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)  # 减少顶部边距
        main_layout.setSpacing(2)  # 组件之间的间距
        
        # 创建自定义标题栏
        self.title_bar = CustomTitleBar()
        main_layout.addWidget(self.title_bar)
        
        # 连接标题栏信号
        self.title_bar.close_clicked.connect(self.close)
        self.title_bar.minimize_clicked.connect(self.showMinimized)
        self.title_bar.dock_toggled.connect(self.on_dock_changed)
        self.title_bar.lock_toggled.connect(self.on_lock_changed)
        self.title_bar.topmost_toggled.connect(self.on_topmost_changed)
        
        # 创建各个部分
        # self.create_target_section(main_layout)
        self.create_primary_tabs_section(main_layout)
        self.create_secondary_tabs_section(main_layout)
        self.create_action_buttons_section(main_layout)
        self.create_tree_section(main_layout)
        self.create_search_section(main_layout)
        self.create_status_section(main_layout)
        
        # 菜单栏功能已整合到设置按钮中
        
    # def create_target_section(self, parent_layout):
    #     """创建目标窗口部分"""
    #     # target_group = QGroupBox("当前目标")
    #     target_group = QWidget()

    #     parent_layout.addWidget(target_group)
        
    #     target_layout = QHBoxLayout(target_group)
    #     target_layout.setContentsMargins(0, 0, 0, 0)
        
    #     # 目标标签
    #     self.target_label = QLabel("目标: 无")
    #     self.target_label.setObjectName("target_label")
    #     target_layout.addWidget(self.target_label, 1)
        
    #     # 控制按钮组
    #     controls_layout = QHBoxLayout()
        
    #     # 置顶复选框
    #     self.topmost_checkbox = QCheckBox("置顶")
    #     self.topmost_checkbox.setChecked(self.always_on_top)
    #     self.topmost_checkbox.toggled.connect(self.on_topmost_changed)
    #     controls_layout.addWidget(self.topmost_checkbox)
        
    #     # 锁定复选框
    #     self.lock_checkbox = QCheckBox("锁定")
    #     self.lock_checkbox.setChecked(self.is_locked)
    #     self.lock_checkbox.toggled.connect(self.on_lock_changed)
    #     controls_layout.addWidget(self.lock_checkbox)
        
    #     # 吸附复选框
    #     self.dock_checkbox = QCheckBox("吸附")
    #     self.dock_checkbox.setChecked(self.dock_enabled)
    #     self.dock_checkbox.toggled.connect(self.on_dock_changed)
    #     controls_layout.addWidget(self.dock_checkbox)
        
        # target_layout.addLayout(controls_layout)
        
    def create_primary_tabs_section(self, parent_layout):
        """创建一级Tab部分"""
        primary_group = QWidget()
        parent_layout.addWidget(primary_group)
        
        primary_layout = QHBoxLayout(primary_group)
        primary_layout.setContentsMargins(0, 0, 0, 0)  # 减少底部边距
        
        # Tab容器
        self.primary_tab_widget = QTabWidget()
        self.primary_tab_widget.setTabPosition(QTabWidget.North)
        self.primary_tab_widget.currentChanged.connect(self.on_primary_tab_changed)
        
        # 为Tab栏设置右键菜单
        try:
            self.primary_tab_widget.tabBar().setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            self.primary_tab_widget.tabBar().customContextMenuRequested.connect(self.show_primary_tab_context_menu)
            print("一级Tab右键菜单设置成功")  # 调试信息
        except Exception as e:
            print(f"设置一级Tab右键菜单失败: {e}")
        
        primary_layout.addWidget(self.primary_tab_widget, 1)
        
    def create_secondary_tabs_section(self, parent_layout):
        """创建二级Tab部分"""
        secondary_group = QWidget()
        parent_layout.addWidget(secondary_group)
        
        secondary_layout = QHBoxLayout(secondary_group)
        secondary_layout.setContentsMargins(0, 0, 0, 0)  # 与一级菜单保持一致
        
        # Tab容器
        self.secondary_tab_widget = QTabWidget()
        self.secondary_tab_widget.setTabPosition(QTabWidget.TabPosition.North)
        self.secondary_tab_widget.currentChanged.connect(self.on_secondary_tab_changed)
        
        # 为Tab栏设置右键菜单
        try:
            self.secondary_tab_widget.tabBar().setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            self.secondary_tab_widget.tabBar().customContextMenuRequested.connect(self.show_secondary_tab_context_menu)
            print("二级Tab右键菜单设置成功")  # 调试信息
        except Exception as e:
            print(f"设置二级Tab右键菜单失败: {e}")
        
        secondary_layout.addWidget(self.secondary_tab_widget, 1)
        
    def create_action_buttons_section(self, parent_layout):
        """创建操作按钮部分"""
        # 创建容器widget来控制边距
        action_widget = QWidget()
        action_layout = QHBoxLayout(action_widget)
        action_layout.setContentsMargins(0, 0, 0, 0)  # 减少下边距
        parent_layout.addWidget(action_widget)
        
        # 添加内容按钮
        add_content_btn = ModernButton("➕ 添加内容", "primary")
        add_content_btn.clicked.connect(self.show_add_dialog)
        action_layout.addWidget(add_content_btn)
        
        # 去掉"添加话术标题"按钮，因为添加内容功能已经包含了这个功能
        # add_category_btn = ModernButton("添加话术标题", "secondary")
        # add_category_btn.clicked.connect(self.add_category)
        # action_layout.addWidget(add_category_btn)
        
        action_layout.addStretch()
        
        # 提示标签
        self.tip_label = QLabel()
        self.tip_label.setObjectName("tip_label")
        self.update_tip_text()
        action_layout.addWidget(self.tip_label)
        
    def create_tree_section(self, parent_layout):
        """创建树形列表部分"""
        tree_group = QGroupBox()  # 恢复标题显示
        parent_layout.addWidget(tree_group, 1)  # 设置拉伸因子
        
        tree_layout = QVBoxLayout(tree_group)
        tree_layout.setContentsMargins(0, 0, 0, 0)  # 大幅减少上边距
        
        # 树形控件
        self.tree_widget = ModernTreeWidget()
        self.tree_widget.setHeaderHidden(True)
        self.tree_widget.itemDoubleClicked.connect(self.on_tree_double_click)
        self.tree_widget.itemClicked.connect(self.on_tree_single_click)
        self.tree_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree_widget.customContextMenuRequested.connect(self.show_tree_context_menu)
        tree_layout.addWidget(self.tree_widget)
        
    def create_search_section(self, parent_layout):
        """创建搜索部分"""
        search_group = QWidget()  # 去掉标题
        parent_layout.addWidget(search_group)
        
        search_layout = QHBoxLayout(search_group)
        search_layout.setContentsMargins(0, 0, 0, 0)
        
        # 搜索框
        self.search_edit = SearchLineEdit("搜索话术...")  # 缩短placeholder文字
        self.search_edit.textChanged.connect(self.on_search_changed)
        search_layout.addWidget(self.search_edit, 1)
        
        # 清空按钮
        # clear_btn = ModernButton("清空", "small")
        # clear_btn.clicked.connect(self.clear_search)
        # clear_btn.setMaximumSize(50, 24)  # 限制按钮大小
        # search_layout.addWidget(clear_btn)
        
    def create_status_section(self, parent_layout):
        """创建状态栏部分"""
        status_layout = QHBoxLayout()
        parent_layout.addLayout(status_layout)
        
        # 状态标签
        self.status_label = QLabel("就绪")
        self.status_label.setObjectName("status_label")
        status_layout.addWidget(self.status_label, 1)
        
        # 登录按钮
        self.login_btn = ModernButton("登录", "secondary")
        self.login_btn.clicked.connect(self.show_login_dialog)
        status_layout.addWidget(self.login_btn)
        
        # 设置按钮
        settings_btn = ModernButton("⚙️", "small")
        settings_btn.setMaximumWidth(32)
        settings_btn.clicked.connect(self.show_settings_menu)
        status_layout.addWidget(settings_btn)
        
        # 菜单栏功能已整合到设置按钮中，此方法已移除
    
    def init_monitoring(self):
        """初始化窗口监控"""
        # 获取自己的窗口句柄
        def find_my_window(hwnd, param):
            try:
                if win32gui.IsWindowVisible(hwnd):
                    title = win32gui.GetWindowText(hwnd)
                    if "聚雍宝" in title:
                        self.window_monitor.my_window_handle = hwnd
                        return False
            except:
                pass
            return True
        
        # 创建监控线程
        self.window_monitor = WindowMonitor(self)
        self.window_monitor.window_changed.connect(self.on_window_changed)
        
        # 延迟启动监控
        QTimer.singleShot(1000, self.start_monitoring)
        
    def start_monitoring(self):
        """启动窗口监控"""
        if self.window_monitor:
            # 获取自己的窗口句柄
            def find_my_window(hwnd, param):
                try:
                    if win32gui.IsWindowVisible(hwnd):
                        title = win32gui.GetWindowText(hwnd)
                        if "聚雍宝" in title:
                            if self.window_monitor:
                                self.window_monitor.my_window_handle = hwnd
                            return False
                except:
                    pass
                return True
            
            # 查找自己的窗口句柄
            win32gui.EnumWindows(find_my_window, None)
            self.window_monitor.start()
    
    def init_dock_manager(self):
        """初始化吸附管理器"""
        self.dock_manager = WindowDockManager(self)
        self.dock_manager.dock_position_changed.connect(self.on_dock_position_changed)
    
    def load_initial_data(self):
        """加载初始数据"""
        try:
            # 初始化数据适配器
            self.data_adapter = DataAdapter(
                api_manager=None,
                script_file=self.script_file,
                config_file=self.config_file,
                user_id=0
            )
            
            # 初始化API管理器
            self.api_manager = APIManager()
            
            # 加载数据
            self.load_data_from_adapter()
            
            # 更新界面
            self.update_all_ui()
            
            # 初始化标题栏状态
            if hasattr(self, 'title_bar'):
                self.title_bar.set_dock_state(self.dock_enabled)
                self.title_bar.set_lock_state(self.position_locked)
                self.title_bar.set_topmost_state(self.always_on_top)
            
        except Exception as e:
            print(f"加载初始数据失败: {e}")
            self.status_label.setText(f"数据加载失败: {e}")
    
    def load_data_from_adapter(self):
        """从数据适配器加载数据"""
        if self.data_adapter:
            # 获取话术数据
            scripts_data = self.data_adapter.get_scripts_data()
            if scripts_data:
                self.scripts_data = scripts_data
                # 确保当前Tab存在
                if self.current_primary_tab not in self.scripts_data:
                    self.current_primary_tab = list(self.scripts_data.keys())[0]
                if self.current_secondary_tab not in self.scripts_data[self.current_primary_tab]:
                    self.current_secondary_tab = list(self.scripts_data[self.current_primary_tab].keys())[0]
            else:
                # 使用默认数据
                self.scripts_data = utils.init_scripts_data()
            
            # 加载配置
            config = self.data_adapter.get_config_data()
            if config:
                self.send_mode = config.get('send_mode', self.send_mode)
                self.always_on_top = config.get('always_on_top', self.always_on_top)
                self.dock_enabled = config.get('dock_enabled', self.dock_enabled)
                self.dock_gap = config.get('dock_gap', self.dock_gap)
                
                # 更新吸附管理器配置
                if self.dock_manager:
                    self.dock_manager.set_dock_gap(self.dock_gap)
                
                # 更新UI状态
                if hasattr(self, 'dock_checkbox'):
                    self.dock_checkbox.setChecked(self.dock_enabled)
            
            # 更新当前数据
            self.current_scripts_data = self.get_current_scripts_data()
            self.filtered_scripts = self.current_scripts_data.copy()
    
    def get_current_scripts_data(self) -> Dict[str, Any]:
        """获取当前选中Tab的数据"""
        if hasattr(self, 'scripts_data'):
            return self.scripts_data.get(self.current_primary_tab, {}).get(self.current_secondary_tab, {})
        return {}
    
    def update_all_ui(self):
        """更新所有界面元素"""
        self.update_primary_tabs()
        self.update_secondary_tabs()
        self.update_tree()
        self.update_login_status()
        self.update_tip_text()
    
    def update_primary_tabs(self):
        """更新一级Tab"""
        # 清空现有Tab
        self.primary_tab_widget.clear()
        self.primary_tabs.clear()
        
        # 添加新Tab
        if self.scripts_data:
            for tab_name in self.scripts_data.keys():
                tab_widget = QWidget()
                self.primary_tabs[tab_name] = tab_widget
                self.primary_tab_widget.addTab(tab_widget, tab_name)
        # 注释掉添加"+"按钮的代码，因为话术类型是写死的，不需要添加功能
        # # 添加"+"按钮作为最后一个Tab
        # add_tab_widget = QWidget()
        # self.primary_tab_widget.addTab(add_tab_widget, "+")
            # 选中当前Tab
            tab_names = list(self.scripts_data.keys())
            if self.current_primary_tab in tab_names:
                index = tab_names.index(self.current_primary_tab)
                self.primary_tab_widget.setCurrentIndex(index)
        
        # 重新设置右键菜单（因为Tab被清空重建了）
        try:
            self.primary_tab_widget.tabBar().setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            self.primary_tab_widget.tabBar().customContextMenuRequested.connect(self.show_primary_tab_context_menu)
            print("一级Tab右键菜单重新设置成功")  # 调试信息
        except Exception as e:
            print(f"重新设置一级Tab右键菜单失败: {e}")
    
    def update_secondary_tabs(self):
        """更新二级Tab"""
        # 临时断开信号连接，避免在更新过程中触发事件
        self.secondary_tab_widget.currentChanged.disconnect()
        
        # 清空现有Tab
        self.secondary_tab_widget.clear()
        
        # 添加新Tab
        if self.current_primary_tab in self.scripts_data:
            for tab_name in self.scripts_data[self.current_primary_tab].keys():
                tab_widget = QWidget()
                self.secondary_tab_widget.addTab(tab_widget, tab_name)
            
            # 添加"+"按钮作为最后一个Tab，用于添加话术分类
            add_tab_widget = QWidget()
            self.secondary_tab_widget.addTab(add_tab_widget, "+")
            
            # 选中当前Tab
            tab_names = list(self.scripts_data[self.current_primary_tab].keys())
            if self.current_secondary_tab in tab_names:
                index = tab_names.index(self.current_secondary_tab)
                self.secondary_tab_widget.setCurrentIndex(index)
                print(f"设置二级Tab索引: {index}, 对应Tab: {self.current_secondary_tab}")  # 调试信息
        
        # 重新连接信号
        self.secondary_tab_widget.currentChanged.connect(self.on_secondary_tab_changed)
        
        # 重新设置右键菜单（因为Tab被清空重建了）
        try:
            self.secondary_tab_widget.tabBar().setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            self.secondary_tab_widget.tabBar().customContextMenuRequested.connect(self.show_secondary_tab_context_menu)
            print("二级Tab右键菜单重新设置成功")  # 调试信息
        except Exception as e:
            print(f"重新设置二级Tab右键菜单失败: {e}")
    
    def update_tree(self):
        """更新树形列表"""
        self.tree_widget.clear()
        
        first_category_item = None
        
        # 处理新的三级数据结构：话术分类 -> 话术标题 -> 话术内容列表
        for category_name, titles_data in self.filtered_scripts.items():
            # 创建分类节点
            category_item = QTreeWidgetItem([f"📁 {category_name}"])
            category_item.setData(0, Qt.ItemDataRole.UserRole, {"type": "category", "name": category_name})
            self.tree_widget.addTopLevelItem(category_item)
            
            # 记录第一个分类项，用于默认高亮
            if first_category_item is None:
                first_category_item = category_item
            
            # 添加话术标题节点
            if isinstance(titles_data, dict):
                for title_name, contents_list in titles_data.items():
                    # 创建标题节点
                    title_item = QTreeWidgetItem([f"📝 {title_name}"])
                    title_item.setData(0, Qt.ItemDataRole.UserRole, {"type": "title", "name": title_name, "category": category_name})
                    category_item.addChild(title_item)
                    
                    # 添加话术内容节点
                    if isinstance(contents_list, list):
                        for i, content in enumerate(contents_list):
                            display_text = content if len(content) <= 50 else content[:50] + "..."
                            script_item = QTreeWidgetItem([f"💬 {display_text}"])
                            script_item.setData(0, Qt.ItemDataRole.UserRole, {
                                "type": "script", 
                                "content": content, 
                                "category": category_name,
                                "title": title_name,
                                "index": i
                            })
                            title_item.addChild(script_item)
                    
                    title_item.setExpanded(True)
            else:
                # 兼容旧的数据结构（直接是话术列表）
                if isinstance(titles_data, list):
                    for i, content in enumerate(titles_data):
                        display_text = content if len(content) <= 50 else content[:50] + "..."
                        script_item = QTreeWidgetItem([f"💬 {display_text}"])
                        script_item.setData(0, Qt.ItemDataRole.UserRole, {
                            "type": "script", 
                            "content": content, 
                            "category": category_name,
                            "index": i
                        })
                        category_item.addChild(script_item)
            
            category_item.setExpanded(True)
        
        # 设置第一个一级分类为默认高亮
        if first_category_item:
            self.tree_widget.setCurrentItem(first_category_item)
    
    def update_login_status(self):
        """更新登录状态"""
        if self.is_logged_in and self.current_user_id:
            self.login_btn.setText(f"用户:{self.current_user_id[:6]}...")
        else:
            self.login_btn.setText("登录")
    
    def update_tip_text(self):
        """更新提示文字"""
        mode_text = {
            "添加到剪贴板": "复制到剪贴板",
            "添加到输入框": "添加到输入框",
            "直接发送": "直接发送"
        }
        tip = f"双击话术 → {mode_text.get(self.send_mode, self.send_mode)}"
        self.tip_label.setText(tip)
    
    # 事件处理方法
    def on_window_changed(self, window_handle: int, window_title: str):
        """窗口变化事件"""
        if not self.is_locked:
            self.target_window = window_handle
            self.target_title = window_title
            self.update_target_display()
            
            # 如果启用了吸附功能，更新吸附目标
            if self.dock_enabled and self.dock_manager:
                self.dock_manager.enable_docking(window_handle)
    
    def update_target_display(self):
        """更新目标显示"""
        display_title = self.target_title
        if len(display_title) > 15:
            display_title = display_title[:15] + "..."
        
        lock_status = "🔒" if self.is_locked else ""
        dock_status = "📎" if self.dock_enabled else ""
        # self.target_label.setText(f"{lock_status}{dock_status}目标: {display_title}")
        # 目标标签已被移除，改为在状态栏显示
        self.status_label.setText(f"{lock_status}{dock_status}目标: {display_title}")
    
    def on_topmost_changed(self, checked: bool):
        """置顶状态改变"""
        self.always_on_top = checked
        if checked:
            self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)
        else:
            self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowStaysOnTopHint)
        self.show()  # 重新显示窗口以应用标志
        self.save_config()
    
    def on_lock_changed(self, checked: bool):
        """锁定状态改变"""
        self.is_locked = checked
        if self.window_monitor:
            self.window_monitor.is_locked = checked
        self.update_target_display()
        
        if checked and not self.target_window:
            self.lock_checkbox.setChecked(False)
            self.is_locked = False
            QMessageBox.warning(self, "警告", "没有检测到目标窗口！")
    
    def on_dock_changed(self, checked: bool):
        """吸附状态改变"""
        self.dock_enabled = checked
        
        if checked:
            if not self.target_window:
                self.dock_checkbox.setChecked(False)
                self.dock_enabled = False
                QMessageBox.warning(self, "警告", "没有检测到目标窗口！请先选择一个窗口。")
                return
            
            # 启用吸附
            if self.dock_manager:
                self.dock_manager.enable_docking(self.target_window)
                self.status_label.setText("✅ 窗口吸附已启用")
        else:
            # 禁用吸附
            if self.dock_manager:
                self.dock_manager.disable_docking()
                self.status_label.setText("❌ 窗口吸附已禁用")
        
        self.save_config()
    
    def on_dock_position_changed(self, x: int, y: int, width: int, height: int):
        """吸附位置变化事件"""
        # 这里可以添加位置变化的处理逻辑
        pass
    
    def on_primary_tab_changed(self, index: int):
        """一级Tab切换"""
        if index >= 0:
            tab_names = list(self.scripts_data.keys())
            
            # 去掉处理"+"Tab点击的逻辑，因为话术类型是写死的，不需要添加功能
            # # 检查是否点击了"+"Tab（最后一个Tab）
            # if index == len(tab_names):
            #     # 点击了"+"Tab，触发添加一级分类
            #     self.add_primary_tab()
            #     return
            
            # 正常的Tab切换
            if index < len(tab_names):
                new_tab = tab_names[index]
                if new_tab != self.current_primary_tab:
                    self.save_scripts()
                    self.current_primary_tab = new_tab
                    self.current_secondary_tab = list(self.scripts_data[new_tab].keys())[0]
                    self.update_secondary_tabs()
                    self.load_current_scripts_data()
    
    def on_secondary_tab_changed(self, index: int):
        """二级Tab切换"""
        if index >= 0:
            tab_names = list(self.scripts_data[self.current_primary_tab].keys())
            
            print(f"二级Tab切换: index={index}, tab_names数量={len(tab_names)}, tab_names={tab_names}")  # 调试信息
            
            # 检查是否点击了"+"Tab（最后一个Tab）
            if index == len(tab_names):
                print("检测到点击了+Tab，打开添加弹窗")  # 调试信息
                # 点击了"+"Tab，打开添加弹窗并默认选择话术分类
                self.show_add_dialog_with_default_type(0)  # 0表示话术分类
                return
            
            if index < len(tab_names):
                new_tab = tab_names[index]
                print(f"切换到二级Tab: {new_tab}, 当前: {self.current_secondary_tab}")  # 调试信息
                if new_tab != self.current_secondary_tab:
                    self.save_scripts()
                    self.current_secondary_tab = new_tab
                    self.load_current_scripts_data()
            else:
                print(f"警告: 二级Tab索引超出范围 index={index}, 最大索引={len(tab_names)-1}")  # 调试信息
    
    def load_current_scripts_data(self):
        """加载当前Tab数据"""
        self.current_scripts_data = self.get_current_scripts_data()
        self.filtered_scripts = self.current_scripts_data.copy()
        print(f"🔍 当前数据结构: {self.current_scripts_data}")
        self.update_tree()
        self.search_edit.clear()
    
    def on_tree_single_click(self, item: QTreeWidgetItem, column: int):
        """树形控件单击事件"""
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if data and data.get("type") == "script":
            # 获取鼠标点击位置
            from PySide6.QtGui import QCursor
            global_pos = QCursor.pos()
            cursor_pos = self.tree_widget.mapFromGlobal(global_pos)
            item_rect = self.tree_widget.visualItemRect(item)
            
            # 计算相对于item左边的点击位置
            relative_x = cursor_pos.x() - item_rect.left()
            
            # 检查是否点击在📤图标区域
            if 0 <= relative_x <= 30:
                script_content = data.get("content", "")
                self.send_script_directly(script_content)
                return
    
    def on_tree_double_click(self, item: QTreeWidgetItem, column: int):
        """树形控件双击事件"""
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if data and data.get("type") == "script":
            script_content = data.get("content", "")
            self.send_script_text(script_content)
    
    def send_script_directly(self, script_content: str):
        """直接发送话术（不依赖发送模式设置）"""
        if not script_content.strip():
            self.status_label.setText("❌ 话术内容为空")
            return
        
        # 检查目标窗口
        if not hasattr(self, 'target_window') or not self.target_window:
            self.status_label.setText("❌ 请先选择目标窗口")
            return
            
        try:
            if self.api_manager:
                success = self.api_manager.send_text_to_window(
                    self.target_window, script_content
                )
                if success:
                    self.status_label.setText("✅ 📤 话术已直接发送")
                else:
                    self.status_label.setText("❌ 发送失败，请检查目标窗口")
            else:
                self.status_label.setText("❌ API管理器未初始化")
        except Exception as e:
            self.status_label.setText(f"❌ 发送错误: {str(e)}")
    
    def on_search_changed(self, text: str):
        """搜索文本改变"""
        search_text = text.strip().lower()
        
        if not search_text:
            self.filtered_scripts = self.current_scripts_data.copy()
        else:
            self.filtered_scripts = {}
            # 搜索所有Tab中的话术
            for primary_tab, secondary_tabs in self.scripts_data.items():
                for secondary_tab, categories in secondary_tabs.items():
                    for category, scripts in categories.items():
                        filtered_scripts = [script for script in scripts
                                          if search_text in script.lower()]
                        if filtered_scripts:
                            display_category = f"[{primary_tab}-{secondary_tab}] {category}"
                            self.filtered_scripts[display_category] = filtered_scripts
        
        self.update_tree()
    
    def clear_search(self):
        """清空搜索"""
        self.search_edit.clear()
        self.filtered_scripts = self.current_scripts_data.copy()
        self.update_tree()
    
    # 功能方法
    def send_script_text(self, script: str):
        """发送话术文本"""
        if self.send_mode == "添加到剪贴板":
            pyperclip.copy(script)
            self.status_label.setText("已复制到剪贴板")
            return
        elif self.send_mode == "添加到输入框":
            if not self.target_window:
                QMessageBox.warning(self, "警告", "没有检测到目标窗口！")
                return
            self.paste_to_input(script)
        else:  # 直接发送
            if not self.target_window:
                QMessageBox.warning(self, "警告", "没有检测到目标窗口！")
                return
            self.send_text_direct(script)
    
    def paste_to_input(self, text: str):
        """粘贴到输入框"""
        try:
            if self.target_window and not win32gui.IsWindow(self.target_window):
                self.status_label.setText("目标窗口已关闭")
                return
            
            if self.target_window:
                win32gui.ShowWindow(self.target_window, win32con.SW_RESTORE)
                win32gui.SetForegroundWindow(self.target_window)
                time.sleep(0.2)
            
            pyperclip.copy(text)
            pyautogui.hotkey('ctrl', 'v')
            self.status_label.setText("已添加到输入框")
            
        except Exception as e:
            self.status_label.setText(f"添加失败: {str(e)}")
    
    def send_text_direct(self, text: str):
        """直接发送文本"""
        try:
            if self.target_window and not win32gui.IsWindow(self.target_window):
                self.status_label.setText("目标窗口已关闭")
                return
            
            if self.target_window:
                win32gui.ShowWindow(self.target_window, win32con.SW_RESTORE)
                win32gui.SetForegroundWindow(self.target_window)
                time.sleep(0.2)
            
            pyperclip.copy(text)
            pyautogui.hotkey('ctrl', 'v')
            time.sleep(0.1)
            pyautogui.press('enter')
            self.status_label.setText("已直接发送")
            
        except Exception as e:
            self.status_label.setText(f"发送失败: {str(e)}")
    
    def add_primary_tab(self):
        """添加一级Tab"""
        from components.Input_dialog import ask_string
        
        tab_name = ask_string(self, "新增一级分类", "请输入分类名称:")
        
        if tab_name and tab_name.strip():
            tab_name = tab_name.strip()
            if tab_name not in self.scripts_data:
                self.save_scripts()
                self.scripts_data[tab_name] = {"默认": {}}
                self.current_primary_tab = tab_name
                self.current_secondary_tab = "默认"
                self.update_all_ui()
                self.save_scripts()
                self.status_label.setText(f"已添加一级分类: {tab_name}")
            else:
                QMessageBox.warning(self, "警告", "分类名称已存在！")
    
    def rename_primary_tab(self, old_name: str):
        """重命名一级Tab"""
        from components.Input_dialog import ask_string
        
        new_name = ask_string(self, "修改一级分类名称", "请输入新的分类名称:", old_name)
        
        if new_name and new_name.strip() and new_name != old_name:
            new_name = new_name.strip()
            if new_name not in self.scripts_data:
                # 重命名数据
                self.scripts_data[new_name] = self.scripts_data.pop(old_name)
                
                # 更新当前选中的Tab
                if self.current_primary_tab == old_name:
                    self.current_primary_tab = new_name
                
                self.update_all_ui()
                self.save_scripts()
                self.status_label.setText(f"已重命名一级分类: {old_name} → {new_name}")
            else:
                QMessageBox.warning(self, "警告", "分类名称已存在！")
    
    def delete_primary_tab(self, tab_name: str):
        """删除一级Tab"""
        if len(self.scripts_data) <= 1:
            QMessageBox.warning(self, "警告", "至少需要保留一个一级分类！")
            return
            
        reply = QMessageBox.question(
            self, "确认删除",
            f"确定要删除一级分类 '{tab_name}' 及其所有内容吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                del self.scripts_data[tab_name]
                
                # 如果删除的是当前选中的Tab，切换到第一个Tab
                if self.current_primary_tab == tab_name:
                    self.current_primary_tab = list(self.scripts_data.keys())[0]
                    self.current_secondary_tab = list(self.scripts_data[self.current_primary_tab].keys())[0]
                
                self.update_all_ui()
                self.save_scripts()
                self.status_label.setText(f"已删除一级分类: {tab_name}")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"删除失败: {str(e)}")
    
    def add_secondary_tab(self):
        """添加二级Tab"""
        from components.Input_dialog import ask_string
        
        tab_name = ask_string(self, "新增二级分类", f"请输入分类名称（所属: {self.current_primary_tab}）:")
        
        if tab_name and tab_name.strip():
            tab_name = tab_name.strip()
            if tab_name not in self.scripts_data[self.current_primary_tab]:
                self.scripts_data[self.current_primary_tab][tab_name] = {}
                self.current_secondary_tab = tab_name
                self.update_secondary_tabs()
                self.load_current_scripts_data()
                self.save_scripts()
                self.status_label.setText(f"已添加二级分类: {tab_name}")
            else:
                QMessageBox.warning(self, "警告", "分类名称已存在！")
    
    def show_add_dialog(self):
        """显示添加内容弹窗"""
        try:
            # 如果弹窗已经存在且可见，则将其置于前台
            if hasattr(self, 'add_dialog') and self.add_dialog and self.add_dialog.isVisible():
                self.add_dialog.raise_()
                self.add_dialog.activateWindow()
                return
            
            # 获取用户权限（这里可以根据实际需求从API或配置中获取）
            user_permissions = self.get_user_permissions()
            
            # 创建并显示添加弹窗
            self.add_dialog = AddDialog(self.scripts_data, user_permissions, self)
            
            # 连接信号
            self.add_dialog.category_added_signal.connect(self.on_category_added)
            self.add_dialog.title_added_signal.connect(self.on_title_added)
            self.add_dialog.content_added_signal.connect(self.on_content_added)
            
            # 连接弹窗关闭信号
            self.add_dialog.accepted.connect(lambda: self.status_label.setText("✅ 内容添加成功"))
            self.add_dialog.rejected.connect(lambda: self.status_label.setText("❌ 取消添加"))
            
            # 显示非模态弹窗
            self.add_dialog.show()
            self.add_dialog.raise_()
            self.add_dialog.activateWindow()
            
            # 在弹窗显示后设置默认值
            print(f"准备设置默认值: primary_tab={self.current_primary_tab}, secondary_tab={self.current_secondary_tab}")
            # 修复lambda变量作用域问题
            current_primary = self.current_primary_tab
            current_secondary = self.current_secondary_tab
            QTimer.singleShot(100, lambda: self.add_dialog.set_default_values(
                script_type=current_primary,
                category=current_secondary
            ))
                
        except Exception as e:
            QMessageBox.critical(self, "错误", f"显示添加弹窗失败：{str(e)}")
            
    def get_user_permissions(self) -> Dict[str, bool]:
        """获取用户权限"""
        # 这里可以根据实际需求从API或配置中获取用户权限
        # 目前返回默认权限，后续可以对接接口
        default_permissions = {
            'add_secondary_tab': True,
            'add_category': True,
            'add_script': True
        }
        
        # 如果有登录用户，可以根据用户角色返回不同权限
        if hasattr(self, 'current_user') and self.current_user:
            user_role = getattr(self.current_user, 'role', 'user')
            if user_role == 'admin':
                return {
                    'add_secondary_tab': True,
                    'add_category': True,
                    'add_script': True
                }
            elif user_role == 'manager':
                return {
                    'add_secondary_tab': False,
                    'add_category': True,
                    'add_script': True
                }
            else:  # regular user
                return {
                    'add_secondary_tab': False,
                    'add_category': False,
                    'add_script': True
                }
        
        return default_permissions
        
    def show_add_dialog_with_default_type(self, default_type: int):
        """显示添加内容弹窗并设置默认类型"""
        try:
            print(f"🔍 show_add_dialog_with_default_type 被调用，default_type={default_type}")
            
            # 如果弹窗已经存在且可见，则将其置于前台
            if hasattr(self, 'add_dialog') and self.add_dialog and self.add_dialog.isVisible():
                self.add_dialog.raise_()
                self.add_dialog.activateWindow()
                return
            
            # 获取用户权限
            user_permissions = self.get_user_permissions()
            
            # 创建并显示添加弹窗
            self.add_dialog = AddDialog(self.scripts_data, user_permissions, self)
            
            # 设置默认类型
            self.add_dialog.set_default_type(default_type)
            
            # 连接信号
            self.add_dialog.category_added_signal.connect(self.on_category_added)
            self.add_dialog.title_added_signal.connect(self.on_title_added)
            self.add_dialog.content_added_signal.connect(self.on_content_added)
            
            # 连接弹窗关闭信号
            self.add_dialog.accepted.connect(lambda: self.status_label.setText("✅ 内容添加成功"))
            self.add_dialog.rejected.connect(lambda: self.status_label.setText("❌ 取消添加"))
            
            # 显示非模态弹窗
            self.add_dialog.show()
            self.add_dialog.raise_()
            self.add_dialog.activateWindow()
            
            # 在弹窗显示后设置默认值
            print(f"🔍 准备设置默认值: primary_tab={self.current_primary_tab}, secondary_tab={self.current_secondary_tab}")
            # 修复lambda变量作用域问题
            current_primary = self.current_primary_tab
            current_secondary = self.current_secondary_tab
            
            # 直接调用而不使用QTimer
            self.add_dialog.set_default_values(
                script_type=current_primary,
                category=current_secondary
            )
                
        except Exception as e:
            QMessageBox.critical(self, "错误", f"显示添加弹窗失败：{str(e)}")
        
    def on_category_added(self, script_type_name: str, category_name: str):
        """处理添加话术分类"""
        try:
            if script_type_name not in self.scripts_data:
                QMessageBox.warning(self, "错误", f"话术类型 '{script_type_name}' 不存在！")
                return
                
            if category_name in self.scripts_data[script_type_name]:
                QMessageBox.warning(self, "警告", f"话术分类 '{category_name}' 已存在！")
                return
                
            # 添加新的话术分类（正确初始化为空字典）
            self.scripts_data[script_type_name][category_name] = {}
            
            # 切换到新添加的分类
            self.current_primary_tab = script_type_name
            self.current_secondary_tab = category_name
            
            # 更新当前数据
            self.current_scripts_data = self.get_current_scripts_data()
            self.filtered_scripts = self.current_scripts_data.copy()
            
            # 保存并更新界面（保持在新添加的位置）
            self.save_scripts()
            self.update_secondary_tabs()  # 只更新二级Tab，保持一级Tab位置
            self.update_tree()
            
            self.status_label.setText(f"✅ 已添加话术分类: {category_name}")
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"添加话术分类失败：{str(e)}")
            
    def on_title_added(self, script_type_name: str, category_name: str, title_name: str):
        """处理添加话术标题"""
        try:
            if script_type_name not in self.scripts_data:
                QMessageBox.warning(self, "错误", f"话术类型 '{script_type_name}' 不存在！")
                return
                
            if category_name not in self.scripts_data[script_type_name]:
                QMessageBox.warning(self, "错误", f"话术分类 '{category_name}' 不存在！")
                return
                
            if title_name in self.scripts_data[script_type_name][category_name]:
                QMessageBox.warning(self, "警告", f"话术标题 '{title_name}' 已存在！")
                return
                
            # 添加新的话术标题（初始化为空列表）
            self.scripts_data[script_type_name][category_name][title_name] = []
            
            # 切换到对应的菜单
            self.current_primary_tab = script_type_name
            self.current_secondary_tab = category_name
            
            # 更新当前数据
            self.current_scripts_data = self.get_current_scripts_data()
            self.filtered_scripts = self.current_scripts_data.copy()
            
            # 保存并更新界面（保持在对应的位置）
            self.save_scripts()
            # 确保Tab保持在正确位置
            self.update_primary_tabs()
            self.update_secondary_tabs()
            self.update_tree()
            
            self.status_label.setText(f"✅ 已添加话术标题: {title_name}")
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"添加话术标题失败：{str(e)}")
            
    def on_content_added(self, script_type_name: str, category_name: str, title_name: str, content: str):
        """处理添加话术内容"""
        try:
            if script_type_name not in self.scripts_data:
                QMessageBox.warning(self, "错误", f"话术类型 '{script_type_name}' 不存在！")
                return
                
            if category_name not in self.scripts_data[script_type_name]:
                QMessageBox.warning(self, "错误", f"话术分类 '{category_name}' 不存在！")
                return
                
            if title_name not in self.scripts_data[script_type_name][category_name]:
                QMessageBox.warning(self, "错误", f"话术标题 '{title_name}' 不存在！")
                return
                
            # 添加新的话术内容
            self.scripts_data[script_type_name][category_name][title_name].append(content)
            
            # 保存当前用户的Tab位置
            current_primary = self.current_primary_tab
            current_secondary = self.current_secondary_tab
            
            # 保存数据
            self.save_scripts()
            
            # 只有当添加的内容在当前显示的Tab中时，才更新界面
            if current_primary == script_type_name and current_secondary == category_name:
                # 更新当前数据
                self.current_scripts_data = self.get_current_scripts_data()
                self.filtered_scripts = self.current_scripts_data.copy()
                # 只更新树形列表，不更新Tab
                self.update_tree()
            
            self.status_label.setText(f"✅ 已添加话术内容到: {title_name}")
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"添加话术内容失败：{str(e)}")

    def add_category(self):
        """添加话术分类"""
        from components.Input_dialog import ask_string
        
        category = ask_string(self, "添加分类", "请输入分类名称:")
        
        if category and category.strip():
            category = category.strip()
            if category not in self.current_scripts_data:
                self.current_scripts_data[category] = []
                self.save_scripts()
                self.filtered_scripts = self.current_scripts_data.copy()
                self.update_tree()
                self.status_label.setText(f"已添加分类: {category}")
            else:
                QMessageBox.warning(self, "警告", "分类已存在！")
    
    def show_tree_context_menu(self, position):
        """显示树形控件右键菜单"""
        item = self.tree_widget.itemAt(position)
        
        print(f"🔍 右键菜单被触发，position: {position}")
        print(f"🔍 点击的item: {item}")
        
        menu = QMenu(self)
        
        if not item:
            # 点击空白区域的菜单
            print("🔍 点击的是空白区域")
            add_title_action = QAction("添加话术标题", self)
            add_title_action.triggered.connect(lambda: self.show_add_dialog_with_default_type(1))  # 1表示添加话术标题
            menu.addAction(add_title_action)
            menu.exec(self.tree_widget.mapToGlobal(position))
            return
        
        data = item.data(0, Qt.ItemDataRole.UserRole)
        print(f"🔍 item的数据: {data}")
        print(f"🔍 数据类型: {data.get('type') if data else 'None'}")
        
        if not data:
            print("🔍 item没有数据，返回")
            return
        
        if data.get("type") == "category":
            # 分类节点菜单
            add_script_action = QAction("添加话术", self)
            add_script_action.triggered.connect(lambda: self.show_add_dialog_with_default_type(2))  # 2表示添加话术内容
            menu.addAction(add_script_action)
            
            menu.addSeparator()
            
            edit_action = QAction("编辑分类", self)
            category_name = data.get("name")
            edit_action.triggered.connect(lambda checked, name=category_name: self.edit_category(name))
            menu.addAction(edit_action)
            
            delete_action = QAction("删除分类", self)
            delete_action.triggered.connect(lambda checked, name=category_name: self.delete_category(name))
            menu.addAction(delete_action)
            
        elif data.get("type") == "title":
            # 话术标题节点菜单
            add_script_action = QAction("添加话术内容", self)
            # 修复lambda作用域问题
            title_data_copy = data.copy()
            add_script_action.triggered.connect(lambda checked, d=title_data_copy: self.show_add_dialog_with_title_default(d))
            menu.addAction(add_script_action)
            
            menu.addSeparator()
            
            edit_action = QAction("编辑标题", self)
            edit_action.triggered.connect(lambda checked, d=data.copy(): self.edit_title(d))
            menu.addAction(edit_action)
            
            delete_action = QAction("删除标题", self)
            delete_action.triggered.connect(lambda checked, d=data.copy(): self.delete_title(d))
            menu.addAction(delete_action)
            
        elif data.get("type") == "script":
            # 话术节点菜单
            edit_action = QAction("编辑话术", self)
            script_data_copy = data.copy()
            edit_action.triggered.connect(lambda checked, d=script_data_copy: self.edit_script(d))
            menu.addAction(edit_action)
            
            delete_action = QAction("删除话术", self)
            delete_action.triggered.connect(lambda checked, d=script_data_copy: self.delete_script(d))
            menu.addAction(delete_action)
        
        menu.exec(self.tree_widget.mapToGlobal(position))
    
    def show_primary_tab_context_menu(self, position):
        """显示一级Tab右键菜单"""
        print(f"右键菜单被触发，位置: {position}")  # 调试信息
        
        # 获取点击的Tab索引
        tab_index = self.primary_tab_widget.tabBar().tabAt(position)
        print(f"Tab索引: {tab_index}")  # 调试信息
        
        if tab_index < 0:
            print("无效的Tab索引")
            return
            
        tab_names = list(self.scripts_data.keys())
        print(f"Tab名称列表: {tab_names}")  # 调试信息
        
        # 如果点击的是"+"Tab，不显示右键菜单
        if tab_index >= len(tab_names):
            print("点击的是+Tab，不显示菜单")
            return
            
        tab_name = tab_names[tab_index]
        print(f"选中的Tab名称: {tab_name}")  # 调试信息
        
        try:
            menu = QMenu(self)
            
            rename_action = QAction("修改名称", self)
            rename_action.triggered.connect(lambda: self.rename_primary_tab(tab_name))
            menu.addAction(rename_action)
            
            delete_action = QAction("删除分类", self)
            delete_action.triggered.connect(lambda: self.delete_primary_tab(tab_name))
            menu.addAction(delete_action)
            
            # 在Tab栏上显示菜单
            global_pos = self.primary_tab_widget.tabBar().mapToGlobal(position)
            print(f"菜单显示位置: {global_pos}")  # 调试信息
            menu.exec(global_pos)
            
        except Exception as e:
            print(f"右键菜单错误: {e}")
    
    def show_secondary_tab_context_menu(self, position):
        """显示二级Tab右键菜单"""
        print(f"二级Tab右键菜单被触发，位置: {position}")  # 调试信息
        
        # 获取点击的Tab索引
        tab_index = self.secondary_tab_widget.tabBar().tabAt(position)
        print(f"二级Tab索引: {tab_index}")  # 调试信息
        
        if tab_index < 0:
            print("无效的二级Tab索引")
            return
            
        tab_names = list(self.scripts_data[self.current_primary_tab].keys())
        print(f"二级Tab名称列表: {tab_names}")  # 调试信息
        
        if tab_index >= len(tab_names):
            print("点击的是无效Tab，不显示菜单")
            return
            
        tab_name = tab_names[tab_index]
        print(f"选中的二级Tab名称: {tab_name}")  # 调试信息
        
        try:
            menu = QMenu(self)
            
            rename_action = QAction("修改名称", self)
            rename_action.triggered.connect(lambda: self.rename_secondary_tab(tab_name))
            menu.addAction(rename_action)
            
            delete_action = QAction("删除分类", self)
            delete_action.triggered.connect(lambda: self.delete_secondary_tab(tab_name))
            menu.addAction(delete_action)
            
            # 在Tab栏上显示菜单
            global_pos = self.secondary_tab_widget.tabBar().mapToGlobal(position)
            print(f"二级Tab菜单显示位置: {global_pos}")  # 调试信息
            menu.exec(global_pos)
            
        except Exception as e:
            print(f"二级Tab右键菜单错误: {e}")
    
    def add_script_to_category(self, category: str):
        """向分类添加话术"""
        from components.Input_dialog import ask_string
        
        script = ask_string(self, "添加话术", f"请输入话术内容（分类: {category}）:", "", True)
        
        if script and script.strip():
            if category not in self.current_scripts_data:
                self.current_scripts_data[category] = []
            
            self.current_scripts_data[category].append(script.strip())
            self.save_scripts()
            self.filtered_scripts = self.current_scripts_data.copy()
            self.update_tree()
            self.status_label.setText(f"已添加话术到 {category}")
    
    def edit_category(self, old_name: str):
        """编辑分类名称"""
        from components.Input_dialog import ask_string
        
        new_name = ask_string(self, "编辑分类", "请修改分类名称:", old_name)
        
        if new_name and new_name.strip() and new_name != old_name:
            new_name = new_name.strip()
            if new_name not in self.current_scripts_data:
                self.current_scripts_data[new_name] = self.current_scripts_data.pop(old_name)
                self.save_scripts()
                self.filtered_scripts = self.current_scripts_data.copy()
                self.update_tree()
                self.status_label.setText(f"分类已重命名: {old_name} → {new_name}")
            else:
                QMessageBox.warning(self, "警告", "分类名称已存在！")
    
    def delete_category(self, category: str):
        """删除分类"""
        reply = QMessageBox.question(
            self, "确认删除", 
            f"确定要删除分类 '{category}' 及其所有话术吗？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            if category in self.current_scripts_data:
                del self.current_scripts_data[category]
                self.save_scripts()
                self.filtered_scripts = self.current_scripts_data.copy()
                self.update_tree()
                self.status_label.setText(f"已删除分类: {category}")
    
    def edit_script(self, data: Dict[str, Any]):
        """编辑话术"""
        from components.Input_dialog import ask_string
        
        old_script = data.get("content", "")
        category = data.get("category", "")
        
        new_script = ask_string(self, "编辑话术", "请修改话术内容:", old_script, True)
        
        if new_script and new_script.strip():
            try:
                index = self.current_scripts_data[category].index(old_script)
                self.current_scripts_data[category][index] = new_script.strip()
                self.save_scripts()
                self.filtered_scripts = self.current_scripts_data.copy()
                self.update_tree()
                self.status_label.setText("话术已更新")
            except (ValueError, KeyError):
                QMessageBox.warning(self, "错误", "找不到要编辑的话术！")
    
    def show_add_dialog_with_title_default(self, title_data: Dict[str, Any]):
        """显示添加弹窗并设置话术标题默认值"""
        try:
            print(f"🔍 show_add_dialog_with_title_default 被调用")
            print(f"🔍 接收到的 title_data: {title_data}")
            print(f"🔍 title_data 类型: {type(title_data)}")
            
            # 如果弹窗已经存在且可见，则将其置于前台
            if hasattr(self, 'add_dialog') and self.add_dialog and self.add_dialog.isVisible():
                self.add_dialog.raise_()
                self.add_dialog.activateWindow()
                return
            
            # 获取用户权限
            user_permissions = self.get_user_permissions()
            
            # 创建并显示添加弹窗
            self.add_dialog = AddDialog(self.scripts_data, user_permissions, self)
            
            # 设置默认类型为添加话术内容
            self.add_dialog.set_default_type(2)
            
            # 连接信号
            self.add_dialog.category_added_signal.connect(self.on_category_added)
            self.add_dialog.title_added_signal.connect(self.on_title_added)
            self.add_dialog.content_added_signal.connect(self.on_content_added)
            
            # 连接弹窗关闭信号
            self.add_dialog.accepted.connect(lambda: self.status_label.setText("✅ 内容添加成功"))
            self.add_dialog.rejected.connect(lambda: self.status_label.setText("❌ 取消添加"))
            
            # 显示非模态弹窗
            self.add_dialog.show()
            self.add_dialog.raise_()
            self.add_dialog.activateWindow()
            
            # 在弹窗显示后设置默认值，包括话术标题
            print(f"🔍 话术标题数据: {title_data}")
            print(f"🔍 当前一级Tab: {self.current_primary_tab}")
            print(f"🔍 当前二级Tab: {self.current_secondary_tab}")
            
            # 提取标题名称和分类名称
            title_name = title_data.get("name", "") if title_data else ""
            category_name = title_data.get("category", "") if title_data else ""
            
            print(f"🔍 提取的标题名称: '{title_name}'")
            print(f"🔍 提取的分类名称: '{category_name}'")
            
            # 使用当前Tab信息作为默认值
            current_primary = self.current_primary_tab
            # 如果title_data中有category信息，使用它；否则使用当前二级Tab
            current_secondary = category_name if category_name else self.current_secondary_tab
            
            print(f"🔍 准备设置默认值: script_type={current_primary}, category={current_secondary}, title={title_name}")
            
            # 直接调用而不使用QTimer，避免时序问题
            self.add_dialog.set_default_values(
                script_type=current_primary,
                category=current_secondary,
                title=title_name
            )
                
        except Exception as e:
            QMessageBox.critical(self, "错误", f"显示添加弹窗失败：{str(e)}")
    
    def edit_title(self, data: Dict[str, Any]):
        """编辑话术标题"""
        from components.Input_dialog import ask_string
        
        old_title = data.get("name", "")
        category = data.get("category", "")
        
        new_title = ask_string(self, "编辑话术标题", "请修改话术标题:", old_title)
        
        if new_title and new_title.strip() and new_title != old_title:
            try:
                new_title = new_title.strip()
                # 检查新标题是否已存在
                if new_title in self.current_scripts_data.get(category, {}):
                    QMessageBox.warning(self, "警告", "话术标题已存在！")
                    return
                
                # 重命名标题
                if category in self.current_scripts_data and old_title in self.current_scripts_data[category]:
                    self.current_scripts_data[category][new_title] = self.current_scripts_data[category].pop(old_title)
                    self.save_scripts()
                    self.filtered_scripts = self.current_scripts_data.copy()
                    self.update_tree()
                    self.status_label.setText(f"话术标题已重命名: {old_title} → {new_title}")
                else:
                    QMessageBox.warning(self, "错误", "找不到要编辑的话术标题！")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"编辑话术标题失败: {str(e)}")
    
    def delete_title(self, data: Dict[str, Any]):
        """删除话术标题"""
        title = data.get("name", "")
        category = data.get("category", "")
        
        reply = QMessageBox.question(
            self, "确认删除",
            f"确定要删除话术标题 '{title}' 及其所有内容吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                if category in self.current_scripts_data and title in self.current_scripts_data[category]:
                    del self.current_scripts_data[category][title]
                    self.save_scripts()
                    self.filtered_scripts = self.current_scripts_data.copy()
                    self.update_tree()
                    self.status_label.setText(f"话术标题已删除: {title}")
                else:
                    QMessageBox.warning(self, "错误", "找不到要删除的话术标题！")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"删除话术标题失败: {str(e)}")

    def delete_script(self, data: Dict[str, Any]):
        """删除话术"""
        script = data.get("content", "")
        category = data.get("category", "")
        
        reply = QMessageBox.question(
            self, "确认删除",
            f"确定要删除话术:\n{script[:100]}{'...' if len(script) > 100 else ''}",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                self.current_scripts_data[category].remove(script)
                self.save_scripts()
                self.filtered_scripts = self.current_scripts_data.copy()
                self.update_tree()
                self.status_label.setText("话术已删除")
            except (ValueError, KeyError):
                QMessageBox.warning(self, "错误", "找不到要删除的话术！")
    
    def rename_secondary_tab(self, old_name: str):
        """重命名二级Tab"""
        from components.Input_dialog import ask_string
        
        new_name = ask_string(self, "修改名称", "请输入新的分类名称:", old_name)
        
        if new_name and new_name.strip() and new_name != old_name:
            new_name = new_name.strip()
            if new_name not in self.scripts_data[self.current_primary_tab]:
                self.scripts_data[self.current_primary_tab][new_name] = \
                    self.scripts_data[self.current_primary_tab].pop(old_name)
                
                if self.current_secondary_tab == old_name:
                    self.current_secondary_tab = new_name
                
                self.update_secondary_tabs()
                self.save_scripts()
                self.status_label.setText(f"已重命名: {old_name} → {new_name}")
            else:
                QMessageBox.warning(self, "警告", "分类名称已存在！")
    
    def delete_secondary_tab(self, tab_name: str):
        """删除二级Tab"""
        if len(self.scripts_data[self.current_primary_tab]) <= 1:
            QMessageBox.warning(self, "警告", "至少需要保留一个二级分类！")
            return
        
        reply = QMessageBox.question(
            self, "确认删除",
            f"确定要删除二级分类 '{tab_name}' 及其所有话术吗？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                if tab_name in self.scripts_data[self.current_primary_tab]:
                    del self.scripts_data[self.current_primary_tab][tab_name]
                
                if self.current_secondary_tab == tab_name:
                    if self.scripts_data[self.current_primary_tab]:
                        self.current_secondary_tab = list(self.scripts_data[self.current_primary_tab].keys())[0]
                        self.load_current_scripts_data()
                
                self.update_secondary_tabs()
                self.save_scripts()
                self.status_label.setText(f"已删除二级分类: {tab_name}")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"删除失败: {str(e)}")
    
    def show_login_dialog(self):
        """显示登录对话框"""
        if self.is_logged_in:
            reply = QMessageBox.question(
                self, "登出确认",
                f"当前用户: {self.current_user_id}\n确定要登出吗？",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                self.logout_user()
            return
        
        # 显示登录对话框
        from components.Login_dialog import show_login_dialog
        result = show_login_dialog(self, self._handle_login)
    
    def _handle_login(self, username: str, password: str) -> bool:
        """处理登录逻辑"""
        try:
            if not self.api_manager:
                QMessageBox.critical(self, "登录失败", "API服务不可用")
                return False
            
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
                
                QMessageBox.information(self, "登录成功", f"欢迎回来，{username}！")
                return True
            else:
                QMessageBox.critical(self, "登录失败", result.get('message', '用户名或密码错误'))
                return False
        except Exception as e:
            QMessageBox.critical(self, "登录失败", f"登录时发生错误: {str(e)}")
            return False
    
    def logout_user(self):
        """用户登出"""
        try:
            if self.api_manager:
                self.api_manager.logout()
            
            self.current_user_id = None
            self.is_logged_in = False
            
            # 重新初始化数据适配器
            self.data_adapter = DataAdapter(
                api_manager=self.api_manager,
                script_file=self.script_file,
                config_file=self.config_file,
                user_id=0
            )
            
            # 重新加载数据
            self.load_data_from_adapter()
            self.update_all_ui()
            self.update_login_status()
            
            # 保存配置
            self.save_config()
            
            self.status_label.setText("已登出")
        except Exception as e:
            QMessageBox.critical(self, "登出失败", f"登出时发生错误: {str(e)}")
    
    def sync_cloud_data(self):
        """同步云端数据"""
        try:
            if not self.is_logged_in or not self.current_user_id:
                return False
            
            if self.data_adapter:
                if self.data_adapter:
                    self.data_adapter.api_manager = self.api_manager
                    self.data_adapter.user_id = self.current_user_id or 0
                
                success = self.data_adapter.load_user_data()
                if success:
                    self.load_data_from_adapter()
                    self.update_all_ui()
                    self.status_label.setText("云端数据同步成功")
                    return True
                else:
                    self.status_label.setText("使用默认数据")
                    return False
        except Exception as e:
            print(f"同步云端数据失败: {e}")
            self.status_label.setText("数据同步失败，使用本地数据")
            return False
    
    def show_settings_menu(self):
        """显示设置菜单（整合了原菜单栏功能）"""
        menu = QMenu(self)
        
        # 发送模式子菜单
        send_mode_menu = menu.addMenu("发送模式")
        
        modes = ["直接发送", "添加到输入框", "添加到剪贴板"]
        for mode in modes:
            action = QAction(mode, self)
            action.setCheckable(True)
            action.setChecked(mode == self.send_mode)
            action.triggered.connect(lambda checked, m=mode: self.set_send_mode(m))
            send_mode_menu.addAction(action)
        
        menu.addSeparator()
        
        # 文件管理
        import_action = QAction("导入数据", self)
        import_action.triggered.connect(self.import_data)
        menu.addAction(import_action)
        
        export_action = QAction("导出数据", self)
        export_action.triggered.connect(self.export_data)
        menu.addAction(export_action)
        
        # 云端数据管理
        if self.is_logged_in:
            menu.addSeparator()
            
            upload_action = QAction("上传数据", self)
            upload_action.triggered.connect(self.upload_data_to_cloud)
            menu.addAction(upload_action)
            
            download_action = QAction("拉取数据", self)
            download_action.triggered.connect(self.download_data_from_cloud)
            menu.addAction(download_action)
        
        menu.addSeparator()
        
        # 帮助
        about_action = QAction("关于", self)
        about_action.triggered.connect(self.show_about)
        menu.addAction(about_action)
        
        menu.addSeparator()
        
        # 退出
        exit_action = QAction("退出", self)
        exit_action.triggered.connect(self.close)
        menu.addAction(exit_action)
        
        # 显示菜单
        menu.exec(self.sender().mapToGlobal(QPoint(0, self.sender().height())))
    
    def set_send_mode(self, mode: str):
        """设置发送模式"""
        self.send_mode = mode
        self.save_config()
        self.update_tip_text()
        self.status_label.setText(f"发送模式: {mode}")
    
    def import_data(self):
        """导入数据"""
        from PySide6.QtWidgets import QFileDialog
        
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择要导入的文件", "",
            "Excel文件 (*.xlsx *.xls);;CSV文件 (*.csv);;JSON文件 (*.json);;所有文件 (*.*)"
        )
        
        if file_path and self.data_adapter:
            try:
                success = self.data_adapter.import_data_from_file(file_path)
                if success:
                    self.load_data_from_adapter()
                    self.update_all_ui()
                    QMessageBox.information(self, "导入成功", "数据导入成功！")
                else:
                    QMessageBox.critical(self, "导入失败", "数据导入失败，请检查文件格式！")
            except Exception as e:
                QMessageBox.critical(self, "导入失败", f"导入时发生错误: {str(e)}")
    
    def export_data(self):
        """导出数据"""
        from PySide6.QtWidgets import QFileDialog
        
        file_path, selected_filter = QFileDialog.getSaveFileName(
            self, "选择导出位置", "",
            "Excel文件 (*.xlsx);;CSV文件 (*.csv);;JSON文件 (*.json)"
        )
        
        if file_path and self.data_adapter:
            try:
                # 根据选择的过滤器确定格式
                if "Excel" in selected_filter:
                    file_format = "excel"
                elif "CSV" in selected_filter:
                    file_format = "csv"
                else:
                    file_format = "json"
                
                success = self.data_adapter.export_data_to_file(file_path, file_format)
                if success:
                    QMessageBox.information(self, "导出成功", f"数据已导出到: {file_path}")
                else:
                    QMessageBox.critical(self, "导出失败", "数据导出失败！")
            except Exception as e:
                QMessageBox.critical(self, "导出失败", f"导出时发生错误: {str(e)}")
    
    def upload_data_to_cloud(self):
        """上传数据到云端"""
        try:
            if not self.is_logged_in or not self.current_user_id:
                QMessageBox.warning(self, "警告", "请先登录后再上传数据！")
                return
            
            if not self.api_manager:
                QMessageBox.critical(self, "错误", "API服务不可用")
                return
            
            reply = QMessageBox.question(
                self, "确认上传",
                "确定要将本地数据上传到云端吗？\n这将覆盖云端的现有数据。",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                self.data_adapter.api_manager = self.api_manager
                self.data_adapter.user_id = self.current_user_id
                
                success = self.data_adapter.push_local_scripts_data(data=self.scripts_data)
                if success:
                    QMessageBox.information(self, "上传成功", "数据已成功上传到云端！")
                    self.status_label.setText("数据上传成功")
                else:
                    QMessageBox.critical(self, "上传失败", "数据上传失败，请稍后重试")
                    self.status_label.setText("数据上传失败")
        except Exception as e:
            QMessageBox.critical(self, "上传失败", f"上传时发生错误: {str(e)}")
            self.status_label.setText(f"上传失败: {str(e)}")
    
    def download_data_from_cloud(self):
        """从云端下载数据"""
        try:
            if not self.is_logged_in or not self.current_user_id:
                QMessageBox.warning(self, "警告", "请先登录后再下载数据！")
                return
            
            if not self.api_manager:
                QMessageBox.critical(self, "错误", "API服务不可用")
                return
            
            reply = QMessageBox.question(
                self, "确认下载",
                "确定要从云端下载数据吗？\n这将覆盖本地的现有数据。",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                success = self.data_adapter.load_user_data()
                if success:
                    self.load_data_from_adapter()
                    self.update_all_ui()
                    QMessageBox.information(self, "下载成功", "数据已成功从云端下载！")
                    self.status_label.setText("数据下载成功")
                else:
                    QMessageBox.warning(self, "下载失败", "云端暂无数据或下载失败")
                    self.status_label.setText("云端暂无数据")
        except Exception as e:
            QMessageBox.critical(self, "下载失败", f"下载时发生错误: {str(e)}")
            self.status_label.setText(f"下载失败: {str(e)}")
    
    def on_dock_changed(self, checked: bool):
        """吸附状态改变"""
        self.dock_enabled = checked
        
        if checked:
            if not self.target_window:
                self.dock_checkbox.setChecked(False)
                self.dock_enabled = False
                QMessageBox.warning(self, "警告", "没有检测到目标窗口！请先选择一个窗口。")
                return
            
            # 启用吸附
            if self.dock_manager:
                self.dock_manager.enable_docking(self.target_window)
                self.status_label.setText("✅ 窗口吸附已启用")
        else:
            # 禁用吸附
            if self.dock_manager:
                self.dock_manager.disable_docking()
                self.status_label.setText("❌ 窗口吸附已禁用")
        
        self.save_config()
    
    def on_dock_position_changed(self, x: int, y: int, width: int, height: int):
        """吸附位置变化事件"""
        # 这里可以添加位置变化的处理逻辑
        pass
    
    def on_lock_changed(self, checked: bool):
        """锁定状态改变"""
        self.position_locked = checked
        self.save_config()
        if checked:
            self.status_label.setText("🔒 位置已锁定")
        else:
            self.status_label.setText("🔓 位置已解锁")
    
    def on_topmost_changed(self, checked: bool):
        """置顶状态改变"""
        self.always_on_top = checked
        
        # 更新窗口标志
        if checked:
            self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)
        else:
            self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowStaysOnTopHint)
        
        # 重新显示窗口以应用新的标志
        self.show()
        self.save_config()
        
        if checked:
            self.status_label.setText("⬆ 窗口置顶已启用")
        else:
            self.status_label.setText("⬇ 窗口置顶已禁用")
    
    def init_dock_manager(self):
        """初始化吸附管理器"""
        self.dock_manager = WindowDockManager(self)
        self.dock_manager.dock_position_changed.connect(self.on_dock_position_changed)

    def show_about(self):
        """显示关于对话框"""
        QMessageBox.about(
            self, "关于聚雍宝",
            """
            <h3>聚雍宝 - 智能客服助手</h3>
            <p>版本: 2.0 (PySide6版)</p>
            <p>一个功能强大的客服话术管理和自动发送工具</p>
            <p><b>主要功能:</b></p>
            <ul>
            <li>话术分类管理</li>
            <li>智能窗口检测</li>
            <li>多种发送模式</li>
            <li>云端数据同步</li>
            <li>数据导入导出</li>
            <li>窗口吸附功能</li>
            </ul>
            <p>© 2024 聚雍宝团队</p>
            """
        )
    
    def save_scripts(self):
        """保存话术数据"""
        try:
            if hasattr(self, 'scripts_data') and self.data_adapter:
                self.scripts_data[self.current_primary_tab][self.current_secondary_tab] = self.current_scripts_data
                self.data_adapter.scripts_data = self.scripts_data
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
                'is_logged_in': self.is_logged_in,
                'dock_enabled': getattr(self, 'dock_enabled', False),
                'dock_gap': getattr(self, 'dock_gap', 1)
            }
            if self.data_adapter:
                self.data_adapter.save_local_config_data(config)
        except Exception as e:
            print(f'保存配置失败: {e}')
    
    def get_resize_direction(self, pos):
        """获取鼠标位置对应的调整大小方向"""
        rect = self.rect()
        margin = self.resize_margin
        
        # 检查是否在边缘区域
        left = pos.x() <= margin
        right = pos.x() >= rect.width() - margin
        top = pos.y() <= margin
        bottom = pos.y() >= rect.height() - margin
        
        # 调试信息
        # print(f"鼠标位置: {pos.x()}, {pos.y()}, 窗口大小: {rect.width()}x{rect.height()}")
        # print(f"边缘检测: left={left}, right={right}, top={top}, bottom={bottom}")
        
        if top and left:
            return "top_left"
        elif top and right:
            return "top_right"
        elif bottom and left:
            return "bottom_left"
        elif bottom and right:
            return "bottom_right"
        elif top:
            return "top"
        elif bottom:
            return "bottom"
        elif left:
            return "left"
        elif right:
            return "right"
        else:
            return None
    
    def update_cursor(self, direction):
        """根据调整大小方向更新鼠标光标"""
        from PySide6.QtCore import Qt
        
        cursor_map = {
            "top_left": Qt.CursorShape.SizeFDiagCursor,
            "top_right": Qt.CursorShape.SizeBDiagCursor,
            "bottom_left": Qt.CursorShape.SizeBDiagCursor,
            "bottom_right": Qt.CursorShape.SizeFDiagCursor,
            "top": Qt.CursorShape.SizeVerCursor,
            "bottom": Qt.CursorShape.SizeVerCursor,
            "left": Qt.CursorShape.SizeHorCursor,
            "right": Qt.CursorShape.SizeHorCursor,
        }
        
        if direction in cursor_map:
            self.setCursor(cursor_map[direction])
        else:
            self.setCursor(Qt.CursorShape.ArrowCursor)
    
    def enterEvent(self, event):
        """鼠标进入窗口事件"""
        super().enterEvent(event)
    
    def leaveEvent(self, event):
        """鼠标离开窗口事件"""
        self.setCursor(Qt.CursorShape.ArrowCursor)
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        """鼠标按下事件 - 用于拖拽窗口或调整大小"""
        if event.button() == Qt.MouseButton.LeftButton:
            pos = event.position().toPoint()
            self.resize_direction = self.get_resize_direction(pos)
            
            if self.resize_direction:
                # 开始调整大小
                self.resize_start_pos = event.globalPosition().toPoint()
                self.resize_start_geometry = self.geometry()
            else:
                # 开始拖拽窗口
                self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            
            event.accept()

    def mouseMoveEvent(self, event):
        """鼠标移动事件 - 拖拽窗口或调整大小"""
        if event.buttons() == Qt.MouseButton.LeftButton:
            if self.resize_direction:
                # 调整窗口大小
                self.resize_window(event.globalPosition().toPoint())
            elif self.drag_position:
                # 拖拽窗口
                # 如果启用了吸附功能，暂时禁用它
                if hasattr(self, 'dock_manager') and self.dock_manager and hasattr(self, 'dock_enabled') and self.dock_enabled:
                    self.dock_manager.disable_docking()
                    
                self.move(event.globalPosition().toPoint() - self.drag_position)
            event.accept()
        else:
            # 更新鼠标光标
            pos = event.position().toPoint()
            direction = self.get_resize_direction(pos)
            self.update_cursor(direction)
            event.accept()
        
        # 调用父类方法
        super().mouseMoveEvent(event)
    
    def resize_window(self, global_pos):
        """调整窗口大小"""
        if not hasattr(self, 'resize_start_pos') or not hasattr(self, 'resize_start_geometry') or not self.resize_direction:
            return
            
        delta = global_pos - self.resize_start_pos
        new_geometry = QRect(self.resize_start_geometry)
        
        if self.resize_direction and "left" in self.resize_direction:
            new_geometry.setLeft(new_geometry.left() + delta.x())
        if self.resize_direction and "right" in self.resize_direction:
            new_geometry.setRight(new_geometry.right() + delta.x())
        if self.resize_direction and "top" in self.resize_direction:
            new_geometry.setTop(new_geometry.top() + delta.y())
        if self.resize_direction and "bottom" in self.resize_direction:
            new_geometry.setBottom(new_geometry.bottom() + delta.y())
        
        # 确保窗口不会太小
        min_width = self.minimumWidth() or 300
        min_height = self.minimumHeight() or 400
        
        if new_geometry.width() < min_width:
            if self.resize_direction and "left" in self.resize_direction:
                new_geometry.setLeft(new_geometry.right() - min_width)
            else:
                new_geometry.setRight(new_geometry.left() + min_width)
                
        if new_geometry.height() < min_height:
            if self.resize_direction and "top" in self.resize_direction:
                new_geometry.setTop(new_geometry.bottom() - min_height)
            else:
                new_geometry.setBottom(new_geometry.top() + min_height)
        
        self.setGeometry(new_geometry)

    def mouseReleaseEvent(self, event):
        """鼠标释放事件"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_position = None
            self.resize_direction = None
            
            # 重置光标
            self.setCursor(Qt.CursorShape.ArrowCursor)
            
            # 如果之前启用了吸附功能，重新启用它
            if hasattr(self, 'dock_manager') and self.dock_manager and hasattr(self, 'dock_enabled') and self.dock_enabled:
                if hasattr(self, 'target_window') and self.target_window:
                    self.dock_manager.enable_docking(self.target_window)
            
            event.accept()

    def closeEvent(self, event):
        """窗口关闭事件"""
        # 停止监控线程
        if self.window_monitor:
            self.window_monitor.stop_monitoring()
        
        # 保存数据
        self.save_scripts()
        self.save_config()
        
        event.accept()


def main():
    """主函数"""
    app = QApplication(sys.argv)
    
    # 设置应用程序信息
    app.setApplicationName("聚雍宝")
    app.setApplicationVersion("2.0")
    app.setOrganizationName("聚雍宝团队")
    
    # 应用优化主题（推荐使用优化现代主题）
    try:
        theme_manager.apply_theme(app, "modern_optimized")
        print("✅ 已应用优化现代主题")
    except Exception as e:
        print(f"⚠️ 主题加载失败，使用备用样式: {e}")
        style_manager.apply_style(app, "modern")
    
    # 创建主窗口
    window = AssistantMainWindow()
    window.show()
    
    # 运行应用程序
    sys.exit(app.exec())


if __name__ == "__main__":
    main()