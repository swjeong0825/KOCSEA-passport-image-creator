"""Test helpers.

These tests assume your repo layout is:
  project_root/
    src/
      passportshop/
      passport_photo.py
    tests/
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
