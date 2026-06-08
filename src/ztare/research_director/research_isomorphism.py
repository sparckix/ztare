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

from ztare.common.constraint_isomorphism import (
    ConstraintFingerprint, IsomorphismLoop, SurfacedIsomorphism)


@dataclass
class ResearchPrescription:
    """A surfaced cross-field structure transported to the research seam — a candidate to FORECAST
    and test, not a verified result (the gate, opaque to the engine)."""
    source_theorem: str
    source_field: str
    transported_structure: str   # how its mechanism maps onto the seam
    predict_then_falsify: str     # the concrete prediction whose failure would refute the transport


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
                                 "checkable consequence at the seam; its failure refutes the transport")

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
                                        "mechanism": iso.mechanism, "mapping_hint": iso.mapping_hint}) + "\n")
        except Exception:
            pass
    return isos


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

    print("SELFTEST", "PASSED" if not fails else f"FAILED: {fails}")
    return 0 if not fails else 1


if __name__ == "__main__":
    import sys
    sys.exit(_self_test())
