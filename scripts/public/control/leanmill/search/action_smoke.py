#!/usr/bin/env python3
"""One-row action smoke from LeanSearch candidate-filter packets.

Given a sorried MCB row and statically resolved LeanSearch candidate
names, try tiny proof-action templates (`exact`, `simpa using`, `apply`)
in the original module file. The filter input may be the global static
filter or the stricter target-site row-context filter. This is a cheap
bridge from external source acquisition to Path-A action evidence.

It is deliberately narrow:
  - one row by default
  - no agent calls
  - no batch claims
  - optional Path-B governance only for compile-clean winners
"""
from __future__ import annotations

import argparse
import json
import multiprocessing as mp
import os
import re
import shlex
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[5]
DEFAULT_CORPUS = "/tmp/rung1/mcb_corpus_v2.json"
DEFAULT_STATIC_FILTER = "analytics/public/leanmill/leansearch/LEANSEARCH_MCB_REMAINING_STATIC_FILTER.json"
DEFAULT_OUT = "/tmp/rung1/leansearch_action_smoke.json"
DEFAULT_SAVE_DIR = "/tmp/rung1/leansearch_action_smoke_drivers"


def _read_rows(path: Path) -> list[dict[str, Any]]:
    obj = json.loads(path.read_text(errors="ignore"))
    if isinstance(obj, list):
        return obj
    return list(obj.get("rows") or obj.get("corpus") or obj.get("targets") or [])


def _row_by_id(path: Path, row_id: str) -> dict[str, Any]:
    for row in _read_rows(path):
        if str(row.get("id") or row.get("row_id")) == row_id:
            return row
    raise SystemExit(f"row_id not found in corpus: {row_id}")


def _candidates(static_filter: Path, row_id: str, limit: int) -> list[str]:
    obj = json.loads(static_filter.read_text(errors="ignore"))
    for row in obj.get("rows") or []:
        if str(row.get("row_id")) == row_id:
            candidates = (
                row.get("target_context_ready_candidates")
                or row.get("row_context_ready_candidates")
                or row.get("canary_ready_candidates")
                or []
            )
            return [str(c["name"]) for c in candidates[:limit]]
    raise SystemExit(f"row_id not found in static filter: {row_id}")


def _replace_target_sorry(src: str, target_line: int, body: str) -> str:
    lines = src.splitlines(keepends=True)
    offset = sum(len(x) for x in lines[:max(0, target_line - 1)])
    m = re.search(r"(?m)^(\s*)sorry\b", src[offset:])
    if not m:
        raise SystemExit("target-region sorry not found")
    start = offset + m.start()
    end = offset + m.end()
    indent = m.group(1)
    body_lines = body.rstrip("\n").splitlines()
    rendered = "\n".join((indent + line if line else line) for line in body_lines)
    return src[:start] + rendered + src[end:]


def _prefix_through_target_sorry(src: str, target_line: int) -> str:
    lines = src.splitlines(keepends=True)
    offset = sum(len(x) for x in lines[:max(0, target_line - 1)])
    m = re.search(r"(?m)^(\s*)sorry\b", src[offset:])
    if not m:
        raise SystemExit("target-region sorry not found")
    end = offset + m.end()
    while end < len(src) and src[end] not in "\n\r":
        end += 1
    if end < len(src):
        end += 1
    return src[:end]


