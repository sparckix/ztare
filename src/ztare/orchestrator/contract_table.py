"""GP-157 v5.0 Layer 1 — typed substrate-ABI contract table.

Per panel synthesis (2026-04-25, recorded in
GP-157 seam): the apparatus has had three concurrent test_model.py
contracts (A/B/C) with five sources of contradiction taught to the
mutator. The fix is a single-source-of-truth table mapping each
substrate class to ONE `ContractSpec` — same discipline as the Linux
syscall table.

This module is the **table**; companion modules are:
  - `protocols.py`            — runtime-checkable PEP 544 Protocols
  - `render_evidence_template.py` — generate evidence.txt §D from spec

Adding a substrate class = adding one entry here. evidence.txt blocks,
prompt hints, adherence checks all consume the table; none re-defines
the contract independently.

The table does NOT replace `prompt.py` / `contract_adherence.py` /
`mutation_suite_guard.py` in this commit. That deletion lands after
the next-10-substrates telemetry validates the design (per panel L2/L3
gating). Until then, this is the additive foundation.
"""

from __future__ import annotations

import inspect
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Mapping, Optional


class SubstrateABI(Enum):
    """Stable enumeration of mutator-apparatus interface ABIs.

    Per Linux kernel discipline: monotonic numbering, never renumbered.
    Adding a new ABI appends a new value. Removing/renaming is a
    breaking change requiring DECISION_LOG entry + substrate migration.
    """

    SCALAR_1D = 1
    """`def I_model(d: float, params: Mapping | None = None) -> float`.
    Used by 1D substrates with authored test_model.py: gp159, gp160,
    gp161, gp145, gp146 family. cage_meta.class = '1d'."""

    FEATURE_DICT = 2
    """`def I_model(features: Mapping[str, Any]) -> float`. Used by
    nd_features substrates: gp154 family. cage_meta.class = 'nd_features'.
    Substrate must export visible_rows() / holdout_rows() in features.py."""

    DISCRIMINATOR = 3
    """Legacy assert-based discriminator suite. No I_model contract.
    Substrate runs `python test_model.py` directly; asserts are the
    contract. Used by gp145_saw_mu_square family (closed_form_constant).
    cage_meta.class = 'closed_form_constant'."""

    LEAN_PROOF = 4
    """Lean theorem proof obligations. Mutator emits Lean tactics, not
    Python. Used by GP-122 / GP-139 substrates. cage_meta.class = 'proof_target'."""


@dataclass(frozen=True)
class ContractSpec:
    """Frozen specification for one ABI.

    Immutable after construction; substrate registration writes once
    into CONTRACT_REGISTRY and never mutates.
    """

    abi: SubstrateABI
    """Stable ABI identifier (Linux syscall-table analogue)."""

    signature_str: str
    """Human-readable signature for evidence-template rendering. The
    actual runtime-checkable shape lives in `protocols.py`."""

    docstring: str
    """One-paragraph description of the contract's purpose. Rendered
    into evidence.txt §D and prompt-hint blocks."""

    required_module_globals: tuple[str, ...] = ()
    """Module-level identifiers the apparatus expects in test_model.py
    (e.g. ('MODEL_PARAMS', 'VISIBLE_SET', 'HOLDOUT_SET') for SCALAR_1D)."""

    nullable_feature_keys: frozenset[str] = field(default_factory=frozenset)
    """Gap #2 (panel Failure Mode 2 — over-constrained schemas):
    feature keys that may legitimately be None for some rows because
    the underlying physical quantity does not apply (e.g.
    `intrinsic_dim_d=None` for LLM substrates where intrinsic
    dimension is undefined; gp154 hit this on 80/82 rows).

    Schema validation must NOT reject substrates with these keys
    missing on a subset of rows. The fit engine maps None to its
    declared asymptotic limit (typically infinity for dimensionality
    parameters, zero for noise scales) before passing to scipy.

    Empty set means: every declared key is mandatory on every row.
    Use this set sparingly — silent missing data is harder to debug
    than explicit asymptotic limits."""

    nullable_asymptotic_limits: dict = field(default_factory=dict)
    """For each key in nullable_feature_keys, the asymptotic limit
    used when the field is None. E.g. {'intrinsic_dim_d': float('inf')}
    means missing intrinsic dimension is treated as d=∞ (LLM
    embedding-space limit). Key must appear in nullable_feature_keys."""

    required_filesystem_caps: frozenset[str] = field(default_factory=frozenset)
    """Filesystem capabilities the substrate must provide. Checked at
    seal time by verify_class_consistency_with_substrate. E.g.
    'features.py' for FEATURE_DICT, '*.lean OR Lean references in evidence'
    for LEAN_PROOF."""

    forbidden_module_patterns: tuple[str, ...] = ()
    """Patterns that, if present at module scope, are contract violations.
    E.g. 'I_model(' for SCALAR_1D + FEATURE_DICT (module-level call
    crashes import when MODEL_PARAMS is empty)."""

    skeleton_template: str = ""
    """Canonical code skeleton the mutator should copy. Rendered into
    evidence.txt §D. Single source of truth — no other prompt block
    teaches a different shape."""

    @property
    def cage_meta_class(self) -> str:
        """The cage_meta.class value that selects this ABI."""
        return _ABI_TO_CAGE_META_CLASS[self.abi]


