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
from typing import Dict, Any, Optional, List
import logging
import traceback
import random
import ctypes

# PySide6 imports
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QGridLayout, QLabel, QPushButton, QLineEdit, QTextEdit, QTreeWidget,
    QTreeWidgetItem, QGroupBox, QCheckBox, QComboBox, QFrame, QSplitter,
    QScrollArea, QTabWidget, QStatusBar, QMenuBar, QMenu, QMessageBox,
    QDialog, QDialogButtonBox, QProgressBar, QSpacerItem, QSizePolicy,
    QLayout, QSystemTrayIcon,QStyledItemDelegate
)
from PySide6.QtCore import (
    Qt, QTimer, QThread, QObject, Signal, QSize, QPropertyAnimation,
    QEasingCurve, QRect, QPoint, Slot, QEvent
)
from PySide6.QtGui import (
    QFont, QIcon, QPalette, QColor, QPixmap, QPainter, QBrush,
    QLinearGradient, QAction, QKeySequence, QCursor
)
from PySide6.QtNetwork import QLocalServer, QLocalSocket
# 导入原有模块
import pyautogui
import pyperclip
import win32gui
import win32con
from utils.api_manager import APIManager
from utils.data_adapter import DataAdapter
import utils.utils as utils
import utils.constants as constants
from utils.dock_apps import APPS

# 导入主题管理器
from styles.theme_manager import theme_manager

# 导入窗口吸附管理器
from components.window_dock_manager import WindowDockManager

# 导入自定义标题栏
from components.custom_title_bar import CustomTitleBar

# 导入添加弹窗
from components.add_dialog import AddDialog
from components.settings_dialog import SettingsDialog


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

        # 调试期不强制退出，避免因为轻微的 Hover/Tooltip 异常导致进程直接退出
        # sys.exit(1)
        return

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
        self.position_locked = False
        self.my_window_handle = None

    def run(self):
        """监控线程主循环"""
        while self.monitoring:
            try:
                if self.position_locked:
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
        self.setAlternatingRowColors(False)
        self.setIndentation(20)
        self.setMinimumHeight(200)
        # 设置更紧凑的行高
        self.setUniformRowHeights(True)
        # 去除顶部空白
        self.setContentsMargins(0, 0, 0, 0)
        self.setViewportMargins(0, 0, 0, 0)




class ColorAwareDelegate(QStyledItemDelegate):
    """根据项的 BackgroundRole 主动绘制背景，避免被样式表覆盖"""
    def paint(self, painter: QPainter, option, index):
        brush = index.data(Qt.ItemDataRole.BackgroundRole)
        if isinstance(brush, QBrush) and brush.color().isValid():
            painter.save()
            painter.fillRect(option.rect, brush)
            painter.restore()
        super().paint(painter, option, index)

# =================== 自绘“树形结构”组件 ===================
class ElideLabel(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._full_text = ""
        self.setWordWrap(False)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)

    def set_full_text(self, text: str):
        self._full_text = text or ""
        self._update_elide()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_elide()

    def _update_elide(self):
        try:
            metrics = self.fontMetrics()
            available = max(10, self.width())
            elided = metrics.elidedText(self._full_text, Qt.TextElideMode.ElideRight, available)
            super().setText(elided)
        except Exception:
            try:
                super().setText(self._full_text)
            except Exception:
                pass

