# Checked equational-interpretation seam

Date: 2026-07-18

## Eigenquestion

Can AxiomPack represent and verify an interpretation from one independently
generated equational theory into another, so transported conjectures have a
typed semantic basis rather than a landscape-fingerprint resemblance?

## Category and identity

The object is an **equational theory interpretation**, not a similarity score.
Its identity consists of:

- one frozen source signature and source axiom family;
- one frozen target signature and target axiom family;
- a total source-sort to target-sort map;
- one typed target-term template for every source operation;
- the mechanically translated source axioms;
- one proof obligation per translated axiom.

Equality is byte-stable equality of those frozen components. A change to a
signature, axiom, sort map, or operation image creates another interpretation.

## Candidate theorem

Let \(S\) and \(T\) be many-sorted equational signatures. Suppose each sort of
\(S\) is mapped to a sort of \(T\), and every operation

\[
f : A_1\times\cdots\times A_n\to B
\]

is mapped to a well-typed target term

\[
t_f(x_1,\ldots,x_n) : I(B)
\]

with \(x_i:I(A_i)\). This uniquely extends by substitution to source terms and
then homomorphically to source equational formulas. If the target axioms imply
the translation of every source axiom, every source theorem transports to its
translated target theorem.

The Python seam certifies the syntactic extension and prepares the implication
obligations. Finite search may refute an obligation. Absence of a bounded
countermodel remains bounded evidence. Only separately replayed Lean
consequence proofs may upgrade every obligation to carrier-independent status.

## Non-collapse obligation

At least one positive-arity source operation image must:

1. contain a target operation symbol rather than only returning an input; and
2. be nonconstant in an exact finite target model satisfying the target axioms.

This is a minimal anti-collapse condition. It does not claim that the
interpretation is surprising, injective, full, faithful, or priority-new.

## Proof skeleton

1. Validate exact coverage of source sorts and operations.
2. Type-check each operation template against the mapped argument and result
   sorts in the target signature.
3. Translate terms recursively by capture-free parameter substitution.
4. Translate Boolean connectives and quantifiers while mapping binder sorts.
5. Validate each translated axiom against the target signature.
6. Search for a finite target model satisfying the target axioms and refuting
   any translated source axiom.
7. Build one existing `LeanConsequenceTask` per translated axiom.
8. Recheck supplied proof bytes with the kernel and axiom audit.
9. Admit the interpretation only when every task passes and the non-collapse
   witness replays.

## Kill conditions

- A source sort or operation is unmapped or mapped twice.
- A template has the wrong arity, argument sort, or result sort.
- Translation leaves a source symbol in the target formula.
- Finite search returns a countermodel.
- The target witness fails a target axiom or the non-collapse probe.
- Any Lean obligation is unresolved, rejected, contains a forbidden
  assumption, or changes its frozen task identity.

## Recurrence check

`theory_landscape_morphism.py` currently proposes component-name mappings and
keeps all preservation obligations pending. `finite_model.certify_implication`
already owns bounded countermodel search. `lean_consequence_bridge.py` already
owns conditional Lean tasks, kernel replay, axiom audit, and premise
attribution. The missing piece is the typed interpretation and translation
contract joining those owners.

## Intended first fire

Use two small independently named operation theories with a non-identity term
image, first under exact finite replay and then through the generated Lean
obligations. This validates the seam but does not count as an E4 result. E4
additionally requires frozen machine-generated theories, transported
conjectures, matched de-novo controls, and a pre-registered comparison.
