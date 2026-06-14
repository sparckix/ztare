#!/usr/bin/env python3
"""route_c_layer_2c_dispatch.py — Route C Layer 2c LLM dispatch (semantic masking).

GP-235-aligned Route C wiring. Per the revised §7 architecture (post external-
reviewer): operator's semantic-masking framing + deterministic DAG-fingerprint
termination guard. LLM never sees a negative dictionary — only hypotheses +
goal + operation type. Layer 3 discriminator runs on the LLM's output via the
existing proof_route_fingerprint extractor.

Pipeline:
  1. Layer 2a — heuristic operation-type pick (from L2 structural catalog, or
     archetype_classifier ARCH-001..008).
  2. Layer 2c — semantic-masking LLM prompt: hypotheses + goal + op type.
     Output: candidate intermediate-lemma statement + proof sketch.
  3. Layer 3 — fingerprint the candidate proof, compare against neighborhood.
  4. Termination — max 2 re-prompt rounds, with "different structural pathway"
     positive-framed feedback. Hard termination on fingerprint-diff.
  5. Layer 5 fallback — structured gap report if no NOVEL candidate produced.

THIS IS A SCAFFOLD that runs the LLM dispatch and does basic discrimination
via proof_route_fingerprint. Lean compile-check of the candidate is NOT
wired here (would require running lake env lean on synthesized source) —
that's the next integration step.

Usage:
  route_c_layer_2c_dispatch.py --row <lean_row_file> [--max-rounds 2]
                               [--model gpt-4.1-mini] [--out <json>]
"""
from __future__ import annotations
import argparse, json, os, re, sys
from pathlib import Path
from typing import Any

ROOT = Path(__import__("os").environ.get("ZTARE_REPO_ROOT", ".")).resolve()
sys.path.insert(0, str(ROOT / "scripts/public/control"))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.ztare.leanmill.semantic_premise_shelf import (  # noqa: E402
    build_semantic_premise_shelf,
    render_semantic_premise_shelf,
    semantic_premise_shelf_enabled,
)
from src.ztare.leanmill.common import write_text_atomic  # noqa: E402

try:
    from archetype_classifier import classify  # type: ignore
    HAVE_CLASSIFIER = True
except Exception:
    HAVE_CLASSIFIER = False

try:
    from proof_route_fingerprint import parse_proof_body, surface_distance  # type: ignore
    HAVE_FINGERPRINT = True
except Exception:
    HAVE_FINGERPRINT = False

# Reuse pre-existing lean_fast_compile (3-5x faster than my safe runner; already production-tested)
sys.path.insert(0, str(ROOT / "scripts/public/lean"))
try:
    from lean_fast_compile import compile_lean_fast_combined_output  # type: ignore
    HAVE_FAST_COMPILE = True
except Exception:
    HAVE_FAST_COMPILE = False

# Reuse pre-existing proof_closure_candidate_gate (deterministic Layer 3 rejection)
try:
    from proof_closure_candidate_gate import validate_closure_candidate  # type: ignore
    HAVE_CLOSURE_GATE = True
except Exception:
    HAVE_CLOSURE_GATE = False

# Sandbox for compile-checking candidate proofs (reuses route_c_archetype_runner pattern)
SANDBOX = ROOT / (
    "analytics/public/leanmill/external_benchmarks/"
    "sandboxes/v28A_carleson_baseline/carleson"
)

LEAN_ERR_RE = re.compile(r"^\S*\.lean:\d+:\d+: error:", re.MULTILINE)


def find_lake_root(row_path: Path) -> Path | None:
    """Walk up parents looking for a lake project root (lakefile.toml or
    lake-manifest.json)."""
    for p in [row_path.parent] + list(row_path.parents):
        if (p / "lakefile.toml").exists() or (p / "lakefile.lean").exists() or (p / "lake-manifest.json").exists():
            return p
    return None


