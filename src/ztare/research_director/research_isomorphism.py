"""Research-director consumer of the Constraint-to-Isomorphism engine — out-of-loop edition.

Same canonical engine as leanmill (`ztare.common.constraint_isomorphism`), different domain plug.
The RD use is the operator's standing methodology (see AGENTS.md / memory: "abstract the frontier to
the operator-SEAM, find the field where that seam is already solved, transport the structure,
predict + falsify — never cite-and-launder"). This wires that as a reusable primitive.

KEY AUTHORITY DIFFERENCE FROM leanmill. leanmill has a cheap closed oracle (re-run an A/B, measure
closure/MDL on a holdout) so it can auto-complete the loop. A research ceiling does NOT — verifying
a transported structure IS a research experiment (forecast → test → falsify), human/RD-adjudicated,
not a millisecond holdout score. So the RD consumer is primarily a SURFACING tool: it runs Steps 1+2
(abstract the seam → query cross-field structural matches, in the DEANCHOR direction — forbid the
home field + adjacent) and logs candidates to a ledger for the RD to PRE-REGISTER a forecast on and
test. `compile_to_test`/`oracle` exist for interface-completeness but the oracle is ADVISORY
(returns "unverified — requires an RD experiment") unless a real forecast/experiment oracle is
injected. This preserves the RD boundary: no auto-laundering of a plausible analogy into a result.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

from ztare.common.conflict_ledger import ConflictClause
try:
    from ztare.common.constraint_isomorphism import (
        ConstraintFingerprint, ConstraintMorphism, IsomorphismLoop, SurfacedConjecture, SurfacedIsomorphism,
        default_llm_conjecture_query, prediction_specificity, validate_typed_mapping)
except Exception:  # pragma: no cover - installed package fallback
    from ztare.common.constraint_isomorphism import (
        ConstraintFingerprint, ConstraintMorphism, IsomorphismLoop, SurfacedConjecture, SurfacedIsomorphism,
        default_llm_conjecture_query, prediction_specificity, validate_typed_mapping)
try:
    from ztare.common.kernel_action_schema import KernelActionSchema
except Exception:  # pragma: no cover - installed package fallback
    from ztare.common.kernel_action_schema import KernelActionSchema
try:
    from ztare.common.structural_transfer_action import action_schema_from_isomorphism
except Exception:  # pragma: no cover - installed package fallback
    from ztare.common.structural_transfer_action import action_schema_from_isomorphism


@dataclass
class ResearchPrescription:
    """A surfaced cross-field structure transported to the research seam — a candidate to FORECAST
    and test, not a verified result (the gate, opaque to the engine)."""
    source_theorem: str
    source_field: str
    transported_structure: str   # how its mechanism maps onto the seam
    predict_then_falsify: str     # the concrete prediction whose failure would refute the transport
    action_schema: dict | None = None
    spec_patch: dict | None = None   # optional WORLD_MODEL_SPEC fragment: when the transported structure
    #   compiles to a catalog rule family, carrying it here lets worldmodel_oracle lower + replay-score it
    #   (a closed oracle for the worldmodel substrate). None → the oracle stays advisory (0.0).


class ResearchDomain:
    """`StrangeLoopDomain` for an out-of-loop research ceiling. The oracle is ADVISORY by default —
    inject a real forecast/experiment scorer to close the loop; otherwise this surfaces candidates."""

    def __init__(self, oracle_fn: "Optional[Callable[[object, object], float]]" = None):
        self._oracle_fn = oracle_fn

    def abstract_failure(self, failure_state: dict) -> ConstraintFingerprint:
        """`failure_state` = the seam abstracted to operator-neutral structure, e.g.
        {"constraint_class": "off-diagonal decay of a divergence-free kernel under critical scaling",
         "abstract_form": "...", "home_field": "fluid PDE"}. We strip it to a fingerprint and set
        the home field as forbidden (deanchor → find where this seam is ALREADY solved elsewhere)."""
        fs = failure_state or {}
        return ConstraintFingerprint(
            constraint_class=fs.get("constraint_class", "an unresolved structural seam"),
            abstract_form=fs.get("abstract_form", ""),
            invariants={k: v for k, v in fs.items()
                        if k not in ("constraint_class", "abstract_form", "home_field")},
            forbidden_domain=fs.get("home_field"))  # deanchor away from the research's home discipline

    def compile_to_test(self, iso: SurfacedIsomorphism, context: object) -> ResearchPrescription:
        action_schema = action_schema_from_isomorphism(iso, source_kind="research_isomorphism")
        if iso.morphism is not None:
            morphism = iso.morphism if isinstance(iso.morphism, ConstraintMorphism) else ConstraintMorphism.from_dict(iso.morphism)
            payload = action_schema.setdefault("payload", {})
            payload["constraint_morphism"] = morphism.to_dict()
            payload["transport_validation"] = dict(iso.transport_validation or {})
        return ResearchPrescription(
            source_theorem=iso.theorem, source_field=iso.field,
            transported_structure=iso.mapping_hint or iso.mechanism,
            predict_then_falsify=f"if the {iso.theorem} structure transports, it predicts a sharp, "
                                 "checkable consequence at the seam; its failure refutes the transport",
            action_schema=action_schema)

    def oracle(self, gate: "object | None", holdout: object) -> float:
        if self._oracle_fn is not None:
            return self._oracle_fn(gate, holdout)
        return 0.0  # advisory: a research transport is verified by an RD experiment, not a cheap score

    def banned_terms(self) -> "list[str]":
        return []  # the RD seam is already abstracted by the author; no fixed home vocabulary to ban


def worldmodel_oracle(project_dir) -> "Callable[[object, object], float]":
    """The CLOSED oracle the research docstring says a seam lacks — but the WORLDMODEL substrate HAS one
    (replay gates, milliseconds). Returns an `oracle_fn(gate, holdout)` to inject into ResearchDomain.

    EXPLICIT about what it can check. `gate` is a ResearchPrescription; the oracle scores >0 ONLY when the
    prescription carries a `spec_patch` (a WORLD_MODEL_SPEC fragment) that COMPILES to a catalog rule
    family (spec_catalog.lower_spec) AND that lowered law actually explains recorded evidence: it replays
    the law against the project's episode log and returns the fraction of transitions explained (rollout
    depth / length, 0..1). No spec_patch, a spec that fails to lower, or no log → 0.0 (advisory, the
    unchanged default). This is the no-laundering contract: a transported analogy only scores when it
    becomes a checkable law that fits the data — never on prose alone."""
    from pathlib import Path as _P

    def oracle_fn(gate, holdout) -> float:
        spec = getattr(gate, "spec_patch", None)
        if not spec:
            return 0.0
        from ztare.worldmodel.adapter import episode_log_path
        from ztare.worldmodel.episode_log import EpisodeLog
        from ztare.worldmodel.gates import rollout_depth
        from ztare.worldmodel.spec_catalog import lower_spec
        step, _err = lower_spec(spec)
        if step is None:
            return 0.0
        log_path = episode_log_path(_P(project_dir))
        if not log_path.exists():
            return 0.0
        log = EpisodeLog.read_jsonl(log_path)
        return rollout_depth(step, log) / max(1, len(log))

    return oracle_fn


_LEDGER = Path("analytics/queries/research_isomorphism_candidates.jsonl")
_DICTIONARY = Path("analytics/queries/research_isomorphism_dictionary.jsonl")


def _morphism_record_fields(iso: SurfacedIsomorphism) -> dict:
    if iso.morphism is None:
        return {"constraint_morphism": None, "transport_validation": dict(iso.transport_validation or {})}
    morphism = iso.morphism if isinstance(iso.morphism, ConstraintMorphism) else ConstraintMorphism.from_dict(iso.morphism)
    return {
        "constraint_morphism": morphism.to_dict(),
        "transport_validation": dict(iso.transport_validation or {}),
    }


def _action_schema_with_transport(iso: SurfacedIsomorphism, fp: ConstraintFingerprint, *, transfer_mode: str) -> dict:
    action = action_schema_from_isomorphism(
        iso,
        fp,
        source_kind="research_isomorphism",
        transfer_mode=transfer_mode,
    )
    fields = _morphism_record_fields(iso)
    if fields["constraint_morphism"] is not None:
        action.setdefault("payload", {})["constraint_morphism"] = fields["constraint_morphism"]
        action["payload"]["transport_validation"] = fields["transport_validation"]
    return action


def surface_for_research_ceiling(failure_state: dict, *, n: int = 5, query=None,
                                 ledger: "Path | None" = _LEDGER) -> "list[SurfacedIsomorphism]":
    """The primary RD use: abstract a seam (Step 1) → query cross-field structural matches in the
    DEANCHOR direction (Step 2) → log candidates for the RD to pre-register a forecast on and test.
    Returns the surfaced candidates (verification is the RD's experiment, NOT done here)."""
    dom = ResearchDomain()
    fp = dom.abstract_failure(failure_state)
    isos = (IsomorphismLoop(dom, query=query).query(fp, n)) or []
    if ledger is not None and isos:
        try:
            ledger.parent.mkdir(parents=True, exist_ok=True)
            with ledger.open("a", encoding="utf-8") as f:
                for iso in isos:
                    row = {"constraint_class": fp.constraint_class,
                           "forbidden_domain": fp.forbidden_domain,
                           "theorem": iso.theorem, "field": iso.field,
                           "mechanism": iso.mechanism, "mapping_hint": iso.mapping_hint,
                           "enrichment": iso.enrichment,
                           **_morphism_record_fields(iso),
                           "action_schema": _action_schema_with_transport(
                               iso,
                               fp,
                               transfer_mode="deanchor" if fp.forbidden_domain else "analogy",
                           )}
                    row["candidate_hash"] = _candidate_content_hash(row)
                    f.write(json.dumps(row) + "\n")
        except Exception:
            pass
    return isos


def _provider_and_model(model: str) -> "tuple[str, str | None]":
    """Map a user-selected model FAMILY → the (provider, model_id) the isomorphism query needs, honoring
    the repo transport policy so there are NO surprises: Claude → subscription CLI; GPT/o-series →
    subscription CLI (never a metered OpenAI call); everything else (gemini/deepseek/kimi/grok/…) → API
    with the EXACT resolved id, so the query never silently falls back to gemini. Returns (provider, mid):
    mid=None means "let the provider's subscription runtime choose"."""
    fam = (model or "gemini").strip().lower()
    if fam.startswith("claude"):
        return "claude", None
    if fam == "codex":
        return "codex", None
    if fam.startswith("codex:"):
        return "codex", (fam.split(":", 1)[1].strip() or None)
    if fam.startswith(("gpt", "o1", "o3", "o4")) or fam in {"sol", "terra", "luna"}:
        try:
            from ztare.common.llm_runtime import resolve_model_id
            return "codex", resolve_model_id(fam)
        except Exception:
            return "codex", fam
    try:
        from ztare.common.llm_runtime import resolve_model_id
        return fam, resolve_model_id(fam)
    except Exception:
        return "gemini", None


def _parse_invariant_args(items: "list[str] | None") -> dict:
    invariants = {}
    for raw in items or []:
        if "=" not in raw:
            raise ValueError(f"invariant must be KEY=VALUE, got {raw!r}")
        key, value = raw.split("=", 1)
        key = key.strip()
        if not key:
            raise ValueError(f"invariant key is empty in {raw!r}")
        invariants[key] = value.strip()
    return invariants


def _failure_state_for_seam(
    constraint_class: str,
    *,
    abstract_form: str = "",
    home_field: str = "",
    invariants: "dict | None" = None,
) -> dict:
    failure_state = {"constraint_class": constraint_class, "abstract_form": abstract_form}
    if home_field:
        failure_state["home_field"] = home_field  # deanchor away from the project's own field
    if invariants:
        failure_state.update(invariants)
    return failure_state


_DOMAIN_STOPWORDS = {
    "and", "any", "already", "answer", "domain", "field", "fields", "from", "home",
    "not", "of", "or", "the", "these", "this", "also", "surfaced",
}


def _domain_tokens(value: object) -> set[str]:
    import re

    return {
        token for token in re.findall(r"[a-z0-9]+", str(value or "").lower())
        if len(token) > 2 and token not in _DOMAIN_STOPWORDS
    }


def _domain_families(value: object) -> set[str]:
    tokens = _domain_tokens(value)
    families: set[str] = set()
    if "pde" in tokens or {"partial", "differential", "equation"} <= tokens or "fluid" in tokens:
        families.add("pde")
    if "itp" in tokens or "lean" in tokens or {"theorem", "proving"} <= tokens:
        families.add("theorem_proving")
    if "arc" in tokens or {"grid", "world"} <= tokens:
        families.add("grid_reasoning")
    if "autoresearch" in tokens or {"automated", "research"} <= tokens:
        families.add("autoresearch")
    return families


def candidate_uses_forbidden_domain(iso: SurfacedIsomorphism, fp: ConstraintFingerprint) -> bool:
    """Mechanically reject answers sourced from the field the query excluded."""

    forbidden = str(fp.forbidden_domain or "").strip()
    candidate_field = str(iso.field or "").strip()
    if not forbidden:
        return False
    if not candidate_field:
        return True
    forbidden_norm = " ".join(_domain_tokens(forbidden))
    candidate_norm = " ".join(_domain_tokens(candidate_field))
    if candidate_norm and candidate_norm in forbidden_norm:
        return True
    if _domain_families(forbidden) & _domain_families(candidate_field):
        return True
    distinctive_overlap = _domain_tokens(forbidden) & _domain_tokens(candidate_field)
    return bool(distinctive_overlap)


# ─────────────────────────────────────────────────────────────────────────────
# α → fingerprint: machine-induced structure as the query point (2026-07-03)
# ─────────────────────────────────────────────────────────────────────────────
# The fingerprint was always HAND-written — the operator eyeballs a seam and types
# a constraint_class, which anchors the query on the author's own framing (the home
# surface). These converters close α→fingerprint: evidence-induced structure becomes
# the query point, de-anchoring retrieval from the home surface. The worldmodel's
# induced ROLES (object_roles.induce_roles) and abduced LAW (spec_abduction.
# abduce_spec) — structure read from evidence, zero model calls — render straight
# into a failure_state. DETERMINISTIC: same structure in, same fingerprint out.
# OPERATOR-NEUTRAL by construction: behavioral role labels ("moves_under_actions",
# "monotone_depleting", …) and catalog ops ("translate_block", "consume_extremal", …)
# map to substrate-free nouns (mover, resource, boundary, terrain, guard, consumption)
# so Step 2 retrieves a FORM, never the grid surface the structure was induced from.


def _unwrap_structure(roles, spec):
    """Tolerate being handed the raw induce_roles / abduce_spec results (an
    AbstractState with `.roles`, an AbductionResult with `.spec`) instead of the
    already-unwrapped list/dict — so callers need not peel them first."""
    if roles is not None and hasattr(roles, "roles"):
        roles = roles.roles
    if spec is not None and hasattr(spec, "spec"):
        spec = spec.spec
    return roles, spec


def _structure_facts(roles, spec) -> dict:
    """The single fact table both the fingerprint and its cuts read from: which
    behavioral ROLES are present (by name) and which catalog OPS/GUARDS the abduced
    law uses. Pure booleans — the operator-neutral vocabulary is chosen downstream,
    so this stays evidence, not prose."""
    roles = roles or []
    spec = spec or {}
    names = {getattr(r, "name", "") for r in roles}
    ops: "set[str]" = set()
    gated = restoration = when_count = consume_count = paused = False
    buckets = list((spec.get("actions") or {}).values()) + [spec.get("always") or []]
    for bucket in buckets:
        for rule in (bucket or []):
            op = rule.get("op")
            if op:
                ops.add(op)
            if op == "translate_block" and (rule.get("require_dest_colors")
                                            or rule.get("component_min_colors")):
                gated = True
            if rule.get("fill_color") == "surround":
                restoration = True
            if "when_count" in rule:
                when_count = True
            if op == "consume_extremal" and rule.get("count"):
                consume_count = True
            if op == "identity":
                paused = True
    return {
        "resource": "monotone_depleting" in names,
        "mover": ("moves_under_actions" in names) or ("translate_block" in ops),
        "translate_op": "translate_block" in ops,
        "consume_op": "consume_extremal" in ops,
        "relabel_op": "recolor_map" in ops,
        "boundary": "never_changes" in names,
        "terrain": "covered_uncovered" in names,
        "marker": "static_structural_mirror" in names,
        "gated": gated,
        "consume_count": consume_count,
        "when_count": when_count,
        "restoration": restoration,
        "paused": paused or when_count,
    }


def _oxford(items: "list[str]") -> str:
    if len(items) <= 1:
        return "".join(items)
    if len(items) == 2:
        return f"{items[0]} and {items[1]}"
    return ", ".join(items[:-1]) + ", and " + items[-1]


def _terrain_phrase(f: dict) -> str:
    if f["boundary"] and f["terrain"]:
        return " through a fixed boundary and reactive terrain"
    if f["boundary"]:
        return " through a fixed boundary"
    if f["terrain"]:
        return " across reactive terrain"
    return ""


def _tail_phrase(f: dict) -> str:
    bits = []
    if f["paused"]:
        bits.append("a state-dependent pause")
    if f["restoration"]:
        bits.append("terrain restoration")
    if f["marker"]:
        bits.append("a static goal marker")
    return (", with " + _oxford(bits)) if bits else ""


def _mover_law_phrase(f: dict) -> str:
    if f["translate_op"] and f["gated"]:
        return "a guarded rigid translation of a mover"
    if f["translate_op"]:
        return "a rigid translation of a mover"
    return "a translation of a mover"


def _conservation_sentence(f: dict) -> str:
    """The invariant-level cut: conservation/monotonicity facts only, mechanism
    stripped — the shape that survives whatever the operators turn out to be."""
    bits = []
    if f["resource"]:
        bits.append("a quantity that only ever depletes")
    if f["boundary"]:
        bits.append("a boundary that never changes")
    if f["terrain"]:
        bits.append("terrain conserved except where a mover covers it")
    if f["marker"]:
        bits.append("an invariant goal marker")
    return ("conservation only — " + _oxford(bits)) if bits else \
        "the structure carries no conserved or monotone quantity"


def _constraint_class_sentence(f: dict) -> str:
    """One operator-neutral sentence composed from what is actually present (roles,
    ops, guards). Never mentions the induction substrate."""
    thru, tail = _terrain_phrase(f), _tail_phrase(f)
    if f["mover"]:
        law = _mover_law_phrase(f)
        if f["resource"]:
            verb = "gates" if f["paused"] else "accompanies"
            return f"a monotonically depleting resource {verb} {law}{thru}{tail}"
        return f"{law}{thru}{tail}"
    if f["resource"] and f["consume_op"]:
        return f"a monotonically depleting resource undergoing extremal consumption{thru}{tail}"
    if f["relabel_op"]:
        return f"a global relabeling of the field{thru}{tail}"
    # roles present but no induced law: name the co-occurring structure
    nouns = []
    if f["resource"]:
        nouns.append("a monotonically depleting resource")
    if f["boundary"]:
        nouns.append("a fixed boundary")
    if f["terrain"]:
        nouns.append("reactive terrain")
    if f["marker"]:
        nouns.append("a static goal marker")
    if not nouns:
        return "an unresolved induced structure"
    if len(nouns) == 1:
        return f"{nouns[0]} with no induced law"
    return f"{_oxford(nouns)} co-occur under an as-yet-uninduced law"


def _structure_invariants(f: dict, residual=None) -> dict:
    """The sharp structural facts typed_mapping validates against — few (<=6),
    key=short-phrase. A supplied residual is always kept (the open question is the
    point of the query); the structural facts yield to it if the cap would blow."""
    inv = []
    if f["resource"]:
        inv.append(("resource_direction", "monotone_nonincreasing"))
    if f["mover"]:
        inv.append(("mover_arity",
                    "guarded_translation" if (f["translate_op"] and f["gated"])
                    else "rigid_translation" if f["translate_op"] else "translation"))
    if f["when_count"]:
        inv.append(("guard_family", "threshold_on_global_count"))
    if f["consume_op"]:
        inv.append(("consumption", "extremal_count" if f["consume_count"] else "extremal"))
    if f["relabel_op"] and not f["translate_op"]:
        inv.append(("relabeling", "global"))
    passive = [n for n, on in (("fixed_boundary", f["boundary"]),
                               ("reactive_terrain", f["terrain"]),
                               ("static_goal_marker", f["marker"])) if on]
    if passive:
        inv.append(("passive_structure", "+".join(passive)))
    inv = (inv[:5] + [("unresolved_residual", str(residual))]) if residual else inv[:6]
    return dict(inv)


def fingerprint_dict_from_structure(roles=None, spec=None, residual=None,
                                    home_field: str = "") -> dict:
    """α→fingerprint closes the loop: evidence-induced structure becomes the query
    point, de-anchoring retrieval from the home surface. DETERMINISTIC (no LLM) —
    turns worldmodel ROLES (induce_roles) and an abduced LAW (abduce_spec) into a
    failure_state dict consumable by `abstract_failure` / `surface_multicut`.
    Operator-neutral by construction (mover/resource/boundary/terrain/guard/
    consumption — the grid surface never leaks). `roles`/`spec` may be the raw
    AbstractState/AbductionResult or the unwrapped list/dict; neither -> ValueError."""
    roles, spec = _unwrap_structure(roles, spec)
    if not roles and not spec:
        raise ValueError("need induced roles and/or an abduced spec — got neither")
    f = _structure_facts(roles, spec)
    return _failure_state_for_seam(_constraint_class_sentence(f), home_field=home_field,
                                   invariants=_structure_invariants(f, residual))


def cuts_from_structure(roles=None, spec=None, residual=None,
                        home_field: str = "") -> "list[dict]":
    """The SAME induced structure cut several ways for `surface_multicut` (one cut
    reaches one latent neighborhood — its surviving nouns steer retrieval): (a)
    MECHANISM-level (the induced ops + guards), (b) INVARIANT-level (conservation/
    monotonicity only — the facts that survive any mechanism), and (c) FAILURE-MODE-
    level, ONLY when a `residual` is supplied (what the induced law leaves
    undetermined — the sharpest query point). Reuses fingerprint_dict_from_structure
    for the base fingerprint + validation (DRY). Returns 2 cuts, or 3 with a residual."""
    base = fingerprint_dict_from_structure(roles, spec, residual, home_field)  # also validates
    roles, spec = _unwrap_structure(roles, spec)
    f = _structure_facts(roles, spec)
    inv = {k: v for k, v in base.items()
           if k not in ("constraint_class", "abstract_form", "home_field")}

    def _pick(keys):
        return {k: inv[k] for k in keys if k in inv}

    cuts = [
        # (a) mechanism: the induced law and its guards
        _failure_state_for_seam(base["constraint_class"], home_field=home_field,
                                invariants=_pick(("mover_arity", "guard_family",
                                                  "consumption", "relabeling"))),
        # (b) invariant: conservation / monotonicity, mechanism stripped
        _failure_state_for_seam(_conservation_sentence(f), home_field=home_field,
                                invariants=_pick(("resource_direction", "passive_structure"))),
    ]
    if residual:
        # (c) failure-mode: what the current law fails to determine
        cuts.append(_failure_state_for_seam(
            f"the induced law leaves this undetermined: {residual}", home_field=home_field,
            invariants={"unresolved_residual": str(residual)}))
    return cuts


def prescribe_for_seam(
    constraint_class: str,
    *,
    abstract_form: str = "",
    home_field: str = "",
    model: str = "gemini",
    n: int = 5,
    invariants: "dict | None" = None,
    typed_mapping: bool = False,
    mode: str = "solve",
) -> dict:
    """Workbench "what is this like?": surface cross-field analogies for a research seam and compile
    the top one to a forecastable prescription. `model` is the user's selected model family (global
    settings); it routes per the repo's API/subscription policy (see `_provider_and_model`) so the
    user's pick is honored without surprise. Advisory — a candidate to forecast and test, never a
    verified result. ledger=None: an exploratory UI click is not an RD disposition, so don't pollute
    the candidate ledger. ponytail: flip to _LEDGER if these clicks should be tracked."""
    failure_state = _failure_state_for_seam(
        constraint_class,
        abstract_form=abstract_form,
        home_field=home_field,
        invariants=invariants,
    )
    query = None
    if model:
        from ztare.common.constraint_isomorphism import default_llm_query
        prov, mid = _provider_and_model(model)
        query = lambda fp, k: default_llm_query(  # noqa: E731
            fp,
            k,
            provider=prov,
            model=mid,
            typed_mapping=typed_mapping,
            mode=mode,
        )
    fp = ResearchDomain().abstract_failure(failure_state)
    raw_isos = surface_for_research_ceiling(failure_state, n=n, query=query, ledger=None)
    rejected_forbidden = [iso for iso in raw_isos if candidate_uses_forbidden_domain(iso, fp)]
    isos = [iso for iso in raw_isos if not candidate_uses_forbidden_domain(iso, fp)]
    rejected_typed: list[SurfacedIsomorphism] = []
    if typed_mapping:
        isos, rejected_typed = validate_typed_mapping(isos, fp)
    if not isos:
        return {}
    rx = ResearchDomain().compile_to_test(isos[0], None)
    top = isos[0]
    morphism_payload = None
    if top.morphism is not None:
        morphism = top.morphism if isinstance(top.morphism, ConstraintMorphism) else ConstraintMorphism.from_dict(top.morphism)
        morphism_payload = morphism.to_dict()
    return {"source_theorem": rx.source_theorem, "source_field": rx.source_field,
            "transported_structure": rx.transported_structure,
            "predict_then_falsify": rx.predict_then_falsify,
            "candidate_count": len(isos),
            "rejected_forbidden_count": len(rejected_forbidden),
            "rejected_typed_count": len(rejected_typed),
            "transport_validation": dict(top.transport_validation or {}),
            "constraint_morphism": morphism_payload,
            "alternatives": [{"theorem": i.theorem, "field": i.field} for i in isos[1:4]]}


def _run_debug_dispatch(dispatch, prompt: str, *, provider: str, model: "str | None") -> "tuple[str, dict]":
    """One dispatch only; injected callables keep tests and offline tools hermetic."""

    if dispatch is None:
        from ztare.common.constraint_isomorphism import _dispatch_text_with_receipt

        dispatch = _dispatch_text_with_receipt
    result = dispatch(prompt, provider=provider, model=model)
    if isinstance(result, tuple) and len(result) == 2:
        text, receipt = result
        return str(text or ""), dict(receipt or {}) if isinstance(receipt, dict) else {}
    text = str(result or "")
    return text, {
        "transport": "injected",
        "provider": provider,
        "model": model,
        "returncode": 0,
        "stdout_chars": len(text),
    }


def debug_query_for_seam(
    constraint_class: str,
    *,
    abstract_form: str = "",
    home_field: str = "",
    model: str = "gemini",
    n: int = 5,
    invariants: "dict | None" = None,
    typed_mapping: bool = False,
    mode: str = "solve",
    dispatch=None,
) -> dict:
    """Run the CLI query path with observable dispatch/parse diagnostics."""
    import json as _json
    import re as _re

    from ztare.common.constraint_isomorphism import _build_query_prompt, _parse_isomorphisms

    failure_state = _failure_state_for_seam(
        constraint_class,
        abstract_form=abstract_form,
        home_field=home_field,
        invariants=invariants,
    )
    fp = ResearchDomain().abstract_failure(failure_state)
    prov, mid = _provider_and_model(model)
    prompt = _build_query_prompt(fp, n, typed_mapping=typed_mapping, mode=mode)
    text, dispatch_receipt = _run_debug_dispatch(dispatch, prompt, provider=prov, model=mid)
    result = {
        "provider": prov,
        "model": mid,
        "dispatch_receipt": dispatch_receipt,
        "mode": mode,
        "typed_mapping": typed_mapping,
        "n": n,
        "prompt_len": len(prompt),
        "text_len": len(text or ""),
        "text_head": (text or "")[:500],
        "parse_status": "not_attempted",
        "model_configured": None,
        "dispatch_error_probe": None,
        "candidate_count": 0,
        "rejected_forbidden_count": 0,
        "rejected_typed_count": 0,
        "candidates": [],
    }
    if not text:
        result["parse_status"] = "no_text_from_dispatch"
        return result
    m = _re.search(r"\[.*\]", text, _re.S)
    if not m:
        result["parse_status"] = "no_json_list_in_text"
        return result
    try:
        items = _json.loads(m.group(0))
    except Exception as exc:  # noqa: BLE001
        result["parse_status"] = f"json_parse_error:{type(exc).__name__}"
        return result
    if not isinstance(items, list):
        result["parse_status"] = "json_root_not_list"
        return result
    parsed = _parse_isomorphisms(m.group(0))
    forbidden = [iso for iso in parsed if candidate_uses_forbidden_domain(iso, fp)]
    parsed = [iso for iso in parsed if not candidate_uses_forbidden_domain(iso, fp)]
    typed_rejected: list[SurfacedIsomorphism] = []
    if typed_mapping:
        parsed, typed_rejected = validate_typed_mapping(parsed, fp)
    candidates = [
        {
            "theorem": iso.theorem,
            "field": iso.field,
            "transport_validation": dict(iso.transport_validation or {}),
            "constraint_morphism": _morphism_record_fields(iso)["constraint_morphism"],
        }
        for iso in parsed
    ]
    result["parse_status"] = "parsed"
    result["candidate_count"] = len(candidates)
    result["rejected_forbidden_count"] = len(forbidden)
    result["rejected_typed_count"] = len(typed_rejected)
    result["candidates"] = candidates
    return result


def debug_conjecture_for_seams(
    left_state: dict,
    right_state: dict,
    *,
    model: str = "gemini",
    n: int = 5,
    min_specificity: float = 0.25,
    timeout_s: int = 180,
    dispatch=None,
) -> dict:
    """Observable conjecture-mode dispatch/parse/schema diagnostics."""
    import json as _json
    import re as _re

    from ztare.common.constraint_isomorphism import (
        _build_conjecture_prompt,
        _parse_conjectures,
    )

    dom = ResearchDomain()
    left = dom.abstract_failure(dict(left_state or {}))
    right = dom.abstract_failure(dict(right_state or {}))
    prov, mid = _provider_and_model(model)
    prompt = _build_conjecture_prompt(left, right, n)
    if dispatch is None:
        from ztare.common.constraint_isomorphism import _dispatch_text_with_receipt

        dispatch = lambda value, *, provider, model: _dispatch_text_with_receipt(  # noqa: E731
            value, provider=provider, model=model, timeout_s=timeout_s
        )
    text, dispatch_receipt = _run_debug_dispatch(
        dispatch, prompt, provider=prov, model=mid
    )
    result = {
        "provider": prov,
        "model": mid,
        "dispatch_receipt": dispatch_receipt,
        "mode": "conjecture",
        "n": n,
        "prompt_len": len(prompt),
        "text_len": len(text or ""),
        "text_head": (text or "")[:500],
        "parse_status": "not_attempted",
        "raw_candidate_count": 0,
        "candidate_count": 0,
        "rejected_count": 0,
        "candidates": [],
        "rejected": [],
    }
    if not text:
        result["parse_status"] = "no_text_from_dispatch"
        return result
    m = _re.search(r"\[.*\]", text, _re.S)
    if not m:
        result["parse_status"] = "no_json_list_in_text"
        return result
    try:
        items = _json.loads(m.group(0))
    except Exception as exc:  # noqa: BLE001
        result["parse_status"] = f"json_parse_error:{type(exc).__name__}"
        return result
    if not isinstance(items, list):
        result["parse_status"] = "json_root_not_list"
        return result
    raw = _parse_conjectures(m.group(0))
    result["parse_status"] = "parsed"
    result["raw_candidate_count"] = len(raw)
    kept, rejected = [], []
    for conj in raw:
        if _conjecture_survives_schema(
            conj,
            left,
            right,
            min_specificity=min_specificity,
            require_prior_art_inversion=True,
        ):
            kept.append(conj)
        else:
            rejected.append(conj)
    result["candidate_count"] = len(kept)
    result["rejected_count"] = len(rejected)
    result["candidates"] = [
        {
            "mother_structure": c.mother_structure,
            "specificity": c.specificity,
            "prediction_cards": _prediction_cards(c),
            "prior_art_inversion": c.prior_art_inversion,
        }
        for c in kept
    ]
    result["rejected"] = [
        {"mother_structure": c.mother_structure, "specificity": c.specificity}
        for c in rejected
    ]
    return result


class RefutedPatternsLedger:
    def __init__(self, ledger: "Path | None" = _LEDGER):
        self.ledger = ledger

    def learn(self, conflict_receipt) -> ConflictClause:
        row = dict(conflict_receipt or {})
        self.ledger.parent.mkdir(parents=True, exist_ok=True)
        rows = []
        if self.ledger.exists():
            rows = [json.loads(l) for l in self.ledger.read_text(encoding="utf-8").splitlines() if l.strip()]
        rows.append(row)
        self.ledger.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
        return ConflictClause(
            signature=_cand_key(row),
            receipts_refs=tuple(),
            witness_summary=str(row.get("note") or row.get("witness_summary") or ""),
            provenance=row.get("provenance") or "research_isomorphism.refuted_patterns",
            defeasible=bool(row.get("status") != "refuted"),
        )

    def blocks(self, candidate_signature: str) -> "ConflictClause | None":
        try:
            rows = [json.loads(l) for l in self.ledger.read_text(encoding="utf-8").splitlines() if l.strip()]
        except FileNotFoundError:
            return None  # no ledger yet — nothing refuted, by design
        except Exception as exc:  # noqa: BLE001 — fail closed: a corrupt ledger must not unblock refuted transports
            return ConflictClause(
                signature=candidate_signature,
                witness_summary=f"refuted-patterns ledger unreadable, failing closed: {type(exc).__name__}: {exc}",
                provenance="research_isomorphism.refuted_patterns.ledger_unreadable",
                defeasible=False,
            )
        for row in rows:
            if row.get("disposition_for") == candidate_signature or _cand_key(row) == candidate_signature:
                if row.get("status") in ("refuted", "stale"):
                    return ConflictClause(
                        signature=candidate_signature,
                        receipts_refs=tuple(),
                        witness_summary=str(row.get("note") or ""),
                        provenance="research_isomorphism.refuted_patterns",
                        defeasible=True,
                    )
        return None

    def revive(self, evidence_card):
        return evidence_card

    def open_clauses(self) -> list[ConflictClause]:
        try:
            rows = [json.loads(l) for l in self.ledger.read_text(encoding="utf-8").splitlines() if l.strip()]
        except FileNotFoundError:
            return []  # no ledger yet — nothing refuted, by design
        except Exception as exc:  # noqa: BLE001 — fail closed with a witness, never a silent empty
            return [ConflictClause(
                signature="refuted_patterns:ledger-unreadable",
                witness_summary=f"refuted-patterns ledger unreadable, failing closed: {type(exc).__name__}: {exc}",
                provenance="research_isomorphism.refuted_patterns.ledger_unreadable",
                defeasible=False,
            )]
        return [ConflictClause(signature=_cand_key(r), receipts_refs=tuple(), witness_summary=r.get("note", ""),
                                provenance="research_isomorphism.refuted_patterns",
                                defeasible=bool(r.get("status") != "refuted"))
                for r in rows if r.get("status") in ("refuted", "stale")]


def refuted_patterns(*, ledger: "Path | None" = None, limit: int = 8) -> "list[str]":
    """Refuted/stale transports from the disposition ledger — fed BACK into the query as no-goods so the
    engine stops resurfacing known-dead shapes (the no_good_store discipline applied to analogies; e.g.
    parallel-makespan scheduling was refuted for the serial-Lean substrate and should never come back)."""
    led = ledger if ledger is not None else _LEDGER
    try:
        rows = [json.loads(l) for l in led.read_text(encoding="utf-8").splitlines() if l.strip()]
    except FileNotFoundError:
        return []  # no ledger yet — nothing refuted, by design
    except (OSError, ValueError) as exc:
        # fail closed with a visible sentinel line, never a silent empty
        return [
            "REFUTED-PATTERNS LEDGER UNREADABLE "
            f"({type(exc).__name__}: {exc}) — prior refutations still in force; "
            "do not resurface previously refuted transports"
        ]
    by_key = {_cand_key(r): r for r in rows if not r.get("disposition_for")}
    out = []
    for r in rows:
        if r.get("status") in ("refuted", "stale") and r.get("disposition_for") in by_key:
            c = by_key[r["disposition_for"]]
            out.append(f"{c.get('theorem')} ({c.get('field')}): {r.get('note', '')[:120]}")
    return out[-limit:]


def surface_multicut(cuts: "list[dict]", *, n_per_cut: int = 4, query=None,
                     ledger: "Path | None" = _LEDGER, feedback: bool = True) -> "list[SurfacedIsomorphism]":
    """MULTI-CUT surfacing (2026-06-12 introspective upgrade): the FINGERPRINT is the quality bottleneck —
    one abstraction cut of a seam reaches one latent neighborhood (its surviving nouns steer retrieval).
    Query the SAME seam under several cuts (mechanism-level / invariant-level / failure-mode-level) and
    merge, deduped by (theorem, field). Each cut also carries the ledger's refuted/stale transports as
    do-not-resurface no-goods (`feedback=True`). Returns the merged candidate list (dispositions are the
    follow-through, as ever)."""
    seen: "set[tuple]" = set()
    merged: "list[SurfacedIsomorphism]" = []
    nogood = refuted_patterns(ledger=ledger) if feedback else []
    for cut in cuts:
        fs = dict(cut)
        if nogood:
            # top-level extra keys land in the fingerprint's `invariants` (see abstract_failure) →
            # rendered under STRUCTURAL INVARIANTS in the engine prompt, visible to the model
            fs["do_not_resurface_refuted_transports"] = nogood
        for iso in surface_for_research_ceiling(fs, n=n_per_cut, query=query, ledger=ledger):
            k = (iso.theorem, iso.field)
            if k not in seen:
                seen.add(k)
                merged.append(iso)
    merged.sort(key=lambda i: (i.enrichment is None, -(i.enrichment or 0.0)))  # graded first, None last
    return merged


def diversity_query(providers: "tuple[str, ...]" = ("gemini", "deepseek"), *,
                    typed_mapping: bool = True, mode: str = "solve",
                    rejected_sink: "Optional[list]" = None):
    """Query-factory (#122 leg 5): fan the structural query across DIVERSE providers and merge,
    deduped by (theorem, field) — one model's candidates correlate (the forecast-pool lesson). With
    `typed_mapping`, each provider's candidates are MECHANICALLY validated against the fingerprint's
    invariants (decorative analogies die at the schema); rejects go to `rejected_sink` (audit, never
    silent)."""
    def q(fp, n):
        from ztare.common.constraint_isomorphism import default_llm_query, validate_typed_mapping
        seen, out = set(), []
        for p in providers:
            isos = default_llm_query(fp, n, provider=p, typed_mapping=typed_mapping, mode=mode)
            if typed_mapping:
                isos, rej = validate_typed_mapping(isos, fp)
                if rejected_sink is not None:
                    rejected_sink.extend(rej)
            for iso in isos:
                k = (iso.theorem.lower()[:48], iso.field.lower()[:24])
                if k not in seen:
                    seen.add(k)
                    out.append(iso)
        return out
    return q


def surface_upgraded(cuts: "list[dict]", *, n_per_cut: int = 4,
                     providers: "tuple[str, ...]" = ("gemini", "deepseek"),
                     ledger: "Path | None" = _LEDGER) -> dict:
    """The FULL #122 pipeline over a seam: multi-cut × diverse-provider TYPED solve queries (decorative
    analogies mechanically rejected) + an IMPOSSIBILITY pass (no-go transports — the cheapest research
    value) + a SECOND-ORDER deanchor round (first round's fields banned, forcing distant basins).
    Refuted-disposition feedback rides every query. Returns
    {solve, impossibility, second_order, rejected_untyped} — dispositions remain the follow-through."""
    from ztare.common.constraint_isomorphism import second_order_fingerprint
    rejected: "list" = []
    q_solve = diversity_query(providers, typed_mapping=True, mode="solve", rejected_sink=rejected)
    solve = surface_multicut(cuts, n_per_cut=n_per_cut, query=q_solve, ledger=ledger)
    # impossibility pass on the PRIMARY cut (untyped — a no-go maps approaches, not components)
    q_imp = diversity_query(providers[:1], typed_mapping=False, mode="impossibility")
    impossibility = surface_multicut(cuts[:1], n_per_cut=n_per_cut, query=q_imp, ledger=ledger)
    # second-order deanchor: ban the first round's fields, re-query the primary cut
    second_order: "list" = []
    if solve and cuts:
        dom = ResearchDomain()
        fp2 = second_order_fingerprint(dom.abstract_failure(dict(cuts[0])), solve)
        q2 = diversity_query(providers[:1], typed_mapping=True, mode="solve", rejected_sink=rejected)
        second_order = [i for i in q2(fp2, n_per_cut)
                        if (i.theorem, i.field) not in {(s.theorem, s.field) for s in solve}]
        if ledger is not None and second_order:
            try:
                with ledger.open("a", encoding="utf-8") as f:
                    for iso in second_order:
                        row = {"constraint_class": fp2.constraint_class,
                               "forbidden_domain": fp2.forbidden_domain,
                               "theorem": iso.theorem, "field": iso.field,
                               "mechanism": iso.mechanism,
                               "mapping_hint": iso.mapping_hint,
                               "enrichment": iso.enrichment,
                               **_morphism_record_fields(iso),
                               "action_schema": _action_schema_with_transport(
                                   iso, fp2, transfer_mode="second_order_deanchor")}
                        row["candidate_hash"] = _candidate_content_hash(row)
                        f.write(json.dumps(row) + "\n")
            except OSError:
                pass
    return {"solve": solve, "impossibility": impossibility, "second_order": second_order,
            "rejected_untyped": rejected}


def surface_two_hop(cuts: "list[dict]", *, providers: "tuple[str, ...]" = ("deepseek",),
                    n: int = 3, query=None, ledger: "Path | None" = _LEDGER) -> dict:
    """COMPOSITIONAL two-hop surfacing (A~C via B): run the PRIMARY cut single-hop to surface bridge
    structures B, then compose_transports hops again through each B into structurally-distant fields
    C — the common abstraction found by COMPOSING two partial matches (the engine is otherwise
    single-hop). Second-hop candidates are logged with transfer_mode="two_hop" (mirrors
    surface_upgraded's second-order write). `query` is injectable for tests; the default fans a TYPED
    solve query across `providers`. Returns {first_hop, two_hop}."""
    from ztare.common.constraint_isomorphism import compose_transports
    if query is None:
        query = diversity_query(providers, typed_mapping=True, mode="solve")
    fp = ResearchDomain().abstract_failure(dict(cuts[0]))
    first_hop = query(fp, n) or []
    rejected: list[SurfacedIsomorphism] = []
    two_hop = compose_transports(fp, first_hop, query, n=n, rejected_sink=rejected)
    if ledger is not None and two_hop:
        try:
            ledger.parent.mkdir(parents=True, exist_ok=True)
            with ledger.open("a", encoding="utf-8") as f:
                for iso in two_hop:
                    row = {"constraint_class": fp.constraint_class,
                           "forbidden_domain": fp.forbidden_domain,
                           "theorem": iso.theorem, "field": iso.field,
                           "mechanism": iso.mechanism, "mapping_hint": iso.mapping_hint,
                           "enrichment": iso.enrichment,
                           **_morphism_record_fields(iso),
                           "action_schema": _action_schema_with_transport(
                               iso, fp, transfer_mode="two_hop")}
                    row["candidate_hash"] = _candidate_content_hash(row)
                    f.write(json.dumps(row) + "\n")
        except OSError:
            pass
    return {"first_hop": first_hop, "two_hop": two_hop, "rejected": rejected}


def _required_invariant_keys(fp: ConstraintFingerprint) -> "set[str]":
    return {k for k in fp.invariants if k != "do_not_resurface_refuted_transports"}


def _lowering_covers(fp: ConstraintFingerprint, lowering: object) -> bool:
    keys = _required_invariant_keys(fp)
    if not keys:
        return isinstance(lowering, dict)
    if not isinstance(lowering, dict):
        return False
    return all(str(lowering.get(k, "")).strip().lower() not in ("", "n/a", "none", "null", "-", "?", "tbd", "todo", "unset")
               for k in keys)


def _side_list(obj: object, side: str) -> "list[str]":
    if not isinstance(obj, dict):
        return []
    val = obj.get(side) or []
    if isinstance(val, str):
        val = [val]
    return [_prediction_text(v) for v in val if _prediction_text(v)]


def _prediction_text(item: object) -> str:
    if isinstance(item, dict):
        return " ".join(str(v).strip() for v in item.values() if str(v).strip()).strip()
    return str(item).strip()


def _as_list(obj: object, side: str) -> list:
    if not isinstance(obj, dict):
        return []
    val = obj.get(side) or []
    if isinstance(val, str) or isinstance(val, dict):
        val = [val]
    return [v for v in val if _prediction_text(v)]


def _prediction_cards(conj: SurfacedConjecture) -> "list[dict]":
    """Normalize free-text or typed conjecture predictions into experiment cards.

    The LLM may invent a mother-structure name; downstream code should consume the
    bounded measurement/refuter surface. Missing structured fields stay explicit,
    so weak conjectures are inspectable instead of being laundered by prose.
    """
    cards = []
    for side in ("left", "right"):
        preds = _as_list(conj.novel_predictions, side)
        kills = _as_list(conj.kill_conditions, side)
        for idx, pred in enumerate(preds):
            kill = kills[idx] if idx < len(kills) else {}
            pred_d = pred if isinstance(pred, dict) else {"prediction": _prediction_text(pred)}
            kill_d = kill if isinstance(kill, dict) else {"refuter": _prediction_text(kill)}
            cards.append({
                "side": side,
                "prediction": str(pred_d.get("prediction") or _prediction_text(pred)).strip(),
                "measurement": str(pred_d.get("measurement") or "").strip(),
                "intervention": str(pred_d.get("intervention") or "").strip(),
                "horizon": str(pred_d.get("horizon") or "").strip(),
                "expected_observation": str(pred_d.get("expected_observation") or "").strip(),
                "novelty_reason": str(pred_d.get("novelty_reason") or "").strip(),
                "refuter": str(kill_d.get("refuter") or _prediction_text(kill)).strip(),
                "gate": str(kill_d.get("gate") or "").strip(),
                "receipt": str(kill_d.get("receipt") or "").strip(),
            })
    return cards


def _prior_art_inversion_plan_valid(conj: SurfacedConjecture) -> bool:
    """Require a bounded nearest-prior-art search plan before live conjectures survive."""

    row = (
        conj.prior_art_inversion
        if isinstance(conj.prior_art_inversion, dict)
        else {}
    )
    queries = row.get("search_queries")
    axes = row.get("comparison_axes")
    kill = str(row.get("kill_if_matched") or "").strip()
    return (
        isinstance(queries, list)
        and any(str(value).strip() for value in queries)
        and isinstance(axes, list)
        and any(str(value).strip() for value in axes)
        and bool(kill)
    )


def _conjecture_behavior_tokens(conj: SurfacedConjecture) -> "set[str]":
    import re

    stop = {
        "a", "an", "and", "any", "are", "as", "at", "be", "by", "for", "from", "if", "in",
        "into", "is", "it", "its", "no", "not", "of", "on", "or", "rather", "should",
        "than", "that", "the", "their", "then", "there", "this", "to", "under", "with",
        "within", "without",
    }
    text = json.dumps({
        "predictions": conj.novel_predictions,
        "kills": conj.kill_conditions,
    }, sort_keys=True)
    out = set()
    for token in re.findall(r"[a-zA-Z0-9_/<>:=+-]+", text.lower()):
        if len(token) < 3 or token in stop:
            continue
        for suffix in ("ing", "ed", "es", "s"):
            if len(token) > len(suffix) + 3 and token.endswith(suffix):
                token = token[:-len(suffix)]
                break
        out.add(token)

    # Coarse experiment-family buckets catch vocabulary variants such as
    # "hold kernel" vs "escrow release" when they ask for the same measurements.
    blob = " ".join(out)
    buckets = {
        "phase_clock": ("phase", "residue", "clock", "tick", "p/q", "schedule"),
        "pause_hold": ("pause", "hold", "stall", "idle", "non-gate", "escrow"),
        "budget_counter": ("budget", "counter", "resource", "deplet", "consume", "balance"),
        "bounded_window": ("action", "step", "transition", "window", "period", "bound"),
        "reset_vs_path": ("reset", "terminate", "path-active", "discontinuity", "translation-invariant"),
    }
    for name, needles in buckets.items():
        if any(n in blob for n in needles):
            out.add(f"bucket:{name}")
    return out


def conjecture_behavior_similarity(a: SurfacedConjecture, b: SurfacedConjecture) -> float:
    ta, tb = _conjecture_behavior_tokens(a), _conjecture_behavior_tokens(b)
    if not ta and not tb:
        return 1.0
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def _dedupe_conjectures_by_behavior(conjs: "list[SurfacedConjecture]", *,
                                    threshold: float = 0.30) -> "list[SurfacedConjecture]":
    kept: list[SurfacedConjecture] = []
    for conj in conjs:
        duplicate_of = None
        for prev in kept:
            if conjecture_behavior_similarity(conj, prev) >= threshold:
                duplicate_of = prev
                break
        if duplicate_of is None:
            kept.append(conj)
            continue
        dups = getattr(duplicate_of, "duplicates", None)
        if dups is None:
            dups = []
            setattr(duplicate_of, "duplicates", dups)
        dups.append({
            "mother_structure": conj.mother_structure,
            "specificity": conj.specificity,
            "lowerings": conj.lowerings,
            "novel_predictions": conj.novel_predictions,
            "kill_conditions": conj.kill_conditions,
        })
    return kept


def _run_offline_adjudicator(conj: SurfacedConjecture, left: ConstraintFingerprint,
                             right: ConstraintFingerprint, offline_adjudicator=None) -> dict:
    if offline_adjudicator is None:
        return {"status": "not_run", "sides": {}}
    result = offline_adjudicator(conj, left, right) or {}
    sides = result.get("sides") if isinstance(result, dict) else {}
    if not isinstance(sides, dict):
        sides = {}
    statuses = {str(v.get("status") if isinstance(v, dict) else v) for v in sides.values()}
    if "refuted" in statuses:
        status = "refuted"
    elif statuses and statuses <= {"covered"}:
        status = "covered"
    elif "covered" in statuses:
        status = "partially_covered"
    elif "needs_live" in statuses:
        status = "needs_live"
    else:
        status = str(result.get("status") or "not_run") if isinstance(result, dict) else "not_run"
    out = dict(result) if isinstance(result, dict) else {}
    out["status"] = status
    out["sides"] = sides
    return out


def _adjudication_blocks_conjecture(adjudication: dict) -> bool:
    return str((adjudication or {}).get("status") or "") == "refuted"


def closed_champion_fact_adjudicator(facts: dict):
    """Build an offline adjudicator from closed-champion facts.

    `facts` shape:
      {"left": {"covered": ["pause onset follows dest law"], "refuted": ["unbounded phase"]},
       "right": {"covered": [...], "refuted": [...]}}

    It is deliberately explicit: this wrapper does not infer champion semantics from prose. The caller
    supplies the champion-derived facts/patterns, and `conjecture_between` enforces the result.
    """
    import re

    def _matches(patterns, blob: str) -> "list[str]":
        hits = []
        for pat in patterns or []:
            raw = str(pat).strip()
            if not raw:
                continue
            try:
                if re.search(raw, blob, re.I):
                    hits.append(raw)
                    continue
            except re.error:
                pass
            if raw.lower() in blob.lower():
                hits.append(raw)
        return hits

    def adjudicator(conj: SurfacedConjecture, left: ConstraintFingerprint, right: ConstraintFingerprint) -> dict:
        sides = {}
        for side in ("left", "right"):
            blob = " ".join(_side_list(conj.novel_predictions, side)
                            + _side_list(conj.kill_conditions, side))
            cfg = facts.get(side, {}) if isinstance(facts, dict) else {}
            refuted = _matches(cfg.get("refuted"), blob)
            covered = _matches(cfg.get("covered"), blob)
            if refuted:
                sides[side] = {"status": "refuted", "matches": refuted}
            elif covered:
                sides[side] = {"status": "covered", "matches": covered}
            else:
                sides[side] = {"status": "needs_live"}
        return {"source": "closed_champion_facts", "sides": sides}

    return adjudicator


def _conjecture_survives_schema(conj: SurfacedConjecture, left: ConstraintFingerprint,
                                right: ConstraintFingerprint, *, min_specificity: float = 0.25,
                                require_prior_art_inversion: bool = False) -> bool:
    lowers = conj.lowerings if isinstance(conj.lowerings, dict) else {}
    if not _lowering_covers(left, lowers.get("left")):
        return False
    if not _lowering_covers(right, lowers.get("right")):
        return False
    if not _side_list(conj.novel_predictions, "left") or not _side_list(conj.novel_predictions, "right"):
        return False
    if not _side_list(conj.kill_conditions, "left") or not _side_list(conj.kill_conditions, "right"):
        return False
    if require_prior_art_inversion and not _prior_art_inversion_plan_valid(conj):
        return False
    conj.specificity = prediction_specificity(conj)
    return (conj.specificity or 0.0) >= min_specificity


def _action_schema_from_conjecture(conj: SurfacedConjecture, left: ConstraintFingerprint,
                                   right: ConstraintFingerprint, offline_adjudication: "dict | None" = None) -> dict:
    offline_adjudication = offline_adjudication or {"status": "not_run", "sides": {}}
    return KernelActionSchema(
        record_type="kernel_action_schema",
        source_kind="research_isomorphism",
        action_family="structural_transfer",
        action_name="conjectural_correspondence",
        source_summary=f"{conj.mother_structure}: proposed shared object for two fingerprints",
        target_mapping=json.dumps(conj.lowerings, sort_keys=True)[:500],
        nearest_confuser=(
            "retrieved analogy or one-sided metaphor; reject unless both lowerings cover their "
            "fingerprint invariants and both sides yield target-side predictions"
        ),
        falsifier=json.dumps(conj.kill_conditions, sort_keys=True)[:500],
        verification_artifact=(
            "experiment card, sealed replay gate, forecast resolution, or disposition row for each "
            "prediction before promotion to a correspondence entry"
        ),
        action_constraints=[
            "do not treat the conjecture as an established correspondence",
            "do not use novelty language until the prior-art inversion plan is executed and a source-bound receipt rules out the nearest systems",
            "run closed-champion/offline adjudication before spending live actions",
            "do not promote without at least one prediction surviving its stated kill condition",
            "record a disposition for every prediction card created from this conjecture",
        ],
        evidence_basis="research_isomorphism: conjectural correspondence path",
        payload={
            "mother_structure": conj.mother_structure,
            "left_fingerprint": {
                "constraint_class": left.constraint_class,
                "abstract_form": left.abstract_form,
                "invariants": dict(left.invariants or {}),
                "home_field": left.forbidden_domain,
            },
            "right_fingerprint": {
                "constraint_class": right.constraint_class,
                "abstract_form": right.abstract_form,
                "invariants": dict(right.invariants or {}),
                "home_field": right.forbidden_domain,
            },
            "novel_predictions": conj.novel_predictions,
            "prediction_cards": _prediction_cards(conj),
            "prior_art_inversion": conj.prior_art_inversion,
            "offline_adjudication": offline_adjudication,
            "specificity": conj.specificity,
        },
    ).to_dict()


def conjecture_between(
    left_state: dict,
    right_state: dict,
    *,
    n: int = 5,
    model: str = "gemini",
    timeout_s: int = 180,
    query=None,
    ledger: "Path | None" = _LEDGER,
    min_specificity: float = 0.25,
    offline_adjudicator=None,
) -> dict:
    """Generative correspondence path: two fingerprints in, conjectural dictionary candidates out.

    This is not `mode="correspondence"` over a single seam. It proposes a new shared structure between
    two fingerprints and keeps only candidates with both lowerings, both prediction sides, kill
    conditions, and enough deterministic prediction specificity.
    """
    dom = ResearchDomain()
    left = dom.abstract_failure(dict(left_state or {}))
    right = dom.abstract_failure(dict(right_state or {}))
    query_receipt = {"transport": "injected", "parse_status": "injected"}
    if query is None:
        import re as _re

        from ztare.common.constraint_isomorphism import (
            _build_conjecture_prompt,
            _dispatch_text_with_receipt,
            _parse_conjectures,
        )

        prov, mid = _provider_and_model(model)
        text, dispatch = _dispatch_text_with_receipt(
            _build_conjecture_prompt(left, right, n),
            provider=prov,
            model=mid,
            timeout_s=timeout_s,
        )
        raw = _parse_conjectures(text)
        match = _re.search(r"\[.*\]", text, _re.S) if text else None
        query_receipt = {
            **dispatch,
            "parse_status": (
                "transport_failed"
                if dispatch.get("status") == "transport_failed"
                else "no_text"
                if not text
                else "no_json_list"
                if match is None
                else "parsed_candidates"
                if raw
                else "valid_empty_or_schema_empty"
            ),
            "raw_candidate_count": len(raw),
        }
    else:
        raw = query(left, right, n) or []
    kept, rejected = [], []
    adjudications: dict[int, dict] = {}
    for conj in raw:
        if not _conjecture_survives_schema(
            conj,
            left,
            right,
            min_specificity=min_specificity,
            require_prior_art_inversion=(query is None),
        ):
            rejected.append(conj)
            continue
        adj = _run_offline_adjudicator(conj, left, right, offline_adjudicator)
        setattr(conj, "offline_adjudication", adj)
        if _adjudication_blocks_conjecture(adj):
            rejected.append(conj)
            continue
        adjudications[id(conj)] = adj
        kept.append(conj)
    kept.sort(key=lambda c: -(c.specificity or 0.0))
    kept = _dedupe_conjectures_by_behavior(kept)
    if ledger is not None and kept:
        try:
            ledger.parent.mkdir(parents=True, exist_ok=True)
            with ledger.open("a", encoding="utf-8") as f:
                for conj in kept:
                    adj = adjudications.get(id(conj), getattr(conj, "offline_adjudication", None)
                                            or {"status": "not_run", "sides": {}})
                    row = {
                        "record_type": "conjectural_correspondence",
                        "left_constraint_class": left.constraint_class,
                        "right_constraint_class": right.constraint_class,
                        "left_forbidden_domain": left.forbidden_domain,
                        "right_forbidden_domain": right.forbidden_domain,
                        "mother_structure": conj.mother_structure,
                        "behavior_key": sorted(_conjecture_behavior_tokens(conj)),
                        "duplicates": getattr(conj, "duplicates", []),
                        "lowerings": conj.lowerings,
                        "novel_predictions": conj.novel_predictions,
                        "prediction_cards": _prediction_cards(conj),
                        "kill_conditions": conj.kill_conditions,
                        "prior_art_inversion": conj.prior_art_inversion,
                        "offline_adjudication": adj,
                        "specificity": conj.specificity,
                        "action_schema": _action_schema_from_conjecture(conj, left, right, adj),
                    }
                    row["candidate_hash"] = _candidate_content_hash(row)
                    f.write(json.dumps(row) + "\n")
        except OSError:
            pass
    return {
        "left": left,
        "right": right,
        "conjectures": kept,
        "rejected": rejected,
        "query_receipt": query_receipt,
    }


def langlands_sweep(fingerprints: "list[dict]", *, budget: int = 20, n: int = 3,
                    model: str = "gemini", query=None, offline_adjudicator=None,
                    ledger: "Path | None" = _LEDGER) -> dict:
    """Budget-capped pair sweep over accumulated fingerprints.

    The caller supplies fingerprint dicts from ledgers/cards/structure cuts. The sweep pairs them in
    order, stops at `budget`, and delegates each pair to `conjecture_between`.
    """
    results = []
    pairs_seen = 0
    for i, left in enumerate(fingerprints or []):
        for right in (fingerprints or [])[i + 1:]:
            if pairs_seen >= budget:
                return {"pairs_tested": pairs_seen, "results": results}
            pairs_seen += 1
            out = conjecture_between(left, right, n=n, model=model, query=query,
                                     offline_adjudicator=offline_adjudicator, ledger=ledger)
            if out["conjectures"]:
                results.append(out)
    return {"pairs_tested": pairs_seen, "results": results}


_DISPOSITIONS = ("forecast", "tested", "wired", "refuted", "stale", "survived")
_SURVIVAL_RECEIPT_STATUSES = {"pass", "passed", "supported", "survived", "verified"}
_EXPERIMENT_VERDICT_SCHEMA = "ztare-research-isomorphism-experiment-verdict-v1"
_EXPERIMENT_VERDICT_PURPOSE = "research_isomorphism_experiment"
_EXPERIMENT_VERDICT_FIELDS = (
    "experiment_verdict",
    "provider_verdict",
    "verification_payload",
)


def _canonical_hash(payload: object) -> str:
    import hashlib

    data = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str)
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def _canonical_json(payload: object) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str)


