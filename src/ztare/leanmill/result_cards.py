"""Content-bound theorem cards for target-conditioned proof curricula.

A card is a read-only view over one governed closure certificate.  It exposes
the statement and source bindings while keeping proof bytes behind a checked
reference to the frozen certificate-ledger snapshot.  This lets calibration,
conjecturing, and target replay share one theorem identity without creating a
second proof authority.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import argparse
from typing import Any, Mapping, Sequence

from ztare.leanmill.lean_source import (
    extract_signature,
    has_sorry,
    preamble_before_target,
    replace_decl_proof,
    resolve_theorem_target,
    split_at_proof,
    top_level_assign,
)
from ztare.leanmill.theory_ir import content_hash
from ztare.leanmill.solver.closed_artifact import finalized_ratification_eligible


RESULT_CARD_SCHEMA = "leanmill.result_card.v1"
RESULT_CARD_DECK_SCHEMA = "leanmill.result_card_deck.v1"
RESULT_CARD_FREEZE_REQUEST_SCHEMA = "leanmill.result_card_freeze_request.v1"


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def certificate_statement(cert: Mapping[str, Any]) -> str:
    """Extract a proof-free target signature through LeanMill's shared parser."""

    probe = str(cert.get("recompilable_probe") or "")
    target = str(cert.get("target") or "")
    identity = resolve_theorem_target(probe, target)
    if identity is None:
        return ""
    block = probe[identity.decl_start:identity.decl_end]
    _head, proof = split_at_proof(block)
    signature = (extract_signature(probe, identity.qualified_name) or "").strip()
    if (
        not proof.strip()
        or not signature
        or top_level_assign(signature) >= 0
        or has_sorry(signature)
        or re.search(r"(?<![A-Za-z0-9_])(admit|by)(?![A-Za-z0-9_])", signature)
    ):
        return ""
    return signature


def certificate_is_governed(cert: Mapping[str, Any]) -> bool:
    governance = cert.get("governance")
    if not isinstance(governance, Mapping):
        return False
    kernel = governance.get("governance_kernel")
    integrity = governance.get("statement_integrity")
    negative = cert.get("matched_negative_control")
    validation = cert.get("solver_validation")
    receipts = (
        validation.get("receipts")
        if isinstance(validation, Mapping)
        else None
    )
    kernel_compile = (
        receipts.get("kernel_compile_receipt")
        if isinstance(receipts, Mapping)
        else None
    )
    matched_control = (
        receipts.get("matched_negative_control_receipt")
        if isinstance(receipts, Mapping)
        else None
    )
    axiom_allowlist = (
        receipts.get("axiom_allowlist_receipt")
        if isinstance(receipts, Mapping)
        else None
    )
    governance_receipt = (
        receipts.get("governance_kernel_receipt")
        if isinstance(receipts, Mapping)
        else None
    )
    statement = certificate_statement(cert)
    from ztare.leanmill.governed_ratification import normalized_target_signature

    bound_statement = normalized_target_signature(
        str(cert.get("recompilable_probe") or ""),
        str(cert.get("target") or ""),
    )
    statement_hash = sha256_bytes(
        bound_statement.encode("utf-8")
    ) if bound_statement else ""
    return bool(
        cert.get("outcome") == "closed"
        and isinstance(kernel, Mapping)
        and kernel.get("available") is True
        and kernel.get("passed") is True
        and isinstance(integrity, Mapping)
        and integrity.get("ok") is True
        and governance.get("integrity_unverified") is not True
        and isinstance(negative, Mapping)
        and negative.get("available") is True
        and negative.get("passed") is True
        and isinstance(validation, Mapping)
        and finalized_ratification_eligible(dict(validation))
        and validation.get("positive_axiom_receipt_required") is True
        and validation.get("discriminating_mnc_required") is True
        and isinstance(kernel_compile, Mapping)
        and kernel_compile.get("available") is True
        and kernel_compile.get("passed") is True
        and isinstance(matched_control, Mapping)
        and matched_control.get("available") is True
        and matched_control.get("passed") is True
        and isinstance(axiom_allowlist, Mapping)
        and axiom_allowlist.get("available") is True
        and axiom_allowlist.get("passed") is True
        and isinstance(governance_receipt, Mapping)
        and governance_receipt.get("available") is True
        and governance_receipt.get("passed") is True
        and bool(statement_hash)
        and cert.get("posed_target_signature_sha256") == statement_hash
        and cert.get("closed_target_signature_sha256") == statement_hash
    )


