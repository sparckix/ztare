"""K-line disposition memory — Minsky K-lines + Banzhaf attribution.

Records the active CONFIGURATION on each success/failure event, keyed by a
PROBLEM SIGNATURE that is a structural quotient of the frontier — substrate-
neutral by design.  Proposes the highest-attribution configuration for a new
problem with a matching-or-nearby signature.

Provenance: Minsky (1980) "K-lines: A Theory of Memory" — a K-line is a
record of the mental state that produced a success, activated when a similar
situation recurs.  Shapley/Banzhaf attribution converts the ledger into a
component ranking.

──────────────────────────────────────────────────────────────────────────────
PROVENANCE SCHEMA (cold-review finding 9 — hindsight laundering guard)
──────────────────────────────────────────────────────────────────────────────
Every row carries four provenance fields:

  origin ∈ {human, agent, hybrid}
    — who generated the configuration.  Receipt-derived rows default to "agent".

  proposal_time_evidence: str
    — what was knowable at proposal time (e.g. which receipts existed).
    Honest about the retrospective limit for backfill rows.

  validation_authority: str
    — which gate or receipt validated the row (e.g. "champion_materialization",
    "scan_and_backfill", "record_human_kline").

  transfer_status ∈ {retrospective_candidate, prospectively_reproduced,
                     cross_substrate_verified}
    — how the row was generated relative to the outcome it records.
    Backfills default to "retrospective_candidate" because the signature/config
    are reconstructed after the fact from current workspace state.
    record_success stamps "prospectively_reproduced" when called live at success
    time (the row is written while the outcome is being observed).

HINDSIGHT LAUNDERING GUARD (propose_configuration):
  Human-origin rows with transfer_status="retrospective_candidate" are EXCLUDED
  from proposals by default.  Rationale: human-derived K-lines may GUIDE
  conductor forensics but cannot enter the zero-human-science ledger until the
  configuration is prospectively rediscovered by the agent stack.
  Override: set env ZTARE_KLINE_HUMAN_PRIOR=1 to include them; the proposal
  receipt will carry "human_prior_allowance": true as an audit trail.

record_human_kline() is the only write path for origin=human rows — used for
curated conductor-forensics entries (always retrospective_candidate).

──────────────────────────────────────────────────────────────────────────────
SUBSTRATE SEAM (seam name: k_line_adapter)
──────────────────────────────────────────────────────────────────────────────
The module has two layers:

  1. ADAPTERS  (worldmodel-specific — read receipts, compute signature/config)
     • problem_signature(project_dir)  ← worldmodel realization today
     • extract_configuration(project_dir)
     Numeric/prose substrate: signature from rubric-family + failure class;
     config from mutator settings.  Leanmill substrate: signature from
     failed-obligation dependency shape; config from tactic / case-split
     settings.  Adapters go in separate modules when a consumer exists; the
     kernel below is substrate-neutral already.

  2. KERNEL  (substrate-neutral: ledger / attribution / proposal)
     • record_success / record_failure / scan_and_backfill
     • attribution
     • propose_configuration

──────────────────────────────────────────────────────────────────────────────
SIGNATURE V3 — NEUTRAL QUOTIENTS ONLY
──────────────────────────────────────────────────────────────────────────────
Six coordinates, each a structural equivalence class; no raw coordinates,
grid dimensions, colors, absolute timestamps, board-content hashes, or LLM
embeddings.

  warrant_stratum:        visible | holdout | transfer
    — which verification tier broke (worldmodel: which gate stratum)
  contradiction_topology: components-1 | components-2 | components-3+
    — claim-evidence conflict shape (worldmodel: witness-hypergraph component count)
  residual_localization:  single_cell | coherent_block | full_frame
    — point / structured-sub-object / global (worldmodel: divergent-cell adjacency)
  input_conditionality:   uniform | mixed
    — failure conditioned on operation/input or uniform (worldmodel: action-dependence)
  regime_position:        boundary | interior
    — at a regime boundary or interior (worldmodel: env-frame-adjacent vs interior)
  epistemic_state:        collapsed-0 | collapsed-1-3 | collapsed-4+ | diverse
    — population diversity + eliminated-family count bucket + stagnation bucket

Worldmodel column translations:
  warrant_stratum   = visible / holdout / transfer gate
  contradiction_topology = witness-hypergraph component count
  residual_localization  = divergent-cell adjacency structure
  input_conditionality   = action-uniform vs action-mixed across witnesses
  regime_position        = env-frame-adjacent (entry_context_note "mid-episode" / boundary) vs interior
  epistemic_state        = from eliminated_families + stagnation

Numeric/prose column:
  warrant_stratum  = train-fit / heldout / transfer
  contradiction_topology = counterexample cluster structure
  residual_localization  = one feature region / systematic bias / model-class misfit
  input_conditionality   = feature-conditional vs unconditional
  regime_position        = distribution-shift point / piecewise seam
  epistemic_state        = same

Leanmill column:
  warrant_stratum  = type-check / obligation / full-proof
  contradiction_topology = failed-obligation dependency shape
  residual_localization  = one lemma / a branch / whole strategy
  input_conditionality   = tactic/case-conditional
  regime_position        = case-split seam
  epistemic_state        = same

──────────────────────────────────────────────────────────────────────────────
ABLATION HOOK
──────────────────────────────────────────────────────────────────────────────
Every Nth run the allocator may DROP the lowest-attribution configuration
component and observe the outcome, converting correlational Banzhaf estimates
to causal estimates.  Hook name: k_line_ablation_drop.  Wiring is a later
card — the attribution output already marks the lowest-attribution component.

──────────────────────────────────────────────────────────────────────────────
CLI
──────────────────────────────────────────────────────────────────────────────
    python -m ztare.common.k_line --project P [--backfill] [--attribution] [--propose]
"""
from __future__ import annotations

