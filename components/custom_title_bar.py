"""
自定义标题栏组件
包含窗口控制按钮和功能切换按钮
"""

from PySide6.QtWidgets import (QWidget, QHBoxLayout, QLabel, QPushButton,
                               QSizePolicy, QSpacerItem)
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QIcon, QPixmap, QPainter


class IconButton(QPushButton):
    """自定义图标按钮"""

    def __init__(self, tooltip="", parent=None,
                 icon_path_on=None, icon_path_off=None, icon_size=16):
        super().__init__(parent)
        self.icon_path_on = icon_path_on
        self.icon_path_off = icon_path_off
        self.icon_size = icon_size
        self.is_checked = False

        # 设置按钮属性
        self.setFixedSize(24, 24)
        self.setToolTip(tooltip)
        self.setCheckable(True)
        self.update_icon()

        # 连接信号
        self.toggled.connect(self.on_toggled)

        # 设置样式
        self.setStyleSheet("""
            QPushButton {
                border: none;
                background: transparent;
                color: #333;
                font-size: 14px;
                font-weight: bold;
                border-radius: 12px;
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 0.2);
            }
            QPushButton:pressed {
                background: rgba(255, 255, 255, 0.3);
            }
        """)

    def on_toggled(self, checked):
        """切换状态"""
        self.is_checked = checked
        self.update_icon()

    def update_icon(self):
        """更新图标"""
        path = self.icon_path_on if self.is_checked else self.icon_path_off
        # 设置图标
        self.setIcon(QIcon(QPixmap(path)))
        self.setIconSize(QSize(self.icon_size, self.icon_size))
        # 清空文本以显示图标
        self.setText("")


class WindowControlButton(QPushButton):
    """窗口控制按钮"""

    def __init__(self, button_type="close", parent=None):
        super().__init__(parent)
        self.button_type = button_type

        # 设置按钮属性
        self.setFixedSize(24, 24)

        # 设置图标和样式
        if button_type == "close":
            self.setText("✕")
            self.setToolTip("关闭")
            self.setStyleSheet("""
                QPushButton {
                    border: none;
                    background: transparent;
                    color: #333;
                    font-size: 12px;
                    font-weight: bold;
                    border-radius: 12px;
                }
                QPushButton:hover {
                    background: #ff4757;
                    color: white;
                }
                QPushButton:pressed {
                    background: #ff3838;
                }
            """)
        elif button_type == "minimize":
            self.setText("−")
            self.setToolTip("最小化")
            self.setStyleSheet("""
                QPushButton {
                    border: none;
                    background: transparent;
                    color: #333;
                    font-size: 14px;
                    font-weight: bold;
                    border-radius: 12px;
                }
                QPushButton:hover {
                    background: rgba(255, 255, 255, 0.2);
                }
                QPushButton:pressed {
                    background: rgba(255, 255, 255, 0.3);
                }
            """)


class CustomTitleBar(QWidget):
    """自定义标题栏"""

    # 信号定义
    close_clicked = Signal()
    minimize_clicked = Signal()
    dock_toggled = Signal(bool)
    lock_toggled = Signal(bool)
    topmost_toggled = Signal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()

    def setup_ui(self):
        """设置UI"""
        # 设置固定高度
        self.setFixedHeight(32)

        # 创建布局
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(4)

        # 标题标签
        self.title_label = QLabel("秒回")
        self.title_label.setStyleSheet("""
            QLabel {
                color: #333;
                font-size: 12px;
                font-weight: bold;
            }
        """)

        # 功能按钮
        self.dock_btn = IconButton(tooltip="窗口吸附",
                                   icon_path_on="static/icon/xifu.png",
                                   icon_path_off="static/icon/weixifu.png",
                                   icon_size=16)
        self.lock_btn = IconButton(tooltip="锁定位置",
                                   icon_path_on="static/icon/suoding.png",
                                   icon_path_off="static/icon/weisuoding.png",
                                   icon_size=16)
        self.topmost_btn = IconButton(tooltip="锁定位置",
                                      icon_path_on="static/icon/zhiding.png",
                                      icon_path_off="static/icon/weizhiding.png",
                                      icon_size=16)

        # 窗口控制按钮
        self.minimize_btn = WindowControlButton("minimize")
        self.close_btn = WindowControlButton("close")

        # 添加到布局
        layout.addWidget(self.title_label)
        layout.addItem(QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))
        layout.addWidget(self.dock_btn)
        layout.addWidget(self.lock_btn)
        layout.addWidget(self.topmost_btn)
        layout.addWidget(self.minimize_btn)
        # layout.addWidget(self.close_btn)

        # 连接信号
        self.close_btn.clicked.connect(self.close_clicked.emit)
        self.minimize_btn.clicked.connect(self.minimize_clicked.emit)
        self.dock_btn.toggled.connect(self.dock_toggled.emit)
        self.lock_btn.toggled.connect(self.lock_toggled.emit)
        self.topmost_btn.toggled.connect(self.topmost_toggled.emit)

        # 设置标题栏样式
        self.setStyleSheet("""
            CustomTitleBar {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                            stop:0 rgba(161, 196, 253, 0.8), 
                            stop:1 rgba(194, 233, 255, 0.8));
                border-bottom: 1px solid rgba(255, 255, 255, 0.3);
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
            }
        """)

    def set_dock_state(self, enabled):
        """设置吸附状态"""
        self.dock_btn.setChecked(enabled)

    def set_lock_state(self, enabled):
        """设置锁定状态"""
        self.lock_btn.setChecked(enabled)

    def set_topmost_state(self, enabled):
        """设置置顶状态"""
        self.topmost_btn.setChecked(enabled)