class ScriptRow(QWidget):
    def __init__(self, display_text: str, content: str, bg_color: Optional[str], callbacks: dict, parent=None):
        super().__init__(parent)
        self.display_text = display_text
        self.content = content
        self.callbacks = callbacks or {}
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        # 保证整行有稳定的高度，避免被压缩导致文字上移/裁剪
        self.setFixedHeight(26)
        # 发送按钮放到最前面，并使用与header切换按钮一致的尺寸以便垂直对齐
        self.send_btn = QPushButton()
        self.send_btn.setIcon(QIcon("static/icon/fasong.png"))
        self.send_btn.setFlat(True)
        self.send_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.send_btn.setFixedSize(26, 26)
        self.send_btn.setIconSize(QSize(26, 26))
        # 发送按钮基础/行悬浮样式：默认透明，行悬浮时橙黄色背景
        self._send_base_style = "QPushButton{background: transparent; border:none;padding:0;}"
        self._send_row_hover_style = "QPushButton{background:#8ec5fc; border:none; padding:0;}"
        self.send_btn.setStyleSheet(self._send_base_style)
        self.send_btn.clicked.connect(lambda: self.callbacks.get("on_send", lambda *_: None)(self.content))
        layout.addWidget(self.send_btn, 0, alignment=Qt.AlignmentFlag.AlignVCenter)
        # 左侧图标 + 标题容器（标题带用户自定义背景色）；无标题时不展示标题容器，只展示图标
        self.title_wrap = QWidget()
        self.title_wrap.setFixedHeight(26)
        title_wrap_layout = QHBoxLayout(self.title_wrap)
        title_wrap_layout.setContentsMargins(0,0,0,0)
        title_wrap_layout.setSpacing(4)
        # 图标
        self.left_icon = QLabel()
        self.left_icon.setFixedSize(26, 26)
        try:
            pix = QPixmap("static/icon/huashu.png")
            if not pix.isNull():
                pix = pix.scaled(20, 20, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                self.left_icon.setPixmap(pix)
        except Exception:
            pass
        title_wrap_layout.addWidget(self.left_icon, 0, alignment=Qt.AlignmentFlag.AlignVCenter)
        # 标题标签（使用用户自定义背景色），仅当有标题时才创建
        self.title_label = None
        if (self.display_text or "").strip():
            self.title_label = ElideLabel()
            self.title_label.setMinimumHeight(26)
            self.title_label.set_full_text(self.display_text)
            # 应用用户自定义背景色（若提供）
            if bg_color:
                self._title_base_style = f"background:{bg_color}; padding:0px;margin-right:4px;"
            else:
                self._title_base_style = "padding:0px; border-radius:4px;"
            self.title_label.setStyleSheet(self._title_base_style)
            title_wrap_layout.addWidget(self.title_label, 0, alignment=Qt.AlignmentFlag.AlignVCenter)
            layout.addWidget(self.title_wrap, 0, alignment=Qt.AlignmentFlag.AlignVCenter)
        else:
            # 仅图标，无标题时仍添加图标容器，使布局对齐
            layout.addWidget(self.title_wrap, 0, alignment=Qt.AlignmentFlag.AlignVCenter)
        
        # 内容标签容器（背景透明）
        self.content_wrap = QWidget()
        self.content_wrap.setFixedHeight(26)
        content_layout = QHBoxLayout(self.content_wrap)
        content_layout.setContentsMargins(0,0,0,0)
        content_layout.setSpacing(0)
        self.content_label = ElideLabel()
        self.content_label.setObjectName("tree_item_text")
        self.content_label.setMinimumHeight(26)
        self.content_label.setStyleSheet("background: transparent;")
        self.content_label.set_full_text(self.content or "")
        content_layout.addWidget(self.content_label, 1, alignment=Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(self.content_wrap, 1, alignment=Qt.AlignmentFlag.AlignVCenter)
        
        # 悬浮2秒后显示预览的定时器（单次）
        self._hovering = False
        self._hover_tip_timer = QTimer(self)
        self._hover_tip_timer.setSingleShot(True)
        self._hover_tip_timer.setInterval(2000)
        def _show_delayed_tip():
            try:
                if getattr(self, "_hover_alive", True) and self._hovering:
                    from PyQt6.QtWidgets import QToolTip
                    from PyQt6.QtGui import QCursor
                    QToolTip.showText(QCursor.pos(), self.full_text, self)
            except Exception:
                pass
        self._hover_tip_timer.timeout.connect(_show_delayed_tip)

        # 避免销毁后定时回调触发异常
        try:
            self.destroyed.connect(lambda *_: QTimer.singleShot(0, lambda: None))
        except Exception:
            pass
        # 行背景透明 + 悬停高亮（橙色）
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setStyleSheet("background: transparent;")
        # 安全注册 hover 监听，并在销毁时清理
        try:
            self._hover_alive = True
            self.destroyed.connect(lambda *_: setattr(self, "_hover_alive", False))
            for w in [
                self,
                self.send_btn,
                self.left_icon,
                getattr(self, 'title_wrap', None),
                getattr(self, 'content_wrap', None),
                getattr(self, 'title_label', None),
                getattr(self, 'content_label', None),
            ]:
                if w:
                    w.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
                    w.setMouseTracking(True)
                    w.installEventFilter(self)
            # 监听祖先容器的尺寸/布局变化，确保缩回时也触发省略计算
            self._resize_watchers = []
            def _install_resize_watchers(widget, depth=0):
                if not widget or depth > 5:
                    return
                try:
                    widget.installEventFilter(self)
                    self._resize_watchers.append(widget)
                except Exception:
                    pass
                _install_resize_watchers(widget.parentWidget(), depth+1)
            _install_resize_watchers(self.parentWidget())
            # 自身也开启鼠标追踪，保证 HoverMove 可用
            self.setMouseTracking(True)
        except Exception:
            pass

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            cb = self.callbacks.get("on_double")
            if cb:
                cb(self.content)
        super().mouseDoubleClickEvent(event)

    def contextMenuEvent(self, event):
        cb = self.callbacks.get("on_context")
        if cb:
            cb({"type": "script"}, self.mapToGlobal(event.pos()))

    def eventFilter(self, obj, event):
        et = event.type()
        if et in (QEvent.Type.Enter, QEvent.Type.HoverEnter):
            self._set_hover(True)
            self._hovering = True
            try:
                self._hover_tip_timer.stop()
                self._hover_tip_timer.start()
            except Exception:
                pass
        elif et in (QEvent.Type.HoverMove, QEvent.Type.MouseMove):
            # 保持悬浮状态，不重置计时器，避免一直推迟显示
            self._hovering = True
            # 当鼠标在标题容器或内容容器内移动时也保持 hover 状态
            try:
                from PyQt6.QtGui import QCursor
                pos = self.mapFromGlobal(QCursor.pos())
                if self.title_wrap.rect().contains(self.title_wrap.mapFromParent(pos)) or self.content_wrap.rect().contains(self.content_wrap.mapFromParent(pos)):
                    self._set_hover(True)
            except Exception:
                pass
        elif et in (QEvent.Type.Leave, QEvent.Type.HoverLeave):
            # 子控件之间切换会产生 HoverLeave，这里判断鼠标是否仍在整行内部，若还在则不当作离开
            try:
                from PyQt6.QtGui import QCursor
                if self.rect().contains(self.mapFromGlobal(QCursor.pos())):
                    return super().eventFilter(obj, event)
            except Exception:
                pass
            self._set_hover(False)
            self._hovering = False
            try:
                self._hover_tip_timer.stop()
                from PyQt6.QtWidgets import QToolTip
                QToolTip.hideText()
            except Exception:
                pass
        return super().eventFilter(obj, event)

    def _set_hover(self, on: bool):
        # 方案二：仅在内容容器(content_wrap)上显示 hover 背景；标题保持原样
        try:
            if on:
                if getattr(self, 'content_wrap', None):
                    self.content_wrap.setStyleSheet("background: #e0c3fc;")
                self.send_btn.setStyleSheet(self._send_row_hover_style)
            else:
                if getattr(self, 'content_wrap', None):
                    self.content_wrap.setStyleSheet("background: transparent;")
                self.send_btn.setStyleSheet(self._send_base_style)
        except Exception:
            pass


    def resizeEvent(self, event):
        super().resizeEvent(event)

class SectionWidget(QWidget):
    def __init__(self, title_id: str, title_name: str, callbacks: dict, parent=None):
        super().__init__(parent)
        self.title_id = title_id
        self.title_name = title_name
        self.callbacks = callbacks or {}
        self.expanded = True
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        # header
        header = QWidget()
        header.setObjectName("section_header")
        h = QHBoxLayout(header)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(0)
        self.toggle_btn = QPushButton()
        self.toggle_btn.setFlat(True)
        self.toggle_btn.setIcon(QIcon("static/icon/shouqi.png"))
        self.toggle_btn.setIconSize(QSize(14, 14))
        self.toggle_btn.setFixedSize(18, 18)
        self.toggle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.toggle_btn.clicked.connect(self.toggle)
        h.addWidget(self.toggle_btn, 0, alignment=Qt.AlignmentFlag.AlignVCenter)
        self.title_label = QLabel(title_name)
        self.title_label.setStyleSheet("font-weight:600;")
        self.title_label.setMinimumHeight(20)
        h.addWidget(self.title_label, 1, alignment=Qt.AlignmentFlag.AlignVCenter)
        header.mouseDoubleClickEvent = lambda e: self.toggle()
        header.contextMenuEvent = lambda e: self.callbacks.get("on_context", lambda *_: None)({"type": "title", "title_id": self.title_id}, header.mapToGlobal(e.pos()))
        self.main_layout.addWidget(header)
        # body container
        self.body = QWidget()
        self.body_layout = QVBoxLayout(self.body)
        # 调整为与header一致的左边距，让行首发送图标与收起/展开按钮垂直对齐
        self.body_layout.setContentsMargins(0, 0, 0, 0)
        self.body_layout.setSpacing(0)
        self.main_layout.addWidget(self.body)
        # spacer
        # self.main_layout.addSpacing(4)

    def add_row(self, row: QWidget):
        self.body_layout.addWidget(row)

    def toggle(self):
        self.expanded = not self.expanded
        self.body.setVisible(self.expanded)
        self.toggle_btn.setIcon(QIcon("static/icon/shouqi.png" if self.expanded else "static/icon/zhankai.png"))
        self.toggle_btn.setIconSize(QSize(14, 14))

class ScriptTree(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0,0,0,0)
        layout.setSpacing(0)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        # 不要横向滚动条
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        # 背景透明（不绘制viewport背景）
        self.scroll.setFrameShape(QFrame.NoFrame)
        self.scroll.setStyleSheet("QScrollArea, QScrollArea > QWidget, QScrollArea > QWidget > QWidget { background: transparent; }")
        layout.addWidget(self.scroll)
        self.container = QWidget()
        # 容器背景透明
        self.container.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.container.setStyleSheet("background: transparent;")
        self.v = QVBoxLayout(self.container)
        self.v.setContentsMargins(0, 0, 0, 0)
        self.v.setSpacing(1)
        self.v.addStretch(1)
        self.scroll.setWidget(self.container)
        self.callbacks = {}

    def set_callbacks(self, callbacks: dict):
        self.callbacks = callbacks or {}

    def clear(self):
        while self.v.count() > 1:
            item = self.v.takeAt(0)
            w = item.widget()
            if w:
                w.setParent(None)
                w.deleteLater()

    def render(self, sections: Optional[List[Dict[str, Any]]], callbacks: Dict[str, Any]):
        self.set_callbacks(callbacks)
        self.clear()
        for title_data in sections or []:
            title_id = title_data.get('id')
            title_name = (title_data.get('name') or '').strip()
            section = SectionWidget(title_id, title_name, {
                "on_context": lambda info, pos, tid=title_id: self._emit_context({"type": "title", "title_id": tid}, pos)
            })
            for script in title_data.get('data') or []:
                title = (script.get('title') or '').strip()
                content = (script.get('content') or '').strip()
                row = ScriptRow(title, content, (script.get('bgColor') or '').strip(), {
                    "on_double": lambda c: self.callbacks.get("on_script_double", lambda *_: None)(c),
                    "on_send": lambda c: self.callbacks.get("on_script_send", lambda *_: None)(c),
                    "on_context": lambda info, pos, sid=script.get('id'): self._emit_context({"type": "script", "script_id": sid}, pos)
                })
                section.add_row(row)
            self.v.insertWidget(self.v.count()-1, section)

    def _emit_context(self, info: dict, global_pos):
        cb = self.callbacks.get("on_context_menu")
        if cb:
            cb(info, global_pos)

    def contextMenuEvent(self, event):
        # 空白处右键
        cb = self.callbacks.get("on_context_menu")
        if cb:
            cb({"type": "blank"}, self.mapToGlobal(event.pos()))

class AssistantMainWindow(QMainWindow):
    """主窗口类"""

    def __init__(self):
        super().__init__()

        # 初始化拖拽相关属性
        self.drag_position = None
        self.resize_direction = None
        self.resize_margin = 4  # 边缘调整大小的区域宽度
        self.resize_start_pos = None
        self.resize_start_geometry = None

        # 初始化数据
        self.init_data()

        # 设置窗口
        self.setup_window()

        # 系统托盘图标
        self.setup_tray()

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

        # 窗口跟踪
        self.target_window = None
        self.target_title = "无"
        self.always_on_top = True

        # 发送模式配置
        self.send_mode = "直接发送"

        # 吸附功能
        self.dock_enabled = False
        self.position_locked = False

        # 新增：吸附位置与可吸附软件初始化
        self.dock_position = "right"
        self.dock_apps = ['全部']

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

        # 搜索状态
        self.is_search = False
        self.search_text = ''

    def setup_window(self):
        """设置窗口属性"""
        self.setWindowTitle("秒回")
        self.setMinimumSize(300, 500)

        # 设置无边框窗口（避免任务栏显示）
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setWindowFlag(Qt.WindowType.Tool, True)
        self.resize(300, 700)

        # 设置窗口图标（如果有的话）
        self.setWindowIcon(QIcon("static/icon/logo.png"))
        # 启用鼠标跟踪与悬停事件，确保未按键时也能更新光标
        self.setMouseTracking(True)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        # 关闭主窗口不退出，托盘常驻
        QApplication.setQuitOnLastWindowClosed(False)

        # 设置窗口置顶：窗口显示后延迟应用，确保句柄有效，避免 ERROR_INVALID_WINDOW_HANDLE(1400)
        if self.always_on_top:
            QTimer.singleShot(0, lambda: self.on_topmost_changed(self.always_on_top))
        
        # 安装事件过滤器，统一处理所有子部件的鼠标移动来更新光标
        self.installEventFilter(self)
        # 全局安装事件过滤器，兜底捕获所有控件的鼠标移动/悬停事件
        QApplication.instance().installEventFilter(self)

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
        if not self.position_locked:
            self.target_window = window_handle
            self.target_title = window_title
            # 若启用吸附，仅对被允许的软件进行吸附
            if self.dock_manager:
                try:
                    if self.dock_enabled:
                        if self.is_window_allowed_for_dock(window_title):
                            if not self.is_our_window(window_handle):
                                self.dock_manager.enable_docking(window_handle)
                            else:
                                self.dock_manager.disable_docking()
                        else:
                            # 当前前台窗口不在允许列表，确保关闭吸附
                            self.dock_manager.disable_docking()
                    else:
                        # 未启用时确保关闭
                        self.dock_manager.disable_docking()
                except Exception as e:
                    print(f"更新吸附目标失败: {e}")

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

    def setup_tray(self):
        """初始化系统托盘图标"""
        try:
            self.tray_icon = QSystemTrayIcon(QIcon("static/icon/app.ico"), self)
            # 双击托盘图标时显示窗口并取消吸附
            self.tray_icon.activated.connect(self._on_tray_activated)
            menu = QMenu(self)

            show_setting = QAction("设置", self)
            show_setting.triggered.connect(self.show_settings_dialog)
            menu.addAction(show_setting)

            exit_action = QAction("退出", self)
            exit_action.triggered.connect(QApplication.instance().quit)
            menu.addAction(exit_action)

            self.tray_icon.setContextMenu(menu)
            self.tray_icon.setToolTip("秒回")
            self.tray_icon.show()

        except Exception as e:
            print(f"系统托盘初始化失败: {e}")

    # <============================获取数据方法==============================>

    def load_initial_data(self):
        """加载初始数据"""
        try:
            # 初始化数据适配器
            self.data_adapter = DataAdapter()
            # 初始化API管理器
            self.api_manager = APIManager()

            # 读取本地配置并应用（若存在）
            try:
                local_conf = self.data_adapter.get_local_config_data()
                if isinstance(local_conf, dict):
                    dp = local_conf.get('dock_position')
                    if dp in ('left', 'right'):
                        self.dock_position = dp or self.dock_position
                    da = local_conf.get('dock_apps')
                    if isinstance(da, list):
                        self.dock_apps = da or self.dock_apps
            except Exception as e:
                print(f"读取本地配置失败: {e}")

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
            if self.current_level_one_id not in level_one_list and len(level_one_list) > 0:
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
                    print("云端数据同步成功")
                    return True
                else:
                    print("使用默认数据")
                    return False
        except Exception as e:
            print(f"同步云端数据失败: {e}")
            print("数据同步失败，使用本地数据")
            return False

    def load_current_scripts_data(self, isClear: bool = False):
        """加载当前Tab数据"""
        self.current_scripts_data = self.data_adapter.get_tree_scripts_data(self.current_type_id,
                                                                            self.current_level_one_id)
        self.filtered_scripts = self.current_scripts_data.copy()
        self.update_tree()
        if isClear:
            self.search_edit.clear()

    def save_config(self):
        """保存配置数据"""
        try:
            config = {
                'send_mode': self.send_mode,
                'always_on_top': self.always_on_top,
                'current_user_id': self.current_user_id,
                'is_logged_in': self.is_logged_in,
                'dock_enabled': getattr(self, 'dock_enabled', False),
                'dock_position': getattr(self, 'dock_position', "right"),
                'dock_apps': getattr(self, 'dock_apps', []),
            }
            if self.data_adapter:
                self.data_adapter.save_local_config_data(config)
        except Exception as e:
            print(f'保存配置失败: {e}')

    # 托盘关闭拦截：关闭窗口时隐藏到托盘，不退出程序
    def on_minimize_clicked(self):
        """最小化按钮统一隐藏到托盘"""
        try:
            self.on_dock_changed(False)
            # 最小化直接隐藏，避免被吸附恢复
            QTimer.singleShot(0, self.hide)
        except Exception as e:
            print(f"最小化到托盘失败: {e}")

    # <============================创建界面元素方法==============================>

    def create_ui(self):
        """创建用户界面"""
        # 创建中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        central_widget.setObjectName("main_frame")
        # 确保中央部件也启用鼠标跟踪与悬停事件，从而未按键时能收到 mouseMoveEvent/HoverMove
        central_widget.setMouseTracking(True)
        central_widget.setAttribute(Qt.WidgetAttribute.WA_Hover, True)

        # 主布局
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)  # 减少顶部边距
        main_layout.setSpacing(2)  # 组件之间的间距

        # 创建自定义标题栏
        self.title_bar = CustomTitleBar()
        self.title_bar.setMouseTracking(True)
        main_layout.addWidget(self.title_bar)

        # 连接标题栏信号
        # self.title_bar.close_clicked.connect(self.close)
        self.title_bar.minimize_clicked.connect(self.on_minimize_clicked)
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

        # 自绘树形结构替代原生 QTreeWidget
        self.script_tree = ScriptTree()
        tree_layout.addWidget(self.script_tree)
        # 绑定回调，保持原交互不变：双击、按钮发送、右键菜单（分类/脚本/空白）
        self.script_tree.set_callbacks({
            "on_script_double": lambda c: self.send_script_text(c),
            "on_script_send": lambda c: self.send_script_directly(c),
            "on_context_menu": self._on_script_tree_context_menu
        })

    def create_search_section(self, parent_layout):
        """创建搜索部分"""
        search_group = QWidget()  # 去掉标题
        parent_layout.addWidget(search_group)

        search_layout = QHBoxLayout(search_group)
        search_layout.setContentsMargins(2, 0, 2, 0)

        # 搜索框
        self.search_edit = SearchLineEdit("搜索话术...")  # 缩短placeholder文字
        self.search_edit.textChanged.connect(self.on_search_changed)
        search_layout.addWidget(self.search_edit, 1)

    def create_status_section(self, parent_layout):
        """创建状态栏部分"""
        status_layout = QHBoxLayout()
        parent_layout.addLayout(status_layout)

        # 登录按钮
        self.login_btn = ModernButton("登录", "secondary")
        self.login_btn.clicked.connect(self.show_login_dialog)
        status_layout.addWidget(self.login_btn)

        # 设置按钮
        settings_btn = ModernButton("⚙️", "small")
        settings_btn.setMaximumWidth(32)
        settings_btn.clicked.connect(self.show_settings_dialog)
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
        """更新自绘树形列表"""
        try:
            callbacks = {
                "on_script_double": lambda c: self.send_script_text(c),
                "on_script_send": lambda c: self.send_script_directly(c),
                "on_context_menu": self._on_script_tree_context_menu,
            }
            self.script_tree.render(self.filtered_scripts, callbacks)
        except Exception as e:
            print("渲染自绘树失败:", e)

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
            # 启用吸附
            if self.dock_manager:
                self.dock_manager.enable_docking(self.target_window)
        else:
            # 禁用吸附
            if self.dock_manager:
                self.dock_manager.disable_docking()

        self.save_config()

    def _on_tray_activated(self, reason: QSystemTrayIcon.ActivationReason):
        """系统托盘激活事件：左键双击显示并取消吸附"""
        try:
            if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
                # 取消吸附（先关闭，避免定时器竞态导致再次隐藏/最小化）
                self.on_dock_changed(False)
                # 展示主窗口（保持不进任务栏，因为设置了 Qt.Tool）
                self.showNormal()
                # 同步标题栏按钮状态（如果存在）
                if hasattr(self, "title_bar") and self.title_bar:
                    try:
                        self.title_bar.set_dock_state(False)
                    except Exception:
                        pass
                # 可选：激活到前台，如不需要可以移除以进一步减少闪烁
                self.activateWindow()
        except Exception as e:
            print(f"托盘双击处理失败: {e}")

    def on_lock_changed(self, checked: bool):
        """锁定状态改变"""
        self.position_locked = checked
        self.save_config()

    def on_topmost_changed(self, checked: bool):
        """置顶状态改变（仅使用 Qt 方式）"""
        self.always_on_top = checked
        # 暂停更新，降低闪烁
        self.setUpdatesEnabled(False)

        # 优先用 QWindow 层面切换置顶，减少窗口重建
        wh = self.windowHandle()
        if wh is not None:
            wh.setFlag(Qt.WindowType.WindowStaysOnTopHint, checked)
        else:
            self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, checked)

        # 若窗口不可见或最小化，恢复到正常显示；避免调用 show()/raise_/activateWindow
        if (not self.isVisible()) or (self.windowState() & Qt.WindowState.WindowMinimized):
            self.showNormal()

        # 恢复更新并保存配置
        self.setUpdatesEnabled(True)
        self.save_config()

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
                if len(level_one_list) > 0:
                    self.current_level_one_id = level_one_list[0]['id']
                else:
                    self.current_level_one_id = 0
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

    def _on_script_tree_context_menu(self, info: dict, global_pos):
        """自绘树的右键菜单回调：兼容原有“添加/修改/删除”逻辑"""
        menu = QMenu(self)
        t = info.get("type")
        if t == "blank":
            if not self.current_level_one_id:
                return
            add_title_action = QAction("添加话术标题", self)
            add_title_action.triggered.connect(lambda checked: self.show_add_dialog('level_two', self.current_level_one_id))
            menu.addAction(add_title_action)
            id_list = self.data_adapter.level_one_children_idList_byIds.get((self.current_type_id, self.current_level_one_id), [])
            if len(id_list) > 0:
                add_script_action = QAction("添加话术", self)
                add_script_action.triggered.connect(lambda checked: self.show_add_dialog('script', id_list[0]))
                menu.addAction(add_script_action)
        elif t == "title":
            if self.is_search:
                return
            title_id = info.get("title_id")
            rename_action = QAction("修改话术标题名称", self)
            rename_action.triggered.connect(lambda checked=False, tid=title_id: self.show_edit_dialog('level_two', tid))
            delete_action = QAction("删除话术标题", self)
            delete_action.triggered.connect(lambda checked=False, tid=title_id: self.delete_level_two(tid))
            menu.addAction(rename_action)
            menu.addAction(delete_action)
        elif t == "script":
            script_id = info.get("script_id")
            edit_action = QAction("修改话术", self)
            edit_action.triggered.connect(lambda checked=False, sid=script_id: self.show_edit_dialog('script', sid))
            delete_action = QAction("删除话术", self)
            delete_action.triggered.connect(lambda checked=False, sid=script_id: self.delete_script(sid))
            menu.addAction(edit_action)
            menu.addAction(delete_action)
        if menu.actions():
            menu.exec(global_pos)
        else:
            return

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
            print("❌ 话术内容为空")
            return

        # 检查目标窗口
        if not hasattr(self, 'target_window') or not self.target_window:
            print("❌ 请先选择目标窗口")
            return

        try:
            # 直接使用本地发送逻辑，不依赖 APIManager
            self.send_text_direct(script_content)
            print("✅ 📤 话术已直接发送")
            return
        except Exception as e:
            print(f"❌ 发送错误: {str(e)}")

    # 功能方法
    def send_script_text(self, script: str):
        """发送话术文本"""
        if self.send_mode == "添加到剪贴板":
            pyperclip.copy(script)
            print("已复制到剪贴板")
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
                print("目标窗口已关闭")
                return

            if self.target_window:
                win32gui.ShowWindow(self.target_window, win32con.SW_RESTORE)
                win32gui.SetForegroundWindow(self.target_window)
                time.sleep(0.2)

            pyperclip.copy(text)
            pyautogui.hotkey('ctrl', 'v')
            print("已添加到输入框")

        except Exception as e:
            print(f"添加失败: {str(e)}")

    def send_text_direct(self, text: str):
        """直接发送文本"""
        try:
            if self.target_window and not win32gui.IsWindow(self.target_window):
                print("目标窗口已关闭")
                return

            if self.target_window:
                win32gui.ShowWindow(self.target_window, win32con.SW_RESTORE)
                win32gui.SetForegroundWindow(self.target_window)
                time.sleep(0.2)

            pyperclip.copy(text)
            pyautogui.hotkey('ctrl', 'v')
            time.sleep(0.1)
            pyautogui.press('enter')
            print("已直接发送")

        except Exception as e:
            print(f"发送失败: {str(e)}")

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

            print("已登出")
        except Exception as e:
            QMessageBox.critical(self, "登出失败", f"登出时发生错误: {str(e)}")

    # <============================设置功能相关方法==============================>

    def show_settings_dialog(self):
        """显示设置弹窗"""
        try:
            # 创建或复用弹窗
            if not hasattr(self, 'settings_dialog') or self.settings_dialog is None:
                self.settings_dialog = SettingsDialog(self)

                # 同步发送模式：弹窗改动 -> 主窗口
                self.settings_dialog.send_mode_changed.connect(self.set_send_mode)

                # 新增：吸附初始化与信号接入
                self.settings_dialog.dock_position_changed.connect(self.set_dock_position)
                self.settings_dialog.dock_apps_changed.connect(self.set_dock_enabled_apps)

            # 新增：初始化吸附位置与可吸附软件
            if hasattr(self.settings_dialog, 'set_dock_config'):
                self.settings_dialog.set_dock_config(getattr(self, 'dock_position', "right"),
                                                     getattr(self, 'dock_apps', []))
            # 同步当前发送模式到弹窗
            if hasattr(self.settings_dialog, 'set_send_mode'):
                self.settings_dialog.set_send_mode(getattr(self, 'send_mode', "直接发送"))

            # 展示弹窗（非模态，置顶）
            self.settings_dialog.show()
            self.settings_dialog.raise_()
            self.settings_dialog.activateWindow()
        except Exception as e:
            QMessageBox.critical(self, "错误", f"显示设置弹窗失败：{str(e)}")

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
        print(f"发送模式: {mode}")

    def set_dock_position(self, pos: str):
        """设置吸附位置（left/right）"""
        if pos not in ("left", "right"):
            return
        self.dock_position = pos
        self.save_config()
        print(f"📎 吸附位置: {'左侧' if pos == 'left' else '右侧'}")
        # 若已启用吸附且存在目标窗口，可根据需要刷新吸附
        try:
            # 先设置吸附侧边
            if hasattr(self, 'dock_manager') and self.dock_manager:
                try:
                    self.dock_manager.set_side('left' if pos == 'left' else 'right')
                except Exception as e:
                    print(f"设置吸附侧边失败: {e}")
            if getattr(self, 'dock_enabled', False) and getattr(self, 'dock_manager', None) and getattr(self,
                                                                                                        'target_window',
                                                                                                        None):
                # 仅当当前窗口允许吸附且不是本程序窗口时才刷新
                if self.is_window_allowed_for_dock(self.target_title or "") and not self.is_our_window(
                        self.target_window):
                    self.dock_manager.disable_docking()
                    self.dock_manager.enable_docking(self.target_window)
                else:
                    # 不允许则关闭吸附
                    self.dock_manager.disable_docking()
        except Exception as e:
            print(f"更新吸附位置时刷新失败: {e}")

    def set_dock_enabled_apps(self, apps: list):
        """设置允许吸附的软件列表"""
        # 仅存储并持久化，具体吸附逻辑使用时根据列表判断
        self.dock_apps = list(apps) if isinstance(apps, list) else []
        self.save_config()
        print(f"📎 可吸附软件: {', '.join(self.dock_apps) if self.dock_apps else '未选择'}")
        # 切换允许列表后，如果当前窗口不允许，则关闭吸附
        try:
            if self.dock_enabled and self.dock_manager:
                if not self.is_window_allowed_for_dock(self.target_title or ""):
                    self.dock_manager.disable_docking()
        except Exception as e:
            print(f"更新允许软件列表后处理失败: {e}")

    def is_window_allowed_for_dock(self, title: str) -> bool:
        """判断当前窗口标题是否在允许吸附的软件列表中（基于统一 APPS 配置）"""
        try:
            t = (title or "").lower()
            selected = set(getattr(self, 'dock_apps', []) or [])
            if not selected:
                return False
            result = list(filter(lambda item: item == '全部', selected))
            if len(result) > 0:
                return True
            # 汇总选中项的关键词
            keywords = []
            found = False
            for app in APPS:
                name = app.get("name")
                arr = list(filter(lambda item: item == name, selected))
                if len(arr):
                    kws = app.get("keywords", [])
                    keywords.extend(kws)
            for kw in keywords:
                if kw:  # 确保kw不是空值
                    if kw.lower() == t:
                        found = True
            return found
        except Exception:
            return False

    def is_our_window(self, hwnd: int) -> bool:
        """判断句柄是否属于本程序进程"""
        try:
            import win32process
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            return pid == os.getpid()
        except Exception:
            return False

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
                if self.data_adapter:
                    self.data_adapter.init_data()
                    self.load_data_from_adapter()
                success = self.data_adapter.push_local_scripts_data()
                if success:
                    QMessageBox.information(self, "上传成功", "数据已成功上传到云端！")
                    print("数据上传成功")
                else:
                    QMessageBox.critical(self, "上传失败", "数据上传失败，请稍后重试")
                    print("数据上传失败")
        except Exception as e:
            QMessageBox.critical(self, "上传失败", f"上传时发生错误: {str(e)}")
            print(f"上传失败: {str(e)}")

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
                    print("数据下载成功")
                else:
                    QMessageBox.warning(self, "下载失败", "云端暂无数据或下载失败")
                    print("云端暂无数据")
        except Exception as e:
            QMessageBox.critical(self, "下载失败", f"下载时发生错误: {str(e)}")
            print(f"下载失败: {str(e)}")

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
        """鼠标进入窗口事件：进入后立即根据当前位置更新光标"""
        try:
            from PySide6.QtGui import QCursor
            global_pos = QCursor.pos()
            local_pos = self.mapFromGlobal(global_pos)
            direction = self.get_resize_direction(local_pos)
            self.update_cursor(direction)
        except Exception:
            pass
        super().enterEvent(event)

    def leaveEvent(self, event):
        """鼠标离开窗口事件"""
        self.setCursor(Qt.CursorShape.ArrowCursor)
        super().leaveEvent(event)
        
    def eventFilter(self, obj, event):
        """统一事件过滤器：用于在未按键时也更新光标形状"""
        try:
            if event.type() in (QEvent.Type.MouseMove, QEvent.Type.HoverMove):
                # 将事件位置映射到主窗口坐标系
                if hasattr(event, 'position'):
                    pos = event.position().toPoint()
                elif hasattr(event, 'pos'):
                    pos = event.pos()
                else:
                    pos = None
                
                if pos is not None:
                    # 如果事件来自子控件，需要映射到主窗口坐标
                    if isinstance(obj, QWidget):
                        local_to_window = obj.mapTo(self, pos)
                        direction = self.get_resize_direction(local_to_window)
                        self.update_cursor(direction)
                        return False
        except Exception:
            pass
        return super().eventFilter(obj, event)

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
                add_dialog.content_added_signal.connect(lambda level_two_id, content, title: self.add_script_content_with_color(level_two_id, content, title, getattr(add_dialog, 'selected_bg_color', '')))

            # 连接弹窗关闭信号
            add_dialog.accepted.connect(lambda: print("✅ 内容添加成功"))
            add_dialog.rejected.connect(lambda: print("❌ 取消添加"))

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
                    id_list = self.data_adapter.type_children_idList_byIds.get(type_id, [])
                    if not self.current_level_one_id and len(id_list) > 0:
                        self.current_level_one_id = id_list[0]

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
        """添加话术内容回调（兼容旧逻辑，无颜色）"""
        try:
            if self.data_adapter:
                success = self.data_adapter.add_script(level_two_id, content=script_content, title=script_title_value, bgColor='')
                if success:
                    self.update_ui('add_script')
                else:
                    QMessageBox.warning(self, "警告", "添加失败")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"添加失败: {str(e)}")

    def add_script_content_with_color(self, level_two_id: str,
                                      script_content: str, script_title_value: str, bg_color: str):
        """添加话术内容回调（包含背景色）"""
        try:
            if self.data_adapter:
                success = self.data_adapter.add_script(level_two_id, content=script_content, title=script_title_value, bgColor=(bg_color or ''))
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
                edit_dialog.content_edited_signal.connect(lambda script_id, new_value, script_title: self.edit_script_with_color(script_id, new_value, script_title, getattr(edit_dialog, 'selected_bg_color', None)))

            # 连接弹窗关闭信号
            edit_dialog.accepted.connect(lambda: print("✅ 编辑成功"))
            edit_dialog.rejected.connect(lambda: print("❌ 取消编辑"))

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
        """编辑话术内容（兼容旧逻辑，不改颜色）"""
        try:
            if self.data_adapter:
                success = self.data_adapter.edit_script(script_id, content=new_value, title=script_title_value)
                if success:
                    self.update_ui('edit_script')
                else:
                    QMessageBox.warning(self, "警告", "编辑失败：未找到该话术或ID无效")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"编辑话术内容失败: {str(e)}")

    def edit_script_with_color(self, script_id: int, new_value: str, script_title_value: str, bg_color: Optional[str]):
        """编辑话术内容（可修改背景色）"""
        try:
            if self.data_adapter:
                success = self.data_adapter.edit_script(script_id, content=new_value, title=script_title_value, bgColor=bg_color)
                if success:
                    self.update_ui('edit_script')
                else:
                    QMessageBox.warning(self, "警告", "编辑失败：未找到该话术或ID无效")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"编辑话术内容失败: {str(e)}")

    # <============================删除功能（话术分类、话术标题、话术内容）==============================>

    def delete_level_one(self, level_one_id: int, level_one_name: str):
        """删除话术分类（使用 DataAdapter）"""
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Question)
        msg.setWindowTitle("确认删除")
        msg.setText(f"确定要删除一级分类 '{level_one_name}' 及其所有话术吗？")
        msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        # 设置中文按钮文本
        yes_btn = msg.button(QMessageBox.Yes)
        no_btn = msg.button(QMessageBox.No)
        if yes_btn:
            yes_btn.setText("确定")
        if no_btn:
            no_btn.setText("取消")
        reply = msg.exec()

        if reply == QMessageBox.Yes:
            try:
                success = self.data_adapter.delete_level_one(level_one_id)
                if success:
                    id_list = self.data_adapter.type_children_idList_byIds.get(self.current_type_id)
                    if self.current_level_one_id == level_one_id and len(id_list) > 0:
                        self.current_level_one_id = id_list[0]
                    else:
                        self.current_level_one_id = 0

                    self.update_ui('delete_level_one')
                else:
                    QMessageBox.warning(self, "错误", "删除失败：未找到该分类或ID无效")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"删除失败: {str(e)}")

    def delete_level_two(self, level_two_id: int, level_two_name: str):
        """删除分类标题（使用 DataAdapter）"""
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Question)
        msg.setWindowTitle("确认删除")
        msg.setText(f"确定要删除二级分类 '{level_two_name}' 及其所有话术吗？")
        msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        # 设置中文按钮文本
        yes_btn = msg.button(QMessageBox.Yes)
        no_btn = msg.button(QMessageBox.No)
        if yes_btn:
            yes_btn.setText("确定")
        if no_btn:
            no_btn.setText("取消")
        reply = msg.exec()

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
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Question)
        msg.setWindowTitle("确认删除")
        msg.setText(f"确定要删除话术:\n{content[:100]}{'...' if len(content) > 100 else ''}")
        msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        # 设置中文按钮文本
        yes_btn = msg.button(QMessageBox.Yes)
        no_btn = msg.button(QMessageBox.No)
        if yes_btn:
            yes_btn.setText("确定")
        if no_btn:
            no_btn.setText("取消")
        reply = msg.exec()

        if reply == QMessageBox.Yes:
            try:
                success = self.data_adapter.delete_script(script_id)
                if success:
                    self.update_ui('delete_script')
                else:
                    QMessageBox.warning(self, "错误", "找不到要删除的话术！")
            except Exception as e:
                print('ValueError', e)
                QMessageBox.warning(self, "错误", "找不到要删除的话术！")

