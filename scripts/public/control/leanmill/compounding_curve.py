#!/usr/bin/env python3
"""Compounding-curve telemetry (#110) — make the self-evolving loop's compounding LEGIBLE (or falsify it).

READ-ONLY over the governance exhaust (never a soundness surface):
  • adhoc_closure_certificates.jsonl  → kernel-closed rungs over time (the verified-rung tree growth)
  • solver_lane_attempts.db           → wallclock-per-rung trend + per-run move mix
  • RE-DERIVATION RATE                → closures whose target was ALREADY certified at attempt time
    (the amnesia metric: ~100% re-derivation before the 2026-06-12 persistence/compounding fixes; should → 0 after)

Usage:
  python -m scripts.public.control.leanmill.compounding_curve [--repo .] [--json OUT] [--selftest]
Emits a markdown summary to stdout; `--json` additionally writes a dashboard-shaped payload.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from collections import defaultdict
from pathlib import Path

CERTS_REL = "analytics/public/queries/adhoc_closure_certificates.jsonl"
DB_REL = "analytics/public/queries/solver_lane_attempts.db"


def load_certs(repo: Path) -> "list[dict]":
    p = repo / CERTS_REL
    if not p.exists():
        return []
    out = []
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue   # a torn line never breaks telemetry
    return sorted(out, key=lambda d: d.get("ts") or "")


def rungs_over_time(certs: "list[dict]") -> "list[dict]":
    """Cumulative kernel-closed DISTINCT targets by timestamp (the verified-rung growth curve)."""
    seen: set = set()
    curve = []
    for c in certs:
        if c.get("outcome") != "closed":
            continue
        t = c.get("target")
        if t in seen:
            continue
        seen.add(t)
        curve.append({"ts": c.get("ts"), "target": t, "cumulative_rungs": len(seen)})
    return curve


def _clean_since() -> str:
    """CLEAN-REGIME cutoff (ISO ts). The historical ledger is contaminated by this period's fixed bugs (carrier
    rows, GATE/firewall bugs, credit-starved retrieval, test probes), so observational compounding signals over
    it are NOISE. Per AGENTS.md truth-seeking + the operator's call ('fwd-looking if we cannot filter'): anchor
    the metrics to runs AFTER the fixes landed, and let them ACCRUE. Mirrors `move_calibration`'s admissibility
    cutoff. Override with ZTARE_LEANMILL_COMPOUNDING_CLEAN_SINCE; default = post this session's fixes."""
    import os
    return os.environ.get("ZTARE_LEANMILL_COMPOUNDING_CLEAN_SINCE", "2026-06-24T00:00:00+00:00")


_NOISE_TARGETS = {"bank_wiring_probe", "cite_probe_lemma"}


def _is_noise_target(name: str) -> bool:
    """Test/wiring probes that pollute the metric (they're not real research closures). Conservative: an explicit
    set + the `_probe` convention (a genuine lemma almost never ends in `_probe`)."""
    n = (name or "").strip()
    return n in _NOISE_TARGETS or n.endswith("_probe") or n.startswith("probe_")


def _rederivation_key(cert: dict) -> str:
    """Identity of the THEOREM a cert closed, for the re-derivation metric. Keyed by the α-normalized STATEMENT
    (binder-name / whitespace invariant), NOT the target NAME — the planner gives DIFFERENT theorems the same
    generic node name (`iso_lemma1` is ≥3 distinct lemmas), so name-keying FALSELY flags them as re-derivation
    (2026-06-19 RCA). Reuses the canonical α-key (`proof_cache.normalize_statement_equiv`) + decl parser. Falls
    back to `goal_sha` (still statement-identity, never name) then the raw target only when no source is present."""
    probe = cert.get("recompilable_probe") or ""
    tgt = cert.get("target") or ""
    if probe.strip():
        try:
            import sys, os
            sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "src"))
            from ztare.leanmill.solver.statement_integrity import decl_blocks
            from ztare.leanmill.solver.proof_cache import normalize_statement_equiv
            blocks = dict(decl_blocks(probe))
            stmt = blocks.get(tgt) or (next(iter(blocks.values()), "") if len(blocks) == 1 else "")
            if stmt.strip():
                return "stmt::" + normalize_statement_equiv(stmt)
        except Exception:  # noqa: BLE001 — telemetry must never crash; degrade to a statement-identity fallback
            pass
    gs = cert.get("goal_sha")
    return ("sha::" + gs) if gs else ("name::" + tgt)


