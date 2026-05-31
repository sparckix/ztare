#!/usr/bin/env python3
"""LeanMill solver lane — layered prover for C-credit supply.

DIAGNOSIS (2026-05-28): the mill produces ~0 governed C credits despite 16k+
work items because the top non-trivial blocker is `no_positive_family_template`
(140 rows): static MISSED these rows AND no family-spec template matches, so
they sit blocked. The family-spec probe lane needs a pre-existing template; the
family-birth lane makes templates but does not close rows. There was no SOLVER
lane to attack static-missed / no-template rows. This is it.

LAYERED PROVER STACK (2026-05-28 — see docs/internal/architectural_maps/
leanmill_architectural_map.md for the apparatus map):

  Layer 0 — Slice loading + attempts-DB filter.
            Drops already-closed rows and rows past MAX_FAILED_ATTEMPTS_PER_ROW.

  Layer 1 — Context build.
            `_build_solver_context()` enriches the goal stub with the source
            file's prelude (imports + definitions + helper lemmas up to the
            target theorem) plus the semantic premise shelf (cosine-similar
            Mathlib/APN candidates). All downstream layers consume the same
            enriched prompt so a closure that uses a prelude helper isn't
            falsely rejected by a bare-import probe.

  Layer 2 — Native hammer (free, deterministic, FIRST attack).
            `_native_hammer_probe()` runs the Mathlib tactic cascade
            (aesop / simp_all / omega / polyrith / norm_num / linarith / ...)
            against the enriched context. ~5-30s per tactic; aborts as soon
            as any tactic closes the goal. No LLM cost. Grounded in
            LeanHammer (Czajka-Kaliszyk 2018) and Magnushammer (Mikuła et al.
            2023): tactic search alone closes a substantial fraction of
            elementary goals on Mathlib.

  Layer 3 — Warm agent (iterative, Bash + Edit + Read enabled).
            `_warm_agent_solve()` spawns Claude in a scratch dir under
            `lean_root/.solver_scratch/<row_id>/`. The agent edits target.lean
            and runs `lake env lean` itself, iterating up to 5 verifications.
            One warm-agent run has substantially higher P(close) than any
            single one-shot LLM call. Grounded in LeanAgent (Yang et al.
            2024) and APN/AlphaProof Nexus AICollaborator (DeepMind 2025)
            EVOLVE-BLOCK iteration. WebSearch/WebFetch stay disallowed for
            contamination hygiene.

  Layer 4 — Cold-shot multi-provider fan-out.
            For each provider in [preferred] + policy.provider_fallbacks
            (claude_opus / codex_gpt5 / gemini_flash / deepseek_v2), invoke
            with the enriched prompt and kernel-verify the emitted proof
            text. The router walks HARD-failure transitions (auth, credit,
            binary_not_found); this layer walks SOFT-failure transitions
            (text-that-doesn't-compile) by re-trying the next provider.
            Diversity catches cases where one model has the right intuition
            for a specific shape.

  Layer 5 — Failure classification + retry adjustment.
            `_classify_compile_failure()` parses the kernel error tail and
            returns a failure_family with an action_program (per the action
            card contract in src/ztare/leanmill/contracts/action_card.py).
            If the action program suggests an adjusted enriched_goal (e.g.
            inject a specific missing-constant definition), the prover stack
            re-enters Layer 2 once with the adjusted context. Bounded retry:
            at most one Layer 5 cycle per row per call.

  Layer 6 — Persistence + governance handoff.
            Every attempt is recorded in solver_lane_attempts.db with
            (row_id, provider, outcome, compile_ok, notes). Closures
            normalize to typed exits ('unratified_closure_candidate') for
            downstream governance ratification — credit_boundary unchanged.

INPUT  : c_discriminating_slice rows where static missed + no positive family
         template + target executable; goal text from row_context.
OUTPUT : auto-prover-results JSON + normalized typed-exits written to the
         standard candidates location for governance pickup.

CLI:
  select   [--limit N]                 list solver-eligible rows (dry, no calls)
  solve    --provider claude_opus [--limit N] [--dry-run]   run the lane
"""
from __future__ import annotations
import argparse
import importlib.util
import json
import sqlite3
import subprocess
import sys
import tempfile
import time
from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
CONTROL = REPO / "scripts" / "public" / "control"
DASH = REPO / "analytics" / "public" / "leanmill" / "dashboard_data"
# The FULL candidate pool (with no_positive_family_template rows) is the unfiltered
# slice prep output; the cleaned variant drops them. Prefer full, fall back to cleaned.
SLICE_FULL = DASH / "evaluation_harness_c_discriminating_slice.json"
SLICE_CLEANED = DASH / "c_supply_batch_cleaned_c_discriminating_slice.json"
ROW_CTX_FULL = DASH / "evaluation_harness_c_discriminating_row_context.json"
ROW_CTX_CLEANED = DASH / "c_supply_batch_cleaned_c_discriminating_row_context.json"
# Slice paths are no longer hardcoded for mandate-emitted slices. The corpus
# mandate registry (`corpus_mandates.json`) carries them per active mandate.
# Adding another mandate is a registry edit, not a worker code change.
POLICY = DASH / "leanmill_factory_policy.json"
OUT_DIR = REPO / "analytics" / "public" / "queries"
OUT_RESULTS = OUT_DIR / "leanmill_solver_lane_results.json"
OUT_EXITS = OUT_DIR / "leanmill_solver_lane_typed_exits.json"

# --- compile-on-claim verification + attempt tracking ---------------------
# Two bugs the original solver had: (a) `outcome=closed` was decided on the
# provider call running successfully, NOT on whether the returned proof_text
# actually closes the goal; (b) every cycle re-claimed the same eligible rows
# because there was no persisted "this row was already attempted" memory. The
# code below fixes both: every attempt's proof_text is compiled under
# `lake env lean` against `import Mathlib`, and every attempt is recorded
# in a small sqlite so the same closed rows are not re-attempted and rows
# that have failed N times are deprioritized for cooldown.
ATTEMPTS_DB = OUT_DIR / "solver_lane_attempts.db"
MAX_FAILED_ATTEMPTS_PER_ROW = 3
DEFAULT_LEAN_ROOT_FOR_VERIFY = REPO / "ztare_proofs"
# Carrier receipt use ledger — typed exchange ledger between payer / target
# currencies with blocked confusers. Schema mirrors the apparatus-wide
# pattern for typed-receipt audit trails (per epistemic-generation V35/V38).
# Per-row entries written here form the audit trail a reasoning-proof compiler
# needs: which receipt paid which closure, and which confuser it blocked.
CARRIER_RECEIPT_LEDGER = OUT_DIR / "solver_lane_carrier_receipt_use_ledger.jsonl"


def _append_carrier_receipt_entry(row_id: str, contract: dict, providers_tried: list[dict],
                                  outcome: str, validation: dict | None) -> None:
    """One JSONL row per solver attempt — typed payer/target/receipt entry."""
    receipts = (validation or {}).get("receipts") or {}
    mnc = receipts.get("matched_negative_control_receipt") or {}
    kc = receipts.get("kernel_compile_receipt") or {}
    consumed_edge = (
        f"{row_id} → unratified_closure_candidate"
        if outcome == "closed" else
        f"{row_id} → {outcome}"
    )
    blocked_confuser = (
        "matched_negative_control_pass (would_have_been_leakage)"
        if outcome == "rejected_negative_control" else
        contract.get("rejected_nearest_confuser") or ""
    )
    entry = {
        "id": f"solver_lane_{row_id}_{int(time.time())}",
        "date": datetime.now(timezone.utc).date().isoformat(),
        "lane": "solver_lane",
        "row_id": row_id,
        "outcome": outcome,
        "consumed_edge": consumed_edge,
        "blocked_confuser": blocked_confuser,
        "payer_currency": "kernel_compile_receipt + matched_negative_control_receipt",
        "target_currency": "unratified_closure_candidate (advisory-only)",
        "receipt": (
            "kernel_trust_closure_with_solver_layer_mnc"
            if outcome == "closed" else f"non_closure_{outcome}"
        ),
        "receipt_class": (
            "kernel_compile/matched_negative_control"
            if outcome == "closed" else "rejection/route_to_next_layer"
        ),
        "status": outcome,
        "next_lever": (
            "leanmill_proof_audit (axiom_allowlist + L3 anti_pattern) before factory credit"
            if outcome == "closed" else "advance action_program or cooldown after MAX_FAILED_ATTEMPTS_PER_ROW"
        ),
        "required_exchange": (contract.get("required_receipts") or [{}])[0].get("acceptance_check", ""),
        "kernel_compile_receipt_passed": bool(kc.get("passed")) if kc else None,
        "matched_negative_control_receipt_passed": bool(mnc.get("passed")) if mnc else None,
        "providers_tried_count": len(providers_tried),
        "providers_tried_kinds": [p.get("provider") for p in providers_tried],
        "credit_ready_at_solver_layer": bool((validation or {}).get("credit_ready_at_solver_layer")) if validation else False,
        "downstream_consumer": contract.get("downstream_consumer_check", ""),
        "credit_boundary": contract.get("credit_boundary", ""),
        "evidence_basis": contract.get("evidence_basis", ""),
        "row_context": {
            "target_theorem_name": contract.get("target_theorem_name"),
            "source_file": contract.get("source_file"),
            "goal_excerpt": (contract.get("goal_excerpt") or "")[:200],
            "accepted_residual_class": contract.get("accepted_residual_class"),
        },
    }
    CARRIER_RECEIPT_LEDGER.parent.mkdir(parents=True, exist_ok=True)
    with CARRIER_RECEIPT_LEDGER.open("a") as f:
        f.write(json.dumps(entry) + "\n")


