#!/usr/bin/env python3
"""Entry point for PassportShop GUI (Step 1: window shell)."""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)

from passportshop.ui.main_window import run

if __name__ == "__main__":
    run()