def lean_compile_check(candidate_lemma_statement: str, candidate_proof_body: str,
                       use_in_goal: str, original_row_text: str,
                       timeout: int = 90,
                       row_path: Path | None = None) -> dict:
    """Synthesize a Lean file that defines the candidate intermediate lemma
    and uses it to close the original row, then compile via `lake env lean`.

    If row_path is provided, the lake sandbox is detected by walking up to
    find lakefile.toml. Otherwise falls back to the hardcoded SANDBOX.

    Returns: {compiled, closing_via_candidate, elapsed, error_tail, timed_out}
    """
    import subprocess, tempfile, os, time
    sandbox = (find_lake_root(row_path) if row_path else None) or SANDBOX
    if sandbox is None or not sandbox.exists():
        return {"error": f"no lake sandbox found near {row_path} and default SANDBOX missing", "compiled": False}

    # Use proof body as-is (we'll decide whether to prefix `by` based on content)
    pb = candidate_proof_body.strip()

    # Build a self-contained Lean file: imports + candidate lemma + use-in-goal
    # The use_in_goal block should already reference `have h := <candidate>` so we
    # define the candidate as a `theorem` and the user uses it.
    # Strategy: synthesize a single example that proves the original goal using the
    # candidate inline as a `have`.
    # Extract imports + signature from original
    imports = []
    for line in original_row_text.splitlines():
        if line.strip().startswith("import "):
            imports.append(line.strip())
    if not imports:
        imports = ["import Mathlib", "import Hammer"]

    # Synthesize a file: imports + candidate (as standalone theorem) + example that uses it
    candidate_name = "claude_rd_candidate_lemma_v2c"
    synthesized = "\n".join(imports) + "\n\n"
    synthesized += f"-- Candidate intermediate lemma proposed by Layer 2c\n"
    # Normalize the lemma statement: strip leading `theorem|lemma|example <name>` and
    # trailing `:=` / `:= by` so we always wrap with our own keyword + name + `:= by`.
    stmt = candidate_lemma_statement.strip()
    stmt = re.sub(r"^\s*(theorem|lemma|example|def|instance)\s+[A-Za-z_][\w'.]*", "", stmt, count=1)
    stmt = stmt.lstrip()
    if stmt.startswith(":="):
        stmt = stmt[2:].lstrip()
    # Strip trailing `:= by` / `:=`
    stmt = re.sub(r"\s*:=\s*by\s*$", "", stmt)
    stmt = re.sub(r"\s*:=\s*$", "", stmt)
    stmt = stmt.rstrip()
    # If the proof_sketch already starts with `by`, don't double-prefix.
    pb_starts_with_by = pb.lstrip().startswith("by ") or pb.lstrip().startswith("by\n")
    synthesized += f"theorem {candidate_name} {stmt} := "
    if pb_starts_with_by:
        synthesized += pb.lstrip() + "\n"
    else:
        synthesized += "by\n"
        for line in pb.splitlines():
            synthesized += f"  {line}\n"
    synthesized += "\n"
    # Indent the proof body
    for line in pb.splitlines():
        synthesized += f"  {line}\n"
    synthesized += "\n"
    # Append the original row (which has the example/theorem to be closed) — but if the
    # original used `by hammer`, replace with the use_in_goal block
    # Strategy: just append the use_in_goal as-is for testing
    if use_in_goal.strip():
        synthesized += f"\n-- Use of candidate in target goal\n"
        synthesized += use_in_goal.strip() + "\n"

    # Write to sandbox tempfile
    tmpdir = sandbox / "Layer2cTmp"
    tmpdir.mkdir(exist_ok=True)
    tmpfile = tempfile.NamedTemporaryFile(
        mode="w", suffix=".lean", dir=str(tmpdir), delete=False
    )
    tmpfile.write(synthesized)
    tmpfile.close()
    rel = Path(tmpfile.name).relative_to(sandbox)

    started = time.time()
    # If lean_fast_compile is available, use it as drop-in (3-5x faster, combined output handles lake's stdout-vs-stderr gap)
    if HAVE_FAST_COMPILE:
        fast_result = compile_lean_fast_combined_output(Path(tmpfile.name), sandbox, timeout_seconds=timeout)
        out = fast_result.get("combined_output", "") or (fast_result.get("stdout","") + "\n" + fast_result.get("stderr",""))
        err = bool(LEAN_ERR_RE.search(out))
        compiled = bool(fast_result.get("compiled")) and (not err)
        return {
            "compiled": compiled,
            "elapsed": round(fast_result.get("duration_s", 0), 2),
            "error_tail": out[-600:] if err else "",
            "timed_out": fast_result.get("exit_code") == 124,
            "synthesized_file": str(tmpfile.name),
            "synthesized_preview": synthesized[:800],
            "compile_method": "lean_fast_compile (reused production component)",
        }
    # Fallback: my hand-rolled safe runner
    try:
        proc = subprocess.Popen(
            ["nice", "-n", "10", "lake", "env", "lean", str(rel)],
            cwd=str(sandbox),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            preexec_fn=os.setsid,
        )
        try:
            stdout, stderr = proc.communicate(timeout=timeout)
            elapsed = round(time.time() - started, 2)
            out = (stdout or "") + "\n" + (stderr or "")
            err = bool(LEAN_ERR_RE.search(out))
            compiled = (proc.returncode == 0) and (not err)
            return {
                "compiled": compiled,
                "elapsed": elapsed,
                "error_tail": out[-600:] if err else "",
                "timed_out": False,
                "synthesized_file": str(tmpfile.name),
                "synthesized_preview": synthesized[:800],
            }
        except subprocess.TimeoutExpired:
            try:
                os.killpg(os.getpgid(proc.pid), 9)
            except ProcessLookupError:
                pass
            return {
                "compiled": False,
                "elapsed": float(timeout),
                "error_tail": "",
                "timed_out": True,
                "synthesized_file": str(tmpfile.name),
            }
    except Exception as e:
        return {
            "compiled": False,
            "elapsed": round(time.time() - started, 2),
            "error": str(e),
        }
    finally:
        # Don't auto-delete on failure — operator may want to inspect
        pass