import json
import os
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

LEDGER_SCHEMA = "ztare.k_line.v1"
ATTRIBUTION_SCHEMA = "ztare.k_line_attribution.v1"

# Provenance field literals (cold-review finding 9)
ORIGIN_HUMAN = "human"
ORIGIN_AGENT = "agent"
ORIGIN_HYBRID = "hybrid"
TRANSFER_RETROSPECTIVE = "retrospective_candidate"
TRANSFER_PROSPECTIVE = "prospectively_reproduced"
TRANSFER_CROSS_SUBSTRATE = "cross_substrate_verified"

# ── Utilities ──────────────────────────────────────────────────────────────────


def _read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    out = []
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except Exception:  # noqa: BLE001
            pass
    return out


def _last_row(path: Path) -> dict | None:
    rows = _read_jsonl(path)
    return rows[-1] if rows else None


# ── Configuration extractor (worldmodel adapter) ───────────────────────────────


def extract_configuration(project_dir: str | Path) -> dict[str, Any]:
    """Extract a low-dimensional configuration dict from workspace receipts.

    Read-only; every field sourced from an existing artifact.
    Returns None for each field that cannot be determined.

    Fields:
      engine:           last routed engine name (str | None)
      phase:            last routed phase (str | None)
      specialist_mode:  'workbench' | 'sealed' | None
      specialist_model: model env value recorded at dispatch time (str | None)
      specialist_effort: effort env value (str | None)
      width_shards:     K (int | None)
      width_samples:    samples_per_shard (int | None)
      width_effort:     effort string from allocator (str | None)
      has_ground_truth: bool | None
      champion_source:  str | None (from promoted_sha / from_ref)
      has_engine_routing: bool  (False if engine_routing.jsonl absent)
    """
    project_dir = Path(project_dir)
    ws = project_dir / "workspace"

    cfg: dict[str, Any] = {}

    # ── Engine + phase (engine_routing.jsonl last row) ──
    er_row = _last_row(ws / "engine_routing.jsonl")
    if er_row is not None:
        cfg["engine"] = er_row.get("engine")
        cfg["phase"] = er_row.get("phase")
        cfg["has_engine_routing"] = True
    else:
        cfg["engine"] = None
        cfg["phase"] = None
        cfg["has_engine_routing"] = False

    # ── Specialist mode + model + effort (residual_specialists.jsonl last row) ──
    rs_row = _last_row(ws / "residual_specialists.jsonl")
    if rs_row is not None:
        # mode is per-dispatch; take the first dispatch that has it
        dispatches = rs_row.get("dispatches") or []
        modes = [d.get("mode") for d in dispatches if d.get("mode")]
        cfg["specialist_mode"] = modes[0] if modes else None
        # model/effort are env-ambient at dispatch time — not recorded in the receipt
        # ponytail: None here is honest; caller can inject via env if they want it
        cfg["specialist_model"] = None
        cfg["specialist_effort"] = None
    else:
        cfg["specialist_mode"] = None
        cfg["specialist_model"] = None
        cfg["specialist_effort"] = None

    # ── K/shards + samples + effort (width_allocations.jsonl last row) ──
    wa_row = _last_row(ws / "width_allocations.jsonl")
    if wa_row is not None:
        dec = wa_row.get("decision") or {}
        cfg["width_shards"] = dec.get("shards")
        cfg["width_samples"] = dec.get("samples_per_shard")
        cfg["width_effort"] = dec.get("effort")
    else:
        cfg["width_shards"] = None
        cfg["width_samples"] = None
        cfg["width_effort"] = None

    # ── Briefing features: has_ground_truth, champion_source ──
    # ground_truth.json presence (prompt-leak-audit target)
    cfg["has_ground_truth"] = (project_dir / "ground_truth.json").exists()

    # champion_source: from_ref of last promoted row in champion_materialization.jsonl
    cm_rows = _read_jsonl(ws / "champion_materialization.jsonl")
    promoted = [r for r in cm_rows if r.get("result") == "promoted"]
    if promoted:
        last_p = promoted[-1]
        cfg["champion_source"] = last_p.get("from_ref") or last_p.get("promoted_sha")
    else:
        cfg["champion_source"] = None

    return cfg


