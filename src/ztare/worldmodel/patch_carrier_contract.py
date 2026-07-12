from __future__ import annotations

import json


def patch_base_declaration(source_ref: str, sha256: str | None = None) -> str:
    """Return the canonical PATCH_BASE declaration used in prompt projections."""

    return (
        'PATCH_BASE = {"source_ref": '
        + json.dumps(str(source_ref))
        + ', "sha256": '
        + json.dumps(str(sha256 or ""))
        + "}"
    )


def patch_delta_signature(preferred: bool = True) -> str:
    """Leaf-facing patch-delta signature.

    The gate still accepts older four-argument deltas for compatibility, but
    worker-facing surfaces should not advertise the adapter trace coordinate.
    """

    return (
        "PATCH_DELTA(base_next, state, action)"
        if preferred
        else "PATCH_DELTA(base_next, state, action, t)"
    )


def patch_carrier_brief_line(*, include_compat_note: bool = False) -> str:
    line = (
        "Patch-base carrier, only when this prompt supplies a concrete "
        'patch_base_ref plus full SHA: `PATCH_BASE = {"source_ref":'
        '"workspace/submissions/<file>.py","sha256":"<full-sha256>"}` plus '
        f"`def {patch_delta_signature()}: ...`."
    )
    if include_compat_note:
        line += (
            " Older 4-argument deltas are ABI-compatible, but the adapter replay "
            "index is not transition-law evidence."
        )
    return line


def patch_base_reference_brief(source_ref: str, sha256: str | None, *, indent: str = "  ") -> str:
    return f"{indent}`{patch_base_declaration(source_ref, sha256)}`"