def rederivation_rate(certs: "list[dict]") -> dict:
    """Closures of an ALREADY-certified STATEMENT = re-derivation (the amnesia metric). First closure per
    statement is genuine; every later 'closed' cert for the SAME statement (α-equivalent) re-proved known work.
    Keyed by statement-identity (see `_rederivation_key`), not the planner's generic target name. Rejections are
    excluded — governance refusing a re-proof is the system working, not amnesia."""
    first_ts: dict = {}
    redo, total = 0, 0
    by_target: "dict[str, int]" = defaultdict(int)
    for c in certs:
        if c.get("outcome") != "closed":
            continue
        k = _rederivation_key(c)
        total += 1
        if k in first_ts:
            redo += 1
            by_target[c.get("target") or k] += 1
        else:
            first_ts[k] = c.get("ts")
    return {"closures": total, "distinct_rungs": len(first_ts), "rederived": redo,
            "rederivation_rate": round(redo / total, 3) if total else None,
            "worst_offenders": sorted(by_target.items(), key=lambda kv: -kv[1])[:5]}


def reuse_rate(certs: "list[dict]") -> dict:
    """COMPOUNDING REUSE metric (DreamProver-style; the literature's non-negotiable bar — a lemma bank is only
    REAL if banked results are later CITED. Prior 'growing library' systems (LEGO-Prover, TroVE) reported gains
    that EVAPORATED under compute-matched baselines and whose lemmas were single-use; the antidote is to measure
    reuse explicitly. Re-derivation (above) is the DUAL: re-derivation↓ and reuse↑ together = real compounding).
    Two rates over the closure-cert history in ts order:
      • `proof_reuse_rate` — fraction of closures whose proof CITES a lemma banked by an EARLIER closure
        (DreamProver's 'fraction of solved theorems depending on a learned lemma');
      • `lemma_reuse_rate`  — fraction of banked lemmas (distinct earlier-closed targets) later cited ≥1×
        (DreamProver's 'fraction of stored lemmas reused').
    Citation = a token-boundary NAME match in the proof text — a LOWER BOUND (`aesop`/`simp` can use a banked
    lemma by TYPE without naming it; never an over-count). COMPUTE-CONTROL CAVEAT: this counts citations, NOT a
    compute-matched lift — a reuse number is necessary-but-not-sufficient evidence; pair it with an A/B
    (compound on/off, same budget) before claiming the bank causes closures (the exact bar prior work failed)."""
    import re as _re
    banked: dict = {}                                # name -> first-closed ts (lemmas available to cite later)
    cited: set = set()
    closures, with_reuse = 0, 0
    by_reused: "dict[str, int]" = defaultdict(int)
    for c in certs:
        if c.get("outcome") != "closed":
            continue
        name = (c.get("target") or "").strip()
        proof = c.get("proof_text") or ""
        closures += 1
        hits = [n for n in banked if n and n != name
                and _re.search(r"(?<![\w.'])" + _re.escape(n) + r"(?![\w.'])", proof)]
        if hits:
            with_reuse += 1
            for n in hits:
                cited.add(n); by_reused[n] += 1
        if name and name not in banked:
            banked[name] = c.get("ts")
    nb = len(banked)
    return {"closures": closures, "banked_lemmas": nb,
            "proofs_citing_a_banked_lemma": with_reuse,
            "proof_reuse_rate": round(with_reuse / closures, 3) if closures else None,
            "lemmas_reused": len(cited),
            "lemma_reuse_rate": round(len(cited) / nb, 3) if nb else None,
            "top_reused": sorted(by_reused.items(), key=lambda kv: -kv[1])[:5]}