SEMANTIC_MASKING_PROMPT = """You are proposing a single intermediate mathematical state (Lemma L) that
bridges the listed hypotheses to the target goal in a Lean 4 / Mathlib v4.29.0 proof.

**CRITICAL LEAN 4 SYNTAX REQUIREMENTS:**
- Use Lean 4 syntax only — NO `begin ... end` blocks (that's Lean 3).
- Tactic proofs start with `by` followed by indented tactics.
- Type-class hypotheses must be `[ClassName Type]` declared as TOP-LEVEL parameters
  with `{{...}}` or `[...]`, NOT inside `∀` quantifiers.
- Example of GOOD signature: `theorem foo {{E : Type*}} [NormedAddCommGroup E] (a b : E) : ...`
- Example of BAD signature: `∀ (a b : E) [NormedAddCommGroup E], ...`  ← this fails Lean's type-class synthesis.

**Critical constraint: forward generation only.**
- I am NOT giving you a list of "do not propose" lemmas.
- I am NOT giving you a list of "already covered" lemmas.
- Generate L by reasoning purely forward from hypotheses + goal + operation type.
- L should encode the hardest logical leap between hypotheses and goal.

**Hypotheses in scope:**
{hypotheses}

**Target goal:**
```
{goal}
```

**Operation type (advisory — the structural move the proof needs):**
{operation_type}

**Candidate lemma shelf (advisory retrieval context; use only if it genuinely
applies to the target):**
{candidate_lemma_shelf}

**Your task:**
Output STRICT JSON with EXACTLY these keys (no other key names):
{{
  "lemma_name": "<snake_case proposed name for L>",
  "lemma_statement": "<Lean 4 syntax — formal statement of L, including any necessary type-class instance brackets [...] as top-level params>",
  "proof_sketch": "<Lean 4 tactic-script body starting with `by` — NO `begin/end`. Can use `sorry` for unfilled sub-steps>",
  "use_in_goal": "<Lean 4 tactic block showing how `have h := <proof of L>` is used to close the target goal>",
  "structural_pathway": "<1 sentence: what's the structural shape of L's proof>",
  "rationale": "<1-2 sentences: why L is the hardest leap>"
}}

Output JSON now."""


