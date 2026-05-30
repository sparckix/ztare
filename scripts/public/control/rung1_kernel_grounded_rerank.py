#!/usr/bin/env python3
"""Rung-1: Kernel-Grounded Candidate-Action Rerank (the wedge).

The single cheapest falsifier of the Path-A thesis (no training, no GNN,
no new architecture): does ranking candidate lemmas × Lean actions by
REAL pinned-kernel behaviour beat a text/accessibility-ordered candidate
pool + the SAME generic action sweep + the SAME governance filter, on
closure-or-exact-gap efficiency, with ZERO false ratifications?

Honest framing (cold cross-provider correction 2026-05-17): external
systems (LeanHammer / LeanDojo-ReProver / Lean State Search) are
candidate SOURCES and baselines, NOT strawmen. The wedge claim is
narrow: kernel-grounded candidate-ACTION ranking BEFORE search explodes
+ governance-clean feedback — not "we verify, they don't". Unavailable
external sources are recorded as UNAVAILABLE, never faked.

Corpus schema (rung1_corpus.json):
  {"rows":[{"id","bucket","statement","candidate_pool":[lemma,...],
            "intended_closer": <name|null>}]}
  bucket ∈ {control, pin_delta, escape_route, public_hammer_open, ns_gap}
  `intended_closer` is metadata ONLY (novelty gate); the scorer/baseline
  NEVER receives it.

NOT auto-run: needs the canonical pinned sandbox free + a real bucketed
corpus. Metric = closed_or_exact_gap@budget (NOT hit@k, NOT local
progress alone — compiled proofs can still be vacuous / gold-name /
one-exact? / indirect-leakage / currency-mismatched: governance decides).
"""
from __future__ import annotations
import argparse, json, os, random, re, subprocess, tempfile, threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import sys as _sys
_REPO = Path(__file__).resolve().parents[3]
if str(_REPO) not in _sys.path:
    _sys.path.insert(0, str(_REPO))
# Persistent import-amortized REPL (the accelerant): `import Mathlib`
# paid ONCE per worker process, not per probe (~300-4000x). Reuses the
# canonical leanprover-community/repl, pinned to the sandbox toolchain.
# Per-thread instance (one live process / worker; not thread-safe per
# instance — the process IS the parallelism unit).
from src.ztare.formal.lean_persistent import PersistentLean  # noqa: E402

_TL = threading.local()


def _repl(sb: Path) -> PersistentLean:
    """Thread-local persistent REPL for `sb` (lazy spawn; import paid
    once per worker thread, reused for every probe it handles)."""
    inst = getattr(_TL, "repl", None)
    if inst is None or getattr(_TL, "sb", None) != str(sb):
        if inst is not None:
            inst.close()
        inst = PersistentLean(sb)
        _TL.repl, _TL.sb = inst, str(sb)
    return inst

# canonical pinned v4.29.0 sandbox (param)
DEFAULT_SB = ("analytics/public/leanmill/external_benchmarks/"
              "sandboxes/v28A_carleson_baseline/carleson")
_STD = {"propext", "Classical.choice", "Quot.sound"}
# APPARATUS FIX (2026-05-17, operator: "this can't happen again"):
# a bare `import Mathlib\n<src>` file does NOT have Mathlib's `scoped`
# notation in scope, so a composed proof using standard notation
# (`ℝ≥0∞`, `ℝ≥0`, `∑ ∈`) fails with a PARSE error ("expected token")
# that masks as a downstream "unsolved goals ⊢ sorry". Structural fix:
# prepend the standard scoped-notation prelude to EVERY probe/govern
# compile (validated at pinned v4.29.0). Conservative/additive — only
# makes MORE standard notation parse; cannot break a proof that didn't
# use it. (The DEEP fix the public repos use — LeanDojo/ReProver/
# LeanHammer elaborate against the REAL proof state in a persistent
# Lean env, never a synthesized bare file — is recorded as the durable
# next architecture; this prelude is the correct interim class-killer.)
_PRELUDE = "import Mathlib\nopen scoped ENNReal NNReal BigOperators\n"


