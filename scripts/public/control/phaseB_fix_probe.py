#!/usr/bin/env python3
"""phaseB_fix_probe.py — pick the Phase-B axiom-audit mechanism that is
ERR-CLEAN AT SCALE (the T1 de-module fails ~42% of real files via
`public import`/`public theorem` legacy-mode rejection; validated on
only 2 rows = under-powered).

Scale: ALL real corpus rows (full 40, NOT the pinned easy-15), span
gold_n_steps. Each row still has its `sorry` ⇒ a CORRECT audit must
report `sorryAx` and introduce NO new errors vs the as-is module open.

Mechanisms:
  ENV = NO de-module: open the true module file once, then run
        `#print axioms <target>` against the returned REPL env. This is
        the preferred path if clean: no rewritten module body and no
        in-file metaprogramming.
  T2  = drop `module` line + strip leading public/private/protected
  T3  = T2 + drop a `prelude` line
  T4  = T2 + strip those modifiers ANYWHERE (not just leading) + drop
        any `@[expose]`/`meta ` leading tokens
  RUNCMD = NO de-module: as-is module file + an in-module
        `open Lean Elab Command in #eval` axiom collector (best-effort;
        if it hits the module restriction or errors, it's just dropped
        — we do NOT iterate on metaprogramming, treadmill guard).
  INJECT = NO de-module: insert the same collector immediately after
        the target declaration, preserving the namespace/section where
        the target short name is valid. This tests the likely fix for
        RUNCMD's unknown/ambiguous short-name failures.

Winner = 0 new errors, audit_ok (sorryAx) on all rows, 0 module-
restriction errors, least invasive. Machine-safe: ONE heavy proc. Run:
python3 scripts/public/control/phaseB_fix_probe.py
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(Path(__file__).parent))

MOD_ERR = re.compile(r"cannot use .#print axioms. in a .module.", re.I)
OUT = "/tmp/rung1/_phaseB_fix_probe.json"


def _drop_line(src, pred):
    out, done = [], False
    for ln in src.splitlines(keepends=True):
        if not done and pred(ln.strip()):
            done = True
            continue
        out.append(ln)
    return "".join(out)


def T2(s):
    s = _drop_line(s, lambda x: x == "module")
    return re.sub(r"(?m)^(\s*)(public|private|protected)\s+", r"\1", s)


def T3(s):
    return _drop_line(T2(s), lambda x: x == "prelude")


def T4(s):
    s = _drop_line(s, lambda x: x == "module")
    s = _drop_line(s, lambda x: x == "prelude")
    s = re.sub(r"(?m)^(\s*)@\[expose\]\s*", r"\1", s)
    s = re.sub(r"\b(public|private|protected|meta)\s+", "", s)
    return s


_DECL_START = re.compile(
    r"(?m)^(?:(?:public\s+|private\s+|protected\s+)?"
    r"(?:theorem|lemma|def|abbrev|instance|structure|class|inductive|"
    r"namespace|end|section|noncomputable|open|variable|attribute)\b"
    r"|@\[|/--|/-)")


_DECL_NAME = re.compile(
    r"(?m)^(?:public\s+|private\s+|protected\s+)?"
    r"(?:theorem|lemma)\s+([^\s(:]+)")


def _target_decl_name(src: str, hint: str) -> str:
    """Return the exact theorem/lemma declaration name containing the
    target sorry. Corpus hints are sometimes only prefixes
    (`Integrable`) or miss a prime suffix; auditing the declaration
    with the actual `sorry` is the invariant Phase-B needs."""
    matches = list(_DECL_NAME.finditer(src))
    for i, m in enumerate(matches):
        cut = matches[i + 1].start() if i + 1 < len(matches) else len(src)
        block = src[m.start():cut]
        if re.search(r"\bsorry\b", block):
            return m.group(1)
    return hint


def _inject_after_target(src: str, decl_name: str, audit_cmd: str) -> str:
    """Insert audit_cmd immediately after target theorem/lemma block,
    preserving local namespace/section name resolution. Fail-loud by
    appending at EOF only if the declaration cannot be found; the probe
    will mark that via missing sorryAx/new errors."""
    m = re.search(
        rf"(?m)^(?:public\s+|private\s+|protected\s+)?"
        rf"(theorem|lemma)\s+{re.escape(decl_name)}(?=\s|[:(\[{{]|$)",
        src)
    if not m:
        return src + audit_cmd
    nxt = _DECL_START.search(src, m.end())
    cut = nxt.start() if nxt else len(src)
    return src[:cut].rstrip() + "\n" + audit_cmd + "\n" + src[cut:].lstrip("\n")


def _raw_from_check(r: dict) -> str:
    return str(r.get("raw") or r.get("output") or "")


def _errs_from_check(r: dict) -> set:
    return {str(e)[:120] for e in (r.get("errors") or [])}


def _env_axioms(L, env, target_name: str, short: str, timeout: int = 240):
    """Run #print axioms against the already-elaborated module env.
    Full name first avoids namespace ambiguity; short-name fallback
    preserves parity with the historical #print path."""
    names = []
    if target_name:
        names.append(target_name)
    if short and short not in names:
        names.append(short)
    last = {"raw": "", "errs": set(), "name": None}
    for nm in names:
        r = L.check(f"#print axioms {nm}", timeout=timeout, env=env)
        raw = _raw_from_check(r)
        errs = _errs_from_check(r)
        last = {"raw": raw, "errs": errs, "name": nm}
        low = raw.lower()
        if ("sorryax" in low or "depends on axioms:" in low
                or "does not depend on any axioms" in low):
            return last
    return last