def _candidate_content_hash(row: dict) -> str:
    """Hash the complete immutable candidate payload, separate from its queue key."""

    excluded = {"candidate_hash", "dictionary_entry", "disposition_for", "key"}
    return _canonical_hash({key: value for key, value in row.items() if key not in excluded})


def _survival_receipt_claim(row: dict, receipt: "dict | None") -> dict:
    import hashlib

    if not isinstance(receipt, dict):
        raise ValueError("survived disposition requires an experiment_receipt object")
    candidate_hash = _candidate_content_hash(row)
    stored_hash = str(row.get("candidate_hash") or "").strip()
    if stored_hash and stored_hash != candidate_hash:
        raise ValueError("candidate_hash does not match the stored candidate payload")
    if str(receipt.get("candidate_hash") or "").strip() != candidate_hash:
        raise ValueError("experiment_receipt.candidate_hash does not bind the candidate payload")
    status = str(receipt.get("status") or "").strip().lower()
    if status not in _SURVIVAL_RECEIPT_STATUSES:
        raise ValueError(f"experiment_receipt.status must be one of {sorted(_SURVIVAL_RECEIPT_STATUSES)}")
    for field_name in ("receipt_id", "evidence_ref", "evidence_sha256"):
        if not str(receipt.get(field_name) or "").strip():
            raise ValueError(f"experiment_receipt.{field_name} is required")
    experiment_id = str(receipt.get("experiment_id") or "").strip()
    intervention_id = str(receipt.get("intervention_id") or "").strip()
    if not experiment_id and not intervention_id:
        raise ValueError("experiment_receipt.experiment_id or intervention_id is required")
    evidence = Path(str(receipt["evidence_ref"])).expanduser().resolve()
    try:
        actual_evidence_sha = hashlib.sha256(evidence.read_bytes()).hexdigest()
    except OSError as exc:
        raise ValueError(f"experiment_receipt.evidence_ref is unreadable: {exc}") from exc
    if actual_evidence_sha != str(receipt["evidence_sha256"]).strip().lower():
        raise ValueError("experiment_receipt.evidence_sha256 does not match evidence_ref")
    outcome = receipt.get("outcome")
    outcome_status = (
        str(outcome.get("status") or outcome.get("verdict") or "").strip().lower()
        if isinstance(outcome, dict)
        else str(outcome or "").strip().lower()
    )
    if outcome_status not in _SURVIVAL_RECEIPT_STATUSES:
        raise ValueError(
            "experiment_receipt.outcome must report a passing or survived experiment"
        )
    return {
        "candidate_hash": candidate_hash,
        "receipt_id": str(receipt["receipt_id"]).strip(),
        "experiment_id": experiment_id,
        "intervention_id": intervention_id,
        "outcome": outcome,
        "status": status,
        "evidence_ref": str(receipt["evidence_ref"]).strip(),
        "evidence_sha256": actual_evidence_sha,
    }