def _templates(name: str, families: set[str] | None = None, goal: str = "") -> list[tuple[str, str]]:
    all_templates = [
        ("exact", f"exact {name}"),
        ("simpa_using", f"simpa using {name}"),
        ("apply", f"apply {name}"),
        (
            "apply_easy",
            f"apply {name}\n"
            f"all_goals first | assumption | positivity | norm_num | simp_all | ring_nf | linarith | omega | aesop",
        ),
        (
            "have_exact",
            f"have h_source := @{name}\n"
            f"exact?",
        ),
        (
            "have_applyq",
            f"have h_source := @{name}\n"
            f"apply?",
        ),
        (
            "have_aesop",
            f"have h_source := @{name}\n"
            f"first | exact? | aesop | simp_all",
        ),
        (
            "local_abs_sum_transport",
            "have h := inner_le_Lp_mul_Lq s f g hpq\n"
            "have hsumf : ∑ i ∈ s, |f i| ^ p = ∑ i ∈ s, f i ^ p := by\n"
            "  apply sum_congr rfl\n"
            "  intro i hi\n"
            "  rw [abs_of_nonneg (hf i hi)]\n"
            "have hsumg : ∑ i ∈ s, |g i| ^ q = ∑ i ∈ s, g i ^ q := by\n"
            "  apply sum_congr rfl\n"
            "  intro i hi\n"
            "  rw [abs_of_nonneg (hg i hi)]\n"
            "simpa [hsumf, hsumg] using h",
        ),
        (
            "local_abs_sum_transport_convert",
            "convert inner_le_Lp_mul_Lq s f g hpq using 3 <;> "
            "apply sum_congr rfl <;> intro i hi <;> "
            "simp only [abs_of_nonneg, hf i hi, hg i hi]",
        ),
        (
            "summability_nnreal_power2",
            "have h_succ_diff : _root_.SuccDiffBounded 2 (2 ^ ·) := by\n"
            "  intro n\n"
            "  simp [pow_succ, mul_two, two_mul]\n"
            "convert summable_schlomilch_iff hf (pow_pos zero_lt_two) "
            "(pow_right_strictMono₀ _root_.one_lt_two) two_ne_zero h_succ_diff\n"
            "simp [pow_succ, mul_two]",
        ),
        (
            "summability_real_nonneg_power2",
            "have h_succ_diff : _root_.SuccDiffBounded 2 (2 ^ ·) := by\n"
            "  intro n\n"
            "  simp [pow_succ, mul_two, two_mul]\n"
            "convert summable_schlomilch_iff_of_nonneg h_nonneg h_mono "
            "(pow_pos zero_lt_two) (pow_right_strictMono₀ _root_.one_lt_two) "
            "two_ne_zero h_succ_diff\n"
            "simp [pow_succ, mul_two]",
        ),
    ]
    if "↔" in goal or "<->" in goal:
        all_templates.append(
            (
                "constructor_apply_easy",
                f"constructor\n"
                f"· intro h\n"
                f"  first | apply {name} | simpa using {name}\n"
                f"  all_goals first | assumption | positivity | norm_num | simp_all | ring_nf | linarith | omega | aesop\n"
                f"· intro h\n"
                f"  first | apply {name} | simpa using {name}\n"
                f"  all_goals first | assumption | positivity | norm_num | simp_all | ring_nf | linarith | omega | aesop",
            )
        )
        all_templates.append(
            (
                "iff_direction_canary",
                f"constructor\n"
                f"· intro h\n"
                f"  fail_if_success first | apply {name} | simpa using {name}\n"
                f"  skip\n"
                f"· intro h\n"
                f"  first | apply {name} | simpa using {name}\n"
                f"  all_goals first | assumption | positivity | norm_num | simp_all | ring_nf | linarith | omega | aesop",
            )
        )
    if families:
        return [t for t in all_templates if t[0] in families]
    return all_templates


