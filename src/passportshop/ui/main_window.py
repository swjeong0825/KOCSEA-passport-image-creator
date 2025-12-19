from __future__ import annotations

import os
import tkinter as tk
from dataclasses import asdict, replace
from tkinter import filedialog, messagebox, ttk

from PIL import Image, ImageOps

from passportshop.app.state import AppState
from passportshop.ui.image_canvas import ImageCanvas


class PassportShopApp(ttk.Frame):
    """Step 2: Upload photo + preview (Process/Validate/Save still stubbed)."""

    def __init__(self, master: tk.Tk, state: AppState):
        super().__init__(master)
        self.master = master
        self.state = state

        self._build_style()
        self._build_layout()
        self._bind_shortcuts()

        self.set_status("Ready.")
        self._set_buttons_initial_state()

    # ---------- UI construction ----------

    def _build_style(self) -> None:
        style = ttk.Style(self.master)
        # Use OS theme where possible
        try:
            style.theme_use("clam" if "clam" in style.theme_names() else style.theme_use())
        except Exception:
            pass

    def _build_layout(self) -> None:
        self.pack(fill="both", expand=True)

        # Top toolbar
        toolbar = ttk.Frame(self, padding=(10, 8))
        toolbar.pack(side="top", fill="x")

        self.btn_upload = ttk.Button(toolbar, text="Upload", command=self.on_upload)
        self.btn_process = ttk.Button(toolbar, text="Process", command=self.on_process)
        self.btn_validate = ttk.Button(toolbar, text="Validate", command=self.on_validate)
        self.btn_save = ttk.Button(toolbar, text="Save/Export", command=self.on_save)
        self.btn_reset = ttk.Button(toolbar, text="Reset", command=self.on_reset)

        self.btn_upload.pack(side="left")
        ttk.Separator(toolbar, orient="vertical").pack(side="left", fill="y", padx=8)
        self.btn_process.pack(side="left")
        self.btn_validate.pack(side="left", padx=(6, 0))
        self.btn_save.pack(side="left", padx=(6, 0))
        self.btn_reset.pack(side="left", padx=(12, 0))

        self.progress = ttk.Progressbar(toolbar, mode="indeterminate", length=120)
        self.progress.pack(side="right")

        # Main split area
        main = ttk.PanedWindow(self, orient="horizontal")
        main.pack(side="top", fill="both", expand=True, padx=10, pady=(0, 10))

        # Left pane: Original
        left = ttk.Frame(main)
        main.add(left, weight=1)

        lf_orig = ttk.LabelFrame(left, text="Original", padding=8)
        lf_orig.pack(fill="both", expand=True)

        self.original_canvas = ImageCanvas(lf_orig)
        self.original_canvas.pack(fill="both", expand=True)

        self.original_meta = ttk.Label(lf_orig, text="No file loaded.")
        self.original_meta.pack(side="bottom", anchor="w", pady=(6, 0))

        # Right pane: Notebook
        right = ttk.Frame(main)
        main.add(right, weight=1)

        nb = ttk.Notebook(right)
        nb.pack(fill="both", expand=True)

        # Processed tab
        tab_processed = ttk.Frame(nb, padding=8)
        nb.add(tab_processed, text="Processed")

        # Split processed tab into preview + settings
        proc_paned = ttk.PanedWindow(tab_processed, orient="vertical")
        proc_paned.pack(fill="both", expand=True)

        proc_preview = ttk.LabelFrame(proc_paned, text="Processed Preview", padding=8)
        self.processed_canvas = ImageCanvas(proc_preview)
        self.processed_canvas.pack(fill="both", expand=True)
        self.processed_meta = ttk.Label(proc_preview, text="Not processed yet.")
        self.processed_meta.pack(side="bottom", anchor="w", pady=(6, 0))
        proc_paned.add(proc_preview, weight=3)

        settings = ttk.LabelFrame(proc_paned, text="Settings", padding=8)
        proc_paned.add(settings, weight=1)

        # Settings grid
        settings.columnconfigure(1, weight=1)

        ttk.Label(settings, text="Output size (px):").grid(row=0, column=0, sticky="w", pady=3)
        self.var_size = tk.IntVar(value=self.state.params.size)
        self.spin_size = ttk.Spinbox(settings, from_=300, to=1200, textvariable=self.var_size, width=8)
        self.spin_size.grid(row=0, column=1, sticky="w", pady=3)

        ttk.Label(settings, text="Head ratio:").grid(row=1, column=0, sticky="w", pady=3)
        self.var_head_ratio = tk.DoubleVar(value=self.state.params.head_ratio)
        self.entry_head_ratio = ttk.Entry(settings, textvariable=self.var_head_ratio, width=10)
        self.entry_head_ratio.grid(row=1, column=1, sticky="w", pady=3)

        self.var_remove_bg = tk.BooleanVar(value=self.state.params.remove_background)
        self.chk_remove_bg = ttk.Checkbutton(settings, text="White background (rembg)", variable=self.var_remove_bg)
        self.chk_remove_bg.grid(row=2, column=0, columnspan=2, sticky="w", pady=3)

        self.btn_defaults = ttk.Button(settings, text="Restore defaults", command=self.on_restore_defaults)
        self.btn_defaults.grid(row=3, column=0, sticky="w", pady=(8, 0))

        # Validation tab
        tab_val = ttk.Frame(nb, padding=8)
        nb.add(tab_val, text="Validation")

        tab_val.columnconfigure(0, weight=1)
        tab_val.rowconfigure(0, weight=1)

        columns = ("rule", "status", "details")
        self.tree = ttk.Treeview(tab_val, columns=columns, show="headings", height=10)
        self.tree.heading("rule", text="Rule")
        self.tree.heading("status", text="Status")
        self.tree.heading("details", text="Details")
        self.tree.column("rule", width=160, stretch=False)
        self.tree.column("status", width=80, stretch=False)
        self.tree.column("details", width=380, stretch=True)

        self.tree.grid(row=0, column=0, sticky="nsew")

        btn_row = ttk.Frame(tab_val)
        btn_row.grid(row=1, column=0, sticky="ew", pady=(8, 0))
        btn_row.columnconfigure(0, weight=1)

        self.btn_copy_report = ttk.Button(btn_row, text="Copy report", command=self.on_copy_report)
        self.btn_copy_report.pack(side="left")

        # Status bar
        status = ttk.Frame(self, padding=(10, 6))
        status.pack(side="bottom", fill="x")

        self.status_var = tk.StringVar(value="Ready.")
        self.status_label = ttk.Label(status, textvariable=self.status_var)
        self.status_label.pack(side="left")

    def _bind_shortcuts(self) -> None:
        # Mac uses Command; Windows/Linux uses Control.
        # We bind both.
        self.master.bind_all("<Control-o>", lambda e: self.on_upload())
        self.master.bind_all("<Command-o>", lambda e: self.on_upload())

        self.master.bind_all("<Control-r>", lambda e: self.on_process())
        self.master.bind_all("<Command-r>", lambda e: self.on_process())

        self.master.bind_all("<Control-s>", lambda e: self.on_save())
        self.master.bind_all("<Command-s>", lambda e: self.on_save())

    # ---------- UI utilities ----------

    def set_status(self, text: str) -> None:
        self.status_var.set(text)

    def set_busy(self, busy: bool, message: str | None = None) -> None:
        if message:
            self.set_status(message)
        if busy:
            self.progress.start(12)
        else:
            self.progress.stop()

    def _set_buttons_initial_state(self) -> None:
        # Step 2: Process disabled until upload; Validate/Save disabled until processed (Step 3)
        self.btn_process.state(["disabled"])
        self.btn_validate.state(["disabled"])
        self.btn_save.state(["disabled"])
        self.btn_copy_report.state(["disabled"])

    def _sync_params_from_ui(self) -> None:
        # Update state.params from widgets (processing comes in Step 3).
        params = self.state.params

        try:
            params = replace(params, size=int(self.var_size.get()))
        except Exception:
            pass

        try:
            params = replace(params, head_ratio=float(self.var_head_ratio.get()))
        except Exception:
            pass

        params = replace(params, remove_background=bool(self.var_remove_bg.get()))
        self.state.params = params


    def _clear_validation_view(self) -> None:
        for iid in self.tree.get_children():
            self.tree.delete(iid)
        self.btn_copy_report.state(["disabled"])

    def _load_image_rgb(self, path: str) -> Image.Image:
        """Load an image, apply EXIF orientation, return RGB PIL Image (matches passport_photo.py behavior)."""
        img = Image.open(path)
        img = ImageOps.exif_transpose(img)
        if img.mode != "RGB":
            img = img.convert("RGB")
        return img

    # ---------- Event handlers ----------

    def on_upload(self) -> None:
        path = filedialog.askopenfilename(
            title="Select a photo",
            filetypes=[
                ("Image files", "*.jpg *.jpeg *.png *.bmp *.tif *.tiff *.webp"),
                ("All files", "*.*"),
            ],
        )
        if not path:
            return

        try:
            pil = self._load_image_rgb(path)
        except Exception as e:
            messagebox.showerror("Upload failed", f"Could not open image.\n\n{e}")
            self.set_status("Upload failed.")
            return

        # Update state
        self.state.input_path = path
        self.state.original_pil = pil

        # New upload invalidates downstream results
        self.state.processed_pil = None
        self.state.processed_temp_path = None
        self.state.validation_report = None

        # Update UI (Original preview)
        self.original_canvas.set_image(pil)
        self.original_meta.configure(
            text=f"File: {os.path.basename(path)}   Size: {pil.width}x{pil.height}"
        )

        # Clear processed + validation UI
        self.processed_canvas.clear()
        self.processed_meta.configure(text="Not processed yet.")
        self._clear_validation_view()

        # Enable Process only
        self.btn_process.state(["!disabled"])
        self.btn_validate.state(["disabled"])
        self.btn_save.state(["disabled"])

        self.set_status("Loaded photo. Ready to process.")

    def on_process(self) -> None:
        # Step 3 will implement real processing.
        self._sync_params_from_ui()
        messagebox.showinfo("Step 2", "Process will be implemented in Step 3.")
        self.set_status(f"Process clicked (params: {asdict(self.state.params)}).")

    def on_validate(self) -> None:
        # Step 4 will implement validation.
        messagebox.showinfo("Step 2", "Validate will be implemented in Step 4.")
        self.set_status("Validate clicked (Step 4 will run rules).")

    def on_save(self) -> None:
        # Step 5 will implement export.
        messagebox.showinfo("Step 2", "Save/Export will be implemented in Step 5.")
        self.set_status("Save clicked (Step 5 will export the image/report).")

    def on_reset(self) -> None:
        self.state.reset()
        self.original_canvas.clear()
        self.processed_canvas.clear()
        self.original_meta.configure(text="No file loaded.")
        self.processed_meta.configure(text="Not processed yet.")
        self._clear_validation_view()
        self._set_buttons_initial_state()
        self.set_status("Reset complete.")

    def on_restore_defaults(self) -> None:
        self.state.params = replace(
            self.state.params,
            size=600,
            head_ratio=0.62,
            remove_background=True,
        )

        self.var_size.set(self.state.params.size)
        self.var_head_ratio.set(self.state.params.head_ratio)
        self.var_remove_bg.set(self.state.params.remove_background)

        self.set_status("Defaults restored.")

    def on_copy_report(self) -> None:
        # Step 2: no report yet
        self.master.clipboard_clear()
        self.master.clipboard_append("No report yet.")
        self.set_status("Copied placeholder report.")


def run() -> None:
    root = tk.Tk()
    root.title("PassportShop")
    root.geometry("1100x700")
    root.minsize(900, 600)

    state = AppState()
    PassportShopApp(root, state)

    root.mainloop()
