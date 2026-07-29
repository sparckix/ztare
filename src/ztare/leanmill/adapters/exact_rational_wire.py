"""Deterministic size projection for canonical exact-rational wire values.

Python may reject ``str(large_int)`` according to a process-global decimal
conversion guard.  Adapter semantics must not depend on that ambient setting.
This module computes the exact canonical wire size without converting a large
integer to decimal, so callers can enforce their own reviewed ceiling first.
"""
from __future__ import annotations

from fractions import Fraction


# Below CPython's default 4,300-digit guard.  Callers still catch conversion
# failures because an embedding process may configure a stricter guard.
MAX_CANONICAL_INTEGER_DECIMAL_DIGITS = 4_096


def exact_integer_decimal_digits(value: int) -> int:
    """Return ``len(str(abs(value)))`` without large-int string conversion."""

    if type(value) is not int:
        raise TypeError("decimal digit projection requires an integer")
    magnitude = abs(value)
    if magnitude < 10:
        return 1

    # 30103 / 100000 is a close upper approximation to log10(2).  Under
    # the adapters' one-million-bit hard ceiling this estimate differs from
    # the exact digit count by at most one; the comparisons make the result
    # exact rather than trusting the approximation.
    bit_index = magnitude.bit_length() - 1
    digits = (bit_index * 30_103) // 100_000 + 1
    decimal_floor = 10 ** (digits - 1)
    while magnitude < decimal_floor:
        decimal_floor //= 10
        digits -= 1
    while magnitude >= decimal_floor * 10:
        decimal_floor *= 10
        digits += 1
    return digits


def project_canonical_rational_wire(value: Fraction) -> dict[str, int]:
    """Project exact decimal digits and ASCII bytes for canonical ``n/d``."""

    frozen = Fraction(value)
    numerator_digits = exact_integer_decimal_digits(frozen.numerator)
    denominator_digits = exact_integer_decimal_digits(frozen.denominator)
    wire_bytes = numerator_digits + (1 if frozen.numerator < 0 else 0)
    if frozen.denominator != 1:
        wire_bytes += 1 + denominator_digits
    return {
        "numerator_decimal_digits": numerator_digits,
        "denominator_decimal_digits": denominator_digits,
        "max_integer_decimal_digits": max(
            numerator_digits, denominator_digits
        ),
        "wire_bytes": wire_bytes,
    }


__all__ = [
    "MAX_CANONICAL_INTEGER_DECIMAL_DIGITS",
    "exact_integer_decimal_digits",
    "project_canonical_rational_wire",
]
