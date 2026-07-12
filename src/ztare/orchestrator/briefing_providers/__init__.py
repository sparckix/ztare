"""Mutator-briefing providers.

Shared invariant: a provider MUST render content or an explicit
UNAVAILABLE/DEGRADED banner — never a silent omission on read/parse/
compute error. Use ``section_unavailable`` for the uniform banner so the
mutator (and post-hoc operator audits) see a stable, greppable marker
instead of a dropped section.
"""
from __future__ import annotations


def section_unavailable(section: str, exc: BaseException, *, msg_prefix_chars: int = 200) -> str:
    """Uniform UNAVAILABLE banner for a briefing section.

    Format (stable, greppable):
        <SECTION> UNAVAILABLE — <exc type>: <msg prefix>; prior guidance still in force

    NEVER pass a ``SystemExit``/``KeyboardInterrupt`` here to swallow it —
    those must be re-raised by the caller. This helper is for ordinary
    read/parse/compute failures only.
    """
    msg = str(exc)
    if len(msg) > msg_prefix_chars:
        msg = msg[:msg_prefix_chars] + "…"
    return (
        f"## ⚠️  {section} UNAVAILABLE\n\n"
        f"{section} UNAVAILABLE — {type(exc).__name__}: {msg}; "
        f"prior guidance still in force\n\n"
    )