# ── Signature extractor (worldmodel adapter) ───────────────────────────────────


def _divergent_cell_localization(divergent_cells: list[dict]) -> str:
    """Classify divergent-cell adjacency into residual_localization bucket.

    Translation-invariant: uses relative adjacency, not absolute positions.
    Returns: 'single_cell' | 'coherent_block' | 'full_frame'
    """
    if not divergent_cells:
        return "single_cell"
    if len(divergent_cells) == 1:
        return "single_cell"

    # Build adjacency: two cells are adjacent if |dr|<=1 and |dc|<=1
    coords = [(c.get("row", 0), c.get("col", 0)) for c in divergent_cells]
    n = len(coords)

    # Union-Find for components
    parent = list(range(n))

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: int, b: int) -> None:
        parent[find(a)] = find(b)

    for i in range(n):
        for j in range(i + 1, n):
            r0, c0 = coords[i]
            r1, c1 = coords[j]
            if abs(r0 - r1) <= 1 and abs(c0 - c1) <= 1:
                union(i, j)

    n_components = len({find(i) for i in range(n)})

    # Heuristic: if one component and cells are dense → coherent_block
    # if scattered multiple components → implies full_frame when count is large
    if n_components == 1:
        return "coherent_block"
    # Multiple components: if they span more than half the divergent count → full_frame
    if n >= 8:
        return "full_frame"
    return "coherent_block"


def _witness_component_bucket(divergent_cells: list[dict]) -> str:
    """Hypergraph component count bucket for contradiction_topology.

    Uses the same adjacency as localization but reports the count bucket.
    Translation-invariant.
    """
    if not divergent_cells:
        return "components-1"

    coords = [(c.get("row", 0), c.get("col", 0)) for c in divergent_cells]
    n = len(coords)
    parent = list(range(n))

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for i in range(n):
        for j in range(i + 1, n):
            r0, c0 = coords[i]
            r1, c1 = coords[j]
            if abs(r0 - r1) <= 1 and abs(c0 - c1) <= 1:
                parent[find(i)] = find(j)

    k = len({find(i) for i in range(n)})
    if k == 1:
        return "components-1"
    if k == 2:
        return "components-2"
    return "components-3+"


def _regime_position(entry_context_note: str | None, step_index: int | None) -> str:
    """Determine regime_position: 'boundary' | 'interior'.

    worldmodel realization: env-frame-adjacent = boundary.
    step_index==0 means the failure is at the first holdout step = boundary.
    entry_context_note 'mid-episode' → interior; else boundary.
    """
    if step_index == 0:
        return "boundary"
    note = (entry_context_note or "").lower()
    if "mid-episode" in note:
        return "interior"
    return "boundary"


def _epistemic_bucket(
    eliminated_families: list,
    stagnation: int,
    population_depth_variance: float,
) -> str:
    """Map population state to epistemic_state bucket.

    collapsed-0:   0 eliminations, stagnation>0, low diversity
    collapsed-1-3: 1–3 eliminations
    collapsed-4+:  4+ eliminations
    diverse:       stagnation==0 and population_depth_variance>0
    """
    n_elim = len(eliminated_families)
    if n_elim == 0 and stagnation == 0 and population_depth_variance > 0:
        return "diverse"
    if n_elim == 0:
        return "collapsed-0"
    if n_elim <= 3:
        return "collapsed-1-3"
    return "collapsed-4+"


def _action_conditionality(first_failure_action: Any, witnesses: list[dict]) -> str:
    """Return 'uniform' or 'mixed' based on action field across witnesses.

    If only one witness, uses first_failure_action.
    Translation-invariant (structural, not which action).
    """
    actions = set()
    if first_failure_action is not None:
        actions.add(first_failure_action)
    for w in witnesses:
        a = w.get("action")
        if a is not None:
            actions.add(a)
    return "uniform" if len(actions) <= 1 else "mixed"


def _warrant_stratum_from_materialization(project_dir: Path) -> str:
    """Determine which gate tier broke last (warrant_stratum).

    Reads champion_materialization.jsonl: if promoted rows exist, we're in
    holdout territory; check gate_summary_after.  If only no_op rows, infer
    from the rank tuple.
    """
    ws = project_dir / "workspace"
    cm_rows = _read_jsonl(ws / "champion_materialization.jsonl")
    if not cm_rows:
        return "visible"
    # Last row: if result==no_op and reason mentions 'holdout' → holdout
    last = cm_rows[-1]
    reason = (last.get("reason") or "").lower()
    if "holdout" in reason:
        return "holdout"
    # promoted rows: check gate_summary_after for score<1 → holdout
    promoted = [r for r in cm_rows if r.get("result") == "promoted"]
    if promoted:
        gs = promoted[-1].get("gate_summary_after") or {}
        score = gs.get("score")
        if score is not None and score < 1.0:
            return "holdout"
    # fallback: use residual_specialists gate_results
    rs_rows = _read_jsonl(ws / "residual_specialists.jsonl")
    if rs_rows:
        last_rs = rs_rows[-1]
        for gr in last_rs.get("gate_results", {}).values():
            if gr and gr.get("holdout_depth", 0) > 0:
                return "holdout"
    return "visible"


