"""GP-157 v5.0 Layer 1 — generate evidence.txt §D from ContractSpec.

Per panel synthesis from the evidence-contract review: the 5-source
contradiction failure mode (gp159) is structurally cured iff
evidence.txt §D is GENERATED from the ContractSpec, not hand-authored.
Substrate authors continue to write Evidence Sets A/B/C (the substrate-
specific scientific content); §D ("MANDATORY Python Contract") is
mechanically rendered from the ABI.

Usage:
    from src.ztare.orchestrator.contract_table import get_spec_by_class
    from src.ztare.orchestrator.render_evidence_template import (
        render_evidence_set_d,
    )

    spec = get_spec_by_class("1d")
    section_d = render_evidence_set_d(spec)
    # → drop into evidence.txt or ship as part of `make seal`'s template

Future tooling: cross-check that the
substrate's evidence.txt §D matches the freshly-rendered §D for its
declared cage_meta.class. Drift = misconfigured substrate.
"""

from __future__ import annotations

from src.ztare.orchestrator.contract_table import ContractSpec, SubstrateABI


# ── Rendering ─────────────────────────────────────────────────────────────


def render_evidence_set_d(spec: ContractSpec) -> str:
    """Return the canonical Evidence Set D text for one ContractSpec.

    The output is markdown suitable for direct inclusion in
    `projects/<slug>/evidence.txt`. Single source of truth: any change to
    the contract semantics edits THIS function and the table — every
    substrate's §D regenerates uniformly.
    """
    if spec.abi in (SubstrateABI.DISCRIMINATOR, SubstrateABI.LEAN_PROOF):
        # Non-I_model contracts use a different template.
        return _render_non_imodel(spec)
    return _render_imodel(spec)


def _render_imodel(spec: ContractSpec) -> str:
    forbidden_block = ""
    if spec.forbidden_module_patterns:
        rules = []
        for pat in spec.forbidden_module_patterns:
            if pat == "I_model(":
                rules.append(
                    "  - DO NOT call `I_model(...)` at module scope. "
                    "MODEL_PARAMS is empty at import time; module-level "
                    "calls detonate. Put debug calls inside "
                    "`if __name__ == \"__main__\":` (apparatus does NOT run that block)."
                )
                rules.append(
                    "  - DO NOT define `_post_fit_sanity()` / `_validate()` / similar "
                    "private helpers to hide module-level logic — the apparatus does "
                    "NOT invoke private helpers, so deferred asserts never run AND "
                    "I_model goes unverified."
                )
            else:
                rules.append(f"  - DO NOT include `{pat}` at module scope.")
        forbidden_block = "\n".join(rules)

    caps_block = ""
    if spec.required_filesystem_caps:
        caps_block = (
            "Substrate filesystem requirements (substrate author's responsibility):\n"
            + "\n".join(f"  - {cap}" for cap in sorted(spec.required_filesystem_caps))
        )

    skeleton = spec.skeleton_template.rstrip("\n")
    skeleton_block = f"```python\n{skeleton}\n```" if skeleton else ""

    return f"""## Evidence Set D — MANDATORY Python Contract (ABI={spec.abi.name})

**This block is auto-generated from `src/ztare/orchestrator/contract_table.py`.**
**Single source of truth for the test_model.py shape contract. Do not edit this**
**block by hand in evidence.txt — edit the table.**

{spec.docstring}

**Required signature:**

    {spec.signature_str}

**Required module-level identifiers in test_model.py:**

  - {chr(10).join(f"  - `{g}`" for g in spec.required_module_globals).strip()}

**Hard rules — apparatus rejects on violation:**

{forbidden_block}
  - I_model MUST return a finite float for every visible-set row.
    NaN/inf/None/list returns score zero immediately.
  - Use `p.get(name, default)` for every parameter read, so I_model
    returns a finite float in BOTH the empty-MODEL_PARAMS state
    (apparatus pre-fit) and the post-fit state.

**Canonical skeleton — copy this, edit the body:**

{skeleton_block}

{caps_block}

**Why this hint exists:** the apparatus IMPORTS test_model.py at gate
time. Whatever is at module scope runs at import. The mutator's I_model
must work the moment the file is imported. Hidden helpers that the
apparatus never calls are not a workaround — they're a contract violation.
"""


def _render_non_imodel(spec: ContractSpec) -> str:
    return f"""## Evidence Set D — MANDATORY Contract (ABI={spec.abi.name})

**This block is auto-generated from `src/ztare/orchestrator/contract_table.py`.**

{spec.docstring}

**Substrate filesystem requirements:**
  - {", ".join(sorted(spec.required_filesystem_caps)) if spec.required_filesystem_caps else "(none)"}
"""


def render_active_contract_label(spec: ContractSpec) -> str:
    """Return the one-line top-of-prompt label for this contract.

    Mirrors `prompt.py:active_contract_label` but driven from ContractSpec
    rather than from inline string-typed conditions. Will replace that
    function in a future commit; ships now as additive primitive.
    """
    return (
        f"ACTIVE CONTRACT: {spec.abi.name} ({spec.signature_str}). "
        f"See evidence.txt §D — it OVERRIDES any test_model.py shape implied "
        f"elsewhere in this prompt."
    )
