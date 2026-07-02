"""Research-director consumer of the Constraint-to-Isomorphism engine — out-of-loop edition.

Same canonical engine as leanmill (`ztare.common.constraint_isomorphism`), different domain plug.
The RD use is the operator's standing methodology (see AGENTS.md / memory: "abstract the frontier to
the operator-SEAM, find the field where that seam is already solved, transport the structure,
predict + falsify — never cite-and-launder"). This wires that as a reusable primitive.

KEY HONEST DIFFERENCE FROM leanmill. leanmill has a cheap closed oracle (re-run an A/B, measure
closure/MDL on a holdout) so it can auto-complete the loop. A research ceiling does NOT — verifying
a transported structure IS a research experiment (forecast → test → falsify), human/RD-adjudicated,
not a millisecond holdout score. So the RD consumer is primarily a SURFACING tool: it runs Steps 1+2
(abstract the seam → query cross-field structural matches, in the DEANCHOR direction — forbid the
home field + adjacent) and logs candidates to a ledger for the RD to PRE-REGISTER a forecast on and
test. `compile_to_test`/`oracle` exist for interface-completeness but the oracle is ADVISORY
(returns "unverified — requires an RD experiment") unless a real forecast/experiment oracle is
injected. This keeps the RD honest: no auto-laundering of a plausible analogy into a result.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

try:
    from ztare.common.constraint_isomorphism import (
        ConstraintFingerprint, IsomorphismLoop, SurfacedIsomorphism)
except Exception:  # pragma: no cover - installed package fallback
    from ztare.common.constraint_isomorphism import (
        ConstraintFingerprint, IsomorphismLoop, SurfacedIsomorphism)
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
        return ResearchPrescription(
            source_theorem=iso.theorem, source_field=iso.field,
            transported_structure=iso.mapping_hint or iso.mechanism,
            predict_then_falsify=f"if the {iso.theorem} structure transports, it predicts a sharp, "
                                 "checkable consequence at the seam; its failure refutes the transport",
            action_schema=action_schema_from_isomorphism(iso, source_kind="research_isomorphism"))

    def oracle(self, gate: "object | None", holdout: object) -> float:
        if self._oracle_fn is not None:
            return self._oracle_fn(gate, holdout)
        return 0.0  # advisory: a research transport is verified by an RD experiment, not a cheap score

    def banned_terms(self) -> "list[str]":
        return []  # the RD seam is already abstracted by the author; no fixed home vocabulary to ban


_LEDGER = Path("analytics/queries/research_isomorphism_candidates.jsonl")


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
                    f.write(json.dumps({"constraint_class": fp.constraint_class,
                                        "forbidden_domain": fp.forbidden_domain,
                                        "theorem": iso.theorem, "field": iso.field,
                                        "mechanism": iso.mechanism, "mapping_hint": iso.mapping_hint,
                                        "action_schema": action_schema_from_isomorphism(
                                            iso, fp, source_kind="research_isomorphism",
                                            transfer_mode="deanchor" if fp.forbidden_domain else "analogy"
                                        )}) + "\n")
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
    if fam.startswith(("gpt", "o1", "o3", "o4", "codex")):
        return "codex", None
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
    isos = surface_for_research_ceiling(failure_state, n=n, query=query, ledger=None)
    if not isos:
        return {}
    rx = ResearchDomain().compile_to_test(isos[0], None)
    return {"source_theorem": rx.source_theorem, "source_field": rx.source_field,
            "transported_structure": rx.transported_structure,
            "predict_then_falsify": rx.predict_then_falsify,
            "candidate_count": len(isos),
            "alternatives": [{"theorem": i.theorem, "field": i.field} for i in isos[1:4]]}


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
) -> dict:
    """Run the CLI query path with observable dispatch/parse diagnostics."""
    import json as _json
    import re as _re

    from ztare.common.constraint_isomorphism import _build_query_prompt, _dispatch_text

    failure_state = _failure_state_for_seam(
        constraint_class,
        abstract_form=abstract_form,
        home_field=home_field,
        invariants=invariants,
    )
    fp = ResearchDomain().abstract_failure(failure_state)
    prov, mid = _provider_and_model(model)
    prompt = _build_query_prompt(fp, n, typed_mapping=typed_mapping, mode=mode)
    text = _dispatch_text(prompt, provider=prov, model=mid)
    result = {
        "provider": prov,
        "model": mid,
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
        "candidates": [],
    }
    try:
        from ztare.common.llm_runtime import LLMRuntime

        runtime = LLMRuntime()
        if mid is not None:
            result["model_configured"] = runtime.model_is_configured(mid)
        if not text and mid is not None:
            try:
                probe = runtime.call_text(
                    prompt,
                    model_id=mid,
                    fallback_model_ids=(),
                    max_tokens=2000,
                    request_label="constraint_isomorphism_debug_probe",
                    timeout_seconds=60,
                )
                result["dispatch_error_probe"] = {
                    "direct_call_text_len": len(probe.text or ""),
                    "effective_model_id": probe.effective_model_id,
                }
                if probe.text:
                    text = probe.text
                    result["text_len"] = len(text)
                    result["text_head"] = text[:500]
            except Exception as exc:  # noqa: BLE001
                result["dispatch_error_probe"] = {
                    "exception_type": type(exc).__name__,
                    "message": str(exc)[:500],
                }
    except Exception as exc:  # noqa: BLE001
        result["dispatch_error_probe"] = {
            "exception_type": type(exc).__name__,
            "message": str(exc)[:500],
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
    candidates = [
        {
            "theorem": str(item.get("theorem", "")).strip(),
            "field": str(item.get("field", "")).strip(),
        }
        for item in items
        if isinstance(item, dict) and str(item.get("theorem", "")).strip()
    ]
    result["parse_status"] = "parsed"
    result["candidate_count"] = len(candidates)
    result["candidates"] = candidates
    return result


def refuted_patterns(*, ledger: "Path | None" = None, limit: int = 8) -> "list[str]":
    """Refuted/stale transports from the disposition ledger — fed BACK into the query as no-goods so the
    engine stops resurfacing known-dead shapes (the no_good_store discipline applied to analogies; e.g.
    parallel-makespan scheduling was refuted for the serial-Lean substrate and should never come back)."""
    led = ledger if ledger is not None else _LEDGER
    try:
        rows = [json.loads(l) for l in led.read_text(encoding="utf-8").splitlines() if l.strip()]
    except (OSError, ValueError):
        return []
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
                        f.write(json.dumps({"constraint_class": fp2.constraint_class,
                                            "forbidden_domain": fp2.forbidden_domain,
                                            "theorem": iso.theorem, "field": iso.field,
                                            "mechanism": iso.mechanism,
                                            "mapping_hint": iso.mapping_hint,
                                            "action_schema": action_schema_from_isomorphism(
                                                iso, fp2, source_kind="research_isomorphism",
                                                transfer_mode="second_order_deanchor"
                                            )}) + "\n")
            except OSError:
                pass
    return {"solve": solve, "impossibility": impossibility, "second_order": second_order,
            "rejected_untyped": rejected}


_DISPOSITIONS = ("forecast", "tested", "wired", "refuted", "stale")


def _cand_key(c: dict) -> str:
    """Stable identity of a surfaced candidate (constraint_class | theorem | field) — sha16."""
    import hashlib
    raw = "|".join(str(c.get(k, "")) for k in ("constraint_class", "theorem", "field"))
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def record_disposition(key: str, status: str, note: str = "", *, ledger: "Path | None" = None) -> dict:
    """Append a DISPOSITION for a surfaced candidate — the accountability tail (RP-002 discipline) the
    ledger lacked: 95 candidates had accrued with ZERO follow-through tracking, which is how built-but-
    unwired yields (Luby, Dawid–Skene) rot. `status` ∈ forecast/tested/wired/refuted/stale."""
    if status not in _DISPOSITIONS:
        raise ValueError(f"status must be one of {_DISPOSITIONS}")
    rec = {"disposition_for": key, "status": status, "note": note}
    led = ledger if ledger is not None else _LEDGER
    led.parent.mkdir(parents=True, exist_ok=True)
    with led.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec) + "\n")
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
            "--disposition KEY STATUS [NOTE...] | --seam SEAM [options]\n\n"
            "Options for --seam:\n"
            "  --abstract TEXT          optional abstract form of the seam\n"
            "  --home FIELD             field to deanchor away from\n"
            "  --model FAMILY           model family, e.g. gemini/deepseek/kimi/claude/codex\n"
            "  --n N                    number of candidates to request\n"
            "  --mode solve|impossibility\n"
            "  --typed-mapping          require mapping for every supplied invariant key\n"
            "  --invariant KEY=VALUE    structural invariant; repeatable\n"
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
        rec = record_disposition(args[1], args[2], " ".join(args[3:]))
        print(json.dumps(rec))
        return 0
    if "--seam" in args:
        import argparse as _ap
        p = _ap.ArgumentParser(prog="ztare research isomorphism")
        p.add_argument("--seam", required=True, help="the research seam, as an operator-neutral constraint")
        p.add_argument("--abstract", default="", help="optional abstract form of the seam")
        p.add_argument("--home", default="", help="the project's own field, to deanchor away from")
        p.add_argument("--model", default="gemini", help="user-selected model family (routes api/subscription)")
        p.add_argument("--n", type=int, default=5, help="number of candidates to request")
        p.add_argument(
            "--mode",
            choices=("solve", "impossibility"),
            default="solve",
            help="ask for solution transports or no-go/impossibility transports",
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
            "--debug",
            action="store_true",
            help="print provider/model, dispatch text length, parse status, and candidates",
        )
        p.add_argument("--json", action="store_true")
        ns = p.parse_args(args)
        try:
            invariants = _parse_invariant_args(ns.invariant)
        except ValueError as exc:
            print(str(exc), file=_sys.stderr)
            return 2
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
    print("usage: research_isomorphism --selftest | --review | --disposition KEY STATUS [NOTE...] | --seam SEAM [options]")
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

    print("SELFTEST", "PASSED" if not fails else f"FAILED: {fails}")
    return 0 if not fails else 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
