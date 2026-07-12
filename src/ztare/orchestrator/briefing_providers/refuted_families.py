from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from ztare.orchestrator.mutator_briefing import BriefingContext, BriefingProvider
from ztare.common.conflict_ledger import ConflictClause

_LEDGER_NAME = "refuted_families.jsonl"
_DEFAULT_FAILURE_THRESHOLD = 3


def _workspace_path(ctx: BriefingContext) -> Path:
    return Path(ctx.workspace_dir or (Path(ctx.project_dir) / "workspace"))


def _candidate_memory_path(ctx: BriefingContext) -> Path:
    return _workspace_path(ctx) / "candidate_memory.json"


def _ledger_path(ctx: BriefingContext) -> Path:
    return _workspace_path(ctx) / _LEDGER_NAME


class LedgerSourceUnreadable(RuntimeError):
    """A ledger source file exists but could not be read/parsed.

    Distinct from file-absent-by-design (a legitimately empty state): on this
    error the persisted refuted-families ledger must NOT be rewritten, and the
    briefing section must say so instead of silently vanishing."""


def _load_json(path: Path) -> Any:
    """Parsed JSON, or None when the file is absent by design.

    Raises LedgerSourceUnreadable on any read/parse error so a transient
    failure can never masquerade as an empty source."""
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return None
    except OSError as exc:
        raise LedgerSourceUnreadable(f"{path}: {type(exc).__name__}: {exc}") from exc
    try:
        return json.loads(text)
    except ValueError as exc:
        raise LedgerSourceUnreadable(f"{path}: {type(exc).__name__}: {exc}") from exc


def _candidate_rows(ctx: BriefingContext) -> list[dict[str, Any]]:
    payload = _load_json(_candidate_memory_path(ctx))
    rows = payload.get("records") if isinstance(payload, dict) else None
    return [row for row in rows or [] if isinstance(row, dict)]


def _normalize_text(value: Any) -> str:
    return " ".join(str(value or "").strip().lower().split())


def _mechanical_signature(row: dict[str, Any]) -> str | None:
    residual = row.get("target_residual_class") or row.get("residual_class")
    if not residual:
        residual = row.get("failure_family") or row.get("blocked_residual_class")
    repair = row.get("repair_shape") or row.get("repair_class") or row.get("required_transform")
    if not residual and not repair:
        return None
    residual_sig = _normalize_text(residual) or "unknown-residual"
    repair_sig = _normalize_text(repair) or "unknown-repair"
    return f"{residual_sig} x {repair_sig}"


def _witness_summary(rows: list[dict[str, Any]]) -> str:
    counter = Counter(
        (_normalize_text(row.get("diagnosis")) or _normalize_text(row.get("outcome")) or "unspecified")
        for row in rows
    )
    if not counter:
        return "no witness summary"
    items = ", ".join(f"{label}:{count}" for label, count in counter.most_common(3))
    return items


def _receipt_refs(rows: list[dict[str, Any]]) -> list[str]:
    refs: list[str] = []
    for row in rows:
        for key in ("receipt_ref", "receipt_path", "source_ref", "source", "evidence_ref"):
            ref = str(row.get(key) or "").strip()
            if ref:
                refs.append(ref)
                break
    return refs


def _family_rows(ctx: BriefingContext) -> list[dict[str, Any]]:
    rows = _candidate_rows(ctx)
    by_sig: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        sig = _mechanical_signature(row)
        if sig:
            by_sig[sig].append(row)
    threshold = int((ctx.rubric or {}).get("refuted_family_threshold", _DEFAULT_FAILURE_THRESHOLD))
    families: list[dict[str, Any]] = []
    for sig, sig_rows in by_sig.items():
        failed = [row for row in sig_rows if _normalize_text(row.get("source_type")) == "deterministic_near_miss" or _normalize_text(row.get("status")) in {"failure", "blocked"} or _normalize_text(row.get("outcome")) in {"blocked", "failed"}]
        if len(failed) < threshold and not any(_normalize_text(row.get("diagnosis")).startswith("exhaust") for row in sig_rows):
            continue
        families.append(
            {
                "family_signature": sig,
                "receipts_refs": _receipt_refs(sig_rows),
                "witness_summary": _witness_summary(sig_rows),
                "provenance": {
                    "source": "candidate_memory",
                    "row_count": len(sig_rows),
                    "failed_count": len(failed),
                },
            }
        )
    return sorted(families, key=lambda row: row["family_signature"])


def refresh_refuted_families_ledger(ctx: BriefingContext) -> list[dict[str, Any]]:
    # Raises LedgerSourceUnreadable when candidate_memory exists but cannot be
    # read: the persisted ledger stays untouched (a transient read error must
    # never erase refuted-family memory).
    families = _family_rows(ctx)
    path = _ledger_path(ctx)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in families), encoding="utf-8")
    return families


