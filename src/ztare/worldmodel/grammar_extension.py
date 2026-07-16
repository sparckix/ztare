"""Sandbox decoder for extension functions carried by historical candidates.

This module has no proposal, dispatch, registration, or promotion authority.
Current grammar proposals travel through ``grammar_reflex`` to the governed
executable-carrier evaluator.  The decoder remains because admissible carrier
artifacts may contain extension source that must be reconstructed safely.
"""
from __future__ import annotations

from ztare.common.sandboxed_python import script_is_safe

_SAFE_BUILTINS = {
    "range": range,
    "len": len,
    "tuple": tuple,
    "list": list,
    "enumerate": enumerate,
    "min": min,
    "max": max,
    "sum": sum,
    "abs": abs,
    "reversed": reversed,
    "zip": zip,
    "sorted": sorted,
    "all": all,
    "any": any,
    "int": int,
    "bool": bool,
}


def compile_extension(code: str):
    """Decode a carried ``extension`` function under the bounded sandbox."""
    if not script_is_safe(code):
        return None, "rejected by sandbox safety scan"
    namespace: dict = {"__builtins__": _SAFE_BUILTINS}
    try:
        exec(code, namespace)  # noqa: S102 -- safety scan + minimal builtins
    except Exception as exc:  # noqa: BLE001
        return None, f"exec failed: {exc}"
    fn = namespace.get("extension")
    if not callable(fn):
        return None, "no `extension` function defined"
    probe = ((0, 1), (2, 0))
    try:
        out = fn(probe)
    except Exception as exc:  # noqa: BLE001
        return None, f"probe call failed: {exc}"
    if not isinstance(out, tuple) or not all(isinstance(row, tuple) for row in out):
        return None, "probe call returned wrong shape"
    return fn, ""
