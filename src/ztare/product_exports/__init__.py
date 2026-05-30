"""Public-safe typed exports for downstream product surfaces.

These exports are intentionally narrower than the internal kernel vocabulary.
They are designed for consumption by product repos such as ClearJudgment and
Mini-ZTARE without leaking private seams, private provenance, or internal
runtime control surfaces.
"""

from .judgment_primitives import (
    JUDGMENT_PRIMITIVES_V1,
    NON_PRIMITIVE_RUNTIME_CONCEPTS_V1,
    export_judgment_primitives_payload,
    render_typescript_module,
)

__all__ = [
    "JUDGMENT_PRIMITIVES_V1",
    "NON_PRIMITIVE_RUNTIME_CONCEPTS_V1",
    "export_judgment_primitives_payload",
    "render_typescript_module",
]