def _experiment_verdict_subject(claim: dict) -> dict:
    return {
        "schema": _EXPERIMENT_VERDICT_SCHEMA,
        "candidate_hash": claim["candidate_hash"],
        "experiment_id": claim["experiment_id"],
        "intervention_id": claim["intervention_id"],
        "outcome": claim["outcome"],
        "evidence_ref": claim["evidence_ref"],
        "evidence_sha256": claim["evidence_sha256"],
    }


def build_signed_experiment_verdict(
    row: dict,
    receipt: dict,
    *,
    private_key_pem: str,
    verifier_ref: str,
) -> dict:
    """Sign the exact experiment claim required for dictionary promotion."""

    from ztare.leanmill.formal_verification_provider import (
        attach_signature,
        build_payload,
    )

    claim = _survival_receipt_claim(row, receipt)
    subject = _experiment_verdict_subject(claim)
    if not str(private_key_pem or "").strip() or not str(verifier_ref or "").strip():
        raise ValueError("private_key_pem and verifier_ref are required")
    subject_ref = f"research-isomorphism-candidate:{claim['candidate_hash']}"
    binding_id = claim["experiment_id"] or claim["intervention_id"]
    claim_ref = f"{subject_ref}:survived:{binding_id}"
    payload = build_payload(
        formal_system="other",
        property_class="evidence_chain",
        verdict="verified",
        subject_ref=subject_ref,
        subject_text=_canonical_json(subject),
        claim_ref=claim_ref,
        certificate_ref=claim["evidence_ref"],
        certificate_text=claim["evidence_sha256"],
        verifier_ref=verifier_ref,
        verification_summary="Bound experiment outcome supports correspondence survival.",
        faithfulness_refs=[f"sha256:{claim['candidate_hash']}"],
        checker_evidence_refs=[claim["evidence_ref"]],
        input_refs=[f"sha256:{claim['candidate_hash']}", claim["evidence_sha256"]],
        output_refs=[claim_ref],
        run_id=binding_id,
        extra_metadata={
            "purpose": _EXPERIMENT_VERDICT_PURPOSE,
            "authority_schema": _EXPERIMENT_VERDICT_SCHEMA,
            "experiment_subject": subject,
        },
    )
    return attach_signature(payload, private_key_pem)