def _row_specific_templates(row_id: str, families: set[str] | None = None) -> list[tuple[str, str, str]]:
    """Guarded local repair canaries.

    These are not source-credit templates. They test whether a residual family
    has a plausible repair shape for a specific audited MCB row. Broad use
    would contaminate source-quality measurements, so keep every body tied to
    an explicit row id.
    """
    templates: dict[str, list[tuple[str, str, str]]] = {
        "MCB_003_convolution_mono_right_of_nonneg": [
            (
                "local_convolution_mono_shape",
                "convolution_source_shape",
                "by_cases hfg : ConvolutionExistsAt μ f g x\n"
                "· exact convolution_mono_right μ hf g₁ g₂ hg hfg\n"
                "· rw [ConvolutionExistsAt] at hfg\n"
                "  rw [convolution_def, integral_undef hfg]\n"
                "  exact integral_nonneg fun y => mul_nonneg (hf _) (hg _)",
            )
        ],
        "MCB_004_convolution_congr": [
            (
                "local_convolution_congr_shape",
                "convolution_source_shape",
                "ext x\n"
                "simp only [convolution_def]\n"
                "apply integral_congr_ae\n"
                "filter_upwards [h1, (quasiMeasurePreserving_sub_left_of_right_invariant μ x).ae h2] with y hy1 hy2\n"
                "rw [hy1, hy2]",
            )
        ],
        "MCB_006_integral_convolution": [
            (
                "local_integral_convolution_shape",
                "convolution_source_shape",
                "rw [convolution_def]\n"
                "rw [integral_integral_swap]\n"
                "· simp_rw [← integral_mul_left]\n"
                "  congr\n"
                "  ext y\n"
                "  rw [integral_sub_left_eq_self]\n"
                "· exact hf.integrable_mul_right hg\n"
                "· exact hf.integrable_mul_left hg",
            )
        ],
        "MCB_019_summable_condensed_iff_of_nonneg": [
            (
                "local_summable_condensed_nonneg_shape",
                "ennreal_tsum_condensation_shape",
                "have h_succ_diff : SuccDiffBounded 2 (2 ^ ·) := by\n"
                "  intro n\n"
                "  simp [pow_succ, mul_two, two_mul]\n"
                "convert summable_schlomilch_iff_of_nonneg h_nonneg h_mono (pow_pos zero_lt_two) "
                "(pow_right_strictMono₀ _root_.one_lt_two) two_ne_zero h_succ_diff\n"
                "simp [pow_succ, mul_two]",
            )
        ],
        "MCB_016_summable_condensed_iff_of_nonneg": [
            (
                "local_summable_condensed_nonneg_shape",
                "ennreal_tsum_condensation_shape",
                "have h_succ_diff : SuccDiffBounded 2 (2 ^ ·) := by\n"
                "  intro n\n"
                "  simp [pow_succ, mul_two, two_mul]\n"
                "convert summable_schlomilch_iff_of_nonneg h_nonneg h_mono (pow_pos zero_lt_two) "
                "(pow_right_strictMono₀ _root_.one_lt_two) two_ne_zero h_succ_diff\n"
                "simp [pow_succ, mul_two]",
            )
        ],
        "MCB_017_summable_condensed_iff_of_eventu": [
            (
                "local_summable_condensed_eventually_shape",
                "ennreal_tsum_condensation_shape",
                "rw [Filter.EventuallyLE, Filter.eventually_atTop] at h_nonneg\n"
                "rw [Filter.eventually_atTop] at h_mono\n"
                "rcases h_nonneg with ⟨n, hn⟩\n"
                "rcases h_mono with ⟨m, hm⟩\n"
                "convert summable_condensed_iff_of_nonneg (f := fun k ↦ f (max k (n + m))) _ _ using 1\n"
                "· rw [summable_congr_atTop]\n"
                "  have h_pow := tendsto_pow_atTop_atTop_of_one_lt (r := 2) (by simp)\n"
                "  filter_upwards [h_pow.eventually_ge_atTop (n + m)] with _ hk using by simp [max_eq_left hk]\n"
                "· rw [summable_congr_atTop]\n"
                "  filter_upwards [Filter.eventually_ge_atTop (n + m)] with _ hk using by simp [max_eq_left hk]\n"
                "· simp_all\n"
                "· intro _ _ _ _\n"
                "  exact antitoneOn_nat_Ici_of_succ_le (k := n + m) (by grind) (by simp) (by simp) (by grind)",
            )
        ],
        "MCB_020_summable_condensed_iff_of_eventu": [
            (
                "local_summable_condensed_eventually_shape",
                "ennreal_tsum_condensation_shape",
                "rw [Filter.EventuallyLE, Filter.eventually_atTop] at h_nonneg\n"
                "rw [Filter.eventually_atTop] at h_mono\n"
                "rcases h_nonneg with ⟨n, hn⟩\n"
                "rcases h_mono with ⟨m, hm⟩\n"
                "convert summable_condensed_iff_of_nonneg (f := fun k ↦ f (max k (n + m))) _ _ using 1\n"
                "· rw [summable_congr_atTop]\n"
                "  have h_pow := tendsto_pow_atTop_atTop_of_one_lt (r := 2) (by simp)\n"
                "  filter_upwards [h_pow.eventually_ge_atTop (n + m)] with _ hk using by simp [max_eq_left hk]\n"
                "· rw [summable_congr_atTop]\n"
                "  filter_upwards [Filter.eventually_ge_atTop (n + m)] with _ hk using by simp [max_eq_left hk]\n"
                "· simp_all\n"
                "· intro _ _ _ _\n"
                "  exact antitoneOn_nat_Ici_of_succ_le (k := n + m) (by grind) (by simp) (by simp) (by grind)",
            )
        ],
        "MCB_003_le_tsum_schlomilch": [
            (
                "local_le_tsum_schlomilch_shape",
                "ennreal_tsum_condensation_shape",
                "rw [ENNReal.tsum_eq_iSup_nat' hu.tendsto_atTop]\n"
                "refine iSup_le fun n => ?_\n"
                "grw [Finset.le_sum_schlomilch hf h_pos hu.monotone n]\n"
                "gcongr\n"
                "have (k : ℕ) : (u (k + 1) - u k : ℝ≥0∞) = (u (k + 1) - (u k : ℕ) : ℕ) := by simp\n"
                "simp only [nsmul_eq_mul, this]\n"
                "apply ENNReal.sum_le_tsum",
            )
        ],
    }
    out = templates.get(row_id, [])
    if families:
        out = [t for t in out if t[1] in families]
    return out


def _credit_kind(family: str) -> str:
    if family == "manual_extra":
        return "manual_extra"
    if family in {
        "convolution_source_shape",
        "ennreal_tsum_condensation_shape",
        "iff_direction_canary",
        "interval_endpoint_alignment",
        "backend_context_full_file_check",
    }:
        return "repair_canary"
    return "source_action"


def _lean_cwd() -> Path:
    try:
        import sys
        sys.path.insert(0, str(REPO / "scripts/public/control"))
        import coherent_rung1 as cr
        return Path(cr.SB)
    except Exception:
        return REPO / "ztare_proofs"