UNIQUE_KEY = "chatassistant_single_instance"
def setup_single_instance():
    """确保单实例运行；已有实例则连接并退出，否则启动本地服务器"""
    socket = QLocalSocket()
    socket.connectToServer(UNIQUE_KEY)
    if socket.waitForConnected(100):
        try:
            socket.write(b"raise")
            socket.flush()
            socket.waitForBytesWritten(100)
        except Exception:
            pass
        socket.disconnectFromServer()
        return None
    server = QLocalServer()
    try:
        QLocalServer.removeServer(UNIQUE_KEY)
    except Exception:
        pass
    if not server.listen(UNIQUE_KEY):
        return None
    return server


def bring_to_front(win):
    """唤起主窗口"""
    try:
        win.showNormal()
        win.raise_()
        win.activateWindow()
    except Exception:
        pass


def main():
    """主函数"""
    # 创建 Qt 应用
    app = QApplication(sys.argv)
    QApplication.setQuitOnLastWindowClosed(False)

    # 单实例控制：如检测到已有实例，直接退出；否则监听本地服务器
    server = setup_single_instance()
    if server is None:
        # 已有实例：二次启动仅用于唤醒，直接退出当前进程
        sys.exit(0)

    # 设置应用程序信息
    app.setApplicationName("秒回")
    app.setApplicationVersion("2.0")
    app.setOrganizationName("秒回团队")

    # 应用主题（内嵌优先，开发环境自动回退）
    applied = False
    try:
        import styles_rc  # 可选：打包有该模块，开发环境可能没有
    except ImportError:
        styles_rc = None

    if styles_rc:
        try:
            from PySide6.QtCore import QFile
            f = QFile(":/styles/modern_optimized.qss")
            if f.open(QFile.ReadOnly | QFile.Text):
                app.setStyleSheet(bytes(f.readAll()).decode("utf-8"))
                f.close()
                print("✅ 已应用内嵌样式")
                applied = True
        except Exception as e:
            print(f"⚠️ 内嵌样式加载失败: {e}")

    if not applied:
        try:
            theme_manager.apply_theme(app, "modern_optimized")
            print("✅ 本地开发使用文件样式")
        except Exception as e:
            print(f"⚠️ 主题加载失败: {e}")

    # 创建主窗口
    window = AssistantMainWindow()

    # 新连接时唤起主窗口
    if server:
        def _on_new_connection():
            try:
                sock = server.nextPendingConnection()
                bring_to_front(window)
                if sock:
                    sock.close()
            except Exception:
                bring_to_front(window)

        server.newConnection.connect(_on_new_connection)

    window.show()

    # 运行应用程序事件循环
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