def certificate_strength_rank(cert: Mapping[str, Any]) -> tuple[Any, ...]:
    """Order equivalent receipts by usable source and governed byte binding."""

    governance = cert.get("governance")
    carried = (
        isinstance(governance, Mapping)
        and governance.get("probe_match") == "carried_exact_artifact"
    )
    return (
        bool(certificate_statement(cert)),
        certificate_is_governed(cert),
        bool(carried),
        not bool(cert.get("recompilable_probe_reconstructed")),
        bool(cert.get("recompilable_probe_sha256")),
        str(cert.get("ts") or ""),
    )


def _read_frozen_ledger(path: Path) -> list[tuple[int, dict[str, Any]]]:
    rows: list[tuple[int, dict[str, Any]]] = []
    for line_number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not raw.strip():
            continue
        try:
            row = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid certificate JSON at line {line_number}") from exc
        if not isinstance(row, dict):
            raise ValueError(f"certificate line {line_number} is not an object")
        rows.append((line_number, row))
    return rows


def select_certificates(
    ledger_path: Path,
    target_names: Sequence[str],
) -> dict[str, tuple[int, dict[str, Any]]]:
    """Select one strongest governed certificate for every requested identity."""

    wanted = tuple(dict.fromkeys(str(row).strip() for row in target_names if str(row).strip()))
    if len(wanted) != len(target_names):
        raise ValueError("result-card target identities must be nonempty and unique")
    grouped: dict[str, list[tuple[int, dict[str, Any]]]] = {target: [] for target in wanted}
    for line_number, row in _read_frozen_ledger(ledger_path):
        target = str(row.get("target") or "")
        if target in grouped:
            grouped[target].append((line_number, row))
    selected: dict[str, tuple[int, dict[str, Any]]] = {}
    for target in wanted:
        candidates = grouped[target]
        if not candidates:
            raise ValueError(f"no closure certificate for result-card target {target}")
        line_number, cert = max(candidates, key=lambda row: certificate_strength_rank(row[1]))
        proof = str(cert.get("proof_text") or "").strip()
        if (
            not certificate_is_governed(cert)
            or not certificate_statement(cert)
            or not proof
            or has_sorry(proof)
            or re.search(r"(?<![A-Za-z0-9_])admit(?![A-Za-z0-9_])", proof)
        ):
            raise ValueError(f"selected certificate for {target} is not card-admissible")
        selected[target] = (line_number, cert)
    return selected


def _source_receipts(
    paths: Sequence[Path], *, freeze_content: bool = False
) -> list[dict[str, str]]:
    receipts: list[dict[str, str]] = []
    for path in paths:
        source = Path(path)
        if not source.is_file():
            raise ValueError(f"result-card source is missing: {source}")
        data = source.read_bytes()
        receipt = {"ref": str(source), "sha256": sha256_bytes(data)}
        if freeze_content:
            try:
                receipt["content"] = data.decode("utf-8")
            except UnicodeDecodeError as exc:
                raise ValueError(
                    f"result-card objective source is not UTF-8: {source}"
                ) from exc
        receipts.append(receipt)
    if not receipts:
        raise ValueError("science-facing result cards require at least one source binding")
    return receipts