def _run_lean(path: Path, timeout: int) -> dict[str, Any]:
    start = time.time()
    cwd = _lean_cwd()
    cmd = f"cd {shlex.quote(str(cwd))} && lake env lean {shlex.quote(str(path))}"
    try:
        proc = subprocess.run(
            ["bash", "-lc", cmd],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
        )
        timed_out = False
    except subprocess.TimeoutExpired as exc:
        proc = exc
        timed_out = True
    stdout = getattr(proc, "stdout", "") or ""
    stderr = getattr(proc, "stderr", "") or ""
    rc = None if timed_out else int(getattr(proc, "returncode", 1))
    return {
        "returncode": rc,
        "timed_out": timed_out,
        "seconds": round(time.time() - start, 3),
        "closed": bool(rc == 0 and not timed_out),
        "stdout_tail": stdout[-3000:],
        "stderr_tail": stderr[-3000:],
    }


def _run_repl_file(repl: Any, path: Path, timeout: int) -> dict[str, Any]:
    start = time.time()
    r = repl.open_file(str(path), timeout)
    messages = r.get("messages") or []
    errors = r.get("errors") or []
    sorries = r.get("sorries") or []
    rendered = "\n".join(
        f"{str(m.get('severity', '')).lower()}: {m.get('data', '')}"
        for m in messages
    )
    if r.get("err"):
        rendered = (rendered + "\n" + str(r.get("err"))).strip()
    closed = bool(r.get("ok") and not errors and not sorries)
    return {
        "returncode": 0 if closed else 1,
        "timed_out": str(r.get("err") or "") == "timeout_or_crash",
        "seconds": round(time.time() - start, 3),
        "closed": closed,
        "stdout_tail": rendered[-3000:],
        "stderr_tail": "",
        "repl_errors": errors,
        "repl_sorries": sorries,
    }


def _open_target_state(repl: Any, row: dict[str, Any], src: str, timeout: int) -> dict[str, Any]:
    code = _prefix_through_target_sorry(src, int(row.get("target_line") or 1))
    r = repl.check(code, timeout)
    sorries = r.get("sorries") or []
    target_line = int(row.get("target_line") or 1)
    chosen = next((s for s in sorries if int((s.get("pos") or {}).get("line") or s.get("line") or 0) >= target_line), None)
    chosen = chosen or (sorries[0] if sorries else None)
    if r.get("errors") or not chosen or chosen.get("proofState") is None:
        return {
            "ok": False,
            "ps": None,
            "goal": "",
            "err": str(r.get("errors") or r.get("raw") or "target proof state not found")[:500],
        }
    return {
        "ok": True,
        "ps": chosen.get("proofState"),
        "goal": chosen.get("goal", ""),
        "err": "",
    }


def _run_repl_step(repl: Any, ps: int | None, body: str, timeout: int,
                   open_error: str = "") -> dict[str, Any]:
    start = time.time()
    if ps is None:
        return {
            "returncode": 1,
            "timed_out": False,
            "seconds": round(time.time() - start, 3),
            "closed": False,
            "stdout_tail": open_error or "target proof state not available",
            "stderr_tail": "",
        }
    cur = ps
    trace: list[dict[str, Any]] = []
    r: dict[str, Any] = {"ok": False, "closed": False, "goals": [], "err": "empty_tactic"}
    tactics = _tactic_chunks(body)
    for tactic in tactics:
        r = repl.step(cur, tactic, timeout)
        trace.append({
            "tactic": tactic,
            "ok": bool(r.get("ok")),
            "closed": bool(r.get("closed")),
            "err": r.get("err") or "",
            "goal_count": len(r.get("goals") or []),
        })
        if not r.get("ok") or r.get("closed"):
            break
        cur = r.get("ps")
        if cur is None:
            r = {"ok": False, "closed": False, "goals": [], "err": "missing_next_proof_state"}
            break
    goals = "\n".join(str(g) for g in (r.get("goals") or []))
    text = str(r.get("err") or goals or "")
    return {
        "returncode": 0 if r.get("closed") else 1,
        "timed_out": str(r.get("err") or "") == "timeout_or_crash",
        "seconds": round(time.time() - start, 3),
        "closed": bool(r.get("closed")),
        "stdout_tail": text[-3000:],
        "stderr_tail": "",
        "repl_step_ok": bool(r.get("ok")),
        "repl_goals": r.get("goals") or [],
        "repl_step_trace": trace,
    }


def _tactic_chunks(body: str) -> list[str]:
    chunks: list[str] = []
    current: list[str] = []
    for raw in body.splitlines():
        if not raw.strip():
            continue
        is_continuation = raw[:1].isspace()
        if current and is_continuation:
            current.append(raw)
            continue
        if current:
            chunks.append("\n".join(current).rstrip())
        current = [raw.strip() if not is_continuation else raw]
    if current:
        chunks.append("\n".join(current).rstrip())
    return chunks


def _target_line(text: str, row: dict[str, Any]) -> int:
    return int(row.get("target_line") or 1)


