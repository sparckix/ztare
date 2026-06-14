#!/usr/bin/env python3
"""LLM theorem closed loop: nominate → lake build → revise → verify.

Minimum viable theorem-writer loop:

  1. Run llm_graph_analyst.py to get nominations from Gemini.
  2. For each nomination, run the typed identifier pre-filter.
  3. Write to ztare_proofs/ZtareProofs/<name>_iter.lean, run lake build, then
     run the existing Lean axiom/forbidden-token audit.
  4. If build/audit fails, capture the error, ask Gemini to revise the theorem
     (with the error as falsifier feedback), retry up to N times.
  5. Log each nomination's outcome: VERIFIED (lake-built clean) or
     UNVERIFIABLE (failed all retries) plus the full revision history.

This converts "theorem scout that proposes wrong things" into "verified
scout that only ships things lake-build plus axiom-audit accepts." Stage 1
is a regex-based identifier filter; Lean elaboration remains the ground truth.

# Honest scope

  - Stage 1 + Stage 3 only: cheap typed filter plus compiler/audit check
  - Falsifier log is training data for future stages (4: learning loop)
  - Failed revisions are still useful: they teach where the apparatus
    proposes implausible things

Usage:
    python scripts/public/analytics_shared/llm_theorem_closed_loop.py
    python scripts/public/analytics_shared/llm_theorem_closed_loop.py --max-revisions 5
    python scripts/public/analytics_shared/llm_theorem_closed_loop.py --dry-run  # don't actually run lake
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from math import ceil
from datetime import UTC, datetime
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts" / "public" / "lean"))
DEFAULT_CLOSED_LOOP_LOG = (
    REPO / "analytics" / "public" / "queries" / "closed_loop" / "closed_loop_log.jsonl"
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

NOMINATION_RE = re.compile(
    r"```lean\s*\n([\s\S]*?)\n\s*```",
    re.MULTILINE,
)


def extract_lean_blocks(text: str) -> list[str]:
    """Pull out every ```lean fenced block."""
    return [m.group(1).strip() for m in NOMINATION_RE.finditer(text)]


def extract_theorem_name(lean_src: str) -> str | None:
    m = re.search(r"\b(?:theorem|lemma)\s+([A-Za-z_][A-Za-z0-9_]*)", lean_src)
    return m.group(1) if m else None


def has_theorem_or_lemma(lean_src: str) -> bool:
    return extract_theorem_name(lean_src) is not None


def semantic_domain_tokens(lean_src: str) -> set[str]:
    """Identifiers that make the theorem about this proof spine.

    The closed loop is allowed to repair orientation and wrappers, but a
    revision that turns `sharpTarget ≤ ...` into a generic Nat lemma is not a
    repaired theorem. This cheap filter keeps the compiler from accepting
    target drift as progress.
    """
    import lean_decl_index as ldi
    surface = ldi.identifier_check_surface(lean_src)
    local_names = ldi.local_names_in_snippet(surface)
    theorem_name = extract_theorem_name(lean_src)
    if theorem_name:
        local_names.add(theorem_name)
    tokens: set[str] = set()
    for tok in ldi.IDENT_RE.findall(surface):
        head = tok.split(".")[0]
        tail = tok.split(".")[-1]
        if tok in local_names or head in local_names or tail in local_names:
            continue
        if tok in ldi.GLOBAL_OK or head in ldi.GLOBAL_OK:
            continue
        if re.fullmatch(r"\d+", tok):
            continue
        tokens.add(tok)
        if "." in tok:
            tokens.add(tail)
    return tokens


def semantic_revision_check(original: str, current: str) -> dict:
    """Reject target drift before stage 1 / lake build."""
    original_name = extract_theorem_name(original)
    current_name = extract_theorem_name(current)
    if original_name and current_name and original_name != current_name:
        return {
            "valid": False,
            "reason": (
                f"theorem name drifted from {original_name} to {current_name}"
            ),
        }
    current_tokens = semantic_domain_tokens(current)
    if not current_tokens:
        return {
            "valid": False,
            "reason": "revised theorem has no domain/spine identifiers",
        }
    original_tokens = semantic_domain_tokens(original)
    if original_tokens and current_tokens.isdisjoint(original_tokens):
        return {
            "valid": False,
            "reason": (
                "revised theorem lost all original domain identifiers: "
                f"original={sorted(original_tokens)[:8]}, "
                f"current={sorted(current_tokens)[:8]}"
            ),
        }
    if len(original_tokens) >= 3:
        min_preserved = max(2, ceil(len(original_tokens) / 2))
        n_preserved = len(original_tokens & current_tokens)
        if n_preserved < min_preserved:
            return {
                "valid": False,
                "reason": (
                    "revised theorem deleted too much of the original "
                    f"quantity surface: preserved {n_preserved}/"
                    f"{len(original_tokens)}, required {min_preserved}"
                ),
            }
    return {"valid": True, "reason": "semantic target preserved"}


_RUNTIME = None


def _get_runtime():
    global _RUNTIME
    if _RUNTIME is not None:
        return _RUNTIME
    # Lazy import keeps --help / dry inspection usable on machines
    # without optional provider SDKs installed.
    from src.ztare.common.llm_runtime import LLMRuntime

    _RUNTIME = LLMRuntime()
    return _RUNTIME


def call_gemini(prompt: str, model: str | None = None,
                max_tokens: int = 4000) -> str:
    """Provider-agnostic LLM call (legacy name preserved)."""
    from src.ztare.common.llm_runtime import pick_default_model_id_for_scripts

    model_id = model or pick_default_model_id_for_scripts()
    if model_id is None:
        return (
            "ERROR: no LLM provider available — set ANTHROPIC_API_KEY, "
            "OPENAI_API_KEY, or GEMINI_API_KEY"
        )
    try:
        response = _get_runtime().call_text(
            prompt,
            model_id=model_id,
            max_tokens=max_tokens,
            request_label="llm_theorem_closed_loop",
        )
        return response.text or "(empty response)"
    except Exception as exc:
        return f"ERROR: {type(exc).__name__}: {exc}"


def get_initial_nominations() -> list[str]:
    """Run llm_graph_analyst.py and parse its Lean blocks."""
    print("[step 1] running llm_graph_analyst...")
    output_path = (
        REPO / "projects" / "ns_millennium_hunt" / "workspace" / "queries"
        / "llm_graph_analyst_output.md"
    )
    before_mtime = output_path.stat().st_mtime if output_path.exists() else None
    result = subprocess.run(
        ["./venv/bin/python", "projects/ns_millennium_hunt/scripts/llm_graph_analyst.py", "--no-transitivity"],
        cwd=REPO, capture_output=True, text=True, timeout=300,
    )
    after_mtime = output_path.stat().st_mtime if output_path.exists() else None
    output_is_fresh = (
        output_path.exists()
        and (before_mtime is None or after_mtime != before_mtime)
    )
    if result.returncode != 0 and not output_is_fresh:
        print("  analyst run failed and no fresh output was written")
        if result.stderr:
            print(result.stderr[-1000:])
        return []
    if output_is_fresh:
        text = output_path.read_text()
    else:
        text = result.stdout
    blocks = extract_lean_blocks(text)
    print(f"  parsed {len(blocks)} Lean blocks from analyst output")
    return blocks


def write_and_build(lean_src: str, slug: str, dry_run: bool = False) -> dict:
    """Write Lean source to ztare_proofs and run lake build."""
    from src.ztare.gates.lean_proof_gate import (
        audit_axioms,
        write_lean_target,
    )
    from lean_fast_compile import compile_lean_fast_combined_output
    proofs_root = REPO / "ztare_proofs"
    if dry_run:
        return {"compiled": True, "stdout": "[dry-run]", "stderr": "",
                "exit_code": 0, "duration_s": 0.0,
                "raw_compiled": True, "axiom_audit_passed": True,
                "dry_run": True,
                "lean_path": str(proofs_root / "ZtareProofs" / f"{slug}_iter.lean")}
    target = write_lean_target(lean_src, slug, proofs_root)
    result = compile_lean_fast_combined_output(
        target, proofs_root, timeout_seconds=120)
    result["lean_path"] = str(target)
    result["raw_compiled"] = result["compiled"]
    if result["compiled"]:
        audit = audit_axioms(target, proofs_root)
        result.update(audit)
        if not audit.get("axiom_audit_passed"):
            result["compiled"] = False
            forbidden = ", ".join(audit.get("forbidden_tokens", []))
            axioms = ", ".join(audit.get("extra_axioms", []))
            result["stderr"] = (
                (result.get("stderr") or "")
                + "\n[lean-audit rejected target]"
                + (f"\nforbidden_tokens: {forbidden}" if forbidden else "")
                + (f"\nextra_axioms: {axioms}" if axioms else "")
            )
    else:
        result["axiom_audit_passed"] = False
    result["lean_path"] = str(target)
    return result


def load_prior_failure_signal() -> str:
    """Stage 4 closure: pull aggregate failure history from prior runs.

    Reads analytics/public/queries/closed_loop/closed_loop_log.learning.json +
    recent
    closed_loop_log.jsonl rows, returns a short prefix the next
    nomination prompt can condition on. Converts Stage 4 from
    descriptive to corrective.
    """
    learning_path = (
        REPO
        / "analytics"
        / "public"
        / "queries"
        / "closed_loop"
        / "closed_loop_log.learning.json"
    )
    log_path = REPO / "analytics" / "public" / "queries" / "closed_loop" / "closed_loop_log.jsonl"
    if not learning_path.exists() and not log_path.exists():
        return ""
    parts = ["# Prior closed-loop run signals (avoid repeating these failures):"]
    if learning_path.exists():
        learning = json.loads(learning_path.read_text())
        if learning.get("top_unresolved_idents"):
            top_unresolved = ", ".join(
                f"{ident} (rejected {n}x)"
                for ident, n in learning["top_unresolved_idents"][:8])
            parts.append(f"- Identifiers most-rejected by typed filter: {top_unresolved}")
        if learning.get("top_lake_errors"):
            parts.append("- Most-common lake-build error patterns:")
            for err, n in learning["top_lake_errors"][:3]:
                parts.append(f"    {n}x: {err[:80]}")
        if learning.get("top_semantic_errors"):
            parts.append("- Most-common semantic target-drift errors:")
            for err, n in learning["top_semantic_errors"][:3]:
                parts.append(f"    {n}x: {err[:100]}")
    if log_path.exists():
        rows = [
            json.loads(l) for l in log_path.read_text().splitlines()
            if l.strip()
        ]
        rows = [r for r in rows if not r.get("run_meta", {}).get("dry_run")]
        unverified_names = [r["name"] for r in rows[-20:]
                             if r.get("verdict") == "UNVERIFIABLE"][:5]
        if unverified_names:
            parts.append(
                f"- Recently-failed nominations (do NOT re-propose): "
                f"{', '.join(unverified_names)}")
    if len(parts) == 1:
        return ""  # nothing to add
    parts.append("")
    return "\n".join(parts)


def revise_prompt(original: str, error: str, prior_attempts: list[str]) -> str:
    history = ""
    if prior_attempts:
        history = "\n\nPrior attempts that lake build rejected:\n"
        for i, attempt in enumerate(prior_attempts, 1):
            history += f"\n--- attempt {i} ---\n```lean\n{attempt}\n```\n"
    failure_prefix = load_prior_failure_signal()
    return f"""{failure_prefix}You proposed this Lean 4 theorem:

```lean
{original}
```

`lake build` rejected it with the following error:

```
{error[:2000]}
```

{history}

Revise the theorem signature and proof so that:
  1. All quantities resolve to existing declarations in the current Lean spine
  2. The orientation is provable (e.g. use domain-specific positive-part /
     norm / reserve wrappers if signed quantities are involved; use
     le_trans / lt_of_le_of_lt for transitivity)
  3. The theorem name and domain target are preserved. Do NOT replace this
     with a generic Nat/Real/example lemma.
  4. The proof body is auditable. Do NOT use `sorry`, `admit`, `axiom`,
     or `native_decide`; the verifier rejects them.

Return ONLY the revised Lean code in a single ```lean fenced block."""


def load_decl_index() -> dict:
    """Stage 1 dependency: decl index built by lean_decl_index.py."""
    import lean_decl_index as ldi
    print("  rebuilding decl index (stage 1 dependency)...")
    idx = ldi.build_index(ldi.LEAN_DIR)
    ldi.INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
    ldi.INDEX_PATH.write_text(json.dumps(idx, indent=2))
    return idx


def stage1_typed_filter(nomination: str, decl_index: dict) -> dict:
    import lean_decl_index as ldi
    return ldi.check_nomination(nomination, decl_index)


def stage1_error_message(type_check: dict) -> str:
    """Human-readable typed-filter failure for the revision model/log."""
    parts: list[str] = []
    unresolved = type_check.get("unresolved", [])
    if unresolved:
        parts.append(
            "These identifiers do not resolve to declarations in the spine: "
            + ", ".join(unresolved)
            + ". Either find the actual declaration name or wrap them in "
              "positivePart / norm / abs as appropriate."
        )
    shadowed = type_check.get("shadowed_globals", [])
    if shadowed:
        parts.append(
            "These theorem binders shadow existing spine declarations: "
            + ", ".join(shadowed)
            + ". Rename local binders or use the existing declaration; do not "
              "make a theorem pass by rebinding a decision-critical global name as "
              "an arbitrary parameter."
        )
    if not parts:
        parts.append("Pre-build type filter rejected the nomination.")
    return " ".join(parts)


def run_closed_loop(nomination: str, max_revisions: int,
                    dry_run: bool = False,
                    decl_index: dict | None = None) -> dict:
    """Verify-or-falsify loop for a single nomination.

    Pipeline per attempt: stage 1 typed filter → write_and_build → on fail
    revise via Gemini with error + unresolved-identifier feedback → repeat.
    """
    name = extract_theorem_name(nomination) or "anon"
    slug = f"closed_loop_{name}"
    history: list[dict] = []
    current = nomination
    prior_attempts: list[str] = []

    for attempt in range(max_revisions + 1):
        if not has_theorem_or_lemma(current):
            history.append({
                "attempt": attempt,
                "lean_src": current,
                "stage0_decl_filter": "FAIL",
                "reason": "no theorem/lemma declaration in nomination",
                "compiled": False,
            })
            break
        if re.search(r"\?[A-Za-z_][A-Za-z0-9_]*", current):
            history.append({
                "attempt": attempt,
                "lean_src": current,
                "stage0_decl_filter": "FAIL",
                "reason": "placeholder metavariable marker present",
                "compiled": False,
            })
            break
        semantic_check = semantic_revision_check(nomination, current)
        if not semantic_check["valid"]:
            history.append({
                "attempt": attempt,
                "lean_src": current,
                "stage0_semantic_filter": "FAIL",
                "reason": semantic_check["reason"],
                "compiled": False,
            })
            if attempt >= max_revisions:
                break
            prior_attempts.append(current)
            prompt = revise_prompt(nomination, semantic_check["reason"],
                                    prior_attempts[:-1])
            revised = call_gemini(prompt)
            new_blocks = extract_lean_blocks(revised)
            if not new_blocks:
                break
            current = new_blocks[0]
            continue
        # Stage 1: typed nomination filter
        type_check = (stage1_typed_filter(current, decl_index)
                      if decl_index else {"valid": True, "unresolved": []})
        if not type_check["valid"]:
            history.append({
                "attempt": attempt,
                "lean_src": current,
                "stage1_filter": "FAIL",
                "unresolved_idents": type_check["unresolved"],
                "shadowed_globals": type_check.get("shadowed_globals", []),
                "compiled": False,
            })
            # Skip lake build — go straight to revision with type-error feedback
            if attempt >= max_revisions:
                break
            prior_attempts.append(current)
            error_msg = stage1_error_message(type_check)
            prompt = revise_prompt(current, error_msg, prior_attempts[:-1])
            revised = call_gemini(prompt)
            new_blocks = extract_lean_blocks(revised)
            if not new_blocks:
                break
            current = new_blocks[0]
            continue

        # Stage 3: lake build
        result = write_and_build(current, slug, dry_run=dry_run)
        history.append({
            "attempt": attempt,
            "lean_src": current,
            "stage1_filter": "PASS",
            "compiled": result["compiled"],
            "raw_compiled": result.get("raw_compiled"),
            "axiom_audit_passed": result.get("axiom_audit_passed"),
            "exit_code": result.get("exit_code"),
            "stderr_tail": (result.get("stderr") or "")[-1500:],
        })
        if result["compiled"]:
            verdict = "DRY_RUN_ACCEPTED" if dry_run else "VERIFIED"
            return {"name": name, "verdict": verdict,
                    "attempts": attempt + 1, "history": history,
                    "final": current}
        if attempt >= max_revisions:
            break
        prior_attempts.append(current)
        prompt = revise_prompt(current, result.get("stderr", ""),
                                prior_attempts[:-1])
        revised = call_gemini(prompt)
        new_blocks = extract_lean_blocks(revised)
        if not new_blocks:
            history.append({"attempt": attempt + 1, "revision_failed":
                             "no Lean block in LLM revision"})
            break
        current = new_blocks[0]
    return {"name": name, "verdict": "UNVERIFIABLE",
            "attempts": len(history), "history": history,
            "final": current}


def stage4_learning_summary(log_path: Path) -> dict:
    """Stage 4: aggregate the closed-loop log into a learning signal.

    Tracks: verified-rate, common type-filter rejections, common lake errors.
    Outputs guidance for the next pipeline iteration's prompt.
    """
    if not log_path.exists():
        return {}
    rows = [json.loads(l) for l in log_path.read_text().splitlines() if l.strip()]
    rows = [r for r in rows if not r.get("run_meta", {}).get("dry_run")]
    if not rows:
        return {}
    verified = [r for r in rows if r["verdict"] == "VERIFIED"]
    unverified = [r for r in rows if r["verdict"] == "UNVERIFIABLE"]
    # Aggregate common unresolved-identifier patterns
    common_unresolved: dict[str, int] = {}
    common_lake_errors: dict[str, int] = {}
    common_semantic_errors: dict[str, int] = {}
    for r in unverified:
        for h in r.get("history", []):
            for u in h.get("unresolved_idents", []):
                common_unresolved[u] = common_unresolved.get(u, 0) + 1
            for u in h.get("shadowed_globals", []):
                key = f"{u} (shadowed global)"
                common_unresolved[key] = common_unresolved.get(key, 0) + 1
            if h.get("stage0_semantic_filter") == "FAIL":
                reason = h.get("reason", "")
                if reason:
                    common_semantic_errors[reason] = (
                        common_semantic_errors.get(reason, 0) + 1)
            err = h.get("stderr_tail", "")
            if err:
                # Group by first error line (rough categorization)
                first_line = err.split("\n")[0][:80] if err else ""
                if first_line:
                    common_lake_errors[first_line] = (
                        common_lake_errors.get(first_line, 0) + 1)
    return {
        "n_total": len(rows),
        "n_verified": len(verified),
        "n_unverifiable": len(unverified),
        "verification_rate": len(verified) / max(len(rows), 1),
        "top_unresolved_idents": sorted(common_unresolved.items(),
                                          key=lambda x: -x[1])[:10],
        "top_lake_errors": sorted(common_lake_errors.items(),
                                    key=lambda x: -x[1])[:5],
        "top_semantic_errors": sorted(common_semantic_errors.items(),
                                       key=lambda x: -x[1])[:5],
    }


def load_nominations_from_file(path: Path) -> list[str]:
    """Load Lean nominations from markdown fences or JSONL proof sketches.

    JSONL producers may also emit graph-search rows that are intentionally not
    Lean nominations. Those rows must opt in with closed_loop_ready=true before
    this loop treats their proof_sketch as theorem text. This prevents graph
    quantity names from being used as pseudo-Lean declarations.
    """
    text = path.read_text()
    blocks = extract_lean_blocks(text)
    if blocks:
        return blocks
    nominations: list[str] = []
    for line in text.splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if row.get("candidate_status") == "search_candidate_only":
            continue
        if (row.get("candidate_kind") == "untyped_graph_orientation"
                and not row.get("closed_loop_ready")):
            continue
        sketch = row.get("proof_sketch")
        if isinstance(sketch, str) and sketch.strip():
            nominations.append(sketch.strip())
    return nominations


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-revisions", type=int, default=3,
                    help="maximum LLM revision attempts per nomination")
    ap.add_argument("--dry-run", action="store_true",
                    help="don't actually run lake; assume all builds succeed")
    ap.add_argument("--out", type=Path,
                    default=DEFAULT_CLOSED_LOOP_LOG)
    ap.add_argument("--nominations-file", type=Path,
                    help="skip llm_graph_analyst; read Lean blocks from this file")
    args = ap.parse_args()

    decl_index = load_decl_index()
    print(f"  decl index: {decl_index['n_declarations']} declarations across "
          f"{decl_index['n_files']} files (stage 1 ready)")

    if args.nominations_file:
        nominations = load_nominations_from_file(args.nominations_file)
        print(f"loaded {len(nominations)} nominations from {args.nominations_file}")
    else:
        nominations = get_initial_nominations()

    if not nominations:
        print("no nominations; bailing")
        return 1

    print(f"\n[step 2] running closed loop on {len(nominations)} nominations "
          f"({args.max_revisions} max revisions each)...")
    results = []
    for i, nom in enumerate(nominations, 1):
        name = extract_theorem_name(nom) or f"anon_{i}"
        print(f"\n--- nomination {i}/{len(nominations)}: {name} ---")
        result = run_closed_loop(nom, args.max_revisions,
                                  dry_run=args.dry_run,
                                  decl_index=decl_index)
        verdict = result["verdict"]
        print(f"  {verdict} after {result['attempts']} attempt(s)")
        if verdict == "UNVERIFIABLE":
            last_hist = result["history"][-1] if result["history"] else {}
            last_err = (
                (last_hist.get("stderr_tail") or last_hist.get("reason") or "")
                [-300:]
            )
            print(f"  last error tail: {last_err}")
        results.append(result)

    if args.dry_run and args.out == DEFAULT_CLOSED_LOOP_LOG:
        args.out = args.out.with_name("closed_loop_log.dry_run.jsonl")

    # Write log
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w") as f:
        for r in results:
            r.setdefault("run_meta", {})
            r["run_meta"].update({
                "timestamp_utc": datetime.now(UTC).isoformat(timespec="seconds"),
                "decl_index_fingerprint": decl_index.get("source_fingerprint"),
                "decl_index_n_declarations": decl_index.get("n_declarations"),
                "nominations_file": str(args.nominations_file) if args.nominations_file else None,
                "nominations_file_sha256": (
                    file_sha256(args.nominations_file)
                    if args.nominations_file and args.nominations_file.exists()
                    else None
                ),
                "dry_run": args.dry_run,
            })
            f.write(json.dumps(r) + "\n")

    # Summary
    verified = [r for r in results if r["verdict"] == "VERIFIED"]
    dry_accepted = [r for r in results if r["verdict"] == "DRY_RUN_ACCEPTED"]
    unverified = [r for r in results if r["verdict"] == "UNVERIFIABLE"]
    print(f"\n=== summary ===")
    print(f"  verified: {len(verified)} / {len(results)}")
    if dry_accepted:
        print(f"  dry-run accepted: {len(dry_accepted)} / {len(results)}")
    print(f"  unverifiable: {len(unverified)}")
    print(f"  log: {args.out}")
    if verified:
        print(f"\n  VERIFIED theorems:")
        for r in verified:
            print(f"    - {r['name']} (in {r['attempts']} attempts)")
    if dry_accepted:
        print(f"\n  DRY-RUN ACCEPTED (typed filter only; not proof progress):")
        for r in dry_accepted:
            print(f"    - {r['name']} (in {r['attempts']} attempts)")
    if unverified:
        if args.dry_run:
            print(f"\n  UNVERIFIABLE (dry-run smoke; excluded from Stage 4):")
        else:
            print(f"\n  UNVERIFIABLE (training data for next pipeline iter):")
        for r in unverified:
            print(f"    - {r['name']} (after {r['attempts']} revisions)")

    # Stage 4: learning summary
    learning = stage4_learning_summary(args.out)
    if learning:
        print(f"\n=== stage 4 learning signal ===")
        print(f"  verification rate: {learning['verification_rate']:.2%}")
        if learning["top_unresolved_idents"]:
            print(f"  top unresolved identifiers across all attempts:")
            for ident, count in learning["top_unresolved_idents"]:
                print(f"    {count:>3}x  {ident}")
        if learning["top_lake_errors"]:
            print(f"  top lake-build error categories:")
            for err, count in learning["top_lake_errors"]:
                print(f"    {count:>3}x  {err[:75]}")
        if learning.get("top_semantic_errors"):
            print(f"  top semantic target-drift errors:")
            for err, count in learning["top_semantic_errors"]:
                print(f"    {count:>3}x  {err[:100]}")
        # Persist learning signal next to log
        learning_path = args.out.with_suffix(".learning.json")
        learning_path.write_text(json.dumps(learning, indent=2))
        print(f"  learning signal: {learning_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
