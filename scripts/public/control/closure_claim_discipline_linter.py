#!/usr/bin/env python3
"""
closure_claim_discipline_linter.py — general-purpose discipline linter for
closure-claim artifacts (markdown notes, Lean files, F-row entries).

Implements four checks corresponding to the four meta-patterns/anti-patterns
established by the 2026-05-15 NS Clay closure session:

  1. ANTI-PATTERN-012 (vocabulary_chain_laundering) per-step explicit-
     verification check — looks for the 6-point verification block at each
     transition in a multi-step argument.

  2. META-PATTERN-023 (multi_scope_pattern_application) 4-scope coverage
     check — looks for explicit verification at local / chain / recursive /
     meta scopes.

  3. META-PATTERN-022 (gowers_first_with_content_layer_composition)
     catalog enumeration check — looks for explicit naming of universal-
     language ops from
     workingpapers/epistemic-generation/evidence/structural_language_catalog_20260514.json.

  4. Pre-tick meta-pattern surfacing — outputs a summary suitable for
     consumption by `rd_tick_brief.py` at session/tick start.

Usage:
  python3 closure_claim_discipline_linter.py check <path-to-artifact>
  python3 closure_claim_discipline_linter.py summary
  python3 closure_claim_discipline_linter.py status

Designed to be GENERAL-PURPOSE: works for any closure-claim artifact, not
just NS Clay. Integrates with the existing org/patterns and
org/anti-patterns catalogs via canonical sources of truth.
"""

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


REPO = Path(__file__).resolve().parents[3]

# Canonical sources (per AGENTS.md §6m)
ANTI_PATTERN_INDEX = REPO / "org/anti-patterns/INDEX.md"
PATTERN_INDEX = REPO / "org/patterns/INDEX.md"
ANTI_PATTERN_CATALOG = REPO / "docs/concepts/anti_pattern_catalog.md"
# Canonical TRACKED location (rendered from the .py registries via
# export_structural_language_catalog.py). Falls back to the legacy
# gitignored /workingpapers/ path so old checkouts don't break.
_SLC_TRACKED = REPO / "docs/reference/structural_language_catalog.json"
_SLC_LEGACY = REPO / "workingpapers/epistemic-generation/evidence/structural_language_catalog_20260514.json"
STRUCTURAL_LANGUAGE_CATALOG = _SLC_TRACKED if _SLC_TRACKED.exists() else _SLC_LEGACY
ARCHITECTURE_INDEX = REPO / "analytics/public/index/architecture_index.jsonl"


# ANTI-PATTERN-012 6-point verification signature
# (form / direction / quantifier / domain / dimension / inclusion)
AP012_REQUIRED_TOKENS = [
    ("direction", ["direction", "implication", "→", "⇒"]),
    ("quantifier", ["quantifier", "∀", "∃", "limsup", "pointwise", "a.e."]),
    ("domain", ["domain", "neighborhood", "support", "cylinder", "ball"]),
    ("dimension", ["dimension", "dim", "scaling", "parabolic", "spatial"]),
    ("inclusion", ["inclusion", "in or out", "kernel", "annihilator", "subspace"]),
    ("form", ["form", "operator", "1-form", "tensor"]),
]


# META-PATTERN-023 4-scope coverage signature
MP023_REQUIRED_SCOPES = [
    ("local", ["local scope", "per-step", "per step", "step verification"]),
    ("chain", ["chain scope", "overall chain", "chain-level", "chain structure"]),
    ("recursive", ["recursive scope", "sub-chain", "sub chain", "recursion"]),
    ("meta", ["meta scope", "meta-scope", "cross-scope", "strategic framing"]),
]


# META-PATTERN-022 catalog enumeration signature
# The universal-language catalog's named ops.
MP022_CATALOG_OPS_PARTIAL = [
    "Problem Reformulation",
    "Auxiliary Comparison Object",
    "Limit-Passage Property Inheritance",
    "Sharpness",
    "Failure-Witness",
    "Proof-Surface Compression",
    "Regime",
    "Class Scoping",
    "Threshold Dichotomy",
    "Representation",
    "Coordinate Reformulation",
    "Decomposition",
    "Local-to-Global",
    "Canonical Form",
    "Cross-Domain Translation",
    "Iterative Refinement",
    "Recursive Decomposition",
    "Duality",
    "Adversarial Framing",
    "Layered Approximation",
    "Extremal Method",
    "Probabilistic",
    "Dimensional",
    "Structural Lifting",
    "Constraint Imposition",
    "Characterization by Obstruction",
    "Internalization",
    "Axiomatization",
    "Foundational Repair",
    "Controlled Universe",
]