def wallclock_and_moves(repo: Path) -> dict:
    """Per-run-tag: attempts, closes, wallclock, and whether the RETIRED cold one-shots still fire (should be 0
    after the agent-first ladder, 2026-06-12)."""
    p = repo / DB_REL
    if not p.exists():
        return {}
    out: dict = {}
    try:
        with sqlite3.connect(str(p)) as con:
            rows = con.execute(
                "SELECT COALESCE(run_tag,'(untagged)'), COUNT(*), "
                "SUM(CASE WHEN outcome LIKE '%closed%' THEN 1 ELSE 0 END), "
                "ROUND(SUM(COALESCE(wallclock_s,0))), "
                "SUM(CASE WHEN provider IN ('claude_opus','codex_gpt5','gemini_flash','deepseek_v2',"
                "'leancopilot','leanhammer') THEN 1 ELSE 0 END) "
                "FROM attempts GROUP BY 1 ORDER BY MAX(attempt_at) DESC LIMIT 12").fetchall()
    except sqlite3.Error:
        return {}
    for tag, n, closes, wall, cold in rows:
        out[tag] = {"attempts": n, "closes": closes or 0, "wallclock_s": wall or 0,
                    "cold_oneshot_attempts": cold or 0}
    return out


def windowed_health(certs: "list[dict]", recent_n: int = 40) -> dict:
    """CLEAN-REGIME (forward-looking) compounding health — rates over closures SINCE `_clean_since()` (post all the
    fixed bugs), excluding test/wiring probes, using the FULL history to decide 'seen before' / 'banked before'.
    The all-time rates are a CUMULATIVE GHOST (pre-fix re-derivations + probe pollution), so this is the number
    that reflects the engine you run NOW and ACCRUES going forward. `recent_n` is a fallback cap when too few
    clean closures exist yet. (Necessary-not-sufficient: a count window is from-use evidence, not a causal A/B.)"""
    import re as _re
    cutoff = _clean_since()
    closed = [c for c in certs if c.get("outcome") == "closed"]
    clean_idx = [i for i, c in enumerate(closed)
                 if (c.get("ts") or "") >= cutoff and not _is_noise_target(c.get("target") or "")]
    if len(clean_idx) < 5:                       # too little clean data yet ⇒ fall back to the last recent_n (still noise-filtered)
        clean_idx = [i for i in range(len(closed)) if not _is_noise_target(closed[i].get("target") or "")][-recent_n:]
    counted = set(clean_idx)
    seen: dict = {}; banked: dict = {}
    redo = tot = reuse_hits = 0
    for i, c in enumerate(closed):
        k = _rederivation_key(c)
        name = (c.get("target") or "").strip()
        proof = c.get("proof_text") or ""
        if i in counted:
            tot += 1
            if k in seen:
                redo += 1
            if any(n and n != name and _re.search(r"(?<![\w.'])" + _re.escape(n) + r"(?![\w.'])", proof) for n in banked):
                reuse_hits += 1
        seen.setdefault(k, i)
        if name and not _is_noise_target(name):
            banked.setdefault(name, i)
    return {"clean_since": cutoff, "clean_closures": tot,
            "rederivation_rate": round(redo / tot, 3) if tot else None, "rederived": redo,
            "proof_reuse_rate": round(reuse_hits / tot, 3) if tot else None,
            "proofs_citing_a_banked_lemma": reuse_hits}