def problem_signature(project_dir: str | Path) -> dict[str, str]:
    """Compute a stable, low-dimensional structural signature for the current frontier.

    All six coordinates are substrate-neutral quotients.  No raw coordinates,
    grid dimensions, colors, absolute timestamps, content hashes, or LLM embeddings.

    Invariance test (enforced by tests/test_k_line.py):
      Apply a translation + color-permutation + episode-time-shift to synthetic
      witness data; the signature must be bit-identical before and after.

    Returns a dict with keys:
      warrant_stratum, contradiction_topology, residual_localization,
      input_conditionality, regime_position, epistemic_state
    """
    project_dir = Path(project_dir)
    ws = project_dir / "workspace"

    # ── Load frontier ──
    try:
        from ztare.worldmodel.residual_specialists import build_frontier
        frontier = build_frontier(project_dir)
    except Exception:  # noqa: BLE001
        frontier = {}

    first_failure = frontier.get("first_failure") or {}
    divergent_cells = first_failure.get("divergent_cells") or []
    action = first_failure.get("action")
    step_index = first_failure.get("step_index")
    eliminated_families = frontier.get("eliminated_families") or []

    # ── entry_context_note from candidate_memory ──
    entry_context_note: str | None = None
    cm_path = ws / "candidate_memory.json"
    if cm_path.exists():
        try:
            raw = json.loads(cm_path.read_text(encoding="utf-8"))
            recs = raw.get("records", []) if isinstance(raw, dict) else raw
            if recs:
                champ = max(recs, key=lambda r: r.get("holdout_depth") or 0)
                ct = champ.get("counterexample_trace") or {}
                hw = ct.get("holdout_witness") or champ.get("holdout_witness") or {}
                entry_context_note = hw.get("entry_context_note")
        except Exception:  # noqa: BLE001
            pass

    # ── Stagnation + population variance from width_allocations ──
    wa_row = _last_row(ws / "width_allocations.jsonl")
    stagnation = 0
    if wa_row is not None:
        stagnation = wa_row.get("signals", {}).get("stagnation") or 0

    # Population depth variance (structural diversity signal; translation-invariant)
    population_depth_variance: float = 0.0
    if cm_path.exists():
        try:
            raw = json.loads(cm_path.read_text(encoding="utf-8"))
            recs = raw.get("records", []) if isinstance(raw, dict) else raw
            depths = [r.get("holdout_depth") or 0 for r in recs]
            if len(depths) > 1:
                mean = sum(depths) / len(depths)
                population_depth_variance = sum((d - mean) ** 2 for d in depths) / len(depths)
        except Exception:  # noqa: BLE001
            pass

    return {
        "warrant_stratum": _warrant_stratum_from_materialization(project_dir),
        "contradiction_topology": _witness_component_bucket(divergent_cells),
        "residual_localization": _divergent_cell_localization(divergent_cells),
        "input_conditionality": _action_conditionality(action, []),
        "regime_position": _regime_position(entry_context_note, step_index),
        "epistemic_state": _epistemic_bucket(eliminated_families, stagnation, population_depth_variance),
    }


# ── Ledger operations (substrate-neutral kernel) ───────────────────────────────


def _ledger_path(project_dir: Path) -> Path:
    return project_dir / "workspace" / "k_lines.jsonl"


def record_success(
    project_dir: str | Path,
    event: dict,
    *,
    signature: dict | None = None,
    configuration: dict | None = None,
) -> dict:
    """Append a success k-line row.  Computes signature/config if not provided.

    Stamps transfer_status=prospectively_reproduced — this path is called live
    at success time, so the row is written while the outcome is observed.
    """
    project_dir = Path(project_dir)
    sig = signature if signature is not None else problem_signature(project_dir)
    cfg = configuration if configuration is not None else extract_configuration(project_dir)
    row = {
        "schema": LEDGER_SCHEMA,
        "ts": time.strftime("%Y%m%dT%H%M%SZ", time.gmtime()),
        "signature": sig,
        "configuration": cfg,
        "event_ref": event,
        "outcome": "success",
        "origin": ORIGIN_AGENT,
        "proposal_time_evidence": "live — workspace receipts at call time",
        "validation_authority": "record_success",
        "transfer_status": TRANSFER_PROSPECTIVE,
    }
    ledger = _ledger_path(project_dir)
    ledger.parent.mkdir(parents=True, exist_ok=True)
    with ledger.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row) + "\n")
    return row


