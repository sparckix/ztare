"""One strict, depth-safe copier for LeanMill protocol data."""
from __future__ import annotations

import math
from typing import Any


def strict_json_data(
    value: Any,
    *,
    context: str,
    max_depth: int = 128,
    max_wire_bytes: int | None = None,
    max_integer_bits: int | None = None,
    allow_finite_floats: bool = False,
) -> Any:
    """Copy canonical JSON data after an iterative type/depth preflight."""

    stack: list[tuple[Any, int]] = [(value, 0)]
    wire_bytes = 0

    def string_wire_bytes(item: str) -> int:
        size = 2
        for character in item:
            codepoint = ord(character)
            if character in {'"', "\\"} or character in "\b\t\n\f\r":
                size += 2
            elif codepoint < 0x20 or 0x7F <= codepoint <= 0xFFFF:
                size += 6
            elif codepoint > 0xFFFF:
                size += 12
            else:
                size += 1
        return size

    def add_wire_bytes(amount: int) -> None:
        nonlocal wire_bytes
        wire_bytes += amount
        if max_wire_bytes is not None and wire_bytes > max_wire_bytes:
            raise ValueError(f"{context} exceeds the maximum JSON wire size")

    while stack:
        current, depth = stack.pop()
        if depth > max_depth:
            raise ValueError(f"{context} exceeds the maximum JSON nesting depth")
        if type(current) is dict:
            if any(type(key) is not str for key in current):
                raise TypeError(f"{context} object keys must be strings")
            add_wire_bytes(2 + max(0, len(current) - 1))
            for key in current:
                add_wire_bytes(string_wire_bytes(key) + 1)
            stack.extend((item, depth + 1) for item in current.values())
        elif type(current) is list:
            add_wire_bytes(2 + max(0, len(current) - 1))
            stack.extend((item, depth + 1) for item in current)
        elif type(current) is str:
            add_wire_bytes(string_wire_bytes(current))
        elif type(current) is int:
            if (
                max_integer_bits is not None
                and abs(current).bit_length() > max_integer_bits
            ):
                raise ValueError(f"{context} exceeds the JSON integer bit ceiling")
            add_wire_bytes(len(str(current)))
        elif type(current) is bool:
            add_wire_bytes(4 if current else 5)
        elif type(current) is float and allow_finite_floats:
            if not math.isfinite(current):
                raise TypeError(f"{context} floats must be finite")
            add_wire_bytes(len(repr(current)))
        elif current is None:
            add_wire_bytes(4)
        else:
            raise TypeError(
                f"{context} must be data-only JSON, got "
                f"{type(current).__qualname__}"
            )

    def copy(current: Any) -> Any:
        if type(current) is dict:
            return {key: copy(current[key]) for key in sorted(current)}
        if type(current) is list:
            return [copy(item) for item in current]
        return current

    return copy(value)


__all__ = ["strict_json_data"]
