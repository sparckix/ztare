"""pre_tick_obligation_compiler.py — GP-241 deterministic obligation compiler.

Cold GPT-5.5 verdict (Meta-Darwin'd, conceded superior to "recommend
catalog items"): the forcing object is a GOAL-DERIVED PROOF OBLIGATION,
not an item id. goal text → deterministic feature extraction → catalog
activation clauses (DNF, NOT fuzzy scores / NOT embeddings / NOT LLM /
NOT training — nondeterministic ⇒ unauditable quarantine; corpus is ~60
self-describing items) → sparse mandatory tick contract → commit gate
recomputes from goal+catalog hashes and requires witness OR structured
why_not. Abstention is first-class (flooding is itself a failed
membrane). Precision caps enforced.

Shares PHILOSOPHY with src/ztare/orchestrator/mutator_briefing.py
(deterministic, no-priors, tiered, persisted composition) but the
semantics differ: mutator_briefing emits ADVISORY text; this emits an
ENFORCED contract the daemon recomputes. Build-once / two consumers:
this core is substrate-agnostic (free-text goal + org-wide catalogs);
a later reviewed change registers the same core as a T0 forcing
provider into mutator_briefing for the V4 autoresearch loop.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from src.ztare.common.paths import REPO_ROOT

ROUTING = REPO_ROOT / "org" / "catalog_routing"
MANIFEST = (REPO_ROOT / "projects" / "ns_millennium_hunt" / "workspace"
            / "ns_residual_manifest.md")
EXTRACTOR_VERSION = "pretick-oblig/v1"

CAPS = {"L1": 2, "L2": 2, "L3": 1}
CAP_TOTAL = 4
CLOSURE_SAFETY_L3_CAP = 2
KNOWN_RECEIPTS = {"forecast_tick_packet"}


def _norm(s: str) -> str:
    return " ".join((s or "").lower().split())


def extract_features(goal: str) -> dict:
    """Deterministic structural feature extraction. Every feature is a
    reproducible boolean function of the goal text (+ a fixed env fact
    for prior-atom availability). No model, no randomness."""
    g = _norm(goal)
    closure = any(k in g for k in (
        "exhausted", "terminus", "stop", "closed", "dead end", "no path",
        "no further", "give up", "real terminus", "channel exhausted",
        "settled", "impossible"))
    artifact_only = (any(k in g for k in (
        "formatting", "broken link", "links", "typo", "rename", "lint",
        "whitespace")) and any(k in g for k in (
        "no research claim", "without changing any research claim",
        "already-stamped", "already stamped", "no claim change")))
    return {
        "closure_or_terminus_claim": closure and not artifact_only,
        "prior_atom_similarity_available": MANIFEST.is_file(),
        "asks_pivot_or_discriminator": any(k in g for k in (
            "discriminator", "pivot", "next step", "propose the next",
            "falsif", "what would falsify", "eigenquestion")),
        "strong_positive_claim": any(k in g for k in (
            "breakthrough", "this might be it", "promising", "finally",
            "proven", "solved", "closure reached")) and not artifact_only,
        "math_estimate_goal": any(k in g for k in (
            "bound", "estimate", "inequality", "a priori", "norm",
            "barrier", "majorant", "certificate", "intertwiner")),
        "artifact_integrity_only": artifact_only,
        # high-value recurring RD failure modes, deterministic from goal:
        "amnesia_risk": (any(k in g for k in (
            "new reduction", "new approach", "fresh attempt", "novel route",
            "new idea", "try a different", "propose a new")) and not any(
            k in g for k in ("checked prior", "amnesia", "manifest",
            "alias", "prior work checked", "precheck"))) and not artifact_only,
        "citation_load_bearing": any(k in g for k in (
            "cite", "per the theorem", "by the theorem of", "according to",
            "as shown in", "literature says", "known result", "well-known")),
        "stuck_diminishing": any(k in g for k in (
            "stuck", "diminishing returns", "no progress", "multiple "
            "iterations", "exhausted options", "going in circles",
            "spinning")) and not artifact_only,
        # GP-241 #57: the stem "impossib" catches both "impossible"
        # AND "impossibility/impossibilities" — the prior list had only
        # "impossible", so the CANONICAL negative-result phrasing
        # "(sharply) characterize the impossibility of X" wrongly
        # yielded declares_impossible=False, which then minted a
        # MANDATORY judge-bound successful-CONSTRUCTION obligation on a
        # tick whose honest outcome is "constructed-and-excluded" (a
        # category error that wedged a scientifically-complete negative
        # tick). Added the negative-characterization verbs too. Pure
        # deterministic extraction widening; epistemic accountability
        # for a negative result is enforced by the forecast resolution
        # + H6 catch, not by a construction obligation.
        "declares_impossible": any(k in g for k in (
            "impossib", "cannot be done", "unreachable", "give up",
            "no way forward", "settled negative", "provably hopeless",
            "characterize the impossib", "rule out", "no such",
            "negative result", "sharply characterize the impossib",
            "exclude the")),
        # this session's RCA mechanized: a decision-critical ARCHITECTURE /
        # mechanism / design decision must get a cold cross-provider
        # generative pass, never self-simulated review.
        "load_bearing_arch_decision": any(k in g for k in (
            "architecture", "design decision", "decision-critical decision",
            "which approach", "should we build", "mechanism choice",
            "spec decision", "redesign", "which mechanism")),
    }


def derive_signals(text: str) -> dict:
    """VERIFIER-DERIVED typed signals from the transition text (cold
    GPT-5.5 sev-5 must-fix: declared signals are agent-controlled — an
    uncooperative agent omits a declaration to dodge a mandatory
    obligation). The daemon OR-merges these with declared so a
    declaration may only ADD an obligation, NEVER suppress one the
    text plainly implies. Maps the prose feature names → the typed
    declared_true signal names used in the activation clauses."""
    f = extract_features(text or "")
    return {
        "proposes_new_route": bool(f.get("amnesia_risk")),
        "declares_impossible": bool(f.get("declares_impossible")
                                    or f.get("closure_or_terminus_claim")),
        "citation_load_bearing": bool(f.get("citation_load_bearing")),
        "asks_discriminator": bool(f.get("asks_pivot_or_discriminator")),
        "positive_claim": bool(f.get("strong_positive_claim")),
        "stuck": bool(f.get("stuck_diminishing")),
        "load_bearing_arch_decision": bool(f.get("load_bearing_arch_decision")),
        "math_estimate": bool(f.get("math_estimate_goal")),
    }


def merge_signals(declared: dict | None, text: str) -> dict:
    """Union of Trues: declared may ADD, the verifier-derived floor
    cannot be suppressed by an absent/false declaration."""
    declared = declared or {}
    derived = derive_signals(text)
    keys = set(declared) | set(derived)
    return {k: bool(declared.get(k)) or bool(derived.get(k)) for k in keys}


def _load_clauses(clause_files: list[str] | None = None) -> list[dict]:
    # clause_files lets a DIFFERENT substrate (e.g. V4) use its OWN
    # activation file — RD obligations must NOT leak into V4 (operator
    # 2026-05-17: V4 obligations are substrate-specific).
    names = clause_files or ["l1_activation.yaml", "l2_activation.yaml",
                             "l3_activation.yaml"]
    out: list[dict] = []
    for n in names:
        p = ROUTING / n
        if p.is_file():
            try:
                out += yaml.safe_load(p.read_text(encoding="utf-8")) or []
            except Exception:
                continue
    return out


def _catalog_hashes() -> dict:
    h = {}
    for layer in ("l1", "l2", "l3"):
        p = ROUTING / f"{layer}_activation.yaml"
        h[layer] = (hashlib.sha256(p.read_bytes()).hexdigest()[:16]
                    if p.is_file() else "absent")
    return h


def _normalize_discharge_policy(raw: dict | None) -> dict:
    if not isinstance(raw, dict):
        return {"mode": "judge", "receipts": []}
    mode = str(raw.get("mode") or "judge").strip().lower()
    if mode != "receipt":
        return {"mode": "judge", "receipts": []}
    receipts_raw = raw.get("receipts") or raw.get("allowed_receipts") or []
    if raw.get("receipt"):
        receipts_raw = list(receipts_raw) + [raw.get("receipt")]
    receipts = sorted({
        str(r).strip()
        for r in receipts_raw
        if str(r).strip() in KNOWN_RECEIPTS
    })
    if not receipts:
        return {"mode": "judge", "receipts": []}
    return {
        "mode": "receipt",
        "receipts": receipts,
        "scope": str(raw.get("scope") or "routine_process"),
    }


def _clause_fires(clause: dict, feats: dict, g: str) -> tuple[bool, list, str]:
    matched: list[str] = []
    for cl in clause.get("activation", []):
        need_all = cl.get("all", [])
        if not all(feats.get(f) for f in need_all):
            continue
        # GP-241 #57: optional deterministic NEGATIVE guard. A clause
        # may declare `none: [feature names]`; if ANY listed feature is
        # truthy the clause does NOT fire. Same DNF/auditable class as
        # `all`/`any_lexical` (no fuzzy/LLM); it only RELAXES the
        # mandatory net (excludes a case), so it cannot expand forcing
        # — and a negative-result/impossibility goal excluded here is
        # still epistemically bound by the forecast + H6 catch. Used to
        # stop an impossibility-characterization goal from minting a
        # successful-construction obligation (category error).
        none_f = cl.get("none", [])
        if any(feats.get(f) for f in none_f):
            continue
        matched += [f for f in need_all if feats.get(f)]
        any_lex = cl.get("any_lexical")
        if any_lex:
            hit = [w for w in any_lex if w in g]
            if not hit:
                continue
            matched += [f"lex:{hit[0]}"]
        return True, matched, cl.get("clause_id", "?")
    return False, [], ""


@dataclass
class TickContract:
    contract_id: str
    goal_hash: str
    catalog_hashes: dict
    extractor_version: str
    mandatory_obligations: list = field(default_factory=list)
    advisory_candidates: list = field(default_factory=list)
    abstentions: list = field(default_factory=list)

    def as_dict(self) -> dict:
        return self.__dict__.copy()


def _typed_satisfied(clause: dict, transition_type: str,
                     declared: dict) -> bool:
    """ANTI-OVERFIT INVARIANT (cold GPT-5.5 + operator, 2026-05-17):
    'No unstamped interpretation may enter the forcing path. Only
    deterministic, hash-addressed, AGENT-DECLARED fields may activate
    MANDATORY obligations.' Keyword-sniffed prose is unstamped
    interpretation ⇒ advisory only. Mandatory-eligibility requires the
    clause's typed_when to hold over the typed transition_type +
    explicit declared signals (auditable; paraphrase cannot bypass)."""
    tw = clause.get("typed_when")
    if not tw:
        return False  # no typed anchor ⇒ never mandatory (advisory only)
    tt_ok = (transition_type in tw["transition_type_in"]
             if tw.get("transition_type_in") else True)
    dt = tw.get("declared_true") or []
    dt_ok = all(bool(declared.get(k)) for k in dt) if dt else True
    # require at least one POSITIVE typed condition (not vacuous)
    has_cond = bool(tw.get("transition_type_in") or dt)
    return has_cond and tt_ok and dt_ok


def start_tick(goal: str, transition_type: str = "",
               declared: dict | None = None,
               clause_files: list[str] | None = None) -> TickContract:
    g = _norm(goal)
    declared = declared or {}
    feats = extract_features(goal)
    fired: list[dict] = []
    for c in _load_clauses(clause_files):
        # GP-241 #63: the `none:` negative guard must be CLAUSE-LEVEL
        # and authoritative over BOTH the lexical (`_clause_fires`) AND
        # the typed_when (`_typed_satisfied`) paths. #57 only put it in
        # `_clause_fires`, so a negative-result goal with `math_estimate`
        # declared still minted auxiliary_comparison_object_construction
        # via typed_ok alone (the recurring frozen-at-start obligation
        # that forced the operator-retire treadmill, TICK644/646/647).
        # If ANY activation clause declares `none: [features]` and any
        # listed feature is truthy, the WHOLE catalog clause is excluded
        # — deterministic, auditable, only RELAXES the mandatory net (a
        # negative-result tick is bound by the forecast + H6 catch, not
        # by a spurious construction obligation).
        _none_block = any(
            feats.get(_nf)
            for _act in (c.get("activation") or [])
            for _nf in (_act.get("none") or []))
        if _none_block:
            continue
        ok, matched, cid = _clause_fires(c, feats, g)
        typed_ok = _typed_satisfied(c, transition_type, declared)
        if not ok and not typed_ok:
            continue
        structural_n = len([m for m in matched if not m.startswith("lex:")])
        lexical_n = len([m for m in matched if m.startswith("lex:")])
        rank = (3 if typed_ok else 0) + structural_n * 2 + (1 if lexical_n else 0)
        # misdeclaration cross-check: prose/feature says this clause is
        # relevant but the agent did NOT declare the typed signal ⇒
        # surface as advisory (the dodge is visible, not silent).
        misdeclare = ok and not typed_ok and (structural_n or lexical_n)
        fired.append({
            "layer": c["layer"], "item_id": c["item_id"],
            "catalog_anchor": c.get("catalog_anchor"),
            "activation_clause_id": cid, "rank": rank,
            "matched_features": matched,
            "obligation": c["obligation"],
            "witness_schema": c.get("witness_schema", {}),
            "why_not_enum": c.get("why_not_enum", []),
            "discharge": _normalize_discharge_policy(c.get("discharge")),
            # MANDATORY iff a typed (declared/transition_type) anchor
            # holds — NOT on keyword-sniffed prose (paraphrase-proof).
            "safety_critical": bool(c.get("safety_critical")),
            "_mandatory_eligible": typed_ok,
            "_misdeclaration_suspected": misdeclare,
        })
    # SAFETY-CRITICAL FIRST (codex confirm sev-5 fix: caps must never
    # demote a safety obligation — e.g. relapse_to_prior_alias — below
    # a non-safety one like citation_laundering).
    fired.sort(key=lambda o: (not o["safety_critical"], -o["rank"],
                              o["layer"], o["item_id"]))

    mandatory, advisory, per_layer = [], [], {"L1": 0, "L2": 0, "L3": 0}
    for o in fired:
        layer = o["layer"]
        cap = CAPS[layer]
        if layer == "L3" and any(
                f in o["matched_features"]
                for f in ("closure_or_terminus_claim",)):
            cap = CLOSURE_SAFETY_L3_CAP
        misdeclare = o.pop("_misdeclaration_suspected", False)
        safety = o.get("safety_critical")
        # safety-critical + typed-eligible ⇒ ALWAYS mandatory, EXEMPT
        # from L3/total caps and NOT counted against the non-safety
        # budget (caps apply only to non-safety obligations).
        if o["_mandatory_eligible"] and safety:
            o.pop("_mandatory_eligible")
            mandatory.append(o)
        elif (o["_mandatory_eligible"] and per_layer[layer] < cap
                and len(mandatory) < CAP_TOTAL + sum(
                    1 for m in mandatory if m.get("safety_critical"))):
            o.pop("_mandatory_eligible")
            mandatory.append(o)
            per_layer[layer] += 1
        else:
            o.pop("_mandatory_eligible", None)
            advisory.append({
                "layer": layer, "item_id": o["item_id"],
                "reason": ("MISDECLARATION_SUSPECTED: prose suggests this "
                           "obligation but the typed transition_type/"
                           "declared signal was not set — declare it or "
                           "it stays advisory")
                if misdeclare else "lexical_only_or_capped"})

    abstentions = [{"layer": L, "reason": "no_activation_clause_satisfied"}
                   for L in ("L1", "L2", "L3")
                   if not any(m["layer"] == L for m in mandatory)]
    gh = hashlib.sha256(g.encode()).hexdigest()[:16]
    ch = _catalog_hashes()
    cid = hashlib.sha256(
        (gh + json.dumps(ch, sort_keys=True) + EXTRACTOR_VERSION)
        .encode()).hexdigest()[:16]
    return TickContract(cid, gh, ch, EXTRACTOR_VERSION,
                        mandatory, advisory, abstentions)


def judge_prompt_for(goal: str, transition_type: str,
                     declared: dict | None, item_id: str,
                     witness: dict) -> str:
    """SINGLE SOURCE OF TRUTH for the judge prompt (cold review
    baxgapbe9). Both judge_out_of_loop AND the daemon call this; the
    daemon binds sha256(this) as prompt_hash so a mutator cannot feed
    the judge a weakened rubric — the obligation is RECOMPUTED
    un-forgeably from the goal here. Deterministic (sorted JSON)."""
    c = start_tick(goal, transition_type, declared or {})
    ob = next((o for o in c.mandatory_obligations
               if o["item_id"] == item_id), None)
    if ob is None:
        return ""  # not a real fired obligation ⇒ empty ⇒ no match
    rubric = {
        "obligation": ob.get("obligation"),
        "required_witness_fields": ob.get(
            "witness_schema", {}).get("required", []),
        "why_not_enum": ob.get("why_not_enum", []),
    }
    w = {k: v for k, v in (witness or {}).items() if k != "provenance"}
    reason = str(w.get("reason", "")).strip()
    is_why_not = bool(reason and reason in (ob.get("why_not_enum") or []))
    discharge_kind = "why_not" if is_why_not else "witness"
    pass_rule = (
        "PASS only if the discharge is a valid why_not: the reason is "
        "one of the allowed why_not_enum values and the justification "
        "specifically establishes why this obligation is not applicable "
        "for this tick. Do NOT require the successful-construction "
        "witness fields for a valid why_not."
        if is_why_not else
        "PASS only if the witness shows the obligation's actual required "
        "work was DONE (named, specific, verifiable), not asserted."
    )
    return (
        "You are an INDEPENDENT cross-provider JUDGE of whether an "
        "agent's discharge GENUINELY satisfies a forcing obligation — "
        "not whether it is fluently written. Fluent prose that does "
        "not evidence the actual work is FAIL.\n\nOBLIGATION RUBRIC:\n"
        + json.dumps(rubric, sort_keys=True, ensure_ascii=False,
                     indent=2)
        + f"\n\nDISCHARGE KIND: {discharge_kind}\n\n"
        + "\n\nAGENT DISCHARGE:\n"
        + json.dumps(w, sort_keys=True, ensure_ascii=False, indent=2)
        + "\n\nJudge strictly. Output ONLY JSON: {\"verdict\":"
        " \"pass\"|\"fail\", \"reasons\": [..], \"evidence_gaps\":"
        " [..], \"gaming_signals\": [..]}. " + pass_rule)


def _resolve_provenance(ref: str, *, item_id: str | None = None,
                        substantive: bool = False,
                        expect_tick_id: str | None = None,
                        expect_contract_id: str | None = None,
                        expect_witness_sha: str | None = None,
                        allowed_receipts: set[str] | None = None
                        ) -> tuple[bool, str]:
    """ANTI-GAMING FIX #1 + #2 (2026-05-17). #1: discharge may not be
    self-asserted prose. #2 (cold review b9is0a1fx: fix #1 was
    STILL-GAMEABLE — provenance unbound to the obligation): a
    SUBSTANTIVE fired obligation must bind to a `judge:` verdict — a
    chain-valid daemon-signed row with transition_type=='judge_verdict'
    that itself BINDS this obligation's item_id and carries a separate
    judge_identity. Nothing produces judge_verdict rows yet ⇒ this
    FAIL-CLOSES every substantive discharge until the mutator→JUDGE→
    monitor primitive (reuse of test_thesis/sandbox_gaming_extractor)
    is wired. stamped:/file:/catch: are payload references only — NOT
    sufficient to discharge a substantive obligation (the cold-review
    bypass: pointing stamped: at the tick's own start row).
    Fail-closed: any error / unrecognized / unresolvable ⇒ (False,…).
    Kinds:
      judge:<verdict_proposal_id> — REQUIRED for substantive: a
        chain-valid signed `judge_verdict` row binding this item_id +
        a judge_identity (the separate warm judge).
      stamped:<proposal_id> — GOLD: a chain-valid, daemon-SIGNED
        ledger row (e.g. a real cold-review / adversary tick). The
        agent cannot forge this (it is the daemon's own signature).
      catch:<catch_id>      — a catch_ledger.jsonl entry with that id
        AND author_agent != concurring_agent (the #28 discipline).
      file:<repo-relpath>   — a real file, ≥400 bytes (substance, not
        a prose-in-proposal stub). Weaker (agent-writable) but at
        least existence+mass, externally inspectable.
    """
    ref = str(ref or "").strip()
    if ":" not in ref:
        return False, f"no provenance scheme in {ref!r}"
    kind, _, val = ref.partition(":")
    val = val.strip()
    try:
        if kind == "receipt":
            # Routine process obligations may use a tiny known-receipt
            # adapter when the catalog explicitly opts them in. The
            # adapter still verifies daemon-signed lifecycle receipts.
            # Substantive math/failure-mode obligations remain on
            # judge: provenance.
            if val not in KNOWN_RECEIPTS:
                return False, f"unknown receipt provenance {val!r}"
            allowed = allowed_receipts or set()
            if val not in allowed:
                return False, (
                    f"receipt:{val} is not catalog-allowed for "
                    f"{item_id}; use judge provenance")
            if not expect_tick_id or not expect_contract_id:
                return False, "receipt binding missing tick_id/contract_id"
            from src.ztare.gates.stamped_state import chain_valid, _rows
            valid, _ = chain_valid(_rows())
            start = next((r for r in valid
                          if r.get("transition_type") == "start_tick"
                          and str(r.get("tick_id")) == str(expect_tick_id)
                          and str(r.get("contract_id")) == str(expect_contract_id)),
                         None)
            if not start:
                return False, "no chain-valid start_tick receipt for this tick/contract"
            if not str(start.get("forecast_contract_id", "")).strip():
                return False, "start_tick lacks frozen forecast_contract_id"
            kinds = {
                str(r.get("manifest_kind"))
                for r in valid
                if r.get("transition_type") == "manifest_receipt"
                and str(r.get("tick_id")) == str(expect_tick_id)
            }
            missing = {"pretick", "posttick"} - kinds
            if missing:
                return False, (
                    "missing chain-valid manifest_receipt(s): "
                    + ",".join(sorted(missing)))
            return True, (
                "receipt:forecast_tick_packet chain-valid start + "
                "pretick/posttick receipts bound to tick/contract")
        if kind == "judge":
            # The daemon signs a judge_verdict ONLY after verifying a
            # JUDGE-KEY signature over the execution proof + that
            # prompt_hash matches the prompt recomputed from the FROZEN
            # start_tick + total proof binding + committed cross-family
            # anchor (cold reviews baxgapbe9 / b1djdevru / boibujil4).
            # The mutator lacks the judge private key, so a chain-valid
            # daemon-signed judge_verdict provably required a real
            # separate judge run — not forgeable.
            #
            # `judge:auto` (the worker protocol): the agent does NOT
            # need to know the verdict's proposal_id. It submits the
            # witness with provenance `judge:auto`; the daemon emits a
            # signed judge_request, the out-of-loop ztare_judge worker
            # produces the verdict, and THIS resolver accepts the first
            # chain-valid PASS judge_verdict that binds this exact
            # (item_id, tick_id, contract_id, witness_sha). Id-free, so
            # there is no agent-coordination channel to game.
            from src.ztare.gates.stamped_state import chain_valid, _rows

            def _judge_row_ok(r: dict) -> tuple[bool, str]:
                if r.get("transition_type") != "judge_verdict":
                    return False, "row is not a judge_verdict transition"
                jid = str(r.get("judge_identity", "")).strip()
                bound = r.get("bound_obligations") or []
                if not jid:
                    return False, "no judge_identity"
                if item_id and item_id not in bound:
                    return False, f"does not bind obligation {item_id!r}"
                if substantive and (not expect_tick_id
                                    or not expect_contract_id
                                    or not expect_witness_sha):
                    return False, ("binding context not threaded "
                                   "(tick_id/contract_id/witness_sha)")
                if expect_tick_id and str(r.get("tick_id")) != str(
                        expect_tick_id):
                    return False, (f"bound to tick {r.get('tick_id')!r}"
                                   f", not {expect_tick_id!r} (replay)")
                if expect_contract_id and str(
                        r.get("contract_id")) != str(expect_contract_id):
                    return False, (f"bound to contract "
                                   f"{r.get('contract_id')!r}, not "
                                   f"{expect_contract_id!r} (replay)")
                if expect_witness_sha and str(
                        r.get("witness_sha")) != str(expect_witness_sha):
                    return False, ("witness_sha mismatch — verdict is "
                                   "for a DIFFERENT artifact (replay/"
                                   "substitution)")
                if str(r.get("verdict", "")).strip().lower() != "pass":
                    return False, (f"verdict is not 'pass' "
                                   f"({r.get('verdict')!r})")
                return True, (f"signed PASS judge_verdict (judge={jid}) "
                              f"bound to {item_id} @ {expect_tick_id}/"
                              f"{expect_contract_id}")

            valid, _ = chain_valid(_rows())
            if val == "auto":
                last = "no chain-valid PASS judge_verdict yet"
                for r in valid:
                    if r.get("transition_type") != "judge_verdict":
                        continue
                    ok, msg = _judge_row_ok(r)
                    if ok:
                        return True, f"judge:auto {msg}"
                    last = msg
                return False, (f"judge:auto pending — no chain-valid "
                               f"PASS judge_verdict bound to "
                               f"{item_id!r} @ {expect_tick_id}/"
                               f"{expect_contract_id} ({last})")
            for r in valid:
                if (str(r.get("proposal_id")) != val
                        and str(r.get("official_state_hash")) != val):
                    continue
                ok, msg = _judge_row_ok(r)
                return ok, f"judge:{val} {msg}"
            return False, f"judge:{val} not a chain-valid signed row"
        if substantive:
            return False, (f"substantive obligation requires a "
                           f"`judge:` verdict (got {kind!r}); "
                           f"stamped:/file:/catch: are payload refs "
                           f"only, not a discharge — cold-review "
                           f"b9is0a1fx fix #2)")
        if kind == "stamped":
            from src.ztare.gates.stamped_state import chain_valid, _rows
            valid, _ = chain_valid(_rows())
            if any(str(r.get("proposal_id")) == val
                   or str(r.get("official_state_hash")) == val
                   for r in valid):
                return True, f"stamped:{val} chain-valid signed row"
            return False, f"stamped:{val} not a chain-valid signed row"
        if kind == "catch":
            from src.ztare.common.paths import REPO_ROOT
            cl = (REPO_ROOT / "analytics/public/ledgers/catch/"
                  "catch_ledger.jsonl")
            for ln in cl.read_text(encoding="utf-8",
                                   errors="ignore").splitlines():
                try:
                    e = __import__("json").loads(ln)
                except Exception:
                    continue
                if str(e.get("catch_id")) == val:
                    a = str(e.get("author_agent", "")).strip()
                    c = str(e.get("concurring_agent", "")).strip()
                    if a and c and a != c:
                        return True, f"catch:{val} (author≠concurring)"
                    return False, (f"catch:{val} author==concurring "
                                   f"or empty (self-attest)")
            return False, f"catch:{val} not in catch ledger"
        if kind == "file":
            from src.ztare.common.paths import REPO_ROOT
            p = (REPO_ROOT / val)
            if p.is_file() and p.stat().st_size >= 400:
                return True, f"file:{val} ({p.stat().st_size}B)"
            return False, f"file:{val} missing or <400B (stub)"
    except Exception as e:
        return False, f"{kind}:{val} resolve error {type(e).__name__}"
    return False, f"unknown provenance kind {kind!r}"


def validate_tick_contract(goal: str, witnesses: dict | None,
                           why_not: dict | None,
                           transition_type: str = "",
                           declared: dict | None = None,
                           tick_id: str | None = None,
                           contract_id: str | None = None,
                           frozen_obligation_discharge: dict | None = None
                           ) -> tuple[bool, list]:
    """Un-forgeable: RECOMPUTES the contract from the goal + TYPED
    transition_type/declared signals. ANTI-GAMING FIX #1: each fired
    mandatory obligation needs a discharge (witness OR why_not) that
    BINDS TO A REAL EXTERNAL ARTIFACT via `provenance` —
    self-asserted free prose / bare why_not enum is REJECTED (that was
    the laundering hole the operator caught). The legitimate "this
    obligation does not apply" path is the obligation NOT FIRING (the
    typed signal is absent) — NOT dismissing a fired one by
    self-assertion."""
    witnesses = witnesses or {}
    why_not = why_not or {}
    contract = start_tick(goal, transition_type, declared or {})
    failures: list[str] = []
    for ob in contract.mandatory_obligations:
        iid = ob["item_id"]
        w = witnesses.get(iid)
        wn = why_not.get(iid)
        disc = w if isinstance(w, dict) else (
            wn if isinstance(wn, dict) else None)
        if disc is None:
            failures.append(
                f"{iid}: no discharge (need a witness OR why_not "
                f"dict, each with a resolving `provenance`)")
            continue
        # Every fired mandatory obligation is SUBSTANTIVE ⇒ its
        # discharge must bind to a `judge:` verdict (separate-agent,
        # obligation-bound, PASS, bound to THIS tick/contract and the
        # EXACT witness content). Fail-closed until the judge primitive
        # is wired (cold-review b9is0a1fx #2 + (d) replay-binding).
        _wsha = hashlib.sha256(json.dumps(
            {k: v for k, v in disc.items() if k != "provenance"},
            sort_keys=True, ensure_ascii=False).encode("utf-8")
        ).hexdigest()
        frozen_policy = (
            frozen_obligation_discharge.get(iid)
            if isinstance(frozen_obligation_discharge, dict)
            else None
        )
        policy = _normalize_discharge_policy(frozen_policy or ob.get("discharge"))
        allowed_receipts = set(policy.get("receipts") or [])
        substantive = policy.get("mode") != "receipt"
        prov_ok, prov_why = _resolve_provenance(
            disc.get("provenance"), item_id=iid, substantive=substantive,
            expect_tick_id=tick_id, expect_contract_id=contract_id,
            expect_witness_sha=_wsha, allowed_receipts=allowed_receipts)
        if not prov_ok:
            need = (
                "a daemon lifecycle receipt or separate-agent judge verdict"
                if allowed_receipts else "a separate-agent judge verdict"
            )
            failures.append(
                f"{iid}: discharge NOT bound to {need} "
                f"({prov_why}) — self-asserted prose / "
                f"bare why_not / unbound stamped|file|catch rejected "
                f"(anti-gaming fix #1+#2)")
            continue
        if isinstance(w, dict):
            req = ob.get("witness_schema", {}).get("required", [])
            missing = [r for r in req
                       if not str(w.get(r, "")).strip()]
            if missing:
                failures.append(
                    f"{iid}: witness missing required {missing}")
            continue
        if wn.get("reason") not in ob.get("why_not_enum", []):
            failures.append(
                f"{iid}: why_not.reason not in "
                f"{ob.get('why_not_enum', [])}")
    return (not failures), failures


def main() -> int:
    import sys
    goal = sys.argv[1] if len(sys.argv) > 1 else ""
    print(json.dumps(start_tick(goal).as_dict(), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