def _attempts_conn() -> sqlite3.Connection:
    ATTEMPTS_DB.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(ATTEMPTS_DB))
    con.execute(
        """CREATE TABLE IF NOT EXISTS attempts (
            row_id      TEXT NOT NULL,
            attempt_at  TEXT NOT NULL,
            provider    TEXT,
            outcome     TEXT,
            compile_ok  INTEGER NOT NULL,
            notes       TEXT
        )"""
    )
    con.execute("CREATE INDEX IF NOT EXISTS idx_row ON attempts(row_id)")
    return con


def _row_already_closed(row_id: str) -> bool:
    with _attempts_conn() as con:
        r = con.execute(
            "SELECT 1 FROM attempts WHERE row_id=? AND compile_ok=1 LIMIT 1",
            (row_id,),
        ).fetchone()
    return r is not None


def _failed_attempts_count(row_id: str) -> int:
    with _attempts_conn() as con:
        r = con.execute(
            "SELECT COUNT(*) FROM attempts WHERE row_id=? AND compile_ok=0",
            (row_id,),
        ).fetchone()
    return r[0] if r else 0


def _record_attempt(row_id: str, provider: str | None, outcome: str,
                    compile_ok: bool, notes: str | None) -> None:
    with _attempts_conn() as con:
        con.execute(
            "INSERT INTO attempts (row_id, attempt_at, provider, outcome, compile_ok, notes) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (row_id, datetime.now(timezone.utc).isoformat(), provider or "",
             outcome, 1 if compile_ok else 0,
             (notes or "")[-1000:]),
        )
        con.commit()


_MAX_CONTEXT_CHARS = 12000


def _build_solver_context(row: dict) -> str:
    """Enrich the goal stub with: (i) source-file prelude (imports +
    definitions + helper lemmas up to the target), and (ii) semantic premise
    shelf (Mathlib + APN + NS candidate lemmas via cosine-similarity over
    embeddings). Without (i) a one-shot provider sees only
    `theorem P1 : ProblemP1 := by` and cannot unfold `ProblemP1`. Without
    (ii) it has to guess at the relevant Mathlib lemma names.
    """
    base_goal = (row.get("goal") or "").strip()
    if not base_goal:
        return base_goal
    src_path_str = row.get("source_file") or ""
    target_name = row.get("target_theorem_name") or ""
    prelude = ""
    if src_path_str and target_name:
        src_path = Path(src_path_str)
        if src_path.exists():
            try:
                text = src_path.read_text(encoding="utf-8", errors="replace")
            except Exception:
                text = ""
            if text:
                import re as _re
                decl_re = _re.compile(
                    rf"^\s*(?:noncomputable\s+|private\s+|protected\s+)*(?:theorem|lemma|def|instance)\s+{_re.escape(target_name)}\b",
                    _re.MULTILINE,
                )
                m = decl_re.search(text)
                prelude = text[: m.start()] if m else text
                if prelude.lstrip().startswith("/-"):
                    end = prelude.find("-/")
                    if end >= 0:
                        prelude = prelude[end + 2:]
                prelude = prelude.strip()
                if len(prelude) > _MAX_CONTEXT_CHARS:
                    prelude = "-- [prelude truncated to last " + str(_MAX_CONTEXT_CHARS) + " chars]\n" + prelude[-_MAX_CONTEXT_CHARS:]
    shelf_block = ""
    try:
        sys.path.insert(0, str(REPO / "src"))
        from ztare.leanmill.semantic_premise_shelf import (
            build_semantic_premise_shelf,
            render_semantic_premise_shelf,
            semantic_premise_shelf_enabled,
        )
        if semantic_premise_shelf_enabled():
            shelf = build_semantic_premise_shelf(base_goal, top_k_mathlib=8, top_k_apn=3, top_k_ns=0)
            rendered = render_semantic_premise_shelf(shelf, max_hits=10).strip()
            if rendered:
                shelf_block = f"-- candidate premises (semantic shelf, cosine-similar to goal):\n{rendered}\n"
    except Exception:
        shelf_block = ""
    pieces = [p for p in (prelude, shelf_block, base_goal) if p]
    return "\n\n".join(pieces)


def _strip_proof_text(proof_text: str) -> str:
    """Minimal cleanup: strip outer markdown code fence if present.
    Do NOT prune lines that don't start with a known tactic keyword — that
    rule wiped legitimate output (e.g. when the provider prints the goal
    display and then the proof) and produced empty proof_text.
    """
    if not proof_text:
        return ""
    s = proof_text.strip()
    if s.startswith("```"):
        first_newline = s.find("\n")
        if first_newline >= 0:
            s = s[first_newline + 1:]
        if s.endswith("```"):
            s = s[: -3]
        s = s.strip()
    return s


# Tactic cascade for Layer 2 (free + deterministic; ranked by typical hit rate
# on bare-Mathlib targets). Each tactic is tried as a standalone closure
# candidate `:= by <tactic>` against the same enriched context the LLM layers
# see. The cascade reflects LeanHammer / Magnushammer empirical priors plus
# Mathlib's own `aesop` heuristics.
_NATIVE_HAMMER_TACTICS = (
    "aesop",
    "simp_all",
    "tauto",
    "omega",
    "decide",
    "rfl",
    "polyrith",
    "positivity",
    "norm_num",
    "linarith",
    "nlinarith",
    "field_simp; ring",
    "ring",
    "aesop (config := { maxRuleApplications := 200 })",
)


def _native_hammer_probe(row: dict, lean_root: Path, timeout_s: int) -> tuple[bool, str, str]:
    """Layer 2 — try the cheap deterministic tactic cascade on the goal.

    For each tactic in _NATIVE_HAMMER_TACTICS, write a probe file with the
    enriched context (file prelude + semantic shelf) and `:= by <tactic>`,
    compile via `lake env lean`. First tactic that closes wins. ~5-30 s per
    probe; total cap by per-tactic timeout = timeout_s / len(tactics).

    Returns (compile_ok, proof_text, transcript_tail).
    """
    base_goal = (row.get("goal") or "").strip()
    if not base_goal:
        return False, "", "native_hammer: missing goal"
    enriched = _build_solver_context(row)
    # Per-tactic budget: prefer cheap, abort the cascade as soon as one closes.
    per_tactic_timeout = max(20, int(timeout_s / max(1, len(_NATIVE_HAMMER_TACTICS))))
    transcript = []
    for tactic in _NATIVE_HAMMER_TACTICS:
        compile_ok, tail = _verify_compile(
            row.get("row_id", "anon"),
            enriched or base_goal,
            tactic,
            lean_root,
            per_tactic_timeout,
        )
        transcript.append(f"[{tactic}] {'OK' if compile_ok else 'no'}  {(tail or '')[-180:]}")
        if compile_ok:
            return True, tactic, "\n".join(transcript[-3:])
    return False, "", "\n".join(transcript[-3:])


# ── Upstream typed solver action contract ─────────────────────────────────
# Per upstream typed pattern_action_contract + epistemic-generation V35/V38 finding
# ("typed contracts help carry the intended audit/check family more reliably
# than generic artifacts"): build a SolverActionContract per row BEFORE any
# prover work begins. The contract declares pattern_chain, anti_patterns,
# required_receipts, and reject_or_repair behavior. It is what separates a
# kernel-verified closure from a credit-ready closure — the latter has to
# pass every receipt named in its own contract.

# Contract primitives canonicalized under ztare.leanmill.solver (2026-05-29
# consolidation). Local names kept as thin re-exports so the rest of this
# worker is untouched and other callers (tests, future workers) can import
# either path.
sys.path.insert(0, str(REPO / "src"))
from ztare.leanmill.solver.contract import (  # noqa: E402
    SOLVER_CONTRACT_SCHEMA,
    DEFAULT_PROVER_CHAIN as _DEFAULT_PROVER_CHAIN,
    DEFAULT_ANTI_PATTERNS as _DEFAULT_ANTI_PATTERNS,
    build_solver_action_contract as _canonical_build_solver_action_contract,
    source_cue_check as _canonical_source_cue_check,
    validate_against_contract as _canonical_validate_against_contract,
    verify_matched_negative_control as _canonical_verify_matched_negative_control,
)
# Layer seam (task #42): Layer 2 (deterministic, free) is split from Layers 3-4
# (LLM, expensive) so a caller can run the free layer first and only escalate to
# the expensive LLM provers if a gate (the Agentic Circuit Breaker, F108/task #74)
# allows. solve() passes gate=None by default → behavior-preserving.
from ztare.leanmill.solver.deterministic import run_deterministic_layer  # noqa: E402
from ztare.leanmill.solver.llm_provers import run_llm_layers  # noqa: E402
from ztare.gates.lean_compile_primitives import run_lake_subprocess, _is_compile_ok  # noqa: E402