def _validated_survival_receipt(
    row: dict,
    receipt: "dict | None",
    *,
    trusted_public_key_pem: str | None,
) -> dict:
    from ztare.leanmill.formal_verification_provider import (
        PROVIDER,
        SCHEMA_VERSION,
        sha256_ref,
        verify_payload_signature,
    )

    claim = _survival_receipt_claim(row, receipt)
    if not isinstance(receipt, dict):  # guarded by _survival_receipt_claim
        raise ValueError("survived disposition requires an experiment_receipt object")
    if not str(trusted_public_key_pem or "").strip():
        raise ValueError(
            "survived disposition requires a trusted_public_key_pem supplied by the consumer"
        )
    payload = next(
        (
            receipt.get(field_name)
            for field_name in _EXPERIMENT_VERDICT_FIELDS
            if isinstance(receipt.get(field_name), dict)
        ),
        None,
    )
    if not isinstance(payload, dict):
        raise ValueError("experiment_receipt requires a signed experiment_verdict")

    subject = _experiment_verdict_subject(claim)
    subject_ref = f"research-isomorphism-candidate:{claim['candidate_hash']}"
    binding_id = claim["experiment_id"] or claim["intervention_id"]
    claim_ref = f"{subject_ref}:survived:{binding_id}"
    metadata = payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {}
    failures = []
    expected_fields = {
        "schema_version": SCHEMA_VERSION,
        "provider": PROVIDER,
        "formal_system": "other",
        "property_class": "evidence_chain",
        "verdict": "verified",
        "subject_ref": subject_ref,
        "subject_digest": sha256_ref(_canonical_json(subject)),
        "claim_ref": claim_ref,
        "certificate_ref": claim["evidence_ref"],
        "certificate_digest": sha256_ref(claim["evidence_sha256"]),
        "run_id": binding_id,
    }
    for field_name, expected in expected_fields.items():
        if payload.get(field_name) != expected:
            failures.append(field_name)
    if metadata.get("purpose") != _EXPERIMENT_VERDICT_PURPOSE:
        failures.append("metadata.purpose")
    if metadata.get("authority_schema") != _EXPERIMENT_VERDICT_SCHEMA:
        failures.append("metadata.authority_schema")
    if metadata.get("experiment_subject") != subject:
        failures.append("metadata.experiment_subject")
    if not str(payload.get("verifier_ref") or "").strip():
        failures.append("verifier_ref")
    if not str(payload.get("verification_summary") or "").strip():
        failures.append("verification_summary")
    if payload.get("counterexample_ref") is not None:
        failures.append("counterexample_ref")
    faithfulness_refs = payload.get("faithfulness_refs")
    if not isinstance(faithfulness_refs, list) or f"sha256:{claim['candidate_hash']}" not in faithfulness_refs:
        failures.append("faithfulness_refs")
    checker_evidence_refs = payload.get("checker_evidence_refs")
    if not isinstance(checker_evidence_refs, list) or claim["evidence_ref"] not in checker_evidence_refs:
        failures.append("checker_evidence_refs")
    try:
        signature_ok = verify_payload_signature(payload, trusted_public_key_pem)
    except (KeyError, TypeError, ValueError):
        signature_ok = False
    if not signature_ok:
        failures.append("signature")
    if failures:
        raise ValueError(
            "experiment_receipt signed experiment verdict failed: " + ", ".join(failures)
        )

    normalized = dict(receipt)
    normalized.pop("receipt_hash", None)
    for field_name in _EXPERIMENT_VERDICT_FIELDS:
        normalized.pop(field_name, None)
    normalized.update(claim)
    normalized["experiment_verdict"] = dict(payload)
    normalized["receipt_hash"] = _canonical_hash(normalized)
    return normalized


