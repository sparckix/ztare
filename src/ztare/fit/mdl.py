"""Minimum Description Length (MDL) — the canonical home for the model-selection / compression
math shared across the codebase. Two families, one principle (minimize total description length):

  - bic(): the RSS/Gaussian Bayesian Information Criterion for continuous model selection (curve
    fitting). `fit/compress_champion` uses it to pick the simplest gate-passing form. Lower = better.

  - two-part code length / marginal_compression(): the dictionary/cache MDL. Given items with a
    storage cost and reuse counts, which items net-COMPRESS a corpus (earn caching) vs which are
    dead weight (cost more to store than they save)? The leanmill lemma library uses it to decide
    which banked lemmas to keep in the leaf's context.

Domain-agnostic by design: everything here operates on NUMBERS (point counts, SSE, item sizes,
reuse/exposure counts) — never on Lean text or curve data. Callers compute the sizes; this module
does the MDL accounting. That keeps BIC and the dictionary-MDL in ONE canonical place instead of
re-inlined per call site (BIC was inlined 3× in compress_champion before this) or reimplemented
per domain.
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import Callable, Protocol

# ============================================================ BIC (continuous model selection) ===

def bic(n_pts: int, mse: float, k: int) -> float:
    """Bayesian Information Criterion for a least-squares fit:  n·ln(σ̂²) + k·ln(n), where
    σ̂² = MSE (mean squared error) and `k` is the parameter count (the complexity penalty).
    Lower is better. This is the pure textbook formula — the CALLER supplies an already-positive
    MSE (and owns any numerical floor against log(0), which is data-specific hygiene). That keeps
    this exactly faithful to every prior inline use in compress_champion, whose call sites floored
    differently (some floored SSE, one floored MSE); each now passes its own floored MSE unchanged.

    This is the Gaussian special case of `bic_from_loglik` (the model-independent additive constants
    n·ln(2π)+n are dropped — they cancel in any model comparison on the same data)."""
    return n_pts * math.log(mse) + k * math.log(n_pts)


def bic_from_loglik(log_likelihood: float, k: int, n_obs: int) -> float:
    """General Bayesian Information Criterion for ANY likelihood model:  −2·ln L̂ + k·ln(n),
    where L̂ is the maximized likelihood, `k` the free-parameter count, `n` the number of
    observations. Lower is better. Use this for non-Gaussian models (Bernoulli/binomial, etc.) —
    e.g. deciding whether a finer model (more parameters) is justified by its likelihood gain or
    is just overfitting sparse data. `bic(n, mse, k)` above is the Gaussian special case."""
    return -2.0 * log_likelihood + k * math.log(n_obs)


# ====================================================== two-part code length (dictionary MDL) ===

DEFAULT_CITATION_COST = 4      # units to invoke a cached item (`exact L a b`) vs inlining its body
DEFAULT_MIN_EXPOSURE = 3       # times an item must be offered before net-negative ⇒ proven dead weight

_DESCRIPTION_TOKEN_RE = re.compile(r"[A-Za-z0-9_./:+-]+")

KEEP, RETIRE, PROVISIONAL = "KEEP", "RETIRE", "PROVISIONAL"


def description_units(*parts: object) -> int:
    """Approximate representation length in stable token-like units.

    Domain owners decide which representation closure belongs in ``parts``.
    This function only supplies the shared, deterministic unit measure.
    """

    text = " ".join(str(part) for part in parts if part is not None)
    return max(1, len(_DESCRIPTION_TOKEN_RE.findall(text)))


def marginal_compression(item_size: int, reuse: int, citation_cost: int = DEFAULT_CITATION_COST) -> int:
    """Net units saved by caching an item ONCE vs inlining it at every use:
        reuse · (item_size − citation_cost)  −  item_size.
    Positive ⇒ the item compresses the corpus and earns its storage.
        reuse=0 → −item_size      (pure storage cost, never repaid → dead weight)
        reuse=1 → −citation_cost  (break-even minus invocation overhead; inlining was cheaper)
        reuse≥2 (item_size ≫ cost) → positive (a genuine compressor)."""
    return reuse * (item_size - citation_cost) - item_size


@dataclass
class ItemStat:
    name: str
    size: int
    reuse: int
    exposure: int
    marginal: int
    verdict: str


def score_item(name: str, size: int, reuse: int, exposure: int, *,
               citation_cost: int = DEFAULT_CITATION_COST,
               min_exposure: int = DEFAULT_MIN_EXPOSURE) -> ItemStat:
    """Verdict for one cached item. KEEP = net compressor. RETIRE = exposed `min_exposure`+ times
    and still net-negative (proven dead weight). PROVISIONAL = net-negative but under-exposed — kept,
    because it hasn't had a fair chance to be reused yet (resolves the cache chicken-and-egg)."""
    marg = marginal_compression(size, reuse, citation_cost)
    if marg > 0:
        verdict = KEEP
    elif exposure < min_exposure:
        verdict = PROVISIONAL
    else:
        verdict = RETIRE
    return ItemStat(name=name, size=size, reuse=reuse, exposure=exposure, marginal=marg, verdict=verdict)


