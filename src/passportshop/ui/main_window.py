from __future__ import annotations

import os
import threading
import traceback
import tkinter as tk
from dataclasses import replace
from tkinter import filedialog, messagebox, ttk

from PIL import Image, ImageOps

from passportshop.app.state import AppState
from passportshop.app.temp_paths import TempPaths
from passportshop.ui.image_canvas import ImageCanvas
from passportshop.validation.validator import format_report_text, validate_passport_photo

# Use the existing non-GUI pipeline (expected to be in your project root as passport_photo.py)
try:
    from passport_photo import process_passport_photo  # type: ignore
except Exception:
    process_passport_photo = None


class PassportShopApp(ttk.Frame):
    """PassportShop GUI (Steps 1–4 implemented; Step 5 export stub)."""

    def __init__(self, master: tk.Tk, state: AppState):
        super().__init__(master)
        self.master = master
        self.state = state

        # Stable temp paths for preview output
        self.temp_paths = TempPaths.default(app_name="passportshop")

        self._build_style()
        self._build_layout()
        self._bind_shortcuts()

        self.set_status("Ready.")
        self._set_buttons_initial_state()

    # ---------- UI construction ----------

    def _build_style(self) -> None:
        style = ttk.Style(self.master)
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
        self.tree.column("rule", width=180, stretch=False)
        self.tree.column("status", width=80, stretch=False)
        self.tree.column("details", width=420, stretch=True)

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
        self.master.bind_all("<Control-o>", lambda e: self.on_upload())
        self.master.bind_all("<Command-o>", lambda e: self.on_upload())

        self.master.bind_all("<Control-r>", lambda e: self.on_process())
        self.master.bind_all("<Command-r>", lambda e: self.on_process())

        self.master.bind_all("<Control-s>", lambda e: self.on_save())
        self.master.bind_all("<Command-s>", lambda e: self.on_save())

    # ---------- Utilities ----------

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
        self.btn_process.state(["disabled"])
        self.btn_validate.state(["disabled"])
        self.btn_save.state(["disabled"])
        self.btn_copy_report.state(["disabled"])

    def _set_processing_ui(self, processing: bool, message: str = "Working…") -> None:
        if processing:
            self.btn_upload.state(["disabled"])
            self.btn_process.state(["disabled"])
            self.btn_validate.state(["disabled"])
            self.btn_save.state(["disabled"])
            self.btn_reset.state(["disabled"])
            self.btn_copy_report.state(["disabled"])
            self.set_busy(True, message)
        else:
            self.btn_upload.state(["!disabled"])
            self.btn_reset.state(["!disabled"])

            if self.state.input_path:
                self.btn_process.state(["!disabled"])
            else:
                self.btn_process.state(["disabled"])

            if self.state.processed_pil is not None:
                self.btn_validate.state(["!disabled"])
                self.btn_save.state(["!disabled"])
            else:
                self.btn_validate.state(["disabled"])
                self.btn_save.state(["disabled"])

            if self.state.validation_report is not None:
                self.btn_copy_report.state(["!disabled"])
            else:
                self.btn_copy_report.state(["disabled"])

            self.set_busy(False)

    def _clear_validation_view(self) -> None:
        for iid in self.tree.get_children():
            self.tree.delete(iid)
        self.btn_copy_report.state(["disabled"])

    def _render_validation_report(self) -> None:
        self._clear_validation_view()
        report = self.state.validation_report
        if report is None:
            return

        for r in report.results:
            status = "✅" if r.passed else "❌"
            self.tree.insert("", "end", values=(r.rule_id, status, r.message))

        self.btn_copy_report.state(["!disabled"])

    def _load_image_rgb(self, path: str) -> Image.Image:
        img = Image.open(path)
        img = ImageOps.exif_transpose(img)
        if img.mode != "RGB":
            img = img.convert("RGB")
        return img

    def _sync_params_from_ui(self) -> None:
        # ProcessingParams is frozen -> replace() to update
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

    # ---------- Step 2: Upload ----------

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

        self.state.input_path = path
        self.state.original_pil = pil

        # New upload invalidates downstream
        self.state.processed_pil = None
        self.state.processed_temp_path = None
        self.state.validation_report = None

        self.original_canvas.set_image(pil)
        self.original_meta.configure(text=f"File: {os.path.basename(path)}   Size: {pil.width}x{pil.height}")

        self.processed_canvas.clear()
        self.processed_meta.configure(text="Not processed yet.")
        self._clear_validation_view()

        self.btn_process.state(["!disabled"])
        self.btn_validate.state(["disabled"])
        self.btn_save.state(["disabled"])

        self.set_status("Loaded photo. Ready to process.")

    # ---------- Step 3: Process (existing pipeline) ----------

    def on_process(self) -> None:
        if not self.state.input_path:
            messagebox.showwarning("No input", "Upload a photo first.")
            return

        if process_passport_photo is None:
            messagebox.showerror(
                "Pipeline not found",
                "Could not import process_passport_photo.\n\n"
                "Make sure passport_photo.py is importable and contains process_passport_photo().",
            )
            return

        self._sync_params_from_ui()
        params = self.state.params

        in_path = self.state.input_path
        out_path = str(self.temp_paths.preview_image)
        self.state.processed_temp_path = out_path

        # UI: busy + disable controls
        self._set_processing_ui(True, message="Processing…")

        def worker() -> None:
            err: Exception | None = None
            tb: str | None = None
            try:
                process_passport_photo(
                    input_path=in_path,
                    output_path=out_path,
                    size=params.size,
                    head_ratio=params.head_ratio,
                    remove_background=params.remove_background,
                )
            except Exception as e:
                err = e
                tb = traceback.format_exc()

            def finish_on_ui_thread() -> None:
                if err is not None:
                    self.state.processed_pil = None
                    self.state.validation_report = None
                    self._set_processing_ui(False)
                    messagebox.showerror("Processing failed", f"{err}\n\n{tb or ''}".strip())
                    self.set_status("Processing failed.")
                    return

                try:
                    processed = self._load_image_rgb(out_path)
                except Exception as e2:
                    self.state.processed_pil = None
                    self.state.validation_report = None
                    self._set_processing_ui(False)
                    messagebox.showerror("Load failed", f"Processed image was created, but could not be loaded.\n\n{e2}")
                    self.set_status("Load processed image failed.")
                    return

                # Update state + UI
                self.state.processed_pil = processed
                self.state.validation_report = None
                self._clear_validation_view()

                self.processed_canvas.set_image(processed)
                self.processed_meta.configure(
                    text=f"Temp: {os.path.basename(out_path)}   Size: {processed.width}x{processed.height}"
                )

                self._set_processing_ui(False)
                self.set_status("Processing complete. Ready to validate or save.")

            self.master.after(0, finish_on_ui_thread)

        threading.Thread(target=worker, daemon=True).start()

    # ---------- Step 4: Validate ----------

    def on_validate(self) -> None:
        if self.state.processed_pil is None:
            messagebox.showwarning("Not ready", "Process a photo first.")
            return

        self._sync_params_from_ui()
        processed = self.state.processed_pil
        params = self.state.params

        self._set_processing_ui(True, message="Validating…")

        def worker() -> None:
            err: Exception | None = None
            tb: str | None = None
            report = None
            try:
                report = validate_passport_photo(processed, params)
            except Exception as e:
                err = e
                tb = traceback.format_exc()

            def finish_on_ui_thread() -> None:
                self._set_processing_ui(False)
                if err is not None:
                    details = f"{err}\n\n{tb or ''}".strip()
                    messagebox.showerror("Validation failed", details)
                    self.set_status("Validation failed.")
                    return

                self.state.validation_report = report
                self._render_validation_report()

                if report and report.passed:
                    self.set_status("Validation complete. All checks passed.")
                else:
                    self.set_status("Validation complete (some checks failed).")

            self.master.after(0, finish_on_ui_thread)

        threading.Thread(target=worker, daemon=True).start()

    def on_copy_report(self) -> None:
        report = self.state.validation_report
        if report is None:
            messagebox.showinfo("No report", "Run Validate first.")
            return

        text = format_report_text(report)
        self.master.clipboard_clear()
        self.master.clipboard_append(text)
        self.set_status("Copied validation report.")

    # ---------- Step 5 stub ----------

    def on_save(self) -> None:
        messagebox.showinfo("Step 4", "Save/Export will be implemented in Step 5.")
        self.set_status("Save clicked (Step 5 will export the image/report).")

    def on_reset(self) -> None:
        self.state.reset()
        try:
            self.temp_paths.cleanup()
        except Exception:
            pass

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


def run() -> None:
    root = tk.Tk()
    root.title("PassportShop")
    root.geometry("1100x700")
    root.minsize(900, 600)

    state = AppState()
    PassportShopApp(root, state)

    root.mainloop()
