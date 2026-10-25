# 磨针清理 · 免费简化版 0.1.0

基于 mzcleaner/mzcleaner 公开 Python 源码的独立简化版，非原作者官方发行版。
无需账号、扫码、付费或在线授权。桌面运行库随包提供，不需要另装 Python。

## 使用

Windows 10/11 x64：完整解压便携 ZIP，运行 MzCleanerFree.exe。
保留同目录的 _internal 文件夹。默认以普通用户权限运行。

- 缓存清理：用户临时目录、Windows Temp、Chrome/Edge 默认配置的 Cache 与 Code Cache。
- 大文件查找：选择目录，查找不小于 100 MB 的文件。
- 重复文件查找：对小于 100 MB 的非空文件按大小和 MD5 分组，每组留下第一份，列出其他副本。
- 相似文件分析：只读，按名称和大小分析 1 KB～10 MB 的常见媒体、文档文件。
- 目录大小分析、软件占用分析：只读。

清理项默认不选中。勾选后点击“清理选中项”，确认框列出目标路径。
确认后永久删除，不进入回收站。锁定或无权限的项目保留，并显示失败原因；不会自动提权。
重复文件的保留副本由扫描顺序决定，请核对路径后选择。
软件占用只统计注册表中有安装路径的项目，多个项目可能共享路径。

未包含登录/VIP/客服推广、用户目录迁移、软件搬家，以及原版直接删除系统组件仓库、微信/QQ附件的入口。
本版不自动扫描、不自动清理、不请求作者的登录或支付接口。Flet 桌面界面通过本机回环连接与 Python 后端通信。

## 修复

- 确认清理直接 await 异步操作，不再从无事件循环的线程调用 ensure_future。
- 成功项移除，失败项保留；只统计实际删除的字节。
- 工作线程负责扫描与文件操作，界面更新回到事件循环。
- 扫描/清理期间禁止切换任务和修改选择。
- 停止扫描保留已有结果，扫描异常不会改写为“未发现可清理项”。
- 分析页不提供删除入口；目录链接不递归清理。

## 开发与打包

使用 PowerShell 7 和 Python 3.14 x64（此次构建版本 3.14.7）。

~~~powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-build.txt
.\.venv\Scripts\python.exe main.py
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
pwsh -File build.ps1 -Python .\.venv\Scripts\python.exe
~~~

便携目录输出到 dist/MzCleanerFree。构建依赖 Flet 0.28.3、PyInstaller 6.22.3。
实际依赖版本以分发包 BUILD-INFO.json 为准。
源代码提交后，运行 `.\.venv\Scripts\python.exe package.py` 生成便携 ZIP、源码 ZIP 与 SHA256SUMS.txt。

## 来源与许可

上游：https://github.com/mzcleaner/mzcleaner
基线：852c9617737503ec5db3015565d8cd4609e0c6ea。
保留上游 LICENSE（MIT）。修改后的源代码随测试包另行提供。
Flet/Flet Desktop 为 Apache-2.0；其他运行时声明随包保留于 licenses 与 _internal 中。

测试范围：自建临时样本的清理回归和当前 Windows 桌面检查。
不表示已经覆盖不同机器、系统权限、软件版本和真实聊天数据。