def record_failure(
    project_dir: str | Path,
    event: dict,
    *,
    signature: dict | None = None,
    configuration: dict | None = None,
) -> dict:
    """Append a failure k-line row for attribution contrast."""
    project_dir = Path(project_dir)
    sig = signature if signature is not None else problem_signature(project_dir)
    cfg = configuration if configuration is not None else extract_configuration(project_dir)
    row = {
        "schema": LEDGER_SCHEMA,
        "ts": time.strftime("%Y%m%dT%H%M%SZ", time.gmtime()),
        "signature": sig,
        "configuration": cfg,
        "event_ref": event,
        "outcome": "failure",
        "origin": ORIGIN_AGENT,
        "proposal_time_evidence": "live — workspace receipts at call time",
        "validation_authority": "record_failure",
        "transfer_status": TRANSFER_PROSPECTIVE,
    }
    ledger = _ledger_path(project_dir)
    ledger.parent.mkdir(parents=True, exist_ok=True)
    with ledger.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row) + "\n")
    return row


def scan_and_backfill(project_dir: str | Path) -> int:
    """Walk existing receipts and backfill k-line rows.  Best-effort, honest Nones.

    Sources:
      champion_materialization.jsonl — result==promoted → success; result==no_op → failure
      residual_specialists.jsonl — rows with investigated==true → success

    Skips rows already present in k_lines.jsonl (matched by event_ref.ts).
    Returns number of newly appended rows.
    """
    project_dir = Path(project_dir)
    ws = project_dir / "workspace"

    # Load existing event_refs to avoid duplicates
    existing_event_refs: set[str] = set()
    for row in _read_jsonl(_ledger_path(project_dir)):
        ev = row.get("event_ref") or {}
        key = ev.get("ts") or ev.get("event_ts") or ""
        if key:
            existing_event_refs.add(key)

    # Compute current signature + config once (best-effort; may differ from historical)
    try:
        sig = problem_signature(project_dir)
    except Exception:  # noqa: BLE001
        sig = {k: None for k in ["warrant_stratum", "contradiction_topology",
                                  "residual_localization", "input_conditionality",
                                  "regime_position", "epistemic_state"]}
    try:
        cfg = extract_configuration(project_dir)
    except Exception:  # noqa: BLE001
        cfg = {}

    appended = 0

    # ── champion_materialization.jsonl ──
    for row in _read_jsonl(ws / "champion_materialization.jsonl"):
        ts = row.get("ts", "")
        if ts in existing_event_refs:
            continue
        outcome = "success" if row.get("result") == "promoted" else "failure"
        event_ref = {"source": "champion_materialization", "ts": ts, "result": row.get("result")}
        ledger_row = {
            "schema": LEDGER_SCHEMA,
            "ts": time.strftime("%Y%m%dT%H%M%SZ", time.gmtime()),
            "signature": sig,
            "configuration": cfg,
            "event_ref": event_ref,
            "outcome": outcome,
            "backfill": True,
            "origin": ORIGIN_AGENT,
            "proposal_time_evidence": "retrospective — signature/config from current workspace, not historical snapshot",
            "validation_authority": "champion_materialization",
            "transfer_status": TRANSFER_RETROSPECTIVE,
        }
        with _ledger_path(project_dir).open("a", encoding="utf-8") as f:
            f.write(json.dumps(ledger_row) + "\n")
        existing_event_refs.add(ts)
        appended += 1

    # ── residual_specialists.jsonl — investigated turns ──
    for row in _read_jsonl(ws / "residual_specialists.jsonl"):
        ts = str(row.get("timestamp", ""))
        if ts in existing_event_refs:
            continue
        # Any dispatch with investigated=True is a credit
        dispatches = row.get("dispatches") or []
        has_investigated = any(d.get("investigated") for d in dispatches)
        if not has_investigated:
            # Still record it as a run (outcome=failure if no promotion)
            pass
        event_ref = {
            "source": "residual_specialists",
            "ts": ts,
            "investigated": has_investigated,
            "sharding_mode": row.get("sharding_mode"),
        }
        outcome = "success" if has_investigated else "failure"
        ledger_row = {
            "schema": LEDGER_SCHEMA,
            "ts": time.strftime("%Y%m%dT%H%M%SZ", time.gmtime()),
            "signature": sig,
            "configuration": cfg,
            "event_ref": event_ref,
            "outcome": outcome,
            "backfill": True,
            "origin": ORIGIN_AGENT,
            "proposal_time_evidence": "retrospective — signature/config from current workspace, not historical snapshot",
            "validation_authority": "residual_specialists",
            "transfer_status": TRANSFER_RETROSPECTIVE,
        }
        with _ledger_path(project_dir).open("a", encoding="utf-8") as f:
            f.write(json.dumps(ledger_row) + "\n")
        existing_event_refs.add(ts)
        appended += 1

    return appended


