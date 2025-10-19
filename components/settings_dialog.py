from PySide6.QtWidgets import (
    QDialog, QWidget, QListWidget, QListWidgetItem, QStackedWidget,
    QHBoxLayout, QVBoxLayout, QFormLayout, QGridLayout, QLabel, QCheckBox,
    QComboBox, QPushButton, QRadioButton, QButtonGroup, QScrollArea
)
from PySide6.QtCore import Qt, Signal, QFile, QIODevice
import os
from typing import Optional, List
from utils.dock_apps import APPS


class DockSettingsWidget(QWidget):
    """吸附设置页：选择吸附位置 + 选择支持吸附的软件"""
    # 新信号
    dock_position_changed = Signal(str)   # "left" | "right"
    dock_apps_changed = Signal(list)      # 选中的软件列表

    def __init__(self, parent=None):
        super().__init__(parent)
        # 顶部对齐：外层垂直布局 + 表单布局
        col = QVBoxLayout(self)
        col.setContentsMargins(10, 10, 10, 10)
        col.setSpacing(0)

        form = QFormLayout()
        form.setContentsMargins(0, 0, 0, 0)
        form.setSpacing(4)

        # 吸附位置：左/右（默认右）
        pos_row = QHBoxLayout()
        pos_row.setSpacing(8)
        self.rb_left = QRadioButton("左侧")
        self.rb_right = QRadioButton("右侧")
        self.rb_right.setChecked(True)
        pos_group = QButtonGroup(self)
        pos_group.addButton(self.rb_left)
        pos_group.addButton(self.rb_right)
        pos_row.addWidget(self.rb_left)
        pos_row.addWidget(self.rb_right)
        # 单选整体左对齐，不做等分
        pos_row.setAlignment(Qt.AlignmentFlag.AlignLeft)
        pos_wrap = QWidget()
        pos_wrap.setLayout(pos_row)
        form.addRow("吸附位置:", pos_wrap)

        # 支持吸附的软件列表（标题单独一行，名称每行最多3个，左对齐）
        # 标题与滚动列表合并为一行，减少中间空白
        apps_header = QLabel("请选择需要吸附的软件:")
        apps_header.setStyleSheet("padding:0; margin:0;")

        # 动态生成复选框：每行最多3个，左对齐
        grid = QGridLayout()
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(6)
        self.cb_by_name = {}
        for idx, app in enumerate(APPS):
            name = app.get("name", "")
            cb = QCheckBox(name)
            self.cb_by_name[name] = cb
            r, c = divmod(idx, 3)
            grid.addWidget(cb, r, c, Qt.AlignmentFlag.AlignLeft)

        apps_wrap = QWidget()
        apps_wrap.setLayout(grid)

        # 加滚动容器：超过固定高度时显示竖向滚动，水平滚动禁用
        scroll = QScrollArea()
        scroll.setObjectName("apps_scroll")
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setMaximumHeight(240)  # 可按需调整
        scroll.setWidget(apps_wrap)

        # 合并容器：标题 + 滚动区
        section = QWidget()
        section_layout = QVBoxLayout(section)
        section_layout.setContentsMargins(0, 0, 0, 0)
        section_layout.setSpacing(4)
        section_layout.addWidget(apps_header, 0, Qt.AlignmentFlag.AlignLeft)
        section_layout.addWidget(scroll)

        form.addRow(section)

        # tip = QLabel("说明：选择吸附位置（左/右），并勾选允许吸附的软件。")
        # tip.setWordWrap(on=True)
        # tip.setStyleSheet("color:#666; font-size:12px;")
        # form.addRow(tip)

        # 将表单加入外层布局并添加拉伸，使整体贴顶
        col.addLayout(form)
        col.addStretch(1)

        # 信号：位置变化
        self.rb_left.toggled.connect(lambda checked: checked and self.dock_position_changed.emit("left"))
        self.rb_right.toggled.connect(lambda checked: checked and self.dock_position_changed.emit("right"))

        # 信号：软件选择变化
        def emit_apps():
            selected = [name for name, cb in self.cb_by_name.items() if cb.isChecked()]
            self.dock_apps_changed.emit(selected)

        for cb in self.cb_by_name.values():
            cb.toggled.connect(emit_apps)

    # 兼容旧接口（不再使用，仅为避免外部调用报错）
    def set_values(self, enabled: bool, gap: int):
        pass

    # 新接口：设置当前配置
    def set_config(self, position: str = "right", apps: Optional[List[str]] = None):
        if position == "left":
            self.rb_left.setChecked(True)
        else:
            self.rb_right.setChecked(True)
        apps = apps or []
        # 根据 name 勾选对应项
        for name, cb in getattr(self, "cb_by_name", {}).items():
            cb.setChecked(name in apps)


class SendSettingsWidget(QWidget):
    """发送设置页：一行选择框（下拉）"""
    send_mode_changed = Signal(str)  # "直接发送" | "添加到输入框" | "添加到剪贴板"

    def __init__(self, parent=None):
        super().__init__(parent)
        # 顶部一行 + 底部拉伸，控件贴顶显示
        col = QVBoxLayout(self)
        col.setContentsMargins(0,0,0,0)
        col.setSpacing(4)

        row = QHBoxLayout()
        row.setSpacing(4)

        label = QLabel("发送模式:")
        label.setObjectName("send_mode_label")
        label.setFixedHeight(22)
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["直接发送", "添加到输入框", "添加到剪贴板"])
        # 更紧凑尺寸
        self.mode_combo.setFixedHeight(22)
        self.mode_combo.setMinimumWidth(160)

        row.addWidget(label, 0, Qt.AlignmentFlag.AlignVCenter)
        row.addWidget(self.mode_combo, 1, Qt.AlignmentFlag.AlignVCenter)

        col.addLayout(row)
        col.addStretch(1)

        # 信号
        self.mode_combo.currentTextChanged.connect(self.send_mode_changed.emit)

        # 默认值
        self.mode_combo.setCurrentText("直接发送")

    def set_mode(self, mode: str):
        """设置当前发送模式"""
        idx = self.mode_combo.findText(mode)
        if idx >= 0:
            self.mode_combo.setCurrentIndex(idx)


