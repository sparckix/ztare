#!/usr/bin/env python3
"""THE LeanMill dashboard (#119) — ONE integrated view over every leanmill surface (operator mandate
2026-06-12: "integrate all the dashboards within leanmill into one").

WHY scripts/ (the invariant): this is REPORTING over the canonical artifacts — the attempts DB, the
closure-certificate ledger, the no-good store and the compounding-curve exports. It computes nothing the
kernel depends on; src/ stays the apparatus, this renders it.

Mines, per run_tag (and overall):
  • attempts / closures / RATIFIED closures / advances, wallclock by move (the burn-vs-work view)
  • the guard telemetry the 2026-06-12 hardening added: in-run dedup skips, warm-goal-cap refusals,
    GAP-carrying failures (informative vs blind)
  • cert health: verified / integrity-unverified / governance-rejected (+ the laundering reasons)
  • trust-conservation verdict per recent run (run_standards.trust_conservation_audit)
  • proven-rung shelf (kernel-closed, citable — target, goal_sha, probe size)

INTEGRATION CONTRACT (no frankenstein): the existing workers stay the CANONICAL computers —
compounding_curve.py, build_frontier_ledger.py, observability.py, station_health_dashboard.py,
factory_intelligence.py, evaluation_no_lift_report.py each keep producing their JSON artifacts; this
module MINES only the two stores nothing else mines (attempts DB + cert ledger + faithfulness
round-trip observations) and READS every other view's artifact, rendering ONE html + ONE bundle.
A missing artifact renders as an explicit "not produced yet" row, never a crash (graceful sections).

Outputs analytics/public/leanmill/dashboard_data/leanmill_dashboard.{json,html} — the ONE entry.

  python scripts/public/control/leanmill/leanmill_dashboard.py [--out DIR] [--since ISO]
  python scripts/public/control/leanmill/leanmill_dashboard.py --selftest
"""
from __future__ import annotations

import argparse
import html
import json
import sqlite3
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO / "src"))

DEFAULT_DB = REPO / "analytics/public/queries/solver_lane_attempts.db"
DEFAULT_CERTS = REPO / "analytics/public/queries/adhoc_closure_certificates.jsonl"
DEFAULT_OUT = REPO / "analytics/public/leanmill/dashboard_data"


def mine_attempts(db_path: Path, since: str) -> dict:
    """Per-run attempt rollups + the hardening-guard telemetry counters."""
    con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    runs: dict = {}
    q = ("select run_tag, move, outcome, ratified, wallclock_s, notes from attempts "
         "where attempt_at >= ? order by attempt_at")
    for tag, move, outcome, ratified, wall, notes in con.execute(q, (since,)):
        r = runs.setdefault(tag or "(untagged)", {
            "attempts": 0, "closed": 0, "ratified": 0, "advanced": 0,
            "wallclock_by_move": {}, "dedup_skips": 0, "cap_refusals": 0, "gap_failures": 0})
        r["attempts"] += 1
        r["wallclock_by_move"][move] = round(r["wallclock_by_move"].get(move, 0) + (wall or 0), 1)
        if outcome == "closed":
            r["closed"] += 1
        if ratified == 1:
            r["ratified"] += 1
        if outcome == "advanced":
            r["advanced"] += 1
        n = notes or ""
        if "in-run dedup" in n:
            r["dedup_skips"] += 1
        if "warm_goal_cap" in n:
            r["cap_refusals"] += 1
        if "| GAP:" in n:
            r["gap_failures"] += 1
    return runs


def mine_certs(certs_path: Path, since: str) -> dict:
    """Cert-ledger health + the citable rung shelf."""
    out = {"verified": 0, "integrity_unverified": 0, "rejected": 0,
           "rejection_reasons": {}, "rungs": []}
    try:
        lines = certs_path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return out
    for ln in lines:
        try:
            c = json.loads(ln)
        except ValueError:
            continue
        if c.get("disposition_for") or str(c.get("ts") or "") < since:
            continue
        gov = c.get("governance") or {}
        if c.get("outcome") == "closed":
            if gov.get("integrity_unverified"):
                out["integrity_unverified"] += 1
            else:
                out["verified"] += 1
                out["rungs"].append({"target": c.get("target"), "goal_sha": c.get("goal_sha"),
                                     "probe_bytes": len(c.get("recompilable_probe") or ""),
                                     "ts": c.get("ts")})
        elif c.get("outcome") == "rejected_governance":
            out["rejected"] += 1
            for f in ((gov.get("governance_kernel") or {}).get("confirmed") or ["unspecified"]):
                out["rejection_reasons"][f] = out["rejection_reasons"].get(f, 0) + 1
    return out


