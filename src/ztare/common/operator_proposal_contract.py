"""Kernel contract for automated OPERATOR PROPOSAL cards (grammar-ceiling triage).

Every autoresearch substrate has a hypothesis language with an expressivity
ceiling. When the residual is irreducible under the current family/catalog, the
SYSTEM (not the human conductor) should propose a NEW operator — as a
FALSIFIABLE card: evidence indices, per-family failure proofs, and a planted-
synthetic acceptance test. This is the DreamCoder / library-learning move (grow
the DSL from residual compression) with the falsifiability discipline those
systems lack.

Four in-house instances share this shape and independently reinvent it:
  * worldmodel operator catalog (grammar-ceiling residual);
  * fit function families (GP-045 cold-residual = "no family reduces this");
  * leanmill lemma/tactic families;
  * deai self-improving tell taxonomy (its candidates-harvest loop IS this).
Four instances => the CONTRACT is kernel-level. Each substrate plugs in its own
residual clusterer, family-failure checks, and acceptance harness — the same
alpha/gamma split as ``ztare.common.abstraction_functor``: the kernel owns the
card shape, dispositions, persistence, and validation; only the three plug-in
methods instantiate per substrate.

Card shape (JSON-able)::

    {"schema": <substrate schema string>,
     "failure_family": <cluster signature (the dedup key)>,
     "failure_family_sha": <sha256 of failure_family>,
     "evidence_indices": [<residual transition/row indices>],
     "spatial_footprint": <substrate-defined stats dict>,
     "why_existing_ops_fail": {<family>: <one-line deterministic check result>},
     "proposed_operator_sketch": <name + param shape (heuristic)>,
     "acceptance_test": <planted-synthetic falsification recipe>,
     "disposition": "open" | "accepted" | "rejected"}

The conductor validates a card via its acceptance_test and sets a disposition;
until then the card is ``open`` and briefs the mutator as a grammar-ceiling
signal.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

DEFAULT_SCHEMA = "operator-proposal-v1"

# Default rules path: four levels up from this module lands at repo root.
_MACHINERY_RULES_PATH = Path(__file__).parent.parent.parent.parent / "MACHINERY_RULES.md"

REQUIRED_CARD_FIELDS = (
    "schema",
    "failure_family",
    "evidence_indices",
    "spatial_footprint",
    "why_existing_ops_fail",
    "proposed_operator_sketch",
    "acceptance_test",
)

DISPOSITION_OPEN = "open"
DISPOSITION_ACCEPTED = "accepted"
DISPOSITION_REJECTED = "rejected"
_CLOSED = (DISPOSITION_ACCEPTED, DISPOSITION_REJECTED)


def family_sha(failure_family: Any) -> str:
    """Stable dedup key: sha256 of the failure-family signature string."""
    return hashlib.sha256(str(failure_family).encode()).hexdigest()


def operator_proposal_card(
    *,
    failure_family: Any,
    evidence_indices: list,
    spatial_footprint: dict,
    why_existing_ops_fail: dict,
    proposed_operator_sketch: str,
    acceptance_test: str,
    schema: str = DEFAULT_SCHEMA,
    disposition: str = DISPOSITION_OPEN,
) -> dict:
    """Assemble one proposal card. Substrate-agnostic: the clusterer names the
    family, the family-failure checks fill ``why_existing_ops_fail``, and the
    acceptance harness fills ``acceptance_test``; this only fixes the shape and
    attaches the dedup sha + disposition."""
    return {
        "schema": str(schema),
        "failure_family": failure_family,
        "failure_family_sha": family_sha(failure_family),
        "evidence_indices": list(evidence_indices),
        "spatial_footprint": dict(spatial_footprint),
        "why_existing_ops_fail": dict(why_existing_ops_fail),
        "proposed_operator_sketch": str(proposed_operator_sketch),
        "acceptance_test": str(acceptance_test),
        "disposition": str(disposition),
    }


def validate_operator_proposal_card(card: Any) -> dict:
    """Contract/IR gate on card SHAPE (not on whether the operator is real —
    that is the acceptance_test's job). Mirrors leanmill action_card.validate."""
    failures: list[dict] = []
    if not isinstance(card, dict):
        return {"schema": "operator-proposal-validation-v1", "status": "fail",
                "failures": [{"failure": "missing_card"}]}
    for f in REQUIRED_CARD_FIELDS:
        if card.get(f) in (None, "", [], {}):
            failures.append({"failure": f"missing_{f}"})
    if not isinstance(card.get("evidence_indices"), list) or not card.get("evidence_indices"):
        failures.append({"failure": "evidence_indices_not_nonempty_list"})
    wef = card.get("why_existing_ops_fail")
    if not isinstance(wef, dict) or not wef:
        failures.append({"failure": "why_existing_ops_fail_not_nonempty_dict"})
    elif not all(isinstance(v, str) and v for v in wef.values()):
        failures.append({"failure": "why_existing_ops_fail_values_not_strings"})
    return {"schema": "operator-proposal-validation-v1",
            "status": "pass" if not failures else "fail", "failures": failures}


def is_open(card: dict) -> bool:
    return str(card.get("disposition", DISPOSITION_OPEN)) not in _CLOSED


def set_disposition(card: dict, disposition: str) -> dict:
    out = dict(card)
    out["disposition"] = str(disposition)
    return out


def write_proposal_cards(path: "Path | str", cards: list[dict]) -> list[dict]:
    """Append cards to a JSONL ledger, DEDUP by failure_family sha (across the
    existing ledger and within this batch). Returns the rows actually written."""
    p = Path(path)
    seen: set[str] = set()
    if p.exists():
        for line in p.read_text().splitlines():
            if not line.strip():
                continue
            try:
                seen.add(str(json.loads(line).get("failure_family_sha")))
            except Exception:  # noqa: BLE001 — a corrupt row never blocks writes
                continue
    written: list[dict] = []
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a") as f:
        for card in cards:
            sha = card.get("failure_family_sha") or family_sha(card.get("failure_family"))
            if sha in seen:
                continue
            seen.add(sha)
            row = dict(card)
            row["failure_family_sha"] = sha
            row.setdefault("disposition", DISPOSITION_OPEN)
            f.write(json.dumps(row) + "\n")
            written.append(row)
    return written


def open_cards(path: "Path | str") -> list[dict]:
    """Undispositioned cards from a ledger (the mutator-facing grammar-ceiling
    evidence). Missing ledger -> empty."""
    p = Path(path)
    if not p.exists():
        return []
    latest: dict[str, dict] = {}
    order: list[str] = []
    for line in p.read_text().splitlines():
        if not line.strip():
            continue
        try:
            d = json.loads(line)
        except Exception:  # noqa: BLE001
            continue
        if not isinstance(d, dict):
            continue
        sha = d.get("failure_family_sha")
        if not sha:
            failure_family = d.get("failure_family")
            if failure_family in (None, ""):
                continue
            sha = family_sha(failure_family)
            d["failure_family_sha"] = sha
        sha = str(sha)
        if sha not in latest:
            order.append(sha)
        latest[sha] = d
    return [latest[sha] for sha in order if is_open(latest[sha])]


def record_disposition(path: "Path | str", card: dict,
                       *, attestation: "dict | None" = None) -> dict:
    """UPSERT a dispositioned card by failure_family sha: rewrite the matching
    ledger row in place (or append if absent). One row per family — the same
    dedup key `write_proposal_cards` uses, so an accepted/rejected disposition
    supersedes the open card instead of duplicating it.

    If ``attestation`` is supplied (the inner dict from ``attest()``), it is
    persisted on the same ledger line under the key ``"attestation"`` (Rule 6,
    I3: Attestation — cognitive-firm/draft.md §3).
    """
    p = Path(path)
    sha = card.get("failure_family_sha") or family_sha(card.get("failure_family"))
    row = dict(card)
    row["failure_family_sha"] = sha
    if attestation is not None:
        row["attestation"] = dict(attestation)
    rows: list[dict] = []
    replaced = False
    if p.exists():
        for line in p.read_text().splitlines():
            if not line.strip():
                continue
            try:
                d = json.loads(line)
            except Exception:  # noqa: BLE001 — a corrupt row never blocks the upsert
                continue
            if str(d.get("failure_family_sha")) == sha:
                rows.append(row)
                replaced = True
            else:
                rows.append(d)
    if not replaced:
        rows.append(row)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("".join(json.dumps(r) + "\n" for r in rows))
    return row


def attest(card: dict, outcome: str, principal: str, ts: str, suite: str,
           rules_path: "Path | str | None" = None) -> dict:
    """I3: principal-signed, machine-verifiable run attestation (cognitive-firm/draft.md §3).

    Returns {"attestation": {card_sha, outcome, principal, rules_sha, suite, ts}}.
    rules_sha is the first 16 hex digits of sha256(rules file); empty string if the
    file is absent.  Liability for a wrong verdict remains an open institutional
    problem per the paper ("Attestation and Liability").
    """
    rp = Path(rules_path) if rules_path is not None else _MACHINERY_RULES_PATH
    rules_sha = ""
    if rp.exists():
        rules_sha = hashlib.sha256(rp.read_bytes()).hexdigest()[:16]
    return {
        "attestation": {
            "card_sha": family_sha(card.get("failure_family", "")),
            "outcome": str(outcome),
            "principal": str(principal),
            "rules_sha": rules_sha,
            "suite": str(suite),
            "ts": str(ts),
        }
    }


def implement_and_validate(card: dict, leaf_runner, harness,
                           ledger: "Path | str | None" = None) -> dict:
    """Pure orchestration of one proposal card through a sealed leaf and the
    substrate harness. ``leaf_runner(card)`` returns a proposed artifact (a
    patch/spec, opaque to the kernel — leaf sealing is the runner's problem).
    ``harness(artifact)`` is the substrate ACCEPTANCE gate and returns
    ``{"accepted": bool, "receipt": str, "counterexample": str|None}``.

    Accept -> disposition ``accepted`` + the receipt; reject -> ``rejected`` +
    the counterexample. The dispositioned card is returned and, if ``ledger`` is
    given, persisted (upsert by family sha, superseding the open row)."""
    artifact = leaf_runner(card)
    verdict = harness(artifact)
    accepted = bool(verdict.get("accepted"))
    out = set_disposition(card, DISPOSITION_ACCEPTED if accepted else DISPOSITION_REJECTED)
    if accepted:
        out["receipt"] = str(verdict.get("receipt", ""))
    else:
        out["counterexample"] = str(verdict.get("counterexample", ""))
    if ledger is not None:
        record_disposition(ledger, out)
    return out


@runtime_checkable
class OperatorProposalSubstrate(Protocol):
    """The per-substrate plug-in seam (alpha/gamma split). A substrate supplies:

      * ``cluster_residual`` — group the residual (transitions/rows the current
        model mispredicts) by diff signature into clusters;
      * ``family_failures`` — for each EXISTING operator family, a one-line
        deterministic proof that it cannot explain the cluster;
      * ``acceptance_test`` — the planted-synthetic falsification recipe that
        the conductor runs to accept/reject the proposed operator.

    ``propose(...)`` (kernel-provided default) wires these into cards."""

    def cluster_residual(self, evidence, model, residual_indices) -> list[dict]: ...
    def family_failures(self, cluster) -> dict: ...
    def acceptance_test(self, cluster) -> str: ...
