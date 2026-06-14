"""SMT (z3) binding of the exhaustive-equivalence faithfulness leg — a REAL second non-Lean checker.

Parallel to leanmill's `provable_equivalence` (`∀ x, ref ↔ cand` by Lean `decide` over a Fintype), this
proves two formalizations of a rule equivalent over the WHOLE input space via z3: `ref ≢ cand` is UNSAT ⇒
equivalent on every request. It is genuinely different from both Lean (`decide`) and the python-eval
checker, and it adds a property neither gives for free: when two policies diverge, z3 returns the SPECIFIC
counterexample request — the exact security hole — which is the glass-box, auditable payoff of
checker-agnostic governance. A local deterministic solver (z3-solver, pip), NOT a metered API, so it is
clean under the external-prover-API rule; it is the "add SMT as a general-purpose lib" direction realized.

The verdict type + strict-pass rule are the shared `governed_verification` contract — this module is the
SMT substrate binding, the way `LeanLakeChecker` is the Lean binding. z3 is imported lazily so importing
this module never hard-fails when z3 is absent (it fails CLOSED at use, never silently admits).

  python -m ztare.common.smt_checker --selftest
"""
from __future__ import annotations

from ztare.common.governed_verification import CheckResult


class SmtPolicyChecker:
    """A finite-domain rule checker over enum attributes (access policies / boolean compliance rules — the
    decidable non-math sweet spot). `domain` maps attribute → its enum members, e.g.
    {"role": ["admin", "analyst", "guest"], "resource": ["secret", "internal", "pub"]}. Policies are written
    in a small z3-flavoured DSL over the attribute names + their members + And/Or/Not/Implies, e.g.
    "And(role == admin, resource == secret)". `name='smt_z3'` for the audit trail."""

    name = "smt_z3"

    def __init__(self, domain: "dict[str, object]"):
        """`domain` maps each attribute to its TYPE: a list of strings (enum members), or one of
        "int" / "real" / "bool". Numeric attributes (int/real) give z3 its edge over a finite `decide`
        checker — it proves rule-equivalence over the INFINITE range of amounts, and the counterexample
        is the exact distinguishing value (e.g. the $10,000 transaction a launderer structures to)."""
        import z3  # lazy: absent z3 ⇒ ImportError here, never a silent admit
        self._z3 = z3
        self._domain = dict(domain)        # attr -> type spec; used by the cross-substrate generators
        self._consts: "dict[str, object]" = {}
        self._ns: "dict[str, object]" = {"And": z3.And, "Or": z3.Or, "Not": z3.Not, "Implies": z3.Implies}
        for attr, spec in domain.items():
            if isinstance(spec, (list, tuple)):
                sort, vals = z3.EnumSort(attr.capitalize(), list(spec))
                const = z3.Const(attr, sort)
                for name, val in zip(spec, vals):
                    if name in self._ns:
                        raise ValueError(f"enum member name collides with a reserved/other name: {name!r}")
                    self._ns[name] = val
            elif spec == "int":
                const = z3.Int(attr)
            elif spec == "real":
                const = z3.Real(attr)
            elif spec == "bool":
                const = z3.Bool(attr)
            else:
                raise ValueError(f"unsupported attribute type for {attr!r}: {spec!r} (use a list / 'int' / 'real' / 'bool')")
            self._consts[attr] = const
            self._ns[attr] = const

    def _compile(self, policy_src: str):
        expr = eval(policy_src, {"__builtins__": {}}, dict(self._ns))  # noqa: S307 — sandboxed ns, no builtins
        if not self._z3.is_bool(expr):
            raise TypeError(f"policy is not a boolean formula: {policy_src!r}")
        return expr

    def verify(self, policy_src: str) -> CheckResult:
        """Well-formedness: does the policy compile to a boolean z3 formula over the domain? (the
        compile-leg analogue). Fail-closed on any parse/type error."""
        try:
            self._compile(policy_src)
            return CheckResult(True, "well-formed boolean policy", self.name)
        except Exception as e:  # noqa: BLE001
            return CheckResult(False, f"ill-formed policy (fail-closed): {e!r}", self.name)

    def equivalence(self, ref_src: str, cand_src: str) -> CheckResult:
        """EXHAUSTIVE equivalence over every request via z3: `ref ≢ cand` UNSAT ⇒ equivalent everywhere
        (100% faithfulness on the domain); SAT ⇒ NON-equivalent, with the counterexample request in the
        diagnostics. Fail-closed on `unknown` or a compile error (never admit on inconclusive)."""
        try:
            ref, cand = self._compile(ref_src), self._compile(cand_src)
        except Exception as e:  # noqa: BLE001
            return CheckResult(False, f"smt compile error (fail-closed): {e!r}", self.name)
        z3 = self._z3
        s = z3.Solver()
        s.add(z3.Not(ref == cand))
        verdict = s.check()
        if verdict == z3.unsat:
            return CheckResult(True, "equivalent on EVERY request (z3 found no counterexample)", self.name)
        if verdict == z3.sat:
            return CheckResult(False, f"NON-equivalent — counterexample request: {{{self._request_of(s.model())}}}", self.name)
        return CheckResult(False, f"z3 inconclusive ({verdict}) — fail-closed", self.name)

    def _request_of(self, m) -> str:
        """A z3 model as a concrete request; an attr z3 left free reads as 'any' (divergence holds for any)."""
        return ", ".join(f"{a}={m[c] if m[c] is not None else 'any'}" for a, c in self._consts.items())

    # ── Permissiveness / vacuity operations ──────────────────────────────────────────────────────────
    # REPLICATION of established policy analysis (AWS Zelkova, FMCAD 2018 / CAV 2022; Cedar symbolic
    # compiler, OOPSLA/FSE 2024 — Apache-2.0, Lean-verified encoding over cvc5). NO novelty is claimed on
    # the SMT operations. The contribution is GOVERNANCE framing: `non_vacuity` runs as a FAIL-CLOSED
    # control alongside equivalence (Cedar reports vacuity as an advisory finding, not a gate), and every
    # verdict flows through the substrate-neutral CheckResult/is_ok contract so ONE governance consumer
    # spans this checker and the Lean proof checker.

    def implies(self, sub_src: str, super_src: str) -> CheckResult:
        """Subsumption / permissiveness ordering (Zelkova core op; Cedar check-implies): is every request
        `sub` permits also permitted by `super` (sub less-or-equally permissive)? `And(sub, ¬super)` UNSAT
        ⇒ subsumed; SAT ⇒ `sub` WIDENS the allow-set, returning the over-granted request. The SMT analogue
        of statement_integrity's 'no dropped hypothesis' — dropping a condition WIDENS the allow-set, the
        dangerous direction the equivalence leg sees only as 'differ'."""
        try:
            sub, sup = self._compile(sub_src), self._compile(super_src)
        except Exception as e:  # noqa: BLE001
            return CheckResult(False, f"smt compile error (fail-closed): {e!r}", self.name)
        z3 = self._z3
        s = z3.Solver()
        s.add(z3.And(sub, z3.Not(sup)))
        v = s.check()
        if v == z3.unsat:
            return CheckResult(True, "subsumed (less-or-equally permissive)", self.name)
        if v == z3.sat:
            return CheckResult(False, f"WIDENS — request permitted by sub but not super: {{{self._request_of(s.model())}}}", self.name)
        return CheckResult(False, f"z3 inconclusive ({v}) — fail-closed", self.name)

    def compare(self, p1_src: str, p2_src: str) -> CheckResult:
        """Four-way permissiveness verdict (Cedar `analyze compare`): Equivalent / p1 MorePermissive /
        p1 LessPermissive / Incomparable, composed from the two `implies` directions. ok=True iff
        Equivalent — the natural top-level closure-decision diagnostic."""
        a, b = self.implies(p1_src, p2_src), self.implies(p2_src, p1_src)
        for r in (a, b):
            if r.diagnostics.startswith("smt compile"):
                return CheckResult(False, r.diagnostics, self.name)
        if a.ok and b.ok:
            return CheckResult(True, "Equivalent", self.name)
        if a.ok:
            return CheckResult(False, f"p1 LessPermissive than p2 — p2 over-grants: {b.diagnostics}", self.name)
        if b.ok:
            return CheckResult(False, f"p1 MorePermissive than p2 — p1 over-grants: {a.diagnostics}", self.name)
        return CheckResult(False, "Incomparable (each permits a request the other forbids)", self.name)

    def always_allow(self, p_src: str) -> CheckResult:
        """Cedar check-always-allows. ok=False (a laundering hazard) if the policy permits EVERY request."""
        try:
            p = self._compile(p_src)
        except Exception as e:  # noqa: BLE001
            return CheckResult(False, f"smt compile error (fail-closed): {e!r}", self.name)
        z3 = self._z3
        s = z3.Solver()
        s.add(z3.Not(p))
        if s.check() == z3.unsat:
            return CheckResult(False, "VACUOUS: always-allows (permits every request)", self.name)
        return CheckResult(True, "not always-allow (contingent on the request)", self.name)

    def always_deny(self, p_src: str) -> CheckResult:
        """Cedar check-always-denies. ok=False (a laundering hazard) if the policy denies EVERY request."""
        try:
            p = self._compile(p_src)
        except Exception as e:  # noqa: BLE001
            return CheckResult(False, f"smt compile error (fail-closed): {e!r}", self.name)
        z3 = self._z3
        s = z3.Solver()
        s.add(p)
        if s.check() == z3.unsat:
            return CheckResult(False, "VACUOUS: always-denies (no request is permitted)", self.name)
        return CheckResult(True, "not always-deny (contingent on the request)", self.name)

    def non_vacuity(self, p_src: str) -> CheckResult:
        """FAIL-CLOSED vacuity control — the one thing the Lean vacuity organ forces onto SMT that Cedar
        treats only as an advisory finding. A contingent rule must have BOTH a permitted and a denied
        request (`policy` SAT and `¬policy` SAT). Two policies can be 'equivalent' because BOTH are
        always-deny — a laundered pass; run this ALONGSIDE equivalence so a vacuous rule is never admitted.
        The SMT transplant of 'a negative/equivalence verdict is inadmissible without a non-vacuity control
        through the same code path'."""
        try:
            p = self._compile(p_src)
        except Exception as e:  # noqa: BLE001
            return CheckResult(False, f"smt compile error (fail-closed): {e!r}", self.name)
        z3 = self._z3
        can_allow = z3.Solver()
        can_allow.add(p)
        can_deny = z3.Solver()
        can_deny.add(z3.Not(p))
        allow_sat = can_allow.check() == z3.sat
        deny_sat = can_deny.check() == z3.sat
        if allow_sat and deny_sat:
            return CheckResult(True, "contingent (has both a permitted and a denied request)", self.name)
        if not allow_sat:
            return CheckResult(False, "VACUOUS: always-denies (no request is permitted)", self.name)
        return CheckResult(False, "VACUOUS: always-allows (every request permitted)", self.name)

    # ── Cross-substrate test generation (the leapfrog: SMT proposes, the Lean kernel ratifies) ─────────
    # The genuinely-distinct direction, not in Zelkova/Cedar (SMT-only) nor in Lean provers (can't search an
    # infinite space): the decidable solver searches the (often INFINITE) request space for the exact
    # decision-boundary / divergence inputs a human battery misses, and emits them as labelled
    # (request, decision) cases the Lean instance-battery consumes for KERNEL-grade certification. SMT does
    # the whole-space search (fast, untrusted); the Lean kernel does the per-case certification (trusted).
    # Neither substrate alone gives boundary-complete AND kernel-certified.

    def _py_value(self, m, attr):
        """A z3 model value → a python value (enum→member name str, int→int, real→float, bool→bool); a
        free attr → a domain default so the generated request is fully concrete (renderable to Lean)."""
        v = m[self._consts[attr]]
        spec = self._domain[attr]
        if v is None:
            return spec[0] if isinstance(spec, (list, tuple)) else (0 if spec in ("int", "real") else False)
        if isinstance(spec, (list, tuple)):
            return str(v)
        if spec == "bool":
            return bool(self._z3.is_true(v))
        return v.as_long() if spec == "int" else float(v.as_fraction())

    def _z3_lit(self, attr, val):
        spec = self._domain[attr]
        if isinstance(spec, (list, tuple)):
            return self._ns[val]
        if spec == "int":
            return self._z3.IntVal(int(val))
        if spec == "real":
            return self._z3.RealVal(val)
        return self._z3.BoolVal(bool(val))

    def _full_request(self, m) -> dict:
        return {a: self._py_value(m, a) for a in self._consts}

    def _decide_at(self, formula, request: dict) -> bool:
        """Evaluate a compiled formula at a concrete request (all attrs fixed)."""
        s = self._z3.Solver()
        for a, val in request.items():
            s.add(self._consts[a] == self._z3_lit(a, val))
        s.add(formula)
        return s.check() == self._z3.sat

    def distinguishing_requests(self, ref_src: str, cand_src: str, max_cases: int = 6) -> "list[tuple[dict, bool]]":
        """Enumerate up to `max_cases` concrete requests where `ref` and `cand` DISAGREE, each labelled with
        the REFERENCE's decision (the trusted ground truth). The adversarial cases that EXPOSE a laundered
        candidate — auto-derived over the whole request space, not human-guessed. Feed to the Lean
        instance-battery for kernel certification (SMT proposes the cases, the kernel ratifies them)."""
        try:
            ref, cand = self._compile(ref_src), self._compile(cand_src)
        except Exception:  # noqa: BLE001
            return []
        z3 = self._z3
        s = z3.Solver()
        s.add(ref != cand)
        out: "list[tuple[dict, bool]]" = []
        while len(out) < max_cases and s.check() == z3.sat:
            req = self._full_request(s.model())
            out.append((req, self._decide_at(ref, req)))
            s.add(z3.Or(*[self._consts[a] != self._z3_lit(a, v) for a, v in req.items()]))  # block it
        return out

    def auto_laundered_candidates(self, rule_src: str, *, max_candidates: int = 16) -> "list[tuple[str, str]]":
        """Enumerate the PLAUSIBLE laundered variants of a policy rule SOURCE — the perturbations a human
        reviewer misses and a gamed formalizer slips in: off-by-one on each numeric threshold (±1) and
        boundary-operator weakening/widening (`>=`→`>`, `<=`→`<`, `>`→`>=`, `<`→`<=`). Returns
        `[(candidate_src, label)]` for every variant that (a) COMPILES to a well-formed z3 boolean and (b) is
        NOT equivalent to the trusted rule (a genuine laundering — z3 found a disagreeing request). Feed each to
        `distinguishing_requests(rule_src, candidate_src)` to get the exact boundary instances where the trusted
        rule and the laundered variant DISAGREE — WITHOUT a human having to supply the candidate (this auto-
        derives the laundering surface a hand-written boundary covers only one point of). PROPOSER ONLY: the
        Lean kernel still RE-VERIFIES every generated case via the instance battery; nothing is certified here."""
        import re
        raw: "list[tuple[str, str]]" = []
        # (1) numeric-literal off-by-one — ±1 on each STANDALONE integer threshold (never inside an identifier
        #     like `cet1Bp`; the negative lookarounds exclude word-chars and decimal points).
        for m in re.finditer(r"(?<![\w.])(\d+)(?![\w.])", rule_src):
            base = int(m.group(1))
            for delta in (-1, 1):
                nv = base + delta
                if nv < 0:
                    continue
                raw.append((rule_src[:m.start()] + str(nv) + rule_src[m.end():], f"off_by_one:{base}->{nv}"))
        # (2) boundary-operator perturbation — multi-char ops first (so `>=` is not mis-split into `>`), then
        #     the single-char ops via negative lookarounds. One candidate per operator type present.
        for frm, to, tag in ((">=", ">", "weaken:ge->gt"), ("<=", "<", "weaken:le->lt")):
            if frm in rule_src:
                raw.append((rule_src.replace(frm, to), tag))
        if re.search(r"(?<![<>=])>(?!=)", rule_src):
            raw.append((re.sub(r"(?<![<>=])>(?!=)", ">=", rule_src), "widen:gt->ge"))
        if re.search(r"(?<![<>=])<(?!=)", rule_src):
            raw.append((re.sub(r"(?<![<>=])<(?!=)", "<=", rule_src), "widen:lt->le"))
        # validate (compiles + genuinely laundered, i.e. non-equivalent to the trusted rule), dedup.
        out: "list[tuple[str, str]]" = []
        seen = {rule_src.replace(" ", "")}
        for cand, label in raw:
            key = cand.replace(" ", "")
            if key in seen:
                continue
            seen.add(key)
            try:
                self._compile(cand)                       # must be a well-formed z3 boolean
            except Exception:  # noqa: BLE001 — drop ill-formed variants
                continue
            if self.equivalence(rule_src, cand).ok:       # equivalent ⇒ NOT a laundering ⇒ skip
                continue
            out.append((cand, label))
            if len(out) >= max_candidates:
                break
        return out

    def auto_distinguishing_battery(self, rule_src: str, *, max_candidates: int = 16,
                                    max_cases_per_candidate: int = 4) -> "list[tuple[dict, bool]]":
        """End-to-end: `auto_laundered_candidates` → `distinguishing_requests` per candidate → the merged,
        deduped battery of boundary instances (each labelled by the TRUSTED rule's decision) that exposes the
        whole auto-derived laundering surface. Drop-in producer for `default_smt_boundary_battery` /
        `default_instance_battery` (the kernel ratifies each case). No human supplies a candidate or a boundary."""
        battery: "list[tuple[dict, bool]]" = []
        seen_req: set = set()
        for cand, _label in self.auto_laundered_candidates(rule_src, max_candidates=max_candidates):
            for req, dec in self.distinguishing_requests(rule_src, cand, max_cases=max_cases_per_candidate):
                key = tuple(sorted(req.items()))
                if key in seen_req:
                    continue
                seen_req.add(key)
                battery.append((req, dec))
        return battery

    def threshold_cases(self, rule_src: str, numeric_attr: str) -> "list[tuple[dict, bool]]":
        """Find the lower decision-FLIP boundary of `numeric_attr` for `rule`, over its INFINITE range, via
        z3 Optimize, and return the two straddling cases: the value AT the threshold (allow) and just below
        it (deny) — the exact edge (the $10,000 structured transfer) a human battery misses. The SMT side of
        SMT-seeds-the-kernel: these become kernel-certified Lean instance-battery cases."""
        try:
            rule = self._compile(rule_src)
        except Exception:  # noqa: BLE001
            return []
        if self._domain.get(numeric_attr) != "int":
            return []
        z3 = self._z3
        c = self._consts[numeric_attr]
        opt = z3.Optimize()
        opt.add(rule)
        opt.minimize(c)
        if opt.check() != z3.sat or opt.model()[c] is None:
            return []
        at_req = self._full_request(opt.model())
        below = dict(at_req)
        below[numeric_attr] = at_req[numeric_attr] - 1
        return [(at_req, True), (below, self._decide_at(rule, below))]


