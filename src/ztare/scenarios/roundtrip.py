"""Governed artifacts — the prose round-trip (reingest gate + claim-lifecycle annotation). See `artifacts.py`
for the module-level docstring. Two directions: `reingest_gate`/`promote_reingest` gate a downstream-polished
rendering back INTO the governed graph (an update path); `annotate` reads a source doc and reports each
sentence's claim lifecycle (read-only analysis, the inverse of the firewall)."""
from __future__ import annotations

from dataclasses import dataclass, field

from ztare.common.control_state_machine import ControlStateChart, ControlTransition
from ztare.scenarios.governed_types import GovernedElement, GovernedState, ProvenanceVerdict, normalize
from ztare.scenarios.verdict import _SUPPORT_EDGES


def _prose_sentences(text: str) -> "list[str]":
    """Yield the CLAIM-bearing sentences of a document, STRIPPING markdown markers so a claim written as a bullet
    / block-quote / table cell is gated, NOT skipped (the structure-laundering hole: an unsupported bullet used
    to pass because the whole line was dropped). Skips only true non-claims: headings (section labels), code
    fences, horizontal rules, table-separator rows, and lines already carrying a `← governed` provenance stamp
    (rendered-governed structure). Shared by reingest_gate and annotate so 'what is a claim line' is one
    definition; the MATCH strictness differs per caller (a gate is strict, a tagger is permissive)."""
    import re

    out: "list[str]" = []
    for raw in (text or "").split("\n"):
        line = raw.strip()
        if not line or line.startswith("#"):                       # empty / heading (a label, not a claim)
            continue
        if re.fullmatch(r"_For:\s*.+_", line):                    # recipient metadata, not document prose
            continue
        if line.startswith(("```", "~~~")) or re.fullmatch(r"[-*_=]{3,}", line):   # code fence / horizontal rule
            continue
        if re.fullmatch(r"\|?[\s:|+-]+\|?", line):                 # table-separator row (e.g. |---|:--:|)
            continue
        if "← governed" in line or re.fullmatch(r"</?[a-zA-Z][^>]*>", line) \
                or re.fullmatch(r"<[a-zA-Z][^>]*>.*</[a-zA-Z]+>", line):           # provenance stamp / presentation tag
            continue
        segments = [c.strip() for c in line.strip("|").split("|")] if line.startswith("|") else [line]
        for seg in segments:
            seg = re.sub(r"^\s*(?:>+\s*|[-*+]\s+|\d+[.)]\s+)", "", seg)   # strip quote / bullet / ordered marker
            seg = re.sub(r"<sub>.*?</sub>", "", seg).strip()             # strip an inline provenance stamp
            for sentence in re.split(r"(?<=[.!?])\s+", seg):
                sentence = sentence.strip()
                if sentence:
                    out.append(sentence)
    return out


def align(sentence: str, governed: GovernedState) -> "GovernedElement | None":
    """PERMISSIVE alignment for `annotate` ONLY (which TAGS input, and is not a gate). Returns the first governed
    element whose normalized text equals, contains, or is contained by `sentence` — containment included so a
    bare claim sentence maps to a governed node that bundles it with a note. NOT used by reingest_gate: for
    OUTPUT gating, containment is unsafe — a sentence that is a substring of a governed claim is a DROPPED
    qualifier (see `_governed_sentences`)."""
    norm = normalize(sentence)
    if not norm:
        return None
    for element in governed.elements:
        g = normalize(element.text)
        if g and (norm == g or norm in g or g in norm):
            return element
    return None


def _sentence_key(text: str) -> str:
    """The reingest match key: whitespace-normalized, with a TRAILING sentence-terminator stripped so a governed
    claim (often stored with no end punctuation) matches its rendered sentence ("X" ⟺ "X."). Strips ONLY trailing
    terminators — an INTERNAL qualifier ("under evidence E") is untouched, so the qualifier-drop hole stays shut."""
    return normalize(text).rstrip(".!?").rstrip()