ABSORBED_VIEWS = {
    # section title → (artifact relpath under dashboard_data | absolute fallback, producer command)
    "Compounding curve (rungs over time, re-derivation rate)":
        ("compounding_curve.json", "python scripts/public/control/leanmill/compounding_curve.py --json"),
    "Build-frontier ledger (built shelf vs GAPs)":
        ("build_frontier_ledger.json", "python scripts/public/control/leanmill/build_frontier_ledger.py --json DEFAULT"),
    "Factory observability":
        ("leanmill_observability.json", "python scripts/public/control/leanmill/observability.py"),
    "Station health (residual-C factory)":
        ("station_health_dashboard.json", "python scripts/public/control/leanmill/station_health_dashboard.py"),
    "Factory intelligence":
        ("leanmill_factory_intelligence.json", "python scripts/public/control/leanmill/factory_intelligence.py"),
    "No-lift receipts (evaluation harness)":
        ("evaluation_harness_no_lift_report.json", "python scripts/public/control/leanmill/evaluation_no_lift_report.py"),
    "Solver-lane telemetry (moves / exits / efficiency)":
        ("solver_lane_telemetry.json", "python scripts/public/control/leanmill/solver_lane_telemetry.py"),
    "Non-math governance wedge (firewall vs LLM judge)":
        ("nonmath_firewall_ab.json",
         "PYTHONPATH=src ./venv/bin/python projects/leanmill_experiments/firewall_vs_agent_judge.py --real --json"),
}


def read_absorbed(dash_dir: Path) -> dict:
    """Read every absorbed view's canonical artifact (graceful on absence — explicit, never silent)."""
    out: dict = {}
    for title, (rel, producer) in ABSORBED_VIEWS.items():
        p = dash_dir / rel
        try:
            out[title] = {"artifact": rel, "data": json.loads(p.read_text(encoding="utf-8")),
                          "mtime": p.stat().st_mtime}
        except OSError:
            out[title] = {"artifact": rel, "missing": True, "producer": producer}
        except ValueError as e:
            out[title] = {"artifact": rel, "error": f"unparseable: {e}"[:120]}
    return out


def mine_faithfulness(obs_path: Path, since: str) -> dict:
    """The autoformalizer FUNNEL nothing else mines: faithfulness round-trip verdicts
    (OUT_DIR/faithfulness_roundtrip_observations.jsonl) — admitted vs rejected + top rejection text."""
    out = {"observations": 0, "admitted": 0, "rejected": 0, "recent_rejections": []}
    try:
        lines = obs_path.read_text(encoding="utf-8").splitlines()
    except OSError:
        out["missing"] = True
        return out
    for ln in lines:
        try:
            r = json.loads(ln)
        except ValueError:
            continue
        if str(r.get("ts") or r.get("at") or "") < since:
            continue
        out["observations"] += 1
        verdict = str(r.get("verdict") or r.get("faithful") or "").lower()
        if verdict in ("true", "faithful", "yes", "admitted"):
            out["admitted"] += 1
        else:
            out["rejected"] += 1
            if len(out["recent_rejections"]) < 5:
                out["recent_rejections"].append(str(r.get("reason") or r.get("raw") or "")[:140])
    return out


def mine_work_receipts(ledger: Path, since: str) -> dict:
    """Theory-work credit accounting (#123): theory_extension receipts + consumer stamps — definitions
    earn through USE; this view is what makes that credit VISIBLE (an agent's theory work must show in
    the progress surface or it stays behaviorally second-class)."""
    out = {"theory_extensions": 0, "completed": 0, "rejected": 0, "gaps": 0,
           "consumer_stamps": 0, "recent": []}
    try:
        lines = ledger.read_text(encoding="utf-8").splitlines()
    except OSError:
        out["missing"] = True
        return out
    for ln in lines:
        try:
            r = json.loads(ln)
        except ValueError:
            continue
        if r.get("consumer_stamp_for") is not None:
            out["consumer_stamps"] += 1
            continue
        if str(r.get("ts") or "") < since:
            continue
        item = r.get("item") or {}
        if item.get("kind") == "theory_extension":
            out["theory_extensions"] += 1
            v = r.get("verdict")
            out["completed" if v == "completed" else "rejected" if v == "rejected" else "gaps"] += 1
            if len(out["recent"]) < 8:
                out["recent"].append({"statement": str(item.get("statement"))[:80], "verdict": v,
                                      "campaign": item.get("campaign"),
                                      "new_decls": (r.get("formal_leg") or {}).get("new_decls")})
    return out