_DOMAIN = {"role": ["admin", "analyst", "guest"], "resource": ["secret", "internal", "pub"]}


def _selftest() -> int:
    fails = []

    def ok(n, c):
        print(f"  [{'PASS' if c else 'FAIL'}] {n}")
        if not c:
            fails.append(n)

    try:
        chk = SmtPolicyChecker(_DOMAIN)
    except ImportError:
        print("  [SKIP] z3 not installed — SmtPolicyChecker selftest skipped")
        return 0

    REF = "And(role == admin, resource == secret)"
    EQUIV = "And(resource == secret, role == admin)"        # reordered ∧ — semantically equal
    LAUNDER = {
        "broadening": "Or(role == admin, resource == secret)",
        "dropped clause": "role == admin",
        "flipped role": "And(role == analyst, resource == secret)",
    }
    ok("verify_wellformed", chk.verify(REF).ok)
    ok("verify_rejects_garbage", not chk.verify("role ==== nope").ok)
    ok("equiv_accepts_reordered", chk.equivalence(REF, EQUIV).ok)
    for name, pol in LAUNDER.items():
        v = chk.equivalence(REF, pol)
        ok(f"equiv_rejects_{name}", not v.ok and "counterexample" in v.diagnostics)

    # subsumption / permissiveness ordering — positive AND negative control through the same path
    ok("implies_subsumed", chk.implies(REF, "role == admin").ok)                 # admin∧secret ⊆ admin
    wid = chk.implies("role == admin", REF)                                      # admin ⊄ admin∧secret (widens)
    ok("implies_flags_widening", not wid.ok and "WIDENS" in wid.diagnostics)
    # compare four-way verdict
    ok("compare_equivalent", chk.compare(REF, EQUIV).ok)
    dropped = chk.compare(REF, "role == admin")                                  # REF stricter than admit-all-admins
    ok("compare_less_permissive", not dropped.ok and "LessPermissive" in dropped.diagnostics)
    broader = chk.compare("role == admin", REF)
    ok("compare_more_permissive", not broader.ok and "MorePermissive" in broader.diagnostics)
    # non-vacuity FAIL-CLOSED control: a contingent rule passes; always-allow / always-deny are flagged
    ok("nonvacuity_contingent_ok", chk.non_vacuity(REF).ok)
    ok("nonvacuity_flags_always_allow",
       not chk.non_vacuity("Or(role == admin, Not(role == admin))").ok)         # tautology = always-allow
    ok("nonvacuity_flags_always_deny",
       not chk.non_vacuity("And(role == admin, role == analyst)").ok)           # contradiction = always-deny
    ok("always_allow_flags_tautology", not chk.always_allow("Or(role == admin, Not(role == admin))").ok)
    ok("always_deny_flags_contradiction", not chk.always_deny("And(role == admin, role == analyst)").ok)

    # cross-substrate generation (numeric domain): SMT proposes the boundary / divergence cases
    aml = SmtPolicyChecker({"amount": "int", "cross_border": "bool", "kyc": "bool"})
    REF_AML = "And(amount >= 10000, cross_border, Not(kyc))"
    LAUND_AML = "And(amount > 10000, cross_border, Not(kyc))"     # >= silently weakened to >
    tc = aml.threshold_cases(REF_AML, "amount")
    ok("threshold_finds_exact_edge",
       any(r.get("amount") == 10000 and lab for r, lab in tc) and
       any(r.get("amount") == 9999 and not lab for r, lab in tc))
    dr = aml.distinguishing_requests(REF_AML, LAUND_AML)
    ok("distinguishing_finds_divergence",
       len(dr) >= 1 and all(r.get("amount") == 10000 for r, _ in dr) and all(lab for _, lab in dr))

    # AUTO-laundered-candidate generation: the firewall no longer needs a HUMAN to supply the candidate —
    # it auto-derives the laundering surface (the test's hand-written LAUND_AML falls out automatically).
    cands = aml.auto_laundered_candidates(REF_AML)
    cand_srcs = {c.replace(" ", "") for c, _ in cands}
    ok("auto_laundered_generates_the_hand_written_op_weakening", LAUND_AML.replace(" ", "") in cand_srcs)
    ok("auto_laundered_also_finds_off_by_one",
       any("amount>=9999" in c or "amount>=10001" in c for c in cand_srcs))
    ok("auto_laundered_emits_only_REAL_launderings",
       bool(cands) and all(not aml.equivalence(REF_AML, c).ok for c, _ in cands))
    batt = aml.auto_distinguishing_battery(REF_AML)
    ok("auto_battery_finds_10000_boundary_with_NO_human_candidate",
       len(batt) >= 1 and any(r.get("amount") == 10000 and lab for r, lab in batt))
    # reproduces the certify-demo (Basel CET1) hand-picked 449 boundary AUTOMATICALLY
    basel = SmtPolicyChecker({"cet1Bp": "int"})
    basel_srcs = {c.replace(" ", "") for c, _ in basel.auto_laundered_candidates("cet1Bp >= 450")}
    ok("auto_laundered_reproduces_certify_demo_449", "cet1Bp>=449" in basel_srcs)
    ok("auto_battery_reproduces_certify_demo_boundary",
       any(r.get("cet1Bp") == 449 and not lab for r, lab in basel.auto_distinguishing_battery("cet1Bp >= 450")))

    print("SELFTEST", "PASSED" if not fails else f"FAILED: {fails}")
    return 0 if not fails else 1


if __name__ == "__main__":
    import sys
    if "--selftest" in sys.argv:
        sys.exit(_selftest())
    print(__doc__)
