"""Anti-unification lemma extraction (#124 deferred-leg pulled forward, mathematician lens) — the
library's EDITOR: two kernel-proven sibling rungs often instantiate one unstated general lemma; the
least-general-generalization (lgg) of their STATEMENTS localizes that schema, and the schema becomes a
TARGETED conjecture seed ("formalize the common generalization; instantiate to recover both").

SOUNDNESS (the obstruction_to_conjecture pattern — same package, same discipline): the schema is a
PROMPT SEED for MOVE_CONJECTURE / theory_consolidation, never a compilable statement and never credit.
The agent writes the typed general lemma; the unchanged kernel + governance gate it; a bad schema yields
a no_advance, never a false closure. So this module needs NO type inference — metavariables are holes
the AGENT fills with typed binders.

REUSE (no parallel parsers): tokenization = `statement_integrity._norm` discipline via
`obstruction_to_conjecture._tokens`; statement extraction from certs = `semantic_premise_shelf.
own_ledger_corpus` (the one cert-ledger reader). Alignment = stdlib difflib (deterministic).

  python -m ztare.leanmill.solver.anti_unify --selftest
"""
from __future__ import annotations

import difflib
import re

from ztare.leanmill.solver.obstruction_to_conjecture import _tokens

_MAX_VARS = 4          # a schema that needs >4 holes is not one lemma — it's two unrelated statements
_MAX_COVERAGE = 0.4    # >40% holes ⇒ the "schema" is mostly hole — reject (useless generalization)


def _signature_tokens(stmt: str) -> "list[str]":
    """Tokens of the STATEMENT signature (everything before the top-level `:=`) — the proof body is
    irrelevant to generalization and only adds alignment noise."""
    from ztare.leanmill.lean_source import signature_before_proof
    sig = signature_before_proof(stmt or "")   # binder-safe: a `let k := 5` hyp isn't read as the proof `:=`
    sig = re.sub(r"^\s*(?:@\[[^\]]*\]\s*)?(?:private\s+|protected\s+)?(?:theorem|lemma)\s+\S+", "", sig.strip())
    return _tokens(sig)


def anti_unify(stmt_a: str, stmt_b: str) -> "dict | None":
    """lgg of two Lean statements at token level. Returns
    {schema, vars: {?Mi: (a_span, b_span)}, n_vars, coverage} or None (degenerate / over-general /
    identical). CONSISTENCY (what makes this anti-unification, not a diff): the SAME (a_span, b_span)
    difference recurring is bound to the SAME metavariable."""
    ta, tb = _signature_tokens(stmt_a), _signature_tokens(stmt_b)
    if not ta or not tb or ta == tb:
        return None
    sm = difflib.SequenceMatcher(a=ta, b=tb, autojunk=False)
    out: "list[str]" = []
    var_of: "dict[tuple[str, str], str]" = {}
    hole_tokens = 0
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            out.extend(ta[i1:i2])
            continue
        a_span, b_span = " ".join(ta[i1:i2]), " ".join(tb[j1:j2])
        key = (a_span, b_span)
        if key not in var_of:
            var_of[key] = f"?M{len(var_of) + 1}"
        out.append(var_of[key])
        hole_tokens += max(i2 - i1, j2 - j1)
    n_vars = len(var_of)
    coverage = hole_tokens / max(1, max(len(ta), len(tb)))
    if n_vars == 0 or n_vars > _MAX_VARS or coverage > _MAX_COVERAGE:
        return None
    schema = " ".join(out)
    if ":" not in schema:
        return None                      # no statement shape survived — not a lemma schema
    return {"schema": schema,
            "vars": {v: k for k, v in var_of.items()},
            "n_vars": n_vars, "coverage": round(coverage, 3)}


def schema_conjecture_seed(au: dict, name_a: str, name_b: str) -> str:
    """Render the lgg as a TARGETED conjecture prompt (advisory; the kernel gates the result)."""
    if not au:
        return ""
    lines = [f"Two kernel-proven lemmas ({name_a}, {name_b}) instantiate ONE unstated general lemma.",
             "Their common schema (each ?Mi is a hole where they differ):",
             f"  {au['schema']}"]
    for v, (a, b) in au["vars"].items():
        lines.append(f"  {v}: {name_a} has `{a}`  |  {name_b} has `{b}`")
    lines.append("STATE the typed general lemma (introduce a binder per ?Mi with the right type/class), "
                 "PROVE it, then derive both originals as one-line instantiations. The general lemma must "
                 "be STRICTLY more general — if the holes force incompatible types, REJECT (say so).")
    return "\n".join(lines)