def record_human_kline(
    project_dir: str | Path,
    signature: dict,
    configuration: dict,
    note: str,
) -> dict:
    """Append a human-curated conductor-forensics K-line.

    Always origin=human, transfer_status=retrospective_candidate.
    These rows are EXCLUDED from propose_configuration by default (see
    ZTARE_KLINE_HUMAN_PRIOR guard).  They serve as conductor-forensics
    references — never as zero-human-science ledger entries until the
    configuration is prospectively rediscovered by the agent stack.
    """
    project_dir = Path(project_dir)
    row = {
        "schema": LEDGER_SCHEMA,
        "ts": time.strftime("%Y%m%dT%H%M%SZ", time.gmtime()),
        "signature": signature,
        "configuration": configuration,
        "event_ref": {"source": "record_human_kline", "note": note},
        "outcome": "human_forensic",
        "origin": ORIGIN_HUMAN,
        "proposal_time_evidence": "curator note — not reconstructed from receipts",
        "validation_authority": "record_human_kline",
        "transfer_status": TRANSFER_RETROSPECTIVE,
        "note": note,
    }
    ledger = _ledger_path(project_dir)
    ledger.parent.mkdir(parents=True, exist_ok=True)
    with ledger.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row) + "\n")
    return row


# ── Attribution (substrate-neutral kernel) ─────────────────────────────────────


def _attribution_for_rows(rows: list[dict]) -> dict[str, dict]:
    """Compute per-component Banzhaf-style contrasts for a slice of rows."""
    n_total = len(rows)
    n_success = sum(1 for r in rows if r.get("outcome") == "success")

    all_component_keys: set[str] = set()
    for row in rows:
        cfg = row.get("configuration") or {}
        for k in cfg:
            all_component_keys.add(k)

    components: dict[str, dict] = {}
    for comp_key in sorted(all_component_keys):
        value_stats: dict[Any, dict] = defaultdict(lambda: {"success": 0, "total": 0})
        for row in rows:
            cfg = row.get("configuration") or {}
            v = cfg.get(comp_key)
            val_key = str(v)
            value_stats[val_key]["total"] += 1
            if row.get("outcome") == "success":
                value_stats[val_key]["success"] += 1

        per_value: dict[str, dict] = {}
        for val_key, stats in value_stats.items():
            n_v = stats["total"]
            s_v = stats["success"]
            n_nv = n_total - n_v
            s_nv = n_success - s_v
            p_v = s_v / n_v if n_v else None
            p_nv = s_nv / n_nv if n_nv else None
            contrast = (p_v - p_nv) if (p_v is not None and p_nv is not None) else None
            per_value[val_key] = {
                "support": n_v,
                "success_count": s_v,
                "p_success": round(p_v, 4) if p_v is not None else None,
                "p_success_complement": round(p_nv, 4) if p_nv is not None else None,
                "contrast": round(contrast, 4) if contrast is not None else None,
                "insufficient_evidence": n_v < 3,
            }

        best_val = None
        best_contrast: float | None = None
        for val_key, vs in per_value.items():
            if not vs["insufficient_evidence"] and vs["contrast"] is not None:
                if best_contrast is None or vs["contrast"] > best_contrast:
                    best_contrast = vs["contrast"]
                    best_val = val_key

        components[comp_key] = {
            "values": per_value,
            "best_value": best_val,
            "best_contrast": round(best_contrast, 4) if best_contrast is not None else None,
        }
    return components


def attribution(project_dir: str | Path) -> dict:
    """Compute per-component marginal estimates (Banzhaf-style presence contrast).

    Method: correlational_v1 — P(success|component=v) − P(success|component≠v)
    over k_lines.jsonl rows.  Labeled as correlational; schedule ablations for
    causal estimates (hook: k_line_ablation_drop).

    Origin segments are kept separate: human and agent rows are NEVER mixed
    in one contrast computation (human-origin rows are advisory only and would
    contaminate the zero-human-science ledger statistics).

    Emits workspace/k_line_attribution.json and returns it.
    """
    project_dir = Path(project_dir)

    rows = _read_jsonl(_ledger_path(project_dir))
    if not rows:
        result: dict = {
            "schema": ATTRIBUTION_SCHEMA,
            "method": "correlational_v1 — schedule ablations for causal estimates",
            "n_rows": 0,
            "components": {},
            "note": "no k-line rows; run --backfill first",
        }
        _write_attribution(project_dir, result)
        return result

    # Segment by origin — never mix human and agent rows in one contrast
    agent_rows = [r for r in rows if r.get("origin", ORIGIN_AGENT) != ORIGIN_HUMAN]
    human_rows = [r for r in rows if r.get("origin") == ORIGIN_HUMAN]

    n_total = len(rows)
    n_agent = len(agent_rows)
    n_human = len(human_rows)
    n_success = sum(1 for r in agent_rows if r.get("outcome") == "success")
    n_failure = sum(1 for r in agent_rows if r.get("outcome") == "failure")

    # Attribution computed over agent rows only (the zero-human-science ledger)
    components = _attribution_for_rows(agent_rows)

    # Human-origin advisory summary (no contrast — advisory only)
    human_summary: dict = {}
    for r in human_rows:
        cfg = r.get("configuration") or {}
        for k, v in cfg.items():
            human_summary.setdefault(k, []).append(str(v))

    result = {
        "schema": ATTRIBUTION_SCHEMA,
        "method": "correlational_v1 — schedule ablations for causal estimates",
        "n_rows": n_total,
        "n_agent_rows": n_agent,
        "n_human_rows": n_human,
        "n_success": n_success,
        "n_failure": n_failure,
        "components": components,
        "human_advisory": human_summary,
        "note": (
            "Attribution computed over agent-origin rows only. "
            "Human-origin rows are listed in human_advisory and excluded from contrast. "
            "Ablation hook: k_line_ablation_drop drops the lowest-contrast component every Nth run "
            "to generate causal estimates."
        ),
    }
    _write_attribution(project_dir, result)
    return result


