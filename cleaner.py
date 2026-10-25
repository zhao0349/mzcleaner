"""执行选中文件删除；只统计实际删除的字节，保留并报告失败。"""
import os
from dataclasses import dataclass


@dataclass
class CleanResult:
    success: bool
    path: str
    size: int
    error: str = ""


class FileCleaner:
    def delete_files(self, paths):
        results = []
        for path in paths:
            try:
                size = os.lstat(path).st_size
                os.remove(path)
                results.append(CleanResult(True, path, size))
            except FileNotFoundError:
                results.append(CleanResult(True, path, 0))
            except OSError as ex:
                results.append(CleanResult(False, path, 0, str(ex)))
        return results

    def clean_directory_contents(self, dir_path):
        if not os.path.isdir(dir_path):
            return CleanResult(False, dir_path, 0, "目录不存在")
        if os.path.islink(dir_path) or os.path.isjunction(dir_path):
            return CleanResult(False, dir_path, 0, "跳过目录链接")
        errors = []
        total = 0

        def clean(path):
            nonlocal total
            try:
                with os.scandir(path) as entries:
                    for entry in entries:
                        try:
                            if entry.is_symlink() or entry.is_junction():
                                errors.append(f"跳过链接：{entry.name}")
                            elif entry.is_dir(follow_symlinks=False):
                                clean(entry.path)
                                os.rmdir(entry.path)
                            elif entry.is_file(follow_symlinks=False):
                                size = entry.stat(follow_symlinks=False).st_size
                                os.remove(entry.path)
                                total += size
                        except OSError as ex:
                            errors.append(f"{entry.name}: {ex}")
            except OSError as ex:
                errors.append(str(ex))

        clean(dir_path)
        return CleanResult(not errors, dir_path, total, "；".join(errors[:3]))