def _cand_key(c: dict) -> str:
    """Stable sha16 identity: content hash for new rows, legacy name tuple otherwise."""
    import hashlib
    candidate_hash = str(c.get("candidate_hash") or "").strip().lower()
    if len(candidate_hash) == 64 and all(ch in "0123456789abcdef" for ch in candidate_hash):
        return candidate_hash[:16]
    if c.get("record_type") == "conjectural_correspondence":
        raw = "|".join(str(c.get(k, "")) for k in (
            "left_constraint_class", "right_constraint_class", "mother_structure"
        ))
        return hashlib.sha256(raw.encode()).hexdigest()[:16]
    raw = "|".join(str(c.get(k, "")) for k in ("constraint_class", "theorem", "field"))
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def _load_candidate_by_key(key: str, *, ledger: "Path | None" = None) -> "dict | None":
    led = ledger if ledger is not None else _LEDGER
    try:
        rows = [json.loads(l) for l in led.read_text(encoding="utf-8").splitlines() if l.strip()]
    except (OSError, ValueError):
        return None
    for row in rows:
        if row.get("disposition_for"):
            continue
        if _cand_key(row) == key:
            return row
    return None


def register_correspondence_dictionary_entry(
    row: dict,
    *,
    experiment_receipt: "dict | None" = None,
    dictionary: "Path | None" = None,
    note: str = "",
    trusted_public_key_pem: str | None = None,
) -> dict:
    """Promote a conjecture only after verifying its signed experiment verdict."""
    if row.get("record_type") != "conjectural_correspondence":
        raise ValueError("only conjectural_correspondence rows can become dictionary entries")
    receipt = _validated_survival_receipt(
        row,
        experiment_receipt,
        trusted_public_key_pem=trusted_public_key_pem,
    )
    rec = {
        "record_type": "learned_correspondence_dictionary_entry",
        "source_key": _cand_key(row),
        "mother_structure": row.get("mother_structure"),
        "left_constraint_class": row.get("left_constraint_class"),
        "right_constraint_class": row.get("right_constraint_class"),
        "lowerings": row.get("lowerings") or {},
        "novel_predictions": row.get("novel_predictions") or {},
        "kill_conditions": row.get("kill_conditions") or {},
        "specificity": row.get("specificity"),
        "candidate_hash": receipt["candidate_hash"],
        "experiment_receipt": receipt,
        "note": note,
    }
    path = dictionary if dictionary is not None else _DICTIONARY
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = set()
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            item = json.loads(line)
            existing.add(item.get("candidate_hash") or item.get("source_key"))
    except (OSError, ValueError):
        existing = set()
    if rec["candidate_hash"] not in existing:
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec) + "\n")
    return rec