class SettingsDialog(QDialog):
    """设置弹窗：左侧菜单，右侧内容"""
    # 对外信号
    dock_position_changed = Signal(str)   # "left" | "right"
    dock_apps_changed = Signal(list)      # 选中的软件列表

    # 新增：发送模式信号（与主窗口联动）
    send_mode_changed = Signal(str)  # "直接发送" | "添加到输入框" | "添加到剪贴板"

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("设置")
        self.setModal(False)
        self.setFixedSize(600, 420)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.WindowStaysOnTopHint)

        self._load_stylesheet()

        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # 左侧菜单
        self.menu = QListWidget()
        self.menu.setFixedWidth(100)
        self.menu.setObjectName("settings_menu")
        item1 = QListWidgetItem("发送设置")
        item1.setData(Qt.ItemDataRole.UserRole, 0)
        self.menu.addItem(item1)
        item2 = QListWidgetItem("吸附设置")
        item2.setData(Qt.ItemDataRole.UserRole, 1)
        self.menu.addItem(item2)
        # 居中所有菜单项（批量设置）
        for i in range(self.menu.count()):
            it = self.menu.item(i)
            if it is not None:
                it.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

        # 右侧内容
        self.stack = QStackedWidget()
        self.stack.setObjectName("settings_stack")

        self.dock_page = DockSettingsWidget()
        self.send_page = SendSettingsWidget()

        self.stack.addWidget(self.send_page)
        self.stack.addWidget(self.dock_page)

        # 底部操作区（可选）
        right_wrap = QVBoxLayout()
        right_wrap.setContentsMargins(0, 0, 0, 0)
        right_wrap.setSpacing(0)
        right_container = QWidget()
        right_container.setObjectName("settings_right")
        right_container.setLayout(QVBoxLayout())
        right_container.layout().setContentsMargins(12, 12, 12, 12)
        right_container.layout().setSpacing(12)
        right_container.layout().addWidget(self.stack)

        # 底部按钮
        # btn_bar = QHBoxLayout()
        # btn_bar.setContentsMargins(12, 8, 12, 12)
        # btn_bar.addStretch()
        # self.close_btn = QPushButton("关闭")
        # self.close_btn.setObjectName("close_btn")
        # btn_bar.addWidget(self.close_btn)

        # bottom = QWidget()
        # bottom.setLayout(btn_bar)

        # 右侧整体容器
        right_area = QVBoxLayout()
        right_area.setContentsMargins(0, 0, 0, 0)
        right_area.setSpacing(0)
        right_area.addWidget(right_container, 1)
        # right_area.addWidget(bottom, 0)

        right = QWidget()
        right.setLayout(right_area)

        root.addWidget(self.menu, 0)
        root.addWidget(right, 1)

        # 交互
        def _on_menu_changed(current: QListWidgetItem, previous: QListWidgetItem):
            if current is None:
                return
            idx = current.data(Qt.ItemDataRole.UserRole)
            # 兜底：若未绑定索引，则按当前位置
            if idx is None:
                idx = self.menu.row(current)
            self.stack.setCurrentIndex(int(idx))

        self.menu.currentItemChanged.connect(_on_menu_changed)
        # 默认选中第一项并触发切换
        self.menu.setCurrentRow(0)
        # self.close_btn.clicked.connect(self.close)

        # 子页信号透传（使用新信号）
        self.dock_page.dock_position_changed.connect(self.dock_position_changed.emit)
        self.dock_page.dock_apps_changed.connect(self.dock_apps_changed.emit)

        # 新的发送模式信号
        self.send_page.send_mode_changed.connect(self.send_mode_changed.emit)

    def _load_stylesheet(self):
        try:
            # 优先从资源文件读取
            f = QFile(":/styles/settings_dialog.qss")
            if f.open(QIODevice.OpenModeFlag.ReadOnly | QIODevice.OpenModeFlag.Text):
                try:
                    qss = bytes(f.readAll()).decode("utf-8")
                    self.setStyleSheet(qss)
                    return
                finally:
                    f.close()
            # 回退到磁盘路径（开发环境）
            qss_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "styles", "settings_dialog.qss")
            if os.path.exists(qss_path):
                with open(qss_path, 'r', encoding='utf-8') as f2:
                    self.setStyleSheet(f2.read())
        except Exception as e:
            print(f"加载设置弹窗样式失败: {e}")

    # 提供便捷设置/读取当前值的接口（供外部初始化/持久化）
    def set_dock_values(self, enabled: bool = False, gap: int = 0):
        # 兼容旧方法：不生效，仅避免旧调用报错
        pass

    def set_dock_config(self, position: str = "right", apps: Optional[List[str]] = None):
        """设置吸附位置与支持软件"""
        self.dock_page.set_config(position, apps or [])

    def set_send_values(self, hotkey: str = "Enter", delay_ms: int = 0, enter_to_send: bool = True):
        # 兼容旧接口：不再使用这些参数，保持不报错
        pass

    def set_send_mode(self, mode: str = "直接发送"):
        """设置发送模式（推荐使用新接口）"""
        self.send_page.set_mode(mode)