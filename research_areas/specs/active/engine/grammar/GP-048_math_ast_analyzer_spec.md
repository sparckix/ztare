# GP-048 Math AST Analyzer Spec

## Status

Active

## Scope

- defines an extension to the existing `_NormalizeFamilyAst` normalizer in `src/ztare/validator/structural_memory.py` so that it emits **structural primitive sets** and supports **symbolic tree-edit-distance** between two normalized ASTs
- defines the primitive vocabulary used by GP-047 preservation lane's diversity floor and by GP-045 cold-residual successor mode's residual-set novelty check
- defines the parser's treatment of scipy/numpy/math idioms, implicit multiplication, and nested composition
- defines failure modes and telemetry when parsing fails

Does not cover:

- a symbolic computer algebra system (CAS); this is a coarse structural classifier, not a full simplifier
- equivalence detection up to algebraic rewriting (e.g., `exp(x)*exp(y)` == `exp(x+y)`); deferred as an open question
- parameter-value comparison; primitives and tree structure are parameter-agnostic
- any mutation/rewrite of submitted math; analyzer is read-only
- any dependency beyond Python's stdlib `ast` module; no sympy/mathematica pull-in

## Decision

Extend the existing `_NormalizeFamilyAst` class in `structural_memory.py` rather than build a new parser. The existing normalizer already handles Python `ast.parse(..., mode="eval")`, already normalizes independent variables and parameter names to stable placeholders (`X0`, `X1`, `P0`, `P1`), and already produces a stable fingerprint over the normalized AST dump. It does not yet extract a **structural primitive set** or compute **tree-edit-distance** between two normalized ASTs — those are the two additions this spec authorizes.

This means GP-048 is *not* a from-scratch parser project. It is a targeted ~150-line extension of existing, tested infrastructure. The blocking-prerequisite status from GP-047 is honored but the scope estimate is corrected: GP-048 is a one-session work item, not a multi-week one.

## Problem

GP-047 preservation lane's diversity floor requires two capabilities the current `structural_memory.py` does not expose:

1. **Structural primitive set extraction.** Given a parsed math expression, report the set of structural primitives it uses (e.g., `{power, exp_pos, rational_with_additive_offset}`) so that the diversity floor can check `primitives(I_new) - primitives(I_champion)` is non-empty. The current normalizer produces a fingerprint but does not expose which primitives the AST contains.

2. **Symbolic tree-edit-distance.** Given two parsed math expressions, compute a standard tree-edit-distance (node insertions, deletions, relabels, unit cost) over their normalized ASTs. The diversity floor uses this to enforce a minimal-edit envelope `[d_min, d_max]` on preservation-lane proposals. The current normalizer produces a fingerprint, which tells you *whether* two forms are identical up to variable/parameter renaming, but not *how far apart* they are when they differ.

