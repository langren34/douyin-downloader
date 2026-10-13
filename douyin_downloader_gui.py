#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
douyin_downloader_gui.py — 抖音视频下载工具（图形界面版）

双击运行即可使用；也可命令行：python douyin_downloader_gui.py

功能：
  - 粘贴抖音链接 / 分享短链 / 分享口令 → 自动提取并下载
  - 可选 cookies.txt（浏览器扩展「Get cookies.txt LOCALLY」导出）
  - 自动识别签名直链（douyinvod 链接）并直接下载
  - 下载过程日志 + 完成提示 + 一键打开输出文件夹
"""

import os
import queue
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

# 复用同目录 douyin_downloader.py 的核心逻辑
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import douyin_downloader as dd  # noqa: E402

BG = "#17181c"
CARD = "#22242a"
INPUT = "#2b2e35"
FG = "#e8eaed"
MUTED = "#9aa3ad"
ACCENT = "#34d399"
ACCENT_DARK = "#0e8a63"
BLUE = "#60a5fa"
BORDER = "#383b42"


def sanitize_display(name, limit=80):
    return (name[:limit] + "…") if len(name) > limit else name


class DouyinGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("抖音视频下载工具")
        self.root.geometry("720x600")
        self.root.minsize(640, 520)
        self.root.configure(bg=BG)
        self.q = queue.Queue()
        self.working = False

        self._build_style()
        self._build_ui()
        self.root.after(100, self._poll_queue)

    def _build_style(self):
        style = ttk.Style(self.root)
        style.theme_use("clam")
        style.configure("TButton", font=("Microsoft YaHei UI", 10), padding=(14, 7))
        style.configure("Accent.TButton", background=ACCENT, foreground="#0b0c0e", font=("Microsoft YaHei UI", 10, "bold"))
        style.map("Accent.TButton", background=[("active", "#2ee0a1"), ("disabled", "#3a4a42")])
        style.configure("TEntry", fieldbackground=INPUT, foreground=FG, insertcolor=FG, bordercolor=BORDER, padding=6)
        style.configure("TLabel", background=BG, foreground=FG)

    @staticmethod
    def _resource_path(name):
        base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
        return os.path.join(base, name)

    def _load_logo(self, size=40):
        try:
            from PIL import Image, ImageTk
            img = Image.open(self._resource_path("zuonan_logo.png")).convert("RGBA")
            img = img.resize((size, size), Image.LANCZOS)
            return ImageTk.PhotoImage(img)
        except Exception:
            return None

    def _build_ui(self):
        # 标题行：logo + 标题 + 出品信息
        self.logo_img = self._load_logo(40)
        head = tk.Frame(self.root, bg=BG)
        head.pack(fill="x", padx=18, pady=(16, 2))
        if self.logo_img:
            tk.Label(head, image=self.logo_img, bg=BG).pack(side="left")
            self.root.iconphoto(True, self.logo_img)
        tcol = tk.Frame(head, bg=BG)
        tcol.pack(side="left", padx=(10, 0))
        title = tk.Label(tcol, text="抖音视频下载工具", font=("Microsoft YaHei UI", 15, "bold"),
                         bg=BG, fg=FG, anchor="w")
        title.pack(anchor="w")
        sub = tk.Label(tcol, text="佐喃社区出品（测试版）", font=("Microsoft YaHei UI", 8),
                       bg=BG, fg=BLUE, anchor="w")
        sub.pack(anchor="w")

        tip = tk.Label(self.root, text="粘贴视频链接、分享短链或整段口令，自动提取并下载",
                       font=("Microsoft YaHei UI", 9), bg=BG, fg=MUTED, anchor="w")
        tip.pack(fill="x", padx=18, pady=(0, 10))

        # 输入卡片
        card = tk.Frame(self.root, bg=CARD, bd=0, highlightthickness=1, highlightbackground=BORDER)
        card.pack(fill="x", padx=18, pady=6)

        tk.Label(card, text="抖音链接 / 分享口令", font=("Microsoft YaHei UI", 9, "bold"),
                 bg=CARD, fg=FG, anchor="w").pack(fill="x", padx=12, pady=(10, 4))
        self.url_text = tk.Text(card, height=4, wrap="word", font=("Consolas", 10),
                                bg=INPUT, fg=FG, insertbackground=FG,
                                highlightthickness=1, highlightbackground=BORDER, relief="flat")
        self.url_text.pack(fill="x", padx=12, pady=(0, 6))

        # cookies / 输出目录
        opt = tk.Frame(self.root, bg=BG)
        opt.pack(fill="x", padx=18, pady=4)

        left = tk.Frame(opt, bg=BG)
        left.pack(side="left", fill="x", expand=True, padx=(0, 8))
        right = tk.Frame(opt, bg=BG)
        right.pack(side="left", fill="x", expand=True)

        tk.Label(left, text="cookies.txt（可选）", font=("Microsoft YaHei UI", 9), bg=BG, fg=MUTED, anchor="w").pack(fill="x")
        lrow = tk.Frame(left, bg=BG)
        lrow.pack(fill="x")
        self.cookies_var = tk.StringVar(value="")
        tk.Entry(lrow, textvariable=self.cookies_var, font=("Microsoft YaHei UI", 9),
                 bg=INPUT, fg=FG, insertbackground=FG, relief="flat", highlightthickness=1, highlightbackground=BORDER).pack(
                 side="left", fill="x", expand=True, ipady=4)
        tk.Button(lrow, text="…", command=self._pick_cookies, font=("Microsoft YaHei UI", 10),
                  bg=CARD, fg=FG, relief="flat", activebackground=BORDER, activeforeground=FG, width=2,
                  cursor="hand2").pack(side="left", padx=(6, 0))

        tk.Label(right, text="保存到", font=("Microsoft YaHei UI", 9), bg=BG, fg=MUTED, anchor="w").pack(fill="x")
        rrow = tk.Frame(right, bg=BG)
        rrow.pack(fill="x")
        self.out_var = tk.StringVar(value=dd.default_output_dir())
        tk.Entry(rrow, textvariable=self.out_var, font=("Microsoft YaHei UI", 9),
                 bg=INPUT, fg=FG, insertbackground=FG, relief="flat", highlightthickness=1, highlightbackground=BORDER).pack(
                 side="left", fill="x", expand=True, ipady=4)
        tk.Button(rrow, text="…", command=self._pick_outdir, font=("Microsoft YaHei UI", 10),
                  bg=CARD, fg=FG, relief="flat", activebackground=BORDER, activeforeground=FG, width=2,
                  cursor="hand2").pack(side="left", padx=(6, 0))

        # 直链模式勾选
        self.direct_var = tk.BooleanVar(value=False)
        tk.Checkbutton(self.root, text="我粘贴的是签名直链（douyinvod），直接下载",
                       variable=self.direct_var, bg=BG, fg=MUTED, activebackground=BG,
                       selectcolor=CARD, font=("Microsoft YaHei UI", 9), anchor="w").pack(fill="x", padx=18, pady=(2, 2))

        # 按钮行
        btns = tk.Frame(self.root, bg=BG)
        btns.pack(fill="x", padx=18, pady=8)
        self.dl_btn = tk.Button(btns, text="⬇  一键下载", command=self._start_download,
                                font=("Microsoft YaHei UI", 11, "bold"), bg=ACCENT, fg="#0b0c0e",
                                activebackground=ACCENT_DARK, activeforeground="#fff", relief="flat",
                                padx=22, pady=8, cursor="hand2")
        self.dl_btn.pack(side="left")
        self.open_btn = tk.Button(btns, text="打开输出目录", command=self._open_outdir,
                                  font=("Microsoft YaHei UI", 10), bg=CARD, fg=FG, relief="flat",
                                  activebackground=BORDER, activeforeground=FG, padx=16, pady=8, cursor="hand2")
        self.open_btn.pack(side="right")

        # 日志
        log_card = tk.Frame(self.root, bg=CARD, highlightthickness=1, highlightbackground=BORDER)
        log_card.pack(fill="both", expand=True, padx=18, pady=(4, 6))
        tk.Label(log_card, text="运行日志", font=("Microsoft YaHei UI", 9, "bold"),
                 bg=CARD, fg=FG, anchor="w").pack(fill="x", padx=12, pady=(8, 2))
        self.log = tk.Text(log_card, height=10, wrap="word", state="disabled",
                           font=("Consolas", 9), bg=INPUT, fg="#c8d3dc", relief="flat",
                           highlightthickness=0, insertbackground=FG)
        self.log.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        # 状态栏
        self.status = tk.Label(self.root, text="就绪", font=("Microsoft YaHei UI", 9),
                               bg=BG, fg=ACCENT, anchor="w")
        self.status.pack(fill="x", padx=18, pady=(0, 10))

    # ---------- helpers ----------
    def _pick_cookies(self):
        f = filedialog.askopenfilename(title="选择 cookies.txt", filetypes=[("Cookie 文件", "*.txt"), ("所有文件", "*.*")])
        if f:
            self.cookies_var.set(f)

    def _pick_outdir(self):
        d = filedialog.askdirectory(title="选择保存目录")
        if d:
            self.out_var.set(d)

    def _open_outdir(self):
        out = self.out_var.get().strip() or dd.default_output_dir()
        os.makedirs(out, exist_ok=True)
        os.startfile(out)

    def _log(self, msg, color="#c8d3dc"):
        self.q.put(("log", msg, color))

    def _set_status(self, msg, color="#34d399"):
        self.q.put(("status", msg, color))

    def _set_working(self, flag):
        self.q.put(("working", flag, None))

    def _poll_queue(self):
        try:
            while True:
                kind, msg, color = self.q.get_nowait()
                if kind == "log":
                    self.log.configure(state="normal")
                    self.log.insert("end", msg + "\n", ("c",))
                    self.log.tag_config("c", foreground=color)
                    self.log.see("end")
                    self.log.configure(state="disabled")
                elif kind == "status":
                    self.status.configure(text=msg, fg=color)
                elif kind == "working":
                    self.working = msg
                    state = "disabled" if msg else "normal"
                    self.dl_btn.configure(state=state)
                    if msg:
                        self._log("开始处理…", BLUE)
                    else:
                        self._log("完成。", ACCENT)
        except queue.Empty:
            pass
        self.root.after(100, self._poll_queue)

    # ---------- actions ----------
    def _gather_input(self):
        raw = self.url_text.get("1.0", "end").strip()
        if not raw:
            messagebox.showwarning("提示", "请先粘贴抖音链接或分享口令")
            return None
        return raw

    def _start_download(self):
        if self.working:
            return
        raw = self._gather_input()
        if raw is None:
            return
        cookies = self.cookies_var.get().strip() or None
        out = self.out_var.get().strip() or dd.default_output_dir()
        direct = self.direct_var.get()
        self._set_working(True)
        threading.Thread(target=self._download_worker, args=(raw, cookies, out, direct), daemon=True).start()

    def _download_worker(self, raw, cookies, out, direct):
        """一键下载：直链→直接下；有 cookies→yt-dlp 先试；否则→浏览器自动提取直链下载"""
        try:
            if direct or "douyinvod" in raw:
                if "douyinvod" not in raw:
                    self._log("[hint] 直链模式需要粘贴 douyinvod 开头的签名链接；", "#fbbf24")
                    self._log("       分享口令/普通链接请取消勾选后重试。", "#fbbf24")
                    self._set_status("需粘贴 douyinvod 直链", "#fbbf24")
                    return
                url, vid, full = dd.resolve_share_url(raw)
                self._log(f"[direct] 签名直链模式")
                ok, dest = dd.download_direct(raw, vid, out, "douyin_video")
                if ok and dd.verify_mp4(dest):
                    size = os.path.getsize(dest)
                    self._log(f"[ok] 下载完成：{dest}（{size / 1024 / 1024:.1f} MB）", ACCENT)
                    self._set_status(f"完成：{os.path.basename(dest)}", ACCENT)
                else:
                    self._log("[fail] 下载失败或文件无效（签名链接可能已过期，请重新提取）", "#f87171")
                    self._set_status("失败", "#f87171")
                return

            url, vid, full = dd.resolve_share_url(raw)
            self._log(f"[link] {url}")
            if vid:
                self._log(f"[id]   {vid}")

            # 优先 yt-dlp（快；cookies 指定时）
            if cookies:
                ytdlp = dd.find_ytdlp()
                if ytdlp:
                    self._log(f"[策略] 使用 cookies.txt")
                    ok, dest, err = dd.ytdlp_download(ytdlp, url, cookies, [], out)
                    if ok and dest and os.path.exists(dest) and dd.verify_mp4(dest):
                        size = os.path.getsize(dest)
                        self._log(f"[ok] 下载完成：{dest}（{size / 1024 / 1024:.1f} MB）", ACCENT)
                        self._set_status(f"完成：{os.path.basename(dest)}", ACCENT)
                        return
                    self._log("[warn] cookies 方式失败，改走自动提取…", "#fbbf24")

            # 自动提取（CDP 驱动本机浏览器）
            self._log("[auto] 启动本机浏览器自动提取直链（约 1 分钟内）…", "#fbbf24")
            ok, src, err = dd.extract_direct_with_browser(full, headless=True, timeout=60)
            if not ok:
                self._log(f"[fail] 自动提取失败：{err}", "#f87171")
                self._log("  兜底办法：浏览器装「Get cookies.txt LOCALLY」导出 cookies.txt 填入上方，", MUTED)
                self._log("  或取消勾选后在浏览器右键视频复制 douyinvod 链接粘贴（勾选直链）。", MUTED)
                self._set_status("需要 Cookie 或直链", "#fbbf24")
                return
            self._log("[auto] 直链已提取，开始下载…", ACCENT)
            ok2, dest = dd.download_direct(src, vid, out, "douyin")
            if ok2 and dd.verify_mp4(dest):
                size = os.path.getsize(dest)
                self._log(f"[ok] 下载完成：{dest}（{size / 1024 / 1024:.1f} MB）", ACCENT)
                self._set_status(f"完成：{os.path.basename(dest)}", ACCENT)
            else:
                self._log("[fail] 下载失败或文件无效（直链可能已过期）", "#f87171")
                self._set_status("失败", "#f87171")
        except Exception as e:
            self._log(f"[error] {e}", "#f87171")
            self._set_status("出错", "#f87171")
        finally:
            self._set_working(False)


def main():
    root = tk.Tk()
    DouyinGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