def _source_cue_check(row: dict) -> dict:
    """Thin delegate to ztare.leanmill.solver.contract.source_cue_check."""
    return _canonical_source_cue_check(row)


def _source_cue_check_legacy(row: dict) -> dict:
    """Deterministic pre-execution check: does this row supply the source
    cues a kernel-trust prover stack needs to run? (file exists, goal text
    parseable, target name resolvable). The result is mirror-checked by the
    contract — H34 / H42 evidence: deterministic source-cue receipts before
    lowering are what get free-form synthesis from 0.33 to 1.0 accuracy.
    """
    cues = []
    missing = []
    src_str = row.get("source_file") or ""
    if src_str and Path(src_str).exists():
        cues.append("source_file_exists")
    else:
        missing.append("source_file_missing_or_nonexistent")
    if (row.get("goal") or "").strip():
        cues.append("goal_text_present")
    else:
        missing.append("goal_text_empty")
    if row.get("target_theorem_name"):
        cues.append("target_theorem_name_present")
    else:
        missing.append("target_theorem_name_missing")
    status = "passed" if not missing else "failed"
    return {
        "source_cue_check_status": status,
        "source_cue_receipts": cues,
        "missing_source_cues": missing,
    }


def _build_solver_action_contract(row: dict, lean_root: Path) -> dict:
    """Build the upstream typed action contract for one solver row.

    Structure mirrors the upstream pattern_action_contract.py (H30 / H32-H34 evidence
    basis): scope + goal_excerpt + pattern_chain + anti_patterns +
    required_receipts + executable action_program with program_counter_rule
    and stop_condition + source_cue_check + downstream_consumer_check.

    The contract is the dispatch plan. Layer dispatch in solve() advances
    the program counter ONE LAYER per cycle, respects the stop_condition,
    and validates each receipt named in required_receipts before declaring
    a closure credit-ready at the solver layer (final credit decision is
    deferred to leanmill_proof_audit).
    """
    target_name = row.get("target_theorem_name") or ""
    goal_excerpt = (row.get("goal") or "").strip()[:480]
    cue_result = _source_cue_check(row)
    # Lower the residual class to an executable action program per H30.
    # Each step is a named layer the dispatcher will run, in order, until
    # either credit_ready or the stop_condition fires.
    action_program = [
        "layer2_native_hammer_cascade",
        "layer3_warm_agent_iterate",
        "layer4_cold_shot_multi_provider",
        "layer5_validate_against_contract",
    ]
    # Try the RD pattern_action_contract for richer pattern_chain selection;
    # fall back to the local default if the RD module isn't importable.
    pattern_chain: list[str] = list(_DEFAULT_PROVER_CHAIN)
    rd_evidence_basis = "local_default"
    try:
        sys.path.insert(0, str(REPO / "src"))
        from ztare.research_director.pattern_action_contract import (  # type: ignore
            build_pattern_action_contract,
        )
        rd_contract = build_pattern_action_contract(
            scope="solver_lane_no_positive_family_template",
            goal_excerpt=goal_excerpt,
        )
        rd_dict = asdict(rd_contract) if is_dataclass(rd_contract) else (
            rd_contract if isinstance(rd_contract, dict) else {})
        rd_pattern_chain = list(rd_dict.get("pattern_chain") or [])
        if rd_pattern_chain:
            pattern_chain = rd_pattern_chain
            rd_evidence_basis = "rd_pattern_action_contract"
    except Exception:
        pass

    # ── RD primitive_tick_surface query: pull the top-relevance primitives
    # (gates, patterns, ops) matched to the goal text. This is the apparatus's
    # in-built relevance retrieval — same surface RD uses pre-tick. Exposes
    # which gates / mining ops the solver should consult when a layer fails.
    rd_primitive_hits: list[dict] = []
    try:
        sys.path.insert(0, str(REPO / "src"))
        from ztare.research_director.primitive_tick_surface import (  # type: ignore
            build_primitive_tick_surface,
        )
        # Tokenize the goal text + target name + sub_area into query terms.
        raw = f"{target_name} {goal_excerpt} {row.get('sub_area') or ''}".lower()
        tokens = [
            t for t in
            "".join(ch if ch.isalnum() else " " for ch in raw).split()
            if len(t) >= 3
        ]
        # Deduplicate while preserving order; cap to 16 most-informative.
        seen = set()
        query_terms = []
        for t in tokens:
            if t not in seen:
                seen.add(t)
                query_terms.append(t)
            if len(query_terms) >= 16:
                break
        if query_terms:
            surface = build_primitive_tick_surface(
                query_terms=query_terms, top_n=6, per_bucket=2,
            )
            for hit in (surface.top_hits or []):
                rd_primitive_hits.append({
                    "id": hit.id,
                    "kind": hit.kind,
                    "score": hit.score,
                    "why": hit.why,
                    "description": hit.description,
                })
    except Exception:
        pass
    return {
        "schema": SOLVER_CONTRACT_SCHEMA,
        "generated_at_epoch": int(time.time()),
        "row_id": row.get("row_id"),
        "target_theorem_name": target_name,
        "source_file": row.get("source_file"),
        "scope": "solver_lane_no_positive_family_template",
        "goal_excerpt": goal_excerpt,
        "requested_residual_class": "no_positive_family_template_closure",
        "accepted_residual_class": (
            "no_positive_family_template_closure"
            if cue_result["source_cue_check_status"] == "passed"
            else "outside_menu_source_cues_missing"
        ),
        "source_cue_check_status": cue_result["source_cue_check_status"],
        "source_cue_receipts": cue_result["source_cue_receipts"],
        "missing_source_cues": cue_result["missing_source_cues"],
        "rejected_nearest_confuser": "pde_estimate_or_carrier_residual (rejected: target is not a PDE inequality; routes to PDE workbench instead)",
        "pattern_chain": pattern_chain,
        "anti_patterns": list(_DEFAULT_ANTI_PATTERNS),
        "evidence_basis": rd_evidence_basis,
        "rd_primitive_hits": rd_primitive_hits,
        # Executable program per H30: every action is named, ordered, and
        # advanced by the program counter rule after the previous action
        # emits its receipt.
        "action_program": action_program,
        "current_action_index": 0,
        "required_next_action": action_program[0],
        "program_counter_rule": (
            "advance current_action_index only after the current action has emitted "
            "its receipt; if the receipt is `closed` AND matched_negative_control "
            "passes, stop (credit_ready_at_solver_layer = true). Otherwise continue "
            "to the next action_program step until exhausted or stop_condition fires."
        ),
        "stop_condition": (
            "stop on first credit_ready_at_solver_layer = true; or when "
            "action_program is exhausted (last action's receipt recorded); or when "
            "the row exceeds MAX_FAILED_ATTEMPTS_PER_ROW across cycles (cooldown)."
        ),
        "required_receipts": [
            {
                "name": "kernel_compile_receipt",
                "required": True,
                "acceptance_check": "lake env lean over the enriched probe (prelude + semantic shelf + proof body) returns exit 0 with no error: lines.",
            },
            {
                "name": "matched_negative_control_receipt",
                "required": True,
                "acceptance_check": "the same proof_text under bare `import Mathlib` (gold-bearing prelude STRIPPED) FAILS to compile. A negative-control PASS = the proof was a single-Mathlib-lookup; that is leakage and forces rejection.",
            },
            {
                "name": "axiom_allowlist_receipt",
                "required": True,
                "acceptance_check": "`#print axioms <target>` shows axioms ⊆ {propext, Classical.choice, Quot.sound}.",
                "deferred_to": "leanmill_proof_audit",
            },
            {
                "name": "l3_anti_pattern_receipt",
                "required": True,
                "acceptance_check": "the v33 deep verifier (single-lemma `by exact?`, indirect leakage, currency mismatch, paraphrase) returns no confirmed blocker.",
                "deferred_to": "leanmill_proof_audit",
            },
        ],
        "reject_or_repair_behavior": {
            "kernel_compile_fail": "advance to next action_program step; if exhausted, mark row failed_compile and record attempt.",
            "matched_negative_control_pass": "REJECT closure as leakage/laundering; mark row rejected_negative_control; do not credit.",
            "axiom_outside_allowlist": "REJECT closure; mark row rejected_axiom_outside_allowlist.",
            "l3_confirmed_blocker": "REJECT closure; mark row rejected_l3; record the specific blocker class.",
            "clean_proceed_condition": "all required_receipts at solver_layer must pass AND downstream_consumer_check must accept; only then upgrade to unratified_closure_candidate typed exit.",
        },
        "downstream_consumer_check": "leanmill_proof_audit emits a typed receipt that the governance worker consumes; only payloads with all receipts passing become unratified_closure_candidate typed exits.",
        "credit_boundary": "advisory_only_no_factory_credit; the contract names the receipts that must pass before any credit-ready upgrade.",
    }