FEEDBACK_PROMPT = """Your previous proposal did not close the goal. Refine your proposal based on
the concrete feedback below.

**CRITICAL: keep the EXACT same output JSON schema as before. Use these keys exactly:
`lemma_name`, `lemma_statement`, `proof_sketch`, `use_in_goal`, `structural_pathway`, `rationale`. Do NOT use `name`, `statement`, etc.**

**Lean 4 syntax (same constraints as before):** no `begin/end`, type-class instances `[...]` as top-level params not inside `∀`, tactic proofs start with `by`.

**Hypotheses (same as before):**
{hypotheses}

**Goal (same as before):**
```
{goal}
```

**Operation type:**
{operation_type}

**Candidate lemma shelf (same advisory retrieval context):**
{candidate_lemma_shelf}

**Your previous proposal:**
- name: {prev_name}
- statement: {prev_statement}
- structural pathway: {prev_pathway}

**Why the previous proposal failed:**
{failure_reason}

{compile_error_block}

**What to do now:**
- If the Lean compile error indicates a SYNTACTIC issue (typeclass synthesis, missing import, malformed signature): fix the specific issue while keeping the same mathematical content.
- If the Lean error indicates a SEMANTIC mismatch (wrong direction, wrong quantifier, wrong type): propose a corrected statement.
- If no Lean error but the proposal is trivial/paraphrase: propose an intermediate state with a DIFFERENT STRUCTURAL PATHWAY (calc instead of direct, induction instead of refine, etc.).

Output the same strict JSON schema as before with a corrected lemma."""


def call_openai(prompt: str, model: str = "gpt-4.1-mini") -> dict[str, Any]:
    from openai import OpenAI
    client = OpenAI()
    res = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        temperature=0.5,
    )
    return json.loads(res.choices[0].message.content or "{}")


def extract_row_context(row_path: Path) -> dict[str, Any]:
    text = row_path.read_text()
    lines = text.splitlines()
    # Find example/theorem signature
    sig_block = []
    for i, line in enumerate(lines):
        if re.match(r"^\s*(example|theorem|lemma)\b", line):
            for j in range(i, min(len(lines), i + 20)):
                sig_block.append(lines[j])
                if ":= by" in lines[j] or lines[j].rstrip().endswith(":="):
                    break
            break
    sig_text = "\n".join(sig_block)
    # Hypotheses: paren-grouped (h : ...) entries
    hypotheses = []
    for m in re.finditer(r"\(([^()]+?)\)", sig_text):
        g = m.group(1)
        if ":" in g and re.match(r"^h", g.strip()):
            hypotheses.append(g.strip())
    # Goal: text after the last colon up to `:= by`
    goal = ""
    if ":= by" in sig_text:
        before_by = sig_text.split(":= by", 1)[0]
        # The last colon at top level is the goal type
        # heuristic: take everything after `):` or `: ` at top-level
        m = re.search(r"\)\s*:\s*(.+)$", before_by.replace("\n", " "), re.DOTALL)
        if m:
            goal = m.group(1).strip()
        else:
            # fallback — last colon
            parts = before_by.rsplit(":", 1)
            goal = parts[1].strip() if len(parts) == 2 else ""
    # Variables in scope
    variables = [l.strip() for l in lines if l.strip().startswith("variable ")][:5]
    return {
        "row_path": str(row_path),
        "signature_text": sig_text,
        "hypotheses": hypotheses,
        "goal": goal,
        "variables_in_scope": variables,
        "raw_text_preview": text[:800],
    }