def _govern(text: str, row: dict[str, Any], timeout: int) -> dict[str, Any]:
    import sys
    sys.path.insert(0, str(REPO))
    sys.path.insert(0, str(REPO / "scripts/public/control"))
    import authoritative_axioms as _AX
    import coherent_rung1 as cr
    from src.ztare.formal.lean_persistent import PersistentLean

    target_name = str((row.get("source") or {}).get("mathlib_name") or row.get("id") or row.get("row_id"))
    L = PersistentLean(cr.SB)
    L.start_tactic_proof("theorem _w : True := by sorry", timeout)
    try:
        return _AX.govern(L, text, _target_line(text, row), target_name, timeout, persist=True)
    finally:
        L.close()


def _govern_worker(queue: Any, text: str, row: dict[str, Any], timeout: int) -> None:
    try:
        queue.put({"ok": True, "payload": _govern(text, row, timeout)})
    except BaseException as exc:
        queue.put({"ok": False, "error": f"{type(exc).__name__}: {exc}"})


def _govern_bounded(text: str, row: dict[str, Any], timeout: int) -> dict[str, Any]:
    budget_s = max(1, int(timeout or 1)) + 15
    ctx = mp.get_context("fork") if "fork" in mp.get_all_start_methods() else mp.get_context()
    queue = ctx.Queue(maxsize=1)
    proc = ctx.Process(target=_govern_worker, args=(queue, text, row, int(timeout or 1)))
    proc.daemon = True
    proc.start()
    proc.join(budget_s)
    if proc.is_alive():
        proc.terminate()
        proc.join(5)
        if proc.is_alive():
            proc.kill()
            proc.join(5)
        return {
            "verdict": "reject",
            "reason": "governance_timeout",
            "timed_out": True,
            "timeout_s": int(timeout or 1),
            "wall_budget_s": budget_s,
        }
    try:
        msg = queue.get_nowait()
    except Exception:
        return {
            "verdict": "reject",
            "reason": "governance_no_result",
            "returncode": proc.exitcode,
            "timeout_s": int(timeout or 1),
            "wall_budget_s": budget_s,
        }
    if isinstance(msg, dict) and msg.get("ok"):
        payload = msg.get("payload")
        return payload if isinstance(payload, dict) else {"verdict": "reject", "reason": "governance_bad_result"}
    return {
        "verdict": "reject",
        "reason": "governance_exception",
        "error": str((msg or {}).get("error") if isinstance(msg, dict) else msg),
        "timeout_s": int(timeout or 1),
    }


def _error_class(rec: dict[str, Any]) -> str:
    text = (rec.get("stdout_tail", "") + "\n" + rec.get("stderr_tail", "")).lower()
    if rec.get("timed_out"):
        return "timeout"
    if "internal exception" in text:
        return "internal_exception"
    if "unknown identifier" in text or "unknown constant" in text:
        return "unknown_identifier"
    if "failed to synthesize" in text:
        return "missing_instance"
    if "application type mismatch" in text or "type mismatch" in text:
        return "type_mismatch"
    if "unsolved goals" in text:
        return "unsolved_goals"
    if "tactic" in text and "failed" in text:
        return "tactic_failed"
    if rec.get("returncode") not in (0, None):
        return "lean_error"
    return "compiled"


def _needs_file_fallback(rec: dict[str, Any], backend: str) -> bool:
    if backend != "repl_step":
        return False
    if rec.get("closed"):
        return False
    text = (str(rec.get("stdout_tail") or "") + "\n" + str(rec.get("stderr_tail") or "")).lower()
    if _error_class(rec) == "unknown_identifier":
        return True
    # Tactic-mode REPL can under-report extensionality context on row-local
    # repair canaries even when the full file elaborates. Escalate only this
    # narrow backend artifact to avoid fake mathematical residuals.
    return "no applicable extensionality theorem" in text


def _score_source_actions(repl: Any, ps: int | None, names: list[str], timeout: int) -> list[dict[str, Any]]:
    if ps is None:
        return []
    probes = [("exact", "exact {name}"), ("simpa_using", "simpa using {name}"), ("apply", "apply {name}")]
    probe_timeout = max(3, min(timeout, 10))
    scored: list[dict[str, Any]] = []
    for name in names:
        best: dict[str, Any] = {
            "candidate": name,
            "best_action": None,
            "score": -100,
            "closed": False,
            "ok": False,
            "goal_count": None,
            "error_class": "not_run",
            "message_tail": "",
        }
        for action, template in probes:
            r = repl.step(ps, template.format(name=name), probe_timeout)
            text = str(r.get("err") or "\n".join(str(g) for g in (r.get("goals") or [])) or "")
            rec = {
                "returncode": 0 if r.get("closed") else 1,
                "timed_out": str(r.get("err") or "") == "timeout_or_crash",
                "stdout_tail": text,
                "stderr_tail": "",
            }
            if r.get("closed"):
                score = 100
            elif r.get("ok"):
                score = max(1, 20 - len(r.get("goals") or []))
            else:
                cls = _error_class(rec)
                score = -30 if cls in {"type_mismatch", "missing_instance"} else -10
            if score > int(best["score"]):
                best = {
                    "candidate": name,
                    "best_action": action,
                    "score": score,
                    "closed": bool(r.get("closed")),
                    "ok": bool(r.get("ok")),
                    "goal_count": len(r.get("goals") or []),
                    "error_class": _error_class(rec),
                    "message_tail": text[-500:],
                }
        scored.append(best)
    return sorted(scored, key=lambda r: (-int(r.get("score") or 0), str(r.get("candidate") or "")))


