"""The multi-claim decision verdict (COMPOUNDER) — a THIN wrapper over the grounded argument kernel. Fable's
review: don't maintain two verdict machines that drift. The principled verdict FUNCTION (grounded ABA acceptance)
and the decision-hinge analysis (ATMS minimal cores) live in `argument_kernel`; this module just packages them
into the `Verdict` the deliverable path expects. The legacy single-toggle `decision_sensitivity` /
`_verdict_status` fold has been REMOVED — minimal cores subsume it (and catch jointly-pivotal sets it missed).
Deterministic, no LLM."""
from __future__ import annotations

from dataclasses import dataclass, field

from ztare.scenarios.argument_kernel import _accepted, minimal_cores, verdict_reason
from ztare.scenarios.argument_kernel import verdict as _grounded_verdict
from ztare.scenarios.governed_types import GovernedState

_SUPPORT_EDGES = ("SUPPORTS", "DERIVES")


@dataclass
class Verdict:
    """A governed verdict over the argument graph, from the grounded argument kernel. `load_bearing` is the
    assumption the decision most turns on — the one appearing in the most MINIMAL CORES (the ATMS
    minimal-environment / prime-implicant analysis), NOT graph degree and NOT a single-toggle swing (which
    misses jointly-pivotal sets). `citations` are the decisive assumption-sets (cores). `coverage` is the
    fraction of claims that are grounded-accepted (a decision-confidence proxy alongside the status)."""
    status: str                       # SUPPORTED | BLOCKED | REFUTED
    reason: str
    citations: "list[str]" = field(default_factory=list)
    load_bearing: str = ""            # the assumption in the most minimal cores ("" if the verdict has no core)
    load_bearing_ties: "list[str]" = field(default_factory=list)  # co-hinges tied for most-cores
    coverage: float = 0.0             # fraction of claims grounded-accepted


def _coverage(governed: GovernedState) -> float:
    """Decision-confidence proxy: the fraction of claims that are grounded-ACCEPTED (evidence-rooted), not merely
    the fraction with some in-edge — so it agrees with the grounded verdict. 0.0 when there are no claims."""
    claims = governed.of_kind("thesis") + governed.of_kind("claim")
    if not claims:
        return 0.0
    accepted = _accepted(governed, frozenset())
    return round(sum(1 for c in claims if c.id in accepted) / len(claims), 3)


def assemble_verdict(governed: GovernedState) -> Verdict:
    """The governed verdict + its load-bearing analysis, from the grounded argument kernel. Status = grounded ABA
    acceptance; load_bearing = the assumption in the most minimal cores (ties exposed, not hidden); citations =
    the decisive assumption-sets. Presentation (the brief, the audit drawer) is a RENDERER concern — the kernel
    emits the data (`serialize_governed`), renderers lay it out."""
    from collections import Counter

    status = _grounded_verdict(governed)
    cores = minimal_cores(governed)
    counts = Counter(a for c in cores for a in c)
    if counts:
        top = max(counts.values())
        ties = sorted(a for a, n in counts.items() if n == top)
    else:
        ties = []
    load_bearing = ties[0] if ties else ""
    reason = verdict_reason(governed)  # single door: same human, actionable reason the brief/workbench show
    citations = [f"core:{{{','.join(sorted(c))}}}" for c in cores[:8]]
    return Verdict(status, reason, citations, load_bearing=load_bearing,
                   load_bearing_ties=ties, coverage=_coverage(governed))
