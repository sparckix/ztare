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
            `_agentic_leaf_warm_solve()` (the SINGLE leaf entry → best-of-N
            `solve_robust` → `agentic_leaf.solve_leaf`) dispatches the agent in
            the warm Lean project: it edits the probe, warm-checks, iterates,
            and — if it leaves the proof in its RESPONSE rather than the file —
            the leaf recovers it (`_recover_proof_from_response`). One warm-agent
            run has substantially higher P(close) than any single one-shot LLM
            call. Grounded in LeanAgent (Yang et al.
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
from dataclasses import asdict, dataclass, is_dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

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


def _public_path(value) -> str:
    """Repo-relative path for public artifacts; no local home-directory leaks. Delegates to the canonical
    `common.public_path` (was a byte-identical copy in typed_exit — the forgotten-sibling shape, de-duplicated
    2026-06-22). Passes this module's REPO so the relativization base is unchanged."""
    from ztare.leanmill.common import public_path as _pp
    return _pp(value, REPO)


def _public_text(value: str) -> str:
    """Scrub local absolute prefixes inside public notes/errors."""
    out = str(value or "")
    repo = str(REPO)
    home = str(Path.home())
    out = out.replace(repo + os.sep, "")
    out = out.replace(repo, ".")
    out = out.replace(home + os.sep, "<home>/")
    out = out.replace(home, "<home>")
    return out


def _public_sanitize(value):
    if isinstance(value, dict):
        return {k: _public_sanitize(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_public_sanitize(v) for v in value]
    if isinstance(value, tuple):
        return [_public_sanitize(v) for v in value]
    if isinstance(value, Path):
        return _public_path(value)
    if isinstance(value, str):
        return _public_text(value)
    return value


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
            "source_file": _public_path(contract.get("source_file")),
            "goal_excerpt": (contract.get("goal_excerpt") or "")[:200],
            "accepted_residual_class": contract.get("accepted_residual_class"),
        },
    }
    CARRIER_RECEIPT_LEDGER.parent.mkdir(parents=True, exist_ok=True)
    with CARRIER_RECEIPT_LEDGER.open("a") as f:
        f.write(json.dumps(_public_sanitize(entry)) + "\n")


def _attempts_conn() -> sqlite3.Connection:
    ATTEMPTS_DB.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(ATTEMPTS_DB), timeout=30)
    # Concurrency: WAL + busy_timeout so PARALLEL solver workers on ONE machine can share the attempts
    # DB without "database is locked" / lost writes (multi-core sharding of an A/B). Cross-MACHINE
    # writers still need a real DB or per-worker shards that merge — sqlite over a network FS is unsafe.
    try:
        con.execute("PRAGMA journal_mode=WAL")
        con.execute("PRAGMA busy_timeout=30000")
        con.execute("PRAGMA synchronous=NORMAL")
    except Exception:
        pass
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
                      ("move", "TEXT"), ("wallclock_s", "REAL"), ("run_tag", "TEXT"),
                      # carrier_live (#90): was the PROVIDER/substrate live at attempt time? NULL=unknown
                      # (treated live — back-compat for pre-existing rows), 1=live, 0=DEAD instrument (provider
                      # quota/auth-dead). Dynamic admissibility — the calibration filter drops carrier_live=0 so
                      # a provider outage (codex exhaustion) self-cleans WITHOUT moving the static date-cutoff.
                      ("carrier_live", "INTEGER")):
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


def _unratified_closes_count(row_id: str, since: str | None = None) -> int:
    """Count THIS run's close-attempts the governance did NOT ratify (compile_ok=1, ratified=0) — the anti-laundering gate
    refusing a laundered / non-assembling closure. Surfaced into failure_class so an exact_gap/open is not
    mis-summarized as a generic 'other_error' toolchain artifact when the real story is 'governance blocked
    N closes' (the denef debug 2026-06-09: 3 laundered closes of the open conjecture, all ratified=0, were
    buried under apparatus/other_error)."""
    with _attempts_conn() as con:
        q = "SELECT COUNT(*) FROM attempts WHERE row_id=? AND compile_ok=1 AND ratified=0"
        args: list = [row_id]
        if since:
            q += " AND attempt_at>=?"
            args.append(since)
        r = con.execute(q, args).fetchone()
    return r[0] if r else 0


def _record_attempt(row_id: str, provider: str | None, outcome: str,
                    compile_ok: bool, notes: str | None,
                    proof_state: dict | None = None,
                    est_p_close: float | None = None,
                    move: str | None = None,
                    wallclock_s: float | None = None,
                    carrier_live: "bool | None" = None) -> None:
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
    # #90: an INADMISSIBLE outcome IS a dead-carrier signal (the instrument wasn't usable — provider quota/auth
    # dead, substrate dead), so tag carrier_live=0 ⇒ the calibration filter drops it (apparatus_certificate rule:
    # a 0/N from a dead instrument must not enter calibration). One place, covers every _record_attempt caller;
    # conservative — only the explicit `inadmissible*` outcomes; a real closed/failed attempt stays NULL (=live).
    if carrier_live is None and isinstance(outcome, str) and outcome.startswith("inadmissible"):
        carrier_live = False
    public_notes = _public_text(notes or "")
    if proof_state is None:
        from ztare.leanmill.solver.proof_state import proof_state_signal
        proof_state = proof_state_signal(0 if compile_ok else 1, notes or "")
    # BEST-EFFORT telemetry: the attempts DB is calibration/observability, NOT a soundness surface (the kernel
    # + closure certs are the trust record). A transient sqlite error (e.g. a WAL `disk I/O error`) must NEVER
    # crash a multi-hour solve — it killed a healthy P1 RUNG-A run mid-decomposition (2026-06-18). Log + carry on.
    try:
        with _attempts_conn() as con:
            con.execute(
                "INSERT INTO attempts (row_id, attempt_at, provider, outcome, compile_ok, "
                "notes, goals_remaining, error_class, progress, est_p_close, move, wallclock_s, run_tag, carrier_live) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (row_id, datetime.now(timezone.utc).isoformat(), provider or "",
                 outcome, 1 if compile_ok else 0,
                 public_notes[-1000:],
                 proof_state.get("goals_remaining"), proof_state.get("error_class"),
                 proof_state.get("progress"), est_p_close, _move_label, wallclock_s, _run_tag,
                 (None if carrier_live is None else (1 if carrier_live else 0))),
            )
            con.commit()
    except Exception as _attempt_db_err:  # noqa: BLE001 — telemetry write must not be fatal to the solve
        import sys as _sys
        print(f"[telemetry] _record_attempt DB write skipped (non-fatal): {_attempt_db_err!r}",
              file=_sys.stderr, flush=True)





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
    src_path_str = ProofTarget.from_row(row).source_file   # source-only BY INTENT (not source_path's fallback)
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
                # `import Mathlib` is re-added by the verifier; drop a leading duplicate so the COMPILED
                # probe has one header-valid import (a second `import` after `open`/defs would error).
                prelude = _re.sub(r"\A\s*import\s+Mathlib\s*\n+", "", prelude, count=1)
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
                # COMMENT every rendered line. The enriched context is fed to the KERNEL by the
                # native/cold/frontier verify paths (not only to the LLM prompt); the raw lemma
                # previews (full of `:=`, `=`, `↔`) were landing as top-level Lean → the probe never
                # parsed, which is why those moves were silently dead. `--` per line keeps the prompt
                # value and makes the compiled probe valid.
                commented = "\n".join(("-- " + ln) if ln.strip() else "--"
                                      for ln in rendered.splitlines())
                shelf_block = f"-- candidate premises (semantic shelf, cosine-similar to goal):\n{commented}\n"
                # SEMANTIC-REUSE defeq tier (2026-06-25, retrieve→VERIFY): the shelf RETRIEVED these by
                # embedding (vocab-agnostic); now KERNEL-VERIFY whether the goal is DEFEQ to a banked hit
                # (`@goal=@cand:=rfl`) and, if so, surface a STRONG cite signal — the cross-vocab reuse the
                # α-cache can't see (`PoolState.WellFormed` ≡ `PoolWellFormed`). Advisory only (the agent cites,
                # the kernel re-verifies — zero new soundness surface); fail-safe + BOUNDED (top hits, capped
                # probes) so it never breaks or slows the context build. Default-on (sound + cheap on the warm
                # env); ZTARE_LEANMILL_SEMANTIC_REUSE=0 reverts.
                try:
                    from ztare.leanmill.solver.proof_cache import (semantic_reuse_enabled,
                                                                   defeq_reuse_candidate)
                    if semantic_reuse_enabled() and isinstance(shelf, dict):
                        _cands = [{"name": h.get("name", ""), "statement": h.get("preview", "")}
                                  for h in (shelf.get("hits") or [])[:5]
                                  if h.get("name") and h.get("preview")]
                        _gp = _enriched_goal_stub(source_text, target_name, base_goal, row) or base_goal
                        _hit = defeq_reuse_candidate(_gp, (target_name or "adhoc_probe"), _cands,
                                                     shelf_lean_root, max_check=3)
                        if _hit:
                            shelf_block = (f"-- ★ KERNEL-DEFEQ reuse: the goal is the SAME Prop as banked "
                                           f"`{_hit['name']}` — close directly with `exact @{_hit['name']}`.\n"
                                           + shelf_block)
                except Exception:  # noqa: BLE001 — the defeq tier is advisory; never break the context build
                    pass
    except Exception:
        shelf_block = ""
    # The GOAL piece must be a COMPILE-VALID theorem stub ending `:= by` (the kernel verifies the
    # enriched context in the native/cold/frontier paths, not just the LLM prompt). Prefer the REAL
    # statement verbatim from source (robust — no signature reconstruction); else wrap row['goal'].
    goal_piece = _enriched_goal_stub(source_text, target_name, base_goal, row) or base_goal
    pieces = [p for p in (prelude, shelf_block, goal_piece) if p]
    return "\n\n".join(pieces)


def _enriched_goal_stub(source_text: str, target_name: str, base_goal: str, row: dict) -> str:
    """A compile-valid theorem stub ending `:= by`, for the enriched context's goal piece.

    Robust by construction: takes the target's statement VERBATIM from the source (decl text up to its
    `:=`, then `:= by`), so the statement is never reconstructed by a brittle regex; falls back to
    wrapping the bare signature in `row['goal']` only when the source is unavailable.
    """
    from ztare.leanmill import lean_source as _ls   # single source of truth for Lean parsing
    name = (target_name or row.get("target_theorem_name") or "adhoc_probe")
    return _ls.wrapped_goal_stub(source_text, name, base_goal)


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


def _native_compile_stub(source_text: str, target_name: str) -> str:
    """Build a COMPILE-valid theorem stub for native_hammer from the REAL source file.

    The statement is kept VERBATIM (binders + conclusion, exactly as Lean parses them); only the
    target's trailing `sorry` proof is swapped for `:= by` (the caller appends the tactic). A single
    leading `import Mathlib` is dropped (the verifier re-adds it). Returns "" if there is no swappable
    proof. This never RECONSTRUCTS the statement — the old path regex-extracted a bare signature and
    shipped a malformed, never-parsing blob, so native_hammer was dead on every adhoc target. Here Lean
    parses the original text; a bad swap fails to compile (detectable) rather than silently mis-stating.
    """
    from ztare.leanmill import lean_source as _ls   # single source of truth for Lean parsing
    return _ls.compile_stub(source_text, target_name)


def _native_hammer_self_test(lean_root: Path, timeout_s: int = 300) -> tuple[bool, str]:
    """POSITIVE CONTROL: native_hammer must close a trivial target through the FULL probe path
    (stub-build + verify). If it can't compile `: True := by trivial`, the probe-assembly harness is
    broken (not the math) and every native_hammer NEGATIVE is inadmissible. Run before trusting a 0/N.
    """
    import tempfile as _tf
    with _tf.TemporaryDirectory() as _td:
        sp = Path(_td) / "NhSmoke.lean"
        sp.write_text("import Mathlib\n\ntheorem nh_smoke : True :=\nsorry\n", encoding="utf-8")
        row = {"row_id": "native_hammer::selftest", "target_theorem_name": "nh_smoke",
               "goal": ": True", "source_file": str(sp), "sorried_file": str(sp)}
        ok, _proof, tail = _native_hammer_probe(row, lean_root, timeout_s)
    return ok, ("native_hammer probe path OK (closed trivial control)" if ok
                else f"native_hammer probe path BROKEN — cannot close a trivial control: {tail[-200:]}")


# ── Strategist-gate positive control (the dead-instrument lesson, one level up) ──────────────────────
# The COMPILE-carrier moves (native_hammer) get `_native_hammer_self_test`. The GENERATE-carrier moves
# (conjecture / specialize / decompose) are gated by `conjecture_advances` / `decomposition_dag_audit` —
# kernel checks that could be SILENTLY always-False (a broken load-bearing `: True` swap, a citation regex
# that never matches the real proof format, a `_compile_probe` wired to a dead lean_root). If a gate is
# dead it REJECTS every strategist move → zero strategist closures → a strategist NEGATIVE reads as a real
# null when it is a dead-gate artifact. P1 rides ENTIRELY on these gates, so this control is the
# admissibility guard for any decompose-based run. Fixtures are self-contained ℕ arithmetic (version-
# independent), so one run per lean_root validates the gates everywhere. Each gate must PASS a known-good
# decomposition (carrier fires) AND REJECT a known-bad one (circular / non-load-bearing — the gate has
# teeth); both legs through the SAME code path the real moves use.
_CONJ_POS = (  # genuine reduction: G (2*n=n+n) follows from L (n+n=2*n); L load-bearing; non-circular
    "theorem sg_helper (n : Nat) : n + n = 2 * n := by sorry",
    "theorem sg_tgt (n : Nat) : 2 * n = n + n := by rw [sg_helper]",
    "sg_helper", "2 * n = n + n")
_CONJ_NEG_CIRCULAR = (  # L restates G verbatim → must be rejected as circular (no reduction)
    "theorem sg_helper (n : Nat) : 2 * n = n + n := by sorry",
    "theorem sg_tgt (n : Nat) : 2 * n = n + n := by exact sg_helper n",
    "sg_helper", "2 * n = n + n")
_CONJ_NEG_NOTLB = (  # L cited but `ring` proves G without it → must be rejected as not load-bearing
    "theorem sg_helper (n : Nat) : n + n = 2 * n := by sorry",
    "theorem sg_tgt (n : Nat) : 2 * n = n + n := by have _ := sg_helper n; ring",
    "sg_helper", "2 * n = n + n")


def _strategist_gates_self_test(lean_root: Path, timeout_s: int = 60) -> dict:
    """POSITIVE+NEGATIVE control for the generate-carrier gates. Returns {gate: bool, _gate_detail: str}.
    A gate is `True` only if its known-good fixture PASSES and BOTH teeth-fixtures are REJECTED."""
    from ztare.leanmill.solver import conjecture as _cj
    out: dict = {}
    pos_ok, pos_msg = _cj.conjecture_advances(*_CONJ_POS[:3], lean_root, timeout_s,
                                              goal_conclusion=_CONJ_POS[3])
    neg_c, _ = _cj.conjecture_advances(*_CONJ_NEG_CIRCULAR[:3], lean_root, timeout_s,
                                       goal_conclusion=_CONJ_NEG_CIRCULAR[3])
    neg_l, _ = _cj.conjecture_advances(*_CONJ_NEG_NOTLB[:3], lean_root, timeout_s,
                                       goal_conclusion=_CONJ_NEG_NOTLB[3])
    out["conjecture_advances"] = bool(pos_ok) and not neg_c and not neg_l
    if not out["conjecture_advances"]:
        out["_conjecture_advances_detail"] = (f"positive={pos_ok!r} ({pos_msg}); "
                                              f"circular_rejected={not neg_c}; nonloadbearing_rejected={not neg_l}")
    dag_pos, dag_v = _cj.decomposition_dag_audit(
        ["theorem sg_dl1 (n : Nat) : n + 0 = n := by sorry",
         "theorem sg_dl2 (n : Nat) : 0 + n = n := by sorry"],
        "theorem sg_dtgt (n : Nat) : n + 0 + (0 + n) = n + n := by rw [sg_dl1, sg_dl2]",
        ["sg_dl1", "sg_dl2"], lean_root, timeout_s, goal_conclusion="n + 0 + (0 + n) = n + n")
    dag_neg, _ = _cj.decomposition_dag_audit(  # cited but `rfl` proves G without the lemma → not load-bearing
        ["theorem sg_dl1 (n : Nat) : n + 0 = n := by sorry"],
        "theorem sg_dtgt (n : Nat) : n + n = n + n := by have _ := sg_dl1 n; rfl",
        ["sg_dl1"], lean_root, timeout_s, goal_conclusion="n + n = n + n")
    out["decomposition_dag_audit"] = bool(dag_pos) and not dag_neg
    if not out["decomposition_dag_audit"]:
        out["_decomposition_dag_audit_detail"] = (f"positive={dag_pos!r} ({dag_v}); "
                                                  f"nonloadbearing_rejected={not dag_neg}")
    return out


_PREFLIGHT_CACHE: dict = {}


def _preflight_dead_loud_record(move: str, lean_root, detail: str, until_clause: str,
                                kind: str = "DEAD MOVE") -> None:
    """Loud banner + an attempts-DB row when a move/gate fails its positive control — so a dead carrier
    can never be a silent null again (the dead-instrument lesson). Best-effort DB write."""
    bar = "=" * 70
    print(f"\n{bar}\n⚠ {kind} — {move} failed its positive control on {lean_root}\n"
          f"  {detail}\n  Negatives from {move} are INADMISSIBLE until {until_clause}.\n{bar}\n", flush=True)
    try:
        with _attempts_conn() as _c:
            _c.execute(
                "INSERT INTO attempts (row_id, attempt_at, provider, outcome, compile_ok, notes, move) "
                "VALUES (?,?,?,?,?,?,?)",
                (f"preflight::{move}", datetime.now(timezone.utc).isoformat(),
                 move, "harness_dead", 0, _public_text(str(detail))[:300], move))
    except Exception:
        pass


def preflight_moves_alive(lean_root, timeout_s: int = 120) -> dict:
    """STANDING POSITIVE CONTROL — run before trusting any move NEGATIVE. Asks whether native_hammer
    (the cheap deterministic cascade) can close a trivial `: True := by trivial`. If not, its
    probe-assembly harness is broken and every native_hammer `failed_compile` is INADMISSIBLE — the
    exact failure that hid the dead-instrument bug for months. Cached per lean_root; loud + recorded
    in the attempts DB when dead so the signal can never be silent again. Non-blocking by default.

    TIMEOUT (2026-06-09): no longer hand-guessed — `cold_calibration.cold_safe_timeout` floors it to the box's
    MEASURED cold-Mathlib reload × margin. The 60s default false-failed on a cold page cache (the reload alone is
    ~60-90s here) and wrongly killed native_hammer; the floor is now self-learnt per box, so this can't recur.
    """
    # GENERATE-carrier gates (conjecture / decompose) are only checked when the strategist menu is live (a
    # strategist NEGATIVE is only interpretable then) — keeps the bare-leaf arm fast. CACHE KEY MUST include
    # `_strat_on`: an A/B runs arm A (bare, menu off) then arm B (apparatus, menu on) on the SAME lean_root;
    # keying on the root alone would serve arm B the bare-arm cache and SKIP the strategist battery entirely
    # — silently re-opening the dead-gate hole this control exists to close (seam bug, caught pre-launch).
    _strat_on = (os.environ.get("ZTARE_LEANMILL_MENU") == "full"
                 or any(os.environ.get(f) == "1" for f in
                        ("ZTARE_CONJECTURE_DECOMPOSE", "ZTARE_LEANMILL_GENERALIZE",
                         "ZTARE_LEANMILL_SPECIALIZE", "ZTARE_LEANMILL_COMPOSITE_RATIFY")))
    key = (str(lean_root), _strat_on)
    if key in _PREFLIGHT_CACHE:
        return _PREFLIGHT_CACHE[key]
    from ztare.leanmill.cold_calibration import cold_safe_timeout
    timeout_s = cold_safe_timeout(timeout_s, lean_root)   # self-measured cold-Mathlib floor — kills the hand-
    #   guessed cold-false-fail that wrongly marked native_hammer dead (the bug class, mechanized away).
    try:
        ok, msg = _native_hammer_self_test(Path(lean_root), timeout_s)
    except Exception as e:  # noqa: BLE001
        ok, msg = False, f"self-test crashed: {e!r}"
    alive = {"native_hammer": ok}
    if not ok:
        _preflight_dead_loud_record("native_hammer", lean_root, msg,
                                    "the probe assembly is fixed")
    # Same loud + DB-record contract as native. Validated 2026-06-08 (both gates ALIVE on v4.30).
    if _strat_on:
        try:
            sg = _strategist_gates_self_test(Path(lean_root), timeout_s)
        except Exception as e:  # noqa: BLE001
            sg = {"conjecture_advances": False, "decomposition_dag_audit": False,
                  "_conjecture_advances_detail": f"self-test crashed: {e!r}",
                  "_decomposition_dag_audit_detail": f"self-test crashed: {e!r}"}
        for gate in ("conjecture_advances", "decomposition_dag_audit"):
            gok = bool(sg.get(gate))
            alive[gate] = gok
            if not gok:
                _preflight_dead_loud_record(gate, lean_root, sg.get(f"_{gate}_detail", ""),
                                            "the gate's positive control passes", kind="DEAD GATE")
    _PREFLIGHT_CACHE[key] = alive
    return alive


# Tactic cascade for Layer 2 (free + deterministic; ranked by typical hit rate
# on bare-Mathlib targets). Each tactic is tried as a standalone closure
# candidate `:= by <tactic>` against the same enriched context the LLM layers
# see. The cascade reflects LeanHammer / Magnushammer empirical priors plus
# Mathlib's own `aesop` heuristics.
_NATIVE_HAMMER_TACTICS = (
    # ORDERING (2026-06-09 fix): CHEAP DETERMINISTIC closers FIRST, then the expensive library/analysis
    # search. The 2026-06-04 RCA correctly ADDED `exact?` + analysis automation but put them FIRST — under
    # the per-move cap (e.g. 120s) `exact?`'s whole-environment scan + `aesop` STARVE `decide`/`norm_num`,
    # so a goal closable by `decide`/`norm_num` in <5s caps out UNSOLVED (observed 2026-06-09: even
    # `Nat.factorial 12 = 479001600` and `¬ Nat.Prime 3233` "failed" purely on starvation — the budget was
    # spent on `exact?`/`aesop` before the cascade reached the cheap closers). Fast tactics FAIL-FAST
    # (rfl/decide/norm_num/omega exit in <5s when they don't apply), so trying them first costs ~nothing and
    # leaves the bulk of the budget for the genuinely-hard `exact?`/`aesop` goals — keeping the
    # citation-closing capability the RCA added WITHOUT starving the cheap closers.
    # ── fast deterministic closers (close-or-fail-fast) ──
    "rfl",
    "decide",
    "norm_num",
    "simp_all",
    "omega",
    "tauto",
    "positivity",
    "ring",
    "field_simp; ring",
    "linarith",
    # STRUCTURAL conjunction-assembler (2026-06-25): a target that is `C₁ ∧ … ∧ Cₙ` where each conjunct is
    # (defeq to) an in-scope PROVEN shelf lemma is closed MECHANICALLY here — `And.intro`-split, then cite the
    # shelf per conjunct — instead of falling through to a slow agentic decompose (the "why is assembling the
    # already-proven lemmas slow" RCA: `aesop`/`exact?` don't crack a wide, ∀-fronted `∧`, so it reached the LLM
    # solve). Deterministic structural closer, NOT a move: there is no discovery in And-intro + cite, so putting
    # it behind agency would be agency-creep. `repeat' apply And.intro` is N-agnostic (right-nested `∧`) and a
    # no-op on a non-conjunction (fails-fast → just the trailing cite); a conjunct that genuinely COMBINES shelf
    # lemmas (needs a real bridge) fails here and falls through to the agent — the Goldilocks split intact.
    "(repeat' apply And.intro) <;> (first | assumption | exact?)",
    # ── expensive library / analysis / heavy search (reserve the remaining budget) ──
    "exact?",                    # Lean library search — cite an existing/imported lemma (RCA 2026-06-04)
    "gcongr",                    # analysis/measure-theory automation for NS Track-B goals (RCA 2026-06-04)
    "fun_prop",
    "measurability",
    "aesop",
    "nlinarith",
    # `polyrith` REMOVED 2026-06-14: its external Sage service was shut down ("polyrith is no longer
    # available …"), so it ERRORED on every call — a dead cascade slot that burned budget + emitted a
    # confusing failure on exactly the polynomial goals P1 needs. The polynomial-ideal capability it
    # provided (linear-combination over a Gröbner basis) now lives in the `groebner` agent transport tool
    # (common/groebner_cert → `linear_combination`), which the leaf can elect.
    "aesop (config := { maxRuleApplications := 200 })",
)

