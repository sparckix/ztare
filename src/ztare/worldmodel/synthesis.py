"""Deterministic synthesis kernel over the episode log (GP-250 P0').

Separation of concerns, applied: deterministic search first, the LLM only at
the ceiling. The kernel searches the guarded-command fragment of the seed
grammar — a chain of context-gated plain transforms,

    IF guard_1 THEN plain_1 ELIF guard_2 THEN plain_2 ... ELSE plain_k

— by *deductive context split* rather than blind enumeration: observed
transitions are partitioned by a guard family (action identity, step residue,
cell count), a minimal plain transform is synthesized per context from the
composed transform pool, and the chain is assembled mechanically. This is the
grid analog of the loop's Stage-1 template search: a fixed deterministic
sweep that resolves the easy mass so the mutator is reserved for real
ceilings. If any context admits no consistent transform under every guard
family, the pass returns `grammar_ceiling` — the typed event on which the LLM
mutator (P1) proposes grammar extensions through the promotion contract.

Committee semantics: replay survivors agree on the log by construction, so
members are distinguished on counterfactuals — each under-constrained context
contributes its minimal behaviorally-distinct alternatives, and the committee
is the capped cross product. That committee is exactly what the exploration
policy prices disagreement over.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from itertools import product

from ztare.worldmodel.episode_log import EpisodeLog, Transition
from ztare.worldmodel.grid_dsl import (
    COLOR_LITS, EXTENSIONS, SHIFT_OFFSETS, Program, evaluate, program_size,
)

_PLAIN_POOL_CACHE: dict = {}
_MAX_COMMITTEE = 64
_MAX_ALTERNATIVES_PER_CONTEXT = 4


def _observed_colors(log: EpisodeLog, cap: int = 6) -> tuple:
    """Colors witnessed in the evidence, most-frequent first, capped to bound
    the recolor pair explosion on wide palettes (ARC-AGI-3 uses 16 colors on
    64x64 grids; only witnessed colors can matter to a recovered law)."""
    freq: dict = {}
    for tr in log:
        for g in (tr.s, tr.s_next):
            for row in g:
                for c in row:
                    freq[c] = freq.get(c, 0) + 1
    ranked = sorted(freq, key=lambda c: (-freq[c], c))[:cap]
    return tuple(sorted(ranked)) or COLOR_LITS


def _plain_pool(colors: tuple = COLOR_LITS) -> "list[tuple]":
    """Plain (guard-free) transforms: identity, single and depth-2 compositions
    of translation and relabeling. Size-ordered; cached per color pool."""
    cached = _PLAIN_POOL_CACHE.get(colors)
    if cached is not None:
        return cached
    singles: "list[tuple]" = [("s",)]
    for dy, dx in product(SHIFT_OFFSETS, repeat=2):
        if (dy, dx) != (0, 0):
            singles.append(("shift", ("s",), dy, dx))
    for a, b in product(colors, repeat=2):
        if a != b:
            singles.append(("recolor", ("s",), ("lit", a), ("lit", b)))
    pool = list(singles)
    for outer in singles[1:]:
        for inner in singles[1:]:
            if outer[0] == "shift":
                pool.append(("shift", inner, outer[2], outer[3]))
            else:
                pool.append(("recolor", inner, outer[2], outer[3]))
    pool.sort(key=program_size)
    _PLAIN_POOL_CACHE[colors] = pool
    return pool


def _plain_pool_with_extensions(colors: tuple = COLOR_LITS) -> "list[tuple]":
    """Base pool plus earned extensions (applied to the state and composed
    once with each base single). Built fresh so newly promoted extensions
    join the search immediately."""
    base = _plain_pool(colors)
    if not EXTENSIONS:
        return base
    singles = [p for p in base if program_size(p) <= 4]
    extended = list(base)
    for name in sorted(EXTENSIONS):
        extended.append(("ext", name, ("s",)))
        for inner in singles:
            if inner != ("s",):
                extended.append(("ext", name, inner))
    extended.sort(key=program_size)
    return extended


# ── guard families ──────────────────────────────────────────────────────────
# A guard family maps a transition to a context key and renders the guard
# expression for a given key. Families are tried in order; the first family
# whose every context admits a consistent transform wins (MDL prefers fewer,
# simpler guards via the assembly step).

def _family_none():
    return ("none", lambda tr: 0, lambda key: None, (0,))


def _family_action(arity: int):
    return ("action", lambda tr: tr.a,
            lambda key: ("eq", ("action",), ("lit", key)), tuple(range(arity)))


def _family_step_mod(m: int):
    return (f"step_mod_{m}", lambda tr: tr.t % m,
            lambda key: ("eq", ("mod", ("step",), ("lit", m)), ("lit", key)),
            tuple(range(m)))


def _family_count(color: int, observed_counts: "tuple[int, ...]"):
    def ctx(tr: Transition) -> int:
        return sum(1 for row in tr.s for c in row if c == color)
    return (f"count_{color}", ctx,
            lambda key: ("eq", ("count", color), ("lit", key)), observed_counts)


def _guard_families(log: EpisodeLog, action_arity: int, colors: tuple = COLOR_LITS):
    families = [_family_none(), _family_action(action_arity),
                _family_step_mod(2), _family_step_mod(3)]
    for color in [c for c in colors if c != 0]:
        counts = tuple(sorted({sum(1 for row in tr.s for c in row if c == color) for tr in log}))
        if 1 < len(counts) <= 4:
            families.append(_family_count(color, counts))
    return families


# ── per-context synthesis + chain assembly ──────────────────────────────────

def _consistent_transforms(tuples: "list[Transition]",
                           colors: tuple = COLOR_LITS) -> "list[tuple]":
    """Minimal behaviorally-distinct plain transforms consistent with every
    tuple in one context. Behavior is keyed on the context's own states, so
    alternatives that only differ off-context survive as committee material."""
    out: "dict[tuple, tuple]" = {}
    for cand in _plain_pool_with_extensions(colors):
        ok = True
        for tr in tuples:
            if evaluate(cand, tr.s, tr.a, tr.t) != tr.s_next:
                ok = False
                break
        if not ok:
            continue
        sig = tuple(evaluate(cand, tr.s, a, tr.t) for tr in tuples for a in (tr.a,))
        if sig not in out:
            out[sig] = cand
        if len(out) >= _MAX_ALTERNATIVES_PER_CONTEXT:
            break
    return sorted(out.values(), key=program_size)


def _assemble_chain(guards: "list[tuple | None]", bodies: "list[tuple]") -> Program:
    """Fold (guard, body) pairs into a guarded chain; a None guard is the else."""
    program: Program = ("s",)
    for guard, body in reversed(list(zip(guards, bodies))):
        program = body if guard is None else ("if", guard, body, program)
    # unguarded single body: the chain IS the body
    if len(bodies) == 1 and guards[0] is None:
        return bodies[0]
    return program


@dataclass(frozen=True)
class SynthesisResult:
    """Typed outcome of one synthesis pass.

    status: "committee"       — one or more counterfactually distinct survivors
            "grammar_ceiling" — no guard family closes every context
            "no_evidence"     — empty log; synthesis not attempted
    """
    status: str
    committee: "tuple[Program, ...]" = field(default=())
    guard_family: str = ""
    evidence_hash: str = ""

    @property
    def champion(self) -> "Program | None":
        return self.committee[0] if self.committee else None


def _probe_signature(program: Program, log: EpisodeLog, action_arity: int) -> tuple:
    """Predictions over every logged state crossed with every legal action.
    Members with identical signatures are inseparable on the reachable-so-far
    surface: the policy cannot discriminate them, so they count as one."""
    return tuple(evaluate(program, tr.s, a, tr.t)
                 for tr in log for a in range(action_arity))


def synthesize(log: EpisodeLog, action_arity: int) -> SynthesisResult:
    """Search every guard family and pool the survivors. Spanning all closing
    families (never first-fit) is what makes a singleton committee mean
    something: no alternative anywhere in the guarded fragment survives the
    log, so identification is sound within the fragment."""
    if len(log) == 0:
        return SynthesisResult(status="no_evidence")

    rows = list(log)
    colors = _observed_colors(log)
    members_by_sig: "dict[tuple, Program]" = {}
    closing_families: "list[str]" = []

    for name, ctx_of, render_guard, keys in _guard_families(log, action_arity, colors):
        by_key: "dict[int, list[Transition]]" = {k: [] for k in keys}
        skip = False
        for tr in rows:
            k = ctx_of(tr)
            if k not in by_key:
                skip = True
                break
            by_key[k].append(tr)
        if skip:
            continue

        per_key: "list[list[tuple]]" = []
        closed = True
        for k in keys:
            alts = _consistent_transforms(by_key[k], colors) if by_key[k] else list(_plain_pool_with_extensions(colors)[:_MAX_ALTERNATIVES_PER_CONTEXT])
            if not alts:
                closed = False
                break
            per_key.append(alts)
        if not closed:
            continue

        closing_families.append(name)
        guards = [render_guard(k) for k in list(keys)[:-1]] + [None]
        produced = 0
        for combo in product(*per_key):
            member = _assemble_chain(guards, list(combo))
            sig = _probe_signature(member, log, action_arity)
            held = members_by_sig.get(sig)
            if held is None or program_size(member) < program_size(held):
                members_by_sig[sig] = member
            produced += 1
            if produced >= _MAX_COMMITTEE:
                break

    if not members_by_sig:
        return SynthesisResult(status="grammar_ceiling", evidence_hash=log.content_hash())

    committee = tuple(sorted(members_by_sig.values(), key=program_size))[:_MAX_COMMITTEE]
    return SynthesisResult(status="committee", committee=committee,
                           guard_family=",".join(closing_families),
                           evidence_hash=log.content_hash())


def _any_consistent_transform(tuples: "list[Transition]", colors: tuple) -> bool:
    """Existence-only fast path: first pool candidate consistent with every
    tuple wins. Coverage needs existence, not the full distinct-behavior set."""
    for cand in _plain_pool_with_extensions(colors):
        ok = True
        for tr in tuples:
            if evaluate(cand, tr.s, tr.a, tr.t) != tr.s_next:
                ok = False
                break
        if ok:
            return True
    return False


def context_coverage(log: EpisodeLog, action_arity: int) -> "tuple[int, int]":
    """(covered, total) non-empty guard-family contexts admitting at least one
    consistent transform from the current pool (extensions included). The
    monotone progress measure for multi-extension grammar growth on worlds
    where no single primitive closes synthesis (observed on the first real
    interactive environment): an extension earns retention by strictly
    increasing coverage, and closure is coverage == total for some family."""
    colors = _observed_colors(log)
    covered = total = 0
    for name, ctx_of, render_guard, keys in _guard_families(log, action_arity, colors):
        by_key: "dict[int, list[Transition]]" = {k: [] for k in keys}
        ok = True
        for tr in log:
            k = ctx_of(tr)
            if k not in by_key:
                ok = False
                break
            by_key[k].append(tr)
        if not ok:
            continue
        for k in keys:
            if by_key[k]:
                total += 1
                if _any_consistent_transform(by_key[k], colors):
                    covered += 1
    return covered, total
