"""MOVE_FUNCTOR_LIFT — discrete → continuous/spectral lift (NumPy-exogenous, kernel-gated, 2026-06-08).

The strategist move for a node STUCK on a DISCRETE / combinatorial goal over a finite structure (a graph,
a finite group's Cayley graph, a 0/1 matrix, a finite poset): instead of attacking the combinatorial claim
directly, LIFT it to the continuous/spectral domain along a FUNCTOR the mathematician uses by hand:

    graph G ──(adjacency)──▶ matrix A ──(eigen / spectral gap)──▶ a continuous bound on a DISCRETE property
                                                                  (Expander Mixing Lemma, Cheeger,
                                                                   Hoffman bound, interlacing, …)

Worked archetype (Expander Mixing Lemma): bound the edge count `e(S,T)` between two vertex sets of a
d-regular graph by `(d/n)|S||T| + λ·√(|S||T|)`, where λ = the second-largest |eigenvalue| of the adjacency
matrix. The eigenvalue λ is found in NumPy (`numpy.linalg.eigvalsh`, EXOGENOUS — Lean has no native
eigensolver for a concrete numeric matrix), and the continuous bound is discharged in Lean by APPLYING an
EXISTING Mathlib bridge lemma (the "pullback" of the spectral statement to the discrete one).

THE GATE THAT MAKES THIS SOUND-AND-FAST (the whole point of this move):
  the required Mathlib BRIDGE LEMMA — the functor's pullback, e.g. `SimpleGraph.expander_mixing` or
  `Matrix.IsHermitian.eigenvalues`, whatever the leaf names — MUST ALREADY EXIST. We verify that BEFORE
  committing any budget, with a falsify-style EXISTENCE probe (`#check <bridge>` compiled under the kernel,
  exactly like the existence checks in conjecture/witness_transport). If the bridge lemma is ABSENT the move
  ABORTS (`bridge_absent`) — we do NOT try to PROVE the bridge from scratch (that is the open-problem regime
  the SPECIALIZE / CONJECTURE moves are for, and a bare leaf times out reinventing spectral graph theory).
  This is the narrow, domain-specific niche: a discrete goal whose continuous bridge is ALREADY in Mathlib.

SOUNDNESS (no laundering, mirrors conjecture.py / witness_transport.py exactly):
  * NumPy never CLOSES anything — it only computes a numeric λ / spectral gap (a WITNESS, like the SymPy
    witness in witness_transport). A wrong/hallucinated λ merely makes the assembled Lean proof FAIL to
    compile (a MISS), never a false closure: the kernel re-derives the bound from the cited bridge lemma.
  * The closure is decided ONLY by `_compile_probe` (the v33 kernel typecheck) on the assembled proof, which
    must (a) be sorry-free, (b) CITE the verified-present bridge lemma in real tactic text (comments
    stripped), (c) typecheck against `import Mathlib` + the preamble. Same three legs as `conjecture_advances`.
  * NumPy is LAZY-IMPORTED and FAIL-CLOSED: absent ⇒ `bridge_present=…, numeric=None` ⇒ no spectral data
    ⇒ no proof assembled ⇒ no closure (never a silent admit; the 2026-06-01 dead-instrument rule).

FLAG: gated behind `ZTARE_LEANMILL_FUNCTORLIFT` (default OFF ⇒ this module is never imported by the runner ⇒
byte-identical parity). HONEST SCOPE: narrow + domain-specific (finite graphs/0-1-or-integer matrices whose
spectral bridge is already a Mathlib lemma). NOT a general discrete→continuous oracle. The leaf names the
functor + bridge lemma; the kernel + NumPy are the only arbiters.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

# ── 1. LLM generation (mirrors conjecture_generate / specialize_generate) ───────────────────────────
_FUNCTOR_LIFT_PROMPT = (
    "You are a Lean 4 + spectral-graph-theory expert. The GOAL below is a DISCRETE / combinatorial claim "
    "about a FINITE structure (a graph, a finite 0/1 or integer matrix, a finite group's Cayley graph). "
    "Proving it directly is hard. Use the FUNCTOR LIFT: map the discrete object to a MATRIX, pass to its "
    "SPECTRUM (eigenvalues / spectral gap), and bound the discrete property with a CONTINUOUS spectral "
    "bound (Expander Mixing Lemma, Cheeger inequality, Hoffman bound, eigenvalue interlacing).\n"
    "CRITICAL — the continuous bound must be discharged by an EXISTING Mathlib lemma (the 'bridge'/pullback "
    "of the spectral statement back to the discrete one). NAME that exact Mathlib lemma; do NOT invent a new "
    "one (a bridge that does not already exist will be REJECTED — that is not your job here).\n"
    "Output EXACTLY these four blocks:\n"
    "MATRIX:\n```json\n{{\"matrix\": [[<row0>], [<row1>], ...], \"kind\": \"adjacency\"}}\n```\n"
    "   (the concrete finite matrix the discrete object maps to — a rectangular list-of-lists of integers; "
    "for a graph use its symmetric 0/1 adjacency matrix)\n"
    "BRIDGE:\n```lean\n<the fully-qualified name of the EXISTING Mathlib bridge lemma, e.g. "
    "`Matrix.IsHermitian.eigenvalues` — JUST the name, nothing else>\n```\n"
    "SPECTRAL:\n```lean\n<a one-line Lean comment stating the continuous bound you will instantiate, e.g. "
    "`-- e(S,T) ≤ (d/n)|S||T| + λ√(|S||T|)` — for the human/audit log only>\n```\n"
    "PROOF:\n```lean\n{goal_head} := by\n  <tactics that APPLY the BRIDGE lemma to close the goal; NO sorry, "
    "NO admit; must reference the bridge lemma>\n```\n"
    "Self-contained against `import Mathlib` + the PREAMBLE. The PROOF must cite the BRIDGE lemma in real "
    "tactic text and contain NO sorry.\nGOAL:\n{goal}\n"
)


def functor_lift_generate(row: dict, goal_text: str, lean_root: Path, timeout_s: int,
                          preamble: str = "") -> "tuple[str, str, str, str, str]":
    """Ask the leaf for the discrete→spectral lift: the concrete MATRIX (json), the EXISTING Mathlib BRIDGE
    lemma name, the human-readable SPECTRAL bound, and the Lean PROOF that applies the bridge to close the
    goal. Returns (matrix_json, bridge_name, spectral_note, proof_block, raw_tail). On any parse/dispatch
    failure returns ('', '', '', '', err) ⇒ no_lift, never a false closure. (Same fenced-parse + fail-soft
    contract as conjecture_generate / specialize_generate.)"""
    from ztare.leanmill.lean_source import signature_before_proof   # canonical binder-safe head extractor
    goal_head = signature_before_proof(goal_text or "").strip() or (goal_text or "")
    prompt = _FUNCTOR_LIFT_PROMPT.format(goal=goal_text, goal_head=goal_head)
    if preamble.strip():
        prompt = prompt.replace("the PREAMBLE", "the PREAMBLE below") + "\nPREAMBLE:\n" + preamble.strip() + "\n"
    try:
        from ztare.leanmill.solver.agentic_leaf import default_dispatch
        raw = default_dispatch(prompt, repo=lean_root, timeout=timeout_s) or ""
    except Exception as e:  # noqa: BLE001
        return "", "", "", "", f"dispatch_error: {e!r}"

    from ztare.leanmill.solver.agent_output import fenced_block
    matrix_json = fenced_block(raw, "MATRIX:", "json")
    bridge = fenced_block(raw, "BRIDGE:", "lean")
    spectral = fenced_block(raw, "SPECTRAL:", "lean")
    proof = fenced_block(raw, "PROOF:", "lean")
    # the BRIDGE block is a bare identifier — keep only the first dotted-name token (the leaf may add a stray
    # backtick / trailing prose despite the instruction).
    bm = re.search(r"[A-Za-z_][\w'.]*", bridge)
    bridge = bm.group(0) if bm else ""
    return matrix_json, bridge, spectral, proof, (raw or "")[-200:]


# ── 2. The bridge-lemma EXISTENCE gate (falsify-style, MUST pass BEFORE committing) ─────────────────
def bridge_lemma_exists(bridge_name: str, lean_root: Path, timeout_s: int, preamble: str = "") -> "tuple[bool, str]":
    """GATE-FIRST existence check for the Mathlib bridge lemma (the functor's pullback). Compile a minimal
    `#check @<bridge_name>` probe under the kernel (the same `_compile_probe` every other move uses, the same
    pattern as the `#check`/`exact?` existence checks elsewhere in the solver). The bridge EXISTS iff that
    probe typechecks cleanly.

    Returns (exists, reason). `_compile_probe` returns None on an INFRA failure (sandbox missing / lake
    timeout): we treat None as 'cannot confirm' ⇒ FALSE (fail-CLOSED — never assume a bridge is present on a
    tooling error; that would let the move proceed to assemble a proof against a possibly-nonexistent lemma).

    This is the move's reason to exist: if the bridge is ABSENT we ABORT here and NEVER ask the leaf to prove
    the spectral theory from scratch (it times out — see the module docstring)."""
    name = (bridge_name or "").strip()
    if not name or not re.fullmatch(r"[A-Za-z_][\w'.]*", name):
        return False, f"no/invalid bridge lemma name: {name!r}"
    from ztare.gates.v33_preflight_risk_detector import _compile_probe
    _pre = (preamble.strip() + "\n\n") if preamble.strip() else ""
    # `#check @<name>` elaborates the (possibly polymorphic) constant by its FULLY-EXPLICIT form — it errors
    # iff the identifier is unknown / not in scope. A `#check` is non-closing, so this can never launder a
    # proof; it strictly tests presence-in-Mathlib.
    probe = _pre + f"import Mathlib\n\n#check @{name}"
    if not probe.lstrip().startswith("import"):
        probe = "import Mathlib\n\n" + probe
    ok = _compile_probe(probe, lean_root, "FunctorLiftBridge", timeout_s)
    if ok is True:
        return True, f"bridge lemma `{name}` is present in Mathlib (#check clean)"
    if ok is None:
        return False, f"could not confirm bridge `{name}` (infra/timeout) — fail-closed (treated as absent)"
    return False, f"bridge lemma `{name}` is ABSENT (#check errored) — ABORT (do NOT prove it from scratch)"


# ── 3. NumPy-EXOGENOUS spectral compute (lazy import, fail-CLOSED if absent) ─────────────────────────
def _load_matrix(matrix_json: str) -> "list | None":
    """Parse the leaf's MATRIX json to a rectangular list-of-lists of numbers. None on any defect (⇒ the
    caller produces no numeric ⇒ no proof ⇒ no closure — never a silent admit)."""
    if not (matrix_json or "").strip():
        return None
    try:
        obj = json.loads(matrix_json)
    except Exception:  # noqa: BLE001
        return None
    mat = obj.get("matrix") if isinstance(obj, dict) else obj
    if not isinstance(mat, list) or not mat or not all(isinstance(r, list) and r for r in mat):
        return None
    width = len(mat[0])
    if any(len(r) != width for r in mat):
        return None                                   # not rectangular
    for r in mat:
        if not all(isinstance(x, (int, float)) and not isinstance(x, bool) for x in r):
            return None
    return mat


def compute_spectral_bound(matrix_json: str) -> "dict | None":
    """EXOGENOUS spectral compute on the leaf's concrete matrix (NumPy). Returns a dict of numeric spectral
    quantities the assembled Lean proof / audit can reference:
        {n, eigenvalues, spectral_radius, lambda2 (2nd-largest |eigenvalue|, the EML expander param),
         spectral_gap (λ1 − λ2 for a symmetric matrix), symmetric}
    or None if the matrix is unusable OR NumPy is unavailable.

    NumPy is LAZY-IMPORTED and FAIL-CLOSED: if `import numpy` raises (absent in the env) we return None — the
    move then produces no spectral data and assembles no proof, so a missing NumPy is a clean MISS, NEVER a
    silent admit (the 2026-06-01 dead-instrument rule: a negative is inadmissible without the instrument
    actually running). Eigenvalues of a symmetric/Hermitian matrix use `eigvalsh` (real spectrum, the graph
    case); a non-symmetric matrix falls back to `eigvals` and reports |eigenvalues|."""
    mat = _load_matrix(matrix_json)
    if mat is None:
        return None
    try:
        import numpy as np  # LAZY + FAIL-CLOSED: absent ⇒ None (no silent admit)
    except Exception:  # noqa: BLE001 — ImportError or a broken numpy install
        return None
    try:
        A = np.array(mat, dtype=float)
        if A.ndim != 2 or A.shape[0] != A.shape[1]:
            return None                                # only square matrices have a spectrum
        symmetric = bool(np.allclose(A, A.T))
        if symmetric:
            ev = np.linalg.eigvalsh(A)                 # real spectrum (the graph/Hermitian case)
            absev = np.abs(ev)
            lambda1 = float(np.max(ev))
            # λ2 = the SECOND-largest eigenvalue in ABSOLUTE value (the Expander-Mixing param)
            order = np.argsort(absev)[::-1]
            lambda2 = float(absev[order[1]]) if A.shape[0] >= 2 else 0.0
            gap = float(lambda1 - float(ev[np.argsort(ev)[-2]])) if A.shape[0] >= 2 else 0.0
            eig_list = [round(float(x), 9) for x in ev]
        else:
            ev = np.linalg.eigvals(A)
            absev = np.abs(ev)
            order = np.argsort(absev)[::-1]
            lambda1 = float(absev[order[0]])
            lambda2 = float(absev[order[1]]) if A.shape[0] >= 2 else 0.0
            gap = float(lambda1 - lambda2)
            eig_list = [round(float(abs(x)), 9) for x in ev]
        return {
            "n": int(A.shape[0]),
            "eigenvalues": eig_list,
            "spectral_radius": round(float(np.max(absev)), 9),
            "lambda2": round(lambda2, 9),
            "spectral_gap": round(gap, 9),
            "symmetric": symmetric,
        }
    except Exception:  # noqa: BLE001 — a singular/degenerate matrix etc.: no spectral data ⇒ None (no admit)
        return None


# ── 4. The KERNEL gate (mirrors conjecture_advances) ────────────────────────────────────────────────
def functor_lift_advances(proof: str, bridge_name: str, lean_root: Path, timeout_s: int,
                          preamble: str = "", spectral: "dict | None" = None) -> "tuple[bool, str]":
    """Kernel-checked CLOSURE test for the assembled lift proof. The goal closes iff:
      (a) the bridge lemma is verified-present (the caller MUST have run `bridge_lemma_exists` first; we
          re-assert it cheaply here so a direct call can't skip the gate),
      (b) NumPy actually produced spectral data (`spectral` is a dict) — a lift with no eigenvalues computed
          is not a spectral lift (guards against a silent NumPy-absent admit),
      (c) the PROOF is sorry-free / admit-free,
      (d) the PROOF CITES the bridge lemma in real tactic text (comments stripped — not a spurious direct
          proof that ignores the lift), and
      (e) the snippet TYPECHECKS under `import Mathlib` + the preamble (`_compile_probe`).
    NumPy never closes — only (e), the kernel, decides. A wrong λ makes (e) fail (a MISS), never a false
    closure. Returns (closed, reason). (Same shape + same `_compile_probe` arbiter as conjecture_advances.)"""
    if not (proof or "").strip():
        return False, "no lift proof generated"
    if spectral is None:
        return False, "no spectral data (NumPy absent or matrix unusable) — no lift to verify (fail-closed)"
    from ztare.leanmill.lean_source import has_sorry as _has_sorry, strip_comments   # comment-stripping (2026-06-13 audit)
    if _has_sorry(proof):
        return False, "lift proof not sorry-free (must close via the bridge, not a hidden sorry)"
    name = (bridge_name or "").strip()
    if not name:
        return False, "no bridge lemma named"
    proof_nc = strip_comments(proof)   # strip Lean comments
    # cite-check: the bridge lemma must appear by its (possibly final) name component in real tactic text.
    short = name.split(".")[-1]
    if name not in proof_nc and not re.search(rf"(?<![\w'.]){re.escape(short)}(?![\w'])", proof_nc):
        return False, "lift proof does not CITE the bridge lemma in tactic text (spurious / comment-only)"
    # (a) re-assert the bridge is present (cheap #check) — a direct caller cannot bypass the existence gate.
    present, why = bridge_lemma_exists(name, lean_root, timeout_s, preamble=preamble)
    if not present:
        return False, f"bridge gate failed: {why}"
    from ztare.gates.v33_preflight_risk_detector import _compile_probe
    _pre = (preamble.strip() + "\n\n") if preamble.strip() else ""
    snippet = _pre + proof.strip()
    if not snippet.lstrip().startswith("import"):
        snippet = "import Mathlib\n\n" + snippet
    ok = _compile_probe(snippet, lean_root, "FunctorLiftClose", timeout_s)
    if ok is None:
        return False, "lift proof: kernel infra/timeout (indeterminate) — fail-closed (no closure)"
    if ok is not True:
        return False, "lift proof did NOT typecheck (the spectral bound does not discharge the goal)"
    return True, ("closed — discrete goal lifted to the spectrum (λ2={l2}, gap={g}) and discharged via the "
                  "verified bridge `{b}`").format(l2=spectral.get("lambda2"), g=spectral.get("spectral_gap"), b=name)


def _selftest() -> int:
    """POSITIVE + NEGATIVE controls for every NON-Lean leg (NumPy + parsers + the bridge-name guard). The
    legs that require a live Lean toolchain (`bridge_lemma_exists` / `functor_lift_advances` end-to-end) are
    exercised in-loop by the runner against the real sandbox; here we prove the GATE SAYS NO on bad input
    (a gate that never refuses is a false-success generator) and the EXOGENOUS NumPy compute is correct."""
    fails = []

    def ok(name, cond):
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}")
        if not cond:
            fails.append(name)

    # ── matrix parse: POSITIVE (good json) + NEGATIVE (ragged / non-numeric / garbage / empty) ──
    ok("parse: POS valid 2x2 adjacency json",
       _load_matrix('{"matrix": [[0, 1], [1, 0]], "kind": "adjacency"}') == [[0, 1], [1, 0]])
    ok("parse: POS bare list-of-lists (no wrapper)", _load_matrix('[[0,1],[1,0]]') == [[0, 1], [1, 0]])
    ok("parse: NEG ragged rows → None", _load_matrix('{"matrix": [[0, 1], [1]]}') is None)
    ok("parse: NEG non-numeric entry → None", _load_matrix('{"matrix": [["a", 1], [1, 0]]}') is None)
    ok("parse: NEG bool entry rejected → None", _load_matrix('{"matrix": [[true, 1], [1, 0]]}') is None)
    ok("parse: NEG not json → None", _load_matrix('not json at all') is None)
    ok("parse: NEG empty → None", _load_matrix('') is None)

    # ── NumPy EXOGENOUS spectral compute: POSITIVE controls on KNOWN spectra ──
    # K2 (single edge) adjacency [[0,1],[1,0]]: eigenvalues {+1,-1}; spectral_radius 1; λ2 = 1; gap = 0.
    k2 = compute_spectral_bound('{"matrix": [[0,1],[1,0]]}')
    if k2 is None:
        ok("numpy: AVAILABLE (lazy import succeeded)", False)
    else:
        ok("numpy: AVAILABLE (lazy import succeeded)", True)
        ok("numpy: K2 eigenvalues {-1,+1}", sorted(k2["eigenvalues"]) == [-1.0, 1.0])
        ok("numpy: K2 spectral_radius = 1", abs(k2["spectral_radius"] - 1.0) < 1e-9)
        ok("numpy: K2 symmetric flag", k2["symmetric"] is True)
        # C4 (4-cycle) adjacency: eigenvalues {2, 0, 0, -2}; λ1 = 2 (Perron = degree d), λ2 = 2 (|−2|),
        # spectral radius 2. (A bipartite d-regular graph has −d in its spectrum ⇒ |λ2| = d.)
        c4 = compute_spectral_bound('{"matrix":[[0,1,0,1],[1,0,1,0],[0,1,0,1],[1,0,1,0]]}')
        ok("numpy: C4 Perron eigenvalue +2 present", c4 is not None and 2.0 in c4["eigenvalues"])
        ok("numpy: C4 spectral_radius = 2 (degree)", c4 is not None and abs(c4["spectral_radius"] - 2.0) < 1e-9)
        ok("numpy: C4 λ2 = 2 (bipartite ⇒ −d in spectrum)", c4 is not None and abs(c4["lambda2"] - 2.0) < 1e-9)
        # Petersen graph: 3-regular, well-known spectrum {3, 1 (×5), −2 (×4)} ⇒ spectral_radius 3, gap = 3−1 = 2.
        pet = [[0,1,0,0,1,1,0,0,0,0],[1,0,1,0,0,0,1,0,0,0],[0,1,0,1,0,0,0,1,0,0],
               [0,0,1,0,1,0,0,0,1,0],[1,0,0,1,0,0,0,0,0,1],[1,0,0,0,0,0,0,1,1,0],
               [0,1,0,0,0,0,0,0,1,1],[0,0,1,0,0,1,0,0,0,1],[0,0,0,1,0,1,1,0,0,0],
               [0,0,0,0,1,0,1,1,0,0]]
        ps = compute_spectral_bound(json.dumps({"matrix": pet}))
        ok("numpy: Petersen spectral_radius = 3", ps is not None and abs(ps["spectral_radius"] - 3.0) < 1e-6)
        ok("numpy: Petersen spectral_gap = 2 (3−1)", ps is not None and abs(ps["spectral_gap"] - 2.0) < 1e-6)
    # NEGATIVE: a non-square matrix has no spectrum ⇒ None (not an admit).
    ok("numpy: NEG non-square matrix → None", compute_spectral_bound('{"matrix": [[0,1,0],[1,0,1]]}') is None)

    # ── bridge-name guard: POSITIVE (valid dotted name passes the syntactic guard, then dispatches to the
    #    kernel #check) + NEGATIVE (empty / illegal chars are rejected WITHOUT a kernel call) ──
    bad, why = bridge_lemma_exists("", Path("/nonexistent"), 5)
    ok("bridge: NEG empty name rejected (no kernel call)", bad is False and "no/invalid" in why)
    bad2, _ = bridge_lemma_exists("not a name; rm -rf", Path("/nonexistent"), 5)
    ok("bridge: NEG illegal chars rejected (no kernel call)", bad2 is False)
    # a syntactically-valid name on a NONEXISTENT sandbox ⇒ _compile_probe returns None ⇒ fail-CLOSED (absent),
    # NOT a silent True. This is the dead-instrument guard: no toolchain ⇒ the gate says NO.
    absent, areason = bridge_lemma_exists("Matrix.IsHermitian.eigenvalues", Path("/nonexistent"), 5)
    ok("bridge: NEG no-toolchain ⇒ fail-closed (treated absent, not a silent admit)",
       absent is False and ("fail-closed" in areason or "ABSENT" in areason))

    # ── KERNEL gate guard (functor_lift_advances): every NON-kernel refusal leg, POS-shaped vs NEG ──
    sp_ok = {"lambda2": 1.0, "spectral_gap": 0.0}
    bad3, w3 = functor_lift_advances("", "Mathlib.Foo", Path("/nonexistent"), 5, spectral=sp_ok)
    ok("advances: NEG empty proof rejected", bad3 is False and "no lift proof" in w3)
    bad4, w4 = functor_lift_advances("by exact Mathlib.Foo h", "Mathlib.Foo", Path("/nonexistent"), 5, spectral=None)
    ok("advances: NEG no spectral data (NumPy-absent) ⇒ rejected (fail-closed)",
       bad4 is False and "no spectral data" in w4)
    bad5, w5 = functor_lift_advances("by sorry", "Mathlib.Foo", Path("/nonexistent"), 5, spectral=sp_ok)
    ok("advances: NEG sorry in proof rejected", bad5 is False and "sorry-free" in w5)
    # cites NEITHER the full name NOR the short name ⇒ rejected as spurious, BEFORE any kernel call.
    bad6, w6 = functor_lift_advances("by simp", "SimpleGraph.expander_mixing", Path("/nonexistent"), 5, spectral=sp_ok)
    ok("advances: NEG proof does not cite the bridge ⇒ rejected (spurious)",
       bad6 is False and "does not CITE" in w6)
    # cites the bridge + sorry-free + has spectral data, but the (nonexistent) sandbox ⇒ bridge gate fails
    # ⇒ fail-CLOSED (no closure). Confirms the existence gate is RE-ASSERTED inside advances (can't be skipped).
    bad7, w7 = functor_lift_advances("by exact expander_mixing h", "SimpleGraph.expander_mixing",
                                     Path("/nonexistent"), 5, spectral=sp_ok)
    ok("advances: cited+sorry-free but bridge-absent ⇒ fail-closed (gate re-asserted)",
       bad7 is False and "bridge gate failed" in w7)

    print("SELFTEST", "PASSED" if not fails else f"FAILED {fails}")
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(_selftest())