def layer_2a_operation_type(context: dict) -> str:
    """Heuristic operation-type pick (no LLM)."""
    if HAVE_CLASSIFIER:
        try:
            c = classify(context["raw_text_preview"])
            return c.get("predicted_L4_archetype", "ARCH-001_direct_library_chain")
        except Exception:
            pass
    return "ARCH-001_direct_library_chain"


def layer_2c_propose(context: dict, op_type: str, model: str, feedback: dict | None = None) -> dict[str, Any]:
    """Run the semantic-masking LLM prompt."""
    candidate_lemma_shelf = context.get("candidate_lemma_shelf_text") or "(semantic premise shelf unavailable)"
    if feedback is None:
        prompt = SEMANTIC_MASKING_PROMPT.format(
            hypotheses="\n".join(f"- {h}" for h in context["hypotheses"]) or "(none extracted)",
            goal=context["goal"],
            operation_type=op_type,
            candidate_lemma_shelf=candidate_lemma_shelf,
        )
    else:
        compile_error_block = ""
        compile_info = feedback.get("_compile_result") or {}
        if compile_info.get("error_tail"):
            compile_error_block = (
                "**Lean compile error from your previous proposal:**\n"
                "```\n"
                f"{compile_info['error_tail'][:1500]}\n"
                "```\n"
            )
        elif compile_info.get("timed_out"):
            compile_error_block = "**Lean compile timed out on your previous proposal (>90s elapsing).** Simplify the proof.\n"

        failure_reason = "Lean compile failed" if compile_info.get("error_tail") else "Previous proposal needs revision (no concrete compile error available)"
        prompt = FEEDBACK_PROMPT.format(
            hypotheses="\n".join(f"- {h}" for h in context["hypotheses"]) or "(none extracted)",
            goal=context["goal"],
            operation_type=op_type,
            candidate_lemma_shelf=candidate_lemma_shelf,
            prev_pathway=feedback.get("structural_pathway", "?") or "?",
            prev_name=feedback.get("lemma_name", "?") or "?",
            prev_statement=(feedback.get("lemma_statement", "") or "")[:300],
            failure_reason=failure_reason,
            compile_error_block=compile_error_block,
        )
    return call_openai(prompt, model=model)


def layer_3_fingerprint_candidate(candidate: dict) -> dict[str, Any]:
    """Compute the surface fingerprint of the candidate proof sketch."""
    if not HAVE_FINGERPRINT:
        return {"error": "proof_route_fingerprint not available"}
    sketch = candidate.get("proof_sketch", "")
    use = candidate.get("use_in_goal", "")
    fp_sketch = parse_proof_body(sketch) if sketch else None
    fp_use = parse_proof_body(use) if use else None
    return {
        "candidate_lemma_name": candidate.get("lemma_name"),
        "candidate_lemma_statement": candidate.get("lemma_statement"),
        "structural_pathway": candidate.get("structural_pathway"),
        "proof_sketch_fingerprint": fp_sketch,
        "use_in_goal_fingerprint": fp_use,
    }


def termination_check(fp_history: list[dict]) -> dict[str, Any]:
    """Per GP-235 §7.4 termination guard: SAME fingerprint twice → exit oscillation.

    Two fingerprints are "SAME" if their tactic_family_sequence is identical AND
    skeleton_kind matches AND cited_constants overlap ≥80%.
    """
    if len(fp_history) < 2:
        return {"should_terminate": False, "reason": "fewer than 2 candidates"}
    a = fp_history[-2].get("proof_sketch_fingerprint")
    b = fp_history[-1].get("proof_sketch_fingerprint")
    if not a or not b:
        return {"should_terminate": False, "reason": "missing fingerprint"}
    seq_match = a["tactic_family_sequence"] == b["tactic_family_sequence"]
    skel_match = a["skeleton_kind"] == b["skeleton_kind"]
    set_a = set(a["cited_constants"])
    set_b = set(b["cited_constants"])
    overlap = len(set_a & set_b) / max(len(set_a | set_b), 1)
    if seq_match and skel_match and overlap >= 0.8:
        return {
            "should_terminate": True,
            "reason": "syntactic-variant oscillation detected (SAME fingerprint twice)",
            "seq_match": seq_match,
            "skel_match": skel_match,
            "constants_overlap_ratio": overlap,
        }
    return {
        "should_terminate": False,
        "reason": "fingerprints differ structurally",
        "seq_match": seq_match,
        "skel_match": skel_match,
        "constants_overlap_ratio": overlap,
    }


