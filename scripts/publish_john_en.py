#!/usr/bin/env python3
"""DEPRECATED — shim for backward compat. Delegates to publish_calvin_en.py.

Use directly:
    python3 scripts/publish_calvin_en.py john
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
subprocess.check_call([sys.executable, str(ROOT / 'publish_calvin_en.py'), 'john'])
