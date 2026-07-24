"""主内容区域 - 扫描面板组件（支持所有扫描类型）"""

import asyncio
import threading
import flet as ft
from theme import COLORS
from scanner import DiskScanner, SCAN_TYPES, ScanResult, ScanTask
from cleaner import FileCleaner


# 扫描类型 → 菜单索引的映射
SCAN_TYPE_KEYS = [
    "basic_clean", "system_clean", "wechat_clean", "qq_clean",
    "user_dir_migrate", "software_usage", "software_move",
    "large_files", "duplicate_files", "similar_files", "dir_size_view",
]

# 需要确认清理的扫描类型（目录清理用 clean_directory_contents）
DIR_CLEAN_TYPES = {"basic_clean", "system_clean", "wechat_clean", "qq_clean"}


class ScanPanel(ft.Container):
    """主扫描操作面板 - 支持11种扫描类型"""

    def __init__(self, page: ft.Page):
        self.page = page
        self._scan_type_key = "basic_clean"
        self._scan_task: ScanTask = SCAN_TYPES["basic_clean"]
        self._is_scanning = False
        self._is_cleaning = False
        self._results: list[ScanResult] = []
        self._selected_indices: set[int] = set()
        self._scanner: DiskScanner | None = None
        self._cleaner: FileCleaner | None = None

        # ── 标题 ──
        self._title = ft.Text(
            value=self._scan_task.title,
            size=22,
            color=COLORS["text"],
            weight=ft.FontWeight.W_600,
        )

        # ── 描述文字 ──
        self._desc_text = ft.Text(
            value=self._scan_task.description,
            size=13,
            color=COLORS["secondary"],
            italic=True,
        )

        # ── 状态提示 ──
        self._status_text = ft.Text(
            value="请点击开始扫描",
            size=14,
            color=COLORS["secondary"],
        )

        # ── 进度环 ──
        self._progress_ring = ft.ProgressRing(
            width=20,
            height=20,
            color=COLORS["primary"],
            visible=False,
        )

        # ── 进度条 ──
        self._progress_bar = ft.ProgressBar(
            width=200,
            color=COLORS["primary"],
            bgcolor=COLORS["border"],
            visible=False,
        )

        # ── 统计信息 ──
        self._stats_row = ft.Row(controls=[], spacing=16, visible=False)

        # ── 按钮 ──
        self._btn_scan = ft.OutlinedButton(
            content=ft.Row(
                controls=[
                    ft.Icon(name=ft.Icons.SEARCH, size=18),
                    ft.Text("开始扫描", size=14),
                ],
                spacing=6,
                alignment=ft.MainAxisAlignment.CENTER,
            ),
            style=ft.ButtonStyle(
                side=ft.BorderSide(1.5, COLORS["primary"]),
                shape=ft.RoundedRectangleBorder(radius=20),
                color=COLORS["primary"],
                bgcolor=COLORS["card"],
            ),
            height=40,
            on_click=self._on_scan_click,
        )

        self._btn_pause = ft.OutlinedButton(
            content=ft.Row(
                controls=[
                    ft.Icon(name=ft.Icons.PAUSE, size=18),
                    ft.Text("暂停扫描", size=14),
                ],
                spacing=6,
                alignment=ft.MainAxisAlignment.CENTER,
            ),
            style=ft.ButtonStyle(
                side=ft.BorderSide(1.5, COLORS["disabled"]),
                shape=ft.RoundedRectangleBorder(radius=20),
                color=COLORS["disabled"],
                bgcolor=COLORS["button_disabled_bg"],
            ),
            height=40,
            disabled=True,
            on_click=self._on_pause_click,
        )

        self._btn_clean = ft.OutlinedButton(
            content=ft.Row(
                controls=[
                    ft.Icon(name=ft.Icons.DELETE_OUTLINE, size=18),
                    ft.Text("开始清理", size=14),
                ],
                spacing=6,
                alignment=ft.MainAxisAlignment.CENTER,
            ),
            style=ft.ButtonStyle(
                side=ft.BorderSide(1.5, COLORS["disabled"]),
                shape=ft.RoundedRectangleBorder(radius=20),
                color=COLORS["disabled"],
                bgcolor=COLORS["button_disabled_bg"],
            ),
            height=40,
            disabled=True,
            on_click=self._on_clean_click,
        )

        # ── 全选/取消 ──
        self._btn_select_all = ft.TextButton(
            text="全选",
            style=ft.ButtonStyle(color=COLORS["primary"], text_style=ft.TextStyle(size=13)),
            on_click=self._on_select_all,
            visible=False,
        )
        self._btn_deselect_all = ft.TextButton(
            text="取消全选",
            style=ft.ButtonStyle(color=COLORS["secondary"], text_style=ft.TextStyle(size=13)),
            on_click=self._on_deselect_all,
            visible=False,
        )

        # ── 结果列表面板 ──
        self._result_list = ft.ListView(
            controls=[],
            spacing=1,
            expand=True,
            visible=False,
        )

        # ── 空状态占位 ──
        self._empty_placeholder = ft.Container(
            content=ft.Column(
                controls=[
                    ft.Icon(name=ft.Icons.SEARCH_OFF, size=64, color=COLORS["disabled"]),
                    ft.Text(value="暂无扫描结果", size=14, color=COLORS["disabled"]),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=12,
            ),
            alignment=ft.alignment.center,
            expand=True,
        )

        # ── 结果区域 ──
        self._result_area = ft.Container(
            content=ft.Stack(
                controls=[self._empty_placeholder, self._result_list],
                expand=True,
            ),
            expand=True,
        )

        # ── 结果标题 ──
        self._result_title = ft.Text(
            value="扫描结果：",
            size=18,
            color=COLORS["text"],
            weight=ft.FontWeight.W_500,
            visible=False,
        )

        # ── 组装卡片 ──
        card_content = ft.Column(
            controls=[
                ft.Row(controls=[self._title]),
                ft.Container(height=4),
                ft.Row(controls=[self._desc_text]),
                ft.Container(height=8),
                ft.Row(
                    controls=[
                        self._status_text,
                        self._progress_ring,
                        self._progress_bar,
                    ],
                    spacing=10,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                self._stats_row,
                ft.Container(height=12),
                ft.Row(
                    controls=[
                        self._btn_scan,
                        self._btn_pause,
                        self._btn_clean,
                        self._btn_select_all,
                        self._btn_deselect_all,
                    ],
                    spacing=10,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                ft.Divider(height=1, color=COLORS["border"]),
                self._result_title,
                ft.Container(height=8),
                self._result_area,
            ],
            spacing=0,
            expand=True,
        )

        card = ft.Container(
            content=card_content,
            bgcolor=COLORS["card"],
            border_radius=15,
            padding=ft.padding.all(24),
            border=ft.border.all(1, COLORS["border"]),
            expand=True,
            shadow=ft.BoxShadow(
                spread_radius=0.5,
                blur_radius=8,
                color=ft.Colors.with_opacity(0.06, "#000000"),
                offset=ft.Offset(0, 2),
            ),
        )

        super().__init__(
            content=card,
            bgcolor=COLORS["background"],
            padding=ft.padding.all(20),
            expand=True,
        )

    # ── 公共接口 ──────────────────────────────────────────

    def set_scan_type(self, index: int):
        """切换扫描类型"""
        if 0 <= index < len(SCAN_TYPE_KEYS):
            self._scan_type_key = SCAN_TYPE_KEYS[index]
            self._scan_task = SCAN_TYPES[self._scan_type_key]
            self._title.value = self._scan_task.title
            self._desc_text.value = self._scan_task.description
            self._reset_scan_state()
            self.update()

    def _reset_scan_state(self):
        """重置扫描状态"""
        self._is_scanning = False
        self._is_cleaning = False
        self._results = []
        self._selected_indices = set()
        self._scanner = None
        self._cleaner = None

        # 状态
        self._status_text.value = "请点击开始扫描"
        self._status_text.color = COLORS["secondary"]
        self._progress_ring.visible = False
        self._progress_bar.visible = False
        self._progress_bar.value = 0

        # 统计
        self._stats_row.visible = False
        self._stats_row.controls.clear()

        # 按钮：扫描可用，其他禁用
        self._btn_scan.content.controls[0].name = ft.Icons.SEARCH
        self._btn_scan.content.controls[1].value = "开始扫描"
        self._btn_scan.disabled = False
        self._btn_scan.style = self._btn_style_active()

        self._btn_pause.disabled = True
        self._btn_pause.style = self._btn_style_disabled()

        self._btn_clean.disabled = True
        self._btn_clean.style = self._btn_style_disabled()

        self._btn_select_all.visible = False
        self._btn_deselect_all.visible = False

        # 结果
        self._result_title.visible = False
        self._result_list.controls.clear()
        self._result_list.visible = False
        self._empty_placeholder.visible = True

    # ── 扫描逻辑 ──────────────────────────────────────────

    async def _on_scan_click(self, e):
        if self._is_scanning or self._is_cleaning:
            return

        self._is_scanning = True
        self._scanner = DiskScanner(progress_callback=self._on_scan_progress)
        self._results = []
        self._selected_indices = set()

        # 更新UI：扫描中状态
        self._btn_scan.content.controls[0].name = ft.Icons.HOURGLASS_EMPTY
        self._btn_scan.content.controls[1].value = "正在扫描..."
        self._btn_scan.disabled = True
        self._btn_scan.style = self._btn_style_scanning()

        self._progress_ring.visible = True
        self._progress_bar.visible = True
        self._progress_bar.value = 0
        self._status_text.value = "正在扫描中，请稍候..."
        self._status_text.color = COLORS["primary"]

        self._btn_pause.disabled = False
        self._btn_pause.style = self._btn_style_active()

        self._result_title.visible = False
        self._result_list.visible = False
        self._empty_placeholder.visible = True
        self._btn_select_all.visible = False
        self._btn_deselect_all.visible = False
        self._stats_row.visible = False
        self.update()

        # 在线程中执行扫描（避免阻塞UI）
        await asyncio.to_thread(self._run_scan)

        # 扫描完成，更新UI
        await self._finalize_scan()

    def _run_scan(self):
        """在线程中执行实际扫描"""
        try:
            scan_type = self._scan_type_key
            if scan_type == "basic_clean":
                self._results = self._scanner.scan_basic_clean()
            elif scan_type == "system_clean":
                self._results = self._scanner.scan_system_clean()
            elif scan_type == "wechat_clean":
                self._results = self._scanner.scan_wechat_clean()
            elif scan_type == "qq_clean":
                self._results = self._scanner.scan_qq_clean()
            elif scan_type == "user_dir_migrate":
                self._results = self._scanner.scan_user_dirs()
            elif scan_type == "software_usage":
                self._results = self._scanner.scan_software_usage()
            elif scan_type == "software_move":
                self._results = self._scanner.scan_software_usage()
            elif scan_type == "large_files":
                self._results = self._scanner.scan_large_files()
            elif scan_type == "duplicate_files":
                self._results = self._scanner.scan_duplicate_files()
            elif scan_type == "similar_files":
                self._results = self._scanner.scan_similar_files()
            elif scan_type == "dir_size_view":
                self._results = self._scanner.scan_dir_sizes()
        except Exception as ex:
            self._results = []
            self._status_text.value = f"扫描出错: {ex}"
            self._status_text.color = COLORS["link_red"]

    def _on_scan_progress(self, message: str, current: int, total: int):
        """扫描进度回调（来自工作线程）"""
        self._status_text.value = message
        if total > 0:
            self._progress_bar.value = current / total
        # 使用 page 的 run_task 确保在主线程更新
        try:
            self.page.run_task(
                asyncio.sleep(0.01)
            )
        except Exception:
            pass

    async def _finalize_scan(self):
        """扫描完成后更新UI（在主线程调用）"""
        self._is_scanning = False
        self._progress_ring.visible = False
        self._progress_bar.visible = False

        total_size = sum(r.size for r in self._results)

        if not self._results:
            self._status_text.value = "扫描完成，未发现可清理项"
            self._status_text.color = COLORS["secondary"]
        else:
            self._status_text.value = f"扫描完成，发现 {len(self._results)} 项，共 {self._format_size(total_size)}"
            self._status_text.color = COLORS["primary"]

        # 恢复开始扫描按钮
        self._btn_scan.content.controls[0].name = ft.Icons.SEARCH
        self._btn_scan.content.controls[1].value = "开始扫描"
        self._btn_scan.disabled = False
        self._btn_scan.style = self._btn_style_active()

        # 启用暂停禁用
        self._btn_pause.disabled = True
        self._btn_pause.style = self._btn_style_disabled()

        # 有结果时启用清理
        if self._results:
            self._btn_clean.disabled = False
            self._btn_clean.style = self._btn_style_active()
            self._btn_select_all.visible = True
            self._btn_deselect_all.visible = True

        # 构建统计行
        self._stats_row.controls.clear()
        self._stats_row.controls.append(
            ft.Text(
                value=f"共 {len(self._results)} 项 | 总大小 {self._format_size(total_size)}",
                size=14,
                color=COLORS["primary"],
                weight=ft.FontWeight.W_500,
            )
        )
        self._stats_row.visible = bool(self._results)

        # 显示结果列表
        self._build_result_list()
        self._result_title.visible = True
        self._result_list.visible = bool(self._results)
        self._empty_placeholder.visible = not bool(self._results)

        self.update()

    def _build_result_list(self):
        """构建扫描结果列表"""
        self._result_list.controls.clear()

        for i, result in enumerate(self._results):
            row = self._build_result_row(i, result)
            self._result_list.controls.append(row)

    def _build_result_row(self, index: int, result: ScanResult) -> ft.Container:
        """构建单条结果行"""
        is_checked = index in self._selected_indices

        icon_map = {
            "临时文件": ft.Icons.DELETE_SWEEP,
            "系统缓存": ft.Icons.CACHED,
            "系统记录": ft.Icons.HISTORY,
            "回收站": ft.Icons.DELETE,
            "浏览器缓存": ft.Icons.LANGUAGE,
            "系统更新": ft.Icons.SYSTEM_UPDATE,
            "系统日志": ft.Icons.RECEIPT_LONG,
            "系统备份": ft.Icons.BACKUP,
            "微信缓存": ft.Icons.CHAT,
            "QQ缓存": ft.Icons.MESSAGE,
            "用户目录": ft.Icons.FOLDER_OPEN,
            "已安装软件": ft.Icons.APPS,
            "大文件": ft.Icons.DESCRIPTION,
            "重复文件": ft.Icons.CONTENT_COPY,
            "相似文件": ft.Icons.FIND_REPLACE,
            "目录": ft.Icons.FOLDER,
        }
        icon_name = icon_map.get(result.category, ft.Icons.INSERT_DRIVE_FILE)

        checkbox = ft.Checkbox(
            value=is_checked,
            on_change=lambda e, i=index: self._on_item_toggle(i, e.control.value),
            fill_color=COLORS["primary"],
            check_color=ft.Colors.WHITE,
        )

        name_text = ft.Text(
            value=result.name[:60] + ("..." if len(result.name) > 60 else ""),
            size=13,
            color=COLORS["text"],
            weight=ft.FontWeight.W_500,
            tooltip=result.name if len(result.name) > 60 else None,
        )

        path_text = ft.Text(
            value=result.path[:80] + ("..." if len(result.path) > 80 else ""),
            size=11,
            color=COLORS["secondary"],
            tooltip=result.path if len(result.path) > 80 else None,
        )

        size_text = ft.Text(
            value=result.size_display,
            size=13,
            color=COLORS["primary"],
            weight=ft.FontWeight.W_600,
        )

        category_badge = ft.Container(
            content=ft.Text(
                value=result.category,
                size=10,
                color=COLORS["primary"],
            ),
            bgcolor=COLORS["sidebar_selected_bg"],
            border_radius=10,
            padding=ft.padding.only(left=8, right=8, top=2, bottom=2),
        )

        return ft.Container(
            content=ft.Row(
                controls=[
                    checkbox,
                    ft.Icon(name=icon_name, size=18, color=COLORS["secondary"]),
                    ft.Column(
                        controls=[name_text, path_text],
                        spacing=2,
                        expand=True,
                    ),
                    category_badge,
                    size_text,
                ],
                spacing=10,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=ft.padding.only(left=8, right=12, top=8, bottom=8),
            border_radius=8,
            bgcolor=COLORS["sidebar_selected_bg"] if is_checked else COLORS["card"],
            on_click=lambda e, i=index: self._on_row_click(i),
        )

    # ── 清理逻辑 ──────────────────────────────────────────

    async def _on_clean_click(self, e):
        if self._is_cleaning or not self._results:
            return

        if not self._selected_indices:
            # 没有选中任何项，弹出确认
            self._show_confirm_dialog(
                "确认清理",
                "没有选中任何项目。您确定要清理所有扫描到的文件吗？",
                lambda: asyncio.ensure_future(self._do_clean_all())
            )
            return

        select_all = len(self._selected_indices) == len(self._results)
        msg = f"已选中 {len(self._selected_indices)} 项，共 {self._get_selected_size()}\n\n确定要清理选中的文件吗？此操作不可撤销。"
        self._show_confirm_dialog(
            "确认清理",
            msg,
            lambda: asyncio.ensure_future(self._do_clean_selected())
        )

    def _show_confirm_dialog(self, title: str, message: str, on_confirm):
        """显示确认对话框"""

        def close_dlg(e):
            dlg.open = False
            self.page.update()

        def confirm(e):
            dlg.open = False
            self.page.update()
            on_confirm()

        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text(title, size=18),
            content=ft.Text(message, size=14, color=COLORS["secondary"]),
            actions=[
                ft.TextButton("取消", on_click=close_dlg),
                ft.ElevatedButton(
                    "确定清理",
                    on_click=confirm,
                    style=ft.ButtonStyle(
                        bgcolor=COLORS["link_red"],
                        color=ft.Colors.WHITE,
                    ),
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        self.page.open(dlg)
        self.page.update()

    async def _do_clean_all(self):
        """清理所有结果"""
        await self._execute_clean(set(range(len(self._results))))

    async def _do_clean_selected(self):
        """清理选中项"""
        await self._execute_clean(self._selected_indices.copy())

    async def _execute_clean(self, indices: set[int]):
        """执行清理操作"""
        self._is_cleaning = True
        self._btn_clean.disabled = True
        self._btn_scan.disabled = True
        self._btn_pause.disabled = True

        self._status_text.value = "正在清理..."
        self._status_text.color = COLORS["primary"]
        self._progress_ring.visible = True
        self.update()

        # 收集要清理的路径
        paths = [self._results[i].path for i in indices if i < len(self._results)]

        # 执行清理
        cleaner = FileCleaner()
        deleted_count = 0
        total_size = 0
        errors = 0

        # 对于目录类型的扫描项（基础清理、系统清理、微信/QQ缓存），清空目录内容
        if self._scan_type_key in DIR_CLEAN_TYPES:
            for path in paths:
                result = cleaner.clean_directory_contents(path)
                if result.success:
                    deleted_count += 1
                    total_size += result.size
                else:
                    errors += 1

                # 更新进度
                idx = indices.pop() if indices else -1
                if idx >= 0:
                    self._selected_indices.discard(idx)

                self._status_text.value = f"正在清理... ({deleted_count}/{len(paths)})"
                try:
                    self.update()
                except Exception:
                    pass
                await asyncio.sleep(0.05)
        else:
            # 文件类型直接删除
            results = await asyncio.to_thread(cleaner.delete_files, paths)
            for r in results:
                if r.success:
                    deleted_count += 1
                    total_size += r.size
                else:
                    errors += 1

        # 从结果中移除已清理的项
        original_len = len(self._results)
        self._results = [r for i, r in enumerate(self._results) if i not in indices]
        self._selected_indices = set()

        # 更新UI
        self._is_cleaning = False
        self._progress_ring.visible = False

        if not self._results:
            self._status_text.value = f"清理完成！成功 {deleted_count} 项，释放 {self._format_size(total_size)}"
            self._status_text.color = COLORS["primary"]
            self._btn_clean.disabled = True
            self._btn_clean.style = self._btn_style_disabled()
            self._btn_select_all.visible = False
            self._btn_deselect_all.visible = False
            self._result_list.visible = False
            self._empty_placeholder.visible = True
        else:
            self._status_text.value = f"清理完成！成功 {deleted_count} 项，释放 {self._format_size(total_size)}"
            self._status_text.color = COLORS["primary"]
            self._btn_clean.disabled = False
            self._build_result_list()
            self._result_list.visible = True

        self._btn_scan.disabled = False
        self._stats_row.controls.clear()
        self._stats_row.controls.append(
            ft.Text(
                value=f"剩余 {len(self._results)} 项 | 已释放 {self._format_size(total_size)}",
                size=14,
                color=COLORS["primary"],
                weight=ft.FontWeight.W_500,
            )
        )
        self._stats_row.visible = bool(self._results)
        self._result_title.visible = True

        self.update()

    # ── 暂停/继续 ────────────────────────────────────────

    async def _on_pause_click(self, e):
        if self._scanner and self._is_scanning:
            self._scanner.cancel()
            self._btn_pause.disabled = True
            self._btn_pause.style = self._btn_style_disabled()
            self._status_text.value = "正在停止扫描..."
            self._status_text.color = COLORS["secondary"]
            self._progress_ring.visible = False
            self._progress_bar.visible = False
            self.update()
            # _run_scan 线程会在下一次检查 _cancelled 标志时退出
            # _on_scan_click 会在线程返回后自动调用 _finalize_scan

    # ── 选择操作 ──────────────────────────────────────────

    def _on_item_toggle(self, index: int, checked: bool):
        if checked:
            self._selected_indices.add(index)
        else:
            self._selected_indices.discard(index)
        self._build_result_list()
        self.update()

    def _on_row_click(self, index: int):
        """点击行切换勾选"""
        if index in self._selected_indices:
            self._selected_indices.discard(index)
        else:
            self._selected_indices.add(index)
        self._build_result_list()
        self.update()

    async def _on_select_all(self, e):
        self._selected_indices = set(range(len(self._results)))
        self._build_result_list()
        self.update()

    async def _on_deselect_all(self, e):
        self._selected_indices = set()
        self._build_result_list()
        self.update()

    # ── 辅助 ──────────────────────────────────────────────

    def _get_selected_size(self) -> str:
        total = sum(self._results[i].size for i in self._selected_indices if i < len(self._results))
        return self._format_size(total)

    @staticmethod
    def _format_size(size: int) -> str:
        if size < 1024:
            return f"{size} B"
        elif size < 1024 * 1024:
            return f"{size / 1024:.1f} KB"
        elif size < 1024 * 1024 * 1024:
            return f"{size / (1024 * 1024):.2f} MB"
        else:
            return f"{size / (1024 * 1024 * 1024):.2f} GB"

    @staticmethod
    def _btn_style_active():
        return ft.ButtonStyle(
            side=ft.BorderSide(1.5, COLORS["primary"]),
            shape=ft.RoundedRectangleBorder(radius=20),
            color=COLORS["primary"],
            bgcolor=COLORS["card"],
        )

    @staticmethod
    def _btn_style_disabled():
        return ft.ButtonStyle(
            side=ft.BorderSide(1.5, COLORS["disabled"]),
            shape=ft.RoundedRectangleBorder(radius=20),
            color=COLORS["disabled"],
            bgcolor=COLORS["button_disabled_bg"],
        )

    @staticmethod
    def _btn_style_scanning():
        return ft.ButtonStyle(
            side=ft.BorderSide(1.5, COLORS["primary"]),
            shape=ft.RoundedRectangleBorder(radius=20),
            color=COLORS["primary"],
            bgcolor="#E8F5F2",
        )
