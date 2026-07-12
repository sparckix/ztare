"""Per-run failure-mode diagnostics — the run-level OBSERVABILITY epilogue.

A governed solve records every move attempt (move / outcome / error_class / notes / wallclock_s / run_tag) to
`solver_lane_attempts.db`, but a run only ever PRINTED an opaque `N/M closed`. When a run closes nothing the
operator had to hand-query SQLite to learn *why* (the 2026-06-20 incident: 5 rungs, 0 closures — the real cause,
100% `unknown identifier` from a namespace-context bug, was invisible). This module reads those attempts back and
SURFACES the failure mode with a headline verdict, so a run says e.g. "STRUCTURAL — 92% unknown-identifier (scope
bug, not hard math)" instead of "0/5 closed".

Two surfaces:
  • `summarize_run(...)` / `render(...)` — call as an epilogue at the end of a run (filter by run_tag).
  • CLI: `python -m ztare.leanmill.run_diagnostics --run-tag T` or `--window-min 70`.

NO soundness surface — read-only over telemetry; it changes what the operator SEES, never a verdict.
"""
from __future__ import annotations

import os
import json
import sqlite3
from collections import Counter
from pathlib import Path

_REPO = Path(__file__).resolve().parents[3]
_DEFAULT_DB = _REPO / "analytics/public/queries/solver_lane_attempts.db"
_DEFAULT_LEAN_ROOT = _REPO / "ztare_proofs"

# Refine the coarse `other_error` bucket from the attempt notes — THIS is what makes a scope/context bug visible
# (it was buried under `other_error` before). Ordered: first match wins. (substring, refined_class, is_structural).
# "structural" = the apparatus never got a clean shot at the MATH (scope/syntax/context) — a fixable infra/harness
# signal, NOT genuine difficulty. "genuine" = an honest proof gap (unsolved_goals / no_advance).
_REFINE = [
    ("unknown identifier", "unknown_identifier", True),
    ("unknown constant", "unknown_identifier", True),
    ("unknown namespace", "unknown_identifier", True),
    ("function expected", "unknown_identifier", True),   # a missing-def applied to args (the namespace-bug shape)
    ("ambiguous", "ambiguous_name", True),
    ("unexpected token", "syntax_error", True),
    ("unexpected identifier", "syntax_error", True),
    ("expected ", "syntax_error", True),
    ("type mismatch", "type_mismatch", True),
    ("failed to synthesize", "instance_missing", True),
    ("unsolved goals", "unsolved_goals", False),
    ("linarith failed", "tactic_failed", False),
    ("simp made no progress", "tactic_failed", False),
    ("ring failed", "tactic_failed", False),
    ("statement-false", "statement_false", False),
    # governance rejections — the firewall WORKING (a bad/altered/laundered proof correctly blocked), NOT a
    # scope/context bug. The apparatus got a clean shot; the agent produced something the firewall caught.
    ("signature_altered", "governance_block", False),
    ("statement_integrity", "governance_block", False),
    ("laundering", "governance_block", False),
    ("target_signature", "governance_block", False),
    ("does not follow", "lemma_no_compose", False),
    ("goal does not follow", "lemma_no_compose", False),
    # native_hammer SKIPPED a goal it already failed this run — a deterministic no-op, NOT a real failure or a
    # structural bug. Surfacing it as `other_error` (its old fate) inflated the failure count with noise.
    ("in-run dedup", "dedup_skip", False),
    # the leaf produced a proof that didn't compile (a genuine proof error, distinct from a scope/context bug)
    ("agentic_leaf open: compile_error", "leaf_proof_compile_error", False),
    ("compile_error", "leaf_proof_compile_error", False),
    ("dead instrument", "dead_instrument", True),
    ("inadmissible", "dead_instrument", True),
    # proposer-pool per-model attribution rows (`solver_core._governed_pool_preattack` → `_record_attempt(...,
    # outcome="failed", notes="governed_pool")`): a tried proposal whose proof FAILED the campaign-aware compile
    # verify — an honest non-closure (same class as failed_compile), NOT a harness fault. Bare `"failed"` isn't in
    # the honest-non-close outcome map and "governed_pool" matched nothing, so these fell through to
    # `other_error`/structural and made a healthy pool read as a kernel bug (2026-07-02 ftap_hard false alarm).
    # LAST in the list on purpose: if the writer ever enriches notes with the verify's actual Lean error, the
    # specific rules above (unknown identifier / type mismatch / …) win first-match and classify it better.
    ("governed_pool", "pool_proposal_compile_error", False),
]


