"""LEVEL-3 governance: the system's own machinery (classifiers, refines,
gates) as a governed object.

Motivating bug (2026-07-03): the env classifier EXCUSED 0-diff blocked-move
frames as non-physics while live play diverged on exactly those frames
repeatedly (sprint depth=1 spiral) — a contradiction between two receipts
that code detects mechanically, which only the human conductor caught.

Safety asymmetry — S1/I2 (producer/certifier separation, cognitive-firm
/draft.md §3): machinery-change proposals that TIGHTEN gates/excusals may
auto-adopt on strict improvement ONLY when ``certifier_touched=False``; any
proposal that touches the gates, classifiers, acceptance tests, or the
harness (``certifier_touched=True``) requires a conductor disposition — a
proposal must not amend its own certifier in one transaction.  Every card
carries ``certifier_touched`` so the adopt leg can enforce the split without
reading the proposal text.

Exogenous clock — S3 (cognitive-firm/draft.md §3): ``detect_and_card`` caps
at CARD_CAP=3 new cards per sprint run; beyond that it emits a single
meta-card "machinery churn exceeds clock — escalate" and stops.  Without
this cap the module could drive an unbounded self-repair loop, the runaway-
loop failure S3 exists to prevent.

This module only DETECTS and CARDS; adoption goes through the implement-leg
discipline.
"""
from __future__ import annotations

from ztare.common.operator_proposal_contract import operator_proposal_card, write_proposal_cards

SCHEMA = "machinery-contradiction-v1"
CARD_CAP = 3  # S3 exogenous clock: max new cards written per detect_and_card call


def _card(*, failure_family, evidence_indices, spatial_footprint,
          why_existing_ops_fail, proposed_operator_sketch, acceptance_test,
          certifier_touched: bool) -> dict:
    c = operator_proposal_card(
        schema=SCHEMA,
        failure_family=failure_family,
        evidence_indices=evidence_indices,
        spatial_footprint=spatial_footprint,
        why_existing_ops_fail=why_existing_ops_fail,
        proposed_operator_sketch=proposed_operator_sketch,
        acceptance_test=acceptance_test,
    )
    c["certifier_touched"] = certifier_touched
    return c


def excused_but_diverging(log, divergence_indices) -> list[dict]:
    """Frames live play diverged on that the classifier currently counts as
    env frames: (env_frame_indices(log) ∩ divergence rows) or (divergence
    rows that are 0-diff).  Either condition means excusal is hiding physics.

    Args:
        log: EpisodeLog of the current episode.
        divergence_indices: set/sequence of log row indices where live play
            produced a model_diverged status (rows appended on those rounds).
    """
    from ztare.worldmodel.gates import env_frame_indices  # read-only
    excused = env_frame_indices(log)
    rows = list(log)
    div_set = set(divergence_indices or [])
    # rows both excused by the classifier AND live play diverged on them
    overlap = excused & div_set
    # divergence rows that are 0-diff: blocked moves the law must predict,
    # not excuse (the 2026-07-03 bug class — these should never be excused)
    zero_diff_div = {i for i in div_set
                     if i < len(rows) and rows[i].s == rows[i].s_next}
    hit = overlap | zero_diff_div
    if not hit:
        return []
    return [_card(
        failure_family="excusal:hides:physics:diverged-frames",
        evidence_indices=sorted(hit)[:20],
        spatial_footprint={"excused": len(excused), "diverged": len(div_set),
                           "hit": len(hit)},
        why_existing_ops_fail={
            "machinery": (
                "the classifier excuses frames live play diverges on — "
                "excusal is hiding physics; proposal: narrow the excusal rule"
            )
        },
        proposed_operator_sketch="narrow_env_excusal(tighten_0diff_condition)",
        acceptance_test=(
            "plant 0-diff blocked-move row with normal t advance; verify "
            "env_frame_indices excludes it; verify detector is then silent"
        ),
        certifier_touched=True,  # targets gates.env_frame_indices (certifier)
    )]