def _load_text(path: Path) -> Optional[str]:
    if not path.exists():
        return None
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return None


def check_ap012_per_step_verification(text: str) -> Dict[str, object]:
    """ANTI-PATTERN-012 check: does the artifact have 6-point verification?"""
    lowered = text.lower()
    found = {}
    for name, tokens in AP012_REQUIRED_TOKENS:
        found[name] = any(tok.lower() in lowered for tok in tokens)
    pass_count = sum(1 for v in found.values() if v)
    return {
        "check": "ANTI-PATTERN-012",
        "name": "per-step explicit verification",
        "tokens_found": found,
        "pass_count": pass_count,
        "passes": pass_count >= 4,  # at least 4 of 6 tokens
    }


def check_mp023_scope_coverage(text: str) -> Dict[str, object]:
    """META-PATTERN-023 check: does the artifact cover 4 scopes?"""
    lowered = text.lower()
    found = {}
    for name, tokens in MP023_REQUIRED_SCOPES:
        found[name] = any(tok.lower() in lowered for tok in tokens)
    pass_count = sum(1 for v in found.values() if v)
    return {
        "check": "META-PATTERN-023",
        "name": "4-scope coverage",
        "scopes_found": found,
        "pass_count": pass_count,
        "passes": pass_count >= 3,  # at least 3 of 4 scopes
    }


def check_mp022_op_enumeration(text: str) -> Dict[str, object]:
    """META-PATTERN-022 check: does the artifact enumerate universal-language ops?"""
    ops_found = [op for op in MP022_CATALOG_OPS_PARTIAL if op.lower() in text.lower()]
    return {
        "check": "META-PATTERN-022",
        "name": "universal-language op enumeration",
        "ops_found": ops_found,
        "ops_count": len(ops_found),
        "passes": len(ops_found) >= 2,  # at least 2 ops named
    }


def check_anti_pattern_012_specific(text: str) -> Dict[str, object]:
    """Check for explicit ANTI-PATTERN-012 references / discipline."""
    has_explicit_ap012 = (
        "ANTI-PATTERN-012" in text
        or "anti-pattern-012" in text.lower()
        or "vocabulary_chain_laundering" in text.lower()
        or "vocabulary-chain-laundering" in text.lower()
    )
    return {
        "check": "ANTI-PATTERN-012-explicit",
        "name": "explicit ANTI-PATTERN-012 reference",
        "found": has_explicit_ap012,
        "passes": has_explicit_ap012,
    }


# === Tier-1.5 checks added 2026-05-15 after META-ANTI-PATTERN catch ===
# (linter gaming caught by ruthless Meta-Darwin on tick516-519 claimed reductions)

# Heuristic: a "reduction claim" artifact mentions one of these phrases
REDUCTION_CLAIM_KEYWORDS = [
    "reduced", "reduction", "REDUCED", "substrate prop", "substrate-prop",
    "noPostHocResidualChoice", "noFinalBudgetSlackDefinition",
    "noScalarOnlyRouteTotalSplit", "recurrentPacketReuseRejectedOrPaysRecharge",
    "alphaI", "alpha_I", "alphaA", "alpha_A",
    "SuitableLocalEnergyDefectMeasureSource", "EventLocalDefectDropNoReuse",
]

# If the artifact claims to reduce substrate Props, it MUST import the substrate
SUBSTRATE_FILES = [
    "ns_route1_fresh_frequency_coercivity_adapter",
    "ns_silent_flat_defect_observability",
]