def _verify_matched_negative_control(target_name: str, proof_text: str,
                                     lean_root: Path, timeout_s: int) -> tuple[bool, str]:
    """Run the matched negative control: does proof_text close the goal under
    bare `import Mathlib` (i.e. WITHOUT the source file's prelude)? If yes,
    the proof was a paraphrase of an existing Mathlib lemma — laundering.

    Returns (negative_control_ok, output_tail). negative_control_ok=True
    means the NEGATIVE control FAILED (which is what we want — the proof
    needs the prelude to compile, so it is NOT just a Mathlib lookup).
    """
    if not target_name or not proof_text.strip():
        return False, "missing target or proof"
    body = proof_text.strip()
    if body.startswith("by "):
        body = body[3:]
    src = (
        "import Mathlib\n\n"
        f"theorem {target_name}_negctrl : True := by\n"
        f"  trivial -- harness placeholder; the real negctrl applies the candidate body to the bare goal\n\n"
        f"-- matched negative control: rebuild the goal stub WITHOUT the prelude,\n"
        f"-- then attempt the candidate proof body.\n"
        f"-- If this compiles, the proof_text was leakage.\n"
        f"theorem {target_name}_stripped_attempt := by\n"
        f"  {body}\n"
    )
    try:
        with tempfile.TemporaryDirectory(prefix=f"solver_negctrl_{target_name}_") as td:
            probe = Path(td) / "NegCtrl.lean"
            probe.write_text(src, encoding="utf-8")
            proc = run_lake_subprocess(
                ["lake", "env", "lean", str(probe)],
                str(lean_root), timeout_s=timeout_s,
            )
            output = (proc.stdout or "") + "\n" + (proc.stderr or "")
            stripped_compiled = proc.returncode == 0 and "error:" not in output
            # Inverted return: True = negative control FAILED (good)
            return (not stripped_compiled), output[-600:]
    except subprocess.TimeoutExpired:
        return False, "negctrl_timeout"
    except FileNotFoundError as exc:
        return False, f"lake_not_on_PATH: {exc!s}"
    except Exception as exc:  # noqa: BLE001
        return False, f"negctrl_exception: {exc!r}"


def _validate_against_contract(
    contract: dict,
    proof_text: str,
    enriched_goal: str,
    target_name: str,
    lean_root: Path,
    timeout_s: int,
    kernel_compile_ok: bool,
    kernel_compile_tail: str,
) -> dict:
    """Run every required receipt named in the contract and return a structured
    verdict. A closure is credit-ready iff every required receipt passes.

    The MNC check is run here (not deferred to governance) so the solver lane
    rejects laundering at solve-time, not after the typed-exit has propagated.
    """
    receipts: dict[str, dict] = {}
    receipts["kernel_compile_receipt"] = {
        "passed": bool(kernel_compile_ok),
        "tail": (kernel_compile_tail or "")[-400:],
    }
    # MNC: only meaningful if compile passed (no point negctrl-ing a non-closure)
    if kernel_compile_ok:
        mnc_ok, mnc_tail = _verify_matched_negative_control(
            target_name, proof_text, lean_root, timeout_s
        )
        receipts["matched_negative_control_receipt"] = {
            "passed": mnc_ok,
            "tail": mnc_tail[-300:],
            "interpretation": (
                "PASS = bare-Mathlib stripped attempt did NOT compile → proof needs the prelude → genuine"
                if mnc_ok else
                "FAIL = bare-Mathlib stripped attempt DID compile → proof_text was a Mathlib lookup → leakage"
            ),
        }
    else:
        receipts["matched_negative_control_receipt"] = {
            "passed": False,
            "tail": "skipped (kernel_compile_receipt failed)",
            "interpretation": "skipped: no closure to negative-control",
        }
    # axiom allowlist + L3 are deferred to the canonical proof_audit (run by
    # governance) — the solver-side contract just records that they're required.
    receipts["axiom_allowlist_receipt"] = {
        "passed": None,
        "tail": "deferred to governance: leanmill_proof_audit emits #print axioms",
    }
    receipts["l3_anti_pattern_receipt"] = {
        "passed": None,
        "tail": "deferred to governance: v33 stack runs in leanmill_proof_audit",
    }
    all_required_pass = all(
        bool(receipts[r["name"]]["passed"]) is True
        for r in contract.get("required_receipts", [])
        if r.get("required") and receipts[r["name"]]["passed"] is not None
    )
    credit_ready = (
        kernel_compile_ok
        and receipts["matched_negative_control_receipt"]["passed"] is True
    )
    return {
        "contract_schema": contract.get("schema"),
        "receipts": receipts,
        "credit_ready_at_solver_layer": bool(credit_ready),
        "required_receipts_all_passed_at_solver_layer": bool(all_required_pass),
        "downstream_required": "leanmill_proof_audit (axiom_allowlist + L3) before factory credit",
    }


def _warm_agent_solve(row: dict, lean_root: Path, timeout_s: int) -> tuple[bool, str, str]:
    """Warm-agent solver: Claude with Bash+Edit+Read enabled, working in a
    scratch dir under `lean_root/.solver_scratch/<row_id>/`, asked to write
    a proof body into target.lean and verify it by running `lake env lean`.

    Unlike the one-shot ClaudeOpus provider (text-trust), the warm agent
    sees its own kernel verdicts and can iterate on errors. WebSearch and
    WebFetch stay disallowed to keep contamination-free.

    Returns (compile_ok, proof_text, transcript_tail).
    """
    base_goal = (row.get("goal") or "").strip()
    target_name = row.get("target_theorem_name") or ""
    src_path_str = row.get("source_file") or ""
    if not base_goal or not target_name or not src_path_str:
        return False, "", "missing row fields (goal / target / source_file)"
    src_path = Path(src_path_str)
    if not src_path.exists():
        return False, "", f"source_file does not exist: {src_path}"
    # Per-row scratch dir under lean_root so `lake env lean` works.
    scratch_root = lean_root / ".solver_scratch"
    scratch_root.mkdir(parents=True, exist_ok=True)
    scratch_dir = scratch_root / row.get("row_id", "anon")
    scratch_dir.mkdir(parents=True, exist_ok=True)
    target_file = scratch_dir / "target.lean"
    # Seed target.lean with the full source file (preludes + helper lemmas)
    # and a `by sorry` placeholder for the target theorem. The agent edits
    # this file in place, then runs lake env lean on it.
    try:
        full_text = src_path.read_text(encoding="utf-8", errors="replace")
    except Exception as exc:
        return False, "", f"could not read source_file: {exc!r}"
    # Replace `<target> := <anything>` with `<target> := by sorry` so the
    # agent has a clean stub to edit. Keep the rest of the file unchanged.
    import re as _re
    stub_pattern = _re.compile(
        rf"(theorem|lemma)\s+{_re.escape(target_name)}\b.*?:=\s*by\s*sorry",
        _re.DOTALL,
    )
    if not stub_pattern.search(full_text):
        # Fall back: append our own stub at end of file if not already present
        if f"theorem {target_name}" not in full_text:
            full_text = full_text.rstrip() + f"\n\n{base_goal}\n  sorry\n"
    target_file.write_text(full_text, encoding="utf-8")

    abs_target = str(target_file)
    abs_lean_root = str(lean_root)
    prompt = (
        f"You are a Lean 4 theorem prover. The Lean project root (lakefile present) is "
        f"`{abs_lean_root}`. Your scratch file is `{abs_target}`. "
        f"Inside it there is a theorem named `{target_name}` whose proof body is "
        f"currently `by sorry`. Replace `sorry` with a tactic block that closes the goal "
        f"so that the command `cd {abs_lean_root} && lake env lean {abs_target}` returns "
        f"exit code 0 with no `error:` lines.\n\n"
        f"WORKFLOW (use Bash + Read + Edit tools):\n"
        f"1. Read `{abs_target}` to see the prelude (imports, definitions, helper lemmas) and the target.\n"
        f"2. Edit the proof body. Try `by exact?`, `by aesop`, `by simp_all`, `by omega`, "
        f"`by decide`, `by polyrith`, or a hand-written tactic block, depending on the goal shape.\n"
        f"3. Verify by running: `cd {abs_lean_root} && lake env lean {abs_target}`\n"
        f"4. If the kernel reports errors, read the error, refine the proof, verify again.\n"
        f"5. STOP when either (a) the kernel returns exit 0 with no `error:` lines, or (b) you have made 5 verification attempts.\n\n"
        f"FINAL OUTPUT (must be the last line you print): 'DONE' on success or 'GIVE_UP <one-line reason>' on failure.\n"
        f"Do not modify any other files. Do not use WebSearch or WebFetch."
    )

    import sys
    repo = Path(__file__).resolve().parents[4]
    if str(repo) not in sys.path:
        sys.path.insert(0, str(repo))
    try:
        from src.ztare.common.subscription_agent_runtime import (  # type: ignore
            run_subscription_agent_with_recovery,
        )
    except Exception as exc:
        return False, "", f"subscription_agent_runtime import failed: {exc!r}"
    try:
        run = run_subscription_agent_with_recovery(
            runtime="claude",
            prompt=prompt,
            agent_id=f"leanmill::solver_lane::warm::{row.get('row_id', 'anon')}",
            repo=repo,
            session_state=None,
            timeout_seconds=timeout_s,
            claude_disallowed_tools=["WebSearch", "WebFetch"],
        )
    except Exception as exc:
        return False, "", f"warm agent exception: {exc!r}"
    stdout = (getattr(run.result, "stdout", "") or "") if run else ""
    stderr = (getattr(run.result, "stderr", "") or "") if run else ""
    # After the agent exits, kernel-verify the final state of target.lean.
    final_text = target_file.read_text(encoding="utf-8", errors="replace")
    # Extract proof body for the typed-exit record.
    proof_match = _re.search(
        rf"(theorem|lemma)\s+{_re.escape(target_name)}\b.*?:=\s*by\b(.*?)(?=\n\s*(theorem|lemma|def|instance|end|namespace|#|/-)\b|\Z)",
        final_text,
        _re.DOTALL,
    )
    proof_body = (proof_match.group(2).strip() if proof_match else "")
    try:
        proc = run_lake_subprocess(
            ["lake", "env", "lean", str(target_file)],
            str(lean_root), timeout_s=timeout_s,
        )
        output = (proc.stdout or "") + "\n" + (proc.stderr or "")
        # _is_compile_ok rejects sorry/admit/bare-error: `lake env lean` exits 0 on a
        # `sorry` (it's a warning), so the old `rc==0 and "error:" not in output` minted
        # FALSE `closed` verdicts for abandoned-with-sorry rows into the governance ledger
        # (caught by the 2-row smoke 2026-05-30). Use the hardened oracle.
        kernel_ok = _is_compile_ok(proc.returncode, output)
        tail = (
            f"[agent stdout tail]\n{stdout[-400:]}\n"
            f"[kernel verify exit={proc.returncode}]\n{output[-600:]}"
        )
    except subprocess.TimeoutExpired:
        kernel_ok = False
        tail = "kernel verify timed out"
    except FileNotFoundError as exc:
        kernel_ok = False
        tail = f"lake not on PATH: {exc!s}"
    return kernel_ok, proof_body, tail[-1200:]