def absorb_diverge_spiral(rounds) -> list[dict]:
    """>=3 consecutive rounds with status model_diverged and depth<=2 while
    the log grew.  Card: identification absorbs but play instantly re-diverges
    — divergence frames are not entering the law (excused, mis-scoped, or
    outside the grammar).

    Args:
        rounds: the sprint's rounds list — dicts with keys ``pursuit``/
            ``status`` (pursuit status), ``steps``/``depth`` (play depth),
            ``log`` (log length after the round), and ``round`` (round number).
    """
    def _status(r: dict) -> str:
        return r.get("pursuit") or r.get("status", "")

    def _depth(r: dict) -> int:
        return r.get("steps", r.get("depth", 9999))

    best: list = []
    run: list = []
    for r in rounds:
        if _status(r) == "model_diverged" and _depth(r) <= 2:
            run.append(r)
        else:
            if len(run) > len(best):
                best = run
            run = []
    if len(run) > len(best):
        best = run

    if len(best) < 3:
        return []
    logs = [r.get("log") for r in best if r.get("log") is not None]
    if len(logs) < 2 or logs[-1] <= logs[0]:
        return []  # log didn't grow across the spiral — no absorption evidence
    return [_card(
        failure_family="absorb-diverge:spiral:depth<=2",
        evidence_indices=[r.get("round", i + 1) for i, r in enumerate(best)],
        spatial_footprint={"run_length": len(best),
                           "log_growth": logs[-1] - logs[0]},
        why_existing_ops_fail={
            "machinery": (
                "identification absorbs but play instantly re-diverges — "
                "the divergence frames are not entering the law "
                "(excused, mis-scoped, or outside the grammar)"
            )
        },
        proposed_operator_sketch="inspect_excused_frames_in_divergence_log()",
        acceptance_test=(
            "plant >=3 consecutive model_diverged depth<=2 rounds with "
            "growing log; verify card fires; verify silent when spiral broken"
        ),
        certifier_touched=False,  # targets law/grammar, not the certifier
    )]


def terminal_verifier_edge_model_mismatch(rounds) -> list[dict]:
    """A verifier-edge transition occurred on a transition the model missed.

    The external verifier keeps outcome authority. The witnessed edge is also a
    counterexample receipt for the transition law; verifier vocabulary must not
    directly author model or advice updates. Some callers wrap the edge inside
    a broader pursuit status such as ``multilife``; the typed mismatch field is
    the authority for this detector, not the enclosing label.
    """
    hits = []
    witness_shas = set()
    for i, r in enumerate(rounds or []):
        mismatch = r.get(
            "transition_model_mismatch",
            r.get("terminal_verifier_model_mismatch"),
        )
        if mismatch:
            hits.append(r.get("round") or r.get("cycle") or i + 1)
            sha = r.get("terminal_witness_sha")
            if sha:
                witness_shas.add(sha)
    if not hits:
        return []
    return [_card(
        failure_family="terminal-verifier-edge:refines:transition-law",
        evidence_indices=hits[:20],
        spatial_footprint={
            "terminal_verifier_mismatch_edges": len(hits),
            "terminal_witness_classes": len(witness_shas) or len(hits),
            "terminal_witness_shas": sorted(witness_shas)[:20],
        },
        why_existing_ops_fail={
            "machinery": (
                "a terminal verifier event occurred on an edge the transition "
                "model did not predict; preserve the edge as a replayable "
                "counterexample, not only as an outcome receipt"
            )
        },
        proposed_operator_sketch="route_terminal_verifier_edge_mismatch_to_law_refinement()",
        acceptance_test=(
            "plant a round with transition_model_mismatch=true and a witness; "
            "verify card fires across enclosing pursuit labels; verify silent "
            "when the transition edge matches the model"
        ),
        certifier_touched=False,
    )]