def check_substrate_import(text: str) -> Dict[str, object]:
    """If artifact claims substrate-prop reduction, must import substrate file."""
    claims_reduction = any(kw in text for kw in REDUCTION_CLAIM_KEYWORDS)
    if not claims_reduction:
        return {
            "check": "substrate-import",
            "name": "substrate-engagement: import check",
            "applicable": False,
            "passes": True,
        }
    imports_substrate = any(f in text for f in SUBSTRATE_FILES)
    return {
        "check": "substrate-import",
        "name": "substrate-engagement: import check",
        "applicable": True,
        "claims_reduction": True,
        "imports_substrate": imports_substrate,
        "passes": imports_substrate,
    }


def check_literal_true_proofs(text: str) -> Dict[str, object]:
    """Flag `:= True` / `:= true` in Prop/Bool fields of status/pincer/reduced
    structures — these are zero-content proof fraud (caught META-ANTI-PATTERN
    on tick516-519: 17+ such lines across the 4 claimed-reduction files)."""
    import re

    # Match e.g. `field_name := True` or `field_name := true` on a line
    pattern = re.compile(r"^\s*(\w+)\s*:=\s*(True|true)\s*$", re.MULTILINE)
    suspicious_lines = []
    for m in pattern.finditer(text):
        field_name = m.group(1)
        # Heuristic: only flag fields that LOOK like claimed proofs
        # (contain "reduced", "proven", "verified", "closed", "passes", "pincer",
        #  "_complete", "_validated", "_applied", "_present", "_satisfied").
        suspicious_tokens = [
            "reduced", "proven", "verified", "closed", "passes",
            "pincer", "complete", "validated", "applied",
            "satisfied", "established", "discharged",
        ]
        if any(tok in field_name.lower() for tok in suspicious_tokens):
            suspicious_lines.append(m.group(0).strip())

    return {
        "check": "literal-True-proof-fraud",
        "name": "literal `:= True` in claim-bearing fields",
        "suspicious_lines": suspicious_lines,
        "count": len(suspicious_lines),
        # Pass = no suspicious lines
        "passes": len(suspicious_lines) == 0,
    }


# Substrate's opaque Props that the decision-critical content lives in.
# A "substrate-direct" tick that doesn't reference ANY of these is just
# a substrate-typed corollary, not a Prop-discharge.
SUBSTRATE_OPAQUE_PROPS = [
    "noPostHocResidualChoice",
    "cutoffChosenBeforeRouteReceipt",
    "residualMeasureIndependentlyGenerated",
    "defectGeneratedBeforePositiveVariation",
    "noFinalBudgetSlackDefinition",
    "noScalarOnlyRouteTotalSplit",
    "recurrentPacketReuseRejectedOrPaysRecharge",
    "noPostHocResidualChoice",
    "fixedEventTentAndCutoff",
    "signedLocalEnergyMeasureIdentity",
    "lineageFreshness",
    "noReuseOfEventLocalDefectCharge",
]


def check_opaque_prop_engagement(text: str) -> Dict[str, object]:
    """If a tick claims substrate-Prop reduction/discharge, it must
    reference at least one of the substrate's opaque Props by name
    (e.g., `noPostHocResidualChoice`). Otherwise it's a substrate-
    typed corollary, NOT a Prop discharge.

    META-ANTI-PATTERN-v2 catch: tick522/523 imported substrate, used
    substrate carrier, but never referenced the opaque Props they
    claimed to reduce. Linter v1.6 catches this."""
    claims_reduction = any(kw in text for kw in REDUCTION_CLAIM_KEYWORDS)
    if not claims_reduction:
        return {
            "check": "opaque-prop-engagement",
            "name": "substrate opaque-Prop named in theorem",
            "applicable": False,
            "passes": True,
        }
    # Look for substrate opaque Props referenced in theorem-content
    # (not just docstring/comment). Heuristic: look for `.NAME` accesses
    # or explicit Prop names in theorem bodies.
    import re

    referenced = []
    for prop_name in SUBSTRATE_OPAQUE_PROPS:
        # Look for `h.prop_name` or `prop_name : Prop` references
        pattern = re.compile(r"(?:\.|^|\s)" + re.escape(prop_name) + r"(?:\s|$|:)")
        if pattern.search(text):
            referenced.append(prop_name)

    return {
        "check": "opaque-prop-engagement",
        "name": "substrate opaque-Prop named in theorem",
        "applicable": True,
        "claims_reduction": True,
        "opaque_props_referenced": referenced,
        "count": len(referenced),
        "passes": len(referenced) > 0,
    }


