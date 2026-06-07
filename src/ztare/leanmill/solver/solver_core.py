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
import os
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
# Durable closure-certificate ledger. The ProofCache (`proof_cache.py`, the COMPRESS store in
# docs/concepts/leanmill_architecture.md) is the system-of-record for the PROOF TEXT; this co-persists
# the AUDIT context per ad-hoc closure — the governance-kernel verdict, the matched negative control,
# and the EXACT recompilable probe (the .lean that compiled clean) — so any closure is fully auditable
# from ONE durable, tracked record. Fixes the gap where solve_adhoc returned proof_text + governance in
# its result dict but ad-hoc callers (e.g. spectral_baseline) discarded them and the leaf's substrate
# RobustProbe was overwritten by the next run — leaving only /tmp scratch. Append-only JSONL.
ADHOC_CLOSURE_CERTIFICATES = OUT_DIR / "adhoc_closure_certificates.jsonl"


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
    # Partial-progress telemetry (GP-187): additive columns so a best-first / DAG search has a gradient
    # to climb instead of a binary compile_ok. Migrate older DBs in place (no-op once columns exist).
    have = {r[1] for r in con.execute("PRAGMA table_info(attempts)").fetchall()}
    for col, decl in (("goals_remaining", "INTEGER"), ("error_class", "TEXT"),
                      ("progress", "REAL"),
                      # ratified = the GOVERNANCE verdict (NULL=not-yet-governed, 1=ratified, 0=rejected).
                      # compile_ok is the solver PROPOSAL; ratified is what the rating layer (Brier/Elo)
                      # scores, so gamed-then-rejected closures count as losses (2026-06-04 FP fix).
                      ("ratified", "INTEGER"),
                      # est_p_close = the move-policy's forecast AT DISPATCH TIME (skin-in-the-game).
                      ("est_p_close", "REAL"),
                      # move-yield shape (2026-06-06): the CANONICAL move (not the raw provider — cold/frontier
                      # logged the provider name, losing move identity); per-move wall TIME (yield-per-second,
                      # the throughput dimension); and a run_tag to slice A/B arms vs production. Additive.
                      ("move", "TEXT"), ("wallclock_s", "REAL"), ("run_tag", "TEXT")):
        if col not in have:
            con.execute(f"ALTER TABLE attempts ADD COLUMN {col} {decl}")
    # BACKFILL `move` for HISTORICAL rows (the provider was always stored, and provider→move is
    # deterministic) — so the new per-move shape applies to the full 621-row history, not just new rows.
    # `wallclock_s`/`run_tag` were NEVER recorded historically ⇒ they stay NULL for old rows (only new
    # rows populate). Runs once (guarded by `move` being freshly added); idempotent via `WHERE move IS NULL`.
    if "move" not in have:
        try:
            from ztare.leanmill.solver.move_calibration import PROVIDER_TO_MOVE
            for _prov, _mv in PROVIDER_TO_MOVE.items():
                con.execute("UPDATE attempts SET move=? WHERE move IS NULL AND provider=?", (_mv, _prov))
            # providers NOT in the closure map (specialize/conjecture_lemma/falsify) → the provider IS the
            # move label (matches the going-forward auto-derivation PROVIDER_TO_MOVE.get(provider, provider))
            con.execute("UPDATE attempts SET move=provider "
                        "WHERE move IS NULL AND provider IS NOT NULL AND provider!=''")
            con.commit()
        except Exception:  # noqa: BLE001 — backfill is best-effort; a map import error must not break the DB
            pass
    return con


def _record_governance_verdict(row_id: str, ratified: bool, since: str | None = None) -> int:
    """Stamp the governance RATIFICATION verdict onto THIS RUN's not-yet-governed attempts. A probe
    that compiled (compile_ok=1) but was `rejected_governance` is ratified=0 — so the rating layer
    scores RATIFIED outcomes, not raw compile_ok. `since` (a run-start ISO timestamp) SCOPES the
    stamp to this run's attempts (avoids over-stamping prior runs). Returns rows stamped."""
    with _attempts_conn() as con:
        if since:
            cur = con.execute(
                "UPDATE attempts SET ratified=? WHERE row_id=? AND ratified IS NULL "
                "AND compile_ok=1 AND attempt_at>=?",
                (1 if ratified else 0, row_id, since))
        else:
            cur = con.execute(
                "UPDATE attempts SET ratified=? WHERE row_id=? AND ratified IS NULL AND compile_ok=1",
                (1 if ratified else 0, row_id))
        con.commit()
        return cur.rowcount


