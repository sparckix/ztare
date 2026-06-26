#!/usr/bin/env python3
"""Backward-compatible entrypoint for the GP-245 controlled-use audit."""

from __future__ import annotations

import importlib


def main() -> int:
    module = importlib.import_module("controlled_use_audit")
    return int(module.main())


if __name__ == "__main__":
    raise SystemExit(main())