def build_result_card_deck(
    *,
    ledger_path: Path,
    target_names: Sequence[str],
    source_refs_by_target: Mapping[str, Sequence[Path]],
    objective: str,
    objective_source_refs: Sequence[Path],
    epoch: int = 0,
) -> dict[str, Any]:
    """Freeze a source-bound card deck without copying any proof bytes into it."""

    if not objective.strip() or type(epoch) is not int or epoch < 0:
        raise ValueError("result-card deck requires a nonempty objective and nonnegative epoch")
    ledger = Path(ledger_path)
    ledger_sha256 = sha256_file(ledger)
    selected = select_certificates(ledger, target_names)
    objective_sources = _source_receipts(
        objective_source_refs, freeze_content=True
    )
    objective_sha256 = sha256_bytes(objective.strip().encode("utf-8"))
    cards: list[dict[str, Any]] = []
    for target in target_names:
        line_number, cert = selected[target]
        probe = str(cert["recompilable_probe"])
        proof = str(cert["proof_text"]).strip()
        statement = certificate_statement(cert)
        identity = resolve_theorem_target(probe, target)
        assert identity is not None
        statement_sha256 = sha256_bytes(statement.encode("utf-8"))
        context_sha256 = sha256_bytes(
            preamble_before_target(probe, identity.qualified_name).encode("utf-8")
        )
        sources = _source_receipts(source_refs_by_target.get(target) or ())
        source_sha256 = content_hash(sources)
        probe_sha256 = sha256_bytes(probe.encode("utf-8"))
        hidden_probe = replace_decl_proof(probe, target, "by sorry")
        hidden_probe_sha256 = sha256_bytes(hidden_probe.encode("utf-8"))
        declared_probe_sha = str(cert.get("recompilable_probe_sha256") or "")
        if declared_probe_sha and declared_probe_sha != probe_sha256:
            raise ValueError(f"certificate probe digest mismatch for {target}")
        cert_sha256 = content_hash(dict(cert))
        proof_sha256 = sha256_bytes(proof.encode("utf-8"))
        card_identity = {
            "target_identity": identity.qualified_name,
            "statement_sha256": statement_sha256,
            "context_sha256": context_sha256,
            "source_sha256": source_sha256,
            "epoch": epoch,
        }
        card_core: dict[str, Any] = {
            "card_schema": RESULT_CARD_SCHEMA,
            "card_id": "result-card:" + content_hash(card_identity),
            "source_kind": "source_bound",
            "source_receipts": sources,
            "source_sha256": source_sha256,
            "target_identity": identity.qualified_name,
            "context_sha256": context_sha256,
            "epoch": epoch,
            "lean_statement": statement,
            "statement_sha256": statement_sha256,
            "hidden_proof_ref": {
                "ledger_sha256": ledger_sha256,
                "line_number": line_number,
                "certificate_sha256": cert_sha256,
            },
            "proof_sha256": proof_sha256,
            "recompilable_probe_sha256": probe_sha256,
            "hidden_replay_probe_sha256": hidden_probe_sha256,
            "statement_faithfulness_receipt": {
                "status": "source_bound_for_independent_review",
                "source_sha256": source_sha256,
                "claim_boundary": "binds the formal card to frozen sources; it does not certify novelty",
            },
            "kernel_receipt": {
                "checker": cert.get("checker"),
                "certificate_schema": cert.get("certificate_schema") or "legacy_governed_closure",
                "certificate_sha256": cert_sha256,
                "governance_kernel": dict((cert.get("governance") or {}).get("governance_kernel") or {}),
                "statement_integrity": dict((cert.get("governance") or {}).get("statement_integrity") or {}),
                "matched_negative_control": dict(cert.get("matched_negative_control") or {}),
            },
            "difficulty_receipt": {"status": "pending_hidden_proof_replay", "attempts": []},
            "usefulness_receipt": {"status": "pending_target_replay"},
            "golf_variants": [],
        }
        cards.append({**card_core, "card_sha256": content_hash(card_core)})
    deck_context_sha256 = content_hash(
        {
            "card_context_sha256s": [row["context_sha256"] for row in cards],
            "objective_sources": objective_sources,
            "epoch": epoch,
        }
    )
    core: dict[str, Any] = {
        "schema": RESULT_CARD_DECK_SCHEMA,
        "ledger_ref": str(ledger),
        "ledger_sha256": ledger_sha256,
        "objective": objective.strip(),
        "objective_sha256": objective_sha256,
        "objective_source_receipts": objective_sources,
        "context_sha256": deck_context_sha256,
        "epoch": epoch,
        "cards": cards,
        "proof_visibility": "hidden_by_default_resolvable_only_from_frozen_ledger",
    }
    return {**core, "deck_sha256": content_hash(core)}