def _full_corpus():
    # use the FULL corpus, never the pinned easy-15.
    fc = Path("/tmp/rung1/coherent_rung1_corpus.json.fullcache")
    if fc.exists():
        rows = json.loads(fc.read_text())["rows"]
        if len(rows) >= 20:
            return rows
    import shutil
    import coherent_rung1 as cr
    cp = Path(cr.CORPUS)
    bak = cp.with_suffix(".json.easy15bak")
    if cp.exists():
        shutil.move(str(cp), str(bak))
    rows = cr.build_corpus()           # regenerates full 40
    shutil.move(str(cp), str(fc))      # keep full as fullcache
    if bak.exists():
        shutil.move(str(bak), str(cp))  # restore pinned easy-15
    return rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--env-only", action="store_true",
                    help="Only probe the no-de-module env-backed audit.")
    ap.add_argument("--inject-only", action="store_true",
                    help="Only probe the in-context injected collector.")
    ap.add_argument("--limit", type=int, default=20)
    a = ap.parse_args()

    import coherent_rung1 as cr
    from src.ztare.formal.lean_persistent import PersistentLean

    rows = sorted(_full_corpus(),
                  key=lambda r: (r.get("gold_n_steps") or 999))
    # ~20 spanning difficulty (even stride)
    step = max(1, len(rows) // 20)
    sample = rows[::step][:a.limit]
    repl_mode = ("fresh REPL per row"
                 if a.inject_only else f"warming REPL on {cr.SB.name}")
    print(f"[pbp] {len(sample)} rows spanning gold_n_steps "
          f"{[r.get('gold_n_steps') for r in sample]}; {repl_mode} ...",
          flush=True)
    L = None
    if not a.inject_only:
        L = PersistentLean(cr.SB)
        L.start_tactic_proof("theorem _w : True := by sorry", 180)

    def errset(of):
        errs = {str(m.get("data", ""))[:120]
                for m in (of.get("errors") or [])}
        if of.get("ok") is False:
            errs.add(str(of.get("err") or "open_file_not_ok")[:120])
        return errs

    def raw_messages(of):
        raw = "\n".join(str(m.get("data", "")) for m in
                        (of.get("messages") or []))
        if not raw and of.get("ok") is False:
            raw = str(of.get("err") or "")
        return raw

    mechs = {} if (a.env_only or a.inject_only) else {
        "T2": T2, "T3": T3, "T4": T4}
    probe_names = ((["ENV"] if not a.inject_only else [])
                   + list(mechs)
                   + (["RUNCMD"] if not (a.env_only or a.inject_only) else [])
                   + (["INJECT"] if not a.env_only else []))
    agg = {m: {"new_err_rows": 0, "audit_ok": 0, "mod_err": 0}
           for m in probe_names}
    per_row = []
    for row in sample:
        if a.inject_only:
            L = PersistentLean(cr.SB)
            L.start_tactic_proof("theorem _w : True := by sorry", 180)
        rid = row["id"]
        src = Path(row["sorried_file"]).read_text(errors="ignore")
        audit_name = _target_decl_name(src, row["target_name"])
        short = audit_name.split(".")[-1]
        # INJECT is intentionally one-pass: opening the original module
        # first can make the subsequent same-module injected open lose
        # audit messages in the persistent REPL. The eventual gate can
        # classify errors by their source span instead of doing a prior
        # base open. The de-module probes still need a base error set.
        if a.inject_only:
            base_of, base = {"env": None, "errors": []}, set()
        else:
            base_of = L.open_file(row["sorried_file"], 240)
            base = errset(base_of)
            if base_of.get("ok") is False:
                base = set()
        rr = {"id": rid, "target_hint": row["target_name"],
              "audit_name": audit_name, "short": short}
        if not a.inject_only:
            # ENV: no rewritten file. The corpus row still contains the
            # target sorry, so a correct audit must expose sorryAx.
            env_a = _env_axioms(L, base_of.get("env"), audit_name,
                                short, 240)
            raw = env_a["raw"]
            new = env_a["errs"]
            me = bool(MOD_ERR.search(raw)) or any(MOD_ERR.search(e)
                                                  for e in new)
            ok = ("sorryax" in raw.lower())
            if new:
                agg["ENV"]["new_err_rows"] += 1
            if ok:
                agg["ENV"]["audit_ok"] += 1
            if me:
                agg["ENV"]["mod_err"] += 1
            rr["ENV"] = {"new_errs": len(new), "mod_err": me,
                         "sorryAx": ok, "name": env_a["name"],
                         "raw_head": raw[:220]}
        for mname, fn in mechs.items():
            tf = Path(f"/tmp/rung1/_pbp_{mname}.lean")
            tf.write_text(fn(src) + f"\n#print axioms {audit_name}\n")
            of = L.open_file(str(tf), 240)
            tf.unlink(missing_ok=True)
            raw = raw_messages(of)
            new = errset(of) - base
            me = bool(MOD_ERR.search(raw)) or any(
                MOD_ERR.search(str(e)) for e in (of.get("errors") or []))
            ok = ("sorryax" in raw.lower())
            if new:
                agg[mname]["new_err_rows"] += 1
            if ok:
                agg[mname]["audit_ok"] += 1
            if me:
                agg[mname]["mod_err"] += 1
            rr[mname] = {"new_errs": len(new), "mod_err": me,
                         "sorryAx": ok}
        if not a.env_only:
            tf = Path("/tmp/rung1/_pbp_INJECT.lean")
            audit = (
                f"\n#check {audit_name}\n"
                "open Lean Elab Command in\n#eval show "
                "CommandElabM Unit from do\n  let ax ← liftCoreM "
                f"(Lean.collectAxioms ``{audit_name})\n  logInfo m!\"AXIOMS "
                "{ax.qsort Name.lt |>.map MessageData.ofConstName |>.toList}\"\n"
            )
            tf.write_text(_inject_after_target(src, audit_name, audit))
            of = L.open_file(str(tf), 240)
            tf.unlink(missing_ok=True)
            raw = raw_messages(of)
            new = errset(of) - base
            me = bool(MOD_ERR.search(raw)) or any(
                MOD_ERR.search(str(e)) for e in (of.get("errors") or []))
            ok = ("sorryax" in raw.lower())
            if new:
                agg["INJECT"]["new_err_rows"] += 1
            if ok:
                agg["INJECT"]["audit_ok"] += 1
            if me:
                agg["INJECT"]["mod_err"] += 1
            rr["INJECT"] = {"new_errs": len(new), "mod_err": me,
                            "sorryAx": ok, "raw_head": raw[:220],
                            "errors_head": sorted(new)[:3]}
        # RUNCMD best-effort (no de-module)
        if not (a.env_only or a.inject_only):
          try:
            tf = Path("/tmp/rung1/_pbp_RUNCMD.lean")
            tf.write_text(
                src + "\nopen Lean Elab Command in\n#eval show "
                "CommandElabM Unit from do\n  let ax ← liftCoreM "
                f"(Lean.collectAxioms ``{audit_name})\n  logInfo m!\"AXJSON "
                "{ax.toList}\"\n")
            of = L.open_file(str(tf), 240)
            tf.unlink(missing_ok=True)
            raw = raw_messages(of)
            new = errset(of) - base
            me = bool(MOD_ERR.search(raw))
            ok = ("sorryax" in raw.lower())
            if new:
                agg["RUNCMD"]["new_err_rows"] += 1
            if ok:
                agg["RUNCMD"]["audit_ok"] += 1
            if me:
                agg["RUNCMD"]["mod_err"] += 1
            rr["RUNCMD"] = {"new_errs": len(new), "mod_err": me,
                            "audit_ok": ok, "raw_head": raw[:160]}
          except Exception as e:  # noqa: BLE001
            rr["RUNCMD"] = {"exc": str(e)[:120]}
        per_row.append(rr)
        print(f"  {rid[:30]:30s} "
              + " | ".join(f"{m}:e{rr[m].get('new_errs','?')}"
                           f"{'/sx' if rr[m].get('sorryAx') or rr[m].get('audit_ok') else ''}"
                           for m in probe_names),
              flush=True)
        if a.inject_only:
            L.close()
            L = None
    if L is not None:
        L.close()
    Path(OUT).write_text(json.dumps(
        {"n": len(sample), "agg": agg, "per_row": per_row}, indent=1))

    n = len(sample)
    print("\n=== PHASE-B FIX VERDICT ===")
    print(json.dumps(agg, indent=1))
    # pick least-invasive mech with 0 mod_err, new_err_rows==0,
    # audit_ok on all rows.
    order = ["INJECT", "ENV", "T2", "T3", "T4", "RUNCMD"]
    winner = None
    for m in order:
        if m not in agg:
            continue
        a = agg[m]
        if a["mod_err"] == 0 and a["new_err_rows"] == 0 \
                and a["audit_ok"] == n:
            winner = m
            break
    if winner:
        print(f"WINNER: {winner} — 0 new errors across {n} rows, "
              f"sorryAx audit works on all, no module restriction. "
              f"Wire {winner} as the Phase-B transform; then re-run "
              f"gold_proof_control (regression) + scale check.")
    else:
        available = [m for m in order if m in agg]
        best = min(available, key=lambda m: (agg[m]["mod_err"],
                                             agg[m]["new_err_rows"],
                                             n - agg[m]["audit_ok"]))
        print(f"NO clean winner. Least-bad = {best} "
              f"({json.dumps(agg[best])}). Inspect per-row in {OUT}; "
              f"may need a smarter audit (separate importing module).")
    print("detail:", OUT)
    return 0 if winner else 1


if __name__ == "__main__":
    raise SystemExit(main())