_HONEST_NONCLOSE_OUTCOMES = {
    # the agent got a clean shot and the PROOF did not land — an honest non-closure, NOT an unclassified error.
    # Bucketing these as `other_error` (the old fate) made an honest-gap run read as a crash (the 2026-06-23
    # consciousness RCA: faithful=True + admitted_and_exact_gap rendered as `✗ other_error`).
    "failed_compile": ("proof_compile_error", False),   # a proof attempt that did not typecheck
    "compile_error": ("proof_compile_error", False),
    "exact_gap": ("unproven", False),                   # the agent honestly admitted it could not close
    "admitted_and_exact_gap": ("unproven", False),
    "open": ("unproven", False),
    "no_close": ("unproven", False),
    "deferred": ("deferred_wall", False),               # campaign wall reached → honestly deferred, not a failure
}


def _definition_api_summary(obj: dict) -> dict:
    receipt = obj.get("definition_api_receipt")
    if not isinstance(receipt, dict):
        return {}
    defs = receipt.get("definitions") if isinstance(receipt.get("definitions"), list) else []
    flagged = []
    for row in defs:
        if not isinstance(row, dict):
            continue
        flags = row.get("flags") if isinstance(row.get("flags"), list) else []
        if flags:
            flagged.append({
                "name": str(row.get("name") or ""),
                "kind": str(row.get("kind") or ""),
                "computability": str(row.get("computability") or ""),
                "flags": [str(f) for f in flags],
            })
    return {
        "schema": "leanmill.definition_api_summary.v1",
        "receipt_schema": str(receipt.get("schema") or ""),
        "target_name": str(receipt.get("target_name") or ""),
        "definition_count": len([r for r in defs if isinstance(r, dict)]),
        "summary_flags": [str(f) for f in receipt.get("summary_flags", [])]
        if isinstance(receipt.get("summary_flags"), list) else [],
        "flagged_definitions": flagged[:12],
        "flagged_definition_count": len(flagged),
    }


def _library_delta_summary(obj: dict) -> dict:
    receipt = obj.get("library_delta_receipt")
    if not isinstance(receipt, dict):
        return {}
    summary = receipt.get("summary") if isinstance(receipt.get("summary"), dict) else {}
    decls = receipt.get("public_decls") if isinstance(receipt.get("public_decls"), list) else []
    flagged = []
    for row in decls:
        if not isinstance(row, dict):
            continue
        warnings = row.get("warnings") if isinstance(row.get("warnings"), list) else []
        if warnings:
            flagged.append({
                "name": str(row.get("name") or ""),
                "kind": str(row.get("kind") or ""),
                "namespace": str(row.get("namespace") or ""),
                "warnings": [str(w) for w in warnings],
            })
    return {
        "schema": "leanmill.library_delta_summary.v1",
        "receipt_schema": str(receipt.get("schema") or ""),
        "target_name": str(receipt.get("target_name") or ""),
        "public_decl_count": int(summary.get("public_decl_count") or 0),
        "theorem_count": int(summary.get("theorem_count") or 0),
        "definition_count": int(summary.get("definition_count") or 0),
        "dependency_edge_count": int(summary.get("dependency_edge_count") or 0),
        "warning_count": int(summary.get("warning_count") or len(flagged)),
        "warnings": [str(w) for w in receipt.get("warnings", [])]
        if isinstance(receipt.get("warnings"), list) else [],
        "flagged_decls": flagged[:12],
        "flagged_decl_count": len(flagged),
    }


def _refine_class(error_class: "str | None", notes: "str | None",
                  outcome: "str | None" = None) -> "tuple[str, bool]":
    """(refined_class, is_structural). Split the catch-all `other_error` into an actionable class: first the notes
    text (specific Lean errors), then the OUTCOME itself (an honest non-closure like `failed_compile`/`exact_gap`
    is NOT an unclassified error), then the recorded error_class. Reserve `other_error` for the genuinely
    unknown — so honest gaps stop masquerading as crashes (the 2026-06-23 consciousness telemetry RCA)."""
    blob = ((notes or "") + " " + (error_class or "")).lower()
    for sub, cls, structural in _REFINE:
        if sub in blob:
            return cls, structural
    if outcome and outcome in _HONEST_NONCLOSE_OUTCOMES:
        return _HONEST_NONCLOSE_OUTCOMES[outcome]
    ec = (error_class or "other_error").strip() or "other_error"
    # honest unproven goals are NOT structural; everything genuinely unknown stays "other_error" (structural-ish:
    # we couldn't even classify it, which itself is worth surfacing).
    return ec, ec not in ("unsolved_goals", "no_advance", "no_seed")


