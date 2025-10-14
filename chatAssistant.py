"""
秒回 - PySide6版本
智能客服助手 - 现代化界面版本
"""
from symbol import compound_stmt
import sys
import os
import json
import time
import threading
from pathlib import Path
from typing import Dict, Any, Optional
import logging
import traceback
import random

# PySide6 imports
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QGridLayout, QLabel, QPushButton, QLineEdit, QTextEdit, QTreeWidget,
    QTreeWidgetItem, QGroupBox, QCheckBox, QComboBox, QFrame, QSplitter,
    QScrollArea, QTabWidget, QStatusBar, QMenuBar, QMenu, QMessageBox,
    QDialog, QDialogButtonBox, QProgressBar, QSpacerItem, QSizePolicy,
    QLayout
)
from PySide6.QtCore import (
    Qt, QTimer, QThread, QObject, Signal, QSize, QPropertyAnimation,
    QEasingCurve, QRect, QPoint, Slot
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
from utils.api_manager import APIManager
from utils.data_adapter import DataAdapter
import utils.utils as utils
import utils.constants as constans

# 导入主题管理器
from styles.theme_manager import theme_manager

# 导入窗口吸附管理器
from components.window_dock_manager import WindowDockManager

# 导入自定义标题栏
from components.custom_title_bar import CustomTitleBar

# 导入添加弹窗
from components.add_dialog import AddDialog


def setup_pyqt_exception_handling():
    """设置 PyQt 异常处理"""
    # 备份原始异常钩子
    sys._excepthook = sys.excepthook

    def pyqt_exception_hook(exctype, value, traceback_obj):
        """PyQt 异常钩子"""
        # 记录异常
        log_exception(exctype, value, traceback_obj)

        # 调用原始异常钩子
        sys._excepthook(exctype, value, traceback_obj)

        # 可选：如果希望程序继续运行，可以注释掉下面这行
        sys.exit(1)

    # 设置异常钩子
    sys.excepthook = pyqt_exception_hook


def log_exception(exctype, value, traceback_obj):
    """记录异常"""
    try:
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        file_handler = logging.FileHandler('pyqt_errors.log', mode='a', encoding='utf-8')
        file_handler.setFormatter(formatter)

        logger = logging.getLogger('pyqt_errors')
        logger.setLevel(logging.ERROR)

        # 避免重复添加处理器
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)
        logger.addHandler(file_handler)

        error_msg = "".join(traceback.format_exception(exctype, value, traceback_obj))

        print(f"PyQt异常捕获：\n{error_msg}")
        logger.error(f"PyQt异常捕获：\n{error_msg}")

        # 立即刷新日志
        file_handler.flush()
        file_handler.close()

    except Exception as e:
        print(f"记录异常时出错: {e}")


"""流式布局类"""