def conservation(since: str, run_tags: "list[str]") -> dict:
    """Per-run trust-conservation verdicts (the seam check no layer-local test can do)."""
    try:
        from ztare.leanmill.run_standards import trust_conservation_audit
    except Exception as e:  # noqa: BLE001
        return {"error": repr(e)[:120]}
    return {t: trust_conservation_audit(since, run_tag=t) for t in run_tags if t != "(untagged)"}


def render_html(bundle: dict) -> str:
    e = html.escape

    def table(rows, headers):
        h = "".join(f"<th>{e(str(x))}</th>" for x in headers)
        b = "".join("<tr>" + "".join(f"<td>{e(str(c))}</td>" for c in row) + "</tr>" for row in rows)
        return f"<table><tr>{h}</tr>{b}</table>"

    runs = bundle["runs"]
    run_rows = [(t, r["attempts"], r["closed"], r["ratified"], r["advanced"], r["dedup_skips"],
                 r["cap_refusals"], r["gap_failures"],
                 round(sum(r["wallclock_by_move"].values()) / 60, 1))
                for t, r in sorted(runs.items())]
    certs = bundle["certs"]
    cons = bundle["conservation"]
    cons_rows = [(t, "OK" if (v or {}).get("ok") else ("VIOLATION" if (v or {}).get("ok") is False else "n/a"),
                  "; ".join((v or {}).get("violations", []))[:120]) for t, v in cons.items()
                 if isinstance(v, dict)]
    rung_rows = [(r["ts"][:16], r["target"], r["goal_sha"], r["probe_bytes"]) for r in certs["rungs"][-20:]]
    ff = bundle.get("faithfulness") or {}
    absorbed_html = ""
    for title, v in (bundle.get("absorbed") or {}).items():
        if v.get("missing"):
            body = f"<p><i>artifact not produced yet</i> — <code>{e(v['producer'])}</code></p>"
        elif v.get("error"):
            body = f"<p><b>artifact unreadable:</b> {e(v['error'])}</p>"
        else:
            d = v["data"]
            keys = list(d)[:14] if isinstance(d, dict) else []
            summary = {k: d[k] for k in keys if not isinstance(d.get(k), (dict, list))} if isinstance(d, dict) else {}
            sizes = {k: f"{type(d[k]).__name__}[{len(d[k])}]" for k in keys
                     if isinstance(d.get(k), (dict, list))} if isinstance(d, dict) else {}
            body = (f"<p><code>{e(v['artifact'])}</code> · scalars: {e(json.dumps(summary, default=str)[:500])}"
                    + (f" · collections: {e(json.dumps(sizes))}" if sizes else "") + "</p>")
        absorbed_html += f"<h2>{e(title)}</h2>{body}"
    return f"""<!doctype html><meta charset="utf-8"><title>LeanMill dashboard</title>
<style>body{{font:14px system-ui;margin:2rem;max-width:1100px}}table{{border-collapse:collapse;margin:.6rem 0 1.4rem}}
td,th{{border:1px solid #ccc;padding:.25rem .6rem;text-align:left}}th{{background:#f0f0f0}}h2{{margin-top:1.6rem}}</style>
<h1>LeanMill — integrated dashboard</h1>
<p>generated from the canonical artifacts (attempts DB, cert ledger, conservation audit) · window since {e(bundle["since"])}</p>
<h2>Runs (work vs burn)</h2>
{table(run_rows, ["run_tag", "attempts", "closed", "ratified", "advanced", "dedup skips", "cap refusals", "GAP-carrying fails", "agent-min"])}
<h2>Certificate health</h2>
<p>verified: <b>{certs["verified"]}</b> · integrity-unverified (hollow): <b>{certs["integrity_unverified"]}</b> ·
governance-rejected: <b>{certs["rejected"]}</b> · rejection reasons: {e(json.dumps(certs["rejection_reasons"]))}</p>
<h2>Trust conservation (per run)</h2>
{table(cons_rows, ["run_tag", "verdict", "violations"])}
<h2>Proven rung shelf (kernel-closed, citable)</h2>
{table(rung_rows, ["ts", "target", "goal_sha", "probe bytes"])}
<h2>Theory work (definitions/API — credit through use)</h2>
<p>{("<i>no theory receipts yet</i>" if (bundle.get("work_receipts") or {}).get("missing") else
     f"extensions: <b>{bundle['work_receipts']['theory_extensions']}</b> · completed: "
     f"<b>{bundle['work_receipts']['completed']}</b> · rejected: <b>{bundle['work_receipts']['rejected']}</b> · "
     f"consumer stamps (definitions actually USED): <b>{bundle['work_receipts']['consumer_stamps']}</b>")}</p>
<h2>Autoformalizer faithfulness funnel</h2>
<p>{("<i>no observations yet</i>" if ff.get("missing") else
     f"observations: <b>{ff.get('observations', 0)}</b> · admitted: <b>{ff.get('admitted', 0)}</b> · "
     f"rejected: <b>{ff.get('rejected', 0)}</b>")}</p>
{absorbed_html}
"""