# Typed config OVERRIDE (#49): the cascade above is the CANONICAL default; an operator may retune it via
# solver.yaml WITHOUT a code edit. Absent file ⇒ empty override ⇒ byte-parity (the default tuple stands).
from ztare.leanmill.solver.config import SolverConfig  # noqa: E402
_SOLVER_CONFIG = SolverConfig.load_default()
if _SOLVER_CONFIG.native_hammer_tactics:
    _NATIVE_HAMMER_TACTICS = tuple(_SOLVER_CONFIG.native_hammer_tactics)
_NATIVE_HAMMER_PER_TACTIC_FLOOR_S = _SOLVER_CONFIG.native_hammer_per_tactic_floor_s or 20


# (run_tag, campaign_env_fp, goal_sha) → last-tactic tail for cascades that ran ALL tactics and failed.
# Keyed by run_tag so a new run never inherits stale verdicts (the cross-run state-leak class), AND by the
# campaign warm-env fingerprint (theory file size:mtime) so banking a rung MID-RUN invalidates the memo:
# without that, a goal that failed BEFORE its enabling lemma was banked stays memoized-as-failed and is
# SKIPPED on re-attempt — silently defeating WITHIN-run compounding (the exact reuse the amnesia fix unlocks;
# the native cascade cites banked decls via exact?). No campaign substrate ⇒ fp="" ⇒ byte-parity. Process-
# local, telemetry-grade (a wrong skip costs a missed cheap closure, never soundness — the kernel re-verifies).
_NATIVE_CASCADE_FAILED_MEMO: "dict[tuple[str, str, str], str]" = {}


def _campaign_env_fingerprint() -> str:
    """Identity of the ACTIVE campaign warm-env (size:mtime of the theory file), so the native-cascade
    failure memo invalidates whenever a rung is banked into it. '' when no campaign substrate is registered
    (⇒ the env can't change mid-run ⇒ memo valid for the whole run = current behaviour). Gated by
    ZTARE_LEANMILL_DEDUP_ENV_AWARE (default-on); =0 reverts to an env-blind memo (the old behaviour) so the
    correctness-vs-cost trade — banking invalidates the whole memo ⇒ still-failing goals re-run once per env
    version — can be A/B'd without disabling the memo entirely (ZTARE_LEANMILL_NATIVE_DEDUP=0)."""
    if os.environ.get("ZTARE_LEANMILL_DEDUP_ENV_AWARE", "1") == "0":
        return ""
    try:
        from ztare.formal.repl_compile import get_campaign_substrate
        _cs = get_campaign_substrate()
        if _cs:
            st = Path(_cs).stat()
            return f"{st.st_size}:{st.st_mtime}"
    except Exception:  # noqa: BLE001 — fingerprint failure ⇒ treat as no-substrate (parity), never crash
        pass
    return ""
# Calibration-banner de-spam (2026-06-13 v6 log RCA): the full ~16-line move-calibration table was
# re-printed on EVERY solve_adhoc entry — 368 table lines (40%) of the 918-line v6 log, burying the
# actual reasoning. Print the FULL table only when it CHANGES (first time + on a real shift); otherwise
# a compact one-liner. ZTARE_LEANMILL_VERBOSE_CALIB=1 restores the always-full behaviour.
_LAST_CALIB_FP: "list[str | None]" = [None]


def _native_hammer_probe(row: dict, lean_root: Path, timeout_s: int) -> tuple[bool, str, str]:
    """Layer 2 — try the cheap deterministic tactic cascade on the goal.

    For each tactic in _NATIVE_HAMMER_TACTICS, write a probe file with the
    enriched context (file prelude + semantic shelf) and `:= by <tactic>`,
    compile via `lake env lean`. First tactic that closes wins. ~5-30 s per
    probe; total cap by per-tactic timeout = timeout_s / len(tactics).

    Returns (compile_ok, proof_text, transcript_tail).
    """
    base_goal = (row.get("goal") or "").strip()
    name = row.get("target_theorem_name") or ""
    # COMPILE the REAL source (statement verbatim, proof swapped) — NOT a reconstructed goal. The old
    # path fed _build_solver_context() (prelude + RAW semantic-shelf text + a bare, unwrapped signature)
    # straight to the compiler; that never parsed, so native_hammer was a dead instrument on every adhoc
    # target. The shelf is LLM-PROMPT context, not compiler input. Fix = real-file proof-swap.
    src_text = ""
    # TYPED CONTRACT (contracts.ProofTarget): the source/sorried fallback lives in ONE place now
    # (`source_path()`) instead of being re-spelled at each call-site where it can drift — behaviour-identical
    # here (source_file ?: sorried_file). First adoption of the kernel-wide typed-contract migration (#49).
    _sp = ProofTarget.from_row(row).source_path()
    if _sp and Path(_sp).exists():
        try:
            src_text = Path(_sp).read_text(encoding="utf-8", errors="replace")
        except Exception:
            src_text = ""
    enriched = _native_compile_stub(src_text, name)
    if not enriched:                         # fallback: wrap the bare signature into a valid stub
        if not base_goal:
            return False, "", "native_hammer: missing goal/source"
        if base_goal.lstrip().startswith(("theorem", "lemma", "example")):
            _cs = base_goal.rstrip()
            if not _cs.endswith(":= by"):
                # Strip the trailing `sorry`/proof and normalize to exactly one `:= by`. BUG FIX 2026-06-09:
                # the old `else _cs + " := by"` DOUBLE-appended for a goal ending `:= by sorry` →
                # `… := by := by` (malformed) ⇒ EVERY tactic failed to compile ⇒ native_hammer silently dead
                # on any adhoc row WITHOUT a source_file (the synthetic-row path). Now idempotent.
                _cs = _cs.removesuffix("sorry").rstrip()
                if _cs.endswith(":= by"):
                    pass                                   # already a valid stub
                elif _cs.endswith(":="):
                    _cs = _cs + " by"
                else:
                    _cs = _cs + " := by"
            enriched = _cs
        else:
            enriched = f"theorem {name or 'adhoc_probe'} {base_goal} := by"
    # IN-RUN DEDUP (v3 RCA 2026-06-12): the cascade is DETERMINISTIC — identical goal + identical tactic
    # list ⇒ identical verdict — yet v3 re-ran the FULL cascade 5× on one byte-identical goal (different
    # DAG nodes / nested solves carrying the same goal text; per-node `moves_tried` can't see across
    # nodes). Memo FAILURES only (a success ends the node + ProofCache banks it), keyed by run_tag so no
    # state leaks across runs (the arm/run-boundary state class), and ONLY when the cascade COMPLETED —
    # a budget-clipped cascade may behave differently on retry, so it is never memoized. Pure-efficiency
    # memo on a free move; no agency removed, no verdict changed. ZTARE_LEANMILL_NATIVE_DEDUP=0 reverts.
    import hashlib as _hl_nh
    _dedup_on = os.environ.get("ZTARE_LEANMILL_NATIVE_DEDUP", "1") != "0"
    _memo_key = (os.environ.get("ZTARE_SOLVER_RUN_TAG", ""),
                 _campaign_env_fingerprint(),   # bank-a-rung-mid-run invalidates stale failures (within-run compounding)
                 _hl_nh.sha256(f"{enriched}|{_NATIVE_HAMMER_TACTICS}".encode()).hexdigest())
    if _dedup_on and _memo_key in _NATIVE_CASCADE_FAILED_MEMO:
        return False, "", ("[native_hammer] in-run dedup: identical goal already FAILED the full cascade "
                           "this run (deterministic; re-run is waste) | prior: "
                           + _NATIVE_CASCADE_FAILED_MEMO[_memo_key][-160:])
    # Per-tactic budget: prefer cheap, abort the cascade as soon as one closes.
    per_tactic_timeout = max(_NATIVE_HAMMER_PER_TACTIC_FLOOR_S, int(timeout_s / max(1, len(_NATIVE_HAMMER_TACTICS))))
    # PER-MOVE CAP (ZTARE_LEANMILL_PERMOVE_CAPS=1, default-off=parity): the legacy per_tactic = timeout_s/N
    # is a FRACTION of the total that, summed over the 18-tactic cascade, runs ~400s and lets native_hammer
    # monopolise the whole per-target wallclock (the starvation leak — _cap on the outer arg was divided away
    # here). ON ⇒ treat `timeout_s` as the cascade's TOTAL DEADLINE: fixed per-tactic slice + STOP once the
    # cumulative budget is spent (the last tactic is clipped to fit), so native is bounded by its cap.
    import time as _t_nh
    from ztare.leanmill.cold_calibration import cold_safe_timeout
    _caps_on = os.environ.get("ZTARE_LEANMILL_PERMOVE_CAPS") != "0"   # DEFAULT-ON 2026-06-07 (=0 reverts)
    _nh_start = _t_nh.time()
    if _caps_on:
        # COLD-SAFE per-tactic slice (was a fixed 30s — BELOW the ~90s cold Mathlib reload, so on a cold page
        # cache EVERY tactic's compile timed out, incl. the first `rfl`, and native_hammer read DEAD on a
        # trivial it can close: the recurring cold-false-fail, here at the cascade level). The self-measured
        # floor lifts it to the box's baseline; a WARM tactic still finishes in ~5-30s (the floor is a budget
        # ceiling, not a forced wait); the cumulative deadline below still bounds the TOTAL cascade time.
        per_tactic_timeout = cold_safe_timeout(30, lean_root)
    transcript = []
    _clipped = False   # a cap-clipped cascade is NOT memoized (retry under a bigger budget may differ)
    for tactic in _NATIVE_HAMMER_TACTICS:
        if _caps_on:
            _rem = timeout_s - (_t_nh.time() - _nh_start)
            if _rem <= 5:
                transcript.append(f"[native_hammer] cap deadline {timeout_s}s reached — cascade stopped")
                _clipped = True
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
    if _dedup_on and not _clipped:
        _NATIVE_CASCADE_FAILED_MEMO[_memo_key] = transcript[-1] if transcript else "all tactics failed"
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
)  # (`validate_against_contract` / `verify_matched_negative_control` removed 2026-06-23 — dead siblings)

# Phase-timing seam (cycle/lead-time observability) — `with _phase_timer("govern.mnc", target=name): ...` emits a
# per-phase duration to the SHARED telemetry ledger (common.telemetry, read by factory_intelligence). Defensive
# import + nullcontext fallback so telemetry can never break the solver if the module is unavailable.
try:  # noqa: E402
    from ztare.leanmill.phase_timing import phase_timer as _phase_timer
except Exception:  # noqa: BLE001
    import contextlib as _ctxlib_pt

    def _phase_timer(*_a, **_k):  # type: ignore
        return _ctxlib_pt.nullcontext()
# Layer seam (task #42): Layer 2 (deterministic, free) is split from Layers 3-4
# (LLM, expensive) so a caller can run the free layer first and only escalate to
# the expensive LLM provers if a gate (the Agentic Circuit Breaker, F108/task #74)
# allows. solve() passes gate=None by default → behavior-preserving.
from ztare.leanmill.solver.deterministic import run_deterministic_layer  # noqa: E402
from ztare.leanmill.solver.llm_provers import run_llm_layers  # noqa: E402
from ztare.gates.lean_compile_primitives import run_lake_subprocess, _is_compile_ok  # noqa: E402
from ztare.leanmill.contracts import ProofTarget, primary_result  # noqa: E402 — typed-contract migration (#49)


