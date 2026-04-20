"""Generic set-distance primitives.

Lives outside ``proxy_signature.py`` so callers that need a distance
metric do not have to import a module named after a different concern.
The current callers are:

- ``proxy_signature.compute_anchor_proxy_coverage`` (anchor-proxy drift)
- ``latent_distance`` (GP-029 iter-over-iter motion observability)
- ``projects/eu_union_stability/promote_hypothesis.py`` (hypothesis
  bundle diversity guard — currently keeps a private copy; left
  unchanged here to avoid touching project scripts)

Adding a new set-distance primitive (weighted Jaccard, Sorensen-Dice,
etc.) belongs in this module, not in a domain-specific one.
"""

from __future__ import annotations


def jaccard_distance(set_a: set[str], set_b: set[str]) -> float:
    """Return ``1 - |A ∩ B| / |A ∪ B|``.

    Returns ``0.0`` for two empty sets (the conventional choice — no
    elements means no observable difference). Returns ``1.0`` for two
    disjoint non-empty sets.
    """

    union = set_a | set_b
    if not union:
        return 0.0
    return 1.0 - (len(set_a & set_b) / len(union))