class FlowLayout(QLayout):
    """自动换行的流式布局"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._item_list = []
        self._spacing = -1

    def __del__(self):
        item = self.takeAt(0)
        while item:
            item = self.takeAt(0)

    def addItem(self, item):
        self._item_list.append(item)

    def count(self):
        return len(self._item_list)

    def itemAt(self, index):
        if 0 <= index < len(self._item_list):
            return self._item_list[index]
        return None

    def takeAt(self, index):
        if 0 <= index < len(self._item_list):
            return self._item_list.pop(index)
        return None

    def expandingDirections(self):
        return Qt.Orientation(0)

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, width):
        height = self._do_layout(QRect(0, 0, width, 0), True)
        return height

    def setGeometry(self, rect):
        super().setGeometry(rect)
        self._do_layout(rect, False)

    def sizeHint(self):
        return self.minimumSize()

    def minimumSize(self):
        size = QSize()
        for item in self._item_list:
            size = size.expandedTo(item.minimumSize())
        size += QSize(2 * self.contentsMargins().left(), 2 * self.contentsMargins().top())
        return size

    def _do_layout(self, rect, test_only):
        x = rect.x()
        y = rect.y()
        line_height = 0
        spacing = self.spacing()

        for item in self._item_list:
            widget = item.widget()
            if widget.isHidden():
                continue

            space_x = spacing
            space_y = spacing

            next_x = x + item.sizeHint().width() + space_x
            if next_x - space_x > rect.right() and line_height > 0:
                x = rect.x()
                y = y + line_height + space_y
                next_x = x + item.sizeHint().width() + space_x
                line_height = 0

            if not test_only:
                item.setGeometry(QRect(QPoint(x, y), item.sizeHint()))

            x = next_x
            line_height = max(line_height, item.sizeHint().height())

        return y + line_height - rect.y()


class WindowMonitor(QThread):
    """窗口监控线程"""

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
                        if title and title.strip() and "秒回" not in title:
                            self.window_changed.emit(current_window, title.strip())
                    except:
                        pass

                self.msleep(500)
            except Exception as e:
                print('监控线程主循环报错', e)
                self.msleep(1000)

    def stop_monitoring(self):
        """停止监控"""
        self.monitoring = False
        self.quit()
        self.wait()


class ModernButton(QPushButton):
    """现代化按钮组件"""

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

    def init_data(self):
        """初始化数据变量"""
        # Tab数据结构
        self.current_type_id = 0
        self.current_level_one_id = 0

        # 数据结构
        self.scripts_data = []
        self.current_scripts_data = []
        self.filtered_scripts = []

        # 数据存储
        self.level_one_category_dict = {}
        self.level_two_category_dict = {}
        self.right_click_data = {}

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

        # 组件
        self.api_manager = None
        self.data_adapter = None
        self.window_monitor = None
        self.dock_manager = None

        # UI组件引用
        self.primary_tabs = {}
        self.level_one_tab_buttons = {}
        self.level_one_buttons_widget = None
        self.secondary_buttons_layout = None

        # 吸附功能配置
        self.dock_enabled = False
        self.dock_gap = 1

        # 搜索状态
        self.is_search = False
        self.search_text = ''

    def setup_window(self):
        """设置窗口属性"""
        self.setWindowTitle("秒回")
        self.setMinimumSize(300, 500)

        # 设置无边框窗口
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.resize(300, 700)

        # 设置窗口图标（如果有的话）
        # self.setWindowIcon(QIcon("styles/icons/app_icon.png"))

        # 设置窗口置顶
        if self.always_on_top:
            self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)

    # <============================监控窗口相关方法==============================>

    def init_monitoring(self):
        """初始化窗口监控"""

        # 获取自己的窗口句柄
        def find_my_window(hwnd, param):
            try:
                if win32gui.IsWindowVisible(hwnd):
                    title = win32gui.GetWindowText(hwnd)
                    if "秒回" in title:
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

    def start_monitoring(self):
        """启动窗口监控"""
        if self.window_monitor:
            # 获取自己的窗口句柄
            def find_my_window(hwnd, param):
                try:
                    if win32gui.IsWindowVisible(hwnd):
                        title = win32gui.GetWindowText(hwnd)
                        if "秒回" in title:
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

    # <============================获取数据方法==============================>

    def load_initial_data(self):
        """加载初始数据"""
        try:
            # 初始化数据适配器
            self.data_adapter = DataAdapter()
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

            # 延迟更新按钮布局，确保界面完全渲染
            QTimer.singleShot(100, self.update_level_one_tabs)

        except Exception as e:
            print(f"加载初始数据失败: {e}")

    def load_data_from_adapter(self):
        """从数据适配器加载数据"""
        if self.data_adapter:
            # 获取话术数据
            self.scripts_data = self.data_adapter.get_scripts_data()

            # 设置当前选中类型id
            if self.current_type_id not in self.data_adapter.all_type_id_list:
                self.current_type_id = self.data_adapter.all_type_id_list[0]

            # 设置当前选中一级分类id
            level_one_list = self.data_adapter.get_level_one_list(self.current_type_id)
            if self.current_level_one_id not in level_one_list:
                self.current_level_one_id = level_one_list[0]['id']

    def sync_cloud_data(self):
        """同步云端数据"""
        try:
            if not self.is_logged_in or not self.current_user_id:
                return False

            if self.data_adapter:
                if self.data_adapter:
                    self.data_adapter.api_manager = self.api_manager
                    uid = 0
                    try:
                        uid = int(self.current_user_id) if (
                                self.current_user_id is not None and str(self.current_user_id).isdigit()) else 0
                    except:
                        uid = 0
                    self.data_adapter.user_id = uid

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

    def load_current_scripts_data(self, isClear: bool = False):
        """加载当前Tab数据"""
        self.current_scripts_data = self.data_adapter.get_tree_scripts_data(self.current_type_id,
                                                                            self.current_level_one_id)
        self.filtered_scripts = self.current_scripts_data.copy()
        self.update_tree()
        if isClear:
            self.search_edit.clear()

    def save_scripts(self):
        """保存话术数据"""
        try:
            if hasattr(self, 'scripts_data') and self.data_adapter:
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

    # <============================处理基础数据方法==============================>

    def update_current_level_one_category_dict(self, data):
        '''更新一级分类dict数据'''
        self.level_one_category_dict = {}
        for level_one_category_data in data:
            dict = {
                'name': level_one_category_data['name'],
                'script_type_id': level_one_category_data['script_type_id'],
                'level_one_category_id': level_one_category_data['level_one_category_id']
            }
            self.level_one_category_dict[level_one_category_data['level_one_category_id']] = dict

    # <============================创建界面元素方法==============================>

    def create_ui(self):
        """创建用户界面"""
        # 创建中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        central_widget.setObjectName("main_frame")

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
        self.create_primary_tabs_section(main_layout)
        self.create_secondary_tabs_section(main_layout)
        self.create_tree_section(main_layout)
        self.create_search_section(main_layout)
        self.create_status_section(main_layout)

    def create_primary_tabs_section(self, parent_layout):
        """创建话术类型Tab部分"""
        primary_group = QWidget()
        parent_layout.addWidget(primary_group)

        # 2. 设置水平布局，边距全部设为0（更紧凑）
        primary_layout = QHBoxLayout(primary_group)
        primary_layout.setContentsMargins(0, 0, 0, 0)  # 减少底部边距

        # 3. 创建标签页控件
        self.type_tab_widget = QTabWidget()
        self.type_tab_widget.setTabPosition(QTabWidget.North)  # 标签在顶部
        self.type_tab_widget.currentChanged.connect(self.on_primary_tab_changed)  # 切换标签时触发

        # 4. 为标签栏设置右键菜单功能
        # try:
        #     # 设置标签栏支持自定义右键菜单
        #     self.type_tab_widget.tabBar().setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        #     # 连接右键菜单请求信号到处理函数
        #     self.type_tab_widget.tabBar().customContextMenuRequested.connect(self.show_primary_tab_context_menu)
        #     print("一级Tab右键菜单设置成功")  # 调试信息
        # except Exception as e:
        #     print(f"设置一级Tab右键菜单失败: {e}")  # 错误处理

        primary_layout.addWidget(self.type_tab_widget, 1)

    def create_secondary_tabs_section(self, parent_layout):
        """创建话术分类Tab部分（按钮形式）"""
        secondary_group = QWidget()
        parent_layout.addWidget(secondary_group)

        secondary_layout: QVBoxLayout = QVBoxLayout(secondary_group)
        secondary_layout.setContentsMargins(0, 0, 0, 0)
        # secondary_layout.setSpacing(0)

        # 创建按钮容器
        self.level_one_buttons_widget = QWidget()
        # self.level_one_buttons_widget.setMinimumHeight(40)

        # 存储按钮的字典和布局信息
        self.level_one_tab_buttons = {}
        self.button_rows = []  # 存储每行的按钮

        # 直接添加按钮容器到布局
        secondary_layout.addWidget(self.level_one_buttons_widget)

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

    # <============================更新界面元素方法==============================>

    def update_all_ui(self):
        """更新所有界面元素"""
        self.update_type_tabs()
        self.update_level_one_tabs(True)
        self.update_tree()
        self.update_login_status()

    def update_ui(self, type: str):
        print('type', type)
        if type == 'switch_type':
            self.update_level_one_tabs()
            self.load_current_scripts_data()

        if type == 'switch_level_one':
            self.load_current_scripts_data()
        elif type == 'add_level_one':
            self.update_level_one_tabs()
        elif type == 'edit_level_one':
            self.update_level_one_tabs()
        elif type == 'delete_level_one':
            self.update_level_one_tabs()
            self.load_current_scripts_data()

        if type == 'add_level_two':
            self.load_current_scripts_data()
        elif type == 'edit_level_two':
            self.load_current_scripts_data()
        elif type == 'delete_level_two':
            self.load_current_scripts_data()

        if type == 'add_script':
            self.load_current_scripts_data()
        elif type == 'edit_script':
            self.load_current_scripts_data()
        elif type == 'delete_script':
            self.load_current_scripts_data()

        if self.is_search:
            self.is_search = False
            self.clear_search()

    def update_type_tabs(self):
        """更新话术类型Tab"""
        # 清空现有Tab
        self.type_tab_widget.clear()
        self.primary_tabs.clear()

        # 添加新Tab
        if self.scripts_data:
            for type_attr in self.data_adapter.all_type_data_list:
                type_name = type_attr.get('name')
                type_id = type_attr.get('id')
                tab_widget = QWidget()
                tab_widget.setProperty('script_type_id', type_id)

                self.primary_tabs[type_id] = tab_widget
                self.type_tab_widget.addTab(tab_widget, type_name)

            # 选中当前Tab
            idList = self.data_adapter.all_type_id_list
            if self.current_type_id in idList:
                index = idList.index(self.current_type_id)
                self.type_tab_widget.setCurrentIndex(index)
                self.update_level_one_tabs()
            else:
                print('未找到当前一级tab选中值')

    def update_level_one_tabs(self, first: Optional[bool] = False):
        """更新话术分类Tab（按钮形式）"""
        # 清空现有按钮
        for button in self.level_one_tab_buttons.values():
            button.deleteLater()
        self.level_one_tab_buttons.clear()

        # 添加新按钮
        if self.current_type_id in self.data_adapter.all_type_id_list:
            # 按钮参数
            button_height = 24
            button_spacing = 1
            margin = 1
            min_button_width = 20  # 最小宽度
            max_button_width = 90  # 最大宽度

            # 计算容器宽度
            container_width = self.level_one_buttons_widget.width()
            if container_width <= 50:  # 如果宽度太小或为0，使用父容器宽度
                parent_width = self.width() if self.width() > 0 else 300
                container_width = parent_width

            x = margin
            y = margin

            level_one_List = self.data_adapter.get_level_one_list(self.current_type_id)

            for level_one_attr in level_one_List:
                level_one_id = level_one_attr.get('id')
                level_one_name = level_one_attr.get('name')
                type_id = level_one_attr.get('typeId')

                # 创建按钮
                button = ModernTabButton(level_one_name, level_one_id == self.current_level_one_id)
                # 设置属性
                button.setProperty("level_one_id", level_one_id)

                button.setParent(self.level_one_buttons_widget)

                # 根据文字内容计算按钮宽度
                font_metrics = button.fontMetrics()
                text_width = font_metrics.horizontalAdvance(level_one_name)
                # 添加左右内边距
                button_width = max(min_button_width, min(text_width + 10, max_button_width))

                button.setFixedSize(button_width, button_height)

                # 检查是否需要换行
                if x + button_width > container_width - margin and x > margin:
                    # 换行
                    x = margin
                    y += button_height + button_spacing

                # 连接点击事件 - 使用默认参数捕获循环变量
                button.clicked.connect(
                    lambda checked=False, type_id=type_id, level_one_id=level_one_id,
                           level_one_name=level_one_name: self.on_secondary_button_clicked(type_id, level_one_id,
                                                                                           level_one_name))

                # 设置右键菜单
                button.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
                button.customContextMenuRequested.connect(
                    lambda pos, type_id=type_id, level_one_id=level_one_id,
                           level_one_name=level_one_name: self.show_level_one_button_context_menu(pos, type_id,
                                                                                                  level_one_id,
                                                                                                  level_one_name)
                )

                # 设置位置
                button.move(x, y)
                button.show()

                self.level_one_tab_buttons[level_one_id] = button

                # 计算下一个按钮位置
                x += button_width + button_spacing

            # 添加"+"按钮
            add_button = ModernTabButton("+", False)
            add_button.setParent(self.level_one_buttons_widget)
            add_button_width = 30
            add_button.setFixedSize(add_button_width, button_height)

            # 检查"+"按钮是否需要换行
            if x + add_button_width > container_width - margin and x > margin:
                x = margin
                y += button_height + button_spacing

            add_button.clicked.connect(
                lambda checked: self.show_add_dialog('level_one', self.current_type_id))

            # 设置位置
            add_button.move(x, y)
            add_button.show()

            self.level_one_tab_buttons["+"] = add_button

            # 更新容器高度 - 根据最后一个按钮的位置计算
            # 如果所有按钮都在第一行 (y == margin)，则只需要一行的高度
            if y == margin:  # 所有按钮都在第一行
                new_height = button_height + margin * 2
            else:  # 有多行按钮
                new_height = y + button_height + margin

            # 设置最小高度，确保不会太小
            new_height = max(new_height, 0)
            self.level_one_buttons_widget.setMinimumHeight(new_height)
            self.level_one_buttons_widget.setMaximumHeight(new_height)

            if first:
                self.load_current_scripts_data()

    def update_tree(self):
        """更新树形列表"""
        self.tree_widget.clear()
        # 处理数据结构：话术标题 -> 话术内容列表
        for title_data in self.filtered_scripts:
            # 创建分类节点
            category_item = QTreeWidgetItem([f"📁 {title_data['name']}"])
            category_item.setData(0, Qt.ItemDataRole.UserRole,
                                  {"type": "title", "id": title_data['id'], "name": title_data['name']})
            self.tree_widget.addTopLevelItem(category_item)

            # 添加话术内容
            if isinstance(title_data['data'], list):
                for script_data in title_data['data']:
                    display_text = script_data['content'] if len(script_data['content']) <= 50 else script_data[
                                                                                                        'content'][
                                                                                                    :50] + "..."
                    script_item = QTreeWidgetItem([f"💬 {display_text}"])
                    script_item.setData(0, Qt.ItemDataRole.UserRole, {
                        "type": "script",
                        "id": script_data['id'],
                        "content": script_data['content'],
                        "title": script_data['title'],
                    })
                    category_item.addChild(script_item)
            category_item.setExpanded(True)

    def update_login_status(self):
        """更新登录状态"""
        if self.is_logged_in and self.current_user_id:
            self.login_btn.setText(f"用户:{self.current_user_id[:6]}...")
        else:
            self.login_btn.setText("登录")

    # <============================状态栏相关方法==============================>

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

    # <============================话术类型点击事件相关方法==============================>

    def on_primary_tab_changed(self, index: int):
        """话术类型Tab切换（通过索引）"""
        type_id_list = self.data_adapter.all_type_id_list
        if index < len(type_id_list):
            type_id = type_id_list[index]
            if type_id != self.current_type_id:
                # 更新当前类型
                self.current_type_id = type_id

                level_one_list = self.data_adapter.get_level_one_list(self.current_type_id)
                self.current_level_one_id = level_one_list[0]['id']

                # 刷新
                self.update_ui('switch_type')

    # <============================话术分类点击事件相关方法==============================>

    def on_secondary_button_clicked(self, type_id: int, level_one_id: int, level_one_name: str):
        """话术分类按钮点击事件"""
        if level_one_id != self.current_level_one_id:
            # 更新按钮状态
            for btn_level_one_id, button in self.level_one_tab_buttons.items():
                if level_one_name != "+":  # 跳过"+"按钮
                    button.set_selected(btn_level_one_id == level_one_id)
                    self.current_level_one_id = level_one_id
                    if self.is_search:
                        # 清空搜索框
                        self.is_search = False
                        self.clear_search()

            # 刷新
            self.update_ui('switch_level_one')

    def show_level_one_button_context_menu(self, position, type_id: int, level_one_id: int,
                                           level_one_name: str):
        """显示话术分类按钮右键菜单"""
        if level_one_name == "+":
            return  # "+"按钮不显示右键菜单

        try:
            menu = QMenu(self)
            rename_action = QAction("修改一级分类名称", self)
            rename_action.triggered.connect(
                lambda checked: self.show_edit_dialog('level_one', level_one_id))
            menu.addAction(rename_action)

            delete_action = QAction("删除一级分类", self)
            delete_action.triggered.connect(
                lambda: self.delete_level_one(level_one_id, level_one_name))
            menu.addAction(delete_action)

            # 获取按钮并显示菜单
            button = self.level_one_tab_buttons.get(level_one_id)
            if button:
                global_pos = button.mapToGlobal(position)
                menu.exec(global_pos)

        except Exception as e:
            print(f"话术分类按钮右键菜单错误: {e}")

    # <============================树形结构点击事件相关方法==============================>

    def on_tree_single_click(self, item: QTreeWidgetItem, column: int):
        """树形控件单击事件"""
        pass
        # data = item.data(0, Qt.ItemDataRole.UserRole)
        # if data and data.get("type") == "script":
        #     # 获取鼠标点击位置
        #     from PySide6.QtGui import QCursor
        #     global_pos = QCursor.pos()
        #     cursor_pos = self.tree_widget.mapFromGlobal(global_pos)
        #     item_rect = self.tree_widget.visualItemRect(item)

        #     # 计算相对于item左边的点击位置
        #     relative_x = cursor_pos.x() - item_rect.left()

        #     # 检查是否点击在📤图标区域
        #     if 0 <= relative_x <= 30:
        #         script_content = data.get("content", "")
        #         self.send_script_directly(script_content)
        #         return

    def on_tree_double_click(self, item: QTreeWidgetItem, column: int):
        """树形控件双击事件"""
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if data and data.get("type") == "script":
            script_content = data.get("content", "")
            self.send_script_text(script_content)

    def show_tree_context_menu(self, position):
        """显示树形控件右键菜单"""
        item = self.tree_widget.itemAt(position)

        menu = QMenu(self)

        if not item:
            # 点击空白区域的菜单
            add_title_action = QAction("添加话术标题", self)
            add_title_action.triggered.connect(
                lambda checked: self.show_add_dialog('level_two', self.current_level_one_id))
            menu.addAction(add_title_action)

            add_script_action = QAction("添加话术", self)
            id_list = self.data_adapter.level_one_children_idList_byIds.get(
                (self.current_type_id, self.current_level_one_id), 0)
            add_script_action.triggered.connect(
                lambda checked: self.show_add_dialog('script', id_list[0]))
            menu.addAction(add_script_action)

            menu.exec(self.tree_widget.mapToGlobal(position))
            return

        data = item.data(0, Qt.ItemDataRole.UserRole)

        if not data:
            print("🔍 item没有数据，返回")
            return

        if data.get("type") == "title":
            if self.is_search:
                return
                # 分类节点菜单
            level_two_name = data.get("name")
            level_two_id = data.get("id")

            add_script_action = QAction("添加话术", self)
            add_script_action.triggered.connect(
                lambda checked: self.show_add_dialog('script', level_two_id))  # 2表示添加话术内容
            menu.addAction(add_script_action)

            menu.addSeparator()
            edit_action = QAction("编辑话术标题", self)
            edit_action.triggered.connect(
                lambda checked=False: self.show_edit_dialog('level_two', level_two_id))
            menu.addAction(edit_action)

            delete_action = QAction("删除话术标题", self)
            delete_action.triggered.connect(
                lambda checked=False: self.delete_level_two(level_two_id, level_two_name))
            menu.addAction(delete_action)

        elif data.get("type") == "script":
            # 话术节点菜单
            edit_action = QAction("编辑话术", self)
            script_id = data['id']
            content = data['content']
            self.right_click_data = data

            edit_action.triggered.connect(
                lambda checked=False: self.show_edit_dialog('script', script_id))
            menu.addAction(edit_action)

            delete_action = QAction("删除话术", self)
            delete_action.triggered.connect(lambda checked=False: self.delete_script(script_id, content))
            menu.addAction(delete_action)

        menu.exec(self.tree_widget.mapToGlobal(position))

    # <============================搜索框相关方法==============================>

    def on_search_changed(self, text: str):
        """搜索文本改变（按当前列表结构过滤）"""
        self.search_text = text.strip().lower()
        if not self.search_text:
            self.filtered_scripts = self.current_scripts_data.copy()
            self.is_search = False
        else:
            self.is_search = True
            filtered = []
            matched_scripts = []
            # 在当前二级分类列表中进行过滤
            for script_data in self.data_adapter.all_script_data_list:
                if self.search_text in (script_data.get('content').lower()) or self.search_text in (
                        script_data.get('title', '').lower()):
                    matched_scripts.append(script_data)

            if len(matched_scripts):
                filtered.append({
                    'id': 0,
                    'name': '话术',
                    'data': matched_scripts
                })
            self.filtered_scripts = filtered
        self.update_tree()

    def clear_search(self):
        """清空搜索"""
        self.search_edit.clear()
        self.search_text = ''
        self.filtered_scripts = self.current_scripts_data.copy()
        self.is_search = False
        self.update_tree()

    # <============================发送模式相关方法==============================>

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
        if self.is_search:
            self.is_search = False
            self.clear_search()

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

    # <============================权限控制相关方法==============================>

    def get_user_permissions(self) -> Dict[str, bool]:
        pass

    # <============================登陆/登出相关方法==============================>

    def show_login_dialog(self):
        """显示登录对话框"""
        if self.is_logged_in:
            reply = QMessageBox.question(
                self, "登出确认",
                f"当前用户: {self.current_user_id}\n确定要登出吗？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
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
            self.data_adapter = DataAdapter()

            # 重新加载数据
            self.load_data_from_adapter()
            self.update_all_ui()
            self.update_login_status()

            # 保存配置
            self.save_config()

            self.status_label.setText("已登出")
        except Exception as e:
            QMessageBox.critical(self, "登出失败", f"登出时发生错误: {str(e)}")

    # <============================设置功能相关方法==============================>

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
        # import_action = QAction("导入数据", self)
        # import_action.triggered.connect(self.import_data)
        # menu.addAction(import_action)
        #
        # export_action = QAction("导出数据", self)
        # export_action.triggered.connect(self.export_data)
        # menu.addAction(export_action)

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
        self.status_label.setText(f"发送模式: {mode}")

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
                uid = 0
                try:
                    uid = int(self.current_user_id) if (
                            self.current_user_id is not None and str(self.current_user_id).isdigit()) else 0
                except:
                    uid = 0
                self.data_adapter.user_id = uid

                # 统一通过保存与索引刷新后再上传，避免直接赋值
                self.save_scripts()
                if self.data_adapter:
                    self.data_adapter.init_data()
                    self.load_data_from_adapter()
                success = self.data_adapter.push_local_scripts_data()
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
                # 先设置 API 管理器与用户ID
                self.data_adapter.api_manager = self.api_manager
                uid = 0
                try:
                    uid = int(self.current_user_id) if (
                            self.current_user_id is not None and str(self.current_user_id).isdigit()) else 0
                except:
                    uid = 0
                self.data_adapter.user_id = uid
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

    # <============================手动该改变窗口大小相关方法==============================>

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
                if hasattr(self, 'dock_manager') and self.dock_manager and hasattr(self,
                                                                                   'dock_enabled') and self.dock_enabled:
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
        if not hasattr(self, 'resize_start_pos') or not hasattr(self,
                                                                'resize_start_geometry') or not self.resize_direction:
            return

        delta = global_pos - self.resize_start_pos
        geom = self.resize_start_geometry or self.geometry()
        new_geometry = QRect(geom)

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
            if hasattr(self, 'dock_manager') and self.dock_manager and hasattr(self,
                                                                               'dock_enabled') and self.dock_enabled:
                if hasattr(self, 'target_window') and self.target_window:
                    self.dock_manager.enable_docking(self.target_window)

            event.accept()

    # <============================添加功能（话术分类、话术标题、话术内容）==============================>

    def show_add_dialog(self, add_type: str, id: int):
        """显示添加内容弹窗并设置默认类型"""
        try:
            # 创建并显示添加弹窗
            add_dialog = AddDialog(self)
            # 设置默认类型
            add_dialog.set_add_mode(add_type, id)

            # 连接新增信号
            if add_type == 'level_one':
                add_dialog.level_one_added_signal.connect(self.add_level_one_callback)
            elif add_type == 'level_two':
                add_dialog.level_two_added_signal.connect(self.add_level_two_callback)
            elif add_type == 'script':
                add_dialog.level_one_added_signal.connect(self.add_level_one_callback)
                add_dialog.level_two_added_signal.connect(self.add_level_two_callback)
                add_dialog.content_added_signal.connect(self.add_script_content_callback)

            # 连接弹窗关闭信号
            add_dialog.accepted.connect(lambda: self.status_label.setText("✅ 内容添加成功"))
            add_dialog.rejected.connect(lambda: self.status_label.setText("❌ 取消添加"))

            # 显示非模态弹窗
            add_dialog.show()
            add_dialog.raise_()
            add_dialog.activateWindow()

        except Exception as e:
            QMessageBox.critical(self, "错误", f"显示添加弹窗失败：{str(e)}")

    def add_level_one_callback(self, type_id: int, value: str):
        """处理添加话术分类"""
        try:
            if self.data_adapter:
                success = self.data_adapter.add_level_one(type_id, value)
                if success:
                    self.update_ui('add_level_one')
                else:
                    QMessageBox.warning(self, "警告", "添加失败")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"添加失败: {str(e)}")

    def add_level_two_callback(self, level_one_id: int, value: str):
        """处理添加话术标题"""
        try:
            if self.data_adapter:
                success = self.data_adapter.add_level_two(level_one_id, value)
                if success:
                    self.update_ui('add_level_two')
                else:
                    QMessageBox.warning(self, "警告", "添加失败")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"添加失败: {str(e)}")

    def add_script_content_callback(self, level_two_id: str,
                                    script_content: str, script_title_value: str):
        """添加话术内容回调"""
        try:
            if self.data_adapter:
                success = self.data_adapter.add_script(level_two_id, content=script_content, title=script_title_value)
                if success:
                    self.update_ui('add_script')
                else:
                    QMessageBox.warning(self, "警告", "添加失败")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"添加失败: {str(e)}")

    # <============================修改功能（话术分类、话术标题、话术内容）==============================>

    def show_edit_dialog(self, edit_type: str, id: int):
        """显示编辑对话框"""
        try:
            # 创建编辑对话框
            edit_dialog = AddDialog(self, True)

            # 设置编辑模式
            edit_dialog.set_edit_mode(edit_type, id)

            # 连接编辑信号
            if edit_type == 'level_one':
                edit_dialog.level_one_edited_signal.connect(self.edit_level_one_callback)
            elif edit_type == 'level_two':
                edit_dialog.level_two_edited_signal.connect(self.edit_level_two_callback)
            elif edit_type == 'script':
                edit_dialog.content_edited_signal.connect(self.edit_script_callback)

            # 连接弹窗关闭信号
            edit_dialog.accepted.connect(lambda: self.status_label.setText("✅ 编辑成功"))
            edit_dialog.rejected.connect(lambda: self.status_label.setText("❌ 取消编辑"))

            # 显示非模态弹窗
            edit_dialog.show()
            edit_dialog.raise_()
            edit_dialog.activateWindow()

        except Exception as e:
            QMessageBox.critical(self, "错误", f"显示编辑对话框失败：{str(e)}")

    def edit_level_one_callback(self, level_one_id: int, new_value: str):
        """编辑话术分类（使用 DataAdapter）"""
        try:
            if self.data_adapter:
                success = self.data_adapter.edit_level_one_name(level_one_id, new_value)
                if success:
                    self.update_ui('edit_level_one')
                else:
                    QMessageBox.warning(self, "警告", "编辑失败：未找到该分类或ID无效")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"编辑话术分类失败: {str(e)}")

    def edit_level_two_callback(self, level_two_id: int, new_value: str):
        """编辑话术标题（使用 DataAdapter）"""
        try:
            if self.data_adapter:
                success = self.data_adapter.edit_level_two_name(level_two_id, new_value)
                if success:
                    self.update_ui('edit_level_two')
                else:
                    QMessageBox.warning(self, "警告", "编辑失败：未找到该标题或ID无效")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"编辑话术标题失败: {str(e)}")

    def edit_script_callback(self, script_id: int, new_value: str, script_title_value: str):
        """编辑话术内容（使用 DataAdapter）"""
        try:
            if self.data_adapter:
                success = self.data_adapter.edit_script(script_id, content=new_value, title=script_title_value)
                if success:
                    self.update_ui('edit_script')
                else:
                    QMessageBox.warning(self, "警告", "编辑失败：未找到该话术或ID无效")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"编辑话术内容失败: {str(e)}")

    # <============================删除功能（话术分类、话术标题、话术内容）==============================>

    def delete_level_one(self, level_one_id: int, level_one_name: str):
        """删除话术分类（使用 DataAdapter）"""
        # 使用数据适配器的索引获取真实的一级分类数量进行校验
        level_one_list = self.data_adapter.get_level_one_list(self.current_type_id) or []
        if len(level_one_list) <= 1:
            QMessageBox.warning(self, "警告", "至少需要保留一个一级分类！")
            return

        reply = QMessageBox.question(
            self, "确认删除",
            f"确定要删除一级分类 '{level_one_name}' 及其所有话术吗？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            try:
                success = self.data_adapter.delete_level_one(level_one_id)
                if success:
                    self.update_ui('delete_level_one')
                else:
                    QMessageBox.warning(self, "错误", "删除失败：未找到该分类或ID无效")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"删除失败: {str(e)}")

    def delete_level_two(self, level_two_id: int, level_two_name: str):
        """删除分类标题（使用 DataAdapter）"""
        reply = QMessageBox.question(
            self, "确认删除",
            f"确定要删除二级分类 '{level_two_name}' 及其所有话术吗？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            try:
                success = self.data_adapter.delete_level_two(level_two_id)
                if success:
                    self.update_ui('delete_level_two')
                else:
                    QMessageBox.warning(self, "错误", "删除失败：未找到该分类或ID无效")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"删除失败: {str(e)}")

    def delete_script(self, script_id: int, content: str):
        """删除话术"""
        reply = QMessageBox.question(
            self, "确认删除",
            f"确定要删除话术:\n{content[:100]}{'...' if len(content) > 100 else ''}",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            try:
                success = self.data_adapter.delete_script(script_id)
                if success:
                    self.update_ui('delete_script')
            except Exception as e:
                print('ValueError', e)
                QMessageBox.warning(self, "错误", "找不到要删除的话术！")

    # <============================窗口默认事件==============================>

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
    # setup_pyqt_exception_handling()
    """主函数"""
    constans.file_abs_path = os.path.dirname(os.path.abspath(__file__))
    app = QApplication(sys.argv)

    # 设置应用程序信息
    app.setApplicationName("秒回")
    app.setApplicationVersion("2.0")
    app.setOrganizationName("秒回团队")

    # 应用优化主题（推荐使用优化现代主题）
    try:
        theme_manager.apply_theme(app, "modern_optimized")
        print("✅ 已应用优化现代主题")
    except Exception as e:
        print(f"⚠️ 主题加载失败: {e}")

    # 创建主窗口
    window = AssistantMainWindow()
    window.show()

    # 运行应用程序
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
