"""First-class capture of the LEAF's chain-of-thought (CoT) — the STaR / rejection-sampling training signal
(DeepSeek-Prover-V2 pattern) the harness previously DISCARDED. The dispatch `out` (codex/claude stdout, which
carries the reasoning) was parsed for the `-- GAP:` line, then thrown away; the full reasoning survived only in
codex's ephemeral, unlinked session rollouts (`~/.codex/sessions/…/rollout-*.jsonl`). This module persists ONE
append-only JSONL record per leaf attempt, linked to the campaign target, so the reasoning is (a) durable, (b)
retrievable for RCA — reading it corrected a whole-session misdiagnosis (2026-07-03: "underpowered model" → the
real cause, compile-latency starvation), and (c) trainable.

DESIGN (the world-class way, 2026-07-03):
  • JSONL, not a DB — append-only, git/merge-friendly (mergeable via `state_convergence`), streams into
    `export_training_corpus`. A DB adds ops overhead and is not the field norm for prover corpora.
  • Capture is CHEAP at dispatch; `outcome`/`proof` are JOINED at export by (target, run_tag) against the
    closures/ledger — the capture-raw-label-later ETL (we don't know the kernel verdict yet at dispatch).
  • BOTH full CoT AND the structured `gap` (the `-- GAP:` "why-not" label) are kept — full CoT is the primary
    SFT signal for VERIFIED proofs (STaR); `gap` is the structured failure label for curriculum / why-not
    negatives. Not either/or.
  • `session_id` links back to the provider's own structured rollout for the richest trace.

Best-effort telemetry: a write here must NEVER raise into the solve (a training-corpus write cannot break a
proof run)."""
from __future__ import annotations

import json
import os
import time
from pathlib import Path


def _repo_root() -> Path:
    p = Path(__file__).resolve()
    for a in p.parents:
        if (a / "analytics" / "public" / "queries").is_dir():
            return a
    return p.parents[4]


LEDGER = _repo_root() / "analytics" / "public" / "queries" / "cot_traces.jsonl"


def extract_gap(cot: str) -> str:
    """The leaf's structured honest-gap (`-- GAP: …`, the 'why-not' label) — kept ALONGSIDE the full CoT."""
    for line in (cot or "").splitlines():
        s = line.strip()
        if s.startswith("-- GAP:"):
            return s[len("-- GAP:"):].strip()[:400]
    return ""


def record_cot(*, target: str, runtime: str, cot: str, session_id: str = "", mode: str = "",
               goal: str = "", rc: "int | None" = None, ledger: "Path | None" = None,
               probe_tag: str = "", max_cot: int = 24000) -> None:
    """Append ONE leaf-attempt CoT trace. `target` is the clean theorem name; the CAMPAIGN is `run_tag` (read
    from the run env, the ONE source); `probe_tag` keeps the full `{target}__{probe}` for probe-level joins.
    `outcome` is left blank and JOINED at export. Never raises (telemetry)."""
    if os.environ.get("ZTARE_LEANMILL_COT_CAPTURE", "1") == "0":
        return
    led = ledger or LEDGER
    try:
        led.parent.mkdir(parents=True, exist_ok=True)
        rec = {
            "ts": time.time(),
            "run_tag": os.environ.get("ZTARE_SOLVER_RUN_TAG", ""),
            "target": target,
            "probe_tag": probe_tag,
            "goal": (goal or "")[:600],
            "mode": mode,
            "runtime": runtime,
            "model": (os.environ.get("ZTARE_CODEX_AGENT_MODEL") if runtime == "codex"
                      else os.environ.get("ZTARE_CLAUDE_AGENT_MODEL")) or "account-default",
            "effort": (os.environ.get("ZTARE_CODEX_EFFORT") if runtime == "codex"
                       else os.environ.get("ZTARE_CLAUDE_EFFORT")) or "",
            "session_id": session_id,
            "rc": rc,
            "gap": extract_gap(cot),
            "cot": (cot or "")[:max_cot],
            "outcome": "",   # JOINED at export by (target, run_tag) vs closures/ledger — capture-raw-label-later
        }
        with led.open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except Exception:  # noqa: BLE001 — a training-corpus write must never break the solve
        pass


def _selftest() -> int:
    import tempfile
    fails = []

    def ok(n, c):
        print(f"  [{'PASS' if c else 'FAIL'}] {n}")
        if not c:
            fails.append(n)

    ok("extract_gap pulls the '-- GAP:' why-not label",
       extract_gap("theorem t := by\n  -- GAP: need List.filter_nodup\n  sorry") == "need List.filter_nodup")
    ok("extract_gap empty when no gap line", extract_gap("theorem t := by exact rfl") == "")
    _led = Path(tempfile.mkdtemp(prefix="cot_")) / "cot.jsonl"
    os.environ["ZTARE_SOLVER_RUN_TAG"] = "ut_run"
    record_cot(target="iso_lemma1__probe", runtime="codex", cot="reasoning…\n  -- GAP: X\nsorry",
               session_id="s1", mode="direct", goal="P", rc=0, ledger=_led)
    _rows = [json.loads(x) for x in _led.read_text().splitlines()]
    ok("one trace appended", len(_rows) == 1)
    r = _rows[0]
    ok("trace links target + run_tag (join key for outcome labeling)",
       r["target"] == "iso_lemma1__probe" and r["run_tag"] == "ut_run")
    ok("trace keeps BOTH full CoT and the structured gap",
       "reasoning" in r["cot"] and r["gap"] == "X" and r["outcome"] == "")
    ok("=0 disables capture (A/B / opt-out)",
       (os.environ.__setitem__("ZTARE_LEANMILL_COT_CAPTURE", "0"),
        record_cot(target="t2", runtime="codex", cot="x", ledger=_led),
        len(_led.read_text().splitlines()) == 1)[-1])
    os.environ.pop("ZTARE_LEANMILL_COT_CAPTURE", None)
    print("SELFTEST", "PASSED" if not fails else f"FAILED: {fails}")
    return 0 if not fails else 1


if __name__ == "__main__":
    import sys
    raise SystemExit(_selftest() if "--selftest" in sys.argv else 0)
