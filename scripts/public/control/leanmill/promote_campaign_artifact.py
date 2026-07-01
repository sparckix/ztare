#!/usr/bin/env python3
"""Promote a machine-checked campaign closure to a filed .lean artifact WITH a per-campaign "factory cert" header.

The proof body is the VERBATIM machine closure (copied from `closures/<target>.lean`, never hand-authored). The
header is GENERATED metadata — the campaign's P0 economics so the artifact is self-documenting: outcome+axioms,
time-to-closure, compute-to-closure, the phase decomposition (where the wall went), yield, reuse (cited banked
rungs), the decomposition bill-of-materials, moves, domain+generality. Sources are the SAME durable read-models
factory_intelligence uses (phase_timing.summarize_campaign_cycle_time / summarize_phase_timings + the attempts
DB), plus #print axioms from a compile. Reusable for ANY campaign closure, not this one specifically.

  PYTHONPATH=src python scripts/.../promote_campaign_artifact.py \
      --run-tag <rt> --target <closure_name> \
      --dest ztare_proofs/leanmill-formalizations/strategy/<file>.lean [--log <run.log>]

  CANONICAL dest = ztare_proofs/leanmill-formalizations/{strategy,finance}/ (the curated, GitHub-public
  formalizations home, alongside leanmill-formalizations/blueprints/). NOT ztare_proofs/ZtareProofs/strategy/
  (a stale auto-default). The local repo is master; the VPS is a mirror — file artifacts into the LOCAL repo.
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


def _laundering_markers(body: str) -> "list[str]":
    """PUBLISH-BOUNDARY GUARD (2026-06-30 RCA). A filed `closed · faithful` artifact must be the SELF-CONTAINED
    real proof: no `sorry`, and no local `axiom` DECLARATIONS. A local `axiom` decl is the tell of the PROBE-WORLD
    standalone — the solver stubs cited banked rungs as `axiom`s so the single theorem recompiles in isolation.
    Publishing THAT with a clean-axioms header is the laundering-looking disconnect Gemini flagged on VCG (the
    first COMPOSITE campaign filed): the real substrate proof is axiom-clean — those stubs are proven theorems
    there — but the standalone stubs them, so `#print axioms` on the filed FILE shows the stubs and contradicts
    the header. Refuse to file when these appear so the disconnect can never ship; file the substrate instead.
    Uses the canonical `lean_source` comment-aware scanners (a `sorry`/`axiom` inside a comment is not a hit)."""
    from ztare.leanmill import lean_source as _ls
    markers: "list[str]" = []
    if _ls.has_sorry(body):
        markers.append("body contains `sorry` (a closed·faithful artifact must be sorry-free)")
    code = _ls.blank_comments(body)             # comment-blanked, offsets preserved → honest line scan
    for i, ln in enumerate(code.splitlines(), 1):
        if __import__("re").match(r"\s*axiom\s+\w", ln):
            markers.append(f"L{i}: local `axiom` declaration (probe-world stub) — {body.splitlines()[i-1].strip()[:70]}")
    return markers


def _p0_sidecar(closure: Path) -> "dict | None":
    """Honest P0 STAMPED at campaign close (autoformalize_notes) in the warm/persisted world: persisted-world
    `#print axioms` + this-run banked/reused counts. promote READS this instead of re-deriving P0 from the cold
    probe closure — which times out (→ `axioms ?`), reports probe-world stub axioms, and whose log-regex misses
    intra-run banking (→ `reuse 0`). Absent for pre-2026-06-30 runs ⇒ callers fall back to the probe compile /
    log parse. This is the single source of truth that ends the recurring P0-at-promote bug class."""
    sc = closure.parent / (closure.stem + ".p0.json")
    if not sc.exists():
        return None
    try:
        import json
        return json.loads(sc.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return None


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
    """Banked rungs reused this run — the COMPOUNDING signal. DB `cache_reuse` rows undercount, so read the run
    log (NOT Lean ⇒ log-text parse, not lean_source): both the proof-level `CITED banked rung ... for '<name>'`
    cites AND the campaign-level `REUSED from bank ... theorem <name>` skips (the (b) banked-lemma reuse, which
    skips re-formalizing an already-proven decl). Counting only the former under-reported a fully-reused run as
    'cited 0' even though it stood entirely on banked work."""
    names: "list[str]" = []
    if log and log.exists():
        import re
        txt = log.read_text(encoding="utf-8", errors="ignore")
        for m in re.finditer(r"CITED banked rung.*?for '([^']+)'", txt):
            if m.group(1) not in names:
                names.append(m.group(1))
        for m in re.finditer(r"REUSED from bank[^\n]*?:\s*theorem\s+(\w+)", txt):
            if m.group(1) not in names:
                names.append(m.group(1))
    return names


def _fmt(n) -> str:
    return "—" if n is None else f"{n:g}"


def _family_rows(run_tag: str, only: "set[str] | None" = None) -> "list[dict]":
    """Attempt rows for run_tag's campaign family (v4/v5/v6…) — the honest multi-run milestone view (a milestone
    whose lemmas were proven in one run and whose target closed in a later reuse run must NOT report only the
    cheap reuse run's time-to-closure: that UNDER-represents the real proving cost — a confound). Uses the
    canonical `campaign_family` strip. `only` (optional) restricts to specific member run_tags — used to EXCLUDE
    pre-fix / debugging runs whose wall was bug-thrash, not proving (the OTHER confound direction)."""
    from ztare.leanmill.phase_timing import campaign_family
    fam = campaign_family(run_tag)
    if not ATTEMPTS.exists():
        return []
    cx = sqlite3.connect(f"file:{ATTEMPTS}?mode=ro", uri=True)
    try:
        cols = ("run_tag", "attempt_at", "outcome", "ratified", "wallclock_s", "move", "provider")
        all_rows = [dict(zip(cols, r)) for r in cx.execute(f"SELECT {','.join(cols)} FROM attempts").fetchall()]
    finally:
        cx.close()
    return [r for r in all_rows if campaign_family(r.get("run_tag") or "") == fam
            and (only is None or (r.get("run_tag") or "") in only)]


def _family_block(run_tag: str, only: "set[str] | None" = None) -> "list[str]":
    """Render the campaign-FAMILY P0 rollup (combined wall + per-member role) so a multi-run milestone is honest:
    which run PROVED the lemmas vs which CLOSED the target vs a discarded attempt — never a single-run blob.
    `only` restricts to the genuine post-fix runs (excludes pre-fix bug-thrash)."""
    from ztare.leanmill.phase_timing import campaign_family
    fam = campaign_family(run_tag)
    camps = summarize_campaign_cycle_time(_family_rows(run_tag, only=only)).get("campaigns", {})
    members = {rt: c for rt, c in camps.items() if campaign_family(rt) == fam}
    if not members:
        return []
    # REAL ELAPSED = span (last−first attempt), NOT summed `wallclock_s` (active-solve only, which omits
    # consolidation / formalization / Mathlib imports / warm-env builds / inter-attempt gaps and UNDER-states the
    # true time ~5× — 2026-06-25 RCA: a 79-min campaign read as 593s). Report span as the honest wall; keep the
    # active-solve sum alongside it as the (smaller) compute figure.
    span = round(sum((c.get("span_s") or 0) for c in members.values()), 1)
    active = round(sum(((c.get("cost_to_closure_s") or {}).get("total_wall_s") or 0) for c in members.values()), 1)
    closed = sum(((c.get("yield") or {}).get("closed") or 0) for c in members.values())
    out = [f"  milestone   : campaign family '{fam}' — {len(members)} run(s) · REAL elapsed (span) "
           f"{span:g}s (~{span/60:.0f} min active) · active-solve {active:g}s · {closed} closures "
           f"[span=elapsed is the honest wall; the single-run 'time' line above is the filed run only]"]
    for rt, c in sorted(members.items()):
        sp = c.get("span_s") or 0
        out.append(f"     - {rt}: {((c.get('yield') or {}).get('closed') or 0)}/{c.get('attempts', 0)} closed · "
                   f"elapsed {sp:g}s (~{sp/60:.1f} min)")
    return out


def build_header(run_tag: str, target: str, closure: Path, log: "Path | None", axioms: str = "", domain: str = "",
                 family: bool = False, family_runs: "set[str] | None" = None) -> str:
    rows = _attempt_rows(run_tag)
    cct = summarize_campaign_cycle_time(rows).get("campaigns", {}).get(run_tag, {})
    ph = summarize_phase_timings(run_tag=run_tag)
    phases = {k: round(v.get("total_s", 0.0), 1) for k, v in ph.get("phases", {}).items() if k != "campaign"}
    lead = (ph.get("runs", {}).get(run_tag, {}) or {}).get("lead_time_s")
    moves = Counter(r["move"] for r in rows if r.get("move"))
    ttc = cct.get("time_to_closure_s", {}) or {}
    ctc = cct.get("cost_to_closure_s", {}) or {}
    yld = cct.get("yield", {}) or {}
    # sidecar: next to the closure (fresh promote) OR keyed on TARGET in CLOSURES (so --from-file backfills read it)
    p0 = _p0_sidecar(closure) or _p0_sidecar(CLOSURES / f"{target}.lean")
    # axioms + reuse: prefer the close-time stamp (honest persisted world); fall back to probe compile / log.
    ax_str = axioms.strip() or (p0 or {}).get("axioms") or _axioms(closure)
    if p0:
        reuse_str = (f"{p0.get('banked_this_run', 0)} rung(s) banked this run · "
                     f"{p0.get('reused_from_bank', 0)} reused from prior bank")
    else:
        cited = _cited_rungs(log)
        reuse_str = f"cited {len(cited)} banked rung(s)" + (f" — {', '.join(cited)}" if cited else "")
    ph_str = " · ".join(f"{v:g}s {k}" for k, v in sorted(phases.items(), key=lambda kv: -kv[1])) or "—"
    mv_str = " · ".join(f"{m}×{c}" for m, c in moves.most_common()) or "—"
    L = [
        "/-",
        f"LeanMill campaign provenance — {target}",
        "The theorem(s) below are the VERBATIM machine-checked closure. This header is GENERATED from run",
        f"telemetry (run_tag={run_tag}) by promote_campaign_artifact.py — not hand-authored.",
        "",
        f"  outcome     : closed · faithful · axioms {ax_str}",
        f"  domain      : {domain.strip() or cct.get('domain', 'unspecified')}",
        f"  time        : time-to-closure {_fmt(ttc.get('mean'))}s (first {_fmt(ttc.get('first'))}s · "
        f"p50 {_fmt(ttc.get('p50'))}s · p95 {_fmt(ttc.get('p95'))}s) · campaign span {_fmt(cct.get('span_s'))}s "
        f"(lead {_fmt(lead)}s)",
        f"  compute     : cost-to-closure {_fmt(ctc.get('mean'))}s mean · {_fmt(ctc.get('total_wall_s'))}s total",
        f"  yield       : {yld.get('closed', 0)}/{cct.get('attempts', 0)} attempts closed "
        f"({yld.get('failed', 0)} failed)",
        f"  phases      : {ph_str}",
        f"  reuse       : {reuse_str}",
        f"  moves       : {mv_str}",
    ]
    if family:
        L.extend(_family_block(run_tag, only=family_runs))
    L.extend(["-/", ""])
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
    ap.add_argument("--family", action="store_true",
                    help="also render the campaign-FAMILY rollup (combined wall + per-run roles) — the honest "
                         "P0 for a milestone proven in one run and target-closed in a later reuse run")
    ap.add_argument("--family-runs", default="",
                    help="comma-separated member run_tags to RESTRICT the family rollup to (exclude pre-fix / "
                         "debugging runs whose wall was bug-thrash, not proving — keeps the P0 un-confounded)")
    ap.add_argument("--allow-nonstandard-body", action="store_true",
                    help="override the publish-boundary guard (file a body with a `sorry`/local `axiom` even so). "
                         "For a DELIBERATELY axiomatic development whose header honestly lists the axioms — NOT for "
                         "a composite whose probe standalone stubbed its cited rungs (file the substrate instead).")
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
    # PUBLISH-BOUNDARY GUARD (2026-06-30 RCA): refuse to file a probe-world standalone (cited rungs stubbed as
    # `axiom`) or a body with a `sorry` under a clean-axioms header — that is the laundering-looking disconnect.
    # The real self-contained proof is the SUBSTRATE (the sidecar's `theory_file`); file THAT.
    _markers = _laundering_markers(body)
    if _markers and not a.allow_nonstandard_body:
        _sc = _p0_sidecar(CLOSURES / f"{a.target}.lean") or {}
        _tf = _sc.get("theory_file")
        print("REFUSED to file — the body is not a self-contained kernel-clean proof (would look laundered):")
        for m in _markers[:12]:
            print(f"  · {m}")
        print("This is the PROBE-WORLD standalone (cited banked rungs axiomatised for portability), not the real")
        print("proof. File the persisted SUBSTRATE instead" + (f": {_tf}" if _tf else " (the campaign theory .lean)")
              + " — verify it is `#print axioms`-clean + sorry-free, then `--from-file <substrate>`.")
        print("(If this is a deliberately-axiomatic development whose header lists the axioms, pass --allow-nonstandard-body.)")
        return 2
    _fam_runs = {s.strip() for s in a.family_runs.split(",") if s.strip()} or None
    header = build_header(a.run_tag, a.target, body_path, Path(a.log) if a.log else None,
                          axioms=a.axioms, domain=a.domain, family=a.family, family_runs=_fam_runs)
    dest = Path(a.dest or a.from_file)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(header + body, encoding="utf-8")
    print(f"FILED {dest} (verbatim proof + generated provenance header)")
    print("--- header ---")
    print(header)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
