"""Governed artifacts — base types (the governed graph, artifact primitives). See `artifacts.py` for the
module-level docstring; this module holds the layer everything else builds on (no internal deps)."""
from __future__ import annotations

from dataclasses import dataclass, field


def normalize(text: str) -> str:
    """The equality normalizer for the firewall: whitespace-collapsed. Verbatim-modulo-whitespace only — NOT
    semantic. Two texts are 'the same claim' iff they normalize equal."""
    return " ".join((text or "").split())


@dataclass(frozen=True)
class GovernedElement:
    """One element of the run's governed final state — a HARDENED claim, a bound evidence item, a falsifier,
    or an adversarial finding. `text` is the authoritative governed wording; artifacts must cite it verbatim."""
    id: str
    kind: str          # claim | evidence | falsifier | finding
    text: str
    source_key: str = ""  # content/lineage identity; byte-identical evidence collapses to one source


# Edge kinds ARE the workbench research-map's relations (`ztare-research-graph-v1`) — the governed argument
# graph and the research map are the same object. The ONLY connectives a deliverable may use, each licensed by
# a governed edge of the matching kind. A relation in an artifact ("therefore", "this mitigates", ordering,
# juxtaposition) is a CLAIM about the relation between two governed elements — so it must cite a governed edge,
# or it launders rhetoric through layout.
EDGE_KINDS = ("REPORTS", "SUPPORTS", "DERIVES", "CHALLENGES", "CONTRADICTS", "CONSTRAINS", "TESTS",
              "FALSIFIES", "RULED_OUT")
_EDGE_CONNECTIVE = {
    "REPORTS": "reports", "SUPPORTS": "supports", "DERIVES": "derives from", "CHALLENGES": "challenges",
    "CONTRADICTS": "contradicts", "CONSTRAINS": "constrains", "TESTS": "tests",
    "FALSIFIES": "falsifies", "RULED_OUT": "rules out",
}


@dataclass(frozen=True)
class GovernedEdge:
    """A governed RELATION between two governed elements — produced inside the loop under the same
    proposer≠grader discipline as the elements. The argument graph is itself governed; the deliverable is a
    rendering of it, and connective tissue is mechanically licensed by these edges."""
    src: str
    kind: str          # one of EDGE_KINDS
    dst: str
    warrant: str = "W3"   # Toulmin warrant class by DETERMINISTIC checkability (argument_kernel.WARRANT_RANK):
    #                       W0 kernel-certificate (LeanMill) · W1 re-executable (recomputes from bound data) ·
    #                       W2 verbatim-quote binding · W3 proposed-unchecked (LLM edge, admitted but MARKED).
    #                       Default W3: an edge is proposed-unchecked until an admission gate mints a stronger class.


@dataclass
class GovernedState:
    """The run's governed final state — the ONLY legal source for artifact content (elements) AND for artifact
    structure (edges). Nothing an artifact asserts — a claim OR a relation between claims — may lack a pre-image."""
    elements: "list[GovernedElement]" = field(default_factory=list)
    edges: "list[GovernedEdge]" = field(default_factory=list)

    def by_id(self, element_id: str) -> "GovernedElement | None":
        return next((e for e in self.elements if e.id == element_id), None)

    def of_kind(self, kind: str) -> "list[GovernedElement]":
        return [e for e in self.elements if e.kind == kind]

    def ids(self) -> "set[str]":
        return {e.id for e in self.elements}

    def has_edge(self, src: str, kind: str, dst: str) -> bool:
        return any(e.src == src and e.kind == kind and e.dst == dst for e in self.edges)


@dataclass(frozen=True)
class Slot:
    """A filled slot in a deliverable: a label + a ref into the governed state + the text placed in the
    artifact. The firewall requires `text` to be verbatim/normalized-equal to the referenced element's text."""
    label: str
    element_id: str
    text: str


@dataclass(frozen=True)
class Relation:
    """A relational statement in a deliverable ("X supports Y") — MUST be licensed by a governed edge of the
    same (src, kind, dst), or it launders rhetoric through layout. This is how a deliverable becomes an
    ARGUMENT (governed edges) rather than a list (governed elements)."""
    src_id: str
    kind: str          # one of EDGE_KINDS
    dst_id: str


@dataclass
class Deliverable:
    """A composed deliverable: a name + governed slots (element content) + governed relations (argument
    structure), OR a stub (an intentional, accounted-for omission)."""
    name: str
    slots: "list[Slot]" = field(default_factory=list)
    relations: "list[Relation]" = field(default_factory=list)
    stub_reason: str = ""      # non-empty ⇒ intentionally omitted (still counts toward set-completeness)
    label: str = ""            # presentation title from a declarative scenario spec; not factual content
    audience: str = ""         # presentation metadata only
    description: str = ""      # presentation metadata only
    presentation_brief: str = ""  # renderer guidance only; never a factual source


@dataclass
class ProvenanceVerdict:
    ok: bool
    violations: "list[str]" = field(default_factory=list)


# Node kinds ARE the research-map node types (`ztare-research-graph-v1`). FINDING_KINDS group the adversarial
# buckets (a research map has no single "finding" type — tensions, gaps and constraints ARE the findings).
NODE_KINDS = ("thesis", "claim", "candidate", "evidence", "tension", "gap", "constraint", "branch",
              "falsifier", "rejected")
FINDING_KINDS = ("tension", "gap", "constraint", "finding")  # research-map buckets + the thin-fallback kind
