#!/usr/bin/env python3
"""codex_proofstate_pilot.py — base-rate-gated paired pilot, COLD CODEX.

Cost is the binding constraint: API is unaffordable; codex subscription
is sunk cost ($0/call). A *cold* codex (fresh `--ephemeral` session,
no this-conversation context) is a strong, agentic, and — for these
rows — exactly-as-clean-as-a-fresh-API-call prover (pretraining
caveat unchanged, NOT worsened). Same model both arms ⇒ the
agent-vs-API confound dissolves.

Controlled paired design (cold review epd-db0a29d142bb):
  STATEFUL arm = `codex exec -s workspace-write -C <scratch>`: a fresh
    codex told to replace the `sorry` in the leak-tight sorried file;
    it MAY run lake/Lean and iterate against the live proof state
    (the agentic, state-aware arm — the operator's instinct).
  BLIND arm  = `codex exec -s read-only`: SAME model, given ONLY the
    theorem/goal text, told to emit ONE complete proof body; the
    read-only sandbox PHYSICALLY prevents tool use / state inspection
    / repair (so it is genuinely "blind", not a 3rd arm).
  Both verified identically by the warm PersistentLean REPL (kernel +
  no `sorry`/error at target line). Same per-goal wall-clock budget.
  Serial, checkpointed, one warm REPL → machine-safe (NOT the parallel
  -heavy-Lean pattern that crashed the box).

HONEST residuals (stated, not laundered):
  * codex output is non-deterministic — fine for a COARSE base-rate
    gate, not for the final tight comparison.
  * pretraining contamination (Mathlib in training) unchanged — a
    cold codex has no session memory so it is no worse than a fresh
    API call; a fully clean claim still needs post-cutoff/private
    theorems (separate, later).
  * stateful arm in workspace-write *could* read Mathlib source to
    find the original proof — the proof-term constant audit
    (usedConstants ⊆ allowed; reject target/self) is the real leak
    defense; ENFORCED here as `leak_flag` (a leaked proof is NOT
    counted solved). Pilot reports it explicitly.

Base-rate gate (cold-spec): proceed to N=100 only if union-solve ∈
[20%,80%] and discordance ≥4 — NOT "both arms nonzero" (stateful>0,
blind=0 is a large effect, not a floor).
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))
from src.ztare.formal.lean_persistent import PersistentLean  # noqa: E402

BANNED = ("sorry", "admit", "stop", "native_decide", "import ", "axiom ")
BLIND_PROMPT = (
    "You are a Lean 4 / Mathlib proof expert. Below is a theorem's "
    "hypotheses and goal. Output ONLY one complete Lean 4 tactic proof "
    "body (what would follow `by`). No theorem header, no `by`, no "
    "prose, no code fences, no `sorry`/`admit`/new imports. You have "
    "NO tools and cannot run anything.\n\n## Goal\n{goal}\n")
STATE_PROMPT = (
    "You are a Lean 4 / Mathlib proof expert. The file {fname} in this "
    "directory contains a theorem whose proof is `:= by sorry`. "
    "REPLACE the `sorry` with a correct proof. You MAY run "
    "`lake env lean {fname}` (and other lake/Lean commands) to inspect "
    "the proof state and iterate until it compiles with no errors and "
    "no `sorry`. Do not add new imports, `axiom`, or `native_decide`. "
    "Do not read other Mathlib source files to copy the original "
    "proof — prove it yourself. Edit only {fname}.")


_NEXT_TOP = re.compile(
    r"\n(theorem |lemma |def |abbrev |instance |structure |class |"
    r"inductive |namespace |end |section |@\[|/--|/-|attribute |"
    r"open |variable |noncomputable |private |protected |scoped |"
    r"universe )")


def _target_block(src: str, tgt_name: str) -> str:
    """ONLY the target theorem's own decl block (`theorem/lemma
    <tgt_name> … := …` up to the next top-level decl). Prevents the
    whole-file false positive — the sorried file is the ENTIRE Mathlib
    source; the target name appears in many sibling decls."""
    if not tgt_name:
        return ""
    m = re.search(rf"^(theorem|lemma)\s+{re.escape(tgt_name)}\b",
                  src, re.M)
    if not m:
        return ""
    nxt = _NEXT_TOP.search(src, m.end())
    return src[m.start(): (nxt.start() + 1 if nxt else len(src))]


def _codex(prompt: str, model: str, sandbox: str, cd: str | None,
           timeout: int, last_msg: Path) -> tuple[bool, str]:
    # NON-REGRESSIVE timeout fix (2026-05-18): IDENTICAL command; only
    # adds own process-group + killpg so `timeout` ACTUALLY bounds it.
    # The old subprocess.run(timeout) did NOT kill codex's orphaned
    # node->rust->lake grandchildren; communicate() then blocked the
    # FULL budget (the 360.0s blind hang ≈ half of every row's wall-
    # clock; the 1851s coherent hang). Success path is byte-identical
    # (clean-exit rows unaffected); only the broken unbounded hang is
    # cut. Per memory feedback_parity_control_before_deltas: the one
    # allowed environment fix.
    import os, signal
    cmd = ["codex", "exec", "-s", sandbox, "--ephemeral",
           "--skip-git-repo-check", "-m", model,
           "-o", str(last_msg)]
    if cd:
        cmd += ["-C", cd]
    cmd.append(prompt)
    try:
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE, text=True,
                              start_new_session=True)
    except Exception as e:  # noqa: BLE001
        return False, f"spawn:{e}"
    try:
        p.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(os.getpgid(p.pid), signal.SIGKILL)
        except Exception:
            try:
                p.kill()
            except Exception:
                pass
        try:
            p.communicate(timeout=20)
        except Exception:
            pass
        return False, "timeout"
    except Exception as e:  # noqa: BLE001
        return False, f"run:{e}"
    msg = last_msg.read_text(errors="ignore") if last_msg.exists() else ""
    return True, msg


def _verify(L: PersistentLean, sorried_file: str, target_line: int,
            block_or_filepath: str, is_file: bool) -> dict:
    """Kernel verification via the warm REPL. is_file: stateful arm
    edited the file in place → verify that file. else: blind block →
    substitute for the sorry and verify."""
    if is_file:
        path = block_or_filepath
    else:
        src = Path(sorried_file).read_text(errors="ignore")
        blk = re.sub(r"^```\w*|```$", "", block_or_filepath,
                     flags=re.M).strip()
        if not blk or any(b in blk for b in BANNED):
            return {"solved": False, "why": "bad_block"}
        new = re.sub(r":=\s*by\s*\n\s*sorry",
                     ":= by\n  " + blk.replace("\n", "\n  "),
                     src, count=1)
        tf = Path(sorried_file + ".cand.lean")
        tf.write_text(new)
        path = str(tf)
    of = L.open_file(path, timeout=600)
    if not is_file:
        Path(path).unlink(missing_ok=True)
    if not of["ok"]:
        return {"solved": False, "why": "compile_fail:" + of["err"][:80]}
    errs = of.get("errors", [])
    leftover = [s for s in of["sorries"]
                if s["line"] and abs(s["line"] - target_line) <= 3]
    return {"solved": (not errs) and (not leftover),
            "why": "clean" if (not errs and not leftover)
            else f"errs={len(errs)} sorry={len(leftover)}"}


def run_row(L, row, model, t_budget, scratch):
    rid = row["id"]
    sf = row["sorried_file"]
    tl = row["target_line"]
    lm = Path(scratch) / "last.txt"
    # BLIND: read-only sandbox (physically no tools), one shot
    t0 = time.time()
    # EQUAL wall-clock (cold-spec): blind gets the SAME budget as
    # stateful. It is one-shot+toolless so it usually finishes
    # sooner, but it must be ALLOWED the same time — codex's agent
    # harness needs enough wall-clock just to emit its answer; a
    # shorter blind budget structurally fails it (dry-run bug:
    # blind "timeout" at 120s was harness-latency, not a real miss).
    ok, msg = _codex(BLIND_PROMPT.format(goal=row.get("goal", "")),
                      model, "read-only", None, t_budget, lm)
    bres = (_verify(L, sf, tl, msg, False) if ok
            else {"solved": False, "why": msg})
    b = {"solved": bres["solved"], "why": bres["why"],
         "secs": round(time.time() - t0, 1)}
    # STATEFUL: workspace-write inside the SOURCE-ISOLATED lake env
    # (oleans only, NO Mathlib *.lean source) — codex can run
    # `lake env lean` + see live proof state but CANNOT read the
    # original proof to transcribe it (the cold-review leak boundary,
    # verified feasible). Blind stays read-only (no leak possible).
    t0 = time.time()
    iso = Path(scratch).parent / "iso_env"
    fn = "mcb_target.lean"
    shutil.copy(sf, iso / fn)
    ok, _ = _codex(STATE_PROMPT.format(fname=fn), model,
                    "workspace-write", str(iso), t_budget,
                    Path(scratch) / "slast.txt")
    solved_file = str(iso / fn)
    sres = (_verify(L, sf, tl, solved_file, True) if ok
            else {"solved": False, "why": "timeout/spawn"})
    # leak belt-and-suspenders: reject only if the target's OWN proof
    # block self-references its name. CRITICAL: scope to the target
    # theorem's block alone — the sorried file is the ENTIRE Mathlib
    # source (hundreds of other theorems); a whole-file grep is a
    # guaranteed false positive (the name appears in sibling lemmas).
    if sres["solved"]:
        tgt_name = (row.get("source", {}) or {}).get(
            "mathlib_name", "").split(".")[-1]
        blk = _target_block(Path(solved_file).read_text(errors="ignore"),
                            tgt_name)
        proofpart = (blk.split(":= by", 1)[1] if ":= by" in blk
                     else blk.split(":=", 1)[1] if ":=" in blk else "")
        if tgt_name and re.search(rf"\b{re.escape(tgt_name)}\b",
                                  proofpart):
            sres = {"solved": False, "why": "leak:self_name_in_proof"}
    s = {"solved": sres["solved"], "why": sres["why"],
         "secs": round(time.time() - t0, 1)}
    return s, b


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sandbox", required=True)
    ap.add_argument("--corpus", default="/tmp/rung1/mcb_corpus_v2.json")
    ap.add_argument("--n", type=int, default=30)
    ap.add_argument("--model", default="gpt-5.5")
    ap.add_argument("--budget", type=int, default=360,
                    help="per-goal EQUAL wall-clock cap (s), both arms "
                         "(dry-run: stateful used 230/240 — too tight; "
                         "360 gives headroom without truncating)")
    ap.add_argument("--ckpt", default="/tmp/rung1/codex_pilot_ckpt.jsonl")
    ap.add_argument("--scratch", default="/tmp/rung1/codex_scratch")
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()

    rows = json.load(open(a.corpus))["rows"]
    rows.sort(key=lambda r: r.get("gold_n_steps", 99))
    if len(rows) > a.n:
        st = len(rows) / a.n
        rows = [rows[int(i * st)] for i in range(a.n)]
    if a.limit:
        rows = rows[: a.limit]
    Path(a.scratch).mkdir(parents=True, exist_ok=True)

    done = {}
    ck = Path(a.ckpt)
    if ck.exists():
        for ln in ck.read_text().splitlines():
            try:
                d = json.loads(ln)
                done[d["id"]] = d
            except Exception:
                pass

    L = PersistentLean(Path(a.sandbox).expanduser().resolve())
    L.start_tactic_proof("theorem _w : True := by sorry", 180)
    fh = ck.open("a")
    for row in rows:
        if row["id"] in done:
            continue
        s, b = run_row(L, row, a.model, a.budget, a.scratch)
        rec = {"id": row["id"], "gold_steps": row.get("gold_n_steps"),
               "stateful_solved": s["solved"], "stateful": s,
               "blind_solved": b["solved"], "blind": b}
        fh.write(json.dumps(rec) + "\n")
        fh.flush()
        done[row["id"]] = rec
        print(json.dumps({"id": row["id"], "S": s["solved"],
                          "B": b["solved"], "s_why": s["why"],
                          "b_why": b["why"]}))
    fh.close()
    L.close()

    R = list(done.values())
    n = len(R)
    S = sum(r["stateful_solved"] for r in R)
    B = sum(r["blind_solved"] for r in R)
    U = sum(1 for r in R if r["stateful_solved"] or r["blind_solved"])
    n10 = sum(1 for r in R if r["stateful_solved"]
              and not r["blind_solved"])
    n01 = sum(1 for r in R if r["blind_solved"]
              and not r["stateful_solved"])
    ur = U / n if n else 0
    gate = (0.20 <= ur <= 0.80) and (n10 + n01) >= 4
    summary = {"n": n, "stateful": S, "blind": B, "union": U,
               "union_rate": round(ur, 3), "n10_S_only": n10,
               "n01_B_only": n01, "discordant": n10 + n01,
               "base_rate_gate": "PASS" if gate else "FAIL",
               "model": a.model,
               "interpretation": (
                   "proceed to N=100 paired McNemar test" if gate else
                   "fix design before scaling — NOT a proof-state "
                   "verdict (both-extreme or too-few discordant)")}
    print("\n" + json.dumps(summary, indent=1))
    Path("/tmp/rung1/codex_pilot_summary.json").write_text(
        json.dumps({"summary": summary, "rows": R}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
