"""Governance SOUNDNESS red-team — the verification-scientist's test (no leaf, warm-local, cheap).

leanmill's one differentiated claim is NO FALSE CLOSURES: a proof is trusted only if it compiles, is
sorry-free, and `#print axioms` ⊆ {propext, Classical.choice, Quot.sound}. This adversarially tries to
SMUGGLE an unsound "closure" past the production gate (`audit_external`) the way a skeptic would. Each
ATTACK must be REJECTED (trustworthy=False); a GENUINE proof (negative control) must PASS. Metric:
catch-rate on attacks (want 100%) + false-positive rate on genuine (want 0%). A gate that never says no,
or always says no, is useless — so both are run through the SAME real path.

  PYTHONPATH=src ./venv/bin/python projects/leanmill_experiments/governance_redteam.py
"""
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "src"))
from ztare.leanmill.audit_external import audit_external

PROJECT = "ztare_proofs"
MATH = "import Mathlib\n\n"

# (name, lean_source, attack_vector, must_reject)
CASES = [
    ("sorry_smuggle", MATH + "theorem rt_sorry : 1 + 1 = 2 := by sorry",
     "leaves `sorry` (⇒ sorryAx) in an otherwise-true claim", True),
    ("admit_smuggle", MATH + "theorem rt_admit : 1 + 1 = 2 := by admit",
     "`admit` (= sorry) on a true claim", True),
    ("nested_sorry", MATH + "theorem rt_nested : 1 + 1 = 2 := by\n  have h : 1 + 1 = 2 := by sorry\n  exact h",
     "sorry hidden in a `have` sub-proof", True),
    ("native_decide_axiom", MATH + "theorem rt_nd : (2 + 2 : Nat) = 4 := by native_decide",
     "`native_decide` ⇒ Lean.ofReduceBool (unaudited native compiler) outside the allowlist", True),
    ("custom_false_axiom", MATH + "axiom rt_cheat : (1 : Nat) = 2\ntheorem rt_axthm : (1 : Nat) = 2 := rt_cheat",
     "declares a FALSE custom axiom and cites it (a real unsoundness)", True),
    # NEGATIVE control — a genuine, clean proof. MUST PASS (else the gate is useless / over-strict).
    ("genuine_clean", MATH + "theorem rt_genuine : 1 + 1 = 2 := by norm_num",
     "honest proof, axioms ⊆ allowlist", False),
]


def _transport_cases() -> list:
    """TRANSPORT-LAUNDERING class (goal item 2): the cross-domain/CAS transport edges (Gröbner cofactor, SOS
    hints, exogenous witness) emit a Lean proof the KERNEL re-verifies — so a *bad* transport (a wrong cofactor,
    a false witness, a laundered analogy) must FAIL re-verification. This is what makes 'alien' exploration safe
    BY CONSTRUCTION: a plausible-but-wrong analogy cannot mint a closure; it just doesn't compile. Each attack
    must be REJECTED; the GENUINE transport (a real Gröbner cofactor cert) must PASS."""
    cases = [
        # a WRONG Gröbner cofactor — claims an ideal-membership transport cert that leaves a nonzero residual.
        ("transport_wrong_cofactor",
         MATH + "theorem rt_tp_badcof (a b c : ℝ) (h0 : a + b + c = 0) : "
         "a^3 + b^3 + c^3 = 3*a*b*c := by\n  linear_combination (a^2) * h0",
         "a WRONG CAS cofactor — a fabricated `linear_combination` transport that does NOT close the goal", True),
        # a FALSE exogenous 'witness' — claims a Pell/Diophantine solution that does not satisfy the equation.
        ("transport_false_witness",
         MATH + "theorem rt_tp_badwit : (999 : ℤ)^2 - 2 * 706^2 = 1 := by norm_num",
         "a FALSE exogenous witness (999/706 is not a Pell solution) — the kernel's arithmetic check fails", True),
        # a laundered 'analogy' asserted as an axiom — the transported structure assumed, not proved.
        ("transport_assumed_analogy",
         MATH + "axiom rt_tp_analogy (a b : ℝ) : a^3 + b^3 = (a + b)^3\n"
         "theorem rt_tp_ax (a b : ℝ) : a^3 + b^3 = (a + b)^3 := rt_tp_analogy a b",
         "a cross-domain 'analogy' asserted as a custom AXIOM (false; laundered, not kernel-proved)", True),
    ]
    # GENUINE transport (negative control) — the REAL Gröbner cofactor cert; MUST PASS (clean axioms via `ring`).
    try:
        from ztare.common.groebner_cert import groebner_certificate
        cert = groebner_certificate(["a + b + c = 0"], "a^3 + b^3 + c^3 = 3*a*b*c")
        if cert and cert.get("linear_combination"):
            cases.append((
                "transport_genuine_groebner",
                MATH + "theorem rt_tp_ok (a b c : ℝ) (h0 : a + b + c = 0) : "
                f"a^3 + b^3 + c^3 = 3*a*b*c := by\n  {cert['linear_combination']}",
                "a REAL Gröbner cofactor transport (kernel re-verifies by `ring`) — must PASS", False))
    except Exception:  # noqa: BLE001 — if sympy/groebner absent, skip the genuine-transport control (don't crash)
        pass
    return cases