def _iso_span_minutes(stamps: "list[str]") -> "float | None":
    """Wall span in minutes from ISO-8601 attempt_at strings (lexicographic min/max — ISO sorts correctly)."""
    xs = [s for s in stamps if s]
    if len(xs) < 2:
        return None
    try:
        from datetime import datetime
        lo = datetime.fromisoformat(min(xs)); hi = datetime.fromisoformat(max(xs))
        return max(0.0, (hi - lo).total_seconds() / 60.0)
    except Exception:  # noqa: BLE001
        return None


def read_run_manifest(*, run_tag: "str | None" = None, manifest_path: "str | Path | None" = None,
                      lean_root: "str | Path | None" = None) -> dict:
    """Read the diagnostics subset of a LeanMill `run_manifest.json`.

    The manifest can carry large receipts; diagnostics only need launch inputs
    and authority modes. Missing or malformed manifests return `{}`.
    """
    try:
        if manifest_path:
            p = Path(manifest_path)
        elif run_tag:
            p = Path(lean_root or _DEFAULT_LEAN_ROOT) / ".solver_scratch" / run_tag / "run_manifest.json"
        else:
            return {}
        if not p.exists():
            return {}
        obj = json.loads(p.read_text(encoding="utf-8"))
        return {
            "path": str(p),
            "schema": obj.get("schema") or "",
            "run_tag": obj.get("run_tag") or "",
            "run_scratch": obj.get("run_scratch") or "",
            "git_head": obj.get("git_head") or "",
            "blueprint": obj.get("blueprint") if isinstance(obj.get("blueprint"), dict) else {},
            "substrate": obj.get("substrate") if isinstance(obj.get("substrate"), dict) else {},
            "providers": obj.get("providers") if isinstance(obj.get("providers"), dict) else {},
            "code_fingerprints": (
                obj.get("code_fingerprints") if isinstance(obj.get("code_fingerprints"), dict) else {}
            ),
            "authority_modes": obj.get("authority_modes") if isinstance(obj.get("authority_modes"), dict) else {},
            "cache_authority_classes": (
                obj.get("cache_authority_classes") if isinstance(obj.get("cache_authority_classes"), dict) else {}
            ),
            "definition_api_summary": _definition_api_summary(obj),
            "library_delta_summary": _library_delta_summary(obj),
        }
    except Exception:  # noqa: BLE001
        return {}


