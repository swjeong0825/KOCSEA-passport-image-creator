from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Optional, Tuple

from PIL import Image, ImageTk


class ImageCanvas(ttk.Frame):
    """A resizable canvas that can display a PIL image scaled to fit."""

    def __init__(self, master, *, bg: str = "#f3f3f3"):
        super().__init__(master)
        self._canvas = tk.Canvas(self, highlightthickness=0, bg=bg)
        self._canvas.pack(fill="both", expand=True)

        self._photo: Optional[ImageTk.PhotoImage] = None
        self._pil: Optional[Image.Image] = None

        self._canvas.bind("<Configure>", self._on_resize)

        self._placeholder_id = self._canvas.create_text(
            10, 10, anchor="nw",
            text="No image loaded",
            fill="#555",
            font=("TkDefaultFont", 11),
        )

    def set_image(self, pil: Optional[Image.Image]) -> None:
        self._pil = pil
        self._redraw()

    def clear(self) -> None:
        self.set_image(None)

    def _on_resize(self, _evt) -> None:
        self._redraw()

    def _fit_size(self, img_w: int, img_h: int, box_w: int, box_h: int) -> Tuple[int, int]:
        if img_w <= 0 or img_h <= 0 or box_w <= 2 or box_h <= 2:
            return (1, 1)
        scale = min(box_w / img_w, box_h / img_h)
        new_w = max(1, int(img_w * scale))
        new_h = max(1, int(img_h * scale))
        return new_w, new_h

    def _redraw(self) -> None:
        self._canvas.delete("img")
        if self._pil is None:
            self._canvas.itemconfigure(self._placeholder_id, state="normal")
            return

        self._canvas.itemconfigure(self._placeholder_id, state="hidden")

        w = max(1, self._canvas.winfo_width())
        h = max(1, self._canvas.winfo_height())

        pil = self._pil
        new_w, new_h = self._fit_size(pil.width, pil.height, w, h)
        resized = pil.resize((new_w, new_h), Image.LANCZOS)

        self._photo = ImageTk.PhotoImage(resized)
        x = (w - new_w) // 2
        y = (h - new_h) // 2
        self._canvas.create_image(x, y, anchor="nw", image=self._photo, tags=("img",))
