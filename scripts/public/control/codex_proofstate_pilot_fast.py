#!/usr/bin/env python3
"""codex_proofstate_pilot_fast.py — parallel, hard-bounded variant.

Same controlled paired design + leak boundary as codex_proofstate_pilot
(imported, not forked), with three speedups that DO NOT recreate the
heavy-Lean crash:

  1. HARD timeout: codex runs in its own process group
     (start_new_session) and is SIGKILL'd as a group on timeout — fixes
     the leak where subprocess.run(timeout) left node→rust→tool
     grandchildren running 600–700s on a 360s budget.
  2. BOUNDED codex parallelism (--workers, default 3): codex calls are
     I/O-bound (idle-waiting on the model API, CPU≈0) so N concurrent
     codex goals keep load low while cutting wall-clock ~Nx. This is
     the OPPOSITE of the crash, which was parallel *heavy Lean*
     (RAM/CPU-bound, load ~28).
  3. The single warm PersistentLean REPL (verification — the only
     shared, heavy, stateful resource) is serialized behind a lock;
     each parallel row gets its OWN source-isolated iso clone (oleans
     symlinked read-only-shared, only the target .lean per-row) so
     workers cannot clobber each other.

Checkpointed/resumable (same JSONL contract). Machine-safety: workers
capped low; the heavy piece (Lean) stays serial; only the light
I/O-bound piece (codex) parallelizes.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(Path(__file__).parent))
from src.ztare.formal.lean_persistent import PersistentLean  # noqa: E402
from codex_proofstate_pilot import (  # noqa: E402  (reuse, no fork)
    BANNED, BLIND_PROMPT, STATE_PROMPT, _target_block, _verify)

_REPL_LOCK = threading.Lock()
_CKPT_LOCK = threading.Lock()


def _codex_hard(prompt: str, model: str, sandbox: str, cd: str | None,
                timeout: int, last_msg: Path) -> tuple[bool, str]:
    """codex exec in its OWN process group; SIGKILL the whole group on
    timeout (no orphaned grandchildren running past budget)."""
    cmd = ["codex", "exec", "-s", sandbox, "--ephemeral",
           "--skip-git-repo-check", "-m", model, "-o", str(last_msg)]
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
    return True, (last_msg.read_text(errors="ignore")
                  if last_msg.exists() else "")


def _row_iso(base_iso: Path, pool: Path, rid: str) -> Path:
    """Per-row source-isolated lake clone: symlink the heavy read-only
    shared bits (.lake/oleans, lakefile, manifest, toolchain); only the
    target .lean is private so parallel workers never collide."""
    d = pool / re.sub(r"[^A-Za-z0-9_]", "_", rid)
    if d.exists():
        shutil.rmtree(d)
    d.mkdir(parents=True)
    for name in (".lake", "lakefile.toml", "lakefile.lean",
                 "lake-manifest.json", "lean-toolchain"):
        srcp = base_iso / name
        if srcp.exists():
            os.symlink(srcp, d / name)
    return d


def _run_row(L, row, model, t_budget, base_iso, pool, scratch):
    rid = row["id"]
    sf = row["sorried_file"]
    tl = row["target_line"]
    lm = Path(scratch) / f"{re.sub(r'[^A-Za-z0-9_]','_',rid)}.blind.txt"
    # BLIND: read-only sandbox, one-shot, equal wall-clock
    t0 = time.time()
    ok, msg = _codex_hard(BLIND_PROMPT.format(goal=row.get("goal", "")),
                          model, "read-only", None, t_budget, lm)
    if ok:
        with _REPL_LOCK:
            bres = _verify(L, sf, tl, msg, False)
    else:
        bres = {"solved": False, "why": msg}
    b = {"solved": bres["solved"], "why": bres["why"],
         "secs": round(time.time() - t0, 1)}
    # STATEFUL: per-row source-isolated env, agentic w/ live state
    t0 = time.time()
    iso = _row_iso(base_iso, pool, rid)
    fn = "mcb_target.lean"
    shutil.copy(sf, iso / fn)
    ok, _ = _codex_hard(STATE_PROMPT.format(fname=fn), model,
                        "workspace-write", str(iso), t_budget,
                        Path(scratch) /
                        f"{re.sub(r'[^A-Za-z0-9_]','_',rid)}.s.txt")
    if ok:
        with _REPL_LOCK:
            sres = _verify(L, sf, tl, str(iso / fn), True)
    else:
        sres = {"solved": False, "why": "timeout/spawn"}
    if sres["solved"]:
        tgt = (row.get("source", {}) or {}).get(
            "mathlib_name", "").split(".")[-1]
        blk = _target_block(Path(iso / fn).read_text(errors="ignore"),
                            tgt)
        pp = (blk.split(":= by", 1)[1] if ":= by" in blk else
              blk.split(":=", 1)[1] if ":=" in blk else "")
        if tgt and re.search(rf"\b{re.escape(tgt)}\b", pp):
            sres = {"solved": False, "why": "leak:self_name_in_proof"}
    shutil.rmtree(iso, ignore_errors=True)
    s = {"solved": sres["solved"], "why": sres["why"],
         "secs": round(time.time() - t0, 1)}
    return rid, row.get("gold_n_steps"), s, b


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sandbox", required=True)
    ap.add_argument("--corpus", default="/tmp/rung1/mcb_corpus_v2.json")
    ap.add_argument("--n", type=int, default=100)
    ap.add_argument("--model", default="gpt-5.5")
    ap.add_argument("--budget", type=int, default=300)
    ap.add_argument("--workers", type=int, default=3,
                    help="parallel codex goals (I/O-bound; keep ≤4 — "
                         "the heavy Lean stays serial behind a lock)")
    ap.add_argument("--ckpt", default="/tmp/rung1/codex_fast_ckpt.jsonl")
    ap.add_argument("--scratch", default="/tmp/rung1/codex_fast_scratch")
    ap.add_argument("--iso", default="/tmp/rung1/iso_env")
    ap.add_argument("--pool", default="/tmp/rung1/iso_pool")
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
    Path(a.pool).mkdir(parents=True, exist_ok=True)
    base_iso = Path(a.iso)
    if not base_iso.exists():
        print(f"FATAL: source-isolated base env missing: {base_iso}")
        return 2

    done = {}
    ck = Path(a.ckpt)
    if ck.exists():
        for ln in ck.read_text().splitlines():
            try:
                d = json.loads(ln)
                done[d["id"]] = d
            except Exception:
                pass
    todo = [r for r in rows if r["id"] not in done]
    print(f"[fast] {len(todo)} to run ({len(done)} resumed), "
          f"workers={a.workers}, budget={a.budget}s")

    L = PersistentLean(Path(a.sandbox).expanduser().resolve())
    L.start_tactic_proof("theorem _w : True := by sorry", 180)
    fh = ck.open("a")
    with ThreadPoolExecutor(max_workers=a.workers) as ex:
        futs = {ex.submit(_run_row, L, r, a.model, a.budget,
                          base_iso, Path(a.pool), a.scratch): r["id"]
                for r in todo}
        for fut in as_completed(futs):
            rid, gs, s, bl = fut.result()
            rec = {"id": rid, "gold_steps": gs,
                   "stateful_solved": s["solved"], "stateful": s,
                   "blind_solved": bl["solved"], "blind": bl}
            with _CKPT_LOCK:
                fh.write(json.dumps(rec) + "\n")
                fh.flush()
                done[rid] = rec
            print(json.dumps({"id": rid, "S": s["solved"],
                              "B": bl["solved"], "s_why": s["why"],
                              "secs": s["secs"]}))
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
    from math import comb
    Nd = n10 + n01
    p = (sum(comb(Nd, k) for k in range(n10, Nd + 1)) / 2 ** Nd
         if Nd else 1.0)
    summary = {"n": n, "stateful": S, "blind": B, "union": U,
               "union_rate": round(U / n, 3) if n else 0,
               "n10_S_only": n10, "n01_B_only": n01,
               "discordant": Nd, "mcnemar_p_one_sided": p,
               "model": a.model, "workers": a.workers}
    print("\n" + json.dumps(summary, indent=1))
    Path("/tmp/rung1/codex_fast_summary.json").write_text(
        json.dumps({"summary": summary, "rows": R}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
