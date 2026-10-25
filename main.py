"""磨针C盘清理 - Windows桌面清理工具

使用 Flet 0.28.x 构建的现代 Windows 11 风格桌面应用。
基于公开源码的独立免费简化版：缓存清理、文件查找与只读空间分析。
"""

import flet as ft
from theme import COLORS
from components.header import Header
from components.sidebar import Sidebar
from components.scan_panel import ScanPanel


def main(page: ft.Page):
    """应用主入口"""

    # 窗口配置
    page.title = "磨针清理 · 免费简化版 0.1.0"
    page.window.width = 1280
    page.window.height = 720
    page.window.min_width = 960
    page.window.min_height = 640
    page.window.maximized = False
    page.padding = 0
    page.spacing = 0
    page.theme_mode = ft.ThemeMode.LIGHT
    page.bgcolor = COLORS["background"]
    page.theme = ft.Theme(
        font_family="Microsoft YaHei",
    )

    # 主扫描面板（需要 page 引用用于对话框和异步操作）
    scan_panel = ScanPanel(page)

    # 菜单切换回调
    async def on_menu_change(index: int, title: str):
        return scan_panel.set_scan_type(index)

    # 侧边栏
    sidebar = Sidebar(on_menu_change=on_menu_change)

    # 顶部导航栏
    header = Header(page)

    # 整体布局
    page.add(
        ft.Column(
            controls=[
                header,
                ft.Row(
                    controls=[
                        sidebar,
                        scan_panel,
                    ],
                    spacing=0,
                    expand=True,
                ),
            ],
            spacing=0,
            expand=True,
        )
    )

    page.update()


if __name__ == "__main__":
    ft.app(target=main)
