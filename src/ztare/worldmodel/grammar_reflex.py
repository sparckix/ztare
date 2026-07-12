"""THE GRAMMAR REFLEX (GP-250): chain the organs that already exist.

The loop grew every organ for self-extending its own hypothesis grammar —
residual triage (``operator_proposals``), the sealed-leaf implement contract
(``operator_proposal_contract.implement_and_validate`` + ``operator_implement``),
and the abducer's prior-seeded warm start — but nothing CHAINED them: a sprint
that hit the catalog ceiling always deferred to the human-governed checkpoint.

This module is the missing conductor-free reflex. On an abduction PARTIAL it:

  1. triages the residual the current catalog cannot express into proposal
     cards (``propose_operators``) and writes them (dedup) to the ledger;
  2. for up to ``budget`` OPEN cards, runs the EXISTING proven implement path
     (``implement_and_validate`` over the sealed ``worldmodel_leaf_runner`` and
     the ``worldmodel_harness`` acceptance gate);
  3. on acceptance, RE-ABDUCES the same log (prior_spec seeded) — if that closes
     the law the caller keeps playing the SAME run; else it checkpoints, now with
     the cards + dispositions on the ledger as the briefing.

MACHINERY_RULES compliance (rules cited by number):
  * Rule 3 (Certifier Separation): operator-proposal cards target the GRAMMAR,
    never a gate/classifier/acceptance-test/harness, so they are not
    ``certifier_touched`` by construction. Sprint leaves only consume
    evidence-bearing, non-certifier cards; a defensive assert remains before
    implementation so a mislabelled card can never auto-adopt here.
  * Rule 4 (Tightening Only for Auto-Adopt): a NEW operator ADDS expressiveness,
    which is the TIGHTEN side — it lets the deterministic law explain a residual
    that previously fell to the ungoverned mutator; it never loosens a gate or an
    excusal, so no countersigned loosening receipt is required.
  * Rule 5 (Exogenous Clock): ``budget`` is the conductor-set cap on implement
    attempts per reflex round; the detector never sets its own clock.
  * Rule 6 (Attestation on Every Adoption): each acceptance writes one attestation
    (card sha, outcome, principal, rules-file sha, harness summary, ts) onto the
    ledger row via ``attest`` + ``record_disposition``.
"""
from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from ztare.common.operator_proposal_contract import (
    DISPOSITION_ACCEPTED,
    DISPOSITION_REJECTED,
    attest,
    implement_and_validate,
    open_cards,
    operator_proposal_card,
    record_disposition,
    set_disposition,
)
from ztare.worldmodel.operator_implement import (
    worldmodel_harness,
    worldmodel_leaf_runner,
)
from ztare.worldmodel.operator_proposals import _infer_mismatches, propose_operators, write_proposals
from ztare.worldmodel.spec_abduction import abduce_spec


def _ledger_path(project) -> Path:
    return Path(project) / "workspace" / "operator_proposals.jsonl"


def _arity(log) -> int:
    return max((tr.a for tr in log), default=0) + 1


def prescribe_for_seam(*args, **kwargs) -> dict:
    """Late import seam so tests can monkeypatch without loading model plumbing."""
    from ztare.research_director.research_isomorphism import prescribe_for_seam as _prescribe
    return _prescribe(*args, **kwargs)


def _stable_json(obj) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str)


def _bridge_cache_path(project) -> Path:
    return Path(project) / "workspace" / "grammar_reflex_structural_bridge.json"


def _bridge_enabled() -> bool:
    return os.environ.get("ZTARE_REFLEX_STRUCTURAL_BRIDGE", "0") == "1"


def _bridge_evidence_indices(cards: list[dict]) -> list[int]:
    idxs: list[int] = []
    for card in cards:
        for raw in card.get("evidence_indices") or []:
            try:
                idxs.append(int(raw))
            except (TypeError, ValueError):
                continue
    return sorted(set(idxs)) or [0]


