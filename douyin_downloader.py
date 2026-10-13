#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
douyin_downloader.py — 抖音视频下载工具（Windows / Python 3.10+）

用法示例：
    python douyin_downloader.py "https://www.douyin.com/video/7695624957384002826"
    python douyin_downloader.py "https://v.douyin.com/xxxx/"          # 分享短链
    python douyin_downloader.py "8.88 复制打开抖音看看..."              # 分享口令（自动提取链接）
    python douyin_downloader.py "<链接>" --cookies cookies.txt        # 指定浏览器导出的 cookies
    python douyin_downloader.py "<链接>" --info                      # 只查标题/时长/作者
    python douyin_downloader.py "<链接>" --direct "https://v26-web.douyinvod.com/...signed..."   # 直接下载已提取的签名直链
    python douyin_downloader.py "<链接>" --output "D:/videos"

策略（自动按顺序尝试）：
    1. 用户指定 --cookies <cookies.txt>（浏览器插件导出的 Netscape 格式）
    2. --cookies-from-browser 依次尝试本机 edge / chrome / firefox
    3. 以上都失败时给出明确指引（抖音要求新鲜 Cookie，纯脚本直抓会被安全验证拦截）
    4. --direct 可绕过解析，直接下载浏览器/助手已提取出的签名直链（链接约 2 小时有效）

依赖：yt-dlp（`python -m pip install -U yt-dlp`）。未安装时 --direct 模式仍可用。
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
import urllib.error

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36")

URL_RE = re.compile(r"https?://[^\s\"'，。、；：（）【】]+", re.IGNORECASE)
DOUYIN_VIDEO_RE = re.compile(r"douyin\.com/(?:video|note|discover)/(\d+)", re.IGNORECASE)


def find_ytdlp():
    """定位可用的 yt-dlp（python -m yt_dlp），避免 PATH 上旧版 yt-dlp.exe 干扰。

    按顺序尝试：当前解释器（含打包后的 exe）→ PATH 上的 python/python3 →
    常见 Python 安装路径；只要某个 python 里装有 yt_dlp 模块即可用。
    """
    code = "import yt_dlp; print(yt_dlp.version.__version__)"
    candidates = []
    for exe in [
        sys.executable,
        shutil.which("python"),
        shutil.which("python3"),
        shutil.which("py"),
        r"C:\Users\ZN34\AppData\Local\Programs\Python\Python314\python.exe",
    ]:
        if exe and exe not in candidates:
            candidates.append(exe)
    for exe in candidates:
        try:
            r = subprocess.run([exe, "-c", code], capture_output=True, text=True, timeout=20)
            if r.returncode == 0 and r.stdout.strip():
                return [exe, "-m", "yt_dlp"]
        except Exception:
            continue
    if shutil.which("yt-dlp"):
        return ["yt-dlp"]
    return None


def resolve_share_url(text):
    """从输入中提取 URL；短链直接交给 yt-dlp，同时解析出真实视频 ID。"""
    m = URL_RE.search(text or "")
    url = m.group(0) if m else (text or "").strip()
    if not url:
        return None, None, text

    full = url
    video_id = None
    # 若是 douyin 短链，跟随重定向拿到真实页面地址
    if re.search(r"(v\.douyin\.com|douyin\.com)", url, re.IGNORECASE) and re.search(r"v\.douyin\.com", url, re.IGNORECASE):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            resp = urllib.request.urlopen(req, timeout=25)
            full = resp.geturl()
        except Exception as e:
            print(f"[warn] 短链解析失败：{e}，将直接尝试原链接")
            full = url

    m = DOUYIN_VIDEO_RE.search(full)
    if m:
        video_id = m.group(1)
    else:
        # 兼容 share text 中直接带数字 id 的场景
        m2 = re.search(r"(\d{15,20})", full)
        if m2:
            video_id = m2.group(1)
    return url, video_id, full


def sanitize(name, limit=60):
    name = re.sub(r'[\\/:*?"<>|\r\n\t]+', "_", name).strip(" ._")
    return name[:limit] or "douyin_video"