def _row_already_closed(row_id: str) -> bool:
    # Only a ratified (or not-yet-governed) compile_ok=1 counts as closed — a governance-REJECTED
    # closure (compile_ok=1, ratified=0) must NOT filter the row out forever (it wasn't a real closure).
    with _attempts_conn() as con:
        r = con.execute(
            "SELECT 1 FROM attempts WHERE row_id=? AND compile_ok=1 "
            "AND (ratified IS NULL OR ratified=1) LIMIT 1",
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
                    compile_ok: bool, notes: str | None,
                    proof_state: dict | None = None,
                    est_p_close: float | None = None,
                    move: str | None = None,
                    wallclock_s: float | None = None) -> None:
    # est_p_close = the move-policy's forecast at dispatch time. When the caller didn't pass one (the
    # CASCADE sites), DERIVE it from the provider via the SAME calibrated prior the policy uses
    # (PROVIDER_TO_MOVE → _move_prior) — uniform forecast loop across all modes in ONE place.
    # `move` (the CANONICAL move) is auto-derived from the provider when not passed (PROVIDER_TO_MOVE maps
    # cold/frontier raw provider names → their move; everything else IS its move label). run_tag slices runs.
    _move_label = move
    if provider:
        try:
            from ztare.leanmill.solver.move_calibration import PROVIDER_TO_MOVE
            if _move_label is None:
                _move_label = PROVIDER_TO_MOVE.get(provider, provider)
            if est_p_close is None:
                from ztare.leanmill.solver.governed_dag_search import _move_prior
                _mv = PROVIDER_TO_MOVE.get(provider)
                if _mv is not None:
                    est_p_close = _move_prior(_mv)
        except Exception:
            pass
    _run_tag = os.environ.get("ZTARE_SOLVER_RUN_TAG") or None
    if proof_state is None:
        from ztare.leanmill.solver.proof_state import proof_state_signal
        proof_state = proof_state_signal(0 if compile_ok else 1, notes or "")
    with _attempts_conn() as con:
        con.execute(
            "INSERT INTO attempts (row_id, attempt_at, provider, outcome, compile_ok, "
            "notes, goals_remaining, error_class, progress, est_p_close, move, wallclock_s, run_tag) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (row_id, datetime.now(timezone.utc).isoformat(), provider or "",
             outcome, 1 if compile_ok else 0,
             (notes or "")[-1000:],
             proof_state.get("goals_remaining"), proof_state.get("error_class"),
             proof_state.get("progress"), est_p_close, _move_label, wallclock_s, _run_tag),
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
    source_text = ""
    shelf_lean_root = None
    if src_path_str:
        src_path = Path(src_path_str)
        if src_path.exists():
            try:
                source_text = src_path.read_text(encoding="utf-8", errors="replace")
            except Exception:
                source_text = ""
            # lake project root for import resolution (the in-scope citation leg resolves
            # `import ZtareProofs.X` → <root>/ZtareProofs/X.lean): walk up to the dir holding ZtareProofs/.
            for _p in [src_path.parent, *src_path.parents]:
                if (_p / "ZtareProofs").is_dir() or (_p / "lakefile.lean").exists() \
                        or (_p / "lake-manifest.json").exists():
                    shelf_lean_root = _p
                    break
    prelude = ""
    if source_text and target_name:
        text = source_text
        if True:
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
            shelf = build_semantic_premise_shelf(base_goal, top_k_mathlib=8, top_k_apn=3, top_k_ns=0,
                                                  source=source_text, lean_root=shelf_lean_root)
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
    # RCA fix 2026-06-04: library search FIRST. The cascade had no `exact?`, so a goal closable by a
    # single in-scope/IMPORTED lemma (`exact <existing_lemma>`) could never close — the hammer
    # ring-bashed and timed out (observed on indicatorTranslationInteriorTerm_…_of_memLp, whose
    # conclusion is identical to an imported lemma + an unused hypothesis). `exact?` is Lean's own
    # library search; it closes the goal when a matching term exists. The memoization principle made
    # concrete: cite the library you have before re-deriving from scratch.
    "exact?",
    # Analysis/measure-theory automation (RCA 2026-06-04): the cascade was algebra/logic-tuned
    # (ring/omega/nlinarith/aesop) with ZERO analysis automation, yet NS Track-B goals are eLpNorm /
    # measurability / monotonicity. gcongr (generalized monotone congruence — e.g. eLpNorm_mono_measure
    # shape), measurability, and fun_prop are the analysis workhorses an NS goal needs.
    "gcongr",
    "fun_prop",
    "measurability",
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
    # PER-MOVE CAP (ZTARE_LEANMILL_PERMOVE_CAPS=1, default-off=parity): the legacy per_tactic = timeout_s/N
    # is a FRACTION of the total that, summed over the 18-tactic cascade, runs ~400s and lets native_hammer
    # monopolise the whole per-target wallclock (the starvation leak — _cap on the outer arg was divided away
    # here). ON ⇒ treat `timeout_s` as the cascade's TOTAL DEADLINE: fixed per-tactic slice + STOP once the
    # cumulative budget is spent (the last tactic is clipped to fit), so native is bounded by its cap.
    import time as _t_nh
    _caps_on = os.environ.get("ZTARE_LEANMILL_PERMOVE_CAPS") != "0"   # DEFAULT-ON 2026-06-07 (=0 reverts)
    _nh_start = _t_nh.time()
    if _caps_on:
        per_tactic_timeout = 30   # fixed slice; the TOTAL is bounded by the deadline check below
    transcript = []
    for tactic in _NATIVE_HAMMER_TACTICS:
        if _caps_on:
            _rem = timeout_s - (_t_nh.time() - _nh_start)
            if _rem <= 5:
                transcript.append(f"[native_hammer] cap deadline {timeout_s}s reached — cascade stopped")
                break
        # Library-search tactics scan the WHOLE environment (incl. imported files) → slower than a
        # fixed tactic; give them ≥60s or they time out before finding an in-scope citation. Observed:
        # `exact?` closes the indicatorTranslationInteriorTerm bridge in ~22s, > the 20s uniform floor —
        # without this the RCA fix would itself still time out (RCA 2026-06-04).
        tac_timeout = max(60, per_tactic_timeout) if tactic in ("exact?", "apply?") else per_tactic_timeout
        if _caps_on:
            tac_timeout = min(tac_timeout, max(10, int(_rem)))   # clip the slice to the remaining cap
        compile_ok, tail = _verify_compile(
            row.get("row_id", "anon"),
            enriched or base_goal,
            tactic,
            lean_root,
            tac_timeout,
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
                                     lean_root: Path, timeout_s: int,
                                     goal_type: str | None = None) -> tuple[bool, str]:
    """Run the matched negative control: does proof_text close the goal under bare `import Mathlib`
    (WITHOUT the source file's prelude)? If yes, the proof was a single-Mathlib-lookup — laundering.

    Returns (negative_control_ok, tail). negative_control_ok=True means the negative control FAILED
    (good — the proof needs the prelude, so it is NOT a bare-Mathlib lookup → no leakage).

    `goal_type` is REQUIRED for a meaningful test — the row's goal string `"<binders> : <type>"`
    (already includes the `:`). The stripped attempt is `theorem X_stripped <goal> := by <body>`.
    Without it the stub was ill-formed → never compiled → MNC always "passed" (a structural NO-OP
    that never caught leakage). FAIL-OPEN discipline: a tooling error or a goal that can't even be
    stated under bare Mathlib (unknown-identifier — the target NEEDS prelude defs) is INCONCLUSIVE →
    return True (do not reject; the kernel v33 leakage organs are the real leakage check)."""
    if not target_name or not proof_text.strip():
        return True, "inconclusive: missing target or proof"
    g = (goal_type or "").strip()
    if not g or g == target_name:   # no real type (bare name fallback) → can't build a valid attempt
        return True, "inconclusive: no goal_type (cannot build a well-formed stripped attempt)"
    if ":" not in g:                 # a bare type with no binders/colon → prepend the type colon
        g = ": " + g
    body = proof_text.strip()
    if body.startswith("by "):
        body = body[3:]
    src = (
        "import Mathlib\n\n"
        f"-- matched negative control: state the goal under bare Mathlib (no prelude) + the candidate\n"
        f"-- body. If THIS compiles, proof_text was a bare-Mathlib lookup → leakage.\n"
        f"theorem {target_name}_stripped_attempt {g} := by\n"
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
            # Goal not even STATABLE under bare Mathlib (needs prelude defs) → inconclusive, not leakage.
            if re.search(r"unknown (identifier|constant|declaration)", output):
                return True, "inconclusive: goal needs prelude defs (unknown identifier under bare Mathlib)"
            stripped_compiled = proc.returncode == 0 and "error:" not in output
            return (not stripped_compiled), output[-600:]
    except subprocess.TimeoutExpired:
        return True, "inconclusive: negctrl_timeout (fail-open, not a leakage verdict)"
    except FileNotFoundError as exc:
        return True, f"inconclusive: lake_not_on_PATH ({exc!s}) — fail-open"
    except Exception as exc:  # noqa: BLE001
        return True, f"inconclusive: negctrl_exception ({exc!r}) — fail-open"


def _validate_against_contract(
    contract: dict,
    proof_text: str,
    enriched_goal: str,
    target_name: str,
    lean_root: Path,
    timeout_s: int,
    kernel_compile_ok: bool,
    kernel_compile_tail: str,
    goal_type: str | None = None,
) -> dict:
    """Run every required receipt named in the contract and return a structured
    verdict. A closure is credit-ready iff every required receipt passes.

    The MNC check is run here (not deferred to governance) so the solver lane
    rejects laundering at solve-time, not after the typed-exit has propagated.
    `goal_type` (the row's `"<binders> : <type>"`) makes the MNC well-formed.
    """
    receipts: dict[str, dict] = {}
    receipts["kernel_compile_receipt"] = {
        "passed": bool(kernel_compile_ok),
        "tail": (kernel_compile_tail or "")[-400:],
    }
    # MNC: only meaningful if compile passed (no point negctrl-ing a non-closure)
    if kernel_compile_ok:
        mnc_ok, mnc_tail = _verify_matched_negative_control(
            target_name, proof_text, lean_root, timeout_s, goal_type=goal_type
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
    # ── AUTHORITATIVE KERNEL (2026-06-06; default ON, ZTARE_KERNEL_AUTHORITATIVE=0 reverts to kc∧mnc) ──
    # The solver-lane gate used to ratify on kernel-compile ∧ MNC and DEFER the anti-laundering organ stack
    # (vacuity / gold-name / single-lemma / leakage / consequence / currency / statement-integrity) to the
    # downstream worker — the deferral that let the warm-path statement-alteration through. We now fold the
    # ONE canonical kernel (`run_anti_laundering_kernel` — the SAME stack solve_adhoc uses; NO reduced
    # per-mode reimplementation) into solve-time `credit_ready`, so a CONFIRMED laundering organ blocks at
    # the solver lane. De-risked by the observe corpus (6/6 real closures → kernel_would_block=False).
    # FAIL-OPEN on an organ crash (a tooling error must NOT block a valid closure); fail-CLOSED only on a
    # CONFIRMED organ flag (kernel.passed=False). Reversible to the pre-flip behavior via the env escape.
    kernel_passed = True
    if kernel_compile_ok and os.environ.get("ZTARE_KERNEL_AUTHORITATIVE", "1") != "0":
        try:
            import json as _json
            from ztare.gates.lean_proof_gate import run_anti_laundering_kernel as _kernel
            _body = (proof_text or "").strip()
            if (enriched_goal or "").rstrip().endswith(":= by"):
                _b = _body[3:].lstrip() if _body.startswith("by ") else _body
                _src = f"{enriched_goal}\n  {_b}\n"
            else:
                _src = f"{enriched_goal}\n{_body}\n"
            if not _src.lstrip().startswith("import"):
                _src = "import Mathlib\n\n" + _src
            # Full Cage routing (GP-086 Phase 6, ZTARE_LEANMILL_CAGE_ROUTING=1; default-OFF). When on, the
            # anti-laundering verdict is dispatched through the ONE Cage orchestrator (`leanmill_cage`);
            # behavior-IDENTICAL by construction (the routed gate IS run_anti_laundering_kernel — regression-
            # checked), so the flip is reversible. Off ⇒ the direct kernel call (byte-parity).
            if os.environ.get("ZTARE_LEANMILL_CAGE_ROUTING") == "1":
                from ztare.leanmill.solver.leanmill_cage import govern_via_cage as _gvc
                _k = _gvc(_src, lean_root / "_kernel.lean", lean_root,
                          original_source=enriched_goal, target_name=target_name)
            else:
                _k = _kernel(_src, lean_root / "_kernel.lean", lean_root,
                             original_source=enriched_goal, target_name=target_name)
            kernel_passed = bool(_k.get("passed"))
            receipts["governance_kernel_receipt"] = {
                "passed": kernel_passed, "confirmed": _k.get("confirmed"), "flags": _k.get("flags"),
                "interpretation": ("PASS = no CONFIRMED anti-laundering organ fired"
                                   if kernel_passed else f"FAIL = confirmed: {_k.get('confirmed')}")}
            with (OUT_DIR / "kernel_parity.jsonl").open("a", encoding="utf-8") as _f:
                _f.write(_json.dumps({"target": target_name,
                                      "hand_wired": {"kc": receipts["kernel_compile_receipt"]["passed"],
                                                     "mnc": receipts["matched_negative_control_receipt"]["passed"]},
                                      "kernel": {"passed": kernel_passed, "confirmed": _k.get("confirmed")},
                                      "kernel_blocked": (kernel_passed is False)}) + "\n")
        except Exception as _e:  # noqa: BLE001 — FAIL-OPEN: an organ crash must not block a valid closure
            receipts["governance_kernel_receipt"] = {"passed": True,
                                                     "tail": f"fail-open (organ error): {repr(_e)[:120]}"}
    else:
        receipts["governance_kernel_receipt"] = {"passed": None,
                                                 "tail": "skipped (no compile, or ZTARE_KERNEL_AUTHORITATIVE=0)"}

    all_required_pass = all(
        bool(receipts[r["name"]]["passed"]) is True
        for r in contract.get("required_receipts", [])
        if r.get("required") and receipts[r["name"]]["passed"] is not None
    )
    credit_ready = (
        kernel_compile_ok
        and receipts["matched_negative_control_receipt"]["passed"] is True
        and kernel_passed  # AUTHORITATIVE: a confirmed anti-laundering organ blocks the closure at solve-time
    )
    return {
        "contract_schema": contract.get("schema"),
        "receipts": receipts,
        "credit_ready_at_solver_layer": bool(credit_ready),
        "required_receipts_all_passed_at_solver_layer": bool(all_required_pass),
        "downstream_required": "leanmill_proof_audit (axiom_allowlist + L3) before factory credit",
    }


def _agentic_leaf_warm_solve(row: dict, lean_root: Path, timeout_s: int) -> tuple[bool, str, str]:
    """Flag-gated (ZTARE_AGENTIC_LEAF=1) warm solve via the validated `agentic_leaf` primitive.
    Calibration-first (provider + substrate liveness ⇒ a dead instrument returns INADMISSIBLE,
    never a fake negative) + best-of-N across codex+claude + independent axiom-allowlist gate.
    Returns the worker's (compile_ok, proof_text, transcript_tail) contract. §6n review pending."""
    import re as _re
    from ztare.leanmill.solver.agentic_leaf import solve_robust
    target = row.get("target_theorem_name") or ""
    base_goal = (row.get("goal") or "").strip()
    body = "\n".join(l for l in Path(row["source_file"]).read_text(encoding="utf-8", errors="replace").splitlines()
                     if not l.strip().startswith("import "))
    mt = _re.search(rf"(?m)^\s*(?:theorem|lemma)\s+{_re.escape(target)}\b", body)
    defs = body[:mt.start()].rstrip() if mt else body
    mg = _re.search(rf"(?ms)^\s*(?:theorem|lemma)\s+{_re.escape(target)}\b\s*:\s*(.+?)\s*:=", body)
    goal = mg.group(1).strip() if mg else base_goal
    # GAP-REFINE: prepend the (Lean-comment) refine context — the leaf's own unsolved goals + prior
    # attempt + the premise shelf it otherwise ignores — so the strongest move stops running starved.
    # Comments only ⇒ inert at compile; the agent reads them as guidance. Empty unless the caller set it.
    _rc = (row.get("_refine_context") or "").strip()
    if _rc:
        defs = _rc + "\n\n" + defs
    # CEGIS no-good INFORMING (M2). DEFAULT-ON (disable via ZTARE_LEANMILL_NOGOOD=0): sound by
    # construction — it only INFORMS (comment-inert at compile; a no-op on a fresh store), can NEVER
    # prune/suppress a closable path, and adds no move-budget cost, so default-ON only ever helps.
    # Prepend a Lean-comment block of CONFIRMED prior refutations so the leaf never re-explores a dead
    # region. Best-effort (a store error is silent, never fails the solve).
    if os.environ.get("ZTARE_LEANMILL_NOGOOD") != "0":
        try:
            from ztare.leanmill.solver.no_good_store import NoGoodStore as _NGS
            _ngb = _NGS(OUT_DIR / "solver_lane_no_good_store.jsonl").prompt_block(goal)
            if _ngb:
                defs = _ngb + "\n\n" + defs
        except Exception:  # noqa: BLE001 — informing is best-effort; never fail the solve
            pass
    r = solve_robust(goal, defs=defs, project_dir=str(lean_root), repo=str(lean_root),
                     lake_bin="lake", providers=("codex", "claude"), target=target,
                     timeout=timeout_s, decompose=True)
    if r.inadmissible:
        return False, "", f"INADMISSIBLE (uncalibrated instrument, not a real negative): {r.reason}"
    if not r.closed:
        return False, "", f"agentic_leaf open: {r.reason}"
    winner = (r.calibration.get("best_of") or {}).get("winner", "codex")
    probe = lean_root / f"RobustProbe_{winner}_0.lean"
    proof = ""
    ptxt = ""
    if probe.exists():
        ptxt = probe.read_text(encoding="utf-8", errors="replace")
        pm = _re.search(rf"(?ms)theorem\s+{_re.escape(target)}\b.*?:=\s*(by.*?)(?:\n#print|\Z)", ptxt)
        proof = pm.group(1).strip() if pm else ""
    # STATEMENT-INTEGRITY AT SOLVE TIME (2026-06-06, found by the strategist-lift false control). The
    # agent edits a WHOLE probe file, so it can keep the theorem NAME but ALTER the statement — e.g. on a
    # false goal it proved `¬ ∀ n, …` under the original name, and the DAG ratified `closed` because the
    # solver-layer gate was kernel∧MNC only (statement_integrity was DEFERRED to the downstream worker).
    # The warm/agentic-leaf path is the one move that trusts a self-edited file (cold/frontier recompile
    # against the ORIGINAL goal), so it must run the integrity diff HERE. A laundered statement ⇒ NOT a
    # closure (honest negative), never a ratified close. The gate allows ADDED helper decls; it rejects
    # only an altered target signature / tampered depended-on decl. See statement_integrity.check.
    if ptxt:
        from ztare.leanmill.solver import statement_integrity as _si
        try:
            _orig_src = Path(row["source_file"]).read_text(encoding="utf-8", errors="replace")
            _verdict = _si.check(_orig_src, ptxt, target)
        except Exception as _e:  # noqa: BLE001  — integrity tooling failure must not mint a closure
            return False, "", f"statement_integrity ERROR (fail-closed, no closure): {_e!r}"
        if not _verdict.ok:
            # CEGIS RECORD + obstruction→conjecture SEED (M2). The integrity verdict is a CONFIRMED cheat
            # (the exogenous decl-diff organ) — record it as a no-good (informs future leaf prompts) and
            # extract a TARGETED conjecture seed (the refutation→construction dual: the altered decl
            # LOCALIZES the sound bridge lemma the cheat shadowed). Additive — the honest negative below is
            # unchanged. Default off = PARITY. record_integrity_verdict fails OPEN on ok=True (a sound probe
            # never becomes a no-good); seeds_from_refutation returns [] on a clean probe.
            if os.environ.get("ZTARE_LEANMILL_NOGOOD") != "0":
                try:
                    from ztare.leanmill.solver.no_good_store import NoGoodStore as _NGS
                    _NGS(OUT_DIR / "solver_lane_no_good_store.jsonl").record_integrity_verdict(
                        goal, _verdict, source=f"agentic_leaf:{target}")
                    from ztare.leanmill.solver import obstruction_to_conjecture as _o2c
                    _seeds = _o2c.seeds_from_refutation(_orig_src, ptxt, target)
                    if _seeds:  # stash on the row so a later MOVE_CONJECTURE on this node targets the obstruction
                        row["_obstruction_seeds"] = [{"prompt": s.targeted_prompt,
                                                      "next_target": s.next_target_statement} for s in _seeds]
                except Exception:  # noqa: BLE001 — recording/extraction is best-effort; never block the negative
                    pass
            return False, "", ("statement_integrity FAILED (laundering blocked at solve time): "
                               + "; ".join(_verdict.violations)[:240])
    return True, proof, f"agentic_leaf closed by {winner} (rounds={r.rounds}, decomposed={r.decomposed})"


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
    # §6n FLIP 2026-06-02 (operator-authorized): route the warm solve through the validated
    # agentic_leaf primitive by DEFAULT. It adds calibration-first (provider+substrate liveness,
    # so a dead instrument can't masquerade as a real negative) + best-of-N across codex+claude +
    # independent axiom-allowlist gating. The agentic leaf is the frontier move generator (a SOTA
    # general model iterating against the kernel); the governed harness itself is the frontier
    # prover. Reversible: ZTARE_AGENTIC_LEAF=0 falls back to the legacy one-shot warm agent below.
    if os.environ.get("ZTARE_AGENTIC_LEAF", "1") != "0":
        return _agentic_leaf_warm_solve(row, lean_root, timeout_s)
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


def _build_refine_context(enriched_goal: str, prior_proof: str, unsolved_blocks: "list[str]") -> str:
    """The gap-refine guidance handed back to the warm leaf as LEAN COMMENTS: its own unsolved goals
    (the exogenous compiler residual), its prior attempt (refine, don't restart), and the premise
    shelf the warm move otherwise ignores. Comments compile inert; the agent reads them. Sound by
    construction — the kernel/MNC contract still gates any emitted proof, so no false-closure risk.
    Mirrors the working stepwise loop in proof_search.py (feed unsolved goals back), not an i.i.d. retry."""
    def _commented(text: str) -> str:
        return "\n".join("-- " + ln for ln in (text or "").splitlines() if ln.strip())
    parts = ["-- [gap-refine] Your previous whole-proof attempt did NOT close — the kernel left these "
             "goals UNSOLVED. Continue from this state; reuse what worked and discharge ONLY the residual:"]
    for b in (unsolved_blocks or [])[:3]:
        parts.append(_commented(b))
    if (prior_proof or "").strip():
        parts.append("-- [gap-refine] your previous proof attempt (refine it, do not restart from scratch):")
        parts.append(_commented(prior_proof))
    for seg in (enriched_goal or "").split("\n\n"):   # the premise shelf (already comment-formatted)
        if "candidate premises" in seg or "premise shelf" in seg:
            parts.append(seg.strip())
            break
    return "\n".join(parts) + "\n"


# MOVE_CONJECTURE generation + kernel-checked advance-test EXTRACTED to
# `src/ztare/leanmill/solver/conjecture.py` (task #42, first slice — general solver logic with no
# worker-internal deps). Imported function-level in `_build_dag_move_runner` below (after the src
# path is on sys.path, matching the existing governed_dag_search / agentic_leaf import pattern).


def _preamble_from_source(r: dict) -> str:
    """The source prelude BEFORE the target theorem (imports + depended-on defs/structures). Threaded
    into SPECIALIZE so a special case over bespoke defs (e.g. P1's RationalFunctionInJetVariables) still
    compiles self-contained. Returns '' if the source is absent/unreadable (⇒ bare `import Mathlib`)."""
    sp = r.get("source_file")
    if not sp:
        return ""
    try:
        txt = Path(sp).read_text(encoding="utf-8", errors="ignore")
    except Exception:  # noqa: BLE001
        return ""
    name = r.get("target_theorem_name") or ""
    if not name:
        return txt.rstrip()
    import re as _re_pre
    parts = _re_pre.split(
        r"(?m)^\s*(?:noncomputable\s+|private\s+|protected\s+)*(?:theorem|lemma)\s+" + _re_pre.escape(name) + r"\b",
        txt, maxsplit=1)
    return parts[0].rstrip() if len(parts) > 1 else txt.rstrip()


# ── Per-move ABSOLUTE leaf-timeout caps (move-starvation fix, 2026-06-06). The legacy per-move leaf
# timeouts are FRACTIONS of the total wallclock (verify_timeout = timeout_s//2; warm = verify_timeout*2 =
# ~the whole budget), so a single early move (native/warm) monopolises the wallclock and the loop breaks
# before move_policy can offer the tail (cold/frontier/conjecture/strategist/FALSIFY) — FALSIFY is offered
# 6th and was NEVER reached (diagnosis: projects/leanmill_experiments/strategist_lift/FALSIFY_DIAGNOSIS_
# 2026-06-06.md; prod DB: native+warm = 90% of attempts, only warm ever closes). _cap decouples each
# move's LEAF-GENERATION timeout from the total: DEFAULT-OFF (ZTARE_LEANMILL_PERMOVE_CAPS != "1") returns
# the legacy expr UNCHANGED (byte-identical parity); ON returns an absolute seconds cap so the full menu
# fits a sized wallclock. Per-move override: ZTARE_LEANMILL_CAP_<KEY>=secs. Caps the agent/prover call
# only (the dominant cost), NOT the kernel compile/gate timeouts (bounded ceilings, left on verify_timeout).
# Per-move leaf budget as a FRACTION of the run's TOTAL wallclock — the single budget knob — clamped to
# sane [floor, ceil] absolutes. NOT hardcoded seconds off an assumed 900s (the smell): these SCALE with
# whatever total the operator sets — minutes for an easy target, HOURS for an open problem. The fractions
# ARE the allocation policy (warm, the closer, gets the largest single-invocation share); the floor stops a
# move being starved on a short run; the ceil bounds a SINGLE invocation (an agentic leaf past ~30 min
# rarely closes what it hasn't) so a long run spends its hours on MANY moves, not one that never returns.
_PERMOVE_FRAC = {   # move: (fraction_of_wallclock, floor_s, ceil_s)
    "warm":          (0.40, 150, 1800),
    "native_hammer": (0.10,  45,  180),
    "cold_frontier": (0.20,  90,  900),
    "conjecture":    (0.15,  90,  900),
    "specialize":    (0.10,  60,  600),
    "generalize":    (0.15,  90,  900),
    "tactic_step":   (0.18, 120,  900),
    "falsify":       (0.15,  90,  600),
    "corroborate":   (0.15,  90,  600),   # Popper-dual of falsify; same shape (one leaf call + kernel gate)
    "witness_transport": (0.05, 30, 120),  # a bounded SymPy subprocess + one kernel compile — cheap + fast
}


def _permove_cap(move_key: str, legacy: int, wallclock: int) -> int:
    """Per-move leaf budget. Caps off (`ZTARE_LEANMILL_PERMOVE_CAPS=0`) ⇒ the legacy value (parity).
    Caps on ⇒ a FRACTION of the run's `wallclock`, clamped to the move's [floor, ceil] — so budgets scale
    with the operator's total instead of being hardcoded off 900. `ZTARE_LEANMILL_CAP_<MOVE>=secs` still
    pins an absolute override when you want one."""
    if os.environ.get("ZTARE_LEANMILL_PERMOVE_CAPS") == "0":   # DEFAULT-ON 2026-06-07
        return legacy
    _env = os.environ.get(f"ZTARE_LEANMILL_CAP_{move_key.upper()}")
    if _env and _env.isdigit():
        return int(_env)
    frac, floor, ceil = _PERMOVE_FRAC.get(move_key, (0.15, 45, max(120, legacy)))
    return int(min(ceil, max(floor, frac * max(0, wallclock))))


def _build_dag_move_runner(r: dict, contract: dict, enriched_goal: str,
                           verify_timeout: int, provider: str, fallbacks: list[str],
                           invoke_with_routing, providers_tried: list[dict], lean_root=None):
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
        MOVE_CONJECTURE, MOVE_SPECIALIZE, MOVE_GENERALIZE, MOVE_FALSIFY, MOVE_TACTIC_STEP,
        MOVE_CORROBORATE, MOVE_WITNESS_TRANSPORT,
    )
    from ztare.leanmill.solver.proof_state import proof_state_signal
    from ztare.leanmill.solver.conjecture import (conjecture_generate, conjecture_advances,
                                                   _lemma_conclusion)  # #42 slice

    target_name = r.get("target_theorem_name") or ""
    # The run's TOTAL wallclock (verify_timeout = timeout_s//2, so wallclock = verify_timeout*2). Per-move
    # caps are FRACTIONS of THIS — so the whole budget can be minutes or HOURS and the allocation scales,
    # nothing hardcoded off 900. `_cap` is a thin local capture so the call sites stay clean.
    _run_wallclock = verify_timeout * 2

    # BOOSTING (ZTARE_LEANMILL_BOOST=1; see governed_dag_search). The search loop tags a bottleneck node with
    # boost_factor>1; move_runner copies it here so _cap concentrates DEPTH on that node's move (a larger
    # per-move cap), bounded by the run wallclock so one node can't exceed the whole budget. Default 1.0 = the
    # cap is byte-identical to the un-boosted path (parity when the flag is off).
    _boost = {"factor": 1.0}

    def _cap(move_key: str, legacy: int) -> int:
        base = _permove_cap(move_key, legacy, _run_wallclock)
        f = _boost.get("factor", 1.0)
        if f <= 1.0:
            return base
        # Boost must be MONOTONE NON-DECREASING vs the un-boosted base: `max(base, …)` guards the case where a
        # move's FLOOR already exceeds the run wallclock (e.g. the warm floor 150 > a short run's wallclock
        # 120), where a bare `min(base*f, wallclock)` would clamp BELOW base and shrink the closer's budget on
        # exactly the bottleneck node boosting is meant to help (bug found 2026-06-07). Still wallclock-capped.
        return max(base, min(int(base * f), int(_run_wallclock)))

    def _ps(compile_ok: bool, tail: str) -> dict:
        """Partial-progress gradient (GP-187) for the DAG search, parsed from the
        SAME compile tail the move already produced (zero extra compile). A
        non-closing move that left 1 goal scores ~0.5 → the search keeps investing
        in that node instead of treating every non-closure as identical."""
        s = proof_state_signal(0 if compile_ok else 1, tail or "")
        return {"goals_remaining": s["goals_remaining"], "progress": s["progress"],
                "error_class": s["error_class"]}

    def _govern(proof_text: str, compile_ok: bool, compile_tail: str) -> tuple[bool, bool]:
        """Run the existing contract validation; return (kernel_clean, mnc_passed)."""
        if not compile_ok or not proof_text.strip():
            return False, False
        validation = _validate_against_contract(
            contract=contract, proof_text=proof_text, enriched_goal=enriched_goal,
            target_name=target_name, lean_root=(lean_root or DEFAULT_LEAN_ROOT_FOR_VERIFY),
            timeout_s=verify_timeout, kernel_compile_ok=compile_ok,
            kernel_compile_tail=compile_tail, goal_type=r.get("goal"),
        )
        kc = validation["receipts"]["kernel_compile_receipt"]["passed"]
        mnc = validation["receipts"]["matched_negative_control_receipt"]["passed"]
        return bool(kc), bool(mnc)

    def move_runner(node, move, budget):
        start = time.time()
        # BOOSTING: adopt this node's per-move cap multiplier (1.0 when the flag is off / node not a
        # bottleneck) so every _cap(...) call inside this move sees the boosted budget. Reset per move.
        _boost["factor"] = float(getattr(node, "boost_factor", 1.0) or 1.0)
        # the move-policy's forecast for THIS move at dispatch time (recorded → true-forecast Brier)
        try:
            from ztare.leanmill.solver.governed_dag_search import _move_prior as _mp
            fc = _mp(move)
        except Exception:
            fc = None
        # #35 decomposition (ZTARE_CONJECTURE_DECOMPOSE=1; default off = PARITY). For a SPAWNED sub_goal
        # node (a conjectured/decomposed lemma L), the generators must prove L = node.goal_text, NOT
        # re-prove the root goal G — the inertness fix (adversarial review w1162vqnh found every generator
        # re-proved G, so the conjecture move was a no-op). Default off ⇒ _eff_goal/_eff_row collapse to
        # the current (G / r) values BYTE-IDENTICALLY; the ON-path needs real decomposition validation.
        _spawned = bool(os.environ.get("ZTARE_CONJECTURE_DECOMPOSE") == "1"
                        and node.kind == "sub_goal" and node.node_id != "n0_root"
                        and (node.goal_text or "").strip())
        _eff_goal = node.goal_text if _spawned else (enriched_goal or node.goal_text)

        def _eff_row():
            if not _spawned:
                return r
            import re as _re3
            _nr = dict(r)
            _nr["goal"] = node.goal_text
            _mm = _re3.search(r"(?:theorem|lemma)\s+([A-Za-z_][\w'.]*)", node.goal_text or "")
            if _mm:
                _nr["target_theorem_name"] = _mm.group(1)
            return _nr

        if move == MOVE_NATIVE_HAMMER:
            ok, proof, tail = _native_hammer_probe(
                _eff_row(), (lean_root or DEFAULT_LEAN_ROOT_FOR_VERIFY),
                _cap("native_hammer", min(180, verify_timeout)),
            )
            proof_text = f"by {proof}" if proof else ""
            kc, mnc = _govern(proof_text, ok, tail) if ok else (False, False)
            _record_attempt(r["row_id"], "native_hammer",
                            "closed" if (kc and mnc) else "failed_compile", kc and mnc, tail,
                            est_p_close=fc, wallclock_s=round(time.time() - start, 2))
            providers_tried.append({"provider": "native_hammer",
                                    "outcome": "closed" if (kc and mnc) else "failed_compile",
                                    "compile_ok": kc, "mnc_passed": mnc,
                                    "node_id": node.node_id, "move": move,
                                    "agent_kind": "native_hammer_cascade"})
            return MoveResult(move=move, kernel_clean=kc, mnc_passed=mnc,
                              proof_text=proof_text, tail=(tail or "")[-300:],
                              wallclock_s=round(time.time() - start, 2), **_ps(ok, tail))
        if move == MOVE_CLAUDE_WARM:
            # The warm move runs through the SHARED RefineHandover contract — the SAME driver the
            # autoformalizer uses (produce→verify→feedback→refine→gate). PARITY-SAFE: max_refines=0 when
            # ZTARE_GAP_REFINE!=1 ⇒ ONE warm solve + govern, byte-identical to the pre-contract path;
            # max_refines=1 ⇒ on a near-miss (≥1 goal / progress≥0.4) the driver hands the leaf back its
            # own unsolved goals + premise shelf + prior attempt and retries ONCE, keep-better. Kernel/MNC
            # gate unchanged (accept only on kc&mnc). #26b — both feedback loops on ONE contract.
            from types import SimpleNamespace
            from ztare.common.refine_handover import RefineHandover
            from ztare.leanmill.solver.proof_state import extract_unsolved_goals

            def _warm_gen(_ctx):
                _o, _p, _t = _warm_agent_solve(_ctx["row"], (lean_root or DEFAULT_LEAN_ROOT_FOR_VERIFY),
                                               _cap("warm", max(180, verify_timeout * 2)))
                return {"ok": _o, "proof": _p, "tail": _t}

            def _warm_verify(_a):
                _kc, _mnc = _govern(_a["proof"], _a["ok"], _a["tail"]) if _a["ok"] else (False, False)
                _pp = _ps(_a["ok"], _a["tail"])
                return SimpleNamespace(accepted=bool(_kc and _mnc), kc=_kc, mnc=_mnc,
                                       progress=_pp.get("progress") or 0.0,
                                       goals=_pp.get("goals_remaining") or 0,
                                       checks={"kernel_clean": _kc, "mnc_passed": _mnc},
                                       reason="closed" if (_kc and _mnc) else "failed_compile")

            def _warm_refine_ctx(_a, _v, _ctx):
                if not (_v.goals >= 1 or _v.progress >= 0.4):
                    return None                          # not a near-miss ⇒ no refine (parity)
                _r2 = dict(_ctx["row"])
                _r2["_refine_context"] = _build_refine_context(
                    enriched_goal, _a["proof"], extract_unsolved_goals(_a["tail"]))
                return {"row": _r2}

            def _warm_better(_a, _va, _b, _vb):
                return (_b, _vb) if (_vb.accepted or _vb.progress > _va.progress) else (_a, _va)

            _rh = RefineHandover(generate=_warm_gen, verify=_warm_verify,
                                 accept_when=lambda _v: _v.accepted,
                                 build_refine_context=_warm_refine_ctx, better=_warm_better,
                                 # DEFAULT-ON (2026-06-07): the gap-refine retry-feedback (hand the leaf
                                 # back its own unsolved goals + premise shelf + prior attempt on a
                                 # near-miss). Safe-by-construction — `_warm_better` keep-betters, so a
                                 # refine round can only IMPROVE the result, never regress; the kernel/MNC
                                 # still gate. `ZTARE_GAP_REFINE=0` reverts. This is the nurture the leaf
                                 # was missing: one attempt + no feedback ⇒ apparatus-induced "couldn't".
                                 max_refines=0 if os.environ.get("ZTARE_GAP_REFINE") == "0" else 1)
            _art, _ver, _trace = _rh.run({"row": _eff_row()})
            ok, proof_text, tail = _art["ok"], _art["proof"], _art["tail"]
            kc, mnc = _ver.kc, _ver.mnc
            refined = len(_trace) > 1
            _lbl = "claude_opus_warm" + ("_refine" if refined else "")
            _record_attempt(r["row_id"], _lbl,
                            "closed" if (kc and mnc) else "failed_compile", kc and mnc, tail,
                            est_p_close=fc, wallclock_s=round(time.time() - start, 2))
            providers_tried.append({"provider": _lbl,
                                    "outcome": "closed" if (kc and mnc) else "failed_compile",
                                    "compile_ok": kc, "mnc_passed": mnc,
                                    "node_id": node.node_id, "move": move,
                                    "agent_kind": "warm_agent_gap_refine" if refined else "warm_agent"})
            return MoveResult(move=move, kernel_clean=kc, mnc_passed=mnc,
                              proof_text=proof_text, tail=(tail or "")[-300:],
                              wallclock_s=round(time.time() - start, 2), **_ps(ok, tail))
        if move in (MOVE_COLD_SHOT, MOVE_FRONTIER):
            # Cold-shot fan-out across preferred + fallbacks. The frontier slot is
            # provider-agnostic: a lab prover registered in the chain plugs in here
            # as one more provider; governance is identical.
            chain = [provider] + [f for f in fallbacks if f != provider]
            best = None
            # WHOLE-MOVE budget (caps on): _cap is the budget for the ENTIRE chain, not per-provider — a
            # 2-3 provider chain otherwise costs 2-3× the cap (the residual leak the red-team flagged). Each
            # provider gets min(cap, remaining); the chain stops when the budget is spent. Caps off ⇒ _cap
            # returns verify_timeout and the deadline never trips (parity: per-provider verify_timeout as before).
            _cf_cap = _cap("cold_frontier", verify_timeout)
            _cf_caps_on = os.environ.get("ZTARE_LEANMILL_PERMOVE_CAPS") != "0"   # DEFAULT-ON 2026-06-07
            for prov_name in chain:
                _prov_to = _cf_cap
                if _cf_caps_on:
                    _cf_rem = _cf_cap - (time.time() - start)
                    if _cf_rem <= 5:
                        break   # whole-move budget spent — do not start another provider
                    _prov_to = min(_cf_cap, max(15, int(_cf_rem)))
                decision = invoke_with_routing(
                    _eff_goal, preferred=prov_name,
                    fallbacks=[], timeout_s=_prov_to,
                )
                res = decision.result
                proof_text = (res.proof_text if res else None) or ""
                compile_ok, compile_tail = (False, "no provider proof")
                if res is not None and res.ok and proof_text.strip():
                    compile_ok, compile_tail = _verify_compile(
                        r["row_id"], _eff_goal, proof_text,
                        (lean_root or DEFAULT_LEAN_ROOT_FOR_VERIFY), verify_timeout,
                    )
                kc, mnc = _govern(proof_text, compile_ok, compile_tail) if compile_ok else (False, False)
                label = decision.chosen_provider or prov_name
                _record_attempt(r["row_id"], label,
                                "closed" if (kc and mnc) else ("failed_compile" if (res and res.ok) else "failed"),
                                kc and mnc, compile_tail, est_p_close=fc, wallclock_s=round(time.time() - start, 2))
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
                              wallclock_s=round(time.time() - start, 2), **_ps(kc, compile_tail))
        if move == MOVE_CONJECTURE:
            # INVENT a lemma L that unlocks the goal: prove G ASSUMING L (kernel-checked, L=sorry), then
            # SPAWN L as a child to prove. Earns its place ONLY if G-given-L typechecks + the goal-proof
            # CITES L + is sorry-free. The move does NOT close G (kernel_clean=False) — it ADVANCES via
            # new_sub_goal_text; the spawned L child is gated by the SAME kernel+MNC when proven (cold/
            # frontier prove children via node.goal_text). No false-closure (G stays open until L closes).
            _gt = enriched_goal or node.goal_text
            # CEGIS obstruction→conjecture SEED (M2, ZTARE_LEANMILL_NOGOOD=1): if a prior warm refutation
            # localized the obstruction, TARGET the conjecture prompt at the shadowed bridge lemma instead
            # of inventing blind. Default off / no seed ⇒ prompt_override=None ⇒ byte-identical blind path.
            _seed_prompt = None
            if os.environ.get("ZTARE_LEANMILL_NOGOOD") != "0":
                _sds = r.get("_obstruction_seeds") or []
                if _sds:
                    _seed_prompt = _sds[0].get("prompt")
            _lemma, _proof, _lname, _craw = conjecture_generate(
                r, _gt, (lean_root or DEFAULT_LEAN_ROOT_FOR_VERIFY),
                _cap("conjecture", max(120, verify_timeout)),
                prompt_override=_seed_prompt)
            _adv, _atail = conjecture_advances(
                _lemma, _proof, _lname, (lean_root or DEFAULT_LEAN_ROOT_FOR_VERIFY),
                _cap("conjecture", max(120, verify_timeout)),
                # circularity check compares L's conclusion to G's — parse G from the CLEAN goal, NOT the
                # premise-shelf-commented enriched_goal (which _lemma_conclusion mis-parses → check wouldn't fire).
                goal_conclusion=_lemma_conclusion(_eff_row().get("goal") or node.goal_text or _gt))
            # Borrow B (#39, ZTARE_CONJECTURE_REVIEW=1; default off = PARITY): a per-edge PRODUCTIVITY
            # filter — even a SOUND (L⇒G) decomposition is pruned if the reviewer judges L not strictly
            # easier / circular. ADVISORY + fail-OPEN (never blocks a sound edge on a tooling error); the
            # kernel + conjecture_advances already gate soundness. Off ⇒ behaviour byte-unchanged.
            if _adv and os.environ.get("ZTARE_CONJECTURE_REVIEW") == "1":
                from ztare.leanmill.solver.conjecture import decomposition_review
                _worthy, _wreason = decomposition_review(
                    _gt, _lemma, (lean_root or DEFAULT_LEAN_ROOT_FOR_VERIFY),
                    _cap("conjecture", max(60, verify_timeout)))
                if not _worthy:
                    _adv = False
                    _atail = f"reviewer pruned (not a productive decomposition): {_wreason[:90]}"
            _record_attempt(r["row_id"], "conjecture_lemma",
                            "advanced" if _adv else "no_advance", False, _atail, est_p_close=fc, wallclock_s=round(time.time() - start, 2))
            providers_tried.append({"provider": "conjecture_lemma",
                                    "outcome": "advanced" if _adv else "no_advance",
                                    "compile_ok": False, "mnc_passed": False,
                                    "node_id": node.node_id, "move": move, "agent_kind": "conjecture"})
            return MoveResult(move=move, kernel_clean=False, mnc_passed=False,
                              proof_text=(_proof if _adv else ""),
                              new_sub_goal_text=(_lemma if _adv else None),
                              residual=("conjectured_lemma_pending" if _adv else "conjecture_no_advance"),
                              tail=(_atail or "")[-300:],
                              wallclock_s=round(time.time() - start, 2), **_ps(False, ""))
        if move == MOVE_SPECIALIZE:
            # SPECIALIZE (capability B, wm3zp587b): generate a PROVABLE WEAKER special case G' + the
            # `G ⇒ G'` witness, kernel-gate it to a verified RUNG (specialization_is_genuine: G' closes
            # sorry-free AND G⇒G' typechecks AND G'≠G, non-vacuous). A rung is honest partial progress on
            # a hard/open goal — it does NOT close G (kernel_clean stays False ⇒ no false-closure surface);
            # the search records `rung=True` and resolves the node to the typed `rung` lever. MNC is not
            # run because nothing is being CLOSED (a rung is, by construction, not a closure of G).
            from ztare.leanmill.solver.conjecture import (specialize_generate, specialization_is_genuine,
                                                           specialization_substantive)
            _gt = enriched_goal or node.goal_text
            # The special case G' + the G⇒G' witness are compiled SELF-CONTAINED (import Mathlib only); for
            # a goal over bespoke defs (e.g. P1) they must see those defs too, so thread the source preamble
            # (the prelude before the target theorem) into BOTH the leaf prompt and the kernel gate.
            _pre = _preamble_from_source(r)
            _sp, _impl, _sname, _sraw = specialize_generate(
                r, _gt, (lean_root or DEFAULT_LEAN_ROOT_FOR_VERIFY),
                _cap("specialize", max(120, verify_timeout)), preamble=_pre)
            _genuine, _why = specialization_is_genuine(
                # "G' identical to G" check needs G's conclusion from the CLEAN goal, not enriched_goal
                # (premise-shelf comments make _lemma_conclusion mis-parse → the check wouldn't fire).
                _sp, _impl, _sname, _lemma_conclusion(_eff_row().get("goal") or node.goal_text or _gt),
                (lean_root or DEFAULT_LEAN_ROOT_FOR_VERIFY), max(120, verify_timeout), preamble=_pre)
            # SUBSTANTIVENESS (cross-field non-degeneracy, Leg 3a — STRUCTURAL parameter retention). ADVISORY
            # by default (records a flag so we can MEASURE substantive-vs-trivial rungs); the prompt already
            # steers AWAY from the degenerate corner. ZTARE_SPECIALIZE_SUBSTANTIVE_GATE=1 promotes it to a
            # HARD gate (a degenerate-corner rung is demoted to no_rung) — opt-in until pos/neg calibration
            # shows 1.0/0.0 (per §3b: don't fail-closed on a fresh gate).
            _subst, _subst_why = (specialization_substantive(_gt, _sp) if _genuine else (None, ""))
            _hard = os.environ.get("ZTARE_SPECIALIZE_SUBSTANTIVE_GATE") == "1"
            _rung = _genuine and (not _hard or _subst is not False)
            _outcome = ("rung" if _rung else ("rung_degenerate_corner" if _genuine else "no_rung"))
            _record_attempt(r["row_id"], "specialize", _outcome, False,
                            f"{_why} | substantive={_subst} ({_subst_why})", est_p_close=fc, wallclock_s=round(time.time() - start, 2))
            # BANK the verified rung G' into the canonical proof_cache (the COMPRESS store of record). A
            # rung's G' is a kernel-verified theorem (the gate proved it sorry-free), but the DAG caches
            # only GOAL-closures (`ratified_close`), so rungs would NOT accumulate — verified P1 special
            # cases would be re-derived every run. Bank it statement-keyed (the REAL ProofCache.put API)
            # so it persists + is reusable; `put` dedupes (no-op if already banked). Split on the proof
            # separator `:= by`, NOT the first `:=` (P1's rung carries a structure literal `{… := 1 …}`).
            if _rung and _sp:
                try:
                    import re as _re_rg
                    from ztare.leanmill.solver.proof_cache import ProofCache as _PC
                    _m = _re_rg.search(r":=\s*by\b", _sp)
                    if _m:
                        _stmt, _body = _sp[:_m.start()].rstrip(), _sp[_m.start():].strip()
                        if _stmt and _body:
                            _PC(OUT_DIR / "solver_lane_proof_cache.jsonl").put(
                                _stmt, _body, source=f"specialize_rung:{_outcome}")
                except Exception:  # noqa: BLE001 — banking is best-effort; a cache error must not fail the move
                    pass
            # M5 RUNG-TIGHTENING (ZTARE_LEANMILL_RUNG_TIGHTEN=1; default off = parity): extract + KERNEL-VERIFY
            # an explicit STRONGER bound B implied by the just-banked rung G', and bank B into the SAME cache so
            # a LATER rung can CITE it (one-off rungs → a monotone-tightening chain toward G). A fabricated/
            # unrelated bound fails the gate (B compiles + B⇒G' typechecks + B≠G') and is NEVER banked.
            if _rung and _sp and os.environ.get("ZTARE_LEANMILL_RUNG_TIGHTEN") == "1":
                try:
                    import re as _re_rt
                    from ztare.leanmill.solver.proof_margin_of_safety import rung_tighten as _rt
                    from ztare.leanmill.solver.proof_cache import ProofCache as _PCt
                    _bnd, _impl_b, _bnm = _rt(_sp, _lemma_conclusion(_sp), _sname,
                                              (lean_root or DEFAULT_LEAN_ROOT_FOR_VERIFY),
                                              max(120, verify_timeout), preamble=_pre)
                    _tightened = bool(_bnd)
                    if _tightened:
                        _mb = _re_rt.search(r":=\s*by\b", _bnd)
                        if _mb:
                            _bs, _bb = _bnd[:_mb.start()].rstrip(), _bnd[_mb.start():].strip()
                            if _bs and _bb:
                                _PCt(OUT_DIR / "solver_lane_proof_cache.jsonl").put(
                                    _bs, _bb, source=f"rung_tighten:{_outcome}")
                    _record_attempt(r["row_id"], "rung_tighten", "tightened" if _tightened else "no_tighten",
                                    False, _bnm, est_p_close=fc, wallclock_s=round(time.time() - start, 2))
                except Exception:  # noqa: BLE001 — tightening is best-effort; never fail the rung
                    pass
            providers_tried.append({"provider": "specialize", "outcome": _outcome,
                                    "compile_ok": _rung, "mnc_passed": False, "substantive": _subst,
                                    "node_id": node.node_id, "move": move, "agent_kind": "specialize"})
            return MoveResult(move=move, kernel_clean=False, mnc_passed=False,
                              rung=_rung,
                              proof_text=(_sp if _rung else ""),
                              residual=("verified_special_case_rung" if _rung else
                                        ("specialize_degenerate_corner" if _genuine else "specialize_no_rung")),
                              tail=(f"substantive={_subst}: {_subst_why}" if _genuine else (_why or ""))[-300:],
                              wallclock_s=round(time.time() - start, 2), **_ps(False, ""))
        if move == MOVE_GENERALIZE:
            # GENERALIZE (capability B, wm3zp587b): the CLOSURE move. The leaf returns a SELF-CONTAINED
            # tactic-block proof of the ORIGINAL goal that strengthens INTERNALLY (a `have`/`suffices`
            # proving a stronger fact, then instantiates). Because a closure of G is a proof OF G, this
            # routes through the EXACT SAME governance as a direct move — `_verify_compile` (kernel) +
            # `_govern` (matched-negative-control + statement_integrity via _validate_against_contract).
            # No separate closure path, no false-closure surface: the strengthening lives in a `have`, the
            # ratified theorem is G unaltered. Closes iff kc&mnc, identical to warm/cold.
            from ztare.leanmill.solver.conjecture import generalize_generate
            _gt = enriched_goal or node.goal_text
            _gproof, _gname, _graw = generalize_generate(
                r, _gt, (lean_root or DEFAULT_LEAN_ROOT_FOR_VERIFY), _cap("generalize", max(180, verify_timeout)))
            compile_ok, compile_tail = (False, "no generalize proof")
            if _gproof.strip():
                compile_ok, compile_tail = _verify_compile(
                    r["row_id"], _gt, _gproof, (lean_root or DEFAULT_LEAN_ROOT_FOR_VERIFY), verify_timeout)
            kc, mnc = _govern(_gproof, compile_ok, compile_tail) if compile_ok else (False, False)
            _record_attempt(r["row_id"], "generalize",
                            "closed" if (kc and mnc) else "failed_compile", kc and mnc, compile_tail,
                            est_p_close=fc, wallclock_s=round(time.time() - start, 2))
            providers_tried.append({"provider": "generalize",
                                    "outcome": "closed" if (kc and mnc) else "failed_compile",
                                    "compile_ok": kc, "mnc_passed": mnc,
                                    "node_id": node.node_id, "move": move, "agent_kind": "generalize"})
            return MoveResult(move=move, kernel_clean=kc, mnc_passed=mnc,
                              proof_text=_gproof, tail=(compile_tail or "")[-300:],
                              wallclock_s=round(time.time() - start, 2), **_ps(compile_ok, compile_tail))
        if move == MOVE_TACTIC_STEP:
            # TACTIC-STEPPING (M3 v2): per-step agentic search — the leaf emits ONE tactic at a time vs a
            # PERSISTENT proofState built from OUR decl (the moat: no file edit; the leaf reacts to each live
            # goal). REPL-closed is NEVER the verdict — the accepted sequence is reassembled into a `by` block
            # and re-verified through the SAME governance (_verify_compile + _govern = kernel + MNC +
            # statement_integrity), exactly like generalize. CALIBRATION-FIRST: a dead substrate ⇒ INADMISSIBLE
            # (NOT a fake negative). Default-OFF (stuck-gated in _strategist_move).
            from ztare.leanmill.solver.conjecture import tactic_step_solve
            _gt = enriched_goal or node.goal_text
            _pre = _preamble_from_source(r)
            _lr = lean_root or DEFAULT_LEAN_ROOT_FOR_VERIFY
            _pb, _info = tactic_step_solve(_eff_row(), _lr, _cap("tactic_step", max(180, verify_timeout)), preamble=_pre)
            if _info.get("inadmissible"):
                _record_attempt(r["row_id"], "tactic_step", "inadmissible", False,
                                _info["inadmissible"][:120], est_p_close=fc, wallclock_s=round(time.time() - start, 2))
                return MoveResult(move=move, kernel_clean=False, mnc_passed=False,
                                  residual="tactic_step_inadmissible",
                                  tail=("INADMISSIBLE (substrate dead, not a real negative): "
                                        + _info["inadmissible"])[:300],
                                  wallclock_s=round(time.time() - start, 2), **_ps(False, ""))
            compile_ok, compile_tail = (False, "no tactic-step proof")
            if _pb.strip():
                compile_ok, compile_tail = _verify_compile(
                    r["row_id"], _gt, _pb, _lr, verify_timeout)
            kc, mnc = _govern(_pb, compile_ok, compile_tail) if compile_ok else (False, False)
            _record_attempt(r["row_id"], "tactic_step", "closed" if (kc and mnc) else "failed_compile",
                            kc and mnc, compile_tail, est_p_close=fc, wallclock_s=round(time.time() - start, 2))
            providers_tried.append({"provider": "tactic_step",
                                    "outcome": "closed" if (kc and mnc) else "failed_compile",
                                    "compile_ok": kc, "mnc_passed": mnc, "node_id": node.node_id,
                                    "move": move, "agent_kind": "tactic_step",
                                    "steps": _info.get("steps")})
            return MoveResult(move=move, kernel_clean=kc, mnc_passed=mnc, proof_text=_pb,
                              tail=(compile_tail or "")[-300:],
                              wallclock_s=round(time.time() - start, 2), **_ps(compile_ok, compile_tail))
        if move == MOVE_WITNESS_TRANSPORT:
            # WITNESS TRANSPORT (computational closure, 2026-06-07): a non-linear existential SymPy can solve
            # but the native cascade cannot CLOSE. solve_witness FINDS the witness (SymPy, direct path = no
            # LLM) and emits a Lean tactic; the kernel PROVES it through the EXACT SAME governance as warm/
            # generalize (_verify_compile + _govern). A wrong witness fails to compile (a miss), never a false
            # closure. The LLM-script fallback is opt-in (ZTARE_LEANMILL_WITNESS_LLM=1); default = direct only.
            from ztare.leanmill.solver.witness_transport import solve_witness
            _wt_goal = (_eff_row().get("goal") or node.goal_text or enriched_goal or "").strip()
            _wt_lr = lean_root or DEFAULT_LEAN_ROOT_FOR_VERIFY
            _wt_disp = None
            if os.environ.get("ZTARE_LEANMILL_WITNESS_LLM") == "1":
                from ztare.leanmill.solver.agentic_leaf import default_dispatch as _wt_disp
            _wt_sol = solve_witness(_wt_goal, dispatch=_wt_disp, lean_root=_wt_lr,
                                    timeout_s=_cap("witness_transport", max(30, verify_timeout)))
            if _wt_sol is None:
                _record_attempt(r["row_id"], "witness_transport", "no_witness", False,
                                "no computable witness", est_p_close=fc,
                                wallclock_s=round(time.time() - start, 2))
                return MoveResult(move=move, kernel_clean=False, mnc_passed=False,
                                  tail="witness_transport: no computable witness",
                                  wallclock_s=round(time.time() - start, 2), **_ps(False, ""))
            _wt_tac, _wt_meta = _wt_sol
            compile_ok, compile_tail = _verify_compile(r["row_id"], _wt_goal, _wt_tac, _wt_lr, verify_timeout)
            kc, mnc = _govern(_wt_tac, compile_ok, compile_tail) if compile_ok else (False, False)
            _record_attempt(r["row_id"], "witness_transport",
                            "closed" if (kc and mnc) else "failed_compile", kc and mnc,
                            (_wt_meta.get("path", "") + " :: " + (compile_tail or ""))[-200:],
                            est_p_close=fc, wallclock_s=round(time.time() - start, 2))
            providers_tried.append({"provider": "witness_transport",
                                    "outcome": "closed" if (kc and mnc) else "failed_compile",
                                    "compile_ok": kc, "mnc_passed": mnc, "node_id": node.node_id,
                                    "move": move, "agent_kind": f"witness_transport:{_wt_meta.get('path')}"})
            return MoveResult(move=move, kernel_clean=kc, mnc_passed=mnc, proof_text=_wt_tac,
                              tail=(compile_tail or "")[-300:], wallclock_s=round(time.time() - start, 2),
                              **_ps(compile_ok, compile_tail))
        if move in (MOVE_FALSIFY, MOVE_CORROBORATE):
            # FALSIFY (Invert leg, 2026-06-06) + CORROBORATE (its Popper DUAL, 2026-06-07): pursue a
            # kernel-checked proof of ¬G. On the OPEN/untrusted regime the target may be FALSE; a falsifying
            # witness is a first-class outcome that feeds the existing falsifier sink (status handler +
            # residual_to_lever 'falsifier' lever). Routed through the SHARED Popper inversion contract
            # (common.inversion.run_inversion). FALSIFY uses conjecture.LeanFalsifier (direct ¬G);
            # CORROBORATE uses conjecture.LeanConsequenceCorroborator (¬G via a refuted CONSEQUENCE,
            # `G→K ∧ ¬K ⟹ ¬G`) — SAME invert/adjudicate gate, only the witness route differs. SOUND: the
            # refuted Prop is OURS (built from the goal signature via _closed_goal_prop), the leaf supplies
            # ONLY the proof body / consequence — so "negate a strawman / weakened statement" (the warm-path
            # statement-alteration vector) is structurally impossible. The kernel RATIFIES: compile sorry-free
            # (falsification_is_genuine) + the anti-laundering organs (run_anti_laundering_kernel) —
            # falsifier=True is set ONLY off those receipts; the search never self-credits. Never closes G.
            from ztare.leanmill.solver.conjecture import LeanFalsifier, LeanConsequenceCorroborator
            from ztare.common.inversion import run_inversion
            _inv_cls = LeanConsequenceCorroborator if move == MOVE_CORROBORATE else LeanFalsifier
            _mkey = "corroborate" if move == MOVE_CORROBORATE else "falsify"
            # Build ¬G from the CLEAN goal (the row/node theorem), NOT the enriched context — _closed_goal_prop
            # needs a parseable signature (the premise-shelf-commented enriched_goal would mis-parse ⇒ FALSIFY
            # would silently never fire). The preamble (_pre) still carries the bespoke defs for the kernel.
            _clean_goal = (_eff_row().get("goal") or node.goal_text or enriched_goal or "").strip()
            _pre = _preamble_from_source(r)
            _lr = lean_root or DEFAULT_LEAN_ROOT_FOR_VERIFY

            def _falsify_organs(refute_block: str) -> "tuple[bool, str]":
                """The exogenous arbiter's anti-laundering leg: route the ¬G source through the ONE kernel
                (vacuity / gold-name / leakage / consequence). statement_integrity is N/A here (the refute
                theorem is ¬G under OUR fixed signature, not a re-statement of the named target), so
                original_source=None. FAIL-OPEN on an organ crash (never block a real falsifier)."""
                try:
                    import re as _re_f
                    from ztare.gates.lean_proof_gate import run_anti_laundering_kernel as _kernel
                    _src = ((_pre.strip() + "\n\n") if _pre.strip() else "") + refute_block.strip()
                    if not _src.lstrip().startswith("import"):
                        _src = "import Mathlib\n\n" + _src
                    _fm = _re_f.search(r"theorem\s+(\w+_refute)\b", refute_block)
                    _k = _kernel(_src, _lr / "_falsify_kernel.lean", _lr,
                                 original_source=None, target_name=(_fm.group(1) if _fm else None))
                    return bool(_k.get("passed")), f"organs confirmed={_k.get('confirmed')}"
                except Exception as _e:  # noqa: BLE001 — FAIL-OPEN
                    return True, f"organs fail-open: {repr(_e)[:80]}"

            _lf = _inv_cls(_eff_row(), _lr, _cap(_mkey, max(180, verify_timeout)), preamble=_pre,
                           kernel_check=_falsify_organs)
            _verdict = run_inversion(_lf, _clean_goal, {"lean_goal": _clean_goal})
            _is_fls = (_verdict.falsified is True)
            _outcome = "falsified" if _is_fls else "no_falsifier"
            _record_attempt(r["row_id"], _mkey, _outcome, False,
                            (_verdict.detail or "")[-200:], est_p_close=fc, wallclock_s=round(time.time() - start, 2))
            providers_tried.append({"provider": _mkey, "outcome": _outcome,
                                    "compile_ok": _is_fls, "mnc_passed": False,
                                    "node_id": node.node_id, "move": move, "agent_kind": _mkey})
            return MoveResult(move=move, kernel_clean=False, mnc_passed=False, falsifier=_is_fls,
                              proof_text=(_verdict.witness if _is_fls else ""),
                              residual=(f"falsifying_witness_for_{target_name or 'goal'}" if _is_fls
                                        else "falsify_no_witness"),
                              tail=(_verdict.detail or "")[-300:],
                              wallclock_s=round(time.time() - start, 2), **_ps(False, ""))
        return MoveResult(move=move, kernel_clean=False, mnc_passed=False,
                          tail=f"unknown move {move}")

    return move_runner