def summarize_run(*, db_path: "str | Path | None" = None, run_tag: "str | None" = None,
                  since_iso: "str | None" = None, window_min: "float | None" = None,
                  manifest_path: "str | Path | None" = None,
                  lean_root: "str | Path | None" = None,
                  verdict_path: "str | Path | None" = None) -> dict:
    """Read the attempts for ONE run (by run_tag, or a recent time window) and summarize the failure mode.
    Filter precedence: run_tag (exact) > since_iso > window_min (now-window) > all rows. Returns a dict
    (also feeds `render`). Never raises on a missing/locked DB — returns {"error": ...}."""
    db = Path(db_path) if db_path else _DEFAULT_DB
    manifest = read_run_manifest(run_tag=run_tag, manifest_path=manifest_path, lean_root=lean_root)
    verdict_summary = {}
    try:
        from ztare.leanmill.verdict_store import summarize_verdicts
        verdict_summary = summarize_verdicts(verdict_path, run_tag=run_tag or "")
    except Exception:  # noqa: BLE001
        verdict_summary = {}
    if not db.exists():
        out = {"error": f"no attempts DB at {db}", "total": 0}
        if manifest:
            out["run_manifest"] = manifest
        if verdict_summary.get("total"):
            out["typed_verdicts"] = verdict_summary
        return out
    if since_iso is None and window_min:
        try:
            from datetime import datetime, timezone, timedelta
            since_iso = (datetime.now(timezone.utc) - timedelta(minutes=window_min)).isoformat()
        except Exception:  # noqa: BLE001
            since_iso = None
    try:
        c = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
        cols = [r[1] for r in c.execute("PRAGMA table_info(attempts)")]
        wanted = ["move", "outcome", "error_class", "notes", "attempt_at"]
        if "ratified" in cols:
            wanted.append("ratified")
        if "row_id" in cols:
            wanted.append("row_id")   # the per-TARGET key — lets us roll up "which target closed vs gapped"
        idx = {name: i for i, name in enumerate(wanted)}
        where, args = "", []
        if run_tag and "run_tag" in cols:
            where, args = "WHERE run_tag = ?", [run_tag]
        elif since_iso:
            where, args = "WHERE attempt_at > ?", [since_iso]
        rows = c.execute(f"SELECT {', '.join(wanted)} FROM attempts {where} ORDER BY attempt_at", args).fetchall()
        c.close()
    except Exception as e:  # noqa: BLE001
        return {"error": f"query failed: {e}", "total": 0}

    total = len(rows)
    by_move_outcome: Counter = Counter()
    by_class: Counter = Counter()
    structural = 0
    closed = 0
    ratified = 0
    dedup_skips = 0
    stamps: list = []
    per_target: dict = {}   # row_id -> {"closed": bool, "attempts": int, "blocks": Counter}
    for row in rows:
        move, outcome, ec, notes, at = (row[idx["move"]], row[idx["outcome"]], row[idx["error_class"]],
                                        row[idx["notes"]], row[idx["attempt_at"]])
        rat = row[idx["ratified"]] if "ratified" in idx else None
        tgt = (row[idx["row_id"]] if "row_id" in idx else None) or "?"
        stamps.append(at)
        by_move_outcome[(move or "?", outcome or "?")] += 1
        pt = per_target.setdefault(tgt, {"closed": False, "ratified": False, "attempts": 0, "blocks": Counter()})
        pt["attempts"] += 1
        if outcome == "closed":
            closed += 1
            pt["closed"] = True
        if rat in (1, "1", True):
            ratified += 1
            pt["ratified"] = True
        if outcome not in ("closed", "advanced"):
            cls, is_struct = _refine_class(ec, notes, outcome)
            if cls == "dedup_skip":        # a no-op re-attempt, NOT a failure — keep it out of the tally + noise
                dedup_skips += 1
                continue
            by_class[cls] += 1
            pt["blocks"][cls] += 1
            if is_struct:
                structural += 1
    fails = sum(by_class.values())
    span = _iso_span_minutes(stamps)
    headline, detail = _classify(total, closed, ratified, fails, structural, by_class, span)
    # PER-TARGET rollup + WATCH list: a target that did NOT close and whose dominant block is a GOVERNANCE
    # reject (statement_integrity / target_signature_altered) is a likely FALSE-NEGATIVE — the gate rejected a
    # proof, it is NOT an honest math gap. Surfacing this is what turns "scour 4 sources" into "read the debrief".
    targets, watch = {}, []
    for tgt, pt in per_target.items():
        top_block = pt["blocks"].most_common(1)[0][0] if pt["blocks"] else None
        # A move-level `closed` is NOT a verified closure — governance can REJECT it post-close (ratified=0).
        # `ratified` is the truth (kernel + #print-axioms + MNC + statement_integrity all passed).
        if pt["ratified"]:
            status = "ratified"
        elif pt["closed"]:
            status = "closed-NOT-ratified"
        else:
            status = top_block or "open"
        targets[str(tgt)] = {"closed": pt["closed"], "ratified": pt["ratified"],
                             "attempts": pt["attempts"], "top_block": top_block, "status": status}
        if pt["closed"] and not pt["ratified"]:
            watch.append(f"{str(tgt)[:48]}: a move CLOSED but the closure was NOT RATIFIED — governance rejected "
                         "it post-close (axiom audit / MNC / consequence-exposure / statement_integrity). 0 verified "
                         "despite 'closed'. Surface WHICH organ rejected, and whether it is a real catch or a false-reject.")
        if (not pt["closed"]) and top_block == "governance_block":
            watch.append(f"{str(tgt)[:48]}: NOT closed; dominant block = governance_block (statement_integrity/"
                         "signature_altered) ×{} — likely a FALSE-NEGATIVE (gate rejected a proof, not a math gap), "
                         "ESPECIALLY if a sibling/isomorphic target DID close.".format(pt['blocks']['governance_block']))
    out = {
        "total": total, "closed": closed, "ratified": ratified, "failures": fails,
        "structural_failures": structural, "dedup_skips": dedup_skips,
        "wall_minutes": (round(span, 1) if span else None),
        "throughput_per_min": (round(total / span, 2) if span and span > 0 else None),
        "by_move_outcome": {f"{m}/{o}": n for (m, o), n in by_move_outcome.most_common()},
        "by_failure_class": dict(by_class.most_common()),
        "targets": targets, "watch": watch,
        "headline": headline, "detail": detail,
        "filter": (f"run_tag={run_tag}" if run_tag else (f"since={since_iso}" if since_iso else "ALL")),
    }
    if manifest:
        out["run_manifest"] = manifest
    if verdict_summary.get("total"):
        out["typed_verdicts"] = verdict_summary
    try:
        from ztare.leanmill.phase_timing import summarize_phase_timings
        out["dispatch_budget"] = summarize_phase_timings(run_tag=run_tag or "").get("dispatch_budget", {})
    except Exception:  # noqa: BLE001 — diagnostics remain available without timing telemetry
        out["dispatch_budget"] = {}
    return out