def ytdlp_download(ytdlp, url, cookies_file, browser_candidates, output_dir):
    """用 yt-dlp 下载，逐个策略尝试。返回 (成功, 文件路径, 错误信息)。"""
    base = ytdlp + [
        "--no-warnings",
        "-f", "bv*+ba/b",
        "--merge-output-format", "mp4",
        "-o", os.path.join(output_dir, "%(title)s_%(id)s.%(ext)s"),
        "--restrict-filenames",  # 避免中文/空格导致 Windows 路径问题
    ]
    attempts = []

    if cookies_file:
        attempts.append(("cookies.txt", base + ["--cookies", cookies_file]))
    for b in browser_candidates:
        attempts.append((f"browser:{b}", base + [f"--cookies-from-browser", b]))
    attempts.append(("no-cookies", base))

    last_err = None
    for name, cmd in attempts:
        print(f"[try] {name}")
        r = subprocess.run(cmd + [url], capture_output=True, text=True, timeout=300)
        out = (r.stdout or "") + "\n" + (r.stderr or "")
        if r.returncode == 0:
            # 找到实际产物文件
            dest = None
            for line in (r.stdout or "").splitlines():
                m = re.search(r"Destination:\s*(.+)$", line) or re.search(r"Merging formats into\s*[\"']?([^\"']+)[\"']?\s*$", line)
                if m:
                    dest = m.group(1).strip()
                    break
            return True, dest, out
        last_err = out
        if "Fresh cookies" not in out and "cookies" not in out.lower() and "sign in" not in out.lower():
            # 非 Cookie 类错误（如视频不存在/地区限制），继续试也没意义，提前终止
            return False, None, out
    return False, None, last_err


def download_direct(signed_url, video_id, output_dir, fallback_name):
    """直接下载签名直链（--direct 模式），带 Referer 头。"""
    os.makedirs(output_dir, exist_ok=True)
    name = sanitize(fallback_name or f"douyin_{video_id or 'video'}")
    dest = os.path.join(output_dir, f"{name}_{video_id}.mp4") if video_id else os.path.join(output_dir, f"{name}.mp4")
    req = urllib.request.Request(signed_url, headers={
        "User-Agent": UA,
        "Referer": "https://www.douyin.com/",
        "Accept": "*/*",
    })
    with urllib.request.urlopen(req, timeout=120) as resp, open(dest, "wb") as f:
        while True:
            chunk = resp.read(65536)
            if not chunk:
                break
            f.write(chunk)
    if os.path.getsize(dest) > 0:
        return True, dest
    return False, dest


def verify_mp4(path):
    try:
        with open(path, "rb") as f:
            head = f.read(12)
        return head[4:8] == b"ftyp"
    except Exception:
        return False


def print_info(ytdlp, url, cookies_file, browser_candidates):
    cmd = ytdlp + ["--no-warnings", "--simulate", "--print",
                   "标题: %(title)s\n作者: %(uploader)s\n时长: %(duration)s 秒\n尺寸: %(width)sx%(height)s",
                   "--cookies-from-browser", browser_candidates[0]] if browser_candidates else ytdlp + ["--simulate"]
    # 简化：统一试一次 browser:candidates[0]
    args = ytdlp + ["--no-warnings", "--simulate", "--print",
                    "标题: %(title)s | 作者: %(uploader)s | 时长: %(duration)s 秒 | 尺寸: %(width)sx%(height)s"]
    if cookies_file:
        args += ["--cookies", cookies_file]
    elif browser_candidates:
        args += ["--cookies-from-browser", browser_candidates[0]]
    r = subprocess.run(args + [url], capture_output=True, text=True, timeout=120)
    print((r.stdout or "") + (r.stderr or ""))


