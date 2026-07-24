"""左侧菜单项组件"""

import flet as ft
from theme import COLORS


class MenuItem(ft.Container):
    """可点击的菜单项，包含图标和文字"""

    def __init__(
        self,
        icon,
        text: str,
        selected: bool = False,
        on_click=None,
    ):
        self.icon_name = icon
        self.text_value = text
        self._selected = selected

        self._icon = ft.Icon(
            name=icon,
            size=20,
            color=COLORS["sidebar_selected_text"] if selected else COLORS["sidebar_text"],
        )
        self._label = ft.Text(
            value=text,
            size=14,
            color=COLORS["sidebar_selected_text"] if selected else COLORS["sidebar_text"],
        )

        super().__init__(
            content=ft.Row(
                controls=[
                    self._icon,
                    self._label,
                ],
                spacing=12,
                alignment=ft.MainAxisAlignment.START,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=ft.padding.only(left=24, right=16),
            height=45,
            bgcolor=COLORS["sidebar_selected_bg"] if selected else None,
            border_radius=8,
            margin=ft.margin.only(left=8, right=8, top=2, bottom=2),
            on_click=on_click,
            animate=ft.Animation(200, ft.AnimationCurve.EASE),
        )

    @property
    def selected(self) -> bool:
        return self._selected

    @selected.setter
    def selected(self, value: bool):
        self._selected = value
        color = COLORS["sidebar_selected_text"] if value else COLORS["sidebar_text"]
        self._icon.color = color
        self._label.color = color
        self.bgcolor = COLORS["sidebar_selected_bg"] if value else None
        self.update()
