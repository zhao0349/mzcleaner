"""左侧菜单栏组件"""

import flet as ft
from theme import COLORS
from components.menu_item import MenuItem


class Sidebar(ft.Container):
    """左侧功能导航菜单"""

    MENU_ITEMS = [
        {"icon": ft.Icons.CLEANING_SERVICES_OUTLINED, "text": "基础清理"},
        {"icon": ft.Icons.SECURITY_OUTLINED, "text": "系统清理"},
        {"icon": ft.Icons.CHAT_OUTLINED, "text": "微信清理"},
        {"icon": ft.Icons.MESSAGE_OUTLINED, "text": "QQ清理"},
        {"icon": ft.Icons.FOLDER_OPEN_OUTLINED, "text": "用户目录迁移"},
        {"icon": ft.Icons.LIST_ALT_OUTLINED, "text": "软件占用查询"},
        {"icon": ft.Icons.ARROW_FORWARD_OUTLINED, "text": "软件搬家"},
        {"icon": ft.Icons.DESCRIPTION_OUTLINED, "text": "大文件查找"},
        {"icon": ft.Icons.CONTENT_COPY_OUTLINED, "text": "重复文件查找"},
        {"icon": ft.Icons.LOOP_OUTLINED, "text": "相似文件查找"},
        {"icon": ft.Icons.FOLDER_OUTLINED, "text": "目录大小查看"},
    ]

    def __init__(self, on_menu_change=None):
        self.on_menu_change = on_menu_change
        self._menu_items: list[MenuItem] = []
        self._selected_index = 0

        self._menu_column = ft.Column(
            controls=[],
            spacing=0,
            scroll=ft.ScrollMode.AUTO,
        )

        super().__init__(
            content=ft.Column(
                controls=[
                    # Logo / 标题区域
                    ft.Container(
                        content=ft.Row(
                            controls=[
                                ft.Icon(
                                    name=ft.Icons.CLEANING_SERVICES,
                                    size=24,
                                    color=COLORS["primary"],
                                ),
                                ft.Text(
                                    value="磨针C盘清理",
                                    size=16,
                                    color=COLORS["primary"],
                                    weight=ft.FontWeight.W_600,
                                ),
                            ],
                            spacing=8,
                            alignment=ft.MainAxisAlignment.CENTER,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                        height=60,
                        padding=ft.padding.only(left=16, right=16),
                    ),
                    ft.Divider(height=1, color=COLORS["border"]),
                    # 菜单列表
                    ft.Container(
                        content=self._menu_column,
                        expand=True,
                        padding=ft.padding.only(top=8, bottom=8),
                    ),
                ],
                spacing=0,
            ),
            width=220,
            bgcolor=COLORS["sidebar_bg"],
            border=ft.border.only(right=ft.BorderSide(1, COLORS["border"])),
        )

        self._build_menu()

    def _build_menu(self):
        """构建菜单项列表"""
        for i, item in enumerate(self.MENU_ITEMS):
            menu_item = MenuItem(
                icon=item["icon"],
                text=item["text"],
                selected=(i == self._selected_index),
                on_click=lambda e, idx=i: self._on_item_click(idx),
            )
            self._menu_items.append(menu_item)
            self._menu_column.controls.append(menu_item)

    def _on_item_click(self, index: int):
        """菜单项点击事件"""
        if index == self._selected_index:
            return

        # 取消旧选中
        if 0 <= self._selected_index < len(self._menu_items):
            self._menu_items[self._selected_index].selected = False

        # 设置新选中
        self._selected_index = index
        self._menu_items[index].selected = True

        # 通知外部
        if self.on_menu_change:
            self.on_menu_change(index, self.MENU_ITEMS[index]["text"])

    @property
    def current_title(self) -> str:
        return self.MENU_ITEMS[self._selected_index]["text"]
