# 抖音视频下载工具（Douyin Downloader）

> 佐喃社区出品（测试版） · zzznan.com

一个 Windows 下简单好用的抖音视频下载工具：粘贴分享口令/链接，一键下载无水印视频。

## 功能特性

- **一键下载**：粘贴抖音链接、分享短链或整段分享口令，点「⬇ 一键下载」即可
- **自动提取直链**：内置 CDP 自动驱动本机 Chrome/Edge 打开视频页提取签名直链（无需登录、无需 Cookie）
- **多方式兼容**：支持 cookies.txt、签名直链（douyinvod）直接下载
- **图形界面**：深色主题，带佐喃社区 logo，日志实时显示，一键打开输出目录
- **命令行可用**：适合脚本化、批量使用

## 界面预览

- 顶部：佐喃社区 logo + 「佐喃社区出品（测试版）」
- 输入框：粘贴链接/口令
- 可选：cookies.txt、保存目录
- 按钮：「⬇ 一键下载」「打开输出目录」
- 日志区：实时显示下载进度与结果

## 快速开始

### 方式一：直接使用 exe（推荐普通用户）

下载 `douyin_downloader.exe` 双击运行即可（需本机装有 Python 3.10+ 及 yt-dlp，程序会自动探测调用）。

### 方式二：源码运行

```bash
# 安装依赖
python -m pip install -U yt-dlp pillow websocket-client

# 命令行下载
python douyin_downloader.py "https://v.douyin.com/xxxx/"
python douyin_downloader.py "8.88 复制打开抖音看看… https://v.douyin.com/xxxx/ 口令文本"

# 图形界面
python douyin_downloader_gui.py
```

### 签名直链模式（可选）

- 浏览器打开抖音视频页 → 右键视频 → 复制视频地址（douyinvod 开头的链接）
- 命令行：`python douyin_downloader.py "<链接>" --direct "<签名直链>"`
- GUI：勾选「我粘贴的是签名直链」后粘贴

### cookies.txt 模式（可选）

浏览器安装扩展「Get cookies.txt LOCALLY」，打开一条抖音视频页后导出 cookies.txt：

```bash
python douyin_downloader.py "<链接>" --cookies cookies.txt
```

## 命令行参数

| 参数 | 说明 |
|------|------|
| `input` | 抖音视频链接 / 分享短链 / 分享口令 |
| `--cookies <file>` | Netscape 格式 cookies.txt |
| `--direct <url>` | 直接下载已提取的签名直链（跳过解析） |
| `--output <dir>` | 输出目录（默认：脚本旁 douyin_downloads） |
| `--info` | 只查视频信息，不下载 |
| `--no-browser-cookies` | 不尝试浏览器 cookies |

## 打包为 exe

```bash
python -m PyInstaller --noconfirm --onefile --windowed --name douyin_downloader \
  --add-data "zuonan_logo.png;." --icon "zuonan_logo.ico" \
  douyin_downloader_gui.py
```

## 技术说明

- 下载核心：yt-dlp（需 ≥2026.x，旧版抖音解析已失效）
- 自动提取：CDP 驱动本机 Chrome/Edge（headless=new + --remote-allow-origins=*），打开视频页后触发播放，轮询 `video.currentSrc` 获取 douyinvod 签名直链
- 签名直链约 2 小时有效，过期需重新提取
- 纯脚本无 Cookie 直抓会被抖音安全验证拦截，这是抖音的正常防护

## 文件结构

```
douyin-downloader/
├── douyin_downloader.py        # 命令行核心（解析/策略/直链下载/校验）
├── douyin_downloader_gui.py    # tkinter 图形界面
├── zuonan_logo.png             # 界面 logo
├── zuonan_logo.ico             # exe/窗口图标
└── douyin_downloader.exe       # 打包好的独立程序（可选）
```

## 免责声明

本工具仅用于个人学习与研究，请遵守抖音平台及相关法律法规，不要用于侵犯他人版权等用途。下载内容版权归原作者所有。

---

佐喃社区 · zzznan.com
