"""Launch a Python module after installing environment bindings in-process.

Shell-level ``KEY=value python ...`` launch wrappers can perturb subscription
agent CLIs spawned later by the Python process on macOS. This helper keeps the
outer Python launch clean, then applies the requested bindings before running a
target module via ``runpy``.
"""
from __future__ import annotations

import runpy
import sys


def _split(argv: list[str]) -> tuple[dict[str, str], list[str]]:
    try:
        marker = argv.index("--")
    except ValueError as exc:
        raise SystemExit("usage: env_launch KEY=VALUE... -- -m module [args...]") from exc
    env_args = argv[:marker]
    command = argv[marker + 1:]
    bindings: dict[str, str] = {}
    for item in env_args:
        if "=" not in item or item.startswith("="):
            raise SystemExit(f"env_launch expected KEY=VALUE before --, got: {item!r}")
        key, value = item.split("=", 1)
        bindings[key] = value
    if len(command) < 2 or command[0] != "-m":
        raise SystemExit("env_launch currently supports: -- -m module [args...]")
    return bindings, command


def main(argv: list[str] | None = None) -> int:
    import os

    bindings, command = _split(list(sys.argv[1:] if argv is None else argv))
    os.environ.update(bindings)
    module = command[1]
    sys.argv = [module, *command[2:]]
    runpy.run_module(module, run_name="__main__", alter_sys=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