def score_items(sizes: "dict[str, int]", reuse: "dict[str, int]",
                exposure: "dict[str, int] | None" = None, *,
                citation_cost: int = DEFAULT_CITATION_COST,
                min_exposure: int = DEFAULT_MIN_EXPOSURE) -> "list[ItemStat]":
    """Score every cached item, best compressor first. `sizes` maps name→size; reuse/exposure
    default to 0 for unseen names."""
    exposure = exposure or {}
    stats = [
        score_item(name, size, reuse.get(name, 0), exposure.get(name, 0),
                   citation_cost=citation_cost, min_exposure=min_exposure)
        for name, size in sizes.items()
    ]
    stats.sort(key=lambda s: (-s.marginal, -s.reuse, s.name))
    return stats


def mdl_partition(sizes: "dict[str, int]", reuse: "dict[str, int]",
                  exposure: "dict[str, int] | None" = None, *,
                  citation_cost: int = DEFAULT_CITATION_COST,
                  min_exposure: int = DEFAULT_MIN_EXPOSURE) -> "tuple[list[str], list[str]]":
    """(keep, retire) names. KEEP = net compressors + under-exposed provisionals; RETIRE = proven
    dead weight. The MDL-optimal cache is exactly the KEEP set."""
    keep, retire = [], []
    for s in score_items(sizes, reuse, exposure, citation_cost=citation_cost, min_exposure=min_exposure):
        (retire if s.verdict == RETIRE else keep).append(s.name)
    return keep, retire


def compression_report(stats: "list[ItemStat]") -> dict:
    """Aggregate compression: units the kept items save vs the dead weight the retired ones cost.
    A self-justifying cache has net > 0."""
    saved = sum(s.marginal for s in stats if s.marginal > 0)
    waste = -sum(s.marginal for s in stats if s.verdict == RETIRE)
    return {"compression_saved": saved, "dead_weight_cost": waste, "net": saved - waste,
            "n_keep": sum(1 for s in stats if s.verdict == KEEP),
            "n_provisional": sum(1 for s in stats if s.verdict == PROVISIONAL),
            "n_retire": sum(1 for s in stats if s.verdict == RETIRE)}


# =========================================================== the extension interface (Strategy) ===
# Consumers don't reimplement the MDL accounting — they import `MDLLibrary` and supply their own
# `size_fn` (how big is one item, in their domain's units), or subclass and override
# `description_length`. The keep/retire/provisional logic above is shared verbatim. autoresearch
# uses the bare functions; leanmill plugs in a Lean-token sizer; a future text cache plugs in a
# byte/token sizer — all on the SAME engine.


class SizeFn(Protocol):
    def __call__(self, item: object) -> int: ...


class MDLLibrary:
    """A generic MDL-governed cache/library: domain-agnostic compression accounting + a pluggable
    description-length function. Construct with `size_fn`, or subclass and override
    `description_length`. `items` everywhere is a name→domain-object map (the size_fn turns each
    object into its size); `reuse`/`exposure` are name→count maps."""

    def __init__(self, size_fn: "Callable[[object], int] | None" = None, *,
                 citation_cost: int = DEFAULT_CITATION_COST,
                 min_exposure: int = DEFAULT_MIN_EXPOSURE):
        self._size_fn = size_fn
        self.citation_cost = citation_cost
        self.min_exposure = min_exposure

    def description_length(self, item: object) -> int:
        if self._size_fn is None:
            raise NotImplementedError("provide a size_fn or override description_length()")
        return self._size_fn(item)

    def _sizes(self, items: "dict[str, object]") -> "dict[str, int]":
        return {name: self.description_length(obj) for name, obj in items.items()}

    def score(self, items: "dict[str, object]", reuse: "dict[str, int]",
              exposure: "dict[str, int] | None" = None) -> "list[ItemStat]":
        return score_items(self._sizes(items), reuse, exposure,
                           citation_cost=self.citation_cost, min_exposure=self.min_exposure)

    def partition(self, items: "dict[str, object]", reuse: "dict[str, int]",
                  exposure: "dict[str, int] | None" = None) -> "tuple[list[str], list[str]]":
        return mdl_partition(self._sizes(items), reuse, exposure,
                            citation_cost=self.citation_cost, min_exposure=self.min_exposure)

    def report(self, items: "dict[str, object]", reuse: "dict[str, int]",
               exposure: "dict[str, int] | None" = None) -> dict:
        return compression_report(self.score(items, reuse, exposure))