def _governed_sentences(governed: GovernedState) -> "set[str]":
    """The STRICT membership set for reingest: every governed element's full text AND each of its sentences,
    keyed by `_sentence_key`. A polished sentence passes only if it IS one of these — so a sentence that drops a
    qualifier from a governed claim (a substring, not a full governed sentence) is NOT a member and is flagged.
    This is the qualifier-drop hole closed at the gate; `align`'s containment stays on the non-gate annotate side."""
    out: "set[str]" = set()
    for element in governed.elements:
        whole = _sentence_key(element.text)
        if whole:
            out.add(whole)
        # Use the exact document tokenizer for multiline governed elements.
        # Tensions and evidence often carry a short label followed by prose;
        # the renderer preserves that newline, so a second tokenizer here
        # falsely rejects an unchanged governed source packet.
        for sentence in _prose_sentences(element.text):
            key = _sentence_key(sentence)
            if key:
                out.add(key)
    return out


def reingest_gate(polished_text: str, governed: GovernedState) -> ProvenanceVerdict:
    """SAFE downstream polish (Fable's v1.5): a user's AI-polished deliverable comes back; every claim sentence
    must be VERBATIM a governed sentence, or it is flagged UNGOVERNED — fail-closed, total, no LLM judge. STRICT
    by design (this is OUTPUT gating, the stamp): (1) markers are stripped so a laundered bullet/quote/table-cell
    is gated, not skipped; (2) match is normalized-EQUALITY against `_governed_sentences`, never containment, so
    dropping a scope qualifier from a governed claim is caught. Catches the failure modes: an inserted
    connective claim ("therefore", "this refutes") and a silently-weakened claim. Opposite valence from
    `annotate`, which reads INPUT and is permissive."""
    governed_sentences = _governed_sentences(governed)
    violations: "list[str]" = []
    for line in _prose_sentences(polished_text):
        if _sentence_key(line) not in governed_sentences:
            violations.append(f"UNGOVERNED: {line[:90]}")
    return ProvenanceVerdict(ok=not violations, violations=violations)


# ── reingest as an explicit governed-UPDATE path (annotate is read-only ANALYSIS; this is the update gate) ────
# The boundary the review asked to un-blend: `annotate` reads a document and reports lifecycle status, mutating
# nothing. Re-ingest PROMOTES a downstream-polished rendering back as canonical — but only through a session
# that (1) binds to the base governed-state hash, (2) shows a diff (what traced, what was dropped, what is
# ungoverned), (3) promotes ONLY if nothing is ungoverned AND the base has not shifted underneath. NB: re-ingest
# promotes a RENDERING; it does not mutate the governed graph (edges are produced inside the loop under
# proposer≠grader, never by pasting prose) — so the "diff" is trace/drop/ungoverned, not edge edits.
def _governed_hash(governed: GovernedState) -> str:
    """A stable content hash of the governed state (elements + edges), binding a reingest session to the exact
    base it was opened against — so a promote can refuse if the hardened state shifted underneath."""
    import hashlib

    elements = "|".join(sorted(f"{e.id}={normalize(e.text)}" for e in governed.elements))
    edges = "|".join(sorted(f"{e.src}-{e.kind}-{e.dst}" for e in governed.edges))
    return hashlib.sha256(f"{elements}||{edges}".encode("utf-8")).hexdigest()[:16]


@dataclass
class ReingestDiff:
    """What the polished text does relative to the governed state. `ungoverned` BLOCKS promote (untraceable
    prose); `dropped_claims` is a completeness WARNING (a hardened claim silently absent from the polish); the
    trace count is how many governed claims survived verbatim."""
    traced_claims: int = 0
    dropped_claims: "list[str]" = field(default_factory=list)
    ungoverned: "list[str]" = field(default_factory=list)


@dataclass
class ReingestSession:
    """An explicit re-ingest session: the polished rendering measured against a specific base governed state.
    `promotable` iff nothing is ungoverned."""
    project: str
    base_hash: str
    diff: ReingestDiff
    promotable: bool


def reingest_diff(polished_text: str, governed: GovernedState) -> ReingestDiff:
    """Diff a polished rendering against the governed state: traced governed claims, dropped claims (present in
    the graph, absent from the polish — a completeness signal), and ungoverned sentences (in the polish, not
    traceable — these block a promote). Deterministic, reuses the reingest membership set."""
    governed_sentences = _governed_sentences(governed)
    polished = {_sentence_key(s) for s in _prose_sentences(polished_text)}
    claims = governed.of_kind("thesis") + governed.of_kind("claim")
    traced = sum(1 for c in claims if _sentence_key(c.text) in polished)
    dropped = [c.text for c in claims if _sentence_key(c.text) not in polished]
    ungoverned = [s[:90] for s in (_sentence_key(x) for x in _prose_sentences(polished_text))
                  if s not in governed_sentences]
    return ReingestDiff(traced_claims=traced, dropped_claims=dropped, ungoverned=ungoverned)