def default_output_dir():
    """确定默认输出目录。

    - 打包成 exe（--onefile）时，__file__ 指向临时解压目录（_MEI...），
      必须改用 exe 所在目录，否则下载产物会丢进临时目录；
    - 脚本模式保持脚本旁 douyin_downloads。
    """
    if getattr(sys, "frozen", False):
        base = os.path.dirname(os.path.abspath(sys.executable))
        try:
            d = os.path.join(base, "douyin_downloads")
            os.makedirs(d, exist_ok=True)
            return d
        except Exception:
            pass
        d = os.path.join(os.path.expanduser("~"), "Downloads", "douyin_downloads")
        os.makedirs(d, exist_ok=True)
        return d
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "douyin_downloads")


BROWSER_CANDIDATES = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
]


def find_browser():
    """返回本机可用的 Chrome/Edge 可执行路径。"""
    for p in BROWSER_CANDIDATES:
        if os.path.exists(p):
            return p
    return shutil.which("chrome") or shutil.which("msedge")


def extract_direct_with_browser(video_page_url, headless=True, timeout=45):
    """用本机 Chrome/Edge（CDP 协议）打开视频页，自动提取签名直链。

    抖音对纯脚本/无 Cookie 请求返回验证码页，但真实浏览器（未登录即可）
    能正常渲染并拿到 <video> 播放地址。本函数借助 Chrome 的
    --remote-debugging-port 用 CDP 读取 `video.currentSrc`，效果等同于
    人工在浏览器里复制直链，全程无需登录。

    返回 (成功, 直链或 None, 错误信息或 None)。
    """
    try:
        import websocket
    except ImportError:
        return False, None, "缺少 websocket-client，请运行：python -m pip install websocket-client"

    browser = find_browser()
    if not browser:
        return False, None, "未找到 Chrome/Edge 浏览器"

    user_data = tempfile.mkdtemp(prefix="douyin_cdp_")
    args = [browser,
            f"--user-data-dir={user_data}",
            "--remote-debugging-port=0",
            "--remote-allow-origins=*",
            "--no-first-run",
            "--no-default-browser-check",
            "--disable-blink-features=AutomationControlled",
            "--window-size=1280,800",
            "about:blank"]
    if headless:
        args.insert(1, "--headless=new")
    proc = subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        # 1) 读 DevToolsActivePort 拿调试端口
        port = None
        port_file = os.path.join(user_data, "DevToolsActivePort")
        for _ in range(30):
            if os.path.exists(port_file):
                try:
                    with open(port_file, "r", encoding="utf-8") as f:
                        lines = f.read().splitlines()
                    if lines and lines[0].strip().isdigit():
                        port = int(lines[0].strip())
                        break
                except Exception:
                    pass
            if proc.poll() is not None:
                break
            time.sleep(1)
        if not port:
            return False, None, "浏览器调试端口未就绪"

        # 2) 找页面 target 的 websocket 地址
        ws_url = None
        for _ in range(10):
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{port}/json", timeout=5) as r:
                    targets = json.loads(r.read().decode("utf-8", "ignore"))
                for t in targets:
                    if t.get("type") == "page":
                        ws_url = t.get("webSocketDebuggerUrl")
                        break
                if ws_url:
                    break
            except Exception:
                pass
            time.sleep(1)
        if not ws_url:
            return False, None, "CDP 页面目标未找到"

        # 3) 打开视频页并等待加载
        ws = websocket.create_connection(ws_url, timeout=10)
        ws.send(json.dumps({"id": 1, "method": "Page.enable"}))
        ws.recv()
        ws.send(json.dumps({"id": 2, "method": "Page.navigate",
                            "params": {"url": video_page_url}}))
        deadline = time.time() + timeout
        loaded = False
        while time.time() < deadline and not loaded:
            try:
                ws.settimeout(3)
                msg = json.loads(ws.recv())
                if msg.get("method") == "Page.loadEventFired":
                    loaded = True
            except Exception:
                break

        # 4) 轮询提取 <video> 播放地址（抖音先给预览片段，播放后才切到
        #    douyinvod 真实直链；这里主动触发播放并等待真实直链出现）
        js = """(() => {
          const v = document.querySelector('video');
          if (!v) return JSON.stringify({src: ''});
          const s = v.currentSrc || v.src || '';
          if (!s.includes('douyinvod')) {
            try { v.muted = true; v.play().catch(function(){}); } catch (e) {}
          }
          return JSON.stringify({src: s});
        })()"""
        src = None
        while time.time() < deadline:
            try:
                ws.send(json.dumps({"id": 3, "method": "Runtime.evaluate",
                                    "params": {"expression": js, "returnByValue": True}}))
                while True:
                    ws.settimeout(5)
                    msg = json.loads(ws.recv())
                    if msg.get("id") == 3:
                        val = ((msg.get("result") or {}).get("result") or {}).get("value")
                        if val:
                            try:
                                info = json.loads(val)
                                cur = info.get("src") or ""
                            except Exception:
                                cur = str(val)
                            if cur and "douyinvod" in cur:
                                src = cur
                        break
            except Exception:
                break
            if src:
                break
            time.sleep(1)
        ws.close()
        if src:
            return True, src, None
        return False, None, "页面未出现真实播放地址（可能被验证码拦截）"
    finally:
        try:
            proc.terminate()
        except Exception:
            pass


