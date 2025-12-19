from __future__ import annotations

from dataclasses import dataclass

@dataclass(frozen=True)
class ProcessingParams:
    """
    Parameters that control how the passport photo is generated.

    size:
        Output width/height in pixels (square). Default 600.
    head_ratio:
        Target head height ratio: (chin -> top of head/forehead landmark) / image_height.
        Typical U.S. digital guidance is ~0.50–0.69; default 0.62.
    remove_background:
        If True, attempts to replace background with white via rembg.
    """
    size: int = 600
    head_ratio: float = 0.62
    remove_background: bool = True