def _load_refuted_families(ctx: BriefingContext) -> list[dict[str, Any]]:
    path = _ledger_path(ctx)
    if not path.exists():
        return refresh_refuted_families_ledger(ctx)
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise LedgerSourceUnreadable(f"{path}: {type(exc).__name__}: {exc}") from exc
    rows = []
    for line in text.splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except Exception:
            continue
        if isinstance(row, dict) and row.get("family_signature"):
            rows.append(row)
    return rows


class RefutedFamiliesProvider(BriefingProvider):
    name = "refuted_families"
    priority = 84
    tier = 2
    max_fragment_chars = 2400

    def applies(self, ctx: BriefingContext) -> bool:
        try:
            return bool(_load_refuted_families(ctx))
        except LedgerSourceUnreadable:
            return True  # the UNREADABLE banner must render

    def fragment(self, ctx: BriefingContext) -> str:
        try:
            rows = _load_refuted_families(ctx)
        except LedgerSourceUnreadable as exc:
            return (
                "## ⚠️  REFUTED FAMILIES UNREADABLE — prior refutations still in force\n\n"
                f"Ledger source read error: `{exc}`. The refuted-families ledger was NOT "
                "rewritten this iter; treat every previously refuted family as still "
                "blocked and do not resubmit candidates from those classes.\n"
            )
        if not rows:
            return ""
        lines = ["## Refuted Families"]
        for row in rows:
            refs = ", ".join(row.get("receipts_refs") or []) or "no receipt refs"
            lines.append(
                f"- `{row['family_signature']}` exhausted with {len(row.get('receipts_refs') or [])} receipts - novelty must leave this class."
            )
            lines.append(f"  - receipts: {refs}")
            lines.append(f"  - witness: {row.get('witness_summary') or 'unspecified'}")
            provenance = row.get("provenance") or {}
            lines.append(
                f"  - provenance: {provenance.get('source', 'unknown')} rows={provenance.get('row_count', '?')} failed={provenance.get('failed_count', '?')}"
            )
        return "\n".join(lines) + "\n"

    def structured_records(self, ctx: BriefingContext) -> list[dict]:
        try:
            return _load_refuted_families(ctx)
        except LedgerSourceUnreadable as exc:
            return [{
                "refuted_families_unreadable": str(exc),
                "prior_refutations_still_in_force": True,
            }]


class RefutedFamiliesLedger:
    def __init__(self, ctx: BriefingContext):
        self.ctx = ctx

    def learn(self, conflict_receipt) -> ConflictClause:
        row = dict(conflict_receipt or {})
        return ConflictClause(
            signature=str(row.get("family_signature") or ""),
            receipts_refs=tuple(str(x) for x in row.get("receipts_refs") or [] if str(x).strip()),
            witness_summary=str(row.get("witness_summary") or ""),
            provenance=row.get("provenance") or {"source": "candidate_memory"},
            defeasible=bool(row.get("defeasible", False)),
        )

    def blocks(self, candidate_signature: str) -> "ConflictClause | None":
        try:
            rows = _load_refuted_families(self.ctx)
        except LedgerSourceUnreadable as exc:
            # fail closed: an unreadable ledger must not unblock refuted families
            return ConflictClause(
                signature=candidate_signature,
                witness_summary=f"refuted-families ledger unreadable, failing closed: {exc}",
                provenance={"source": "refuted_families.ledger_unreadable"},
                defeasible=False,
            )
        for row in rows:
            if row.get("family_signature") == candidate_signature:
                return ConflictClause(
                    signature=row.get("family_signature", ""),
                    receipts_refs=tuple(row.get("receipts_refs") or []),
                    witness_summary=row.get("witness_summary") or "",
                    provenance=row.get("provenance") or {"source": "candidate_memory"},
                    defeasible=True,
                )
        return None

    def revive(self, evidence_card):
        return evidence_card

    def open_clauses(self) -> list[ConflictClause]:
        try:
            rows = _load_refuted_families(self.ctx)
        except LedgerSourceUnreadable as exc:
            return [ConflictClause(
                signature="refuted_families:ledger-unreadable",
                witness_summary=f"refuted-families ledger unreadable, failing closed: {exc}",
                provenance={"source": "refuted_families.ledger_unreadable"},
                defeasible=False,
            )]
        return [
            ConflictClause(
                signature=row.get("family_signature", ""),
                receipts_refs=tuple(row.get("receipts_refs") or []),
                witness_summary=row.get("witness_summary") or "",
                provenance=row.get("provenance") or {"source": "candidate_memory"},
                defeasible=True,
            )
            for row in rows
        ]


def refuted_family_card_from_rows(rows: list[dict[str, Any]], *, provenance: dict[str, Any] | None = None) -> dict[str, Any] | None:
    if not rows:
        return None
    sig = _mechanical_signature(rows[0])
    if not sig:
        return None
    return {
        "family_signature": sig,
        "receipts_refs": _receipt_refs(rows),
        "witness_summary": _witness_summary(rows),
        "provenance": provenance or {"source": "candidate_memory", "row_count": len(rows)},
    }