def record_disposition(key: str, status: str, note: str = "", *, ledger: "Path | None" = None,
                       dictionary: "Path | None" = None,
                       experiment_receipt: "dict | None" = None,
                       trusted_public_key_pem: str | None = None) -> dict:
    """Append a DISPOSITION for a surfaced candidate — the accountability tail (RP-002 discipline) the
    ledger lacked: 95 candidates had accrued with ZERO follow-through tracking, which is how built-but-
    unwired yields (Luby, Dawid–Skene) rot. `status` ∈ forecast/tested/wired/refuted/stale/survived."""
    if status not in _DISPOSITIONS:
        raise ValueError(f"status must be one of {_DISPOSITIONS}")
    led = ledger if ledger is not None else _LEDGER
    row = _load_candidate_by_key(key, ledger=led)
    receipt = None
    if status == "survived":
        if row is None:
            raise ValueError(f"candidate {key!r} not found")
        receipt = _validated_survival_receipt(
            row,
            experiment_receipt,
            trusted_public_key_pem=trusted_public_key_pem,
        )
    rec = {"disposition_for": key, "status": status, "note": note}
    if receipt is not None:
        rec["candidate_hash"] = receipt["candidate_hash"]
        rec["experiment_receipt"] = receipt
    led.parent.mkdir(parents=True, exist_ok=True)
    with led.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec) + "\n")
    if status == "survived":
        if row and row.get("record_type") == "conjectural_correspondence":
            rec["dictionary_entry"] = register_correspondence_dictionary_entry(
                row,
                experiment_receipt=receipt,
                dictionary=dictionary,
                note=note,
                trusted_public_key_pem=trusted_public_key_pem,
            )
    return rec


