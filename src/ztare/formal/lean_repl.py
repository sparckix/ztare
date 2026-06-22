"""GP-122: Constrained Lean 4 REPL for ZTARE Proof Generation.

Takes a Lean 4 stub from lean_compiler.py and uses an LLM agent to
attempt to fill in proof tactics. The LLM is constrained by the ZTARE
intermediate lemma (the compression result). Lean 4 verifies each step.

Architecture (AlphaGeometry pattern):
1. ZTARE (Topological Oracle) finds the compression / rotation
2. lean_compiler.py (Axiom Translator) generates Lean stub
3. THIS MODULE (Constrained Prover) fills the proof via LLM + Lean REPL

The Lean verifier is the ultimate hard gate: if the proof typechecks,
it's correct. No narrative, no gaming, no artifacts.

This module now also emits a structured proof-obligation ledger so the
retry loop has a coarse proof-progress substrate rather than raw stderr
alone.

Usage:
    from ztare.formal.lean_repl import attempt_proof
    result = attempt_proof(lean_stub, max_attempts=10)
"""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path
from typing import Any

from ztare.common.llm_runtime import LLMRuntime, resolve_model_id


LEAN_BIN = Path.home() / ".elan" / "bin" / "lean"
ZTARE_PROOFS_DIR = Path("ztare_proofs")
LEDGER_FILENAME = "proof_obligation_ledger.json"
STALL_THRESHOLD = 3

_STATUS_RANK = {
    "hard_fail": 0,
    "compiles_with_sorry": 1,
    "verified": 2,
}

_ERROR_CLASS_PATTERNS: list[tuple[str, str]] = [
    ("timeout", r"timed out"),
    ("statement_drift", r"header drift|declaration header drift|assumption drift|missing original import|missing original declaration"),
    ("parse_import", r"unknown package|unknown module|object file|imports? failed|parse error|unexpected token|invalid syntax"),
    ("unknown_identifier", r"unknown constant|unknown identifier|unknown tactic"),
    ("contains_sorry", r"\bsorry\b|\badmit\b"),
    ("tactic_mismatch", r"tactic|failed to synthesize|unsolved goals|goal is not of the form|rewrite failed|simp made no progress"),
    ("unsolved_goal_family", r"application type mismatch|type mismatch|has type|expected type|synthesized type class instance"),
]


def check_lean(
    code: str,
    timeout: int = 60,
    project_dir: Path | str | None = None,
) -> dict[str, Any]:
    """Submit Lean 4 code to the Lean checker and return the result.

    `project_dir` selects the lake project the snippet is elaborated in
    (default: ZTARE_PROOFS_DIR — unchanged for existing callers). Passing
    a pinned sandbox lets a caller govern against a frozen Mathlib rev
    without forking this primitive.

    Concurrency: each call writes a UNIQUE tempfile inside `project_dir`
    (was a fixed `_ztare_repl_attempt.lean` — a fleet-global fixed-path
    race: two concurrent callers clobbered each other's file). Unique
    tempfiles make this primitive safe under autoresearch parallelism.

    Returns (all prior keys preserved; `raw` added):
        {"success", "output", "errors", "stderr", "stderr_lines",
         "returncode", "raw"} — `raw` = combined stdout+stderr (the
        UNFILTERED diagnostics, incl. Lean's `error(class):` lines that
        the `errors` filter drops; governed callers parse `raw`).
    """
    import os
    import tempfile

    proj = Path(project_dir) if project_dir is not None else ZTARE_PROOFS_DIR
    proj.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(suffix=".lean", dir=str(proj))
    tmp_path = Path(tmp_name)

    try:
        os.write(fd, code.encode("utf-8"))
        os.close(fd)
        lake_bin = LEAN_BIN.parent / "lake"
        result = subprocess.run(
            [str(lake_bin), "env", str(LEAN_BIN), tmp_path.name],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(proj),
        )

        stderr_lines = [line.strip() for line in result.stderr.splitlines() if line.strip()]
        errors = [line for line in stderr_lines if "error" in line.lower()]

        return {
            "success": result.returncode == 0 and len(errors) == 0,
            "output": result.stdout.strip(),
            "errors": errors,
            "stderr": result.stderr.strip(),
            "stderr_lines": stderr_lines,
            "returncode": result.returncode,
            "raw": (result.stdout or "") + (result.stderr or ""),
        }
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "output": "",
            "errors": ["Lean timed out"],
            "stderr": "",
            "stderr_lines": [],
            "returncode": -1,
            "raw": "TIMEOUT",
        }
    except Exception as e:
        return {
            "success": False,
            "output": "",
            "errors": [str(e)],
            "stderr": "",
            "stderr_lines": [],
            "returncode": -1,
            "raw": str(e),
        }
    finally:
        tmp_path.unlink(missing_ok=True)


