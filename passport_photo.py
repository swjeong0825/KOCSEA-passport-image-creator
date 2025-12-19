#!/usr/bin/env python3
"""
passport_photo.py

Generate a U.S.-passport-style 2x2" (square) image at 600x600 pixels:
- Detects a face (MediaPipe Face Mesh)
- Scales image so head height is ~target proportion of output height
- Crops a centered 600x600 square around the face
- Optionally replaces background with white (rembg)

Usage:
  python passport_photo.py --input /path/in.jpg --output /path/out.jpg
  python passport_photo.py --input in.jpg --output out.jpg --size 600 --head-ratio 0.62
  python passport_photo.py --input in.jpg --output out.jpg --no-bg

Notes:
- This script is for building your own tooling; always verify the final photo meets
  official requirements and is accepted by your application workflow.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from typing import Tuple, Optional

import numpy as np
from PIL import Image, ImageOps

# OpenCV is used for resizing (fast, high-quality interpolation options)
import cv2

# MediaPipe for face landmarks
import mediapipe as mp


@dataclass(frozen=True)
class LandmarkPx:
    x: float
    y: float


def _load_image_rgb(path: str) -> Image.Image:
    """Load an image, apply EXIF orientation, return RGB PIL Image."""
    img = Image.open(path)
    img = ImageOps.exif_transpose(img)
    if img.mode != "RGB":
        img = img.convert("RGB")
    return img


def _pil_to_bgr_np(img: Image.Image) -> np.ndarray:
    """PIL RGB -> OpenCV BGR numpy array."""
    arr = np.array(img)  # RGB
    return cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)


def _bgr_np_to_pil(img_bgr: np.ndarray) -> Image.Image:
    """OpenCV BGR numpy array -> PIL RGB."""
    rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
    return Image.fromarray(rgb)


def _detect_face_landmarks(img_rgb: Image.Image) -> Tuple[LandmarkPx, LandmarkPx, LandmarkPx]:
    """
    Detect face mesh landmarks and return (nose_tip, forehead_top, chin) pixel coords.

    Uses MediaPipe FaceMesh landmark indices:
      - nose tip: 1
      - forehead/top: 10  (approx top of forehead)
      - chin: 152
    """
    mp_face_mesh = mp.solutions.face_mesh

    # MediaPipe expects RGB numpy array
    rgb = np.array(img_rgb)

    with mp_face_mesh.FaceMesh(
        static_image_mode=True,
        refine_landmarks=True,
        max_num_faces=1,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5,
    ) as face_mesh:
        results = face_mesh.process(rgb)

    if not results.multi_face_landmarks:
        raise RuntimeError("No face detected. Try a clearer, front-facing photo with good lighting.")

    h, w = rgb.shape[:2]
    lm = results.multi_face_landmarks[0].landmark

    def to_px(i: int) -> LandmarkPx:
        return LandmarkPx(x=lm[i].x * w, y=lm[i].y * h)

    nose_tip = to_px(1)
    forehead = to_px(10)
    chin = to_px(152)

    # Basic sanity: chin below forehead
    if chin.y <= forehead.y:
        raise RuntimeError("Face landmarks looked inconsistent. Try a different image.")

    return nose_tip, forehead, chin


def _resize_bgr(img_bgr: np.ndarray, scale: float) -> np.ndarray:
    """Resize OpenCV BGR image by scale."""
    if scale <= 0:
        raise ValueError("Scale must be > 0")
    h, w = img_bgr.shape[:2]
    new_w = max(1, int(round(w * scale)))
    new_h = max(1, int(round(h * scale)))
    return cv2.resize(img_bgr, (new_w, new_h), interpolation=cv2.INTER_LANCZOS4)


def _crop_square_with_padding(
    img_bgr: np.ndarray,
    center_xy: Tuple[float, float],
    size: int,
    pad_color_bgr: Tuple[int, int, int] = (255, 255, 255),
) -> np.ndarray:
    """
    Crop a size x size square centered at center_xy from img_bgr.
    If crop goes out of bounds, pad with pad_color_bgr.
    """
    h, w = img_bgr.shape[:2]
    cx, cy = center_xy
    half = size / 2.0

    left = int(round(cx - half))
    top = int(round(cy - half))
    right = left + size
    bottom = top + size

    # Destination canvas
    out = np.full((size, size, 3), pad_color_bgr, dtype=np.uint8)

    # Source region intersection
    src_left = max(0, left)
    src_top = max(0, top)
    src_right = min(w, right)
    src_bottom = min(h, bottom)

    if src_left >= src_right or src_top >= src_bottom:
        # Entire crop out of bounds
        return out

    # Destination placement
    dst_left = src_left - left
    dst_top = src_top - top
    dst_right = dst_left + (src_right - src_left)
    dst_bottom = dst_top + (src_bottom - src_top)

    out[dst_top:dst_bottom, dst_left:dst_right] = img_bgr[src_top:src_bottom, src_left:src_right]
    return out


def _white_background_with_rembg(pil_rgb: Image.Image) -> Image.Image:
    """
    Remove background using rembg and composite onto a white background.
    If rembg isn't available or fails, returns original image.
    """
    try:
        from rembg import remove  # type: ignore
    except Exception:
        return pil_rgb

    try:
        # rembg works well with PIL; it returns an RGBA image (usually)
        cut = remove(pil_rgb)
        if isinstance(cut, bytes):
            cut = Image.open(io.BytesIO(cut))  # pragma: no cover
        cut = cut.convert("RGBA")

        white = Image.new("RGBA", cut.size, (255, 255, 255, 255))
        comp = Image.alpha_composite(white, cut).convert("RGB")
        return comp
    except Exception:
        return pil_rgb


def process_passport_photo(
    input_path: str,
    output_path: str,
    size: int = 600,
    head_ratio: float = 0.62,
    remove_background: bool = True,
) -> None:
    """
    Process input image and save a square output at `size` x `size`.

    Args:
      input_path: path to input image
      output_path: path to write output image (jpg/png/etc)
      size: output side length in pixels (default 600)
      head_ratio: target head height as a fraction of output height (e.g., 0.62)
      remove_background: if True, attempts background removal -> white background
    """
    if size < 200:
        raise ValueError("size too small; expected something like 600")
    if not (0.50 <= head_ratio <= 0.69):
        # This range is commonly cited for digital framing guidance.
        raise ValueError("head_ratio should be between 0.50 and 0.69 for typical U.S. passport framing guidance.")

    pil = _load_image_rgb(input_path)

    # Detect landmarks on the original image
    nose, forehead, chin = _detect_face_landmarks(pil)
    head_height_px = chin.y - forehead.y

    # Compute scale so head height matches the desired proportion of the output
    target_head_px = head_ratio * float(size)
    scale = target_head_px / float(head_height_px)

    # Resize the whole image and scale landmark coordinates too
    bgr = _pil_to_bgr_np(pil)
    bgr_rs = _resize_bgr(bgr, scale)

    nose_rs = (nose.x * scale, nose.y * scale)

    # Crop square around the face center (nose tip is a stable anchor)
    cropped = _crop_square_with_padding(bgr_rs, nose_rs, size=size, pad_color_bgr=(255, 255, 255))

    out_pil = _bgr_np_to_pil(cropped)

    if remove_background:
        out_pil = _white_background_with_rembg(out_pil)

    # Save with good JPEG quality by default
    out_lower = output_path.lower()
    if out_lower.endswith((".jpg", ".jpeg")):
        out_pil.save(output_path, format="JPEG", quality=95, optimize=True)
    else:
        out_pil.save(output_path)


def _build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Generate a 600x600 U.S. passport-style photo from an input image.")
    p.add_argument("--input", "-i", required=True, help="Path to input image (jpg/png/heic converted, etc.)")
    p.add_argument("--output", "-o", required=True, help="Path to output image (jpg/png)")
    p.add_argument("--size", type=int, default=600, help="Output size in pixels (default: 600)")
    p.add_argument("--head-ratio", type=float, default=0.62, help="Target head height / image height (0.50–0.69)")
    p.add_argument("--no-bg", action="store_true", help="Disable background removal/whitening step")
    return p


def main(argv: Optional[list[str]] = None) -> int:
    args = _build_arg_parser().parse_args(argv)

    try:
        process_passport_photo(
            input_path=args.input,
            output_path=args.output,
            size=args.size,
            head_ratio=args.head_ratio,
            remove_background=not args.no_bg,
        )
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2

    print(f"Saved: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