def open_reingest_session(project: str, polished_text: str, governed: GovernedState) -> ReingestSession:
    """Open a re-ingest session against the CURRENT governed state. Read-only — computes the diff + promotability
    and binds the base hash; promotion is a separate, explicit step (`promote_reingest`)."""
    diff = reingest_diff(polished_text, governed)
    return ReingestSession(project=project, base_hash=_governed_hash(governed),
                           diff=diff, promotable=not diff.ungoverned)


def promote_reingest(session: ReingestSession, polished_text: str, governed: GovernedState,
                     out_path: str, *, at: str = "") -> dict:
    """Promote a polished rendering to canonical — ONLY if (1) the base governed state is unchanged since the
    session opened (hash match) and (2) nothing is ungoverned. Writes the promoted artifact + a sibling
    `.reingest.json` audit record (base hash, diff, timestamp). Refuses otherwise, with a reason. Never mutates
    the governed graph."""
    if _governed_hash(governed) != session.base_hash:
        return {"promoted": False, "reason": "base governed state changed since the session opened; re-open"}
    if session.diff.ungoverned:
        return {"promoted": False,
                "reason": f"{len(session.diff.ungoverned)} ungoverned sentence(s) — fix or drop before promote",
                "ungoverned": session.diff.ungoverned}
    import json as _json
    import os

    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write(polished_text)
    audit = {"schema": "ztare-reingest-promote-v1", "project": session.project, "base_hash": session.base_hash,
             "promoted_at": at, "traced_claims": session.diff.traced_claims,
             "dropped_claims": session.diff.dropped_claims}
    with open(os.path.splitext(out_path)[0] + ".reingest.json", "w", encoding="utf-8") as fh:
        _json.dump(audit, fh, indent=2, ensure_ascii=False)
    return {"promoted": True, "path": out_path, "traced_claims": session.diff.traced_claims,
            "dropped_claims": session.diff.dropped_claims}


# ── Back-annotation: the INVERSE of the forward firewall (the annotated-PRD round-trip) ──────────────────────
# A document (a PRD, a proposal) is INPUT, not a deliverable — so an unaligned sentence is "no claim surfaced",
# NEVER a violation (Fable). The four statuses are a claim's LIFECYCLE STAGES, formalized as a finite state
# machine (reusing `common.control_state_machine`) so the transitions + invariants are one canonical table, not
# scattered ad-hoc branches. Sharpened definitions (each carries an invariant on the chart):
#   BACKED       — aligns to a governed element that carries a SUPPORTS/DERIVES edge AND no open counter.
#   CONTRADICTED — aligns to a governed element that carries a FALSIFIES/CONTRADICTS edge (counter-evidence /
#                  a failed gate). Overrides BACKED until the counter is RULED_OUT.
#   UNTESTED     — aligned/surfaced but no evidence and no counter yet (the queue — the assumption to go test).
#   INERT        — present in the document but not connected to any governed claim. NOT "ungoverned rhetoric":
#                  the surfacer has false negatives, so an unmatched sentence is UNKNOWN, not BAD.
# Same `annotate` call against a MATURING governed state walks the chart (UNTESTED → BACKED as evidence lands;
# → CONTRADICTED on counter-evidence) — no pre-run/post-run mode switch; an empty graph simply cannot emit BACKED.
CLAIM_LIFECYCLE = ControlStateChart(
    schema="ztare-claim-lifecycle-v1",
    transitions=(
        ControlTransition("INERT", "align_to_claim", "UNTESTED",
                          invariant="sentence matches a governed element (verbatim / containment)"),
        ControlTransition("UNTESTED", "bind_evidence", "BACKED",
                          invariant="the aligned element gains a governed SUPPORTS/DERIVES edge, no open counter"),
        ControlTransition("UNTESTED", "counter_evidence", "CONTRADICTED",
                          invariant="the aligned element gains a governed FALSIFIES/CONTRADICTS edge"),
        ControlTransition("BACKED", "counter_evidence", "CONTRADICTED",
                          invariant="new counter-evidence overrides support until the counter is resolved"),
        ControlTransition("CONTRADICTED", "resolve_counter", "BACKED",
                          invariant="the counter is RULED_OUT and governed support remains"),
    ),
)
ANNOTATION_STATUSES = ("BACKED", "CONTRADICTED", "UNTESTED", "INERT")
STATUS_LABELS = {"BACKED": "backed", "CONTRADICTED": "contradicted",
                 "UNTESTED": "untested assumption", "INERT": "no claim surfaced"}