def undispositioned(*, ledger: "Path | None" = None) -> "list[dict]":
    """Surfaced candidates with NO disposition yet — the review queue. Each row gains its `key`."""
    led = ledger if ledger is not None else _LEDGER
    try:
        rows = [json.loads(l) for l in led.read_text(encoding="utf-8").splitlines() if l.strip()]
    except (OSError, ValueError):
        return []
    done = {r.get("disposition_for") for r in rows if r.get("disposition_for")}
    out = []
    for r in rows:
        if r.get("disposition_for"):
            continue
        k = _cand_key(r)
        if k not in done:
            out.append(dict(r, key=k))
    return out


def main(argv: "list[str] | None" = None) -> int:
    import sys as _sys
    args = list(_sys.argv[1:] if argv is None else argv)
    if not args or args[0] in ("-h", "--help"):
        print(
            "usage: research_isomorphism --selftest | --review | "
            "--disposition KEY STATUS [--receipt JSONFILE] "
            "[--trusted-public-key PEMFILE] [NOTE...] | --from-structure JSONFILE | "
            "--seam SEAM [options]\n\n"
            "Options for --seam:\n"
            "  --abstract TEXT          optional abstract form of the seam\n"
            "  --home FIELD             field to deanchor away from\n"
            "  --right-seam TEXT        second seam for --mode conjecture\n"
            "  --right-abstract TEXT    optional abstract form of the second seam\n"
            "  --right-home FIELD       second seam's field for --mode conjecture\n"
            "  --model FAMILY           model family, e.g. gemini/deepseek/kimi/claude/codex\n"
            "  --n N                    number of candidates to request\n"
            "  --timeout-s N            bounded subscription/API dispatch wall time\n"
            "  --mode solve|impossibility|completion|correspondence|conjecture\n"
            "  --typed-mapping          require mapping for every supplied invariant key\n"
            "  --invariant KEY=VALUE    structural invariant; repeatable\n"
            "  --right-invariant K=V    second-seam invariant for --mode conjecture; repeatable\n"
            "  --debug                  show provider/model, dispatch text length, parse status\n"
            "  --json                   emit JSON"
        )
        return 0
    if args and args[0] == "--selftest":
        return _self_test()
    if args and args[0] == "--review":
        q = undispositioned()
        for r in q:
            print(f"[{r['key']}] {r.get('field')} | {r.get('theorem')} | seam: {str(r.get('constraint_class'))[:80]}")
        print(f"{len(q)} undispositioned candidate(s)")
        return 0
    if len(args) >= 3 and args[0] == "--disposition":
        tail = list(args[3:])
        receipt = None
        trusted_public_key_pem = None
        if "--receipt" in tail:
            idx = tail.index("--receipt")
            if idx + 1 >= len(tail):
                print("--receipt requires a JSON file", file=_sys.stderr)
                return 2
            try:
                receipt = json.loads(Path(tail[idx + 1]).read_text(encoding="utf-8"))
            except (OSError, ValueError) as exc:
                print(f"cannot read experiment receipt: {exc}", file=_sys.stderr)
                return 2
            del tail[idx:idx + 2]
        if "--trusted-public-key" in tail:
            idx = tail.index("--trusted-public-key")
            if idx + 1 >= len(tail):
                print("--trusted-public-key requires a PEM file", file=_sys.stderr)
                return 2
            try:
                trusted_public_key_pem = Path(tail[idx + 1]).read_text(encoding="utf-8")
            except OSError as exc:
                print(f"cannot read trusted public key: {exc}", file=_sys.stderr)
                return 2
            del tail[idx:idx + 2]
        try:
            rec = record_disposition(
                args[1],
                args[2],
                " ".join(tail),
                experiment_receipt=receipt,
                trusted_public_key_pem=trusted_public_key_pem,
            )
        except ValueError as exc:
            print(str(exc), file=_sys.stderr)
            return 2
        print(json.dumps(rec))
        return 0
    if args and args[0] == "--from-structure":
        if len(args) < 2:
            print("usage: research_isomorphism --from-structure JSONFILE", file=_sys.stderr)
            return 2
        from ztare.worldmodel.object_roles import Role
        data = json.loads(Path(args[1]).read_text(encoding="utf-8"))
        roles = [Role(r["name"], r.get("members", []), r.get("evidence", ""))
                 for r in data.get("roles", [])] or None
        cuts = cuts_from_structure(roles, data.get("spec"), data.get("residual"),
                                   data.get("home_field", ""))
        print(json.dumps(cuts, indent=2))
        return 0
    if "--seam" in args:
        import argparse as _ap
        p = _ap.ArgumentParser(prog="ztare research isomorphism")
        p.add_argument("--seam", required=True, help="the research seam, as an operator-neutral constraint")
        p.add_argument("--abstract", default="", help="optional abstract form of the seam")
        p.add_argument("--home", default="", help="the project's own field, to deanchor away from")
        p.add_argument("--right-seam", default="", help="second seam for --mode conjecture")
        p.add_argument("--right-abstract", default="", help="optional abstract form of the second seam")
        p.add_argument("--right-home", default="", help="second seam's field for --mode conjecture")
        p.add_argument("--model", default="gemini", help="user-selected model family (routes api/subscription)")
        p.add_argument("--n", type=int, default=5, help="number of candidates to request")
        p.add_argument("--timeout-s", type=int, default=180, help="dispatch wall time")
        p.add_argument(
            "--mode",
            choices=("solve", "impossibility", "completion", "correspondence", "conjecture"),
            default="solve",
            help="ask for retrieval transports or a two-fingerprint conjectural correspondence",
        )
        p.add_argument(
            "--typed-mapping",
            action="store_true",
            help="ask candidates to map every supplied --invariant key",
        )
        p.add_argument(
            "--invariant",
            action="append",
            default=[],
            metavar="KEY=VALUE",
            help="structural invariant to include in the fingerprint; repeatable",
        )
        p.add_argument(
            "--right-invariant",
            action="append",
            default=[],
            metavar="KEY=VALUE",
            help="structural invariant for the second fingerprint; repeatable",
        )
        p.add_argument(
            "--debug",
            action="store_true",
            help="print provider/model, dispatch text length, parse status, and candidates",
        )
        p.add_argument("--json", action="store_true")
        ns = p.parse_args(args)
        try:
            invariants = _parse_invariant_args(ns.invariant)
            right_invariants = _parse_invariant_args(ns.right_invariant)
        except ValueError as exc:
            print(str(exc), file=_sys.stderr)
            return 2
        if ns.mode == "conjecture":
            if not ns.right_seam:
                print("--mode conjecture requires --right-seam", file=_sys.stderr)
                return 2
            left_state = _failure_state_for_seam(
                ns.seam,
                abstract_form=ns.abstract,
                home_field=ns.home,
                invariants=invariants,
            )
            right_state = _failure_state_for_seam(
                ns.right_seam,
                abstract_form=ns.right_abstract,
                home_field=ns.right_home,
                invariants=right_invariants,
            )
            if ns.debug:
                dbg = debug_conjecture_for_seams(
                    left_state,
                    right_state,
                    model=ns.model,
                    n=ns.n,
                    timeout_s=ns.timeout_s,
                )
                print(json.dumps(dbg) if ns.json else json.dumps(dbg, indent=2))
                return 0 if dbg.get("candidate_count", 0) else 1
            out = conjecture_between(
                left_state,
                right_state,
                n=ns.n,
                model=ns.model,
                timeout_s=ns.timeout_s,
                ledger=None if ns.debug else _LEDGER,
            )
            payload = {
                "candidate_count": len(out["conjectures"]),
                "rejected_count": len(out["rejected"]),
                "query_receipt": out.get("query_receipt"),
                "conjectures": [
                    {
                        "mother_structure": c.mother_structure,
                        "specificity": c.specificity,
                        "lowerings": c.lowerings,
                        "novel_predictions": c.novel_predictions,
                        "prediction_cards": _prediction_cards(c),
                        "kill_conditions": c.kill_conditions,
                    }
                    for c in out["conjectures"]
                ],
            }
            if ns.json:
                print(json.dumps(payload))
            elif out["conjectures"]:
                top = out["conjectures"][0]
                print(
                    f"{top.mother_structure}\n"
                    f"  candidates: {len(out['conjectures'])} kept, {len(out['rejected'])} rejected\n"
                    f"  specificity: {top.specificity:.2f}\n"
                    f"  predictions: {json.dumps(top.novel_predictions, sort_keys=True)[:500]}"
                )
            else:
                print("no conjectural correspondence survived schema checks")
            return 0 if out["conjectures"] else 1
        if ns.debug:
            dbg = debug_query_for_seam(
                ns.seam,
                abstract_form=ns.abstract,
                home_field=ns.home,
                model=ns.model,
                n=ns.n,
                invariants=invariants,
                typed_mapping=ns.typed_mapping,
                mode=ns.mode,
            )
            print(json.dumps(dbg) if ns.json else json.dumps(dbg, indent=2))
            return 0 if dbg.get("candidate_count", 0) else 1
        rx = prescribe_for_seam(
            ns.seam,
            abstract_form=ns.abstract,
            home_field=ns.home,
            model=ns.model,
            n=ns.n,
            invariants=invariants,
            typed_mapping=ns.typed_mapping,
            mode=ns.mode,
        )
        if ns.json:
            print(json.dumps(rx))
        elif rx:
            print(
                f"{rx['source_theorem']} ({rx['source_field']})\n"
                f"  candidates: {rx.get('candidate_count', 1)}\n"
                f"  {rx['transported_structure']}\n"
                f"  test: {rx['predict_then_falsify']}"
            )
        else:
            print("no cross-field analogy surfaced; rerun with --debug to distinguish dispatch, parse, and empty-result cases")
        return 0 if rx else 1
    print("usage: research_isomorphism --selftest | --review | --disposition KEY STATUS [NOTE...] | --from-structure JSONFILE | --seam SEAM [options]")
    return 2