def _extract_imports(code: str) -> list[str]:
    imports = []
    for line in code.splitlines():
        stripped = line.strip()
        if stripped.startswith("import "):
            imports.append(stripped.split(None, 1)[1])
    return imports


def _extract_declarations(code: str) -> list[str]:
    names: list[str] = []
    pattern = re.compile(r"^\s*(?:theorem|lemma|example)\s+([A-Za-z_]\w*)", re.MULTILINE)
    for match in pattern.finditer(code):
        names.append(match.group(1))
    return names


def _extract_declaration_headers(code: str) -> list[str]:
    headers: list[str] = []
    pattern = re.compile(r"^\s*(?:theorem|lemma|example)\b.+$", re.MULTILINE)
    for match in pattern.finditer(code):
        headers.append(match.group(0).strip())
    return headers


def _extract_assumptions(code: str) -> list[str]:
    assumptions: list[str] = []
    pattern = re.compile(r"^\s*(?:axiom|variable)\s+(.+)$", re.MULTILINE)
    for match in pattern.finditer(code):
        assumptions.append(match.group(1).strip())
    return assumptions


def _extract_open_goal_sites(code: str) -> list[dict[str, Any]]:
    sites: list[dict[str, Any]] = []
    for lineno, line in enumerate(code.splitlines(), start=1):
        stripped = line.strip()
        if stripped.startswith("--"):
            continue
        if "sorry" in stripped or "admit" in stripped:
            marker = "sorry" if "sorry" in stripped else "admit"
            sites.append({"line": lineno, "marker": marker, "snippet": stripped[:160]})
    return sites


def _build_stub_signature(code: str) -> dict[str, Any]:
    return {
        "imports": _extract_imports(code),
        "declarations": _extract_declarations(code),
        "declaration_headers": _extract_declaration_headers(code),
        "assumptions": _extract_assumptions(code),
    }