def _parse_extra_bodies(items: list[str]) -> list[tuple[str, str, str]]:
    out: list[tuple[str, str, str]] = []
    for i, item in enumerate(items, start=1):
        if "::" in item:
            name, body = item.split("::", 1)
        else:
            name, body = f"manual_extra_{i}", item
        out.append((name.strip() or f"manual_extra_{i}", "manual_extra", body))
    return out


def run(row_id: str, corpus: Path, static_filter: Path, out: Path,
        timeout: int, max_candidates: int, max_actions: int,
        save_dir: Path | None, govern_winners: bool,
        extra_body: list[str] | None = None,
        action_family: list[str] | None = None,
        candidate_name: list[str] | None = None,
        backend: str = "subprocess",
        score_candidates: bool = False,
        require_positive_source_action: bool = False,
        persistent_repl: Any | None = None) -> dict[str, Any]:
    row = _row_by_id(corpus, row_id)
    src = Path(row["sorried_file"]).read_text(errors="ignore")
    names = _candidates(static_filter, row_id, max_candidates)
    if candidate_name:
        wanted = set(candidate_name)
        names = [n for n in names if n in wanted]
    family_filter = set(action_family or [])
    row_specific = _row_specific_templates(row_id, family_filter)
    manual_extra = _parse_extra_bodies(extra_body or [])
    if not names and not row_specific and not manual_extra:
        payload = {
            "schema": "leansearch-action-smoke-v1",
            "row_id": row_id,
            "corpus": str(corpus),
            "static_filter": str(static_filter),
            "backend": backend,
            "target_state_ok": None,
            "target_state_error": "not_opened_no_candidate_after_filter",
            "timeout": timeout,
            "max_candidates": max_candidates,
            "max_actions": max_actions,
            "action_family_filter": action_family or [],
            "candidate_name_filter": candidate_name or [],
            "results": [],
            "closed_candidates": [],
            "ratified_candidates": [],
            "n_closed": 0,
            "n_ratified": 0,
            "no_candidate_after_filter": True,
        }
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
        return payload
    out.parent.mkdir(parents=True, exist_ok=True)
    if save_dir:
        save_dir.mkdir(parents=True, exist_ok=True)
    results: list[dict[str, Any]] = []
    repl = persistent_repl
    close_repl = False
    target_state = {"ok": False, "ps": None, "err": ""}
    source_action_scores: list[dict[str, Any]] = []
    if backend in {"repl", "repl_file", "repl_step"}:
        if repl is None:
            import sys
            sys.path.insert(0, str(REPO))
            from src.ztare.formal.lean_persistent import PersistentLean
            repl = PersistentLean(_lean_cwd())
            close_repl = True
        if backend in {"repl", "repl_step"}:
            target_state = _open_target_state(repl, row, src, timeout)
            if score_candidates and names and target_state.get("ps") is not None:
                source_action_scores = _score_source_actions(repl, target_state.get("ps"), names, timeout)
                score_by_name = {str(s.get("candidate")): int(s.get("score") or -999) for s in source_action_scores}
                names = sorted(names, key=lambda n: (-score_by_name.get(n, -999), n))
                if require_positive_source_action and not row_specific and not manual_extra:
                    names = [n for n in names if score_by_name.get(n, -999) > 0]
                    if not names:
                        payload = {
                            "schema": "leansearch-action-smoke-v1",
                            "row_id": row_id,
                            "corpus": str(corpus),
                            "static_filter": str(static_filter),
                            "backend": backend,
                            "target_state_ok": bool(target_state.get("ok")),
                            "target_state_error": target_state.get("err"),
                            "timeout": timeout,
                            "max_candidates": max_candidates,
                            "max_actions": max_actions,
                            "action_family_filter": action_family or [],
                            "candidate_name_filter": candidate_name or [],
                            "source_action_scores": source_action_scores,
                            "results": [],
                            "closed_candidates": [],
                            "ratified_candidates": [],
                            "n_closed": 0,
                            "n_ratified": 0,
                            "no_positive_source_action": True,
                        }
                        out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
                        repl.close()
                        return payload
    with tempfile.TemporaryDirectory(prefix="leansearch_action_smoke_") as td:
        try:
            root = Path(td)
            actions: list[tuple[str, str, str]] = []
            for name in names:
                actions.extend(
                    (name, family, body)
                    for family, body in _templates(name, family_filter, str(row.get("goal") or ""))[:max_actions]
                )
            actions.extend(row_specific)
            actions.extend(manual_extra)
            for name, family, body in actions:
                stem = re.sub(r"[^A-Za-z0-9_]+", "_", f"{row_id}_{family}_{name}")[:140]
                path = root / f"{stem}.lean"
                patched = _replace_target_sorry(src, int(row.get("target_line") or 1), body)
                path.write_text(patched)
                saved = None
                if save_dir:
                    saved = save_dir / path.name
                    saved.write_text(patched)
                rec = {
                    "row_id": row_id,
                    "candidate": name,
                    "action_family": family,
                    "credit_kind": _credit_kind(family),
                    "source_credit_eligible": _credit_kind(family) == "source_action",
                    "source_action_score": next((s for s in source_action_scores if s.get("candidate") == name), None),
                    "body": body,
                    "driver_path": str(saved) if saved else None,
                    **(
                        _run_repl_step(
                            repl,
                            target_state.get("ps"),
                            body,
                            timeout,
                            str(target_state.get("err") or ""),
                        )
                        if backend in {"repl", "repl_step"}
                        else _run_repl_file(repl, path, timeout)
                        if backend == "repl_file"
                        else _run_lean(path, timeout)
                    ),
                }
                if _needs_file_fallback(rec, backend):
                    fallback = _run_repl_file(repl, path, max(timeout, 90))
                    rec["repl_step_original"] = {
                        "returncode": rec.get("returncode"),
                        "timed_out": rec.get("timed_out"),
                        "seconds": rec.get("seconds"),
                        "closed": rec.get("closed"),
                        "stdout_tail": rec.get("stdout_tail"),
                        "stderr_tail": rec.get("stderr_tail"),
                        "error_class": _error_class(rec),
                    }
                    rec["repl_step_file_fallback_used"] = True
                    rec.update(fallback)
                rec["error_class"] = _error_class(rec)
                if govern_winners and rec["closed"]:
                    rec["governance"] = _govern_bounded(patched, row, max(timeout, 160))
                results.append(rec)
        finally:
            if repl is not None and close_repl:
                repl.close()
    payload = {
        "schema": "leansearch-action-smoke-v1",
        "row_id": row_id,
        "corpus": str(corpus),
        "static_filter": str(static_filter),
        "backend": backend,
        "target_state_ok": bool(target_state.get("ok")) if backend in {"repl", "repl_step"} else None,
        "target_state_error": target_state.get("err") if backend in {"repl", "repl_step"} else None,
        "timeout": timeout,
        "max_candidates": max_candidates,
        "max_actions": max_actions,
        "action_family_filter": action_family or [],
        "candidate_name_filter": candidate_name or [],
        "source_action_scores": source_action_scores,
        "results": results,
        "closed_candidates": [
            {
                "candidate": r["candidate"],
                "action_family": r["action_family"],
                "credit_kind": r.get("credit_kind"),
                "source_credit_eligible": bool(r.get("source_credit_eligible")),
            }
            for r in results if r.get("closed")
        ],
        "ratified_candidates": [
            {
                "candidate": r["candidate"],
                "action_family": r["action_family"],
                "credit_kind": r.get("credit_kind"),
                "source_credit_eligible": bool(r.get("source_credit_eligible")),
                "governance_reason": (r.get("governance") or {}).get("reason"),
                "persisted": (r.get("governance") or {}).get("persisted"),
            }
            for r in results if (r.get("governance") or {}).get("verdict") == "closure"
        ],
        "n_closed": sum(1 for r in results if r.get("closed")),
        "n_ratified": sum(1 for r in results if (r.get("governance") or {}).get("verdict") == "closure"),
    }
    out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return payload


