#!/usr/bin/env python3
"""RD forecast-tick close helper.

This is a client-side safety wrapper, not an authority. It keeps the
GP-241 daemon as the only writer, but removes the brittle manual steps
that caused repeated RD close loops:

* derive frozen start goal/substrate from the signed chain;
* preflight the proposed F-row against known lexical tripwires;
* preflight L1/L2/L3 declarations before H7;
* derive catalog-approved receipt/judge provenance for obligation discharges
  before the first submit;
* freeze payload bytes and resubmit unchanged until the judge pass binds.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[3]
STORE = Path(os.environ.get("ZTARE_OFFICIAL_STORE", "/srv/ztare_official_store"))
PY = sys.executable

FORMAL_CLAIM_PATTERNS = tuple(
    re.compile(pattern, re.IGNORECASE | re.DOTALL)
    for pattern in (
        r"\b(clay|millennium[- ]problem|navier[- ]stokes)\b.{0,100}"
        r"\b(proved|proven|solved|resolved|closed|settled|closure|qed)\b",
        r"\b(proved|proven|solved|resolved|closed|settled|closure)\b.{0,100}"
        r"\b(clay|millennium[- ]problem|navier[- ]stokes)\b",
        r"\b(formal|compiled)\s+proof\b",
        r"\b(theorem|lean)\b.{0,100}"
        r"\b(proves|proved|proven|settles|solves|closes|closure)\b",
        r"\b(proves|proved|proven|settles|solves|closes)\b.{0,100}"
        r"\b(theorem|lean)\b",
        r"\b(qed|sorry-free|axiom-free|target_statement_hash)\b",
        r"∎",
    )
)

PAYLOAD_FILES = ("f_row.txt", "declared.json", "witnesses.json", "why_not.json")
OPTIONAL_PAYLOAD_FILES = ("declarations.txt", "research_done.json")
SANCTIONED_DISPATCH_CLASSES = {
    "adversarial_kill",
    "cold_deanchor_carveout3",
    "divide_and_conquer",
}
F_ROW_BACKTICK_DATE_RE = re.compile(
    r"(?m)^(?P<prefix>date:\s*)`(?P<date>\d{4}-\d{2}-\d{2})`\s*$"
)
F_ROW_PLAIN_DATE_RE = re.compile(
    r"(?m)^(?P<prefix>date:\s*)(?P<date>\d{4}-\d{2}-\d{2})\s*$"
)


def _json_load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _json_write(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n",
                    encoding="utf-8")


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _chain_rows() -> list[dict[str, Any]]:
    ledger = STORE / "official" / "transitions.stamped.jsonl"
    rows: list[dict[str, Any]] = []
    if not ledger.is_file():
        raise SystemExit(f"official stamped ledger not found: {ledger}")
    for line in ledger.read_text(encoding="utf-8", errors="ignore").splitlines():
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows


def _frozen_start(tick_id: str) -> dict[str, Any]:
    for row in reversed(_chain_rows()):
        if row.get("transition_type") == "start_tick" and row.get("tick_id") == tick_id:
            return row
    raise SystemExit(f"no frozen start_tick row for {tick_id}")


def _manifest(kind: str, tick_id: str) -> dict[str, Any]:
    path = STORE / "official" / "manifests" / f"{tick_id}.{kind}.json"
    if not path.is_file():
        raise SystemExit(f"missing official {kind} manifest receipt file: {path}")
    return _json_load(path)


def _payload_hash(payload_dir: Path) -> str:
    h = hashlib.sha256()
    for name in PAYLOAD_FILES + OPTIONAL_PAYLOAD_FILES:
        path = payload_dir / name
        if path.is_file():
            h.update(name.encode("utf-8"))
            h.update(b"\0")
            h.update(path.read_bytes())
            h.update(b"\0")
    return h.hexdigest()


def _formal_claim_tripwire(text: str) -> str | None:
    for pattern in FORMAL_CLAIM_PATTERNS:
        match = pattern.search(text)
        if match:
            return match.group(0)
    return None


def _dispatch_ledger_error(text: str) -> str | None:
    marker = "dispatch_ledger:"
    if marker not in text:
        return f"missing {marker}"
    ledger = text.split(marker, 1)[1].splitlines()[0]
    entries = [entry.strip() for entry in ledger.split(";") if entry.strip()]
    if not entries:
        return "empty dispatch_ledger"
    for entry in entries:
        if "=" not in entry:
            return f"dispatch_ledger entry missing '=': {entry!r}"
        value = entry.rsplit("=", 1)[1].strip()
        if value not in SANCTIONED_DISPATCH_CLASSES:
            return (
                f"unsanctioned dispatch class {value!r}; use one of "
                f"{sorted(SANCTIONED_DISPATCH_CLASSES)} with no trailing punctuation"
            )
    return None


def _consumes_surfaced_error(text: str) -> str | None:
    marker = "consumes_surfaced:"
    if marker not in text:
        return f"missing {marker}"
    tail = text.split(marker, 1)[1].strip()
    if not tail:
        return "empty consumes_surfaced"
    token = tail.split()[0].strip()
    if token[-1:] in {".", ",", ";", ":"}:
        return f"consumes_surfaced id has trailing punctuation: {token!r}"
    return None


def _ensure_f_row_date(payload_dir: Path, *, write: bool,
                       window_hours: int = 24) -> str | None:
    """Normalize the proposed row to tick_close.py's date grammar.

    `tick_close.py` intentionally parses the row date from backticks so
    stale-table rows cannot be matched accidentally.  The RD helper owns the
    clerical normalization before payload freeze; the daemon still owns the
    authoritative close.
    """
    path = payload_dir / "f_row.txt"
    text = path.read_text(encoding="utf-8")
    match = F_ROW_BACKTICK_DATE_RE.search(text)
    if match:
        date_text = match.group("date")
    else:
        plain = F_ROW_PLAIN_DATE_RE.search(text)
        if not plain:
            return (
                "F-row date missing or malformed. Add a standalone line "
                "`date: `YYYY-MM-DD``; the backticks are required by "
                "tick_close.py's stale-row guard."
            )
        date_text = plain.group("date")
        if not write:
            return (
                "F-row date is plain ISO. Wrap it as "
                f"`date: `{date_text}`` or rerun without --no-write so the "
                "helper can normalize it before freezing payload bytes."
            )
        text = F_ROW_PLAIN_DATE_RE.sub(
            lambda m: f"{m.group('prefix')}`{m.group('date')}`",
            text,
            count=1,
        )
        path.write_text(text, encoding="utf-8")
    try:
        row_date = datetime.strptime(date_text, "%Y-%m-%d").replace(
            tzinfo=timezone.utc
        )
    except ValueError:
        return f"F-row date is not ISO YYYY-MM-DD: {date_text!r}"
    floor = datetime.now(timezone.utc) - timedelta(hours=window_hours)
    if row_date.date() < floor.date():
        return (
            f"F-row date `{date_text}` is older than the close window floor "
            f"{floor.strftime('%Y-%m-%d')}; update the proposed row for this "
            "fresh tick instead of reusing a stale row."
        )
    return None


def _require_payload(payload_dir: Path) -> None:
    missing = [name for name in PAYLOAD_FILES if not (payload_dir / name).is_file()]
    if missing:
        raise SystemExit(f"payload missing required files: {', '.join(missing)}")


def _requires_research_done(start: dict[str, Any], payload_dir: Path) -> bool:
    """Return whether the signed start declares depth-sensitive research.

    This close client is substrate-agnostic.  It must not infer from project
    names or domain vocabulary.  The tick opener owns the generic signal.
    """
    if (payload_dir / "research_done.json").is_file():
        return True
    declared = start.get("start_declared_signals") or {}
    if isinstance(declared, dict):
        for key, value in declared.items():
            if value and str(key).lower() in {
                "hard_mathematical_residual",
                "hard_research_residual",
                "proof_frontier",
                "formal_frontier",
                "research_depth_required",
                "recursive_research_required",
            }:
                return True
    return False


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _is_under(path: Path, root: Path) -> bool:
    try:
        path.resolve(strict=True).relative_to(root.resolve(strict=True))
        return True
    except (FileNotFoundError, ValueError):
        return False


def _sync_allowlist() -> set[str]:
    manifest = REPO / "deploy/vps_sync_files.txt"
    if not manifest.is_file():
        return set()
    return {
        line.strip()
        for line in manifest.read_text(encoding="utf-8", errors="ignore").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }


def _artifact_ref_error(ref: Any, payload_dir: Path) -> str | None:
    if isinstance(ref, str):
        raw_path = ref
        root_name = "payload"
        expected_sha = ""
    elif isinstance(ref, dict):
        allowed_keys = {"path", "root", "sha256"}
        extra = sorted(set(ref) - allowed_keys)
        if extra:
            return f"unsupported artifact ref keys: {extra}"
        raw_path = str(ref.get("path") or "")
        root_name = str(ref.get("root") or "payload")
        expected_sha = str(ref.get("sha256") or "").strip().lower()
    else:
        return "artifact ref must be a path string or {path, root?, sha256?}"

    text = raw_path.strip()
    if not text or text.lower() in {"none", "n/a", "na", "not_applicable"}:
        return "artifact path is empty"
    if "\n" in text or "\x00" in text or "://" in text:
        return "artifact path must be a local file path"
    root_map = {
        "payload": payload_dir,
        "repo": REPO,
        "store": STORE,
    }
    root = root_map.get(root_name)
    if root is None:
        return "artifact root must be one of payload, repo, store"

    path = Path(text)
    if path.is_absolute():
        candidate = path
        if not _is_under(candidate, root):
            return f"absolute artifact path escapes declared root {root_name}"
    else:
        if any(part in {"", ".", ".."} for part in path.parts):
            return "artifact path must not contain empty, '.', or '..' segments"
        candidate = root / path

    try:
        resolved = candidate.resolve(strict=True)
    except FileNotFoundError:
        return f"artifact file not found: {text}"
    if not resolved.is_file():
        return f"artifact is not a file: {text}"
    if not _is_under(resolved, root):
        return f"artifact resolves outside declared root {root_name}"
    rel_text = (
        resolved.relative_to(REPO.resolve(strict=True)).as_posix()
        if root_name == "repo"
        else (path.as_posix() if not path.is_absolute() else text)
    )
    if root_name == "repo" and rel_text not in _sync_allowlist():
        return (
            f"repo artifact is not VPS-sync allowlisted: {rel_text}. "
            "For per-tick scratch/workbench evidence, copy a small receipt "
            "into the close payload and reference it as "
            "{\"root\":\"payload\",\"path\":\"artifacts/...\"}; do not add "
            "tick scratch output to deploy/vps_sync_files.txt."
        )
    if expected_sha:
        if not re.fullmatch(r"[0-9a-f]{64}", expected_sha):
            return "artifact sha256 must be 64 lowercase hex characters"
        actual_sha = _sha256_file(resolved)
        if actual_sha != expected_sha:
            return "artifact sha256 mismatch"
    return None


PLACEHOLDER_VALUES = {
    "replace_me",
    "fill_me",
    "todo",
    "tbd",
    "placeholder",
}


def _nonempty_string(value: Any) -> bool:
    text = str(value or "").strip()
    return bool(text) and text.lower() not in PLACEHOLDER_VALUES


def _claim_boundary_schema_error(receipt: dict[str, Any]) -> str | None:
    rows = receipt.get("rows")
    if not isinstance(rows, list):
        return "claim_boundary_typed_rows receipt needs rows[]"
    if len(rows) != 2:
        return "claim_boundary_typed_rows receipt needs exactly two rows"
    by_kind: dict[str, dict[str, Any]] = {}
    required = {
        "claim_kind",
        "claim_text",
        "answer_object",
        "success_criterion",
        "evidence_available",
        "missing_evidence_or_blocker",
        "permitted_status",
        "pass_fail_boundary",
    }
    for idx, row in enumerate(rows, start=1):
        if not isinstance(row, dict):
            return f"claim_boundary_typed_rows row {idx} must be an object"
        missing = sorted(k for k in required if not _nonempty_string(row.get(k)))
        if missing:
            return f"claim_boundary_typed_rows row {idx} missing {missing}"
        kind = str(row.get("claim_kind") or "").strip().lower()
        if kind not in {"broad", "narrow"}:
            return (
                "claim_boundary_typed_rows claim_kind must be broad or narrow"
            )
        if kind in by_kind:
            return f"claim_boundary_typed_rows duplicate {kind} row"
        by_kind[kind] = row
    if set(by_kind) != {"broad", "narrow"}:
        return "claim_boundary_typed_rows needs one broad and one narrow row"
    broad_status = str(by_kind["broad"].get("permitted_status") or "").strip().upper()
    narrow_status = str(by_kind["narrow"].get("permitted_status") or "").strip().upper()
    if broad_status != "BLOCKED":
        return "claim_boundary_typed_rows broad row must be BLOCKED"
    if narrow_status != "PERMITTED":
        return "claim_boundary_typed_rows narrow row must be PERMITTED"
    if (
        str(by_kind["broad"].get("claim_text") or "").strip()
        == str(by_kind["narrow"].get("claim_text") or "").strip()
    ):
        return "claim_boundary_typed_rows broad/narrow claim_text must differ"
    return None


def _meta_language_edge_schema_error(receipt: dict[str, Any]) -> str | None:
    decisive = [
        "observed_state",
        "candidate_edge",
        "required_check",
        "forbidden_sibling",
        "permitted_update_if_paid",
        "stop_rule",
    ]
    missing = [k for k in decisive if not _nonempty_string(receipt.get(k))]
    if missing:
        return f"meta_language_edge_receipt missing decisive fields {missing}"
    candidate = str(receipt.get("candidate_edge") or "").strip().lower()
    sibling = str(receipt.get("forbidden_sibling") or "").strip().lower()
    required_check = str(receipt.get("required_check") or "").strip().lower()
    if candidate == sibling:
        return "meta_language_edge_receipt candidate_edge equals forbidden_sibling"
    if required_check in {"pattern label", "mm label", "label", "family label"}:
        return "meta_language_edge_receipt required_check cannot be a label"
    if "label alone" in required_check:
        return "meta_language_edge_receipt required_check cannot be label-alone"
    return None


def _carrier_schema_receipt_error(
    name: str,
    slot: str,
    receipt: Any,
    required_fields: list[str],
) -> str | None:
    if not isinstance(receipt, dict):
        return f"research_done.json carrier schema receipt {name!r} must be an object"
    if name == "claim_boundary_typed_rows" or slot == "claim_boundary_schema_artifact":
        return _claim_boundary_schema_error(receipt)
    if name == "meta_language_edge_receipt" or slot == "meta_language_edge_artifact":
        return _meta_language_edge_schema_error(receipt)
    missing = [
        field for field in required_fields
        if not _nonempty_string(receipt.get(field))
    ]
    if missing:
        return (
            "research_done.json carrier schema receipt "
            f"{name!r} missing required fields {missing}"
        )
    return None


def _contract_carrier_error(data: dict[str, Any],
                            contract_ref: Any,
                            payload_dir: Path) -> str | None:
    """Check the research receipt fills the pattern action contract.

    The contract is a dynamic data contract, not a static type system.  It
    closes the recurrent "named the pattern but did not follow it" gap by
    requiring each required carrier slot to be backed by either a local
    artifact ref (legacy mode) or a typed field receipt (schema mode).
    """
    raw_path = (
        contract_ref if isinstance(contract_ref, str)
        else str((contract_ref or {}).get("path") or "")
    )
    root_name = (
        "payload" if isinstance(contract_ref, str)
        else str((contract_ref or {}).get("root") or "payload")
    )
    root_map = {"payload": payload_dir, "repo": REPO, "store": STORE}
    root = root_map.get(root_name)
    if root is None:
        return "pattern action contract has invalid root"
    contract_path = Path(raw_path)
    candidate = contract_path if contract_path.is_absolute() else root / contract_path
    try:
        contract = _json_load(candidate.resolve(strict=True))
    except Exception as exc:  # noqa: BLE001
        return f"pattern action contract is not readable JSON: {exc}"
    if not isinstance(contract, dict):
        return "pattern action contract must be a JSON object"
    carriers = contract.get("evidence_carriers") or []
    if not isinstance(carriers, list):
        return "pattern action contract evidence_carriers must be a list"
    carrier_artifacts = data.get("carrier_artifacts") or {}
    if not isinstance(carrier_artifacts, dict):
        return "research_done.json carrier_artifacts must be an object"
    carrier_schemas = data.get("carrier_schema_receipts") or {}
    if not isinstance(carrier_schemas, dict):
        return "research_done.json carrier_schema_receipts must be an object"
    loops = data.get("loops") or []
    loop_slots: dict[str, Any] = {}
    if isinstance(loops, list):
        for loop in loops:
            if not isinstance(loop, dict):
                continue
            for key in (
                "orientation_artifact",
                "stress_test_artifact",
                "verification_artifact",
            ):
                if key in loop and key not in loop_slots:
                    loop_slots[key] = loop[key]
    for carrier in carriers:
        if not isinstance(carrier, dict) or not carrier.get("required"):
            continue
        name = str(carrier.get("name") or "").strip()
        slot = str(carrier.get("artifact_slot") or "").strip()
        if not name or not slot:
            return "required pattern carrier missing name or artifact_slot"
        required_fields = [
            str(field).strip()
            for field in (carrier.get("required_fields") or [])
            if str(field).strip()
        ]
        schema_receipt = carrier_schemas.get(name)
        if schema_receipt is None:
            schema_receipt = carrier_schemas.get(slot)
        if schema_receipt is not None:
            schema_error = _carrier_schema_receipt_error(
                name,
                slot,
                schema_receipt,
                required_fields,
            )
            if schema_error:
                return schema_error
            if required_fields or name in {
                "claim_boundary_typed_rows",
                "meta_language_edge_receipt",
            }:
                continue
        ref = carrier_artifacts.get(name)
        if ref is None:
            ref = carrier_artifacts.get(slot)
        if ref is None:
            ref = loop_slots.get(slot)
        if ref is None:
            return (
                "research_done.json does not fill required pattern carrier "
                f"{name!r} / slot {slot!r} with carrier_artifacts or "
                "carrier_schema_receipts"
            )
        artifact_error = _artifact_ref_error(ref, payload_dir)
        if artifact_error:
            return (
                f"research_done.json invalid carrier artifact {name!r}: "
                f"{artifact_error}"
            )
    return None


def _research_done_error(payload_dir: Path, start: dict[str, Any],
                         tick_id: str, contract_id: str) -> str | None:
    """Require an explicit research stop rule before hard-math close.

    This is deliberately small.  The goal is to make "why stop now?" a
    first-class receipt, not to add another membrane subsystem.
    """
    if not _requires_research_done(start, payload_dir):
        return None
    path = payload_dir / "research_done.json"
    if not path.is_file():
        return (
            "depth-sensitive close payload missing research_done.json. Add a "
            "small receipt with tick_id, contract_id, min_recursive_loops, "
            "loops[], pattern_action_contract, stop_rule, stop_reason, "
            "why_enough, and remaining_live_vectors."
        )
    try:
        raw = _json_load(path)
    except Exception as exc:  # noqa: BLE001
        return f"research_done.json is not valid JSON: {exc}"
    if not isinstance(raw, dict):
        return "research_done.json must be a JSON object"
    data = raw.get("research_completion")
    if data is None:
        data = raw
    if not isinstance(data, dict):
        return "research_done.json research_completion must be an object"
    if str(data.get("tick_id") or "") != tick_id:
        return "research_done.json tick_id does not match close tick_id"
    if str(data.get("contract_id") or "") != contract_id:
        return "research_done.json contract_id does not match close contract_id"
    loops = data.get("loops")
    if not isinstance(loops, list):
        return "research_done.json needs loops[]"
    if "min_recursive_loops" not in data:
        return "research_done.json needs explicit min_recursive_loops"
    try:
        min_loops = int(data.get("min_recursive_loops"))
    except (TypeError, ValueError):
        return "research_done.json min_recursive_loops must be an integer"
    if min_loops < 1:
        return "research_done.json min_recursive_loops must be >= 1"
    if len(loops) < min_loops:
        return (
            f"research_done.json has {len(loops)} loop(s), below "
            f"min_recursive_loops={min_loops}"
        )
    stop_reason = str(data.get("stop_reason") or "").strip()
    allowed_stop_reasons = {
        "diminishing_information_yield",
        "named_kill_condition_hit",
        "budget_exhausted",
        "operator_interrupt",
        "superseded_by_new_contract",
        "frontier_split_required",
    }
    if stop_reason not in allowed_stop_reasons:
        return (
            "research_done.json stop_reason must be one of "
            f"{sorted(allowed_stop_reasons)}"
        )
    if len(str(data.get("stop_rule") or "").strip()) < 30:
        return "research_done.json stop_rule is too thin"
    if len(str(data.get("why_enough") or "").strip()) < 80:
        return "research_done.json why_enough is too thin"
    contract_ref = data.get("pattern_action_contract")
    contract_error = _artifact_ref_error(contract_ref, payload_dir)
    if contract_error:
        return (
            "research_done.json pattern_action_contract invalid: "
            f"{contract_error}"
        )
    live_vectors = data.get("remaining_live_vectors")
    if not isinstance(live_vectors, list):
        return "research_done.json needs remaining_live_vectors[]"
    live_vector_text = _string_list(live_vectors)
    terminal_stop_reasons = {"named_kill_condition_hit", "operator_interrupt"}
    if not live_vector_text and stop_reason not in terminal_stop_reasons:
        return (
            "research_done.json remaining_live_vectors[] may be empty only "
            f"for terminal stop reasons {sorted(terminal_stop_reasons)}"
        )
    for idx, loop in enumerate(loops, start=1):
        if not isinstance(loop, dict):
            return f"research_done.json loop {idx} is not an object"
        refs_seen: set[str] = set()
        for key in (
            "orientation_artifact",
            "stress_test_artifact",
            "verification_artifact",
        ):
            artifact_error = _artifact_ref_error(loop.get(key), payload_dir)
            if artifact_error:
                return (
                    f"research_done.json loop {idx} invalid {key}: "
                    f"{artifact_error}"
                )
            ref_text = json.dumps(loop.get(key), sort_keys=True)
            if ref_text in refs_seen:
                return f"research_done.json loop {idx} reuses artifact ref {key}"
            refs_seen.add(ref_text)
        if len(str(loop.get("new_information") or "").strip()) < 60:
            return f"research_done.json loop {idx} new_information is too thin"
        if len(str(loop.get("next_question_or_kill") or "").strip()) < 30:
            return f"research_done.json loop {idx} next_question_or_kill is too thin"
    carrier_error = _contract_carrier_error(data, contract_ref, payload_dir)
    if carrier_error:
        return carrier_error
    return None


def _derive_declares(start: dict[str, Any]) -> str:
    signals = start.get("start_declared_signals") or {}
    return ",".join(k for k, v in sorted(signals.items()) if v)


def _start_discharge_policy(start: dict[str, Any]) -> dict[str, dict[str, Any]]:
    policy = start.get("mandatory_obligation_discharge")
    if isinstance(policy, dict) and policy:
        return {
            str(k): v for k, v in policy.items()
            if isinstance(v, dict)
        }
    sys.path.insert(0, str(REPO))
    from src.ztare.surfacing.pre_tick_obligation_compiler import (  # noqa: PLC0415
        merge_signals,
        start_tick,
    )
    declared = merge_signals(
        start.get("start_declared_signals") or {},
        str(start.get("goal") or ""),
    )
    contract = start_tick(
        str(start.get("goal") or ""),
        str(start.get("start_transition_type") or ""),
        declared,
    )
    return {
        str(o["item_id"]): o.get("discharge", {"mode": "judge", "receipts": []})
        for o in contract.mandatory_obligations
    }


def _start_obligation_specs(start: dict[str, Any]) -> dict[str, dict[str, Any]]:
    sys.path.insert(0, str(REPO))
    from src.ztare.surfacing.pre_tick_obligation_compiler import (  # noqa: PLC0415
        merge_signals,
        start_tick,
    )
    declared = merge_signals(
        start.get("start_declared_signals") or {},
        str(start.get("goal") or ""),
    )
    contract = start_tick(
        str(start.get("goal") or ""),
        str(start.get("start_transition_type") or ""),
        declared,
    )
    return {str(o["item_id"]): o for o in contract.mandatory_obligations}


def _desired_provenance(policy: dict[str, Any]) -> str:
    if str(policy.get("mode") or "").lower() == "receipt":
        receipts = {
            str(r).strip()
            for r in (policy.get("receipts") or policy.get("allowed_receipts") or [])
            if str(r).strip()
        }
        if "forecast_tick_packet" in receipts:
            return "receipt:forecast_tick_packet"
    return "judge:auto"


def _obligation_payload_error(start: dict[str, Any],
                              witnesses: dict[str, Any],
                              why_not: dict[str, Any]) -> str | None:
    specs = _start_obligation_specs(start)
    for item, ob in specs.items():
        has_witness = isinstance(witnesses.get(item), dict)
        has_why_not = isinstance(why_not.get(item), dict)
        if has_witness and has_why_not:
            return (
                f"{item}: provide either witnesses[{item!r}] or "
                f"why_not[{item!r}], not both"
            )
        if not has_witness and not has_why_not:
            required = (ob.get("witness_schema") or {}).get("required", [])
            allowed = ob.get("why_not_enum") or []
            return (
                f"{item}: missing discharge payload; provide "
                f"witnesses[{item!r}] with required fields {required} "
                f"or why_not[{item!r}] with reason in {allowed}"
            )
        if has_why_not:
            wn = why_not[item]
            allowed = ob.get("why_not_enum") or []
            reason = str(wn.get("reason") or "").strip()
            if reason not in allowed:
                return (
                    f"{item}: why_not.reason must be one of {allowed}, "
                    f"got {reason!r}"
                )
            if len(str(wn.get("justification") or "").strip()) < 40:
                return f"{item}: why_not.justification is too thin"
            continue
        witness = witnesses[item]
        required = (ob.get("witness_schema") or {}).get("required", [])
        missing = [key for key in required if not str(witness.get(key, "")).strip()]
        if missing:
            return f"{item}: witness missing required fields {missing}"
        if item == "premature_settled_negative":
            witness_text = json.dumps(witness, ensure_ascii=False).lower()
            argues_not_applicable = any(
                phrase in witness_text
                for phrase in (
                    "not a consensus negative",
                    "not a settled negative",
                    "not a negative claim",
                    "preserves the live",
                    "live construction target",
                )
            )
            if argues_not_applicable and "not_a_negative_claim" in (
                ob.get("why_not_enum") or []
            ):
                return (
                    "premature_settled_negative: payload argues the obligation "
                    "is not applicable inside a witness. Move this discharge to "
                    "why_not with reason `not_a_negative_claim` and a concrete "
                    "justification, or provide an actual constructed falsifier/"
                    "derived obstruction witness."
                )
    return None


def _preflight(payload_dir: Path, tick_id: str, contract_id: str,
               owner: str, *, write: bool) -> str:
    _require_payload(payload_dir)
    start = _frozen_start(tick_id)
    post = _manifest("posttick", tick_id)
    frozen_substrate = str(start.get("substrate") or "")
    post_substrate = str(post.get("substrate") or "")
    if post_substrate != frozen_substrate:
        raise SystemExit(
            "posttick substrate mismatch: "
            f"{post_substrate!r} != frozen start {frozen_substrate!r}. "
            "Rerun posttick with the frozen start substrate."
        )

    date_error = _ensure_f_row_date(payload_dir, write=write)
    if date_error:
        raise SystemExit(f"F-row date preflight failed: {date_error}")
    f_row = (payload_dir / "f_row.txt").read_text(encoding="utf-8")
    bad = _formal_claim_tripwire(f_row)
    if bad:
        raise SystemExit(
            f"F-row appears to make a formal-result claim {bad!r}; "
            "reword the proposed row before H7."
        )
    for token, label in ((tick_id, "tick id"), (contract_id, "contract id"),
                         (f"owner: {owner}", "owner tag"),
                         ("consumes_surfaced:", "consumes_surfaced"),
                         ("dispatch_ledger:", "dispatch_ledger")):
        if token not in f_row:
            raise SystemExit(f"F-row missing {label}: {token}")
    ledger_error = _dispatch_ledger_error(f_row)
    if ledger_error:
        raise SystemExit(f"F-row dispatch_ledger invalid: {ledger_error}")
    consumed_error = _consumes_surfaced_error(f_row)
    if consumed_error:
        raise SystemExit(f"F-row consumes_surfaced invalid: {consumed_error}")
    research_error = _research_done_error(payload_dir, start, tick_id, contract_id)
    if research_error:
        raise SystemExit(f"research sufficiency preflight failed: {research_error}")

    declared = _json_load(payload_dir / "declared.json")
    sys.path.insert(0, str(REPO))
    from src.ztare.gates.commit_membrane_gate import evaluate  # noqa: PLC0415
    verdict = evaluate(f_row, declared, transition_type="tick_close",
                       substrate=frozen_substrate)
    if not verdict.official:
        raise SystemExit("L1/L2/L3 declaration preflight failed:\n"
                         + verdict.as_json())

    witnesses = _json_load(payload_dir / "witnesses.json")
    why_not = _json_load(payload_dir / "why_not.json")
    shape_error = _obligation_payload_error(start, witnesses, why_not)
    if shape_error:
        raise SystemExit(f"mandatory obligation discharge preflight failed: {shape_error}")
    obligations = list(start.get("mandatory_obligations") or [])
    discharge_policy = _start_discharge_policy(start)
    missing: list[str] = []
    changed = False
    for item in obligations:
        target = None
        if isinstance(witnesses.get(item), dict):
            target = witnesses[item]
        elif isinstance(why_not.get(item), dict):
            target = why_not[item]
        else:
            missing.append(item)
            continue
        desired_provenance = _desired_provenance(discharge_policy.get(item, {}))
        if target.get("provenance") != desired_provenance:
            target["provenance"] = desired_provenance
            changed = True
    if missing:
        raise SystemExit("mandatory obligations missing discharge payloads: "
                         + ", ".join(missing))
    if changed:
        if not write:
            raise SystemExit("payload needs judge:auto provenance; rerun without --no-write")
        _json_write(payload_dir / "witnesses.json", witnesses)
        _json_write(payload_dir / "why_not.json", why_not)

    decl_file = payload_dir / "declarations.txt"
    if not decl_file.is_file() or not decl_file.read_text(encoding="utf-8").strip():
        if not write:
            raise SystemExit("payload missing declarations.txt; rerun without --no-write")
        decl_file.write_text(_derive_declares(start) + "\n", encoding="utf-8")

    return _payload_hash(payload_dir)


def _run_tick_close(payload_dir: Path, tick_id: str, contract_id: str,
                    owner: str) -> subprocess.CompletedProcess[str]:
    cmd = [
        PY, "scripts/public/control/tick_close.py",
        "--tick-row", tick_id,
        "--contract-id", contract_id,
        "--owner", owner,
        "--f-row-body-file", str(payload_dir / "f_row.txt"),
        "--declared-json", (payload_dir / "declared.json").read_text(encoding="utf-8"),
        "--witnesses-json", (payload_dir / "witnesses.json").read_text(encoding="utf-8"),
        "--why-not-json", (payload_dir / "why_not.json").read_text(encoding="utf-8"),
    ]
    decl_file = payload_dir / "declarations.txt"
    if decl_file.is_file():
        cmd.extend(["--declare-file", str(decl_file)])
    return subprocess.run(cmd, cwd=REPO, text=True, capture_output=True,
                          timeout=240)


def _judge_pending(output: str) -> bool:
    low = output.lower()
    if "verdict is not 'pass' ('fail')" in low:
        return False
    if (
        "witness_sha mismatch" in low
        or "does not bind obligation" in low
        or "no chain-valid pass judge_verdict bound" in low
    ):
        return True
    return "judge:auto pending" in low or "no judge_verdict yet" in low


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tick-id", required=True)
    ap.add_argument("--contract-id", required=True)
    ap.add_argument("--payload-dir", required=True)
    ap.add_argument("--owner", default=os.environ.get("RD_OWNER", "codex:RD"))
    ap.add_argument("--wait-seconds", type=int, default=420)
    ap.add_argument("--poll-seconds", type=int, default=20)
    ap.add_argument("--no-write", action="store_true",
                    help="preflight only; do not add safe derived fields")
    ap.add_argument("--preflight-only", action="store_true")
    args = ap.parse_args()

    payload_dir = Path(args.payload_dir)
    if not payload_dir.is_absolute():
        payload_dir = REPO / payload_dir

    frozen_hash = _preflight(payload_dir, args.tick_id, args.contract_id,
                             args.owner, write=not args.no_write)
    print(json.dumps({
        "status": "preflight_ok",
        "payload_dir": str(payload_dir),
        "payload_sha256": frozen_hash,
        "tick_id": args.tick_id,
        "contract_id": args.contract_id,
    }, indent=2, sort_keys=True))
    if args.preflight_only:
        return 0

    deadline = time.time() + args.wait_seconds
    attempt = 0
    last = ""
    while True:
        attempt += 1
        if _payload_hash(payload_dir) != frozen_hash:
            raise SystemExit("payload changed after freeze; aborting before judge resubmit")
        proc = _run_tick_close(payload_dir, args.tick_id, args.contract_id,
                               args.owner)
        out = (proc.stdout or "") + (proc.stderr or "")
        last = out
        print(out, end="" if out.endswith("\n") else "\n")
        if proc.returncode == 0:
            print(json.dumps({"status": "closed", "attempt": attempt}, indent=2))
            return 0
        if not _judge_pending(out):
            print(json.dumps({"status": "blocked", "attempt": attempt}, indent=2))
            return proc.returncode
        if time.time() + args.poll_seconds > deadline:
            print(json.dumps({
                "status": "judge_pending_timeout",
                "attempt": attempt,
                "next": "rerun this same command; payload bytes are frozen",
            }, indent=2))
            return 1
        time.sleep(args.poll_seconds)


if __name__ == "__main__":
    raise SystemExit(main())