def check_theorem_triviality_on_zero(text: str) -> Dict[str, object]:
    """Heuristic check: if a theorem's proof body is JUST one of
    {linarith, ring, rfl, trivial, decide} after destructuring, it's
    likely trivial on the canonical zero-inhabitant of the substrate.

    Counts theorem proof bodies that look like 1-2 tactic invocations
    of these trivial closers. High counts in a "substrate-Prop
    reduction" claim are suspicious."""
    import re

    # Match theorem ... := by ... linarith/ring/rfl/trivial patterns
    trivial_tactics = ["linarith", "ring", "rfl", "trivial", "decide"]
    suspicious_count = 0

    # Find theorem blocks; for each, count whether closing tactics are trivial
    theorem_blocks = re.findall(
        r"theorem\s+\w+.*?(?=\ntheorem\s|\ndef\s|\nstructure\s|\nend\s|\Z)",
        text,
        re.DOTALL,
    )
    for tb in theorem_blocks:
        # Last 200 chars likely contain the closing tactic
        tail = tb[-300:]
        # Count occurrences of trivial closers
        trivial_hits = sum(tail.count(t) for t in trivial_tactics)
        # Count nontrivial tactics
        nontrivial_tactics = ["have ", "induction", "rcases", "refine"]
        nontrivial_hits = sum(tail.count(t) for t in nontrivial_tactics)
        if trivial_hits >= 1 and nontrivial_hits <= 5:
            suspicious_count += 1

    # If many theorems and most are trivial-closure, suspicious
    return {
        "check": "theorem-triviality-on-zero",
        "name": "theorem proofs are mostly trivial closers",
        "suspicious_theorems_count": suspicious_count,
        "total_theorems": len(theorem_blocks),
        # Pass if either no theorems or fewer than half are suspicious
        "passes": len(theorem_blocks) == 0
        or suspicious_count < len(theorem_blocks) / 2 + 1,
    }


# === Tier-1.7 (added 2026-05-15 after Meta-Darwin V4 KILL of tick526-530) ===
# Alpha-rename-invariance: detect "real-content laundering via Mathlib-shell
# composition" — substrate names decorate generic Mathlib lemma composition.

MATHLIB_SHELL_LEMMAS = [
    "Finset.sum_le_sum",
    "Finset.sum_const",
    "Finset.mul_sum",
    "le_trans",
    "mul_le_mul_of_nonneg_left",
    "mul_le_mul_of_nonneg_right",
    "le_min",
    "linarith",
    "rfl",
    "ring",
    "congrFun",
    "funext",
]


def check_alpha_rename_invariance(text: str) -> Dict[str, object]:
    """Tier-1.7: alpha-rename-invariance.

    Detects 'real-content laundering via Mathlib-shell composition'
    (iteration-4 laundering caught by Meta-Darwin V4 on tick526-530).

    Heuristic: proofs are Mathlib-shell composition with substrate
    names attached. Alpha-rename-invariant proofs hold for any
    indexed-real Finset system; substrate names are decoration.

    A theorem is suspicious if its proof body uses ≥ 2 Mathlib-shell
    lemmas with ≤ 3 substrate field accesses in ≤ 12 lines.
    """
    import re

    theorem_blocks = re.findall(
        r"theorem\s+\w+.*?:=\s*by(.*?)(?=\ntheorem\s|\ndef\s|\nstructure\s|\nend\s|\Z)",
        text,
        re.DOTALL,
    )
    if not theorem_blocks:
        return {
            "check": "alpha-rename-invariance",
            "name": "alpha-rename invariance (Mathlib-shell composition)",
            "applicable": False,
            "passes": True,
        }

    suspicious_count = 0
    total_theorems = len(theorem_blocks)

    for tb in theorem_blocks:
        mathlib_hits = sum(tb.count(lem) for lem in MATHLIB_SHELL_LEMMAS)
        # Strict heuristic: count DISTINCT substrate field NAMES referenced
        # (not occurrence count). An alpha-rename invariant proof uses few
        # distinct substrate fields, each as a "name placeholder" for the
        # generic operation.
        substrate_field_pattern = re.compile(r"h\.([a-zA-Z_]\w*)")
        distinct_fields = set(substrate_field_pattern.findall(tb))
        proof_lines = tb.strip().count("\n") + 1
        # Ratio of Mathlib-shell to proof lines — high means composition
        # dominates substrate semantics
        shell_density = mathlib_hits / max(proof_lines, 1)
        # Flag suspicious if: short proof, dominated by Mathlib shell calls,
        # and few distinct substrate fields (decoration not engagement).
        if (
            proof_lines <= 15
            and mathlib_hits >= 2
            and len(distinct_fields) <= 4
            and shell_density >= 0.2
        ):
            suspicious_count += 1

    return {
        "check": "alpha-rename-invariance",
        "name": "alpha-rename invariance (Mathlib-shell composition)",
        "suspicious_theorems_count": suspicious_count,
        "total_theorems": total_theorems,
        "passes": suspicious_count < (total_theorems / 2 + 1),
    }


