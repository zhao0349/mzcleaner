"""免费简化版顶部说明。"""
import flet as ft
from theme import COLORS


class Header(ft.Container):
    def __init__(self, page: ft.Page):
        super().__init__(
            content=ft.Row([
                ft.Text("免费简化版 0.1.0", weight=ft.FontWeight.W_600, size=16),
                ft.Text("离线使用 · 无需账号 · 手动选择后清理", color=COLORS["secondary"], expand=True),
                ft.TextButton("退出", on_click=lambda e: page.window.close()),
            ]),
            padding=ft.padding.symmetric(horizontal=24, vertical=12),
            bgcolor=COLORS["header_bg"],
            border=ft.border.only(bottom=ft.BorderSide(1, COLORS["border"])),
        )
