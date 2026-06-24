#!/usr/bin/env python3
"""Promote a machine-checked campaign closure to a filed .lean artifact WITH a per-campaign "factory cert" header.

The proof body is the VERBATIM machine closure (copied from `closures/<target>.lean`, never hand-authored). The
header is GENERATED metadata — the campaign's P0 economics so the artifact is self-documenting: outcome+axioms,
time-to-closure, compute-to-closure, the phase decomposition (where the wall went), yield, reuse (cited banked
rungs), the decomposition bill-of-materials, moves, domain+generality. Sources are the SAME durable read-models
factory_intelligence uses (phase_timing.summarize_campaign_cycle_time / summarize_phase_timings + the attempts
DB), plus #print axioms from a compile. Reusable for ANY campaign closure, not this one specifically.

  PYTHONPATH=src python scripts/.../promote_campaign_artifact.py \
      --run-tag <rt> --target <closure_name> --dest ztare_proofs/ZtareProofs/strategy/<file>.lean [--log <run.log>]
"""
from __future__ import annotations

import argparse
import sqlite3
import subprocess
import sys
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO / "src"))

from ztare.leanmill.phase_timing import summarize_campaign_cycle_time, summarize_phase_timings  # noqa: E402

ATTEMPTS = REPO / "analytics" / "public" / "queries" / "solver_lane_attempts.db"
CLOSURES = REPO / "ztare_proofs" / ".solver_scratch" / "closures"
LEAN_ROOT = REPO / "ztare_proofs"


def _attempt_rows(run_tag: str) -> "list[dict]":
    if not ATTEMPTS.exists():
        return []
    cx = sqlite3.connect(f"file:{ATTEMPTS}?mode=ro", uri=True)
    try:
        cols = ("run_tag", "attempt_at", "outcome", "ratified", "wallclock_s", "move", "provider")
        return [dict(zip(cols, r)) for r in cx.execute(
            f"SELECT {','.join(cols)} FROM attempts WHERE run_tag=?", (run_tag,)).fetchall()]
    finally:
        cx.close()


def _axioms(closure: Path) -> str:
    """#print axioms from a compile (the closure carries the `#print axioms` command). Best-effort; '?' if the
    toolchain/compile is unavailable — never block filing on it."""
    try:
        out = subprocess.run(["lake", "env", "lean", str(closure)], cwd=str(LEAN_ROOT),
                             capture_output=True, text=True, timeout=400).stdout
        ax = []
        cap = False
        for ln in out.splitlines():
            if "depends on axioms:" in ln:
                cap = True
                ax.append(ln.split("depends on axioms:", 1)[1].strip())
                continue
            if cap:
                ax.append(ln.strip())
                if "]" in ln:
                    break
        joined = " ".join(ax).strip()
        return joined or "(none printed)"
    except Exception:  # noqa: BLE001
        return "?"


def _cited_rungs(log: "Path | None") -> "list[str]":
    """Banked rungs cited this run. DB `cache_reuse` rows undercount the pre-attack `_pvp` cite (solver_core
    follow-up), so enrich from the run log's `CITED banked rung ... for '<name>'` lines when a log is given."""
    names: "list[str]" = []
    if log and log.exists():
        import re
        for m in re.finditer(r"CITED banked rung.*?for '([^']+)'", log.read_text(encoding="utf-8", errors="ignore")):
            if m.group(1) not in names:
                names.append(m.group(1))
    return names


def _fmt(n) -> str:
    return "—" if n is None else f"{n:g}"


def build_header(run_tag: str, target: str, closure: Path, log: "Path | None", axioms: str = "", domain: str = "") -> str:
    rows = _attempt_rows(run_tag)
    cct = summarize_campaign_cycle_time(rows).get("campaigns", {}).get(run_tag, {})
    ph = summarize_phase_timings(run_tag=run_tag)
    phases = {k: round(v.get("total_s", 0.0), 1) for k, v in ph.get("phases", {}).items() if k != "campaign"}
    lead = (ph.get("runs", {}).get(run_tag, {}) or {}).get("lead_time_s")
    moves = Counter(r["move"] for r in rows if r.get("move"))
    ttc = cct.get("time_to_closure_s", {}) or {}
    ctc = cct.get("cost_to_closure_s", {}) or {}
    yld = cct.get("yield", {}) or {}
    cited = _cited_rungs(log)
    ph_str = " · ".join(f"{v:g}s {k}" for k, v in sorted(phases.items(), key=lambda kv: -kv[1])) or "—"
    mv_str = " · ".join(f"{m}×{c}" for m, c in moves.most_common()) or "—"
    L = [
        "/-",
        f"LeanMill campaign provenance — {target}",
        "The theorem(s) below are the VERBATIM machine-checked closure. This header is GENERATED from run",
        f"telemetry (run_tag={run_tag}) by promote_campaign_artifact.py — not hand-authored.",
        "",
        f"  outcome     : closed · faithful · axioms {axioms.strip() or _axioms(closure)}",
        f"  domain      : {domain.strip() or cct.get('domain', 'unspecified')}",
        f"  time        : time-to-closure {_fmt(ttc.get('mean'))}s (first {_fmt(ttc.get('first'))}s · "
        f"p50 {_fmt(ttc.get('p50'))}s · p95 {_fmt(ttc.get('p95'))}s) · campaign span {_fmt(cct.get('span_s'))}s "
        f"(lead {_fmt(lead)}s)",
        f"  compute     : cost-to-closure {_fmt(ctc.get('mean'))}s mean · {_fmt(ctc.get('total_wall_s'))}s total",
        f"  yield       : {yld.get('closed', 0)}/{cct.get('attempts', 0)} attempts closed "
        f"({yld.get('failed', 0)} failed)",
        f"  phases      : {ph_str}",
        f"  reuse       : cited {len(cited)} banked rung(s)" + (f" — {', '.join(cited)}" if cited else ""),
        f"  moves       : {mv_str}",
        "-/",
        "",
    ]
    return "\n".join(L)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-tag", required=True)
    ap.add_argument("--target", required=True)
    ap.add_argument("--dest", default="", help="output path; defaults to --from-file (in-place backfill)")
    ap.add_argument("--log", default="")
    ap.add_argument("--axioms", default="", help="pre-verified #print axioms (skips a recompile; e.g. on a memory-tight box)")
    ap.add_argument("--domain", default="", help="override the domain label (old runs predate the ## Domain stamp)")
    ap.add_argument("--from-file", default="", help="backfill an EXISTING filed .lean (prepend the header in place) instead of reading closures/")
    a = ap.parse_args()
    # BODY = an existing filed artifact (backfill) OR the verbatim closure (fresh promote). Either way the proof is
    # copied verbatim; only the generated header is prepended.
    body_path = Path(a.from_file) if a.from_file else (CLOSURES / f"{a.target}.lean")
    if not body_path.exists():
        print(f"ERROR: body not found: {body_path}")
        return 1
    body = body_path.read_text(encoding="utf-8")
    if "LeanMill campaign provenance" in body[:1200]:
        print(f"SKIP {body_path}: already carries a provenance header (idempotent — not double-prepending)")
        return 0
    header = build_header(a.run_tag, a.target, body_path, Path(a.log) if a.log else None,
                          axioms=a.axioms, domain=a.domain)
    dest = Path(a.dest or a.from_file)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(header + body, encoding="utf-8")
    print(f"FILED {dest} (verbatim proof + generated provenance header)")
    print("--- header ---")
    print(header)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