def visible_holdout_split(visible_ok, holdout_depth, holdout_len,
                          prev_holdout_depth) -> list[dict]:
    """Visible replay improved while holdout regressed vs previous champion.
    Card: refine overfits visible evidence — selection arbiter and holdout
    disagree.

    Args:
        visible_ok: whether the candidate passes visible-replay consistency.
        holdout_depth: rollout depth on the held-out episode for this candidate.
        holdout_len: length of the holdout episode (to contextualise depth).
        prev_holdout_depth: champion's holdout depth before this refine.
    """
    if not visible_ok:
        return []
    if prev_holdout_depth is None or holdout_depth >= prev_holdout_depth:
        return []
    return [_card(
        failure_family="overfit:visible:holdout-regressed",
        evidence_indices=[holdout_depth, prev_holdout_depth],
        spatial_footprint={"visible_ok": visible_ok,
                           "holdout_depth": holdout_depth,
                           "holdout_len": holdout_len,
                           "prev_holdout_depth": prev_holdout_depth},
        why_existing_ops_fail={
            "machinery": (
                "refine overfits visible evidence — "
                "selection arbiter and holdout disagree"
            )
        },
        proposed_operator_sketch="holdout_gated_selection(require_holdout_nondecline=True)",
        acceptance_test=(
            "plant visible_ok=True, holdout_depth < prev_holdout_depth; "
            "verify card fires; verify silent when holdout_depth >= prev"
        ),
        certifier_touched=True,  # targets the selection arbiter / holdout gate
    )]


def tested_but_undispositioned(candidate_pool_path, ledger_path) -> list[dict]:
    """LEVEL-3 closure gap (sibling of the Strategy Office ledger-closure audit):
    gate-passing candidates exist — they were TESTED to enter the pool — yet the
    operator-proposal ledger carries OPEN cards and has never recorded a single
    disposition. Tested evidence is accumulating without closing the grammar
    ledger. Silent once ANY card is accepted/rejected."""
    import json as _json
    from pathlib import Path

    from ztare.common.operator_proposal_contract import open_cards

    pool = Path(candidate_pool_path)
    n_tested = (sum(1 for ln in pool.read_text().splitlines() if ln.strip())
                if pool.exists() else 0)
    open_ = open_cards(ledger_path)
    dispositioned = False
    ledger = Path(ledger_path)
    if ledger.exists():
        for ln in ledger.read_text().splitlines():
            if not ln.strip():
                continue
            try:
                d = _json.loads(ln)
            except Exception:  # noqa: BLE001
                continue
            if isinstance(d, dict) and d.get("disposition") in ("accepted", "rejected"):
                dispositioned = True
                break
    if n_tested == 0 or not open_ or dispositioned:
        return []
    return [_card(
        failure_family="ledger:tested-but-undispositioned",
        evidence_indices=[n_tested],
        spatial_footprint={"candidates_tested": n_tested, "open_cards": len(open_)},
        why_existing_ops_fail={"machinery":
            "gate-passing candidates accumulate while the grammar ledger has open "
            "cards and zero dispositions — tested evidence is not closing the ledger"},
        proposed_operator_sketch="conductor_disposition(open_operator_cards)",
        acceptance_test=(
            "plant a nonempty candidate_pool + open cards with no disposition; verify "
            "card fires; verify silent once any card is accepted/rejected"),
        certifier_touched=False,  # targets the disposition backlog, not the gates
    )]