def _check_stub_integrity(candidate_code: str, baseline_signature: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    candidate_signature = _build_stub_signature(candidate_code)

    baseline_imports = list(baseline_signature.get("imports", []))
    candidate_imports = set(candidate_signature.get("imports", []))
    for imp in baseline_imports:
        if imp not in candidate_imports:
            errors.append(f"header drift: missing original import '{imp}'")

    if candidate_signature.get("assumptions", []) != baseline_signature.get("assumptions", []):
        errors.append("header drift: assumption drift")

    if candidate_signature.get("declarations", []) != baseline_signature.get("declarations", []):
        errors.append("header drift: missing original declaration")
    elif candidate_signature.get("declaration_headers", []) != baseline_signature.get("declaration_headers", []):
        errors.append("header drift: declaration header drift")

    return errors


def _classify_error_lines(error_lines: list[str], code: str) -> list[str]:
    classes: list[str] = []
    haystack = "\n".join(error_lines).lower()
    for cls, pattern in _ERROR_CLASS_PATTERNS:
        if re.search(pattern, haystack, re.IGNORECASE):
            classes.append(cls)
    if not error_lines and any(site["marker"] == "sorry" for site in _extract_open_goal_sites(code)):
        classes.append("contains_sorry")
    if not classes and error_lines:
        classes.append("other_hard_fail")
    return classes


def _extract_goal_signatures(error_lines: list[str]) -> list[str]:
    signatures: list[str] = []
    patterns = [
        re.compile(r"unknown (?:constant|identifier|tactic)\s+'?([A-Za-z0-9_\.]+)'?", re.IGNORECASE),
        re.compile(r"application type mismatch", re.IGNORECASE),
        re.compile(r"type mismatch", re.IGNORECASE),
        re.compile(r"failed to synthesize\s+([A-Za-z0-9_\.]+)", re.IGNORECASE),
        re.compile(r"unsolved goals?", re.IGNORECASE),
    ]
    for line in error_lines:
        for pattern in patterns:
            match = pattern.search(line)
            if match:
                if match.groups():
                    signatures.append(pattern.pattern.split("\\s")[0] + ":" + match.group(1))
                else:
                    signatures.append(pattern.pattern.split("\\s")[0])
                break
    seen: set[str] = set()
    out: list[str] = []
    for sig in signatures:
        if sig not in seen:
            seen.add(sig)
            out.append(sig[:160])
    return out[:8]


def _status_for_attempt(lean_result: dict[str, Any], code: str) -> str:
    if lean_result.get("success"):
        return "compiles_with_sorry" if _extract_open_goal_sites(code) else "verified"
    return "hard_fail"


def _summarize_attempt(
    attempt: int,
    code: str,
    lean_result: dict[str, Any],
    previous: dict[str, Any] | None,
) -> dict[str, Any]:
    status = _status_for_attempt(lean_result, code)
    error_lines = list(lean_result.get("errors", []))
    obstruction_classes = _classify_error_lines(error_lines, code)
    open_goal_sites = _extract_open_goal_sites(code)
    summary: dict[str, Any] = {
        "attempt": attempt,
        "status": status,
        "success": bool(lean_result.get("success")),
        "returncode": int(lean_result.get("returncode", -1)),
        "imports": _extract_imports(code),
        "declarations": _extract_declarations(code),
        "assumptions": _extract_assumptions(code),
        "open_goal_sites": open_goal_sites,
        "open_goal_count": len(open_goal_sites),
        "error_count": len(error_lines),
        "error_classes": obstruction_classes,
        "goal_signatures": _extract_goal_signatures(error_lines),
        "error_excerpt": error_lines[:5],
        "code_preview": code[:500],
        "progress_verdict": "initial" if previous is None else "stalled",
        "delta": {},
        "stall_streak": 1,
        "bottleneck_label": None,
    }

    if previous is None:
        return summary

    prev_rank = _STATUS_RANK.get(str(previous.get("status")), -1)
    curr_rank = _STATUS_RANK.get(status, -1)
    prev_error_count = int(previous.get("error_count", 0))
    prev_open_goals = int(previous.get("open_goal_count", 0))
    same_error_classes = previous.get("error_classes", []) == obstruction_classes

    improved = (
        curr_rank > prev_rank
        or (curr_rank == prev_rank and len(error_lines) < prev_error_count)
        or (status == "compiles_with_sorry" and len(open_goal_sites) < prev_open_goals)
    )
    regressed = (
        curr_rank < prev_rank
        or (curr_rank == prev_rank and len(error_lines) > prev_error_count and len(open_goal_sites) >= prev_open_goals)
    )

    if improved:
        verdict = "improved"
    elif regressed:
        verdict = "regressed"
    else:
        verdict = "stalled"

    stall_streak = int(previous.get("stall_streak", 1))
    if same_error_classes and verdict == "stalled":
        stall_streak += 1
    else:
        stall_streak = 1

    bottleneck_label = None
    if stall_streak >= STALL_THRESHOLD:
        primary = obstruction_classes[0] if obstruction_classes else "other_hard_fail"
        if primary == "parse_import":
            bottleneck_label = "statement_translation"
        elif primary == "statement_drift":
            bottleneck_label = "statement_translation"
        elif primary == "unknown_identifier":
            bottleneck_label = "premise_retrieval"
        elif primary == "unsolved_goal_family":
            bottleneck_label = "lemma_split"
        elif primary in {"tactic_mismatch", "contains_sorry"}:
            bottleneck_label = "tactic_local"
        elif primary == "timeout":
            bottleneck_label = "lemma_split"
        else:
            bottleneck_label = "other_obstruction"

    summary["progress_verdict"] = verdict
    summary["stall_streak"] = stall_streak
    summary["bottleneck_label"] = bottleneck_label
    summary["delta"] = {
        "status_rank_delta": curr_rank - prev_rank,
        "error_count_delta": len(error_lines) - prev_error_count,
        "open_goal_count_delta": len(open_goal_sites) - prev_open_goals,
        "same_error_classes": same_error_classes,
    }
    return summary


def _write_ledger(project_dir: Path | None, ledger: dict[str, Any]) -> None:
    if project_dir is None:
        return
    ledger_path = project_dir / "workspace" / LEDGER_FILENAME
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    ledger_path.write_text(json.dumps(ledger, indent=2), encoding="utf-8")


def _format_feedback(previous: dict[str, Any]) -> str:
    lines = [
        "## Structured feedback from previous attempt",
        f"- status: {previous.get('status')}",
        f"- progress_verdict: {previous.get('progress_verdict')}",
        f"- error_classes: {', '.join(previous.get('error_classes', [])) or 'none'}",
        f"- goal_signatures: {', '.join(previous.get('goal_signatures', [])) or 'none'}",
        f"- error_count: {previous.get('error_count')}",
        f"- open_goal_count: {previous.get('open_goal_count')}",
    ]
    if previous.get("bottleneck_label"):
        lines.append(f"- bottleneck_label: {previous['bottleneck_label']}")
    if previous.get("error_excerpt"):
        lines.append("- raw_error_excerpt:")
        for err in previous["error_excerpt"]:
            lines.append(f"  - {err}")
    if previous.get("bottleneck_label") in {"lemma_split", "premise_retrieval", "statement_translation"}:
        lines.append(
            "- policy_hint: repeated retries are stalling; preserve the theorem statement and focus on the named bottleneck rather than wholesale rewrites."
        )
    return "\n".join(lines)


def _should_stop_early(summary: dict[str, Any]) -> bool:
    if summary.get("progress_verdict") != "stalled":
        return False
    if int(summary.get("stall_streak", 0)) < STALL_THRESHOLD:
        return False
    return summary.get("bottleneck_label") in {
        "statement_translation",
        "premise_retrieval",
        "lemma_split",
    }


PROVER_SYSTEM_PROMPT = """You are a Lean 4 proof assistant. You receive:
1. A Lean 4 theorem statement (the stub from ZTARE's compression)
2. Structured feedback from previous proof attempts (if any)

Your job is to write Lean 4 tactic proofs that make the theorem typecheck.

Rules:
1. Output ONLY valid Lean 4 code. No markdown, no explanation, no commentary.
2. Use standard mathlib4 tactics: simp, norm_num, ring, linarith, omega, exact, apply, intro, etc.
3. The theorem statement is GIVEN — do not modify it unless the structured feedback says the statement/import layer is broken.
4. If you receive feedback, address the named obstruction class directly.
5. Start simple (try sorry first to check the statement compiles, then replace with real tactics).
6. Use the ZTARE constraint (the intermediate lemma) as your primary proof strategy.
7. If the loop is stalled on the same obstruction family, avoid cosmetic rewrites and target the bottleneck.
"""


def attempt_proof(
    lean_stub: str,
    max_attempts: int = 10,
    model: str = "gpt4.1",
    project_dir: Path | None = None,
) -> dict[str, Any]:
    """Attempt to prove a Lean 4 stub using LLM-guided tactic search.

    The LLM proposes proof tactics. Lean 4 checks them. Structured proof
    feedback, not just raw stderr, feeds the next attempt. Loop until success
    or max_attempts exhausted.

    Returns:
        {"proved": bool, "attempts": int, "final_code": str, "history": list}
    """
    runtime = LLMRuntime()
    model_id = resolve_model_id(model)

    history: list[dict[str, Any]] = []
    current_code = lean_stub
    previous_summary: dict[str, Any] | None = None
    baseline_signature = _build_stub_signature(lean_stub)
    ledger: dict[str, Any] = {
        "schema_version": 1,
        "opened_by": "GP-187 Slice A",
        "project_dir": str(project_dir) if project_dir else None,
        "baseline_signature": baseline_signature,
        "attempts": [],
        "final_bottleneck_label": None,
        "stop_reason": None,
    }

    print(f"  🔬 Lean REPL: attempting proof ({max_attempts} attempts max)")
    print(f"  🔬 Model: {model}")

    for attempt in range(1, max_attempts + 1):
        feedback_block = (
            _format_feedback(previous_summary)
            if previous_summary is not None
            else "## First attempt — start with sorry to check the statement compiles, then replace with real tactics."
        )
        user_prompt = f"""## Lean 4 Theorem to Prove

```lean
{current_code}
```

{feedback_block}

Write the complete Lean 4 file with the proof filled in.
Output ONLY the Lean 4 code, nothing else.
"""

        try:
            full_prompt = f"{PROVER_SYSTEM_PROMPT}\n\n{user_prompt}"
            llm_response = runtime.call_text(
                full_prompt,
                model_id=model_id,
                max_tokens=3000,
                request_label=f"lean_proof_attempt_{attempt}",
            )
            response_text = llm_response.text if hasattr(llm_response, "text") else str(llm_response)

            code = response_text.strip()
            if "```lean" in code:
                code = code.split("```lean", 1)[1].split("```", 1)[0].strip()
            elif "```" in code:
                code = code.split("```", 1)[1].split("```", 1)[0].strip()
        except Exception as e:
            summary = {
                "attempt": attempt,
                "status": "hard_fail",
                "success": False,
                "returncode": -1,
                "imports": _extract_imports(current_code),
                "declarations": _extract_declarations(current_code),
                "declaration_headers": _extract_declaration_headers(current_code),
                "assumptions": _extract_assumptions(current_code),
                "open_goal_sites": _extract_open_goal_sites(current_code),
                "open_goal_count": len(_extract_open_goal_sites(current_code)),
                "error_count": 1,
                "error_classes": ["llm_runtime_error"],
                "goal_signatures": [],
                "error_excerpt": [f"LLM call failed: {e}"],
                "code_preview": current_code[:500],
                "progress_verdict": "stalled" if previous_summary else "initial",
                "delta": {},
                "stall_streak": 1,
                "bottleneck_label": "llm_runtime_error",
            }
            history.append(summary)
            ledger["attempts"].append(summary)
            ledger["final_bottleneck_label"] = "llm_runtime_error"
            _write_ledger(project_dir, ledger)
            print(f"    Attempt {attempt}: LLM error — {e}")
            previous_summary = summary
            continue

        integrity_errors = _check_stub_integrity(code, baseline_signature)
        if integrity_errors:
            lean_result = {
                "success": False,
                "output": "",
                "errors": integrity_errors,
                "stderr": "\n".join(integrity_errors),
                "stderr_lines": integrity_errors,
                "returncode": -2,
            }
        else:
            lean_result = check_lean(code)
        summary = _summarize_attempt(attempt, code, lean_result, previous_summary)
        history.append(summary)
        ledger["attempts"].append(summary)
        ledger["final_bottleneck_label"] = summary.get("bottleneck_label")
        _write_ledger(project_dir, ledger)

        if lean_result["success"]:
            print(f"    Attempt {attempt}: ✅ PROOF TYPECHECKS")
            if summary["status"] == "compiles_with_sorry":
                print("    (contains sorry — proof incomplete, continuing)")
                current_code = code
                previous_summary = summary
                continue

            if project_dir:
                proof_path = project_dir / "workspace" / "verified_proof.lean"
                proof_path.parent.mkdir(parents=True, exist_ok=True)
                proof_path.write_text(code, encoding="utf-8")
                print(f"    Saved to {proof_path}")

            return {
                "proved": True,
                "attempts": attempt,
                "final_code": code,
                "history": history,
                "proof_obligation_ledger": ledger,
                "ledger_path": str(project_dir / "workspace" / LEDGER_FILENAME) if project_dir else None,
                "final_bottleneck_label": summary.get("bottleneck_label"),
            }

        current_code = code
        previous_summary = summary
        print(
            f"    Attempt {attempt}: ❌ status={summary['status']} "
            f"classes={summary['error_classes']} progress={summary['progress_verdict']}"
        )
        for err in summary["error_excerpt"][:2]:
            print(f"      {err[:100]}")
        if _should_stop_early(summary):
            ledger["stop_reason"] = "stalled_on_bottleneck"
            ledger["final_bottleneck_label"] = summary.get("bottleneck_label")
            _write_ledger(project_dir, ledger)
            print(
                "    Early stop: repeated non-local bottleneck "
                f"({summary['bottleneck_label']})"
            )
            break

    print(f"  🔬 Lean REPL: exhausted {max_attempts} attempts")
    return {
        "proved": False,
        "attempts": len(history),
        "final_code": current_code,
        "history": history,
        "proof_obligation_ledger": ledger,
        "ledger_path": str(project_dir / "workspace" / LEDGER_FILENAME) if project_dir else None,
        "final_bottleneck_label": ledger.get("final_bottleneck_label"),
        "stop_reason": ledger.get("stop_reason"),
    }


def prove_from_compression(
    project_dir: Path,
    model: str = "gpt4.1",
    max_attempts: int = 10,
) -> dict[str, Any]:
    """End-to-end: read ZTARE compression → generate Lean stub → attempt proof.

    This is the full pipeline:
    1. Read compression_results.json for the best gate-passing form
    2. Call lean_compiler to generate the stub
    3. Call attempt_proof to try to prove it
    """
    comp_path = project_dir / "workspace" / "compression_results.json"
    if not comp_path.exists():
        return {"error": "No compression results found"}

    results = json.loads(comp_path.read_text())
    passed = [r for r in results if r.get("gates_passed")]
    if not passed:
        return {"error": "No gate-passing compression forms"}

    best = min(passed, key=lambda r: r.get("bic", float("inf")))
    print(f"  Best compression: {best['name']} k={best['k']}")
    print(f"    {best['expression']}")

    lean_stub_path = project_dir / f"{project_dir.name}.lean"
    if lean_stub_path.exists():
        lean_stub = lean_stub_path.read_text(encoding="utf-8")
        print(f"  Lean stub loaded from {lean_stub_path}")
    else:
        try:
            from ztare.formal.lean_compiler import compile_to_lean

            lean_stub = compile_to_lean(project_dir)
            print("  Lean stub generated")
        except Exception as e:
            return {"error": f"Lean compilation failed: {e}"}

    return attempt_proof(
        lean_stub,
        max_attempts=max_attempts,
        model=model,
        project_dir=project_dir,
    )
