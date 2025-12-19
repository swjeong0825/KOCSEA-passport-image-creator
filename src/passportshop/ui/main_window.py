from __future__ import annotations

import tkinter as tk
from tkinter import ttk, messagebox
from dataclasses import asdict

from passportshop.app.state import AppState
from passportshop.ui.image_canvas import ImageCanvas


class PassportShopApp(ttk.Frame):
    """Step 1: GUI shell + layout (no real upload/process yet)."""

    def __init__(self, master: tk.Tk, state: AppState):
        super().__init__(master)
        self.master = master
        self.state = state

        self._build_style()
        self._build_layout()
        self._bind_shortcuts()

        self.set_status("Ready.")
        self._set_buttons_initial_state()

    def _build_style(self) -> None:
        style = ttk.Style(self.master)
        try:
            style.theme_use("clam" if "clam" in style.theme_names() else style.theme_use())
        except Exception:
            pass

    def _build_layout(self) -> None:
        self.pack(fill="both", expand=True)

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

        main = ttk.PanedWindow(self, orient="horizontal")
        main.pack(side="top", fill="both", expand=True, padx=10, pady=(0, 10))

        left = ttk.Frame(main)
        main.add(left, weight=1)

        lf_orig = ttk.LabelFrame(left, text="Original", padding=8)
        lf_orig.pack(fill="both", expand=True)

        self.original_canvas = ImageCanvas(lf_orig)
        self.original_canvas.pack(fill="both", expand=True)
        self.original_meta = ttk.Label(lf_orig, text="No file loaded.")
        self.original_meta.pack(side="bottom", anchor="w", pady=(6, 0))

        right = ttk.Frame(main)
        main.add(right, weight=1)

        nb = ttk.Notebook(right)
        nb.pack(fill="both", expand=True)

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
        self.btn_copy_report = ttk.Button(btn_row, text="Copy report", command=self.on_copy_report)
        self.btn_copy_report.pack(side="left")

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

    def set_status(self, text: str) -> None:
        self.status_var.set(text)

    def _set_buttons_initial_state(self) -> None:
        self.btn_process.state(["disabled"])
        self.btn_validate.state(["disabled"])
        self.btn_save.state(["disabled"])
        self.btn_copy_report.state(["disabled"])

    def _sync_params_from_ui(self) -> None:
        try:
            self.state.params.size = int(self.var_size.get())
        except Exception:
            pass
        try:
            self.state.params.head_ratio = float(self.var_head_ratio.get())
        except Exception:
            pass
        self.state.params.remove_background = bool(self.var_remove_bg.get())

    def _clear_validation_view(self) -> None:
        for iid in self.tree.get_children():
            self.tree.delete(iid)
        self.btn_copy_report.state(["disabled"])

    # ---- Step 1 stub handlers ----

    def on_upload(self) -> None:
        messagebox.showinfo("Step 1", "Upload will be implemented in Step 2.")
        self.set_status("Upload clicked (Step 2 will load an image).")

    def on_process(self) -> None:
        self._sync_params_from_ui()
        messagebox.showinfo("Step 1", "Process will be implemented in Step 3.")
        self.set_status(f"Process clicked (params: {asdict(self.state.params)}).")

    def on_validate(self) -> None:
        messagebox.showinfo("Step 1", "Validate will be implemented in Step 4.")
        self.set_status("Validate clicked (Step 4 will run rules).")

    def on_save(self) -> None:
        messagebox.showinfo("Step 1", "Save/Export will be implemented in Step 5.")
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
        self.state.params.size = 600
        self.state.params.head_ratio = 0.62
        self.state.params.remove_background = True
        self.var_size.set(self.state.params.size)
        self.var_head_ratio.set(self.state.params.head_ratio)
        self.var_remove_bg.set(self.state.params.remove_background)
        self.set_status("Defaults restored.")

    def on_copy_report(self) -> None:
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