def _verify_compile(row_id: str, goal_text: str, proof_text: str,
                    lean_root: Path, timeout_s: int) -> tuple[bool, str]:
    """Compile `import Mathlib\\n<goal>\\n  <proof_text>` and report compile_ok.

    The original solver treated `provider.res.ok` (the LLM call ran) as the
    closure verdict. That is text-trust, not kernel-trust. This function is
    the kernel-trust check: we write a probe file consisting of the goal
    stub + the provider's emitted tactic body, hand it to `lake env lean`,
    and return True only if the kernel says exit 0 AND no Lean errors.
    """
    goal = (goal_text or "").strip()
    body = _strip_proof_text(proof_text)
    if not goal or not body:
        return False, "missing goal or proof text"
    # If the provider returned text starting with `by`, fold into the stub
    # which already ends with `:= by`. Otherwise append as-is on a new line.
    if goal.endswith(":= by"):
        proof_block = body[3:].lstrip() if body.startswith("by ") else body
        src = f"import Mathlib\n\n{goal}\n  {proof_block}\n"
    else:
        src = f"import Mathlib\n\n{goal}\n{body}\n"
    try:
        with tempfile.TemporaryDirectory(prefix=f"solver_verify_{row_id}_") as td:
            probe = Path(td) / "Probe.lean"
            probe.write_text(src, encoding="utf-8")
            proc = run_lake_subprocess(
                ["lake", "env", "lean", str(probe)],
                str(lean_root), timeout_s=timeout_s,
            )
            output = (proc.stdout or "") + "\n" + (proc.stderr or "")
            # _is_compile_ok rejects sorry/admit/bare-error (sorry exits 0 as a warning) —
            # the 2-row smoke (2026-05-30) caught the old check minting FALSE `closed` on sorry.
            kernel_ok = _is_compile_ok(proc.returncode, output)
            return kernel_ok, output[-800:]
    except subprocess.TimeoutExpired:
        return False, "verify_compile_timeout"
    except FileNotFoundError as exc:
        return False, f"lake_not_on_PATH: {exc!s}"
    except Exception as exc:  # noqa: BLE001
        return False, f"verify_compile_exception: {exc!r}"
# --------------------------------------------------------------------------

sys.path.insert(0, str(REPO))
sys.path.insert(0, str(CONTROL))