def _resolve_hidden_certificate(
    deck: Mapping[str, Any], card_id: str
) -> tuple[Mapping[str, Any], Mapping[str, Any]]:
    validate_result_card_deck(deck)
    card = next((row for row in deck["cards"] if row["card_id"] == card_id), None)
    if not isinstance(card, Mapping):
        raise ValueError("unknown result-card identity")
    ledger = Path(str(deck["ledger_ref"]))
    if sha256_file(ledger) != deck["ledger_sha256"]:
        raise ValueError("result-card certificate ledger changed after deck freeze")
    reference = card["hidden_proof_ref"]
    indexed = dict(_read_frozen_ledger(ledger))
    cert = indexed.get(int(reference["line_number"]))
    if not isinstance(cert, dict) or content_hash(cert) != reference["certificate_sha256"]:
        raise ValueError("result-card certificate reference does not resolve")
    probe = str(cert.get("recompilable_probe") or "")
    if sha256_bytes(probe.encode("utf-8")) != card["recompilable_probe_sha256"]:
        raise ValueError("result-card probe bytes changed")
    return card, cert


def resolve_hidden_proof(deck: Mapping[str, Any], card_id: str) -> str:
    """Resolve one hidden proof after checking every frozen byte identity."""

    card, cert = _resolve_hidden_certificate(deck, card_id)
    proof = str(cert.get("proof_text") or "").strip()
    if sha256_bytes(proof.encode("utf-8")) != card["proof_sha256"]:
        raise ValueError("result-card proof bytes changed")
    return proof


def resolve_hidden_probe(deck: Mapping[str, Any], card_id: str) -> str:
    """Resolve the carried source probe while retaining the card's proof policy."""

    _card, cert = _resolve_hidden_certificate(deck, card_id)
    return str(cert["recompilable_probe"])


def result_card_replay_identity(card: Mapping[str, Any]) -> dict[str, str]:
    """Return the theorem/probe identity that owns hidden-proof difficulty.

    Objective sources and deck epochs deliberately do not participate: they
    govern conjecturing, whereas replay difficulty is measured against the
    exact proof-hidden Lean probe.
    """

    return {
        "target_identity": str(card.get("target_identity") or ""),
        "statement_sha256": str(card.get("statement_sha256") or ""),
        "context_sha256": str(card.get("context_sha256") or ""),
        "proof_sha256": str(card.get("proof_sha256") or ""),
        "recompilable_probe_sha256": str(
            card.get("recompilable_probe_sha256") or ""
        ),
    }


def validate_result_card_deck(deck: Mapping[str, Any]) -> None:
    core = {key: value for key, value in deck.items() if key != "deck_sha256"}
    if (
        deck.get("schema") != RESULT_CARD_DECK_SCHEMA
        or deck.get("deck_sha256") != content_hash(core)
        or not isinstance(deck.get("cards"), list)
        or not deck["cards"]
    ):
        raise ValueError("invalid result-card deck envelope")
    for raw in deck.get("objective_source_receipts") or ():
        if not isinstance(raw, Mapping):
            raise ValueError("result-card objective source receipt is malformed")
        frozen = raw.get("content")
        if frozen is not None and (
            not isinstance(frozen, str)
            or sha256_bytes(frozen.encode("utf-8")) != raw.get("sha256")
        ):
            raise ValueError("result-card frozen objective source bytes do not match receipt")
    seen: set[str] = set()
    for raw in deck["cards"]:
        if not isinstance(raw, Mapping):
            raise ValueError("result-card row is malformed")
        card_core = {key: value for key, value in raw.items() if key != "card_sha256"}
        if (
            raw.get("card_schema") != RESULT_CARD_SCHEMA
            or raw.get("card_sha256") != content_hash(card_core)
            or raw.get("card_id") in seen
            or not str(raw.get("lean_statement") or "").strip()
            or top_level_assign(str(raw.get("lean_statement") or "")) >= 0
            or has_sorry(str(raw.get("lean_statement") or ""))
            or "proof_text" in raw
        ):
            raise ValueError("invalid or proof-leaking result card")
        hidden_probe_sha256 = raw.get("hidden_replay_probe_sha256")
        if hidden_probe_sha256 is not None and not re.fullmatch(
            r"[0-9a-f]{64}", str(hidden_probe_sha256)
        ):
            raise ValueError("invalid result-card hidden replay probe digest")
        seen.add(str(raw["card_id"]))


