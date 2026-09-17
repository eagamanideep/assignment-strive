"""Create rfx_classifier.zip for submission. Works on Windows, macOS and Linux.

Usage: python package.py
"""
from __future__ import annotations

import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "rfx_classifier.zip"
EXCLUDE_DIRS = {".venv", "venv", "__pycache__", ".pytest_cache", ".git", ".idea", ".vscode"}
EXCLUDE_FILES = {".DS_Store", "Thumbs.db", "desktop.ini", OUTPUT.name}


def main() -> None:
    count = 0
    with zipfile.ZipFile(OUTPUT, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(ROOT.rglob("*")):
            rel = path.relative_to(ROOT)
            if path.is_dir() or path.name in EXCLUDE_FILES or EXCLUDE_DIRS & set(rel.parts):
                continue
            zf.write(path, Path("rfx_classifier") / rel)  # zipfile stores forward slashes on every OS
            count += 1
    print(f"Wrote {OUTPUT.name} ({count} files)")


if __name__ == "__main__":
    main()
