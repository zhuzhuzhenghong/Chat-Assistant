"""
窗口吸附管理器 - 实现窗口自动吸附功能
"""
import win32gui
import win32con
from PySide6.QtCore import QTimer, QObject, Signal
from PySide6.QtWidgets import QWidget
from typing import Optional, Tuple


class WindowDockManager(QObject):
    """窗口吸附管理器"""

    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        self.main_window = main_window
        self.target_window_handle = None
        self.is_docking_enabled = False
        self.dock_gap = 0  # 吸附间隔，默认1px
        self.dock_timer = QTimer()
        self.dock_timer.timeout.connect(self.update_dock_position)
        self.dock_timer.setInterval(20)  # 20ms更新一次

        # 窗口位置缓存
        self.last_target_rect = None
        self.is_docking = False
        # 吸附侧边：'right' 或 'left'
        self.side = "right"

    def enable_docking(self, target_window_handle: int):
        """启用窗口吸附"""
        if not target_window_handle:
            return

        self.target_window_handle = target_window_handle
        self.is_docking_enabled = True

        # 立即执行一次吸附
        self.update_dock_position()

        # 启动定时器监控目标窗口
        self.dock_timer.start()

    def disable_docking(self):
        """禁用窗口吸附"""
        self.is_docking_enabled = False
        self.target_window_handle = None
        self.dock_timer.stop()
        self.last_target_rect = None

    def set_side(self, side: str):
        """设置吸附侧边：'left' 或 'right'"""
        if side not in ("left", "right"):
            return
        self.side = side

    def get_window_rect(self, window_handle: int) -> Optional[Tuple[int, int, int, int]]:
        """获取窗口矩形区域"""
        try:
            if not win32gui.IsWindow(window_handle):
                return None

            rect = win32gui.GetWindowRect(window_handle)
            return rect  # (left, top, right, bottom)
        except Exception as e:
            print(f"获取窗口矩形失败: {e}")
            return None

    def is_window_minimized(self, window_handle: int) -> bool:
        """检查窗口是否最小化"""
        try:
            placement = win32gui.GetWindowPlacement(window_handle)
            return placement[1] == win32con.SW_SHOWMINIMIZED
        except:
            return False

    def is_window_visible(self, window_handle: int) -> bool:
        """检查窗口是否可见"""
        try:
            return bool(win32gui.IsWindowVisible(window_handle))
        except:
            return False

    def calculate_dock_position(self, target_rect: Tuple[int, int, int, int]) -> Tuple[int, int, int, int]:
        """计算吸附位置（支持左/右侧）"""
        target_left, target_top, target_right, target_bottom = target_rect

        # 获取主窗口当前大小
        main_window_size = self.main_window.size()
        main_width = main_window_size.width()
        main_height = main_window_size.height()

        # 计算目标窗口的高度
        target_height = target_bottom - target_top

        # 根据侧边计算吸附位置
        if getattr(self, "side", "right") == "left":
            # 目标窗口左侧：主窗口贴在目标窗口左边，预留间隔
            dock_x = target_left - self.dock_gap - main_width
        else:
            # 目标窗口右侧：主窗口贴在目标窗口右边，预留间隔
            dock_x = target_right + self.dock_gap

        dock_y = target_top
        dock_width = main_width
        dock_height = target_height  # 高度与目标窗口保持一致

        return (dock_x, dock_y, dock_width, dock_height)

    def update_dock_position(self):
        """更新吸附位置"""
        if not self.is_docking_enabled or not self.target_window_handle:
            return

        # 检查目标窗口是否仍然有效
        if not self.is_window_visible(self.target_window_handle):
            print("目标窗口不可见，停止吸附")
            self.disable_docking()
            return

        # 检查目标窗口是否最小化
        if self.is_window_minimized(self.target_window_handle):
            # 目标窗口最小化时，隐藏主窗口或最小化
            if not self.main_window.isMinimized():
                self.main_window.showMinimized()
            return
        else:
            # 目标窗口恢复时，恢复主窗口
            if self.main_window.isMinimized():
                self.main_window.showNormal()

        # 获取目标窗口位置
        target_rect = self.get_window_rect(self.target_window_handle)
        if not target_rect:
            print("无法获取目标窗口位置")
            return

        # 检查目标窗口位置是否发生变化
        if self.last_target_rect == target_rect:
            return

        self.last_target_rect = target_rect

        # 计算新的吸附位置
        dock_x, dock_y, dock_width, dock_height = self.calculate_dock_position(target_rect)

        # 防止递归调用
        if self.is_docking:
            return

        self.is_docking = True

        try:
            # 移动和调整主窗口大小
            self.main_window.setGeometry(dock_x, dock_y, dock_width, dock_height)

        except Exception as e:
            print(f"更新吸附位置失败: {e}")
        finally:
            self.is_docking = False

    def get_target_window_title(self) -> str:
        """获取目标窗口标题"""
        if not self.target_window_handle:
            return ""

        try:
            return win32gui.GetWindowText(self.target_window_handle)
        except:
            return ""

    def is_docking_active(self) -> bool:
        """检查吸附是否激活"""
        return self.is_docking_enabled and self.target_window_handle is not None
