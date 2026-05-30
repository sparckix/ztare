#!/usr/bin/env python3
"""Batched candidate generator — K candidates in parallel, take any that pass.

Standard typed-endpoint flow: 1 candidate → fail → revise → retry. Wall-clock
per attempt is API call (~5-30s) + lake build (~1-2s) + revision (~5-30s).

Batched flow: ask LLM for K independent candidates in one prompt → lake-build
all in parallel → keep any that pass. Wall-clock per success drops 3-5x
because:
  - One LLM call instead of K serial calls
  - Lake builds parallelize trivially (one process per candidate)
  - First success short-circuits the rest

# Reuse

  - `scripts/public/lean/typed_endpoint_pack.py` for context-pack construction
  - `scripts/public/lean/lean_fast_compile.py::compile_lean_fast` for fast lake invocation
  - Same Stage 4 failure-category logging

# Substrate-agnostic

The K-parallel pattern works for any (target, field, patch_class) triple
the typed-endpoint pack accepts. Default K=4; CLI overridable.

# Honest scope

  - Trivially-parallel lake builds assume each candidate file is independent
    and doesn't depend on others' build artifacts. The fast-compile path
    (`lake env lean`) preserves this.
  - Diverse candidates require the LLM to produce VARIETY, not just
    different framings of the same idea. Prompted with explicit
    "produce K MAXIMALLY DIFFERENT candidates" instruction.

Usage:
    python scripts/public/lean/batched_candidate_generator.py \\
        --target TrackBProfileLipschitzClayObligation \\
        --field continuation \\
        --patch-class instance_with_evidence \\
        --k 4
"""
from __future__ import annotations

import argparse
import concurrent.futures
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))


BATCHED_SUFFIX_PROMPT = """

# Important: produce {k} MAXIMALLY DIFFERENT candidates

The apparatus runs all candidates in parallel through lake-build. Diversity
across candidates is what gives this approach its leverage. So:

  - Each candidate should explore a DIFFERENT structural approach
    (e.g. one transitivity-style, one direct-construction, one falsifier-style)
  - Vary the choice of intermediate quantities / hypotheses
  - Vary the proof strategy (`exact`, `apply`, `refine`, ...)
  - Prefer falsifier-first candidates that rule out a named escape lane before
    presenting a positive bridge.
  - Prefer source constructors and projection lemmas already listed in the
    context pack. Do not create free assumptions that are equivalent to the
    target endpoint.

Output exactly {k} Lean blocks, each in its own ```lean fenced block,
separated by blank lines. Do NOT output prose between them. Do NOT add
"# CANNOT PATCH" — even if uncertain, attempt {k} different angles.

Anti-tautology rule: do not prove a bridge by reading the requested endpoint
field from the target record. If the target is `T.f`, a candidate whose proof
uses `R.f`, `rw [R.f]`, or `simpa using R.f` is self-referential and will be
discarded. Use independent source constructors, prior receipts, or explicit
missing-primitive assumptions only.

Import discipline: use Lean module imports like `import ZtareProofs.foo`.
Do not use filesystem-style imports such as `import ztare_proofs.ZtareProofs.foo`."""


SOURCE_WITNESS_PROMPT = """

# Source-witness mode

This run is searching for an upstream source witness, not an accessor theorem.
Do not take the target structure itself as an argument. Construct the requested
field from earlier source objects, handoffs, receipts, primitive lemmas, or a
named missing primitive. A candidate whose signature contains `(R : {target})`
or equivalent target-record input will be discarded."""


# 2026-05-06 PM: was hardcoded gemini-3-pro-preview; switched to
# LLMRuntime + pick_default_model_id_for_scripts. Operator with only
# Anthropic / OpenAI keys no longer fails. Override via LLM_DISPATCH_PREF.
from src.ztare.common.llm_runtime import (
    LLMRuntime,
    pick_default_model_id_for_scripts,
    resolve_model_id,
)
from src.ztare.formal.lean_candidate_hygiene import (
    candidate_degeneracy_reason,
    extract_lean_blocks,
    normalize_candidate_source,
)
from src.ztare.supervisor.llm_budget_guard import (
    LLMBudgetDenied,
    LLMBudgetSession,
    estimate_llm_call_cost,
    print_budget_report,
    write_pending_operator_gate,
)

