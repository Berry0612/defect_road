"""Windows UI for visualizing image-folder tracking results side by side."""

import threading
from pathlib import Path
from typing import Optional
from tkinter import BOTH, DISABLED, LEFT, NORMAL, RIGHT, X, Y, filedialog, messagebox, ttk
import tkinter as tk

from PIL import Image, ImageOps, ImageTk

from track import IMG_EXTS, natural_key, run as run_tracking


APP_TITLE = "Track UI"
PREVIEW_SIZE = (420, 320)


class TrackUI:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title(APP_TITLE)
        self.root.geometry("1200x800")
        self.root.minsize(1000, 700)

        self.image_refs = []
        self.worker_thread: Optional[threading.Thread] = None

        self.input_dir_var = tk.StringVar()
        self.output_dir_var = tk.StringVar(value=str(Path.cwd() / "output_ui"))
        self.model_path_var = tk.StringVar(value=str(Path.cwd() / "best.pt"))
        self.status_var = tk.StringVar(value="選擇圖像資料夾後開始追蹤")

        self._build_ui()

    def _build_ui(self) -> None:
        self.root.configure(bg="#111318")

        outer = ttk.Frame(self.root, padding=16)
        outer.pack(fill=BOTH, expand=True)

        title = ttk.Label(outer, text="影像追蹤預覽", font=("Segoe UI", 18, "bold"))
        title.pack(anchor="w")

        subtitle = ttk.Label(
            outer,
            text="左邊原圖，右邊處理後的結果。先選資料夾，再按開始。",
        )
        subtitle.pack(anchor="w", pady=(4, 14))

        form = ttk.Frame(outer)
        form.pack(fill=X)

        self._add_path_row(form, "輸入資料夾", self.input_dir_var, self.browse_input_dir, 0)
        self._add_path_row(form, "輸出資料夾", self.output_dir_var, self.browse_output_dir, 1)
        # 模型權重輸入欄位
        self._add_model_row(form, "模型權重", self.model_path_var, self.browse_model_file, 2)

        actions = ttk.Frame(outer)
        actions.pack(fill=X, pady=(10, 8))

        self.run_button = ttk.Button(actions, text="開始追蹤並預覽", command=self.start_tracking)
        self.run_button.pack(side=LEFT)

        self.clear_button = ttk.Button(actions, text="清空預覽", command=self.clear_preview)
        self.clear_button.pack(side=LEFT, padx=(8, 0))

        status = ttk.Label(actions, textvariable=self.status_var)
        status.pack(side=RIGHT)

        preview_container = ttk.Frame(outer)
        preview_container.pack(fill=BOTH, expand=True, pady=(8, 0))

        self.canvas = tk.Canvas(preview_container, highlightthickness=0, bg="#111318")
        self.scrollbar = ttk.Scrollbar(preview_container, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = ttk.Frame(self.canvas)

        self.scrollable_frame.bind(
            "<Configure>",
            lambda _event: self.canvas.configure(scrollregion=self.canvas.bbox("all")),
        )

        self.canvas_window = self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.pack(side=LEFT, fill=BOTH, expand=True)
        self.scrollbar.pack(side=RIGHT, fill=Y)

        self.canvas.bind("<Configure>", self._resize_canvas_window)
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)

        self._style_widgets()

    def _style_widgets(self) -> None:
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TFrame", background="#111318")
        style.configure("TLabel", background="#111318", foreground="#e8ecf1", font=("Segoe UI", 10))
        style.configure("TButton", font=("Segoe UI", 10, "bold"), padding=(12, 8))
        style.configure("TEntry", fieldbackground="#1b1f26", foreground="#e8ecf1")

    def _add_path_row(self, parent: ttk.Frame, label_text: str, variable: tk.StringVar, browse_command, row: int) -> None:
        label = ttk.Label(parent, text=label_text, width=12)
        label.grid(row=row, column=0, sticky="w", pady=4)

        entry = ttk.Entry(parent, textvariable=variable)
        entry.grid(row=row, column=1, sticky="ew", padx=(0, 8), pady=4)

        button = ttk.Button(parent, text="瀏覽", command=browse_command)
        button.grid(row=row, column=2, sticky="e", pady=4)

        parent.columnconfigure(1, weight=1)

    def _add_model_row(self, parent: ttk.Frame, label_text: str, variable: tk.StringVar, browse_command, row: int) -> None:
        label = ttk.Label(parent, text=label_text, width=12)
        label.grid(row=row, column=0, sticky="w", pady=4)

        entry = ttk.Entry(parent, textvariable=variable)
        entry.grid(row=row, column=1, sticky="ew", padx=(0, 8), pady=4)

        button = ttk.Button(parent, text="瀏覽", command=browse_command)
        button.grid(row=row, column=2, sticky="e", pady=4)

        parent.columnconfigure(1, weight=1)

    def browse_input_dir(self) -> None:
        selected = filedialog.askdirectory(title="選擇輸入圖像資料夾")
        if selected:
            self.input_dir_var.set(selected)

    def browse_output_dir(self) -> None:
        selected = filedialog.askdirectory(title="選擇輸出資料夾")
        if selected:
            self.output_dir_var.set(selected)

    def browse_model_file(self) -> None:
        selected = filedialog.askopenfilename(title="選擇模型權重", filetypes=[("PyTorch", "*.pt"), ("All files", "*.*")])
        if selected:
            self.model_path_var.set(selected)

    def start_tracking(self) -> None:
        if self.worker_thread and self.worker_thread.is_alive():
            messagebox.showinfo("處理中", "目前已有追蹤任務執行中。")
            return

        input_dir = Path(self.input_dir_var.get().strip())
        output_dir = Path(self.output_dir_var.get().strip())

        if not input_dir.exists() or not input_dir.is_dir():
            messagebox.showerror("輸入資料夾錯誤", "請先選擇有效的圖像資料夾。")
            return

        frames = sorted([p for p in input_dir.iterdir() if p.suffix.lower() in IMG_EXTS], key=natural_key)
        if not frames:
            messagebox.showerror("沒有圖像", "資料夾內找不到支援的圖像檔。")
            return

        self.run_button.configure(state=DISABLED)
        self.clear_button.configure(state=DISABLED)
        self.status_var.set("正在追蹤與產生預覽...")
        self.clear_preview()

        model_path = self.model_path_var.get().strip() or None

        self.worker_thread = threading.Thread(
            target=self._worker,
            args=(input_dir, output_dir, model_path),
            daemon=True,
        )
        self.worker_thread.start()

    def _worker(self, input_dir: Path, output_dir: Path, model_path: str | None) -> None:
        try:
            run_tracking(input_dir, output_dir, model_path)
            self.root.after(0, lambda: self._show_results(input_dir, output_dir))
        except Exception as exc:
            self.root.after(0, lambda: self._show_error(exc))

    def _show_error(self, exc: Exception) -> None:
        self.run_button.configure(state=NORMAL)
        self.clear_button.configure(state=NORMAL)
        self.status_var.set("執行失敗")
        messagebox.showerror("追蹤失敗", str(exc))

    def _show_results(self, input_dir: Path, output_dir: Path) -> None:
        self.run_button.configure(state=NORMAL)
        self.clear_button.configure(state=NORMAL)
        self.status_var.set("完成。可向下捲動檢視左右對照結果。")
        self.render_pairs(input_dir, output_dir)

    def clear_preview(self) -> None:
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
        self.image_refs.clear()

    def render_pairs(self, input_dir: Path, output_dir: Path) -> None:
        self.clear_preview()

        processed_dir = output_dir / "processed_frames"
        input_frames = sorted(
            [p for p in input_dir.iterdir() if p.suffix.lower() in IMG_EXTS],
            key=natural_key,
        )

        if not processed_dir.exists():
            self.status_var.set("找不到處理後影像資料夾")
            return

        # 只顯示前三組以便快速檢視
        for index, original_path in enumerate(input_frames[:3], start=1):
            processed_path = processed_dir / original_path.name

            row = ttk.Frame(self.scrollable_frame, padding=(0, 0, 0, 18))
            row.pack(fill=X, expand=True)

            header = ttk.Label(row, text=f"{index}. {original_path.name}", font=("Segoe UI", 11, "bold"))
            header.pack(anchor="w", pady=(0, 8))

            pair = ttk.Frame(row)
            pair.pack(fill=X, expand=True)
            pair.columnconfigure(0, weight=1)
            pair.columnconfigure(1, weight=1)

            self._add_image_panel(pair, 0, "原圖", original_path)
            self._add_image_panel(pair, 1, "處理後", processed_path)

        if not input_frames:
            empty = ttk.Label(self.scrollable_frame, text="沒有可顯示的圖像。")
            empty.pack(anchor="w")

    def _add_image_panel(self, parent: ttk.Frame, column: int, title: str, image_path: Path) -> None:
        panel = ttk.Frame(parent)
        panel.grid(row=0, column=column, sticky="nsew", padx=6)
        panel.columnconfigure(0, weight=1)

        label = ttk.Label(panel, text=title, font=("Segoe UI", 10, "bold"))
        label.pack(anchor="w", pady=(0, 6))

        image = self._load_preview_image(image_path)
        image_label = ttk.Label(panel, image=image, anchor="center")
        image_label.image = image
        image_label.pack(fill=BOTH, expand=True)
        self.image_refs.append(image)

        path_label = ttk.Label(panel, text=str(image_path), wraplength=PREVIEW_SIZE[0] + 40)
        path_label.pack(anchor="w", pady=(6, 0))

    def _load_preview_image(self, image_path: Path) -> ImageTk.PhotoImage:
        if not image_path.exists():
            placeholder = Image.new("RGB", PREVIEW_SIZE, color="#262b33")
            return ImageTk.PhotoImage(placeholder)

        image = Image.open(image_path).convert("RGB")
        preview = ImageOps.contain(image, PREVIEW_SIZE)
        canvas = Image.new("RGB", PREVIEW_SIZE, color="#0f1116")
        offset = ((PREVIEW_SIZE[0] - preview.width) // 2, (PREVIEW_SIZE[1] - preview.height) // 2)
        canvas.paste(preview, offset)
        return ImageTk.PhotoImage(canvas)

    def _resize_canvas_window(self, event) -> None:
        self.canvas.itemconfigure(self.canvas_window, width=event.width)

    def _on_mousewheel(self, event) -> None:
        if self.canvas.winfo_containing(event.x_root, event.y_root) is self.canvas:
            self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")


def main() -> None:
    root = tk.Tk()
    TrackUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()