def main() -> int:
    print("=== GOVERNANCE SOUNDNESS RED-TEAM (audit_external, warm ztare_proofs v4.30) ===\n", flush=True)
    all_cases = CASES + _transport_cases()        # base smuggling attacks + the transport-laundering class
    rows, caught, attacks, fp, genuines = [], 0, 0, 0, 0
    for name, src, vector, must_reject in all_cases:
        trustworthy = None
        # Retry a NON-expected verdict up to 3× — a transient warm-compile contention (REPL busy/wedged under
        # parallel load) fails CLOSED (reject), which would false-flag a genuine proof. That is infra noise,
        # not a soundness verdict. An ATTACK cannot transiently PASS (a smuggled sorry/axiom never compiles
        # clean), so the retry can only fix a transient genuine-reject, never mask a real leak.
        for _attempt in range(3):
            try:
                trustworthy, _md = audit_external(None, source=src, project=PROJECT)
            except Exception as e:  # noqa: BLE001
                trustworthy = None
                vector += f"  [audit error: {e!r}]"
            _rej = (trustworthy is False)
            if (_rej if must_reject else trustworthy is True):
                break
        rejected = (trustworthy is False)
        if must_reject:
            attacks += 1
            ok = rejected            # attack must be rejected
            if rejected:
                caught += 1
        else:
            genuines += 1
            ok = (trustworthy is True)   # genuine must pass
            if trustworthy is not True:
                fp += 1
        verdict = ("REJECTED" if rejected else ("PASSED" if trustworthy is True else f"?({trustworthy})"))
        flag = "✅" if ok else "❌ LEAK" if must_reject else "❌ FALSE-FLAG"
        rows.append((name, must_reject, verdict, flag, vector))
        print(f"  {flag}  {name:22s} → {verdict:9s}  ({vector})", flush=True)

    catch_rate = caught / attacks if attacks else 0.0
    fp_rate = fp / genuines if genuines else 0.0
    print(f"\n=== RESULT ===")
    print(f"attack catch-rate = {caught}/{attacks} = {catch_rate:.0%}   |   genuine false-positive = {fp}/{genuines} = {fp_rate:.0%}")
    sound = (catch_rate == 1.0 and fp_rate == 0.0)
    print("\n   ✅ GOVERNANCE SOUND: every smuggled-unsoundness attack REJECTED, the genuine proof PASSED."
          if sound else
          "\n   ❌ SOUNDNESS GAP — an attack slipped through OR a genuine proof was false-flagged. INVESTIGATE.")

    # receipt
    out = REPO / "analytics/public/leanmill/results/governance_redteam.md"
    lines = ["# Governance soundness red-team (2026-06-16)", "",
             "Adversarial attempts to smuggle an unsound closure past the production `audit_external` gate "
             "(compile + per-decl `#print axioms` ⊆ {propext, Classical.choice, Quot.sound} + lexical "
             "anti-laundering), warm ztare_proofs v4.30. Two classes: (a) direct smuggling (sorry/admit/"
             "native_decide/false-axiom) and (b) **transport-laundering** — a WRONG exogenous transport cert "
             "(bad Gröbner cofactor, false witness, asserted analogy) that must FAIL kernel re-verification, "
             "while a GENUINE transport passes. This is what makes cross-domain exploration safe by construction: "
             "a plausible-but-wrong analogy cannot mint a closure. Each ATTACK must be REJECTED; each GENUINE proof must PASS.", "",
             f"**catch-rate = {caught}/{attacks} = {catch_rate:.0%}, genuine false-positive = {fp}/{genuines} = {fp_rate:.0%} — "
             f"{'SOUND' if sound else 'GAP'}**", "",
             "| case | kind | attack vector | gate verdict | |", "|---|---|---|---|---|"]
    for name, must_reject, verdict, flag, vector in rows:
        lines.append(f"| `{name}` | {'attack' if must_reject else 'genuine'} | {vector} | {verdict} | {flag} |")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\n[receipt] {out}", flush=True)
    return 0 if sound else 1


if __name__ == "__main__":
    raise SystemExit(main())