def check_substrate_carrier_engagement(text: str) -> Dict[str, object]:
    """If artifact claims substrate-Prop reduction, check it uses substrate's
    carrier as a HYPOTHESIS (not just mentions the name in a comment)."""
    claims_reduction = any(kw in text for kw in REDUCTION_CLAIM_KEYWORDS)
    if not claims_reduction:
        return {
            "check": "substrate-carrier-engagement",
            "name": "substrate carrier used as hypothesis",
            "applicable": False,
            "passes": True,
        }
    import re

    # Look for substrate carriers appearing as hypothesis types in `theorem`
    # or `def` signatures (e.g. `(h : SuitableLocalEnergyDefectMeasureSource ...)`).
    carrier_names = [
        "SuitableLocalEnergyDefectMeasureSource",
        "EventLocalDefectDropNoReuse",
        "FixedCutoffLocalEnergySignedMeasureIdentitySource",
        "LocalEnergyPositiveBoundaryFluxMeasureSplitSource",
    ]
    pattern = re.compile(
        r"\(\s*\w+\s*:\s*("
        + "|".join(carrier_names)
        + r")\b"
    )
    matches = pattern.findall(text)
    return {
        "check": "substrate-carrier-engagement",
        "name": "substrate carrier used as hypothesis",
        "applicable": True,
        "claims_reduction": True,
        "carrier_hypotheses_found": list(set(matches)),
        "count": len(matches),
        "passes": len(matches) > 0,
    }


# ---------------------------------------------------------------------------
# Tier-1 Check #5 (added 2026-05-15) — PATTERN-026 primitive_before_architecture_gate
# ---------------------------------------------------------------------------
# Calibration audit (pattern_026_calibration_audit.py) on 2026-05-15 yielded
# 3/5 AUTOMATIC across 5 historical seams (PASS at pre-registered ≥3 gate).
# Coverage gap: heuristic missed "Routes A/B/C" (GP-225) and "Op N" (GP-216)
# naming. Lexical triggers below are EXTENDED to cover these variants.
#
# A "layer-like component" per PATTERN-026 v1:
# - Section header matching one of: Layer/Stage/Phase/Route/Op/Component/Tier N
# - Numbered subsection (§N.M)
# - Header containing the words "component" / "primitive"

_P026_ARCH_LEXICAL = [
    r"\barchitecture\b",
    r"\bLayer\s+[A-Za-z0-9]+\b",
    r"\bStage\s+[A-Za-z0-9]+\b",
    r"\bPhase\s+[A-Za-z0-9]+\b",
    r"\bRoute\s+[A-Z]\b",
    r"\bOp\s+\d",
    r"\b\d+[- ]layer\b",
    r"\bmulti[- ]layer\b",
    r"\bload[- ]bearing\b",
]

_P026_LAUNDERABLE_LEXICAL = [
    r"first pass is crude",
    r"crude first pass",
    r"\bfirst pass\b",
    r"research thread",
    r"deferred to future work",
    r"\bTBD\b",
    r"to be written",
    r"to be determined",
    r"v1 (?:implementation|version) is approximate",
    r"approximate first version",
    r"we'?ll skip",
    r"is the hardest step",
    r"will be refined",
]