def recurring_leaf_friction(ledger_path, *, min_count: int = 2) -> list[dict]:
    """Aggregate recurring leaf friction into a level-3 card.

    This is the friction-ledger analogue of ``tested_but_undispositioned``:
    instead of counting tested-but-unresolved candidates, it groups repeated
    stuck-exit diagnoses and emits one card when a friction class reappears.
    """
    import json as _json
    from collections import Counter, defaultdict
    from pathlib import Path

    ledger = Path(ledger_path)
    if not ledger.exists():
        return []
    rows = []
    for ln in ledger.read_text().splitlines():
        if not ln.strip():
            continue
        try:
            row = _json.loads(ln)
        except Exception:  # noqa: BLE001
            continue
        if isinstance(row, dict):
            rows.append(row)
    if not rows:
        return []
    grouped = defaultdict(list)
    for row in rows:
        friction = str(row.get("friction") or row.get("diagnosis") or "").strip()
        if not friction:
            continue
        grouped[friction].append(row)
    recurring = {k: v for k, v in grouped.items() if len(v) >= int(min_count)}
    if not recurring:
        return []
    top_friction, top_rows = max(recurring.items(), key=lambda item: (len(item[1]), item[0]))
    counts = Counter(str(r.get("outcome") or "unknown") for r in top_rows)
    return [_card(
        failure_family="leaf-friction:recurring:stuck-exits",
        evidence_indices=[len(top_rows)],
        spatial_footprint={
            "ledger_rows": len(rows),
            "recurring_friction_classes": len(recurring),
            "top_friction": top_friction,
            "top_friction_count": len(top_rows),
            "outcomes": dict(counts),
        },
        why_existing_ops_fail={
            "machinery": (
                "the leaf repeatedly reports the same missing affordance and the "
                "friction ledger has not yet turned that repetition into a harness card"
            )
        },
        proposed_operator_sketch="harness_card_from_recurring_leaf_friction(top_friction)",
        acceptance_test=(
            "plant repeated stuck rows with the same friction string; verify the "
            "detector emits one card; verify silence when each friction class is unique"
        ),
        certifier_touched=False,
    )]


def authority_artifact_demoted_in_prompt(
    *,
    authority_records,
    prompt_text: str,
    authority_label: str,
    demotion_markers: list[str] | None = None,
    failure_family: str = "briefing:authority-artifact:hidden-or-demoted",
) -> list[dict]:
    """Higher-authority artifacts exist, but the rendered prompt omits them or
    gives baseline authority to a lower artifact. This is the apparatus-level
    version of a candidate-selection error: the evidence survived its gate, then
    disappeared before the next worker could use it.

    Args:
        authority_records: higher-authority records with stable anchors such as
            sha, submission/path, or summary.
        prompt_text: rendered mutator briefing/prompt body.
        authority_label: short label for the artifact class.
        demotion_markers: strings whose presence means a lower artifact has been
            promoted as the active baseline.
        failure_family: stable card family for dedup.
    """
    records = [r for r in (authority_records or []) if isinstance(r, dict)]
    if not records:
        return []
    prompt = str(prompt_text or "")
    markers = list(demotion_markers or [])
    if not prompt:
        return [_authority_demoted_card(records, "empty_prompt", authority_label, failure_family)]

    best = sorted(records, key=lambda r: (
        int(r.get("authority_rank") or 0),
        int(r.get("visible_exact_rows") or 0),
        int(r.get("holdout_depth") or 0),
        float(r.get("gate_score") or 0.0),
        str(r.get("sha") or ""),
    ), reverse=True)[0]
    anchors = [
        str(best.get("sha") or ""),
        str(best.get("submission") or ""),
        str(best.get("summary") or "")[:80],
    ]
    visible = any(anchor and anchor in prompt for anchor in anchors)
    demoted = next((marker for marker in markers if marker and marker in prompt), "")
    if visible and not demoted:
        return []
    reason = f"demotion_marker:{demoted}" if demoted else "authority_artifact_not_rendered"
    return [_authority_demoted_card(records, reason, authority_label, failure_family)]


def full_survivor_hidden_from_prompt(records, prompt_text: str) -> list[dict]:
    """Candidate-memory instantiation of `authority_artifact_demoted_in_prompt`:
    a full deterministic survivor must dominate near-miss patch bases."""
    survivors = [
        r for r in (records or [])
        if isinstance(r, dict) and r.get("source_type") == "full_survivor"
    ]
    return authority_artifact_demoted_in_prompt(
        authority_records=survivors,
        prompt_text=prompt_text,
        authority_label="full_deterministic_survivor",
        demotion_markers=["Mandatory Patch Base"],
        failure_family="briefing:full-survivor:hidden-or-demoted",
    )