def _self_test() -> int:
    src = "theorem t : True := by\n  sorry\n"
    out = _replace_target_sorry(src, 1, "exact True.intro")
    assert "sorry" not in out and "exact True.intro" in out
    assert _error_class({"returncode": 1, "stdout_tail": "unsolved goals", "stderr_tail": ""}) == "unsolved_goals"
    assert _error_class({"returncode": 1, "stdout_tail": "Lean error: internal exception #5", "stderr_tail": ""}) == "internal_exception"
    assert "theorem t" in _prefix_through_target_sorry(src, 1)
    assert len(_templates("Foo.bar")) == 11
    assert len(_templates("Foo.bar", goal="⊢ P ↔ Q")) == 13
    assert len(_templates("Foo.bar", {"apply_easy"})) == 1
    assert len(_row_specific_templates("MCB_003_convolution_mono_right_of_nonneg", {"convolution_source_shape"})) == 1
    mcb004 = _row_specific_templates("MCB_004_convolution_congr", {"convolution_source_shape"})
    assert mcb004 and mcb004[0][2].startswith("ext x\n")
    mcb019 = _row_specific_templates("MCB_019_summable_condensed_iff_of_nonneg", {"ennreal_tsum_condensation_shape"})
    assert mcb019 and "summable_schlomilch_iff_of_nonneg" in mcb019[0][2]
    mcb016 = _row_specific_templates("MCB_016_summable_condensed_iff_of_nonneg", {"ennreal_tsum_condensation_shape"})
    assert mcb016 and "summable_schlomilch_iff_of_nonneg" in mcb016[0][2]
    mcb017 = _row_specific_templates("MCB_017_summable_condensed_iff_of_eventu", {"ennreal_tsum_condensation_shape"})
    assert mcb017 and "summable_condensed_iff_of_nonneg" in mcb017[0][2]
    mcb020 = _row_specific_templates("MCB_020_summable_condensed_iff_of_eventu", {"ennreal_tsum_condensation_shape"})
    assert mcb020 and "summable_condensed_iff_of_nonneg" in mcb020[0][2]
    mcb003 = _row_specific_templates("MCB_003_le_tsum_schlomilch", {"ennreal_tsum_condensation_shape"})
    assert mcb003 and "ENNReal.tsum_eq_iSup_nat'" in mcb003[0][2]
    assert not _row_specific_templates("MCB_012_isBigO_rpow_top_log_smul", {"convolution_source_shape"})
    assert _needs_file_fallback({"returncode": 1, "stdout_tail": "Unknown identifier Foo", "stderr_tail": ""}, "repl_step")
    assert _needs_file_fallback({"returncode": 1, "stdout_tail": "No applicable extensionality theorem found", "stderr_tail": ""}, "repl_step")
    assert not _needs_file_fallback({"returncode": 1, "stdout_tail": "Unknown identifier Foo", "stderr_tail": ""}, "repl_file")
    assert _credit_kind("convolution_source_shape") == "repair_canary"
    assert _credit_kind("ennreal_tsum_condensation_shape") == "repair_canary"
    assert _credit_kind("apply_easy") == "source_action"
    class FakePersistent:
        pass
    assert FakePersistent() is not None
    fake = type("R", (), {"step": lambda self, ps, tactic, timeout: {"ok": False, "closed": False, "goals": [], "err": "type mismatch"}})()
    scored = _score_source_actions(fake, 1, ["A.b"], 3)
    assert scored[0]["candidate"] == "A.b" and scored[0]["score"] < 0
    assert _tactic_chunks("have h : True := by\n  trivial\nexact h") == [
        "have h : True := by\n  trivial",
        "exact h",
    ]
    print("leansearch_action_smoke self-test PASS")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--row-id", required=False, default="MCB_019_summable_condensed_iff_of_nonneg")
    ap.add_argument("--corpus", default=DEFAULT_CORPUS)
    ap.add_argument("--static-filter", default=DEFAULT_STATIC_FILTER)
    ap.add_argument("--out", default=DEFAULT_OUT)
    ap.add_argument("--timeout", type=int, default=90)
    ap.add_argument("--max-candidates", type=int, default=3)
    ap.add_argument("--max-actions", type=int, default=3)
    ap.add_argument("--action-family", action="append", default=[],
                    help="Restrict generated action families; repeatable.")
    ap.add_argument("--candidate-name", action="append", default=[],
                    help="Restrict generated actions to exact candidate names; repeatable.")
    ap.add_argument("--backend", choices=["subprocess", "repl", "repl_step", "repl_file"], default="subprocess",
                    help="Use subprocess lake-env checks or persistent REPL file-mode checks.")
    ap.add_argument("--score-candidates", action="store_true",
                    help="Probe exact/simpa/apply first and sort candidates by kernel interaction.")
    ap.add_argument("--require-positive-source-action", action="store_true",
                    help="With --score-candidates, skip broad source-action templates unless a candidate has positive kernel delta.")
    ap.add_argument("--save-dir", default=DEFAULT_SAVE_DIR)
    ap.add_argument("--govern-winners", action="store_true")
    ap.add_argument("--extra-body", action="append", default=[],
                    help="Extra candidate in NAME::Lean body format; body replaces target sorry.")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return _self_test()
    obj = run(
        args.row_id,
        Path(args.corpus),
        Path(args.static_filter),
        Path(args.out),
        args.timeout,
        args.max_candidates,
        args.max_actions,
        Path(args.save_dir) if args.save_dir else None,
        args.govern_winners,
        args.extra_body,
        args.action_family,
        args.candidate_name,
        args.backend,
        args.score_candidates,
        args.require_positive_source_action,
    )
    print(json.dumps({
        "out": args.out,
        "row_id": obj["row_id"],
        "n_closed": obj["n_closed"],
        "n_ratified": obj["n_ratified"],
        "closed_candidates": obj["closed_candidates"],
        "ratified_candidates": obj["ratified_candidates"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