def _classify(total, closed, ratified, fails, structural, by_class, span) -> "tuple[str, str]":
    if total == 0:
        return "NO ATTEMPTS", "No move attempts recorded for this filter — the run never reached the solver, or the run_tag/window is wrong."
    if closed > 0:
        return "PRODUCTIVE", f"{closed} closure(s), {ratified} ratified. Lift/quality is in the closures, not this summary."
    struct_frac = (structural / fails) if fails else 0.0
    starved = bool(span and span > 5 and total / span < 0.5)
    top = next(iter(by_class), None)
    top_n = by_class.get(top, 0) if top else 0
    top_frac = (top_n / fails) if fails else 0.0
    if struct_frac >= 0.6:
        msg = (f"{int(struct_frac*100)}% of failures are STRUCTURAL (top: {top} ×{top_n}, {int(top_frac*100)}%) — the "
               f"apparatus isn't getting clean shots at the MATH (scope/context/syntax), NOT genuine difficulty. "
               f"Look at a context/namespace/import bug or a malformed harness feed BEFORE concluding 'hard'.")
        if starved:
            msg += f" ALSO throughput-starved ({total} attempts / {round(span)}min)."
        return "STRUCTURAL-FAIL", msg
    if starved:
        return "STARVED", (f"Only {total} attempts in {round(span)}min ({round(total/span,2)}/min) — wall-clock is "
                           f"eaten by slow dispatch, not move-verify cycles. Few shots on goal regardless of math.")
    if top in ("unsolved_goals", "no_advance", "lemma_no_compose", "tactic_failed", "statement_false"):
        return "GENUINE-HARD", (f"Failures are honest proof gaps (top: {top} ×{top_n}). The apparatus got clean "
                                f"shots and the math/decomposition didn't land — this is real difficulty, not a bug.")
    return "MIXED", f"No single dominant mode (top: {top} ×{top_n}). Inspect by_failure_class."