def _root_error(out: str) -> str:
    """Repair-feedback must carry the ROOT cause, not the bare tail
    (Rung-3: the surfaced 'unsolved goals ⊢ sorry' masked the real
    'expected token on ℝ≥0∞'). Return the FIRST diagnostic error."""
    m = re.search(r"^\S+:\d+:\d+:\s*error.*$", out, re.M)
    return m.group(0) if m else (out.strip().splitlines()[-1]
                                 if out.strip() else "")
# generic action sweep — SAME for every baseline (fairness invariant)
# BRUTALLY-MINIMAL falsifier action set (lead-time fix): the slow,
# rarely-decisive tactics (aesop / apply? / nlinarith / ring / norm_num
# / omega) dominated compile cost without separating the arms. The
# question "does kernel-grounded candidate-action ranking beat
# text/random with the SAME actions?" is answered with a lean core.
# Single-step + 2-step templates. The certified multi-step proofs are
# `ext;simp only[..]`, `constructor;..`, `rw[..];simp` — single-step
# actions structurally cannot express them, which is WHY the shallow
# grid was non-probative (cold-review depth-2 ablation).
ACTIONS = [
    "exact {C}", "apply {C}", "simp only [{C}]", "rw [{C}]",
    "exact?", "simp", "simp_all",
    "ext i j <;> simp only [{C}]", "ext i <;> simp [{C}]",
    "ext i j <;> simp_all", "constructor <;> simp_all",
    "simp only [{C}] <;> exact?", "rw [{C}] <;> simp",
    "refine {C} ?_ <;> exact?",
]


def batch_probe(sb: Path, items, timeout: int = 600):
    """Probe a batch through the thread's persistent REPL. `items` =
    list of (probe_id, full_decl), full_decl a complete
    `theorem <uniqueid> … := by <tac>`. Returns {probe_id: "closed" |
    "progress" | "fail"}. Each probe is an ISOLATED check() off the
    frozen prelude env — import is amortized by the live process (once
    per worker), so the old one-file/line-span/sentinel-desync machinery
    is retired. Still sound-by-construction: a non-clean elaboration is
    never "closed".
    """
    # PERSISTENT-REPL REWRITE (2026-05-17): the old body crammed every
    # probe into ONE synthesized file to amortize `import Mathlib`, then
    # attributed errors by line-span with a trailing sentinel to detect
    # parser desync. The persistent REPL pays the import ONCE per worker
    # and elaborates each probe in an ISOLATED branch off the frozen
    # prelude env — so span-parsing AND the desync artifact class simply
    # do not exist. Each item is an independent check(); the
    # {closed|progress|fail} contract is preserved byte-for-byte so
    # _process_row_impl is untouched. Mapping is FAITHFUL to the old
    # semantics (closed = clean; progress = sorry-only / unproven, no
    # hard error; else fail). The richer 'clean unsolved-goals = honest
    # exact_gap' signal the persistent state now makes available is
    # deliberately NOT folded in here — that is a Rung-1-rerun design
    # change, separately reviewed, not a silent migration rider.
    R = _repl(sb)
    per_item = max(30, min(int(timeout), 120))
    res: dict[str, str] = {}
    for pid, decl in items:
        r = R.check(decl, per_item)
        if r["success"]:
            res[pid] = "closed"
            continue
        has_err = bool(r.get("errors"))
        has_sorry = bool(r.get("sorries"))
        # no hard error, goal merely unproven (sorry/elaborated-open)
        res[pid] = "progress" if (not has_err and has_sorry) else "fail"
    return res


def _run(sb: Path, src: str, timeout: int = 120):
    """Single submission through the thread's persistent REPL. Contract
    preserved: returns (returncode, combined_diagnostics) — rc 0 iff
    clean (no error severity, no sorry); the text carries the same
    'error'/'unknown'/'unsolved goals'/'depends on axioms:'/'Try this'
    substrings the callers (governance / closer_absent_at_pin / probe)
    grep. The prelude (`import Mathlib` + scoped notation) is the FROZEN
    base env loaded once per worker — no per-call re-import."""
    r = _repl(sb).check(src, timeout)
    return (0 if r["success"] else 1), r["raw"]


