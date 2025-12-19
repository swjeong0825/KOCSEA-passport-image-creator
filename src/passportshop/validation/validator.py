from __future__ import annotations

from typing import Any, List, Optional, Tuple

import numpy as np
from PIL import Image

from passportshop.core.models import ProcessingParams
from passportshop.validation.report import RuleResult, ValidationReport


# Prefer the same landmark detector used by the generation pipeline, if available.
_detect_face_landmarks = None
try:
    from passport_photo import _detect_face_landmarks as _pipeline_detect_face_landmarks  # type: ignore
    _detect_face_landmarks = _pipeline_detect_face_landmarks
except Exception:
    _detect_face_landmarks = None


def _pil_to_np_rgb(img: Image.Image) -> np.ndarray:
    arr = np.asarray(img)
    if arr.ndim == 2:
        arr = np.stack([arr, arr, arr], axis=-1)
    if arr.shape[-1] == 4:
        arr = arr[:, :, :3]
    return arr.astype(np.uint8)


def _near_white_ratio_border(img_rgb: np.ndarray, margin: int, thr: int = 245) -> float:
    h, w, _ = img_rgb.shape
    m = max(1, min(margin, h // 2, w // 2))
    top = img_rgb[:m, :, :]
    bottom = img_rgb[h - m :, :, :]
    left = img_rgb[:, :m, :]
    right = img_rgb[:, w - m :, :]

    border = np.concatenate(
        [top.reshape(-1, 3), bottom.reshape(-1, 3), left.reshape(-1, 3), right.reshape(-1, 3)],
        axis=0,
    )
    mask = (border[:, 0] >= thr) & (border[:, 1] >= thr) & (border[:, 2] >= thr)
    return float(mask.mean()) if border.size else 0.0


def _lighting_metrics(img_rgb: np.ndarray) -> dict[str, Any]:
    gray = (0.2126 * img_rgb[:, :, 0] + 0.7152 * img_rgb[:, :, 1] + 0.0722 * img_rgb[:, :, 2]).astype(np.float32)
    mean = float(gray.mean())
    std = float(gray.std())
    dark_clip = float((gray <= 10).mean())
    bright_clip = float((gray >= 245).mean())
    return {"luma_mean": mean, "luma_std": std, "dark_clip": dark_clip, "bright_clip": bright_clip}


def _lm_xy(p: Any) -> Optional[Tuple[float, float]]:
    """
    Accepts either:
      - LandmarkPx (with .x/.y) from passport_photo.py :contentReference[oaicite:2]{index=2}
      - (x, y) tuple/list
    Returns (x, y) as floats.
    """
    if p is None:
        return None
    if hasattr(p, "x") and hasattr(p, "y"):
        return float(p.x), float(p.y)
    try:
        return float(p[0]), float(p[1])
    except Exception:
        return None


def _get_landmarks(img_rgb_pil: Image.Image) -> Optional[Tuple[Any, Any, Any]]:
    """Return (nose_tip, forehead_top, chin) if possible."""
    if _detect_face_landmarks is None:
        return None
    try:
        return _detect_face_landmarks(img_rgb_pil)  # type: ignore[misc]
    except Exception:
        return None


def validate_passport_photo(processed_rgb: Image.Image, params: ProcessingParams) -> ValidationReport:
    """
    Validate a processed passport photo and return a ValidationReport.

    Rules are best-effort heuristics intended for user guidance. They are NOT an official
    adjudication of passport acceptance.
    """
    results: List[RuleResult] = []

    # Rule: Size
    w, h = processed_rgb.size
    size_ok = (w == params.size) and (h == params.size)
    results.append(
        RuleResult(
            rule_id="Size",
            passed=size_ok,
            message=f"{w}x{h} pixels (expected {params.size}x{params.size}).",
            metrics={"width": w, "height": h, "expected": params.size},
        )
    )

    img_rgb = _pil_to_np_rgb(processed_rgb)
    H, W = img_rgb.shape[0], img_rgb.shape[1]

    # Landmarks for head ratio + centering
    nose_xy = forehead_xy = chin_xy = None
    lm = _get_landmarks(processed_rgb)
    if lm is not None:
        nose_xy = _lm_xy(lm[0])
        forehead_xy = _lm_xy(lm[1])
        chin_xy = _lm_xy(lm[2])

    # Rule: Head ratio
    if forehead_xy is None or chin_xy is None:
        results.append(
            RuleResult(
                rule_id="Head ratio",
                passed=False,
                message="Could not detect face landmarks (needed for head size check).",
                metrics={"head_ratio": None, "range": [0.50, 0.69]},
            )
        )
    else:
        head_px = max(0.0, float(chin_xy[1] - forehead_xy[1]))
        ratio = head_px / float(H) if H else 0.0
        lo, hi = 0.50, 0.69
        ok = (ratio >= lo) and (ratio <= hi)
        msg = f"{ratio:.2f} of image height (target {lo:.2f}–{hi:.2f})."
        if not ok:
            msg += " Adjust distance to camera or re-take with head sized appropriately."
        results.append(
            RuleResult(
                rule_id="Head ratio",
                passed=ok,
                message=msg,
                metrics={"head_ratio": ratio, "head_px": head_px, "range": [lo, hi]},
            )
        )

    # Rule: Centering (nose x near image center)
    if nose_xy is None:
        results.append(
            RuleResult(
                rule_id="Centering",
                passed=False,
                message="Could not detect face landmarks (needed for centering check).",
                metrics={"nose_x": None, "center_x": W / 2.0},
            )
        )
    else:
        center_x = W / 2.0
        dx = float(nose_xy[0] - center_x)
        tol = 0.08 * W  # 8% tolerance
        ok = abs(dx) <= tol
        msg = f"Nose offset {dx:+.0f}px (tolerance ±{tol:.0f}px)."
        if not ok:
            msg += " Re-center your face (keep nose near the middle)."
        results.append(
            RuleResult(
                rule_id="Centering",
                passed=ok,
                message=msg,
                metrics={"nose_x": nose_xy[0], "center_x": center_x, "dx_px": dx, "tolerance_px": tol},
            )
        )

    # Rule: Background whiteness (border pixels)
    margin = max(10, int(0.05 * min(H, W)))
    white_ratio = _near_white_ratio_border(img_rgb, margin=margin, thr=245)
    bg_ok = white_ratio >= 0.95
    bg_msg = f"Near-white border pixels: {white_ratio*100:.1f}% (target ≥ 95%)."
    if not bg_ok:
        bg_msg += " Background may not be white enough."
    results.append(
        RuleResult(
            rule_id="Background whiteness",
            passed=bg_ok,
            message=bg_msg,
            metrics={"white_ratio": white_ratio, "margin_px": margin, "threshold": 245},
        )
    )

    # Rule: Lighting heuristics
    lmets = _lighting_metrics(img_rgb)
    mean = lmets["luma_mean"]
    std = lmets["luma_std"]
    dark_clip = lmets["dark_clip"]
    bright_clip = lmets["bright_clip"]

    ok_mean = 60.0 <= mean <= 210.0
    ok_clip = (dark_clip <= 0.02) and (bright_clip <= 0.02)
    ok_std = 15.0 <= std <= 90.0
    light_ok = ok_mean and ok_clip and ok_std

    light_msg = f"Mean {mean:.0f}, Std {std:.0f}, Clip(D/B) {dark_clip*100:.1f}%/{bright_clip*100:.1f}%."
    if not light_ok:
        light_msg += " Avoid harsh shadows/backlight; use even front lighting."

    results.append(
        RuleResult(
            rule_id="Lighting",
            passed=light_ok,
            message=light_msg,
            metrics=lmets,
        )
    )

    passed = all(r.passed for r in results)
    return ValidationReport(passed=passed, results=results)


def format_report_text(report: ValidationReport) -> str:
    lines: List[str] = []
    lines.append("PassportShop Validation Report")
    lines.append("-" * 32)
    lines.append(f"Overall: {'PASS' if report.passed else 'FAIL'}")
    lines.append("")
    for r in report.results:
        mark = "✅" if r.passed else "❌"
        lines.append(f"{mark} {r.rule_id}: {r.message}")
    return "\n".join(lines)