def main():
    ap = argparse.ArgumentParser(description="抖音视频下载工具")
    ap.add_argument("input", nargs="?", help="抖音视频链接 / 分享短链 / 分享口令文本")
    ap.add_argument("--cookies", help="Netscape 格式 cookies.txt（浏览器插件导出）")
    ap.add_argument("--direct", help="直接下载已提取的签名直链（跳过解析）")
    ap.add_argument("--output", default=None, help="输出目录（默认：脚本旁 douyin_downloads）")
    ap.add_argument("--info", action="store_true", help="只打印视频信息，不下载")
    ap.add_argument("--no-browser-cookies", action="store_true", help="不尝试浏览器 cookies")
    args = ap.parse_args()

    output_dir = args.output or default_output_dir()
    os.makedirs(output_dir, exist_ok=True)

    if args.direct:
        ok, dest = download_direct(args.direct, None, output_dir, args.input or "")
        if ok and verify_mp4(dest):
            print(f"[ok] 已下载：{dest}（{os.path.getsize(dest)} 字节）")
        else:
            print(f"[fail] 下载失败或文件无效：{dest}")
        return

    if not args.input:
        ap.print_help()
        return

    url, video_id, full = resolve_share_url(args.input)
    print(f"[link] {url}")
    if video_id:
        print(f"[id]   {video_id}")

    ytdlp = find_ytdlp()
    if not ytdlp:
        print("[warn] 未找到 yt-dlp（`python -m pip install -U yt-dlp` 安装）。"
              "--direct 模式仍可用；普通模式需要 yt-dlp。")
        return

    browser_candidates = [] if args.no_browser_cookies else ["edge", "chrome", "firefox"]

    if args.info:
        print_info(ytdlp, url, args.cookies, browser_candidates)
        return

    ok, dest, err = ytdlp_download(ytdlp, url, args.cookies, browser_candidates, output_dir)
    if ok and dest and os.path.exists(dest):
        if verify_mp4(dest):
            print(f"[ok] 已下载：{dest}（{os.path.getsize(dest)} 字节）")
        else:
            print(f"[warn] 文件存在但头校验失败：{dest}")
        return

    print("[fail] 自动解析未能完成。")
    print("原因摘要：")
    print(err[-1200:])
    print()
    print("抖音要求新鲜 Cookie（不一定要登录）。任选其一：")
    print("  1) 浏览器安装扩展「Get cookies.txt LOCALLY」，打开一条抖音视频页后导出 cookies.txt，")
    print("     再运行：python douyin_downloader.py \"<链接>\" --cookies cookies.txt")
    print("  2) 让助手在真实浏览器里打开视频页提取签名直链，然后运行：")
    print("     python douyin_downloader.py \"<链接>\" --direct \"<签名直链>\"")
    print(f"输出目录：{output_dir}")


if __name__ == "__main__":
    main()
