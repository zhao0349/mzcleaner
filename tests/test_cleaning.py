"""本批清理调用链与失败处理回归；只操作本次创建的临时样本。"""
import asyncio
import inspect
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from cleaner import FileCleaner
from scanner import DiskScanner, ScanResult
from components.scan_panel import ScanPanel, SCAN_TYPE_KEYS


class PageStub:
    def __init__(self):
        self.overlay = []
        self.dialog = None
    def open(self, dialog): self.dialog = dialog
    def close(self, dialog): self.dialog = None


class CleaningTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        base = ROOT/'build'/'test-fixtures'
        base.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(prefix='simple-regression-', dir=base)
        self.root = Path(self.temp.name).resolve()
        assert self.root.is_relative_to(base.resolve())
        self.page = PageStub()
        self.panel = ScanPanel(self.page)
        self.panel.page = self.page
        self.panel.update = lambda: None

    def tearDown(self):
        self.temp.cleanup()

    def add_cache(self):
        cache = self.root/'cache'
        cache.mkdir()
        (cache/'sample.txt').write_bytes(b'123456')
        self.panel._results = [ScanResult('测试缓存', str(cache), 6, '临时文件')]
        return cache

    async def test_cache_scan_uses_only_retained_cache_locations(self):
        temp = self.root/'Temp'
        browser = self.root/'Local'/'Google'/'Chrome'/'User Data'/'Default'/'Cache'
        for folder in [temp, browser]:
            folder.mkdir(parents=True)
            (folder/'sample.bin').write_bytes(b'1234')
        with patch.dict(os.environ, {'TEMP': str(temp), 'WINDIR': str(self.root/'Windows'),
                                     'LOCALAPPDATA': str(self.root/'Local')}):
            results = DiskScanner().scan_basic_clean()
        self.assertEqual({r.path for r in results}, {str(temp), str(browser)})
        self.assertEqual(sum(r.size for r in results), 8)

    async def test_empty_selection_and_cancel_do_not_delete(self):
        cache = self.add_cache()
        await self.panel._on_clean_click(None)
        self.assertIsNone(self.page.dialog)
        self.panel._selected_indices = {0}
        await self.panel._on_clean_click(None)
        self.assertFalse(self.panel.set_scan_type(1))
        await self.page.dialog.actions[0].on_click(None)
        self.assertTrue((cache/'sample.txt').exists())
        self.assertFalse(self.panel.busy)

    async def test_async_confirmation_cleans_and_removes_result(self):
        cache = self.add_cache()
        self.panel._selected_indices = {0}
        await self.panel._on_clean_click(None)
        callback = self.page.dialog.actions[1].on_click
        self.assertTrue(inspect.iscoroutinefunction(callback))
        await callback(None)
        self.assertEqual(list(cache.iterdir()), [])
        self.assertEqual(self.panel._results, [])
        self.assertIn('释放 6 B', self.panel._status.value)
        self.assertFalse(self.panel.busy)

    async def test_partial_failure_counts_only_deleted_bytes_and_keeps_result(self):
        cache = self.add_cache()
        locked = cache/'locked.txt'
        locked.write_bytes(b'1234')
        self.panel._results[0].size = 10
        original = os.remove
        def remove(path):
            if Path(path) == locked:
                raise PermissionError('sample locked')
            return original(path)
        with patch('cleaner.os.remove', side_effect=remove):
            await self.panel._execute_clean({0})
        self.assertTrue(locked.exists())
        self.assertEqual(len(self.panel._results), 1)
        self.assertEqual(self.panel._results[0].size, 4)
        self.assertIn('失败 1 项', self.panel._status.value)
        self.assertIn('释放 6 B', self.panel._status.value)
        self.assertTrue(self.panel._errors.visible)

    async def test_duplicate_scan_and_selected_deletion_preserve_original(self):
        for name in ['one.txt', 'two.txt']:
            (self.root/name).write_bytes(b'same file')
        self.panel.set_scan_type(SCAN_TYPE_KEYS.index('duplicate_files'))
        self.panel._path.value = str(self.root)
        await self.panel._on_scan_click(None)
        self.assertEqual(len(self.panel._results), 1)
        self.panel._selected_indices = {0}
        await self.panel._on_clean_click(None)
        await self.page.dialog.actions[1].on_click(None)
        self.assertEqual(len(list(self.root.glob('*.txt'))), 1)
        self.assertFalse(self.panel._results)

    async def test_readonly_analysis_and_scan_errors(self):
        cache = self.add_cache()
        self.panel.set_scan_type(SCAN_TYPE_KEYS.index('dir_size_view'))
        self.panel._path.value = str(self.root)
        await self.panel._on_scan_click(None)
        self.assertEqual(len(self.panel._results), 1)
        self.assertFalse(self.panel._clean_button.visible)
        await self.panel._execute_clean({0})
        self.assertTrue((cache/'sample.txt').exists())
        with patch.object(DiskScanner, 'scan_dir_sizes', side_effect=OSError('sample failure')):
            await self.panel._on_scan_click(None)
        self.assertEqual(self.panel._status.value, '扫描失败')
        self.assertTrue(self.panel._errors.visible)
        self.assertFalse(self.panel.busy)


if __name__ == '__main__':
    unittest.main(verbosity=2)
