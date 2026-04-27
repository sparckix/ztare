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

Usage:
    from src.ztare.formal.lean_repl import attempt_proof
    result = attempt_proof(lean_stub, max_attempts=10)
"""

from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path

from src.ztare.common.llm_runtime import LLMRuntime, resolve_model_id


LEAN_BIN = Path.home() / ".elan" / "bin" / "lean"
ZTARE_PROOFS_DIR = Path("ztare_proofs")


def check_lean(code: str, timeout: int = 60) -> dict:
    """Submit Lean 4 code to the Lean checker and return the result.

    Returns:
        {"success": True/False, "output": str, "errors": list[str]}
    """
    # Write inside ztare_proofs/ so Lean can find Mathlib
    tmp_path = ZTARE_PROOFS_DIR / "_ztare_repl_attempt.lean"
    tmp_path.write_text(code, encoding="utf-8")

    try:
        # Use lake env lean to get Mathlib in the search path
        lake_bin = LEAN_BIN.parent / "lake"
        result = subprocess.run(
            [str(lake_bin), "env", str(LEAN_BIN), str(tmp_path.name)],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(ZTARE_PROOFS_DIR),
        )

        errors = []
        for line in result.stderr.splitlines():
            if "error" in line.lower():
                errors.append(line.strip())

        return {
            "success": result.returncode == 0 and len(errors) == 0,
            "output": result.stdout.strip(),
            "errors": errors,
            "stderr": result.stderr.strip()[:500],
            "returncode": result.returncode,
        }
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "output": "",
            "errors": ["Lean timed out"],
            "stderr": "",
            "returncode": -1,
        }
    except Exception as e:
        return {
            "success": False,
            "output": "",
            "errors": [str(e)],
            "stderr": "",
            "returncode": -1,
        }
    finally:
        tmp_path.unlink(missing_ok=True)


PROVER_SYSTEM_PROMPT = """You are a Lean 4 proof assistant. You receive:
1. A Lean 4 theorem statement (the stub from ZTARE's compression)
2. Error messages from previous proof attempts (if any)

Your job is to write Lean 4 tactic proofs that make the theorem typecheck.

Rules:
1. Output ONLY valid Lean 4 code. No markdown, no explanation, no commentary.
2. Use standard mathlib4 tactics: simp, norm_num, ring, linarith, omega, exact, apply, intro, etc.
3. The theorem statement is GIVEN — do not modify it. Only fill in the proof.
4. If you receive error messages, analyze them and fix the specific tactic that failed.
5. Start simple (try sorry first to check the statement, then replace with real tactics).
6. Use the ZTARE constraint (the intermediate lemma) as your primary proof strategy.
"""


def attempt_proof(
    lean_stub: str,
    max_attempts: int = 10,
    model: str = "gpt4.1",
    project_dir: Path | None = None,
) -> dict:
    """Attempt to prove a Lean 4 stub using LLM-guided tactic search.

    The LLM proposes proof tactics. Lean 4 checks them. Errors feed
    back to the LLM for the next attempt. Loop until success or
    max_attempts exhausted.

    Returns:
        {"proved": bool, "attempts": int, "final_code": str, "history": list}
    """
    runtime = LLMRuntime()
    model_id = resolve_model_id(model)

    history = []
    current_code = lean_stub
    errors_so_far = ""

    print(f"  🔬 Lean REPL: attempting proof ({max_attempts} attempts max)")
    print(f"  🔬 Model: {model}")

    for attempt in range(1, max_attempts + 1):
        # Step 1: Ask LLM to fill/fix the proof
        user_prompt = f"""## Lean 4 Theorem to Prove

```lean
{current_code}
```

{f"## Errors from previous attempt{chr(10)}{errors_so_far}" if errors_so_far else "## First attempt — start with sorry to check the statement compiles, then replace with real tactics."}

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

            # Extract Lean code from response
            code = response_text.strip()
            if "```lean" in code:
                code = code.split("```lean")[1].split("```")[0].strip()
            elif "```" in code:
                code = code.split("```")[1].split("```")[0].strip()

        except Exception as e:
            history.append({"attempt": attempt, "error": f"LLM call failed: {e}"})
            print(f"    Attempt {attempt}: LLM error — {e}")
            continue

        # Step 2: Check with Lean 4
        lean_result = check_lean(code)

        history.append({
            "attempt": attempt,
            "code": code[:500],
            "success": lean_result["success"],
            "errors": lean_result["errors"],
        })

        if lean_result["success"]:
            print(f"    Attempt {attempt}: ✅ PROOF TYPECHECKS")

            # Check if it still has sorry
            if "sorry" in code:
                print(f"    (contains sorry — proof incomplete, continuing)")
                errors_so_far = "The code compiles but contains 'sorry'. Replace ALL sorry with real proof tactics."
                current_code = code
                continue

            # Save the successful proof
            if project_dir:
                proof_path = project_dir / "workspace" / "verified_proof.lean"
                proof_path.parent.mkdir(parents=True, exist_ok=True)
                proof_path.write_text(code)
                print(f"    Saved to {proof_path}")

            return {
                "proved": True,
                "attempts": attempt,
                "final_code": code,
                "history": history,
            }
        else:
            errors_so_far = "\n".join(lean_result["errors"][:5])
            current_code = code
            print(f"    Attempt {attempt}: ❌ {len(lean_result['errors'])} error(s)")
            for e in lean_result["errors"][:2]:
                print(f"      {e[:100]}")

    print(f"  🔬 Lean REPL: exhausted {max_attempts} attempts")
    return {
        "proved": False,
        "attempts": max_attempts,
        "final_code": current_code,
        "history": history,
    }


def prove_from_compression(
    project_dir: Path,
    model: str = "gpt4.1",
    max_attempts: int = 10,
) -> dict:
    """End-to-end: read ZTARE compression → generate Lean stub → attempt proof.

    This is the full pipeline:
    1. Read compression_results.json for the best gate-passing form
    2. Call lean_compiler to generate the stub
    3. Call attempt_proof to try to prove it
    """
    # Step 1: Get the compression result
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

    # Step 2: Generate Lean stub
    lean_stub_path = project_dir / f"{project_dir.name}.lean"
    if lean_stub_path.exists():
        lean_stub = lean_stub_path.read_text()
        print(f"  Lean stub loaded from {lean_stub_path}")
    else:
        # Generate via lean_compiler
        try:
            from src.ztare.formal.lean_compiler import compile_to_lean
            lean_stub = compile_to_lean(project_dir)
            print(f"  Lean stub generated")
        except Exception as e:
            return {"error": f"Lean compilation failed: {e}"}

    # Step 3: Attempt proof
    return attempt_proof(
        lean_stub,
        max_attempts=max_attempts,
        model=model,
        project_dir=project_dir,
    )
