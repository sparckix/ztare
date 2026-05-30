#!/usr/bin/env python3
"""build_module_context_benchmark.py — leak-tight benchmark (cold-validated).

ALGORITHM (cold xhigh GPT-5.5 epd-242f7c0e78c5, option 1 — the
regex/preamble-scrape variant is RETIRED, see GP-233 seam §9):

  Per candidate Mathlib theorem T in its pinned source file F:
    1. Copy F, replacing ONLY T's proof body with `:= by sorry`
       in place (entire prefix + T's exact binders/section context /
       attributes preserved; T is NOT re-posed under a fresh name).
    2. Elaborate F' through Lean's REAL frontend via the persistent
       repl File mode (`{"path":F',"allTactics":true}`). Lean runs
       every command before T in its true context, so the returned
       proofState for the injected `sorry` is the genuine pre-command
       state with T NOT yet registered (variant-b in-construction →
       self-reference structurally impossible). No regex context.
    3. Keep iff: F' elaborates with no hard error other than the
       injected sorry; gold body is multi-step (>=min_steps tactic
       nodes); AND a fixed one-step solver suite FAILS from the
       proofState (operational multi-step def + single-lemma /
       trivial-`exact?` leak reject, per the cold review).
  Emits rows carrying the persisted sorried-file path + target line so
  the decisive experiment re-opens the exact leak-tight proof state.

Reuse, not rebuild: vendored leanprover-community/repl File mode +
`sorries[].proofState` (no LeanDojo trace, no hand-rolled frontend).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))
from src.ztare.formal.lean_persistent import PersistentLean  # noqa: E402

NEXT_TOP = re.compile(
    r"\n(theorem |lemma |def |abbrev |instance |structure |class |"
    r"inductive |namespace |end |section |@\[|/--|/-|attribute |"
    r"open |variable |noncomputable |private |protected |scoped |"
    r"universe |macro |elab |syntax |notation |declare_)")
ONE_STEP_SUITE = ["rfl", "assumption", "simp_all", "norm_num", "decide",
                  "exact?", "aesop", "omega", "linarith", "tauto"]


def n_tactic_steps(body: str) -> int:
    if "by" not in body:
        return 1
    toks = len(re.findall(r"\b(intro|apply|exact|refine|rw|simp|have|"
                          r"obtain|rcases|induction|cases|constructor|"
                          r"calc|conv|ext|use|by_contra|specialize|"
                          r"set|suffices|change|gcongr|trans)\b", body))
    seps = len(re.findall(r"<;>|;|\n", body))
    return max(toks, 2 if seps else 1)


def sorry_in_place(src: str, name: str):
    """Return (modified_src, target_line, gold_body) with ONLY
    `<kw> name … := <body>` replaced by `… := by sorry`. None on
    failure (self-correcting: a bad slice simply fails to elaborate
    or is filtered downstream — never a false keep)."""
    m = re.search(rf"^(theorem|lemma)\s+{re.escape(name)}\b", src, re.M)
    if not m:
        return None
    start = m.start()
    nxt = NEXT_TOP.search(src, m.end())
    end = nxt.start() + 1 if nxt else len(src)
    block = src[start:end]
    # find the body-introducing ':=' at top brace/paren depth
    depth = 0
    bi = -1
    i = 0
    while i < len(block) - 1:
        c = block[i]
        if c in "([{⟨":
            depth += 1
        elif c in ")]}⟩":
            depth -= 1
        elif depth == 0 and block[i:i + 2] == ":=":
            bi = i
            break
        i += 1
    if bi < 0:
        return None
    gold_body = block[bi + 2:].strip()
    new_block = block[:bi].rstrip() + " := by\n  sorry\n"
    new_src = src[:start] + new_block + src[end:]
    target_line = src[:start].count("\n") + 1
    return new_src, target_line, gold_body


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sandbox", required=True)
    ap.add_argument("--pairs",
                    default="analytics/public/leanmill/_legacy_lemma_relevance/"
                            "mathlib_pairs.jsonl")
    ap.add_argument("--out", default="/tmp/rung1/mcb_corpus_v2.json")
    ap.add_argument("--files-dir", default="/tmp/rung1/mcb_files")
    ap.add_argument("--target-n", type=int, default=40)
    ap.add_argument("--min-used", type=int, default=4)
    ap.add_argument("--min-steps", type=int, default=3)
    ap.add_argument("--scan-cap", type=int, default=1500)
    ap.add_argument("--checkpoint-jsonl",
                    help="Append one JSON row per accepted candidate for resume/monitoring.")
    ap.add_argument("--partial-out",
                    help="Rewrite a partial corpus JSON after every accepted candidate.")
    ap.add_argument("--progress-json",
                    help="Rewrite lightweight progress JSON during scanning.")
    ap.add_argument("--exclude-corpus",
                    help="Optional corpus whose source mathlib names should be skipped before Lean work.")
    a = ap.parse_args()

    sb = Path(a.sandbox).expanduser().resolve()
    ml = sb / ".lake" / "packages" / "mathlib" / "Mathlib"
    fdir = Path(a.files_dir)
    fdir.mkdir(parents=True, exist_ok=True)
    L = PersistentLean(sb)
    _w = time.time()
    L.start_tactic_proof("theorem _warm_ : True := by sorry", 180)
    print(f"[warmup] {time.time()-_w:.1f}s")

    exclude_names: set[str] = set()
    if a.exclude_corpus:
        try:
            ex_obj = json.loads(Path(a.exclude_corpus).read_text(errors="ignore"))
            ex_rows = ex_obj if isinstance(ex_obj, list) else (
                ex_obj.get("rows") or ex_obj.get("corpus") or ex_obj.get("targets") or []
            )
            exclude_names = {
                str((r.get("source") or {}).get("mathlib_name") or r.get("target_name") or "")
                for r in ex_rows
            }
            exclude_names.discard("")
        except FileNotFoundError:
            exclude_names = set()

    cands = []
    for line in open(a.pairs):
        try:
            r = json.loads(line)
        except Exception:
            continue
        if r.get("target_kind") != "theorem":
            continue
        if len(set(r.get("used_lemmas") or [])) < a.min_used:
            continue
        if str(r.get("target_name") or "") in exclude_names:
            continue
        f = ml / r["target_file"]
        if f.exists():
            cands.append((r["target_name"], r["target_file"], str(f),
                          len(set(r["used_lemmas"]))))
    print(f"[candidates] {len(cands)} multi-step w/ pinned source; "
          f"scanning up to {a.scan_cap}")

    checkpoint = Path(a.checkpoint_jsonl) if a.checkpoint_jsonl else None
    partial_out = Path(a.partial_out) if a.partial_out else None
    progress_json = Path(a.progress_json) if a.progress_json else None
    if checkpoint:
        checkpoint.parent.mkdir(parents=True, exist_ok=True)
    if partial_out:
        partial_out.parent.mkdir(parents=True, exist_ok=True)
    if progress_json:
        progress_json.parent.mkdir(parents=True, exist_ok=True)

    def write_partial(rows_now, scanned_now, kept_now):
        payload = {
            "sandbox": str(sb), "n": len(rows_now),
            "algorithm": "in_place_sorry_repl_file_mode_v3_cold_validated",
            "selection": {"min_used_lemmas": a.min_used,
                          "min_tactic_steps": a.min_steps,
                          "scanned": scanned_now},
            "leak_tightness": ["in_place_T_not_registered_at_sorry",
                               "real_frontend_module_context",
                               "one_step_suite_fails_(single_lemma_reject)"],
            "consumed_by": "stateful_beam_prove.py --file-corpus",
            "partial": True,
            "rows": rows_now,
        }
        if partial_out:
            partial_out.write_text(json.dumps(payload, indent=1, ensure_ascii=False))
        if progress_json:
            progress_json.write_text(json.dumps({
                "state": "running",
                "target_n": a.target_n,
                "kept": kept_now,
                "scanned": scanned_now,
                "scan_cap": a.scan_cap,
                "updated_epoch": time.time(),
                "partial_out": str(partial_out) if partial_out else "",
                "checkpoint_jsonl": str(checkpoint) if checkpoint else "",
            }, indent=2, sort_keys=True) + "\n")

    kept, rows, scanned = 0, [], 0
    write_partial(rows, scanned, kept)
    for name, tfile, fpath, nused in cands:
        if kept >= a.target_n or scanned >= a.scan_cap:
            break
        scanned += 1
        if progress_json and scanned % 5 == 0:
            write_partial(rows, scanned, kept)
        short = name.split(".")[-1]
        try:
            src = Path(fpath).read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        si = sorry_in_place(src, short)
        if not si:
            continue
        new_src, tline, gold_body = si
        if n_tactic_steps(gold_body) < a.min_steps:
            continue
        ff = fdir / f"mcb_{kept}_{short[:30]}.lean"
        ff.write_text(new_src, encoding="utf-8")
        of = L.open_file(str(ff), timeout=600)
        if not of["ok"]:
            continue
        tgt = next((s for s in of["sorries"]
                    if s["line"] and abs(s["line"] - tline) <= 3), None)
        if not tgt or tgt["proofState"] is None:
            continue
        # no hard error except the injected sorry's own declaration
        hard = [m for m in of.get("errors", [])
                if "sorry" not in str(m.get("data", "")).lower()]
        if hard:
            continue
        # operational multi-step + single-lemma leak reject:
        # one-step suite must FAIL from the real proof state
        ps = tgt["proofState"]
        one_shot = False
        for t in ONE_STEP_SUITE:
            st = L.step(ps, t, timeout=20)
            if st.get("closed"):
                one_shot = True
                break
        if one_shot:
            ff.unlink(missing_ok=True)
            continue
        row_payload = {
            "id": f"MCB_{kept:03d}_{short[:32]}",
            "sorried_file": str(ff),
            "target_line": tline,
            "source": {"mathlib_name": name, "file": tfile},
            "gold_n_steps": n_tactic_steps(gold_body),
            "n_used_lemmas": nused,
            "goal": tgt["goal"][:600],
        }
        rows.append(row_payload)
        if checkpoint:
            with checkpoint.open("a") as fh:
                fh.write(json.dumps({
                    "event": "accepted_row",
                    "accepted_at_epoch": time.time(),
                    "kept_index": kept,
                    "scanned": scanned,
                    "row": row_payload,
                }, sort_keys=True, ensure_ascii=False) + "\n")
                fh.flush()
        kept += 1
        write_partial(rows, scanned, kept)
        if kept % 5 == 0:
            print(f"[kept {kept}/{a.target_n}] scanned {scanned} "
                  f"(last {short} {n_tactic_steps(gold_body)}st)")

    L.close()
    out = {
        "sandbox": str(sb), "n": len(rows),
        "algorithm": "in_place_sorry_repl_file_mode_v3_cold_validated",
        "selection": {"min_used_lemmas": a.min_used,
                      "min_tactic_steps": a.min_steps,
                      "scanned": scanned},
        "leak_tightness": ["in_place_T_not_registered_at_sorry",
                           "real_frontend_module_context",
                           "one_step_suite_fails_(single_lemma_reject)"],
        "consumed_by": "stateful_beam_prove.py --file-corpus",
        "rows": rows,
    }
    Path(a.out).write_text(json.dumps(out, indent=1, ensure_ascii=False))
    if progress_json:
        progress_json.write_text(json.dumps({
            "state": "complete",
            "target_n": a.target_n,
            "kept": len(rows),
            "scanned": scanned,
            "scan_cap": a.scan_cap,
            "updated_epoch": time.time(),
            "out": a.out,
            "partial_out": str(partial_out) if partial_out else "",
            "checkpoint_jsonl": str(checkpoint) if checkpoint else "",
        }, indent=2, sort_keys=True) + "\n")
    print(f"\n=> {len(rows)} leak-tight rows / {scanned} scanned "
          f"({100*len(rows)/max(1,scanned):.1f}%) -> {a.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