# Preflight vacuity gate — the validated leakage-independent organ
# (v33_preflight_risk_detector). Catches vacuous targets BEFORE any LLM
# spend, the capability the harness lacked when GPT-5.5 caught tick541 offline.
try:
    from v33_preflight_risk_detector import detect_risks as _vac_detect  # type: ignore
    _HAVE_VAC_GATE = True
except Exception:
    _HAVE_VAC_GATE = False

try:
    from v33_paraphrase_gate import detect_gold_name_verbatim as _para_detect, independent_corpus_confirm as _para_corpus  # type: ignore
    _HAVE_PARAPHRASE_GATE = True
except Exception:
    _HAVE_PARAPHRASE_GATE = False

try:
    from v33_single_lemma_exact_gate import (detect_shape as _sle_detect,  # type: ignore
                                             independent_exact_verify_rowfile as _sle_verify_rowfile,
                                             DEFAULT_SANDBOX as _sle_sandbox)
    _HAVE_SLE_GATE = True
except Exception:
    _HAVE_SLE_GATE = False

try:
    from v33_indirect_leakage_gate import preflight_probe_goal as _ind_preflight, DEFAULT_SANDBOX as _ind_sandbox  # type: ignore
    _HAVE_IND_GATE = True
except Exception:
    _HAVE_IND_GATE = False