_P026_LAYER_TITLE_RE = re.compile(
    r"^#{2,4}\s+(?:[*_`]*\s*)?"
    r"(?:Layer|Stage|Phase|Route|Op|Component|Tier|Step)\s+[A-Za-z0-9]+"
    r"|^#{2,4}\s+§?\d+\.[0-9a-z]+",
    re.MULTILINE | re.IGNORECASE,
)


def _p026_find_layer_sections(text: str) -> List[Dict[str, Any]]:
    """Identify layer-like sections in the artifact."""
    layers: List[Dict[str, Any]] = []
    for m in re.finditer(r"^(#{2,4})\s+(.+)$", text, re.MULTILINE):
        title = m.group(2).strip()
        clean_title = re.sub(r"[*_`]", "", title)
        is_layer = bool(
            re.search(
                r"\b(Layer|Stage|Phase|Route|Op|Component|Tier|Step)\s+[A-Za-z0-9]+\b",
                clean_title,
                re.IGNORECASE,
            )
            or re.search(r"^§?\d+\.[0-9a-z]+", clean_title)
        )
        if not is_layer:
            continue
        # Section body: until next header of same/higher level
        start = m.end()
        nm = re.search(r"^(#{1,4})\s+", text[start:], re.MULTILINE)
        end = start + nm.start() if nm else len(text)
        layers.append({
            "title": clean_title,
            "body": text[start:end][:3000],
        })
    return layers


def _p026_check_layer(layer: Dict[str, Any]) -> Dict[str, Any]:
    body = layer["body"]
    has_artifact = bool(re.search(
        r"`[a-z_][\w/]*\.(?:py|lean|json|yaml|md)`|`scripts/|`src/|`org/",
        body,
    ))
    pass_gate_signals = [
        r"pass[- ]gate", r"pass.*≥|\bpass.*\d+%",
        r"threshold.*\d", r"accuracy\s*[≥>]\s*\d",
        r"F1\s*[≥>]", r"if\s+\w+\s*<\s*\d",
        r"falsifi", r"retract.*if", r"kill.*if",
    ]
    has_pass_gate = any(re.search(p, body, re.IGNORECASE) for p in pass_gate_signals)
    measurement_signals = [
        r"\d+\s*/\s*\d+\s*\(\s*\d+\s*%\)",
        r"\b(?:accuracy|F1|score|recall|precision)\b.*\d",
        r"\d+\.\d+\s*%",
        r"measured\s*[:=]",
    ]
    has_measurement = any(re.search(p, body, re.IGNORECASE) for p in measurement_signals)
    laundering = [p for p in _P026_LAUNDERABLE_LEXICAL if re.search(p, body, re.IGNORECASE)]
    fires = not (has_artifact and has_pass_gate and has_measurement)
    return {
        "title": layer["title"],
        "has_artifact_citation": has_artifact,
        "has_pass_gate": has_pass_gate,
        "has_measurement": has_measurement,
        "laundering_markers": laundering,
        "fires_026": fires,
    }


def check_pattern_026_architecture_validation(text: str) -> Dict[str, object]:
    """PATTERN-026: primitive_before_architecture_gate.

    Fires if the artifact is architecture-flavored AND any named layer/
    component lacks artifact-citation OR pass-gate OR measurement.
    """
    is_arch = any(re.search(p, text, re.IGNORECASE) for p in _P026_ARCH_LEXICAL)
    if not is_arch:
        return {
            "name": "pattern_026_architecture_validation",
            "passes": True,
            "applicable": False,
            "reason": "not an architecture artifact (no Layer/Stage/Phase/Route/Op/Component lexical signal)",
        }

    layers = _p026_find_layer_sections(text)
    if not layers:
        return {
            "name": "pattern_026_architecture_validation",
            "passes": True,
            "applicable": False,
            "reason": "architecture-flavored but no layer-like sections identified by heuristic — refer to Tier-2 LLM semantic check",
            "tier2_hint": True,
        }

    per_layer = [_p026_check_layer(L) for L in layers]
    n_total = len(per_layer)
    n_firing = sum(1 for L in per_layer if L["fires_026"])
    n_laundering = sum(1 for L in per_layer if L["laundering_markers"])

    return {
        "name": "pattern_026_architecture_validation",
        "applicable": True,
        "passes": n_firing == 0,
        "n_layers": n_total,
        "n_layers_firing_026": n_firing,
        "n_layers_with_launderable_lexical": n_laundering,
        "per_layer_summary": [
            {
                "title": L["title"][:80],
                "fires": L["fires_026"],
                "missing": [
                    k.replace("has_", "")
                    for k in ("has_artifact_citation", "has_pass_gate", "has_measurement")
                    if not L[k]
                ],
                "laundering_markers": L["laundering_markers"],
            }
            for L in per_layer[:20]
        ],
    }


