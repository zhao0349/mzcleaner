"""扫描与手动清理；分析页只读，工作线程只负责文件操作。"""
import asyncio
import os
import time
import flet as ft
from theme import COLORS
from scanner import DiskScanner, SCAN_TYPES

SCAN_TYPE_KEYS = list(SCAN_TYPES)
PATH_TYPES = {"large_files", "duplicate_files", "similar_files", "dir_size_view"}
CLEAN_TYPES = {"basic_clean", "large_files", "duplicate_files"}


class ScanPanel(ft.Container):
    def __init__(self, page: ft.Page):
        self._scan_type_key = SCAN_TYPE_KEYS[0]
        self._results = []
        self._selected_indices = set()
        self._is_scanning = False
        self._is_cleaning = False
        self._confirming = False
        self._scanner = None
        self._loop = None
        self._last_progress = 0.0
        self._title = ft.Text(size=22, weight=ft.FontWeight.W_600)
        self._description = ft.Text(size=13, color=COLORS["secondary"])
        self._status = ft.Text("点击开始扫描", selectable=True)
        self._progress = ft.ProgressRing(width=18, height=18, visible=False)
        self._path = ft.TextField(label="扫描目录", value="C:\\", expand=True, dense=True)
        self._picker = ft.FilePicker(on_result=self._folder_chosen)
        self._browse = ft.OutlinedButton("选择目录", on_click=self._choose_folder)
        self._path_row = ft.Row([self._path, self._browse], visible=False)
        self._scan_button = ft.ElevatedButton("开始扫描", icon=ft.Icons.SEARCH, on_click=self._on_scan_click)
        self._stop_button = ft.OutlinedButton("停止扫描", disabled=True, on_click=self._on_stop)
        self._clean_button = ft.OutlinedButton("清理选中项", icon=ft.Icons.DELETE_OUTLINE,
                                               disabled=True, on_click=self._on_clean_click)
        self._all_button = ft.TextButton("全选", disabled=True, on_click=self._select_all)
        self._none_button = ft.TextButton("取消全选", disabled=True, on_click=self._select_none)
        self._result_list = ft.ListView(expand=True, spacing=4)
        self._summary = ft.Text("暂无扫描结果", color=COLORS["secondary"])
        self._errors = ft.Text(color=COLORS["link_red"], selectable=True, visible=False)
        super().__init__(
            expand=True, padding=24, bgcolor=COLORS["background"],
            content=ft.Column([
                self._title, self._description, self._path_row,
                ft.Row([self._scan_button, self._stop_button, self._clean_button]),
                ft.Row([self._progress, self._status]),
                self._errors,
                ft.Row([self._all_button, self._none_button, self._summary]),
                ft.Divider(), self._result_list,
            ], spacing=14, expand=True),
        )
        page.overlay.append(self._picker)
        self._configure_type()

    @property
    def busy(self):
        return self._is_scanning or self._is_cleaning or self._confirming

    def _configure_type(self):
        task = SCAN_TYPES[self._scan_type_key]
        self._title.value = task.title
        self._description.value = task.description
        self._path_row.visible = self._scan_type_key in PATH_TYPES
        for control in (self._clean_button, self._all_button, self._none_button):
            control.visible = self._scan_type_key in CLEAN_TYPES

    def set_scan_type(self, index):
        if self.busy:
            return False
        self._scan_type_key = SCAN_TYPE_KEYS[index]
        self._results = []
        self._selected_indices.clear()
        self._status.value = "点击开始扫描"
        self._errors.visible = False
        self._configure_type()
        self._refresh_results()
        return True

    async def _choose_folder(self, e):
        self._picker.get_directory_path(dialog_title="选择扫描目录", initial_directory=self._path.value)

    async def _folder_chosen(self, e):
        if e.path and not self.busy:
            self._path.value = e.path
            self.update()

    def _set_busy_controls(self):
        self._scan_button.disabled = self.busy
        self._path.disabled = self.busy
        self._browse.disabled = self.busy
        self._stop_button.disabled = not self._is_scanning
        self._clean_button.disabled = self.busy or not self._selected_indices
        self._all_button.disabled = self.busy or not self._results
        self._none_button.disabled = self.busy or not self._selected_indices
        self._result_list.disabled = self.busy
        self._progress.visible = self._is_scanning or self._is_cleaning

    async def _on_scan_click(self, e):
        if self.busy:
            return
        path = os.path.abspath(os.path.expandvars(self._path.value.strip().strip('"')))
        if self._scan_type_key in PATH_TYPES and not os.path.isdir(path):
            self._status.value = "扫描目录不存在，请重新选择"
            self.update()
            return
        self._is_scanning = True
        self._loop = asyncio.get_running_loop()
        self._scanner = DiskScanner(progress_callback=self._on_scan_progress)
        self._results = []
        self._selected_indices.clear()
        self._errors.visible = False
        self._status.value = "正在扫描…"
        self._refresh_results()
        methods = {
            "basic_clean": lambda: self._scanner.scan_basic_clean(),
            "software_usage": lambda: self._scanner.scan_software_usage(),
            "large_files": lambda: self._scanner.scan_large_files([path]),
            "duplicate_files": lambda: self._scanner.scan_duplicate_files([path]),
            "similar_files": lambda: self._scanner.scan_similar_files([path]),
            "dir_size_view": lambda: self._scanner.scan_dir_sizes(path),
        }
        try:
            self._results = await asyncio.to_thread(methods[self._scan_type_key])
            label = "扫描已停止，保留已找到的结果" if self._scanner._cancelled else "扫描完成"
            self._status.value = f"{label}：{len(self._results)} 项"
        except Exception as ex:
            self._status.value = "扫描失败"
            self._errors.value = str(ex)
            self._errors.visible = True
        finally:
            self._is_scanning = False
            self._refresh_results()

    def _on_scan_progress(self, message, current, total):
        now = time.monotonic()
        if now - self._last_progress >= 0.15:
            self._last_progress = now
            self._loop.call_soon_threadsafe(self._show_scan_progress, message)

    def _show_scan_progress(self, message):
        if self._is_scanning:
            self._status.value = message
            self.update()

    async def _on_stop(self, e):
        if self._scanner and self._is_scanning:
            self._scanner.cancel()
            self._stop_button.disabled = True
            self._status.value = "正在停止扫描…"
            self.update()

    def _refresh_results(self):
        self._result_list.controls.clear()
        selectable = self._scan_type_key in CLEAN_TYPES
        for i, result in enumerate(self._results):
            async def toggle(e, index=i):
                if self.busy:
                    return
                if e.control.value:
                    self._selected_indices.add(index)
                else:
                    self._selected_indices.discard(index)
                self._refresh_summary()
                self.update()
            self._result_list.controls.append(ft.Container(
                content=ft.Row([
                    ft.Checkbox(value=i in self._selected_indices, on_change=toggle, visible=selectable),
                    ft.Column([
                        ft.Text(result.name, weight=ft.FontWeight.W_500),
                        ft.Text(result.path, size=12, color=COLORS["secondary"], selectable=True),
                    ], expand=True, spacing=4),
                    ft.Text(result.size_display, width=100, text_align=ft.TextAlign.RIGHT),
                ]), padding=12, bgcolor=COLORS["card"], border_radius=8,
            ))
        self._refresh_summary()
        self.update()

    def _refresh_summary(self):
        total = sum(r.size for r in self._results)
        chosen = sum(self._results[i].size for i in self._selected_indices)
        self._summary.value = f"共 {len(self._results)} 项 / {self._format_size(total)}"
        if self._scan_type_key in CLEAN_TYPES:
            self._summary.value += f" · 已选 {len(self._selected_indices)} 项 / {self._format_size(chosen)}"
        self._set_busy_controls()

    async def _select_all(self, e):
        if not self.busy:
            self._selected_indices = set(range(len(self._results)))
            self._refresh_results()

    async def _select_none(self, e):
        if not self.busy:
            self._selected_indices.clear()
            self._refresh_results()

    async def _on_clean_click(self, e):
        if self.busy or self._scan_type_key not in CLEAN_TYPES or not self._selected_indices:
            return
        indices = self._selected_indices.copy()
        chosen = [self._results[i] for i in sorted(indices)]
        self._confirming = True
        self._set_busy_controls()
        self.update()

        async def cancel(e):
            self.page.close(dialog)
            self._confirming = False
            self._set_busy_controls()
            self.update()

        async def confirm(e):
            self.page.close(dialog)
            self._confirming = False
            await self._execute_clean(indices)

        paths = "\n".join(r.path for r in chosen[:8])
        if len(chosen) > 8:
            paths += f"\n…共 {len(chosen)} 项"
        action = "清空所选缓存目录的内容" if self._scan_type_key == "basic_clean" else "删除所选文件"
        dialog = ft.AlertDialog(
            modal=True, title=ft.Text("确认清理"),
            content=ft.Column([
                ft.Text(f"将{action}，预计 {self._format_size(sum(r.size for r in chosen))}。\n永久删除，不进入回收站。"),
                ft.Text(paths, size=12, selectable=True),
            ], width=560, tight=True, scroll=ft.ScrollMode.AUTO),
            actions=[ft.TextButton("取消", on_click=cancel), ft.ElevatedButton("确定清理", on_click=confirm)],
        )
        self.page.open(dialog)

    async def _execute_clean(self, indices):
        if self._is_cleaning or self._scan_type_key not in CLEAN_TYPES:
            return
        from cleaner import FileCleaner
        self._is_cleaning = True
        self._errors.visible = False
        self._set_busy_controls()
        self.update()
        completed = set()
        freed = 0
        errors = []
        cleaner = FileCleaner()
        try:
            for number, index in enumerate(sorted(indices), 1):
                item = self._results[index]
                self._status.value = f"正在清理 {number}/{len(indices)}：{item.name}"
                self.update()
                if self._scan_type_key == "basic_clean":
                    result = await asyncio.to_thread(cleaner.clean_directory_contents, item.path)
                else:
                    result = (await asyncio.to_thread(cleaner.delete_files, [item.path]))[0]
                freed += result.size
                if result.success:
                    completed.add(index)
                else:
                    errors.append(f"{item.path}: {result.error}")
                    item.size = max(0, item.size - result.size)
            self._status.value = f"清理完成：成功 {len(completed)} 项，失败 {len(errors)} 项，释放 {self._format_size(freed)}"
        except Exception as ex:
            errors.append(str(ex))
            self._status.value = "清理中断，未完成的项目已保留"
        finally:
            self._results = [r for i, r in enumerate(self._results) if i not in completed]
            self._selected_indices.clear()
            self._is_cleaning = False
            self._errors.value = "\n".join(errors[:3])
            if len(errors) > 3:
                self._errors.value += f"\n另有 {len(errors) - 3} 项失败；请关闭占用文件的程序后重新扫描。"
            self._errors.visible = bool(errors)
            self._refresh_results()

    @staticmethod
    def _format_size(size):
        return DiskScanner._format_size(size)