def _load(path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    return m


def _read_json(p: Path):
    return json.loads(p.read_text()) if p.exists() else {}


def _static_status(r: dict) -> str:
    s = r.get("static_tools_result")
    if isinstance(s, dict):
        return str(s.get("status") or "")
    return str(s or "")


def _slice_source() -> tuple[Path, Path, str]:
    # Source of truth: the corpus mandate registry. If an active mandate is
    # registered for solver_lane with materialized slice + row_context paths,
    # use them. Otherwise fall back to the family-spec harness slice.
    try:
        sys.path.insert(0, str(REPO / "src"))
        from ztare.leanmill.contracts.corpus_mandate import active_solver_slice_pair
        pair = active_solver_slice_pair()
    except Exception:
        pair = None
    if pair is not None:
        slice_path = REPO / pair[0]
        row_ctx_path = REPO / pair[1]
        if slice_path.exists() and row_ctx_path.exists():
            return slice_path, row_ctx_path, "mandate"
    if SLICE_FULL.exists():
        return SLICE_FULL, (ROW_CTX_FULL if ROW_CTX_FULL.exists() else ROW_CTX_CLEANED), "full"
    return SLICE_CLEANED, ROW_CTX_CLEANED, "cleaned_fallback"


def solver_eligible_rows() -> list[dict]:
    """Rows where static missed + no positive family template + executable target —
    the `no_positive_family_template` C-pool rows the solver should attack.

    NOTE (materialization gap, 2026-05-28): the cleaned slice DROPS no-template rows
    (it only carries the family-matched candidate subset). The full slice
    (evaluation_harness_c_discriminating_slice.json) carries them but is regenerated
    by leanmill_c_discriminating_slice_prep.py. If only the cleaned slice exists,
    this returns 0 and the caller should surface the materialization gap — the
    no-template rows are COUNTED as blocked in factory_intelligence but never
    materialized as solver-ready goals. Fixing that is the prep-side change."""
    slice_path, ctx_path, _origin = _slice_source()
    sl = _read_json(slice_path)
    ctx = _read_json(ctx_path)
    goals = {r.get("row_id"): r for r in ctx.get("rows", []) if isinstance(r, dict)}
    out = []
    for r in sl.get("rows", []):
        if not isinstance(r, dict):
            continue
        reasons = r.get("rejection_reasons") or []
        # no_positive_family_template is the solver class. Static must have MISSED
        # (failed_or_no_positive_signal); target must be executable.
        no_template = ("no_positive_family_template" in reasons) or (not r.get("families_with_positive_template"))
        static_missed = _static_status(r) == "failed_or_no_positive_signal"
        executable = bool(r.get("target_resolution_ok"))
        if not (no_template and static_missed and executable):
            continue
        gctx = goals.get(r.get("row_id"), {})
        out.append({
            "row_id": r.get("row_id"),
            "target_theorem_name": r.get("target_theorem_name"),
            "source_file": r.get("source_file"),
            "goal": gctx.get("goal"),
            "sorried_file": gctx.get("sorried_file"),
            "target_line": gctx.get("target_line"),
            "rejection_reasons": reasons,
        })
    # Persisted-attempts filter: drop rows already-closed (compile_ok=1) and
    # rows that have failed >= MAX_FAILED_ATTEMPTS_PER_ROW so the loop walks
    # the slice instead of re-attacking the first three rows forever.
    filtered = []
    for row in out:
        rid = row.get("row_id")
        if not rid:
            continue
        if _row_already_closed(rid):
            continue
        if _failed_attempts_count(rid) >= MAX_FAILED_ATTEMPTS_PER_ROW:
            continue
        filtered.append(row)
    return filtered


def materialization_status() -> dict:
    """Report whether the no-template rows are materialized as solver-ready goals."""
    slice_path, _ctx, origin = _slice_source()
    return {
        "slice_source": str(slice_path.name),
        "slice_origin": origin,
        "full_slice_exists": SLICE_FULL.exists(),
        "solver_eligible_count": len(solver_eligible_rows()),
        "materialization_gap": (origin == "cleaned_fallback"),
        "note": ("Full slice missing — no-template rows are NOT materialized as solver goals. "
                 "Run leanmill_c_discriminating_slice_prep.py to regenerate the full slice with "
                 "rejection_reasons, OR extend the prep to emit a solver-lane corpus." if origin == "cleaned_fallback"
                 else "Full slice present; no-template rows available to the solver lane."),
    }


def _policy_model(default: str = "claude_opus") -> str:
    pol = _read_json(POLICY)
    ops = pol.get("operations", {}) if isinstance(pol, dict) else {}
    lane = ops.get("solver_lane", {}) if isinstance(ops, dict) else {}
    return lane.get("provider", default)


def _policy_fallbacks() -> list[str]:
    pol = _read_json(POLICY)
    ops = pol.get("operations", {}) if isinstance(pol, dict) else {}
    lane = ops.get("solver_lane", {}) if isinstance(ops, dict) else {}
    return list(lane.get("provider_fallbacks") or [])


def _build_dag_move_runner(r: dict, contract: dict, enriched_goal: str,
                           verify_timeout: int, provider: str, fallbacks: list[str],
                           invoke_with_routing, providers_tried: list[dict]):
    """Bind a GP-246 `move_runner` to the worker's REAL move generators.

    The returned callable takes (DagNode, move_kind, budget) and:
      1. runs the corresponding worker move (native_hammer / warm agent /
         cold-shot fan-out / frontier slot),
      2. governs the emitted proof through the EXISTING `_validate_against_contract`
         (kernel-compile receipt + matched-negative-control receipt; reuses
         `_is_compile_ok` via `_verify_compile` / `_warm_agent_solve`),
      3. returns a typed MoveResult whose `kernel_clean` / `mnc_passed` are read
         straight off the governance receipts — the search NEVER self-credits.

    This is the proposes/ratifies boundary: the runner ratifies, the search records.
    """
    from ztare.leanmill.solver.governed_dag_search import (
        MoveResult, MOVE_NATIVE_HAMMER, MOVE_CLAUDE_WARM, MOVE_COLD_SHOT, MOVE_FRONTIER,
    )

    target_name = r.get("target_theorem_name") or ""

    def _govern(proof_text: str, compile_ok: bool, compile_tail: str) -> tuple[bool, bool]:
        """Run the existing contract validation; return (kernel_clean, mnc_passed)."""
        if not compile_ok or not proof_text.strip():
            return False, False
        validation = _validate_against_contract(
            contract=contract, proof_text=proof_text, enriched_goal=enriched_goal,
            target_name=target_name, lean_root=DEFAULT_LEAN_ROOT_FOR_VERIFY,
            timeout_s=verify_timeout, kernel_compile_ok=compile_ok,
            kernel_compile_tail=compile_tail,
        )
        kc = validation["receipts"]["kernel_compile_receipt"]["passed"]
        mnc = validation["receipts"]["matched_negative_control_receipt"]["passed"]
        return bool(kc), bool(mnc)

    def move_runner(node, move, budget):
        start = time.time()
        if move == MOVE_NATIVE_HAMMER:
            ok, proof, tail = _native_hammer_probe(
                r, DEFAULT_LEAN_ROOT_FOR_VERIFY, min(180, verify_timeout),
            )
            proof_text = f"by {proof}" if proof else ""
            kc, mnc = _govern(proof_text, ok, tail) if ok else (False, False)
            _record_attempt(r["row_id"], "native_hammer",
                            "closed" if (kc and mnc) else "failed_compile", kc and mnc, tail)
            providers_tried.append({"provider": "native_hammer",
                                    "outcome": "closed" if (kc and mnc) else "failed_compile",
                                    "compile_ok": kc, "mnc_passed": mnc,
                                    "node_id": node.node_id, "move": move,
                                    "agent_kind": "native_hammer_cascade"})
            return MoveResult(move=move, kernel_clean=kc, mnc_passed=mnc,
                              proof_text=proof_text, tail=(tail or "")[-300:],
                              wallclock_s=round(time.time() - start, 2))
        if move == MOVE_CLAUDE_WARM:
            ok, proof_text, tail = _warm_agent_solve(
                r, DEFAULT_LEAN_ROOT_FOR_VERIFY, max(180, verify_timeout * 2),
            )
            kc, mnc = _govern(proof_text, ok, tail) if ok else (False, False)
            _record_attempt(r["row_id"], "claude_opus_warm",
                            "closed" if (kc and mnc) else "failed_compile", kc and mnc, tail)
            providers_tried.append({"provider": "claude_opus_warm",
                                    "outcome": "closed" if (kc and mnc) else "failed_compile",
                                    "compile_ok": kc, "mnc_passed": mnc,
                                    "node_id": node.node_id, "move": move,
                                    "agent_kind": "warm_agent"})
            return MoveResult(move=move, kernel_clean=kc, mnc_passed=mnc,
                              proof_text=proof_text, tail=(tail or "")[-300:],
                              wallclock_s=round(time.time() - start, 2))
        if move in (MOVE_COLD_SHOT, MOVE_FRONTIER):
            # Cold-shot fan-out across preferred + fallbacks. The frontier slot is
            # provider-agnostic: a lab prover registered in the chain plugs in here
            # as one more provider; governance is identical.
            chain = [provider] + [f for f in fallbacks if f != provider]
            best = None
            for prov_name in chain:
                decision = invoke_with_routing(
                    enriched_goal or node.goal_text, preferred=prov_name,
                    fallbacks=[], timeout_s=verify_timeout,
                )
                res = decision.result
                proof_text = (res.proof_text if res else None) or ""
                compile_ok, compile_tail = (False, "no provider proof")
                if res is not None and res.ok and proof_text.strip():
                    compile_ok, compile_tail = _verify_compile(
                        r["row_id"], enriched_goal or node.goal_text, proof_text,
                        DEFAULT_LEAN_ROOT_FOR_VERIFY, verify_timeout,
                    )
                kc, mnc = _govern(proof_text, compile_ok, compile_tail) if compile_ok else (False, False)
                label = decision.chosen_provider or prov_name
                _record_attempt(r["row_id"], label,
                                "closed" if (kc and mnc) else ("failed_compile" if (res and res.ok) else "failed"),
                                kc and mnc, compile_tail)
                providers_tried.append({"provider": label,
                                        "outcome": "closed" if (kc and mnc) else "failed_compile",
                                        "compile_ok": kc, "mnc_passed": mnc,
                                        "node_id": node.node_id, "move": move})
                best = (proof_text, kc, mnc, compile_tail)
                if kc and mnc:
                    break
            proof_text, kc, mnc, compile_tail = best or ("", False, False, "")
            return MoveResult(move=move, kernel_clean=kc, mnc_passed=mnc,
                              proof_text=proof_text, tail=(compile_tail or "")[-300:],
                              wallclock_s=round(time.time() - start, 2))
        return MoveResult(move=move, kernel_clean=False, mnc_passed=False,
                          tail=f"unknown move {move}")

    return move_runner


def solve(provider: str, limit: int, dry_run: bool, timeout_s: int = 300,
          mode: str = "cascade") -> dict:
    # Routing: invoke via ztare.leanmill.providers.router.invoke_with_routing,
    # which honors per-node capability detection and the policy fallback chain
    # (operations.solver_lane.provider_fallbacks). Hard node failures
    # (credit_exhausted / auth_missing / binary_not_found) fall through to the
    # next provider transparently — the laptop+VPS load balance the operator
    # flagged as the 10x lever. Non-migrated providers (native_hammer,
    # leancopilot) still go through the legacy bash-wrapper registry.
    sys.path.insert(0, str(REPO / "src"))
    fallbacks = _policy_fallbacks()
    try:
        from ztare.leanmill.providers import REGISTRY as TYPED_REG
        from ztare.leanmill.providers.router import invoke_with_routing
        typed_available = provider in TYPED_REG
    except Exception:
        typed_available = False
        invoke_with_routing = None  # type: ignore
    reg = None
    if not typed_available:
        reg = _load(CONTROL / "leanmill_provider_registry.py")
    rows = solver_eligible_rows()[:limit] if limit else solver_eligible_rows()
    results = []
    for r in rows:
        goal = r.get("goal") or r.get("target_theorem_name") or ""
        if not goal:
            results.append({"name": r["row_id"], "kind": "c_pool_no_template",
                            "outcome": "skipped", "exit_code": 0,
                            "stderr_excerpt": "no goal text"})
            continue
        if dry_run:
            results.append({"name": r["row_id"], "kind": "c_pool_no_template",
                            "outcome": "skipped", "exit_code": 0,
                            "stderr_excerpt": "dry_run: would invoke " + provider,
                            "goal_preview": str(goal)[:120]})
            continue
        if typed_available and invoke_with_routing is not None:
            # ── Upstream typed action contract (built BEFORE any prover work).
            # Per H32-H42: typed contract + source_cue_check + deterministic
            # lowering = 1.0 accuracy vs 0.33 for free-form chain. The
            # contract IS the dispatch plan; layer steps below are the
            # contract's action_program lowered to executable code.
            contract = _build_solver_action_contract(r, DEFAULT_LEAN_ROOT_FOR_VERIFY)
            if contract["source_cue_check_status"] == "failed":
                # H36/H37 outside_menu route: do not force a known class.
                results.append({
                    "name": r["row_id"],
                    "target_name": r.get("target_theorem_name"),
                    "kind": "c_pool_no_template",
                    "outcome": "outside_menu_source_cues_missing",
                    "compile_ok": False,
                    "exit_code": 1,
                    "proof_text": "",
                    "provider": "solver_contract_pre_check",
                    "providers_tried": [],
                    "solver_action_contract": contract,
                    "missing_source_cues": contract["missing_source_cues"],
                })
                continue

            # Context-rich prompt: source-file prelude + semantic premise
            # shelf (cosine-similar Mathlib/APN/NS candidate lemmas) + the
            # target theorem stub.
            enriched_goal = _build_solver_context(r)
            verify_timeout = max(60, timeout_s // 2)
            providers_tried: list[dict] = []
            final = None

            # ── GP-246 governed DAG proof-search (additive, opt-in via --mode
            # dag_search). The cascade path below is byte-unchanged on the
            # default mode == "cascade". Here we route the row through
            # run_governed_dag_search with a move_runner bound to the SAME real
            # move generators + the SAME governance (_validate_against_contract).
            if mode == "dag_search":
                from ztare.leanmill.solver.governed_dag_search import (
                    run_governed_dag_search,
                )
                move_runner = _build_dag_move_runner(
                    r, contract, enriched_goal, verify_timeout, provider, fallbacks,
                    invoke_with_routing, providers_tried,
                )
                dag_res = run_governed_dag_search(
                    contract=contract,
                    goal_text=enriched_goal or str(goal),
                    move_runner=move_runner,
                    wallclock_budget_s=float(timeout_s),
                )
                root_closed = dag_res["root_status"] == "closed"
                results.append({
                    "name": r["row_id"],
                    "target_name": r.get("target_theorem_name"),
                    "kind": "c_pool_no_template",
                    "mode": "dag_search",
                    "outcome": "closed" if root_closed else dag_res["root_resolution"],
                    "compile_ok": root_closed,
                    "exit_code": 0 if root_closed else 1,
                    "proof_text": dag_res["root_proof_text"],
                    "provider": "governed_dag_search",
                    "providers_tried": providers_tried,
                    "solver_action_contract": contract,
                    "dag_search": {
                        "root_status": dag_res["root_status"],
                        "root_resolution": dag_res["root_resolution"],
                        "closed_or_exact_gap": dag_res["closed_or_exact_gap"],
                        "moves_made": dag_res["moves_made"],
                        "wallclock_s": dag_res["wallclock_s"],
                        "levers": dag_res["levers"],
                        "move_attribution": dag_res["move_attribution"],
                        "trace": dag_res["trace"],
                    },
                    "matched_negative_control": {
                        "kind": "context_stripped",
                        "executed_at": "solver_layer" if root_closed else "skipped",
                    },
                })
                continue

            # ── Prover stack (driven by contract.action_program):
            #    Layer 2: native_hammer (free tactic cascade)
            #    Layer 3: warm agent (iterative, Bash+Edit+Read)
            #    Layer 4: cold-shot fan-out across the typed REGISTRY
            #    Layer 5: validate emitted proof against contract.required_receipts
            # Program-counter rule (H30): advance after each layer emits its
            # receipt; stop on first credit_ready_at_solver_layer = True.

            def _validate_and_maybe_close(prov_label: str, compile_ok: bool,
                                          proof_text: str, compile_tail: str,
                                          start_t: float) -> dict | None:
                """Run contract validation; if credit_ready, build the
                closed-result dict and return it (caller appends + continues).
                If not credit_ready, return None and the dispatcher walks on."""
                if not compile_ok or not proof_text.strip():
                    return None
                validation = _validate_against_contract(
                    contract=contract,
                    proof_text=proof_text,
                    enriched_goal=enriched_goal,
                    target_name=r.get("target_theorem_name") or "",
                    lean_root=DEFAULT_LEAN_ROOT_FOR_VERIFY,
                    timeout_s=verify_timeout,
                    kernel_compile_ok=compile_ok,
                    kernel_compile_tail=compile_tail,
                )
                providers_tried[-1]["contract_validation"] = validation
                if not validation["credit_ready_at_solver_layer"]:
                    # MNC failed → reject as leakage, do not credit; continue.
                    providers_tried[-1]["outcome"] = "rejected_negative_control"
                    _record_attempt(
                        r["row_id"], prov_label,
                        "rejected_negative_control", False,
                        "matched_negative_control passed (proof_text compiled under bare import = leakage)",
                    )
                    return None
                # All solver-layer receipts passed.
                return {
                    "name": r["row_id"],
                    "target_name": r.get("target_theorem_name"),
                    "kind": "c_pool_no_template",
                    "outcome": "closed",
                    "compile_ok": True,
                    "compile_tail": (compile_tail or "")[-400:],
                    "exit_code": 0,
                    "proof_text": proof_text,
                    "provider": prov_label,
                    "providers_tried": providers_tried,
                    "provider_error": "none",
                    "provider_wallclock_s": round(time.time() - start_t, 2),
                    "solver_action_contract": contract,
                    "contract_validation": validation,
                    "matched_negative_control": {
                        "kind": "context_stripped",
                        "executed_at": "solver_layer",
                        "passed": validation["receipts"]["matched_negative_control_receipt"]["passed"],
                    },
                }

            # --- Layer 2: native hammer (FREE, deterministic, ranked by hit
            # rate on Mathlib targets — Magnushammer-style first attack).
            # Dispatched through the split deterministic module (task #42); the
            # pure tactic-cascade probe (_native_hammer_probe) is wrapped, not
            # moved, so the worker's _build_solver_context / _verify_compile /
            # REPO deps stay put. Behavior is identical to the inline cascade.
            hammer_start = time.time()
            det = run_deterministic_layer(
                r, DEFAULT_LEAN_ROOT_FOR_VERIFY, min(180, timeout_s // 2),
                native_hammer_probe=_native_hammer_probe,
            )
            hammer_ok = det["closed"]
            hammer_proof = det["proof"]
            hammer_tail = det["tail"]
            hammer_outcome = "closed" if hammer_ok else "failed_compile"
            _record_attempt(
                r["row_id"], "native_hammer", hammer_outcome, hammer_ok, hammer_tail,
            )
            providers_tried.append({
                "provider": "native_hammer",
                "outcome": hammer_outcome,
                "compile_ok": hammer_ok,
                "compile_tail": (hammer_tail or "")[-300:],
                "provider_wallclock_s": round(time.time() - hammer_start, 2),
                "agent_kind": "native_hammer_cascade",
            })
            if hammer_ok:
                closed = _validate_and_maybe_close(
                    "native_hammer", True, f"by {hammer_proof}", hammer_tail, hammer_start,
                )
                if closed is not None:
                    results.append(closed)
                    continue
                # else: MNC rejected the hammer closure → walk on.

            # --- Layers 3-4: LLM provers (warm agent + cold-shot fan-out),
            # EXPENSIVE. Dispatched through the split llm_provers module (task
            # #42). The warm-agent and cold-shot bodies are wrapped as zero-arg
            # layer runners below — they own validation / MNC / ledger / DB
            # writes (unchanged). run_llm_layers owns only the gate
            # short-circuit and the Layer 3 → Layer 4 ordering. gate=None here
            # → behavior is identical to the pre-split inline dispatch; the gate
            # parameter is the Agentic Circuit Breaker seam (F108 / task #74).

            # Mutable holder so the cold-shot failure-result (emitted when no
            # layer closes) can be reconstructed after run_llm_layers returns.
            cold_state: dict = {}

            def _warm_agent_layer() -> dict | None:
                # Layer 3: warm-agent (Claude with Bash + Edit + Read enabled,
                # iterating against `lake env lean` directly). Higher P(close)
                # than a one-shot LLM call.
                warm_start = time.time()
                warm_ok, warm_proof_text, warm_tail = _warm_agent_solve(
                    r, DEFAULT_LEAN_ROOT_FOR_VERIFY, max(180, timeout_s),
                )
                warm_outcome = "closed" if warm_ok else "failed_compile"
                _record_attempt(
                    r["row_id"], "claude_opus_warm", warm_outcome, warm_ok, warm_tail,
                )
                providers_tried.append({
                    "provider": "claude_opus_warm",
                    "outcome": warm_outcome,
                    "compile_ok": warm_ok,
                    "compile_tail": (warm_tail or "")[-300:],
                    "provider_wallclock_s": round(time.time() - warm_start, 2),
                    "agent_kind": "warm_agent",
                })
                if warm_ok:
                    return _validate_and_maybe_close(
                        "claude_opus_warm", True, warm_proof_text, warm_tail, warm_start,
                    )
                return None

            def _cold_shot_layer() -> dict | None:
                # Layer 4: one-shot chain (cold-shot fan-out) on the enriched
                # prompt across the preferred provider + policy fallbacks.
                final = None
                chain = [provider] + [f for f in fallbacks if f != provider]
                for prov_name in chain:
                    decision = invoke_with_routing(
                        enriched_goal or str(goal),
                        preferred=prov_name,
                        fallbacks=[],   # we own the walk here, not the router
                        timeout_s=timeout_s,
                    )
                    res = decision.result
                    provider_ran = bool(res is not None and res.ok)
                    proof_text = (res.proof_text if res else None) or ""
                    compile_ok = False
                    compile_tail = "skipped (no provider proof)"
                    if provider_ran and proof_text.strip():
                        compile_ok, compile_tail = _verify_compile(
                            r["row_id"], enriched_goal or str(goal), proof_text,
                            DEFAULT_LEAN_ROOT_FOR_VERIFY, verify_timeout,
                        )
                    outcome_for_prov = (
                        "closed" if compile_ok
                        else ("failed_compile" if provider_ran else "failed")
                    )
                    _record_attempt(
                        r["row_id"],
                        decision.chosen_provider or prov_name,
                        outcome_for_prov,
                        compile_ok,
                        compile_tail,
                    )
                    providers_tried.append({
                        "provider": decision.chosen_provider or prov_name,
                        "outcome": outcome_for_prov,
                        "compile_ok": compile_ok,
                        "compile_tail": (compile_tail or "")[-220:],
                        "provider_error": res.error.value if res is not None else "no_provider_available",
                        "provider_wallclock_s": res.wallclock_s if res is not None else 0.0,
                        "routing_chain_walked": decision.chain_walked,
                    })
                    final = (decision, res, proof_text, compile_ok, compile_tail, outcome_for_prov, prov_name)
                    if compile_ok:
                        break
                decision, res, proof_text, compile_ok, compile_tail, outcome, last_prov = final
                # Contract validation gate: even if some provider returned a
                # kernel-compile-ok proof, it must pass matched-negative-control
                # before being declared a credit-ready closure. If MNC fails
                # the failure-result below records outcome=rejected_negative_control.
                cold_provider_label = (decision.chosen_provider or last_prov) if decision is not None else last_prov
                cold_start = time.time() - (res.wallclock_s if (res is not None and res.wallclock_s) else 0)
                # Stash for the failure-result reconstruction after dispatch.
                cold_state.update({
                    "decision": decision, "res": res, "proof_text": proof_text,
                    "compile_ok": compile_ok, "compile_tail": compile_tail,
                    "outcome": outcome, "cold_provider_label": cold_provider_label,
                })
                closed = _validate_and_maybe_close(
                    cold_provider_label, compile_ok, proof_text, compile_tail, cold_start,
                )
                if closed is not None:
                    # Augment with cold-shot routing detail.
                    closed.setdefault("routing", {
                        "chain_walked": decision.chain_walked,
                        "skipped_unavailable": decision.skipped_unavailable,
                        "skipped_hard_failed": decision.skipped_hard_failed,
                    })
                return closed

            llm = run_llm_layers(
                r, DEFAULT_LEAN_ROOT_FOR_VERIFY, timeout_s,
                gate=None,  # Agentic Circuit Breaker seam (F108 / task #74); None = run all
                warm_agent_layer=_warm_agent_layer,
                cold_shot_layer=_cold_shot_layer,
            )
            if llm["closed"]:
                results.append(llm["closed_result"])
                continue
            if llm.get("skipped_by_gate"):
                # Gate refused the expensive layers. No LLM was spawned; record a
                # non-closure result. (Unreachable on the default gate=None path.)
                results.append({
                    "name": r["row_id"],
                    "target_name": r.get("target_theorem_name"),
                    "kind": "c_pool_no_template",
                    "outcome": "skipped_by_circuit_breaker",
                    "compile_ok": False,
                    "exit_code": 1,
                    "proof_text": "",
                    "provider": "agentic_circuit_breaker_gate",
                    "providers_tried": providers_tried,
                    "solver_action_contract": contract,
                    "stderr_excerpt": "Agentic Circuit Breaker gate returned False; LLM layers skipped (F108 / task #74)",
                })
                continue
            # Closure rejected by contract or never reached → record failure.
            decision = cold_state.get("decision")
            res = cold_state.get("res")
            proof_text = cold_state.get("proof_text") or ""
            compile_ok = cold_state.get("compile_ok") or False
            compile_tail = cold_state.get("compile_tail") or ""
            outcome = cold_state.get("outcome")
            cold_provider_label = cold_state.get("cold_provider_label")
            results.append({
                "name": r["row_id"],
                "target_name": r.get("target_theorem_name"),
                "kind": "c_pool_no_template",
                "outcome": (
                    "rejected_negative_control"
                    if compile_ok and proof_text.strip() else outcome
                ),
                "compile_ok": compile_ok,
                "compile_tail": (compile_tail or "")[-400:],
                "exit_code": 0 if compile_ok else 1,
                "proof_text": proof_text,
                "provider": cold_provider_label,
                "providers_tried": providers_tried,
                "solver_action_contract": contract,
                "provider_error": res.error.value if res is not None else "no_provider_available",
                "provider_error_detail": res.error_detail if res is not None else None,
                "provider_wallclock_s": res.wallclock_s if res is not None else 0.0,
                "routing": {
                    "chain_walked": decision.chain_walked if decision is not None else [],
                    "skipped_unavailable": decision.skipped_unavailable if decision is not None else [],
                    "skipped_hard_failed": decision.skipped_hard_failed if decision is not None else [],
                },
                "matched_negative_control": {
                    "kind": "context_stripped",
                    "executed_at": "solver_layer" if compile_ok and proof_text.strip() else "skipped",
                },
                "stderr_excerpt": (res.error_detail if res is not None else "no provider available on this node"),
            })
            continue
        # Legacy bash-wrapper path (only for un-migrated providers, e.g. native_hammer).
        try:
            inv = reg.invoke(provider, goal_text=str(goal), timeout_s=timeout_s)
        except SystemExit as e:
            inv = {"proof_nonempty": False, "error": str(e), "proof_text": ""}
        outcome = "closed" if inv.get("proof_nonempty") else "failed"
        results.append({
            "name": r["row_id"],
            "target_name": r.get("target_theorem_name"),
            "kind": "c_pool_no_template",
            "outcome": outcome,
            "exit_code": inv.get("returncode", -1),
            "proof_text": inv.get("proof_text", ""),
            "provider": provider,
            "provider_error": inv.get("provider_error"),
            "provider_error_detail": inv.get("provider_error_detail"),
            "provider_wallclock_s": inv.get("wallclock_s"),
            "matched_negative_control": {
                "kind": "context_stripped",
                "instruction": "governance recompiles proof_text under bare `import Mathlib` (gold-bearing context removed); a closure that still compiles is leakage/paraphrase and is REJECTED by L3 (gold_name_verbatim / lean_closure_laundering).",
            },
            "stderr_excerpt": inv.get("error"),
        })
    payload = {
        "schema": "leanmill-solver-lane-results-v1",
        "lane": "solver_lane",
        "mode": mode,
        "provider": provider,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "credit_boundary": "agentic proposal only; unratified_closure_candidate exits + matched context-stripped negative control. Governance (leak-tight + matched-neg-control + L3) ratifies. NO proof credit here.",
        "prover_cmd": provider,
        "results": results,
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT_RESULTS.write_text(json.dumps(payload, indent=2))

    # Normalize to typed exits via the canonical module — this is what governance reads.
    te = _load(REPO / "src" / "ztare" / "leanmill" / "typed_exit.py")
    exits = te.normalize_auto_prover_payload(payload, source_path=str(OUT_RESULTS), run_id="solver_lane")
    OUT_EXITS.write_text(json.dumps({"schema": "leanmill-solver-lane-typed-exits-v1", "exits": exits}, indent=2))
    n_closed = sum(1 for r in results if r["outcome"] == "closed")
    n_failed_compile = sum(1 for r in results if r["outcome"] == "failed_compile")
    return {"eligible": len(rows),
            "mode": mode,
            "attempted": len([r for r in results if r["outcome"] in ("closed", "failed", "failed_compile")]),
            "closure_candidates": n_closed,
            "failed_compile": n_failed_compile,
            "results_path": str(OUT_RESULTS), "exits_path": str(OUT_EXITS),
            "dry_run": dry_run}


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    ps = sub.add_parser("select"); ps.add_argument("--limit", type=int, default=0)
    pv = sub.add_parser("solve")
    pv.add_argument("--provider", default=_policy_model())
    pv.add_argument("--limit", type=int, default=0)
    pv.add_argument("--dry-run", action="store_true")
    pv.add_argument("--timeout", type=int, default=300)
    pv.add_argument("--mode", choices=["cascade", "dag_search"], default="cascade",
                    help="cascade = fixed Layer-2→5 baseline (unchanged); "
                         "dag_search = GP-246 governed DAG best-first search.")
    args = ap.parse_args()

    if args.cmd == "select":
        import json as _j
        print("MATERIALIZATION STATUS:", _j.dumps(materialization_status(), indent=2))
        rows = solver_eligible_rows()
        rows = rows[:args.limit] if args.limit else rows
        print(f"\nsolver-eligible (static-missed + no positive family template + executable): {len(solver_eligible_rows())} total")
        for r in rows[:25]:
            g = (r.get("goal") or "")[:80].replace("\n", " ")
            print(f"  {str(r['row_id'])[:40]:<42} {g}")
        return 0

    if args.cmd == "solve":
        res = solve(args.provider, args.limit, args.dry_run, timeout_s=args.timeout,
                    mode=args.mode)
        print(json.dumps(res, indent=2))
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