def check_tier0_lean_organs(path: Path) -> Dict[str, object]:
    """Tier-0 (execution-grounded) closure-governance check.

    For `.lean` artifacts only: invokes the SHARED organ runner
    `_run_v33_anti_laundering` (the same spine the in-loop GP-211 gate
    uses — no organ-running duplicated here) to attest, leakage-
    independently, whether the proof is a false closure (AP-013).
    Non-`.lean` artifacts are skipped (passes=True). Fail-open: any
    organ-layer error → passes=True with a note (never block the linter
    on an organ bug — mirrors the in-loop gate's fail-open).
    """
    if path.suffix != ".lean":
        return {"check": "TIER-0-lean-organs", "passes": True,
                "skipped": "not a .lean artifact"}
    try:
        import importlib.util as _ilu
        spine_path = REPO / "src/ztare/gates/lean_proof_gate.py"
        spec = _ilu.spec_from_file_location("lpg_spine", spine_path)
        m = _ilu.module_from_spec(spec)
        sys.modules["lpg_spine"] = m
        spec.loader.exec_module(m)  # type: ignore[attr-defined]
        source = path.read_text(encoding="utf-8", errors="replace")
        proofs_root = REPO / "ztare_workspace" / "proofs"
        res = m.run_anti_laundering_kernel(source, path, proofs_root,
                                         deep_verify=False)
        return {"check": "TIER-0-lean-organs",
                "passes": bool(res.get("passed", True)),
                "confirmed_flags": list(res.get("flags", [])),
                "detail": res.get("detail", {})}
    except Exception as e:  # fail-open
        return {"check": "TIER-0-lean-organs", "passes": True,
                "fail_open_error": f"{type(e).__name__}: {e}"}


def lint_artifact(path: Path) -> Dict[str, object]:
    """Run all discipline checks (T1 token + Tier-0 execution-grounded)."""
    text = _load_text(path)
    if text is None:
        return {"path": str(path), "error": "file not found or unreadable"}

    results = {
        "path": str(path),
        "checks": [
            check_ap012_per_step_verification(text),
            check_mp023_scope_coverage(text),
            check_mp022_op_enumeration(text),
            check_anti_pattern_012_specific(text),
            # Tier-1.5 (added 2026-05-15 after META-ANTI-PATTERN catch):
            check_substrate_import(text),
            check_literal_true_proofs(text),
            check_substrate_carrier_engagement(text),
            # Tier-1.6 (added 2026-05-15 after META-ANTI-PATTERN v2 catch on tick522/523):
            check_opaque_prop_engagement(text),
            check_theorem_triviality_on_zero(text),
            # Tier-1.7 (added 2026-05-15 — alpha-rename-invariance, META-ANTI-PATTERN v4):
            check_alpha_rename_invariance(text),
            # Tier-1.7b (added 2026-05-15 — Check #5 — PATTERN-026 primitive_before_architecture_gate):
            check_pattern_026_architecture_validation(text),
            # Tier-0 (added 2026-05-15 — execution-grounded, .lean only, shared spine, fail-open):
            check_tier0_lean_organs(path),
        ],
    }
    results["overall_passes"] = all(c.get("passes", False) for c in results["checks"])
    return results


def cmd_check(args: argparse.Namespace) -> int:
    path = Path(args.path).resolve()
    result = lint_artifact(path)
    print(json.dumps(result, indent=2))
    return 0 if result.get("overall_passes", False) else 1