_STATUS_MARK = {"BACKED": "✅", "CONTRADICTED": "⛔", "UNTESTED": "🟡", "INERT": "·"}


@dataclass(frozen=True)
class Annotation:
    """One source sentence + its claim-lifecycle status (a CLAIM_LIFECYCLE state). `element_id` is the governed
    element it aligned to ('' when surfaced-but-not-yet-governed, or inert)."""
    sentence: str
    status: str          # one of ANNOTATION_STATUSES (a state of CLAIM_LIFECYCLE)
    element_id: str = ""


def _annotate_sentence(sentence: str, governed: GovernedState, span_norms: "list[str]") -> Annotation:
    """The terminal CLAIM_LIFECYCLE state for a sentence given the CURRENT governed graph. Precedence follows the
    chart: a counter overrides support (CONTRADICTED > BACKED); alignment-without-evidence is UNTESTED; a
    surfaced-but-unaligned span is UNTESTED (in the queue); nothing surfaced is INERT."""
    element = align(sentence, governed)
    if element is not None:
        opposed = any(e.dst == element.id and e.kind in ("FALSIFIES", "CONTRADICTS") for e in governed.edges)
        if opposed:                                                   # counter overrides support (chart precedence)
            return Annotation(sentence, "CONTRADICTED", element.id)
        supported = any(e.dst == element.id and e.kind in _SUPPORT_EDGES for e in governed.edges)
        if supported:
            return Annotation(sentence, "BACKED", element.id)
        return Annotation(sentence, "UNTESTED", element.id)           # in the graph but no evidence/counter yet
    snorm = normalize(sentence)
    if any(span and span in snorm for span in span_norms):
        return Annotation(sentence, "UNTESTED", "")                   # a surfaced assumption, not yet governed
    return Annotation(sentence, "INERT", "")                          # nothing surfaced — NOT "ungoverned rhetoric"


def annotate(doc: str, governed: GovernedState,
             surfaced_spans: "list[str] | None" = None) -> "list[Annotation]":
    """Back-annotate a source doc with each sentence's claim-lifecycle status — the inverse of the firewall.
    NOT a pass/fail gate (a doc never 'fails'; INERT means 'no claim surfaced here', respecting that the LLM
    surfacer has false negatives). `surfaced_spans` are the already-gated verbatim spans from
    `surface_assumptions` (LLM proposes → kernel gated); pass [] pre-surfacing. Deterministic, no LLM."""
    spans = [normalize(s) for s in (surfaced_spans or []) if str(s).strip()]
    return [_annotate_sentence(sentence, governed, spans) for sentence in _prose_sentences(doc)]


def render_annotated(doc_name: str, annotations: "list[Annotation]",
                     rejected: "list[str] | None" = None) -> str:
    """The same document back, each sentence stamped with its lifecycle status. The doc-level headline is an
    assumption COUNT (triage), never pass/fail — a PRD is input. Dropped surfacer anchors go in a quiet footer
    so the surfacer's coverage is inspectable rather than hidden."""
    counts = {s: sum(1 for a in annotations if a.status == s) for s in ANNOTATION_STATUSES}
    lines = [f"# Annotated: {doc_name}", "",
             f"**{counts['UNTESTED']} load-bearing assumption(s)** · "
             f"{counts['BACKED']} backed · {counts['CONTRADICTED']} contradicted · "
             f"{counts['INERT']} no claim surfaced", "", "---", ""]
    for a in annotations:
        stamp = f"{STATUS_LABELS.get(a.status, a.status.lower())}{(':' + a.element_id) if a.element_id else ''}"
        lines += [f"{_STATUS_MARK.get(a.status, '')} {a.sentence} <sub>← {stamp}</sub>", ""]
    if rejected:
        lines += ["---", "", "<sub>Dropped anchors (surfacer proposed, kernel could not verify verbatim):</sub>", ""]
        lines += [f"<sub>· {r}</sub>" for r in rejected]
    return "\n".join(lines) + "\n"