# ── ABI ↔ cage_meta.class binding ─────────────────────────────────────────

_ABI_TO_CAGE_META_CLASS: dict[SubstrateABI, str] = {
    SubstrateABI.SCALAR_1D: "1d",
    SubstrateABI.FEATURE_DICT: "nd_features",
    SubstrateABI.DISCRIMINATOR: "closed_form_constant",
    SubstrateABI.LEAN_PROOF: "proof_target",
}

_CAGE_META_CLASS_TO_ABI: dict[str, SubstrateABI] = {
    v: k for k, v in _ABI_TO_CAGE_META_CLASS.items()
}


# ── Canonical skeletons (single source of truth) ──────────────────────────

_SCALAR_1D_SKELETON = '''import math
from typing import Optional, Mapping

# Module-level constants. The apparatus IMPORTS test_model.py at gate-time;
# whatever is at module scope runs at import. Do not call I_model at module
# scope — MODEL_PARAMS is empty here.
MODEL_PARAMS: dict = {}

VISIBLE_SET = [...]   # apparatus / scaffold provides
HOLDOUT_SET = [...]


def I_model(d: float, params: Optional[Mapping[str, float]] = None) -> float:
    """Scalar prediction. d is a float; params is a dict OR None.
    Use p.get(name, default) for every read so this works in BOTH
    the empty (MODEL_PARAMS={}) and post-fit states. Return one
    finite float — never NaN, never inf, never a list/dict/None.
    """
    p = params if params is not None else MODEL_PARAMS
    a = p.get("a", 1.0)
    b = p.get("b", 0.0)
    return a * d + b   # placeholder — substitute your form
'''

_FEATURE_DICT_SKELETON = '''from typing import Mapping, Any

# features.py is on sys.path and exports visible_rows() / holdout_rows()
# returning [(id, y_observed, features_dict), ...].
from features import visible_rows, holdout_rows

VISIBLE_SET = visible_rows()
HOLDOUT_SET = holdout_rows()
MODEL_PARAMS: dict = {}


def I_model(features: Mapping[str, Any]) -> float:
    """Feature-dict prediction. features is a dict like
    {'log10_N_params': 8.0, 'fit_convention': 'kaplan', ...}.
    Use features.get(key, default) for every read.
    Return one finite float per call.
    """
    x = features.get("log10_N_params", 0.0)
    return -x * 0.07 + 1.5   # placeholder — substitute your form
'''


# ── Contract registry ─────────────────────────────────────────────────────