def _authority_demoted_card(records: list[dict], reason: str,
                            authority_label: str, failure_family: str) -> dict:
    best = sorted(records, key=lambda r: (
        int(r.get("authority_rank") or 0),
        int(r.get("visible_exact_rows") or 0),
        int(r.get("holdout_depth") or 0),
        float(r.get("gate_score") or 0.0),
        str(r.get("sha") or ""),
    ), reverse=True)[0]
    return _card(
        failure_family=failure_family,
        evidence_indices=[str(best.get("sha") or best.get("submission") or "unknown")],
        spatial_footprint={
            "authority_label": authority_label,
            "authority_records": len(records),
            "best_submission": best.get("submission"),
            "best_path": best.get("path"),
            "best_sha": best.get("sha"),
            "visible_exact_rows": best.get("visible_exact_rows"),
            "holdout_depth": best.get("holdout_depth"),
            "reason": reason,
        },
        why_existing_ops_fail={
            "machinery": (
                "a higher-authority artifact exists, but the rendered prompt "
                "omits it or gives baseline authority to a lower artifact"
            )
        },
        proposed_operator_sketch="briefing_authority_tightening(surface_higher_authority_artifact_first)",
        acceptance_test=(
            "plant a higher-authority artifact plus a lower-authority fallback; "
            "render the briefing; verify the higher-authority artifact appears "
            "first, no lower-artifact baseline marker appears, and the detector "
            "is silent"
        ),
        certifier_touched=False,
    )


def detect_and_card(project, log, rounds, *, divergence_indices=None,
                    visible_ok=None, holdout_depth=None, holdout_len=None,
                    prev_holdout_depth=None, candidate_memory_records=None,
                    prompt_text: str | None = None) -> int:
    """Run applicable detectors; write cards to <project>/workspace/
    operator_proposals.jsonl (dedup via write_proposal_cards); return count
    of NEW cards written.

    S3 exogenous clock (cognitive-firm/draft.md §3): caps at CARD_CAP=3 new
    cards per call.  If more than CARD_CAP contradictions are detected, the
    first CARD_CAP are written plus one meta-card "machinery churn exceeds
    clock — escalate", and detection stops.  This prevents an unbounded
    self-repair loop.

    Detector failures are caught individually; a broken detector never
    prevents the others from running or breaks the caller (sprint).
    """
    from pathlib import Path
    ledger = Path(project) / "workspace" / "operator_proposals.jsonl"

    candidates: list[dict] = []
    try:
        candidates.extend(excused_but_diverging(log, divergence_indices or set()))
    except Exception:  # noqa: BLE001 — detector failure must not break a sprint
        pass
    try:
        candidates.extend(absorb_diverge_spiral(rounds))
    except Exception:  # noqa: BLE001
        pass
    try:
        candidates.extend(terminal_verifier_edge_model_mismatch(rounds))
    except Exception:  # noqa: BLE001
        pass
    if visible_ok is not None and holdout_depth is not None and holdout_len is not None:
        try:
            candidates.extend(visible_holdout_split(
                visible_ok, holdout_depth, holdout_len, prev_holdout_depth))
        except Exception:  # noqa: BLE001
            pass
    if candidate_memory_records is not None:
        try:
            candidates.extend(full_survivor_hidden_from_prompt(
                candidate_memory_records, prompt_text or ""))
        except Exception:  # noqa: BLE001
            pass
    try:
        candidates.extend(recurring_leaf_friction(Path(project) / "workspace" / "leaf_friction.jsonl"))
    except Exception:  # noqa: BLE001
        pass

    # S3 clock: if over the cap, emit one meta-card and stop
    if len(candidates) > CARD_CAP:
        total = len(candidates)
        candidates = candidates[:CARD_CAP]
        candidates.append(_card(
            failure_family="machinery:churn:exceeds-clock",
            evidence_indices=[total],
            spatial_footprint={"total_detected": total, "cap": CARD_CAP},
            why_existing_ops_fail={
                "machinery": "machinery churn exceeds clock — escalate"
            },
            proposed_operator_sketch="conductor_review(machinery_contradiction_backlog)",
            acceptance_test=(
                "plant >CARD_CAP contradictions in one call; verify only "
                "CARD_CAP+1 cards written (CARD_CAP detections + meta-card)"
            ),
            certifier_touched=True,
        ))

    if not candidates:
        return 0
    written = write_proposal_cards(ledger, candidates)
    return len(written)