def cite_rate(certs: "list[dict]") -> dict:
    """DIRECT 'compounding FIRED' signal over the CLEAN window — the dual companion to `windowed_health`'s
    re-derivation rate. The proof cache now CITES banked proofs cross-run, stamping `cited_from_cache: true` on the
    closure cert (`cost_to_close_trend`'s `bank_served_rate` reads the SAME flag, but over the FULL pre-fix history —
    a cumulative ghost). This anchors the flag to closures SINCE `_clean_since()`, excluding test/wiring probes
    (reusing the canonical clean-window + noise filter), so it reflects whether the bank is SERVING the engine you
    run NOW. A DIRECT attribution (the cache stamped it), not a name-match lower bound; complements `rederivation_rate`
    (re-derivation↓ + cite↑ = real compounding). MEASUREMENT-ONLY, read-only over the ledger."""
    cutoff = _clean_since()
    closed = [c for c in certs
              if c.get("outcome") == "closed" and not _is_noise_target(c.get("target") or "")
              and (c.get("ts") or "") >= cutoff]
    cited = sum(1 for c in closed if c.get("cited_from_cache"))
    tot = len(closed)
    return {"clean_since": cutoff, "clean_closures": tot, "cited_from_cache": cited,
            "cite_rate": round(cited / tot, 3) if tot else None}