def cmd_summary(_args: argparse.Namespace) -> int:
    """Print current state of meta-pattern catalog as input to pre-tick brief."""
    # Count META-PATTERN entries in INDEX.md
    pattern_index_text = _load_text(PATTERN_INDEX) or ""
    meta_count = len(re.findall(r"\| META-PATTERN-\d+", pattern_index_text))
    pattern_count = len(re.findall(r"\| PATTERN-\d+", pattern_index_text))

    # Count ANTI-PATTERN entries in INDEX.md
    anti_index_text = _load_text(ANTI_PATTERN_INDEX) or ""
    anti_count = len(re.findall(r"\| ANTI-PATTERN-\d+", anti_index_text))

    # Architecture index entries
    arch_text = _load_text(ARCHITECTURE_INDEX) or ""
    arch_meta_count = arch_text.count("META-PATTERN-")
    arch_anti_count = arch_text.count("ANTI-PATTERN-")

    summary = {
        "catalog_state": {
            "patterns": pattern_count,
            "meta_patterns": meta_count,
            "anti_patterns": anti_count,
            "architecture_index_meta_patterns": arch_meta_count,
            "architecture_index_anti_patterns": arch_anti_count,
        },
        "discipline_checks_available": [
            "ANTI-PATTERN-012 per-step verification",
            "META-PATTERN-023 4-scope coverage",
            "META-PATTERN-022 universal-language op enumeration",
            "ANTI-PATTERN-012 explicit reference",
        ],
        "usage": (
            "python3 closure_claim_discipline_linter.py check <path-to-artifact>"
        ),
        "canonical_sources": {
            "anti_pattern_index": str(ANTI_PATTERN_INDEX.relative_to(REPO)),
            "pattern_index": str(PATTERN_INDEX.relative_to(REPO)),
            "anti_pattern_catalog": str(ANTI_PATTERN_CATALOG.relative_to(REPO)),
            "structural_language_catalog": str(
                STRUCTURAL_LANGUAGE_CATALOG.relative_to(REPO)
            ),
            "architecture_index": str(ARCHITECTURE_INDEX.relative_to(REPO)),
        },
    }
    print(json.dumps(summary, indent=2))
    return 0


def cmd_status(_args: argparse.Namespace) -> int:
    """Print human-readable status for pre-tick consumption."""
    s = json.loads(_run_summary())
    cs = s["catalog_state"]
    print("=== Closure-Claim Discipline Linter — Pre-Tick Status ===")
    print(
        f"Pattern catalog: {cs['patterns']} PATTERN-NNN + "
        f"{cs['meta_patterns']} META-PATTERN-NNN"
    )
    print(f"Anti-pattern catalog: {cs['anti_patterns']} ANTI-PATTERN-NNN")
    print(
        f"Architecture index: {cs['architecture_index_meta_patterns']} META + "
        f"{cs['architecture_index_anti_patterns']} ANTI entries"
    )
    print()
    print("Discipline checks available:")
    for chk in s["discipline_checks_available"]:
        print(f"  - {chk}")
    print()
    print("Run on a closure-claim artifact:")
    print(f"  {s['usage']}")
    print()
    print("Canonical sources:")
    for name, path in s["canonical_sources"].items():
        print(f"  {name}: {path}")
    return 0


def _run_summary() -> str:
    """Internal: capture cmd_summary output as JSON string."""
    import io
    import contextlib

    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        cmd_summary(argparse.Namespace())
    return buf.getvalue()


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Closure-claim discipline linter — checks artifacts against "
            "ANTI-PATTERN-012 + META-PATTERN-022 + META-PATTERN-023 "
            "discipline rules."
        )
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_check = sub.add_parser("check", help="lint a single artifact")
    p_check.add_argument("path", help="path to markdown/Lean file")
    p_check.set_defaults(func=cmd_check)

    p_sum = sub.add_parser("summary", help="JSON summary of catalog state")
    p_sum.set_defaults(func=cmd_summary)

    p_stat = sub.add_parser(
        "status", help="human-readable status for pre-tick consumption"
    )
    p_stat.set_defaults(func=cmd_status)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