def closer_absent_at_pin(sb: Path, closer: str) -> bool:
    """STRONG novelty gate (Failure-Mode-3 / SIE lesson): name-set diff
    ('file added later') is INSUFFICIENT. Genuinely-novel iff the actual
    closer `#check @closer` ERRORS (unknown) in pinned vN."""
    if not closer:
        return False
    rc, o = _run(sb, f"#check @{closer}", 60)
    lo = o.lower()
    return ("unknown" in lo) and ("incompatible header" not in lo)


def governance(sb: Path, stmt: str, full_proof: str, timeout: int):
    """Verdict on a row that COMPILED: closure | single_lemma |
    axiom_smuggled | unverified. Reuses the bundle's authoritative
    kernel #print-axioms guard + exact?-single-lemma adjudication."""
    nocom = re.sub(r"/-.*?-/", " ", full_proof, flags=re.S)
    nocom = re.sub(r"--[^\n]*", " ", nocom)
    names = re.findall(r"\b(?:theorem|lemma)\s+([A-Za-z_][\w'.]*)", nocom)
    if not names:
        return "unverified"
    _, ao = _run(sb, full_proof + "\n"
                 + "\n".join(f"#print axioms {n}" for n in dict.fromkeys(names)),
                 timeout)
    al = ao.lower()
    deps: set[str] = set()
    for m in re.finditer(r"depends on axioms:\s*\[([^\]]*)\]", ao, re.S):
        deps |= {x.strip() for x in re.split(r"[,\s]+", m.group(1)) if x.strip()}
    if "incompatible header" in al:
        return "unverified"
    if sorted(deps - _STD) or "sorryax" in al:
        return "axiom_smuggled"
    if "unknown constant" in al or "unknown identifier" in al:
        return "unverified"
    # single-lemma laundering check (bare-goal exact?)
    _, eo = _run(sb, stmt + " := by exact?", timeout)
    if "try this" in eo.lower():
        return "single_lemma"
    # PERSIST every ratified closure for post-hoc audit (false-positive
    # hardening, operator-flagged 2026-05-18): a "closure" verdict is
    # worthless if the proof+axioms cannot be re-inspected later. Save
    # full_proof + the #print-axioms output + ts. Best-effort: NEVER let
    # a persistence failure alter the authoritative verdict.
    try:
        import time as _t
        pdir = Path("/tmp/rung1/ratified_proofs")
        pdir.mkdir(parents=True, exist_ok=True)
        nm = re.sub(r"[^A-Za-z0-9_]", "_", names[0])[:48]
        ts = _t.strftime("%Y%m%dT%H%M%S")
        (pdir / f"{nm}_{ts}.lean").write_text(
            full_proof + "\n/- #print axioms output:\n" + ao + "\n-/\n")
        with (pdir / "ratified_manifest.jsonl").open("a") as _f:
            _f.write(json.dumps({
                "name": names[0], "verdict": "closure",
                "axioms_clean_subset_of": sorted(_STD),
                "deps_seen": sorted(deps), "ts": ts}) + "\n")
    except Exception:
        pass
    return "closure"


def probe(sb: Path, stmt: str, cand: str, action: str, timeout: int):
    """One kernel probe. Returns (outcome, verdict) where outcome ∈
    {closed, progress, fail} and verdict is the governance class when
    closed (else '')."""
    tac = action.replace("{C}", cand)
    full = f"{stmt} := by {tac}"
    rc, o = _run(sb, full, timeout)
    lo = o.lower()
    if rc == 0 and "error" not in lo and "sorry" not in lo:
        return "closed", governance(sb, stmt, full, timeout)
    # honest exact-gap signal: clean 'unsolved goals' (no unknown/elab err)
    if "unsolved goals" in lo and "unknown" not in lo and "type mismatch" not in lo:
        return "progress", ""
    return "fail", ""


