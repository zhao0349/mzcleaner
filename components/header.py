"""顶部导航栏组件"""

import flet as ft
from theme import COLORS


class Header(ft.Container):
    """顶部标题栏，包含导航链接"""

    def __init__(self, page: ft.Page):
        self.page = page

        # 联系客服 - 红色
        self.btn_contact = ft.TextButton(
            text="联系客服",
            style=ft.ButtonStyle(
                color=COLORS["link_red"],
                text_style=ft.TextStyle(size=14),
            ),
        )

        # 教程及问题
        self.btn_tutorial = ft.TextButton(
            text="教程及问题",
            style=ft.ButtonStyle(
                color=COLORS["header_text"],
                text_style=ft.TextStyle(size=14),
            ),
        )

        # 打开官网
        self.btn_website = ft.TextButton(
            text="打开官网",
            style=ft.ButtonStyle(
                color=COLORS["header_text"],
                text_style=ft.TextStyle(size=14),
            ),
        )

        # VIP永久授权 - 绿色加粗
        self.btn_vip = ft.TextButton(
            text="VIP永久授权",
            style=ft.ButtonStyle(
                color=COLORS["link_green"],
                text_style=ft.TextStyle(size=14, weight=ft.FontWeight.W_600),
            ),
        )

        # 登录
        self.btn_login = ft.TextButton(
            text="登录",
            style=ft.ButtonStyle(
                color=COLORS["header_text"],
                text_style=ft.TextStyle(size=14),
            ),
            on_click=self._on_login_click,
        )

        # 退出
        self.btn_exit = ft.TextButton(
            text="退出",
            style=ft.ButtonStyle(
                color=COLORS["header_text"],
                text_style=ft.TextStyle(size=14),
            ),
            on_click=lambda e: page.window.close(),
        )

        # 复制微信号
        self.btn_copy_wechat = ft.TextButton(
            text="复制微信号",
            style=ft.ButtonStyle(
                color=COLORS["header_text"],
                text_style=ft.TextStyle(size=14),
            ),
        )

        super().__init__(
            content=ft.Row(
                controls=[
                    self.btn_contact,
                    self.btn_tutorial,
                    self.btn_website,
                    self.btn_vip,
                    self.btn_login,
                    self.btn_exit,
                    self.btn_copy_wechat,
                ],
                alignment=ft.MainAxisAlignment.END,
                spacing=4,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            height=60,
            bgcolor=COLORS["header_bg"],
            padding=ft.padding.only(left=20, right=20),
            border=ft.border.only(bottom=ft.BorderSide(1, COLORS["border"])),
        )

    def _on_login_click(self, e):
        """点击登录按钮，弹出登录窗口"""

        def close_dlg(e):
            dlg.open = False
            self.page.update()

        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text("登录窗口", size=18),
            content=ft.Column(
                controls=[
                    ft.Text("请输入您的账号信息进行登录", size=14, color=COLORS["secondary"]),
                    ft.TextField(
                        label="用户名",
                        border_radius=8,
                        height=45,
                    ),
                    ft.TextField(
                        label="密码",
                        password=True,
                        can_reveal_password=True,
                        border_radius=8,
                        height=45,
                    ),
                ],
                spacing=16,
                width=320,
                height=180,
            ),
            actions=[
                ft.TextButton("取消", on_click=close_dlg),
                ft.ElevatedButton(
                    "登录",
                    on_click=close_dlg,
                    style=ft.ButtonStyle(
                        bgcolor=COLORS["primary"],
                        color=ft.Colors.WHITE,
                    ),
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )

        self.page.open(dlg)
        self.page.update()