_RUNTIME = LLMRuntime()


def call_gemini(
    prompt: str,
    max_tokens: int = 12000,
    *,
    budget_session: LLMBudgetSession | None = None,
    request_label: str = "batched_candidate_generator",
    model_id: str | None = None,
    allow_model_fallback: bool = False,
) -> str:
    """Provider-agnostic LLM call (legacy name preserved for back-compat).

    Routes to whichever provider is configured (claude/gpt/gemini in
    that default preference order). Returns text or ``ERROR: ...``
    on failure.
    """
    model_id = model_id or pick_default_model_id_for_scripts(
        preference_order=("google", "openai", "anthropic")
    )
    if model_id is None:
        return (
            "ERROR: no LLM provider available — set ANTHROPIC_API_KEY, "
            "OPENAI_API_KEY, or GEMINI_API_KEY"
        )
    try:
        estimate = None
        if budget_session is not None:
            estimate = budget_session.preflight(
                prompt=prompt,
                model_name=model_id,
                max_output_tokens=max_tokens,
                label=request_label,
            )
        response = _RUNTIME.call_text(
            prompt,
            model_id=model_id,
            fallback_model_ids=None if allow_model_fallback else (),
            max_tokens=max_tokens,
            request_label=request_label,
        )
        if budget_session is not None and estimate is not None:
            budget_session.record_response(
                usage=response.usage,
                fallback_estimate=estimate,
                label=request_label,
            )
        return response.text or "(empty)"
    except LLMBudgetDenied as exc:
        return f"ERROR: budget denied: {exc}"
    except Exception as exc:
        return f"ERROR: {type(exc).__name__}: {exc}"


def resolve_script_model(model: str | None) -> str | None:
    """Resolve a CLI model alias or pick the Google-first default."""
    if model:
        try:
            return resolve_model_id(model)
        except ValueError:
            return model
    return pick_default_model_id_for_scripts(
        preference_order=("google", "openai", "anthropic")
    )


def slug_fragment(text: str, *, max_len: int = 24) -> str:
    """Filesystem/Lean-module-safe fragment for generated artifacts."""
    cleaned = re.sub(r"[^A-Za-z0-9_]", "_", text).strip("_").lower()
    return cleaned[:max_len] or "run"