_CHEAP_PRODUCERS = [   # read-only producers (DB/cert mining — NO LLM, NO Lean) safe to auto-refresh on build.
    ("compounding_curve.py", ["--json"]),
    ("solver_lane_telemetry.py", ["--json"]),
    ("build_frontier_ledger.py", ["--json", "DEFAULT"]),
    # NOTE: the "Non-math governance wedge" producer is DELIBERATELY excluded — it dispatches the subscription
    # LLM judge (token cost), so it refreshes MANUALLY only. Auto-refresh must never auto-spend.
]


def _refresh_cheap_producers() -> None:
    """Run the cheap, read-only ABSORBED_VIEWS producers so their views stay LIVE on every dashboard build,
    not just when manually run (the gap: `build()` only READS artifacts; nothing refreshed the new views).
    Each is a bounded, fail-quiet subprocess (the same src→scripts boundary pattern `regenerate_dashboard`
    uses). A stale view is acceptable; a crashed build is not — so every failure is swallowed."""
    import subprocess as _sp
    here = Path(__file__).resolve().parent
    for fname, argv in _CHEAP_PRODUCERS:
        script = here / fname
        if not script.exists():
            continue
        try:
            _sp.run([sys.executable, str(script), *argv], cwd=str(REPO), timeout=120,
                    capture_output=True, text=True)
        except Exception:  # noqa: BLE001 — observability must never break the build
            pass


def build(db: Path = DEFAULT_DB, certs: Path = DEFAULT_CERTS, out_dir: Path = DEFAULT_OUT,
          since: str = "2026-06-01", dash_dir: "Path | None" = None,
          faithfulness_obs: "Path | None" = None, refresh: bool = False) -> dict:
    if refresh:
        _refresh_cheap_producers()   # keep the cheap read-only views fresh (NOT the LLM-judge wedge)
    runs = mine_attempts(db, since)
    dd = dash_dir if dash_dir is not None else DEFAULT_OUT
    fo = faithfulness_obs if faithfulness_obs is not None else (
        REPO / "analytics/public/queries/faithfulness_roundtrip_observations.jsonl")
    bundle = {"since": since, "runs": runs, "certs": mine_certs(certs, since),
              "conservation": conservation(since, list(runs)),
              "faithfulness": mine_faithfulness(fo, since),
              "work_receipts": mine_work_receipts(
                  REPO / "analytics/public/queries/work_receipts.jsonl", since),
              "absorbed": read_absorbed(dd)}
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "leanmill_dashboard.json").write_text(json.dumps(bundle, indent=2, default=str), encoding="utf-8")
    (out_dir / "leanmill_dashboard.html").write_text(render_html(bundle), encoding="utf-8")
    return bundle