# --- external candidate sources: honest adapters, NEVER strawmen ---------
def source_text_bm25(goal: str, pool: list[str]) -> list[str]:
    """B0 baseline ordering: token-overlap of candidate name vs goal."""
    gt = set(re.findall(r"[A-Za-z]+", goal.lower()))
    def sc(n): return -len(set(re.findall(r"[A-Za-z]+", n.lower())) & gt)
    return sorted(pool, key=sc)


def source_external(kind: str, goal: str):
    """B1/B2/B3 hooks (Lean State Search / ReProver-LeanDojo / LeanHammer).
    Returns (None, reason) unless an adapter path is configured — recorded
    UNAVAILABLE, never faked (cold-review failure-mode-1 guard)."""
    env = os.environ.get(f"RUNG1_{kind.upper()}_CMD")
    if not env:
        return None, f"{kind}: UNAVAILABLE (no RUNG1_{kind.upper()}_CMD configured)"
    return None, f"{kind}: adapter configured but not invoked in this build"


def run_arm(sb, row, order: list[str], budget: int, timeout: int):
    """Sweep ranked (cand,action) until a verdict or budget. Returns
    (status, probes_used, verdicts) — status ∈
    {closure, exact_gap, none}; governance-clean closure only."""
    probes = 0
    saw_clean_gap = False
    for cand in order:
        for action in ACTIONS:
            if "{C}" not in action and probes and action in _swept:
                continue
            probes += 1
            outcome, verdict = probe(sb, row["statement"], cand, action, timeout)
            if outcome == "closed" and verdict == "closure":
                return "closure", probes, [verdict]
            if outcome == "progress":
                saw_clean_gap = True
            if probes >= budget:
                return ("exact_gap" if saw_clean_gap else "none"), probes, []
    return ("exact_gap" if saw_clean_gap else "none"), probes, []


_swept: set[str] = set()


def _named(stmt: str, uniq: str) -> str:
    return re.sub(r"^\s*theorem\s+\S+", f"theorem {uniq}", stmt, count=1)