def _self_test() -> int:
    fails = []

    def ok(name, cond):
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}")
        if not cond:
            fails.append(name)

    dom = ResearchDomain()
    fp = dom.abstract_failure({"constraint_class": "off-diagonal kernel decay under critical scaling",
                               "home_field": "fluid PDE"})
    ok("forbids_home_field_deanchor", fp.forbidden_domain == "fluid PDE")

    iso = SurfacedIsomorphism("heat-kernel off-diagonal bound", "spectral geometry",
                              "Gaussian off-diagonal decay of the heat kernel", "maps to the seam's kernel")
    presc = dom.compile_to_test(iso, None)
    ok("compiles_to_prescription_with_falsifier",
       isinstance(presc, ResearchPrescription) and "refutes" in presc.predict_then_falsify)
    ok("oracle_advisory_unverified_by_default", dom.oracle(presc, holdout=[]) == 0.0)

    # surfacing logs candidates (no live LLM — inject a mock query, no ledger write in test)
    cands = surface_for_research_ceiling(
        {"constraint_class": "x", "home_field": "fluid PDE"},
        query=lambda fp, n: [iso], ledger=None)
    ok("surfaces_candidates", len(cands) == 1 and cands[0].field == "spectral geometry")

    # --- disposition tail (hermetic temp ledger) ---
    import tempfile
    td = Path(tempfile.mkdtemp(prefix="riso_"))
    led = td / "cands.jsonl"
    c1 = {"constraint_class": "x", "theorem": "Kossel-Stranski", "field": "crystallography"}
    c2 = {"constraint_class": "x", "theorem": "Coffman-Graham", "field": "scheduling"}
    led.write_text(json.dumps(c1) + "\n" + json.dumps(c2) + "\n", encoding="utf-8")
    q0 = undispositioned(ledger=led)
    ok("review queue lists undispositioned", len(q0) == 2 and all("key" in r for r in q0))
    record_disposition(_cand_key(c1), "wired", "rung_adjacency.py", ledger=led)
    q1 = undispositioned(ledger=led)
    ok("disposition removes candidate from queue", len(q1) == 1 and q1[0]["theorem"] == "Coffman-Graham")
    try:
        record_disposition("k", "bogus", ledger=led)
        ok("invalid status rejected", False)
    except ValueError:
        ok("invalid status rejected", True)

    # --- multi-cut + refuted-feedback (hermetic: mock query captures fingerprints) ---
    record_disposition(_cand_key(c2), "refuted", "parallel-makespan does not fit serial substrate", ledger=led)
    rp = refuted_patterns(ledger=led)
    ok("refuted_patterns lists the refuted transport with note",
       len(rp) == 1 and "Coffman-Graham" in rp[0] and "serial" in rp[0])
    seen_fps = []

    def spy_query(fp, n):
        seen_fps.append(fp)
        # cut-dependent candidates: cut A surfaces iso, cut B surfaces a duplicate + a new one
        if "cutA" in fp.constraint_class:
            return [iso]
        return [iso, SurfacedIsomorphism("LT ripple", "coding theory", "m", "h")]

    merged = surface_multicut(
        [{"constraint_class": "cutA mechanism-level", "home_field": "ITP"},
         {"constraint_class": "cutB failure-mode-level", "home_field": "ITP"}],
        n_per_cut=3, query=spy_query, ledger=led)
    ok("multicut queries every cut", len(seen_fps) == 2)
    ok("multicut merges deduped by (theorem, field)",
       len(merged) == 2 and {m.theorem for m in merged} == {"heat-kernel off-diagonal bound", "LT ripple"})
    ok("refuted no-goods ride into the fingerprint invariants",
       all("do_not_resurface_refuted_transports" in fp.invariants for fp in seen_fps)
       and any("Coffman-Graham" in str(fp.invariants) for fp in seen_fps))

    ok("frontier aliases route through the Codex subscription runtime",
       _provider_and_model("sol") == ("codex", "gpt-5.6-sol")
       and _provider_and_model("terra") == ("codex", "gpt-5.6-terra")
       and _provider_and_model("luna") == ("codex", "gpt-5.6-luna"))

    # --- α→fingerprint: machine-induced structure as the query point (hermetic) ---
    from ztare.worldmodel.object_roles import Role
    fake_roles = [
        Role("monotone_depleting", [3], "global count strictly non-increasing"),
        Role("moves_under_actions", [4], "rigid displacement in 12 transitions"),
        Role("never_changes", [1], "unchanged in every transition"),
    ]
    fake_spec = {
        "actions": {"0": [{"op": "translate_block", "match_colors": [4], "dy": 0, "dx": 1,
                           "require_dest_colors": [0], "fill_color": 0}]},
        "always": [{"op": "consume_extremal", "color": 3, "replacement": 0,
                    "axis": "row", "extreme": "min", "when_count": [3, None, 5]}],
    }
    residual = "the mover's pause length is not fixed by the depleting resource"
    fpd = fingerprint_dict_from_structure(fake_roles, fake_spec, residual, home_field="grid worlds")
    cc = fpd["constraint_class"]
    print("  constraint_class:", cc)
    ok("structure fingerprint is operator-neutral (no surface words)",
       not any(b in cc.lower() for b in ("grid", "color", "pixel", "arc")))
    sinv = {k: v for k, v in fpd.items()
            if k not in ("constraint_class", "abstract_form", "home_field")}
    ok("invariants are few (<=6) and carry the monotone fact",
       len(sinv) <= 6 and sinv.get("resource_direction") == "monotone_nonincreasing")
    cuts3 = cuts_from_structure(fake_roles, fake_spec, residual)
    cuts2 = cuts_from_structure(fake_roles, fake_spec)
    ok("cuts: 3 with a residual (failure-mode cut added), 2 without",
       len(cuts3) == 3 and len(cuts2) == 2
       and any("undetermined" in c["constraint_class"] for c in cuts3))
    raised = False
    try:
        fingerprint_dict_from_structure(roles=None, spec=None)
    except ValueError:
        raised = True
    ok("empty structure -> ValueError", raised)

    # --- backward-compat: BOTH entry paths reach a valid deanchored fingerprint via the SAME
    #     abstract_failure — the hand-written human-text path and the machine structure path coexist ---
    hand_fp = dom.abstract_failure(_failure_state_for_seam(
        "a stalled structural seam", home_field="fluid PDE", invariants={"depth": "O(L)"}))
    ok("hand-written dict path: home_field deanchors + invariants carried",
       hand_fp.forbidden_domain == "fluid PDE" and hand_fp.invariants.get("depth") == "O(L)")
    struct_seen = []
    surface_multicut(cuts_from_structure(fake_roles, fake_spec, residual, home_field="grid worlds"),
                     n_per_cut=2, query=lambda fp, n: (struct_seen.append(fp) or [iso]),
                     ledger=None, feedback=False)
    ok("structure-generated dict path feeds surface_multicut unchanged (abstract_failure deanchors every cut)",
       len(struct_seen) == 3 and all(fp.forbidden_domain == "grid worlds" for fp in struct_seen))

    # --- two-hop consumer: single-hop → compose_transports, second hop annotated 'via B' (hermetic mock) ---
    _B = SurfacedIsomorphism("Heat-kernel bound", "spectral geometry", "gaussian decay", "orig")
    _C = SurfacedIsomorphism("LT ripple", "coding theory", "peeling decoder", "chint")
    _calls = []

    def _q2(fp, n):
        _calls.append(fp)
        return [_B] if len(_calls) == 1 else [_C]  # 1st call = single-hop; bridge query = 2nd

    th = surface_two_hop([{"constraint_class": "seam", "home_field": "grid worlds"}],
                         n=2, query=_q2, ledger=None)
    ok("two-hop consumer runs the primary cut single-hop then a bridge query",
       len(_calls) == 2 and th["first_hop"][0].theorem == "Heat-kernel bound")
    ok("two-hop consumer annotates the second hop 'via B'",
       len(th["two_hop"]) == 1 and th["two_hop"][0].theorem == "LT ripple"
       and th["two_hop"][0].mapping_hint.startswith("via Heat-kernel bound (spectral geometry):"))

    # --- closed WORLDMODEL oracle: no-laundering replay score (hermetic 2-transition log) ---
    from ztare.worldmodel.adapter import episode_log_path
    from ztare.worldmodel.episode_log import EpisodeLog
    wm_dir = Path(tempfile.mkdtemp(prefix="wm_oracle_"))
    _wlog = EpisodeLog()
    _g = ((1, 0), (0, 0))
    _wlog.append(_g, 0, _g)          # two identity transitions the identity spec must explain
    _wlog.append(_g, 0, _g)
    _wlog.write_jsonl(episode_log_path(wm_dir))
    _oracle = worldmodel_oracle(wm_dir)
    _rx_none = ResearchPrescription("T", "f", "structure", "falsifier")           # no spec_patch
    _rx_spec = ResearchPrescription("T", "f", "structure", "falsifier",
                                    spec_patch={"actions": {"0": [{"op": "identity"}]}})
    ok("worldmodel_oracle is advisory (0.0) without a spec_patch",
       _oracle(_rx_none, holdout=None) == 0.0)
    _score = _oracle(_rx_spec, holdout=None)
    ok("worldmodel_oracle scores >0 when a spec_patch compiles + explains the replay log",
       _score > 0.0 and _score == 1.0)

    print("SELFTEST", "PASSED" if not fails else f"FAILED: {fails}")
    return 0 if not fails else 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
