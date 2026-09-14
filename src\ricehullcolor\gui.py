"""Small Tk desktop interface for users who prefer not to use a terminal."""

from __future__ import annotations

import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from .aggregate import aggregate_project
from .pipeline import analyze_image
from .project import candidate_images, init_project


class RiceHullColorApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("RiceHullColor 0.1.0")
        self.geometry("760x520")
        self.configure(bg="white")
        self.project = tk.StringVar()
        self.image = tk.StringVar()
        self.config = tk.StringVar()
        self.expected = tk.StringVar()
        self._build()

    def _row(self, parent, label, variable, chooser, row):
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", padx=8, pady=7)
        ttk.Entry(parent, textvariable=variable).grid(row=row, column=1, sticky="ew", padx=8, pady=7)
        ttk.Button(parent, text="浏览…", command=chooser).grid(row=row, column=2, padx=8, pady=7)

    def _build(self) -> None:
        frame = ttk.Frame(self, padding=12)
        frame.pack(fill="both", expand=True)
        frame.columnconfigure(1, weight=1)
        ttk.Label(frame, text="水稻颖壳颜色可复现分析", font=("Microsoft YaHei", 15, "bold")).grid(row=0, column=0, columnspan=3, pady=(0, 12))
        self._row(frame, "项目文件夹", self.project, self._choose_project, 1)
        self._row(frame, "单张图像", self.image, self._choose_image, 2)
        self._row(frame, "配置文件", self.config, self._choose_config, 3)
        ttk.Label(frame, text="预期粒数（可留空）").grid(row=4, column=0, sticky="w", padx=8, pady=7)
        ttk.Entry(frame, textvariable=self.expected, width=10).grid(row=4, column=1, sticky="w", padx=8, pady=7)
        buttons = ttk.Frame(frame)
        buttons.grid(row=5, column=0, columnspan=3, sticky="w", padx=8, pady=8)
        ttk.Button(buttons, text="建立项目", command=lambda: self._run(self._init)).pack(side="left", padx=4)
        ttk.Button(buttons, text="分析单图", command=lambda: self._run(self._single)).pack(side="left", padx=4)
        ttk.Button(buttons, text="批量分析", command=lambda: self._run(self._batch)).pack(side="left", padx=4)
        ttk.Button(buttons, text="汇总Excel", command=lambda: self._run(self._aggregate)).pack(side="left", padx=4)
        self.log = tk.Text(frame, height=17, wrap="word", bg="#FAFAFA")
        self.log.grid(row=6, column=0, columnspan=3, sticky="nsew", padx=8, pady=8)
        frame.rowconfigure(6, weight=1)
        self._write("提示：正式分析请使用 16 位 sRGB ROI.tif，并逐张检查 04_QC预览图。\n")

    def _choose_project(self):
        value = filedialog.askdirectory()
        if value:
            self.project.set(value)

    def _choose_image(self):
        value = filedialog.askopenfilename(filetypes=[("Images", "*.tif *.tiff *.png *.jpg *.jpeg"), ("All", "*.*")])
        if value:
            self.image.set(value)

    def _choose_config(self):
        value = filedialog.askopenfilename(filetypes=[("YAML", "*.yml *.yaml"), ("All", "*.*")])
        if value:
            self.config.set(value)

    def _write(self, text: str):
        self.log.after(0, lambda: (self.log.insert("end", text), self.log.see("end")))

    def _run(self, function):
        def worker():
            try:
                function()
            except Exception as exc:
                self._write(f"错误：{exc}\n")
                self.after(0, lambda: messagebox.showerror("RiceHullColor", str(exc)))
        threading.Thread(target=worker, daemon=True).start()

    def _require_project(self) -> Path:
        if not self.project.get():
            raise ValueError("请先选择项目文件夹")
        return Path(self.project.get())

    def _expected_count(self):
        return int(self.expected.get()) if self.expected.get().strip() else None

    def _init(self):
        root = self._require_project()
        init_project(root)
        self._write(f"已建立项目：{root}\n")

    def _single(self):
        root = self._require_project()
        if not self.image.get():
            raise ValueError("请选择一张 CAL/ROI 图像")
        result = analyze_image(self.image.get(), root, self.config.get() or None, self._expected_count())
        self._write(f"完成：{Path(self.image.get()).name}，检测 {result['detected_count']} 粒；警告：{result['warnings']}\n")

    def _batch(self):
        root = self._require_project()
        images = candidate_images(root)
        if not images:
            raise FileNotFoundError("03_ROI分析图 和 02_CAL颜色校正图 中未找到图像")
        for index, image in enumerate(images, start=1):
            result = analyze_image(image, root, self.config.get() or None, self._expected_count())
            self._write(f"[{index}/{len(images)}] {image.name}: {result['detected_count']} 粒\n")
        aggregate_project(root)
        self._write("批量分析和 Excel 汇总已完成。\n")

    def _aggregate(self):
        root = self._require_project()
        result = aggregate_project(root)
        self._write(f"Excel：{result['xlsx']}\n")


def main() -> None:
    RiceHullColorApp().mainloop()


if __name__ == "__main__":
    main()