def _selftest() -> int:
    import tempfile
    fails: "list[str]" = []

    def ok(name, cond):
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}")
        if not cond:
            fails.append(name)

    td = Path(tempfile.mkdtemp(prefix="dash_"))
    db = td / "a.db"
    con = sqlite3.connect(db)
    con.execute("create table attempts (run_tag text, move text, outcome text, ratified int, "
                "wallclock_s real, notes text, attempt_at text)")
    con.executemany("insert into attempts values (?,?,?,?,?,?,?)", [
        ("r1", "claude_warm", "closed", 1, 400.0, "agentic_leaf closed", "2026-06-12T10:00:00"),
        ("r1", "native_hammer", "failed_compile", None, 0.01,
         "[native_hammer] in-run dedup: identical goal", "2026-06-12T10:01:00"),
        ("r1", "claude_warm", "failed_compile", None, 0.0,
         "warm_goal_cap: 2 prior warm attempts", "2026-06-12T10:02:00"),
        ("r1", "claude_warm", "failed_compile", None, 300.0,
         "agentic_leaf open: uses_sorry | GAP: missing lemma", "2026-06-12T10:03:00"),
        ("r1", "conjecture_lemma", "advanced", None, 30.0, "compiled", "2026-06-12T10:04:00"),
    ])
    con.commit(); con.close()
    certs = td / "c.jsonl"
    certs.write_text("\n".join(json.dumps(x) for x in [
        {"ts": "2026-06-12T10:00:01", "target": "t1", "outcome": "closed",
         "recompilable_probe": "import Mathlib\ntheorem t1 : True := trivial", "governance": {}, "goal_sha": "aa"},
        {"ts": "2026-06-12T10:00:02", "target": "t2", "outcome": "closed",
         "recompilable_probe": "", "governance": {"integrity_unverified": True}},
        {"ts": "2026-06-12T10:00:03", "target": "t3", "outcome": "rejected_governance",
         "governance": {"governance_kernel": {"confirmed": ["statement_altered_confirmed"]}}},
        {"disposition_for": "k", "status": "wired"},   # disposition rows must be ignored
    ]) + "\n", encoding="utf-8")
    b = build(db=db, certs=certs, out_dir=td / "out", since="2026-06-12", dash_dir=td / "nodash",
              faithfulness_obs=td / "missing.jsonl")
    r1 = b["runs"]["r1"]
    ok("rollup counts (attempts/closed/ratified/advanced)",
       (r1["attempts"], r1["closed"], r1["ratified"], r1["advanced"]) == (5, 1, 1, 1))
    ok("guard telemetry (dedup/cap/GAP)",
       (r1["dedup_skips"], r1["cap_refusals"], r1["gap_failures"]) == (1, 1, 1))
    ok("cert health split", (b["certs"]["verified"], b["certs"]["integrity_unverified"],
                             b["certs"]["rejected"]) == (1, 1, 1))
    ok("rejection reason named",
       b["certs"]["rejection_reasons"].get("statement_altered_confirmed") == 1)
    ok("rung shelf carries verified rung only",
       len(b["certs"]["rungs"]) == 1 and b["certs"]["rungs"][0]["target"] == "t1")
    h = (td / "out" / "leanmill_dashboard.html").read_text(encoding="utf-8")
    ok("html renders all core sections",
       all(s in h for s in ("Runs (work vs burn)", "Certificate health", "Trust conservation",
                            "Proven rung shelf", "statement_altered_confirmed",
                            "Autoformalizer faithfulness funnel")))
    ok("json bundle written", (td / "out" / "leanmill_dashboard.json").exists())
    ok("ALL absorbed views present as sections (missing ⇒ explicit producer hint)",
       all(title in h for title in ABSORBED_VIEWS)
       and "artifact not produced yet" in h)
    # absorbed artifact present ⇒ summarized, not "missing"
    dd2 = td / "dash2"; dd2.mkdir()
    (dd2 / "compounding_curve.json").write_text(json.dumps({"re_derivation_rate": 0.31, "rungs": [1, 2]}),
                                                encoding="utf-8")
    fobs = td / "fobs.jsonl"
    fobs.write_text(json.dumps({"ts": "2026-06-12T10:00:00", "verdict": "faithful"}) + "\n"
                    + json.dumps({"ts": "2026-06-12T10:01:00", "verdict": "rejected", "reason": "vacuous"}) + "\n",
                    encoding="utf-8")
    b2 = build(db=db, certs=certs, out_dir=td / "out2", since="2026-06-12", dash_dir=dd2,
               faithfulness_obs=fobs)
    ok("absorbed artifact summarized when present",
       b2["absorbed"]["Compounding curve (rungs over time, re-derivation rate)"].get("data", {})
       .get("re_derivation_rate") == 0.31)
    ok("faithfulness funnel mined (1 admitted / 1 rejected)",
       (b2["faithfulness"]["admitted"], b2["faithfulness"]["rejected"]) == (1, 1))
    print("SELFTEST", "PASSED" if not fails else f"FAILED: {fails}")
    return 0 if not fails else 1


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    ap.add_argument("--since", default="2026-06-01")
    ap.add_argument("--no-refresh", action="store_true",
                    help="skip auto-refreshing the cheap read-only views (read existing artifacts only)")
    a = ap.parse_args()
    if a.selftest:
        sys.exit(_selftest())
    b = build(out_dir=Path(a.out), since=a.since, refresh=not a.no_refresh)
    miss = [t2 for t2, v in b["absorbed"].items() if v.get("missing")]
    print(f"dashboard: {len(b['runs'])} runs | certs verified={b['certs']['verified']} "
          f"unverified={b['certs']['integrity_unverified']} rejected={b['certs']['rejected']} | "
          f"absorbed views: {len(b['absorbed']) - len(miss)}/{len(b['absorbed'])} live"
          + (f" (missing: {', '.join(miss)})" if miss else "")
          + f" → {a.out}/leanmill_dashboard.html")
