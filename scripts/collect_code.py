#!/usr/bin/env python3
"""Collect all source code files into a single output file.

Usage:
    python scripts/collect_code.py

Output:
    outputs/all_code.txt
"""

import os
from datetime import datetime
from pathlib import Path

# Root directory of the project
ROOT = Path(__file__).parent.parent

# Output file
OUTPUT_DIR = ROOT / "outputs"
OUTPUT_FILE = OUTPUT_DIR / "all_code.txt"

# Directories to skip
SKIP_DIRS = {
    ".venv",
    ".git",
    "__pycache__",
    ".mypy_cache",
    ".pytest_cache",
    "node_modules",
    ".tox",
    "dist",
    "build",
    "*.egg-info",
    ".gemini",
    "outputs",
}

# File extensions to include
INCLUDE_EXTENSIONS = {
    ".py",
    ".toml",
    ".yaml",
    ".yml",
    ".json",
    ".md",
    ".txt",
    ".css",
    ".html",
    ".js",
}

# Files to skip by name
SKIP_FILES = {
    "uv.lock",
    "package-lock.json",
}

# Max file size (skip files larger than this)
MAX_FILE_SIZE = 100_000  # 100KB


def should_skip_dir(dir_path: Path) -> bool:
    """Check if directory should be skipped."""
    for skip in SKIP_DIRS:
        if skip in dir_path.parts:
            return True
    return False


def should_include_file(file_path: Path) -> bool:
    """Check if file should be included."""
    # Check extension
    if file_path.suffix.lower() not in INCLUDE_EXTENSIONS:
        return False

    # Check filename
    if file_path.name in SKIP_FILES:
        return False

    # Check file size
    try:
        if file_path.stat().st_size > MAX_FILE_SIZE:
            return False
    except OSError:
        return False

    return True


def collect_files() -> list[Path]:
    """Collect all source files."""
    files = []

    for root, dirs, filenames in os.walk(ROOT):
        root_path = Path(root)

        # Skip excluded directories
        if should_skip_dir(root_path):
            continue

        # Filter out directories we don't want to traverse
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith(".")]

        for filename in filenames:
            file_path = root_path / filename
            if should_include_file(file_path):
                files.append(file_path)

    # Sort by path for consistent ordering
    files.sort()
    return files


def main():
    """Main entry point."""
    print(f"Collecting source files from: {ROOT}")

    # Ensure output directory exists
    OUTPUT_DIR.mkdir(exist_ok=True)

    files = collect_files()
    print(f"Found {len(files)} files")

    with open(OUTPUT_FILE, "w", encoding="utf-8") as out:
        # Write header
        out.write("=" * 80 + "\n")
        out.write(f"Code Collection - {datetime.now().isoformat()}\n")
        out.write(f"Project: {ROOT.name}\n")
        out.write(f"Total Files: {len(files)}\n")
        out.write("=" * 80 + "\n\n")

        # Write table of contents
        out.write("TABLE OF CONTENTS\n")
        out.write("-" * 40 + "\n")
        for i, file_path in enumerate(files, 1):
            rel_path = file_path.relative_to(ROOT)
            out.write(f"{i:3}. {rel_path}\n")
        out.write("\n" + "=" * 80 + "\n\n")

        # Write each file
        for file_path in files:
            rel_path = file_path.relative_to(ROOT)

            out.write("\n")
            out.write("=" * 80 + "\n")
            out.write(f"FILE: {rel_path}\n")
            out.write("=" * 80 + "\n\n")

            try:
                content = file_path.read_text(encoding="utf-8")
                out.write(content)
                if not content.endswith("\n"):
                    out.write("\n")
            except Exception as e:
                out.write(f"[ERROR reading file: {e}]\n")

        out.write("\n" + "=" * 80 + "\n")
        out.write("END OF CODE COLLECTION\n")
        out.write("=" * 80 + "\n")

    print(f"Output written to: {OUTPUT_FILE}")
    print(f"File size: {OUTPUT_FILE.stat().st_size:,} bytes")


if __name__ == "__main__":
    main()