def cost_to_close_trend(certs: "list[dict]", recent_n: int = 40) -> dict:
    """INFER-VIA-USE compounding signal (AGENTS.md: truth-seek from real runs, don't pay for a synthetic A/B).
    A compounding engine should close LATER targets CHEAPER (the bank/cache/retrieval skip re-derivation), so the
    median per-closure wallclock should trend DOWN as the corpus grows. Read straight from the `wall_s` already in
    every closure cert — no benchmark spend. OBSERVATIONAL CAVEAT (power-aware, AGENTS.md 6n.8): wallclock is
    confounded by the problem-difficulty mix across runs, so a drop is suggestive, not a controlled lift — read it
    as a trend to watch, never a causal claim. `cited_from_cache` (when present, stamped at the cert) is the DIRECT
    attribution: closures the bank SERVED instead of re-deriving."""
    ws = [c.get("wall_s") for c in certs if c.get("outcome") == "closed" and isinstance(c.get("wall_s"), (int, float))]
    served = sum(1 for c in certs if c.get("outcome") == "closed" and c.get("cited_from_cache"))
    closed = sum(1 for c in certs if c.get("outcome") == "closed")

    def _median(xs):
        s = sorted(xs)
        return None if not s else (s[len(s) // 2] if len(s) % 2 else round((s[len(s)//2 - 1] + s[len(s)//2]) / 2, 1))
    early, late = ws[:recent_n], ws[-recent_n:]
    return {"median_wall_s_all": _median(ws), "median_wall_s_early": _median(early),
            "median_wall_s_recent": _median(late), "n_with_wall_s": len(ws),
            "bank_served_closures": served, "closed": closed,
            "bank_served_rate": round(served / closed, 3) if closed else None}


def budget_allocation(repo: Path) -> dict:
    """INFER-VIA-USE difficulty→budget signal (the safe form of the compute-optimal-allocation refinement: surface
    mis-allocation from real runs BEFORE touching the hot path — a speculative router can starve provable hard
    goals or blow budget, and the literature says the win is regime-dependent). Bins attempts by the calibrated
    `est_p_close` (the move-policy's at-dispatch forecast) and reports count / median wallclock / close-rate per
    bin. Reads the attempts DB (already recorded). What to look for: a LOW-prior bin burning high wallclock at ~0
    close-rate ⇒ over-spending on (predicted-)hopeless goals (cap candidate); a HIGH-prior bin with low spend but
    sub-1.0 close-rate ⇒ under-sampling easy wins. Only THEN is a router a tiny evidence-backed tune."""
    p = repo / DB_REL
    if not p.exists():
        return {}
    bins = {"hopeless(<0.1)": (0.0, 0.1), "hard(0.1-0.3)": (0.1, 0.3),
            "med(0.3-0.6)": (0.3, 0.6), "easy(>=0.6)": (0.6, 1.01)}
    out: dict = {"clean_since": _clean_since()}
    cutoff = _clean_since()
    try:
        with sqlite3.connect(str(p)) as con:
            for label, (lo, hi) in bins.items():
                # CLEAN-REGIME only (attempt_at >= cutoff) so the bin isn't pre-fix / dead-instrument noise — a 0%
                # hopeless bin is only a real "don't burn budget" signal post-fix. est_p_close/attempt_at absent on
                # an old schema → the query raises → caught below.
                n, closed, avgw = con.execute(
                    "SELECT COUNT(*), COALESCE(SUM(CASE WHEN COALESCE(ratified,0)>0 THEN 1 ELSE 0 END),0), "
                    "COALESCE(AVG(wallclock_s),0) FROM attempts "
                    "WHERE est_p_close >= ? AND est_p_close < ? AND attempt_at >= ?", (lo, hi, cutoff)).fetchall()[0]
                if n:
                    out[label] = {"attempts": n, "close_rate": round((closed or 0) / n, 3),
                                  "avg_wallclock_s": round(avgw or 0, 1)}
    except sqlite3.Error:
        return {"note": "attempts DB lacks est_p_close/attempt_at/wallclock_s columns (older schema)"}
    return out


def report(repo: Path) -> dict:
    certs = load_certs(repo)
    curve = rungs_over_time(certs)
    rr = rederivation_rate(certs)
    reuse = reuse_rate(certs)
    recent = windowed_health(certs)
    cite = cite_rate(certs)
    cost = cost_to_close_trend(certs)
    alloc = budget_allocation(repo)
    runs = wallclock_and_moves(repo)
    return {"curve": curve, "rederivation": rr, "reuse": reuse, "recent": recent,
            "cite_rate": cite, "cost": cost, "budget_allocation": alloc, "runs": runs}


def render_markdown(rep: dict) -> str:
    lines = ["# Compounding curve — verified-rung growth + amnesia metric", ""]
    rr = rep["rederivation"]
    lines.append(f"**Distinct kernel-closed rungs:** {rr['distinct_rungs']}  |  "
                 f"**re-derivation rate:** {rr['rederivation_rate']} "
                 f"({rr['rederived']}/{rr['closures']} closures re-proved known work — should trend → 0 "
                 "after the 2026-06-12 persistence fixes)")
    if rr["worst_offenders"]:
        lines.append("  worst: " + ", ".join(f"{t}×{n}" for t, n in rr["worst_offenders"]))
    ru = rep.get("reuse") or {}
    if ru:
        lines.append(f"\n**Compounding reuse:** proof-reuse {ru.get('proof_reuse_rate')} "
                     f"({ru.get('proofs_citing_a_banked_lemma')}/{ru.get('closures')} closures cite a banked lemma)  |  "
                     f"lemma-reuse {ru.get('lemma_reuse_rate')} ({ru.get('lemmas_reused')}/{ru.get('banked_lemmas')} "
                     "banked lemmas later cited — name-match LOWER BOUND; pair with a compute-matched A/B before "
                     "claiming the bank CAUSES closures)")
        if ru.get("top_reused"):
            lines.append("  most-cited: " + ", ".join(f"{t}×{n}" for t, n in ru["top_reused"]))
    cr = rep.get("cite_rate") or {}
    if cr:
        lines.append(f"\n**Cache-cite (compounding FIRED, clean window since {str(cr.get('clean_since'))[:10]}):** "
                     f"cite-rate {cr.get('cite_rate')} ({cr.get('cited_from_cache')}/{cr.get('clean_closures')} "
                     "clean closures stamped `cited_from_cache` — DIRECT attribution; complements re-derivation↓)")
    lines.append("\n## Rung growth")
    for pt in rep["curve"][-10:]:
        lines.append(f"- {str(pt['ts'])[:16]}  #{pt['cumulative_rungs']}  {pt['target']}")
    lines.append("\n## Recent runs (attempts / closes / wallclock / cold-oneshot attempts)")
    for tag, m in rep["runs"].items():
        cold_flag = "  ⚠️ cold one-shots fired (pre-agent-first?)" if m["cold_oneshot_attempts"] else ""
        lines.append(f"- `{tag}`: {m['attempts']} att, {m['closes']} closed, {m['wallclock_s']}s"
                     f", cold={m['cold_oneshot_attempts']}{cold_flag}")
    return "\n".join(lines)


def _selftest() -> int:
    import tempfile
    fails: "list[str]" = []

    def ok(name, cond):
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}")
        if not cond:
            fails.append(name)

    repo = Path(tempfile.mkdtemp(prefix="cc_"))
    (repo / "analytics/public/queries").mkdir(parents=True)
    certs = [
        {"ts": "2026-06-10T00:00:00", "target": "A", "outcome": "closed"},
        {"ts": "2026-06-11T00:00:00", "target": "B", "outcome": "closed"},
        {"ts": "2026-06-12T00:00:00", "target": "A", "outcome": "closed"},          # re-derivation
        {"ts": "2026-06-12T01:00:00", "target": "A", "outcome": "rejected_governance"},  # NOT amnesia
        # clean-window closures (>= default _clean_since 2026-06-24) for the cite-rate metric. The pre-fix A/B rows
        # above are < _clean_since ⇒ already exercise the clean-window EXCLUSION; cite_probe exercises noise-filter.
        {"ts": "2026-06-24T00:00:00+00:00", "target": "C", "outcome": "closed", "cited_from_cache": True},   # cache fired
        {"ts": "2026-06-24T01:00:00+00:00", "target": "D", "outcome": "closed"},                              # not cited
        {"ts": "2026-06-24T02:00:00+00:00", "target": "cite_probe", "outcome": "closed", "cited_from_cache": True},  # noise → excluded
    ]
    (repo / CERTS_REL).write_text("\n".join(json.dumps(c) for c in certs))
    rep = report(repo)
    ok("curve counts distinct rungs in ts order",
       [p["cumulative_rungs"] for p in rep["curve"]][:2] == [1, 2] and rep["curve"][0]["target"] == "A")
    ok("re-derivation: A re-proved once; rejection excluded",
       rep["rederivation"]["rederived"] == 1 and rep["rederivation"]["worst_offenders"][0] == ("A", 1))
    ok("missing DB is safe (empty runs)", rep["runs"] == {})
    cr = rep["cite_rate"]
    ok("cite-rate: clean window only, noise + pre-clean excluded (1 cited / 2 clean closures)",
       cr["clean_closures"] == 2 and cr["cited_from_cache"] == 1 and cr["cite_rate"] == 0.5)
    ok("markdown renders cite-rate", "Cache-cite" in render_markdown(rep) and "re-derivation rate" in render_markdown(rep))
    ok("empty repo is safe", report(Path(tempfile.mkdtemp()))["cite_rate"]["cited_from_cache"] == 0)
    print("SELFTEST", "PASSED" if not fails else f"FAILED: {fails}")
    return 0 if not fails else 1


DEFAULT_JSON_REL = "analytics/public/leanmill/dashboard_data/compounding_curve.json"   # the leanmill dashboard home


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=".")
    ap.add_argument("--json", nargs="?", const="DEFAULT", default=None,
                    help=f"also write the dashboard JSON (bare --json ⇒ {DEFAULT_JSON_REL})")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv)
    if a.selftest:
        return _selftest()
    repo = Path(a.repo).resolve()
    rep = report(repo)
    print(render_markdown(rep))
    if a.json:
        out = (repo / DEFAULT_JSON_REL) if a.json == "DEFAULT" else Path(a.json)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(rep, indent=2, default=str))
        print(f"\n[json] {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
