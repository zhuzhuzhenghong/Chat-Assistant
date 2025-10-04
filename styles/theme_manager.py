"""
主题管理器 - 支持多主题切换
"""
from pathlib import Path
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QSettings
from typing import Dict, List


class ThemeManager:
    """主题管理器类"""
    
    def __init__(self):
        self.styles_dir = Path(__file__).parent
        self.settings = QSettings("聚雍宝", "ThemeSettings")
        self.current_theme = self.settings.value("current_theme", "modern")
        
        # 可用主题列表
        self.available_themes = {
            "modern": {
                "name": "现代浅色",
                "file": "modern_style.qss",
                "description": "清新的浅色主题，适合日常使用"
            },
            "modern_optimized": {
                "name": "优化现代主题",
                "file": "modern_optimized.qss", 
                "description": "更加精美的现代化主题，推荐使用"
            },
            "dark": {
                "name": "深色主题", 
                "file": "dark_style.qss",
                "description": "护眼的深色主题，适合夜间使用"
            },
            "dark_optimized": {
                "name": "优化深色主题",
                "file": "dark_optimized.qss",
                "description": "更加精美的深色主题，护眼且美观"
            }
        }
    
    def get_available_themes(self) -> Dict[str, Dict[str, str]]:
        """获取可用主题列表"""
        return self.available_themes
    
    def get_current_theme(self) -> str:
        """获取当前主题"""
        return self.current_theme
    
    def load_theme(self, theme_name: str) -> str:
        """
        加载指定主题的样式表
        
        Args:
            theme_name: 主题名称
            
        Returns:
            样式表字符串
        """
        if theme_name not in self.available_themes:
            print(f"警告: 主题 {theme_name} 不存在，使用默认主题")
            theme_name = "modern"
        
        theme_info = self.available_themes[theme_name]
        style_file = self.styles_dir / theme_info["file"]
        
        if not style_file.exists():
            print(f"警告: 样式文件 {style_file} 不存在")
            return ""
        
        try:
            with open(style_file, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            print(f"加载主题文件失败: {e}")
            return ""
    
    def apply_theme(self, app: QApplication, theme_name: str):
        """
        应用主题到应用程序
        
        Args:
            app: QApplication 实例
            theme_name: 主题名称
        """
        style_sheet = self.load_theme(theme_name)
        if style_sheet:
            app.setStyleSheet(style_sheet)
            self.current_theme = theme_name
            self.save_current_theme()
            print(f"已应用 {self.available_themes[theme_name]['name']} 主题")
        else:
            print("应用主题失败，使用系统默认样式")
    
    def save_current_theme(self):
        """保存当前主题设置"""
        self.settings.setValue("current_theme", self.current_theme)
    
    def get_theme_colors(self, theme_name: str = None) -> Dict[str, str]:
        """
        获取指定主题的颜色调色板
        
        Args:
            theme_name: 主题名称，如果为None则使用当前主题
            
        Returns:
            颜色字典
        """
        if theme_name is None:
            theme_name = self.current_theme
        
        # 根据主题返回不同的颜色配置
        if theme_name == "dark":
            return {
                "primary": "#3498db",
                "primary_dark": "#2980b9", 
                "success": "#2ecc71",
                "success_dark": "#27ae60",
                "danger": "#e74c3c",
                "danger_dark": "#c0392b",
                "warning": "#f39c12",
                "warning_dark": "#e67e22",
                "info": "#17a2b8",
                "light": "#34495e",
                "dark": "#2c3e50",
                "secondary": "#95a5a6",
                "border": "#4a5568",
                "text": "#e1e8ed",
                "text_muted": "#95a5a6",
                "background": "#34495e",
                "background_alt": "#2c3e50"
            }
        else:  # modern 或其他浅色主题
            return {
                "primary": "#3498db",
                "primary_dark": "#2980b9",
                "success": "#2ecc71", 
                "success_dark": "#27ae60",
                "danger": "#e74c3c",
                "danger_dark": "#c0392b",
                "warning": "#f39c12",
                "warning_dark": "#e67e22",
                "info": "#17a2b8",
                "light": "#f8f9fa",
                "dark": "#2c3e50",
                "secondary": "#95a5a6",
                "border": "#e1e8ed",
                "text": "#2c3e50",
                "text_muted": "#7f8c8d",
                "background": "#ffffff",
                "background_alt": "#f8f9fa"
            }
    
    def create_custom_button_style(self, button_type: str = "default", theme_name: str = None) -> str:
        """
        创建自定义按钮样式
        
        Args:
            button_type: 按钮类型
            theme_name: 主题名称
            
        Returns:
            按钮样式字符串
        """
        colors = self.get_theme_colors(theme_name)
        
        base_style = """
            QPushButton {
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: 500;
                font-size: 9pt;
                min-height: 20px;
            }
        """
        
        type_styles = {
            "default": f"""
                QPushButton {{
                    background-color: {colors['primary']};
                    color: white;
                }}
                QPushButton:hover {{
                    background-color: {colors['primary_dark']};
                }}
            """,
            "primary": f"""
                QPushButton {{
                    background-color: {colors['success']};
                    color: white;
                    font-weight: 600;
                }}
                QPushButton:hover {{
                    background-color: {colors['success_dark']};
                }}
            """,
            "danger": f"""
                QPushButton {{
                    background-color: {colors['danger']};
                    color: white;
                }}
                QPushButton:hover {{
                    background-color: {colors['danger_dark']};
                }}
            """
        }
        
        return base_style + type_styles.get(button_type, type_styles["default"])


# 全局主题管理器实例
theme_manager = ThemeManager()