def _write_attribution(project_dir: Path, data: dict) -> None:
    out = project_dir / "workspace" / "k_line_attribution.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(data, indent=2), encoding="utf-8")


# ── Proposal (substrate-neutral kernel) ───────────────────────────────────────


def _sig_distance(a: dict, b: dict) -> int:
    """Count differing coordinates between two signatures."""
    keys = set(a) | set(b)
    return sum(1 for k in keys if a.get(k) != b.get(k))


def propose_configuration(project_dir: str | Path) -> dict:
    """Propose the highest-attribution configuration for the current signature.

    Lookup order: exact signature match first, then bucket-distance-1.
    Each component carries its attribution score + support.
    Components with support < 3 marked 'insufficient_evidence — inherit current default'.
    NEVER proposes science content — configurations only (settings, modes, sections).

    HINDSIGHT LAUNDERING GUARD:
      Human-origin rows with transfer_status=retrospective_candidate are excluded
      from the candidate pool unless env ZTARE_KLINE_HUMAN_PRIOR=1 is set.
      When the allowance is active the receipt carries "human_prior_allowance": true.
    """
    project_dir = Path(project_dir)
    human_prior_allowed = os.environ.get("ZTARE_KLINE_HUMAN_PRIOR", "") == "1"

    sig = problem_signature(project_dir)
    rows = _read_jsonl(_ledger_path(project_dir))
    attr = attribution(project_dir)

    # Apply hindsight laundering guard: drop human retrospective rows unless allowed
    eligible_rows = []
    human_excluded_count = 0
    for r in rows:
        if (
            r.get("origin") == ORIGIN_HUMAN
            and r.get("transfer_status") == TRANSFER_RETROSPECTIVE
            and not human_prior_allowed
        ):
            human_excluded_count += 1
            continue
        eligible_rows.append(r)

    # Filter eligible rows by signature proximity
    exact = [r for r in eligible_rows if r.get("signature") == sig]
    if not exact:
        near = [r for r in eligible_rows if _sig_distance(r.get("signature") or {}, sig) <= 1]
        candidates = near
        match_type = "bucket-distance-1"
    else:
        candidates = exact
        match_type = "exact"

    if not candidates:
        return {
            "schema": "ztare.k_line_proposal.v1",
            "current_signature": sig,
            "match_type": "none",
            "proposed_configuration": {},
            "human_rows_excluded": human_excluded_count,
            "human_prior_allowance": human_prior_allowed,
            "note": "no matching k-line rows; run --backfill",
        }

    # For each config component, pick the value from the highest-attribution row
    # weighted by outcome (prefer success rows)
    success_candidates = [r for r in candidates if r.get("outcome") == "success"]
    pool = success_candidates if success_candidates else candidates

    # Build per-component vote: value → support count among pool
    all_keys: set[str] = set()
    for r in pool:
        cfg = r.get("configuration") or {}
        all_keys.update(cfg.keys())

    proposed: dict[str, dict] = {}
    components = attr.get("components") or {}
    for k in sorted(all_keys):
        value_counts: dict[str, int] = defaultdict(int)
        for r in pool:
            cfg = r.get("configuration") or {}
            val = str(cfg.get(k))
            value_counts[val] += 1
        best_val_str, support = max(value_counts.items(), key=lambda kv: kv[1])

        # Recover typed value from first row that has it
        typed_val: Any = best_val_str
        for r in pool:
            cfg = r.get("configuration") or {}
            if k in cfg and str(cfg[k]) == best_val_str:
                typed_val = cfg[k]
                break

        comp_attr = components.get(k) or {}
        best_contrast = comp_attr.get("best_contrast")
        insufficient = support < 3

        entry: dict = {
            "value": typed_val,
            "support": support,
            "attribution_contrast": best_contrast,
        }
        if insufficient:
            entry["note"] = "insufficient_evidence — inherit current default"

        proposed[k] = entry

    receipt: dict = {
        "schema": "ztare.k_line_proposal.v1",
        "current_signature": sig,
        "match_type": match_type,
        "proposed_configuration": proposed,
        "human_rows_excluded": human_excluded_count,
        "human_prior_allowance": human_prior_allowed,
        "note": "Configurations only — no science content proposed.",
    }
    if human_prior_allowed:
        receipt["human_prior_allowance"] = True
    return receipt