def _bridge_failure_state(cards: list[dict], dispositions: list[dict]) -> dict:
    source = dispositions[-1] if dispositions else (cards[0] if cards else {})
    family = source.get("failure_family", "worldmodel grammar ceiling")
    reasons = source.get("why_existing_ops_fail") or {}
    reason_text = "; ".join(str(v) for v in reasons.values() if str(v).strip())
    counter = str(source.get("counterexample", "")).strip()
    residual = counter or reason_text or str(family)
    return {
        "constraint_class": f"worldmodel catalog ceiling: {family}",
        "abstract_form": str(source.get("proposed_operator_sketch") or residual),
        "home_field": "ARC worldmodel operator catalog",
        "residual": residual[:500],
        "card_count": len(cards),
    }


def _load_bridge_cache(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"schema": "grammar-reflex-structural-bridge-cache-v1", "entries": {}}


def _write_bridge_cache(path: Path, cache: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(cache, sort_keys=True) + "\n", encoding="utf-8")


def _bridge_key(log, spec, failure_state: dict, *, provider: str, n: int, mode: str) -> str:
    try:
        log_hash = log.content_hash()
    except Exception:  # noqa: BLE001
        log_hash = str(len(list(log)))
    payload = {
        "schema": "grammar-reflex-structural-bridge-v1",
        "log_hash": log_hash,
        "spec": spec,
        "failure_state": failure_state,
        "provider": provider,
        "n": int(n),
        "mode": mode,
    }
    return hashlib.sha256(_stable_json(payload).encode()).hexdigest()


def _bridge_card(failure_state: dict, prescription: dict, key: str,
                 evidence_indices: list[int]) -> dict:
    source = prescription.get("source_theorem") or "structural transport"
    field = prescription.get("source_field") or "unknown field"
    return operator_proposal_card(
        failure_family={
            "kind": "structural_transport_bridge",
            "bridge_sha": key[:16],
            "constraint_class": failure_state.get("constraint_class", ""),
        },
        evidence_indices=evidence_indices,
        spatial_footprint={
            "bridge_sha": key[:16],
            "source_field": field,
            "candidate_count": prescription.get("candidate_count", 1),
        },
        why_existing_ops_fail={
            "standard_leaf": "operator-proposal leaf did not pass its harness",
            "transport": str(prescription.get("transported_structure", ""))[:240],
        },
        proposed_operator_sketch=f"{source} ({field}) -> spec_patch",
        acceptance_test=("require spec_patch, then replay against the current evidence with "
                         "strict improvement and no transition regressions"),
    )


def _safe_step(step, tr):
    try:
        return step(tr.s, tr.a, tr.t)
    except Exception:  # noqa: BLE001
        return None


def _baseline_step(ab_result):
    """Returns (step_or_None, err_or_None). err is set iff a baseline SPEC
    existed but could not be loaded — the caller must not adjudicate a
    candidate against that phantom (every row would count base-wrong)."""
    step = getattr(ab_result, "step_fn", None)
    if step is not None:
        return step, None
    spec = getattr(ab_result, "spec", None)
    if not spec:
        return None, None       # no baseline exists at all — legitimate
    try:
        from ztare.worldmodel.spec_catalog import lower_spec
        lowered, lerr = lower_spec(spec)
    except Exception as exc:  # noqa: BLE001
        return None, repr(exc)
    if lowered is None:
        return None, str(lerr or "lower_spec returned None")
    return lowered, None


