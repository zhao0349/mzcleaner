"""核心扫描引擎 - 支持多种C盘清理扫描类型"""

import os
import hashlib
import threading
from pathlib import Path
from dataclasses import dataclass, field


@dataclass
class ScanResult:
    """单条扫描结果"""
    name: str           # 文件/目录名称
    path: str           # 完整路径
    size: int           # 字节数
    category: str       # 分类标签
    is_file: bool = True

    @property
    def size_display(self) -> str:
        """格式化文件大小为人类可读格式"""
        if self.size < 1024:
            return f"{self.size} B"
        elif self.size < 1024 * 1024:
            return f"{self.size / 1024:.1f} KB"
        elif self.size < 1024 * 1024 * 1024:
            return f"{self.size / (1024 * 1024):.2f} MB"
        else:
            return f"{self.size / (1024 * 1024 * 1024):.2f} GB"


@dataclass
class ScanTask:
    """扫描任务配置"""
    scan_type: str      # 扫描类型标识
    title: str          # 显示标题
    description: str    # 描述文本


# 扫描类型常量
SCAN_TYPES = {
    "basic_clean": ScanTask(
        scan_type="basic_clean",
        title="基础清理",
        description="扫描Windows临时文件、回收站、浏览器缓存等系统垃圾"
    ),
    "system_clean": ScanTask(
        scan_type="system_clean",
        title="系统清理",
        description="扫描Windows更新缓存、系统日志、事件日志等深层系统垃圾"
    ),
    "wechat_clean": ScanTask(
        scan_type="wechat_clean",
        title="微信清理",
        description="扫描微信聊天缓存、图片、视频、文件等占用空间"
    ),
    "qq_clean": ScanTask(
        scan_type="qq_clean",
        title="QQ清理",
        description="扫描QQ聊天缓存、图片、文件等占用空间"
    ),
    "user_dir_migrate": ScanTask(
        scan_type="user_dir_migrate",
        title="用户目录迁移",
        description="查看用户文档、桌面、下载等目录占用，支持迁移到其他磁盘"
    ),
    "software_usage": ScanTask(
        scan_type="software_usage",
        title="软件占用查询",
        description="查询已安装软件的磁盘占用情况"
    ),
    "software_move": ScanTask(
        scan_type="software_move",
        title="软件搬家",
        description="查看大型软件的安装位置，辅助迁移到其他磁盘"
    ),
    "large_files": ScanTask(
        scan_type="large_files",
        title="大文件查找",
        description="递归扫描指定目录，找出超过阈值的大文件"
    ),
    "duplicate_files": ScanTask(
        scan_type="duplicate_files",
        title="重复文件查找",
        description="通过MD5哈希值精确查找内容完全相同的重复文件"
    ),
    "similar_files": ScanTask(
        scan_type="similar_files",
        title="相似文件查找",
        description="根据文件名和大小查找可能相似的文件"
    ),
    "dir_size_view": ScanTask(
        scan_type="dir_size_view",
        title="目录大小查看",
        description="计算指定目录下各子目录的大小分布情况"
    ),
}