CONTRACT_REGISTRY: dict[SubstrateABI, ContractSpec] = {
    SubstrateABI.SCALAR_1D: ContractSpec(
        abi=SubstrateABI.SCALAR_1D,
        signature_str="def I_model(d: float, params: Mapping | None = None) -> float",
        docstring=(
            "Scalar 1D prediction. The apparatus imports test_model.py and "
            "calls I_model on each VISIBLE_SET row's `d` value. Visible MRE "
            "drives fitting; holdout MRE gates the score. Both must be finite "
            "floats below the rubric threshold."
        ),
        required_module_globals=("MODEL_PARAMS", "VISIBLE_SET", "HOLDOUT_SET", "I_model"),
        required_filesystem_caps=frozenset(),
        forbidden_module_patterns=("I_model(",),
        skeleton_template=_SCALAR_1D_SKELETON,
    ),
    SubstrateABI.FEATURE_DICT: ContractSpec(
        abi=SubstrateABI.FEATURE_DICT,
        signature_str="def I_model(features: Mapping[str, Any]) -> float",
        docstring=(
            "Feature-dict prediction. The apparatus imports test_model.py and "
            "calls I_model on each row's features dict. Substrate authors "
            "features.py exporting visible_rows() / holdout_rows()."
        ),
        required_module_globals=("MODEL_PARAMS", "VISIBLE_SET", "HOLDOUT_SET", "I_model"),
        # gp154 case: intrinsic_dim_d is undefined for ~80% of rows
        # (LLM substrates have no measurable intrinsic dimension).
        # Schema accepts None there; fit engine maps it to d=∞.
        nullable_feature_keys=frozenset({"intrinsic_dim_d", "noise_scale"}),
        nullable_asymptotic_limits={
            "intrinsic_dim_d": float("inf"),
            "noise_scale": 0.0,
        },
        required_filesystem_caps=frozenset({"features.py"}),
        forbidden_module_patterns=("I_model(",),
        skeleton_template=_FEATURE_DICT_SKELETON,
    ),
    SubstrateABI.DISCRIMINATOR: ContractSpec(
        abi=SubstrateABI.DISCRIMINATOR,
        signature_str="(no I_model — assert-based discriminator suite)",
        docstring=(
            "Legacy assert-based discriminator. The apparatus runs "
            "`python test_model.py` directly; module-level asserts ARE "
            "the contract. No I_model required. Used by closed-form "
            "constant substrates (gp145 family)."
        ),
        required_module_globals=(),
        required_filesystem_caps=frozenset(),
        forbidden_module_patterns=(),
        skeleton_template="",  # legacy substrates author their own
    ),
    SubstrateABI.LEAN_PROOF: ContractSpec(
        abi=SubstrateABI.LEAN_PROOF,
        signature_str="(no I_model — Lean theorem proof obligations)",
        docstring=(
            "Lean proof substrate. Mutator emits Lean tactics, not Python. "
            "The apparatus runs the Lean compiler against the mutator's "
            "submission. Used by GP-122 / GP-139 substrates."
        ),
        required_module_globals=(),
        required_filesystem_caps=frozenset({"*.lean OR Lean references in evidence"}),
        forbidden_module_patterns=(),
        skeleton_template="",
    ),
}


# ── Public API ────────────────────────────────────────────────────────────

def get_spec(abi: SubstrateABI) -> ContractSpec:
    """Return the ContractSpec for an ABI, or raise KeyError if unknown."""
    return CONTRACT_REGISTRY[abi]


def get_spec_by_class(cage_meta_class: str) -> Optional[ContractSpec]:
    """Map cage_meta.class string to ContractSpec, or None when unknown.

    Empty string and unrecognized values return None — caller decides
    whether that's an error or legacy default.
    """
    cls = (cage_meta_class or "").strip().lower()
    abi = _CAGE_META_CLASS_TO_ABI.get(cls)
    if abi is None:
        return None
    return CONTRACT_REGISTRY[abi]


def list_substrate_classes() -> tuple[str, ...]:
    """Return all cage_meta.class values registered in the table.

    Useful for evidence-quality lints + verify_class_consistency_with_substrate
    to know the closed set of valid declarations.
    """
    return tuple(sorted(_CAGE_META_CLASS_TO_ABI.keys()))