def _spec_patch_house_verdict(log, ab_result, spec_patch: dict) -> dict:
    from ztare.worldmodel.gates import env_frame_indices
    from ztare.worldmodel.spec_catalog import lower_spec

    candidate_step, err = lower_spec(spec_patch)
    if candidate_step is None:
        return {"accepted": False, "reason": f"lower_spec_failed:{err}"}
    baseline, baseline_err = _baseline_step(ab_result)
    if baseline_err is not None:
        # A spec existed but would not load: adjudicating against a phantom
        # baseline auto-accepts every candidate. Refuse loudly instead.
        return {"accepted": False, "reason": f"baseline_unloadable: {baseline_err}"}
    env = set(env_frame_indices(log))
    rows = [(i, tr) for i, tr in enumerate(log) if i not in env]
    if not rows:
        return {"accepted": False, "reason": "no_scored_rows"}
    base_wrong = 0
    cand_wrong = 0
    regressions: list[int] = []
    for i, tr in rows:
        target = tr.s_next
        base_ok = False
        if baseline is not None:
            base_ok = _safe_step(baseline, tr) == target
        cand_ok = _safe_step(candidate_step, tr) == target
        if not base_ok:
            base_wrong += 1
        if not cand_ok:
            cand_wrong += 1
        if base_ok and not cand_ok:
            regressions.append(i)
    accepted = cand_wrong < base_wrong and not regressions
    return {
        "accepted": accepted,
        "baseline_wrong": base_wrong,
        "candidate_wrong": cand_wrong,
        "regressions": regressions[:20],
        "scored_rows": len(rows),
        "reason": "strict_improvement_no_regressions" if accepted else "rejected_by_house_arbiter",
    }


def _write_bridge_dictionary_entry(prescription: dict, failure_state: dict, key: str,
                                   verdict: dict, spec_patch: dict) -> dict:
    path = Path(os.environ.get(
        "ZTARE_RESEARCH_ISOMORPHISM_DICTIONARY",
        "analytics/queries/research_isomorphism_dictionary.jsonl",
    ))
    rec = {
        "record_type": "learned_correspondence_dictionary_entry",
        "source_key": f"structural_bridge:{key}",
        "mother_structure": prescription.get("source_theorem") or "structural transport bridge",
        "left_constraint_class": prescription.get("source_field") or "",
        "right_constraint_class": failure_state.get("constraint_class", ""),
        "lowerings": {
            "source": prescription.get("transported_structure", ""),
            "worldmodel_spec_patch": spec_patch,
        },
        "novel_predictions": {
            "worldmodel": prescription.get("predict_then_falsify", ""),
        },
        "kill_conditions": {
            "worldmodel": "future replay regression or loss of strict improvement",
        },
        "specificity": verdict.get("scored_rows"),
        "note": "accepted by grammar_reflex structural bridge replay arbiter",
    }
    existing = set()
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            existing.add(json.loads(line).get("source_key"))
    except (OSError, ValueError):
        existing = set()
    path.parent.mkdir(parents=True, exist_ok=True)
    if rec["source_key"] not in existing:
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec) + "\n")
    return rec


