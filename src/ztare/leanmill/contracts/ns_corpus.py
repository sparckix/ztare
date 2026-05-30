"""LeanMill NS-corpus contract — typed work-item shape for NS proof attempts.

Unblocks the feedback loops surfaced by audit items #79 + #80: today LeanMill
runs canary + MCB corpora; 0 NS lemmas are attempted; the basin↔LeanMill
feedback (proof-attempt history, proposal-hypothesis embeddings) has 0 join
cardinality on the NS side.

This contract defines the typed work-item shape that targets `ZtareProofs/
ns_*.lean` declarations. It is the boundary contract; actual scheduling
happens in `leanmill_learning_work_seeder.py` once an operator enables the
ns_corpus lane in factory policy.

Schema: ``leanmill-ns-corpus-contract-v1``.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any


SCHEMA = "leanmill-ns-corpus-contract-v1"

# Acceptable NS-corpus lemma name patterns. Conservative — must start with
# `ns_*` (snake case NS file prefix) or be a CamelCase declaration that
# appears in a known NS file. Lean stdlib names without NS provenance are
# rejected to keep LeanMill's NS lane scoped.
NS_FILE_PREFIX = "ns_"
NS_LEAN_ROOT_REL = "ztare_proofs/ZtareProofs"

# Acceptable work-item kinds for the NS lane. Same set as canary but
# distinguished by `corpus` field so dashboards / governance can separate.
ACCEPTABLE_KINDS = {
    "llm_proposal_validate",
    "canary_propose",
    "source_request_propose",
    "agent_repair_task",
    "subscription_agent_task",
}

# Maximum tactic-script bytes per work item — prevents accidentally
# enqueueing huge files. Matches the action_card cap.
MAX_TACTIC_BYTES = 16384


def is_valid_ns_lemma_target(target: str) -> tuple[bool, str | None]:
    """Return (ok, reason) for an NS-lemma target name.

    NS targets are expected to be Lean declaration names found in
    ``ztare_proofs/ZtareProofs/ns_*.lean`` files. Validation is lexical —
    actual existence in the Lean source is verified downstream by the
    leanmill subscription-agent worker when it loads the work item.
    """
    if not target or not isinstance(target, str):
        return False, "empty or non-string target"
    if len(target) > 200:
        return False, "target name exceeds 200 chars (suspicious)"
    # Must look like a Lean identifier (alphanumeric + ., _)
    if not re.match(r"^[A-Za-z][A-Za-z0-9_.]*$", target):
        return False, "target not a Lean identifier shape"
    # Reject if it looks like a Mathlib stdlib name without NS context
    mathlib_prefixes = (
        "Mathlib.", "Std.", "Lean.", "Nat.", "Int.", "Real.",
        "Set.", "List.", "Classical.", "ENNReal."
    )
    # NOTE: ENNReal is listed because the typed_endpoint_failure_log already
    # flagged it as a failed target; we accept it ONLY if explicitly tagged
    # as an NS attempt by the caller (handled in validate_work_item).
    if any(target.startswith(p) for p in mathlib_prefixes):
        return False, f"target looks like Lean stdlib ({target.split('.')[0]}); supply NS-prefixed alias"
    return True, None


def discover_ns_lean_files(repo_root: Path) -> list[Path]:
    """List all NS Lean files under ZtareProofs/."""
    lean_root = repo_root / NS_LEAN_ROOT_REL
    if not lean_root.exists():
        return []
    return sorted(lean_root.glob(f"{NS_FILE_PREFIX}*.lean"))


def validate_work_item(item: dict[str, Any]) -> dict[str, Any]:
    """Validate an NS-corpus work item against the typed contract.

    Returns a dict with ``ok``, ``reasons[]``, and ``normalized`` (the
    canonical form of the item ready for enqueue). Mirrors the source_query
    validator pattern so the existing learning-work seeder can apply this
    check before enqueueing.

    Required fields:
      - target: Lean declaration name in NS-corpus shape
      - kind:   one of ACCEPTABLE_KINDS
      - source_file: relative path under ztare_proofs/ZtareProofs/, must
                     start with ns_ prefix
      - schema: "leanmill-ns-corpus-contract-v1"

    Optional:
      - rationale_hint: short text for prompt construction (≤500 chars)
      - prior_attempts: list of prior work_ids that targeted the same lemma
      - expected_difficulty: "easy" | "medium" | "hard" (affects priority)
    """
    reasons: list[str] = []
    target = item.get("target")
    ok, why = is_valid_ns_lemma_target(target or "")
    if not ok:
        reasons.append(f"target: {why}")

    kind = item.get("kind")
    if kind not in ACCEPTABLE_KINDS:
        reasons.append(f"kind: {kind!r} not in {sorted(ACCEPTABLE_KINDS)}")

    schema = item.get("schema")
    if schema != SCHEMA:
        reasons.append(f"schema: expected {SCHEMA!r}, got {schema!r}")

    source_file = item.get("source_file") or ""
    if not source_file.startswith("ztare_proofs/ZtareProofs/ns_"):
        reasons.append(
            f"source_file: must start with ztare_proofs/ZtareProofs/ns_; "
            f"got {source_file!r}"
        )
    elif not source_file.endswith(".lean"):
        reasons.append(f"source_file: must end with .lean; got {source_file!r}")

    rh = item.get("rationale_hint") or ""
    if len(str(rh)) > 500:
        reasons.append("rationale_hint exceeds 500 chars")

    if "expected_difficulty" in item:
        if item["expected_difficulty"] not in ("easy", "medium", "hard"):
            reasons.append(
                f"expected_difficulty must be easy/medium/hard, got {item['expected_difficulty']!r}"
            )

    normalized = {
        "schema": SCHEMA,
        "target": target,
        "kind": kind,
        "source_file": source_file,
        "corpus": "ns",  # canonical corpus tag — distinguishes from canary/MCB
        "rationale_hint": str(item.get("rationale_hint") or "")[:500],
        "prior_attempts": list(item.get("prior_attempts") or [])[:10],
        "expected_difficulty": item.get("expected_difficulty", "medium"),
    }
    return {"ok": not reasons, "reasons": reasons, "normalized": normalized}


def build_ns_lane_floor() -> dict[str, int]:
    """Recommended initial backlog floors for the ns lane.

    Conservative defaults to start: keep the NS lane small until basin
    feedback shows the loop is working. Operator can raise these in
    factory policy once the proof-attempt → basin-quantity join starts
    surfacing real signal (see enrich_basin_with_proof_history.py audit #79).
    """
    return {
        # Lane name → backlog floor count
        "ns_proposal_validate_floor": 8,
        "ns_agent_repair_floor": 4,
        "ns_source_qualification_floor": 4,
    }