def _process_row_impl(row, sb, arms, budget, timeout):
    """ONE batched compile per row amortizes import-Mathlib across the
    whole candidate×action grid (the hard-parallel lever); the batch
    also yields the kernel ranking for free; governance runs only on an
    actual batch-'closed' item (rare). Metric semantics preserved:
    probes counted in ranked order, budget cap, governance-gated
    closure, exact_gap from a clean 'progress'."""
    novel = True
    if row.get("bucket") in ("pin_delta", "escape_route"):
        novel = closer_absent_at_pin(sb, row.get("intended_closer") or "")
    rrep = {"id": row["id"], "bucket": row.get("bucket"),
            "novelty_gate_pass": novel}
    if not novel:
        rrep["skipped"] = ("closer NOT #check-absent at pin "
                           "(file-added-later is insufficient)")
        return rrep
    rid = re.sub(r"[^A-Za-z0-9_]", "", row["id"]) or "R"
    pool = list(row.get("candidate_pool", []))
    stmt = row["statement"]
    c_acts = [x for x in ACTIONS if "{C}" in x]
    noc_acts = [x for x in ACTIONS if "{C}" not in x]
    items, meta, k = [], {}, 0
    for c in pool:
        for action in c_acts:
            pid = f"{rid}p{k}"; k += 1
            items.append((pid, _named(stmt, pid)
                          + " := by " + action.replace("{C}", c)))
            meta[pid] = (c, action)
    for action in noc_acts:
        pid = f"{rid}p{k}"; k += 1
        items.append((pid, _named(stmt, pid) + " := by " + action))
        meta[pid] = (None, action)
    outc = batch_probe(sb, items, timeout=max(timeout * 5, 900))
    og = {}
    for pid, ca in meta.items():
        og[ca] = outc.get(pid, "fail")

    def kscore(c):
        return -max([{"closed": 2, "progress": 1, "fail": 0}[
            og.get((c, act), "fail")] for act in c_acts] or [0])

    text_order = source_text_bm25(stmt, pool)
    rng = random.Random(1234 + abs(hash(row["id"])) % 9999)
    rand_order = list(pool); rng.shuffle(rand_order)
    kern_order = sorted(pool, key=kscore)
    for arm, mode in arms.items():
        order = (text_order if mode == "text" else
                 rand_order if mode == "random" else kern_order)
        probes, saw_gap, status, done = 0, False, "none", False
        for c in order:
            for action in c_acts + noc_acts:
                key = (c if "{C}" in action else None, action)
                probes += 1
                o = og.get(key, "fail")
                if o == "closed":
                    tac = action.replace("{C}", c) if "{C}" in action \
                        else action
                    full = _named(stmt, f"{rid}g") + " := by " + tac
                    if governance(sb, stmt, full, timeout) == "closure":
                        status, done = "closure", True; break
                elif o == "progress":
                    saw_gap = True
                if probes >= budget:
                    done = True; break
            if done:
                break
        if status != "closure":
            status = "exact_gap" if saw_gap else "none"
        rrep[arm] = {"status": status, "probes": probes}
    return rrep


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", required=True)
    ap.add_argument("--sandbox", default=DEFAULT_SB)
    ap.add_argument("--budget", type=int, default=40)
    ap.add_argument("--timeout", type=int, default=120)
    ap.add_argument("--out", required=True)
    ap.add_argument("--workers", type=int, default=6,
                    help="parallel rows (sandbox compiles are independent; "
                         "unique tempfile/probe → thread-safe)")
    ap.add_argument("--dry-run", action="store_true",
                    help="seconds-long preflight: instant structural input "
                         "checks + 2 sanity compiles; catches plumbing bugs "
                         "BEFORE any long run")
    a = ap.parse_args()
    sb = Path(a.sandbox).expanduser().resolve()
    rows = json.load(open(a.corpus))["rows"]
    arms = {"B0_text_order": "text", "B5_random_order": "random",
            "B6_kernel_rerank": "kernel",
            "B7_kernel_rerank_governance": "kernel_gov"}

    if a.dry_run:
        errs = []
        for r in rows:                       # INSTANT (no compile)
            if not r.get("statement") or not r.get("id"):
                errs.append(f"{r.get('id')}: missing id/statement")
            if r.get("bucket") in ("pin_delta", "escape_route") \
               and not (r.get("intended_closer") or "").strip():
                errs.append(f"{r['id']}: pin_delta EMPTY intended_closer "
                            f"→ novelty gate would skip (the plumbing bug)")
            if not r.get("candidate_pool"):
                errs.append(f"{r['id']}: empty candidate_pool")
        # ONE full row end-to-end through the REAL code path (one
        # batched compile, ~tens of s) — catches NameError / logic /
        # plumbing bugs in seconds, never via a long run again.
        sanity = {}
        elig = next((r for r in rows
                     if r.get("bucket") not in ("pin_delta", "escape_route")
                     or (r.get("intended_closer") or "").strip()), None)
        if elig is not None:
            try:
                rr = _process_row_impl(elig, sb, arms, 6, 45)
                sanity["full_row_ok"] = (not rr.get("skipped")) and all(
                    isinstance(rr.get(k), dict) and "status" in rr[k]
                    for k in arms) if not rr.get("skipped") else True
                sanity["sample"] = {"id": rr["id"],
                                    "skipped": bool(rr.get("skipped")),
                                    "B7": rr.get("B7_kernel_rerank_governance")}
            except Exception as e:           # noqa: BLE001
                sanity["full_row_ok"] = False
                sanity["exception"] = f"{type(e).__name__}: {e}"
        ok = (not errs) and bool(sanity.get("full_row_ok"))
        print(json.dumps({"DRY_RUN": "PASS" if ok else "FAIL",
                           "structural_errors": errs, "sanity": sanity,
                           "n_rows": len(rows)}, indent=1))
        return 0 if ok else 3

    report = {"sandbox": str(sb), "budget": a.budget, "rows": [],
              "arms": {}, "external_sources": {}}
    for kind in ("lean_state_search", "reprover_leandojo", "leanhammer"):
        _, why = source_external(kind, "")
        report["external_sources"][kind] = why

    # arms defined above (before dry-run). B5 random-order = the NULL:
    # B7 must beat BOTH B0(text) AND B5(random) to claim kernel signal.
    tally = {k: {"closure": 0, "exact_gap": 0, "none": 0, "probes": 0,
                 "false_ratify": 0} for k in arms}

    def _process_row(row):
        return _process_row_impl(row, sb, arms, a.budget, a.timeout)

    # rows are independent; each probe is a unique-tempfile sandbox
    # compile (thread-safe). Parallelize across rows for scientific
    # yield (serial was the lead-time killer the operator flagged).
    results = []
    with ThreadPoolExecutor(max_workers=max(1, a.workers)) as ex:
        futs = {ex.submit(_process_row, r): r["id"] for r in rows}
        for fut in as_completed(futs):
            results.append(fut.result())
    order_ix = {r["id"]: i for i, r in enumerate(rows)}
    results.sort(key=lambda x: order_ix.get(x["id"], 1e9))
    for rrep in results:                       # sequential aggregation
        report["rows"].append(rrep)
        if rrep.get("skipped"):
            continue
        for arm in arms:
            st = rrep.get(arm, {}).get("status")
            if st in ("closure", "exact_gap", "none"):
                tally[arm][st] += 1
                tally[arm]["probes"] += rrep[arm].get("probes", 0)

    # pass-gate: B7 must beat the STRONGER of B0(text) and B5(random) —
    # beating text while tying random = no kernel signal (NULL not
    # rejected). Baseline = best non-kernel arm on each metric.
    n = max(1, sum(1 for r in report["rows"] if r.get("novelty_gate_pass")))
    def soeg(k):  # closed_or_exact_gap rate
        return (tally[k]["closure"] + tally[k]["exact_gap"]) / n
    def avgp(k):
        return tally[k]["probes"] / n
    base_soeg = max(soeg("B0_text_order"), soeg("B5_random_order"))
    base_probes = min(avgp("B0_text_order"), avgp("B5_random_order"))
    gate = {
        "soeg_B0_text": round(soeg("B0_text_order"), 3),
        "soeg_B5_random_NULL": round(soeg("B5_random_order"), 3),
        "soeg_B7": round(soeg("B7_kernel_rerank_governance"), 3),
        "baseline_soeg_to_beat (max text,random)": round(base_soeg, 3),
        "avg_probes_B0_text": round(avgp("B0_text_order"), 1),
        "avg_probes_B5_random_NULL": round(avgp("B5_random_order"), 1),
        "avg_probes_B7": round(avgp("B7_kernel_rerank_governance"), 1),
        "baseline_probes_to_beat (min text,random)": round(base_probes, 1),
        "false_ratify_B7": tally["B7_kernel_rerank_governance"]["false_ratify"],
        "PASS": bool(
            (soeg("B7_kernel_rerank_governance") - base_soeg >= 0.05
             or avgp("B7_kernel_rerank_governance") <= 0.8 * base_probes)
            and tally["B7_kernel_rerank_governance"]["false_ratify"] == 0),
        "note": ("first-bite gate only — NOT a SOTA-comparison claim. B7 "
                 "must beat the NULL (B5 random) as well as B0(text); "
                 "external B1/B2/B3 sources must be wired before any SOTA "
                 "comparison"),
    }
    report["tally"] = tally
    report["pass_gate"] = gate
    Path(a.out).write_text(json.dumps(report, indent=1))
    print(json.dumps({"pass_gate": gate,
                      "external_sources": report["external_sources"]}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