def lake_build_parallel(candidates: list[tuple[int, str, str]],
                         max_workers: int = 4) -> list[dict]:
    """Run lake-build on each candidate in parallel; return result list."""
    from lean_fast_compile import compile_lean_fast_combined_output
    sys.path.insert(0, str(REPO / "src"))
    from src.ztare.gates.lean_proof_gate import write_lean_target

    proofs_root = REPO / "ztare_proofs"

    def _run(item):
        idx, slug, src = item
        try:
            src = normalize_candidate_source(src)
            target = write_lean_target(src, slug, proofs_root)
            result = compile_lean_fast_combined_output(target, proofs_root)
            return {
                "idx": idx, "slug": slug,
                "compiled": result.get("compiled", False),
                "exit_code": result.get("exit_code"),
                "duration_s": result.get("duration_s"),
                "stderr_tail": (result.get("stderr") or "")[-800:],
                "lean_path": str(target),
                "lean_src": src,
            }
        except Exception as e:
            return {"idx": idx, "slug": slug, "compiled": False,
                    "error": f"{type(e).__name__}: {e}", "lean_src": src}

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as pool:
        results = list(pool.map(_run, candidates))
    return results


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", required=True)
    ap.add_argument("--field", required=True)
    ap.add_argument("--patch-class", default="instance_with_evidence",
                    choices=["transitivity_adapter", "branch_wise_falsifier",
                             "source_provenance_bridge", "instance_with_evidence"])
    ap.add_argument("--k", type=int, default=4,
                    help="number of parallel candidates")
    ap.add_argument("--max-workers", type=int, default=4)
    ap.add_argument("--model",
                    help="model alias/id for the paid generation call; e.g. gemini-pro")
    ap.add_argument("--allow-model-fallback", action="store_true",
                    help="allow provider fallback if the requested/default model fails")
    ap.add_argument("--dry-run", action="store_true",
                    help="build and write the batched prompt, but do not call the LLM")
    ap.add_argument("--budget-estimate-only", action="store_true",
                    help="print/write the paid-call estimate, then exit before LLM dispatch")
    ap.add_argument("--allow-paid", action="store_true",
                    help="authorize paid LLM dispatch after reviewing the estimate")
    ap.add_argument("--max-total-cost-usd", type=float,
                    help="hard per-run spend cap for LLM calls")
    ap.add_argument("--role-id", default="research_director",
                    help="role budget to enforce via spend_tracker")
    ap.add_argument("--session-id",
                    default=f"batched-candidate-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
                    help="spend-tracker session id")
    ap.add_argument("--write-approval-gate", action="store_true",
                    help="write an org/gates/pending budget approval JSON and exit")
    ap.add_argument("--allow-target-field-reference", action="store_true",
                    help="count candidates even if their proof body reads the requested target field")
    ap.add_argument("--require-source-witness", action="store_true",
                    help="demote candidates that take the target structure as an input")
    ap.add_argument("--out-dir", type=Path,
                    default=REPO / "analytics" / "public" / "queries" / "batched_runs")
    args = ap.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)

    print(f"=== batched candidate generator (K={args.k}) ===")
    print(f"  target: {args.target}")
    print(f"  field:  {args.field}")
    print(f"  class:  {args.patch_class}")

    # Reuse typed_endpoint_pack to build the base prompt
    from typed_endpoint_pack import (
        load_workmap_target, resolve_field, find_type_constructors,
        find_type_producers, find_theorems_using_field, load_decl_index,
        build_prompt,
        load_prior_failures, PatchClass,
    )
    target_obj = load_workmap_target(args.target)
    if not target_obj:
        print("  target not in workmap"); return 1
    field_info = resolve_field(target_obj, args.field)
    if not field_info:
        print("  field not in target"); return 1
    decl_index = load_decl_index()
    target_name = target_obj.get("name") or target_obj.get("structure") or args.target
    target_constructors = find_type_constructors(target_name, decl_index)
    target_producers = find_type_producers(target_name, top_n=10)
    constructors = find_type_constructors(field_info["type_head"], decl_index)
    type_producers = find_type_producers(field_info["type_head"], top_n=15)
    nearby = find_theorems_using_field(args.field, field_info["type_head"],
                                       top_n=10)
    prior_failures = load_prior_failures(args.target, args.field, args.patch_class)
    patch_class = PatchClass(args.patch_class)
    base_prompt = build_prompt(target_obj, field_info, patch_class,
                               target_constructors, target_producers,
                               constructors, type_producers, nearby,
                               prior_failures)
    full_prompt = base_prompt + BATCHED_SUFFIX_PROMPT.format(k=args.k)
    if args.require_source_witness:
        full_prompt += SOURCE_WITNESS_PROMPT.format(target=args.target)

    print(f"  prompt size: {len(full_prompt)} chars")
    prompt_path = args.out_dir / f"{args.target}_{args.field}_{args.patch_class}_prompt.txt"
    prompt_path.write_text(full_prompt)
    print(f"  prompt: {prompt_path}")
    model_id = resolve_script_model(args.model)
    if model_id is None:
        print("  no configured LLM provider found")
        return 2
    estimate = estimate_llm_call_cost(
        prompt=full_prompt,
        model_name=model_id,
        max_output_tokens=12000,
        label="batched_candidate_generator",
    )
    print_budget_report(estimate, max_total_cost_usd=args.max_total_cost_usd)
    budget_path = args.out_dir / f"{args.target}_{args.field}_{args.patch_class}_budget.json"
    budget_path.write_text(json.dumps({
        "target": args.target,
        "field": args.field,
        "patch_class": args.patch_class,
        "k": args.k,
        "estimate": {
            "model_name": estimate.model_name,
            "input_tokens_est": estimate.input_tokens,
            "max_output_tokens": estimate.output_tokens,
            "estimated_cost_usd": estimate.estimated_cost_usd,
        },
        "max_total_cost_usd": args.max_total_cost_usd,
        "allow_paid": args.allow_paid,
        "session_id": args.session_id,
        "requested_model": args.model,
        "effective_model_for_estimate": model_id,
        "allow_model_fallback": args.allow_model_fallback,
        "require_source_witness": args.require_source_witness,
    }, indent=2), encoding="utf-8")
    print(f"  budget: {budget_path}")
    if args.write_approval_gate:
        gate = write_pending_operator_gate(
            estimate=estimate,
            action="batched_candidate_generator",
            reason=f"{args.target}::{args.field} ({args.patch_class}, k={args.k})",
            max_total_cost_usd=args.max_total_cost_usd,
        )
        print(f"  wrote approval gate: {gate.relative_to(REPO)}")
        return 0
    if args.dry_run:
        print("  [dry-run] skipping LLM call + lake builds")
        return 0
    if args.budget_estimate_only:
        print("  [budget-estimate-only] skipping LLM call + lake builds")
        return 0
    if not args.allow_paid:
        print("  paid LLM dispatch blocked; rerun with --allow-paid after reviewing budget")
        return 2
    print(f"\n[step 1] requesting {args.k} candidates from {model_id} in one call...")
    budget_session = LLMBudgetSession(
        allow_paid=args.allow_paid,
        max_total_cost_usd=args.max_total_cost_usd,
        role_id=args.role_id,
        session_id=args.session_id,
        action="batched_candidate_generator",
    )
    response = call_gemini(
        full_prompt,
        budget_session=budget_session,
        request_label=f"batched_{args.target}_{args.field}",
        model_id=model_id,
        allow_model_fallback=args.allow_model_fallback,
    )
    print(f"  response: {len(response)} chars")
    response_path = args.out_dir / f"{args.target}_{args.field}_{args.patch_class}_response.txt"
    response_path.write_text(response, encoding="utf-8")
    print(f"  response_text: {response_path}")

    blocks = extract_lean_blocks(response)
    print(f"  parsed {len(blocks)} Lean blocks (asked for {args.k})")
    if not blocks:
        print("  no Lean blocks; aborting")
        return 1

    # Build (idx, slug, src) for parallel lake-build
    target_safe = slug_fragment(args.target, max_len=25)
    artifact_label = slug_fragment(
        f"{args.session_id}_{estimate.model_name}",
        max_len=24,
    )
    candidates = [(i,
                    f"batched_{target_safe}_{slug_fragment(args.field, max_len=15)}_"
                    f"{slug_fragment(args.patch_class, max_len=10)}_{artifact_label}_{i}",
                    src)
                   for i, src in enumerate(blocks)]

    print(f"\n[step 2] lake-build {len(candidates)} in parallel "
          f"(max_workers={args.max_workers})...")
    results = lake_build_parallel(candidates, max_workers=args.max_workers)
    n_compiled = sum(1 for r in results if r.get("compiled"))
    print(f"  {n_compiled}/{len(results)} compiled clean")

    # Anti-degeneracy filter.  A candidate must contain a declaration and
    # must not merely re-export the target field it was asked to bridge.
    real_results = []
    for r in results:
        src = r.get("lean_src", "")
        reason = candidate_degeneracy_reason(
            src,
            target=args.target,
            field=args.field,
            allow_target_field_reference=args.allow_target_field_reference,
            require_source_witness=args.require_source_witness,
        )
        if r.get("compiled") and reason is not None:
            r["compiled"] = False
            r["degenerate"] = True
            r["degenerate_reason"] = reason
        real_results.append(r)
    n_verified = sum(1 for r in real_results if r.get("compiled"))
    print(f"  after anti-degen: {n_verified}/{len(results)} VERIFIED")

    out_path = args.out_dir / f"{args.target}_{args.field}_{args.patch_class}.json"
    out_path.write_text(json.dumps({
        "ts": datetime.now(timezone.utc).isoformat(),
        "target": args.target, "field": args.field,
        "patch_class": args.patch_class, "k": args.k,
        "n_blocks": len(blocks),
        "n_verified": n_verified,
        "results": real_results,
    }, indent=2, default=str))
    print(f"  log: {out_path}")

    if n_verified > 0:
        print(f"\n=== FINAL: {n_verified} VERIFIED candidate(s) found in single batch ===")
        for r in real_results:
            if r.get("compiled"):
                print(f"  ✓ idx={r['idx']} → {r['lean_path']}")
        return 0
    else:
        print(f"\n=== FINAL: 0 verified out of {len(results)} ===")
        # Show the first failure error for diagnostic
        first_fail = next((r for r in real_results if not r.get("compiled")), None)
        if first_fail:
            print(f"  example error tail: {first_fail.get('stderr_tail', '')[-400:]}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