def _attempt_structural_transport_bridge(project, log, ab_result, cards: list[dict],
                                         dispositions: list[dict], ledger: Path, *,
                                         provider: str = "deepseek", n: int = 3,
                                         mode: str = "correspondence") -> dict:
    if not _bridge_enabled():
        return {"status": "disabled"}
    if not dispositions:
        return {"status": "not_triggered", "reason": "no_leaf_attempt"}
    if open_cards(ledger):
        return {"status": "not_triggered", "reason": "standard_cards_remain"}

    failure_state = _bridge_failure_state(cards, dispositions)
    key = _bridge_key(log, getattr(ab_result, "spec", None), failure_state,
                      provider=provider, n=n, mode=mode)
    cache_path = _bridge_cache_path(project)
    cache = _load_bridge_cache(cache_path)
    entries = cache.setdefault("entries", {})
    cached = entries.get(key)
    if cached:
        prescription = dict(cached.get("prescription") or {})
        source = "cache"
    else:
        try:
            prescription = prescribe_for_seam(
                failure_state["constraint_class"],
                abstract_form=failure_state.get("abstract_form", ""),
                home_field=failure_state.get("home_field", ""),
                invariants={"unresolved_residual": failure_state.get("residual", "")},
                model=provider,
                n=n,
                typed_mapping=True,
                mode=mode,
            ) or {}
        except Exception as exc:  # noqa: BLE001
            prescription = {}
            entries[key] = {"status": "query_error", "error": repr(exc)[:240]}
            _write_bridge_cache(cache_path, cache)
            return {"status": "query_error", "bridge_sha": key[:16], "error": repr(exc)[:240]}
        entries[key] = {"status": "queried", "prescription": prescription}
        _write_bridge_cache(cache_path, cache)
        source = "query"

    evidence = _bridge_evidence_indices(cards)
    card = _bridge_card(failure_state, prescription, key, evidence)
    spec_patch = prescription.get("spec_patch") if isinstance(prescription, dict) else None
    if not spec_patch:
        disp = set_disposition(card, DISPOSITION_REJECTED)
        disp["counterexample"] = "NO_SPEC_PATCH"
        record_disposition(ledger, disp)
        return {"status": "no_spec_patch", "bridge_sha": key[:16], "source": source,
                "disposition": disp}

    verdict = _spec_patch_house_verdict(log, ab_result, spec_patch)
    if not verdict.get("accepted"):
        disp = set_disposition(card, DISPOSITION_REJECTED)
        disp["counterexample"] = json.dumps(verdict, sort_keys=True)
        record_disposition(ledger, disp)
        return {"status": "rejected_gates", "bridge_sha": key[:16], "source": source,
                "verdict": verdict, "disposition": disp}

    disp = set_disposition(card, DISPOSITION_ACCEPTED)
    disp["receipt"] = json.dumps(verdict, sort_keys=True)
    att = attest(card, outcome=DISPOSITION_ACCEPTED,
                 principal=f"grammar_reflex::structural_bridge::{provider}",
                 ts=datetime.now(timezone.utc).isoformat(),
                 suite=str(disp.get("receipt", ""))[:160])
    record_disposition(ledger, disp, attestation=att["attestation"])
    disp["attestation"] = att["attestation"]
    dictionary_entry = _write_bridge_dictionary_entry(
        prescription, failure_state, key, verdict, spec_patch)
    return {"status": "accepted", "bridge_sha": key[:16], "source": source,
            "verdict": verdict, "spec_patch": spec_patch, "disposition": disp,
            "dictionary_entry": dictionary_entry}


def _backfill_empty_evidence_cards(ledger: Path, log, spec) -> None:
    """FIX 3: pre-registered cards with evidence_indices=[] are filtered out of
    the implement loop forever.  On each reflex entry, compute matches via
    _infer_mismatches against the current log+spec and append an update row.
    Cards that still match nothing stay open with a receipt note.
    Append-only: record_disposition writes a new row, never edits in place."""
    rows = list(log)
    for card in open_cards(ledger):
        if card.get("evidence_indices"):
            continue  # already has evidence; skip
        matched = _infer_mismatches(rows, spec)
        updated = dict(card)
        if matched:
            updated["evidence_indices"] = matched
            updated["backfill_note"] = f"evidence backfilled: {len(matched)} indices"
        else:
            updated["backfill_note"] = "no_evidence_yet"
        record_disposition(ledger, updated)