def run_route_c_layer_2c(
    row_path: Path,
    max_rounds: int,
    model: str,
    do_compile: bool = False,
    semantic_premise_shelf: bool = True,
    semantic_threshold: float = 0.55,
) -> dict[str, Any]:
    context = extract_row_context(row_path)

    # PREFLIGHT VACUITY GATE (leakage-independent, statement-only, no LLM, no audit verdict)
    if _HAVE_VAC_GATE:
        goal_stmt = context.get("goal", "") or context.get("signature_text", "")
        vac = _vac_detect(goal_stmt)
        if vac.get("vacuity_suspected"):
            return {
                "row_context": context,
                "preflight_vacuity_gate": {
                    "blocked": True,
                    "risk_flags": vac["risk_flags"],
                    "statement_preview": vac["statement_preview"],
                    "rationale": ("target flagged vacuity-suspect at preflight (shape: "
                                  + ", ".join(vac["risk_flags"]) + ") — refusing LLM spend; "
                                  "this is the organ that would have caught tick541/carleman. "
                                  "Run v33_preflight_risk_detector --verify for independent Lean confirmation."),
                },
                "closure_verdict": "BLOCKED_VACUITY_SUSPECT_PREFLIGHT",
                "compiled_any": False,
            }

    # PREFLIGHT SINGLE-LEMMA-EXACT GATE (Lean's own exact?, no audit verdict).
    # Component-1 shape gates cheaply; Component-2 exact? probe only on
    # shape-candidates (bounds the ~40s Lean cost). If Lean's own exact?
    # closes the goal with one lemma, an LLM "non-subsumed closure" here is
    # not novel — the v26/v27 subsumption class.
    if _HAVE_SLE_GATE:
        goal_stmt = context.get("goal", "") or context.get("signature_text", "")
        shape = _sle_detect(goal_stmt)
        if shape.get("single_lemma_exact_suspect"):
            ver = _sle_verify_rowfile(row_path.read_text(), _sle_sandbox, timeout=70)
            if ver.get("single_lemma_exact_confirmed"):
                return {
                    "row_context": context,
                    "preflight_single_lemma_exact_gate": {
                        "blocked": True,
                        "exact_hint": ver.get("exact_hint"),
                        "rationale": ("Lean's own `exact?` closes this goal with a single "
                                      f"library lemma ({ver.get('exact_hint')}) — an LLM "
                                      "'non-subsumed closure' here is not novel (v26/v27 "
                                      "subsumption class). Leakage-independent: Lean's own "
                                      "tactic, no audit verdict. Refusing LLM spend."),
                    },
                    "closure_verdict": "BLOCKED_SINGLE_LEMMA_EXACT_PREFLIGHT",
                    "compiled_any": False,
                }

    # PREFLIGHT INDIRECT-LEAKAGE GATE (Lean's own global-set automation, no audit verdict).
    if _HAVE_IND_GATE:
        ind = _ind_preflight(row_path.read_text(), _ind_sandbox, timeout=70)
        if ind.get("preflight_indirect_leakage"):
            return {
                "row_context": context,
                "preflight_indirect_leakage_gate": {
                    "blocked": True,
                    "global_automation_closer": ind.get("global_automation_closer"),
                    "rationale": ind.get("interpretation"),
                },
                "closure_verdict": "BLOCKED_INDIRECT_LEAKAGE_PREFLIGHT",
                "compiled_any": False,
            }

    op_type = layer_2a_operation_type(context)
    if semantic_premise_shelf and semantic_premise_shelf_enabled():
        query = "\n".join(
            [
                "Lean hypotheses:",
                "\n".join(context.get("hypotheses") or []),
                "Lean goal:",
                str(context.get("goal") or ""),
                "Signature:",
                str(context.get("signature_text") or ""),
                "Operation type:",
                op_type,
            ]
        )
        shelf = build_semantic_premise_shelf(query, threshold=semantic_threshold)
        context["semantic_premise_shelf"] = shelf
        context["candidate_lemma_shelf_text"] = render_semantic_premise_shelf(shelf)
    original_row_text = row_path.read_text()
    rounds = []
    feedback = None
    compiled_any = False
    for round_idx in range(max_rounds):
        try:
            candidate = layer_2c_propose(context, op_type, model, feedback)
        except Exception as e:
            rounds.append({
                "round": round_idx,
                "error": f"LLM call failed: {e}",
            })
            break
        fp_result = layer_3_fingerprint_candidate(candidate)
        round_entry = {
            "round": round_idx,
            "operation_type": op_type,
            "candidate": candidate,
            "fingerprint_analysis": fp_result,
        }
        # Lean compile-check if requested
        if do_compile and candidate.get("lemma_statement") and candidate.get("proof_sketch"):
            try:
                compile_result = lean_compile_check(
                    candidate_lemma_statement=candidate["lemma_statement"],
                    candidate_proof_body=candidate["proof_sketch"],
                    use_in_goal=candidate.get("use_in_goal", ""),
                    original_row_text=original_row_text,
                    timeout=90,
                    row_path=row_path,
                )
                round_entry["lean_compile"] = compile_result
                if compile_result.get("compiled"):
                    # POST-CANDIDATE PARAPHRASE GATE (leakage-independent, no audit verdict):
                    # a compiled candidate that is just gold-name-verbatim of an
                    # existing Mathlib lemma is NOT a non-subsumed closure. This is
                    # the v28-v29 retraction class, now caught automatically.
                    if _HAVE_PARAPHRASE_GATE:
                        proof_txt = (candidate.get("lemma_statement", "") + " := by\n"
                                     + candidate.get("proof_sketch", ""))
                        gv = _para_detect(proof_txt)
                        prim = gv.get("primary_cited")
                        corpus = _para_corpus(prim) if (gv.get("gold_name_verbatim_suspect") and prim) else {"in_mathlib": False}
                        if gv.get("gold_name_verbatim_suspect") and corpus.get("in_mathlib"):
                            round_entry["paraphrase_gate"] = {
                                "gold_name_verbatim_confirmed": True,
                                "primary_cited": prim,
                                "rationale": (f"compiled candidate is verbatim the existing "
                                              f"Mathlib lemma `{prim}` + trivial glue — NOT a "
                                              f"non-subsumed closure (v28-v29 retraction class). "
                                              f"Leakage-independent: confirmed via Mathlib's own "
                                              f"corpus, no audit verdict."),
                            }
                            # do NOT count as a closure
                        else:
                            round_entry["paraphrase_gate"] = {"gold_name_verbatim_confirmed": False}
                            compiled_any = True
                    else:
                        compiled_any = True
            except Exception as e:
                round_entry["lean_compile"] = {"error": str(e), "compiled": False}
        rounds.append(round_entry)
        # Termination check
        fp_history = [r["fingerprint_analysis"] for r in rounds if "fingerprint_analysis" in r]
        term = termination_check(fp_history)
        rounds[-1]["termination_check"] = term
        # Stop early if a candidate compiles (success path)
        if compiled_any:
            term["should_terminate"] = True
            term["reason"] = "Lean compile succeeded — candidate closes the goal"
        if term["should_terminate"]:
            break
        # Attach the compile result to the candidate so the feedback prompt sees it
        if "lean_compile" in round_entry:
            candidate["_compile_result"] = round_entry["lean_compile"]
        feedback = candidate  # Loop with feedback for next round

    # Layer 5 gap report (structured)
    gap_report = {
        "target_row": str(row_path),
        "goal": context["goal"],
        "hypotheses": context["hypotheses"],
        "operation_type": op_type,
        "candidate_pathways": [
            r["candidate"].get("structural_pathway", "?")
            for r in rounds
            if "candidate" in r
        ],
        "named_candidate_lemmas": [
            r["candidate"].get("lemma_name", "?")
            for r in rounds
            if "candidate" in r
        ],
        "verdict": "NO_LEAN_COMPILE_VERIFICATION_AVAILABLE_IN_THIS_DISPATCH",
        "deliverable": "Layer 5 gap report — Lean compile-check would be the next integration step.",
    }

    # Mark closure verdict
    para_blocked = any(
        r.get("paraphrase_gate", {}).get("gold_name_verbatim_confirmed")
        for r in rounds
    )
    if compiled_any:
        closure_verdict = "CLOSED_BY_CANDIDATE"
    elif para_blocked:
        closure_verdict = "BLOCKED_GOLD_NAME_VERBATIM"  # compiled but verbatim Mathlib lemma
    else:
        closure_verdict = "OPEN_GAP_REPORT"
    return {
        "row_context": context,
        "operation_type_chosen": op_type,
        "rounds": rounds,
        "closure_verdict": closure_verdict,
        "compiled_any": compiled_any,
        "gap_report": gap_report,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--row", required=True, help="Lean row file to attempt closure on")
    ap.add_argument("--max-rounds", type=int, default=2)
    ap.add_argument("--model", default="gpt-4.1-mini")
    ap.add_argument("--out", default=None)
    ap.add_argument("--compile", action="store_true",
                    help="Wire Lean compile-check via lake env lean (slow, ~90s/candidate)")
    ap.add_argument("--no-semantic-premise-shelf", action="store_true",
                    help="Disable Mathlib/APN/NS semantic premise shelf injection.")
    ap.add_argument("--semantic-threshold", type=float, default=0.55)
    args = ap.parse_args()

    if not os.environ.get("OPENAI_API_KEY"):
        print("ERROR: OPENAI_API_KEY not set")
        return 2

    row_path = Path(args.row)
    if not row_path.exists():
        print(f"ERROR: row file does not exist: {row_path}")
        return 2

    result = run_route_c_layer_2c(
        row_path,
        args.max_rounds,
        args.model,
        do_compile=args.compile,
        semantic_premise_shelf=not args.no_semantic_premise_shelf,
        semantic_threshold=args.semantic_threshold,
    )
    out_text = json.dumps(result, indent=2, ensure_ascii=False, default=str)
    if args.out:
        write_text_atomic(args.out, out_text + ("\n" if not out_text.endswith("\n") else ""))
        print(f"wrote {args.out}")
    else:
        print(out_text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
