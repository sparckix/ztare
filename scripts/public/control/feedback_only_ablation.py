#!/usr/bin/env python3
"""Same-first-prompt residual-feedback ablation.

Meta-Darwin Test 3: the old A/B wedge was confounded because A started
with different seed hints. This harness removes that confound.

Per row:
  B_static   round 1: base prompt
             retry : same base prompt, same tools, no residual feedback
  A_feedback round 1: identical base prompt byte-for-byte
             retry : base prompt plus only the latest governance residual

The first prompt hash must match per row, or the run fails. The harness
uses the same Codex call primitive and authoritative gate as four-arm
wedge, persists every prompt/raw output/governance record, and is
checkpoint-resumable. Self-test is machine-safe: no Lean, no Codex.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import sys
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(Path(__file__).parent))

FROZEN = "/tmp/rung1/four_arm_frozen_corpus.json"
CKPT = "/tmp/rung1/feedback_only_ablation_ckpt.jsonl"
SUMMARY = "/tmp/rung1/feedback_only_ablation_summary.json"
TRACE_ROOT = "/tmp/rung1/feedback_only_ablation_traces"
TOOL_PRELUDE = ("import Mathlib\nimport Hammer\nimport Duper\n"
                "import Auto\nopen scoped ENNReal NNReal BigOperators")
STATIC_SCHEDULE = ["simp_all", "simp", "aesop", "exact?", "apply?",
                   "hammer", "duper", "linarith", "nlinarith",
                   "ring", "norm_num", "omega"]
ARMS = ("B_static", "A_feedback")
_REPL_LOCK = threading.Lock()


def die(msg: str) -> None:
    print(f"FAIL-LOUD: {msg}", file=sys.stderr)
    raise SystemExit(2)


def _safe_id(s: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]", "_", str(s))


def _sha(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()


def _write_text(trace_dir: Path | None, name: str, text: str) -> None:
    if trace_dir is None:
        return
    trace_dir.mkdir(parents=True, exist_ok=True)
    (trace_dir / name).write_text(text)


def _write_json(trace_dir: Path | None, name: str, data: dict[str, Any]) -> None:
    _write_text(trace_dir, name, json.dumps(data, indent=1, sort_keys=True))


def base_prompt(_PP: Any, fn: str) -> str:
    sched = ", ".join(STATIC_SCHEDULE)
    return (_PP.STATE_PROMPT.format(fname=fn)
            + f" Use this fixed strong tool order when useful: {sched}.")


def residual_feedback(last: dict[str, Any]) -> str:
    verdict = last.get("verdict") or "open"
    reason = last.get("reason") or last.get("verified_by") or "unknown"
    deps = last.get("axioms_deps") or []
    dep_txt = (" Audit details: " + "; ".join(str(x)[:180] for x in deps[:3])
               if deps else "")
    return (
        "\n\nGovernance residual from the prior failed attempt: "
        f"verdict={verdict}; reason={reason}.{dep_txt} "
        "Do not repeat the same proof claim. Use the live Lean errors to "
        "choose a different tactic/decomposition. If the target is still "
        "blocked, emit a precise missing lemma statement instead of prose."
    )


def _persist_lean(SB: Path):
    from src.ztare.formal.lean_persistent import PersistentLean
    L = PersistentLean(SB, prelude=TOOL_PRELUDE, import_timeout=600)
    L.start_tactic_proof("theorem _w : True := by sorry", 180)
    return L


def _load_rows(limit: int, row_id: str | None) -> list[dict[str, Any]]:
    if not Path(FROZEN).exists():
        die(f"{FROZEN} missing; run/fetch the frozen four-arm corpus first.")
    rows = json.load(open(FROZEN))["rows"]
    if row_id:
        rows = [r for r in rows if r["id"] == row_id]
        if not rows:
            die(f"row id not found in frozen corpus: {row_id}")
    if limit:
        rows = rows[:limit]
    if not rows:
        die("no rows selected")
    return rows


def attempt_arm(L: Any, _PP: Any, _PF: Any, _AX: Any, row: dict[str, Any],
                arm: str, model: str, per_call_budget_s: float, max_rounds: int,
                trace_base: Path | None = None) -> dict[str, Any]:
    t0 = time.time()
    rid = f"{row['id']}_{arm}"
    trace_dir = (trace_base / _safe_id(row["id"]) / arm
                 if trace_base is not None else None)
    iso = _PF._row_iso(Path("/tmp/rung1/iso_env"),
                       Path("/tmp/rung1/feedback_only_pool"), rid)
    fn = "mcb_target.lean"
    shutil.copy(row["sorried_file"], iso / fn)
    bp = base_prompt(_PP, fn)
    last: dict[str, Any] = {"verdict": "open", "verified_by": "init"}
    first_verdict = None
    first_prompt_hash = _sha(bp)
    prompt_hashes: list[str] = []
    calls = 0
    saw_axiom_smuggle = False
    for round_idx in range(max_rounds):
        if arm == "A_feedback" and round_idx > 0:
            prompt = bp + residual_feedback(last)
        else:
            prompt = bp
        prompt_hashes.append(_sha(prompt))
        round_name = f"round_{round_idx + 1:02d}"
        _write_text(trace_dir, f"{round_name}.prompt.txt", prompt)
        call_t0 = time.time()
        calls += 1
        ok, msg = _PF._codex_hard(prompt, model, "workspace-write",
                                  str(iso), max(1, int(per_call_budget_s)),
                                  iso / "lastmsg.txt")
        _write_text(trace_dir, f"{round_name}.raw_model_output.txt", msg)
        if (iso / fn).exists():
            _write_text(trace_dir, f"{round_name}.{fn}",
                        (iso / fn).read_text(errors="ignore"))
        _write_json(trace_dir, f"{round_name}.call.json", {
            "row_id": row["id"],
            "arm": arm,
            "round": round_idx + 1,
            "model": model,
            "sandbox": "workspace-write",
            "cwd": str(iso),
            "timeout_s": max(1, int(per_call_budget_s)),
            "ok": ok,
            "codex_status": "ok" if ok else msg,
            "elapsed_s": round(time.time() - call_t0, 3),
            "prompt_sha256": prompt_hashes[-1],
        })
        if not ok:
            last = {"verdict": "open", "verified_by": "codex_no_output",
                    "reason": msg}
        else:
            with _REPL_LOCK:
                last = _AX.govern(L, (iso / fn).read_text(errors="ignore"),
                                  row["target_line"], row["target_name"],
                                  160, persist=True)
            _write_json(trace_dir, f"{round_name}.govern.json", last)
        if first_verdict is None:
            first_verdict = last.get("verdict")
        if last.get("verdict") == "axiom_smuggled":
            saw_axiom_smuggle = True
        if last.get("verdict") == "closure":
            break
    shutil.rmtree(iso, ignore_errors=True)
    verdict = last.get("verdict", "open")
    return {
        "verdict": verdict,
        "ratified": 1 if verdict == "closure" else 0,
        "first_verdict": first_verdict or "open",
        "recovered_after_first_failure": int(first_verdict != "closure"
                                             and verdict == "closure"),
        "axiom_smuggled_seen": int(saw_axiom_smuggle),
        "wrong_target_kind": 0,
        "manual_edits": 0,
        "reason": last.get("reason"),
        "verified_by": last.get("verified_by"),
        "trace_dir": str(trace_dir) if trace_dir is not None else None,
        "calls": calls,
        "secs": round(time.time() - t0, 1),
        "first_prompt_sha256": first_prompt_hash,
        "prompt_sha256": prompt_hashes,
    }


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    n = len(rows)

    def count(arm: str, key: str) -> int:
        return sum(int(r[arm].get(key, 0)) for r in rows)

    def rate(arm: str, key: str) -> float:
        return round(count(arm, key) / n, 3) if n else 0.0

    first_prompt_mismatch = [
        r["id"] for r in rows
        if r["B_static"]["first_prompt_sha256"]
        != r["A_feedback"]["first_prompt_sha256"]
    ]
    out = {
        "n": n,
        "ratified_rate": {a: rate(a, "ratified") for a in ARMS},
        "recovered_after_first_failure": {
            a: count(a, "recovered_after_first_failure") for a in ARMS
        },
        "A_minus_B_recovery": (
            count("A_feedback", "recovered_after_first_failure")
            - count("B_static", "recovered_after_first_failure")
        ),
        "A_minus_B_ratified": round(
            rate("A_feedback", "ratified") - rate("B_static", "ratified"), 3),
        "safety": {
            "A_axiom_smuggled_seen": count("A_feedback", "axiom_smuggled_seen"),
            "B_axiom_smuggled_seen": count("B_static", "axiom_smuggled_seen"),
            "A_wrong_target_kind": count("A_feedback", "wrong_target_kind"),
            "A_manual_edits": count("A_feedback", "manual_edits"),
        },
        "first_prompt_mismatch": first_prompt_mismatch,
        "VERDICT": (
            "INVALID: first prompts differed" if first_prompt_mismatch else
            "A_feedback_positive_smoke" if count(
                "A_feedback", "recovered_after_first_failure")
            > count("B_static", "recovered_after_first_failure") else
            "NO_FEEDBACK_RECOVERY_SMOKE"
        ),
    }
    Path(SUMMARY).write_text(json.dumps(out, indent=1, sort_keys=True) + "\n")
    return out


def run(limit: int, row_id: str | None, model: str, budget: float,
        max_rounds: int, workers: int) -> dict[str, Any]:
    import authoritative_axioms as _AX
    import codex_proofstate_pilot as _PP
    import codex_proofstate_pilot_fast as _PF
    import coherent_rung1 as cr

    os.environ["ZTARE_GATE_RUN_ID"] = "feedback_only_ablation"
    os.environ["ZTARE_GATE_SOURCE"] = "feedback_only_ablation"
    rows = _load_rows(limit, row_id)
    row_ids = {r["id"] for r in rows}
    trace_root = Path(TRACE_ROOT)
    trace_root.mkdir(parents=True, exist_ok=True)
    done: dict[str, dict[str, Any]] = {}
    ckpt = Path(CKPT)
    if ckpt.exists():
        for line in ckpt.read_text().splitlines():
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            if rec.get("id") in row_ids and all(a in rec for a in ARMS):
                done[rec["id"]] = rec
    todo = [r for r in rows if r["id"] not in done]
    L = _persist_lean(cr.SB)
    fh = ckpt.open("a")

    def one(row: dict[str, Any]) -> dict[str, Any]:
        rec = {"id": row["id"], "gold": row.get("gold_n_steps")}
        for arm in ARMS:
            rec[arm] = attempt_arm(L, _PP, _PF, _AX, row, arm, model,
                                   budget, max_rounds, trace_root)
        if (rec["B_static"]["first_prompt_sha256"]
                != rec["A_feedback"]["first_prompt_sha256"]):
            die(f"first prompt mismatch on {row['id']}")
        return rec

    try:
        with ThreadPoolExecutor(max_workers=max(1, workers)) as ex:
            futs = {ex.submit(one, r): r["id"] for r in todo}
            for fut in as_completed(futs):
                rec = fut.result()
                fh.write(json.dumps(rec) + "\n")
                fh.flush()
                done[rec["id"]] = rec
                print(json.dumps({
                    "id": rec["id"],
                    "B_static": rec["B_static"]["verdict"],
                    "A_feedback": rec["A_feedback"]["verdict"],
                    "B_recovered": rec["B_static"]["recovered_after_first_failure"],
                    "A_recovered": rec["A_feedback"]["recovered_after_first_failure"],
                }))
    finally:
        fh.close()
        L.close()
    out = summarize(list(done.values()))
    print(json.dumps(out, indent=1, sort_keys=True))
    return out


def self_test() -> int:
    import codex_proofstate_pilot as _PP
    import codex_proofstate_pilot_fast as _PF

    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        src = root / "s.lean"
        src.write_text("theorem t : True := by\n  sorry\n")
        row = {"id": "r", "sorried_file": str(src),
               "target_line": 1, "target_name": "t", "gold_n_steps": 5}
        calls: list[dict[str, Any]] = []

        old_codex = _PF._codex_hard
        old_iso = _PF._row_iso

        def fake_iso(base: Path, pool: Path, rid: str) -> Path:
            d = root / _safe_id(rid)
            if d.exists():
                shutil.rmtree(d)
            d.mkdir(parents=True)
            return d

        def fake_codex(prompt: str, model: str, sandbox: str,
                       cd: str | None, timeout: int,
                       last_msg: Path) -> tuple[bool, str]:
            calls.append({"cd": cd, "prompt": prompt})
            marker = "\n-- FEEDBACK_MARK\n" if "Governance residual" in prompt else "\n"
            Path(cd or root, "mcb_target.lean").write_text(
                "theorem t : True := by\n  trivial\n" + marker)
            last_msg.write_text("ok")
            return True, "ok"

        class FakeAX:
            @classmethod
            def govern(cls, _L, src_txt, _line, _name, _timeout, persist=True):
                if "FEEDBACK_MARK" in src_txt:
                    return {"verdict": "closure", "reason": "mock_close",
                            "verified_by": "mock"}
                return ({"verdict": "open", "reason": "mock_failure",
                         "verified_by": "mock"})

        try:
            _PF._codex_hard = fake_codex
            _PF._row_iso = fake_iso
            b = attempt_arm(object(), _PP, _PF, FakeAX, row, "B_static",
                            "m", 30, 2, root / "tr")
            a = attempt_arm(object(), _PP, _PF, FakeAX, row, "A_feedback",
                            "m", 30, 2, root / "tr")
        finally:
            _PF._codex_hard = old_codex
            _PF._row_iso = old_iso

        assert b["first_prompt_sha256"] == a["first_prompt_sha256"]
        b_prompts = [c["prompt"] for c in calls[:2]]
        a_prompts = [c["prompt"] for c in calls[2:]]
        assert b_prompts[0] == a_prompts[0], "round-1 prompts must match"
        assert b_prompts[1] == b_prompts[0], "B retry must stay static"
        assert a_prompts[1].startswith(a_prompts[0])
        assert "Governance residual" in a_prompts[1]
        rec = {"id": "r", "B_static": b, "A_feedback": a}
        s = summarize([rec])
        assert not s["first_prompt_mismatch"]
    print("feedback_only_ablation self-test PASS")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--row-id")
    ap.add_argument("--model", default="gpt-5.5")
    ap.add_argument("--budget", type=float, default=180.0,
                    help="Per-Codex-call timeout seconds, not total arm budget.")
    ap.add_argument("--max-rounds", type=int, default=2)
    ap.add_argument("--workers", type=int, default=1,
                    help="Parallel rows. Keep 1 for smoke; Lean gate is serialized.")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return self_test()
    run(args.limit, args.row_id, args.model, args.budget,
        args.max_rounds, args.workers)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