def attempt_grammar_extension(project, log, ab_result, *, leaf="codex", budget=1) -> dict:
    """One reflex round: residual -> cards -> sealed-leaf implement -> re-abduce.

    ``ab_result`` is the PARTIAL abduction that hit the catalog ceiling. Returns::

        {"closed": bool,            # re-abduction closed the law in-run
         "result": AbductionResult, # the closing result, else the original
         "receipt": str | None,     # harness acceptance receipt when closed
         "cards": [...],            # residual cards proposed this round
         "dispositions": [...]}     # the accept/reject trail (per card)

    The leaf (``worldmodel_leaf_runner``) and harness (``worldmodel_harness``) are
    module globals so hermetic tests monkeypatch them — no live codex in tests.
    """
    spec = getattr(ab_result, "spec", None)
    ledger = _ledger_path(project)

    # FIX 3: backfill evidence_indices for pre-registered "closure:*" cards that
    # arrived before any log was available (evidence_indices=[]).  Append-only:
    # each update is a new record_disposition row (not in-place edit).
    _backfill_empty_evidence_cards(ledger, log, spec)

    # (1) triage the residual the catalog cannot express into cards; dedup-write.
    #     mismatch_indices=None -> propose_operators lowers `spec` and infers the
    #     mispredicted rows (the residual).
    cards = propose_operators(log, spec, None)
    write_proposals(project, cards)

    # (2) up to `budget` OPEN cards through the existing proven implement path
    #     (Rule 5: `budget` is the conductor's exogenous cap on this round).
    arity = _arity(log)
    dispositions: list[dict] = []
    # bind the sealed leaf. The substrate harness gets the card's evidence
    # indices inside the loop so its real-improvement leg stays proportional to
    # the residual family being validated.
    def _leaf(card):
        return worldmodel_leaf_runner(card, provider=leaf)

    live_cards = [c for c in open_cards(ledger)
                  if c.get("evidence_indices") and not c.get("certifier_touched")]
    for card in live_cards[: max(int(budget), 0)]:
        # Rule 3: operator cards are grammar-only, never certifier-touched. Assert
        # it so a mislabelled card cannot slip through the auto-adopt path.
        assert not card.get("certifier_touched"), \
            "Rule 3: an operator-proposal card must not be certifier_touched"
        def _harness(artifact, _card=card):
            if isinstance(artifact, dict):
                artifact = dict(artifact)
                artifact.setdefault("_baseline", {"spec": spec})
                artifact.setdefault("_real_indices", list(_card.get("evidence_indices") or []))
            return worldmodel_harness(artifact, real_log=log)

        disp = implement_and_validate(card, _leaf, _harness)
        dispositions.append(disp)

        if disp.get("disposition") == DISPOSITION_ACCEPTED:
            # Rule 6: attest the adoption onto the ledger row.
            att = attest(card, outcome=DISPOSITION_ACCEPTED,
                         principal=f"grammar_reflex::{leaf}",
                         ts=datetime.now(timezone.utc).isoformat(),
                         suite=str(disp.get("receipt", ""))[:160])
            record_disposition(ledger, disp, attestation=att["attestation"])
            disp["attestation"] = att["attestation"]
            # FIX 2: Path A promotions also write a promotion-contract row so
            # p0_metrics.catalog_promotions counts them (the metric reads
            # grammar_extension_promotion_contracts.jsonl which Path B writes;
            # append-only truth — source file unchanged).
            try:
                from ztare.worldmodel.grammar_extension import _write_promotion_contract
                from ztare.worldmodel.grammar_extension import ExtensionReceipt
                _promo_receipt = ExtensionReceipt(
                    env_hint=str(project),
                    model_id=str(leaf),
                    prompt_sha256="",
                    name=str(card.get("failure_family", ""))[:80],
                    python="",
                    rationale=str(card.get("proposed_operator_sketch", ""))[:240],
                    verdict="promoted",
                    detail=str(disp.get("receipt", ""))[:240],
                )
                _write_promotion_contract(project, _promo_receipt)
            except Exception:  # noqa: BLE001 — metric write must not block adoption
                pass
            # (3) re-abduce the SAME log, prior_spec seeded — did the adopted
            #     operator close the law? If so the caller keeps playing in-run.
            new_ab = abduce_spec(log, arity, prior_spec=spec, nogood_project=project)
            return {"closed": bool(getattr(new_ab, "replay_ok", False)),
                    "result": new_ab, "receipt": disp.get("receipt", ""),
                    "cards": cards, "dispositions": dispositions}

        # rejected: persist the disposition (with its counterexample) as briefing.
        record_disposition(ledger, disp)

    bridge = _attempt_structural_transport_bridge(
        project, log, ab_result, cards, dispositions, ledger)
    if bridge.get("status") == "accepted":
        dispositions.append(bridge["disposition"])
        new_ab = abduce_spec(log, arity, prior_spec=bridge.get("spec_patch"),
                             nogood_project=project)
        return {"closed": bool(getattr(new_ab, "replay_ok", False)),
                "result": new_ab, "receipt": bridge["disposition"].get("receipt", ""),
                "cards": cards, "dispositions": dispositions,
                "structural_bridge": bridge}

    # no cards, or every card in budget rejected -> checkpoint with the trail.
    return {"closed": False, "result": ab_result, "receipt": None,
            "cards": cards, "dispositions": dispositions,
            "structural_bridge": bridge}
