from __future__ import annotations

import importlib
import os
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator


class OptionalKernelUnavailable(ImportError):
    """Raised when an optional external kernel is not importable."""


_ENV_SRC_PATHS = {
    "cognitive_firm": "ZTARE_COGNITIVE_FIRM_SRC",
}


def import_optional_kernel_module(
    module_name: str,
    *,
    kernel_id: str,
    extra_src_path: str | Path | None = None,
) -> Any:
    """Import an optional external-kernel module through one boundary.

    Feature code should not mutate ``sys.path`` or know checkout topology. Use
    this door, install the kernel normally, or provide an explicit source path
    via the kernel's environment variable while developing.
    """

    try:
        return importlib.import_module(module_name)
    except ModuleNotFoundError as first_error:
        if not _is_missing_requested_module(first_error, module_name):
            raise
        candidates = _candidate_src_paths(kernel_id, extra_src_path)
        if not candidates:
            raise OptionalKernelUnavailable(
                _install_hint(kernel_id, module_name)
            ) from first_error
        for candidate in candidates:
            with _temporary_sys_path(candidate):
                try:
                    return importlib.import_module(module_name)
                except ModuleNotFoundError as next_error:
                    if not _is_missing_requested_module(next_error, module_name):
                        raise
                    continue
        raise OptionalKernelUnavailable(
            _install_hint(kernel_id, module_name)
        ) from first_error


def _candidate_src_paths(
    kernel_id: str,
    extra_src_path: str | Path | None,
) -> list[Path]:
    paths: list[Path] = []
    if extra_src_path:
        paths.append(Path(extra_src_path).expanduser())
    env_name = _ENV_SRC_PATHS.get(kernel_id)
    if env_name:
        raw = os.environ.get(env_name, "")
        if raw.strip():
            paths.append(Path(raw).expanduser())
    out: list[Path] = []
    seen: set[str] = set()
    for path in paths:
        if not path.is_dir():
            continue
        key = str(path.resolve())
        if key in seen:
            continue
        seen.add(key)
        out.append(path.resolve())
    return out


@contextmanager
def _temporary_sys_path(path: Path) -> Iterator[None]:
    value = str(path)
    inserted = False
    if value not in sys.path:
        sys.path.insert(0, value)
        inserted = True
    try:
        yield
    finally:
        if inserted:
            try:
                sys.path.remove(value)
            except ValueError:
                pass


def _is_missing_requested_module(error: ModuleNotFoundError, module_name: str) -> bool:
    missing = str(getattr(error, "name", "") or "")
    root = module_name.split(".", 1)[0]
    return missing in {root, module_name}


def _install_hint(kernel_id: str, module_name: str) -> str:
    if kernel_id == "cognitive_firm":
        return (
            "optional kernel 'cognitive_firm' is unavailable. Install it into "
            "this environment (`pip install -e <cognitive-firm-checkout>`) or "
            "set ZTARE_COGNITIVE_FIRM_SRC to its src directory."
        )
    return f"optional kernel {kernel_id!r} is unavailable for module {module_name!r}."