def solve(provider: str, limit: int, dry_run: bool, timeout_s: int = 300,
          mode: str = "cascade", rows: "list[dict] | None" = None,
          skip_cue_check: bool = False, lean_root=None) -> dict:
    """`rows` (default None) injects an explicit row list instead of the C-slice — this is the
    ad-hoc-target entry (see `solve_adhoc`): a one-off lemma flows through the SAME governed
    pipeline (contract → moves → MNC → governance → receipt). `skip_cue_check` bypasses the
    slice-routing source-cue gate (which is C-credit routing, not capability-relevant) for
    ad-hoc rows."""
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
        registry_path = CONTROL / "leanmill_provider_registry.py"
        if not registry_path.exists():
            registry_path = CONTROL / "provider_registry.py"
        reg = _load(registry_path)
    if rows is None:
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
        # ── Frontier-type triage (pre-attempt). ADVISORY by default: the verdict is recorded on
        # every result, but the DEFER action only fires under ZTARE_FRONTIER_TRIAGE_DEFER=1 — so
        # the default path attempts everything (parity). Classifies from goal STRUCTURE (human
        # formalization/discovery tags are untrusted per cube_fubini); conservative floor =
        # defaults to attempt, defers only on strong discovery-bound evidence.
        triage_verdict = None
        try:
            from ztare.leanmill.solver.frontier_triage import triage as _triage, defer_enabled
            tv = _triage(str(goal), source_hint=str(r.get("rejection_reasons") or ""))
            triage_verdict = tv.to_dict()
            if defer_enabled() and not tv.attempt:
                results.append({"name": r["row_id"],
                                "target_name": r.get("target_theorem_name"),
                                "kind": "c_pool_no_template",
                                "outcome": "deferred_discovery_bound", "exit_code": 0,
                                "frontier_triage": triage_verdict,
                                "stderr_excerpt": "frontier_triage: " + tv.rationale[:120]})
                continue
        except Exception:
            triage_verdict = None  # advisory — never block on a triage error
        if typed_available and invoke_with_routing is not None:
            # ── Upstream typed action contract (built BEFORE any prover work).
            # Per H32-H42: typed contract + source_cue_check + deterministic
            # lowering = 1.0 accuracy vs 0.33 for free-form chain. The
            # contract IS the dispatch plan; layer steps below are the
            # contract's action_program lowered to executable code.
            contract = _build_solver_action_contract(r, (lean_root or DEFAULT_LEAN_ROOT_FOR_VERIFY))
            if not skip_cue_check and contract["source_cue_check_status"] == "failed":
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
                from ztare.leanmill.solver import governed_dag_search as _gds
                from ztare.leanmill.solver.governed_dag_search import (
                    run_governed_dag_search,
                )
                # Arc-H calibration (opt-in, ZTARE_CALIBRATE_PRIORS=1): replace the stub
                # est_p_close priors with values measured from the attempts DB (Beta posterior,
                # stub-as-prior — safe fallback, small samples stay near stub; free moves floored
                # so calibration only down-weights COSTLY dead moves). DEFAULT ON (2026-06-03)
                # after the mechanism A/B confirmed lift + no-regression; ZTARE_CALIBRATE_PRIORS=0
                # reverts to stubs.
                if os.environ.get("ZTARE_CALIBRATE_PRIORS", "1") != "0":
                    from ztare.leanmill.solver import move_calibration as _mc
                    # RECURSIVE SELF-TUNING: load selection_priors — per move, scores RATIFIED
                    # governance outcomes once that move has enough governed data, else compile_ok
                    # (data-gated, parity when sparse). The environment self-shifts toward "what
                    # governance ratified" as the DB accrues. ONE kernel function; all modes inherit.
                    # #28 calibration→CONTROL (ZTARE_CALIBRATE_AUTOTUNE=1; default off = PARITY): the
                    # recorded-forecast Brier monitor (else dead) DRIVES the Beta prior strength k —
                    # overfitting (out-of-sample > in-sample) ⇒ MORE shrinkage (conservative, raise-only,
                    # can't collapse the distribution). The recorded Brier is LOGGED every run regardless
                    # (observability — the "measure success" half of the loop, previously uncalled).
                    _k, _tune = _mc.DEFAULT_PRIOR_STRENGTH, {"tuned": False}
                    if os.environ.get("ZTARE_CALIBRATE_AUTOTUNE") == "1":
                        _k, _tune = _mc.autotune_strength(str(ATTEMPTS_DB))
                    _sel = _mc.selection_priors(str(ATTEMPTS_DB), strength=_k)
                    _gds.set_move_priors({m: v["p"] for m, v in _sel.items()})
                    # GP-248 CONTEXT-AWARE move prior (ZTARE_LEANMILL_CONTEXT_PRIOR=1; default off = PARITY):
                    # condition the per-move prior on the node's failure context via the EXISTING BIC-selected
                    # per-(move,error_class) posterior (move_calibration.calibrated_priors_for_class) — wiring,
                    # not a new model. Ordering-only; the kernel still ratifies. Unset ⇒ flat prior (parity).
                    if os.environ.get("ZTARE_LEANMILL_CONTEXT_PRIOR") == "1":
                        # MEMOIZE per error_class: _effective_est_p fires O(nodes×moves×loops) times in the
                        # frontier sort, and calibrated_priors_for_class reads the DB + runs BIC — without a
                        # cache that is a DB read per ranking comparison. The DB is effectively static during
                        # one solve (a slightly-stale prior within a solve is fine for ORDERING).
                        _ctx_prior_cache: dict = {}

                        def _ctx_prior(_ec, _cache=_ctx_prior_cache, _k=_k):
                            if _ec not in _cache:
                                _cache[_ec] = _mc.calibrated_priors_for_class(str(ATTEMPTS_DB), _ec, strength=_k)
                            return _cache[_ec]
                        _gds.set_context_prior_fn(_ctx_prior)
                    else:
                        _gds.set_context_prior_fn(None)
                    _bases = {m: v["basis"] for m, v in _sel.items() if v["basis"] != "stub"}
                    _rfb = _mc.recorded_forecast_brier(str(ATTEMPTS_DB), use_ratified=True)
                    print(f"[solver] self-tuning priors (k={_k} autotune={_tune.get('tuned')} "
                          f"recorded_brier={_rfb.get('recorded_forecast_brier')}/n={_rfb.get('n')}; "
                          f"bases: {_bases or 'all-stub'}):\n{_mc.report(str(ATTEMPTS_DB))}")
                # UCB-OVER-MOVES visit snapshot (ZTARE_LEANMILL_UCB_MOVES=1; default off = PARITY) — HOISTED
                # OUT of the CALIBRATE_PRIORS guard above (red-team 2026-06-07): the install/clear must run on
                # EVERY solve regardless of ZTARE_CALIBRATE_PRIORS, else a worker with CALIBRATE_PRIORS=0 +
                # UCB on would skip it and _ucb_move_policy would consult a STALE module-global snapshot from a
                # prior solve. move_policy ranks the closure menu by `calibrated Q + a scale-invariant
                # exploration bonus` over this snapshot; clearing to None when off prevents the leak.
                # WHOLE-DB read (no run_tag slice) is DELIBERATE: the visit denominator is the WARM-START prior
                # — the global production skew (native/warm saturated, tail dormant) — which is exactly what
                # makes the bonus meaningful; per-arm slicing would re-introduce the empty-snapshot cold start.
                if os.environ.get("ZTARE_LEANMILL_UCB_MOVES") == "1":
                    from ztare.leanmill.solver import move_calibration as _mcu
                    _gds.set_move_visits(_mcu.move_visit_counts(str(ATTEMPTS_DB)))
                else:
                    _gds.set_move_visits(None)
                move_runner = _build_dag_move_runner(
                    r, contract, enriched_goal, verify_timeout, provider, fallbacks,
                    invoke_with_routing, providers_tried, lean_root=lean_root,
                )
                # Proof cache: bank kernel-verified lemmas to a persistent jsonl and REUSE them
                # across rows/runs (compounding lift). NON-IATROGENIC: a cache hit is RE-COMPILED
                # in this context via cache_verify before closing (no-false-closure preserved on
                # reuse); a failed re-verify is a cache miss, never a closure. DEFAULT ON
                # (2026-06-03) after the A/B confirmed lift + no-regression; ZTARE_PROOF_CACHE=0
                # disables (cache=None ⇒ behaviour byte-unchanged).
                _cache = _cache_verify = None
                if os.environ.get("ZTARE_PROOF_CACHE", "1") != "0":
                    from ztare.leanmill.solver.proof_cache import ProofCache as _PCw
                    _cache = _PCw(OUT_DIR / "solver_lane_proof_cache.jsonl")
                    _cache_verify = lambda g, p: bool(p) and _verify_compile(
                        r["row_id"], g, p, (lean_root or DEFAULT_LEAN_ROOT_FOR_VERIFY), verify_timeout)[0]
                # max_moves is the TOTAL move budget across the whole DAG (incl. recursively
                # spawned sub-goals). The default 12 caps recursion depth — fine for the C-slice
                # (single-leaf targets) but it STARVES deep decomposition of a large theorem (the
                # conjecture move that banks sub-lemmas never gets budget → "any size" fails). So it
                # is env-scalable (ZTARE_DAG_MAX_MOVES); default 12 = parity for the batch, raised by
                # solve_adhoc for hard one-off targets so the conjecture-DAG can actually go deep.
                _dag_max_moves = int(os.environ.get("ZTARE_DAG_MAX_MOVES", "12"))
                # MOVE-BUDGET (cost units): the dag-search default is 20.0, which the base MOVE_ORDER menu
                # (hammer 0 + warm 3 + cold 4 + frontier 6 + conjecture 2 = 15) nearly exhausts — so the
                # cost-4 strategist moves (generalize/falsify) were STARVED regardless of wallclock (P1 hit
                # exactly 20 units / 8 moves). Raise it (env-tunable) so a stuck node can afford the base
                # menu + several strategist/recursive moves; wallclock (timeout_s) + max_moves stay the real
                # caps. NOT a low-budget self-own.
                _dag_move_budget = float(os.environ.get("ZTARE_DAG_MOVE_BUDGET", "32"))
                dag_res = run_governed_dag_search(
                    contract=contract,
                    goal_text=enriched_goal or str(goal),
                    move_runner=move_runner,
                    wallclock_budget_s=float(timeout_s),
                    max_moves=_dag_max_moves,
                    move_budget_units=_dag_move_budget,
                    target_strength=(triage_verdict or {}).get("target_strength", ""),  # M4 advisory steer
                    cache=_cache,
                    cache_verify=_cache_verify,
                    # TELEMETRY (audit gap #3): record a cache reuse as a first-class attempts-DB row so the
                    # COMPRESS+SCALE lift is sliceable in move_yield_report / per-arm (it bypasses move_runner).
                    on_cache_reuse=(lambda nid, g, rev, wc: _record_attempt(
                        r["row_id"], "cache_reuse", "closed", True,
                        f"reused banked proof (reverified={rev})", wallclock_s=wc))
                        if _cache is not None else None,
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
                    lean_root=(lean_root or DEFAULT_LEAN_ROOT_FOR_VERIFY),
                    timeout_s=verify_timeout,
                    kernel_compile_ok=compile_ok,
                    kernel_compile_tail=compile_tail,
                    goal_type=r.get("goal"),
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
                # In-repo-reference receipt (advisory, beside the premise-shelf / MNC checks):
                # record whether a SOLVED reference of this target was reachable by the sandbox at
                # closure time (the second leakage channel). Observability only — does NOT reject
                # (batch rows may legitimately depend on solved repo lemmas as premises; quarantine
                # is reserved for capability runs via solve_adhoc). Fail-open: a check error never
                # blocks a real closure.
                # PERF (cold-review 2026-06-03): this rglobs + reads every .lean in the repo
                # (~12s on a 20k-file checkout). On the throughput batch path that taxes every
                # closure, so it is OPT-IN (ZTARE_CLOSURE_REF_CHECK=1) — set ON by solve_adhoc, the
                # CAPABILITY entry where leakage-cleanliness is load-bearing. Default-off = no batch
                # latency tax; the field records ran=False so the receipt is still explicit.
                in_repo_refs: list[str] = []
                ref_check_error = None
                ref_check_ran = os.environ.get("ZTARE_CLOSURE_REF_CHECK") == "1"
                if ref_check_ran:
                    try:
                        from ztare.leanmill.solver.reference_leakage_gate import (
                            reachable_solved_references as _rsr,
                        )
                        tn = r.get("target_theorem_name") or ""
                        if tn:
                            in_repo_refs = [str(p) for p in _rsr(
                                [tn], REPO, str((lean_root or DEFAULT_LEAN_ROOT_FOR_VERIFY)))]
                    except Exception as _e:  # observability must never block a closure
                        ref_check_error = repr(_e)[:160]
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
                    "frontier_triage": triage_verdict,
                    "in_repo_reference_check": {
                        "kind": "reachable_solved_references",
                        "executed_at": "solver_layer",
                        "ran": ref_check_ran,
                        "clean": (not in_repo_refs) and ref_check_error is None if ref_check_ran else None,
                        "reachable_solved_references": in_repo_refs,
                        "error": ref_check_error,
                        "note": "advisory: reachable in-repo solved references at closure time; opt-in "
                                "(ZTARE_CLOSURE_REF_CHECK=1, on for solve_adhoc). Non-empty does NOT "
                                "reject (premises are legitimate in batch) but flags a capability claim.",
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
                r, (lean_root or DEFAULT_LEAN_ROOT_FOR_VERIFY), min(180, timeout_s // 2),
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
                    r, (lean_root or DEFAULT_LEAN_ROOT_FOR_VERIFY), max(180, timeout_s),
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
                            (lean_root or DEFAULT_LEAN_ROOT_FOR_VERIFY), verify_timeout,
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
                r, (lean_root or DEFAULT_LEAN_ROOT_FOR_VERIFY), timeout_s,
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
            # the per-row records — REQUIRED by solve_adhoc/solve_family/proof_repair, which read
            # res["results"][0] to detect closure + extract proof_text (without this they scored
            # every closure as a false negative; cold-review catch 2026-06-03).
            "results": results,
            "results_path": str(OUT_RESULTS), "exits_path": str(OUT_EXITS),
            "dry_run": dry_run}


def solve_adhoc(target_name: str, source_text: str, goal: str, *,
                provider: str | None = None, timeout_s: int = 500,
                mode: str = "cascade", substrate: "Path | None" = None) -> dict:
    """Ad-hoc-target entry — run a ONE-OFF lemma through the FULL governed pipeline (the gap that
    bred the bespoke harnesses). `source_text` is a complete .lean file whose `target_name`
    declaration ends in `sorry`; it is written into `substrate`, wrapped in the reference-leakage
    gate, run via `solve(rows=[…], skip_cue_check=True)` (so it flows through contract → moves →
    MNC → governance → receipt), and on a kernel-clean closure its invented helpers are banked to
    the family library (compounding). No re-rolled iteration — this IS the worker pipeline."""
    from ztare.leanmill.solver import reference_leakage_gate as _gate
    from ztare.leanmill.solver import family_lemma_library as _lib
    # APPARATUS FIX (2026-06-05): bootstrap elan/lake onto PATH at the GOVERNED ENTRY, not just main().
    # Direct callers (spectral_baseline, obstruction_lift, autoformalize, any importer) bypassed main()'s
    # bootstrap → `lake` bare-name call → FileNotFoundError on EVERY target → a 0/N that looked like
    # "too hard" but was pure apparatus (the spectral baseline burned 5 targets on this). Idempotent
    # (lru_cached); every solve_adhoc caller is now immune.
    from ztare.gates.lean_compile_primitives import ensure_elan_on_path as _ensure_elan
    _ensure_elan()
    sub = Path(substrate) if substrate else DEFAULT_LEAN_ROOT_FOR_VERIFY
    _run_start = datetime.now(timezone.utc).isoformat()  # scope the ratification stamp to THIS run
    src = sub / f"AdHoc_{target_name}.lean"
    src.write_text(source_text, encoding="utf-8")
    if not goal:  # derive the real goal (binders+type) from the source, not the bare name
        import re as _re
        m = _re.search(rf"(?:theorem|lemma)\s+{_re.escape(target_name)}\b(.*?):=", source_text, _re.S)
        goal = (m.group(1).strip() if m else "") or target_name
    row = {"row_id": f"adhoc::{target_name}", "target_theorem_name": target_name,
           "source_file": str(src), "sorried_file": str(src), "goal": goal,
           "rejection_reasons": ["no_positive_family_template"], "target_resolution_ok": True}
    prov = provider or _policy_model()
    _prev_refchk = os.environ.get("ZTARE_CLOSURE_REF_CHECK")
    os.environ["ZTARE_CLOSURE_REF_CHECK"] = "1"  # capability entry: record the in-repo-ref receipt
    # Hard one-off targets may need DEEP recursive decomposition (conjecture-DAG spawning + banking
    # sub-lemmas). The batch default (12 total moves) starves that, so raise it for the ad-hoc entry
    # unless the caller already pinned ZTARE_DAG_MAX_MOVES. This is the "handle any size" budget.
    _prev_maxmoves = os.environ.get("ZTARE_DAG_MAX_MOVES")
    if _prev_maxmoves is None:
        os.environ["ZTARE_DAG_MAX_MOVES"] = "60"
    try:
        with _gate.clean_capability([target_name], REPO, str(sub)) as quarantined:
            res = solve(prov, limit=0, dry_run=False, timeout_s=timeout_s, mode=mode,
                        rows=[row], skip_cue_check=True, lean_root=sub)
    finally:
        if _prev_refchk is None:
            os.environ.pop("ZTARE_CLOSURE_REF_CHECK", None)
        else:
            os.environ["ZTARE_CLOSURE_REF_CHECK"] = _prev_refchk
        if _prev_maxmoves is None:
            os.environ.pop("ZTARE_DAG_MAX_MOVES", None)
        else:
            os.environ["ZTARE_DAG_MAX_MOVES"] = _prev_maxmoves
    res["quarantined_references"] = [str(p) for p in quarantined]
    r0 = (res.get("results") or [{}])[0]
    # ── FULL L1+L2+L3 GOVERNANCE AT THE CAPABILITY ENTRY (2026-06-04). Previously solve_adhoc DEFERRED
    # the axiom-allowlist + v33 anti-laundering stack to a downstream `leanmill_proof_audit` that was
    # never invoked for ad-hoc runs — i.e. the existing governance was UNDER-USED (it ran MNC only).
    # Now the winning probe is run through the canonical organs in-line:
    #   (1) audit_axioms        — #print axioms ⊆ allowlist                  [lean_proof_gate]
    #   (2) _run_v33_anti_laundering — vacuity / gold-name / single-lemma / paraphrase / leakage  [v33]
    #   (3) statement_integrity — diff winning probe vs ORIGINAL defs (the axis v33 LACKS: it audits
    #       the probe in isolation, so it cannot see a depended-on definition being altered — this is
    #       the channel the mollifier_rate def-edit cheat used; empirically v33 returns clean on it).
    # Fail-OPEN on an organ crash (never block a closure on a gate bug); a CONFIRMED blocker is
    # fail-CLOSED (reject → outcome `rejected_governance`).
    if r0.get("outcome") == "closed":
        gov: dict = {}
        try:
            from ztare.leanmill.solver import statement_integrity as _si
            # Search BOTH the passed substrate AND the default verify root. The cold/external prover
            # route (codex/claude cold) proves in DEFAULT_LEAN_ROOT_FOR_VERIFY (ztare_proofs) regardless
            # of substrate=, so a sidecar-only glob missed its probe → v33 + statement-integrity SILENTLY
            # SKIPPED and the certificate captured nothing (the cold-route governance gap, 2026-06-04).
            _roots = list(dict.fromkeys([sub, DEFAULT_LEAN_ROOT_FOR_VERIFY]))
            cand = sorted([p for r in _roots for p in r.glob("RobustProbe_*.lean")]
                          + [r / f"AdHoc_{target_name}.lean" for r in _roots],
                          key=lambda p: p.stat().st_mtime if p.exists() else 0, reverse=True)
            # Pick the probe that ACTUALLY produced this closure: its body must contain the winning
            # `proof_text`. Falls back to "most-recent sorry-free probe defining the target" only if
            # no body match (older runs / proof_text unavailable). Without the proof_text match the
            # governance organs could run on the WRONG probe (claude vs codex, or a non-closing one).
            _pt = (r0.get("proof_text") or "").strip()
            probe_path = probe_txt = None
            _fallback = None
            for p in cand:
                if not p.exists():
                    continue
                t = p.read_text(encoding="utf-8", errors="replace")
                body = t.split("#print axioms")[0]
                if target_name not in t or "sorry" in body or "admit" in body:
                    continue
                if _pt and _pt in t:           # the exact closing probe
                    probe_path, probe_txt = p, t
                    break
                if _fallback is None:
                    _fallback = (p, t)
            if probe_txt is None and _fallback is not None:
                probe_path, probe_txt = _fallback
                gov["probe_match"] = "fallback (proof_text not found in any probe)"
            # The kernel must recompile the probe against the root it ACTUALLY lives in — a cold-route
            # probe is in ztare_proofs (v4.30), not the sidecar (v4.27); recompiling it against the
            # wrong toolchain would spuriously fail (e.g. a v4.30-only lemma → "unknown constant").
            _probe_root = probe_path.parent if probe_path is not None else sub
            gov["verify_root"] = str(_probe_root)
            blockers: list[str] = []
            if probe_txt is not None:
                # AXIOM allowlist is ALREADY gated by the leaf (verify_lean_proof runs `#print axioms
                # ⊆ {propext,Classical.choice,Quot.sound}` BEFORE a closure is recorded) — so a closure
                # that reached here already passed it. We do NOT re-implement that gate (the bespoke
                # `audit_axioms` re-check was a frankenstein: it duplicated the leaf's gate AND was
                # broken — `<lake-not-installed>` in the worker subprocess → false-rejected clean
                # proofs, 2026-06-04). Governance here adds ONLY the two checks the leaf does NOT:
                #   • v33 anti-laundering (leakage / paraphrase / single-lemma / vacuity)
                #   • statement_integrity (the agent must not have ALTERED a depended-on definition —
                #     v33's blind spot; the original-vs-probe diff).
                # INVARIANT: route through the ONE factory governance kernel — never re-implement
                # checks per mode. `_run_v33_anti_laundering` IS that kernel's extensible organ stack
                # (laundering + vacuity + statement-integrity); passing `original_source` activates the
                # statement-integrity organ (def-alteration). ONE call, no bolted-on per-mode copies.
                try:
                    from ztare.gates.lean_proof_gate import run_anti_laundering_kernel as _kernel
                    k = _kernel(probe_txt, probe_path, _probe_root,
                                original_source=source_text, target_name=target_name)
                    gov["governance_kernel"] = {"passed": bool(k.get("passed")), "flags": k.get("flags"),
                                                "confirmed": k.get("confirmed")}
                    gov["statement_integrity"] = (k.get("detail") or {}).get("statement_integrity")
                    if k.get("passed") is False:
                        blockers.append("kernel:" + ",".join(k.get("confirmed") or k.get("flags") or []))
                except Exception as _e:
                    gov["governance_kernel"] = {"passed": None, "error": repr(_e)[:120]}
                gov["axiom_allowlist"] = "gated by leaf verify_lean_proof (#print axioms) pre-closure"
                # POST-CLOSURE ROBUSTNESS (advisory; ZTARE_PROOF_MARGIN=1, default off = parity). The
                # proof-substrate analogue of GP-112 margin-of-safety: annotate the kernel-verified
                # closure with strengthen/weaken signals (surveyability + the load-bearing-hypothesis
                # perturbation). REUSES the kernel + proof_surveyability_gate (no parallel); NEVER
                # re-rejects (advisory) — so a closure stays closed, but a fragile one is flagged.
                if os.environ.get("ZTARE_PROOF_MARGIN") == "1":
                    try:
                        from ztare.leanmill.solver.proof_margin_of_safety import proof_margin_of_safety
                        gov["margin_of_safety"] = proof_margin_of_safety(
                            probe_txt, target_name, _probe_root, timeout_s=90, deep=True,
                            original_source=source_text)
                    except Exception as _e:  # noqa: BLE001 — advisory: never break the governance path
                        gov["margin_of_safety"] = {"error": repr(_e)[:120]}
            else:
                # No probe to diff → the statement-integrity organ could not run. The leaf's axiom
                # gate + MNC DID run (so it's not ungoverned), but def-alteration is UNVERIFIED here —
                # flag it explicitly rather than silently treating the closure as integrity-clean.
                gov["note"] = "no sorry-free probe defining the target found"
                gov["integrity_unverified"] = True
            res["governance"] = gov
            if blockers:
                r0["outcome"] = "rejected_governance"
                r0["governance_blockers"] = blockers
                res["closure_candidates"] = 0
                res["rejected_reason"] = "governance blocker(s): " + "; ".join(blockers)
                # CEGIS no-good — close the CROSS-RUN governance loop (default-on; ZTARE_LEANMILL_NOGOOD=0
                # disables). The kernel CONFIRMED a laundered closure; solve_adhoc previously banked the
                # witness only to the per-run audit certificate and DISCARDED it, so the same gamed shape
                # could recur on a future run (the same-run governed-retry can't cover cross-run). Record
                # it into the canonical no-good store so a later run of this goal sees it in `prompt_block`.
                # Sound by construction — a no-good only INFORMS the leaf prompt, never prunes/blocks a
                # path (no_good_store SCOPE) — and fail-open (a store error never fails the solve).
                if os.environ.get("ZTARE_LEANMILL_NOGOOD") != "0":
                    try:
                        from ztare.leanmill.solver.no_good_store import (
                            NoGoodStore as _NGS, failure_class_of as _fco)
                        _ngs = _NGS(OUT_DIR / "solver_lane_no_good_store.jsonl")
                        _wit = (r0.get("proof_text") or "").strip() or "; ".join(blockers)
                        _siv = gov.get("statement_integrity")
                        if _siv is not None:  # typed decl-diff violations (definition_altered, …)
                            _ngs.record_integrity_verdict(goal, _siv, source=f"adhoc:{target_name}")
                        for _flag in ((gov.get("governance_kernel") or {}).get("confirmed")
                                      or (gov.get("governance_kernel") or {}).get("flags") or []):
                            _ngs.record(goal, _fco(_flag), _wit, confirmed=True,
                                        source=f"adhoc:{target_name}")
                    except Exception:  # noqa: BLE001 — recording is best-effort; never fail the solve
                        pass
        except Exception as _e:
            res["governance"] = {"error": repr(_e)[:160]}
        # Stamp the RATIFICATION verdict onto this run's attempts: ratified=1 iff governance accepted
        # the closure, 0 if rejected (a gamed compile_ok=1 → ratified=0). The rating layer scores
        # `ratified`, so cheats stop counting as wins (the false-positive fix).
        try:
            n_stamped = _record_governance_verdict(row["row_id"], ratified=(r0.get("outcome") == "closed"),
                                                    since=_run_start)
            res["ratification_stamped_attempts"] = n_stamped
        except Exception as _e:
            res["ratification_error"] = repr(_e)[:120]
        # Durable closure certificate — co-locate the audit verdict with the (cached) proof so the
        # closure is auditable from one tracked record. Written for BOTH a clean closure and a
        # governance-rejection (the rejection is itself an audit event — the kernel firing). The
        # `recompilable_probe` is the exact .lean that the leaf compiled; re-running `#print axioms`
        # on it reproduces the axiom audit with no archaeology. Fail-open (never block on a write bug).
        try:
            # `probe_txt` is the FULL self-contained .lean that compiled clean (imports + opens +
            # any helper lemmas + the theorem) — NOT just the by-block the ProofCache stores. It is
            # the only artifact that recompiles on its own, and the leaf's RobustProbe_*.lean holding
            # it is overwritten by the next target's run. Pin it permanently in TWO places:
            _probe_full = locals().get("probe_txt") or ""
            _closure_lean = None
            if r0.get("outcome") == "closed" and _probe_full.strip():
                # (a) recompilable in place, in the root the probe ACTUALLY lives in (cold-route → ztare_proofs).
                _cdir = (locals().get("_probe_root") or sub) / "closures"
                _cdir.mkdir(parents=True, exist_ok=True)
                _closure_lean = _cdir / f"{target_name}.lean"
                _closure_lean.write_text(_probe_full, encoding="utf-8")
            _cert = {
                "ts": _run_start,
                "target": target_name,
                "outcome": r0.get("outcome"),
                "provider": r0.get("provider") or r0.get("winner"),
                "proof_text": r0.get("proof_text") or "",
                "recompilable_probe": _probe_full,        # full self-contained .lean, portable
                "closure_lean": str(_closure_lean) if _closure_lean else None,  # in-substrate copy
                "governance": res.get("governance"),
                "matched_negative_control": r0.get("matched_negative_control"),
                "substrate": str(sub),
                "wall_s": r0.get("provider_wallclock_s"),
            }
            # (b) tracked, durable, append-only audit ledger (survives even if the substrate is wiped).
            ADHOC_CLOSURE_CERTIFICATES.parent.mkdir(parents=True, exist_ok=True)
            with ADHOC_CLOSURE_CERTIFICATES.open("a", encoding="utf-8") as _cf:
                _cf.write(json.dumps(_cert) + "\n")
            res["closure_certificate"] = str(ADHOC_CLOSURE_CERTIFICATES)
            res["closure_lean"] = str(_closure_lean) if _closure_lean else None
        except Exception as _e:
            res["closure_certificate_error"] = repr(_e)[:120]
    # compounding: on a clean closure, bank the proof's invented helpers for siblings. Bank from the
    # closure's PROOF_TEXT (the leaf proves in its own probe file; the original `src` keeps its
    # `sorry`, so re-reading src banked nothing — cold-review-adjacent catch 2026-06-03).
    if r0.get("outcome") == "closed" and (r0.get("proof_text") or "").strip():
        fam = sub / f"family_context_{target_name.split('_')[0]}.lean"
        if not fam.exists():
            _lib.init_context(fam, source_text.split(f"theorem {target_name}")[0])
        res["banked_helpers"] = _lib.bank(fam, r0.get("proof_text") or "")
    # MECHANIZED apparatus-vs-math tag on EVERY non-closure (convergent eigenquestion, gemini+codex
    # 2026-06-05): never again launder a gated/budget/toolchain failure as "math-hard". The decompose
    # move being OFF (ZTARE_CONJECTURE_DECOMPOSE!=1) is the apparatus signal that bit the P1 runs.
    if r0.get("outcome") not in ("closed", None):
        try:
            if r0.get("outcome") == "rejected_governance":
                # the MOAT fired: the solver GAMED the goal and governance REFUSED — neither apparatus
                # nor math (it's a caught cheat). Tagging it apparatus would launder the moat-event as a
                # resource limit (P1 deep run 2026-06-05 exposed exactly this mis-tag).
                r0["failure_class"] = {"class": "cheat_caught", "error_class": "governance_rejected",
                                       "reason": res.get("rejected_reason") or "governance refused a laundered closure"}
            else:
                from ztare.leanmill.solver.failure_class import classify_failure
                r0["failure_class"] = classify_failure(
                    error_tail=(r0.get("tail") or res.get("rejected_reason") or ""),
                    stop_reason=(r0.get("stop_reason") or res.get("dag_stop_reason") or ""),
                    conjecture_enabled=(os.environ.get("ZTARE_CONJECTURE_DECOMPOSE") == "1"))
        except Exception as _e:  # noqa: BLE001
            r0["failure_class"] = {"class": "unknown", "reason": f"classifier error: {_e!r}"[:120]}
    # AUTONOMOUS RECURSION (ZTARE_LEANMILL_ISO_ROUTE=1, default-OFF = parity): an HONEST non-closure
    # (exact_gap / open / failed — NOT a caught cheat) on a strong_missing target → route to the blueprint
    # producer (isomorphism_decompose) and recurse on its sub-rungs. This is what makes leanmill recursively
    # self-solve: solve_decomposition re-enters solve_adhoc per lemma, which re-enters this route on a
    # strong_missing exact_gap sub-rung, until citable leaves (depth-guarded inside route_and_solve). The
    # MOAT case (rejected_governance) is excluded — a caught cheat is not re-decomposed. Fail-open.
    if (os.environ.get("ZTARE_LEANMILL_ISO_ROUTE") == "1"
            and r0.get("outcome") in ("exact_gap", "open", "failed", "failed_compile")):
        try:
            from ztare.leanmill.solver.isomorphism_decompose import route_and_solve as _ras
            res["iso_route"] = _ras(source_text, target_name, goal, lean_root=sub,
                                    timeout_s=timeout_s, substrate=sub)
        except Exception as _e:  # noqa: BLE001 — routing is best-effort; never break the solve
            res["iso_route"] = {"error": repr(_e)[:160]}
    return res


def solve_adhoc_governed(target_name: str, source_text: str, goal: str, *,
                         max_gov_retries: int | None = None, **kw) -> dict:
    """Governance-feedback→retry wrapper — PARITY with the C-row path (which re-attempts a
    governance-rejected row via the work_queue). Compile-level retry is already handled INSIDE the
    leaf (Layer-5 / timeout-retry); this adds the missing GOVERNANCE-level retry: on a CONFIRMED
    `rejected_governance` of a CLOSED proof (statement altered / laundering), feed the specific
    blocker back to the agent as source-comment guidance and re-solve, bounded by
    ZTARE_GOV_MAX_RETRIES (default 1). A non-rejected outcome (clean closure / open / failed) breaks
    immediately — governance-retry only helps the gamed-then-rejected case, not an honest miss."""
    if max_gov_retries is None:
        max_gov_retries = int(os.environ.get("ZTARE_GOV_MAX_RETRIES", "1"))
    feedback = ""
    res = None
    for attempt in range(max_gov_retries + 1):
        src = source_text + ("" if not feedback else
            "\n\n-- ⚠ GOVERNANCE REJECTED the previous attempt: " + feedback +
            "\n-- The theorem statement AND every definition/structure it depends on are FIXED.\n"
            "-- Do NOT add or alter any structure field, hypothesis, or definition; introduce NO\n"
            "-- axioms beyond {propext, Classical.choice, Quot.sound} and NO sorry/admit.\n"
            "-- Prove the statement EXACTLY AS GIVEN, genuinely.\n")
        res = solve_adhoc(target_name, src, goal, **kw)
        res["governance_retry_attempt"] = attempt
        r0 = (res.get("results") or [{}])[0]
        if r0.get("outcome") != "rejected_governance":
            break  # clean closure, open, or honest fail → governance-retry can't help
        feedback = res.get("rejected_reason") or "; ".join(r0.get("governance_blockers") or [])
    return res


def solve_family(corpus_preamble: str, siblings: "list[dict]", *,
                 provider: str | None = None, timeout_s: int = 500,
                 mode: str = "dag_search", substrate: "Path | None" = None,
                 compound: bool = True) -> dict:
    """Compounding-engine driver (the self-improving flywheel) — solve an ORDERED family of
    siblings through the governed pipeline, threading one shared family context so each closure's
    invented helpers are provisioned to every later sibling.

    `siblings`: ordered list of {"name": <decl name ending in sorry>, "decl": <the `theorem … :=
    by sorry` block>}. `corpus_preamble`: the shared imports/defs/Props every sibling needs.

    Per sibling: source = (provision(ctx) if compound else corpus_preamble) + the sibling's decl;
    solve via `solve_adhoc` (governed + leakage-gated); on a clean closure, bank the proof's NEW
    invented helpers into the shared ctx for later siblings. `compound=False` gives the BASELINE
    arm (corpus only, no banked helpers) — the A/B that measures whether closure-rate accelerates
    as the library grows. Non-iatrogenic: banked decls are kernel-verified, every closure is
    independently kernel-gated, and a non-porting helper surfaces as a compile error not a false
    closure (see family_lemma_library)."""
    from ztare.leanmill.solver import family_lemma_library as _lib
    sub = Path(substrate) if substrate else DEFAULT_LEAN_ROOT_FOR_VERIFY
    ctx = sub / "family_context_FLYWHEEL.lean"
    _lib.init_context(ctx, corpus_preamble)
    # CORPUS names are present in BOTH arms — they are NOT compounding. The reuse metric must count
    # only references to BANKED helpers (decls added by prior closures), excluding the corpus, or it
    # reports a spurious "reuse" from corpus-decl references (flywheel run 2026-06-03 catch).
    corpus_names = _lib.decl_names(corpus_preamble)
    out = {"compound": compound, "n_siblings": len(siblings), "siblings": [],
           "library_growth": [], "banked_total": 0}
    _iy_hist: list = []   # information-yield iteration history (REUSE validator primitive)
    # MDL-OPTIMAL LIBRARY (default OFF until lift-tested): when ON, the leaf is provisioned only the
    # banked lemmas that EARN their place (net compressors + under-exposed provisionals) — proven
    # dead weight is dropped from the context. The reuse/exposure LEDGER is always recorded (cheap,
    # side-effect-only) so the report + the flat-vs-MDL A/B have data even in the default flat mode.
    _use_mdl = os.environ.get("ZTARE_LEANMILL_MDL_LIBRARY") == "1"
    n_closed = 0
    for i, sib in enumerate(siblings):
        name, decl = sib["name"], sib["decl"]
        if compound:
            preamble = _lib.provision_mdl(ctx) if _use_mdl else _lib.provision(ctx)
            # exposure = the banked lemmas the leaf actually saw this iteration (KEEP set under MDL,
            # all banked under flat); exposure-without-reuse is what eventually marks dead weight.
            _provisioned_banked = sorted(_lib.decl_names(preamble) - corpus_names)
            _lib.record_exposure(ctx, _provisioned_banked)
        else:
            preamble, _provisioned_banked = corpus_preamble, []
        lib_size_before = len(_lib.decl_names(_lib.provision(ctx))) if compound else 0
        source_text = preamble.rstrip() + "\n\n" + decl.strip() + "\n"
        res = solve_adhoc(name, source_text, "", provider=provider,
                          timeout_s=timeout_s, mode=mode, substrate=sub)
        rlist = res.get("results") or [{}]
        r0 = rlist[0] if rlist else {}
        closed = r0.get("outcome") == "closed"
        proof_text = r0.get("proof_text") or ""
        banked_now = []
        reused = 0
        if closed:
            n_closed += 1
            if compound:
                # reuse = references to BANKED helpers ONLY (prior context decls MINUS the corpus),
                # so corpus-decl references (present in both arms) cannot inflate the signal.
                banked_so_far = _lib.decl_names(_lib.provision(ctx)) - corpus_names
                reused = sum(proof_text.count(n) for n in banked_so_far if n not in (name,))
                # Bank the CLOSED SIBLING THEOREM itself (decl + proof), not just intra-proof helpers
                # — in a coherent theory build-up the SIBLINGS are the reusable lemmas; banking L1a
                # (closed) is what lets L1b/L2a cite it instead of re-deriving (the SCALE mechanism;
                # the prior body-only banking found nothing because the leaf proves inline). 2026-06-04.
                import re as _re
                closed_thm = decl
                if proof_text.strip():
                    closed_thm = _re.sub(r":=\s*by\s+sorry\s*$", ":= " + proof_text.strip(), decl.strip())
                    if closed_thm == decl.strip():        # decl didn't end in `:= by sorry` as expected
                        closed_thm = decl.split(":=")[0].rstrip() + " := " + proof_text.strip()
                banked_now = _lib.bank(ctx, closed_thm)    # banks the named sibling theorem
                banked_now += _lib.bank(ctx, proof_text)   # + any genuine intra-proof helpers
                out["banked_total"] += len(banked_now)
        out["siblings"].append({
            "order": i, "name": name, "closed": closed,
            "outcome": r0.get("outcome"), "lib_size_before": lib_size_before,
            "banked_this_sibling": banked_now, "banked_helper_refs_in_proof": reused,
            "inadmissible": bool(r0.get("inadmissible")) if "inadmissible" in r0 else None,
            "frontier_triage": r0.get("frontier_triage"),
            "in_repo_reference_check": r0.get("in_repo_reference_check"),
        })
        # library growth = BANKED helpers only (excludes the fixed corpus), so the flywheel signal
        # is "does the reusable-lemma library actually grow", not "how big is the corpus".
        out["library_growth"].append(
            len(_lib.decl_names(_lib.provision(ctx)) - corpus_names) if compound else 0)
        # INFORMATION-YIELD routing (REUSE the autoresearch primitive — not a rebuild): treat each
        # sibling as an iteration, score = cumulative library growth + reuse (the SCALE info gained),
        # and let `evaluate_information_yield` say CONTINUE / REFRESH / PIVOT when the build-up stops
        # yielding (stagnant banking). Advisory here (recorded, doesn't halt) — wired so the loop is
        # info-yield-aware + ready to gate on; queued for lift-testing. 2026-06-04.
        try:
            from ztare.validator.core.information_yield import (
                evaluate_information_yield as _iy, IterationSignal as _Sig)
            _score = (out["library_growth"][-1] if compound else 0) + reused
            _improved = closed and (reused > 0 or (compound and out["library_growth"][-1] >
                                                   (out["library_growth"][-2] if len(out["library_growth"]) > 1 else 0)))
            _iy_hist.append(_Sig(iteration_index=i, score=int(_score),
                                 weakest_point=("" if closed else name), score_improved=bool(_improved)))
            out["siblings"][-1]["info_yield"] = _iy(_iy_hist).action.value
        except Exception as _e:
            out["siblings"][-1]["info_yield_error"] = repr(_e)[:100]
    out["closed"] = n_closed
    out["closure_rate"] = round(n_closed / max(1, len(siblings)), 3)
    return out


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
    pa = sub.add_parser("adhoc", help="run a ONE-OFF lemma through the full governed pipeline "
                                      "(leakage-gated + compounding). The canonical ad-hoc entry — "
                                      "use this instead of bespoke harnesses.")
    pa.add_argument("--target", required=True, help="the lemma's declaration name (ends in sorry)")
    pa.add_argument("--source-file", required=True, help=".lean file: full preamble + the sorried target")
    pa.add_argument("--goal", default="", help="optional goal-text excerpt (for the contract)")
    pa.add_argument("--provider", default=None)
    pa.add_argument("--timeout", type=int, default=500)
    pa.add_argument("--mode", choices=["cascade", "dag_search"], default="dag_search")
    pa.add_argument("--substrate", default=None, help="lake project dir (default: ztare_proofs)")
    pr = sub.add_parser("repair", help="govern-repair a proof that BREAKS under the current "
                                       "toolchain (Mathlib version-migration). Confirms the break, "
                                       "re-proves via the governed pipeline, emits a migration diff.")
    pr.add_argument("--target", required=True, help="the theorem/lemma name whose body to repair")
    pr.add_argument("--source-file", required=True, help=".lean file containing the broken proof")
    pr.add_argument("--provider", default=None)
    pr.add_argument("--timeout", type=int, default=500)
    pr.add_argument("--substrate", default=None)
    pr.add_argument("--force", action="store_true", help="skip the break-confirm (known-broken input)")
    pr.add_argument("--out", default=None)
    pf = sub.add_parser("family", help="run an ORDERED family through the COMPOUNDING engine "
                                        "(bank each closure's helpers → provision to later siblings). "
                                        "The self-improving flywheel; --no-compound = baseline arm.")
    pf.add_argument("--spec", required=True,
                    help='JSON: {"corpus_preamble": "...", "siblings": [{"name":..,"decl":..}, ...]}')
    pf.add_argument("--no-compound", action="store_true",
                    help="BASELINE arm: corpus only, no banked-helper provisioning (for the A/B).")
    pf.add_argument("--provider", default=None)
    pf.add_argument("--timeout", type=int, default=500)
    pf.add_argument("--mode", choices=["cascade", "dag_search"], default="dag_search")
    pf.add_argument("--substrate", default=None)
    pf.add_argument("--out", default=None, help="write the full result JSON here")
    sub.add_parser("selfcheck",
                   help="fail-loud deploy verification: elan resolves, solver "
                        "modules import, a trivial proof COMPILES and a sorry "
                        "proof is REJECTED. Run on every fresh node before solving.")
    args = ap.parse_args()

    # Mechanized fix for `lake_not_on_PATH`: bootstrap the elan bin dir into this
    # process's PATH so every child (deterministic compiles AND dispatched agents
    # that shell out to `lake env lean`) finds lake/lean regardless of whether we
    # were launched from a login shell, nohup, cron, or ssh-exec.
    from ztare.gates.lean_compile_primitives import ensure_elan_on_path
    _elan = ensure_elan_on_path()
    if _elan is None and not getattr(args, "dry_run", False):
        print("WARN: elan/lake not found (~/.elan/bin absent and not on PATH); "
              "compiles will fail. Install lean toolchain or set ELAN_HOME.", flush=True)

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

    if args.cmd == "adhoc":
        src_text = Path(args.source_file).read_text(encoding="utf-8")
        sub = Path(args.substrate) if args.substrate else None
        res = solve_adhoc_governed(args.target, src_text, args.goal, provider=args.provider,
                                   timeout_s=args.timeout, mode=args.mode, substrate=sub)
        print(json.dumps(res, indent=2))
        return 0

    if args.cmd == "repair":
        from ztare.leanmill.solver import proof_repair as _pr
        from ztare.gates.lean_compile_primitives import run_lake_compile_source
        sub_dir = Path(args.substrate) if args.substrate else DEFAULT_LEAN_ROOT_FOR_VERIFY
        lake_bin = (_elan + "/lake") if _elan else "lake"
        src_text = Path(args.source_file).read_text(encoding="utf-8")

        def _compile_fn(s: str):
            ok, tail = run_lake_compile_source(s, lean_root=str(sub_dir),
                                               timeout_s=max(60, args.timeout // 2),
                                               prefix="RepairConfirm")
            return bool(ok), tail or ""

        rep = _pr.repair(src_text, args.target, project_dir=str(sub_dir), lake_bin=lake_bin,
                         solve_adhoc=solve_adhoc, compile_fn=_compile_fn, provider=args.provider,
                         timeout_s=args.timeout, substrate=sub_dir, force=args.force)
        if args.out:
            Path(args.out).write_text(json.dumps(rep, indent=2), encoding="utf-8")
        print(json.dumps(rep, indent=2))
        return 0

    if args.cmd == "family":
        spec = json.loads(Path(args.spec).read_text(encoding="utf-8"))
        sub_dir = Path(args.substrate) if args.substrate else None
        res = solve_family(spec["corpus_preamble"], spec["siblings"],
                           provider=args.provider, timeout_s=args.timeout,
                           mode=args.mode, substrate=sub_dir,
                           compound=not args.no_compound)
        if args.out:
            Path(args.out).write_text(json.dumps(res, indent=2), encoding="utf-8")
        print(json.dumps(res, indent=2))
        return 0

    if args.cmd == "selfcheck":
        # Fail-loud deploy verification. Mechanizes the bugs hit on 2026-05-31
        # (missing solver subtree, lake_not_on_PATH, broken oracle) so a fresh
        # distributed node proves it can compile + reject sorry BEFORE solving.
        from ztare.gates.lean_compile_primitives import run_lake_compile_source
        fails = []
        # 1. toolchain resolves
        if _elan is None:
            fails.append("elan/lake not resolvable (~/.elan/bin absent and not on PATH)")
        else:
            print(f"OK  elan bin dir: {_elan}")
        # 2. solver subtree imports
        try:
            import importlib
            for m in ("contract", "deterministic", "llm_provers", "governed_dag_search"):
                importlib.import_module(f"ztare.leanmill.solver.{m}")
            print("OK  solver modules import (contract/deterministic/llm_provers/governed_dag_search)")
        except Exception as e:
            fails.append(f"solver module import failed: {e!r}")
        # 3. positive control: a trivial proof MUST compile clean (no import → fast)
        try:
            ok_pos, _ = run_lake_compile_source(
                "theorem _selfcheck_ok : True := trivial\n",
                DEFAULT_LEAN_ROOT_FOR_VERIFY, timeout_s=180,
                prefix="leanmill_selfcheck_pos_")
            if ok_pos:
                print("OK  positive control: trivial proof compiles (lake pipeline live)")
            else:
                fails.append("positive control FAILED: trivial proof did not compile "
                             "(lake/toolchain/lean_root broken)")
        except Exception as e:
            fails.append(f"positive control errored: {e!r}")
        # 4. negative control: a sorry proof MUST be rejected (oracle fires)
        try:
            ok_neg, _ = run_lake_compile_source(
                "theorem _selfcheck_sorry : True := by sorry\n",
                DEFAULT_LEAN_ROOT_FOR_VERIFY, timeout_s=180,
                prefix="leanmill_selfcheck_neg_")
            if ok_neg is False:
                print("OK  negative control: sorry proof REJECTED (no-false-closure oracle live)")
            else:
                fails.append(f"negative control FAILED: sorry proof not rejected (ok={ok_neg!r}) "
                             "— no-false-closure oracle is broken")
        except Exception as e:
            fails.append(f"negative control errored: {e!r}")
        if fails:
            print("\nSELFCHECK: FAIL")
            for f in fails:
                print(f"  - {f}")
            return 1
        print("\nSELFCHECK: PASS — node can compile and rejects sorry. Safe to solve.")
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
