"""Trace auditor — zero-authority telemetry reader.

Reads workspace telemetry/ledgers, emits typed findings, and (with --emit)
appends anomalies as rider rows to workspace/leaf_proposals.jsonl — the same
ledger the science-leaf riders use. Never edits code, never dispositions
anything, never writes any file that isn't the state snapshot or the rider
ledger.

CLI:
    python -m ztare.orchestrator.trace_auditor \\
        --project projects/arc3_ls20_gov [--emit] [--llm] [--run-log PATH]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ── constants ────────────────────────────────────────────────────────────────

STATE_FILE = "trace_auditor_state.json"
LEAF_PROPOSAL_LEDGER = "leaf_proposals.jsonl"
DEAD_LEAN_AUDIT_THRESHOLD = 3   # audits before lean/cert gap fires

# Files that are intentionally write-only (state/log/backup) — not dead letters.
# ponytail: single constant; add entries here when a new benign write-only file is introduced.
_DEAD_LETTER_EXEMPTIONS: frozenset[str] = frozenset({
    "trace_auditor_state.json",      # auditor own state — not a receipt
    "leaf_proposals.jsonl",          # rider ledger — consumed by strategy_office, not a receipt itself
    "visited_signatures.jsonl",      # bloom/dedup ledger, reader is the eval harness (not in src/ztare)
    "arc3_play_loop_receipts.jsonl", # written by scripts/public/control/arc3_play_loop.py, read externally
})

# Workspace jsonl/json paths that are genuinely terminal (human/external-only consumers).
# A path in this set is excluded from write-only flagging in check_file_seam_coverage.
# ponytail: seed with known-terminal receipts; default is to FLAG, not exempt.
_SEAM_EXEMPTIONS: frozenset[str] = frozenset({
    "phase_timings.jsonl",           # consumed by check_phase_cost_regression above
    "arc3_play_loop_receipts.jsonl", # human-readable play log, no internal reader needed
    "trace_auditor_state.json",      # auditor own state
    "leaf_proposals.jsonl",          # rider ledger consumed by strategy_office externally
    "visited_signatures.jsonl",      # eval harness, not in src/ztare
})

_ENVELOPE_CAUSES = frozenset({
    "receipt-citation", "field-validation", "missing field", "missing_field",
    "envelope", "formality", "schema", "turn_receipt", "receipt_ref",
    "missing proposal signature",
})


# ── helpers ───────────────────────────────────────────────────────────────────

def _now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8", errors="ignore"))
    except Exception:
        return {}


def _read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
            if isinstance(row, dict):
                rows.append(row)
        except Exception:
            pass
    return rows


def _read_state(ws: Path) -> dict:
    return _read_json(ws / STATE_FILE)


def _write_state(ws: Path, state: dict) -> None:
    (ws / STATE_FILE).write_text(
        json.dumps(state, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )


def _newest_log(ws: Path, run_log: Path | None) -> Path | None:
    if run_log and run_log.exists():
        return run_log
    logs = sorted(ws.glob("*.log"), key=lambda p: p.stat().st_mtime, reverse=True)
    return logs[0] if logs else None


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def _finding(
    check_id: str,
    verdict: str,
    witness: dict,
    note: str,
    recurrence: bool = False,
) -> dict:
    return {
        "check_id": check_id,
        "verdict": verdict,
        "witness": witness,
        "note": note,
        "recurrence": recurrence,
    }


# ── LAYER 1 detectors ────────────────────────────────────────────────────────

def check_dead_channel_constraints(ws: Path, state: dict) -> dict:
    """Anomaly if confirmed==0 AND provisional grew vs previous snapshot."""
    d = _read_json(ws / "derived_constraints.json")
    confirmed = int(d.get("confirmed_constraint_count") or 0)
    provisional = int(d.get("provisional_constraint_count") or 0)
    prev_provisional = int(state.get("prev_provisional_constraint_count") or 0)

    state["prev_provisional_constraint_count"] = provisional

    if confirmed == 0 and provisional > prev_provisional:
        return _finding(
            "dead_channel_constraints",
            "anomaly",
            witness={
                "confirmed_constraint_count": confirmed,
                "provisional_constraint_count": provisional,
                "prev_provisional_constraint_count": prev_provisional,
            },
            note=(
                f"Confirmed constraints stuck at 0 while provisional grew "
                f"{prev_provisional} → {provisional}. Confirmation channel may be dead."
            ),
        )
    return _finding(
        "dead_channel_constraints",
        "ok",
        witness={
            "confirmed_constraint_count": confirmed,
            "provisional_constraint_count": provisional,
        },
        note="Constraint channel healthy.",
    )


def check_dead_channel_lean(ws: Path, state: dict) -> dict:
    """Anomaly if lean feedback emitted blueprint but cert ledger empty for >3 audits."""
    receipt = _read_json(ws / "worldmodel_lean_feedback_receipt.json")
    has_blueprint = bool(receipt) and receipt.get("blueprint_ref")
    cert_path = ws / "invariant_certificates.jsonl"
    certs_empty = not cert_path.exists() or cert_path.stat().st_size == 0

    # increment counter only when the gap persists
    if has_blueprint and certs_empty:
        count = int(state.get("lean_gap_audit_count") or 0) + 1
    else:
        count = 0
    state["lean_gap_audit_count"] = count

    if has_blueprint and certs_empty and count > DEAD_LEAN_AUDIT_THRESHOLD:
        return _finding(
            "dead_channel_lean",
            "anomaly",
            witness={
                "blueprint_ref": str(receipt.get("blueprint_ref") or ""),
                "lean_gap_audit_count": count,
                "invariant_certificates_exists": cert_path.exists(),
            },
            note=(
                f"Lean feedback has blueprint_ref but invariant_certificates.jsonl "
                f"absent/empty for {count} consecutive audits. Proof pipeline stalled."
            ),
        )
    return _finding(
        "dead_channel_lean",
        "ok",
        witness={
            "has_blueprint": has_blueprint,
            "certs_empty": certs_empty,
            "lean_gap_audit_count": count,
        },
        note="Lean channel ok.",
    )


def check_dead_channel_probes(ws: Path, state: dict) -> dict:
    """Anomaly if capability registry includes probe tools but no recent probe receipts."""
    cap_path = ws / "leaf_workbench_capability_proposals.jsonl"
    rows = _read_jsonl(cap_path)
    probe_caps = [
        r for r in rows
        if "probe" in str(r.get("proposal", {}) or {}).lower()
        or "probe" in str(r.get("capability_id") or "").lower()
    ]

    receipt_dir = ws / "visible_cli_receipts"
    last_audit_ts = state.get("last_audit_ts")

    if probe_caps and receipt_dir.exists():
        probe_receipts = [
            p for p in receipt_dir.glob("*.json")
            if "probe" in p.name.lower()
            and (last_audit_ts is None or p.stat().st_mtime > _ts_to_epoch(last_audit_ts))
        ]
        if not probe_receipts:
            return _finding(
                "dead_channel_probes",
                "anomaly",
                witness={
                    "probe_capability_count": len(probe_caps),
                    "new_probe_receipts_since_last_audit": 0,
                },
                note=(
                    f"Capability registry has {len(probe_caps)} probe tool(s) but "
                    "zero probe receipts newer than last audit."
                ),
            )
    return _finding(
        "dead_channel_probes",
        "ok",
        witness={"probe_capability_count": len(probe_caps)},
        note="Probe channel ok (no probe caps or receipts present).",
    )


def _ts_to_epoch(ts: str | None) -> float:
    if not ts:
        return 0.0
    try:
        return datetime.fromisoformat(ts).timestamp()
    except Exception:
        return 0.0


def check_strike_economy(ws: Path, state: dict, run_log: Path | None) -> dict:
    """Anomaly if >50% of R1 rejections are envelope/formality causes."""
    log_path = _newest_log(ws, run_log)
    if log_path is None:
        return _finding(
            "strike_economy",
            "ok",
            witness={"log_found": False},
            note="No run log found; skipped.",
        )

    text = log_path.read_text(encoding="utf-8", errors="ignore")
    rejection_lines = [
        l.strip() for l in text.splitlines()
        if "R1 rejection" in l or "rejection:" in l.lower()
    ]
    if not rejection_lines:
        return _finding(
            "strike_economy",
            "ok",
            witness={"rejection_count": 0, "log": log_path.name},
            note="No R1 rejections in log.",
        )

    envelope_count = sum(
        1 for line in rejection_lines
        if any(kw in line.lower() for kw in _ENVELOPE_CAUSES)
    )
    science_count = len(rejection_lines) - envelope_count
    fraction = envelope_count / len(rejection_lines)

    verdict = "anomaly" if fraction > 0.5 else "ok"
    return _finding(
        "strike_economy",
        verdict,
        witness={
            "total_rejections": len(rejection_lines),
            "envelope_cause_count": envelope_count,
            "science_cause_count": science_count,
            "envelope_fraction": round(fraction, 3),
            "log": log_path.name,
        },
        note=(
            f"{envelope_count}/{len(rejection_lines)} rejections ({fraction:.0%}) "
            "are envelope/formality causes — majority should be science causes."
            if verdict == "anomaly"
            else f"{envelope_count}/{len(rejection_lines)} rejections are envelope causes."
        ),
    )


def check_disposition_skew(ws: Path, state: dict) -> dict:
    """Anomaly if rejected_unlowerable fraction > 0.5 over last 50 rows."""
    rows = _read_jsonl(ws / "strategy_experiment_executions.jsonl")
    window = rows[-50:] if len(rows) > 50 else rows
    if not window:
        return _finding(
            "disposition_skew",
            "ok",
            witness={"window_size": 0},
            note="No strategy experiment executions yet.",
        )
    rejected_ul = sum(1 for r in window if r.get("disposition") == "rejected_unlowerable")
    fraction = rejected_ul / len(window)
    verdict = "anomaly" if fraction > 0.5 else "ok"
    return _finding(
        "disposition_skew",
        verdict,
        witness={
            "window_size": len(window),
            "rejected_unlowerable": rejected_ul,
            "fraction": round(fraction, 3),
        },
        note=(
            f"rejected_unlowerable fraction {fraction:.0%} over last {len(window)} rows — "
            f"above 50% threshold."
            if verdict == "anomaly"
            else f"rejected_unlowerable fraction {fraction:.0%} — within threshold."
        ),
    )


def check_fallback_events(ws: Path, state: dict, run_log: Path | None) -> dict:
    """Note/anomaly if provider fallback fires when --no_model_fallback is expected."""
    log_path = _newest_log(ws, run_log)
    if log_path is None:
        return _finding(
            "fallback_events",
            "ok",
            witness={"log_found": False},
            note="No run log found; skipped.",
        )
    text = log_path.read_text(encoding="utf-8", errors="ignore")
    fallback_lines = [
        l.strip() for l in text.splitlines() if "Provider fallback engaged" in l
    ]
    no_fallback_declared = "no_model_fallback" in text.lower() or "DISABLE" in text

    count = len(fallback_lines)
    verdict = "anomaly" if count > 0 and no_fallback_declared else "ok"
    return _finding(
        "fallback_events",
        verdict,
        witness={
            "fallback_count": count,
            "no_model_fallback_declared": no_fallback_declared,
            "log": log_path.name,
        },
        note=(
            f"{count} fallback event(s) observed despite --no_model_fallback."
            if verdict == "anomaly"
            else f"{count} fallback event(s) — fallback not prohibited or none fired."
        ),
    )


def check_pack_boot_smoke(ws: Path, state: dict) -> dict:
    """Anomaly if visible_workbench_cli manifest exits non-zero or omits probe."""
    # ponytail: run manifest in a temp cwd that mimics a briefing pack workbench;
    # we don't actually build a full BriefingPack (that requires a real repo + LLM
    # briefing chain); we run it from the real source tree instead.
    try:
        repo_root = Path(__file__).resolve().parents[3]
        env = {**os.environ, "PYTHONPATH": str(repo_root / "src")}
        result = subprocess.run(
            [sys.executable, "-m", "ztare.common.visible_workbench_cli", "manifest"],
            capture_output=True, text=True, timeout=30, env=env, cwd=str(repo_root),
        )
        ok = result.returncode == 0
        probe_present = "probe" in (result.stdout or "").lower()
        verdict = "ok" if (ok and probe_present) else "anomaly"
        return _finding(
            "pack_boot_smoke",
            verdict,
            witness={
                "exit_code": result.returncode,
                "probe_in_manifest": probe_present,
                "stdout_chars": len(result.stdout),
            },
            note=(
                "Manifest OK and probe capability registered."
                if verdict == "ok"
                else (
                    f"Manifest exit={result.returncode}; "
                    f"probe_in_manifest={probe_present}. stderr: {result.stderr[:200]}"
                )
            ),
        )
    except Exception as exc:
        return _finding(
            "pack_boot_smoke",
            "anomaly",
            witness={"error": str(exc)},
            note=f"manifest subprocess failed: {exc}",
        )


def _build_src_index(src_root: Path, state: dict) -> dict[str, list[str]]:
    """Return {filename_stem: [module_paths]} index, cached by src-tree mtime.

    The index maps each *filename string* (e.g. "champion_materialization.jsonl")
    to the list of .py files in src_root that contain that string.  Built once per
    audit run via a single glob+grep pass; result is stored in state under a mtime
    key so repeat audits with an unchanged tree skip the scan.
    # ponytail: grep-once-per-audit strategy; per-file mtime would be more precise
    # but would require hashing every file — not worth it for an audit tool.
    """
    py_files = sorted(src_root.rglob("*.py"))
    if not py_files:
        return {}

    # Cache key: max mtime across all py files (cheap, single stat per file)
    max_mtime = max(p.stat().st_mtime for p in py_files)
    cache_key = f"src_index_mtime_{max_mtime:.3f}"
    cached = state.get(cache_key)
    if isinstance(cached, dict):
        return cached

    # Build index: for each py file, collect all *.jsonl / *_receipt*.json /
    # latest_*.json filename strings it contains.
    index: dict[str, list[str]] = {}
    receipt_pat = re.compile(
        r'["\']([^"\']*?(?:\.jsonl|_receipt[^"\']*\.json|latest_[^"\']+\.json))["\']'
    )
    for py in py_files:
        try:
            text = py.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        for m in receipt_pat.finditer(text):
            fname = Path(m.group(1)).name   # strip any path prefix
            index.setdefault(fname, [])
            rel = str(py.relative_to(src_root))
            if rel not in index[fname]:
                index[fname].append(rel)

    state[cache_key] = index
    return index


def check_dead_letter_receipts(ws: Path, state: dict, src_root: Path) -> dict:
    """Anomaly if a workspace ledger/receipt is written but no module in src reads it.

    Proxy for "dead letter": the filename appears in exactly ONE src module
    (the writer).  A file referenced by 2+ modules is considered read by at
    least one of them.  Files in _DEAD_LETTER_EXEMPTIONS are silently skipped.
    """
    # Collect workspace ledger/receipt candidates
    candidates: list[Path] = []
    candidates.extend(ws.glob("*.jsonl"))
    candidates.extend(ws.glob("*_receipt*.json"))
    candidates.extend(ws.glob("latest_*.json"))

    index = _build_src_index(src_root, state)

    dead: list[dict] = []
    dead_scored: list[dict] = []
    _7d = 7 * 24 * 3600
    now_ts = datetime.now(tz=timezone.utc).timestamp()
    for p in sorted(candidates):
        if not p.is_file() or p.stat().st_size == 0:
            continue
        name = p.name
        # Skip exemptions and pre-materialization backup files
        if name in _DEAD_LETTER_EXEMPTIONS or "_pre_materialization_" in name:
            continue
        refs = index.get(name, [])
        if len(refs) <= 1:
            dead.append({"file": name, "referencing_modules": refs})
            # observability-gain proxy
            fp = 0
            r7d = 0
            try:
                if name.endswith(".jsonl"):
                    lines = p.read_text(encoding="utf-8", errors="ignore").splitlines()
                    for line in reversed(lines):
                        line = line.strip()
                        if line:
                            fp = len(json.loads(line).keys())
                            break
                    cutoff = now_ts - _7d
                    r7d = sum(1 for line in lines if line.strip())
                    # count only lines; mtime of whole file as proxy for recency
                    r7d = r7d if p.stat().st_mtime >= cutoff else 0
                else:  # JSON
                    obj = json.loads(p.read_text(encoding="utf-8", errors="ignore"))
                    fp = len(obj) if isinstance(obj, dict) else 0
                    r7d = 1 if p.stat().st_mtime >= now_ts - _7d else 0
            except Exception:
                fp = r7d = 0
            dead_scored.append({
                "file": name,
                "score": fp * r7d,
                "field_path_count": fp,
                "rows_last_7d": r7d,
                "referencing_modules": refs,
            })

    if dead:
        top5 = sorted(dead_scored, key=lambda x: -x["score"])[:5]
        return _finding(
            "dead_letter_receipts",
            "anomaly",
            witness={
                "dead_letter_count": len(dead),
                "dead_letters": dead,
                "top_dead_letters": top5,
            },
            note=(
                f"{len(dead)} workspace ledger/receipt file(s) have no reader in src/ztare "
                f"(filename appears in ≤1 module); "
                f"top-5 ranked by observability proxy (distinct_field_paths × rows_last_7d): "
                + ", ".join(d["file"] for d in top5)
                + (" …" if len(dead) > 5 else "")
            ),
        )
    return _finding(
        "dead_letter_receipts",
        "ok",
        witness={"candidates_checked": len(candidates)},
        note="All workspace ledger/receipt files have ≥2 src module references (writer + reader).",
    )


def check_case_law_divergence(ws: Path, state: dict) -> dict:
    """Anomaly if a reconciliation row exists for a proposal but its ledger
    disposition is still 'rejected' (not yet 'superseded_implemented').

    This fires when the operator has recorded that content was implemented (via
    workspace/disposition_reconciliation.jsonl) but reconcile_dispositions has
    not yet been run, leaving the ledger lying about its state.
    """
    recon_path = ws / "disposition_reconciliation.jsonl"
    ledger_path = ws / "leaf_proposals.jsonl"

    if not recon_path.exists():
        return _finding(
            "case_law_divergence",
            "ok",
            witness={"recon_file_exists": False},
            note="No disposition_reconciliation.jsonl; skip.",
        )

    # Build reconciliation set
    recon_sigs: set[str] = set()
    for line in recon_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            r = json.loads(line)
            sig = str(r.get("proposal_sig") or "").strip()
            if sig:
                recon_sigs.add(sig)
        except Exception:
            pass

    if not recon_sigs:
        return _finding(
            "case_law_divergence",
            "ok",
            witness={"recon_entries": 0},
            note="Reconciliation file empty.",
        )

    # Check ledger for still-rejected proposals that have a recon entry
    divergent: list[str] = []
    if ledger_path.exists():
        for line in ledger_path.read_text(encoding="utf-8", errors="ignore").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
            except Exception:
                continue
            if not isinstance(r, dict):
                continue
            sig = str(r.get("proposal_signature") or "").strip()
            disp = str(r.get("disposition") or "")
            if sig and sig in recon_sigs and disp == "rejected":
                divergent.append(sig[:16])

    if divergent:
        return _finding(
            "case_law_divergence",
            "anomaly",
            witness={
                "divergent_sigs": list(dict.fromkeys(divergent)),   # dedup, preserve order
                "divergent_count": len(set(divergent)),
                "recon_entries": len(recon_sigs),
            },
            note=(
                f"{len(set(divergent))} proposal(s) have a reconciliation entry but are "
                "still marked 'rejected' in the ledger — case law diverges from reality. "
                "Run: strategy_office --reconcile --project <p>"
            ),
        )
    return _finding(
        "case_law_divergence",
        "ok",
        witness={"recon_entries": len(recon_sigs), "divergent_count": 0},
        note="All reconciliation entries have been applied to the ledger.",
    )


# ── CEGAR detectors ───────────────────────────────────────────────────────────

def check_phase_cost_regression(ws: Path, state: dict) -> dict:
    """Anomaly if any phase grows superlinearly in cost or consumes >50% of run time.

    Invariant: cost must scale with residual (work remaining), not history.
    """
    rows = _read_jsonl(ws / "phase_timings.jsonl")
    if not rows:
        return _finding(
            "phase_cost_regression",
            "ok",
            witness={"rows": 0},
            note="No phase_timings.jsonl; skipped.",
        )

    # Only top-level phases (depth==0); nested phases are sub-costs of their parent.
    top = [r for r in rows if isinstance(r.get("depth"), int) and r["depth"] == 0
           and isinstance(r.get("seconds"), (int, float)) and isinstance(r.get("phase"), str)]
    if not top:
        return _finding(
            "phase_cost_regression",
            "ok",
            witness={"rows": len(rows), "top_level_rows": 0},
            note="No depth-0 phase records found.",
        )

    # Group chronologically by phase name.
    from collections import defaultdict
    by_phase: dict[str, list[float]] = defaultdict(list)
    for r in top:
        by_phase[r["phase"]].append(float(r["seconds"]))

    # Per-run total (group rows into "runs" by segmenting on the earliest phase
    # restarting — simple: each contiguous block is a run).
    # ponytail: run-boundary detection via first phase of each run.
    run_totals: list[float] = []
    run_secs: dict[str, list[float]] = defaultdict(list)
    _seen_phases_this_run: set[str] = set()
    _cur_run_total = 0.0
    _cur_run: dict[str, float] = {}
    for r in top:
        ph = r["phase"]
        secs = float(r["seconds"])
        if ph in _seen_phases_this_run:
            # phase recycled → new run boundary
            run_totals.append(_cur_run_total)
            for p, s in _cur_run.items():
                run_secs[p].append(s)
            _cur_run_total = 0.0
            _cur_run = {}
            _seen_phases_this_run = set()
        _seen_phases_this_run.add(ph)
        _cur_run_total += secs
        _cur_run[ph] = _cur_run.get(ph, 0.0) + secs
    # flush last run
    run_totals.append(_cur_run_total)
    for p, s in _cur_run.items():
        run_secs[p].append(s)

    anomalies: list[dict] = []

    # (a) superlinear trend: last value > 2× first value across ≥3 runs
    for phase_name, series in run_secs.items():
        if len(series) >= 3 and series[0] > 0 and series[-1] > 2 * series[0]:
            anomalies.append({
                "phase": phase_name,
                "kind": "superlinear_trend",
                "first_s": round(series[0], 3),
                "last_s": round(series[-1], 3),
                "runs": len(series),
            })

    # (b) dominant phase: any phase consuming >50% of latest run total
    if run_totals:
        latest_total = run_totals[-1]
        if latest_total > 0:
            for phase_name, series in run_secs.items():
                if not series:
                    continue
                frac = series[-1] / latest_total
                if frac > 0.5:
                    anomalies.append({
                        "phase": phase_name,
                        "kind": "dominant_phase",
                        "seconds": round(series[-1], 3),
                        "fraction": round(frac, 3),
                        "run_total_s": round(latest_total, 3),
                    })

    if anomalies:
        notes = "; ".join(
            f"{a['phase']} {a['kind']}: {a.get('first_s','?')}→{a.get('last_s', a.get('fraction','?'))}"
            for a in anomalies
        )
        return _finding(
            "phase_cost_regression",
            "anomaly",
            witness={"anomalies": anomalies, "run_count": len(run_totals)},
            note=(
                f"{notes}. "
                "Invariant breached: cost must scale with residual, not history."
            ),
        )
    return _finding(
        "phase_cost_regression",
        "ok",
        witness={"phases_checked": len(run_secs), "run_count": len(run_totals)},
        note="Phase cost trends within bounds.",
    )


def check_alpha_blind_saturation(ws: Path, state: dict) -> dict:
    """Flags saturation receipts missing disambiguator, alpha_blind kind, and injective functors."""
    sat_rows = _read_jsonl(ws / "abstraction_saturation.jsonl")
    comp_rows = _read_jsonl(ws / "functor_compression_warnings.jsonl")

    issues: list[dict] = []

    # (a) saturation receipt missing saturation_kind field
    for i, r in enumerate(sat_rows):
        if "saturation_kind" not in r:
            issues.append({
                "kind": "missing_saturation_kind",
                "row_index": i,
                "row_keys": sorted(r.keys()),
                "note": "producer should adopt saturation_kind disambiguator (see ImageMaintainingSet.saturation_kind)",
            })

    # (b) alpha_blind saturation kind → raw growing, image flat → refine the quotient
    for i, r in enumerate(sat_rows):
        if r.get("saturation_kind") == "alpha_blind":
            issues.append({
                "kind": "alpha_blind",
                "functor": r.get("functor") or r.get("name") or f"row[{i}]",
                "note": "raw growing but image flat — quotient needs refinement (descend/refine trigger)",
            })

    # (c) injective functors from compression warnings (ratio ≥ 1.0 or > 0.9)
    for r in comp_rows:
        ratio = r.get("compression_ratio")
        if ratio is not None and float(ratio) >= 1.0:
            issues.append({
                "kind": "injective_functor",
                "functor": r.get("functor", "unknown"),
                "compression_ratio": ratio,
                "raw_size": r.get("raw_size"),
                "note": "ratio=1.0 → α compresses nothing, RAM duplication",
            })

    if not sat_rows and not comp_rows:
        return _finding(
            "alpha_blind_saturation",
            "ok",
            witness={"sat_rows": 0, "comp_rows": 0},
            note="No abstraction_saturation.jsonl or functor_compression_warnings.jsonl; skipped.",
        )

    if issues:
        return _finding(
            "alpha_blind_saturation",
            "anomaly",
            witness={"issues": issues, "sat_rows": len(sat_rows), "comp_rows": len(comp_rows)},
            note=(
                f"{len(issues)} saturation/compression issue(s): "
                + "; ".join(i["kind"] + " " + str(i.get("functor", "")) for i in issues[:3])
                + (" …" if len(issues) > 3 else "")
            ),
        )
    return _finding(
        "alpha_blind_saturation",
        "ok",
        witness={"sat_rows": len(sat_rows), "comp_rows": len(comp_rows), "issues": 0},
        note="Saturation receipts carry kind field; no alpha_blind or injective functors.",
    )


# Phase-death markers: a phase failed but the log continued (silent partial run).
_PHASE_DEATH_MARKERS = (
    "RESULT: FAILED",
    "pre-flight FAILED",
    "make[1]: ***",
)
# A subsequent-activity marker that proves the run kept going after the death.
_POST_DEATH_ACTIVITY_MARKERS = (
    "🚀 Launching:",
    "Launching: make",
    "OPTIMIZATION LOOP",
    "iter ",
    "mutator",
)


def check_loop_phase_death(
    ws: Path,
    state: dict,
    run_log: Path | None = None,
    log_paths: list[Path] | None = None,
) -> dict:
    """Anomaly if a phase-fatal marker appears and later phases kept running.

    Scans newest workspace log plus any explicit log_paths.
    """
    # Collect candidate logs
    candidates: list[Path] = []
    if log_paths:
        candidates.extend(p for p in log_paths if isinstance(p, Path) and p.exists())
    # newest log from ws
    newest = _newest_log(ws, run_log)
    if newest and newest not in candidates:
        candidates.append(newest)
    # also scan all *.log files in ws and sibling project workspaces
    for p in sorted(ws.glob("*.log"), key=lambda x: x.stat().st_mtime, reverse=True)[:10]:
        if p not in candidates:
            candidates.append(p)
    # sibling project workspaces
    projects_root = ws.parent.parent
    for proj_ws in sorted(projects_root.glob("*/workspace"), key=lambda x: x.name):
        for p in sorted(proj_ws.glob("*.log"), key=lambda x: x.stat().st_mtime, reverse=True)[:3]:
            if p not in candidates:
                candidates.append(p)

    if not candidates:
        return _finding(
            "loop_phase_death",
            "ok",
            witness={"logs_scanned": 0},
            note="No log files found; skipped.",
        )

    deaths: list[dict] = []
    for log_path in candidates:
        try:
            lines = log_path.read_text(encoding="utf-8", errors="ignore").splitlines()
        except Exception:
            continue
        death_lineno: int | None = None
        death_marker: str = ""
        post_death: str = ""
        for lineno, line in enumerate(lines, 1):
            if death_lineno is None:
                for marker in _PHASE_DEATH_MARKERS:
                    if marker in line:
                        death_lineno = lineno
                        death_marker = marker
                        break
            else:
                for activity in _POST_DEATH_ACTIVITY_MARKERS:
                    if activity in line:
                        post_death = line.strip()[:120]
                        break
                if post_death:
                    break
        if death_lineno is not None and post_death:
            deaths.append({
                "file": str(log_path),
                "death_line": death_lineno,
                "death_marker": death_marker,
                "post_death_activity": post_death,
            })

    if deaths:
        top = deaths[0]
        return _finding(
            "loop_phase_death",
            "anomaly",
            witness={"deaths": deaths, "logs_scanned": len(candidates)},
            note=(
                f"Phase death in {top['file']}:{top['death_line']} "
                f"('{top['death_marker']}') but later phases kept running — "
                f"silent partial run. Activity after death: '{top['post_death_activity']}'"
            ),
        )
    return _finding(
        "loop_phase_death",
        "ok",
        witness={"logs_scanned": len(candidates)},
        note="No silent partial runs detected in scanned logs.",
    )


_DEAD_GRAIN_SIZE_THRESHOLD = 20 * 1024 * 1024   # 20 MB
_DEAD_GRAIN_LINE_THRESHOLD = 10 * 1024           # 10 KB per line


def check_dead_grain_writers(ws: Path, state: dict) -> dict:
    """Heuristic: flags large workspace files with heavy per-line payloads.

    A visited_*.jsonl-style file >20MB with per-line size >10KB is writing at
    the wrong grain — move to packed persistence.  Read-only heuristic, not an error.
    """
    # ponytail: heuristic scan; we only stat + sample the first line to avoid
    # reading gigabytes. Upgrade path: replace with packed (e.g. sqlite, arrow).
    candidates: list[Path] = []
    # ws root
    candidates.extend(ws.glob("*.jsonl"))
    # subdirs (frontier/, etc.)
    for sub in ws.iterdir():
        if sub.is_dir():
            candidates.extend(sub.glob("*.jsonl"))
            candidates.extend(sub.glob("visited_*.jsonl"))

    heavy: list[dict] = []
    for p in candidates:
        try:
            size = p.stat().st_size
        except Exception:
            continue
        if size < _DEAD_GRAIN_SIZE_THRESHOLD:
            continue
        # sample first non-empty line
        try:
            line_size = 0
            with p.open("r", encoding="utf-8", errors="ignore") as fh:
                for raw in fh:
                    raw = raw.rstrip("\n")
                    if raw:
                        line_size = len(raw.encode("utf-8"))
                        break
        except Exception:
            line_size = 0
        if line_size >= _DEAD_GRAIN_LINE_THRESHOLD:
            heavy.append({
                "file": str(p),
                "size_mb": round(size / 1024 / 1024, 1),
                "sample_line_kb": round(line_size / 1024, 1),
                "note": "move to packed persistence (sqlite/arrow)",
            })

    if heavy:
        return _finding(
            "dead_grain_writers",
            "anomaly",
            witness={"heavy_files": heavy},
            note=(
                f"{len(heavy)} file(s) exceed 20MB with >10KB per line — "
                "per-item grain too coarse for flat JSONL: "
                + ", ".join(h["file"].split("/")[-1] + f" ({h['size_mb']}MB)" for h in heavy[:3])
                + (" …" if len(heavy) > 3 else "")
                + ". Move to packed persistence."
            ),
        )
    return _finding(
        "dead_grain_writers",
        "ok",
        witness={"candidates_checked": len(candidates)},
        note="No oversized per-item JSONL grain writers found.",
    )


def check_file_seam_coverage(
    src_root: Path,
    scripts_root: Path | None,
    state: dict,
    *,
    exemptions: frozenset[str] | None = None,
) -> dict:
    """Detect workspace paths that are WRITTEN but never READ in src/ + scripts/.

    Scans .py files under src_root (and scripts_root if given) for string
    literals matching workspace/*.jsonl or workspace/*.json paths.  Classifies
    each path as WRITTEN (near open(...,'a'/'w'), write_text, or a writer
    helper) vs READ (near read_text, open(...,'r'), json.load, _read_jsonl,
    _read_json, _read_all, or read_text).

    A path that is WRITTEN but NEVER READ is a dead-letter seam (the F4/F5
    class).  Paths in the exemptions set are silently skipped.

    Returns a finding with verdict "anomaly" when write-only paths exist.
    """
    _exemptions = (exemptions if exemptions is not None else _SEAM_EXEMPTIONS)
    _ws_path_re = re.compile(
        r'["\']([^"\']*?workspace[/\\][^"\']*?\.(?:jsonl|json))["\']'
    )
    # writer context: these patterns near a path string → it's a write site
    _writer_ctx = re.compile(
        r'open\s*\([^)]*["\'][aw]["\']|\.write_text\s*\(|\.open\s*\([^)]*["\'][aw]["\']'
        r'|_append_jsonl\s*\(|_append\s*\('
    )
    # reader context: near a path string → it's a read site
    _reader_ctx = re.compile(
        r'\.read_text\s*\(|open\s*\([^)]*["\']r["\']|json\.load[s]?\s*\('
        r'|_read_jsonl\s*\(|_read_json\s*\(|_read_all\s*\(|\.splitlines\s*\('
    )

    # Collect all .py files to scan
    py_files: list[Path] = list(src_root.rglob("*.py"))
    if scripts_root and scripts_root.exists():
        py_files.extend(scripts_root.rglob("*.py"))

    # Map: basename → {"written": bool, "read": bool}
    seam: dict[str, dict[str, bool]] = {}

    _WINDOW = 120   # chars on each side of the match to check for context

    for py in py_files:
        try:
            text = py.read_text(encoding="utf-8", errors="ignore")
        except Exception:  # noqa: BLE001
            continue
        for m in _ws_path_re.finditer(text):
            raw_path = m.group(1)
            # Normalize: strip leading path prefix, keep basename
            fname = Path(raw_path).name
            if not fname or fname in _exemptions:
                continue
            # skip intermediate path parts like 'workspace' alone
            if not (fname.endswith(".jsonl") or fname.endswith(".json")):
                continue
            rec = seam.setdefault(fname, {"written": False, "read": False})
            start = max(0, m.start() - _WINDOW)
            end = min(len(text), m.end() + _WINDOW)
            ctx = text[start:end]
            if _writer_ctx.search(ctx):
                rec["written"] = True
            if _reader_ctx.search(ctx):
                rec["read"] = True

    write_only = sorted(
        name for name, rec in seam.items()
        if rec["written"] and not rec["read"]
        and name not in _exemptions
    )

    if write_only:
        return _finding(
            "file_seam_coverage",
            "anomaly",
            witness={
                "write_only_paths": write_only,
                "write_only_count": len(write_only),
                "total_workspace_paths_seen": len(seam),
            },
            note=(
                f"{len(write_only)} workspace path(s) are WRITTEN but never READ "
                f"in src/ + scripts/ — dead-letter seam (F4/F5 class): "
                + ", ".join(write_only[:5])
                + (" …" if len(write_only) > 5 else "")
            ),
        )
    return _finding(
        "file_seam_coverage",
        "ok",
        witness={
            "write_only_count": 0,
            "total_workspace_paths_seen": len(seam),
        },
        note="All written workspace paths have at least one reader in src/ + scripts/.",
    )


def check_contract_surface_drift(src_root: Path, state: dict) -> dict:
    """Deterministic read-only detector: re-runs receipt-type coherence and
    zero-caller-organ checks at audit time.

    Findings are emitted as riders when --emit is active, identical to other
    detectors.  Never edits code; never touches anything outside src_root.

    Two sub-checks:
    (1) RECEIPT-TYPE: known types not taught in any prompt and not in the
        internal-only allowlist (mirrors test_contract_coherence.py §a).
    (2) ZERO-CALLER: exported entry points with no call site in src/ outside
        their definition file (mirrors §d).
    """
    # ponytail: inline imports so the detector is self-contained and does not
    # break the auditor when the ztare package is not on sys.path.
    findings_rows: list[str] = []
    riders: list[dict] = []

    # ── sub-check (1): receipt-type coherence ─────────────────────────────────
    try:
        import re as _re
        import sys as _sys
        _sys.path.insert(0, str(src_root.parent))
        from ztare.validator.worldmodel_typed_payload import (
            _KNOWN_CONTROL_RECEIPT_TYPES,
            worldmodel_typed_payload_contract_prompt,
        )
        from ztare.common.science_output_policy import SCIENCE_OUTPUT_POLICY
        from ztare.common.candidate_first_policy import candidate_first_policy_text

        _INTERNAL_ONLY = frozenset({
            "VISIBLE_WORKBENCH_DIAGNOSTIC",
            "LEAF_WORKBENCH_CAPABILITY_PROPOSAL_QUARANTINED",
        })
        _TOKEN_RE = _re.compile(r'\b([A-Z][A-Z0-9]{0,}(?:_[A-Z0-9]+){1,})\b')
        _all_text = "\n".join([
            worldmodel_typed_payload_contract_prompt(),
            SCIENCE_OUTPUT_POLICY.final_contract_text(),
            candidate_first_policy_text(),
        ])
        taught = set(_TOKEN_RE.findall(_all_text))
        known_set = set(_KNOWN_CONTROL_RECEIPT_TYPES)
        untaught = {
            t for t in known_set
            if t not in taught and t not in _INTERNAL_ONLY
        }
        if untaught:
            findings_rows.append(
                f"receipt_type_untaught:{sorted(untaught)}"
            )
    except Exception as exc:
        findings_rows.append(f"receipt_type_check_error:{exc}")

    # ── sub-check (2): zero-caller organs ────────────────────────────────────
    # ponytail: add entries here when a new entry point is exported from core/
    _MUST_HAVE_CALLERS: list[tuple[str, str]] = [
        ("ztare/validator/core/worldmodel_control_outcome.py", "build_worldmodel_control_only_eval"),
        ("ztare/validator/core/strategy_card_gate.py", "persist_strategy_card_discharges"),
    ]
    zero_callers: list[str] = []
    for def_file, fn_name in _MUST_HAVE_CALLERS:
        try:
            result = subprocess.run(
                ["grep", "-rn", fn_name, str(src_root)],
                capture_output=True,
                text=True,
                timeout=15,
            )
            lines = [
                line for line in result.stdout.splitlines()
                if def_file not in line and ".pyc" not in line
            ]
            if not lines:
                zero_callers.append(fn_name)
        except Exception as exc:
            findings_rows.append(f"zero_caller_check_error:{fn_name}:{exc}")

    if zero_callers:
        findings_rows.append(f"zero_caller_organs:{zero_callers}")

    if findings_rows:
        return _finding(
            "contract_surface_drift",
            "anomaly",
            witness={
                "untaught_types": sorted(untaught) if "untaught" in dir() else [],
                "zero_caller_organs": zero_callers,
                "sub_findings": findings_rows,
            },
            note=(
                "Contract surface drift detected: "
                + "; ".join(findings_rows[:3])
                + (" …" if len(findings_rows) > 3 else "")
            ),
        )
    return _finding(
        "contract_surface_drift",
        "ok",
        witness={
            "untaught_types": [],
            "zero_caller_organs": [],
        },
        note="Contract surfaces coherent: all known types taught in prompts; no zero-caller organs.",
    )


def fire_conjecture_rung(project_dir, findings: "list[dict]", state: dict) -> "list[dict]":
    """The self-extension rung: when a check that was FIXED recurs as an anomaly
    (recurrence=True — the existing tiers already tried and the failure came
    back), the system requisitions new abstractions for itself: abstract the
    seam and fire the isomorphism engine in the deanchor direction, carding
    surfaced structures as pre-registerable lifts. Mechanizes the 2026-07-11
    out-of-loop move (human said "metareason"/"research isomorphism"; four
    mother structures returned, all lifts of existing organs). Guardrails:
    fires ONCE per check_id ever (dedup ledger), n=3, model via
    ZTARE_CONJECTURE_MODEL (default gpt5.5 — cheap; set codex:gpt-5.6-sol for
    deep runs), disable with ZTARE_CONJECTURE_RUNG=0.
    """
    if os.environ.get("ZTARE_CONJECTURE_RUNG", "1") == "0":
        return []
    recurring = [f for f in findings if f.get("recurrence") and f.get("verdict") == "anomaly"]
    if not recurring:
        return []
    ws = Path(project_dir) / "workspace"
    ledger = ws / "conjecture_rung_ledger.jsonl"
    fired_ids = set()
    if ledger.exists():
        for line in ledger.read_text().splitlines():
            try:
                fired_ids.add(json.loads(line).get("check_id"))
            except Exception:  # noqa: BLE001
                pass
    out = []
    for f in recurring:
        cid = f["check_id"]
        if cid in fired_ids:
            continue
        owned = []
        try:
            # No-Frankenstein, mechanized: before requisitioning NEW
            # mathematics, ask the primitive-amnesia precheck whether an
            # owned organ already covers this seam (the precheck itself had
            # usage count 0 in the architecture index until 2026-07-12 —
            # the organ against forgetting was forgotten).
            from ztare.research_director.primitive_amnesia import precheck
            owned = [{"name": r.get("name"), "module": r.get("module"),
                      "when_to_use": r.get("when_to_use"), "score": r.get("score")}
                     for r in (precheck(
                         f"{cid}: {f.get('note','')[:200]}") or [])[:3]]
        except Exception:  # noqa: BLE001
            owned = []
        try:
            from ztare.research_director.research_isomorphism import (
                surface_for_research_ceiling)
            failure_state = {
                "constraint_class": (
                    f"recurring harness/organ failure '{cid}' that resists the "
                    f"existing repair tiers: {f.get('note', '')[:300]}"),
                "abstract_form": (
                    "a failure signature that returns after being fixed suggests "
                    "the repair addressed a property, not the identity; the "
                    "acting structure has not been named"),
                "home_field": "machine learning, program synthesis, AI evaluation harnesses",
                "witness": json.dumps(f.get("witness") or {})[:400],
            }
            isos = surface_for_research_ceiling(failure_state, n=3)
            row = {"schema": "ztare.conjecture_rung.v1", "check_id": cid,
                   "owned_primitives_first": owned,
                   "surfaced": len(isos or []),
                   "candidates": [{"theorem": i.theorem, "field": i.field,
                                    "mechanism": (i.mechanism or "")[:200]}
                                   for i in (isos or [])]}
        except Exception as exc:  # noqa: BLE001
            row = {"schema": "ztare.conjecture_rung.v1", "check_id": cid,
                   "surfaced": 0, "error": f"{type(exc).__name__}: {str(exc)[:150]}"}
        ledger.parent.mkdir(parents=True, exist_ok=True)
        with ledger.open("a") as fh:
            fh.write(json.dumps(row) + chr(10))
        out.append(row)
    return out


def check_recurrence(findings: list[dict], state: dict) -> list[dict]:
    """Tag findings recurrence=True if they previously fired and were marked fixed."""
    last_verdicts = state.get("last_verdicts") or {}
    fixed = state.get("fixed_checks") or {}
    out = []
    for f in findings:
        cid = f["check_id"]
        prev = last_verdicts.get(cid)
        was_fixed = fixed.get(cid, False)
        recurs = was_fixed and f["verdict"] == "anomaly"
        out.append({**f, "recurrence": recurs})
        last_verdicts[cid] = f["verdict"]
        if f["verdict"] == "ok":
            fixed[cid] = True          # mark as fixed when it clears
        elif f["verdict"] == "anomaly" and was_fixed:
            fixed[cid] = False         # reset fixed flag now it's back
    state["last_verdicts"] = last_verdicts
    state["fixed_checks"] = fixed
    return out


# ── LAYER 2 LLM lens (optional) ──────────────────────────────────────────────

def llm_lens(findings: list[dict], ws: Path, run_log: Path | None) -> list[dict]:
    """One LLM call; degrades gracefully on missing creds. Returns extra findings."""
    try:
        from ztare.common.llm_runtime import LLMRuntime, resolve_model_id
    except Exception:
        return []

    log_path = _newest_log(ws, run_log)
    log_tail = ""
    if log_path:
        lines = log_path.read_text(encoding="utf-8", errors="ignore").splitlines()
        log_tail = "\n".join(lines[-80:])

    anomalies = [f for f in findings if f["verdict"] == "anomaly"]
    if not anomalies:
        return []

    prompt = (
        "You are a trace auditor reviewing deterministic findings from an automated "
        "research loop. Findings (JSON):\n"
        + json.dumps(anomalies, indent=2)
        + "\n\nLast 80 lines of newest run log:\n"
        + log_tail
        + "\n\nReturn JSON list of additional findings: "
        '[{"check_id":"llm_<name>","verdict":"ok"|"anomaly","note":"...","witness":{}}]. '
        "Return [] if nothing to add."
    )
    try:
        rt = LLMRuntime()
        model_id = resolve_model_id("anthropic")
        resp = rt.call_text(prompt, model_id=model_id, max_tokens=1000, request_label="trace_auditor_llm")
        raw = json.loads(resp.text or "[]")
        if not isinstance(raw, list):
            return []
        out = []
        for r in raw:
            if isinstance(r, dict) and r.get("check_id"):
                out.append({
                    **r,
                    "recurrence": False,
                    "provenance": "llm_lens",
                })
        return out
    except Exception as exc:
        return [{
            "check_id": "llm_lens_error",
            "verdict": "ok",
            "witness": {"error": str(exc)},
            "note": f"LLM lens unavailable: {exc}",
            "recurrence": False,
            "provenance": "llm_lens",
        }]


# ── LAYER 3 emission ──────────────────────────────────────────────────────────

def _emit_rider(ws: Path, finding: dict) -> dict:
    """Append one anomaly finding as a rider row to leaf_proposals.jsonl."""
    ledger = ws / LEAF_PROPOSAL_LEDGER
    row = {
        "schema": "ztare-leaf-proposal-v1",
        "proposed_change": (
            f"[trace_auditor:{finding['check_id']}] {finding['note']}"
        ),
        "rationale": json.dumps(finding["witness"], sort_keys=True, default=str),
        "observed_friction_refs": [str(ws / STATE_FILE)],
        "category": "process_health",
        "provenance": "trace_auditor",
        "source": "trace_auditor",
        "check_id": finding["check_id"],
        "emitted_utc": _now_utc(),
        "recurrence": finding.get("recurrence", False),
        "disposition": "open",
    }
    ledger.parent.mkdir(parents=True, exist_ok=True)
    with ledger.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, sort_keys=True) + "\n")
    return row


# ── main ──────────────────────────────────────────────────────────────────────

def check_champion_surface_conservation(ws: Path, state: dict) -> dict:
    """Category contract: every declared champion-surface field must resolve
    through the LIVE carrier chain (test_model.py or its PATCH_BASE hop).
    Resolving only via a pre-materialization snapshot means the lineage
    silently dropped the field on promotion (GOAL_PREDICATE incident,
    2026-07-11: neither the patch carrier nor its base restated the
    champion's goal hypothesis — a planner steering to the wrong category
    of goal went undetected until an out-of-loop conductor caught it).
    """
    check_id = "champion_surface_conservation"
    surface = ("GOAL_PREDICATE",)  # extend as fields become load-bearing
    proj = ws.parent
    tm = proj / "test_model.py"
    if not tm.exists():
        return _finding(check_id, "ok", {}, "no test_model.py — nothing to conserve")
    import re as _re
    src = tm.read_text(encoding="utf-8", errors="ignore")
    chain = [src]
    m = _re.search(r'"source_ref"\s*:\s*"([^"]+)"', src)
    if m:
        base = proj / m.group(1)
        if not base.exists():
            base = ws / Path(m.group(1)).name
        if base.exists():
            chain.append(base.read_text(encoding="utf-8", errors="ignore"))
    degraded = [f for f in surface if not any(f in c for c in chain)]
    if not degraded:
        return _finding(check_id, "ok", {}, "champion surface intact through carrier chain")
    return _finding(
        check_id, "anomaly",
        {"missing_fields": degraded, "chain_len": len(chain)},
        f"champion surface field(s) {degraded} not resolvable through the live "
        "carrier chain — only recoverable from snapshots; lineage dropped the "
        "field on promotion. Require candidates/patches to restate or inherit it.",
    )


def check_stale_latest_artifacts(ws: Path, state: dict) -> dict:
    """A `latest_*.json` artifact older than the newest ledger write is a lie:
    downstream readers (briefing providers, leaves) treat it as current.
    Caught manually 2026-07-11: harness_weakness receipts frozen 2 days while
    every candidate was pre-judge-blocked on a residual the leaf never saw —
    computed-but-never-persisted feedback is invisible to the file-seam
    detector (no file appears), so freshness must be checked directly.
    """
    check_id = "stale_latest_artifacts"
    latests = sorted(ws.glob("latest_*.json"))
    if not latests:
        return _finding(check_id, "ok", {}, "no latest_* artifacts")
    ledgers = [p for p in ws.glob("*.jsonl") if p.stat().st_size > 0]
    if not ledgers:
        return _finding(check_id, "ok", {}, "no ledgers to compare against")
    newest_ledger_mtime = max(p.stat().st_mtime for p in ledgers)
    STALE_S = 6 * 3600  # ponytail: half a work-session; tune if noisy
    stale = [p.name for p in latests
             if newest_ledger_mtime - p.stat().st_mtime > STALE_S]
    if not stale:
        return _finding(check_id, "ok", {}, f"{len(latests)} latest_* artifacts fresh")
    return _finding(
        check_id, "anomaly",
        {"stale": stale, "lag_hours_threshold": 6},
        f"latest_* artifacts stale vs active ledgers: {stale[:4]} — readers "
        "are consuming outdated state as current; find the writer that died.",
    )


def check_gate_achievability(ws: Path, state: dict, src_root: "Path | None" = None) -> dict:
    """Identity-first ceiling detection (2026-07-11 incident: holdout rollout
    walked off segment boundaries; 23 distinct candidates pinned at exactly
    4/16, never 5-15 — the gate was unpassable by construction).

    Category discipline: a score PLATEAU is a property, not the failure's
    identity — legit plateaus exist (shared lineage, quantized scores). The
    identity is "max-achievable under the artifact's real structure is below
    threshold", and its proof is an ACHIEVABILITY RECEIPT (planted oracle
    reaching threshold). So: plateau alone -> info; plateau AND no oracle
    receipt newer than the gate mechanics -> anomaly saying RUN THE ORACLE.
    """
    check_id = "gate_achievability"
    import json as _json
    cm = ws / "candidate_memory.json"
    if not cm.exists():
        return _finding(check_id, "ok", {}, "no candidate memory")
    try:
        d = _json.loads(cm.read_text())
        recs = d if isinstance(d, list) else d.get("records", [])
    except Exception:  # noqa: BLE001
        return _finding(check_id, "ok", {}, "candidate memory unreadable")
    by_sha: dict = {}
    for r in recs:
        sha, hd = r.get("sha"), r.get("holdout_depth")
        if sha and isinstance(hd, int):
            by_sha[sha] = hd
    if len(by_sha) < 8:
        return _finding(check_id, "ok", {}, f"only {len(by_sha)} distinct candidates")
    vals = list(by_sha.values())
    top = max(vals)
    from collections import Counter
    mode, n_mode = Counter(v for v in vals if v > 0).most_common(1)[0] if any(v > 0 for v in vals) else (0, 0)
    plateau = n_mode >= 8 and 0 < mode < top and not any(mode < v < top for v in vals)
    if not plateau:
        return _finding(check_id, "ok", {}, "no sub-max plateau across distinct candidates")
    # plateau exists — is there a fresh achievability receipt?
    rec_path = ws / "gate_achievability_receipts.jsonl"
    gates_py = (src_root or Path(__file__).resolve().parents[1]) / "worldmodel" / "gates.py"
    fresh = rec_path.exists() and (
        not gates_py.exists() or rec_path.stat().st_mtime >= gates_py.stat().st_mtime)
    if fresh:
        return _finding(check_id, "ok",
                        {"plateau_value": mode, "n_candidates": n_mode},
                        "plateau present but achievability receipt is fresh — legit constraint")
    return _finding(
        check_id, "anomaly",
        {"plateau_value": mode, "n_distinct_candidates_at_plateau": n_mode,
         "max_observed": top, "gap_values_never_seen": f"({mode},{top})"},
        f"{n_mode} distinct candidates pinned at {mode} with nothing in ({mode},{top}) "
        "and no fresh achievability receipt — run a planted oracle against this gate "
        "before attributing the plateau to physics or solver quality.",
    )


def check_alpha_measurability(ws: Path, state: dict) -> dict:
    """Property-vs-invariant discipline for the champion law: a PORTABLE law
    must factor through the state quotient — equal-grid states must predict
    identically regardless of the replay clock. The bank supplies the
    discriminating pairs for free (same grid witnessed at different t across
    sessions). 2026-07-11: 188 such states existed while a t-keyed champion
    fit trajectories extensionally; this scan would have flagged it days
    before the holdout did. Violations are lawful ONLY under a lawful_time
    rubric AND heldout ratification — the check surfaces the choice.
    """
    check_id = "alpha_measurability"
    import json as _json
    from collections import defaultdict
    proj = ws.parent
    bank = proj / "raw" / "episodes" / "episode_001.jsonl"
    tm = proj / "test_model.py"
    if not bank.exists() or not tm.exists():
        return _finding(check_id, "ok", {}, "no bank or champion")
    try:
        from ztare.worldmodel.evidence_consolidation import _load_carrier_from_source
        from ztare.worldmodel.planner import as_predictor
        pred = as_predictor(_load_carrier_from_source(tm.read_text(), str(tm), proj))
        by_grid = defaultdict(set)
        for line in bank.read_text().splitlines():
            if line.strip():
                r = _json.loads(line)
                by_grid[_json.dumps(r["s"])].add(r["t"])
        pairs = [(g, sorted(ts)) for g, ts in by_grid.items() if len(ts) > 1]
        viol = probes = 0
        for g, ts in pairs[:300]:  # ponytail: bounded scan, plenty for a signal
            sg = tuple(tuple(row) for row in _json.loads(g))
            for a in range(4):
                outs = {_json.dumps(pred(sg, a, t)) for t in ts[:4]}
                probes += 1
                if len(outs) > 1:
                    viol += 1
        if not viol:
            return _finding(check_id, "ok", {"probes": probes},
                            f"law factors through state quotient ({probes} probes)")
        return _finding(
            check_id, "anomaly",
            {"violations": viol, "probes": probes, "multi_t_states": len(pairs)},
            f"champion predicts differently for equal grids at different t "
            f"({viol}/{probes} probes) — extensional trajectory fit suspected; "
            "require state-encoded clock or lawful_time + heldout ratification.",
        )
    except Exception as exc:  # noqa: BLE001
        return _finding(check_id, "ok", {}, f"scan unavailable: {str(exc)[:80]}")


_INDEX_MD_ROW_RE = re.compile(
    r"^\|\s*\*{0,2}([^|*`]+?)\*{0,2}\s*\|\s*`((?:src|scripts)/[^`]+)`\s*\|"
    r"\s*([^|]+?)\s*\|"
)
_LAST_USED_RE = re.compile(r"^(?:never|\d{4}-\d{2}-\d{2})$")

_ORGAN_LIVENESS_CAP = 8   # max items per list before truncation


def _parse_index_md(index_path: Path) -> list[dict]:
    """Return list of {id, path, impact} for rows with src/ or scripts/ paths.

    Parses defensively: skips malformed rows, counts them in returned list tail.
    Row format (variable columns, pipe-delimited markdown table):
      | **ID** | `src/...path...` | impact | [last_used] | [description] | ...
    The impact column is always col[2]; last_used may or may not be present at col[3].
    """
    if not index_path.exists():
        return []
    organs = []
    malformed = 0
    for line in index_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        m = _INDEX_MD_ROW_RE.match(line.strip())
        if not m:
            continue
        organ_id = m.group(1).strip().strip("*").strip()
        path = m.group(2).strip()
        try:
            impact = int(m.group(3))
        except ValueError:
            malformed += 1
            continue
        if not organ_id or not path:
            malformed += 1
            continue
        organs.append({"id": organ_id, "path": path, "impact": impact})
    if malformed:
        organs.append({"_malformed_count": malformed})   # sentinel for witness
    # ponytail: dedup by id, keep first occurrence (INDEX.md may have dup rows)
    seen: set[str] = set()
    deduped: list[dict] = []
    for o in organs:
        if "_malformed_count" in o:
            deduped.append(o)
            continue
        if o["id"] not in seen:
            seen.add(o["id"])
            deduped.append(o)
    return deduped


def _build_import_index(src_root: Path, scripts_root: Path | None) -> dict[str, set[str]]:
    """One-pass: map dotted_module -> set of relative file paths that import it.

    Cached in state is too complex here (state not passed); caller caches the
    result locally for the duration of one check call.
    # ponytail: single grep pass per audit; per-file incremental would be overkill.
    """
    import_re = re.compile(r"(?:from|import)\s+([\w.]+)")
    py_files = list(src_root.rglob("*.py"))
    if scripts_root and scripts_root.exists():
        py_files.extend(scripts_root.rglob("*.py"))
    module_to_files: dict[str, set[str]] = {}
    for py in py_files:
        if ".pyc" in str(py):
            continue
        try:
            text = py.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        rel = str(py)
        for m in import_re.finditer(text):
            mod = m.group(1)
            module_to_files.setdefault(mod, set()).add(rel)
    return module_to_files


def check_organ_liveness(
    ws: Path,
    state: dict,
    src_root: Path,
    scripts_root: Path | None = None,
) -> dict:
    """BUILT ≠ WIRED ≠ FIRED: surface organs that are built but not called or observed firing.

    Reads src/ztare/architecture_index/INDEX.md. For each row whose module path
    exists under src/ (or scripts/), checks:

    (a) WIRED: the module is imported somewhere outside itself and outside tests/.
        Method: single-pass import index over src/ + scripts/ .py files; match
        on dotted module name (e.g. ztare.gates.g_circ).

    (b) FIRED: a first-fire receipt row exists in
        workspace/organ_first_fire.jsonl — the convention file this check
        creates/seeds.  Schema per row:
            {"organ": "<organ_id>", "fired_at": "<iso-utc>",
             "receipt_ref": "<workspace-relative path or description>"}
        Alternatively, the organ's module stem appears in a workspace receipt
        file listed in the row's receipt_ref.  Append rows ONLY for organs you
        can verify fired from existing on-disk receipts.

    Verdict: "anomaly" when BUILT-not-WIRED list OR WIRED-not-FIRED list is
    non-empty.  Both witness lists are capped at _ORGAN_LIVENESS_CAP items
    with an explicit count of dropped items — no silent truncation.
    """
    check_id = "organ_liveness"

    # ── 1. Parse INDEX.md ────────────────────────────────────────────────────
    index_path = src_root.parent / "ztare" / "architecture_index" / "INDEX.md"
    if not index_path.exists():
        # Try relative to src_root itself
        index_path = src_root / "architecture_index" / "INDEX.md"
    raw_organs = _parse_index_md(index_path)
    malformed_count = 0
    # Pull out sentinel if present
    organs: list[dict] = []
    for o in raw_organs:
        if "_malformed_count" in o:
            malformed_count = o["_malformed_count"]
        else:
            organs.append(o)

    # Filter to organs whose module file actually exists
    repo_root = src_root.parent.parent   # src/ztare -> src -> repo
    present = [o for o in organs if (repo_root / o["path"]).exists()]

    if not present:
        return _finding(
            check_id, "ok",
            {"organs_parsed": len(organs), "organs_on_disk": 0, "malformed_rows": malformed_count},
            "No indexed organs found on disk; INDEX.md may be absent or format changed.",
        )

    # ── 2. Build import index (single pass) ──────────────────────────────────
    import_idx = _build_import_index(src_root, scripts_root)

    def _callers(path_str: str) -> set[str]:
        """Return set of files importing this module, excluding self + tests/."""
        mod_path = Path(path_str)
        parts = mod_path.with_suffix("").parts
        if parts and parts[0] == "src":
            parts = parts[1:]
        dotted = ".".join(parts)
        callers = import_idx.get(dotted, set())
        return {c for c in callers if path_str not in c and "tests/" not in c and "tests\\" not in c}

    # ── 3. Load first-fire convention ────────────────────────────────────────
    fire_ledger = ws / "organ_first_fire.jsonl"
    fired_ids: set[str] = set()
    if fire_ledger.exists():
        for line in fire_ledger.read_text(encoding="utf-8", errors="ignore").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
                organ = str(r.get("organ") or "").strip()
                if organ:
                    fired_ids.add(organ)
            except Exception:
                pass

    # ── 4. Classify ──────────────────────────────────────────────────────────
    built_not_wired: list[str] = []
    wired_not_fired: list[str] = []

    for o in present:
        callers = _callers(o["path"])
        wired = bool(callers)
        fired = o["id"] in fired_ids
        if not wired:
            built_not_wired.append(o["id"])
        elif not fired:
            wired_not_fired.append(o["id"])

    # ── 5. Cap with honest overflow ──────────────────────────────────────────
    cap = _ORGAN_LIVENESS_CAP

    def _cap(lst: list[str]) -> tuple[list[str], int]:
        dropped = max(0, len(lst) - cap)
        return lst[:cap], dropped

    bnw_capped, bnw_dropped = _cap(built_not_wired)
    wnf_capped, wnf_dropped = _cap(wired_not_fired)

    total_anomalies = len(built_not_wired) + len(wired_not_fired)

    witness = {
        "organs_checked": len(present),
        "built_not_wired_count": len(built_not_wired),
        "built_not_wired": bnw_capped,
        "built_not_wired_overflow": bnw_dropped,
        "wired_not_fired_count": len(wired_not_fired),
        "wired_not_fired": wnf_capped,
        "wired_not_fired_overflow": wnf_dropped,
        "fired_ids_in_ledger": len(fired_ids),
        "malformed_index_rows": malformed_count,
    }

    if total_anomalies:
        bnw_note = (
            f"{len(built_not_wired)} BUILT-not-WIRED"
            + (f" ({bnw_dropped} more not shown)" if bnw_dropped else "")
            + (f": {', '.join(bnw_capped[:4])}" + (" …" if len(bnw_capped) > 4 else "")
               if bnw_capped else "")
        )
        wnf_note = (
            f"{len(wired_not_fired)} WIRED-not-FIRED"
            + (f" ({wnf_dropped} more not shown)" if wnf_dropped else "")
            + (f": {', '.join(wnf_capped[:4])}" + (" …" if len(wnf_capped) > 4 else "")
               if wnf_capped else "")
        )
        return _finding(
            check_id, "anomaly", witness,
            f"Orphaned organs detected — {bnw_note}; {wnf_note}. "
            "Add import callers for BUILT-not-WIRED; append organ_first_fire.jsonl "
            "row for WIRED-not-FIRED once first-fire is confirmed.",
        )

    return _finding(
        check_id, "ok", witness,
        f"All {len(present)} indexed organs wired and have first-fire receipt.",
    )


def run_audit(
    project: str | Path,
    *,
    emit: bool = False,
    llm: bool = False,
    run_log: Path | None = None,
    src_root: Path | None = None,
    scripts_root: Path | None = None,
) -> dict:
    project_dir = Path(project).resolve()
    ws = project_dir / "workspace"
    _src_root = src_root or Path(__file__).resolve().parents[3] / "src" / "ztare"
    _scripts_root = scripts_root or Path(__file__).resolve().parents[3] / "scripts"

    state = _read_state(ws)
    state.setdefault("audit_count", 0)
    state["audit_count"] = int(state["audit_count"]) + 1
    state["last_audit_ts"] = _now_utc()

    findings: list[dict] = [
        check_dead_channel_constraints(ws, state),
        check_dead_channel_lean(ws, state),
        check_dead_channel_probes(ws, state),
        check_strike_economy(ws, state, run_log),
        check_disposition_skew(ws, state),
        check_fallback_events(ws, state, run_log),
        check_pack_boot_smoke(ws, state),
        check_dead_letter_receipts(ws, state, _src_root),
        check_case_law_divergence(ws, state),
        # CEGAR detectors
        check_phase_cost_regression(ws, state),
        check_alpha_blind_saturation(ws, state),
        check_loop_phase_death(ws, state, run_log),
        check_dead_grain_writers(ws, state),
        # file-seam detector (F4/F5 class: written but never read)
        check_file_seam_coverage(_src_root, _scripts_root, state),
        # contract coherence
        check_contract_surface_drift(_src_root, state),
        check_champion_surface_conservation(ws, state),
        check_stale_latest_artifacts(ws, state),
        check_gate_achievability(ws, state),
        check_alpha_measurability(ws, state),
        check_organ_liveness(ws, state, _src_root, _scripts_root),
    ]

    findings = check_recurrence(findings, state)
    conjecture_rows = fire_conjecture_rung(project_dir, findings, state)
    if conjecture_rows:
        for row in conjecture_rows:
            print(f"[trace_auditor:conjecture_rung] {row['check_id']} -> "
                  f"{row.get('surfaced', 0)} structures surfaced")

    if llm:
        findings.extend(llm_lens(findings, ws, run_log))

    state["last_audit_findings"] = [f["check_id"] + "=" + f["verdict"] for f in findings]
    _write_state(ws, state)

    emitted: list[dict] = []
    if emit:
        for f in findings:
            if f["verdict"] == "anomaly":
                emitted.append(_emit_rider(ws, f))

    return {
        "schema": "ztare-trace-auditor-v1",
        "audit_count": state["audit_count"],
        "audited_utc": state["last_audit_ts"],
        "project": str(project_dir),
        "findings": findings,
        "emitted_rider_count": len(emitted),
        "emitted_riders": emitted,
    }


def _cli() -> None:
    parser = argparse.ArgumentParser(
        prog="ztare.orchestrator.trace_auditor",
        description="Zero-authority telemetry auditor for ztare projects.",
    )
    parser.add_argument("--project", required=True, help="Path to project directory")
    parser.add_argument("--emit", action="store_true", help="Append anomalies to leaf_proposals.jsonl")
    parser.add_argument("--llm", action="store_true", help="Run optional LLM lens (default OFF)")
    parser.add_argument("--run-log", default=None, help="Explicit run log path")
    args = parser.parse_args()

    run_log = Path(args.run_log) if args.run_log else None
    result = run_audit(args.project, emit=args.emit, llm=args.llm, run_log=run_log)

    print(json.dumps(result, indent=2, sort_keys=True, default=str))
    anomalies = [f for f in result["findings"] if f["verdict"] == "anomaly"]
    print(
        f"\n── {len(result['findings'])} checks: "
        f"{len(result['findings']) - len(anomalies)} ok / {len(anomalies)} anomaly "
        f"{'(--emit: ' + str(result['emitted_rider_count']) + ' riders written)' if args.emit else ''}",
        file=sys.stderr,
    )


if __name__ == "__main__":
    _cli()
