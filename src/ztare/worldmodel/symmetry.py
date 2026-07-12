"""Substrate-parametric shape canonicalization (Core-Knowledge geometry prior).

Two regions depict the SAME object when one is a rotation or reflection of the
other — a shape and its symmetries are one object (ARC Core Knowledge: geometry +
objectness). ``canonical_form(pattern, group)`` reduces a coloured point-set to a
canonical representative under a symmetry GROUP; equality of canonical forms is
the shape-equivalence test.

The group is SUPPLIED BY THE SUBSTRATE, never hardcoded at the call site: 2D grids
register the dihedral group D4, a future 3D voxel substrate would register the
octahedral group, and the identity group degrades to plain (translation-tolerant)
equality. Because the transform list lives in the group and not the predicate, one
comparison serves every substrate unchanged.
"""
from __future__ import annotations


def _normalize(cells) -> tuple:
    """Translation-quotient representative: shift a coloured point-set to the
    origin (min y, min x) and sort. Colours ride through geometry unchanged
    (exact palette — a transform moves cells, it never recolours them)."""
    pts = [(int(y), int(x), int(c)) for (y, x, c) in cells]
    if not pts:
        return ()
    my = min(y for y, x, c in pts)
    mx = min(x for y, x, c in pts)
    return tuple(sorted((y - my, x - mx, c) for (y, x, c) in pts))


# The eight elements of the dihedral group D4 acting on (y, x): identity, three
# rotations (90/180/270), and four reflections (two axis-aligned, two diagonal).
_D4 = (
    lambda y, x: (y, x),
    lambda y, x: (-x, y),
    lambda y, x: (-y, -x),
    lambda y, x: (x, -y),
    lambda y, x: (y, -x),
    lambda y, x: (-y, x),
    lambda y, x: (x, y),
    lambda y, x: (-x, -y),
)

# Substrate registry. A substrate declares which group its cells live under; new
# substrates register here (or pass an explicit transform sequence) without any
# change to the callers.
SYMMETRY_GROUPS = {
    "identity": (lambda y, x: (y, x),),
    "dihedral": _D4,
}


def _scale_reduce(norm: tuple) -> tuple:
    """Quotient an origin-normalized coloured point-set by uniform block scale: a
    pattern that is an exact k-block upsampling of a smaller pattern (every
    (y//k, x//k) block fully present in one colour) reduces to that primitive.
    Core-Knowledge scale invariance: a glyph and its 2x-rendered display copy are
    the same shape. Irreducible patterns return unchanged."""
    cells = set(norm)
    if not cells:
        return norm
    h = max(y for y, x, c in cells) + 1
    w = max(x for y, x, c in cells) + 1
    for k in range(min(h, w), 1, -1):
        if h % k or w % k:
            continue
        blocks = {}
        ok = True
        for (y, x, c) in cells:
            key = (y // k, x // k)
            if blocks.setdefault(key, c) != c:
                ok = False
                break
        if ok and all(((by * k + dy, bx * k + dx, c) in cells)
                      for (by, bx), c in blocks.items()
                      for dy in range(k) for dx in range(k)):
            return _scale_reduce(tuple(sorted((by, bx, c)
                                              for (by, bx), c in blocks.items())))
    return norm


def canonical_form(pattern, group="dihedral") -> tuple:
    """Canonical representative of `pattern` (an iterable of (y, x, colour) cells)
    under translation x uniform scale x a symmetry `group`.

    `group` is a registry NAME ('dihedral' for 2D grids; 'identity' for plain
    translation+scale-tolerant equality) OR an explicit sequence of
    (y, x) -> (y, x) transforms a substrate supplies (e.g. an octahedral group for
    3D voxels). The transform list is never written at the call site — pass the
    substrate's group and the same predicate holds on any substrate. Two patterns
    are equivalent iff their canonical forms are equal; the scale quotient makes a
    template glyph equal its k-times-larger rendered copy (ARC scale prior)."""
    transforms = SYMMETRY_GROUPS[group] if isinstance(group, str) else group
    cells = [(int(y), int(x), int(c)) for (y, x, c) in pattern]
    if not cells:
        return ()
    return min(_scale_reduce(_normalize([(*t(y, x), c) for (y, x, c) in cells]))
               for t in transforms)


def shape_similarity(a, b, group="dihedral") -> float:
    """Best Jaccard overlap of two coloured point-sets over the group — the
    ranking score for the live-probe fallback when no member matches EXACTLY
    (the sealed reward, not this score, ultimately disposes). 1.0 iff
    group-equivalent."""
    ca = canonical_form(a, group)
    if not ca:
        return 0.0
    cb_cells = [(int(y), int(x), int(c)) for (y, x, c) in b]
    if not cb_cells:
        return 0.0
    transforms = SYMMETRY_GROUPS[group] if isinstance(group, str) else group
    sa = set(ca)
    best = 0.0
    for t in transforms:
        sb = set(_normalize([(*t(y, x), c) for (y, x, c) in cb_cells]))
        inter = len(sa & sb)
        union = len(sa | sb)
        if union:
            best = max(best, inter / union)
    return best


def _demo() -> None:
    """Self-check: a shape equals its 90° rotation under the dihedral group but
    NOT under the identity (translation-only) group."""
    L = [(0, 0, 4), (1, 0, 4), (2, 0, 4), (2, 1, 4)]          # an L tromino
    L_rot90 = [(0, 0, 4), (0, 1, 4), (0, 2, 4), (1, 0, 4)]    # same L, rotated 90°
    assert canonical_form(L, "dihedral") == canonical_form(L_rot90, "dihedral")
    assert canonical_form(L, "identity") != canonical_form(L_rot90, "identity")
    assert canonical_form(L, [lambda y, x: (y, x)]) == canonical_form(L, "identity")
    assert shape_similarity(L, L_rot90, "dihedral") == 1.0
    # scale quotient: the 2x block-upsampled L is the SAME shape as L
    L2 = [(2 * y + dy, 2 * x + dx, c) for (y, x, c) in L for dy in (0, 1) for dx in (0, 1)]
    assert canonical_form(L2, "identity") == canonical_form(L, "identity")
    print("symmetry._demo ok")


if __name__ == "__main__":
    _demo()