def render(summary: dict) -> str:
    if summary.get("error"):
        msg = f"[run-diagnostics] {summary['error']}"
        if summary.get("run_manifest"):
            mf = summary["run_manifest"]
            msg += f"\n  manifest: {mf.get('path', '')}"
            das = mf.get("definition_api_summary") if isinstance(mf.get("definition_api_summary"), dict) else {}
            if das:
                msg += ("\n  definition/api: "
                        f"defs={das.get('definition_count', 0)} "
                        f"flagged={das.get('flagged_definition_count', 0)} "
                        f"flags={das.get('summary_flags', [])}")
            lds = mf.get("library_delta_summary") if isinstance(mf.get("library_delta_summary"), dict) else {}
            if lds:
                msg += ("\n  library-delta: "
                        f"decls={lds.get('public_decl_count', 0)} "
                        f"edges={lds.get('dependency_edge_count', 0)} "
                        f"flagged={lds.get('flagged_decl_count', 0)} "
                        f"warnings={lds.get('warnings', [])}")
        if summary.get("typed_verdicts"):
            msg += f"\n  typed verdicts: {summary['typed_verdicts'].get('by_kind', {})}"
        return msg
    L = ["", "=" * 72, f"[run-diagnostics] {summary['headline']} — {summary['filter']}", "-" * 72,
         f"  attempts={summary['total']}  closed={summary['closed']}  ratified={summary['ratified']}"
         f"  failures={summary['failures']}  structural={summary['structural_failures']}"]
    if summary.get("run_manifest"):
        mf = summary["run_manifest"]
        modes = mf.get("authority_modes") or {}
        L.append("  manifest: "
                 f"{mf.get('path', '')}  "
                 f"pool={modes.get('proposer_pool', '')} "
                 f"staged={modes.get('staged_reuse', '')} "
                 f"bank_ratify={modes.get('bank_env_ratify', '')}")
        das = mf.get("definition_api_summary") if isinstance(mf.get("definition_api_summary"), dict) else {}
        if das:
            L.append("  definition/api: "
                     f"defs={das.get('definition_count', 0)} "
                     f"flagged={das.get('flagged_definition_count', 0)} "
                     f"flags={das.get('summary_flags', [])}")
        lds = mf.get("library_delta_summary") if isinstance(mf.get("library_delta_summary"), dict) else {}
        if lds:
            L.append("  library-delta: "
                     f"decls={lds.get('public_decl_count', 0)} "
                     f"edges={lds.get('dependency_edge_count', 0)} "
                     f"flagged={lds.get('flagged_decl_count', 0)} "
                     f"warnings={lds.get('warnings', [])}")
    if summary.get("typed_verdicts"):
        tv = summary["typed_verdicts"]
        L.append("  typed verdicts: "
                 + ", ".join(f"{k}×{v}" for k, v in sorted((tv.get("by_kind") or {}).items())))
    if summary.get("wall_minutes") is not None:
        L.append(f"  wall={summary['wall_minutes']}min  throughput={summary['throughput_per_min']}/min")
    db = summary.get("dispatch_budget") or {}
    if db.get("count"):
        L.append("  dispatch budget: "
                 f"calls={db.get('count')} near_cap={db.get('near_cap_count', 0)} "
                 f"mean_use={db.get('utilization_mean', 0):.2f} p95_use={db.get('utilization_p95', 0):.2f} "
                 f"runtime={db.get('by_runtime', {})}")
    if summary.get("by_failure_class"):
        L.append("  failure classes: " + ", ".join(f"{k}×{v}" for k, v in summary["by_failure_class"].items()))
    if summary.get("dedup_skips"):
        L.append(f"  (excluded {summary['dedup_skips']} native_hammer dedup-skips — no-ops, not failures)")
    if summary.get("by_move_outcome"):
        top = list(summary["by_move_outcome"].items())[:8]
        L.append("  move/outcome:    " + ", ".join(f"{k}×{v}" for k, v in top))
    # PER-TARGET rollup — the layer that makes an asymmetry (one twin closed, the other gate-blocked) visible
    # WITHOUT hand-querying SQLite + logs + certs + closure files.
    tgts = summary.get("targets") or {}
    if tgts:
        L.append(f"  per-target ({len(tgts)}):")
        for t, info in list(tgts.items())[:12]:
            st = info.get("status") or ("ratified" if info.get("ratified") else "open")
            mark = {"ratified": "✓ ratified", "closed-NOT-ratified": "⚠ closed-NOT-ratified (gov rejected)"}.get(
                st, f"✗ {st}")
            L.append(f"    {str(t)[:52]:52s} {mark}  ({info['attempts']} attempts)")
    for w in (summary.get("watch") or []):
        L.append(f"  ⚠ WATCH: {w}")
    L.append(f"  >> {summary['detail']}")
    L.append("=" * 72)
    return "\n".join(L)


def print_epilogue(*, run_tag=None, since_iso=None, window_min=None, db_path=None,
                   manifest_path=None, lean_root=None, verdict_path=None) -> dict:
    """Convenience for runners: compute + print + return the summary in one call."""
    s = summarize_run(db_path=db_path, run_tag=run_tag, since_iso=since_iso, window_min=window_min,
                      manifest_path=manifest_path, lean_root=lean_root, verdict_path=verdict_path)
    print(render(s), flush=True)
    return s


def _main() -> int:
    import argparse
    ap = argparse.ArgumentParser(description="Per-run failure-mode diagnostics from solver_lane_attempts.db")
    ap.add_argument("--db", default=None)
    ap.add_argument("--run-tag", default=None)
    ap.add_argument("--since", default=None, help="ISO-8601; rows with attempt_at > this")
    ap.add_argument("--window-min", type=float, default=None, help="last N minutes")
    ap.add_argument("--manifest", default=None, help="explicit run_manifest.json path")
    ap.add_argument("--lean-root", default=None, help="Lean root containing .solver_scratch/<run_tag>/run_manifest.json")
    ap.add_argument("--verdicts", default=None, help="explicit leanmill_verdicts.jsonl path")
    a = ap.parse_args()
    s = summarize_run(db_path=a.db, run_tag=a.run_tag, since_iso=a.since, window_min=a.window_min,
                      manifest_path=a.manifest, lean_root=a.lean_root, verdict_path=a.verdicts)
    print(render(s))
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