def mine_cert_pairs(cert_ledger=None, attempts_db=None, max_pairs: int = 5) -> "list[dict]":
    """Scan the proven-rung corpus (the ONE cert reader) pairwise for generalizable siblings, ranked by
    fewest holes then lowest coverage (the tightest schemas first). Bounded O(n²) over ≤ the corpus cap."""
    from ztare.leanmill.semantic_premise_shelf import own_ledger_corpus
    rungs = [r for r in own_ledger_corpus(cert_ledger, attempts_db) if r["kind"] == "proven_rung"]
    found = []
    for i in range(len(rungs)):
        for j in range(i + 1, len(rungs)):
            au = anti_unify(rungs[i]["text"], rungs[j]["text"])
            if au:
                found.append({**au, "name_a": rungs[i]["name"], "name_b": rungs[j]["name"],
                              "seed": schema_conjecture_seed(au, rungs[i]["name"], rungs[j]["name"])})
    found.sort(key=lambda d: (d["n_vars"], d["coverage"]))
    return found[:max_pairs]


def _selftest() -> int:
    fails: "list[str]" = []

    def ok(name, cond):
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}")
        if not cond:
            fails.append(name)

    a = "theorem rung_exp (f : PowerSeries ℚ) (h : f.coeff 0 = 1) : Integral (exp_series * f) := by simp"
    b = "theorem rung_log (f : PowerSeries ℚ) (h : f.coeff 0 = 1) : Integral (log_series * f) := by simp"
    au = anti_unify(a, b)
    ok("siblings: ONE hole isolates the differing series",
       au is not None and au["n_vars"] == 1 and ("exp_series", "log_series") in au["vars"].values())
    ok("schema keeps the shared statement shape",
       au is not None and "Integral" in au["schema"] and "?M1" in au["schema"] and ":" in au["schema"])
    # CONSISTENCY: the same difference recurring binds to the SAME metavariable
    c = "theorem t1 (n : ℕ) : foo n + foo n = bar := by simp"
    d = "theorem t2 (n : ℕ) : baz n + baz n = bar := by simp"
    au2 = anti_unify(c, d)
    ok("consistency: recurring difference reuses ?M1 (anti-unification, not a diff)",
       au2 is not None and au2["n_vars"] == 1 and au2["schema"].count("?M1") == 2)
    ok("identical statements ⇒ None (nothing to generalize)", anti_unify(a, a) is None)
    ok("unrelated statements ⇒ None (over-general rejected by the coverage gate)",
       anti_unify("theorem x : ∀ n : ℕ, n + 0 = n := by simp",
                  "theorem y (G : Type) [Group G] (g : G) : g * g⁻¹ = 1 := by simp") is None)
    seed = schema_conjecture_seed(au, "rung_exp", "rung_log")
    ok("seed: targeted prompt names both rungs + the hole bindings",
       "rung_exp" in seed and "log_series" in seed and "STRICTLY more general" in seed)
    # mining through the ONE cert reader (hermetic tmp ledger)
    import json
    import tempfile
    from pathlib import Path
    td = Path(tempfile.mkdtemp(prefix="au_"))
    certs = td / "c.jsonl"
    probe_a = "import Mathlib\n\n" + a + "\n"
    probe_b = "import Mathlib\n\n" + b + "\n"
    certs.write_text(json.dumps({"target": "rung_exp", "outcome": "closed", "ts": "t",
                                 "recompilable_probe": probe_a}) + "\n"
                     + json.dumps({"target": "rung_log", "outcome": "closed", "ts": "t",
                                   "recompilable_probe": probe_b}) + "\n", encoding="utf-8")
    mined = mine_cert_pairs(certs, td / "absent.db")
    ok("mining: the sibling pair surfaces from the cert corpus with its seed",
       len(mined) == 1 and {mined[0]["name_a"], mined[0]["name_b"]} == {"rung_exp", "rung_log"}
       and "?M1" in mined[0]["seed"])   # corpus is newest-first — pair order is not asserted
    print("SELFTEST", "PASSED" if not fails else f"FAILED: {fails}")
    return 0 if not fails else 1


if __name__ == "__main__":
    import sys
    sys.exit(_selftest())