# ── Routing prior (forward edge — bias router order/budget, never verdicts) ───


def routing_prior(project_dir: str | Path, current_signature: dict) -> "dict | None":
    """Find K-lines whose signature matches current_signature on >= 4 of 6 axes.

    Aggregates fix_class votes from eligible rows (same hindsight laundering
    guard as propose_configuration: human retrospective rows excluded unless
    ZTARE_KLINE_HUMAN_PRIOR=1), returns the modal fix_class with support count
    and ledger refs.

    Deterministic, no LLM.  Returns None when no rows match threshold.

    Match rule: exact per-axis string equality; axes with value None or
    "unknown" on EITHER side never count as a match (missing data cannot
    manufacture a match).

    Returns: {"fix_class": str, "support": int, "kline_refs": [str, ...]}
             or None
    """
    project_dir = Path(project_dir)
    human_prior_allowed = os.environ.get("ZTARE_KLINE_HUMAN_PRIOR", "") == "1"

    rows = _read_jsonl(_ledger_path(project_dir))

    SIG_AXES = (
        "warrant_stratum",
        "contradiction_topology",
        "residual_localization",
        "input_conditionality",
        "regime_position",
        "epistemic_state",
    )

    def _axes_matching(row_sig: dict) -> int:
        n = 0
        for ax in SIG_AXES:
            cur = current_signature.get(ax)
            row = row_sig.get(ax)
            if cur is None or cur == "unknown" or row is None or row == "unknown":
                continue
            if cur == row:
                n += 1
        return n

    eligible: list[dict] = []
    for r in rows:
        # Hindsight-laundering guard, keyed on TRANSFER_STATUS not origin
        # (2026-07-12, operator catch): an out-of-loop conductor's
        # retrospective disposition is exactly as unearned as a human's —
        # origin records WHO for audit; transfer_status records WHETHER TO
        # BELIEVE. Any retrospective_candidate row is excluded from priors
        # until prospectively reproduced, regardless of origin. The
        # ZTARE_KLINE_HUMAN_PRIOR=1 declared allowance opens all of them.
        if (
            r.get("transfer_status") == TRANSFER_RETROSPECTIVE
            and not human_prior_allowed
        ):
            continue
        fc = (r.get("configuration") or {}).get("fix_class")
        if not fc:
            continue  # no fix_class → not a routing-prior row
        row_sig = r.get("signature") or {}
        if _axes_matching(row_sig) >= 4:
            eligible.append(r)

    if not eligible:
        return None

    # Modal fix_class vote
    vote: dict[str, int] = {}
    refs: dict[str, list[str]] = {}
    for r in eligible:
        fc = r["configuration"]["fix_class"]
        vote[fc] = vote.get(fc, 0) + 1
        refs.setdefault(fc, []).append(r.get("ts", ""))

    modal_fc = max(vote, key=lambda k: vote[k])
    return {
        "fix_class": modal_fc,
        "support": vote[modal_fc],
        "kline_refs": refs[modal_fc],
    }


# ── CLI ────────────────────────────────────────────────────────────────────────


def _cli() -> None:
    import argparse

    p = argparse.ArgumentParser(description="K-line disposition memory")
    p.add_argument("--project", required=True, help="Project dir (e.g. projects/arc3_ls20_gov)")
    p.add_argument("--backfill", action="store_true", help="Scan receipts and backfill k_lines.jsonl")
    p.add_argument("--attribution", action="store_true", help="Compute and emit k_line_attribution.json")
    p.add_argument("--propose", action="store_true", help="Propose configuration for current frontier")
    args = p.parse_args()

    proj = Path(args.project)

    if args.backfill:
        n = scan_and_backfill(proj)
        print(f"backfill: {n} rows appended to {_ledger_path(proj)}")

    if args.attribution:
        a = attribution(proj)
        comps = a.get("components") or {}
        top3 = sorted(
            [(k, v.get("best_contrast") or -999) for k, v in comps.items()],
            key=lambda x: x[1],
            reverse=True,
        )[:3]
        print(f"attribution: n={a.get('n_rows')} success={a.get('n_success')} failure={a.get('n_failure')}")
        print("top-3 components by contrast:")
        for k, c in top3:
            bv = comps[k].get("best_value")
            print(f"  {k}: contrast={c} best_value={bv}")
        print(f"written → {proj / 'workspace' / 'k_line_attribution.json'}")

    if args.propose:
        prop = propose_configuration(proj)
        sig = prop.get("current_signature") or {}
        print(f"signature: {sig}")
        print(f"match_type: {prop.get('match_type')}")
        cfg_out = prop.get("proposed_configuration") or {}
        print("proposed configuration:")
        for k, v in sorted(cfg_out.items()):
            note = v.get("note", "")
            print(f"  {k}: {v.get('value')!r}  (support={v.get('support')}, contrast={v.get('attribution_contrast')}){(' [' + note + ']') if note else ''}")


if __name__ == "__main__":
    _cli()
