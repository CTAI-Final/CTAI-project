#!/usr/bin/env python
"""Regenerate the public practice scenarios in ``data/practice/``.

The generator is deterministic: every file is a pure function of the seed recorded in
``manifest.json``, so regenerating never produces a diff unless the generator itself changed.

Usage:
    python scripts/generate_practice_data.py [--out data/practice]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:  # works without an editable install
    sys.path.insert(0, str(ROOT / "src"))

from ctai.datagen import write_practice_set  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default=str(ROOT / "data" / "practice"))
    args = parser.parse_args()

    for path in write_practice_set(args.out):
        print(f"wrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