def _self_test() -> int:
    fails = []

    def ok(name, cond):
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}")
        if not cond:
            fails.append(name)

    # --- BIC: lock the pure textbook formula (caller supplies the floored MSE) ---
    for n, mse, k in [(20, 1e-3, 2), (50, 0.25, 4), (8, 1e-9, 1), (100, 5.0, 6)]:
        ok(f"bic_is_textbook_n{n}_k{k}",
           abs(bic(n, mse, k) - (n * math.log(mse) + k * math.log(n))) < 1e-12)
    # the way compress_champion reconstructs its old inline values via this bic (exact identity):
    ok("bic_reproduces_sse_floor_site",
       bic(100, max(0.0, 1e-300) / 100, 4) == 100 * math.log(max(0.0, 1e-300) / 100) + 4 * math.log(100))
    ok("bic_reproduces_mse_floor_site",
       bic(100, max(0.0 / 100, 1e-300), 4) == 100 * math.log(max(0.0 / 100, 1e-300)) + 4 * math.log(100))
    ok("bic_penalizes_complexity", bic(50, 0.005, 6) > bic(50, 0.005, 2))  # more params ⇒ worse
    ok("bic_rewards_lower_mse", bic(50, 0.002, 4) < bic(50, 0.02, 4))      # better fit ⇒ better
    # general likelihood-form BIC: more params penalized; better likelihood rewarded
    ok("bic_loglik_penalizes_params", bic_from_loglik(-100, 8, 200) > bic_from_loglik(-100, 2, 200))
    ok("bic_loglik_rewards_fit", bic_from_loglik(-90, 4, 200) < bic_from_loglik(-100, 4, 200))

    # --- two-part code MDL ---
    SIZE = 20
    ok("reuse0_dead_weight", marginal_compression(SIZE, 0) == -SIZE)
    ok("reuse1_break_even_negative", marginal_compression(SIZE, 1) < 0)
    ok("reuse2_net_compressor", marginal_compression(SIZE, 2) > 0)

    sizes = {"compressor": SIZE, "dead_weight": SIZE, "untried": SIZE}
    reuse = {"compressor": 3}
    exposure = {"compressor": 4, "dead_weight": 5, "untried": 1}
    keep, retire = mdl_partition(sizes, reuse, exposure)
    ok("keeps_net_compressor", "compressor" in keep)
    ok("retires_proven_dead_weight", "dead_weight" in retire)
    ok("keeps_under_exposed_provisional", "untried" in keep and "untried" not in retire)

    stats = score_items(sizes, reuse, exposure)
    ok("sorted_best_compressor_first", stats[0].name == "compressor")
    rep = compression_report(stats)
    ok("net_positive_when_compressor_dominates", rep["net"] > 0)
    ok("counts_partition", rep["n_keep"] == 1 and rep["n_provisional"] == 1 and rep["n_retire"] == 1)
    ok("smaller_item_lower_marginal", marginal_compression(6, 2) < marginal_compression(SIZE, 2))

    # --- the extension interface: a consumer plugs in its own size_fn over domain objects ---
    lib = MDLLibrary(size_fn=lambda block: len(str(block).split()))   # size = whitespace tokens
    items = {"big_reused": "a " * SIZE, "big_dead": "b " * SIZE, "untried": "c " * SIZE}
    keep2, retire2 = lib.partition(items, {"big_reused": 3}, {"big_reused": 4, "big_dead": 5, "untried": 1})
    ok("iface_keeps_compressor", "big_reused" in keep2)
    ok("iface_retires_dead_weight", "big_dead" in retire2)
    ok("iface_keeps_provisional", "untried" in keep2)
    ok("iface_report_matches_core", lib.report(items, {"big_reused": 3},
       {"big_reused": 4, "big_dead": 5, "untried": 1})["net"] > 0)

    class _Sub(MDLLibrary):
        def description_length(self, item):
            return len(str(item))   # override path: size = char count
    ok("iface_subclass_override", _Sub().score({"x": "abcde"}, {})[0].size == 5)

    print("SELFTEST", "PASSED" if not fails else f"FAILED: {fails}")
    return 0 if not fails else 1


if __name__ == "__main__":
    import sys
    sys.exit(_self_test())
