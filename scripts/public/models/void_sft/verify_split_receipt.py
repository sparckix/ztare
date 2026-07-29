#!/usr/bin/env python3
"""Verify that formatted Void-SFT bytes use the governed family holdout."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from format_corpus import verify_format_manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, required=True)
    args = parser.parse_args()
    manifest = verify_format_manifest(args.data)
    print(json.dumps({
        "ok": True,
        "receipt_sha256": manifest["receipt_sha256"],
        "corpus_sha256": manifest["corpus_sha256"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
