"""磨针C盘清理 - Windows桌面清理工具

使用 Flet 0.28.x 构建的现代 Windows 11 风格桌面应用。
支持基础清理、系统清理、微信/QQ清理、软件占用查询、大文件/重复文件查找等。
"""

import flet as ft
from theme import COLORS
from components.header import Header
from components.sidebar import Sidebar
from components.scan_panel import ScanPanel


def main(page: ft.Page):
    """应用主入口"""

    # 窗口配置
    page.title = "磨针C盘清理(磨针工具软件 - https://tools.nwumba.cn)"
    page.window.width = 1280
    page.window.height = 720
    page.window.min_width = 960
    page.window.min_height = 640
    page.window.maximized = True
    page.padding = 0
    page.spacing = 0
    page.bgcolor = COLORS["background"]
    page.theme = ft.Theme(
        font_family="Microsoft YaHei",
    )

    # 主扫描面板（需要 page 引用用于对话框和异步操作）
    scan_panel = ScanPanel(page)

    # 菜单切换回调
    def on_menu_change(index: int, title: str):
        scan_panel.set_scan_type(index)

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