def resolve_objective_source_text(receipt: Mapping[str, Any]) -> str:
    """Resolve immutable objective-source bytes from a card-deck receipt.

    New decks carry the bytes. Legacy decks may resolve the referenced file
    only while its digest still matches; a changed file creates a successor
    deck epoch instead of silently changing an in-flight prompt.
    """

    frozen = receipt.get("content")
    expected = str(receipt.get("sha256") or "")
    if isinstance(frozen, str):
        if sha256_bytes(frozen.encode("utf-8")) != expected:
            raise ValueError("result-card frozen objective source bytes do not match receipt")
        return frozen
    source = Path(str(receipt.get("ref") or ""))
    if not source.is_file() or sha256_file(source) != expected:
        raise ValueError("result-card objective source changed after deck freeze")
    return source.read_text(encoding="utf-8")


def build_result_card_deck_from_request(
    request: Mapping[str, Any], *, root: Path
) -> dict[str, Any]:
    """Resolve one declarative freeze request against an explicit repository root."""

    if request.get("schema") != RESULT_CARD_FREEZE_REQUEST_SCHEMA:
        raise ValueError("unsupported result-card freeze request")
    rows = request.get("targets")
    if not isinstance(rows, list) or not rows:
        raise ValueError("result-card freeze request has no targets")
    targets: list[str] = []
    sources: dict[str, list[Path]] = {}
    for row in rows:
        if not isinstance(row, Mapping):
            raise ValueError("result-card freeze target is malformed")
        target = str(row.get("target_identity") or "").strip()
        refs = row.get("source_refs")
        if not target or not isinstance(refs, list) or not refs:
            raise ValueError("result-card freeze target lacks identity or sources")
        targets.append(target)
        sources[target] = [root / str(ref) for ref in refs]
    return build_result_card_deck(
        ledger_path=root / str(request.get("ledger_ref") or ""),
        target_names=targets,
        source_refs_by_target=sources,
        objective=str(request.get("objective") or ""),
        objective_source_refs=[
            root / str(ref) for ref in request.get("objective_source_refs") or ()
        ],
        epoch=int(request.get("epoch", 0)),
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Freeze content-bound LeanMill result cards")
    parser.add_argument("--request", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args(argv)
    request = json.loads(args.request.read_text(encoding="utf-8"))
    deck = build_result_card_deck_from_request(request, root=args.root)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(deck, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({
        "deck_sha256": deck["deck_sha256"],
        "ledger_sha256": deck["ledger_sha256"],
        "cards": len(deck["cards"]),
        "out": str(args.out),
    }, indent=2))
    return 0


__all__ = [
    "RESULT_CARD_DECK_SCHEMA",
    "RESULT_CARD_FREEZE_REQUEST_SCHEMA",
    "RESULT_CARD_SCHEMA",
    "build_result_card_deck",
    "build_result_card_deck_from_request",
    "certificate_is_governed",
    "certificate_statement",
    "certificate_strength_rank",
    "resolve_hidden_proof",
    "resolve_hidden_probe",
    "resolve_objective_source_text",
    "result_card_replay_identity",
    "select_certificates",
    "sha256_file",
    "validate_result_card_deck",
]


if __name__ == "__main__":
    raise SystemExit(main())