def _source_cue_check(row: dict) -> dict:
    """Thin delegate to ztare.leanmill.solver.contract.source_cue_check."""
    return _canonical_source_cue_check(row)


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

    THREE-VALUED by design (2026-06-18 RCA — the mathd_algebra_302 false-`rejected_negative_control`):
    a control that cannot DECIDE must ABSTAIN (return True = no-reject), never fire. Two hard truths fix
    the old "compiles bare ⇒ leakage" rule:
      • This function had a latent `NameError: re not defined` (no local `import re`) → it CRASHED on
        every call and fail-opened — a silent dead instrument (the "bare-except hides a missing import"
        class). Reviving it NAIVELY would resurrect the category error below, so both are fixed together.
      • Without the SOURCE PRELUDE, "the proof compiles under bare Mathlib" is INDISTINGUISHABLE from a
        valid pure-Mathlib proof (a miniF2F goal like `(I/2)^2 = -(1/4)` legitimately compiles bare — that
        is NOT leakage). So this function can only ever return PASS (proof NEEDS the prelude → genuine) or
        INCONCLUSIVE (proof compiles bare ⇒ cannot tell leak from valid). It must NEVER return a leakage
        REJECT on its own — the AUTHORITATIVE kernel (`run_anti_laundering_kernel`, which DOES receive the
        original source) is the real leakage organ and correctly passes pure-Mathlib goals."""
    if not target_name or not proof_text.strip():
        return True, "inconclusive: missing target or proof"
    g = (goal_type or "").strip()
    if not g or g == target_name:   # no real type (bare name fallback) → can't build a valid attempt
        return True, "inconclusive: no goal_type (cannot build a well-formed stripped attempt)"
    if ":" not in g:                 # a bare type with no binders/colon → prepend the type colon
        g = ": " + g
    # CANONICAL splice (no hand-rolled `by` handling — RCA 2026-06-18): `attach_proof` is `by`-token-aware
    # and never doubles `by`, so a multiline `by\n` body can't silently sorry.
    from ztare.leanmill.lean_source import attach_proof as _attach_proof
    import re  # LOCAL import — solver_core uses function-local `import re` throughout (no module-level re);
              # used below for the unknown-identifier check.
    _head = f"theorem {target_name}_stripped_attempt {g} :="
    src = (
        "import Mathlib\n\n"
        "-- matched negative control: state the goal under bare Mathlib (no prelude) + the candidate\n"
        "-- body. If THIS does NOT compile, the proof NEEDS the prelude → genuine (PASS).\n"
        + _attach_proof(_head, proof_text)
    )
    # WARM MNC (kills the cold-`lake env lean` antipattern on the governance critical path — ~0.1s vs ~60-90s):
    # elaborate the bare-Mathlib probe against the FROZEN BASE env (`env=None` ⇒ Mathlib only, NO campaign
    # prelude — which is the MNC's whole point). SOUND/PARITY: base-Mathlib REPL elaboration is byte-equivalent
    # to a cold `lake env lean` over the SAME prelude-free probe (no prelude can leak in via env=None), and
    # `reject_sorry=False` matches the cold verdict (`sorry` is a warning, not `error:`). The unknown-identifier
    # and compiled-bare branches mirror the cold logic exactly. `None` ⇒ REPL unusable (flag off / toolchain
    # mismatch / dead) ⇒ fall through to the authoritative cold compile below (byte-parity when warm is off).
    try:
        from ztare.formal.repl_compile import compile_probe_via_repl as _warm_negctrl
        _rr = _warm_negctrl(src, lean_root, timeout_s, reject_sorry=False, env=None)
    except Exception:  # noqa: BLE001 — warm is an optimization; never let it break the negative control
        _rr = None
    if _rr is not None:
        _ok, _diag = _rr
        if re.search(r"unknown (identifier|constant|declaration)", _diag or ""):
            return True, "inconclusive: goal needs prelude defs (unknown identifier under bare Mathlib)"
        if _ok:
            return True, ("inconclusive: proof compiles under bare Mathlib — pure-Mathlib goal vs leak "
                          "is undecidable without the source prelude; deferred to the authoritative kernel")
        return True, "pass: proof needs the prelude (does not compile under bare Mathlib)"
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
            if stripped_compiled:
                # ABSTAIN: compiles bare ⇒ pure-Mathlib goal (or genuine leak) — INDISTINGUISHABLE here
                # without the source prelude. The authoritative kernel makes this call with the source.
                return True, ("inconclusive: proof compiles under bare Mathlib — pure-Mathlib goal vs leak "
                              "is undecidable without the source prelude; deferred to the authoritative kernel")
            # Proof did NOT compile bare (and not an unknown-id) ⇒ it genuinely NEEDS the prelude → PASS.
            return True, "pass: proof needs the prelude (does not compile under bare Mathlib)"
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
    closure_source: "str | None" = None,
    posed_source: "str | None" = None,
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
        with _phase_timer("govern.mnc", target=target_name):
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
    # Build the closure source ONCE (the SAME _src feeds both the anti-laundering kernel below AND the axiom audit).
    # Canonical proof-splice (NO hand-rolled `head + body` — RCA 2026-06-18: the mathd_algebra_302 drop was a
    # local splice that doubled `by` for a `by\n` body → silent `sorry`). `lean_source.attach_proof` is the
    # ONE binder/`by`-token-aware splicer; both this `_src` and `swap_sorry` route through it.
    from ztare.leanmill.lean_source import attach_proof as _attach_proof
    # `closure_source` (when supplied) is the COMPLETE proof-carrying source to govern verbatim — used by the
    # pre-verified-champion path, which must audit the EXACT mode-agnostic `swap_sorry(source, champion)` artifact
    # the proposer verified (a TERM-mode champion that swap_sorry splices after `:=` is mangled by the layered
    # `attach_proof(enriched_goal-ending-`:= by`, …)` forcing — the two-verify-worlds split that left the pool's
    # champion unratifiable). Default None ⇒ the layered reconstruction (byte-parity for every existing caller).
    _src = closure_source if (closure_source and closure_source.strip()) else _attach_proof(enriched_goal or "", proof_text or "")
    if not _src.lstrip().startswith("import"):
        _src = "import Mathlib\n\n" + _src

    kernel_passed = True
    if kernel_compile_ok and os.environ.get("ZTARE_KERNEL_AUTHORITATIVE", "1") != "0":
        try:
            import json as _json
            from ztare.gates.lean_proof_gate import run_anti_laundering_kernel as _kernel
            # Full Cage routing (GP-086 Phase 6, ZTARE_LEANMILL_CAGE_ROUTING=1; default-OFF). When on, the
            # anti-laundering verdict is dispatched through the ONE Cage orchestrator (`leanmill_cage`);
            # behavior-IDENTICAL by construction (the routed gate IS run_anti_laundering_kernel — regression-
            # checked), so the flip is reversible. Off ⇒ the direct kernel call (byte-parity).
            # ANTI-LAUNDERING BASELINE (RCA 2026-06-23, theory-first strong-Topkis ratify): the gate's
            # `original_source` is the POSED baseline the probe (`_src`) is diffed against (statement-integrity
            # def-alteration + canonical_reelaboration hijack-strip). `enriched_goal` is the LLM context, which
            # `_build_solver_context` TRUNCATES to the last `_MAX_CONTEXT_CHARS` — so for a theory-first target
            # whose statement uses defs living >12k chars before it, those defs are ABSENT from `enriched_goal`
            # but PRESENT in the full `closure_source` probe → canonical_reelaboration strips them as "added
            # shadow defs" → FALSE `context_hijack_confirmed` (it stripped the substrate's OWN `def
            # ParametricArgmaxNonempty/StrongSetMonotone/ParametricArgmaxSet`). The baseline MUST be the
            # COMPLETE posed source. `posed_source` (the row's verbatim sorried file) is that; fall back to
            # `enriched_goal` for callers that don't pass it (byte-parity — their probe is ALSO built from
            # `enriched_goal`, so probe and baseline stay consistent and no false strip occurs).
            _orig_for_gate = posed_source if (posed_source and posed_source.strip()) else enriched_goal
            if os.environ.get("ZTARE_LEANMILL_CAGE_ROUTING") == "1":
                from ztare.leanmill.solver.leanmill_cage import govern_via_cage as _gvc
                _k = _gvc(_src, lean_root / "_kernel.lean", lean_root,
                          original_source=_orig_for_gate, target_name=target_name)
            else:
                _k = _kernel(_src, lean_root / "_kernel.lean", lean_root,
                             original_source=_orig_for_gate, target_name=target_name)
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

    # AXIOM AUDIT (soundness #84 F1/F2, 2026-06-11): the cascade + composite closure paths credited closures
    # WITHOUT `#print axioms` (only the warm leaf ran it), so a `native_decide` proof (Lean.ofReduceBool) compiled
    # clean + passed — a false-closure vector in the gate. Now EVERY closure path is axiom-gated. Fail-CLOSED only
    # on a CONFIRMED banned axiom; fail-OPEN on a tooling error (the kernel's fail-open-on-crash philosophy). Runs
    # ONLY on a candidate closure (kernel_compile_ok) ⇒ one bounded extra compile, not per-attempt.
    axiom_confirmed_bad = False
    axiom_tier = "unaudited"   # #104 TIER: kernel_pure | true_modulo_banned_axioms | inconclusive | unaudited
    if kernel_compile_ok and target_name:
        try:
            from ztare.gates.lean_compile_primitives import audit_axioms_subset as _aax, AXIOM_ALLOWLIST as _AXAL
            from ztare.common.timeouts import timeout_s as _budget
            # WARM-FIRST (2026-06-25): for a campaign closure, audit the proof against the cached theory env (only
            # the new decl elaborates) instead of re-elaborating the whole inlined theory cold per closure.
            _ca = _campaign_aware_axioms(enriched_goal or "", proof_text or "", target_name, lean_root, _budget("axiom_audit"))
            if _ca is not None:
                _clean, axiom_confirmed_bad, _axs = _ca
            else:
                _clean, axiom_confirmed_bad, _axs = _aax(
                    _src, target_name, lean_root / "_axiom_audit.lean", lean_root, timeout_s=_budget("axiom_audit"))
            receipts["axiom_allowlist_receipt"] = {
                "passed": (True if _clean else (False if axiom_confirmed_bad else None)),
                "axioms": _axs,
                "tail": ("clean " + str(_axs) if _clean
                         else (f"BAD_AXIOMS {sorted(set(_axs) - _AXAL)}" if axiom_confirmed_bad
                               else "inconclusive (no #print axioms line) — fail-open")),
            }
            # #104 TIER the outcome: a proof that COMPILES but carries a BANNED axiom (native_decide →
            # Lean.ofReduceBool) is NOT a clean closure (credit_ready stays False — the cert must be kernel-pure),
            # but the statement is TRUE BY COMPUTATION — genuine progress under a weaker trust model, NOT a
            # false/honest-miss. Recording it distinctly (vs silently discarding) lets a downstream pass target a
            # kernel-pure replacement and keeps the telemetry honest.
            axiom_tier = ("kernel_pure" if _clean
                          else ("true_modulo_banned_axioms" if axiom_confirmed_bad else "inconclusive"))
        except Exception as _e:  # noqa: BLE001 — tooling error ⇒ fail-OPEN (must not block a valid closure)
            receipts["axiom_allowlist_receipt"] = {"passed": None, "tail": f"axiom audit error (fail-open): {repr(_e)[:100]}"}

    all_required_pass = all(
        bool(receipts[r["name"]]["passed"]) is True
        for r in contract.get("required_receipts", [])
        if r.get("required") and receipts[r["name"]]["passed"] is not None
    )
    credit_ready = (
        kernel_compile_ok
        and receipts["matched_negative_control_receipt"]["passed"] is True
        and kernel_passed  # AUTHORITATIVE: a confirmed anti-laundering organ blocks the closure at solve-time
        and not axiom_confirmed_bad  # SOUNDNESS #84 F1: a CONFIRMED banned axiom (e.g. native_decide) blocks closure
    )
    return {
        "contract_schema": contract.get("schema"),
        "receipts": receipts,
        "credit_ready_at_solver_layer": bool(credit_ready),
        "required_receipts_all_passed_at_solver_layer": bool(all_required_pass),
        "axiom_tier": axiom_tier,   # #104: kernel_pure | true_modulo_banned_axioms (native_decide) | inconclusive
        "downstream_required": "leanmill_proof_audit (axiom_allowlist + L3) before factory credit",
    }


def _reject_reason_from_validation(validation: "dict | None") -> "tuple[str, str]":
    """Derive the SPECIFIC credit-block outcome from the solver-lane receipts — returns (outcome, detail).

    RCA 2026-06-18 (the mathd_algebra_302 mislabel): the dispatch path hardcoded `rejected_negative_control`
    as the catch-all for ANY "compiled-but-not-credited" proof (`"rejected_negative_control" if compile_ok
    and proof_text.strip() else outcome`). That ONE label conflated FOUR distinct outcomes —
      • a CONFIRMED banned axiom (`native_decide`/`Lean.ofReduceBool`)  → `rejected_banned_axiom`
      • a CONFIRMED anti-laundering organ (the authoritative kernel)     → `rejected_anti_laundering`
      • an actual matched-negative-control leakage flag                  → `rejected_mnc_leakage`
      • a KERNEL-VALID closure DROPPED by a control-flow path            → `uncredited_validated_closure_dropped`
    which (a) made every rejection un-diagnosable (this whole RCA was spent reverse-engineering ONE label)
    and (b) POISONED move-calibration — all four were scored as a "caught cheat" in `_WRONG_TARGET`, driving
    real provers' priors down for closures they actually PRODUCED. The label must be DERIVED from the receipt
    that actually failed, never assumed. The DROPPED case is its own loud signal: the kernel said PASS but the
    closure was not credited ⇒ a flow bug, NOT a cheat (so it must never feed the cheat bucket)."""
    if not validation:
        return "uncredited_no_validation", "no contract validation present (proof never validated)"
    rc = validation.get("receipts") or {}
    def _rec(name: str) -> dict:
        return rc.get(name) or {}
    if _rec("kernel_compile_receipt").get("passed") is False:
        return "rejected_compile", str(_rec("kernel_compile_receipt").get("tail", ""))[:160]
    if _rec("axiom_allowlist_receipt").get("passed") is False:
        return "rejected_banned_axiom", str(_rec("axiom_allowlist_receipt").get("tail", ""))[:160]
    if _rec("governance_kernel_receipt").get("passed") is False:
        conf = _rec("governance_kernel_receipt").get("confirmed") or []
        return "rejected_anti_laundering", f"confirmed organ(s): {conf}"
    if _rec("matched_negative_control_receipt").get("passed") is False:
        return "rejected_mnc_leakage", str(_rec("matched_negative_control_receipt").get("tail", ""))[:160]
    # Every receipt PASSED but credit_ready was still False (or no receipt blocked) ⇒ a kernel-valid closure
    # was DROPPED by the dispatch control flow. Surface it LOUDLY and distinctly — never as leakage.
    return ("uncredited_validated_closure_dropped",
            "all solver-lane receipts passed but credit_ready=False — kernel-valid closure dropped by "
            "dispatch flow (a control-flow bug, NOT laundering)")


def _leaf_goal_from_source(body: str, target: str, base_goal: str) -> str:
    """The leaf's goal (the post-`:` conclusion `solve_leaf` splices into `theorem t : <goal>`), in `∀`-form
    so binders-BEFORE-the-colon work — the dag-search adhoc seam that left RUNG C / denef silently
    un-attackable when the legacy `theorem t : C` regex returned an empty goal. REUSES the CANONICAL Lean
    parsers — `lean_source.extract_signature` (target-aware `<binders> : <concl>` VERBATIM) +
    `conjecture._top_level_colon` (the depth-0 colon finder) — instead of a duplicate balanced-delimiter
    scan. Falls back to `base_goal`."""
    try:
        from ztare.leanmill import lean_source as _ls
        from ztare.leanmill.solver.conjecture import _top_level_colon
        sig = _ls.extract_signature(body, target)
        j = _top_level_colon(sig) if sig else -1
        if j < 0:
            return base_goal
        binders, concl = sig[:j].strip(), sig[j + 1:].strip()
        if not concl:
            return base_goal
        return f"∀ {binders}, {concl}" if binders else concl
    except Exception:  # noqa: BLE001 — best-effort; fall back rather than crash the solve
        return base_goal


# (run_tag, goal_sha) → prior FAILED warm attempts [{reason, gap}] this run. The v3 iatrogenic loop
# (2026-06-12): 9 warm dispatches × 400-1000s on recurring goals across nested solves/DAG nodes, each a
# BLIND fresh "prove X directly" — the agent's own honest-gap diagnosis from the prior attempt was dropped
# at this seam, so it re-derived the same gap at full budget. Per-node moves_tried can't see across nodes.
_WARM_GOAL_ATTEMPTS: "dict[tuple[str, str], list]" = {}


# KERNEL type-equality oracle — the ONE canonical copy now lives in `statement_integrity.kernel_type_equiv_fn`
# (2026-06-21 consolidation). It USED to be defined here AND byte-identically in `lean_proof_gate` — the
# recurring "missed sibling" bug class (two hand-synced copies; fix one, the other rots — that is literally how
# the campaign's faithful ∀-fronted iff got `target_signature_altered`). `statement_integrity.check` now builds
# it DEFAULT-ON when handed a `lean_root`, so the solve-time call below just passes `lean_root=` and no longer
# constructs the oracle by hand. These thin re-export aliases preserve the old names for any external caller.
def _target_type_equiv_fn(target_name: str, lean_root: Path):
    """Back-compat shim → the canonical `statement_integrity.kernel_type_equiv_fn` (see the note above)."""
    from ztare.leanmill.solver.statement_integrity import kernel_type_equiv_fn as _k
    return _k(target_name, lean_root)


_campaign_type_equiv_fn = _target_type_equiv_fn


def _campaign_aware_proof_compiles(target_source: str, proof_text: str, lean_root: Path, timeout_s: int) -> bool:
    """Does `proof_text` close the target decl in `target_source`? THE shared campaign-aware verify seam
    (2026-06-20): when a campaign substrate is registered it routes through the theory ENV (defs + `namespace`
    + fresh-name + #print-axioms audit) — the SAME path the warm leaf uses — else a standalone `_compile_probe`.
    A direct `_compile_probe` is campaign-BLIND (no env/namespace), so a probe whose statement references campaign
    theory defs fails `unknown identifier` regardless of proof quality (the pool-verify bug). Callers that verify
    a proof of a (possibly namespaced) campaign target MUST use this, not `_compile_probe`. Canonical lean_source
    splices (extract_signature + attach_proof), no regex."""
    from ztare.leanmill.lean_source import swap_sorry, theorem_names, extract_signature, attach_proof
    probe = swap_sorry(target_source, proof_text)
    if not probe or "sorry" in probe:
        return False
    try:
        from ztare.formal.repl_compile import get_campaign_substrate, campaign_file_env, warm_verify_campaign
        _sub = get_campaign_substrate()
        if _sub:
            _env = campaign_file_env(_sub, lean_root)
            _names = theorem_names(target_source)
            if _env is not None and _names:
                _name = _names[-1]
                _sig = extract_signature(target_source, _name)
                if _sig.strip():
                    _fresh = f"{_name}_zwv"
                    _fresh_probe = attach_proof(f"theorem {_fresh} {_sig} :=", proof_text)
                    _cw = warm_verify_campaign(_fresh_probe, _fresh, lean_root, timeout_s, env=_env)
                    if _cw is not None:
                        return bool(_cw[0])
    except Exception:  # noqa: BLE001 — never let the campaign path break verify; fall through to standalone
        pass
    from ztare.gates.v33_preflight_risk_detector import _compile_probe as _cp
    return bool(_cp(probe, lean_root, "CampaignVerify", min(int(timeout_s), 180)) is True)


def _campaign_aware_axioms(target_source: str, proof_text: str, target_name: str, lean_root: Path, timeout_s: int):
    """Campaign-aware `#print axioms` for a fresh closure (2026-06-25 verify-starvation TAIL). When a substrate
    is registered, audit the proof by checking a FRESH-named copy of the target decl AGAINST the cached theory
    ENV (only the new decl elaborates) — the SAME warm path `_campaign_aware_proof_compiles` uses — instead of
    re-elaborating the whole inlined theory against base, which TIMES OUT on a heavy theory and falls to cold
    `lake env lean` PER CLOSURE (the ~74s/closure tax that made the run look stuck). Returns
    (clean, confirmed_bad, axs) like `audit_axioms_subset`, or None ⇒ caller uses the cold audit (authoritative).
    Reuses the validated `warm_verify_campaign` (axioms ⊆ allowlist + no sorryAx) — NO new soundness surface;
    a `sorryAx`/banned-axiom REJECT maps to fail-CLOSED, a mere compile/inconclusive maps to None (cold decides)."""
    try:
        from ztare.formal.repl_compile import get_campaign_substrate, campaign_file_env, warm_verify_campaign
        from ztare.leanmill.lean_source import theorem_names, extract_signature, attach_proof
        sub = get_campaign_substrate()
        if not sub or not (proof_text or "").strip() or "sorry" in (proof_text or ""):
            return None
        env = campaign_file_env(sub, lean_root)
        if env is None:
            return None
        names = theorem_names(target_source or "") or ([target_name] if target_name else [])
        if not names:
            return None
        name = target_name if target_name in names else names[-1]
        sig = extract_signature(target_source or "", name)
        if not sig.strip():
            return None
        probe = attach_proof(f"theorem {name}_zax {sig} :=", proof_text)
        cw = warm_verify_campaign(probe, f"{name}_zax", lean_root, timeout_s, env=env)
        if cw is None:
            return None
        ok, diag = cw
        if ok:
            return (True, False, ["warm:clean"])               # axioms ⊆ allowlist, no sorryAx
        if "AXIOM AUDIT REJECT" in (diag or ""):
            return (False, True, ["warm:" + (diag or "")[:80]])  # sorryAx / banned axiom ⇒ fail-CLOSED
        return None                                            # compile/inconclusive ⇒ cold path is authoritative
    except Exception:  # noqa: BLE001 — never break the audit; the cold path remains authoritative
        return None


def _agentic_leaf_warm_solve(row: dict, lean_root: Path, timeout_s: int) -> tuple[bool, str, str]:
    """Flag-gated (ZTARE_AGENTIC_LEAF=1) warm solve via the validated `agentic_leaf` primitive.
    Calibration-first (provider + substrate liveness ⇒ a dead instrument returns INADMISSIBLE,
    never a fake negative) + best-of-N across codex+claude + independent axiom-allowlist gate.
    Returns the worker's (compile_ok, proof_text, transcript_tail) contract. §6n review pending."""
    import re as _re
    from ztare.leanmill.solver.agentic_leaf import leaf_provider_order, probe_dir, solve_robust
    target = row.get("target_theorem_name") or ""
    base_goal = (row.get("goal") or "").strip()
    # WARM-GOAL CAP + RETRY FEEDBACK (v3 RCA): bounded funding of the EXPENSIVE move per identical goal
    # per run — budget discipline at the boundary (a deterministic trust primitive, like timeouts), the
    # agent keeps every strategic choice. Attempt 2 carries the agent's OWN prior diagnosis (no blind
    # retry); at the cap the dispatch refuses ⇒ the ladder falls through to conjecture/decompose/defer.
    # INADMISSIBLE results never count (a dead provider is not a real negative). =0 disables.
    import hashlib as _hl_wg
    _cap = int(os.environ.get("ZTARE_LEANMILL_WARM_GOAL_CAP", "2") or 0)
    _wg_key = (os.environ.get("ZTARE_SOLVER_RUN_TAG", ""),
               _hl_wg.sha256(" ".join(base_goal.split()).encode()).hexdigest())
    _prior = _WARM_GOAL_ATTEMPTS.get(_wg_key, [])
    if _cap and len(_prior) >= _cap:
        _lg = next((p["gap"] for p in reversed(_prior) if p.get("gap")), "")
        return False, "", (f"warm_goal_cap: {len(_prior)} prior warm attempts on this exact goal this run "
                           f"(last: {_prior[-1].get('reason', '?')}"
                           + (f"; agent's own gap: {_lg[:200]}" if _lg else "")
                           + ") — strategy change required (decompose/conjecture/defer)")
    try:  # harness robustness: a missing/unreadable source (e.g. a scratch file cleaned by a concurrent
        # shard) must degrade to a clean MISS, not crash the whole solve as an uncaught FileNotFoundError
        # (which the A/B recorded as exc:FileNotFoundError on 3/24 targets, contaminating the result).
        # Route through ProofTarget.source_path() (2026-06-13 audit A5): a MISSING key is a clean miss,
        # not a KeyError (`row["source_file"]` subscript crashed instead of degrading), and the sorried_file
        # fallback is encoded once in the contract.
        _spath = ProofTarget.from_row(row).source_path()
        if not _spath:
            return False, "", "source_file_unreadable: no source/sorried path on the row"
        _raw = Path(_spath).read_text(encoding="utf-8", errors="replace")
    except OSError as _exc:
        return False, "", f"source_file_unreadable: {_exc!r}"[:200]
    body = "\n".join(l for l in _raw.splitlines() if not l.strip().startswith("import "))
    mt = _re.search(rf"(?m)^\s*(?:theorem|lemma)\s+{_re.escape(target)}\b", body)
    defs = body[:mt.start()].rstrip() if mt else body
    goal = _leaf_goal_from_source(body, target, base_goal)
    # GAP-REFINE: prepend the (Lean-comment) refine context — the leaf's own unsolved goals + prior
    # attempt + the premise shelf it otherwise ignores — so the strongest move stops running starved.
    # Comments only ⇒ inert at compile; the agent reads them as guidance. Empty unless the caller set it.
    _rc = (row.get("_refine_context") or "").strip()
    if _rc:
        defs = _rc + "\n\n" + defs
    # CEGIS no-good INFORMING (M2). DEFAULT-ON (disable via ZTARE_LEANMILL_NOGOOD=0): sound by
    # construction — it only INFORMS (comment-inert at compile; a no-op on a fresh store), can NEVER
    # prune/suppress a closable path, and adds no move-budget cost, so default-ON only ever helps.
    # Prepend the LEARNED-CONTEXT block so the leaf's OWN orchestration is informed by what compounded:
    # the CONFIRMED prior-refutation memo (so it never re-explores a dead region; gated by ZTARE_LEANMILL_NOGOOD,
    # default-on) PLUS — flag-on ZTARE_LEANMILL_LEARNED_CONTEXT — the apparatus's kernel-arbitrated move
    # track-record (the calibration the scheduler used but the agent was blind to). Default config is
    # byte-identical to the prior no-good-only injection. Best-effort (a store error is silent, never fails).
    try:
        from ztare.leanmill.solver import learned_context as _lc
        _ngb = _lc.render(goal, no_good_path=OUT_DIR / "solver_lane_no_good_store.jsonl", db_path=ATTEMPTS_DB)
        if _ngb:
            defs = _ngb + "\n\n" + defs
    except Exception:  # noqa: BLE001 — informing is best-effort; never fail the solve
        pass
    # INSTANCES-FIRST GATE (#124, mathematician leg; default-on, =0 reverts). Before funding a dispatch
    # ≥ half the agent_dispatch budget on a computable-shaped ∀-goal, CONFIRM concrete instances by
    # SymPy — `witness_transport.looks_false`'s POSITIVE dual (same parse/translation/sandbox).
    # ADVISORY at the agency line (Goldilocks): NEVER blocks the dispatch — confirmed instances ride in
    # as cheap confidence, a counterexample as a LIKELY-FALSE warning (the agent's pivot stays its own;
    # the kernel-proved ¬G stays the only refutation verdict). Each outcome is conjecture-book evidence.
    if os.environ.get("ZTARE_LEANMILL_INSTANCES_FIRST", "1") != "0":
        try:
            from ztare.common.timeouts import timeout_s as _ts_if
            if timeout_s >= _ts_if("agent_dispatch") / 2:
                from ztare.leanmill.solver.witness_transport import instance_evidence as _iev
                _ev = _iev(goal)
                if _ev:
                    row["_instance_evidence"] = _ev
                    if _ev.get("refuted"):
                        _asg = ", ".join(f"{v}={x}" for v, x in zip(_ev["vars"], _ev["refuted"]))
                        defs = ("-- INSTANCES-FIRST (SymPy, advisory): a CONCRETE COUNTEREXAMPLE evaluates the\n"
                                f"-- statement FALSE at {_asg} — the statement is LIKELY FALSE as written.\n"
                                "-- Do NOT burn the budget proving it. Verify the counterexample; if it holds, use\n"
                                "-- the `-- STATEMENT-FALSE:` marker with the corrected statement.\n\n") + defs
                    elif len(_ev.get("confirmed") or []) >= 3:
                        _pts = "; ".join(", ".join(f"{v}={x}" for v, x in zip(_ev["vars"], c))
                                         for c in _ev["confirmed"][:5])
                        defs = ("-- INSTANCES-FIRST (SymPy, advisory): the statement HOLDS at "
                                f"{len(_ev['confirmed'])} concrete instances ({_pts}) — no cheap\n"
                                "-- falsification found; evidence ≠ proof, but the general attack is worth funding.\n\n") + defs
                    # conjecture-book evidence (best-effort; stdlib imports LOCAL — the bare-except rule)
                    try:
                        from datetime import datetime as _dt_cb, timezone as _tz_cb
                        from ztare.leanmill import conjecture_book as _cbk
                        _kind = "counterexample_found" if _ev.get("refuted") else (
                            "instance_confirmed" if len(_ev.get("confirmed") or []) >= 3 else "")
                        if _kind:
                            _cbk.record_event(
                                goal, _kind,
                                evidence=(f"refuted at {_ev['refuted']}" if _ev.get("refuted")
                                          else f"{len(_ev['confirmed'])} instances confirmed: {_ev['confirmed'][:5]}"),
                                run_tag=os.environ.get("ZTARE_SOLVER_RUN_TAG", ""), repo_root=REPO,
                                ts=_dt_cb.now(_tz_cb.utc).isoformat())
                    except Exception:  # noqa: BLE001 — the ledger is observability, never blocks the solve
                        pass
        except Exception:  # noqa: BLE001 — the gate is advisory; a SymPy/parse failure must not fail the solve
            pass
    # CONJECTURE-BOOK CONTEXT (#124, read-side — the book is CONSUMED, not just written): accumulated
    # evidence on THIS statement (instances confirmed across runs, proven special cases, any recorded
    # counterexample, pool credence) rides into the prompt. Comment-inert, inform-never-block.
    try:
        from ztare.leanmill import conjecture_book as _cbk_r
        _cb_blk = _cbk_r.render_block(goal, REPO)
        if _cb_blk:
            defs = _cb_blk + "\n\n" + defs
    except Exception:  # noqa: BLE001 — context is best-effort; never fail the solve
        pass
    # RETRY FEEDBACK (comment-inert, same mechanism as no_good/learned_context): the agent's OWN prior
    # failure(s) on THIS goal this run — the lam_litt transcript showed gold-standard gap localization
    # that the next blind dispatch then re-derived at full budget. NOT prescriptive: it relays the
    # agent's own words back, plus the one harness fact it cannot see (a sorried file scores as failure).
    if _cap and _prior:
        _fb_lines = ["-- PRIOR WARM ATTEMPT(S) on THIS exact goal THIS RUN (your own):"]
        for _p in _prior[-2:]:
            _fb_lines.append(f"--   outcome: {_p.get('reason', '?')}"
                             + (f" | your GAP diagnosis: {_p.get('gap', '')[:300]}" if _p.get("gap") else ""))
        _fb_lines.append("-- A sorried probe scores as FAILURE. Either produce a COMPLETE proof this time, "
                         "or localize the gap precisely and STOP EARLY — do not re-derive the same gap.")
        # FIX-MEMORY READ (#125): the prior error is in hand HERE — surface what kernel-verifiably
        # repaired this error signature before (comment-inert, inform-never-block, like no_good).
        if os.environ.get("ZTARE_LEANMILL_FIX_MEMORY", "1") != "0":
            try:
                from ztare.leanmill.solver import fix_memory as _fxm
                _fm_blk = _fxm.prompt_block(OUT_DIR / _fxm.FIX_LEDGER_NAME,
                                            (_prior[-1].get("reason", "") + "\n" + _prior[-1].get("gap", "")))
                if _fm_blk:
                    _fb_lines.append(_fm_blk)
            except Exception:  # noqa: BLE001 — memory is advisory; never fail the solve
                pass
        defs = "\n".join(_fb_lines) + "\n\n" + defs
    # FLAG-TIME statement-false short-circuit (2026-06-23 iso_lemma1 loop): hand the best-of-N a CACHED kernel
    # ¬goal verifier. When an agent flags STATEMENT-FALSE, the leaf/best-of-N verify ¬goal ONCE and stop —
    # instead of burning the whole decompose + portfolio (claude ~545s × N) before solve_adhoc's END epilogue
    # ever runs the same verify. Same kernel check + same gate as the epilogue; soundness unchanged (the
    # downstream governance re-confirms ¬goal before any re-plan — this only stops wasted dispatches).
    _sf_cache: dict = {}
    def _sf_verifier() -> bool:
        if os.environ.get("ZTARE_LEANMILL_VERIFY_STATEMENT_FALSE", "1") == "0":
            return False
        if "v" not in _sf_cache:
            _sf_cache["v"] = False
            try:
                from ztare.leanmill.solver.conjecture import verify_statement_false_claim
                _src = Path(row["source_file"]).read_text(encoding="utf-8", errors="replace")
                _conf, _, _ = verify_statement_false_claim(target, _src, goal, lean_root, 180)
                _sf_cache["v"] = bool(_conf)
            except Exception:  # noqa: BLE001 — a verifier failure ⇒ no short-circuit (normal best-of-N path)
                _sf_cache["v"] = False
        return _sf_cache["v"]
    r = solve_robust(goal, defs=defs, project_dir=str(lean_root), repo=str(lean_root),
                     lake_bin="lake", providers=leaf_provider_order(), target=target,
                     timeout=timeout_s, decompose=True, statement_false_verifier=_sf_verifier)
    if r.inadmissible:
        return False, "", f"INADMISSIBLE (uncalibrated instrument, not a real negative): {r.reason}"

    def _record_prompt_evo(_closed: bool) -> None:
        # PROMPT-EVOLUTION substrate (#124): stamp this ADMISSIBLE outcome with the warm-leaf prompt
        # TEMPLATE fingerprint, so a future template change can be A/B'd through SequentialABGate. Pure
        # telemetry (default-on, =0 disables), best-effort — never affects the solve.
        try:
            from ztare.leanmill.solver import prompt_evolution as _pe
            from ztare.leanmill.solver.prompts import LEAF_SOLVE_COMMON as _tmpl
            from datetime import datetime as _dt_pe, timezone as _tz_pe
            _pe.record_dispatch("warm_leaf", _tmpl, _wg_key[1], _closed,
                                run_tag=os.environ.get("ZTARE_SOLVER_RUN_TAG", ""),
                                ts=_dt_pe.now(_tz_pe.utc).isoformat())
        except Exception:  # noqa: BLE001 — telemetry; never break the solve
            pass

    if not r.closed:
        _record_prompt_evo(False)
        if _cap:   # record the REAL negative (inadmissible never reaches here) for the cap + feedback
            _WARM_GOAL_ATTEMPTS.setdefault(_wg_key, []).append(
                {"reason": (r.reason or "")[:160], "gap": (r.gap or "")[:600]})
        # GAP PROPAGATION (v3 RCA): r.gap is the agent's honest-gap diagnosis — the most useful signal a
        # non-closure produces. It was DROPPED here, leaving only "uses_sorry" in the DB while the named
        # missing lemma vanished. Carry it in the tail (→ attempts-DB notes / failure triage / refine ctx).
        # #128 (mathematician×alien reconciliation — the MISSING producer): the agent's own `-- GAP:` is
        # the richest source of named OPEN conjectures, yet only the instances-first gate fed the
        # conjecture book. Register the GAP as a conjecture so cross-run evidence (instances confirmed,
        # special cases proven) accumulates on it. Best-effort/advisory (stdlib imported LOCALLY per the
        # bare-except rule); never blocks the solve, no governance surface.
        if r.gap and len(str(r.gap).strip()) >= 12:
            try:
                from ztare.leanmill import conjecture_book as _cbk_gap
                _cbk_gap.register(str(r.gap), residual_class="agent_gap",
                                  campaign=os.environ.get("ZTARE_SOLVER_RUN_TAG", ""), repo_root=REPO)
                # CLOSE the credence producer→consumer loop (#142): the conjecture-book CONSUMER (`render_block`,
                # ~L1418) already surfaces "pool credence", but the PRODUCER `route_credence_via_pool` was never
                # invoked — so the credence never populated even when a campaign opted in. Route this OPEN gap
                # through the forecast POOL here. Internally OPT-IN + default-OFF (ZTARE_LEANMILL_CONJECTURE_POOL):
                # a no-op returning None at ZERO token cost unless a campaign deliberately flips it; best-effort.
                from datetime import datetime as _dt_cr, timezone as _tz_cr
                _cbk_gap.route_credence_via_pool(str(r.gap), repo_root=REPO,
                                                 ts=_dt_cr.now(_tz_cr.utc).isoformat())
            except Exception:  # noqa: BLE001 — the book is observability; a write must never break the solve
                pass
        return False, "", (f"agentic_leaf open: {r.reason}"
                           + (f" | GAP: {r.gap[:400]}" if r.gap else "")
                           + (f" | STATEMENT-FALSE: {r.statement_false[:200]}" if r.statement_false else ""))
    _best = r.calibration.get("best_of") or {}
    winner = _best.get("winner", "codex")
    _pdir = probe_dir(lean_root)   # readback MUST match solve_leaf's write dir
    # Use the EXACT winning probe the leaf recorded (2026-06-13 audit A1/B2 — no `_0` guess, no
    # lexically-mis-ordered glob). Fall back to `_0` only for an older leaf that didn't carry it.
    # CANONICAL name (anti-sibling, 2026-06-23): build the fallback through the SAME helper the writer uses, so
    # the reader can never look for `RobustProbe_<winner>_0` while the writer wrote `RobustProbe_<target>_<winner>_0`
    # (the winner_probe-drift bug that discarded a kernel-valid proof as 'probe unreadable').
    from ztare.leanmill.solver.agentic_leaf import robust_probe_name as _rpn, robust_probe_glob as _rpg
    _wp = _best.get("winner_probe") or _rpn(target, winner, 0)
    probe = _pdir / _wp
    if not probe.exists():
        # last resort (old leaf / cleaned dir): the highest NUMERIC attempt suffix, not lexical
        _cands = list(_pdir.glob(_rpg(target, winner)))
        if _cands:
            def _idx(p):
                try:
                    return int(p.stem.rsplit("_", 1)[-1])
                except ValueError:
                    return -1
            probe = max(_cands, key=_idx)
    proof = ""
    ptxt = ""
    if probe.exists():
        ptxt = probe.read_text(encoding="utf-8", errors="replace")
        # CANONICAL proof-body extraction (NO hand-rolled decl regex — `lean_source` exists for exactly this):
        # fence the named decl, then binder-safe split at the proof `:=`. Handles TERM proofs too (the old
        # `(by.*?)` regex silently missed them) and is never truncated by a `:=` inside a binder.
        from ztare.leanmill.lean_source import _decl_body as _ls_decl_body, split_at_proof as _ls_split_at_proof
        _proof_part = _ls_split_at_proof(_ls_decl_body(ptxt, target) or "")[1].lstrip()
        proof = (_proof_part[2:].lstrip() if _proof_part.startswith(":=") else _proof_part)
    # FAIL-CLOSED on an unverifiable closure (2026-06-13 audit): the warm path is THE move that trusts a
    # SELF-EDITED probe file, so the statement-integrity diff below is the ONLY thing standing between it and
    # statement-laundering. If the winning probe is unreadable we cannot run that diff — so we must NOT credit
    # the closure (the prior behaviour silently skipped integrity and returned True). Rare (a closed run
    # normally leaves its probe); loud when it happens.
    if not ptxt:
        return False, "", ("closure reported but the winning probe is unreadable — cannot verify "
                           "statement-integrity on the self-edited file (fail-closed, no closure)")
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
            # DEFAULT-ON kernel type-equality oracle: hand `check` the `lean_root` and it builds the ONE
            # canonical `kernel_type_equiv_fn` itself (no per-caller oracle to construct — see the shim note).
            _verdict = _si.check(_orig_src, ptxt, target, lean_root=lean_root)
        except Exception as _e:  # noqa: BLE001  — integrity tooling failure must not mint a closure
            return False, "", f"statement_integrity ERROR (fail-closed, no closure): {_e!r}"
        if _verdict.ok and _cap and _prior and os.environ.get("ZTARE_LEANMILL_FIX_MEMORY", "1") != "0":
            # FIX-MEMORY WRITE (#125): a RETRY succeeded where the prior attempt failed, and the success
            # is kernel-verified (solve_robust compile-verified probe + the integrity diff just passed) —
            # exactly the confirmed-repair contract. Record error→fix so the next recurrence is informed.
            try:
                from datetime import datetime as _dt_fm, timezone as _tz_fm
                from ztare.leanmill.solver import fix_memory as _fxm2
                _last = _prior[-1]
                _fxm2.record_fix(OUT_DIR / _fxm2.FIX_LEDGER_NAME,
                                 error_tail=(_last.get("reason", "") + "\n" + _last.get("gap", "")),
                                 fixed_by=f"warm_retry:{winner}",
                                 evidence=("retry with the prior-gap feedback closed it"
                                           + (f"; gap addressed: {_last.get('gap', '')[:200]}" if _last.get("gap") else "")),
                                 goal_head=goal[:120], run_tag=os.environ.get("ZTARE_SOLVER_RUN_TAG", ""),
                                 ts=_dt_fm.now(_tz_fm.utc).isoformat())
            except Exception:  # noqa: BLE001 — recording is best-effort; never block the closure
                pass
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
            _record_prompt_evo(False)   # a laundering catch is an admissible NON-close for the prompt A/B
            return False, "", ("statement_integrity FAILED (laundering blocked at solve time): "
                               + "; ".join(_verdict.violations)[:240])
    _record_prompt_evo(True)
    return True, proof, f"agentic_leaf closed by {winner} (rounds={r.rounds}, decomposed={r.decomposed})"


# NOTE: `_warm_agent_solve` was REMOVED 2026-06-23 — ONE leaf entry point. Its live path already delegated
# to `_agentic_leaf_warm_solve` (→ best-of-N `solve_robust` → `solve_leaf`); the only other branch was the
# dead-by-default legacy one-shot baseline (`ZTARE_AGENTIC_LEAF=0`). Callers now invoke
# `_agentic_leaf_warm_solve` directly, so there is no parallel leaf path and a fix lands in ONE place.


@dataclass
class CheckResult:
    """Substrate-neutral verdict of a proof-side Checker — the boxed (ok, diagnostics) the verify seam
    returns, plus `name` recording WHICH checker ratified (auditability across checker substrates)."""
    ok: bool
    diagnostics: str = ""
    name: str = ""


class LeanLakeChecker:
    """The LEAN BINDING of the proof-side verify seam: compile `import Mathlib\\n<goal>\\n  <proof>` via
    `lake env lean` and ratify with the `_is_compile_ok` kernel parser (sorry/admit/bare-error ⇒ not ok;
    the 2-row smoke 2026-05-30 caught the old check minting a FALSE `closed` on sorry). This is kernel-trust
    (the kernel says exit-0 + no errors), not text-trust (the LLM call ran). It is the DEFAULT proof
    checker; any object with the same `verify(...) -> CheckResult` + `.name` can stand in — a smoke checker
    in tests, or a non-Lean checker — which makes the proof side injectable the way the statement side
    (autoformalize's faithfulness_gate) already is. The Lean-specifics (lake invocation, _is_compile_ok
    parser, the Mathlib probe wrapper) live HERE, not smeared across the call sites."""
    name = "lean_lake"

    def verify(self, goal_text: str, proof_text: str, *, lean_root: Path, timeout_s: int,
               row_id: str = "probe") -> "CheckResult":
        goal = (goal_text or "").strip()
        body = _strip_proof_text(proof_text)
        if not goal or not body:
            return CheckResult(False, "missing goal or proof text", self.name)
        # provider text starting with `by` folds into the stub (which ends `:= by`); else append as-is.
        proof_block = body[3:].lstrip() if body.startswith("by ") else body
        if goal.endswith(":= by"):
            src = f"import Mathlib\n\n{goal}\n  {proof_block}\n"
        else:
            src = f"import Mathlib\n\n{goal}\n{body}\n"
        # CAMPAIGN WARM-ENV fast path (2026-06-14): when a campaign theory substrate is registered, verify the
        # proof against the theory's PRE-ELABORATED env (decls amortized once, probe ~0.04s) instead of
        # re-inlining + re-elaborating the heavy prelude PER probe (the v7 verify-starvation — 592-1016s
        # timeouts closed nothing). SOUND: `warm_verify_campaign` runs the `#print axioms` audit against that
        # env, so a proof that LAUNDERS by citing a still-`sorry` decl (live in the env) carries `sorryAx` and
        # is rejected exactly as the cold governance audit would (validated: laundering REJECTED, clean PASS).
        # The target's own sorried decl is live in the env, so the probe uses a FRESH name (no redeclare clash).
        # None ⇒ fall through to the inline REPL/cold path below (byte-parity when no campaign substrate).
        try:
            import re as _re
            from ztare.formal.repl_compile import (get_campaign_substrate, campaign_file_env,
                                                    warm_verify_campaign)
            _sub = get_campaign_substrate()
            if _sub:
                _env = campaign_file_env(_sub, lean_root)
                if _env is not None:
                    _ms = list(_re.finditer(r"(?m)^\s*(theorem|lemma)\s+([A-Za-z_][\w'.]*)", goal))
                    if _ms:
                        _m = _ms[-1]
                        _name = _m.group(2)
                        _stub = goal[_m.start():].strip()                       # "theorem NAME SIG := by"
                        _fresh = f"{_name}_zwv"
                        # CANONICAL prefix-strip + rename (no regex on the decl): strip_decl_prefix returns
                        # everything after `theorem NAME` — the SIG + the `:=`/`:= by` tail VERBATIM.
                        from ztare.leanmill.lean_source import strip_decl_prefix as _strip_pref
                        _stub_fresh = f"theorem {_fresh} {_strip_pref(_stub)}"
                        _wp = (f"{_stub_fresh}\n  {proof_block}\n" if _stub_fresh.rstrip().endswith(":= by")
                               else f"{_stub_fresh}\n{body}\n")
                        _cw = warm_verify_campaign(_wp, _fresh, lean_root, timeout_s, env=_env)
                        if _cw is not None:
                            if _cw[0]:
                                self._persist_verified_probe(src, lean_root, row_id)
                            return CheckResult(_cw[0], _cw[1], self.name)
        except Exception:  # noqa: BLE001 — never let the campaign fast path break the canonical verify
            pass
        # REPL fast-path (ZTARE_LEANMILL_REPL_COMPILE=1 + a LIVE toolchain-matched repl over lean_root): a warm
        # PersistentLean elaborates in ~0.1s vs the ~60-90s cold `lake env lean` below — SAME verdict (no error ∧
        # no sorry) + the error tail for failure_class. None ⇒ fall through (byte-parity when the flag is off).
        try:
            from ztare.formal.repl_compile import compile_probe_via_repl
            _rr = compile_probe_via_repl(src, lean_root, timeout_s, reject_sorry=True)  # no-false-closure: sorry ⇒ not ok
            if _rr is not None:
                if _rr[0]:
                    self._persist_verified_probe(src, lean_root, row_id)
                return CheckResult(_rr[0], _rr[1], self.name)
        except Exception:  # noqa: BLE001 — never let the fast path break the canonical compile
            pass
        try:
            with tempfile.TemporaryDirectory(prefix=f"solver_verify_{row_id}_") as td:
                probe = Path(td) / "Probe.lean"
                probe.write_text(src, encoding="utf-8")
                proc = run_lake_subprocess(
                    ["lake", "env", "lean", str(probe)], str(lean_root), timeout_s=timeout_s,
                )
                output = (proc.stdout or "") + "\n" + (proc.stderr or "")
                _ok = _is_compile_ok(proc.returncode, output)
                if _ok:
                    self._persist_verified_probe(src, lean_root, row_id)
                return CheckResult(_ok, output[-800:], self.name)
        except subprocess.TimeoutExpired:
            return CheckResult(False, "verify_compile_timeout", self.name)
        except FileNotFoundError as exc:
            return CheckResult(False, f"lake_not_on_PATH: {exc!s}", self.name)
        except Exception as exc:  # noqa: BLE001
            return CheckResult(False, f"verify_compile_exception: {exc!r}", self.name)

    @staticmethod
    def _persist_verified_probe(src: str, lean_root: Path, row_id: str) -> None:
        """Persist the EXACT verified-OK probe source to the shared probe_dir (best-effort). WHY (v3 RCA
        2026-06-12): the REPL fast-path verified in-memory and the cold path used a TemporaryDirectory, so a
        cascade/native_hammer closure left NO durable artifact — the governance organs' RobustProbe_*.lean
        glob found nothing ⇒ statement-integrity SILENTLY skipped (`integrity_unverified`), the closure
        certificate captured an EMPTY recompilable_probe, and no closures/<name>.lean was materialized: the
        proven rung was unauditable AND unreusable. Writing the artifact the kernel actually ratified makes
        warm and cold paths artifact-identical with the agentic-leaf path (whose RobustProbe files the glob
        was built for). Name matches the existing readback glob — no reader changes."""
        try:
            import re as _re_pp   # LOCAL import — a bare-except wrapper + missing module-level name is the
            from ztare.leanmill.solver.agentic_leaf import probe_dir   # silent-no-op disease (2026-06-11 lesson)
            safe = _re_pp.sub(r"[^A-Za-z0-9_]+", "_", str(row_id))[:80] or "anon"
            (probe_dir(lean_root) / f"RobustProbe_native_{safe}.lean").write_text(src, encoding="utf-8")
        except Exception:  # noqa: BLE001 — telemetry-grade write; never fail a verified closure on IO
            pass


# The ACTIVE proof-side checker. Default = the Lean binding; swap via set_proof_checker() (tests / a
# non-Lean substrate). Module-global so the existing `_verify_compile(...)` call sites stay byte-identical
# — the indirection is added WITHOUT touching the 8 callers (the statement side was already injectable;
# this brings the proof side to parity).
_PROOF_CHECKER: "object" = LeanLakeChecker()


def set_proof_checker(checker):
    """Swap the active proof-side Checker; returns the previous one (restore in a finally). `checker` is
    any object with `verify(goal, proof, *, lean_root, timeout_s, row_id) -> CheckResult` and a `.name`.
    Calibration discipline: before trusting a swapped checker, run a known-good AND a known-`sorry` probe
    through it and confirm ok / not-ok (a negative is inadmissible without the positive+negative control)."""
    global _PROOF_CHECKER
    prev = _PROOF_CHECKER
    _PROOF_CHECKER = checker
    return prev


def active_proof_checker_name() -> str:
    """Which checker is currently ratifying closures — recorded in the closure certificate for audit."""
    return getattr(_PROOF_CHECKER, "name", "unknown")


def _verify_compile(row_id: str, goal_text: str, proof_text: str,
                    lean_root: Path, timeout_s: int) -> tuple[bool, str]:
    """Thin shim over the active proof-side Checker (default `LeanLakeChecker`). Preserves the stable
    `(compile_ok, tail)` contract its 8 call sites expect; the Lean-specifics now live in the Checker, so
    the proof side is injectable like the statement side. Behavior-identical to the pre-refactor function
    under the default checker. See `set_proof_checker`."""
    r = _PROOF_CHECKER.verify(goal_text, proof_text, lean_root=lean_root, timeout_s=timeout_s, row_id=row_id)
    return r.ok, r.diagnostics
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
    # CALIBRATED ceils 2026-06-11 (scripts/private/move_wallclock_calibration.py over the attempts DB): a move's
    # ceil was ~10× its measured SUCCESS time, so on a LARGE wallclock the doomed direct cascade ate the WHOLE
    # budget before route_and_solve (the decomposition path — the only one that can close a research target like
    # RUNG A) ever fired. warm successes finish by succ_p90=180s (ceil 360 = 2× headroom); cold/frontier by
    # ~79s, external_frontier never (ceil 360). These bind ONLY on big targets — on a ≤900s run the fraction
    # already dominates, so this is byte-parity there and a pure win on the frontier targets the apparatus exists for.
    "warm":          (0.40, 150,  360),  # was ceil 1800 → claude_warm alone ate 720s (40%) of an 1800s target
    "native_hammer": (0.10, 120,  180),  # floor 120 (was 45): a single cold Mathlib reload is ~60-90s on this
    #   box (no persistent REPL), so a <90s floor STARVES native mid-reload on a heavy file ⇒ its failed_compile
    #   is a CAP ARTIFACT, not a math negative (inadmissible). 120 covers the cold reload + the cheap cascade.
    "cold_frontier": (0.20,  90,  360),  # was ceil 900; cold_shot succ_p90≈79s, external_frontier 0 successes
    "conjecture":    (0.15,  90,  900),
    "specialize":    (0.10,  60,  600),
    "generalize":    (0.15,  90,  900),
    "tactic_step":   (0.18, 120,  900),
    "falsify":       (0.15,  90,  600),
    "corroborate":   (0.15,  90,  600),   # Popper-dual of falsify; same shape (one leaf call + kernel gate)
    "witness_transport": (0.05, 30, 120),  # a bounded SymPy subprocess + one kernel compile — cheap + fast
    "sledgehammer":      (0.15, 90, 900),  # one external Isabelle call + per-premise #check probes + a closing compile
    "reflection":        (0.15, 90, 900),  # one leaf call (check/sound/close) + a pre-filter compile + the closure compile
    "abduce":            (0.15, 90, 900),  # a bounded cvc5 abduct + ONE seeded leaf call; proving cost is in the spawned child
    "functor_lift":      (0.15, 90, 900),  # one leaf call (the lift) + a NumPy spectral compute + a bridge #check + closing compile
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
    if move_key == "warm":
        # CONSOLIDATION FIX (v6 RCA 2026-06-12): the warm ceil 360 was calibrated from success-p90 times
        # measured UNDER the old caps — a censored statistic (successes could not take longer than the cap
        # that the calibration then justified: survivorship bias). v6's real frontier closures ran 412-515s
        # THROUGH this ceiling, and the campaign knob (ZTARE_LEANMILL_DISPATCH_S=1800, the "1×30-min
        # session" lever) never reached the leaf because this ceil bound first. The ceil now FOLLOWS the
        # central-factory dispatch budget (default 600 ⇒ moderate lift; campaign 1800 ⇒ the window actually
        # lands); the FRACTION still scales it to the run's wallclock, the idle-kill + warm-goal cap bound
        # the downside, and ZTARE_LEANMILL_CAP_WARM remains the absolute override.
        try:
            from ztare.common.timeouts import timeout_s as _ts_pm
            ceil = max(ceil, _ts_pm("agent_dispatch"))
        except Exception:  # noqa: BLE001 — factory lookup must never break the cap path
            pass
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
         `_is_compile_ok` via `_verify_compile` / `_agentic_leaf_warm_solve`),
      3. returns a typed MoveResult whose `kernel_clean` / `mnc_passed` are read
         straight off the governance receipts — the search NEVER self-credits.

    This is the proposes/ratifies boundary: the runner ratifies, the search records.
    """
    from ztare.leanmill.solver.governed_dag_search import (
        MoveResult, MOVE_NATIVE_HAMMER, MOVE_CLAUDE_WARM, MOVE_COLD_SHOT, MOVE_FRONTIER,
        MOVE_CONJECTURE, MOVE_SPECIALIZE, MOVE_GENERALIZE, MOVE_FALSIFY, MOVE_TACTIC_STEP,
        MOVE_CORROBORATE, MOVE_WITNESS_TRANSPORT, MOVE_SLEDGEHAMMER,
        MOVE_REFLECTION, MOVE_ABDUCE, MOVE_FUNCTOR_LIFT,
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
            # on a regex MISS, give the spawned sub-goal a DISTINCT name (node_id suffix) — never silently
            # inherit the PARENT's name (the inertness bug: the sub-node would prove under the parent's
            # name and mis-attribute). 2026-06-13 audit A3.
            _nr["target_theorem_name"] = (_mm.group(1) if _mm
                                          else f"{r.get('target_theorem_name', 'tgt')}__{node.node_id}")
            return _nr

        def _h_native_hammer():
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
        def _h_claude_warm():
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
                _o, _p, _t = _agentic_leaf_warm_solve(_ctx["row"], (lean_root or DEFAULT_LEAN_ROOT_FOR_VERIFY),
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
        def _h_conjecture():
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
            # THEORY-BUILDING GENERATIVE LEG (2026-06-20): when there is no obstruction seed and the goal
            # classifies as theory-building (the catalogue obligation/two-cultures), drive the conjecture with
            # the CATALOGUE-GUIDED prompt (op mechanism + campaign theory vocabulary + "name the missing GENERAL
            # prerequisite a mathematician would bank") instead of the blind "invent one lemma" prompt. Same
            # LEMMA:/PROOF: contract ⇒ identical conjecture_advances kernel gate + child-spawn + bank. Default-on,
            # =0 reverts to the blind prompt (the A/B baseline). Closes the descriptive→generative catalogue gap.
            if _seed_prompt is None:
                try:
                    from ztare.leanmill.solver import theory_building as _tb
                    if _tb.is_enabled():
                        _tbgap = _tb.classify_gap(_gt)
                        if _tbgap.is_theory_building:
                            _seed_prompt = _tb.build_prompt(_gt, _tbgap, theory_defs=_tb.campaign_theory_defs())
                except Exception:  # noqa: BLE001 — never let the prompt enrichment break the move
                    _seed_prompt = None
            _lemma, _proof, _lname, _craw = conjecture_generate(
                r, _gt, (lean_root or DEFAULT_LEAN_ROOT_FOR_VERIFY),
                _cap("conjecture", max(120, verify_timeout)),
                prompt_override=_seed_prompt)
            _adv, _atail = conjecture_advances(
                _lemma, _proof, _lname, (lean_root or DEFAULT_LEAN_ROOT_FOR_VERIFY),
                _cap("conjecture", max(120, verify_timeout)),
                # PREAMBLE (2026-06-21 RCA): the advance probe must see the campaign's bespoke defs
                # (`HasRatDeriv`, `poleTerm`, `SimpleRootResiduesVanishFor`, …) — else a goal-proof citing
                # them fails `unknown identifier` cold ⇒ a FALSE `no_advance` ("did not typecheck"). SPECIALIZE
                # already threads this; CONJECTURE was the missed sibling call site (146/218 no_advance were
                # this false-negative, all uniformly "did not typecheck" on campaign-vocabulary goals).
                preamble=_preamble_from_source(r),
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
        def _h_specialize():
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
        def _h_generalize():
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
        def _h_tactic_step():
            # TACTIC-STEPPING (M3 v2): per-step agentic search — the leaf emits ONE tactic at a time vs a
            # PERSISTENT proofState built from OUR decl (the anti-laundering invariant: no file edit; the leaf reacts to each live
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
        def _h_witness_transport():
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
        def _h_sledgehammer():
            # SLEDGEHAMMER-SMUGGLE (premise retrieval, 2026-06-08): borrow Isabelle's `sledgehammer` premise
            # selection. Translate G→Isabelle, run sledgehammer on the EXTERNAL server, extract the dependency
            # trace, map the Isabelle fact names to Mathlib (HALLUCINATES), kernel-`#check` each (DROP any that
            # don't resolve), inject the survivors as exact?/aesop premises. FAIL-CLOSED: with no Isabelle server
            # configured (ZTARE_ISABELLE_SERVER unset) `sledgehammer_smuggle` returns '' ⇒ a no-op miss (NOT a
            # false closure). The injected tactic is re-verified through the SAME governance (_verify_compile +
            # _govern = kernel + MNC + statement_integrity) as warm/generalize: a wrong/hallucinated premise set
            # merely fails to compile (a MISS), never a closure. No false-closure surface.
            from ztare.leanmill.solver.sledgehammer import sledgehammer_smuggle
            _sh_goal = (_eff_row().get("goal") or node.goal_text or enriched_goal or "").strip()
            _sh_pre = _preamble_from_source(r)
            _sh_lr = lean_root or DEFAULT_LEAN_ROOT_FOR_VERIFY
            _sh_tac, _sh_info = sledgehammer_smuggle(
                _sh_goal, _sh_lr, _cap("sledgehammer", max(120, verify_timeout)), preamble=_sh_pre)
            compile_ok, compile_tail = (False, "no sledgehammer injection (" + str(_sh_info.get("stage")) + ")")
            if _sh_tac.strip():
                compile_ok, compile_tail = _verify_compile(
                    r["row_id"], _sh_goal, _sh_tac, _sh_lr, verify_timeout)
            kc, mnc = _govern(_sh_tac, compile_ok, compile_tail) if compile_ok else (False, False)
            _sh_drop = _sh_info.get("dropped_hallucinations") or []
            _sh_val = _sh_info.get("validated_names") or []
            # CROSS-SUBSTRATE CONSENSUS (#85): reconcile Isabelle (ATP found a proof) ⇄ Lean (the mapped
            # Mathlib reconstruction is kernel-clean) on the SAME goal — corroboration = a cross-kernel
            # trust-lift on a MATH goal; Isabelle-yes/Lean-no localizes the Isabelle→Mathlib mapping bug.
            # Advisory telemetry only — the _govern kernel above is the SOLE closure arbiter.
            try:
                from ztare.leanmill.solver.sledgehammer import sledgehammer_consensus
                # The consensus validates the Isabelle→Mathlib PREMISE MAPPING (Isabelle's facts, re-checked in
                # Lean), so it is only meaningful when there ARE premises to reconcile → `bool(dependency_trace)`,
                # NOT `bool(proof)`: an Isabelle proof with an EMPTY trace (closed by `simp`, no facts) injects no
                # premises (tactic=''), so a proof-signal there manufactures a false Isabelle-yes/Lean-no conflict.
                # Empty trace ⇒ only the Lean verdict ⇒ INSUFFICIENT (correct). `isabelle_proved` is kept as diag.
                _sh_xsub = sledgehammer_consensus(
                    _sh_goal, isabelle_found=bool(_sh_info.get("dependency_trace")), lean_compiles=kc,
                    isabelle_diag=f"proved={_sh_info.get('isabelle_proved')} facts={_sh_info.get('dependency_trace')}",
                    lean_diag=(compile_tail or "")[:120]).status
            except Exception:  # noqa: BLE001 — telemetry is best-effort, never breaks the move
                _sh_xsub = "error"
            _record_attempt(r["row_id"], "sledgehammer",
                            "closed" if (kc and mnc) else ("no_server" if _sh_info.get("stage") == "no_server"
                                                           else "failed_compile"),
                            kc and mnc,
                            (f"stage={_sh_info.get('stage')} validated={_sh_val} dropped={_sh_drop} "
                             f"xsub={_sh_xsub} :: " + (compile_tail or ""))[-200:],
                            est_p_close=fc, wallclock_s=round(time.time() - start, 2))
            providers_tried.append({"provider": "sledgehammer",
                                    "outcome": "closed" if (kc and mnc) else "failed_compile",
                                    "compile_ok": kc, "mnc_passed": mnc, "node_id": node.node_id,
                                    "move": move, "agent_kind": "sledgehammer_smuggle",
                                    "validated_premises": _sh_val, "dropped_hallucinations": _sh_drop,
                                    "cross_substrate": _sh_xsub})
            return MoveResult(move=move, kernel_clean=kc, mnc_passed=mnc, proof_text=_sh_tac,
                              tail=(compile_tail or "")[-300:],
                              wallclock_s=round(time.time() - start, 2), **_ps(compile_ok, compile_tail))
        def _h_reflection():
            # REFLECTION (computational closure, 2026-06-08): the leaf writes a decidable `def check` + a
            # `theorem check_sound : check args = true → G` + a closing body; reflection_solve GENERATES +
            # pre-filter-GATES (trivial-constant / native_decide reject, fail-closed). The invented helper
            # decls PREPEND to the goal stub (ADDED decls statement_integrity ALLOWS) and the closure of G is
            # RE-VERIFIED through the SAME governance (_verify_compile + _govern). A wrong check/soundness/
            # decide fails to compile (a MISS), never a false closure. Default-OFF (stuck-gated).
            from ztare.leanmill.solver.reflection import reflection_solve
            _rf_gt = enriched_goal or node.goal_text
            _rf_lr = lean_root or DEFAULT_LEAN_ROOT_FOR_VERIFY
            _rf_cbody, _rf_helper, _rf_reason, _rf_info = reflection_solve(
                _eff_row(), _rf_gt, _rf_lr, _cap("reflection", max(180, verify_timeout)),
                preamble=_preamble_from_source(r))
            compile_ok, compile_tail = (False, (_rf_reason or "no reflection closure")[:120])
            if _rf_cbody.strip():
                _rf_gth = ((_rf_helper.rstrip() + "\n\n") if _rf_helper.strip() else "") + _rf_gt
                compile_ok, compile_tail = _verify_compile(r["row_id"], _rf_gth, _rf_cbody, _rf_lr, verify_timeout)
            kc, mnc = _govern(_rf_cbody, compile_ok, compile_tail) if compile_ok else (False, False)
            _record_attempt(r["row_id"], "reflection", "closed" if (kc and mnc) else "failed_compile",
                            kc and mnc, (str(_rf_reason) + " :: " + (compile_tail or ""))[-200:],
                            est_p_close=fc, wallclock_s=round(time.time() - start, 2))
            providers_tried.append({"provider": "reflection",
                                    "outcome": "closed" if (kc and mnc) else "failed_compile",
                                    "compile_ok": kc, "mnc_passed": mnc, "node_id": node.node_id,
                                    "move": move, "agent_kind": "reflection"})
            return MoveResult(move=move, kernel_clean=kc, mnc_passed=mnc, proof_text=_rf_cbody,
                              tail=(compile_tail or "")[-300:],
                              wallclock_s=round(time.time() - start, 2), **_ps(compile_ok, compile_tail))
        def _h_abduce():
            # ABDUCE (SMT-grounded conjecture, 2026-06-08): cvc5 `(get-abduct)` derives the minimal missing
            # premise A; abduce_seed wraps it as a targeted prompt_override for conjecture_generate (replaces
            # weak free-generation with a grounded one). Then the SAME advance/spawn gate as MOVE_CONJECTURE:
            # prove G ASSUMING L=A (kernel, L=sorry) + spawn A as a child. INERT (no_seed) without cvc5.
            # Never closes G (advance-only) — no false-closure surface.
            from ztare.leanmill.solver.abduction import abduce_seed
            _ab_gt = enriched_goal or node.goal_text
            _ab_lr = lean_root or DEFAULT_LEAN_ROOT_FOR_VERIFY
            _ab_seed = abduce_seed((_eff_row().get("goal") or node.goal_text or _ab_gt),
                                   _cap("abduce", max(30, verify_timeout)))
            if _ab_seed is None:
                _record_attempt(r["row_id"], "abduce", "no_seed", False,
                                "no cvc5 abduct (inert / non-arithmetic)", est_p_close=fc,
                                wallclock_s=round(time.time() - start, 2))
                return MoveResult(move=move, kernel_clean=False, mnc_passed=False, residual="abduce_no_seed",
                                  tail="no abduct", wallclock_s=round(time.time() - start, 2), **_ps(False, ""))
            _ab_lemma, _ab_proof, _ab_lname, _ab_raw = conjecture_generate(
                r, _ab_gt, _ab_lr, _cap("abduce", max(120, verify_timeout)),
                prompt_override=_ab_seed.targeted_prompt)
            _ab_adv, _ab_atail = conjecture_advances(
                _ab_lemma, _ab_proof, _ab_lname, _ab_lr, _cap("abduce", max(120, verify_timeout)),
                preamble=_preamble_from_source(r),   # same campaign-vocab false-negative fix as MOVE_CONJECTURE
                goal_conclusion=_lemma_conclusion(_eff_row().get("goal") or node.goal_text or _ab_gt))
            _record_attempt(r["row_id"], "abduce", "advanced" if _ab_adv else "no_advance", False,
                            _ab_atail, est_p_close=fc, wallclock_s=round(time.time() - start, 2))
            providers_tried.append({"provider": "abduce", "outcome": "advanced" if _ab_adv else "no_advance",
                                    "compile_ok": False, "mnc_passed": False, "node_id": node.node_id,
                                    "move": move, "agent_kind": "abduce"})
            return MoveResult(move=move, kernel_clean=False, mnc_passed=False,
                              proof_text=(_ab_proof if _ab_adv else ""),
                              new_sub_goal_text=(_ab_lemma if _ab_adv else None),
                              residual=("abduce_lemma_pending" if _ab_adv else "abduce_no_advance"),
                              tail=(_ab_atail or "")[-300:],
                              wallclock_s=round(time.time() - start, 2), **_ps(False, ""))
        def _h_functor_lift():
            # FUNCTOR_LIFT (spectral/domain closure, 2026-06-08): a stuck DISCRETE goal is lifted to the
            # continuous domain; the module gets the matrix + bridge-lemma name + a Lean proof citing the
            # bridge. TWO independent legs, BOTH required:
            #   (1) EXOGENOUS SPECTRAL TEETH — compute_spectral_bound (NumPy) + functor_lift_advances
            #       (bridge-exists + sorry-free + cites-bridge + the SELF-CONTAINED proof typechecks): the
            #       lift MECHANISM is genuine (a real bridge discharges a real spectral bound), not a direct
            #       proof in disguise.
            #   (2) STATEMENT-INTEGRITY ANCHOR — the leaf's proof is self-contained (`<leaf_sig> := <body>`),
            #       so closing on it ALONE would re-introduce the warm-path statement-alteration vector (the
            #       leaf could prove a WEAKENED `leaf_sig`). So we DISCARD the leaf's signature and re-verify
            #       only its BODY under the ORIGINAL goal stub via the SAME `_verify_compile` + `_govern`
            #       (kernel + MNC + statement_integrity on enriched_goal) every other move uses. A statement
            #       swap ⇒ the body won't typecheck under OUR signature ⇒ a MISS, never a false closure of G.
            # Fail-closed (no-op) without NumPy / a present bridge. Default-OFF (stuck-gated).
            from ztare.leanmill.solver.spectral_lift import (
                functor_lift_generate, compute_spectral_bound, functor_lift_advances)
            _fl_gt = enriched_goal or node.goal_text
            _fl_lr = lean_root or DEFAULT_LEAN_ROOT_FOR_VERIFY
            _fl_pre = _preamble_from_source(r)
            _fl_mat, _fl_bridge, _fl_note, _fl_proof, _fl_raw = functor_lift_generate(
                _eff_row(), _fl_gt, _fl_lr, _cap("functor_lift", max(180, verify_timeout)), preamble=_fl_pre)
            _fl_spec = compute_spectral_bound(_fl_mat) if _fl_mat.strip() else None
            # leg (1): the exogenous spectral/bridge teeth (functor_lift_advances does its OWN kernel compile).
            _fl_adv, _fl_reason = (False, "no lift proof")
            if _fl_proof.strip():
                _fl_adv, _fl_reason = functor_lift_advances(
                    _fl_proof, _fl_bridge, _fl_lr, _cap("functor_lift", max(180, verify_timeout)),
                    preamble=_fl_pre, spectral=_fl_spec)
            # leg (2): re-verify the leaf's BODY (the RHS after the first top-level `:=` — goal_head carries
            # no `:=`) under the ORIGINAL goal stub, then govern. This is the closure-crediting kernel call.
            kc, mnc, compile_ok, compile_tail = False, False, False, _fl_reason
            from ztare.leanmill.lean_source import split_at_proof as _sap_fl
            _fl_body = _sap_fl(_fl_proof)[1][2:].strip() if _fl_adv else ""   # proof body, binder-safe ([2:] drops `:=`)
            if _fl_body:
                compile_ok, compile_tail = _verify_compile(r["row_id"], _fl_gt, _fl_body, _fl_lr, verify_timeout)
                kc, mnc = _govern(_fl_body, compile_ok, compile_tail) if compile_ok else (False, False)
            _fl_credit = bool(kc and mnc)
            _record_attempt(r["row_id"], "functor_lift", "closed" if _fl_credit else "failed_compile",
                            _fl_credit,
                            (f"adv={_fl_adv} :: {_fl_reason} bridge={_fl_bridge} :: " + (compile_tail or ""))[-200:],
                            est_p_close=fc, wallclock_s=round(time.time() - start, 2))
            providers_tried.append({"provider": "functor_lift",
                                    "outcome": "closed" if _fl_credit else "failed_compile",
                                    "compile_ok": kc, "mnc_passed": mnc, "node_id": node.node_id,
                                    "move": move, "agent_kind": "functor_lift", "bridge": _fl_bridge,
                                    "spectral_advanced": _fl_adv})
            return MoveResult(move=move, kernel_clean=kc, mnc_passed=mnc, proof_text=(_fl_body or _fl_proof),
                              tail=(compile_tail or _fl_reason or "")[-300:],
                              wallclock_s=round(time.time() - start, 2), **_ps(compile_ok, compile_tail))
        def _h_falsify_corroborate():
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
        # DISPATCH TABLE (2026-07-01 refactor of the 222-CCN per-move if/elif ladder into named handlers +
        # a single {move: handler} table IN THIS MODULE — preserves the single-move-surface invariant, NOT a
        # scattered/second dispatch surface). Bodies are the former branch bodies verbatim (nested closures
        # over the same scope). The None-guard reproduces the old fall-through: a matched handler that returns
        # nothing (or an unknown move) yields the 'unknown move' MoveResult, exactly as the if-ladder did.
        _dispatch = {
            MOVE_NATIVE_HAMMER: _h_native_hammer, MOVE_CLAUDE_WARM: _h_claude_warm,
            MOVE_CONJECTURE: _h_conjecture, MOVE_SPECIALIZE: _h_specialize,
            MOVE_GENERALIZE: _h_generalize, MOVE_TACTIC_STEP: _h_tactic_step,
            MOVE_WITNESS_TRANSPORT: _h_witness_transport, MOVE_SLEDGEHAMMER: _h_sledgehammer,
            MOVE_REFLECTION: _h_reflection, MOVE_ABDUCE: _h_abduce, MOVE_FUNCTOR_LIFT: _h_functor_lift,
            MOVE_FALSIFY: _h_falsify_corroborate, MOVE_CORROBORATE: _h_falsify_corroborate,
        }
        _h = _dispatch.get(move)
        if _h is not None:
            _r = _h()
            if _r is not None:
                return _r
        return MoveResult(move=move, kernel_clean=False, mnc_passed=False,
                          tail=f"unknown move {move}")

    # ENGAGEMENT JOIN (gap #1, 2026-06-20): wrap the runner so EVERY (node, move) execution records which move
    # the search engaged + the atlas RANK that move held in the menu the agent saw — surfaced (provenance) ×
    # engaged (here) = "the agent used a move the atlas ranked #k". Single chokepoint, best-effort, never gates.
    def _mr_logged(node, move, budget):
        _res = move_runner(node, move, budget)
        try:
            from ztare.leanmill.solver import move_atlas as _ma
            _oc = "closed" if getattr(_res, "ratified_close", False) else (getattr(_res, "error_class", "") or "open")
            _ma.log_engagement(getattr(node, "goal_text", "") or enriched_goal or "",
                               getattr(_res, "move", move), outcome=_oc, via="governed_move")
        except Exception:  # noqa: BLE001 — engagement telemetry is best-effort
            pass
        return _res

    return _mr_logged


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
    # FORECAST-POOL POLICY router (strategic seam, #86): advisory ranking of the target batch by forecast EV
    # (cache-hit first, known no_good sunk). Parity no-op unless ZTARE_LEANMILL_FORECAST_ROUTER=1; it only
    # REORDERS once the PolicyPromotion gate is 'active' (earned by beating baseline), else it just LOGS the
    # ranking to gather the A/B data. Never raises (a bad signal path ⇒ that forecaster abstains).
    _fpriced: dict = {}
    try:
        from ztare.leanmill.solver.forecast_router import rank_rows as _frank
        rows, _flog, _fpriced = _frank(rows, db_path=ATTEMPTS_DB,
                                       cache_path=OUT_DIR / "solver_lane_proof_cache.jsonl",
                                       no_good_path=OUT_DIR / "solver_lane_no_good_store.jsonl",
                                       faithfulness_path=OUT_DIR / "solver_lane_faithfulness_store.jsonl")
        if _flog:
            print(f"[forecast] {_flog}", flush=True)
    except Exception:  # noqa: BLE001
        pass
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
                    _hdr = (f"[solver] self-tuning priors (k={_k} autotune={_tune.get('tuned')} "
                            f"recorded_brier={_rfb.get('recorded_forecast_brier')}/n={_rfb.get('n')}; "
                            f"bases: {_bases or 'all-stub'})")
                    _tbl = _mc.report(str(ATTEMPTS_DB))
                    # DE-SPAM: emit the full table only when it changed since last solve (or verbose flag);
                    # else a one-liner. Killed 40% of the v6 log (368 repeated table lines) — observability
                    # preserved (a real calibration shift still prints the full table).
                    import hashlib as _hl_cb
                    _fp = _hl_cb.sha256((_hdr + "\n" + _tbl).encode("utf-8")).hexdigest()[:12]
                    if os.environ.get("ZTARE_LEANMILL_VERBOSE_CALIB") == "1" or _fp != _LAST_CALIB_FP[0]:
                        print(f"{_hdr}:\n{_tbl}")
                        _LAST_CALIB_FP[0] = _fp
                    else:
                        print(f"{_hdr} [calibration unchanged]")
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
                from ztare.common.timeouts import timeout_s as _budget
                _dag_move_budget = float(_budget("dag_move_budget"))   # central factory (env ZTARE_DAG_MOVE_BUDGET)
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
                # SINGLE-DOOR FLOOR (no-false-clean, 2026-06-25): this branch runs NO downstream firewall/axiom
                # audit — it reports the DAG verdict directly. So a "closed" root MUST carry a kernel-verified
                # proof_text; a closed-with-empty-proof verdict is a bookkeeping bug (a status-flip that bypassed
                # the kernel — the propagate-close class) and is rejected HERE as an honest gap, never emitted as
                # a clean closure. Belt-and-suspenders behind the governed_dag_search invariant enforcement.
                root_closed = dag_res["root_status"] == "closed"
                if root_closed and not (dag_res.get("root_proof_text") or "").strip():
                    print(f"[dag_search] *** root reported 'closed' with EMPTY proof_text "
                          f"({r['row_id']}) — DOWNGRADING to honest gap (single-door: closed ⟺ "
                          f"kernel-verified proof) ***", flush=True)
                    root_closed = False
                    dag_res["root_resolution"] = "closed_without_proof_text_gap"
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
                                          start_t: float,
                                          closure_source: "str | None" = None,
                                          posed_source: "str | None" = None) -> dict | None:
                """Run contract validation; if credit_ready, build the
                closed-result dict and return it (caller appends + continues).
                If not credit_ready, return None and the dispatcher walks on.
                `closure_source` (optional) = the COMPLETE proof-carrying source to govern verbatim — the
                pre-verified-champion path passes the mode-agnostic `swap_sorry(source, champion)` so a TERM
                champion is governed as the proposer verified it (not re-forced into `:= by`)."""
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
                    closure_source=closure_source,
                    posed_source=posed_source,
                )
                providers_tried[-1]["contract_validation"] = validation
                if not validation["credit_ready_at_solver_layer"]:
                    # TRUTHFUL labeling (RCA 2026-06-18): derive WHY credit was blocked from the receipt that
                    # actually failed — never the legacy hardcoded `rejected_negative_control` catch-all (which
                    # mislabeled axiom/kernel/flow rejections as leakage and poisoned move-calibration).
                    _reason, _detail = _reject_reason_from_validation(validation)
                    providers_tried[-1]["outcome"] = _reason
                    _record_attempt(
                        r["row_id"], prov_label, _reason, False,
                        f"credit blocked at solver layer: {_reason} — {_detail}",
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

            # --- Layer 1.5: PRE-VERIFIED CHAMPION (governed proposer pool) ──────────────────────────────
            # A proposer (the governed pool, via solve_adhoc) already produced a proof that passed its own
            # compile-verify and handed it over in row["_preverified_proof"]. Route it through the SAME governance
            # every move uses — kernel compile + MNC + anti-laundering + axiom audit, via _validate_and_maybe_close
            # — BEFORE re-deriving. ROOT-CAUSE FIX (2026-06-22): previously the pool spliced the champion into the
            # source FILE and relied on the DAG/cascade to "re-verify + govern", but those build from the GOAL
            # signature and RE-DERIVE, so a VALID champion was silently discarded → target read closed-NOT-ratified.
            # credit_ready ⇒ a real ratified closure + cert; rejected ⇒ a proper rejected_* (recorded by
            # _validate_and_maybe_close); neither ⇒ fall through to the cascade (re-derive). No new soundness surface
            # — the SAME _validate_against_contract every move routes through. (Only solve_adhoc sets this field,
            # and it runs mode="cascade", so the cascade-path placement covers every current caller.)
            _pvp = (r.get("_preverified_proof") or "").strip()
            if _pvp:
                _pv_prov = r.get("_preverified_provider") or "proposer_pool"
                _pv_start = time.time()
                # Splice + verify the champion the SAME MODE-AGNOSTIC way the proposer did: `swap_sorry(source,
                # champion)` handles a TERM proof (placed after `:=`) AND a tactic `by` body; the layered
                # `enriched_goal` ends `:= by`, which mangles a TERM champion (the two-verify-worlds split that
                # left the pool's valid champion unratifiable). Compile via `_campaign_aware_proof_compiles` (the
                # SAME check the pool used) and govern the EXACT spliced artifact via `closure_source`.
                from ztare.leanmill.lean_source import swap_sorry as _swap_pv
                _pv_root = (lean_root or DEFAULT_LEAN_ROOT_FOR_VERIFY)
                _pv_srctext = ""
                try:
                    _pv_sp = ProofTarget.from_row(r).source_path()
                    if _pv_sp and Path(_pv_sp).exists():
                        _pv_srctext = Path(_pv_sp).read_text(encoding="utf-8", errors="replace")
                except Exception:  # noqa: BLE001 — missing source ⇒ treat as a non-compile, fall to cascade
                    _pv_srctext = ""
                _pv_full = _swap_pv(_pv_srctext, _pvp) if _pv_srctext else ""
                _pv_ok = bool(_pv_full) and "sorry" not in _pv_full and _campaign_aware_proof_compiles(
                    _pv_srctext, _pvp, _pv_root, verify_timeout)
                providers_tried.append({
                    "provider": _pv_prov,
                    "outcome": "compiled" if _pv_ok else "failed_compile",
                    "compile_ok": _pv_ok,
                    "provider_wallclock_s": round(time.time() - _pv_start, 2),
                    "agent_kind": "preverified_champion",
                })
                if _pv_ok:
                    _pv_closed = _validate_and_maybe_close(
                        _pv_prov, True, _pvp, "pre-verified champion (mode-agnostic splice)", _pv_start,
                        closure_source=_pv_full, posed_source=_pv_srctext)
                    if _pv_closed is not None:
                        # Record the closed (compile_ok=1) attempt on THIS row_id — the row the post-solve
                        # governance stamp (`_record_governance_verdict`) and the closure cert anchor on. Without
                        # it the closure was genuine (full governance passed inside `_validate_and_maybe_close`)
                        # but left NO ratified=1 row and NO cert — a telemetry UNDER-report (and the conservation
                        # guard would read green for the wrong reason, having no `closed` row to check).
                        # A closure via the proof_cache cite IS reuse — record it under the CANONICAL `cache_reuse`
                        # move (the DAG path's label), so reuse telemetry + campaign_cycle_time count it instead of
                        # the raw `proof_cache` provider label that read as 0 cites. Other pre-verified providers
                        # (proposer_pool / external) keep their own move (auto-derived from the provider).
                        _record_attempt(r["row_id"], _pv_prov, "closed", True,
                                        "pre-verified champion ratified (mode-agnostic splice)",
                                        move=("cache_reuse" if _pv_prov == "proof_cache" else None))
                        results.append(_pv_closed)
                        continue
                    # governance rejected the champion → _validate_and_maybe_close already recorded the
                    # rejected_* outcome; fall through to the cascade so the target still gets a genuine attempt.
                else:
                    _record_attempt(
                        r["row_id"], _pv_prov, "failed_compile", False,
                        "pre-verified champion did not recompile (mode-agnostic) in solve context")

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
                warm_ok, warm_proof_text, warm_tail = _agentic_leaf_warm_solve(
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
            # TRUTHFUL labeling (RCA 2026-06-18): a compiled-but-uncredited proof here is NOT automatically
            # a negative-control leakage reject — derive the real reason from the last provider's validation
            # receipts (banned-axiom / anti-laundering / mnc-leakage / dropped-valid-closure). The old
            # hardcoded `rejected_negative_control` mislabeled all of them and poisoned move-calibration.
            _last_val = (providers_tried[-1].get("contract_validation") if providers_tried else None)
            _failpath_reason, _ = _reject_reason_from_validation(_last_val)
            results.append({
                "name": r["row_id"],
                "target_name": r.get("target_theorem_name"),
                "kind": "c_pool_no_template",
                "outcome": (
                    _failpath_reason
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
    public_payload = _public_sanitize(payload)
    OUT_RESULTS.write_text(json.dumps(public_payload, indent=2))

    # Normalize to typed exits via the canonical module — this is what governance reads.
    te = _load(REPO / "src" / "ztare" / "leanmill" / "typed_exit.py")
    exits = te.normalize_auto_prover_payload(public_payload, source_path=_public_path(OUT_RESULTS), run_id="solver_lane")
    OUT_EXITS.write_text(json.dumps({"schema": "leanmill-solver-lane-typed-exits-v1", "exits": exits}, indent=2))
    # FORECAST RESOLVE (#86): close the learn loop — map each target's kernel outcome → LearningExit, record
    # per-signal Brier rows (INADMISSIBLE deposits nothing), then reweight so the router can earn promotion
    # (advisory→active). No-op when the router is off (_fpriced is {}); best-effort, never breaks the batch.
    try:
        from ztare.leanmill.solver.forecast_router import resolve_batch as _fresolve_batch
        _fresolve_batch(results, _fpriced, ledger_path=OUT_DIR / "forecast_router_brier.jsonl",
                        weights_path=OUT_DIR / "forecast_router_signal_weights.json", run_tag=str(mode))
    except Exception:  # noqa: BLE001
        pass
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
            "results_path": _public_path(OUT_RESULTS), "exits_path": _public_path(OUT_EXITS),
            "dry_run": dry_run}


def _extract_target_signature(source_text: str, name: str) -> str:
    """The target's signature `<binders> : <conclusion>` VERBATIM from source. Robust: takes everything
    between `theorem <name>` and the PROOF `:=` (the last `:=` before the trailing `sorry`), so a `:=`
    inside a hypothesis/binder can't truncate it (the old `(.*?):=` first-match regex did). Feeds
    row['goal'], which the MNC and other governance/compile consumers wrap into a theorem — a wrong
    signature silently weakens those. Falls back to the first-`:=` capture only if there is no source.
    """
    from ztare.leanmill import lean_source as _ls   # single source of truth for Lean parsing
    return _ls.extract_signature(source_text, name)


def _match_closing_probe(cands: "list[tuple]", target_name: str, proof_text: str) -> "tuple":
    """Pick the probe that ACTUALLY produced this closure, from candidate `(path, text)` pairs, for the
    statement-integrity comparand. Returns `(path, text, match_kind)`.

    WHY (2026-06-22, detbank_verify residual): governance must diff the ORIGINAL source against THIS
    closure's probe. A run has several attempts (pool / cold-shot / native) writing probes for the SAME
    target into the SAME scratch, so the comparand must be disambiguated by the stored `proof_text`. Two
    bugs lived in the old inline finder:
      (1) the persisted probe RE-RENDERS the proof with different indentation than the stored proof_text
          (a pool/cold splice reflows `by <tac>` → `:= by\\n  <tac>`), so a RAW substring test MISSED the
          real probe and recency-fell-back to a SIBLING — fixed by also matching WHITESPACE-NORMALIZED.
      (2) when proof_text was present but unmatched, it STILL fell back to the most-recent sibling probe;
          comparing the original source against a different attempt's signature both FALSE-rejects a clean
          closure (sibling altered) and risks FALSE-admit (sibling clean, this closure altered). Now we
          REFUSE the sibling: return `(None, None, 'withheld_unmatched')` so the caller records
          `integrity_unverified` (fail-CLOSED, ratified withheld) instead of a wrong-comparand verdict.
    The recency-fallback survives ONLY for the no-proof_text case (legacy runs that stored none). SOUND:
    this only chooses WHICH probe statement_integrity audits — it never relaxes that audit, so a laundered
    altered signature is still caught on whichever probe is chosen."""
    import re as _re   # LOCAL (module has no top-level `re`) — the missing-name silent-no-op lesson
    from ztare.leanmill.lean_source import has_sorry as _hs
    def _nrm(s: str) -> str:
        return _re.sub(r"\s+", " ", s or "").strip()
    pt = (proof_text or "").strip()
    pt_n = _nrm(pt)
    pt_body_n = _nrm(pt[3:]) if pt.startswith("by ") else ""
    fallback = None
    for p, t in cands:
        body = t.split("#print axioms")[0]
        # COMMENT-ROBUST sorry exclusion + the target must be defined in this probe (canonical check).
        if target_name not in t or _hs(body):
            continue
        t_n = _nrm(t)
        if pt and (pt in t or (pt_n and pt_n in t_n) or (pt_body_n and pt_body_n in t_n)):
            return p, t, "matched"
        if fallback is None:
            fallback = (p, t)
    if not pt and fallback is not None:
        return fallback[0], fallback[1], "fallback_no_prooftext"
    if pt:
        return None, None, "withheld_unmatched"   # refuse the sibling comparand (fail-closed)
    return None, None, "no_candidate"


def _selftest_match_closing_probe() -> None:
    """Probe-comparand selection: reflowed proof pins its OWN probe; sibling never substituted."""
    sig = "theorem T (n : Nat) : n = n"
    own = f"import Mathlib\n{sig} := by\n  rfl\n#print axioms T\n"            # reflowed `rfl`
    sibling_altered = f"import Mathlib\ntheorem T (n : Nat) (h : False) : n = n := by\n  simp\n"  # weakened
    # (1) whitespace-reflowed proof_text still matches its OWN probe, not the altered sibling
    p, t, mk = _match_closing_probe([("/sib", sibling_altered), ("/own", own)], "T", "by rfl")
    assert mk == "matched" and p == "/own", f"reflow match failed: {mk} {p}"
    # (2) proof_text present but unmatched ⇒ WITHHELD, never the sibling (no wrong-comparand verdict)
    p2, t2, mk2 = _match_closing_probe([("/sib", sibling_altered)], "T", "by exact rfl")
    assert mk2 == "withheld_unmatched" and p2 is None, f"sibling refusal failed: {mk2} {p2}"
    # (3) NO proof_text ⇒ legacy recency-fallback still allowed (back-compat)
    p3, t3, mk3 = _match_closing_probe([("/sib", sibling_altered)], "T", "")
    assert mk3 == "fallback_no_prooftext" and p3 == "/sib", f"legacy fallback regressed: {mk3} {p3}"
    print("  [PASS] _match_closing_probe: reflow-match + sibling-refusal + legacy-fallback")


def _reconstruct_recompilable_probe(source_text: str, goal: str, target_name: str, proof_text: str) -> str:
    """Canonically rebuild a SELF-CONTAINED recompilable .lean from (source/goal + proof) when no on-disk
    RobustProbe matched the closure. WHY (2026-06-19): a cert MUST carry recompilable source — it is what the
    cross-run compounding (`family_lemma_library.bank_decl_to_env`) banks into the campaign warm env AND what
    the `compounding_curve` re-derivation telemetry reads; an EMPTY `recompilable_probe`
    silently UN-banks the rung (amnesia persists) AND hides it from the foresight instrument. The on-disk probe
    is transient (overwritten per target) and some paths write none (composite_ratify parents, planner
    sub-lemmas like `iso_lemma2`, native closures whose RobustProbe was clobbered) — so the cert chokepoint is
    the one place to guarantee source. Reuses the ONE canonical splicer (`swap_sorry`/`attach_proof`) +
    `ensure_import_header` — never a re-rolled `head + body`. Returns "" if nothing usable (no proof / no
    statement). NOT a soundness surface: governance already ran (on `probe_txt`); this only fills the cert
    artifact, and any bank of it is re-verified by the kernel (reverted on failure)."""
    import re   # LOCAL (module has no top-level `re`) — the missing-name silent-no-op lesson (2026-06-11)
    from ztare.leanmill.lean_source import swap_sorry, attach_proof, has_sorry
    from ztare.leanmill.solver.agentic_leaf import ensure_import_header
    proof = (proof_text or "").strip()
    if not proof:
        return ""
    # 1) the REAL source with the trailing sorry swapped for the proof (statement VERBATIM — most faithful).
    src = source_text or ""
    if target_name and target_name in src and has_sorry(src):
        spliced = swap_sorry(src, proof)
        if spliced.strip():
            return ensure_import_header(spliced)
    # 2) no source sorry → splice onto the signature. `goal` is the bare `<binders> : <concl>` (no head) or
    #    an already-full `theorem …` (a planner node's goal_text). Give it a `theorem` head iff it lacks one.
    g = (goal or "").strip()
    if not g:
        return ""
    head = g if re.match(r"(?:theorem|lemma|example|def)\b", g) else f"theorem {target_name or '_'} {g}"
    spliced = attach_proof(head, proof)
    return ensure_import_header(spliced) if spliced.strip() else ""


# ── DECOMPOSE-FIRST + decomposition-closure lift (#106, 2026-06-11) ────────────────────────────────────────
# Two real bugs surfaced on RUNG A: (1) `route_and_solve` (the agentic PLANNER — the ONLY path that can close a
# target needing decomposition) ran AFTER a doomed direct cascade that ate the whole wallclock; (2) even when
# the planner CLOSED the parent through composite_ratify's anti-laundering kernel, solve_adhoc returned the
# CASCADE's `r0` outcome (a miss) and buried the closure in `res["iso_route"]`, so the caller reported "not
# solved" — the recursive planner could literally never report a win. These helpers fix both: let the AGENT
# strategize first when the notes carry a decomposition, and lift a kernel-RATIFIED parent closure to SOLVED.
# (`_notes_carry_decomposition` deleted 2026-06-13, agency unlock #132): a lexical `^theorem`×2 + `:= sorry`
# regex used to gate "is this a decomposition blueprint → plan first". It misrouted a blueprint written with
# `lemma` or with inlined proofs into the doomed direct cascade — the harness lexically second-guessing a
# human's explicit blueprint. The route now keys on the PRESENCE of a top-level blueprint and hands it to the
# agentic planner (`route_and_solve`), which is where the agent works with the decomposition. The kernel /
# composite_ratify still govern every closure, so this is pure agency, no soundness surface.


def _lift_decomposition_closure(res: dict, iso_result) -> bool:
    """LIFT a GOVERNED parent closure from `route_and_solve` into `res`'s primary outcome so the caller reports
    SOLVED. `parent_closed` is True ONLY when composite_ratify's anti-laundering kernel (+ the F2 axiom audit)
    passed — the SAME gate the direct path uses — and we ALSO require the actual composite proof text, so a
    phantom `parent_closed` with no proof can never mint a closure. Returns whether it lifted."""
    _sol = (iso_result.get("solution") or {}) if isinstance(iso_result, dict) else {}
    if not _sol.get("parent_closed"):
        return False
    _comp = _sol.get("composite") or {}
    if not (_comp.get("composite_source") or "").strip():   # defense-in-depth: never lift a proof-less closure
        return False
    _rows = res.get("results") or [{}]
    if _rows and isinstance(_rows[0], dict) and _rows[0].get("outcome") != "closed":
        _rows[0]["outcome"] = "closed"
        _rows[0]["closed_by"] = "decomposition"
        _rows[0]["proof_text"] = _comp["composite_source"]
        res["results"] = _rows
        res["closed_by_decomposition"] = True
        return True
    return False


def _decomposition_closed_result(target_name: str, goal: str, iso_result: dict) -> dict:
    """A solve_adhoc result reporting a GOVERNED decomposition closure as SOLVED (for the decompose-FIRST
    pre-pass, where there is no cascade `res` to lift into). Same soundness basis as `_lift_decomposition_closure`."""
    res = {"results": [{"row_id": f"adhoc::{target_name}", "target_theorem_name": target_name, "goal": goal}],
           "iso_route": iso_result, "quarantined_references": [], "closure_certificate": None}
    _lift_decomposition_closure(res, iso_result)
    return res


def _agent_strategy_verdict(goal: str, source_text: str, lean_root, timeout_s: int) -> str:
    """AGENT-AS-STRATEGIST (#106 follow-up, the operator's 'the agent should NOTICE it can't close this directly'
    point) — the up-front strategic fork the iso planner has, framed MECE over TWO ORTHOGONAL dimensions (docs
    §4.3a): **Dim A — TRUTH** (is the goal TRUE → prove, or FALSE → falsify; a clean ME+CE binary) and **Dim B —
    proof-HOW** (SOLVE_DIRECT vs DECOMPOSE, the sub-choice under 'prove'). Returns ONE of
    'SOLVE_DIRECT' | 'DECOMPOSE' | 'FALSIFY'.

    The FALSIFY branch is the AGENCY that lets the agent NOTICE a goal is FALSE (its context/substrate may already
    refute a too-weak formulation) and ELECT to prove ¬G — instead of the harness DETERMINISTICALLY falsifying for
    it (the creep that was tried + reverted 2026-06-23). Goldilocks: the DECISION is the agent's (a move/strategy,
    upstream agency); the kernel only VERIFIES the ¬G it elects (the soundness boundary). Fail-safe: any error /
    parse-miss → 'SOLVE_DIRECT' (the conservative default = the normal direct cascade, byte-parity)."""
    try:
        from ztare.leanmill.solver.agentic_leaf import default_dispatch
        from ztare.leanmill.solver import prompts as _p
        from ztare.common.timeouts import timeout_s as _tb
        prompt = _p.STRATEGY_ASSESSMENT_PROMPT.format(goal=((goal or "").strip() or (source_text or ""))[:1500])
        raw = (default_dispatch(prompt, repo=lean_root, timeout=min(int(timeout_s), _tb("provider_live"))) or "").strip()
        first = raw.upper().splitlines()[0] if raw else ""
        verdict = ("FALSIFY" if "FALSIFY" in first
                   else "DECOMPOSE" if ("DECOMPOSE" in first and "SOLVE_DIRECT" not in first)
                   else "SOLVE_DIRECT")
        print(f"[solve_adhoc] agent strategy assessment → {verdict}", flush=True)
        return verdict
    except Exception:  # noqa: BLE001 — never let the assessment break the solve
        return "SOLVE_DIRECT"


def _should_decompose_first(*, cited_from_cache: bool, iso_route_on: bool, decompose_first_on: bool,
                            below_cap: bool, strategy_assess_on: bool,
                            native_closes: "Callable[[], bool]",
                            agent_recommends: "Callable[[], bool]",
                            mechanical_conjunctive: "Callable[[], bool]" = lambda: False) -> bool:
    """INVARIANT B (agentic-first), made structural + testable (2026-06-21). Decompose-vs-direct is the AGENT's
    call at EVERY node — `is_top`/`notes` DO NOT APPEAR in this signature, so a top-level blueprinted target can
    NOT be force-decomposed (the 9612a8c16 bug, where `(_is_top and bool(notes))` short-circuited the agent-ask
    and gapped a directly-provable nucleus). Order: cheap config gates → the FREE native pre-filter (a
    trivially-closable goal needs no strategist) → the DETERMINISTIC conjunctive split → the agent strategy-ask.
    `native_closes`/`mechanical_conjunctive`/`agent_recommends` are LAZY zero-arg callables so the agent dispatch
    fires ONLY when native misses AND no mechanical split applies. True ⇒ run the planner BEFORE the direct
    cascade. (`is_top` still selects WHICH notes feed an elected decomposition — handled at the call site.)

    `mechanical_conjunctive` (2026-06-25): a TOP-LEVEL `∧` target whose conjuncts are the work-items by
    construction (`derive_conjunctive_dag`) is closed by SPLIT→cite-banked→`composite_ratify` — a MECHANICAL
    assembly (CODE, no discovery), so it routes to the decompose path WITHOUT paying the agent strategy-ask
    (the code-vs-move law + the Goldilocks ordering: cheap deterministic structure before the expensive agent).
    This is why `SOLVE_DIRECT` no longer bypasses the split on a conjunctive target with a banked theory — the
    AMM RCA (2026-06-25): the agent elected SOLVE_DIRECT and ground a monolithic proof while the cheap split sat
    behind it. The split's own audit still gates correctness (a non-composing split falls through to the agent),
    so this only REORDERS which path is tried first; the kernel ratifies every closure regardless."""
    if cited_from_cache or not iso_route_on or not decompose_first_on or not below_cap or not strategy_assess_on:
        return False
    if native_closes():            # #112: free deterministic filter first — trivial goals skip the strategist
        return False
    if mechanical_conjunctive():   # a top-level ∧ with a deterministic split — mechanical assembly, no strategist
        return True
    return agent_recommends()      # the AGENT decides — every node, including top+blueprint


def _selftest_invariant_b_agentic_decompose() -> None:
    """Regression guard for the agentic-first invariant — the foresight that was MISSING when 9612a8c16 shipped
    an incomplete fix behind an overclaiming comment. Asserts the decompose-vs-direct decision depends ONLY on
    (agent verdict + free native filter + config kill-switches), NEVER on is_top/notes. FAILS against the old
    `(_is_top and bool(notes)) or (...agent...)` code. Run: it is called by the module selftest hook below."""
    base = dict(cited_from_cache=False, iso_route_on=True, decompose_first_on=True, below_cap=True,
                strategy_assess_on=True)
    # the nucleus case: agent says SOLVE_DIRECT, native misses, NOT conjunctive → must NOT decompose (used to gap)
    assert _should_decompose_first(**base, native_closes=lambda: False, agent_recommends=lambda: False) is False
    # hard target: agent says DECOMPOSE → decompose
    assert _should_decompose_first(**base, native_closes=lambda: False, agent_recommends=lambda: True) is True
    # MECHANICAL CONJUNCTIVE (2026-06-25 AMM RCA): a top-level ∧ with a deterministic split → decompose-first
    # EVEN WHEN the agent elected SOLVE_DIRECT (agent_recommends=False), and WITHOUT paying the strategy-ask.
    _agent_asked = []
    assert _should_decompose_first(**base, native_closes=lambda: False,
                                   mechanical_conjunctive=lambda: True,
                                   agent_recommends=lambda: _agent_asked.append(1) or False) is True
    assert not _agent_asked, "mechanical conjunctive split ⇒ skip the agent strategy-ask (it's CODE, not discovery)"
    # the free native filter still wins over the mechanical split (a trivially-closable goal skips everything)
    _conj_probed = []
    assert _should_decompose_first(**base, native_closes=lambda: True,
                                   mechanical_conjunctive=lambda: _conj_probed.append(1) or True,
                                   agent_recommends=lambda: True) is False
    assert not _conj_probed, "native pre-filter closes ⇒ the conjunctive-split probe must NOT even fire"
    # free native filter closes → skip decompose AND never dispatch the agent strategy-ask
    _agent_fired = []
    assert _should_decompose_first(**base, native_closes=lambda: True,
                                   agent_recommends=lambda: _agent_fired.append(1) or True) is False
    assert not _agent_fired, "native pre-filter closes ⇒ the agent strategy-ask must NOT fire (wasted dispatch)"
    # config kill-switches each force direct
    for off in ("decompose_first_on", "strategy_assess_on", "iso_route_on", "below_cap"):
        assert _should_decompose_first(**{**base, off: False},
                                       native_closes=lambda: False, agent_recommends=lambda: True) is False, off
    assert _should_decompose_first(**{**base, "cited_from_cache": True},
                                   native_closes=lambda: False, agent_recommends=lambda: True) is False
    print("[selftest] invariant B (agentic decompose-vs-direct, is_top/notes never force it) OK", flush=True)


# Prompt lives in the canonical registry (prompts.py); local name preserved for the call site.
from ztare.leanmill.solver.prompts import POOL_PROMPT_TMPL as _POOL_PROMPT_TMPL


def _governed_pool_preattack(row: dict, source_text: str, goal: str, sub: Path, timeout_s: int,
                             _iso_depth: "int | None" = None) -> "str | None":
    """GOVERNED PROPOSER POOL pre-attack (the isomorphism-surfaced diverse-propose move; default-on,
    `ZTARE_LEANMILL_PROPOSER_POOL=0` reverts to the single leaf). If the FREE native cascade misses, fan a
    DIVERSE portfolio (claude/codex/kimi), EV-champion-select by per-model prior, serial KERNEL-verify in EV
    order, and on a verified champion return the champion PROOF (the body) for `solve_adhoc` to route through
    governance (`solve()` ratifies it via `_validate_and_maybe_close` BEFORE re-deriving — the fix for the pool-
    closure-drop where a spliced-into-the-file champion was ignored by the DAG/cascade). None on miss / disabled /
    native-already-closes. PURE proposer: the kernel still ratifies every closure downstream (no soundness surface); the
    only price is k model dispatches, gated on a native-miss so trivial goals never pay it (Haldane/Graham)."""
    from ztare.leanmill.solver.proposer_pool import pool_enabled
    if not pool_enabled():   # ONE source of truth for the default (was a raw env-check here that DUPLICATED
        return None          # — and contradicted — proposer_pool.pool_enabled's default; split-brain, 2026-06-20)
    # DEPTH GATE (2026-06-20, operator: "is our pool naive?" — the internals aren't, the TRIGGER was). The pool
    # is for SELF-CONTAINED goals where DIVERSE independent proposers close in parallel (miniF2F-shape). On a
    # DECOMPOSED sub-goal (depth>0) the productive path is sequential decompose→conjecture→bank; firing k models
    # per deep node just burns budget (MEASURED on P1: ~20/21 fail across the theory-building chain, ~100+
    # dispatches for ONE close). Suppress on depth>0 so that budget flows to the conjecture/decompose engine.
    # `ZTARE_LEANMILL_PROPOSER_POOL_MAX_DEPTH` (default 0 = top target only) tunes the ceiling.
    _max_d = int(os.environ.get("ZTARE_LEANMILL_PROPOSER_POOL_MAX_DEPTH", "0") or 0)
    if _iso_depth is not None and int(_iso_depth) > _max_d:
        return None
    target_name = str(row.get("target_theorem_name") or row.get("row_id") or "pool")
    try:
        # cost discipline: a goal the FREE native cascade closes needs no portfolio (don't burn k models).
        if os.environ.get("ZTARE_LEANMILL_POOL_NATIVE_GATE", "1") != "0":
            with _phase_timer("native", target=target_name):
                ok_nh, _, _ = _native_hammer_probe(row, sub, min(int(timeout_s), 120))
            if ok_nh:
                return None
        from ztare.leanmill.solver.proposer_pool import attack_node, model_priors
        tcap = min(int(timeout_s), 180)
        def _verify(prop):
            # CAMPAIGN-AWARE verify (2026-06-20 fix): the prior `_compile_probe` here was campaign-BLIND, so the
            # pool's proposals failed `unknown identifier` on every namespaced campaign/P1 rung (the whole pool
            # was dead weight on P1). Route through the shared seam that uses the theory env + namespace when a
            # campaign substrate is set — the SAME path the warm leaf closes through.
            return _campaign_aware_proof_compiles(source_text, prop.proof_text, sub, tcap)
        out = attack_node(target_name, _POOL_PROMPT_TMPL.format(goal=goal), _verify,
                          repo=str(sub), timeout=tcap, priors=model_priors())
        # PER-MODEL ATTRIBUTION (the missing learning leg): record each KERNEL-VERIFIED pool proposal as a
        # per-MODEL attempt, so `calibrate_by_model` builds REAL diverse-model priors (currently the DB has no
        # kimi/gemini head-to-head — only claude warm/cold) and the pool-vs-single LIFT accrues for FREE in any
        # real run instead of needing a token-burning one-off A/B. Only the TRIED set (verify_order, ≤ the
        # Haldane cap) has a known outcome — the champion (last, iff closed) = closed, the rest verified-and-
        # failed; un-tried proposals stay UNRECORDED (honest: never attempted ⇒ no verdict). Reuses the canonical
        # `_record_attempt` (carrier-liveness + run_tag handled there); governance still ratifies downstream.
        try:
            _n = len(out.verified_order)
            for _i, _m in enumerate(out.verified_order):
                _is_closer = bool(out.closed and _i == _n - 1)
                # CONSERVATION (2026-06-22): the pool VERIFY only proves the champion COMPILES sorry-free — it is
                # NOT a ratified closure (governance/MNC/axiom-audit have not run). Recording "closed" here was the
                # misleading telemetry row that made the target read closed-NOT-ratified. Record the honest per-
                # model signal (`compiled_unratified`); the REAL closure outcome (ratified | rejected_*) is recorded
                # by solve()'s _validate_and_maybe_close once the champion is routed through governance below.
                _record_attempt(target_name, _m, "compiled_unratified" if _is_closer else "failed",
                                compile_ok=_is_closer, notes="governed_pool", move="proposer_pool")
        except Exception:  # noqa: BLE001 — telemetry is best-effort; never block the solve
            pass
        if out.closed and out.committed:
            # ROOT-CAUSE FIX (2026-06-22): RETURN THE CHAMPION PROOF, not a spliced source. The old path spliced the
            # proof into source_text and relied on solve() to "re-verify + govern + bank" — but solve()'s DAG/cascade
            # builds from the GOAL signature and RE-DERIVES (native_hammer's compile_stub even strips a no-sorry
            # source back to `:= by`), so it never compiled the spliced source-as-given. A VALID champion was thus
            # silently dropped and the target read closed-NOT-ratified (pool telemetry said "closed", governance
            # never ran on it). Now solve_adhoc puts the champion in row["_preverified_proof"] and solve() routes it
            # through the SAME governance every move uses (_validate_and_maybe_close) BEFORE re-deriving: it ratifies
            # (real closure + cert) or records a proper rejected_* — never a silent drop. No new soundness surface.
            _champion = (out.committed.proof_text or "").strip()
            if _champion and "sorry" not in _champion:
                print(f"[solve_adhoc] GOVERNED POOL champion for '{row.get('target_theorem_name')}' via "
                      f"{out.committed.model} (EV order {out.verified_order}; cross-model agreement "
                      f"{out.agreement}) — routing to governance for ratification", flush=True)
                return _champion
    except Exception:  # noqa: BLE001 — best-effort; any failure → the normal single-leaf path (never blocks a solve)
        return None
    return None


def solve_adhoc(target_name: str, source_text: str, goal: str, *,
                provider: str | None = None, timeout_s: int = 500,
                mode: str = "cascade", substrate: "Path | None" = None,
                notes: "str | None" = None, _iso_depth: "int | None" = None,
                preverified_proof: "str | None" = None,
                preverified_provider: "str | None" = None) -> dict:
    """Ad-hoc-target entry — run a ONE-OFF lemma through the FULL governed pipeline (the gap that
    bred the bespoke harnesses). `source_text` is a complete .lean file whose `target_name`
    declaration ends in `sorry`; it is written into `substrate`, wrapped in the reference-leakage
    gate, run via `solve(rows=[…], skip_cue_check=True)` (so it flows through contract → moves →
    MNC → governance → receipt), and on a kernel-clean closure its invented helpers are banked to
    the family library (compounding). No re-rolled iteration — this IS the worker pipeline.
    `notes` (optional, #81) = a human / research-director BLUEPRINT for this target — threaded into the
    recursive planner (route_and_solve → attack) as decomposition guidance when the goal does NOT close
    directly. Advisory (the kernel still audits every lemma). This is the entry that lets an ALREADY-
    formalized Lean target (no autoformalize step) also carry blueprint notes into the planner."""
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
    try:
        preflight_moves_alive(sub)      # standing positive control (cached per root); loud if a move is dead
    except Exception:
        pass
    _run_start = datetime.now(timezone.utc).isoformat()  # scope the ratification stamp to THIS run
    from ztare.leanmill.solver.agentic_leaf import probe_dir   # shared scratch dir (probes out of the project root)
    src = probe_dir(sub) / f"AdHoc_{target_name}.lean"
    src.write_text(source_text, encoding="utf-8")
    if not goal:  # derive the goal signature from source ROBUSTLY (verbatim; not the brittle first-`:=`)
        goal = _extract_target_signature(source_text, target_name) or target_name
    # FORMALIZATION-QUALITY lint (2026-06-23 iso_lemma1 RCA): a bare order instance subsumed by an Order class on
    # the same type (`[LE α]` under `[Preorder α]`) is an instance DIAMOND that makes the statement UNPROVABLE —
    # and the symptom (failed_compile / a spurious STATEMENT-FALSE) hides the real cause. Surface it LOUDLY up
    # front so a malformed sub-lemma is diagnosed before the solve burns on it. Advisory (never blocks); the cure
    # is re-formalizing without the redundant binder. The planner's `iso_lemma1` carried `[LE α] [Preorder α]`.
    _redundant_instances: "list[str]" = []
    try:
        from ztare.leanmill.lean_source import redundant_subsumed_instances as _rsi
        _redundant_instances = _rsi(source_text, target_name)
        if _redundant_instances:
            print(f"[solve_adhoc][FORMALIZATION-LINT] '{target_name}' has REDUNDANT subsumed instance(s): "
                  f"{_redundant_instances} — an instance diamond that typically makes the statement UNPROVABLE "
                  f"(2026-06-23 iso_lemma1 RCA). Re-formalize WITHOUT the bare binder.", flush=True)
    except Exception:  # noqa: BLE001 — advisory only; never block a solve
        _redundant_instances = []
    row = {"row_id": f"adhoc::{target_name}", "target_theorem_name": target_name,
           "source_file": str(src), "sorried_file": str(src), "goal": goal,
           "rejection_reasons": ["no_positive_family_template"], "target_resolution_ok": True}
    prov = provider or _policy_model()
    # EXTERNALLY-PRODUCED PROOF (operator hand-off / recovered artifact): route a COMPLETE compiling proof
    # STRAIGHT to governance via the SAME `_preverified_proof` seam the proposer-pool champion uses — kernel
    # compile + MNC + axiom audit + statement_integrity + closure cert, with NO re-derivation. The proof is
    # spliced into `source_text` (swap_sorry) inside solve(), so a theory-building target's bespoke helpers
    # (not in Mathlib) stay in scope. NO new soundness surface — identical to every move's
    # _validate_against_contract; a bogus/sorried proof fails compile or governance and falls through.
    _external_pv = bool((preverified_proof or "").strip())
    if _external_pv:
        row["_preverified_proof"] = preverified_proof.strip()
        row["_preverified_provider"] = preverified_provider or "external"
    # (b) PRE-ATTACK LIBRARY CHECK (amnesia RCA 2026-06-19; SINGLE-DOOR routing 2026-06-24): BEFORE the native
    # pre-filter / planner re-derive a lemma we ALREADY proved, consult the proof_cache (Expr-hash keyed, default-on);
    # a hit hands the banked proof to the ONE preverified-proof governance seam (`_pvp` in solve()) — the SAME door
    # the proposer pool and external proofs use — which splices into the FULL source (defs in scope), compiles
    # campaign-aware, and runs the complete kernel+MNC+axiom governance + banking. NO bespoke splice/verify here (the
    # class of bug that put us here: a private re-verify against the BARE goal had the inlined defs out of scope →
    # `unknown identifier` → silent cite skip → re-derive even on a HIT). ZTARE_LEANMILL_PROOF_CACHE_PREATTACK=0
    # reverts. `_cited_from_cache=True` is the existing "have a candidate, ratify it first, don't re-derive" signal
    # the pool sets; an explicit external proof skips cache/pool/decompose-first → straight to the same `_pvp` door.
    _cited_from_cache = _external_pv
    # CANONICAL CACHE KEY (2026-06-24): the kernel `Expr.hash` of the target's de-Bruijn TYPE — α-/∀-fronting-
    # invariant where the text key is not (the multi-decl define_then_state probe keyed on its leading def's `:=`,
    # and `(h):Q` vs `:∀h,Q` never matched). Computed ONCE here from the warm REPL (a byproduct of the verify we
    # already run) and REUSED at the deposit below so deposit-key == lookup-key for the SAME statement. None ⇒
    # the text key still works (graceful degrade). SOUND regardless: every cache hit is re-verified in-context.
    _canon_key = None
    try:
        from ztare.formal.repl_compile import canonical_type_hash_via_repl as _cth
        _canon_key = _cth(source_text, target_name, sub)
    except Exception:  # noqa: BLE001 — best-effort; text key is the fallback
        _canon_key = None
    if (not _cited_from_cache
            and os.environ.get("ZTARE_LEANMILL_PROOF_CACHE_PREATTACK", "1") != "0"
            and os.environ.get("ZTARE_PROOF_CACHE", "1") != "0"):
        try:
            from ztare.leanmill.solver.proof_cache import ProofCache as _PCpre
            _banked = _PCpre(OUT_DIR / "solver_lane_proof_cache.jsonl").get(goal, key=_canon_key)
            if _banked:
                # SINGLE DOOR (2026-06-24): hand the banked proof to the ONE preverified-proof governance seam
                # (`_pvp` below — the SAME door the proposer pool and external proofs use), NOT a bespoke splice +
                # re-verify here. That door splices into the FULL source (defs in scope), compiles campaign-aware,
                # and runs the complete kernel + MNC + axiom governance + banking. Routing through it means the
                # cache cite can never DRIFT from the pool/external path, and the class of bug it just had — the
                # re-verify ran against the BARE goal (inlined defs out of scope → `unknown identifier` → silent cite
                # skip → 526s re-derive even on a cache HIT) — cannot recur, because there is only one verify site.
                # `_cited_from_cache` skips the pool + decompose-first; `solve()`'s `_pvp` block does the rest.
                row["_preverified_proof"] = _banked
                row["_preverified_provider"] = "proof_cache"
                _cited_from_cache = True
                print(f"[solve_adhoc] CITED banked rung from proof_cache → preverified-proof governance door "
                      f"(full-context verify, single seam) for '{target_name}'", flush=True)
        except Exception:  # noqa: BLE001 — best-effort; any failure → normal derive path (never blocks a solve)
            _cited_from_cache = False
    # GOVERNED PROPOSER POOL pre-attack (isomorphism-surfaced diverse-propose; default-on). After the cache
    # cite, before the single-leaf native/planner attack: fan a diverse portfolio → EV champion → serial kernel
    # verify → splice the verified champion so solve() RE-verifies + governs + banks it (same splice as the cache).
    if not _cited_from_cache:
        with _phase_timer("pool", target=target_name):
            _pooled = _governed_pool_preattack(row, source_text, goal, sub, timeout_s, _iso_depth=_iso_depth)
        if _pooled:
            # The pool returns a verified champion PROOF (not a spliced source). Hand it to solve() via the row;
            # solve() ratifies it through the SAME governance every move uses (_validate_and_maybe_close) BEFORE
            # re-deriving. This is the fix for the pool-closure-drop: a champion merely spliced into the file was
            # ignored by the DAG/cascade (which re-derive from the goal), so a valid proof was silently discarded.
            row["_preverified_proof"] = _pooled
            row["_preverified_provider"] = "proposer_pool"
            _cited_from_cache = True   # have a candidate → skip decompose-first; solve() ratifies it first
    _prev_refchk = os.environ.get("ZTARE_CLOSURE_REF_CHECK")
    os.environ["ZTARE_CLOSURE_REF_CHECK"] = "1"  # capability entry: record the in-repo-ref receipt
    # Hard one-off targets may need DEEP recursive decomposition (conjecture-DAG spawning + banking
    # sub-lemmas). The batch default (12 total moves) starves that, so raise it for the ad-hoc entry
    # unless the caller already pinned ZTARE_DAG_MAX_MOVES. This is the "handle any size" budget.
    _prev_maxmoves = os.environ.get("ZTARE_DAG_MAX_MOVES")
    if _prev_maxmoves is None:
        os.environ["ZTARE_DAG_MAX_MOVES"] = "60"
    # DECOMPOSE-FIRST (agent-as-strategist, #106): a target whose notes carry a decomposition blueprint needs
    # the PLANNER, not the doomed direct cascade — run route_and_solve FIRST. The agent generates + kernel-audits
    # the decomposition and proves the sub-lemmas; if it CLOSES the parent (composite ratified) report SOLVED and
    # SKIP the cascade; else the cascade runs as the FALLBACK (and we reuse this result, no double-dispatch).
    # Gated: ZTARE_LEANMILL_DECOMPOSE_FIRST (default-on) ∧ ISO_ROUTE on ∧ notes carry a formal decomposition.
    # B — the agentic-first INVARIANT (#74/#106, the operator's "the agent orchestrates SOLVING, not just the
    # seeded top"): the agent decides decompose-vs-direct at EVERY node, not only a top target with a human
    # blueprint. `_is_top` no longer GATES — it only chooses WHICH notes feed the decomposition (the seeded
    # blueprint at the top; a FRESH decomposition on a sub-lemma's OWN goal below — never re-decompose a sub-lemma
    # on the PARENT's blueprint, the reason this was top-level-only). `_below_cap` keeps the agent strategy-ask from
    # firing where route_and_solve can't recurse anyway (the depth ceiling) — no wasted dispatch.
    # depth = the THREADED `_iso_depth` (#127, 2026-06-13) — NOT the env var, which is no longer mutated
    # during recursion (it stays "0" at every depth, which would make `_is_top` permanently True and inject
    # the PARENT's blueprint into every sub-lemma). Env is the read-only TOP-LEVEL override (`_iso_depth is None`).
    _d_now = int(_iso_depth) if _iso_depth is not None else int(os.environ.get("ZTARE_ISO_DEPTH", "0") or 0)
    _is_top = _d_now == 0
    _below_cap = _d_now < int(os.environ.get("ZTARE_ISO_MAX_DEPTH", "2") or 2)

    def _native_prefilter_closes() -> bool:
        """#112 (B-ordering): run the FREE deterministic cascade BEFORE paying the agent strategy-ask.
        A trivially-closable goal needs neither a strategist nor a planner — skip both and let the
        canonical cascade in solve() mint the closure through full governance (the duplicate native
        SUCCESS costs ~seconds; a native FAILURE is memoized by the in-run dedup, so the cascade's
        re-attempt is a 0.01s skip — the pre-filter is near-free in the common case). DEFAULT-ON;
        ZTARE_LEANMILL_NATIVE_PREFILTER=0 reverts to ask-first."""
        if os.environ.get("ZTARE_LEANMILL_NATIVE_PREFILTER", "1") == "0":
            return False
        try:
            with _phase_timer("native", target=target_name):
                ok_nh, _tac, _tail = _native_hammer_probe(row, sub, min(int(timeout_s), 300))
            if ok_nh:
                print("[solve_adhoc] native pre-filter CLOSED the goal — skipping the agent "
                      "strategy-ask + planner (the cascade mints it through full governance)", flush=True)
            return bool(ok_nh)
        except Exception:  # noqa: BLE001 — a pre-filter error must never block the strategy path
            return False

    # AGENCY FIX (2026-06-21, invariant B made REAL): the top+blueprint case USED to decompose-first
    # UNCONDITIONALLY — `(_is_top and bool(notes))` short-circuited the native pre-filter AND the agent
    # strategy-ask, so a top target with ANY notes was force-decomposed even when it is a clean DIRECT proof
    # (the substrate-B cyclic-holonomy nucleus: a ~6-line telescoping proof got fragmented into iso_lemmas
    # because a blueprint was attached). That is determinism-creep into the agent's lane — decompose-vs-direct
    # is an AGENCY call, not a soundness boundary — AND it CONTRADICTED this block's own comment ("`_is_top` no
    # longer GATES; the agent decides at EVERY node"). The fix: the agent decides at the top too. `_is_top` now
    # ONLY chooses WHICH notes feed a decomposition that the agent actually elects (the `notes if _is_top` arg
    # below) — it no longer FORCES one. A genuinely-hard blueprinted target still decomposes (the agent, asked
    # "can you close this directly?", says DECOMPOSE on a hard goal); a trivially-closable one is taken by the
    # FREE native pre-filter; a clean direct proof goes straight to the cascade. ZTARE_LEANMILL_DECOMPOSE_FIRST=0
    # and ZTARE_LEANMILL_AGENT_STRATEGY_ASSESS=0 still revert. (Soundness unchanged — this only reorders which
    # PROVING path is tried first; the kernel ratifies every closure regardless.)
    # The agent's strategy verdict — computed ONCE, lazily (the `_should_decompose_first` ordering fires it ONLY
    # when config-on AND the free native pre-filter MISSES), then SHARED by the decompose decision (Dim B) and the
    # FALSIFY route (Dim A) below — so there is exactly one strategist dispatch, never two.
    _strategy: "dict[str, str]" = {}
    def _strategy_verdict() -> str:
        if "v" not in _strategy:
            _strategy["v"] = _agent_strategy_verdict(goal, source_text, sub, timeout_s)
        return _strategy["v"]
    def _mechanical_conjunctive_available() -> bool:
        """A TOP-LEVEL `∧` target with a deterministic conjunct split available (`derive_conjunctive_dag`) →
        route to the split path (mechanical assembly: CODE, no discovery), NOT the agent's SOLVE_DIRECT grind.
        Cheap (pure string ops, no Lean); the split's audit inside route_and_solve gates correctness, so a
        non-conjunctive / non-composing goal falls through to the agent. ZTARE_LEANMILL_DETERMINISTIC_CONJ_DAG=0
        reverts (then this returns False and the agent strategy-ask decides as before)."""
        if os.environ.get("ZTARE_LEANMILL_DETERMINISTIC_CONJ_DAG", "1") == "0":
            return False
        try:
            from ztare.leanmill.solver.isomorphism_decompose import derive_conjunctive_dag as _dcd
            avail = _dcd(source_text or "", target_name) is not None
            if avail:
                print("[solve_adhoc] top-level ∧ target → deterministic conjunctive split available; routing to "
                      "split→cite→composite (mechanical assembly, skipping the SOLVE_DIRECT grind)", flush=True)
            return avail
        except Exception:  # noqa: BLE001 — availability probe is advisory; never block the strategy path
            return False
    _decomp_first = _should_decompose_first(
        cited_from_cache=_cited_from_cache,   # a pre-attack (cache cite OR governed pool) already spliced a proof
        iso_route_on=os.environ.get("ZTARE_LEANMILL_ISO_ROUTE", "1") != "0",
        decompose_first_on=os.environ.get("ZTARE_LEANMILL_DECOMPOSE_FIRST", "1") != "0",
        below_cap=_below_cap,
        strategy_assess_on=os.environ.get("ZTARE_LEANMILL_AGENT_STRATEGY_ASSESS", "1") != "0",
        native_closes=_native_prefilter_closes,                                                # #112: FREE filter FIRST
        mechanical_conjunctive=_mechanical_conjunctive_available,   # 2026-06-25: code-vs-move — split before agent
        agent_recommends=lambda: _strategy_verdict() == "DECOMPOSE")    # Dim B (proof-HOW): the AGENT decides
    _iso_pre = None
    try:
        # FALSIFY route — Dim A (TRUTH), AGENCY not determinism. The agent ELECTED to prove ¬GOAL (it judged the
        # goal FALSE — e.g. its context/substrate refutes a too-weak formulation). Fires ONLY when the agent was
        # actually asked (`_strategy` populated ⇒ config-on + native missed) AND chose FALSIFY. Run the falsify
        # move; a kernel-CONFIRMED ¬G is a real refutation → emit outcome="falsified" so the caller's
        # `_solve_refutation` drives the governed reformulation re-entry (the agent STRENGTHENS + re-attacks). NOT
        # confirmed ⇒ the agent mis-judged (true-but-hard) → fall through to the normal cascade. Sound + non-
        # spurious: ONLY a kernel ¬G refutes (the v7-trap can't fire). Inside `try` so the `finally` env-restore
        # runs on the early return. The DECISION is the agent's; the kernel is the only deterministic part.
        if not _decomp_first and _strategy.get("v") == "FALSIFY":
            try:
                from ztare.leanmill.solver.conjecture import verify_statement_false_claim as _vsf
                from ztare.common.timeouts import timeout_s as _tbf
                _cf, _wf, _bf = _vsf(target_name, source_text, goal, sub, _tbf("leaf_verify"))
                if _cf:
                    print("[solve_adhoc] agent elected FALSIFY → kernel-confirmed ¬G → routing to governed "
                          "reformulation (strengthen + re-attack)", flush=True)
                    _fres = {"results": [{"row_id": f"adhoc::{target_name}", "target_theorem_name": target_name,
                                          "goal": goal, "outcome": "falsified",
                                          "falsifier": (_bf or _wf or "kernel-checked ¬G (agent-elected FALSIFY)")[:600]}],
                             "statement_false_verified": True, "quarantined_references": [],
                             "closure_certificate": None}
                    if _redundant_instances:
                        _fres["redundant_instances"] = _redundant_instances
                    return _fres
                print("[solve_adhoc] agent elected FALSIFY but ¬G NOT kernel-confirmed → true-but-hard; "
                      "proceeding to prove", flush=True)
            except Exception:  # noqa: BLE001 — falsify-route error ⇒ normal cascade (never block a solve)
                pass
        if _decomp_first:
            try:
                from ztare.leanmill.solver.isomorphism_decompose import route_and_solve as _ras_pre
                print(f"[solve_adhoc] decompose-first ({'top+blueprint' if _is_top else 'agent-judged (sub-lemma, fresh)'}) → planner BEFORE the direct cascade", flush=True)
                _iso_pre = _ras_pre(source_text, target_name, goal, lean_root=sub,
                                    timeout_s=timeout_s, substrate=sub, notes=(notes if _is_top else None),
                                    _depth=_iso_depth)
                if ((_iso_pre.get("solution") or {}).get("parent_closed")):
                    return _decomposition_closed_result(target_name, goal, _iso_pre)
            except Exception as _e:  # noqa: BLE001 — best-effort; fall through to the direct cascade
                _iso_pre = {"error": repr(_e)[:160]}
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
    r0 = primary_result(res)   # live ref + fail-loud on missing "results" (the 2026-06-03 flywheel bug)
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
            cand = sorted([p for r in _roots for p in probe_dir(r).glob("RobustProbe_*.lean")]
                          + [probe_dir(r) / f"AdHoc_{target_name}.lean" for r in _roots],
                          key=lambda p: p.stat().st_mtime if p.exists() else 0, reverse=True)
            # Pick the probe that ACTUALLY produced this closure: its body must contain the winning
            # `proof_text`. Falls back to "most-recent sorry-free probe defining the target" only if
            # no body match (older runs / proof_text unavailable). Without the proof_text match the
            # governance organs could run on the WRONG probe (claude vs codex, or a non-closing one).
            # Pick the probe that ACTUALLY produced this closure (canonical helper — testable, and the
            # comment-robust sorry/target checks + whitespace-normalized proof match + sibling-refusal live
            # in ONE place, not inline). _cand_pairs reads each candidate ONCE; the helper disambiguates by
            # the stored proof_text and never substitutes a sibling attempt's probe (the detbank_verify fix).
            _pt = (r0.get("proof_text") or "").strip()
            _cand_pairs = [(p, p.read_text(encoding="utf-8", errors="replace")) for p in cand if p.exists()]
            probe_path, probe_txt, _probe_mk = _match_closing_probe(_cand_pairs, target_name, _pt)
            gov["probe_match"] = _probe_mk
            # The kernel must recompile the probe against the root it ACTUALLY lives in — a cold-route
            # probe is in ztare_proofs (v4.30), not the sidecar (v4.27); recompiling it against the
            # wrong toolchain would spuriously fail (e.g. a v4.30-only lemma → "unknown constant").
            _probe_root = probe_path.parent if probe_path is not None else sub
            gov["verify_root"] = _public_path(_probe_root)
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
                    # FAIL-CLOSED on a kernel crash (2026-06-13 audit): the anti-laundering + statement-
                    # integrity organs did NOT run on this found probe, so the closure is COMPILED but
                    # INTEGRITY-UNVERIFIED (cert/notes layers must not ratify it as integrity-clean — same
                    # signal as the no-probe branch). The proof itself stays kernel-valid (leaf pre-closure).
                    gov["governance_kernel"] = {"passed": None, "error": repr(_e)[:120]}
                    gov["integrity_unverified"] = True
                gov["axiom_allowlist"] = "gated by leaf verify_lean_proof (#print axioms) pre-closure"
                # POST-CLOSURE ROBUSTNESS + DIFFERENTIAL RE-VERIFICATION (DEFAULT-ON 2026-06-12; =0 reverts;
                # was opt-in advisory-only). The battery annotates the kernel-verified closure with
                # strengthen/weaken signals (surveyability + load-bearing-hypothesis perturbation —
                # those stay ADVISORY: a fragile proof is still kernel-TRUE). The 2026-06-12 iso-run
                # transport adds the CONCLUSION-DISCRIMINATION leg, and that ONE verdict is a BLOCKER:
                # if the same proof body ALSO closes the NEGATED conclusion in the same context, the
                # hypotheses are contradictory — the closure is kernel-true but VACUOUS (the shape
                # laundering hides in). Sound to reject on: G and ¬G both closing ⇒ inconsistent
                # context, never a genuine win. Cost: ~1-2 warm compiles, only on closures.
                if os.environ.get("ZTARE_PROOF_MARGIN", "1") != "0":
                    try:
                        from ztare.leanmill.solver.proof_margin_of_safety import proof_margin_of_safety
                        from ztare.common.timeouts import timeout_s as _budget   # central factory (byte-parity: margin_probe defaults to the prior 90)
                        gov["margin_of_safety"] = proof_margin_of_safety(
                            probe_txt, target_name, _probe_root, timeout_s=_budget("margin_probe"), deep=True,
                            original_source=source_text)
                        _disc = (((gov["margin_of_safety"] or {}).get("tests") or {})
                                 .get("conclusion_discrimination") or {})
                        if (_disc.get("detail") or {}).get("differential") == "zero":
                            blockers.append("margin:zero_differential_vacuous_context")
                    except Exception as _e:  # noqa: BLE001 — a battery error never breaks governance (fail-open
                        gov["margin_of_safety"] = {"error": repr(_e)[:120]}   # on ORGAN crash, per the gov contract)
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
                # OBSERVABILITY (2026-06-21): surface WHICH organ blocked + the verify root, so a governance
                # rejection is self-explaining in the log instead of an opaque `rejected_governance` that forces
                # a multi-source forensic scour (the operator's "the kernel must be improved in terms of
                # observability"). A false-reject (e.g. a wrong lean_root breaking the oracle) names itself here.
                try:
                    _siv = (gov.get("statement_integrity") or {})
                    print(f"[governance] REJECTED {target_name}: blockers={blockers} | "
                          f"verify_root={gov.get('verify_root')} | si_ok={_siv.get('ok')} "
                          f"si_viol={(_siv.get('violations') or [])[:2]}", flush=True)
                except Exception:  # noqa: BLE001 — a logging helper never breaks governance
                    pass
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
        # INTEGRITY-UNVERIFIED ⇒ NOT ratified (v3 RCA 2026-06-12): when no probe was found the organs
        # SKIPPED, yet this stamped ratified=1 — fail-OPEN at the trust boundary, so an unauditable
        # closure (empty cert, no recompilable probe) fed the learning layer as a governed win while
        # the notes layer reported "none closed". `outcome` stays `closed` (the kernel DID verify and
        # the leaf's axiom gate ran); only the GOVERNED-win credit is withheld. With the checker now
        # persisting every verified probe, integrity_unverified marks an apparatus anomaly, not a norm.
        try:
            _gov_verified = not (res.get("governance") or {}).get("integrity_unverified")
            n_stamped = _record_governance_verdict(
                row["row_id"], ratified=(r0.get("outcome") == "closed" and _gov_verified),
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
            _probe_reconstructed = False
            # Belt-and-suspenders (2026-06-19): a closure whose on-disk RobustProbe was overwritten / never
            # written (composite_ratify parents, planner sub-lemmas like `iso_lemma2`) would record an EMPTY
            # recompilable_probe — which silently UN-banks the rung from the library-as-environment compounding
            # AND hides it from the compounding-health re-derivation metric. Reconstruct canonically from
            # source/goal + proof so a closure ALWAYS carries recompilable source. Not a soundness surface
            # (governance already ran on probe_txt; a bank of this is kernel-re-verified, reverted on failure).
            if r0.get("outcome") == "closed" and not _probe_full.strip():
                _rc = _reconstruct_recompilable_probe(source_text, goal, target_name, r0.get("proof_text") or "")
                if _rc.strip():
                    _probe_full = _rc
                    _probe_reconstructed = True
            _closure_lean = None
            if r0.get("outcome") == "closed" and _probe_full.strip():
                # (a) recompilable in place, in the root the probe ACTUALLY lives in (cold-route → ztare_proofs).
                _cdir = (locals().get("_probe_root") or sub) / "closures"
                _cdir.mkdir(parents=True, exist_ok=True)
                _closure_lean = _cdir / f"{target_name}.lean"
                _closure_lean.write_text(_probe_full, encoding="utf-8")
            import hashlib as _hl   # local: best-effort block (the NameError-silent-no-op lesson)
            _cert = {
                "ts": _run_start,
                "target": target_name,
                # Planner DAG node names are GENERIC (iso_lemma1 …) and collide ACROSS runs — the goal
                # hash is the stable statement identity (v3 RCA: three same-named certs, three statements).
                "goal_sha": _hl.sha256((goal or "").encode()).hexdigest()[:16],
                "outcome": r0.get("outcome"),
                "provider": r0.get("provider") or r0.get("winner"),
                "proof_text": r0.get("proof_text") or "",
                "recompilable_probe": _probe_full,        # full self-contained .lean, portable
                # True ⇒ rebuilt from source/goal+proof (no on-disk probe matched), NOT the byte-exact compiled
                # artifact — honest flag so a re-`#print axioms` consumer knows; banking re-verifies regardless.
                "recompilable_probe_reconstructed": _probe_reconstructed,
                "closure_lean": _public_path(_closure_lean) if _closure_lean else None,  # in-substrate copy
                "governance": _public_sanitize(res.get("governance")),
                "matched_negative_control": r0.get("matched_negative_control"),
                "substrate": _public_path(sub),
                "checker": active_proof_checker_name(),    # WHICH checker ratified — auditable across substrates
                "wall_s": r0.get("provider_wallclock_s"),
                # INFER-VIA-USE compounding provenance (2026-06-24): True ⇒ the proof-cache/pool pre-attack SERVED
                # this closure (cited a banked rung, re-verified in-context) instead of re-deriving — the direct,
                # benchmark-free attribution of a compounding win, read later by `compounding_curve.cost_to_close_trend`.
                "cited_from_cache": bool(_cited_from_cache),
            }
            # (b) tracked, durable, append-only audit ledger (survives even if the substrate is wiped).
            ADHOC_CLOSURE_CERTIFICATES.parent.mkdir(parents=True, exist_ok=True)
            with ADHOC_CLOSURE_CERTIFICATES.open("a", encoding="utf-8") as _cf:
                _cf.write(json.dumps(_public_sanitize(_cert)) + "\n")
            res["closure_certificate"] = _public_path(ADHOC_CLOSURE_CERTIFICATES)
            res["closure_lean"] = _public_path(_closure_lean) if _closure_lean else None
        except Exception as _e:
            res["closure_certificate_error"] = repr(_e)[:120]
    # PROOF-CACHE DEPOSIT (2026-06-24, the cross-run reuse fix): EVERY clean adhoc closure banks its proof to the
    # canonical proof_cache, keyed by the canonical `Expr.hash` (`_canon_key`) so a FUTURE run's pre-attack lookup
    # CITES it instead of re-deriving. THE single deposit door — native-pre-filter / warm-direct / decompose all
    # flow through here, where the scattered dag-search-only deposit missed them (the banked APR lemmas were in the
    # cert ledger but NEVER in the proof_cache → zero reuse). Dual-indexed (Expr key + text key); re-verified on use.
    if (r0.get("outcome") == "closed" and (r0.get("proof_text") or "").strip()
            and os.environ.get("ZTARE_PROOF_CACHE", "1") != "0"):
        try:
            from ztare.leanmill.solver.proof_cache import ProofCache as _PCdep
            _PCdep(OUT_DIR / "solver_lane_proof_cache.jsonl").put(
                goal, r0.get("proof_text") or "", source=f"adhoc_closure:{target_name}",
                key=locals().get("_canon_key"))
        except Exception:  # noqa: BLE001 — banking is best-effort; never fail a closure on a cache write
            pass
    # compounding: on a clean closure, bank the proof's invented helpers for siblings. Bank from the
    # closure's PROOF_TEXT (the leaf proves in its own probe file; the original `src` keeps its
    # `sorry`, so re-reading src banked nothing — cold-review-adjacent catch 2026-06-03).
    if r0.get("outcome") == "closed" and (r0.get("proof_text") or "").strip():
        fam = sub / f"family_context_{target_name.split('_')[0]}.lean"
        if not fam.exists():
            _lib.init_context(fam, source_text.split(f"theorem {target_name}")[0])
        res["banked_helpers"] = _lib.bank(fam, r0.get("proof_text") or "")
        # CROSS-RUN COMPOUNDING (the amnesia fix, 2026-06-19): also bank the closed RUNG ITSELF into the
        # CAMPAIGN warm-env file (registered by the notes run via set_campaign_substrate) so the cascade
        # `exact?`/`aesop`-cites it BY TYPE next run instead of re-deriving it. INCREMENTAL (here, at the
        # kernel-ratify site) ⇒ a run that dies before its epilogue still compounds what it proved — the RCA
        # was that the epilogue-only bank NEVER fired (long runs die first). Reuses family_lemma_library's
        # canonical engine (content-stable name dodges the planner's generic-name collision; reverify+revert
        # keeps the shared env compiling). Best-effort + flag-gated; never blocks the closure.
        _pf = locals().get("_probe_full") or ""   # set in the cert-write block above; NameError-safe
        if _pf.strip() and os.environ.get("ZTARE_LEANMILL_BANK_RUNGS_TO_THEORY", "1") != "0":
            try:
                from ztare.formal.repl_compile import get_campaign_substrate as _gcs
                _env = _gcs()
                if _env:
                    # lean_root MUST be the campaign theory's LAKE PROJECT (`sub` = ztare_proofs), NOT
                    # `_probe_root`: that is the closure probe's scratch PARENT (…/.solver_scratch/closures),
                    # which has no `lean-toolchain` ⇒ `_toolchain_ok` is False ⇒ `campaign_file_env` returns
                    # None ⇒ the reverify "fails" and EVERY rung reverts as `reverted_noncompile`. This was
                    # THE amnesia banking-never-fires RCA (2026-06-20): banking fired for no run because the
                    # reverify root was a toolchain-less scratch dir. The theory file lives in `sub`; reverify
                    # it against `sub`'s warm REPL.
                    _br = _lib.bank_decl_to_env(_env, target_name, _pf, sub)
                    res["rung_banked_to_env"] = _br.get("banked_as")
                    res["rung_bank_reason"] = _br.get("reason")
                    if _br.get("banked_as"):
                        _hb = _br.get("helpers_banked") or []
                        print(f"[compounding] LIBRARY grew — rung '{target_name}' banked to the campaign env "
                              f"as {_br['banked_as']}"
                              + (f" (+{len(_hb)} helper lemma(s) carried)" if _hb else "")
                              + " (now exact?/aesop-citable, cross-run)", flush=True)
                    elif _br.get("reason") not in ("already", None):
                        # LOUD non-bank (anti-regression 2026-06-24): a SILENT revert hid the helper-drop banking
                        # bug across many runs (reuse=0, the pari-passu AP gap). Surface every non-trivial non-bank
                        # so a reverted_noncompile / reverify_unavailable can't masquerade as "no banking happened".
                        print(f"[compounding] rung '{target_name}' NOT banked (reason={_br.get('reason')}) — "
                              f"not citable next run; investigate bank_decl_to_env on `reverted_noncompile`", flush=True)
            except Exception as _e:  # noqa: BLE001 — compounding is best-effort; never blocks the closure
                res["rung_bank_error"] = repr(_e)[:120]
    # MECHANIZED apparatus-vs-math tag on EVERY non-closure (convergent eigenquestion, gemini+codex
    # 2026-06-05): never again launder a gated/budget/toolchain failure as "math-hard". The decompose
    # move being OFF (ZTARE_CONJECTURE_DECOMPOSE!=1) is the apparatus signal that bit the P1 runs.
    if r0.get("outcome") not in ("closed", None):
        try:
            if r0.get("outcome") == "rejected_governance":
                # the ANTI-LAUNDERING GATE fired: the solver GAMED the goal and governance REFUSED — neither apparatus
                # nor math (it's a caught cheat). Tagging it apparatus would launder the gate-event as a
                # resource limit (P1 deep run 2026-06-05 exposed exactly this mis-tag).
                r0["failure_class"] = {"class": "cheat_caught", "error_class": "governance_rejected",
                                       "reason": res.get("rejected_reason") or "governance refused a laundered closure"}
            else:
                from ztare.leanmill.solver.failure_class import classify_failure
                # de-obscure the gate: count THIS run's governance-rejected closes so a search that BLOCKED
                # laundered closures isn't summarized as a generic toolchain 'other_error' (denef debug).
                try:
                    _gov_rej = _unratified_closes_count(row["row_id"], since=_run_start)
                except Exception:  # noqa: BLE001 — surfacing is advisory; never break classification
                    _gov_rej = 0
                _fc = classify_failure(
                    error_tail=(r0.get("tail") or res.get("rejected_reason") or ""),
                    stop_reason=(r0.get("stop_reason") or res.get("dag_stop_reason") or ""),
                    conjecture_enabled=(os.environ.get("ZTARE_CONJECTURE_DECOMPOSE") == "1"),
                    governance_rejections=_gov_rej)
                r0["failure_class"] = _fc
                # ROADMAP #4: an explicit, fail-LOUD budget_killed flag (derived from the classifier, which
                # already tags budget/timeout cut-offs as `apparatus`) so a lift runner NEVER scores a
                # resource cut-off as a capability-NULL (apparatus ≠ math — the inadmissible-null trap).
                _bk = (_fc.get("class") == "apparatus" and any(
                    k in (_fc.get("reason") or "").lower()
                    for k in ("budget", "timeout", "wallclock", "timed out")))
                r0["budget_killed"] = bool(_bk)
                if _bk:
                    print(f"[BUDGET_KILLED] {r0.get('outcome')} null is an APPARATUS cut-off, NOT a "
                          f"capability-null: {_fc.get('reason')}", flush=True)
        except Exception as _e:  # noqa: BLE001
            r0["failure_class"] = {"class": "unknown", "reason": f"classifier error: {_e!r}"[:120]}
    # AUTONOMOUS RECURSION (ZTARE_LEANMILL_ISO_ROUTE, DEFAULT-ON 2026-06-09; =0 reverts to parity): an HONEST
    # non-closure (exact_gap / open / failed — NOT a caught cheat) on a strong_missing target → route to the
    # recursive PLANNER (isomorphism_decompose.route_and_solve): the warm leaf GENERATES the decomposition, the
    # KERNEL audits it (decomposition_dag_audit: sorry-free + non-circular + load-bearing + proves-G), and the
    # apparatus proves each sub-lemma — solve_decomposition re-enters solve_adhoc per lemma, which re-enters
    # THIS route on a strong_missing exact_gap sub-rung, until citable leaves (depth-guarded, ZTARE_ISO_MAX_DEPTH=2),
    # then composite-ratifies the parent. This is the planner-executor of DeepSeek-Prover-V2 / BFS-Prover-V2 /
    # LEAP, with a KERNEL decomposition-reviewer (not an LLM one) — the governance differentiator. SOUND BY
    # CONSTRUCTION at default-on: the parent closes ONLY through composite_ratify's anti-laundering kernel, and
    # the TERMINAL-REJECTION case (rejected_governance) is EXCLUDED below — a caught cheat is never re-decomposed. The
    # strong_missing triage scopes it (a plain transfer goal does NOT route), so easy goals pay nothing. Fail-open.
    # REACHABILITY FIX (2026-06-10 bug-hunt): the gate MUST match the dag_search producer enum
    # (`residual_to_lever`). {exact_gap, rung, new_sub_target} are the honest non-closures — `rung` = a
    # kernel-proven WEAKER special case with the full goal STILL OPEN (P1's proven rungs are literally this),
    # `new_sub_target` = a residual sub-goal emerged. The gate previously listed only `exact_gap` (+ the
    # cascade-only `open`/`failed`/`failed_compile`), so the recursion silently UNDER-FIRED on rung/new_sub_target
    # — exactly the rung-style non-closures it exists to re-decompose. `falsifier` (target may be false),
    # `retired_impossible` (genuine wall), and `rejected_governance` (caught cheat) correctly stay OUT.
    if _decomp_first:
        # The decompose-FIRST pre-pass already ran route_and_solve (it did NOT close — else we'd have returned).
        # Reuse its result (no double-dispatch) and lift any closure (defensive; normally not closed here).
        res["iso_route"] = _iso_pre
        _lift_decomposition_closure(res, _iso_pre)
    elif (os.environ.get("ZTARE_LEANMILL_ISO_ROUTE", "1") != "0"
            and r0.get("outcome") in ("exact_gap", "rung", "new_sub_target",
                                      "open", "failed", "failed_compile")):
        try:
            from ztare.leanmill.solver.isomorphism_decompose import route_and_solve as _ras
            res["iso_route"] = _ras(source_text, target_name, goal, lean_root=sub,
                                    timeout_s=timeout_s, substrate=sub, notes=notes, _depth=_iso_depth)
            # LIFT a kernel-RATIFIED parent closure into "solved" (#106): without this the cascade's miss
            # (r0) shadowed a genuine composite_ratify closure and the caller reported "not solved".
            _lift_decomposition_closure(res, res["iso_route"])
        except Exception as _e:  # noqa: BLE001 — routing is best-effort; never break the solve
            res["iso_route"] = {"error": repr(_e)[:160]}
    res["notes_used"] = bool(notes and notes.strip())   # #81 exit-point: record blueprint provenance on the result
    # SOFT reformulation signal: surface the agent's OWN `-- STATEMENT-FALSE:` refutation (the target is
    # mis-formalized, not merely hard) so the governed re-entry in `autoformalize_and_solve` can re-formalize the
    # CORRECTED statement with NO human editing the NL — the agent does it himself, the firewall re-verifies
    # faithfulness (it can never launder). Single capture point (vs threading every results.append). Only on a
    # non-closure; advisory + fail-safe (never breaks the solve).
    _r0sf = primary_result(res)
    if _r0sf.get("outcome") != "closed":
        try:
            from ztare.leanmill.solver.agentic_leaf import scan_probes_for_statement_false, probe_dir as _pdir
            _sf = scan_probes_for_statement_false(_pdir(sub))
            if _sf:
                # A `-- STATEMENT-FALSE:` comment is the leaf's CLAIM, not a verdict. The engine's rule is
                # that ONLY a kernel-checked ¬G refutes a target, so GATE the claim here (#143): dispatch the
                # skeptic to PROVE ¬G and kernel-verify it (warm-env when a campaign substrate is live, so
                # confirming a claim does not re-starve verify). Only a CONFIRMED ¬G sets `statement_false`
                # (→ the governed reformulation re-entry); an UNVERIFIED claim is recorded separately + the
                # corrective feedback surfaced, and does NOT trigger reformulation — the v7 trap was the leaf
                # flagging a TRUE, tractable lemma false with a counterexample that fails a structure-field
                # hypothesis, deadlocking reformulation on a provable statement. =0 reverts to the old
                # unverified behaviour (for the A/B baseline only).
                # NB (2026-06-23, Goldilocks): the DECISION to falsify is the AGENT's (it elects PLAN: FALSIFY at
                # the strategy fork, seeing its context/substrate refutations) — NOT a deterministic harness
                # "falsify-on-stall" (that creep was tried + reverted). This epilogue only kernel-VERIFIES a leaf's
                # explicit CLAIM (the soundness boundary); it does not decide strategy.
                if os.environ.get("ZTARE_LEANMILL_VERIFY_STATEMENT_FALSE", "1") != "0":
                    try:
                        from ztare.leanmill.solver.conjecture import (verify_statement_false_claim,
                                                                      statement_false_rejection_feedback)
                        from ztare.common.timeouts import timeout_s as _tbudget
                        _conf, _why, _blk = verify_statement_false_claim(
                            target_name, source_text, goal, sub, _tbudget("leaf_verify"))
                        if _conf:
                            res["statement_false"] = _sf            # KERNEL-CONFIRMED ¬G ⇒ a real refutation
                            _r0sf["statement_false"] = _sf
                            res["statement_false_verified"] = True
                            res["statement_false_refutation"] = (_blk or "")[:1200]
                        else:
                            res["statement_false_unverified"] = _sf  # the agent's CLAIM, not a verdict
                            res["statement_false_verify_detail"] = (_why or "")[:300]
                            res["statement_false_feedback"] = statement_false_rejection_feedback(_sf, _why)
                    except Exception as _sfe:  # noqa: BLE001 — on verify error DON'T promote the claim (sound default)
                        res["statement_false_unverified"] = _sf
                        res["statement_false_verify_detail"] = f"verify_error: {_sfe!r}"[:300]
                else:
                    res["statement_false"] = _sf                     # explicit opt-out: legacy unverified behaviour
                    _r0sf["statement_false"] = _sf
        except Exception:  # noqa: BLE001 — advisory surface; never break the solve
            pass
    if _redundant_instances:   # formalization-lint diagnosis on the result (telemetry; the cure is re-formalize)
        res["redundant_instances"] = _redundant_instances
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
        r0 = primary_result(res)   # live ref + fail-loud on missing "results" (the 2026-06-03 flywheel bug)
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
        r0 = primary_result(res)   # live ref + fail-loud on missing "results" (the 2026-06-03 flywheel bug)
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
                # DEAD-LEARNER FIX (#86): record_reuse was NEVER called → every banked lemma sat at reuse=0
                # while exposure climbed → the MDL ledger retired them ALL as dead weight (exposure-without-
                # reuse). Record the banked helpers this CLOSED proof actually cited (the compression signal),
                # mirroring record_exposure at provision time, so net-compressors now EARN their keep.
                _cited = [n for n in banked_so_far if n not in (name,) and proof_text.count(n) > 0]
                if _cited:
                    _lib.record_reuse(ctx, _cited)
                # Bank the CLOSED SIBLING THEOREM itself (decl + proof), not just intra-proof helpers
                # — in a coherent theory build-up the SIBLINGS are the reusable lemmas; banking L1a
                # (closed) is what lets L1b/L2a cite it instead of re-deriving (the SCALE mechanism;
                # the prior body-only banking found nothing because the leaf proves inline). 2026-06-04.
                from ztare.leanmill.lean_source import (swap_sorry as _swap_sorry,
                                                         attach_proof as _attach, signature_before_proof as _sig_bp)
                closed_thm = decl
                if proof_text.strip():
                    # CANONICAL sorry→proof splice (by-token + binder aware; never a re-rolled `:=` regex / double-by)
                    closed_thm = _swap_sorry(decl, proof_text.strip())
                    if not closed_thm:        # decl didn't end in `:= … sorry` — splice onto the signature instead
                        closed_thm = _attach(_sig_bp(decl).rstrip() + " :=", proof_text.strip())
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
    pa.add_argument("--notes", default=None, metavar="FILE",
                    help="optional blueprint/notes file (NL): decomposition guidance threaded into the "
                         "recursive planner when the target does not close directly (#81)")
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
        notes = Path(args.notes).read_text(encoding="utf-8") if args.notes else None
        res = solve_adhoc_governed(args.target, src_text, args.goal, provider=args.provider,
                                   timeout_s=args.timeout, mode=args.mode, substrate=sub, notes=notes)
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
            from ztare.common.timeouts import timeout_s as _budget   # central factory (byte-parity: selfcheck_compile defaults to the prior 180)
            ok_pos, _ = run_lake_compile_source(
                "theorem _selfcheck_ok : True := trivial\n",
                DEFAULT_LEAN_ROOT_FOR_VERIFY, timeout_s=_budget("selfcheck_compile"),
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
            from ztare.common.timeouts import timeout_s as _budget   # central factory (byte-parity: selfcheck_compile defaults to the prior 180)
            ok_neg, _ = run_lake_compile_source(
                "theorem _selfcheck_sorry : True := by sorry\n",
                DEFAULT_LEAN_ROOT_FOR_VERIFY, timeout_s=_budget("selfcheck_compile"),
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
