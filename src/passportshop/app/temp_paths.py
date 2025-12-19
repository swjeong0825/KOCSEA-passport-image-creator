from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class TempPaths:
    """
    Temp file paths used during GUI preview, before the user saves the final output.
    """
    base_dir: Path
    preview_image: Path

    @staticmethod
    def default(app_name: str = "passportshop") -> "TempPaths":
        base = Path(tempfile.gettempdir()) / app_name
        base.mkdir(parents=True, exist_ok=True)
        preview = base / "preview.jpg"
        return TempPaths(base_dir=base, preview_image=preview)

    def cleanup(self) -> None:
        """
        Best-effort cleanup. Safe to call multiple times.
        """
        try:
            if self.preview_image.exists():
                self.preview_image.unlink()
        except Exception:
            pass
