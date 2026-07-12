"""Causal-variable compiler: substrate-neutral kernel (GP-250 finding 10).

Given a stream of observations exposed through an ADAPTER interface
{objects(), transitions(), collisions()}, compiles:

  (1) TYPED CAUSAL VARIABLES — quotients of raw observations that are
      predictive (value changes correlate with transition differences) and
      intervention-addressable (an action exists whose effect depends on them).

  (2) INVARIANCES — candidate conservation/symmetry statements with support.

  (3) INTERVENTION PROPOSALS — for each variable with weak support, the
      falsification experiment that would strengthen or refute it.

Output: workspace/causal_objects.jsonl  schema=ztare.causal_objects.v1

PROMOTION-GATED: all objects carry status=candidate; nothing here holds
authority until a gate/receipt validates. The validation seam is named below
(CausalObjectLedger.promote) but not built — v2 gate.

No LLM calls. Deterministic. If predictive_support cannot be computed cheaply,
the variable is emitted with status=unscored and a reason string.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Iterator, Protocol, Sequence


# ---------------------------------------------------------------------------
# Adapter protocol — substrate-neutral interface
# ---------------------------------------------------------------------------

class CausalAdapter(Protocol):
    """Substrate-neutral observation interface consumed by the kernel.

    Each method is called once per compile; implementations may cache.
    """

    def objects(self) -> "list[dict[str, Any]]":
        """Per-frame object descriptors.

        Each entry: {"frame_id": int, "object_id": str, "features": dict}
        where features are scalar-valued properties of the object in that frame.
        """
        ...

    def transitions(self) -> "list[dict[str, Any]]":
        """Episode transition rows.

        Each entry: {"t": int, "a": int, "features_before": dict,
                     "features_after": dict, "source_ref": str}
        features are summary statistics of the full state at that step,
        keyed by variable name.
        """
        ...

    def collisions(self) -> "list[dict[str, Any]]":
        """Groups of transitions sharing identical (s, a, t) hash.

        Each entry: {"group_key": str, "count": int, "refs": list[str]}
        Used to detect determinism violations or action-conflated variables.
        """
        ...


# ---------------------------------------------------------------------------
# Output schema
# ---------------------------------------------------------------------------

@dataclass
class CausalVariable:
    variable_id: str
    quotient_description: str
    evidence_refs: list[str]
    predictive_support: "float | None"  # None = unscored
    addressable_support: "float | None"  # None = unscored
    status: str = "candidate"  # always candidate until external gate promotes
    unscored_reason: str = ""

    def to_dict(self) -> dict:
        d = asdict(self)
        d["schema"] = "ztare.causal_objects.v1"
        d["object_type"] = "causal_variable"
        return d


@dataclass
class Invariance:
    invariance_id: str
    description: str
    evidence_refs: list[str]
    support_count: int
    status: str = "candidate"

    def to_dict(self) -> dict:
        d = asdict(self)
        d["schema"] = "ztare.causal_objects.v1"
        d["object_type"] = "invariance"
        return d


@dataclass
class InterventionProposal:
    variable_id: str
    description: str
    falsification_test: str
    motivation: str  # why this variable needs strengthening

    def to_dict(self) -> dict:
        d = asdict(self)
        d["schema"] = "ztare.causal_objects.v1"
        d["object_type"] = "intervention_proposal"
        return d


# ---------------------------------------------------------------------------
# Ledger
# ---------------------------------------------------------------------------

class CausalObjectLedger:
    """Accumulates compiler output; writes workspace/causal_objects.jsonl.

    Promotion seam: promote(variable_id, receipt_ref) is the v2 gate entry
    point — a receipt-bearing external validator sets status=validated.
    Not built: v1 emits only candidates.
    """

    def __init__(self) -> None:
        self.variables: list[CausalVariable] = []
        self.invariances: list[Invariance] = []
        self.proposals: list[InterventionProposal] = []

    def add_variable(self, v: CausalVariable) -> None:
        self.variables.append(v)

    def add_invariance(self, inv: Invariance) -> None:
        self.invariances.append(inv)

    def add_proposal(self, p: InterventionProposal) -> None:
        self.proposals.append(p)

    def promote(self, variable_id: str, receipt_ref: str) -> None:
        """Validation seam (v2 gate). Sets status=validated for the variable.

        ponytail: stub only; caller must supply a real receipt; no gate logic built.
        """
        for v in self.variables:
            if v.variable_id == variable_id:
                v.status = "validated"
                if receipt_ref not in v.evidence_refs:
                    v.evidence_refs.append(receipt_ref)
                return
        raise KeyError(f"variable_id not found: {variable_id}")

    def write_jsonl(self, path: "Path | str") -> Path:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("w") as f:
            for v in self.variables:
                f.write(json.dumps(v.to_dict()) + "\n")
            for inv in self.invariances:
                f.write(json.dumps(inv.to_dict()) + "\n")
            for prop in self.proposals:
                f.write(json.dumps(prop.to_dict()) + "\n")
        return p

    def content_hash(self) -> str:
        payload = json.dumps(
            [v.to_dict() for v in self.variables]
            + [i.to_dict() for i in self.invariances]
            + [p.to_dict() for p in self.proposals],
            separators=(",", ":"), sort_keys=True,
        ).encode()
        return hashlib.sha256(payload).hexdigest()[:16]


# ---------------------------------------------------------------------------
# Kernel
# ---------------------------------------------------------------------------

# Minimum transitions to attempt predictive scoring (below = unscored)
_MIN_TRANSITIONS_FOR_SCORING = 4

# Fraction of actions that must show value-correlated transitions to call
# a variable "addressable" (weak threshold — v1 conservative)
_ADDRESSABILITY_THRESHOLD = 0.5


def _predictive_support(
    transitions: "list[dict]",
    feature_key: str,
) -> "tuple[float | None, str]":
    """Pearson-free predictive-support proxy: fraction of transitions where
    feature_key value differs between before/after (directional change rate).

    Returns (score, reason_if_unscored). Score=None means unscored.
    """
    if len(transitions) < _MIN_TRANSITIONS_FOR_SCORING:
        return None, f"only {len(transitions)} transitions < min {_MIN_TRANSITIONS_FOR_SCORING}"
    changed = sum(
        1 for tr in transitions
        if tr.get("features_before", {}).get(feature_key)
        != tr.get("features_after", {}).get(feature_key)
    )
    return changed / len(transitions), ""


def _addressable_support(
    transitions: "list[dict]",
    feature_key: str,
) -> "tuple[float | None, str]":
    """Addressability proxy: among actions that produce a value change in
    feature_key, what fraction of unique action codes are represented?

    A variable is addressable if at least one action reliably changes it
    *differently* from others. We use: max_action_change_rate - min_action_change_rate.
    A pure background drift would score ~0; an action-gated variable scores high.
    """
    if len(transitions) < _MIN_TRANSITIONS_FOR_SCORING:
        return None, f"only {len(transitions)} transitions < min {_MIN_TRANSITIONS_FOR_SCORING}"

    # group change events by action
    by_action: dict[int, list[bool]] = defaultdict(list)
    for tr in transitions:
        changed = (
            tr.get("features_before", {}).get(feature_key)
            != tr.get("features_after", {}).get(feature_key)
        )
        by_action[tr["a"]].append(changed)

    if not by_action:
        return None, "no action labels in transitions"

    rates = {a: sum(v) / len(v) for a, v in by_action.items()}
    if len(rates) < 2:
        # Only one action observed — can't compare
        return rates[next(iter(rates))], ""

    spread = max(rates.values()) - min(rates.values())
    return spread, ""


def _compile_variables(
    adapter: CausalAdapter,
    max_variables: int,
) -> "tuple[list[CausalVariable], list[InterventionProposal]]":
    """Core loop: for each feature key exposed by the adapter, score and
    decide whether to emit as a causal variable."""
    transitions = adapter.transitions()
    if not transitions:
        return [], []

    # Collect all feature keys across all transitions
    all_keys: set[str] = set()
    for tr in transitions:
        all_keys.update(tr.get("features_before", {}).keys())
        all_keys.update(tr.get("features_after", {}).keys())

    # Collect evidence refs from transitions
    all_refs = list({tr.get("source_ref", "") for tr in transitions if tr.get("source_ref")})

    variables: list[CausalVariable] = []
    proposals: list[InterventionProposal] = []

    for key in sorted(all_keys):  # sorted for determinism
        pred_score, pred_reason = _predictive_support(transitions, key)
        addr_score, addr_reason = _addressable_support(transitions, key)

        unscored_reason = "; ".join(r for r in [pred_reason, addr_reason] if r)

        if pred_score is not None and pred_score == 0.0:
            # Non-predictive: never changes — exclude entirely
            continue

        # Build per-variable evidence refs
        var_refs = [r for r in all_refs]

        vid = f"var_{key}"
        status = "unscored" if unscored_reason else "candidate"

        var = CausalVariable(
            variable_id=vid,
            quotient_description=key,
            evidence_refs=var_refs,
            predictive_support=pred_score,
            addressable_support=addr_score,
            status=status,
            unscored_reason=unscored_reason,
        )
        variables.append(var)

        # Emit intervention proposal for weak or unscored addressability
        needs_proposal = (
            addr_score is None
            or (isinstance(addr_score, float) and addr_score < _ADDRESSABILITY_THRESHOLD)
        )
        if needs_proposal:
            proposals.append(InterventionProposal(
                variable_id=vid,
                description=(
                    f"Test whether '{key}' is action-addressable by holding all other "
                    f"features constant and exhausting the action space."
                ),
                falsification_test=(
                    f"Run N pairs of transitions at identical states; vary only action. "
                    f"If '{key}' changes at the same rate across all actions, "
                    f"it is not addressable — demote to invariance or background."
                ),
                motivation=(
                    f"addressable_support={addr_score!r} ({addr_reason or 'below threshold'}); "
                    f"predictive_support={pred_score!r}"
                ),
            ))

    # Cap and sort by predictive_support descending (scored first)
    def sort_key(v: CausalVariable) -> float:
        if v.predictive_support is None:
            return -1.0
        return v.predictive_support

    variables.sort(key=sort_key, reverse=True)
    return variables[:max_variables], proposals


def _compile_invariances(
    adapter: CausalAdapter,
) -> "list[Invariance]":
    """Detect candidate conservation statements.

    For each scalar feature, check whether its value never changes across all
    observed transitions — conservative: only emits if support_count >= 2.
    Also checks cross-frame object counts for constant-count conservation.
    """
    transitions = adapter.transitions()
    if not transitions:
        return []

    # Collect all feature keys
    all_keys: set[str] = set()
    for tr in transitions:
        all_keys.update(tr.get("features_before", {}).keys())

    all_refs = list({tr.get("source_ref", "") for tr in transitions if tr.get("source_ref")})

    invariances: list[Invariance] = []
    for key in sorted(all_keys):
        unchanging = [
            tr for tr in transitions
            if tr.get("features_before", {}).get(key) == tr.get("features_after", {}).get(key)
            and tr.get("features_before", {}).get(key) is not None
        ]
        if len(unchanging) >= 2 and len(unchanging) == len(transitions):
            invariances.append(Invariance(
                invariance_id=f"inv_conserved_{key}",
                description=f"Feature '{key}' is conserved across all {len(unchanging)} transitions.",
                evidence_refs=all_refs,
                support_count=len(unchanging),
            ))

    # Object count conservation via objects()
    objects = adapter.objects()
    if objects:
        frames: dict[int, int] = Counter(obj["frame_id"] for obj in objects)
        counts = list(frames.values())
        if counts and len(set(counts)) == 1 and len(counts) >= 2:
            invariances.append(Invariance(
                invariance_id="inv_object_count_conserved",
                description=(
                    f"Object count is constant at {counts[0]} across all "
                    f"{len(counts)} observed frames."
                ),
                evidence_refs=all_refs,
                support_count=len(counts),
            ))

    return invariances


def compile_causal_objects(
    adapter: CausalAdapter,
    *,
    max_variables: int = 20,
) -> CausalObjectLedger:
    """Main kernel entry point.

    Deterministic. No LLM calls. Returns a populated CausalObjectLedger
    with status=candidate on all objects.
    """
    ledger = CausalObjectLedger()

    variables, proposals = _compile_variables(adapter, max_variables)
    for v in variables:
        ledger.add_variable(v)
    for p in proposals:
        ledger.add_proposal(p)

    for inv in _compile_invariances(adapter):
        ledger.add_invariance(inv)

    return ledger


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def _cli() -> None:
    import argparse
    import sys

    parser = argparse.ArgumentParser(
        description="Causal-variable compiler — substrate-neutral kernel."
    )
    parser.add_argument("--project", required=True, help="Project directory path")
    parser.add_argument("--adapter", required=True, choices=["worldmodel"],
                        help="Adapter type to use")
    parser.add_argument("--max-variables", type=int, default=20,
                        help="Cap on emitted causal variables")
    args = parser.parse_args()

    project_dir = Path(args.project).resolve()
    if not project_dir.is_dir():
        print(f"ERROR: project dir not found: {project_dir}", file=sys.stderr)
        sys.exit(1)

    if args.adapter == "worldmodel":
        from ztare.worldmodel.causal_compiler_adapter import WorldmodelAdapter
        adapter = WorldmodelAdapter(project_dir)
    else:
        print(f"ERROR: unknown adapter: {args.adapter}", file=sys.stderr)
        sys.exit(1)

    ledger = compile_causal_objects(adapter, max_variables=args.max_variables)

    out_path = project_dir / "workspace" / "causal_objects.jsonl"
    ledger.write_jsonl(out_path)

    print(f"Compiled {len(ledger.variables)} variables, "
          f"{len(ledger.invariances)} invariances, "
          f"{len(ledger.proposals)} proposals → {out_path}")

    if ledger.variables:
        print("\nTop compiled variables:")
        for v in ledger.variables[:5]:
            print(f"  {v.variable_id}: pred={v.predictive_support!r} "
                  f"addr={v.addressable_support!r} status={v.status}")

    if ledger.proposals:
        print(f"\nFirst intervention proposal:")
        p = ledger.proposals[0]
        print(f"  variable_id: {p.variable_id}")
        print(f"  falsification_test: {p.falsification_test}")


if __name__ == "__main__":
    _cli()