class DiskScanner:
    """磁盘扫描器 - 所有扫描逻辑的统一入口"""

    def __init__(self, progress_callback=None):
        self.progress_callback = progress_callback
        self._cancelled = False
        self._results: list[ScanResult] = []
        self._total_size = 0

    def cancel(self):
        """取消当前扫描"""
        self._cancelled = True

    def _report_progress(self, message: str, current: int = 0, total: int = 0):
        if self.progress_callback:
            self.progress_callback(message, current, total)

    # ── 工具方法 ──────────────────────────────────────────

    @staticmethod
    def _get_file_size(path: str) -> int:
        try:
            return os.path.getsize(path)
        except (OSError, PermissionError):
            return 0

    @staticmethod
    def _get_dir_size(dir_path: str) -> int:
        """计算目录总大小"""
        total = 0
        try:
            for entry in os.scandir(dir_path):
                try:
                    if entry.is_file(follow_symlinks=False):
                        total += entry.stat().st_size
                    elif entry.is_dir(follow_symlinks=False):
                        total += DiskScanner._get_dir_size(entry.path)
                except (OSError, PermissionError):
                    continue
        except (OSError, PermissionError):
            pass
        return total

    @staticmethod
    def _safe_listdir(dir_path: str) -> list:
        """安全列出目录内容"""
        try:
            return os.listdir(dir_path)
        except (OSError, PermissionError):
            return []

    @staticmethod
    def _expand_env_path(path: str) -> str:
        """展开环境变量路径"""
        return os.path.expandvars(path)

    # ── 基础清理 ──────────────────────────────────────────

    def scan_basic_clean(self) -> list[ScanResult]:
        """扫描基础系统垃圾"""
        self._cancelled = False
        results = []
        targets = []

        # Windows Temp
        temp_dir = self._expand_env_path("%TEMP%")
        if os.path.isdir(temp_dir):
            size = self._get_dir_size(temp_dir)
            if size > 0:
                results.append(ScanResult(
                    name="临时文件(Temp)",
                    path=temp_dir,
                    size=size,
                    category="临时文件"
                ))

        # Windows Temp (System)
        windir = os.environ.get("WINDIR", "C:\\Windows")
        sys_temp = os.path.join(windir, "Temp")
        if os.path.isdir(sys_temp):
            size = self._get_dir_size(sys_temp)
            if size > 0:
                results.append(ScanResult(
                    name="系统临时文件",
                    path=sys_temp,
                    size=size,
                    category="临时文件"
                ))

        # Prefetch
        prefetch = os.path.join(windir, "Prefetch")
        if os.path.isdir(prefetch):
            size = self._get_dir_size(prefetch)
            if size > 0:
                results.append(ScanResult(
                    name="预读取文件(Prefetch)",
                    path=prefetch,
                    size=size,
                    category="系统缓存"
                ))

        # Recent files
        userprofile = os.environ.get("USERPROFILE", "")
        recent = os.path.join(userprofile, "AppData", "Roaming", "Microsoft", "Windows", "Recent")
        if os.path.isdir(recent):
            size = self._get_dir_size(recent)
            if size > 0:
                results.append(ScanResult(
                    name="最近文档记录",
                    path=recent,
                    size=size,
                    category="系统记录"
                ))

        # Recycle Bin (check size)
        for drive_letter in ["C:", "D:", "E:", "F:"]:
            recycle = os.path.join(drive_letter + "\\", "$Recycle.Bin")
            if os.path.isdir(recycle):
                size = self._get_dir_size(recycle)
                if size > 0:
                    results.append(ScanResult(
                        name=f"回收站({drive_letter})",
                        path=recycle,
                        size=size,
                        category="回收站"
                    ))

        # Browser cache paths
        appdata_local = os.path.join(userprofile, "AppData", "Local")
        browser_caches = {
            "Chrome缓存": os.path.join(appdata_local, "Google", "Chrome", "User Data", "Default", "Cache"),
            "Edge缓存": os.path.join(appdata_local, "Microsoft", "Edge", "User Data", "Default", "Cache"),
            "Chrome Code Cache": os.path.join(appdata_local, "Google", "Chrome", "User Data", "Default", "Code Cache"),
            "Edge Code Cache": os.path.join(appdata_local, "Microsoft", "Edge", "User Data", "Default", "Code Cache"),
        }
        for name, path in browser_caches.items():
            if os.path.isdir(path):
                size = self._get_dir_size(path)
                if size > 0:
                    results.append(ScanResult(
                        name=name,
                        path=path,
                        size=size,
                        category="浏览器缓存"
                    ))

        self._results = results
        self._total_size = sum(r.size for r in results)
        self._report_progress("基础清理扫描完成", len(results), len(results))
        return results

    # ── 系统清理 ──────────────────────────────────────────

    def scan_system_clean(self) -> list[ScanResult]:
        """扫描系统级垃圾文件"""
        self._cancelled = False
        results = []
        windir = os.environ.get("WINDIR", "C:\\Windows")

        # Windows Update 缓存
        update_cache = os.path.join(windir, "SoftwareDistribution", "Download")
        if os.path.isdir(update_cache):
            size = self._get_dir_size(update_cache)
            if size > 0:
                results.append(ScanResult(
                    name="Windows更新缓存",
                    path=update_cache,
                    size=size,
                    category="系统更新"
                ))

        # Delivery Optimization
        delopt = os.path.join(windir, "SoftwareDistribution", "DeliveryOptimization")
        if os.path.isdir(delopt):
            size = self._get_dir_size(delopt)
            if size > 0:
                results.append(ScanResult(
                    name="传递优化文件",
                    path=delopt,
                    size=size,
                    category="系统更新"
                ))

        # CBS Logs
        cbs_logs = os.path.join(windir, "Logs", "CBS")
        if os.path.isdir(cbs_logs):
            size = self._get_dir_size(cbs_logs)
            if size > 0:
                results.append(ScanResult(
                    name="CBS系统日志",
                    path=cbs_logs,
                    size=size,
                    category="系统日志"
                ))

        # Windows Logs
        logs_dir = os.path.join(windir, "Logs")
        if os.path.isdir(logs_dir):
            size = self._get_dir_size(logs_dir)
            if size > 0:
                results.append(ScanResult(
                    name="Windows日志目录",
                    path=logs_dir,
                    size=size,
                    category="系统日志"
                ))

        # Dism cleanup
        winsxs = os.path.join(windir, "WinSxS", "ManifestCache")
        if os.path.isdir(winsxs):
            size = self._get_dir_size(winsxs)
            if size > 0:
                results.append(ScanResult(
                    name="WinSxS清单缓存",
                    path=winsxs,
                    size=size,
                    category="系统缓存"
                ))

        # DriverStore FileRepository
        driver_repo = os.path.join(windir, "System32", "DriverStore", "FileRepository")
        if os.path.isdir(driver_repo):
            size = self._get_dir_size(driver_repo)
            if size > 0:
                results.append(ScanResult(
                    name="驱动备份仓库",
                    path=driver_repo,
                    size=size,
                    category="系统备份"
                ))

        # ServicePack backup
        sp_backup = os.path.join(windir, "ServicePackFiles")
        if os.path.isdir(sp_backup):
            size = self._get_dir_size(sp_backup)
            if size > 0:
                results.append(ScanResult(
                    name="ServicePack备份",
                    path=sp_backup,
                    size=size,
                    category="系统备份"
                ))

        # FontCache
        userprofile = os.environ.get("USERPROFILE", "")
        font_cache = os.path.join(userprofile, "AppData", "Local", "Microsoft", "Windows", "FontCache")
        if os.path.isdir(font_cache):
            size = self._get_dir_size(font_cache)
            if size > 0:
                results.append(ScanResult(
                    name="字体缓存",
                    path=font_cache,
                    size=size,
                    category="系统缓存"
                ))

        self._results = results
        self._total_size = sum(r.size for r in results)
        self._report_progress("系统清理扫描完成", len(results), len(results))
        return results

    # ── 微信清理 ──────────────────────────────────────────

    def scan_wechat_clean(self) -> list[ScanResult]:
        """扫描微信缓存文件"""
        self._cancelled = False
        results = []
        userprofile = os.environ.get("USERPROFILE", "")
        wechat_base = os.path.join(userprofile, "Documents", "WeChat Files")

        if not os.path.isdir(wechat_base):
            self._report_progress("未找到微信数据目录", 0, 0)
            return results

        # 遍历微信号目录
        for wxid in self._safe_listdir(wechat_base):
            wx_path = os.path.join(wechat_base, wxid)
            if not os.path.isdir(wx_path):
                continue

            # FileStorage 下的各类缓存
            file_storage = os.path.join(wx_path, "FileStorage")
            if os.path.isdir(file_storage):
                sub_dirs = {
                    "Image": "图片缓存",
                    "Video": "视频缓存",
                    "File": "收发文件",
                    "MsgAttach": "聊天附件",
                    "CustomEmotion": "表情缓存",
                    "Temp": "临时文件",
                }
                for sub, label in sub_dirs.items():
                    sub_path = os.path.join(file_storage, sub)
                    if os.path.isdir(sub_path):
                        size = self._get_dir_size(sub_path)
                        if size > 0:
                            results.append(ScanResult(
                                name=f"微信-{label}({wxid})",
                                path=sub_path,
                                size=size,
                                category="微信缓存"
                            ))
            else:
                # 旧版本微信目录结构
                sub_dirs_map = {
                    "Image": "图片",
                    "Video": "视频",
                    "File": "文件",
                }
                for sub, label in sub_dirs_map.items():
                    sub_path = os.path.join(wx_path, sub)
                    if os.path.isdir(sub_path):
                        size = self._get_dir_size(sub_path)
                        if size > 0:
                            results.append(ScanResult(
                                name=f"微信-{label}({wxid})",
                                path=sub_path,
                                size=size,
                                category="微信缓存"
                            ))

        self._results = results
        self._total_size = sum(r.size for r in results)
        self._report_progress("微信清理扫描完成", len(results), len(results))
        return results

    # ── QQ清理 ────────────────────────────────────────────

    def scan_qq_clean(self) -> list[ScanResult]:
        """扫描QQ缓存文件"""
        self._cancelled = False
        results = []
        userprofile = os.environ.get("USERPROFILE", "")
        qq_base = os.path.join(userprofile, "Documents", "Tencent Files")

        if not os.path.isdir(qq_base):
            self._report_progress("未找到QQ数据目录", 0, 0)
            return results

        for qqnum in self._safe_listdir(qq_base):
            qq_path = os.path.join(qq_base, qqnum)
            if not os.path.isdir(qq_path):
                continue

            sub_dirs = {
                "Image": "图片",
                "Video": "视频",
                "FileRecv": "接收文件",
                "Audio": "语音消息",
                "Pic": "聊天图片",
            }
            for sub, label in sub_dirs.items():
                sub_path = os.path.join(qq_path, sub)
                if os.path.isdir(sub_path):
                    # 先看子目录（如 Group2, C2C, MobileFile）
                    total_size = 0
                    for inner in self._safe_listdir(sub_path):
                        inner_path = os.path.join(sub_path, inner)
                        if os.path.isdir(inner_path):
                            total_size += self._get_dir_size(inner_path)
                    if total_size == 0:
                        total_size = self._get_dir_size(sub_path)
                    if total_size > 0:
                        results.append(ScanResult(
                            name=f"QQ-{label}({qqnum})",
                            path=sub_path,
                            size=total_size,
                            category="QQ缓存"
                        ))

        self._results = results
        self._total_size = sum(r.size for r in results)
        self._report_progress("QQ清理扫描完成", len(results), len(results))
        return results

    # ── 用户目录迁移 ──────────────────────────────────────

    def scan_user_dirs(self) -> list[ScanResult]:
        """扫描用户目录大小"""
        self._cancelled = False
        results = []
        userprofile = os.environ.get("USERPROFILE", "")

        user_dirs = {
            "桌面": os.path.join(userprofile, "Desktop"),
            "文档": os.path.join(userprofile, "Documents"),
            "下载": os.path.join(userprofile, "Downloads"),
            "图片": os.path.join(userprofile, "Pictures"),
            "音乐": os.path.join(userprofile, "Music"),
            "视频": os.path.join(userprofile, "Videos"),
            "收藏夹": os.path.join(userprofile, "Favorites"),
            "桌面(公用)": os.path.join(os.environ.get("PUBLIC", ""), "Desktop"),
        }

        for name, path in user_dirs.items():
            if os.path.isdir(path):
                self._report_progress(f"正在计算: {name}", 0, 0)
                size = self._get_dir_size(path)
                results.append(ScanResult(
                    name=name,
                    path=path,
                    size=size,
                    category="用户目录",
                    is_file=False
                ))

        self._results = results
        self._total_size = sum(r.size for r in results)
        self._report_progress("用户目录扫描完成", len(results), len(results))
        return results

    # ── 软件占用查询 ──────────────────────────────────────

    def scan_software_usage(self) -> list[ScanResult]:
        """通过注册表查询已安装软件及其占用"""
        self._cancelled = False
        results = []

        reg_paths = [
            r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall",
            r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall",
        ]

        try:
            import winreg
            for reg_path in reg_paths:
                try:
                    key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, reg_path)
                    for i in range(winreg.QueryInfoKey(key)[0]):
                        if self._cancelled:
                            winreg.CloseKey(key)
                            return results
                        try:
                            subkey_name = winreg.EnumKey(key, i)
                            subkey = winreg.OpenKey(key, subkey_name)
                            try:
                                display_name = winreg.QueryValueEx(subkey, "DisplayName")[0]
                            except (OSError, FileNotFoundError):
                                winreg.CloseKey(subkey)
                                continue
                            try:
                                install_location = winreg.QueryValueEx(subkey, "InstallLocation")[0]
                            except (OSError, FileNotFoundError):
                                install_location = ""
                            winreg.CloseKey(subkey)

                            if install_location and os.path.isdir(install_location):
                                size = self._get_dir_size(install_location)
                                if size > 0:
                                    results.append(ScanResult(
                                        name=display_name,
                                        path=install_location,
                                        size=size,
                                        category="已安装软件",
                                        is_file=False
                                    ))
                        except (OSError, FileNotFoundError):
                            continue
                    winreg.CloseKey(key)
                except (OSError, FileNotFoundError):
                    continue
        except ImportError:
            self._report_progress("无法访问Windows注册表", 0, 0)
            return results

        # 按大小降序排序
        results.sort(key=lambda x: x.size, reverse=True)
        self._results = results
        self._total_size = sum(r.size for r in results)
        self._report_progress("软件占用查询完成", len(results), len(results))
        return results

    # ── 大文件查找 ────────────────────────────────────────

    def scan_large_files(self, scan_paths: list[str] = None, min_size_mb: int = 100) -> list[ScanResult]:
        """查找指定目录下的大文件"""
        self._cancelled = False
        results = []
        min_size = min_size_mb * 1024 * 1024

        if scan_paths is None:
            scan_paths = ["C:\\"]

        self._report_progress("开始扫描大文件...", 0, 0)

        for scan_root in scan_paths:
            if self._cancelled:
                break
            try:
                for root, dirs, files in os.walk(scan_root):
                    if self._cancelled:
                        break
                    # 跳过系统目录
                    dirs[:] = [d for d in dirs if not d.startswith("$") and d not in ("System Volume Information",)]
                    for filename in files:
                        if self._cancelled:
                            break
                        filepath = os.path.join(root, filename)
                        try:
                            size = os.path.getsize(filepath)
                            if size >= min_size:
                                results.append(ScanResult(
                                    name=filename,
                                    path=filepath,
                                    size=size,
                                    category="大文件"
                                ))
                        except (OSError, PermissionError):
                            continue
            except (OSError, PermissionError):
                continue

        results.sort(key=lambda x: x.size, reverse=True)
        self._results = results
        self._total_size = sum(r.size for r in results)
        self._report_progress("大文件查找完成", len(results), len(results))
        return results

    # ── 重复文件查找 ──────────────────────────────────────

    def scan_duplicate_files(self, scan_paths: list[str] = None) -> list[ScanResult]:
        """通过MD5找出内容重复的文件（分组显示）"""
        self._cancelled = False
        if scan_paths is None:
            scan_paths = ["C:\\"]

        self._report_progress("正在收集文件列表...", 0, 0)

        # 第一步：收集所有文件，按大小分组
        size_map: dict[int, list[str]] = {}
        for scan_root in scan_paths:
            if self._cancelled:
                break
            try:
                for root, dirs, files in os.walk(scan_root):
                    if self._cancelled:
                        break
                    dirs[:] = [d for d in dirs if not d.startswith("$") and d not in ("System Volume Information",)]
                    for filename in files:
                        if self._cancelled:
                            break
                        filepath = os.path.join(root, filename)
                        try:
                            size = os.path.getsize(filepath)
                            if size > 0 and size < 100 * 1024 * 1024:  # 跳过空文件和超大文件
                                if size not in size_map:
                                    size_map[size] = []
                                size_map[size].append(filepath)
                        except (OSError, PermissionError):
                            continue
            except (OSError, PermissionError):
                continue

        # 第二步：对同大小的文件进行MD5比对
        results = []
        processed = 0
        potential_groups = [files for files in size_map.values() if len(files) >= 2]
        total_groups = len(potential_groups)

        for file_group in potential_groups:
            if self._cancelled:
                break
            processed += 1
            if processed % 100 == 0:
                self._report_progress(f"正在比对哈希值... ({processed}/{total_groups})", processed, total_groups)

            hash_map: dict[str, list[str]] = {}
            for filepath in file_group:
                if self._cancelled:
                    break
                try:
                    file_hash = self._compute_md5(filepath)
                    if file_hash is None:
                        continue
                    if file_hash not in hash_map:
                        hash_map[file_hash] = []
                    hash_map[file_hash].append(filepath)
                except (OSError, PermissionError):
                    continue

            for file_hash, dup_group in hash_map.items():
                if len(dup_group) >= 2:
                    file_size = os.path.getsize(dup_group[0])
                    for fp in dup_group[1:]:  # 保留第一个，其余标记为重复
                        results.append(ScanResult(
                            name=os.path.basename(fp),
                            path=fp,
                            size=file_size,
                            category="重复文件"
                        ))

        results.sort(key=lambda x: x.size, reverse=True)
        self._results = results
        self._total_size = sum(r.size for r in results)
        self._report_progress("重复文件查找完成", len(results), len(results))
        return results

    # ── 相似文件查找 ──────────────────────────────────────

    def scan_similar_files(self, scan_paths: list[str] = None) -> list[ScanResult]:
        """根据文件名相似度查找可能重复的文件"""
        self._cancelled = False
        if scan_paths is None:
            scan_paths = ["C:\\"]

        self._report_progress("正在扫描相似文件...", 0, 0)

        # 收集文件，按 (名称前缀, 大小) 分组
        name_size_map: dict[tuple, list[str]] = {}
        suffixes_to_check = {".jpg", ".jpeg", ".png", ".gif", ".bmp",
                             ".mp4", ".avi", ".mkv", ".mov",
                             ".mp3", ".wav", ".flac",
                             ".doc", ".docx", ".pdf", ".xlsx", ".pptx",
                             ".zip", ".rar", ".7z"}

        for scan_root in scan_paths:
            if self._cancelled:
                break
            try:
                for root, dirs, files in os.walk(scan_root):
                    if self._cancelled:
                        break
                    dirs[:] = [d for d in dirs if not d.startswith("$") and d not in ("System Volume Information",)]
                    for filename in files:
                        if self._cancelled:
                            break
                        ext = os.path.splitext(filename)[1].lower()
                        if ext not in suffixes_to_check:
                            continue
                        filepath = os.path.join(root, filename)
                        try:
                            size = os.path.getsize(filepath)
                            if 1024 < size < 10 * 1024 * 1024:  # 1KB ~ 10MB
                                # 提取名称关键词（去掉括号内容、数字后缀）
                                name_base = self._normalize_name(filename)
                                key = (name_base, size)
                                if key not in name_size_map:
                                    name_size_map[key] = []
                                name_size_map[key].append(filepath)
                        except (OSError, PermissionError):
                            continue
            except (OSError, PermissionError):
                continue

        results = []
        for (name_base, size), file_list in name_size_map.items():
            if len(file_list) >= 2:
                # 所有文件都标记为相似
                for fp in file_list:
                    results.append(ScanResult(
                        name=os.path.basename(fp),
                        path=fp,
                        size=size,
                        category="相似文件"
                    ))

        results.sort(key=lambda x: x.size, reverse=True)
        self._results = results
        self._total_size = sum(r.size for r in results)
        self._report_progress("相似文件查找完成", len(results), len(results))
        return results

    # ── 目录大小查看 ──────────────────────────────────────

    def scan_dir_sizes(self, scan_path: str = None) -> list[ScanResult]:
        """查看目录的大小分布"""
        self._cancelled = False
        if scan_path is None:
            scan_path = "C:\\"

        self._report_progress(f"正在分析目录: {scan_path}", 0, 0)

        results = []
        try:
            for entry in os.scandir(scan_path):
                if self._cancelled:
                    break
                if entry.is_dir(follow_symlinks=False):
                    self._report_progress(f"正在计算: {entry.name}", 0, 0)
                    size = self._get_dir_size(entry.path)
                    results.append(ScanResult(
                        name=entry.name,
                        path=entry.path,
                        size=size,
                        category="目录",
                        is_file=False
                    ))
        except (OSError, PermissionError):
            pass

        results.sort(key=lambda x: x.size, reverse=True)
        self._results = results
        self._total_size = sum(r.size for r in results)
        self._report_progress("目录大小查看完成", len(results), len(results))
        return results

    # ── 辅助方法 ──────────────────────────────────────────

    @staticmethod
    def _compute_md5(filepath: str, chunk_size: int = 8192) -> str | None:
        """计算文件的MD5哈希值"""
        try:
            md5 = hashlib.md5()
            with open(filepath, "rb") as f:
                while chunk := f.read(chunk_size):
                    md5.update(chunk)
            return md5.hexdigest()
        except (OSError, PermissionError):
            return None

    @staticmethod
    def _normalize_name(filename: str) -> str:
        """标准化文件名：去除括号内容、数字后缀"""
        import re
        name = os.path.splitext(filename)[0]
        # 去除括号及内容：(1), (副本), (copy) 等
        name = re.sub(r'[\(\（].*?[\)\）]', '', name)
        # 去除末尾数字
        name = re.sub(r'[\s_\-]*\d+$', '', name)
        # 去除 copy
        name = re.sub(r'\s*[-_]\s*[Cc]opy\s*$', '', name)
        name = re.sub(r'\s*[-_]\s*副本\s*$', '', name)
        name = name.strip()
        return name.lower() if name else filename.lower()

    # ── 公共接口 ──────────────────────────────────────────

    @property
    def total_size(self) -> int:
        return self._total_size

    @property
    def total_size_display(self) -> str:
        return self._format_size(self._total_size)

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