Both capabilities are referenced by GP-047's diversity floor and by the GP-045 cold-residual successor mode's "is this residual structurally distinct from prior residuals" check. Today those checks are either missing (GP-047 has specced but not implemented them) or use a weaker token-level metric (GP-045's jaccard on tokens, which is brittle for math — see GP-047 Open Questions).

A third capability is nice-to-have but not blocking:

3. **Equivalence-up-to-rewriting detection.** Currently the normalizer fingerprints the literal AST structure; `exp(x)*exp(y)` and `exp(x+y)` have different fingerprints even though they are mathematically identical. A proper symbolic normalizer would apply a fixed set of rewrite rules before fingerprinting. This is deferred because the ZTARE use cases (cold-residual novelty, preservation-lane diversity) tolerate false-distinct (two "different" forms that are mathematically identical just register as two distinct fingerprints) far better than they would tolerate false-identical (two genuinely different forms collapsing to one fingerprint and breaking diversity accounting).

## Why It Matters

GP-047 is blocked on this work. GP-045 would benefit from it but is not blocked — its current jaccard metric is weaker but functional. The immediate demand comes from preservation lane's diversity floor, where jaccard on math tokens was shown to be inadequate (sign flips register as near-identical token multisets but are geometrically opposite).

More fundamentally: ZTARE's structural diversity accounting is one of the decisive surfaces of the Invert leg. Cold-residual's "have I seen this form before" check and preservation lane's "is this a meaningful edit" check both depend on an operational notion of *structural distance* between math expressions. Today that notion is implicit, ad-hoc, and split across two different metrics (fingerprint-equality in structural memory, jaccard-on-tokens in cold-residual). GP-048 centralizes it into one place: the AST analyzer.

Without centralization, every new search-mode spec (GP-047, GP-028, any future lane) has to re-invent its own distance metric, and the metrics drift apart. The ZTARE_BOARD acquires N specs each asserting a different notion of "diversity" that cannot be reconciled. GP-048 is the opposite: one structural-distance surface, used by everyone who needs it.

## Constraints

- must not require a new dependency beyond Python stdlib `ast`
- must extend, not replace, `_NormalizeFamilyAst` in `structural_memory.py` (do not create a parallel parser that will drift)
- must preserve the existing fingerprint-stability contract — GP-042 structural memory already relies on it, and breaking it would invalidate all existing structural-memory files
- must be pure-Python and side-effect-free (no disk writes, no network, no environment dependency)
- must fail loud on unparseable input: raise a named exception, never silently pass
- must be deterministic: two calls with the same input return the same primitive set and the same tree-edit-distance
- must scale at least to the size of any expression the mutator has produced historically (current max is well under 200 AST nodes; a 10× headroom is sufficient)
- must be unit-testable with direct AST inputs; must not require a live run to exercise

## Options

### Option A — Extend `_NormalizeFamilyAst` in place

**Description.** Add two new methods to the existing class: `extract_primitives() -> set[str]` and a module-level function `tree_edit_distance(tree_a, tree_b) -> int`. The primitive extraction walks the normalized AST once and classifies each node into the primitive vocabulary. Tree edit distance uses the Zhang-Shasha algorithm (standard, stdlib-implementable) over the normalized ASTs.

**Pros.**
- single source of truth for AST handling
- inherits existing fingerprint tests and normalization logic
- smallest diff; easiest to review
- no new import surface

**Cons.**
- Zhang-Shasha is O(n² × min-depth²) which is fine for current expression sizes but could be surprising if the mutator produces much larger ASTs later
- primitive classification logic lives inside `structural_memory.py` which is not the most obvious home for it

**Verdict.** Recommended.

### Option B — New module `src/ztare/validator/math_ast_analyzer.py`

**Description.** Create a new module that imports `_NormalizeFamilyAst` from `structural_memory.py` and exposes the new APIs there. The existing fingerprint function stays where it is.

**Pros.**
- cleaner separation of concerns: structural memory is about persistent state, AST analysis is about pure functions over expressions
- easier to test in isolation
- GP-048 code is easy to find

**Cons.**
- two places now handle AST normalization; future readers must know to look in both
- import surface doubles

**Verdict.** Acceptable alternative. Preferred if the primitive-extraction logic grows beyond ~100 lines. Start with Option A; migrate to Option B if the file becomes too large.

### Option C — External library (sympy or similar)

**Description.** Replace the stdlib `ast`-based normalizer with a symbolic math library that handles parsing, normalization, primitive extraction, and tree distance natively.

**Pros.**
- mature equivalence detection (sympy handles exp rewrites, trig simplification, polynomial canonicalization)
- fewer custom correctness concerns

**Cons.**
- adds a heavy dependency to the validator's core import path
- sympy's normalization is too aggressive for ZTARE's purposes — it would collapse structurally different forms that the Invert leg wants to distinguish
- breaks the existing fingerprint contract used by GP-042
- pulls in a large surface the apparatus does not otherwise need

**Verdict.** Not recommended. The ZTARE use case specifically *wants* to distinguish forms that sympy would collapse. Over-normalization is the failure mode to avoid.

## Recommendation

**Adopt Option A.** Extend `_NormalizeFamilyAst` in place with two additions: a primitive-extraction method and a module-level tree-edit-distance function. Migrate to Option B later only if the file grows beyond maintainability. Do not pull in sympy or any external library.

## Implementation Sketch

### Primitive vocabulary

The primitive vocabulary is deliberately structural, not domain-named. Physics names (`denominator_bose`, `denominator_fermi`) are forbidden — they would re-introduce the ontology-trap leak that GP-047 critiqued. The vocabulary is:

| Primitive | Triggered by |
|-----------|--------------|
| `constant` | `ast.Constant` with numeric value, unbound constants normalized to `CONST` |
| `variable` | normalized `X0`, `X1`, ... (independent vars) |
| `parameter` | normalized `P0`, `P1`, ... (fit parameters) |
| `power` | `ast.BinOp(op=ast.Pow)` where the exponent is a variable or parameter |
| `polynomial` | `ast.BinOp(op=ast.Pow)` where the exponent is a `constant` |
| `exp_pos` | call to `math.exp` / `exp` / `numpy.exp` where argument is not negated |
| `exp_neg` | call to `math.exp` / `exp` / `numpy.exp` where argument is (or contains) a top-level negation |
| `log` | call to `math.log` / `log` / `numpy.log` |
| `trig` | calls to `sin`, `cos`, `tan` (and their hyperbolic variants) |
| `sigmoid` | pattern: `1 / (1 + exp(-x))` or `tanh` (structural match after normalization) |
| `rational_simple` | `ast.BinOp(op=ast.Div)` where denominator contains variables or parameters but no additive offset |
| `rational_with_additive_offset` | `ast.BinOp(op=ast.Div)` where denominator is `ast.BinOp(op=ast.Add)` or `ast.BinOp(op=ast.Sub)` containing a constant offset (this covers `1/(f(x) + c)` and `1/(f(x) - c)` without naming Planck/Bose/Fermi) |
| `additive_composition` | top-level `ast.BinOp(op=ast.Add)` with more than one non-trivial term |
| `multiplicative_composition` | top-level `ast.BinOp(op=ast.Mult)` with more than one non-trivial factor |

Notes:
- `exp_pos` vs `exp_neg` is distinguished because the geometry is different: growth vs decay. A mutator adding `exp_neg` to a form that only has `exp_pos` is adding a new primitive even though both are "exp".
- `rational_with_additive_offset` is the primitive GP-047 needs to reach denominator-family generators without naming them. It is structurally defined, not physics-defined.
- `sigmoid` is included because it is a distinct geometric primitive (saturating monotone) even though it can be rewritten in terms of `exp`. The ZTARE Invert leg wants to credit the mutator for reaching this shape.

### `extract_primitives(normalized_tree)` → `set[str]`

Walks the normalized AST with a dedicated visitor. For each node, classifies into one or more primitives per the table above. Returns the union as a `set[str]`.

Pseudo-code:

```python
class _PrimitiveExtractor(ast.NodeVisitor):
    def __init__(self) -> None:
        self.primitives: set[str] = set()

    def visit_BinOp(self, node: ast.BinOp) -> None:
        if isinstance(node.op, ast.Pow):
            if isinstance(node.right, ast.Constant):
                self.primitives.add("polynomial")
            else:
                self.primitives.add("power")
        elif isinstance(node.op, ast.Div):
            if _denominator_has_additive_offset(node.right):
                self.primitives.add("rational_with_additive_offset")
            elif _denominator_has_variables(node.right):
                self.primitives.add("rational_simple")
        elif isinstance(node.op, ast.Add):
            self.primitives.add("additive_composition")
        elif isinstance(node.op, ast.Mult):
            self.primitives.add("multiplicative_composition")
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        name = _call_function_name(node)  # handles math.exp, exp, numpy.exp
        if name == "exp":
            if _arg_contains_top_level_negation(node):
                self.primitives.add("exp_neg")
            else:
                self.primitives.add("exp_pos")
        elif name == "log":
            self.primitives.add("log")
        elif name in {"sin", "cos", "tan", "sinh", "cosh", "tanh"}:
            self.primitives.add("trig")
        self.generic_visit(node)
```

Helpers `_denominator_has_additive_offset`, `_denominator_has_variables`, `_call_function_name`, `_arg_contains_top_level_negation` are all small pure functions over the AST.

Sigmoid detection is a structural pattern match after the normalizer runs, handled in a second pass because it spans multiple nodes.

### `tree_edit_distance(tree_a, tree_b)` → `int`

Standard Zhang-Shasha tree edit distance over normalized ASTs. Unit cost for insertion, deletion, and relabel. Relabel-cost is 1 if the nodes have different types or different structural roles (e.g., `BinOp(Add)` vs `BinOp(Mult)`), 0 if they normalize to the same node class.

Implementation: ~60 lines of pure Python, stdlib-only. Reference implementation: the Zhang-Shasha 1989 paper's recurrence, memoized. For trees with fewer than 200 nodes (current ZTARE scale), runtime is negligible.

The distance is computed over the *normalized* trees (post `_NormalizeFamilyAst`), not the raw ASTs, so variable renames and parameter renames do not count as edits.

### Module-level API

Three public functions in `structural_memory.py`:

```python
def normalize_expression(expression: str, independent_vars: list[str], parameter_names: list[str]) -> ast.AST:
    """Parse and normalize a math expression. Raises ExpressionParseError on failure."""

def extract_primitives(normalized_tree: ast.AST) -> set[str]:
    """Return the structural primitive set of a normalized AST."""

def tree_edit_distance(tree_a: ast.AST, tree_b: ast.AST) -> int:
    """Zhang-Shasha tree edit distance between two normalized ASTs."""
```

Plus one named exception:

```python
class ExpressionParseError(ValueError):
    """Raised when a math expression cannot be parsed or normalized."""
```

### Integration with GP-047

GP-047's diversity floor calls `extract_primitives(normalize_expression(champion))` and `extract_primitives(normalize_expression(proposal))`, computes set difference, and rejects if empty. It calls `tree_edit_distance(...)` and checks the envelope `[d_min, d_max]`. No other GP-047 code touches the AST — all analysis goes through this module.

### Integration with GP-045

GP-045 cold-residual successor mode can optionally migrate its residual-novelty check from jaccard-on-tokens to tree-edit-distance-on-normalized-ASTs. This is a separate decision (see GP-047 Open Questions) and not required by this spec. GP-048 makes the migration possible; it does not force it.

### Testing

Unit tests live in `src/ztare/validator/math_ast_analyzer_test.py` (or co-located with structural memory tests if Option A). Test cases:

- primitive extraction on a known-form corpus (one per primitive, plus composite cases)
- primitive extraction on historical champion forms from prior sandbox runs (read from structural memory files), asserting the primitive set matches hand-labeled expectations
- tree edit distance = 0 for identical forms, > 0 for distinct forms, triangle inequality holds on a sample
- round-trip: normalize → extract → fingerprint must be stable across calls
- parse failure on malformed input raises `ExpressionParseError` with a useful message
- known-tricky cases: implicit multiplication rejection (Python `ast` rejects `2x`, so the parser must document that input expressions use `2*x`), `math.exp` vs `exp` equivalence, `numpy.exp` equivalence

### Primitive classification validation

The primitive table is itself decisive: if it classifies `sigmoid` as just "exp + div + add", GP-047's diversity check loses the ability to credit sigmoid as a new primitive. Validation step before deployment: run `extract_primitives` over at least 20 historical champion expressions from structural memory files across prior runs, and assert that a human-labeled "expected primitives" set matches the extracted set. Mismatches are fixed by tightening the classification rules, not by relaxing the test.

## Open Questions

- **Sigmoid detection pattern-match.** Sigmoid is structurally `1 / (1 + exp(-x))` but after normalization the `-x` becomes `-X0` and the `1` becomes `CONST`. The pattern match must survive normalization. Tentative approach: match on the normalized tree, not the raw tree. Needs implementation and test to confirm the pattern survives.
- **`exp_pos` vs `exp_neg` detection under normalization.** Same issue — after constants are renamed to `CONST`, the sign of the exponent argument may be obscured. The classifier needs to walk the pre-normalized argument or retain sign information during normalization. Small fix, but must be designed explicitly.
- **Should `polynomial` and `power` be the same primitive?** They are distinguished here because `phi^2` (polynomial) and `phi^p` (power with fitted exponent) have different identification semantics — one is fixed, one is fitted. But from a geometric standpoint they are the same family. Decision: keep them distinct for now; revisit after sandbox_05 data.
- **Zhang-Shasha vs simpler APTED or simple bag-of-nodes.** Zhang-Shasha is the standard and fits in stdlib. APTED is faster but requires a dependency. Bag-of-nodes (set-difference) is simpler but loses tree structure. Decision: Zhang-Shasha is the right tradeoff for current expression sizes; revisit if scale changes.
- **Equivalence up to algebraic rewriting.** Deferred. ZTARE's diversity accounting tolerates false-distinct better than false-identical, so a literal structural classifier is safer than an aggressive simplifier. If the false-distinct rate becomes a problem in telemetry, open a separate spec.
- **Cost-of-relabel tuning.** Current proposal: unit cost for any relabel. Could be refined (e.g., `exp_pos → exp_neg` is a smaller semantic change than `exp → log`). Tentative answer: unit cost suffices for slice 1; refine only if the diversity envelope on GP-047 turns out to be too coarse.
- **Should primitive extraction be cached per expression hash?** If the same expression is analyzed N times per iter, a small in-memory cache would help. Tentative answer: yes, keyed on the post-normalization fingerprint; cache lives in-process, not on disk.

## Cross-references

- `src/ztare/validator/structural_memory.py` — existing `_NormalizeFamilyAst` and fingerprint logic; GP-048 extends this file (Option A) or imports from it (Option B)
- GP-042 structural memory spec — existing consumer of `_NormalizeFamilyAst`; must not break
- GP-045 cold residual successor mode — optional future consumer of `tree_edit_distance`
- GP-047 preservation lane probe spec (`specs/active/GP-047_preservation_lane_probe_spec.md`) — blocking consumer; GP-047 launch is gated on GP-048 landing
- GP-035 mutator fit primitive seam — related work on `FIT_DECLARATION` parsing; shares the `FitDeclaration` dataclass that `_NormalizeFamilyAst` currently consumes

## Status Note

Draft complete 2026-04-13. Scope reduced from "build an AST parser" to "extend existing `_NormalizeFamilyAst` with two methods and a module-level distance function" after discovering that `structural_memory.py` already implements normalization. Estimated implementation effort: one working session, including tests. Blocker status on GP-047 stands — GP-047 cannot deploy without this — but the blocker is small.

Next steps:
- register GP-048 on `ZTARE_BOARD.md`
- implement `extract_primitives` with unit tests against the primitive table
- implement `tree_edit_distance` using Zhang-Shasha
- validate primitive classification against ≥20 historical champion expressions from structural memory files
- wire into GP-047 diversity floor once GP-047 is ready to deploy
