"""Exact finite filtered-quotient, symbol, and cokernel certificates.

The core is deliberately substrate-neutral.  Callers provide a named graded
basis, exact rational relations, homogeneous linear maps, optional velocities
for moving relation generators, and one distinguished vector.  Filtration
degrees may be integers or finite integer tuples; scalar and product shapes
cannot be mixed inside a map.  Same-space
compilation checks a coinvariant, while cross-grade compilation keeps domain
and codomain identities distinct and checks a symbol cokernel.  A separate
reachability compiler measures named forcing columns after that cokernel, so
an unreachable surviving class is not confused with an excited obstruction.
The quotient compilers first validate degree and relation transport, then
decide whether the distinguished class survives

    ambient / (relations + action images).

A surviving class carries an exact annihilating row functional.  A killed
class carries exact decomposition coefficients.  The compiler makes no claim
that a finite adapter window is complete; that obligation remains with the
adapter.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field, replace
from enum import Enum
from fractions import Fraction
import hashlib
import json
from typing import Mapping, TypeAlias

import sympy as sp
from sympy.polys.matrices import DomainMatrix

from ztare.common.exact_linear_system import (
    certify_column_separation,
    solve_particular,
)
from ztare.common.content_identity import content_sha256, require_sha256_digest
from ztare.common.content_bound_evidence import (
    ContentBoundEvidenceError,
    ContentBoundEvidenceReceipt,
    EvidenceAuthority,
    make_content_bound_evidence,
    replay_content_bound_evidence,
)


RationalInput: TypeAlias = int | str | Fraction | sp.Rational
SparseCoordinates: TypeAlias = Mapping[str, RationalInput]
FiltrationDegree: TypeAlias = int | tuple[int, ...]


FILTERED_TAIL_CONTEXT_SCHEMA = "ztare.filtered_tail_context.v1"
FILTERED_PUISEUX_CONTEXT_SCHEMA = "ztare.filtered_puiseux_context.v1"
FILTERED_POLAR_WITT_CONTEXT_SCHEMA = "ztare.filtered_polar_witt_context.v1"
FILTERED_POLAR_TENSOR_CONTEXT_SCHEMA = (
    "ztare.filtered_polar_tensor_context.v1"
)
FILTERED_CRITICAL_TWO_FLOW_CONTEXT_SCHEMA = (
    "ztare.filtered_critical_two_flow_context.v1"
)
FILTERED_CRITICAL_SUPPORT_CONTEXT_SCHEMA = (
    "ztare.filtered_critical_support_context.v1"
)


class FilteredTailOccurrenceOrder(str, Enum):
    """A compiler-owned well-order for positive tail occurrences."""

    NAT_PARAMETER_POSITIVE_GRADE_LEX = (
        "natural_parameter_then_positive_natural_grade_lex"
    )


class FilteredTailClaim(str, Enum):
    """The exact premise set of an exhaustive tail-minimax composition."""

    PURE_BRANCH_LOWER = "pure_branch_lower_bound"
    LEAST_POSITIVE_BRANCH_LOWER = "least_positive_branch_lower_bound"
    ADMISSIBLE_UPPER = "admissible_upper_construction"


class FilteredTailEvidenceScope(str, Enum):
    """The mathematical extent certified by one tail premise."""

    ALL_ORDER_FINITE_PREFIX_UNIFORM = "all_order_finite_prefix_uniform"
    ADMISSIBLE_ALL_ORDER_CONSTRUCTION = "admissible_all_order_construction"
    FINITE_WINDOW = "finite_window"


class FilteredCriticalSupportClaim(str, Enum):
    """The two typed arrows required for critical-support finiteness."""

    STRICT_TAIL_BOUND = "strict_tail_bound"
    SUPPORT_TO_COST_CHARGE = "support_to_cost_charge"


class FilteredCriticalSupportEvidenceScope(str, Enum):
    """The mathematical extent of a critical-support premise."""

    ALL_EVENTUAL_TAIL_ROWS = "all_eventual_tail_rows"
    ALL_CRITICAL_SUPPORT_ROWS = "all_critical_support_rows"
    FINITE_WINDOW = "finite_window"


class FilteredAsymptoticClaim(str, Enum):
    """The adapter proposition required by asymptotic induction."""

    INFINITE_OCCURRENCE_SUPPORT = "infinite_occurrence_support"


class FilteredAsymptoticEvidenceScope(str, Enum):
    """The mathematical extent of an occurrence-support proposition."""

    ALL_UNBOUNDED_OCCURRENCE_INDICES = (
        "all_unbounded_occurrence_indices"
    )
    FINITE_WINDOW = "finite_window"


class FilteredPuiseuxClaim(str, Enum):
    """Adapter propositions available for a content-bound Puiseux germ."""

    REGULAR_LINEAR_COEFFICIENT_NONZERO = (
        "regular_linear_coefficient_nonzero"
    )
    FIRST_FRACTIONAL_COEFFICIENT_NONZERO = (
        "first_fractional_coefficient_nonzero"
    )
    JULIA_FLOW_IDENTITY = "julia_flow_identity"
    TWO_FLOW_FACTORIZATION_IDENTITY = "two_flow_factorization_identity"


class FilteredPuiseuxEvidenceScope(str, Enum):
    """The mathematical extent of one local-germ proposition."""

    EXACT_FIRST_FRACTIONAL_GERM = "exact_first_fractional_germ"
    EXACT_FORMAL_FLOW_IDENTITY = "exact_formal_flow_identity"
    FINITE_TRUNCATION = "finite_truncation"


class FilteredDensityClockClaim(str, Enum):
    """Adapter arrows needed by the weight-3/2 clock orbit theorem."""

    GROUP_MODULE_POLYNOMIALITY = (
        "semidirect_group_module_coordinate_polynomial"
    )
    CLOCK_FACTORIZATION_IDENTITY = "density_clock_factorization_identity"
    SELECTED_ENDPOINT_TRICHOTOMY = "selected_clock_endpoint_trichotomy"
    LOCAL_ENDPOINT_PUISEUX_LATTICES = (
        "local_clock_endpoint_puiseux_lattices"
    )


class FilteredDensityClockEvidenceScope(str, Enum):
    """The mathematical extent of a density-clock orbit proposition."""

    EXACT_SEMIDIRECT_EXPONENTIAL_POLYNOMIALITY = (
        "exact_semidirect_exponential_group_module_polynomiality"
    )
    EXACT_FORMAL_CLOCK_FACTORIZATION = "exact_formal_clock_factorization"
    SELECTED_ANALYTIC_BRANCH_EXHAUSTIVE = (
        "selected_analytic_branch_exhaustive"
    )
    ALL_POLYNOMIAL_ROOT_AND_INFINITY_CHARTS = (
        "all_polynomial_root_and_infinity_charts"
    )
    FINITE_WINDOW = "finite_window"


class FilteredAlgebraicContinuationClaim(str, Enum):
    """Premises turning a density orbit into a selected algebraic branch."""

    CRITICAL_SQUARE_OUTSIDE_BASE_FIELD = (
        "critical_square_outside_base_field"
    )
    ALGEBRAIC_PLACE_PUISEUX_EXTENSION = (
        "algebraic_place_puiseux_extension"
    )


class FilteredAlgebraicContinuationEvidenceScope(str, Enum):
    """The extent of one algebraic-continuation proposition."""

    EXACT_CRITICAL_FUNCTION_FIELD = "exact_critical_function_field"
    ALL_FINITE_ALGEBRAIC_EXTENSIONS_AT_SELECTED_PLACE = (
        "all_finite_algebraic_extensions_at_selected_place"
    )
    FINITE_WINDOW = "finite_window"


class FilteredPolarTensorModel(str, Enum):
    """A universal split tensor representation owned by the compiler."""

    WITT_DENSITY_2_NEG3_NEG5 = "split_witt_density_2_neg3_neg5"


class FilteredPolarWittModel(str, Enum):
    """A universal tangent-Witt first-defect representation."""

    TANGENT_WITT_FIRST_DEFECT_NEWTON = (
        "tangent_witt_first_defect_newton"
    )


class FilteredPolarWittClaim(str, Enum):
    """Adapter propositions required by the polar-Witt theorem."""

    FINITE_MAXIMAL_FACE_DECOMPOSITION = (
        "finite_maximal_face_decomposition"
    )
    SEMIDIRECT_NEWTON_QUOTIENT_APPLIES = (
        "semidirect_newton_quotient_applies"
    )
    CENTRALIZER_FLOW_EXCLUDED = "centralizer_polynomial_flow_excluded"


class FilteredPolarWittEvidenceScope(str, Enum):
    """The mathematical extent of a polar-Witt proposition."""

    ALL_FINITE_POSITIVE_FACES = "all_finite_positive_faces"
    EXACT_FIRST_DEFECT_QUOTIENT = "exact_first_defect_quotient"
    SCALAR_CENTRALIZER_BRANCH = "scalar_centralizer_branch"
    FINITE_WINDOW = "finite_window"


class FilteredPolarTensorClaim(str, Enum):
    """The exact adapter propositions required by the tensor theorem."""

    FINITE_MAXIMAL_FACE_DECOMPOSITION = (
        "finite_maximal_face_decomposition"
    )
    CRITICAL_MODULE_INFINITE_SUPPORT = "critical_module_infinite_support"
    CRITICAL_TERMINAL_EXCLUDED = "critical_terminal_excluded"


class FilteredPolarTensorEvidenceScope(str, Enum):
    """The mathematical extent of a split tensor proposition."""

    ALL_FINITE_POSITIVE_FACES = "all_finite_positive_faces"
    ALL_CRITICAL_MODULE_ORDERS = "all_critical_module_orders"
    ZERO_POSITIVE_FACE_TERMINAL = "zero_positive_face_terminal"
    FINITE_WINDOW = "finite_window"


class FilteredCriticalTwoFlowClaim(str, Enum):
    """The two non-substitutable arrows closing a critical terminal."""

    ZERO_FACE_REALIZES_TWO_FLOW_FACTORIZATION = (
        "zero_face_realizes_two_flow_factorization"
    )
    NORMALIZED_TWO_FLOW_FACTORIZATION_EXCLUDED = (
        "normalized_two_flow_factorization_excluded"
    )


class FilteredCriticalTwoFlowEvidenceScope(str, Enum):
    """The mathematical extent of a critical-terminal proposition."""

    ALL_STRICT_SUBTHRESHOLD_ZERO_FACES = (
        "all_strict_subthreshold_zero_faces"
    )
    EXACT_NORMALIZED_AUTONOMOUS_TWO_FLOW_CATEGORY = (
        "exact_normalized_autonomous_two_flow_category"
    )
    FINITE_WINDOW = "finite_window"


@dataclass(frozen=True)
class FilteredTailContext:
    """The category/statistic identity shared by every tail premise."""

    schema: str
    category_id: str
    statistic_id: str
    occurrence_order: FilteredTailOccurrenceOrder
    adapter_evidence_sha256: str
    context_sha256: str


@dataclass(frozen=True)
class FilteredCriticalSupportContext:
    """Identity of one support/cost comparison at a critical slope."""

    schema: str
    category_id: str
    support_id: str
    cost_id: str
    slope: str
    adapter_evidence_sha256: str
    compiler_kernel_sha256: str
    context_sha256: str


@dataclass(frozen=True)
class FilteredPuiseuxContext:
    """One exact local fractional germ shared by flow obstructions."""

    schema: str
    germ_id: str
    local_coordinate_id: str
    first_fractional_exponent: str
    local_expansion_evidence_sha256: str
    context_sha256: str


@dataclass(frozen=True)
class FilteredPolarTensorContext:
    """The substrate identity lowered to the universal split tensor model."""

    schema: str
    category_id: str
    filtration_id: str
    model: FilteredPolarTensorModel
    adapter_evidence_sha256: str
    context_sha256: str


@dataclass(frozen=True)
class FilteredPolarWittContext:
    """One substrate lowering to the tangent-Witt/Newton model."""

    schema: str
    category_id: str
    filtration_id: str
    model: FilteredPolarWittModel
    adapter_evidence_sha256: str
    centralizer_evidence_sha256: str
    context_sha256: str


@dataclass(frozen=True)
class FilteredCriticalTwoFlowContext:
    """Identity of one schedule-to-factorization terminal composition."""

    schema: str
    schedule_category_id: str
    factorization_category_id: str
    source_germ_id: str
    visible_germ_id: str
    minimum_generator_vanishing_order: int
    specialization_evidence_sha256: str
    exclusion_evidence_sha256: str
    context_sha256: str


class FilteredObstructionError(ValueError):
    """A typed incompatibility in a filtered-obstruction problem."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code


@dataclass(frozen=True)
class FilteredBasisVector:
    """A named basis vector in a scalar or finite product filtration."""

    name: str
    degree: FiltrationDegree


@dataclass(frozen=True)
class FilteredRelation:
    name: str
    degree: FiltrationDegree
    coordinates: SparseCoordinates


@dataclass(frozen=True)
class FilteredAction:
    """One homogeneous action and optional motion of relation generators.

    ``columns[source][target]`` is the coefficient of ``target`` in the
    image of ``source``.  Every nonzero entry must have degree difference
    ``shift``.  ``relation_velocities[relation]`` is the derivative of that
    moving relation generator in the same ambient basis.
    """

    name: str
    shift: FiltrationDegree
    columns: Mapping[str, SparseCoordinates]
    relation_velocities: Mapping[str, SparseCoordinates] = field(
        default_factory=dict
    )


@dataclass(frozen=True)
class FilteredObstructionProblem:
    name: str
    basis: tuple[FilteredBasisVector, ...]
    relations: tuple[FilteredRelation, ...]
    actions: tuple[FilteredAction, ...]
    distinguished: SparseCoordinates


@dataclass(frozen=True)
class FilteredSymbolMap:
    """One total homogeneous map between two finite filtered spaces.

    Every domain basis vector must occur in ``columns``; use an empty
    coordinate mapping for a proved zero column.  This prevents a truncated
    adapter from silently interpreting an omitted incoming column as zero.
    ``relation_velocities`` is the covariant correction to a moving domain
    relation, expressed in the codomain basis.
    """

    name: str
    shift: FiltrationDegree
    columns: Mapping[str, SparseCoordinates]
    relation_velocities: Mapping[str, SparseCoordinates] = field(
        default_factory=dict
    )


@dataclass(frozen=True)
class FilteredSymbolCokernelProblem:
    """A finite cross-grade symbol cokernel, with distinct domain/codomain."""

    name: str
    domain_basis: tuple[FilteredBasisVector, ...]
    domain_relations: tuple[FilteredRelation, ...]
    codomain_basis: tuple[FilteredBasisVector, ...]
    codomain_relations: tuple[FilteredRelation, ...]
    maps: tuple[FilteredSymbolMap, ...]
    distinguished: SparseCoordinates


@dataclass(frozen=True)
class FilteredReachabilityProblem:
    """A forcing span measured after a validated symbol cokernel.

    The symbol problem owns relations and control images.  The named forcing
    columns are the family, residual, or input directions that can actually
    occur.  This separate lifecycle prevents an ambient cokernel from being
    reported as an obstruction when its surviving classes are unreachable
    from the supplied forcing span.
    """

    name: str
    symbol_problem: FilteredSymbolCokernelProblem
    forcing_columns: Mapping[str, SparseCoordinates]


@dataclass(frozen=True)
class FilteredSurplusProjectionProblem:
    """Affine terminal reachability with a declared surplus demand.

    A common triangular argument permits a control to cancel a terminal
    coordinate only when its complete higher/surplus projection vanishes.
    The two total maps share one domain but have distinct codomains.  The
    compiler solves ``S*x = distinguished_surplus`` first, then tests the
    residual terminal demand modulo ``T(ker S)``.  The default zero surplus
    recovers terminal reachability after forbidding every declared surplus.
    All three relation spaces are retained explicitly.

    Relation velocities are excluded: this lifecycle describes simultaneous
    linear projections on fixed quotient spaces.  Moving relations belong to
    a covariant symbol compiler rather than this static kernel calculation.
    """

    name: str
    domain_basis: tuple[FilteredBasisVector, ...]
    domain_relations: tuple[FilteredRelation, ...]
    surplus_basis: tuple[FilteredBasisVector, ...]
    surplus_relations: tuple[FilteredRelation, ...]
    terminal_basis: tuple[FilteredBasisVector, ...]
    terminal_relations: tuple[FilteredRelation, ...]
    surplus_map: FilteredSymbolMap
    terminal_map: FilteredSymbolMap
    distinguished_terminal: SparseCoordinates
    distinguished_surplus: SparseCoordinates = field(default_factory=dict)


@dataclass(frozen=True)
class FilteredGraphQuotientProblem:
    """A source/target pair modulo the graph of a boundary map.

    The boundary map ``Phi: target -> source`` represents simultaneous
    changes ``(Phi(h), h)``.  The graph quotient is canonically compressed
    to the source quotient by ``(source, target) -> source - Phi(target)``.
    Target degrees are reindexed by the map shift inside the direct sum, so
    nonzero-shift filtered maps remain homogeneous.
    """

    name: str
    source_basis: tuple[FilteredBasisVector, ...]
    source_relations: tuple[FilteredRelation, ...]
    target_basis: tuple[FilteredBasisVector, ...]
    target_relations: tuple[FilteredRelation, ...]
    boundary_map: FilteredSymbolMap
    distinguished_source: SparseCoordinates
    distinguished_target: SparseCoordinates


@dataclass(frozen=True)
class FilteredCoupledBlock:
    """One homogeneous codomain block fed by a shared control domain."""

    name: str
    codomain_basis: tuple[FilteredBasisVector, ...]
    codomain_relations: tuple[FilteredRelation, ...]
    symbol_map: FilteredSymbolMap
    distinguished: SparseCoordinates


@dataclass(frozen=True)
class FilteredCoupledBlockProblem:
    """Several filtered blocks constrained by one common control.

    Each block has its own homogeneous map and filtration shift, but every
    map has the same domain quotient.  Compilation stacks the codomain
    relations and inserts each domain control once across the direct sum.
    This differs from compiling blocks independently, which silently grants
    a different control value in every block.
    """

    name: str
    domain_basis: tuple[FilteredBasisVector, ...]
    domain_relations: tuple[FilteredRelation, ...]
    blocks: tuple[FilteredCoupledBlock, ...]


@dataclass(frozen=True)
class FilteredPolynomialFiberProblem:
    """A polynomial control family in a coupled filtered quotient.

    ``linearization`` supplies the filtered blocks and one rational column
    for every named control monomial.  ``monomial_exponents`` binds each
    domain-basis name to its exponent vector in ``parameters``.  Compilation
    tests the actual monomial point, not an independent coefficient for each
    column: the fiber equations are

        distinguished + map * monomials(parameters) = 0

    in every codomain quotient block.  A supplied rational point is evidence
    only after exact substitution verifies all reduced equations.
    """

    name: str
    linearization: FilteredCoupledBlockProblem
    parameters: tuple[str, ...]
    monomial_exponents: Mapping[str, tuple[int, ...]]
    rational_point: Mapping[str, RationalInput] = field(default_factory=dict)


@dataclass(frozen=True)
class FilteredInductionState:
    """One adapter-certified state in a well-founded cancellation graph.

    ``rank`` lies in ``N^d`` with the ordinary lexicographic order.  The
    compiler does not manufacture the local algebra that makes the outgoing
    transitions exhaustive.  Instead, ``local_certificate_sha256`` binds the
    state to that adapter-owned exact certificate, and
    ``complete_outcomes`` must list every outgoing transition name exactly.
    """

    name: str
    rank: tuple[int, ...]
    local_certificate_sha256: str
    complete_outcomes: tuple[str, ...]


@dataclass(frozen=True)
class FilteredInductionTransition:
    """One exhaustive local outcome in a filtered induction.

    A ``descend`` outcome is uncharged and must target a strictly smaller
    lexicographic rank.  The other outcomes close that branch by retaining a
    terminal or charging one side of the declared filtration budget.
    """

    name: str
    source: str
    outcome: str
    target: str | None = None


@dataclass(frozen=True)
class FilteredInductionProblem:
    """A proof-carrying finite transition graph for filtered cancellation.

    This lifecycle checks well-founded graph logic after local exact
    cancellation blocks have been compiled.  It intentionally does not
    infer that a finite adapter covers an unbounded mathematical family.
    """

    name: str
    states: tuple[FilteredInductionState, ...]
    transitions: tuple[FilteredInductionTransition, ...]
    initial_states: tuple[str, ...]


@dataclass(frozen=True)
class FilteredAsymptoticRateWitness:
    """One closing transition paid on an infinite occurrence family.

    The occurrence index is an adapter-owned unbounded integer ``k``.  Both
    the parameter order and a lower bound for the derivation excess are
    affine in ``k``.  Payment must occur at the same parameter order as the
    terminal occurrence; this gives an injective occurrence-to-payment map
    as soon as the common order slope is positive.
    """

    transition_name: str
    side: str
    payment_order_intercept: int
    payment_order_slope: int
    payment_excess_intercept: int
    payment_excess_slope: int
    coefficient_certificate_sha256: str


@dataclass(frozen=True)
class FilteredAsymptoticInductionProblem:
    """Lift a finite filtered induction to a symmetric limsup lower bound.

    ``occurrence_support_evidence`` binds the adapter theorem that the
    recurrence has infinitely many unbounded nonzero indices to the compiled
    induction transition graph.  The core checks the composition logic:
    finite uncharged descent, exhaustive rate witnesses on every closing
    branch, same-order/no-rebilling payment, and the exact affine slope
    inequality.  It does not infer the adapter's recurrence or its coverage
    of an unbounded substrate family.
    """

    name: str
    induction: FilteredInductionProblem
    threshold: RationalInput
    occurrence_order_intercept: int
    occurrence_order_slope: int
    occurrence_support_evidence: ContentBoundEvidenceReceipt
    closing_witnesses: tuple[FilteredAsymptoticRateWitness, ...]


@dataclass(frozen=True)
class FilteredPuiseuxFlowProblem:
    """A fractional local branch tested against a polynomial flow logarithm.

    The adapter supplies a local holonomy germ

        F(u) = y + a*u + analytic integer powers + c*u**lambda + ...

    with a and c nonzero and lambda > 1 the first nonintegral exponent.
    A polynomial infinitesimal generator must satisfy Julia's equation
    f(F)=F'*f.  The nonroot case has unmatched exponents lambda-1 and
    lambda.  In the root case, the first fractional coefficient forces the
    integer root multiplicity to equal lambda.

    The compiler owns this universal implication.  The substrate adapter
    owns the local expansion, the nonzero coefficients, and the proposition
    that the supplied germ is governed by the flow identity under study.
    Those facts are bound to one shared germ context by exact receipts.
    """

    name: str
    context: FilteredPuiseuxContext
    evidence: tuple[ContentBoundEvidenceReceipt, ...]


@dataclass(frozen=True)
class FilteredDensityClockOrbitProblem:
    """Exclude a finite polynomial orbit using a weight-3/2 density clock.

    The local germ has first fractional exponent ``5/2``.  The adapter also
    supplies separate authority that the semidirect *group-module*
    coordinate is polynomial, the clock factorization through a
    polynomial-flow endpoint, a selected continuation whose endpoint is
    exhaustively regular finite, a nonzero polynomial root, or infinity,
    and the complete local Puiseux lattices in those charts.  Polynomiality
    of an upstream Lie-module logarithm is not a substitute for group-module
    polynomiality.  The compiler owns the resulting exponent arithmetic in
    all three cases.
    """

    name: str
    context: FilteredPuiseuxContext
    evidence: tuple[ContentBoundEvidenceReceipt, ...]


@dataclass(frozen=True)
class FilteredAlgebraicClockContinuationProblem:
    """Derive selected endpoint coverage from a polynomial density orbit.

    The compiler combines the exact squared weight-`3/2` orbit identity with
    the time-one Julia identity.  Their derivative-free eliminant is nonzero
    because the critical residual square does not descend to the rational
    source field.  Thus the endpoint germ is algebraic over the selected
    critical sheet.  A separately owned place-extension theorem then gives
    a Puiseux chart above the named branch point.
    """

    name: str
    context: FilteredPuiseuxContext
    evidence: tuple[ContentBoundEvidenceReceipt, ...]


@dataclass(frozen=True)
class FilteredTwoFlowPuiseuxProblem:
    """A regular fractional germ tested against two polynomial flows.

    The proposed factorization is

        F = exp(g*d/dx) o exp(f*d/dx)(x),

    where both polynomial generators vanish to order at least two at the
    formal base point.  A finite branch at which both factors are regular is
    analytic.  If the factorization instead passes through infinity, a
    nonzero linear term forces ``deg(f) = deg(g)``.  After leading
    normalization, the highest coefficient where nonproportional
    generators differ has degree ``e >= 2``.  Their time coordinates then
    give a first fractional exponent

        1 + (d - e) / (d - 1),

    strictly between one and two.  Proportional generators reduce to one
    polynomial flow and are handled by the Julia obstruction above.

    Therefore a regular germ whose first nonintegral exponent is greater
    than two cannot have such a two-flow factorization.  The adapter owns
    the local germ and the substrate-specific factorization identity.
    """

    name: str
    context: FilteredPuiseuxContext
    evidence: tuple[ContentBoundEvidenceReceipt, ...]
    minimum_generator_vanishing_order: int


@dataclass(frozen=True)
class FilteredCriticalTwoFlowProblem:
    """Compose zero-face realization with exact two-flow exclusion.

    This lifecycle deliberately carries no witness-shaped booleans.  Its two
    receipts certify different arrows: the substrate adapter maps every
    schedule in the named zero-face category into the named factorization
    category, while the obstruction authority proves that exact category
    empty.  Neither receipt can stand in for the other.
    """

    name: str
    context: FilteredCriticalTwoFlowContext
    evidence: tuple[ContentBoundEvidenceReceipt, ...]


@dataclass(frozen=True)
class FilteredPolarWittFactorizationProblem:
    """A finite polar prefix tested in a two-factor Witt identity.

    The adapter supplies a factorization in the tangent one-variable Witt
    group whose product has nonpositive Rees grade.  Under a strict tail
    bound, each factor has finite positive-grade support.  At a maximal
    positive face, the two leading logarithmic terms are opposite.  The
    first noncentral Newton face is therefore governed by the exact
    semidirect transfer

        B + C = z / (1 - exp(-z)) * Z,

    where ``z`` is the adjoint of the maximal face.  A nonzero polynomial
    Newton seed has an infinite image under this transfer.  If the maximal
    face has primitive parameter increment ``p > 0`` and positive Rees
    grade ``h > 0``, its radial degree increment is ``p+h``.  A substrate
    whose payment degree is ``degree_multiplier * (p+h)`` therefore has
    asymptotic rate

        degree_multiplier * (p+h) / p.

    The centralizer branch reduces to a single polynomial flow and must be
    excluded by a separately bound receipt.  The compiler owns the
    universal semidirect/Newton implication and its rate arithmetic.  The
    adapter owns the factorization, the filtration dictionary, and the
    finite-face, exact first-defect quotient, and centralizer propositions.
    A recognized model does not supply those adapter-owned propositions.
    """

    name: str
    threshold: RationalInput
    degree_multiplier: RationalInput
    context: FilteredPolarWittContext
    evidence: tuple[ContentBoundEvidenceReceipt, ...]


@dataclass(frozen=True)
class FilteredPolarTensorFactorizationProblem:
    """Eliminate finite polar prefixes in a split Witt-module quotient.

    The quotient has a Witt coordinate ``A`` and a source-paid module
    coordinate ``J``.  The target factor is the split subalgebra ``J=0``.
    On a maximal positive Rees face, choose the least monomial

        X = s**(-h) * x**d,  h > 0, d > h.

    The universal tensor action used by this lifecycle is

        rho(A)J = 2*x*A*J' - 3*x*A'*J - 5*A*J.

    Its monomial orbit has coefficient

        product_(i=0)^(k-1) (2*e + (2*i-3)*d - 5).

    Only finitely many positive starting exponents ``e`` can make this
    product terminate (at most four, uniformly in ``d``).  An
    infinite-support critical module therefore supplies a nonresonant
    Newton seed after avoiding the finitely many tied face defects.  The
    exact semidirect transfer then creates infinitely many same-factor
    source payments with limiting rate

        degree_multiplier * d / (d-h).

    The adapter owns the split quotient, its source/target cost dictionary,
    and the critical infinite-support certificate.  The compiler owns the
    resonance count, Newton separation, transfer, and rate arithmetic.
    """

    name: str
    threshold: RationalInput
    degree_multiplier: RationalInput
    context: FilteredPolarTensorContext
    evidence: tuple[ContentBoundEvidenceReceipt, ...]
    critical_terminal_certificate: FilteredCriticalTwoFlowCertificate


@dataclass(frozen=True)
class FilteredTailMinimaxCompositionProblem:
    """Compose an exhaustive zero/least-positive tail dichotomy.

    This lifecycle is intentionally small.  A graded coefficient schedule
    either has no positive-grade coefficient or, by well-ordering, has a
    least positive occurrence.  The adapter binds one all-order lower-bound
    certificate for each branch and one admissible upper construction in the
    same statistic/category.  The compiler checks category compatibility,
    exhaustiveness, finite-prefix uniformity, and exact bound arithmetic.
    """

    name: str
    threshold: RationalInput
    context: FilteredTailContext
    evidence: tuple[ContentBoundEvidenceReceipt, ...]


@dataclass(frozen=True)
class FilteredCriticalSupportProblem:
    """Compile eventual critical-support finiteness from two typed arrows.

    The strict tail estimate and the support-to-cost implication are distinct
    propositions.  Keeping them as separate content-bound receipts blocks a
    tail estimate in one filtration from being promoted to support finiteness
    in another.
    """

    name: str
    context: FilteredCriticalSupportContext
    evidence: tuple[ContentBoundEvidenceReceipt, ...]


@dataclass(frozen=True)
class FilteredQuadraticDifferentialProblem:
    """Exclude a rational solution from two conjugate differential rows.

    After separating a quadratic algebraic connection into rational and
    radical parts, a proposed rational (in particular polynomial) unknown
    ``k`` must satisfy

        A_0*k' + B_0*k = C_0,
        A_1*k' + B_1*k = C_1.

    Every coefficient is supplied as an exact rational function in one
    named variable.  A nonzero determinant determines candidate values for
    ``k'`` and ``k`` by Cramer's rule.  The compiler differentiates the
    latter and checks compatibility with the former.  Incompatibility
    excludes every rational solution.  A compatible but nonpolynomial
    unique rational candidate also excludes polynomial solutions.
    """

    name: str
    variable: str
    rational_row: tuple[str, str, str]
    radical_row: tuple[str, str, str]
    adapter_certificate_sha256: str


@dataclass(frozen=True)
class FilteredObstructionCertificate:
    schema: str
    problem_name: str
    basis_order: tuple[str, ...]
    ambient_dimension: int
    relation_rank: int
    action_image_rank: int
    constraint_rank: int
    coinvariant_dimension: int
    relation_transport_verified: bool
    distinguished_survives: bool
    distinguished_pairing: str
    witness_by_basis: tuple[tuple[str, str], ...]
    decomposition_by_column: tuple[tuple[str, str], ...]
    constraint_matrix_sha256: str
    distinguished_sha256: str

    def to_dict(self) -> dict[str, object]:
        result = asdict(self)
        result["basis_order"] = list(self.basis_order)
        result["witness_by_basis"] = [
            {"basis": name, "coefficient": coefficient}
            for name, coefficient in self.witness_by_basis
        ]
        result["decomposition_by_column"] = [
            {"column": name, "coefficient": coefficient}
            for name, coefficient in self.decomposition_by_column
        ]
        return result


@dataclass(frozen=True)
class FilteredSymbolCokernelCertificate:
    schema: str
    problem_name: str
    domain_basis_order: tuple[str, ...]
    codomain_basis_order: tuple[str, ...]
    domain_dimension: int
    codomain_dimension: int
    domain_relation_rank: int
    codomain_relation_rank: int
    symbol_image_rank: int
    constraint_rank: int
    cokernel_dimension: int
    relation_transport_verified: bool
    map_shifts: tuple[tuple[str, FiltrationDegree], ...]
    distinguished_survives: bool
    distinguished_pairing: str
    witness_by_codomain_basis: tuple[tuple[str, str], ...]
    decomposition_by_column: tuple[tuple[str, str], ...]
    constraint_matrix_sha256: str
    distinguished_sha256: str

    def to_dict(self) -> dict[str, object]:
        result = asdict(self)
        result["domain_basis_order"] = list(self.domain_basis_order)
        result["codomain_basis_order"] = list(self.codomain_basis_order)
        result["map_shifts"] = [
            {"map": name, "shift": shift}
            for name, shift in self.map_shifts
        ]
        result["witness_by_codomain_basis"] = [
            {"basis": name, "coefficient": coefficient}
            for name, coefficient in self.witness_by_codomain_basis
        ]
        result["decomposition_by_column"] = [
            {"column": name, "coefficient": coefficient}
            for name, coefficient in self.decomposition_by_column
        ]
        return result


@dataclass(frozen=True)
class FilteredReachabilityCertificate:
    schema: str
    problem_name: str
    symbol_problem_name: str
    codomain_basis_order: tuple[str, ...]
    forcing_names: tuple[str, ...]
    ambient_dimension: int
    cokernel_dimension: int
    forcing_span_rank: int
    reachable_cokernel_dimension: int
    unreachable_cokernel_dimension: int
    forcing_survives_by_name: tuple[tuple[str, bool], ...]
    constraint_matrix_sha256: str
    forcing_matrix_sha256: str

    def to_dict(self) -> dict[str, object]:
        result = asdict(self)
        result["codomain_basis_order"] = list(self.codomain_basis_order)
        result["forcing_names"] = list(self.forcing_names)
        result["forcing_survives_by_name"] = [
            {"forcing": name, "survives": survives}
            for name, survives in self.forcing_survives_by_name
        ]
        return result


@dataclass(frozen=True)
class FilteredSurplusProjectionCertificate:
    schema: str
    problem_name: str
    domain_basis_order: tuple[str, ...]
    surplus_basis_order: tuple[str, ...]
    terminal_basis_order: tuple[str, ...]
    domain_dimension: int
    surplus_dimension: int
    terminal_dimension: int
    domain_relation_rank: int
    surplus_relation_rank: int
    terminal_relation_rank: int
    surplus_image_rank: int
    surplus_kernel_dimension: int
    terminal_reachable_without_surplus_dimension: int
    relation_transport_verified: bool
    distinguished_surplus_is_zero: bool
    distinguished_surplus_reachable: bool
    distinguished_pair_cancellable: bool
    distinguished_cancellable_without_surplus: bool
    distinguished_surplus_pairing: str
    distinguished_pairing: str
    witness_by_surplus_basis: tuple[tuple[str, str], ...]
    witness_by_terminal_basis: tuple[tuple[str, str], ...]
    particular_surplus_preimage_by_domain_basis: tuple[tuple[str, str], ...]
    cancellation_by_domain_basis: tuple[tuple[str, str], ...]
    surplus_map_shift: FiltrationDegree
    terminal_map_shift: FiltrationDegree
    surplus_constraint_sha256: str
    surplus_kernel_sha256: str
    terminal_constraint_sha256: str
    distinguished_surplus_sha256: str
    distinguished_sha256: str
    terminal_residual_sha256: str

    def to_dict(self) -> dict[str, object]:
        result = asdict(self)
        result["domain_basis_order"] = list(self.domain_basis_order)
        result["surplus_basis_order"] = list(self.surplus_basis_order)
        result["terminal_basis_order"] = list(self.terminal_basis_order)
        result["witness_by_terminal_basis"] = [
            {"basis": name, "coefficient": coefficient}
            for name, coefficient in self.witness_by_terminal_basis
        ]
        result["witness_by_surplus_basis"] = [
            {"basis": name, "coefficient": coefficient}
            for name, coefficient in self.witness_by_surplus_basis
        ]
        result["particular_surplus_preimage_by_domain_basis"] = [
            {"basis": name, "coefficient": coefficient}
            for name, coefficient
            in self.particular_surplus_preimage_by_domain_basis
        ]
        result["cancellation_by_domain_basis"] = [
            {"basis": name, "coefficient": coefficient}
            for name, coefficient in self.cancellation_by_domain_basis
        ]
        return result


@dataclass(frozen=True)
class FilteredGraphQuotientCertificate:
    schema: str
    problem_name: str
    source_basis_order: tuple[str, ...]
    target_basis_order: tuple[str, ...]
    source_dimension: int
    target_dimension: int
    source_quotient_dimension: int
    graph_quotient_dimension: int
    boundary_map_shift: FiltrationDegree
    relation_transport_verified: bool
    distinguished_survives: bool
    compressed_source_survives: bool
    distinguished_pairing: str
    compressed_source_by_basis: tuple[tuple[str, str], ...]
    compressed_witness_by_source_basis: tuple[tuple[str, str], ...]
    decomposition_by_graph_column: tuple[tuple[str, str], ...]
    graph_constraint_sha256: str
    compressed_source_sha256: str

    def to_dict(self) -> dict[str, object]:
        result = asdict(self)
        result["source_basis_order"] = list(self.source_basis_order)
        result["target_basis_order"] = list(self.target_basis_order)
        result["compressed_source_by_basis"] = [
            {"basis": name, "coefficient": coefficient}
            for name, coefficient in self.compressed_source_by_basis
        ]
        result["compressed_witness_by_source_basis"] = [
            {"basis": name, "coefficient": coefficient}
            for name, coefficient in self.compressed_witness_by_source_basis
        ]
        result["decomposition_by_graph_column"] = [
            {"column": name, "coefficient": coefficient}
            for name, coefficient in self.decomposition_by_graph_column
        ]
        return result


@dataclass(frozen=True)
class FilteredCoupledBlockCertificate:
    schema: str
    problem_name: str
    domain_basis_order: tuple[str, ...]
    block_basis_order: tuple[tuple[str, tuple[str, ...]], ...]
    domain_dimension: int
    domain_relation_rank: int
    ambient_dimension: int
    block_relation_rank: int
    common_control_rank: int
    constraint_rank: int
    coupled_cokernel_dimension: int
    relation_transport_verified: bool
    block_map_shifts: tuple[tuple[str, FiltrationDegree], ...]
    distinguished_survives: bool
    distinguished_pairing: str
    witness_by_block_basis: tuple[tuple[str, str], ...]
    decomposition_by_column: tuple[tuple[str, str], ...]
    constraint_matrix_sha256: str
    distinguished_sha256: str

    def to_dict(self) -> dict[str, object]:
        result = asdict(self)
        result["domain_basis_order"] = list(self.domain_basis_order)
        result["block_basis_order"] = [
            {"block": block, "basis_order": list(basis_order)}
            for block, basis_order in self.block_basis_order
        ]
        result["block_map_shifts"] = [
            {"block": block, "shift": shift}
            for block, shift in self.block_map_shifts
        ]
        result["witness_by_block_basis"] = [
            {"basis": name, "coefficient": coefficient}
            for name, coefficient in self.witness_by_block_basis
        ]
        result["decomposition_by_column"] = [
            {"column": name, "coefficient": coefficient}
            for name, coefficient in self.decomposition_by_column
        ]
        return result


@dataclass(frozen=True)
class FilteredPolynomialFiberCertificate:
    schema: str
    problem_name: str
    linearization_problem_name: str
    parameter_order: tuple[str, ...]
    monomial_by_domain_basis: tuple[tuple[str, tuple[int, ...]], ...]
    block_basis_order: tuple[tuple[str, tuple[str, ...]], ...]
    ambient_dimension: int
    block_relation_rank: int
    quotient_dimension: int
    common_control_rank: int
    linearized_bundle_survives: bool
    linearized_decomposition_by_column: tuple[tuple[str, str], ...]
    raw_equation_count: int
    independent_equation_count: int
    relation_transport_verified: bool
    block_map_shifts: tuple[tuple[str, FiltrationDegree], ...]
    fiber_status: str
    unit_ideal: bool
    rational_point_verified: bool
    rational_point_by_parameter: tuple[tuple[str, str], ...]
    independent_equations: tuple[str, ...]
    eliminated_parameters: tuple[str, ...]
    triangular_substitutions: tuple[tuple[str, str], ...]
    radical_zero_parameters: tuple[tuple[str, int], ...]
    groebner_parameter_order: tuple[str, ...]
    post_elimination_equations: tuple[str, ...]
    groebner_method: str
    modular_core_prime: int
    groebner_input_equation_indices: tuple[int, ...]
    groebner_basis: tuple[str, ...]
    equation_system_sha256: str
    groebner_basis_sha256: str

    def to_dict(self) -> dict[str, object]:
        result = asdict(self)
        result["parameter_order"] = list(self.parameter_order)
        result["monomial_by_domain_basis"] = [
            {"basis": name, "exponents": list(exponents)}
            for name, exponents in self.monomial_by_domain_basis
        ]
        result["block_basis_order"] = [
            {"block": block, "basis_order": list(basis_order)}
            for block, basis_order in self.block_basis_order
        ]
        result["block_map_shifts"] = [
            {"block": block, "shift": shift}
            for block, shift in self.block_map_shifts
        ]
        result["rational_point_by_parameter"] = [
            {"parameter": name, "value": value}
            for name, value in self.rational_point_by_parameter
        ]
        result["linearized_decomposition_by_column"] = [
            {"column": name, "coefficient": coefficient}
            for name, coefficient in self.linearized_decomposition_by_column
        ]
        result["independent_equations"] = list(
            self.independent_equations
        )
        result["eliminated_parameters"] = list(
            self.eliminated_parameters
        )
        result["triangular_substitutions"] = [
            {"parameter": name, "value": value}
            for name, value in self.triangular_substitutions
        ]
        result["radical_zero_parameters"] = [
            {"parameter": name, "power": power}
            for name, power in self.radical_zero_parameters
        ]
        result["groebner_parameter_order"] = list(
            self.groebner_parameter_order
        )
        result["post_elimination_equations"] = list(
            self.post_elimination_equations
        )
        result["groebner_input_equation_indices"] = list(
            self.groebner_input_equation_indices
        )
        result["groebner_basis"] = list(self.groebner_basis)
        return result


@dataclass(frozen=True)
class FilteredInductionCertificate:
    schema: str
    problem_name: str
    state_order: tuple[str, ...]
    transition_order: tuple[str, ...]
    initial_states: tuple[str, ...]
    rank_dimension: int
    local_coverage_verified: bool
    strict_descent_verified: bool
    all_states_reachable: bool
    branch_outcome_counts: tuple[tuple[str, int], ...]
    maximum_uncharged_descent_length: int
    every_declared_branch_closes: bool
    adapter_completeness_inferred: bool
    state_certificate_sha256: tuple[tuple[str, str], ...]
    transition_graph_sha256: str

    def to_dict(self) -> dict[str, object]:
        result = asdict(self)
        result["state_order"] = list(self.state_order)
        result["transition_order"] = list(self.transition_order)
        result["initial_states"] = list(self.initial_states)
        result["branch_outcome_counts"] = [
            {"outcome": outcome, "count": count}
            for outcome, count in self.branch_outcome_counts
        ]
        result["state_certificate_sha256"] = [
            {"state": state, "sha256": digest}
            for state, digest in self.state_certificate_sha256
        ]
        return result


@dataclass(frozen=True)
class FilteredAsymptoticInductionCertificate:
    schema: str
    problem_name: str
    induction_problem_name: str
    threshold: str
    occurrence_order_intercept: int
    occurrence_order_slope: int
    occurrence_support_infinite: bool
    occurrence_support_certificate_sha256: str
    occurrence_support_receipt_sha256: str
    maximum_uncharged_descent_length: int
    closing_transition_order: tuple[str, ...]
    rate_by_transition: tuple[tuple[str, str], ...]
    side_by_transition: tuple[tuple[str, str], ...]
    minimum_certified_rate: str
    every_closing_branch_rate_certified: bool
    same_order_payment_verified: bool
    no_rebilling_verified: bool
    parameter_shift_invariance_verified: bool
    adapter_completeness_inferred: bool
    induction_transition_graph_sha256: str
    asymptotic_certificate_sha256: str
    asymptotic_proof_envelope_sha256: str

    def to_dict(self) -> dict[str, object]:
        result = asdict(self)
        result["closing_transition_order"] = list(
            self.closing_transition_order
        )
        result["rate_by_transition"] = [
            {"transition": transition, "rate": rate}
            for transition, rate in self.rate_by_transition
        ]
        result["side_by_transition"] = [
            {"transition": transition, "side": side}
            for transition, side in self.side_by_transition
        ]
        return result


@dataclass(frozen=True)
class FilteredPuiseuxFlowCertificate:
    schema: str
    problem_name: str
    first_fractional_exponent: str
    derivative_fractional_exponent: str
    regular_linear_coefficient_nonzero: bool
    fractional_coefficient_nonzero: bool
    julia_equation_verified_by_adapter: bool
    time_one_realization_verified_by_adapter: bool
    zero_generator_excluded_by_nonidentity_germ: bool
    nonroot_exponent_mismatch: bool
    forced_root_multiplicity: str
    forced_root_multiplicity_is_noninteger: bool
    polynomial_generator_excluded: bool
    adapter_completeness_inferred: bool
    local_expansion_certificate_sha256: str
    puiseux_flow_certificate_sha256: str
    evidence_receipt_sha256: tuple[tuple[str, str], ...]
    proof_contract_sha256: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class FilteredDensityClockOrbitCertificate:
    schema: str
    problem_name: str
    first_fractional_exponent: str
    fractional_increment: str
    density_weight: str
    residual_valuation: int
    group_module_polynomiality_verified_by_adapter: bool
    regular_finite_case_excluded: bool
    multiple_nonzero_root_clock_diverges: bool
    simple_root_inverse_order: int
    simple_root_forced_generator_multiplicity: str
    simple_root_case_excluded: bool
    infinity_clock_finite_minimum_residual_degree: int
    infinity_degree_relation: str
    infinity_generator_degree_even: bool
    infinity_fractional_increment_outside_lattice: bool
    infinity_case_excluded: bool
    selected_polynomial_orbit_excluded: bool
    adapter_completeness_inferred: bool
    context_sha256: str
    evidence_receipt_sha256: tuple[tuple[str, str], ...]
    density_clock_orbit_certificate_sha256: str
    proof_contract_sha256: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class FilteredAlgebraicClockContinuationCertificate:
    schema: str
    problem_name: str
    squared_density_identity_verified_by_adapter: bool
    group_module_polynomiality_verified_by_adapter: bool
    time_one_julia_identity_verified_by_adapter: bool
    zero_generator_excluded_before_elimination: bool
    critical_square_outside_base_field: bool
    critical_square_first_nonbase_exponent: str
    derivative_free_eliminant_nonzero: bool
    endpoint_algebraic_over_selected_critical_field: bool
    selected_place_extension_verified_by_adapter: bool
    selected_endpoint_is_finite_or_infinity: bool
    selected_endpoint_trichotomy_derived: bool
    adapter_completeness_inferred: bool
    context_sha256: str
    evidence_receipt_sha256: tuple[tuple[str, str], ...]
    algebraic_continuation_certificate_sha256: str
    selected_endpoint_receipt_sha256: str
    proof_contract_sha256: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class FilteredTwoFlowPuiseuxCertificate:
    schema: str
    problem_name: str
    first_fractional_exponent: str
    regular_linear_coefficient_nonzero: bool
    fractional_coefficient_nonzero: bool
    minimum_generator_vanishing_order: int
    regular_finite_route_is_analytic: bool
    infinity_route_equal_degrees_forced: bool
    nonproportional_infinity_exponent_interval: str
    proportional_case_reduces_to_single_flow: bool
    single_flow_polynomial_generator_excluded: bool
    polynomial_two_flow_factorization_excluded: bool
    adapter_completeness_inferred: bool
    local_expansion_certificate_sha256: str
    two_flow_puiseux_certificate_sha256: str
    evidence_receipt_sha256: tuple[tuple[str, str], ...]
    proportional_julia_receipt_sha256: str
    proof_contract_sha256: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class FilteredCriticalTwoFlowCertificate:
    """Content identity of a composed critical-terminal contradiction."""

    schema: str
    problem_name: str
    schedule_category_id: str
    factorization_category_id: str
    source_germ_id: str
    visible_germ_id: str
    minimum_generator_vanishing_order: int
    zero_face_realizes_two_flow_factorization: bool
    normalized_two_flow_factorization_excluded: bool
    critical_terminal_excluded: bool
    specialization_evidence_sha256: str
    exclusion_evidence_sha256: str
    context_sha256: str
    evidence_receipt_sha256: tuple[tuple[str, str], ...]
    evidence_authority: tuple[tuple[str, str], ...]
    critical_two_flow_certificate_sha256: str
    proof_contract_sha256: str

    def to_dict(self) -> dict[str, object]:
        result = asdict(self)
        result["evidence_receipt_sha256"] = [
            {"claim": claim, "sha256": digest}
            for claim, digest in self.evidence_receipt_sha256
        ]
        result["evidence_authority"] = [
            {"claim": claim, "authority": authority}
            for claim, authority in self.evidence_authority
        ]
        return result


@dataclass(frozen=True)
class FilteredPolarWittFactorizationCertificate:
    schema: str
    problem_name: str
    threshold: str
    degree_multiplier: str
    finite_positive_support: bool
    product_has_nonpositive_rees_support: bool
    opposite_maximal_faces_verified: bool
    newton_invariant: str
    tied_newton_faces_finite: bool
    semidirect_transfer: str
    inverse_transfer_nonpolynomial_on_nonzero_polynomial_seed: bool
    tangent_witt_orbit_nonterminating_or_central: bool
    orbit_order_increment: str
    orbit_payment_degree_increment: str
    orbit_rate_formula: str
    noncentral_branch_strictly_supercritical: bool
    centralizer_branch_reduces_to_polynomial_flow: bool
    centralizer_polynomial_flow_excluded: bool
    arbitrary_finite_polar_prefix_excluded: bool
    adapter_completeness_inferred: bool
    adapter_certificate_sha256: str
    centralizer_certificate_sha256: str
    context_sha256: str
    model: str
    evidence_receipt_sha256: tuple[tuple[str, str], ...]
    evidence_authority: tuple[tuple[str, str], ...]
    polar_witt_certificate_sha256: str
    proof_contract_sha256: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class FilteredPolarTensorFactorizationCertificate:
    schema: str
    problem_name: str
    threshold: str
    degree_multiplier: str
    tensor_action: str
    monomial_orbit_coefficient: str
    newton_invariant: str
    maximum_resonant_start_exponents: int
    infinite_support_has_nonresonant_seed: bool
    semidirect_transfer: str
    target_module_vanishes: bool
    orbit_order_increment: str
    orbit_payment_degree_increment: str
    orbit_rate_formula: str
    positive_face_branch_strictly_supercritical: bool
    finite_positive_prefix_induction_closed: bool
    critical_terminal_factorization_excluded: bool
    strict_subthreshold_factorization_excluded: bool
    adapter_completeness_inferred: bool
    adapter_certificate_sha256: str
    critical_module_certificate_sha256: str
    critical_terminal_certificate_sha256: str
    context_sha256: str
    model: str
    evidence_receipt_sha256: tuple[tuple[str, str], ...]
    evidence_authority: tuple[tuple[str, str], ...]
    polar_tensor_certificate_sha256: str
    proof_contract_sha256: str

    def to_dict(self) -> dict[str, object]:
        result = asdict(self)
        result["evidence_receipt_sha256"] = [
            {"claim": claim, "sha256": digest}
            for claim, digest in self.evidence_receipt_sha256
        ]
        result["evidence_authority"] = [
            {"claim": claim, "authority": authority}
            for claim, authority in self.evidence_authority
        ]
        return result


@dataclass(frozen=True)
class FilteredTailMinimaxCompositionCertificate:
    schema: str
    problem_name: str
    threshold: str
    branch_partition: tuple[str, str]
    branch_partition_exhaustive: bool
    pure_branch_lower_bound: str
    least_positive_branch_lower_bound: str
    unrestricted_lower_bound: str
    upper_construction_bound: str
    unrestricted_minimax_value: str
    statistics_and_category_compatible: bool
    all_lower_branches_all_order: bool
    finite_prefix_uniform: bool
    upper_construction_admissible: bool
    adapter_completeness_inferred: bool
    pure_branch_certificate_sha256: str
    least_positive_branch_certificate_sha256: str
    upper_construction_certificate_sha256: str
    adapter_certificate_sha256: str
    context_sha256: str
    occurrence_order: str
    evidence_receipt_sha256: tuple[tuple[str, str], ...]
    evidence_authority: tuple[tuple[str, str], ...]
    tail_minimax_certificate_sha256: str
    proof_contract_sha256: str

    def to_dict(self) -> dict[str, object]:
        result = asdict(self)
        result["branch_partition"] = list(self.branch_partition)
        result["evidence_receipt_sha256"] = [
            {"claim": claim, "sha256": digest}
            for claim, digest in self.evidence_receipt_sha256
        ]
        result["evidence_authority"] = [
            {"claim": claim, "authority": authority}
            for claim, authority in self.evidence_authority
        ]
        return result


@dataclass(frozen=True)
class FilteredCriticalSupportCertificate:
    schema: str
    problem_name: str
    category_id: str
    support_id: str
    cost_id: str
    slope: str
    eventual_critical_support_vanishing: bool
    critical_support_finite: bool
    infinite_support_forces_late_threshold_cost: bool
    strict_tail_alone_implies_finite_support: bool
    premise_removal_countermodel_accepted: bool
    adapter_completeness_inferred: bool
    adapter_evidence_sha256: str
    compiler_kernel_sha256: str
    context_sha256: str
    evidence_receipt_sha256: tuple[tuple[str, str], ...]
    evidence_authority: tuple[tuple[str, str], ...]
    critical_support_certificate_sha256: str
    proof_contract_sha256: str

    def to_dict(self) -> dict[str, object]:
        result = asdict(self)
        result["evidence_receipt_sha256"] = [
            {"claim": claim, "sha256": digest}
            for claim, digest in self.evidence_receipt_sha256
        ]
        result["evidence_authority"] = [
            {"claim": claim, "authority": authority}
            for claim, authority in self.evidence_authority
        ]
        return result


@dataclass(frozen=True)
class FilteredQuadraticDifferentialCertificate:
    schema: str
    problem_name: str
    variable: str
    determinant_nonzero: bool
    rational_candidate_unique: bool
    derivative_compatibility_nonzero: bool
    candidate_rational_not_polynomial: bool
    rational_solution_excluded: bool
    polynomial_solution_excluded: bool
    determinant_numerator_degree: int
    compatibility_numerator_degree: int | None
    candidate_denominator_degree: int
    determinant_sha256: str
    compatibility_sha256: str
    candidate_sha256: str
    adapter_completeness_inferred: bool
    adapter_certificate_sha256: str
    quadratic_differential_certificate_sha256: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _rational(value: RationalInput) -> sp.Rational:
    if isinstance(value, bool) or isinstance(value, float):
        raise FilteredObstructionError(
            "non_exact_coefficient",
            f"coefficients must be exact rationals, received {value!r}",
        )
    try:
        if isinstance(value, Fraction):
            return sp.Rational(value.numerator, value.denominator)
        return sp.Rational(value)
    except Exception as error:
        raise FilteredObstructionError(
            "non_exact_coefficient",
            f"coefficient does not convert to QQ: {value!r}",
        ) from error


def _domain_matrix(matrix: sp.Matrix) -> DomainMatrix:
    return DomainMatrix.from_Matrix(matrix).to_field()


def _validated_degree(
    value: FiltrationDegree,
    *,
    label: str,
) -> FiltrationDegree:
    if isinstance(value, bool):
        raise FilteredObstructionError(
            "invalid_filtration_degree",
            f"{label} must be an integer or a nonempty integer tuple",
        )
    if isinstance(value, int):
        return value
    if (
        isinstance(value, tuple)
        and value
        and all(isinstance(component, int) and not isinstance(component, bool)
                for component in value)
    ):
        return value
    raise FilteredObstructionError(
        "invalid_filtration_degree",
        f"{label} must be an integer or a nonempty integer tuple",
    )


def _degree_difference(
    target: FiltrationDegree,
    source: FiltrationDegree,
    *,
    label: str,
) -> FiltrationDegree:
    target = _validated_degree(target, label=f"{label} target degree")
    source = _validated_degree(source, label=f"{label} source degree")
    if isinstance(target, int) and isinstance(source, int):
        return target - source
    if isinstance(target, tuple) and isinstance(source, tuple):
        if len(target) != len(source):
            raise FilteredObstructionError(
                "incompatible_filtration_degree",
                f"{label} uses product degrees of lengths "
                f"{len(source)} and {len(target)}",
            )
        return tuple(
            target_component - source_component
            for target_component, source_component in zip(
                target, source, strict=True
            )
        )
    raise FilteredObstructionError(
        "incompatible_filtration_degree",
        f"{label} mixes scalar and product filtration degrees",
    )


def _validate_shift_shape(
    shift: FiltrationDegree,
    source_degree: FiltrationDegree,
    target_degree: FiltrationDegree,
    *,
    label: str,
) -> None:
    shift = _validated_degree(shift, label=f"{label} shift")
    zero = _degree_difference(
        target_degree,
        source_degree,
        label=label,
    )
    if isinstance(zero, int) != isinstance(shift, int):
        raise FilteredObstructionError(
            "incompatible_filtration_degree",
            f"{label} shift has a different filtration shape",
        )
    if isinstance(zero, tuple) and isinstance(shift, tuple):
        if len(zero) != len(shift):
            raise FilteredObstructionError(
                "incompatible_filtration_degree",
                f"{label} shift has product length {len(shift)}, "
                f"expected {len(zero)}",
            )


def _is_zero_degree(value: FiltrationDegree) -> bool:
    value = _validated_degree(value, label="filtration shift")
    if isinstance(value, int):
        return value == 0
    return all(component == 0 for component in value)


def _add_degree(
    degree: FiltrationDegree,
    shift: FiltrationDegree,
    *,
    label: str,
) -> FiltrationDegree:
    """Add compatible scalar or product filtration degrees."""

    degree = _validated_degree(degree, label=f"{label} degree")
    shift = _validated_degree(shift, label=f"{label} shift")
    if isinstance(degree, int) and isinstance(shift, int):
        return degree + shift
    if isinstance(degree, tuple) and isinstance(shift, tuple):
        if len(degree) != len(shift):
            raise FilteredObstructionError(
                "incompatible_filtration_degree",
                f"{label} has product lengths {len(degree)} and "
                f"{len(shift)}",
            )
        return tuple(
            component + increment
            for component, increment in zip(degree, shift, strict=True)
        )
    raise FilteredObstructionError(
        "incompatible_filtration_degree",
        f"{label} mixes scalar and product filtration degrees",
    )


def _matrix_sha256(matrix: sp.Matrix) -> str:
    entries = [
        (row, column, str(matrix[row, column]))
        for row in range(matrix.rows)
        for column in range(matrix.cols)
        if matrix[row, column] != 0
    ]
    payload = {"shape": [matrix.rows, matrix.cols], "entries": entries}
    return hashlib.sha256(
        json.dumps(payload, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _basis_index(
    basis: tuple[FilteredBasisVector, ...],
) -> tuple[dict[str, int], dict[str, FiltrationDegree]]:
    if not basis:
        raise FilteredObstructionError(
            "empty_basis", "at least one basis vector is required"
        )
    names = [item.name for item in basis]
    if any(not name for name in names):
        raise FilteredObstructionError(
            "empty_basis_name", "basis names must be nonempty"
        )
    if len(names) != len(set(names)):
        raise FilteredObstructionError(
            "duplicate_basis_name", "basis names must be unique"
        )
    for item in basis:
        _validated_degree(
            item.degree,
            label=f"basis vector {item.name!r} degree",
        )
    return (
        {item.name: index for index, item in enumerate(basis)},
        {item.name: item.degree for item in basis},
    )


def _column(
    coordinates: SparseCoordinates,
    *,
    basis_index: Mapping[str, int],
    dimension: int,
    label: str,
) -> sp.Matrix:
    result = sp.zeros(dimension, 1)
    for name, raw in coordinates.items():
        if name not in basis_index:
            raise FilteredObstructionError(
                "unknown_basis_name", f"{label} refers to {name!r}"
            )
        result[basis_index[name], 0] += _rational(raw)
    return result


def _relation_matrix(
    basis: tuple[FilteredBasisVector, ...],
    relations: tuple[FilteredRelation, ...],
    *,
    basis_index: Mapping[str, int],
    basis_degrees: Mapping[str, FiltrationDegree],
) -> tuple[sp.Matrix, dict[str, sp.Matrix]]:
    seen: set[str] = set()
    columns: list[sp.Matrix] = []
    by_name: dict[str, sp.Matrix] = {}
    for relation in relations:
        if not relation.name or relation.name in seen:
            raise FilteredObstructionError(
                "invalid_relation_name",
                "relation names must be nonempty and unique",
            )
        seen.add(relation.name)
        _validated_degree(
            relation.degree,
            label=f"relation {relation.name!r} degree",
        )
        column = _column(
            relation.coordinates,
            basis_index=basis_index,
            dimension=len(basis),
            label=f"relation {relation.name}",
        )
        if column == sp.zeros(len(basis), 1):
            raise FilteredObstructionError(
                "zero_relation", f"relation {relation.name!r} is zero"
            )
        for basis_name, raw in relation.coordinates.items():
            if _rational(raw) and basis_degrees[basis_name] != relation.degree:
                raise FilteredObstructionError(
                    "inhomogeneous_relation",
                    f"relation {relation.name!r} declares degree "
                    f"{relation.degree} but uses {basis_name!r} in degree "
                    f"{basis_degrees[basis_name]}",
                )
        columns.append(column)
        by_name[relation.name] = column
    matrix = sp.Matrix.hstack(*columns) if columns else sp.zeros(
        len(basis), 0
    )
    return matrix, by_name


def _action_matrix(
    action: FilteredAction,
    problem: FilteredObstructionProblem,
    *,
    basis_index: Mapping[str, int],
    basis_degrees: Mapping[str, FiltrationDegree],
) -> sp.Matrix:
    if not action.name:
        raise FilteredObstructionError(
            "empty_action_name", "action names must be nonempty"
        )
    first_degree = next(iter(basis_degrees.values()))
    _validate_shift_shape(
        action.shift,
        first_degree,
        first_degree,
        label=f"action {action.name!r}",
    )
    unknown_sources = set(action.columns) - set(basis_index)
    if unknown_sources:
        raise FilteredObstructionError(
            "unknown_action_source",
            f"action {action.name!r} has unknown sources "
            f"{sorted(unknown_sources)}",
        )
    missing_sources = set(basis_index) - set(action.columns)
    if missing_sources:
        raise FilteredObstructionError(
            "incomplete_action_domain",
            f"action {action.name!r} omits basis sources "
            f"{sorted(missing_sources)}; proved zero columns must be explicit",
        )
    matrix = sp.zeros(len(problem.basis), len(problem.basis))
    for source_name, coordinates in action.columns.items():
        source_degree = basis_degrees[source_name]
        column = _column(
            coordinates,
            basis_index=basis_index,
            dimension=len(problem.basis),
            label=f"action {action.name} source {source_name}",
        )
        for target_name, raw in coordinates.items():
            if not _rational(raw):
                continue
            actual_shift = _degree_difference(
                basis_degrees[target_name],
                source_degree,
                label=(
                    f"action {action.name!r} "
                    f"{source_name!r}->{target_name!r}"
                ),
            )
            if actual_shift != action.shift:
                raise FilteredObstructionError(
                    "wrong_filtration_shift",
                    f"action {action.name!r} declares shift {action.shift} "
                    f"but {source_name!r}->{target_name!r} has shift "
                    f"{actual_shift}",
                )
        matrix[:, basis_index[source_name]] = column
    return matrix


def _symbol_map_matrix(
    symbol_map: FilteredSymbolMap,
    *,
    domain_index: Mapping[str, int],
    domain_degrees: Mapping[str, FiltrationDegree],
    codomain_index: Mapping[str, int],
    codomain_degrees: Mapping[str, FiltrationDegree],
) -> sp.Matrix:
    if not symbol_map.name:
        raise FilteredObstructionError(
            "empty_symbol_map_name", "symbol map names must be nonempty"
        )
    _validate_shift_shape(
        symbol_map.shift,
        next(iter(domain_degrees.values())),
        next(iter(codomain_degrees.values())),
        label=f"symbol map {symbol_map.name!r}",
    )
    unknown_sources = set(symbol_map.columns) - set(domain_index)
    if unknown_sources:
        raise FilteredObstructionError(
            "unknown_symbol_source",
            f"symbol map {symbol_map.name!r} has unknown sources "
            f"{sorted(unknown_sources)}",
        )
    missing_sources = set(domain_index) - set(symbol_map.columns)
    if missing_sources:
        raise FilteredObstructionError(
            "incomplete_symbol_domain",
            f"symbol map {symbol_map.name!r} omits basis sources "
            f"{sorted(missing_sources)}; proved zero columns must be explicit",
        )
    matrix = sp.zeros(len(codomain_index), len(domain_index))
    for source_name, coordinates in symbol_map.columns.items():
        source_degree = domain_degrees[source_name]
        column = _column(
            coordinates,
            basis_index=codomain_index,
            dimension=len(codomain_index),
            label=f"symbol map {symbol_map.name} source {source_name}",
        )
        for target_name, raw in coordinates.items():
            if not _rational(raw):
                continue
            actual_shift = _degree_difference(
                codomain_degrees[target_name],
                source_degree,
                label=(
                    f"symbol map {symbol_map.name!r} "
                    f"{source_name!r}->{target_name!r}"
                ),
            )
            if actual_shift != symbol_map.shift:
                raise FilteredObstructionError(
                    "wrong_symbol_shift",
                    f"symbol map {symbol_map.name!r} declares shift "
                    f"{symbol_map.shift} but {source_name!r}->{target_name!r} "
                    f"has shift {actual_shift}",
                )
        matrix[:, domain_index[source_name]] = column
    return matrix


def _rank(matrix: sp.Matrix) -> int:
    return int(_domain_matrix(matrix).rank())


def _validated_symbol_map_matrix(
    symbol_map: FilteredSymbolMap,
    *,
    domain_basis: tuple[FilteredBasisVector, ...],
    domain_relations: tuple[FilteredRelation, ...],
    domain_index: Mapping[str, int],
    domain_degrees: Mapping[str, FiltrationDegree],
    domain_relation_by_name: Mapping[str, sp.Matrix],
    codomain_basis: tuple[FilteredBasisVector, ...],
    codomain_index: Mapping[str, int],
    codomain_degrees: Mapping[str, FiltrationDegree],
    codomain_relations: sp.Matrix,
) -> sp.Matrix:
    """Validate one total filtered map and its relation transport."""

    domain_relation_names = set(domain_relation_by_name)
    unknown_velocities = (
        set(symbol_map.relation_velocities) - domain_relation_names
    )
    if unknown_velocities:
        raise FilteredObstructionError(
            "unknown_symbol_relation_velocity",
            f"symbol map {symbol_map.name!r} gives velocities for "
            f"unknown domain relations {sorted(unknown_velocities)}",
        )
    matrix = _symbol_map_matrix(
        symbol_map,
        domain_index=domain_index,
        domain_degrees=domain_degrees,
        codomain_index=codomain_index,
        codomain_degrees=codomain_degrees,
    )
    for relation in domain_relations:
        velocity_coordinates = symbol_map.relation_velocities.get(
            relation.name, {}
        )
        velocity = _column(
            velocity_coordinates,
            basis_index=codomain_index,
            dimension=len(codomain_basis),
            label=(
                f"symbol map {symbol_map.name} velocity of relation "
                f"{relation.name}"
            ),
        )
        for target_name, raw in velocity_coordinates.items():
            if not _rational(raw):
                continue
            actual_shift = _degree_difference(
                codomain_degrees[target_name],
                relation.degree,
                label=(
                    f"symbol map {symbol_map.name!r} relation velocity "
                    f"{relation.name!r}->{target_name!r}"
                ),
            )
            if actual_shift != symbol_map.shift:
                raise FilteredObstructionError(
                    "wrong_symbol_relation_velocity_shift",
                    f"symbol map {symbol_map.name!r} relation velocity "
                    f"{relation.name!r}->{target_name!r} has shift "
                    f"{actual_shift}, expected {symbol_map.shift}",
                )
        transported = (
            matrix * domain_relation_by_name[relation.name] + velocity
        )
        if _rank(
            sp.Matrix.hstack(codomain_relations, transported)
        ) != _rank(codomain_relations):
            raise FilteredObstructionError(
                "symbol_relation_not_invariant",
                f"symbol map {symbol_map.name!r} transports domain "
                f"relation {relation.name!r} outside codomain relations",
            )
    return matrix


def compile_filtered_obstruction(
    problem: FilteredObstructionProblem,
) -> FilteredObstructionCertificate:
    """Validate and compile one exact finite filtered obstruction problem."""

    basis_index, basis_degrees = _basis_index(problem.basis)
    relation_matrix, relation_by_name = _relation_matrix(
        problem.basis,
        problem.relations,
        basis_index=basis_index,
        basis_degrees=basis_degrees,
    )
    relation_names = set(relation_by_name)
    action_names: set[str] = set()
    action_matrices: list[sp.Matrix] = []
    for action in problem.actions:
        if action.name in action_names:
            raise FilteredObstructionError(
                "duplicate_action_name",
                f"action name {action.name!r} occurs more than once",
            )
        action_names.add(action.name)
        unknown_velocities = set(action.relation_velocities) - relation_names
        if unknown_velocities:
            raise FilteredObstructionError(
                "unknown_relation_velocity",
                f"action {action.name!r} gives velocities for unknown "
                f"relations {sorted(unknown_velocities)}",
            )
        matrix = _action_matrix(
            action,
            problem,
            basis_index=basis_index,
            basis_degrees=basis_degrees,
        )
        for relation in problem.relations:
            velocity = _column(
                action.relation_velocities.get(relation.name, {}),
                basis_index=basis_index,
                dimension=len(problem.basis),
                label=(
                    f"action {action.name} velocity of relation "
                    f"{relation.name}"
                ),
            )
            for target_name, raw in action.relation_velocities.get(
                relation.name, {}
            ).items():
                if not _rational(raw):
                    continue
                actual_shift = _degree_difference(
                    basis_degrees[target_name],
                    relation.degree,
                    label=(
                        f"action {action.name!r} relation velocity "
                        f"{relation.name!r}->{target_name!r}"
                    ),
                )
                if actual_shift != action.shift:
                    raise FilteredObstructionError(
                        "wrong_relation_velocity_shift",
                        f"action {action.name!r} relation velocity "
                        f"{relation.name!r}->{target_name!r} has shift "
                        f"{actual_shift}, expected {action.shift}",
                    )
            transported = matrix * relation_by_name[relation.name] + velocity
            if _rank(sp.Matrix.hstack(relation_matrix, transported)) != _rank(
                relation_matrix
            ):
                raise FilteredObstructionError(
                    "relation_not_invariant",
                    f"action {action.name!r} transports relation "
                    f"{relation.name!r} outside the relation span",
                )
        action_matrices.append(matrix)

    action_image_matrix = (
        sp.Matrix.hstack(*action_matrices)
        if action_matrices
        else sp.zeros(len(problem.basis), 0)
    )
    constraint_matrix = sp.Matrix.hstack(
        relation_matrix, action_image_matrix
    )
    constraint_labels = [
        f"relation:{relation.name}" for relation in problem.relations
    ] + [
        f"action:{action.name}:{basis.name}"
        for action in problem.actions
        for basis in problem.basis
    ]
    distinguished = _column(
        problem.distinguished,
        basis_index=basis_index,
        dimension=len(problem.basis),
        label="distinguished vector",
    )
    if distinguished == sp.zeros(len(problem.basis), 1):
        raise FilteredObstructionError(
            "zero_distinguished", "distinguished vector must be nonzero"
        )

    relation_rank = _rank(relation_matrix)
    action_image_rank = _rank(action_image_matrix)
    constraint_rank = _rank(constraint_matrix)
    augmented_rank = _rank(
        sp.Matrix.hstack(constraint_matrix, distinguished)
    )
    survives = augmented_rank > constraint_rank
    witness_by_basis: tuple[tuple[str, str], ...] = ()
    decomposition_by_column: tuple[tuple[str, str], ...] = ()
    pairing = "0"
    if survives:
        separation, witness = certify_column_separation(
            _domain_matrix(constraint_matrix),
            _domain_matrix(distinguished),
        )
        raw_pairing = sp.Rational(separation.rational_pairing)
        pairing = "1"
        witness_by_basis = tuple(
            sorted(
                (
                    item.name,
                    str(sp.cancel(witness[index, 0] / raw_pairing)),
                )
                for index, item in enumerate(problem.basis)
                if witness[index, 0] != 0
            )
        )
    else:
        _certificate, solution = solve_particular(
            _domain_matrix(constraint_matrix),
            _domain_matrix(distinguished),
        )
        decomposition_by_column = tuple(
            (label, str(solution[index, 0]))
            for index, label in enumerate(constraint_labels)
            if solution[index, 0] != 0
        )

    return FilteredObstructionCertificate(
        schema="ztare.filtered_obstruction_certificate.v1",
        problem_name=problem.name,
        basis_order=tuple(item.name for item in problem.basis),
        ambient_dimension=len(problem.basis),
        relation_rank=relation_rank,
        action_image_rank=action_image_rank,
        constraint_rank=constraint_rank,
        coinvariant_dimension=len(problem.basis) - constraint_rank,
        relation_transport_verified=True,
        distinguished_survives=survives,
        distinguished_pairing=pairing,
        witness_by_basis=witness_by_basis,
        decomposition_by_column=decomposition_by_column,
        constraint_matrix_sha256=_matrix_sha256(constraint_matrix),
        distinguished_sha256=_matrix_sha256(distinguished),
    )


def compile_fixed_grade_obstruction(
    problem: FilteredObstructionProblem,
) -> FilteredObstructionCertificate:
    """Compile a fixed-grade coinvariant only for degree-zero actions.

    A nonzero action shift belongs to a cross-grade symbol problem and is
    refused here before any rank calculation.
    """

    degrees = {item.degree for item in problem.basis}
    if len(degrees) != 1:
        raise FilteredObstructionError(
            "fixed_grade_has_multiple_degrees",
            "a fixed-grade problem must have exactly one basis degree",
        )
    shifted = [
        action.name
        for action in problem.actions
        if not _is_zero_degree(action.shift)
    ]
    if shifted:
        raise FilteredObstructionError(
            "fixed_grade_nonzero_shift",
            "fixed-grade compilation cannot accept shifted actions "
            f"{shifted}; compile a cross-grade symbol cokernel",
        )
    return compile_filtered_obstruction(problem)


def compile_filtered_symbol_cokernel(
    problem: FilteredSymbolCokernelProblem,
) -> FilteredSymbolCokernelCertificate:
    """Validate and compile a finite exact cross-grade symbol cokernel."""

    domain_index, domain_degrees = _basis_index(problem.domain_basis)
    codomain_index, codomain_degrees = _basis_index(problem.codomain_basis)
    domain_relations, domain_relation_by_name = _relation_matrix(
        problem.domain_basis,
        problem.domain_relations,
        basis_index=domain_index,
        basis_degrees=domain_degrees,
    )
    codomain_relations, _codomain_relation_by_name = _relation_matrix(
        problem.codomain_basis,
        problem.codomain_relations,
        basis_index=codomain_index,
        basis_degrees=codomain_degrees,
    )
    map_names: set[str] = set()
    map_matrices: list[sp.Matrix] = []
    for symbol_map in problem.maps:
        if symbol_map.name in map_names:
            raise FilteredObstructionError(
                "duplicate_symbol_map_name",
                f"symbol map name {symbol_map.name!r} occurs more than once",
            )
        map_names.add(symbol_map.name)
        matrix = _validated_symbol_map_matrix(
            symbol_map,
            domain_basis=problem.domain_basis,
            domain_relations=problem.domain_relations,
            domain_index=domain_index,
            domain_degrees=domain_degrees,
            domain_relation_by_name=domain_relation_by_name,
            codomain_basis=problem.codomain_basis,
            codomain_index=codomain_index,
            codomain_degrees=codomain_degrees,
            codomain_relations=codomain_relations,
        )
        map_matrices.append(matrix)

    symbol_image_matrix = (
        sp.Matrix.hstack(*map_matrices)
        if map_matrices
        else sp.zeros(len(problem.codomain_basis), 0)
    )
    constraint_matrix = sp.Matrix.hstack(
        codomain_relations, symbol_image_matrix
    )
    constraint_labels = [
        f"codomain_relation:{relation.name}"
        for relation in problem.codomain_relations
    ] + [
        f"symbol:{symbol_map.name}:{basis.name}"
        for symbol_map in problem.maps
        for basis in problem.domain_basis
    ]
    distinguished = _column(
        problem.distinguished,
        basis_index=codomain_index,
        dimension=len(problem.codomain_basis),
        label="distinguished codomain vector",
    )
    if distinguished == sp.zeros(len(problem.codomain_basis), 1):
        raise FilteredObstructionError(
            "zero_distinguished", "distinguished vector must be nonzero"
        )

    domain_relation_rank = _rank(domain_relations)
    codomain_relation_rank = _rank(codomain_relations)
    symbol_image_rank = _rank(symbol_image_matrix)
    constraint_rank = _rank(constraint_matrix)
    augmented_rank = _rank(
        sp.Matrix.hstack(constraint_matrix, distinguished)
    )
    survives = augmented_rank > constraint_rank
    witness_by_basis: tuple[tuple[str, str], ...] = ()
    decomposition_by_column: tuple[tuple[str, str], ...] = ()
    pairing = "0"
    if survives:
        separation, witness = certify_column_separation(
            _domain_matrix(constraint_matrix),
            _domain_matrix(distinguished),
        )
        raw_pairing = sp.Rational(separation.rational_pairing)
        pairing = "1"
        witness_by_basis = tuple(
            sorted(
                (
                    item.name,
                    str(sp.cancel(witness[index, 0] / raw_pairing)),
                )
                for index, item in enumerate(problem.codomain_basis)
                if witness[index, 0] != 0
            )
        )
    else:
        _certificate, solution = solve_particular(
            _domain_matrix(constraint_matrix),
            _domain_matrix(distinguished),
        )
        decomposition_by_column = tuple(
            (label, str(solution[index, 0]))
            for index, label in enumerate(constraint_labels)
            if solution[index, 0] != 0
        )

    return FilteredSymbolCokernelCertificate(
        schema="ztare.filtered_symbol_cokernel_certificate.v1",
        problem_name=problem.name,
        domain_basis_order=tuple(item.name for item in problem.domain_basis),
        codomain_basis_order=tuple(
            item.name for item in problem.codomain_basis
        ),
        domain_dimension=len(problem.domain_basis),
        codomain_dimension=len(problem.codomain_basis),
        domain_relation_rank=domain_relation_rank,
        codomain_relation_rank=codomain_relation_rank,
        symbol_image_rank=symbol_image_rank,
        constraint_rank=constraint_rank,
        cokernel_dimension=len(problem.codomain_basis) - constraint_rank,
        relation_transport_verified=True,
        map_shifts=tuple(
            (symbol_map.name, symbol_map.shift) for symbol_map in problem.maps
        ),
        distinguished_survives=survives,
        distinguished_pairing=pairing,
        witness_by_codomain_basis=witness_by_basis,
        decomposition_by_column=decomposition_by_column,
        constraint_matrix_sha256=_matrix_sha256(constraint_matrix),
        distinguished_sha256=_matrix_sha256(distinguished),
    )


def compile_filtered_coupled_blocks(
    problem: FilteredCoupledBlockProblem,
) -> FilteredCoupledBlockCertificate:
    """Compile several homogeneous blocks with one shared control vector.

    Each block map is validated independently for filtration shift and
    relation descent.  The quotient calculation then forms the direct sum
    of block codomains and inserts each domain column once, by vertically
    stacking its images.  This enforces one common control across all blocks.
    """

    if not problem.name:
        raise FilteredObstructionError(
            "empty_coupled_block_problem_name",
            "coupled-block problem names must be nonempty",
        )
    if not problem.blocks:
        raise FilteredObstructionError(
            "empty_coupled_blocks",
            "at least one coupled codomain block is required",
        )
    block_names = [block.name for block in problem.blocks]
    if any(not name for name in block_names):
        raise FilteredObstructionError(
            "empty_coupled_block_name",
            "coupled block names must be nonempty",
        )
    if len(block_names) != len(set(block_names)):
        raise FilteredObstructionError(
            "duplicate_coupled_block_name",
            "coupled block names must be unique",
        )

    domain_index, domain_degrees = _basis_index(problem.domain_basis)
    domain_relations, domain_relation_by_name = _relation_matrix(
        problem.domain_basis,
        problem.domain_relations,
        basis_index=domain_index,
        basis_degrees=domain_degrees,
    )

    block_rows: list[
        tuple[
            FilteredCoupledBlock,
            dict[str, int],
            sp.Matrix,
            sp.Matrix,
            sp.Matrix,
        ]
    ] = []
    total_dimension = 0
    total_relation_columns = 0
    for block in problem.blocks:
        codomain_index, codomain_degrees = _basis_index(
            block.codomain_basis
        )
        codomain_relations, _codomain_relation_by_name = _relation_matrix(
            block.codomain_basis,
            block.codomain_relations,
            basis_index=codomain_index,
            basis_degrees=codomain_degrees,
        )
        map_matrix = _validated_symbol_map_matrix(
            block.symbol_map,
            domain_basis=problem.domain_basis,
            domain_relations=problem.domain_relations,
            domain_index=domain_index,
            domain_degrees=domain_degrees,
            domain_relation_by_name=domain_relation_by_name,
            codomain_basis=block.codomain_basis,
            codomain_index=codomain_index,
            codomain_degrees=codomain_degrees,
            codomain_relations=codomain_relations,
        )
        distinguished = _column(
            block.distinguished,
            basis_index=codomain_index,
            dimension=len(block.codomain_basis),
            label=f"distinguished vector in block {block.name!r}",
        )
        block_rows.append((
            block,
            codomain_index,
            codomain_relations,
            map_matrix,
            distinguished,
        ))
        total_dimension += len(block.codomain_basis)
        total_relation_columns += codomain_relations.cols

    relation_matrix = sp.zeros(
        total_dimension, total_relation_columns
    )
    relation_labels: list[str] = []
    row_offset = 0
    column_offset = 0
    for block, _index, relations, _map, _distinguished in block_rows:
        relation_matrix[
            row_offset : row_offset + relations.rows,
            column_offset : column_offset + relations.cols,
        ] = relations
        relation_labels.extend(
            f"block_relation:{block.name}:{relation.name}"
            for relation in block.codomain_relations
        )
        row_offset += relations.rows
        column_offset += relations.cols

    common_control_matrix = sp.Matrix.vstack(
        *(row[3] for row in block_rows)
    )
    distinguished = sp.Matrix.vstack(
        *(row[4] for row in block_rows)
    )
    if distinguished == sp.zeros(total_dimension, 1):
        raise FilteredObstructionError(
            "zero_distinguished",
            "the coupled distinguished bundle must be nonzero",
        )
    constraint_matrix = sp.Matrix.hstack(
        relation_matrix, common_control_matrix
    )
    constraint_labels = relation_labels + [
        f"common_control:{basis.name}" for basis in problem.domain_basis
    ]
    constraint_rank = _rank(constraint_matrix)
    augmented_rank = _rank(
        sp.Matrix.hstack(constraint_matrix, distinguished)
    )
    survives = augmented_rank > constraint_rank

    witness_by_basis: tuple[tuple[str, str], ...] = ()
    decomposition_by_column: tuple[tuple[str, str], ...] = ()
    pairing = "0"
    combined_names = [
        f"{block.name}::{basis.name}"
        for block in problem.blocks
        for basis in block.codomain_basis
    ]
    if survives:
        separation, witness = certify_column_separation(
            _domain_matrix(constraint_matrix),
            _domain_matrix(distinguished),
        )
        raw_pairing = sp.Rational(separation.rational_pairing)
        pairing = "1"
        witness_by_basis = tuple(
            sorted(
                (
                    name,
                    str(sp.cancel(witness[index, 0] / raw_pairing)),
                )
                for index, name in enumerate(combined_names)
                if witness[index, 0] != 0
            )
        )
    else:
        _certificate, solution = solve_particular(
            _domain_matrix(constraint_matrix),
            _domain_matrix(distinguished),
        )
        decomposition_by_column = tuple(
            (label, str(solution[index, 0]))
            for index, label in enumerate(constraint_labels)
            if solution[index, 0] != 0
        )

    return FilteredCoupledBlockCertificate(
        schema="ztare.filtered_coupled_block_certificate.v1",
        problem_name=problem.name,
        domain_basis_order=tuple(
            basis.name for basis in problem.domain_basis
        ),
        block_basis_order=tuple(
            (
                block.name,
                tuple(basis.name for basis in block.codomain_basis),
            )
            for block in problem.blocks
        ),
        domain_dimension=len(problem.domain_basis),
        domain_relation_rank=_rank(domain_relations),
        ambient_dimension=total_dimension,
        block_relation_rank=_rank(relation_matrix),
        common_control_rank=_rank(common_control_matrix),
        constraint_rank=constraint_rank,
        coupled_cokernel_dimension=total_dimension - constraint_rank,
        relation_transport_verified=True,
        block_map_shifts=tuple(
            (block.name, block.symbol_map.shift)
            for block in problem.blocks
        ),
        distinguished_survives=survives,
        distinguished_pairing=pairing,
        witness_by_block_basis=witness_by_basis,
        decomposition_by_column=decomposition_by_column,
        constraint_matrix_sha256=_matrix_sha256(constraint_matrix),
        distinguished_sha256=_matrix_sha256(distinguished),
    )


def _independent_polynomial_equations(
    equations: list[sp.Expr],
    parameters: tuple[sp.Symbol, ...],
) -> tuple[sp.Expr, ...]:
    """Return a deterministic QQ-row basis for polynomial equations."""

    nonzero_equations = [
        sp.expand(equation)
        for equation in equations
        if sp.expand(equation) != 0
    ]
    if not nonzero_equations:
        return ()
    if not parameters:
        if any(equation.free_symbols for equation in nonzero_equations):
            raise FilteredObstructionError(
                "unbound_polynomial_parameter",
                "an equation retains symbols outside the parameter space",
            )
        return (sp.Integer(1),)
    polynomials = [
        sp.Poly(sp.expand(equation), *parameters, domain=sp.QQ)
        for equation in nonzero_equations
    ]
    monomials = sorted(
        {
            monomial
            for polynomial in polynomials
            for monomial, _coefficient in polynomial.terms()
        },
        reverse=True,
    )
    coefficient_matrix = sp.Matrix([
        [polynomial.coeff_monomial(monomial) for monomial in monomials]
        for polynomial in polynomials
    ])
    reduced, _pivots = coefficient_matrix.rref()
    result: list[sp.Expr] = []
    for row in range(reduced.rows):
        if all(reduced[row, column] == 0 for column in range(reduced.cols)):
            continue
        expression = sp.Integer(0)
        for column, monomial in enumerate(monomials):
            coefficient = reduced[row, column]
            if coefficient == 0:
                continue
            term = coefficient
            for parameter, exponent in zip(
                parameters, monomial, strict=True
            ):
                term *= parameter**exponent
            expression += term
        result.append(sp.expand(expression))
    return tuple(result)


def _eliminate_constant_linear_parameters(
    equations: tuple[sp.Expr, ...],
    parameters: tuple[sp.Symbol, ...],
) -> tuple[
    tuple[sp.Expr, ...],
    tuple[sp.Symbol, ...],
    tuple[str, ...],
    tuple[tuple[str, str], ...],
    tuple[tuple[str, int], ...],
]:
    """Existentially eliminate parameters with constant linear columns.

    If ``A*x + b(y) = 0`` and ``A`` is rational and constant, a solution in
    ``x`` exists exactly when every left annihilator of ``A`` kills ``b``.
    Repeating this projection exposes the triangular coefficient rows before
    a nonlinear Groebner calculation.  No division by a control polynomial
    or generic-nonzero assumption is used.
    """

    current_equations = equations
    remaining = list(parameters)
    eliminated: list[str] = []
    substitutions: list[tuple[str, str]] = []
    radical_zeros: list[tuple[str, int]] = []
    while True:
        active = set().union(
            *(equation.free_symbols for equation in current_equations)
        ) if current_equations else set()
        unused = [parameter for parameter in remaining if parameter not in active]
        if unused:
            unused_set = set(unused)
            eliminated.extend(parameter.name for parameter in unused)
            remaining = [
                parameter for parameter in remaining
                if parameter not in unused_set
            ]
        if not remaining:
            current_equations = _independent_polynomial_equations(
                list(current_equations), ()
            )
            break

        candidates = []
        for parameter in remaining:
            derivatives = [
                sp.expand(sp.diff(equation, parameter))
                for equation in current_equations
            ]
            if any(derivative != 0 for derivative in derivatives) and all(
                not derivative.free_symbols for derivative in derivatives
            ):
                candidates.append(parameter)
        if not candidates:
            pure_power = None
            for equation_index, equation in enumerate(current_equations):
                polynomial = sp.Poly(
                    equation, *tuple(remaining), domain=sp.QQ
                )
                terms = polynomial.terms()
                if len(terms) != 1:
                    continue
                monomial, coefficient = terms[0]
                nonzero_indices = [
                    index for index, exponent in enumerate(monomial)
                    if exponent
                ]
                if len(nonzero_indices) != 1 or coefficient == 0:
                    continue
                parameter_index = nonzero_indices[0]
                power = monomial[parameter_index]
                if power < 1:
                    continue
                pure_power = (
                    equation_index,
                    remaining[parameter_index],
                    power,
                )
                break
            if pure_power is not None:
                equation_index, parameter, power = pure_power
                remaining = [
                    item for item in remaining if item != parameter
                ]
                eliminated.append(parameter.name)
                radical_zeros.append((parameter.name, power))
                substituted = [
                    sp.expand(equation.subs(parameter, 0))
                    for index, equation in enumerate(current_equations)
                    if index != equation_index
                ]
                current_equations = _independent_polynomial_equations(
                    substituted, tuple(remaining)
                )
                continue

            pivot_options = []
            for equation_index, equation in enumerate(current_equations):
                for parameter_index, parameter in enumerate(remaining):
                    derivative = sp.expand(sp.diff(equation, parameter))
                    if derivative == 0 or derivative.free_symbols:
                        continue
                    if sp.expand(sp.diff(derivative, parameter)) != 0:
                        continue
                    remainder = sp.expand(equation - derivative * parameter)
                    if parameter in remainder.free_symbols:
                        continue
                    complexity = len(
                        sp.Poly(
                            remainder,
                            *tuple(
                                item for item in remaining
                                if item != parameter
                            ),
                            domain=sp.QQ,
                        ).terms()
                    ) if len(remaining) > 1 else int(remainder != 0)
                    pivot_options.append((
                        complexity,
                        equation_index,
                        parameter_index,
                        parameter,
                        sp.expand(-remainder / derivative),
                    ))
            if not pivot_options:
                break
            (
                _complexity,
                pivot_equation_index,
                _parameter_index,
                pivot_parameter,
                pivot_value,
            ) = min(pivot_options, key=lambda item: item[:3])
            remaining = [
                parameter for parameter in remaining
                if parameter != pivot_parameter
            ]
            eliminated.append(pivot_parameter.name)
            substitutions.append((pivot_parameter.name, str(pivot_value)))
            substituted = [
                sp.expand(equation.subs(pivot_parameter, pivot_value))
                for index, equation in enumerate(current_equations)
                if index != pivot_equation_index
            ]
            current_equations = _independent_polynomial_equations(
                substituted, tuple(remaining)
            )
            continue

        coefficient_matrix = sp.Matrix([
            [sp.Rational(sp.diff(equation, parameter))
             for parameter in candidates]
            for equation in current_equations
        ])
        zero_substitution = {
            parameter: sp.Integer(0) for parameter in candidates
        }
        remainder = sp.Matrix([
            sp.expand(equation.subs(zero_substitution))
            for equation in current_equations
        ])
        annihilators = coefficient_matrix.T.nullspace()
        projected = [
            sp.expand((annihilator.T * remainder)[0, 0])
            for annihilator in annihilators
        ]
        candidate_set = set(candidates)
        eliminated.extend(parameter.name for parameter in candidates)
        remaining = [
            parameter for parameter in remaining
            if parameter not in candidate_set
        ]
        current_equations = _independent_polynomial_equations(
            projected, tuple(remaining)
        )

    return (
        current_equations,
        tuple(remaining),
        tuple(eliminated),
        tuple(substitutions),
        tuple(radical_zeros),
    )


def _string_sequence_sha256(values: tuple[str, ...]) -> str:
    return hashlib.sha256(
        json.dumps(list(values), separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _groebner_basis_is_unit(basis: sp.GroebnerBasis) -> bool:
    return any(
        not polynomial.as_expr().free_symbols
        and polynomial.as_expr() != 0
        for polynomial in basis.polys
    )


def _integer_polynomial_modulus_inputs(
    equations: tuple[sp.Expr, ...],
    parameters: tuple[sp.Symbol, ...],
    prime: int,
) -> tuple[sp.Expr, ...] | None:
    result = []
    for equation in equations:
        polynomial = sp.Poly(equation, *parameters, domain=sp.QQ)
        denominator = sp.Integer(1)
        for _monomial, coefficient in polynomial.terms():
            denominator = sp.ilcm(denominator, coefficient.q)
        if int(denominator) % prime == 0:
            return None
        result.append(sp.expand(denominator * polynomial.as_expr()))
    return tuple(result)


def _modular_unit_ideal(
    equations: tuple[sp.Expr, ...],
    parameters: tuple[sp.Symbol, ...],
    prime: int,
) -> bool:
    if not equations:
        return False
    modular_inputs = _integer_polynomial_modulus_inputs(
        equations, parameters, prime
    )
    if modular_inputs is None:
        return False
    basis = sp.groebner(
        modular_inputs,
        *parameters,
        order="grevlex",
        modulus=prime,
        method="f5b",
    )
    return _groebner_basis_is_unit(basis)


def _select_modular_unit_core(
    equations: tuple[sp.Expr, ...],
    parameters: tuple[sp.Symbol, ...],
    prime: int,
) -> tuple[int, ...] | None:
    """Select a small likely unit core; exact QQ replay remains decisive."""

    if not equations:
        return None
    ordered = sorted(
        range(len(equations)),
        key=lambda index: (
            len(sp.Poly(
                equations[index], *parameters, domain=sp.QQ
            ).terms()),
            sp.Poly(
                equations[index], *parameters, domain=sp.QQ
            ).total_degree(),
            str(equations[index]),
        ),
    )
    size = 1
    selected: tuple[int, ...] | None = None
    while size < len(ordered):
        candidate = tuple(sorted(ordered[:size]))
        if _modular_unit_ideal(
            tuple(equations[index] for index in candidate),
            parameters,
            prime,
        ):
            selected = candidate
            break
        size *= 2
    if selected is None:
        candidate = tuple(range(len(equations)))
        if not _modular_unit_ideal(equations, parameters, prime):
            return None
        selected = candidate

    core = list(selected)
    for index in tuple(core):
        candidate = tuple(item for item in core if item != index)
        if candidate and _modular_unit_ideal(
            tuple(equations[item] for item in candidate),
            parameters,
            prime,
        ):
            core = list(candidate)
    return tuple(core)


def compile_filtered_polynomial_fiber(
    problem: FilteredPolynomialFiberProblem,
) -> FilteredPolynomialFiberCertificate:
    """Compile an exact polynomial fiber in coupled filtered quotients.

    The coupled-block compiler first validates filtration shifts, complete
    domains, and relation transport.  This compiler then annihilates the
    codomain-relation span, substitutes the declared monomial parameter map,
    and computes the exact QQ Groebner ideal of an independent equation row
    basis.  A unit ideal certifies an empty fiber over the algebraic closure;
    a proper ideal is deliberately reported as unresolved unless an exact
    rational point was supplied and verified.
    """

    if not problem.name:
        raise FilteredObstructionError(
            "empty_polynomial_fiber_name",
            "polynomial-fiber problem names must be nonempty",
        )
    if not problem.parameters:
        raise FilteredObstructionError(
            "empty_polynomial_parameter_space",
            "at least one polynomial control parameter is required",
        )
    if (
        any(not name or not name.isidentifier() for name in problem.parameters)
        or len(problem.parameters) != len(set(problem.parameters))
    ):
        raise FilteredObstructionError(
            "invalid_polynomial_parameter_name",
            "polynomial parameter names must be nonempty unique identifiers",
        )

    linear_certificate = compile_filtered_coupled_blocks(
        problem.linearization
    )
    domain_names = tuple(
        basis.name for basis in problem.linearization.domain_basis
    )
    unknown_monomials = set(problem.monomial_exponents) - set(domain_names)
    missing_monomials = set(domain_names) - set(problem.monomial_exponents)
    if unknown_monomials or missing_monomials:
        raise FilteredObstructionError(
            "incomplete_polynomial_monomial_map",
            "monomial exponents must cover the linearization domain exactly; "
            f"unknown={sorted(unknown_monomials)}, "
            f"missing={sorted(missing_monomials)}",
        )
    exponents_by_name: dict[str, tuple[int, ...]] = {}
    for name in domain_names:
        exponents = problem.monomial_exponents[name]
        if (
            not isinstance(exponents, tuple)
            or len(exponents) != len(problem.parameters)
            or any(
                isinstance(exponent, bool)
                or not isinstance(exponent, int)
                or exponent < 0
                for exponent in exponents
            )
        ):
            raise FilteredObstructionError(
                "invalid_polynomial_monomial",
                f"domain basis {name!r} needs {len(problem.parameters)} "
                "nonnegative integer exponents",
            )
        if not any(exponents):
            raise FilteredObstructionError(
                "constant_polynomial_control_monomial",
                "the constant term belongs in the distinguished bundle, "
                f"not domain basis {name!r}",
            )
        exponents_by_name[name] = exponents

    domain_index, domain_degrees = _basis_index(
        problem.linearization.domain_basis
    )
    block_relation_matrices: list[sp.Matrix] = []
    block_map_matrices: list[sp.Matrix] = []
    block_distinguished: list[sp.Matrix] = []
    for block in problem.linearization.blocks:
        codomain_index, codomain_degrees = _basis_index(
            block.codomain_basis
        )
        relations, _relations_by_name = _relation_matrix(
            block.codomain_basis,
            block.codomain_relations,
            basis_index=codomain_index,
            basis_degrees=codomain_degrees,
        )
        block_relation_matrices.append(relations)
        block_map_matrices.append(_symbol_map_matrix(
            block.symbol_map,
            domain_index=domain_index,
            domain_degrees=domain_degrees,
            codomain_index=codomain_index,
            codomain_degrees=codomain_degrees,
        ))
        block_distinguished.append(_column(
            block.distinguished,
            basis_index=codomain_index,
            dimension=len(block.codomain_basis),
            label=f"distinguished vector in block {block.name!r}",
        ))

    total_dimension = sum(
        len(block.codomain_basis) for block in problem.linearization.blocks
    )
    total_relation_columns = sum(
        matrix.cols for matrix in block_relation_matrices
    )
    relation_matrix = sp.zeros(total_dimension, total_relation_columns)
    row_offset = 0
    column_offset = 0
    for relations in block_relation_matrices:
        relation_matrix[
            row_offset : row_offset + relations.rows,
            column_offset : column_offset + relations.cols,
        ] = relations
        row_offset += relations.rows
        column_offset += relations.cols
    common_control_matrix = sp.Matrix.vstack(*block_map_matrices)
    distinguished = sp.Matrix.vstack(*block_distinguished)

    relation_annihilators = relation_matrix.T.nullspace()
    quotient_projection = (
        sp.Matrix.vstack(*(vector.T for vector in relation_annihilators))
        if relation_annihilators
        else sp.zeros(0, total_dimension)
    )
    parameters = tuple(sp.Symbol(name) for name in problem.parameters)
    monomial_vector = sp.Matrix([
        sp.prod(
            parameter**exponent
            for parameter, exponent in zip(
                parameters, exponents_by_name[name], strict=True
            )
        )
        for name in domain_names
    ])
    residual = quotient_projection * (
        distinguished + common_control_matrix * monomial_vector
    )
    raw_equations = [
        sp.expand(residual[row, 0]) for row in range(residual.rows)
    ]
    independent_equations = _independent_polynomial_equations(
        raw_equations, parameters
    )

    rational_point: tuple[tuple[str, str], ...] = ()
    point_verified = False
    if problem.rational_point:
        unknown_point = set(problem.rational_point) - set(problem.parameters)
        missing_point = set(problem.parameters) - set(problem.rational_point)
        if unknown_point or missing_point:
            raise FilteredObstructionError(
                "incomplete_polynomial_rational_point",
                "a rational point must assign every parameter exactly; "
                f"unknown={sorted(unknown_point)}, missing={sorted(missing_point)}",
            )
        substitutions = {
            parameter: _rational(problem.rational_point[parameter.name])
            for parameter in parameters
        }
        if any(
            sp.cancel(equation.subs(substitutions)) != 0
            for equation in independent_equations
        ):
            raise FilteredObstructionError(
                "polynomial_rational_point_not_on_fiber",
                "the supplied rational point does not satisfy the fiber",
            )
        point_verified = True
        rational_point = tuple(
            (name, str(substitutions[sp.Symbol(name)]))
            for name in problem.parameters
        )

    (
        post_elimination_equations,
        groebner_parameters,
        eliminated,
        triangular_substitutions,
        radical_zero_parameters,
    ) = (
        _eliminate_constant_linear_parameters(
            independent_equations, parameters
        )
    )

    if not post_elimination_equations:
        groebner_basis: tuple[str, ...] = ()
        unit_ideal = False
        fiber_status = (
            "rational_point_verified"
            if point_verified
            else "identically_zero_fiber"
        )
        modular_core_prime = 0
        groebner_input_indices: tuple[int, ...] = ()
        groebner_method = "none_identically_zero_fiber"
    elif not groebner_parameters:
        groebner_basis = ("1",)
        unit_ideal = True
        fiber_status = "empty_over_algebraic_closure"
        modular_core_prime = 0
        groebner_input_indices = tuple(
            range(len(post_elimination_equations))
        )
        groebner_method = "constant_linear_elimination_over_QQ"
    else:
        modular_core_prime = 1009
        selected_core = _select_modular_unit_core(
            post_elimination_equations,
            groebner_parameters,
            modular_core_prime,
        )
        groebner_input_indices = (
            selected_core
            if selected_core is not None
            else tuple(range(len(post_elimination_equations)))
        )
        basis = sp.groebner(
            tuple(
                post_elimination_equations[index]
                for index in groebner_input_indices
            ),
            *groebner_parameters,
            order="grevlex",
            method="f5b",
        )
        if selected_core is not None and not _groebner_basis_is_unit(basis):
            groebner_input_indices = tuple(
                range(len(post_elimination_equations))
            )
            basis = sp.groebner(
                post_elimination_equations,
                *groebner_parameters,
                order="grevlex",
                method="f5b",
            )
        groebner_expressions = tuple(
            sp.expand(polynomial.as_expr()) for polynomial in basis.polys
        )
        groebner_basis = tuple(
            str(expression) for expression in groebner_expressions
        )
        unit_ideal = any(
            not expression.free_symbols and expression != 0
            for expression in groebner_expressions
        )
        if unit_ideal:
            fiber_status = "empty_over_algebraic_closure"
        elif point_verified:
            fiber_status = "rational_point_verified"
        else:
            fiber_status = "proper_ideal_unresolved"
        groebner_method = (
            "modular_core_selection_then_f5b_over_QQ"
            if selected_core is not None and unit_ideal
            else "full_f5b_over_QQ_after_constant_linear_elimination"
        )

    independent_strings = tuple(
        str(equation) for equation in independent_equations
    )
    post_elimination_strings = tuple(
        str(equation) for equation in post_elimination_equations
    )
    return FilteredPolynomialFiberCertificate(
        schema="ztare.filtered_polynomial_fiber_certificate.v1",
        problem_name=problem.name,
        linearization_problem_name=problem.linearization.name,
        parameter_order=problem.parameters,
        monomial_by_domain_basis=tuple(
            (name, exponents_by_name[name]) for name in domain_names
        ),
        block_basis_order=linear_certificate.block_basis_order,
        ambient_dimension=total_dimension,
        block_relation_rank=_rank(relation_matrix),
        quotient_dimension=quotient_projection.rows,
        common_control_rank=linear_certificate.common_control_rank,
        linearized_bundle_survives=(
            linear_certificate.distinguished_survives
        ),
        linearized_decomposition_by_column=(
            linear_certificate.decomposition_by_column
        ),
        raw_equation_count=len(raw_equations),
        independent_equation_count=len(independent_equations),
        relation_transport_verified=True,
        block_map_shifts=linear_certificate.block_map_shifts,
        fiber_status=fiber_status,
        unit_ideal=unit_ideal,
        rational_point_verified=point_verified,
        rational_point_by_parameter=rational_point,
        independent_equations=independent_strings,
        eliminated_parameters=eliminated,
        triangular_substitutions=triangular_substitutions,
        radical_zero_parameters=radical_zero_parameters,
        groebner_parameter_order=tuple(
            parameter.name for parameter in groebner_parameters
        ),
        post_elimination_equations=post_elimination_strings,
        groebner_method=groebner_method,
        modular_core_prime=modular_core_prime,
        groebner_input_equation_indices=groebner_input_indices,
        groebner_basis=groebner_basis,
        equation_system_sha256=_string_sequence_sha256(independent_strings),
        groebner_basis_sha256=_string_sequence_sha256(groebner_basis),
    )


def compile_filtered_reachability(
    problem: FilteredReachabilityProblem,
) -> FilteredReachabilityCertificate:
    """Measure the supplied forcing span in a validated symbol cokernel.

    A positive ``cokernel_dimension`` describes the ambient quotient.  The
    separate ``reachable_cokernel_dimension`` is the rank of the named
    forcing columns after quotienting relations and control images.  A zero
    reachable dimension is an exact certificate that the adapter's forcing
    family cannot excite any surviving ambient class.
    """

    if not problem.name:
        raise FilteredObstructionError(
            "empty_reachability_name",
            "reachability problem names must be nonempty",
        )
    if not problem.forcing_columns:
        raise FilteredObstructionError(
            "empty_forcing_span",
            "at least one named forcing column is required",
        )
    if any(not name for name in problem.forcing_columns):
        raise FilteredObstructionError(
            "empty_forcing_name",
            "forcing column names must be nonempty",
        )

    symbol_certificate = compile_filtered_symbol_cokernel(
        problem.symbol_problem
    )
    domain_index, domain_degrees = _basis_index(
        problem.symbol_problem.domain_basis
    )
    codomain_index, codomain_degrees = _basis_index(
        problem.symbol_problem.codomain_basis
    )
    codomain_relations, _relations_by_name = _relation_matrix(
        problem.symbol_problem.codomain_basis,
        problem.symbol_problem.codomain_relations,
        basis_index=codomain_index,
        basis_degrees=codomain_degrees,
    )
    map_matrices = [
        _symbol_map_matrix(
            symbol_map,
            domain_index=domain_index,
            domain_degrees=domain_degrees,
            codomain_index=codomain_index,
            codomain_degrees=codomain_degrees,
        )
        for symbol_map in problem.symbol_problem.maps
    ]
    symbol_images = (
        sp.Matrix.hstack(*map_matrices)
        if map_matrices
        else sp.zeros(len(codomain_index), 0)
    )
    constraints = sp.Matrix.hstack(codomain_relations, symbol_images)
    constraint_rank = _rank(constraints)

    forcing_names = tuple(problem.forcing_columns)
    forcing_columns = []
    for name in forcing_names:
        column = _column(
            problem.forcing_columns[name],
            basis_index=codomain_index,
            dimension=len(codomain_index),
            label=f"forcing column {name}",
        )
        if column == sp.zeros(len(codomain_index), 1):
            raise FilteredObstructionError(
                "zero_forcing_column",
                f"forcing column {name!r} is zero",
            )
        forcing_columns.append(column)
    forcing_matrix = sp.Matrix.hstack(*forcing_columns)
    reachable_rank = (
        _rank(sp.Matrix.hstack(constraints, forcing_matrix))
        - constraint_rank
    )
    forcing_survives = tuple(
        (
            name,
            _rank(sp.Matrix.hstack(constraints, column)) > constraint_rank,
        )
        for name, column in zip(
            forcing_names, forcing_columns, strict=True
        )
    )
    if reachable_rank > symbol_certificate.cokernel_dimension:
        raise AssertionError("reachable quotient rank exceeds cokernel")

    return FilteredReachabilityCertificate(
        schema="ztare.filtered_reachability_certificate.v1",
        problem_name=problem.name,
        symbol_problem_name=problem.symbol_problem.name,
        codomain_basis_order=tuple(
            item.name for item in problem.symbol_problem.codomain_basis
        ),
        forcing_names=forcing_names,
        ambient_dimension=len(problem.symbol_problem.codomain_basis),
        cokernel_dimension=symbol_certificate.cokernel_dimension,
        forcing_span_rank=_rank(forcing_matrix),
        reachable_cokernel_dimension=reachable_rank,
        unreachable_cokernel_dimension=(
            symbol_certificate.cokernel_dimension - reachable_rank
        ),
        forcing_survives_by_name=forcing_survives,
        constraint_matrix_sha256=_matrix_sha256(constraints),
        forcing_matrix_sha256=_matrix_sha256(forcing_matrix),
    )


def compile_filtered_graph_quotient(
    problem: FilteredGraphQuotientProblem,
) -> FilteredGraphQuotientCertificate:
    """Compile a filtered direct sum modulo an exact boundary graph.

    For ``Phi: T -> S`` the compiler constructs the graph map

        h |-> (Phi(h), h)

    in ``S + T[shift]`` and delegates relation and filtration checks to the
    cross-grade symbol compiler.  It independently compresses the
    distinguished pair to ``source - Phi(target)`` and asserts the canonical
    graph-quotient isomorphism against the direct-sum certificate.
    """

    if not problem.name:
        raise FilteredObstructionError(
            "empty_graph_quotient_name",
            "graph-quotient problem names must be nonempty",
        )
    if problem.boundary_map.relation_velocities:
        raise FilteredObstructionError(
            "moving_graph_boundary_not_supported",
            "graph quotients require a static boundary map on fixed "
            "quotients",
        )

    source_index, source_degrees = _basis_index(problem.source_basis)
    target_index, target_degrees = _basis_index(problem.target_basis)
    source_relations, _source_relation_by_name = _relation_matrix(
        problem.source_basis,
        problem.source_relations,
        basis_index=source_index,
        basis_degrees=source_degrees,
    )
    _target_relations, _target_relation_by_name = _relation_matrix(
        problem.target_basis,
        problem.target_relations,
        basis_index=target_index,
        basis_degrees=target_degrees,
    )
    boundary = _symbol_map_matrix(
        problem.boundary_map,
        domain_index=target_index,
        domain_degrees=target_degrees,
        codomain_index=source_index,
        codomain_degrees=source_degrees,
    )

    source_prefix = "source::"
    target_prefix = "target::"
    combined_basis = tuple(
        FilteredBasisVector(
            source_prefix + item.name,
            item.degree,
        )
        for item in problem.source_basis
    ) + tuple(
        FilteredBasisVector(
            target_prefix + item.name,
            _add_degree(
                item.degree,
                problem.boundary_map.shift,
                label=f"graph target basis {item.name!r}",
            ),
        )
        for item in problem.target_basis
    )
    combined_relations = tuple(
        FilteredRelation(
            source_prefix + relation.name,
            relation.degree,
            {
                source_prefix + name: coefficient
                for name, coefficient in relation.coordinates.items()
            },
        )
        for relation in problem.source_relations
    ) + tuple(
        FilteredRelation(
            target_prefix + relation.name,
            _add_degree(
                relation.degree,
                problem.boundary_map.shift,
                label=f"graph target relation {relation.name!r}",
            ),
            {
                target_prefix + name: coefficient
                for name, coefficient in relation.coordinates.items()
            },
        )
        for relation in problem.target_relations
    )
    graph_columns: dict[str, dict[str, RationalInput]] = {}
    for target_item in problem.target_basis:
        column: dict[str, RationalInput] = {
            target_prefix + target_item.name: 1,
        }
        for source_name, coefficient in problem.boundary_map.columns[
            target_item.name
        ].items():
            column[source_prefix + source_name] = coefficient
        graph_columns[target_item.name] = column

    distinguished_pair: dict[str, RationalInput] = {
        source_prefix + name: coefficient
        for name, coefficient in problem.distinguished_source.items()
    }
    distinguished_pair.update({
        target_prefix + name: coefficient
        for name, coefficient in problem.distinguished_target.items()
    })
    graph_certificate = compile_filtered_symbol_cokernel(
        FilteredSymbolCokernelProblem(
            name=problem.name + "_direct_sum_graph",
            domain_basis=problem.target_basis,
            domain_relations=problem.target_relations,
            codomain_basis=combined_basis,
            codomain_relations=combined_relations,
            maps=(
                FilteredSymbolMap(
                    problem.boundary_map.name + "_graph",
                    problem.boundary_map.shift,
                    graph_columns,
                ),
            ),
            distinguished=distinguished_pair,
        )
    )

    distinguished_source = _column(
        problem.distinguished_source,
        basis_index=source_index,
        dimension=len(problem.source_basis),
        label="distinguished graph source vector",
    )
    distinguished_target = _column(
        problem.distinguished_target,
        basis_index=target_index,
        dimension=len(problem.target_basis),
        label="distinguished graph target vector",
    )
    compressed = distinguished_source - boundary * distinguished_target
    source_relation_rank = _rank(source_relations)
    compressed_survives = (
        _rank(sp.Matrix.hstack(source_relations, compressed))
        > source_relation_rank
    )
    if compressed_survives != graph_certificate.distinguished_survives:
        raise AssertionError(
            "direct graph quotient disagrees with canonical compression"
        )
    source_quotient_dimension = (
        len(problem.source_basis) - source_relation_rank
    )
    if graph_certificate.cokernel_dimension != source_quotient_dimension:
        raise AssertionError(
            "graph quotient dimension disagrees with source quotient"
        )

    compressed_witness: tuple[tuple[str, str], ...] = ()
    if compressed_survives:
        separation, witness = certify_column_separation(
            _domain_matrix(source_relations),
            _domain_matrix(compressed),
        )
        raw_pairing = sp.Rational(separation.rational_pairing)
        compressed_witness = tuple(
            sorted(
                (
                    item.name,
                    str(sp.cancel(witness[index, 0] / raw_pairing)),
                )
                for index, item in enumerate(problem.source_basis)
                if witness[index, 0] != 0
            )
        )

    return FilteredGraphQuotientCertificate(
        schema="ztare.filtered_graph_quotient_certificate.v1",
        problem_name=problem.name,
        source_basis_order=tuple(item.name for item in problem.source_basis),
        target_basis_order=tuple(item.name for item in problem.target_basis),
        source_dimension=len(problem.source_basis),
        target_dimension=len(problem.target_basis),
        source_quotient_dimension=source_quotient_dimension,
        graph_quotient_dimension=graph_certificate.cokernel_dimension,
        boundary_map_shift=problem.boundary_map.shift,
        relation_transport_verified=True,
        distinguished_survives=graph_certificate.distinguished_survives,
        compressed_source_survives=compressed_survives,
        distinguished_pairing=graph_certificate.distinguished_pairing,
        compressed_source_by_basis=tuple(
            (item.name, str(compressed[index, 0]))
            for index, item in enumerate(problem.source_basis)
            if compressed[index, 0] != 0
        ),
        compressed_witness_by_source_basis=compressed_witness,
        decomposition_by_graph_column=(
            graph_certificate.decomposition_by_column
        ),
        graph_constraint_sha256=(
            graph_certificate.constraint_matrix_sha256
        ),
        compressed_source_sha256=_matrix_sha256(compressed),
    )


def compile_filtered_surplus_projection(
    problem: FilteredSurplusProjectionProblem,
) -> FilteredSurplusProjectionCertificate:
    """Compile affine terminal reachability over a complete surplus fiber.

    Let ``S`` and ``T`` be the surplus and terminal maps from the shared
    control space.  After quotienting their declared relations, this decides

        S(x) = distinguished_surplus,
        T(x) = distinguished_terminal.

    The default distinguished surplus is zero, recovering terminal
    reachability in ``T(ker S)``.  A negative answer either separates the
    surplus demand from ``im S`` or separates the residual terminal demand
    from ``T(ker S)``.  A positive answer returns one exact control solving
    both quotient equations.
    """

    if not problem.name:
        raise FilteredObstructionError(
            "empty_surplus_projection_name",
            "surplus-projection problem names must be nonempty",
        )
    if problem.surplus_map.relation_velocities:
        raise FilteredObstructionError(
            "moving_surplus_relation_not_supported",
            "surplus projection requires a static map on fixed quotients",
        )
    if problem.terminal_map.relation_velocities:
        raise FilteredObstructionError(
            "moving_terminal_relation_not_supported",
            "terminal projection requires a static map on fixed quotients",
        )

    domain_index, domain_degrees = _basis_index(problem.domain_basis)
    surplus_index, surplus_degrees = _basis_index(problem.surplus_basis)
    terminal_index, terminal_degrees = _basis_index(problem.terminal_basis)
    domain_relations, domain_relation_by_name = _relation_matrix(
        problem.domain_basis,
        problem.domain_relations,
        basis_index=domain_index,
        basis_degrees=domain_degrees,
    )
    surplus_relations, _surplus_relation_by_name = _relation_matrix(
        problem.surplus_basis,
        problem.surplus_relations,
        basis_index=surplus_index,
        basis_degrees=surplus_degrees,
    )
    terminal_relations, _terminal_relation_by_name = _relation_matrix(
        problem.terminal_basis,
        problem.terminal_relations,
        basis_index=terminal_index,
        basis_degrees=terminal_degrees,
    )
    surplus_map = _symbol_map_matrix(
        problem.surplus_map,
        domain_index=domain_index,
        domain_degrees=domain_degrees,
        codomain_index=surplus_index,
        codomain_degrees=surplus_degrees,
    )
    terminal_map = _symbol_map_matrix(
        problem.terminal_map,
        domain_index=domain_index,
        domain_degrees=domain_degrees,
        codomain_index=terminal_index,
        codomain_degrees=terminal_degrees,
    )

    for relation in problem.domain_relations:
        source = domain_relation_by_name[relation.name]
        transported_surplus = surplus_map * source
        if _rank(
            sp.Matrix.hstack(surplus_relations, transported_surplus)
        ) != _rank(surplus_relations):
            raise FilteredObstructionError(
                "surplus_relation_not_invariant",
                f"surplus map {problem.surplus_map.name!r} transports "
                f"domain relation {relation.name!r} outside surplus "
                "relations",
            )
        transported_terminal = terminal_map * source
        if _rank(
            sp.Matrix.hstack(terminal_relations, transported_terminal)
        ) != _rank(terminal_relations):
            raise FilteredObstructionError(
                "terminal_relation_not_invariant",
                f"terminal map {problem.terminal_map.name!r} transports "
                f"domain relation {relation.name!r} outside terminal "
                "relations",
            )

    domain_relation_rank = _rank(domain_relations)
    surplus_relation_rank = _rank(surplus_relations)
    terminal_relation_rank = _rank(terminal_relations)
    surplus_constraints = sp.Matrix.hstack(
        surplus_map,
        -surplus_relations,
    )
    raw_kernel_columns = []
    for vector in surplus_constraints.nullspace():
        domain_part = vector[: len(problem.domain_basis), :]
        if domain_part != sp.zeros(len(problem.domain_basis), 1):
            raw_kernel_columns.append(domain_part)
    raw_kernel = (
        sp.Matrix.hstack(*raw_kernel_columns)
        if raw_kernel_columns
        else sp.zeros(len(problem.domain_basis), 0)
    )
    independent_kernel_columns = raw_kernel.columnspace()
    surplus_kernel = (
        sp.Matrix.hstack(*independent_kernel_columns)
        if independent_kernel_columns
        else sp.zeros(len(problem.domain_basis), 0)
    )

    domain_quotient_dimension = (
        len(problem.domain_basis) - domain_relation_rank
    )
    surplus_image_rank = (
        _rank(sp.Matrix.hstack(surplus_relations, surplus_map))
        - surplus_relation_rank
    )
    surplus_kernel_dimension = (
        domain_quotient_dimension - surplus_image_rank
    )
    computed_kernel_dimension = (
        _rank(sp.Matrix.hstack(domain_relations, surplus_kernel))
        - domain_relation_rank
    )
    if computed_kernel_dimension != surplus_kernel_dimension:
        raise AssertionError(
            "projected surplus nullspace failed quotient rank-nullity"
        )

    terminal_kernel_image = terminal_map * surplus_kernel
    terminal_constraints = sp.Matrix.hstack(
        terminal_relations,
        terminal_kernel_image,
    )
    terminal_reachable_dimension = (
        _rank(terminal_constraints) - terminal_relation_rank
    )
    distinguished_surplus = _column(
        problem.distinguished_surplus,
        basis_index=surplus_index,
        dimension=len(problem.surplus_basis),
        label="distinguished surplus vector",
    )
    distinguished = _column(
        problem.distinguished_terminal,
        basis_index=terminal_index,
        dimension=len(problem.terminal_basis),
        label="distinguished terminal vector",
    )
    surplus_is_zero = (
        distinguished_surplus
        == sp.zeros(len(problem.surplus_basis), 1)
    )
    terminal_is_zero = (
        distinguished == sp.zeros(len(problem.terminal_basis), 1)
    )
    if surplus_is_zero and terminal_is_zero:
        raise FilteredObstructionError(
            "zero_distinguished_pair",
            "at least one distinguished projection must be nonzero",
        )

    surplus_constraint_rank = _rank(surplus_constraints)
    surplus_reachable = (
        _rank(
            sp.Matrix.hstack(
                surplus_constraints,
                distinguished_surplus,
            )
        )
        == surplus_constraint_rank
    )
    surplus_pairing = "0"
    witness_by_surplus_basis: tuple[tuple[str, str], ...] = ()
    particular_control = sp.zeros(len(problem.domain_basis), 1)
    particular_surplus_preimage: tuple[tuple[str, str], ...] = ()
    if not surplus_reachable:
        separation, witness = certify_column_separation(
            _domain_matrix(surplus_constraints),
            _domain_matrix(distinguished_surplus),
        )
        raw_pairing = sp.Rational(separation.rational_pairing)
        surplus_pairing = "1"
        witness_by_surplus_basis = tuple(
            sorted(
                (
                    item.name,
                    str(sp.cancel(witness[index, 0] / raw_pairing)),
                )
                for index, item in enumerate(problem.surplus_basis)
                if witness[index, 0] != 0
            )
        )
    elif not surplus_is_zero:
        _certificate, surplus_solution = solve_particular(
            _domain_matrix(surplus_constraints),
            _domain_matrix(distinguished_surplus),
        )
        particular_control = surplus_solution[
            : len(problem.domain_basis), :
        ]
        particular_surplus_preimage = tuple(
            (item.name, str(particular_control[index, 0]))
            for index, item in enumerate(problem.domain_basis)
            if particular_control[index, 0] != 0
        )
        if _rank(
            sp.Matrix.hstack(
                surplus_relations,
                surplus_map * particular_control
                - distinguished_surplus,
            )
        ) != surplus_relation_rank:
            raise AssertionError(
                "reported particular control misses the surplus demand"
            )

    terminal_residual = distinguished - terminal_map * particular_control
    constraint_rank = _rank(terminal_constraints)
    pair_cancellable = (
        surplus_reachable
        and _rank(
            sp.Matrix.hstack(terminal_constraints, terminal_residual)
        )
        == constraint_rank
    )
    witness_by_basis: tuple[tuple[str, str], ...] = ()
    cancellation_by_domain_basis: tuple[tuple[str, str], ...] = ()
    pairing = "0"
    if surplus_reachable and not pair_cancellable:
        separation, witness = certify_column_separation(
            _domain_matrix(terminal_constraints),
            _domain_matrix(terminal_residual),
        )
        raw_pairing = sp.Rational(separation.rational_pairing)
        pairing = "1"
        witness_by_basis = tuple(
            sorted(
                (
                    item.name,
                    str(sp.cancel(witness[index, 0] / raw_pairing)),
                )
                for index, item in enumerate(problem.terminal_basis)
                if witness[index, 0] != 0
            )
        )
    elif pair_cancellable:
        _certificate, solution = solve_particular(
            _domain_matrix(terminal_constraints),
            _domain_matrix(terminal_residual),
        )
        kernel_coefficients = solution[
            len(problem.terminal_relations) :, :
        ]
        control = (
            particular_control
            + surplus_kernel * kernel_coefficients
        )
        cancellation_by_domain_basis = tuple(
            (item.name, str(control[index, 0]))
            for index, item in enumerate(problem.domain_basis)
            if control[index, 0] != 0
        )
        if _rank(
            sp.Matrix.hstack(
                surplus_relations,
                surplus_map * control - distinguished_surplus,
            )
        ) != surplus_relation_rank:
            raise AssertionError(
                "reported affine cancellation misses the surplus demand"
            )
        if _rank(
            sp.Matrix.hstack(
                terminal_relations,
                terminal_map * control - distinguished,
            )
        ) != terminal_relation_rank:
            raise AssertionError("reported control misses the terminal")

    return FilteredSurplusProjectionCertificate(
        schema="ztare.filtered_surplus_projection_certificate.v2",
        problem_name=problem.name,
        domain_basis_order=tuple(item.name for item in problem.domain_basis),
        surplus_basis_order=tuple(item.name for item in problem.surplus_basis),
        terminal_basis_order=tuple(item.name for item in problem.terminal_basis),
        domain_dimension=len(problem.domain_basis),
        surplus_dimension=len(problem.surplus_basis),
        terminal_dimension=len(problem.terminal_basis),
        domain_relation_rank=domain_relation_rank,
        surplus_relation_rank=surplus_relation_rank,
        terminal_relation_rank=terminal_relation_rank,
        surplus_image_rank=surplus_image_rank,
        surplus_kernel_dimension=surplus_kernel_dimension,
        terminal_reachable_without_surplus_dimension=(
            terminal_reachable_dimension
        ),
        relation_transport_verified=True,
        distinguished_surplus_is_zero=surplus_is_zero,
        distinguished_surplus_reachable=surplus_reachable,
        distinguished_pair_cancellable=pair_cancellable,
        distinguished_cancellable_without_surplus=(
            pair_cancellable and surplus_is_zero
        ),
        distinguished_surplus_pairing=surplus_pairing,
        distinguished_pairing=pairing,
        witness_by_surplus_basis=witness_by_surplus_basis,
        witness_by_terminal_basis=witness_by_basis,
        particular_surplus_preimage_by_domain_basis=(
            particular_surplus_preimage
        ),
        cancellation_by_domain_basis=cancellation_by_domain_basis,
        surplus_map_shift=problem.surplus_map.shift,
        terminal_map_shift=problem.terminal_map.shift,
        surplus_constraint_sha256=_matrix_sha256(surplus_constraints),
        surplus_kernel_sha256=_matrix_sha256(surplus_kernel),
        terminal_constraint_sha256=_matrix_sha256(terminal_constraints),
        distinguished_surplus_sha256=_matrix_sha256(
            distinguished_surplus
        ),
        distinguished_sha256=_matrix_sha256(distinguished),
        terminal_residual_sha256=_matrix_sha256(terminal_residual),
    )


def compile_filtered_induction(
    problem: FilteredInductionProblem,
) -> FilteredInductionCertificate:
    """Check a proof-carrying well-founded filtered transition graph.

    Local exact algebra remains adapter-owned and is bound by the state
    certificate digests.  This compiler checks the composition theorem:
    every declared local outcome either closes its branch by a terminal or
    budget charge, or moves to a strictly smaller rank in ``N^d``.
    """

    if not problem.name:
        raise FilteredObstructionError(
            "empty_problem_name", "induction problem name must be nonempty"
        )
    if not problem.states:
        raise FilteredObstructionError(
            "empty_induction_states", "at least one state is required"
        )

    state_names = tuple(state.name for state in problem.states)
    if any(not name for name in state_names):
        raise FilteredObstructionError(
            "empty_induction_state_name", "state names must be nonempty"
        )
    if len(set(state_names)) != len(state_names):
        raise FilteredObstructionError(
            "duplicate_induction_state_name", "state names must be unique"
        )
    state_by_name = {state.name: state for state in problem.states}

    rank_dimension = len(problem.states[0].rank)
    if rank_dimension == 0:
        raise FilteredObstructionError(
            "empty_induction_rank", "state ranks must be nonempty tuples"
        )
    for state in problem.states:
        if (
            len(state.rank) != rank_dimension
            or any(
                isinstance(component, bool)
                or not isinstance(component, int)
                or component < 0
                for component in state.rank
            )
        ):
            raise FilteredObstructionError(
                "invalid_induction_rank",
                "all state ranks must lie in one fixed N^d",
            )
        digest = state.local_certificate_sha256
        if (
            len(digest) != 64
            or any(character not in "0123456789abcdef" for character in digest)
        ):
            raise FilteredObstructionError(
                "invalid_local_certificate_digest",
                f"state {state.name!r} needs a lowercase SHA-256 digest",
            )
        if len(set(state.complete_outcomes)) != len(state.complete_outcomes):
            raise FilteredObstructionError(
                "duplicate_complete_outcome",
                f"state {state.name!r} repeats a complete outcome",
            )

    if not problem.transitions:
        raise FilteredObstructionError(
            "empty_induction_transitions",
            "at least one transition is required",
        )
    transition_names = tuple(
        transition.name for transition in problem.transitions
    )
    if any(not name for name in transition_names):
        raise FilteredObstructionError(
            "empty_induction_transition_name",
            "transition names must be nonempty",
        )
    if len(set(transition_names)) != len(transition_names):
        raise FilteredObstructionError(
            "duplicate_induction_transition_name",
            "transition names must be unique",
        )

    allowed_outcomes = {
        "descend",
        "terminal_survives",
        "source_charged",
        "target_charged",
    }
    outgoing: dict[str, list[FilteredInductionTransition]] = {
        name: [] for name in state_names
    }
    outcome_counts = {outcome: 0 for outcome in allowed_outcomes}
    for transition in problem.transitions:
        if transition.source not in state_by_name:
            raise FilteredObstructionError(
                "unknown_induction_source",
                f"transition {transition.name!r} has an unknown source",
            )
        if transition.outcome not in allowed_outcomes:
            raise FilteredObstructionError(
                "invalid_induction_outcome",
                f"transition {transition.name!r} has invalid outcome "
                f"{transition.outcome!r}",
            )
        outgoing[transition.source].append(transition)
        outcome_counts[transition.outcome] += 1
        if transition.outcome == "descend":
            if transition.target not in state_by_name:
                raise FilteredObstructionError(
                    "unknown_induction_target",
                    f"descent {transition.name!r} needs a known target",
                )
            source_rank = state_by_name[transition.source].rank
            target_rank = state_by_name[transition.target].rank
            if not target_rank < source_rank:
                raise FilteredObstructionError(
                    "nondecreasing_induction_transition",
                    f"descent {transition.name!r} maps rank {source_rank} "
                    f"to {target_rank}",
                )
        elif transition.target is not None:
            raise FilteredObstructionError(
                "closing_transition_has_target",
                f"closing transition {transition.name!r} cannot have a target",
            )

    for state in problem.states:
        declared = tuple(sorted(state.complete_outcomes))
        actual = tuple(sorted(
            transition.name for transition in outgoing[state.name]
        ))
        if not actual:
            raise FilteredObstructionError(
                "induction_dead_end",
                f"state {state.name!r} has no declared local outcome",
            )
        if declared != actual:
            raise FilteredObstructionError(
                "incomplete_local_coverage",
                f"state {state.name!r} binds outcomes {declared}, "
                f"but the transition graph supplies {actual}",
            )

    if not problem.initial_states:
        raise FilteredObstructionError(
            "empty_induction_initial_states",
            "at least one initial state is required",
        )
    if len(set(problem.initial_states)) != len(problem.initial_states):
        raise FilteredObstructionError(
            "duplicate_induction_initial_state",
            "initial states must be unique",
        )
    if any(name not in state_by_name for name in problem.initial_states):
        raise FilteredObstructionError(
            "unknown_induction_initial_state",
            "every initial state must occur in the state table",
        )

    reachable: set[str] = set()
    frontier = list(problem.initial_states)
    while frontier:
        state_name = frontier.pop()
        if state_name in reachable:
            continue
        reachable.add(state_name)
        frontier.extend(
            transition.target
            for transition in outgoing[state_name]
            if transition.outcome == "descend"
            and transition.target is not None
        )
    unreachable = set(state_names) - reachable
    if unreachable:
        raise FilteredObstructionError(
            "unreachable_induction_state",
            "states are outside the initial transition closure: "
            + ", ".join(sorted(unreachable)),
        )

    path_length_cache: dict[str, int] = {}

    def maximum_descent_length(state_name: str) -> int:
        cached = path_length_cache.get(state_name)
        if cached is not None:
            return cached
        lengths = [
            1 + maximum_descent_length(transition.target)
            for transition in outgoing[state_name]
            if transition.outcome == "descend"
            and transition.target is not None
        ]
        result = max(lengths, default=0)
        path_length_cache[state_name] = result
        return result

    maximum_length = max(
        maximum_descent_length(state_name)
        for state_name in problem.initial_states
    )

    graph_payload = {
        "problem": problem.name,
        "states": [
            {
                "name": state.name,
                "rank": list(state.rank),
                "local_certificate_sha256": (
                    state.local_certificate_sha256
                ),
                "complete_outcomes": sorted(state.complete_outcomes),
            }
            for state in problem.states
        ],
        "transitions": [
            {
                "name": transition.name,
                "source": transition.source,
                "outcome": transition.outcome,
                "target": transition.target,
            }
            for transition in problem.transitions
        ],
        "initial_states": list(problem.initial_states),
    }
    graph_sha256 = hashlib.sha256(
        json.dumps(
            graph_payload,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()

    outcome_order = (
        "terminal_survives",
        "source_charged",
        "target_charged",
        "descend",
    )
    return FilteredInductionCertificate(
        schema="ztare.filtered_induction_certificate.v1",
        problem_name=problem.name,
        state_order=state_names,
        transition_order=transition_names,
        initial_states=problem.initial_states,
        rank_dimension=rank_dimension,
        local_coverage_verified=True,
        strict_descent_verified=True,
        all_states_reachable=True,
        branch_outcome_counts=tuple(
            (outcome, outcome_counts[outcome]) for outcome in outcome_order
        ),
        maximum_uncharged_descent_length=maximum_length,
        every_declared_branch_closes=True,
        adapter_completeness_inferred=False,
        state_certificate_sha256=tuple(
            (state.name, state.local_certificate_sha256)
            for state in problem.states
        ),
        transition_graph_sha256=graph_sha256,
    )


def make_filtered_asymptotic_evidence(
    *,
    claim: FilteredAsymptoticClaim,
    subject_id: str,
    induction: FilteredInductionProblem,
    authority: EvidenceAuthority,
    scope: FilteredAsymptoticEvidenceScope,
    evidence_sha256: str,
) -> ContentBoundEvidenceReceipt:
    """Bind an occurrence-support theorem to its compiled induction graph."""

    if not isinstance(claim, FilteredAsymptoticClaim):
        raise FilteredObstructionError(
            "asymptotic_evidence_claim_unknown",
            "the asymptotic evidence claim is not recognized",
        )
    if not isinstance(scope, FilteredAsymptoticEvidenceScope):
        raise FilteredObstructionError(
            "asymptotic_evidence_scope_unknown",
            "the asymptotic evidence scope is not recognized",
        )
    graph_sha256 = compile_filtered_induction(
        induction
    ).transition_graph_sha256
    try:
        return make_content_bound_evidence(
            claim_id=claim.value,
            subject_id=subject_id,
            context_sha256=graph_sha256,
            authority=authority,
            scope_id=scope.value,
            conclusion={
                "cardinality": "infinite",
                "index_cofinality": "unbounded",
            },
            evidence_sha256=evidence_sha256,
        )
    except ContentBoundEvidenceError as error:
        raise FilteredObstructionError(error.code, str(error)) from error


def compile_filtered_asymptotic_induction(
    problem: FilteredAsymptoticInductionProblem,
) -> FilteredAsymptoticInductionCertificate:
    """Compile a filtered induction into an exact limsup rate certificate.

    The mathematical recurrence and the exhaustion of its substrate states
    remain adapter obligations, bound here by SHA-256 receipts.  The reusable
    theorem checked by this function is that an infinite family of distinct
    occurrence orders cannot be canceled below ``threshold`` when every
    bounded-descent endpoint either survives or pays source/target excess at
    that same order with affine slope at least ``threshold``.
    """

    if not problem.name:
        raise FilteredObstructionError(
            "empty_problem_name", "asymptotic problem name must be nonempty"
        )
    induction = compile_filtered_induction(problem.induction)
    threshold = _rational(problem.threshold)
    if threshold < 0:
        raise FilteredObstructionError(
            "negative_rate_threshold", "rate threshold must be nonnegative"
        )

    def validate_integer(value: int, *, label: str) -> int:
        if isinstance(value, bool) or not isinstance(value, int):
            raise FilteredObstructionError(
                "invalid_affine_rate_data", f"{label} must be an integer"
            )
        return value

    occurrence_intercept = validate_integer(
        problem.occurrence_order_intercept,
        label="occurrence order intercept",
    )
    occurrence_slope = validate_integer(
        problem.occurrence_order_slope,
        label="occurrence order slope",
    )
    if occurrence_intercept < 1:
        raise FilteredObstructionError(
            "invalid_occurrence_order",
            "the first occurrence order must be positive",
        )
    if occurrence_slope <= 0:
        raise FilteredObstructionError(
            "noninjective_occurrence_orders",
            "occurrence order slope must be positive",
        )
    def validate_digest(value: str, *, label: str) -> str:
        if (
            not isinstance(value, str)
            or len(value) != 64
            or any(character not in "0123456789abcdef" for character in value)
        ):
            raise FilteredObstructionError(
                "invalid_asymptotic_certificate_digest",
                f"{label} needs a lowercase SHA-256 digest",
            )
        return value

    try:
        support_receipt = replay_content_bound_evidence(
            problem.occurrence_support_evidence
        )
    except ContentBoundEvidenceError as error:
        raise FilteredObstructionError(error.code, str(error)) from error
    if support_receipt.claim_id != (
        FilteredAsymptoticClaim.INFINITE_OCCURRENCE_SUPPORT.value
    ):
        raise FilteredObstructionError(
            "asymptotic_evidence_claim_mismatch",
            "asymptotic induction needs the infinite-support proposition",
        )
    if support_receipt.subject_id != problem.name:
        raise FilteredObstructionError(
            "asymptotic_evidence_subject_mismatch",
            "the support proposition belongs to another asymptotic problem",
        )
    if support_receipt.context_sha256 != induction.transition_graph_sha256:
        raise FilteredObstructionError(
            "asymptotic_evidence_context_mismatch",
            "the support proposition belongs to another induction graph",
        )
    if support_receipt.authority is EvidenceAuthority.FINITE_EXPERIMENT:
        raise FilteredObstructionError(
            "asymptotic_evidence_authority_insufficient",
            "finite experiment authority cannot discharge infinite support",
        )
    required_scope = (
        FilteredAsymptoticEvidenceScope.ALL_UNBOUNDED_OCCURRENCE_INDICES
    )
    if support_receipt.scope_id != required_scope.value:
        raise FilteredObstructionError(
            "asymptotic_evidence_scope_mismatch",
            "the support proposition must cover all unbounded indices",
        )
    if support_receipt.conclusion() != {
        "cardinality": "infinite",
        "index_cofinality": "unbounded",
    }:
        raise FilteredObstructionError(
            "asymptotic_evidence_conclusion_malformed",
            "the support proposition must conclude infinite cofinal support",
        )
    support_digest = validate_digest(
        support_receipt.evidence_sha256,
        label="occurrence support",
    )

    transition_by_name = {
        transition.name: transition
        for transition in problem.induction.transitions
    }
    closing_names = tuple(
        transition.name
        for transition in problem.induction.transitions
        if transition.outcome != "descend"
    )
    witness_names = tuple(
        witness.transition_name for witness in problem.closing_witnesses
    )
    if any(not name for name in witness_names):
        raise FilteredObstructionError(
            "empty_rate_witness_name",
            "rate witness transition names must be nonempty",
        )
    if len(set(witness_names)) != len(witness_names):
        raise FilteredObstructionError(
            "duplicate_rate_witness",
            "each closing transition needs exactly one rate witness",
        )
    unknown = set(witness_names) - set(transition_by_name)
    if unknown:
        raise FilteredObstructionError(
            "unknown_rate_witness_transition",
            "rate witnesses refer to unknown transitions: "
            + ", ".join(sorted(unknown)),
        )
    descent_witnesses = {
        name
        for name in witness_names
        if transition_by_name[name].outcome == "descend"
    }
    if descent_witnesses:
        raise FilteredObstructionError(
            "rate_witness_on_descent",
            "uncharged descents cannot carry rate witnesses: "
            + ", ".join(sorted(descent_witnesses)),
        )
    missing = set(closing_names) - set(witness_names)
    if missing:
        raise FilteredObstructionError(
            "missing_closing_rate_witness",
            "closing transitions lack rate witnesses: "
            + ", ".join(sorted(missing)),
        )

    allowed_sides = {"source", "target"}
    rates: list[sp.Rational] = []
    rate_rows: list[tuple[str, str]] = []
    side_rows: list[tuple[str, str]] = []
    witness_payload = []
    for witness in problem.closing_witnesses:
        transition = transition_by_name[witness.transition_name]
        if witness.side not in allowed_sides:
            raise FilteredObstructionError(
                "invalid_rate_witness_side",
                f"witness {witness.transition_name!r} has side "
                f"{witness.side!r}",
            )
        required_side = {
            "source_charged": "source",
            "target_charged": "target",
        }.get(transition.outcome)
        if required_side is not None and witness.side != required_side:
            raise FilteredObstructionError(
                "charged_side_mismatch",
                f"transition {witness.transition_name!r} requires "
                f"{required_side!r} payment",
            )

        payment_intercept = validate_integer(
            witness.payment_order_intercept,
            label=f"{witness.transition_name} payment order intercept",
        )
        payment_slope = validate_integer(
            witness.payment_order_slope,
            label=f"{witness.transition_name} payment order slope",
        )
        excess_intercept = validate_integer(
            witness.payment_excess_intercept,
            label=f"{witness.transition_name} excess intercept",
        )
        excess_slope = validate_integer(
            witness.payment_excess_slope,
            label=f"{witness.transition_name} excess slope",
        )
        if (
            payment_intercept != occurrence_intercept
            or payment_slope != occurrence_slope
        ):
            raise FilteredObstructionError(
                "payment_not_at_occurrence_order",
                f"transition {witness.transition_name!r} pays at "
                f"{payment_intercept}+{payment_slope}k instead of "
                f"{occurrence_intercept}+{occurrence_slope}k",
            )
        if excess_slope < 0:
            raise FilteredObstructionError(
                "negative_payment_slope",
                f"transition {witness.transition_name!r} has decreasing "
                "excess lower bound",
            )
        rate = sp.Rational(excess_slope, occurrence_slope)
        if rate < threshold:
            raise FilteredObstructionError(
                "subcritical_closing_branch",
                f"transition {witness.transition_name!r} has rate {rate}, "
                f"below threshold {threshold}",
            )
        coefficient_digest = validate_digest(
            witness.coefficient_certificate_sha256,
            label=f"transition {witness.transition_name} coefficient",
        )
        rates.append(rate)
        rate_rows.append((witness.transition_name, str(rate)))
        side_rows.append((witness.transition_name, witness.side))
        witness_payload.append({
            "transition": witness.transition_name,
            "outcome": transition.outcome,
            "side": witness.side,
            "payment_order": [payment_intercept, payment_slope],
            "payment_excess_lower_bound": [
                excess_intercept,
                excess_slope,
            ],
            "rate": str(rate),
            "coefficient_certificate_sha256": coefficient_digest,
        })

    if not rates:
        raise FilteredObstructionError(
            "empty_rate_witnesses",
            "at least one closing rate witness is required",
        )
    minimum_rate = min(rates)
    payload = {
        "problem": problem.name,
        "induction_transition_graph_sha256": (
            induction.transition_graph_sha256
        ),
        "threshold": str(threshold),
        "occurrence_order": [occurrence_intercept, occurrence_slope],
        "occurrence_support_certificate_sha256": support_digest,
        "witnesses": witness_payload,
    }
    certificate_sha256 = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    proof_envelope_sha256 = content_sha256({
        "schema": "ztare.filtered_asymptotic_induction_proof.v1",
        "problem": problem.name,
        "induction_transition_graph_sha256": (
            induction.transition_graph_sha256
        ),
        "occurrence_support_receipt_sha256": (
            support_receipt.receipt_sha256
        ),
        "semantic_certificate_sha256": certificate_sha256,
    })
    return FilteredAsymptoticInductionCertificate(
        schema="ztare.filtered_asymptotic_induction_certificate.v2",
        problem_name=problem.name,
        induction_problem_name=problem.induction.name,
        threshold=str(threshold),
        occurrence_order_intercept=occurrence_intercept,
        occurrence_order_slope=occurrence_slope,
        occurrence_support_infinite=True,
        occurrence_support_certificate_sha256=support_digest,
        occurrence_support_receipt_sha256=(
            support_receipt.receipt_sha256
        ),
        maximum_uncharged_descent_length=(
            induction.maximum_uncharged_descent_length
        ),
        closing_transition_order=closing_names,
        rate_by_transition=tuple(rate_rows),
        side_by_transition=tuple(side_rows),
        minimum_certified_rate=str(minimum_rate),
        every_closing_branch_rate_certified=True,
        same_order_payment_verified=True,
        no_rebilling_verified=True,
        parameter_shift_invariance_verified=True,
        adapter_completeness_inferred=False,
        induction_transition_graph_sha256=(
            induction.transition_graph_sha256
        ),
        asymptotic_certificate_sha256=certificate_sha256,
        asymptotic_proof_envelope_sha256=proof_envelope_sha256,
    )


def _filtered_puiseux_context_core(
    context: FilteredPuiseuxContext,
) -> dict[str, object]:
    return {
        "schema": context.schema,
        "germ_id": context.germ_id,
        "local_coordinate_id": context.local_coordinate_id,
        "first_fractional_exponent": context.first_fractional_exponent,
        "local_expansion_evidence_sha256": (
            context.local_expansion_evidence_sha256
        ),
    }


def _replay_filtered_puiseux_context(
    context: FilteredPuiseuxContext,
) -> FilteredPuiseuxContext:
    if context.schema != FILTERED_PUISEUX_CONTEXT_SCHEMA:
        raise FilteredObstructionError(
            "puiseux_context_schema_mismatch",
            "the Puiseux context schema is not recognized",
        )
    if (
        not isinstance(context.germ_id, str)
        or not context.germ_id.strip()
        or not isinstance(context.local_coordinate_id, str)
        or not context.local_coordinate_id.strip()
    ):
        raise FilteredObstructionError(
            "puiseux_context_identity_empty",
            "the germ and local coordinate identities must be nonempty",
        )
    exponent = _rational(context.first_fractional_exponent)
    if str(exponent) != context.first_fractional_exponent:
        raise FilteredObstructionError(
            "puiseux_context_exponent_not_canonical",
            "the first fractional exponent must use canonical rational text",
        )
    try:
        require_sha256_digest(
            context.local_expansion_evidence_sha256,
            context="Puiseux local expansion",
        )
        require_sha256_digest(
            context.context_sha256,
            context="Puiseux context",
        )
    except ValueError as error:
        raise FilteredObstructionError(
            "invalid_puiseux_context_digest",
            str(error),
        ) from error
    expected = content_sha256(_filtered_puiseux_context_core(context))
    if context.context_sha256 != expected:
        raise FilteredObstructionError(
            "puiseux_context_digest_mismatch",
            "the Puiseux context content does not replay",
        )
    return context


def make_filtered_puiseux_context(
    *,
    germ_id: str,
    local_coordinate_id: str,
    first_fractional_exponent: RationalInput,
    local_expansion_evidence_sha256: str,
) -> FilteredPuiseuxContext:
    """Create one replayable local-germ identity for flow obstructions."""

    provisional = FilteredPuiseuxContext(
        schema=FILTERED_PUISEUX_CONTEXT_SCHEMA,
        germ_id=germ_id,
        local_coordinate_id=local_coordinate_id,
        first_fractional_exponent=str(
            _rational(first_fractional_exponent)
        ),
        local_expansion_evidence_sha256=(
            local_expansion_evidence_sha256
        ),
        context_sha256="0" * 64,
    )
    context = replace(
        provisional,
        context_sha256=content_sha256(
            _filtered_puiseux_context_core(provisional)
        ),
    )
    return _replay_filtered_puiseux_context(context)


def _filtered_puiseux_claim_conclusion(
    claim: FilteredPuiseuxClaim,
    context: FilteredPuiseuxContext,
) -> dict[str, str]:
    if claim is FilteredPuiseuxClaim.REGULAR_LINEAR_COEFFICIENT_NONZERO:
        return {"coefficient_status": "nonzero"}
    if claim is (
        FilteredPuiseuxClaim.FIRST_FRACTIONAL_COEFFICIENT_NONZERO
    ):
        return {
            "coefficient_status": "nonzero",
            "first_fractional_exponent": (
                context.first_fractional_exponent
            ),
        }
    if claim is FilteredPuiseuxClaim.JULIA_FLOW_IDENTITY:
        return {
            "identity": "f(F)=F_prime*f",
            "flow_endpoint": "F=exp(fD)(x)",
        }
    if claim is FilteredPuiseuxClaim.TWO_FLOW_FACTORIZATION_IDENTITY:
        return {"identity": "F=exp(gD)_after_exp(fD)"}
    raise FilteredObstructionError(
        "puiseux_evidence_claim_unknown",
        "the Puiseux evidence claim is not recognized",
    )


def make_filtered_puiseux_evidence(
    *,
    claim: FilteredPuiseuxClaim,
    context: FilteredPuiseuxContext,
    authority: EvidenceAuthority,
    scope: FilteredPuiseuxEvidenceScope,
    evidence_sha256: str,
) -> ContentBoundEvidenceReceipt:
    """Bind one exact local-germ proposition to a Puiseux context."""

    _replay_filtered_puiseux_context(context)
    if not isinstance(claim, FilteredPuiseuxClaim):
        raise FilteredObstructionError(
            "puiseux_evidence_claim_unknown",
            "the Puiseux evidence claim is not recognized",
        )
    if not isinstance(scope, FilteredPuiseuxEvidenceScope):
        raise FilteredObstructionError(
            "puiseux_evidence_scope_unknown",
            "the Puiseux evidence scope is not recognized",
        )
    try:
        return make_content_bound_evidence(
            claim_id=claim.value,
            subject_id=context.germ_id,
            context_sha256=context.context_sha256,
            authority=authority,
            scope_id=scope.value,
            conclusion=_filtered_puiseux_claim_conclusion(claim, context),
            evidence_sha256=evidence_sha256,
        )
    except ContentBoundEvidenceError as error:
        raise FilteredObstructionError(error.code, str(error)) from error


def _filtered_density_clock_claim_conclusion(
    claim: FilteredDensityClockClaim,
) -> dict[str, str]:
    if claim is FilteredDensityClockClaim.GROUP_MODULE_POLYNOMIALITY:
        return {
            "coordinate": "L",
            "coordinate_level": "semidirect_group_module",
            "polynomiality": "finite_polynomial",
            "not_inferred_from": "finite_lie_module_support",
        }
    if claim is FilteredDensityClockClaim.CLOCK_FACTORIZATION_IDENTITY:
        return {
            "identity": "phi_K=phi_L_after_polynomial_flow_endpoint",
            "squared_density_identity": (
                "K^2*h^2*(h_prime)^3=x^2*L(h)^2"
            ),
            "density_weight": "3/2",
            "residual_valuation": "1",
        }
    if claim is FilteredDensityClockClaim.SELECTED_ENDPOINT_TRICHOTOMY:
        return {
            "endpoint_partition": (
                "regular_finite|nonzero_polynomial_root|infinity"
            )
        }
    if claim is FilteredDensityClockClaim.LOCAL_ENDPOINT_PUISEUX_LATTICES:
        return {
            "regular_finite": "inverse_clock_preserves_first_5/2_term",
            "simple_nonzero_root": (
                "cubic_inverse_with_nonzero_relative_3/2_term"
            ),
            "infinity": (
                "flow_lattice_generated_by_1/(degree-1)_with_"
                "nonzero_relative_3/2_term"
            ),
        }
    raise FilteredObstructionError(
        "density_clock_claim_unknown",
        "the density-clock evidence claim is not recognized",
    )


def make_filtered_density_clock_evidence(
    *,
    claim: FilteredDensityClockClaim,
    context: FilteredPuiseuxContext,
    authority: EvidenceAuthority,
    scope: FilteredDensityClockEvidenceScope,
    evidence_sha256: str,
) -> ContentBoundEvidenceReceipt:
    """Bind one clock-factorization proposition to its fractional germ."""

    _replay_filtered_puiseux_context(context)
    if not isinstance(claim, FilteredDensityClockClaim):
        raise FilteredObstructionError(
            "density_clock_claim_unknown",
            "the density-clock evidence claim is not recognized",
        )
    if not isinstance(scope, FilteredDensityClockEvidenceScope):
        raise FilteredObstructionError(
            "density_clock_evidence_scope_unknown",
            "the density-clock evidence scope is not recognized",
        )
    try:
        return make_content_bound_evidence(
            claim_id=claim.value,
            subject_id=context.germ_id,
            context_sha256=context.context_sha256,
            authority=authority,
            scope_id=scope.value,
            conclusion=_filtered_density_clock_claim_conclusion(claim),
            evidence_sha256=evidence_sha256,
        )
    except ContentBoundEvidenceError as error:
        raise FilteredObstructionError(error.code, str(error)) from error


def _validated_density_clock_evidence(
    *,
    context: FilteredPuiseuxContext,
    evidence: tuple[ContentBoundEvidenceReceipt, ...],
    required_claims: tuple[FilteredDensityClockClaim, ...] | None = None,
) -> dict[FilteredDensityClockClaim, ContentBoundEvidenceReceipt]:
    required = (
        tuple(FilteredDensityClockClaim)
        if required_claims is None
        else required_claims
    )
    if len(evidence) != len(required):
        raise FilteredObstructionError(
            "density_clock_evidence_claim_set_incomplete",
            "the density-clock compiler needs its exact structural propositions",
        )
    receipts: dict[
        FilteredDensityClockClaim, ContentBoundEvidenceReceipt
    ] = {}
    expected_scope = {
        FilteredDensityClockClaim.GROUP_MODULE_POLYNOMIALITY: (
            FilteredDensityClockEvidenceScope.EXACT_SEMIDIRECT_EXPONENTIAL_POLYNOMIALITY
        ),
        FilteredDensityClockClaim.CLOCK_FACTORIZATION_IDENTITY: (
            FilteredDensityClockEvidenceScope.EXACT_FORMAL_CLOCK_FACTORIZATION
        ),
        FilteredDensityClockClaim.SELECTED_ENDPOINT_TRICHOTOMY: (
            FilteredDensityClockEvidenceScope.SELECTED_ANALYTIC_BRANCH_EXHAUSTIVE
        ),
        FilteredDensityClockClaim.LOCAL_ENDPOINT_PUISEUX_LATTICES: (
            FilteredDensityClockEvidenceScope.ALL_POLYNOMIAL_ROOT_AND_INFINITY_CHARTS
        ),
    }
    for carried in evidence:
        try:
            receipt = replay_content_bound_evidence(carried)
            claim = FilteredDensityClockClaim(receipt.claim_id)
        except (ContentBoundEvidenceError, ValueError) as error:
            code = getattr(error, "code", "density_clock_claim_unknown")
            raise FilteredObstructionError(code, str(error)) from error
        if claim in receipts:
            raise FilteredObstructionError(
                "density_clock_evidence_claim_duplicate",
                f"density-clock claim {claim.value!r} occurs more than once",
            )
        if receipt.subject_id != context.germ_id:
            raise FilteredObstructionError(
                "density_clock_evidence_subject_mismatch",
                "the density-clock proposition belongs to another germ",
            )
        if receipt.context_sha256 != context.context_sha256:
            raise FilteredObstructionError(
                "density_clock_evidence_context_mismatch",
                "the density-clock proposition belongs to another context",
            )
        if receipt.authority is EvidenceAuthority.FINITE_EXPERIMENT:
            raise FilteredObstructionError(
                "density_clock_evidence_authority_insufficient",
                "finite experiments cannot discharge a clock orbit theorem",
            )
        if receipt.scope_id != expected_scope[claim].value:
            raise FilteredObstructionError(
                "density_clock_evidence_scope_mismatch",
                f"density-clock claim {claim.value!r} has the wrong scope",
            )
        if receipt.conclusion() != _filtered_density_clock_claim_conclusion(
            claim
        ):
            raise FilteredObstructionError(
                "density_clock_evidence_conclusion_malformed",
                f"density-clock claim {claim.value!r} has the wrong conclusion",
            )
        receipts[claim] = receipt
    if set(receipts) != set(required):
        raise FilteredObstructionError(
            "density_clock_evidence_claim_set_incomplete",
            "density-clock evidence does not cover its exact claim set",
        )
    return receipts


def _filtered_algebraic_continuation_claim_conclusion(
    claim: FilteredAlgebraicContinuationClaim,
) -> dict[str, str]:
    if claim is (
        FilteredAlgebraicContinuationClaim.CRITICAL_SQUARE_OUTSIDE_BASE_FIELD
    ):
        return {
            "element": "K^2",
            "base_field": "rational_source_function_field",
            "first_nonbase_exponent": "3/2",
            "coefficient_status": "nonzero",
        }
    if claim is (
        FilteredAlgebraicContinuationClaim.ALGEBRAIC_PLACE_PUISEUX_EXTENSION
    ):
        return {
            "theorem": (
                "selected_place_extends_to_every_finite_algebraic_"
                "function_field_extension"
            ),
            "endpoint": "finite_or_infinity_puiseux_chart",
        }
    raise FilteredObstructionError(
        "algebraic_continuation_claim_unknown",
        "the algebraic-continuation evidence claim is not recognized",
    )


def make_filtered_algebraic_continuation_evidence(
    *,
    claim: FilteredAlgebraicContinuationClaim,
    context: FilteredPuiseuxContext,
    authority: EvidenceAuthority,
    scope: FilteredAlgebraicContinuationEvidenceScope,
    evidence_sha256: str,
) -> ContentBoundEvidenceReceipt:
    """Bind one exact algebraic-continuation proposition to a germ."""

    _replay_filtered_puiseux_context(context)
    if not isinstance(claim, FilteredAlgebraicContinuationClaim):
        raise FilteredObstructionError(
            "algebraic_continuation_claim_unknown",
            "the algebraic-continuation claim is not recognized",
        )
    if not isinstance(scope, FilteredAlgebraicContinuationEvidenceScope):
        raise FilteredObstructionError(
            "algebraic_continuation_evidence_scope_unknown",
            "the algebraic-continuation scope is not recognized",
        )
    try:
        return make_content_bound_evidence(
            claim_id=claim.value,
            subject_id=context.germ_id,
            context_sha256=context.context_sha256,
            authority=authority,
            scope_id=scope.value,
            conclusion=_filtered_algebraic_continuation_claim_conclusion(
                claim
            ),
            evidence_sha256=evidence_sha256,
        )
    except ContentBoundEvidenceError as error:
        raise FilteredObstructionError(error.code, str(error)) from error


def _validated_algebraic_continuation_evidence(
    *,
    context: FilteredPuiseuxContext,
    evidence: tuple[ContentBoundEvidenceReceipt, ...],
) -> dict[
    FilteredAlgebraicContinuationClaim,
    ContentBoundEvidenceReceipt,
]:
    required = tuple(FilteredAlgebraicContinuationClaim)
    if len(evidence) != len(required):
        raise FilteredObstructionError(
            "algebraic_continuation_evidence_claim_set_incomplete",
            "the algebraic-continuation compiler needs both propositions",
        )
    expected_scope = {
        FilteredAlgebraicContinuationClaim.CRITICAL_SQUARE_OUTSIDE_BASE_FIELD: (
            FilteredAlgebraicContinuationEvidenceScope.EXACT_CRITICAL_FUNCTION_FIELD
        ),
        FilteredAlgebraicContinuationClaim.ALGEBRAIC_PLACE_PUISEUX_EXTENSION: (
            FilteredAlgebraicContinuationEvidenceScope.ALL_FINITE_ALGEBRAIC_EXTENSIONS_AT_SELECTED_PLACE
        ),
    }
    receipts: dict[
        FilteredAlgebraicContinuationClaim,
        ContentBoundEvidenceReceipt,
    ] = {}
    for carried in evidence:
        try:
            receipt = replay_content_bound_evidence(carried)
            claim = FilteredAlgebraicContinuationClaim(receipt.claim_id)
        except (ContentBoundEvidenceError, ValueError) as error:
            code = getattr(
                error,
                "code",
                "algebraic_continuation_claim_unknown",
            )
            raise FilteredObstructionError(code, str(error)) from error
        if claim in receipts:
            raise FilteredObstructionError(
                "algebraic_continuation_evidence_claim_duplicate",
                f"algebraic-continuation claim {claim.value!r} is duplicated",
            )
        if receipt.subject_id != context.germ_id:
            raise FilteredObstructionError(
                "algebraic_continuation_evidence_subject_mismatch",
                "the algebraic-continuation proposition belongs to another germ",
            )
        if receipt.context_sha256 != context.context_sha256:
            raise FilteredObstructionError(
                "algebraic_continuation_evidence_context_mismatch",
                "the algebraic-continuation proposition has another context",
            )
        if receipt.authority is EvidenceAuthority.FINITE_EXPERIMENT:
            raise FilteredObstructionError(
                "algebraic_continuation_evidence_authority_insufficient",
                "finite experiments cannot certify algebraic continuation",
            )
        if receipt.scope_id != expected_scope[claim].value:
            raise FilteredObstructionError(
                "algebraic_continuation_evidence_scope_mismatch",
                f"algebraic-continuation claim {claim.value!r} has the wrong scope",
            )
        if receipt.conclusion() != (
            _filtered_algebraic_continuation_claim_conclusion(claim)
        ):
            raise FilteredObstructionError(
                "algebraic_continuation_evidence_conclusion_malformed",
                f"algebraic-continuation claim {claim.value!r} is malformed",
            )
        receipts[claim] = receipt
    if set(receipts) != set(required):
        raise FilteredObstructionError(
            "algebraic_continuation_evidence_claim_set_incomplete",
            "algebraic-continuation evidence does not cover both claims",
        )
    return receipts


def _validated_puiseux_evidence(
    *,
    context: FilteredPuiseuxContext,
    evidence: tuple[ContentBoundEvidenceReceipt, ...],
    required_claims: tuple[FilteredPuiseuxClaim, ...],
) -> dict[FilteredPuiseuxClaim, ContentBoundEvidenceReceipt]:
    if len(evidence) != len(required_claims):
        raise FilteredObstructionError(
            "puiseux_evidence_claim_set_incomplete",
            "the Puiseux compiler needs exactly its required propositions",
        )
    receipts: dict[
        FilteredPuiseuxClaim,
        ContentBoundEvidenceReceipt,
    ] = {}
    for carried in evidence:
        try:
            receipt = replay_content_bound_evidence(carried)
        except ContentBoundEvidenceError as error:
            raise FilteredObstructionError(error.code, str(error)) from error
        try:
            claim = FilteredPuiseuxClaim(receipt.claim_id)
        except ValueError as error:
            raise FilteredObstructionError(
                "puiseux_evidence_claim_unknown",
                f"unknown Puiseux evidence claim {receipt.claim_id!r}",
            ) from error
        if claim in receipts:
            raise FilteredObstructionError(
                "puiseux_evidence_claim_duplicate",
                f"Puiseux claim {claim.value!r} occurs more than once",
            )
        if receipt.subject_id != context.germ_id:
            raise FilteredObstructionError(
                "puiseux_evidence_subject_mismatch",
                "the Puiseux proposition belongs to another germ",
            )
        if receipt.context_sha256 != context.context_sha256:
            raise FilteredObstructionError(
                "puiseux_evidence_context_mismatch",
                "the Puiseux proposition belongs to another context",
            )
        if receipt.authority is EvidenceAuthority.FINITE_EXPERIMENT:
            raise FilteredObstructionError(
                "puiseux_evidence_authority_insufficient",
                "finite experiment authority cannot discharge a germ theorem",
            )
        receipts[claim] = receipt
    if set(receipts) != set(required_claims):
        raise FilteredObstructionError(
            "puiseux_evidence_claim_set_incomplete",
            "Puiseux evidence does not cover the exact required claim set",
        )
    coefficient_claims = {
        FilteredPuiseuxClaim.REGULAR_LINEAR_COEFFICIENT_NONZERO,
        FilteredPuiseuxClaim.FIRST_FRACTIONAL_COEFFICIENT_NONZERO,
    }
    for claim in required_claims:
        receipt = receipts[claim]
        expected_scope = (
            FilteredPuiseuxEvidenceScope.EXACT_FIRST_FRACTIONAL_GERM
            if claim in coefficient_claims
            else FilteredPuiseuxEvidenceScope.EXACT_FORMAL_FLOW_IDENTITY
        )
        if receipt.scope_id != expected_scope.value:
            raise FilteredObstructionError(
                "puiseux_evidence_scope_mismatch",
                f"Puiseux claim {claim.value!r} has scope "
                f"{receipt.scope_id!r}, expected {expected_scope.value!r}",
            )
        if receipt.conclusion() != _filtered_puiseux_claim_conclusion(
            claim,
            context,
        ):
            raise FilteredObstructionError(
                "puiseux_evidence_conclusion_malformed",
                f"Puiseux claim {claim.value!r} has the wrong conclusion",
            )
        if (
            claim in coefficient_claims
            and receipt.evidence_sha256
            != context.local_expansion_evidence_sha256
        ):
            raise FilteredObstructionError(
                "puiseux_coefficient_expansion_mismatch",
                "coefficient propositions must be owned by the context expansion",
            )
    return receipts


def compile_filtered_puiseux_flow_obstruction(
    problem: FilteredPuiseuxFlowProblem,
) -> FilteredPuiseuxFlowCertificate:
    """Exclude a polynomial flow generator from a fractional holonomy germ.

    For a regular germ whose first fractional exponent is lambda, Julia's
    equation gives an exhaustive dichotomy for a declared time-one flow
    endpoint.  The zero generator is excluded because its time-one map is
    the identity, whereas the germ has a nonzero fractional coefficient.
    If a nonzero generator does not vanish at the base point,
    differentiation exposes lambda-1 one order before composition can
    expose lambda.  If it does vanish, valuation matching gives equal
    integer multiplicities at the base and image points, while the first
    fractional coefficient forces that multiplicity to equal lambda.  A
    nonintegral lambda excludes both branches.
    """

    if not problem.name:
        raise FilteredObstructionError(
            "empty_problem_name",
            "Puiseux flow problem name must be nonempty",
        )
    context = _replay_filtered_puiseux_context(problem.context)
    exponent = _rational(context.first_fractional_exponent)
    if exponent <= 1:
        raise FilteredObstructionError(
            "nonregular_puiseux_exponent",
            "the first fractional exponent must be greater than one",
        )
    if exponent.q == 1:
        raise FilteredObstructionError(
            "integer_puiseux_exponent",
            "an integral exponent supplies no fractional-flow obstruction",
        )
    required_claims = (
        FilteredPuiseuxClaim.REGULAR_LINEAR_COEFFICIENT_NONZERO,
        FilteredPuiseuxClaim.FIRST_FRACTIONAL_COEFFICIENT_NONZERO,
        FilteredPuiseuxClaim.JULIA_FLOW_IDENTITY,
    )
    receipts = _validated_puiseux_evidence(
        context=context,
        evidence=problem.evidence,
        required_claims=required_claims,
    )
    digest = context.local_expansion_evidence_sha256

    derivative_exponent = exponent - 1
    payload = {
        "problem": problem.name,
        "first_fractional_exponent": str(exponent),
        "derivative_fractional_exponent": str(derivative_exponent),
        "regular_linear_coefficient_nonzero": True,
        "fractional_coefficient_nonzero": True,
        "julia_equation_applies": True,
        "time_one_realization_applies": True,
        "zero_generator_excluded_by_nonidentity_germ": True,
        "local_expansion_certificate_sha256": digest,
        "forced_root_multiplicity": str(exponent),
    }
    certificate_sha256 = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    receipt_rows = tuple(
        (claim.value, receipts[claim].receipt_sha256)
        for claim in required_claims
    )
    proof_contract_sha256 = content_sha256({
        "schema": "ztare.filtered_puiseux_flow_proof.v1",
        "context_sha256": context.context_sha256,
        "evidence_receipt_sha256": receipt_rows,
        "semantic_certificate_sha256": certificate_sha256,
    })
    return FilteredPuiseuxFlowCertificate(
        schema="ztare.filtered_puiseux_flow_certificate.v3",
        problem_name=problem.name,
        first_fractional_exponent=str(exponent),
        derivative_fractional_exponent=str(derivative_exponent),
        regular_linear_coefficient_nonzero=True,
        fractional_coefficient_nonzero=True,
        julia_equation_verified_by_adapter=True,
        time_one_realization_verified_by_adapter=True,
        zero_generator_excluded_by_nonidentity_germ=True,
        nonroot_exponent_mismatch=True,
        forced_root_multiplicity=str(exponent),
        forced_root_multiplicity_is_noninteger=True,
        polynomial_generator_excluded=True,
        adapter_completeness_inferred=False,
        local_expansion_certificate_sha256=digest,
        puiseux_flow_certificate_sha256=certificate_sha256,
        evidence_receipt_sha256=receipt_rows,
        proof_contract_sha256=proof_contract_sha256,
    )


def compile_filtered_density_clock_orbit_obstruction(
    problem: FilteredDensityClockOrbitProblem,
) -> FilteredDensityClockOrbitCertificate:
    """Exclude a finite polynomial weight-3/2 density-clock orbit.

    The adapter separately certifies that ``L`` is a polynomial coordinate
    in the semidirect *group*, rather than merely a polynomial Lie-module
    logarithm.  The selected endpoint is regular finite, a nonzero root of
    that polynomial residual, or infinity.  The regular case is the ordinary
    Puiseux/Julia contradiction.  A finite clock at a root forces that root
    to be simple; inversion is cubic and the ``5/2`` germ forces generator
    multiplicity ``3/2``.  At infinity, leading balance forces
    ``2*e=3*d+2``.  Thus ``d`` is even, so the nonzero ``3/2`` correction is
    outside the ``1/(d-1)`` exponent lattice and cannot satisfy Julia's
    equation.

    The compiler does not construct the selected continuation.  It requires
    that proposition as separately scoped content-bound evidence.
    """

    if not problem.name:
        raise FilteredObstructionError(
            "empty_problem_name",
            "density-clock orbit problem name must be nonempty",
        )
    context = _replay_filtered_puiseux_context(problem.context)
    exponent = _rational(context.first_fractional_exponent)
    if exponent != sp.Rational(5, 2):
        raise FilteredObstructionError(
            "unsupported_density_clock_fractional_exponent",
            "the compiled weight-3/2 clock theorem requires exponent 5/2",
        )
    puiseux_claim_ids = {
        FilteredPuiseuxClaim.REGULAR_LINEAR_COEFFICIENT_NONZERO.value,
        FilteredPuiseuxClaim.FIRST_FRACTIONAL_COEFFICIENT_NONZERO.value,
        FilteredPuiseuxClaim.JULIA_FLOW_IDENTITY.value,
    }
    clock_claim_ids = {claim.value for claim in FilteredDensityClockClaim}
    if len(problem.evidence) != len(puiseux_claim_ids | clock_claim_ids):
        raise FilteredObstructionError(
            "density_clock_orbit_evidence_claim_set_incomplete",
            "the density-clock orbit theorem has an incomplete claim set",
        )
    puiseux_evidence = tuple(
        receipt for receipt in problem.evidence
        if receipt.claim_id in puiseux_claim_ids
    )
    clock_evidence = tuple(
        receipt for receipt in problem.evidence
        if receipt.claim_id in clock_claim_ids
    )
    regular_certificate = compile_filtered_puiseux_flow_obstruction(
        FilteredPuiseuxFlowProblem(
            name=f"{problem.name}.regular_finite",
            context=context,
            evidence=puiseux_evidence,
        )
    )
    clock_receipts = _validated_density_clock_evidence(
        context=context,
        evidence=clock_evidence,
    )

    fractional_increment = exponent - 1
    simple_root_inverse_order = 3
    simple_root_forced_multiplicity = (
        1 + fractional_increment / simple_root_inverse_order
    )
    if simple_root_forced_multiplicity.q == 1:
        raise FilteredObstructionError(
            "density_clock_simple_root_not_excluded",
            "the simple-root Julia balance has integral multiplicity",
        )

    # At infinity the leading clock exponent is -(2*e-5)/3.  Matching a
    # nonzero linear source coordinate and Julia's leading order gives
    # 2*e=3*d+2.  Integral e then makes d even, hence d-1 odd.  The branch
    # increment 3/2 cannot be an integer multiple of 1/(d-1).
    infinity_degree_relation = "2*e=3*d+2"
    infinity_generator_degree_even = True
    infinity_fractional_increment_outside_lattice = True

    receipt_rows = tuple(sorted(
        (
            receipt.claim_id,
            receipt.receipt_sha256,
        )
        for receipt in problem.evidence
    ))
    payload = {
        "problem": problem.name,
        "context_sha256": context.context_sha256,
        "first_fractional_exponent": str(exponent),
        "fractional_increment": str(fractional_increment),
        "density_weight": "3/2",
        "residual_valuation": 1,
        "group_module_polynomiality_receipt_sha256": clock_receipts[
            FilteredDensityClockClaim.GROUP_MODULE_POLYNOMIALITY
        ].receipt_sha256,
        "regular_puiseux_certificate_sha256": (
            regular_certificate.puiseux_flow_certificate_sha256
        ),
        "simple_root_inverse_order": simple_root_inverse_order,
        "simple_root_forced_generator_multiplicity": str(
            simple_root_forced_multiplicity
        ),
        "infinity_degree_relation": infinity_degree_relation,
        "evidence_receipt_sha256": receipt_rows,
    }
    certificate_sha256 = content_sha256(payload)
    proof_contract_sha256 = content_sha256({
        "schema": "ztare.filtered_density_clock_orbit_proof.v1",
        "context_sha256": context.context_sha256,
        "evidence_receipt_sha256": receipt_rows,
        "semantic_certificate_sha256": certificate_sha256,
    })
    return FilteredDensityClockOrbitCertificate(
        schema="ztare.filtered_density_clock_orbit_certificate.v1",
        problem_name=problem.name,
        first_fractional_exponent=str(exponent),
        fractional_increment=str(fractional_increment),
        density_weight="3/2",
        residual_valuation=1,
        group_module_polynomiality_verified_by_adapter=True,
        regular_finite_case_excluded=(
            regular_certificate.polynomial_generator_excluded
        ),
        multiple_nonzero_root_clock_diverges=True,
        simple_root_inverse_order=simple_root_inverse_order,
        simple_root_forced_generator_multiplicity=str(
            simple_root_forced_multiplicity
        ),
        simple_root_case_excluded=True,
        infinity_clock_finite_minimum_residual_degree=3,
        infinity_degree_relation=infinity_degree_relation,
        infinity_generator_degree_even=infinity_generator_degree_even,
        infinity_fractional_increment_outside_lattice=(
            infinity_fractional_increment_outside_lattice
        ),
        infinity_case_excluded=True,
        selected_polynomial_orbit_excluded=True,
        adapter_completeness_inferred=False,
        context_sha256=context.context_sha256,
        evidence_receipt_sha256=receipt_rows,
        density_clock_orbit_certificate_sha256=certificate_sha256,
        proof_contract_sha256=proof_contract_sha256,
    )


def compile_filtered_algebraic_clock_continuation(
    problem: FilteredAlgebraicClockContinuationProblem,
) -> FilteredAlgebraicClockContinuationCertificate:
    """Turn an exact polynomial density orbit into endpoint coverage.

    The weight-`3/2` orbit and time-one Julia equations imply the separated
    eliminant

        K^2 * Y^2 * f(Y)^3 - x^2 * f(x)^3 * L(Y)^2.

    The zero-generator case would make the endpoint the identity and force
    the critical residual square into the rational base field.  Otherwise
    ``Y^2*f(Y)^3`` is nonzero.  If the displayed eliminant vanished as a
    polynomial in ``Y``, leading-coefficient comparison would again put
    ``K^2`` in the base field.  Hence the endpoint is algebraic over the
    selected critical sheet.  The separately supplied place-extension
    theorem then yields a finite or infinity Puiseux endpoint over the
    selected branch point.
    """

    if not problem.name:
        raise FilteredObstructionError(
            "empty_problem_name",
            "algebraic clock-continuation problem name must be nonempty",
        )
    context = _replay_filtered_puiseux_context(problem.context)
    exponent = _rational(context.first_fractional_exponent)
    if exponent != sp.Rational(5, 2):
        raise FilteredObstructionError(
            "unsupported_algebraic_continuation_exponent",
            "the critical continuation compiler requires exponent 5/2",
        )
    julia_id = FilteredPuiseuxClaim.JULIA_FLOW_IDENTITY.value
    polynomiality_id = (
        FilteredDensityClockClaim.GROUP_MODULE_POLYNOMIALITY.value
    )
    clock_id = FilteredDensityClockClaim.CLOCK_FACTORIZATION_IDENTITY.value
    algebraic_ids = {
        claim.value for claim in FilteredAlgebraicContinuationClaim
    }
    expected_ids = {julia_id, polynomiality_id, clock_id, *algebraic_ids}
    if (
        len(problem.evidence) != len(expected_ids)
        or {receipt.claim_id for receipt in problem.evidence} != expected_ids
    ):
        raise FilteredObstructionError(
            "algebraic_clock_continuation_evidence_claim_set_incomplete",
            "the compiler needs Julia, group-module polynomiality, density, "
            "nonbase, and place receipts",
        )
    julia_receipts = _validated_puiseux_evidence(
        context=context,
        evidence=tuple(
            receipt for receipt in problem.evidence
            if receipt.claim_id == julia_id
        ),
        required_claims=(FilteredPuiseuxClaim.JULIA_FLOW_IDENTITY,),
    )
    clock_receipts = _validated_density_clock_evidence(
        context=context,
        evidence=tuple(
            receipt for receipt in problem.evidence
            if receipt.claim_id in {polynomiality_id, clock_id}
        ),
        required_claims=(
            FilteredDensityClockClaim.GROUP_MODULE_POLYNOMIALITY,
            FilteredDensityClockClaim.CLOCK_FACTORIZATION_IDENTITY,
        ),
    )
    algebraic_receipts = _validated_algebraic_continuation_evidence(
        context=context,
        evidence=tuple(
            receipt for receipt in problem.evidence
            if receipt.claim_id in algebraic_ids
        ),
    )
    receipt_rows = tuple(sorted(
        (receipt.claim_id, receipt.receipt_sha256)
        for receipt in problem.evidence
    ))
    payload = {
        "problem": problem.name,
        "context_sha256": context.context_sha256,
        "squared_density_identity_receipt_sha256": clock_receipts[
            FilteredDensityClockClaim.CLOCK_FACTORIZATION_IDENTITY
        ].receipt_sha256,
        "group_module_polynomiality_receipt_sha256": clock_receipts[
            FilteredDensityClockClaim.GROUP_MODULE_POLYNOMIALITY
        ].receipt_sha256,
        "time_one_julia_identity_receipt_sha256": julia_receipts[
            FilteredPuiseuxClaim.JULIA_FLOW_IDENTITY
        ].receipt_sha256,
        "critical_square_nonbase_receipt_sha256": algebraic_receipts[
            FilteredAlgebraicContinuationClaim.CRITICAL_SQUARE_OUTSIDE_BASE_FIELD
        ].receipt_sha256,
        "selected_place_extension_receipt_sha256": algebraic_receipts[
            FilteredAlgebraicContinuationClaim.ALGEBRAIC_PLACE_PUISEUX_EXTENSION
        ].receipt_sha256,
        "critical_square_first_nonbase_exponent": "3/2",
        "zero_generator_excluded_before_elimination": True,
        "derivative_free_eliminant_nonzero": True,
        "endpoint_algebraic_over_selected_critical_field": True,
        "selected_endpoint_trichotomy_derived": True,
    }
    certificate_sha256 = content_sha256(payload)
    selected_endpoint_receipt = make_filtered_density_clock_evidence(
        claim=FilteredDensityClockClaim.SELECTED_ENDPOINT_TRICHOTOMY,
        context=context,
        authority=EvidenceAuthority.FILTERED_COMPILER,
        scope=(
            FilteredDensityClockEvidenceScope.SELECTED_ANALYTIC_BRANCH_EXHAUSTIVE
        ),
        evidence_sha256=certificate_sha256,
    )
    proof_contract_sha256 = content_sha256({
        "schema": "ztare.filtered_algebraic_clock_continuation_proof.v1",
        "context_sha256": context.context_sha256,
        "evidence_receipt_sha256": receipt_rows,
        "semantic_certificate_sha256": certificate_sha256,
        "selected_endpoint_receipt_sha256": (
            selected_endpoint_receipt.receipt_sha256
        ),
    })
    return FilteredAlgebraicClockContinuationCertificate(
        schema="ztare.filtered_algebraic_clock_continuation_certificate.v1",
        problem_name=problem.name,
        squared_density_identity_verified_by_adapter=True,
        group_module_polynomiality_verified_by_adapter=True,
        time_one_julia_identity_verified_by_adapter=True,
        zero_generator_excluded_before_elimination=True,
        critical_square_outside_base_field=True,
        critical_square_first_nonbase_exponent="3/2",
        derivative_free_eliminant_nonzero=True,
        endpoint_algebraic_over_selected_critical_field=True,
        selected_place_extension_verified_by_adapter=True,
        selected_endpoint_is_finite_or_infinity=True,
        selected_endpoint_trichotomy_derived=True,
        adapter_completeness_inferred=False,
        context_sha256=context.context_sha256,
        evidence_receipt_sha256=receipt_rows,
        algebraic_continuation_certificate_sha256=certificate_sha256,
        selected_endpoint_receipt_sha256=(
            selected_endpoint_receipt.receipt_sha256
        ),
        proof_contract_sha256=proof_contract_sha256,
    )


def compile_filtered_two_flow_puiseux_obstruction(
    problem: FilteredTwoFlowPuiseuxProblem,
) -> FilteredTwoFlowPuiseuxCertificate:
    """Exclude a two-sided factorization by polynomial autonomous flows.

    The proof is degree-independent.  If both factors are finite along the
    selected branch, analytic ODE dependence makes their composition
    analytic.  Otherwise the inner flow tends to infinity and the outer
    flow returns from infinity.  For a degree-``d`` polynomial field, its
    time coordinate at infinity begins with ``z**(-(d-1))``.  A nonzero
    linear term in the composition forces the two degrees to agree.

    Normalize their leading coefficients and let ``e`` be the largest
    degree at which the two generators differ.  The assumption that both
    fix the formal base point to order at least two gives ``e >= 2``.  The
    transition between their time coordinates has first fractional term

        u ** (1 + (d-e)/(d-1)),

    whose exponent lies strictly between one and two.  If no such ``e``
    exists, the generators are proportional and their product is one
    polynomial flow, already excluded by the Julia compiler.  Hence a first
    nonintegral exponent greater than two excludes every branch.
    """

    if not problem.name:
        raise FilteredObstructionError(
            "empty_problem_name",
            "two-flow Puiseux problem name must be nonempty",
        )
    context = _replay_filtered_puiseux_context(problem.context)
    exponent = _rational(context.first_fractional_exponent)
    if exponent <= 2:
        raise FilteredObstructionError(
            "insufficient_two_flow_exponent",
            "the two-flow obstruction needs a first fractional exponent "
            "strictly greater than two",
        )
    if exponent.q == 1:
        raise FilteredObstructionError(
            "integer_puiseux_exponent",
            "an integral exponent supplies no fractional-flow obstruction",
        )
    minimum_order = problem.minimum_generator_vanishing_order
    if (
        isinstance(minimum_order, bool)
        or not isinstance(minimum_order, int)
        or minimum_order < 2
    ):
        raise FilteredObstructionError(
            "generator_not_tangent_to_identity",
            "both polynomial generators must vanish to order at least two",
        )
    required_claims = (
        FilteredPuiseuxClaim.REGULAR_LINEAR_COEFFICIENT_NONZERO,
        FilteredPuiseuxClaim.FIRST_FRACTIONAL_COEFFICIENT_NONZERO,
        FilteredPuiseuxClaim.TWO_FLOW_FACTORIZATION_IDENTITY,
    )
    receipts = _validated_puiseux_evidence(
        context=context,
        evidence=problem.evidence,
        required_claims=required_claims,
    )
    digest = context.local_expansion_evidence_sha256

    proportional_julia_receipt = make_filtered_puiseux_evidence(
        claim=FilteredPuiseuxClaim.JULIA_FLOW_IDENTITY,
        context=context,
        authority=EvidenceAuthority.FILTERED_COMPILER,
        scope=FilteredPuiseuxEvidenceScope.EXACT_FORMAL_FLOW_IDENTITY,
        evidence_sha256=receipts[
            FilteredPuiseuxClaim.TWO_FLOW_FACTORIZATION_IDENTITY
        ].receipt_sha256,
    )
    single_flow = compile_filtered_puiseux_flow_obstruction(
        FilteredPuiseuxFlowProblem(
            name=f"{problem.name}.proportional_case",
            context=context,
            evidence=(
                receipts[
                    FilteredPuiseuxClaim.REGULAR_LINEAR_COEFFICIENT_NONZERO
                ],
                receipts[
                    FilteredPuiseuxClaim.FIRST_FRACTIONAL_COEFFICIENT_NONZERO
                ],
                proportional_julia_receipt,
            ),
        )
    )
    payload = {
        "problem": problem.name,
        "first_fractional_exponent": str(exponent),
        "regular_linear_coefficient_nonzero": True,
        "fractional_coefficient_nonzero": True,
        "minimum_generator_vanishing_order": minimum_order,
        "two_flow_factorization_applies": True,
        "regular_finite_route_is_analytic": True,
        "infinity_route_equal_degrees_forced": True,
        "nonproportional_infinity_exponent_interval": "1<lambda<2",
        "proportional_case_reduces_to_single_flow": True,
        "single_flow_certificate_sha256": (
            single_flow.puiseux_flow_certificate_sha256
        ),
    }
    certificate_sha256 = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    receipt_rows = tuple(
        (claim.value, receipts[claim].receipt_sha256)
        for claim in required_claims
    )
    proof_contract_sha256 = content_sha256({
        "schema": "ztare.filtered_two_flow_puiseux_proof.v1",
        "context_sha256": context.context_sha256,
        "evidence_receipt_sha256": receipt_rows,
        "proportional_julia_receipt_sha256": (
            proportional_julia_receipt.receipt_sha256
        ),
        "single_flow_certificate_sha256": (
            single_flow.puiseux_flow_certificate_sha256
        ),
        "semantic_certificate_sha256": certificate_sha256,
    })
    return FilteredTwoFlowPuiseuxCertificate(
        schema="ztare.filtered_two_flow_puiseux_certificate.v2",
        problem_name=problem.name,
        first_fractional_exponent=str(exponent),
        regular_linear_coefficient_nonzero=True,
        fractional_coefficient_nonzero=True,
        minimum_generator_vanishing_order=minimum_order,
        regular_finite_route_is_analytic=True,
        infinity_route_equal_degrees_forced=True,
        nonproportional_infinity_exponent_interval="1<lambda<2",
        proportional_case_reduces_to_single_flow=True,
        single_flow_polynomial_generator_excluded=(
            single_flow.polynomial_generator_excluded
        ),
        polynomial_two_flow_factorization_excluded=True,
        adapter_completeness_inferred=False,
        local_expansion_certificate_sha256=digest,
        two_flow_puiseux_certificate_sha256=certificate_sha256,
        evidence_receipt_sha256=receipt_rows,
        proportional_julia_receipt_sha256=(
            proportional_julia_receipt.receipt_sha256
        ),
        proof_contract_sha256=proof_contract_sha256,
    )


def _filtered_polar_witt_context_core(
    context: FilteredPolarWittContext,
) -> dict[str, object]:
    model = (
        context.model.value
        if isinstance(context.model, FilteredPolarWittModel)
        else context.model
    )
    return {
        "schema": context.schema,
        "category_id": context.category_id,
        "filtration_id": context.filtration_id,
        "model": model,
        "adapter_evidence_sha256": context.adapter_evidence_sha256,
        "centralizer_evidence_sha256": (
            context.centralizer_evidence_sha256
        ),
    }


def _replay_filtered_polar_witt_context(
    context: FilteredPolarWittContext,
) -> FilteredPolarWittContext:
    if context.schema != FILTERED_POLAR_WITT_CONTEXT_SCHEMA:
        raise FilteredObstructionError(
            "polar_witt_context_schema_mismatch",
            "the polar-Witt context schema is not recognized",
        )
    if (
        not isinstance(context.category_id, str)
        or not context.category_id.strip()
        or not isinstance(context.filtration_id, str)
        or not context.filtration_id.strip()
    ):
        raise FilteredObstructionError(
            "polar_witt_context_identity_empty",
            "the polar-Witt category and filtration must be nonempty",
        )
    if not isinstance(context.model, FilteredPolarWittModel):
        raise FilteredObstructionError(
            "polar_witt_model_unknown",
            "the tangent-Witt/Newton model is not compiler-owned",
        )
    try:
        require_sha256_digest(
            context.adapter_evidence_sha256,
            context="polar-Witt adapter evidence",
        )
        require_sha256_digest(
            context.centralizer_evidence_sha256,
            context="polar-Witt centralizer evidence",
        )
        require_sha256_digest(
            context.context_sha256,
            context="polar-Witt context",
        )
    except ValueError as error:
        raise FilteredObstructionError(
            "invalid_polar_witt_context_digest",
            str(error),
        ) from error
    expected = content_sha256(_filtered_polar_witt_context_core(context))
    if context.context_sha256 != expected:
        raise FilteredObstructionError(
            "polar_witt_context_digest_mismatch",
            "the polar-Witt context content does not replay",
        )
    return context


def make_filtered_polar_witt_context(
    *,
    category_id: str,
    filtration_id: str,
    model: FilteredPolarWittModel,
    adapter_evidence_sha256: str,
    centralizer_evidence_sha256: str,
) -> FilteredPolarWittContext:
    """Create one replayable lowering to the tangent-Witt/Newton model."""

    provisional = FilteredPolarWittContext(
        schema=FILTERED_POLAR_WITT_CONTEXT_SCHEMA,
        category_id=category_id,
        filtration_id=filtration_id,
        model=model,
        adapter_evidence_sha256=adapter_evidence_sha256,
        centralizer_evidence_sha256=centralizer_evidence_sha256,
        context_sha256="0" * 64,
    )
    context = replace(
        provisional,
        context_sha256=content_sha256(
            _filtered_polar_witt_context_core(provisional)
        ),
    )
    return _replay_filtered_polar_witt_context(context)


def make_filtered_polar_witt_evidence(
    *,
    claim: FilteredPolarWittClaim,
    subject_id: str,
    context: FilteredPolarWittContext,
    authority: EvidenceAuthority,
    scope: FilteredPolarWittEvidenceScope,
    evidence_sha256: str,
) -> ContentBoundEvidenceReceipt:
    """Bind one adapter proposition to a polar-Witt context."""

    _replay_filtered_polar_witt_context(context)
    if not isinstance(claim, FilteredPolarWittClaim):
        raise FilteredObstructionError(
            "polar_witt_evidence_claim_unknown",
            "the polar-Witt evidence claim is not recognized",
        )
    if not isinstance(scope, FilteredPolarWittEvidenceScope):
        raise FilteredObstructionError(
            "polar_witt_evidence_scope_unknown",
            "the polar-Witt evidence scope is not recognized",
        )
    try:
        return make_content_bound_evidence(
            claim_id=claim.value,
            subject_id=subject_id,
            context_sha256=context.context_sha256,
            authority=authority,
            scope_id=scope.value,
            conclusion={},
            evidence_sha256=evidence_sha256,
        )
    except ContentBoundEvidenceError as error:
        raise FilteredObstructionError(error.code, str(error)) from error


def compile_filtered_polar_witt_factorization(
    problem: FilteredPolarWittFactorizationProblem,
) -> FilteredPolarWittFactorizationCertificate:
    """Exclude finite positive Rees faces in a tangent-Witt factorization.

    Let ``s**(-h) * x**d`` be the least-``x`` monomial on a maximal
    positive face, with ``h > 0`` and primitive parameter order
    ``p = d-h > 0``.  For a defect monomial ``s**nu * x**e``, the quantity

        h*e + d*nu

    is invariant under the leading adjoint.  Hence lower faces cannot
    cancel its Newton orbit, and every tied face is finite.  Modulo terms
    containing two defect letters, the exact two-factor law is the
    semidirect identity

        B + C = z/(1-exp(-z)) * Z.

    If ``P`` is a nonzero polynomial, ``z*P(z)/(1-exp(-z))`` is not a
    polynomial: otherwise multiplying by ``1-exp(-z)`` would make a
    nonzero polynomial times ``exp(-z)`` polynomial.  Thus every
    noncentral finite Newton seed has infinitely many nonzero adjoint
    descendants.  In the tangent one-variable Witt algebra an adjoint orbit
    terminates only in the centralizer; the centralizer is the scalar line
    of the leading field.  The adapter binds exclusion of that remaining
    polynomial-flow branch.

    The rate calculation is parametric.  With ``d=p+h``, an orbit has order
    increment ``p`` and payment-degree increment ``m*(p+h)``, where ``m``
    is ``degree_multiplier``.  For positive ``p,h`` this is strictly above
    the threshold whenever ``m >= threshold``.
    """

    if not problem.name:
        raise FilteredObstructionError(
            "empty_problem_name",
            "polar Witt factorization problem name must be nonempty",
        )
    threshold = _rational(problem.threshold)
    multiplier = _rational(problem.degree_multiplier)
    if threshold <= 0:
        raise FilteredObstructionError(
            "nonpositive_rate_threshold",
            "the asymptotic threshold must be positive",
        )
    if multiplier <= 0 or multiplier < threshold:
        raise FilteredObstructionError(
            "insufficient_polar_orbit_rate",
            "the degree multiplier must be positive and at least the "
            "declared threshold",
        )
    context = _replay_filtered_polar_witt_context(problem.context)
    if context.model is not (
        FilteredPolarWittModel.TANGENT_WITT_FIRST_DEFECT_NEWTON
    ):
        raise FilteredObstructionError(
            "polar_witt_model_has_no_orbit_theorem",
            "the compiler has no orbit theorem for this polar-Witt model",
        )
    required_claims = tuple(FilteredPolarWittClaim)
    receipts: dict[
        FilteredPolarWittClaim,
        ContentBoundEvidenceReceipt,
    ] = {}
    for carried in problem.evidence:
        try:
            receipt = replay_content_bound_evidence(carried)
        except ContentBoundEvidenceError as error:
            raise FilteredObstructionError(error.code, str(error)) from error
        try:
            claim = FilteredPolarWittClaim(receipt.claim_id)
        except ValueError as error:
            raise FilteredObstructionError(
                "polar_witt_evidence_claim_unknown",
                f"unknown polar-Witt evidence claim {receipt.claim_id!r}",
            ) from error
        if claim in receipts:
            raise FilteredObstructionError(
                "polar_witt_evidence_claim_duplicate",
                f"polar-Witt claim {claim.value!r} occurs more than once",
            )
        if receipt.context_sha256 != context.context_sha256:
            raise FilteredObstructionError(
                "polar_witt_evidence_context_mismatch",
                f"polar-Witt claim {claim.value!r} belongs to another context",
            )
        if receipt.authority is EvidenceAuthority.FINITE_EXPERIMENT:
            raise FilteredObstructionError(
                "polar_witt_evidence_authority_insufficient",
                f"finite experiment authority cannot discharge {claim.value!r}",
            )
        receipts[claim] = receipt
    missing = set(required_claims) - set(receipts)
    if FilteredPolarWittClaim.SEMIDIRECT_NEWTON_QUOTIENT_APPLIES in missing:
        raise FilteredObstructionError(
            "missing_semidirect_newton_quotient",
            "the factorization needs an exact first-defect Newton quotient",
        )
    if missing or set(receipts) - set(required_claims):
        raise FilteredObstructionError(
            "polar_witt_evidence_claim_set_incomplete",
            "polar-Witt evidence does not cover the exact required claim set",
        )
    subjects = [receipts[claim].subject_id for claim in required_claims]
    if len(subjects) != len(set(subjects)):
        raise FilteredObstructionError(
            "polar_witt_evidence_subject_reused",
            "distinct polar-Witt claims need distinct proposition subjects",
        )
    expected_scopes = {
        FilteredPolarWittClaim.FINITE_MAXIMAL_FACE_DECOMPOSITION: (
            FilteredPolarWittEvidenceScope.ALL_FINITE_POSITIVE_FACES
        ),
        FilteredPolarWittClaim.SEMIDIRECT_NEWTON_QUOTIENT_APPLIES: (
            FilteredPolarWittEvidenceScope.EXACT_FIRST_DEFECT_QUOTIENT
        ),
        FilteredPolarWittClaim.CENTRALIZER_FLOW_EXCLUDED: (
            FilteredPolarWittEvidenceScope.SCALAR_CENTRALIZER_BRANCH
        ),
    }
    for claim in required_claims:
        receipt = receipts[claim]
        if receipt.scope_id != expected_scopes[claim].value:
            raise FilteredObstructionError(
                "polar_witt_evidence_scope_mismatch",
                f"polar-Witt claim {claim.value!r} has scope "
                f"{receipt.scope_id!r}, expected {expected_scopes[claim].value!r}",
            )
        if receipt.conclusion():
            raise FilteredObstructionError(
                "polar_witt_evidence_conclusion_malformed",
                "polar-Witt proposition receipts have no scalar conclusion",
            )
    adapter_digest = context.adapter_evidence_sha256
    centralizer_digest = context.centralizer_evidence_sha256
    for claim in (
        FilteredPolarWittClaim.FINITE_MAXIMAL_FACE_DECOMPOSITION,
        FilteredPolarWittClaim.SEMIDIRECT_NEWTON_QUOTIENT_APPLIES,
    ):
        if receipts[claim].evidence_sha256 != adapter_digest:
            raise FilteredObstructionError(
                "polar_witt_adapter_evidence_mismatch",
                f"polar-Witt claim {claim.value!r} is not adapter-owned",
            )
    if receipts[
        FilteredPolarWittClaim.CENTRALIZER_FLOW_EXCLUDED
    ].evidence_sha256 != centralizer_digest:
        raise FilteredObstructionError(
            "polar_witt_centralizer_evidence_mismatch",
            "the centralizer proposition is not owned by its certificate",
        )
    rate_formula = f"{multiplier}*(p+h)/p"
    payload = {
        "problem": problem.name,
        "threshold": str(threshold),
        "degree_multiplier": str(multiplier),
        "finite_positive_support": True,
        "product_has_nonpositive_rees_support": True,
        "opposite_maximal_faces": True,
        "newton_invariant": "h*e+d*nu",
        "semidirect_transfer": "z/(1-exp(-z))",
        "inverse_transfer_nonpolynomial": True,
        "tangent_witt_orbit_nonterminating_or_central": True,
        "orbit_order_increment": "p=d-h>0",
        "orbit_payment_degree_increment": f"{multiplier}*d",
        "orbit_rate_formula": rate_formula,
        "strict_rate_excess": (
            f"({multiplier}-{threshold})*p+{multiplier}*h>0"
        ),
        "centralizer_polynomial_flow_excluded": True,
        "adapter_certificate_sha256": adapter_digest,
        "centralizer_certificate_sha256": centralizer_digest,
    }
    certificate_sha256 = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    receipt_rows = tuple(
        (claim.value, receipts[claim].receipt_sha256)
        for claim in required_claims
    )
    authority_rows = tuple(
        (claim.value, receipts[claim].authority.value)
        for claim in required_claims
    )
    proof_contract_sha256 = content_sha256({
        "schema": "ztare.filtered_polar_witt_proof.v1",
        "context_sha256": context.context_sha256,
        "evidence_receipt_sha256": receipt_rows,
        "semantic_certificate_sha256": certificate_sha256,
    })
    return FilteredPolarWittFactorizationCertificate(
        schema="ztare.filtered_polar_witt_factorization_certificate.v2",
        problem_name=problem.name,
        threshold=str(threshold),
        degree_multiplier=str(multiplier),
        finite_positive_support=True,
        product_has_nonpositive_rees_support=True,
        opposite_maximal_faces_verified=True,
        newton_invariant="h*e+d*nu",
        tied_newton_faces_finite=True,
        semidirect_transfer="z/(1-exp(-z))",
        inverse_transfer_nonpolynomial_on_nonzero_polynomial_seed=True,
        tangent_witt_orbit_nonterminating_or_central=True,
        orbit_order_increment="p=d-h>0",
        orbit_payment_degree_increment=f"{multiplier}*d",
        orbit_rate_formula=rate_formula,
        noncentral_branch_strictly_supercritical=True,
        centralizer_branch_reduces_to_polynomial_flow=True,
        centralizer_polynomial_flow_excluded=True,
        arbitrary_finite_polar_prefix_excluded=True,
        adapter_completeness_inferred=False,
        adapter_certificate_sha256=adapter_digest,
        centralizer_certificate_sha256=centralizer_digest,
        context_sha256=context.context_sha256,
        model=context.model.value,
        evidence_receipt_sha256=receipt_rows,
        evidence_authority=authority_rows,
        polar_witt_certificate_sha256=certificate_sha256,
        proof_contract_sha256=proof_contract_sha256,
    )


def _filtered_critical_two_flow_context_core(
    context: FilteredCriticalTwoFlowContext,
) -> dict[str, object]:
    return {
        "schema": context.schema,
        "schedule_category_id": context.schedule_category_id,
        "factorization_category_id": context.factorization_category_id,
        "source_germ_id": context.source_germ_id,
        "visible_germ_id": context.visible_germ_id,
        "minimum_generator_vanishing_order": (
            context.minimum_generator_vanishing_order
        ),
        "specialization_evidence_sha256": (
            context.specialization_evidence_sha256
        ),
        "exclusion_evidence_sha256": context.exclusion_evidence_sha256,
    }


def _replay_filtered_critical_two_flow_context(
    context: FilteredCriticalTwoFlowContext,
) -> FilteredCriticalTwoFlowContext:
    if context.schema != FILTERED_CRITICAL_TWO_FLOW_CONTEXT_SCHEMA:
        raise FilteredObstructionError(
            "critical_two_flow_context_schema_mismatch",
            "the critical two-flow context schema is not recognized",
        )
    identities = (
        context.schedule_category_id,
        context.factorization_category_id,
        context.source_germ_id,
        context.visible_germ_id,
    )
    if any(not isinstance(value, str) or not value.strip() for value in identities):
        raise FilteredObstructionError(
            "critical_two_flow_context_identity_empty",
            "the schedule, factorization, source, and visible identities "
            "must be nonempty",
        )
    minimum_order = context.minimum_generator_vanishing_order
    if (
        isinstance(minimum_order, bool)
        or not isinstance(minimum_order, int)
        or minimum_order < 2
    ):
        raise FilteredObstructionError(
            "critical_two_flow_normalization_too_weak",
            "the generators must vanish through at least linear order",
        )
    try:
        require_sha256_digest(
            context.specialization_evidence_sha256,
            context="critical two-flow specialization evidence",
        )
        require_sha256_digest(
            context.exclusion_evidence_sha256,
            context="critical two-flow exclusion evidence",
        )
        require_sha256_digest(
            context.context_sha256,
            context="critical two-flow context",
        )
    except ValueError as error:
        raise FilteredObstructionError(
            "invalid_critical_two_flow_context_digest",
            str(error),
        ) from error
    expected = content_sha256(_filtered_critical_two_flow_context_core(context))
    if context.context_sha256 != expected:
        raise FilteredObstructionError(
            "critical_two_flow_context_digest_mismatch",
            "the critical two-flow context content does not replay",
        )
    return context


def make_filtered_critical_two_flow_context(
    *,
    schedule_category_id: str,
    factorization_category_id: str,
    source_germ_id: str,
    visible_germ_id: str,
    minimum_generator_vanishing_order: int,
    specialization_evidence_sha256: str,
    exclusion_evidence_sha256: str,
) -> FilteredCriticalTwoFlowContext:
    """Create one replayable schedule-to-factorization context."""

    provisional = FilteredCriticalTwoFlowContext(
        schema=FILTERED_CRITICAL_TWO_FLOW_CONTEXT_SCHEMA,
        schedule_category_id=schedule_category_id,
        factorization_category_id=factorization_category_id,
        source_germ_id=source_germ_id,
        visible_germ_id=visible_germ_id,
        minimum_generator_vanishing_order=(
            minimum_generator_vanishing_order
        ),
        specialization_evidence_sha256=specialization_evidence_sha256,
        exclusion_evidence_sha256=exclusion_evidence_sha256,
        context_sha256="0" * 64,
    )
    context = replace(
        provisional,
        context_sha256=content_sha256(
            _filtered_critical_two_flow_context_core(provisional)
        ),
    )
    return _replay_filtered_critical_two_flow_context(context)


def _filtered_critical_two_flow_claim_conclusion(
    claim: FilteredCriticalTwoFlowClaim,
    context: FilteredCriticalTwoFlowContext,
) -> dict[str, object]:
    shared = {
        "factorization_category_id": context.factorization_category_id,
        "source_germ_id": context.source_germ_id,
        "visible_germ_id": context.visible_germ_id,
        "minimum_generator_vanishing_order": (
            context.minimum_generator_vanishing_order
        ),
    }
    if claim is (
        FilteredCriticalTwoFlowClaim.ZERO_FACE_REALIZES_TWO_FLOW_FACTORIZATION
    ):
        return {
            **shared,
            "schedule_category_id": context.schedule_category_id,
            "relation": "every_zero_face_schedule_realizes_factorization",
        }
    if claim is (
        FilteredCriticalTwoFlowClaim.NORMALIZED_TWO_FLOW_FACTORIZATION_EXCLUDED
    ):
        return {
            **shared,
            "category_empty": True,
        }
    raise FilteredObstructionError(
        "critical_two_flow_evidence_claim_unknown",
        "the critical two-flow evidence claim is not recognized",
    )


def make_filtered_critical_two_flow_evidence(
    *,
    claim: FilteredCriticalTwoFlowClaim,
    subject_id: str,
    context: FilteredCriticalTwoFlowContext,
    authority: EvidenceAuthority,
    scope: FilteredCriticalTwoFlowEvidenceScope,
    evidence_sha256: str,
) -> ContentBoundEvidenceReceipt:
    """Bind one arrow of the critical-terminal composition."""

    _replay_filtered_critical_two_flow_context(context)
    if not isinstance(claim, FilteredCriticalTwoFlowClaim):
        raise FilteredObstructionError(
            "critical_two_flow_evidence_claim_unknown",
            "the critical two-flow evidence claim is not recognized",
        )
    if not isinstance(scope, FilteredCriticalTwoFlowEvidenceScope):
        raise FilteredObstructionError(
            "critical_two_flow_evidence_scope_unknown",
            "the critical two-flow evidence scope is not recognized",
        )
    try:
        return make_content_bound_evidence(
            claim_id=claim.value,
            subject_id=subject_id,
            context_sha256=context.context_sha256,
            authority=authority,
            scope_id=scope.value,
            conclusion=_filtered_critical_two_flow_claim_conclusion(
                claim, context
            ),
            evidence_sha256=evidence_sha256,
        )
    except ContentBoundEvidenceError as error:
        raise FilteredObstructionError(error.code, str(error)) from error


def _filtered_critical_two_flow_certificate_payload(
    certificate: FilteredCriticalTwoFlowCertificate,
) -> dict[str, object]:
    return {
        "problem": certificate.problem_name,
        "schedule_category_id": certificate.schedule_category_id,
        "factorization_category_id": certificate.factorization_category_id,
        "source_germ_id": certificate.source_germ_id,
        "visible_germ_id": certificate.visible_germ_id,
        "minimum_generator_vanishing_order": (
            certificate.minimum_generator_vanishing_order
        ),
        "zero_face_realizes_two_flow_factorization": (
            certificate.zero_face_realizes_two_flow_factorization
        ),
        "normalized_two_flow_factorization_excluded": (
            certificate.normalized_two_flow_factorization_excluded
        ),
        "critical_terminal_excluded": certificate.critical_terminal_excluded,
        "specialization_evidence_sha256": (
            certificate.specialization_evidence_sha256
        ),
        "exclusion_evidence_sha256": certificate.exclusion_evidence_sha256,
        "context_sha256": certificate.context_sha256,
    }


def _replay_filtered_critical_two_flow_certificate(
    certificate: FilteredCriticalTwoFlowCertificate,
) -> FilteredCriticalTwoFlowCertificate:
    if certificate.schema != "ztare.filtered_critical_two_flow_certificate.v1":
        raise FilteredObstructionError(
            "critical_two_flow_certificate_schema_mismatch",
            "the critical two-flow certificate schema is not recognized",
        )
    if not (
        certificate.zero_face_realizes_two_flow_factorization
        and certificate.normalized_two_flow_factorization_excluded
        and certificate.critical_terminal_excluded
    ):
        raise FilteredObstructionError(
            "critical_two_flow_certificate_not_terminal",
            "the carried certificate does not exclude the critical terminal",
        )
    expected = content_sha256(
        _filtered_critical_two_flow_certificate_payload(certificate)
    )
    if certificate.critical_two_flow_certificate_sha256 != expected:
        raise FilteredObstructionError(
            "critical_two_flow_certificate_digest_mismatch",
            "the critical two-flow certificate content does not replay",
        )
    proof_payload = {
        "schema": "ztare.filtered_critical_two_flow_proof_contract.v1",
        "theorem_sha256": expected,
        "context_sha256": certificate.context_sha256,
        "evidence_receipt_sha256": [
            digest for _, digest in certificate.evidence_receipt_sha256
        ],
    }
    if content_sha256(proof_payload) != certificate.proof_contract_sha256:
        raise FilteredObstructionError(
            "critical_two_flow_proof_contract_digest_mismatch",
            "the critical two-flow proof contract does not replay",
        )
    return certificate


def compile_filtered_critical_two_flow_terminal(
    problem: FilteredCriticalTwoFlowProblem,
) -> FilteredCriticalTwoFlowCertificate:
    """Compose an exact zero-face realization with category exclusion."""

    if not problem.name:
        raise FilteredObstructionError(
            "empty_problem_name",
            "critical two-flow problem name must be nonempty",
        )
    context = _replay_filtered_critical_two_flow_context(problem.context)
    required_claims = tuple(FilteredCriticalTwoFlowClaim)
    if len(problem.evidence) != len(required_claims):
        raise FilteredObstructionError(
            "critical_two_flow_evidence_claim_set_incomplete",
            "critical two-flow composition needs exactly two proposition receipts",
        )
    receipts: dict[
        FilteredCriticalTwoFlowClaim,
        ContentBoundEvidenceReceipt,
    ] = {}
    for carried in problem.evidence:
        try:
            receipt = replay_content_bound_evidence(carried)
        except ContentBoundEvidenceError as error:
            raise FilteredObstructionError(error.code, str(error)) from error
        try:
            claim = FilteredCriticalTwoFlowClaim(receipt.claim_id)
        except ValueError as error:
            raise FilteredObstructionError(
                "critical_two_flow_evidence_claim_unknown",
                f"unknown critical two-flow claim {receipt.claim_id!r}",
            ) from error
        if claim in receipts:
            raise FilteredObstructionError(
                "critical_two_flow_evidence_claim_duplicate",
                f"critical two-flow claim {claim.value!r} occurs more than once",
            )
        if receipt.context_sha256 != context.context_sha256:
            raise FilteredObstructionError(
                "critical_two_flow_evidence_context_mismatch",
                f"critical two-flow claim {claim.value!r} belongs to another context",
            )
        receipts[claim] = receipt
    if set(receipts) != set(required_claims):
        raise FilteredObstructionError(
            "critical_two_flow_evidence_claim_set_incomplete",
            "critical two-flow evidence does not cover the exact claim set",
        )
    subjects = [receipts[claim].subject_id for claim in required_claims]
    if len(subjects) != len(set(subjects)):
        raise FilteredObstructionError(
            "critical_two_flow_evidence_subject_reused",
            "realization and exclusion need distinct proposition subjects",
        )
    expected_scopes = {
        FilteredCriticalTwoFlowClaim.ZERO_FACE_REALIZES_TWO_FLOW_FACTORIZATION: (
            FilteredCriticalTwoFlowEvidenceScope.ALL_STRICT_SUBTHRESHOLD_ZERO_FACES
        ),
        FilteredCriticalTwoFlowClaim.NORMALIZED_TWO_FLOW_FACTORIZATION_EXCLUDED: (
            FilteredCriticalTwoFlowEvidenceScope.EXACT_NORMALIZED_AUTONOMOUS_TWO_FLOW_CATEGORY
        ),
    }
    expected_authorities = {
        FilteredCriticalTwoFlowClaim.ZERO_FACE_REALIZES_TWO_FLOW_FACTORIZATION: (
            EvidenceAuthority.ADAPTER_EXACT
        ),
        FilteredCriticalTwoFlowClaim.NORMALIZED_TWO_FLOW_FACTORIZATION_EXCLUDED: (
            EvidenceAuthority.FILTERED_COMPILER
        ),
    }
    expected_digests = {
        FilteredCriticalTwoFlowClaim.ZERO_FACE_REALIZES_TWO_FLOW_FACTORIZATION: (
            context.specialization_evidence_sha256
        ),
        FilteredCriticalTwoFlowClaim.NORMALIZED_TWO_FLOW_FACTORIZATION_EXCLUDED: (
            context.exclusion_evidence_sha256
        ),
    }
    for claim in required_claims:
        receipt = receipts[claim]
        if receipt.scope_id != expected_scopes[claim].value:
            raise FilteredObstructionError(
                "critical_two_flow_evidence_scope_mismatch",
                f"critical two-flow claim {claim.value!r} has the wrong scope",
            )
        if receipt.authority is not expected_authorities[claim]:
            raise FilteredObstructionError(
                "critical_two_flow_evidence_authority_mismatch",
                f"critical two-flow claim {claim.value!r} has the wrong authority",
            )
        if receipt.evidence_sha256 != expected_digests[claim]:
            raise FilteredObstructionError(
                "critical_two_flow_evidence_artifact_mismatch",
                f"critical two-flow claim {claim.value!r} has the wrong artifact",
            )
        if receipt.conclusion() != _filtered_critical_two_flow_claim_conclusion(
            claim, context
        ):
            raise FilteredObstructionError(
                "critical_two_flow_evidence_conclusion_mismatch",
                f"critical two-flow claim {claim.value!r} names another proposition",
            )
    receipt_rows = tuple(
        (claim.value, receipts[claim].receipt_sha256)
        for claim in required_claims
    )
    authority_rows = tuple(
        (claim.value, receipts[claim].authority.value)
        for claim in required_claims
    )
    provisional = FilteredCriticalTwoFlowCertificate(
        schema="ztare.filtered_critical_two_flow_certificate.v1",
        problem_name=problem.name,
        schedule_category_id=context.schedule_category_id,
        factorization_category_id=context.factorization_category_id,
        source_germ_id=context.source_germ_id,
        visible_germ_id=context.visible_germ_id,
        minimum_generator_vanishing_order=(
            context.minimum_generator_vanishing_order
        ),
        zero_face_realizes_two_flow_factorization=True,
        normalized_two_flow_factorization_excluded=True,
        critical_terminal_excluded=True,
        specialization_evidence_sha256=(
            context.specialization_evidence_sha256
        ),
        exclusion_evidence_sha256=context.exclusion_evidence_sha256,
        context_sha256=context.context_sha256,
        evidence_receipt_sha256=receipt_rows,
        evidence_authority=authority_rows,
        critical_two_flow_certificate_sha256="0" * 64,
        proof_contract_sha256="0" * 64,
    )
    certificate_sha256 = content_sha256(
        _filtered_critical_two_flow_certificate_payload(provisional)
    )
    proof_contract_sha256 = content_sha256({
        "schema": "ztare.filtered_critical_two_flow_proof_contract.v1",
        "theorem_sha256": certificate_sha256,
        "context_sha256": context.context_sha256,
        "evidence_receipt_sha256": [digest for _, digest in receipt_rows],
    })
    return _replay_filtered_critical_two_flow_certificate(replace(
        provisional,
        critical_two_flow_certificate_sha256=certificate_sha256,
        proof_contract_sha256=proof_contract_sha256,
    ))


def _filtered_polar_tensor_context_core(
    context: FilteredPolarTensorContext,
) -> dict[str, object]:
    model = (
        context.model.value
        if isinstance(context.model, FilteredPolarTensorModel)
        else context.model
    )
    return {
        "schema": context.schema,
        "category_id": context.category_id,
        "filtration_id": context.filtration_id,
        "model": model,
        "adapter_evidence_sha256": context.adapter_evidence_sha256,
    }


def _replay_filtered_polar_tensor_context(
    context: FilteredPolarTensorContext,
) -> FilteredPolarTensorContext:
    if context.schema != FILTERED_POLAR_TENSOR_CONTEXT_SCHEMA:
        raise FilteredObstructionError(
            "polar_tensor_context_schema_mismatch",
            "the polar tensor context schema is not recognized",
        )
    if (
        not isinstance(context.category_id, str)
        or not context.category_id.strip()
        or not isinstance(context.filtration_id, str)
        or not context.filtration_id.strip()
    ):
        raise FilteredObstructionError(
            "polar_tensor_context_identity_empty",
            "the polar tensor category and filtration must be nonempty",
        )
    if not isinstance(context.model, FilteredPolarTensorModel):
        raise FilteredObstructionError(
            "polar_tensor_model_unknown",
            "the split tensor representation is not compiler-owned",
        )
    try:
        require_sha256_digest(
            context.adapter_evidence_sha256,
            context="polar tensor adapter evidence",
        )
        require_sha256_digest(
            context.context_sha256,
            context="polar tensor context",
        )
    except ValueError as error:
        raise FilteredObstructionError(
            "invalid_polar_tensor_context_digest",
            str(error),
        ) from error
    expected = content_sha256(_filtered_polar_tensor_context_core(context))
    if context.context_sha256 != expected:
        raise FilteredObstructionError(
            "polar_tensor_context_digest_mismatch",
            "the polar tensor context content does not replay",
        )
    return context


def make_filtered_polar_tensor_context(
    *,
    category_id: str,
    filtration_id: str,
    model: FilteredPolarTensorModel,
    adapter_evidence_sha256: str,
) -> FilteredPolarTensorContext:
    """Create a replayable lowering to one universal split tensor model."""

    provisional = FilteredPolarTensorContext(
        schema=FILTERED_POLAR_TENSOR_CONTEXT_SCHEMA,
        category_id=category_id,
        filtration_id=filtration_id,
        model=model,
        adapter_evidence_sha256=adapter_evidence_sha256,
        context_sha256="0" * 64,
    )
    context = replace(
        provisional,
        context_sha256=content_sha256(
            _filtered_polar_tensor_context_core(provisional)
        ),
    )
    return _replay_filtered_polar_tensor_context(context)


def make_filtered_polar_tensor_evidence(
    *,
    claim: FilteredPolarTensorClaim,
    subject_id: str,
    context: FilteredPolarTensorContext,
    authority: EvidenceAuthority,
    scope: FilteredPolarTensorEvidenceScope,
    evidence_sha256: str,
    critical_terminal_certificate: (
        FilteredCriticalTwoFlowCertificate | None
    ) = None,
) -> ContentBoundEvidenceReceipt:
    """Bind one adapter proposition to the split tensor context."""

    _replay_filtered_polar_tensor_context(context)
    if not isinstance(claim, FilteredPolarTensorClaim):
        raise FilteredObstructionError(
            "polar_tensor_evidence_claim_unknown",
            "the polar tensor evidence claim is not recognized",
        )
    if not isinstance(scope, FilteredPolarTensorEvidenceScope):
        raise FilteredObstructionError(
            "polar_tensor_evidence_scope_unknown",
            "the polar tensor evidence scope is not recognized",
        )
    if claim is FilteredPolarTensorClaim.CRITICAL_TERMINAL_EXCLUDED:
        if critical_terminal_certificate is None:
            raise FilteredObstructionError(
                "polar_tensor_terminal_certificate_missing",
                "terminal evidence must carry a critical two-flow certificate",
            )
        terminal = _replay_filtered_critical_two_flow_certificate(
            critical_terminal_certificate
        )
        conclusion: dict[str, object] = {
            "terminal_certificate_schema": terminal.schema,
            "terminal_context_sha256": terminal.context_sha256,
            "terminal_certificate_sha256": (
                terminal.critical_two_flow_certificate_sha256
            ),
            "critical_terminal_excluded": True,
        }
        if evidence_sha256 != terminal.critical_two_flow_certificate_sha256:
            raise FilteredObstructionError(
                "polar_tensor_terminal_evidence_mismatch",
                "terminal evidence must identify the carried terminal certificate",
            )
    else:
        if critical_terminal_certificate is not None:
            raise FilteredObstructionError(
                "polar_tensor_terminal_certificate_misplaced",
                "only the terminal claim may carry a terminal certificate",
            )
        conclusion = {}
    try:
        return make_content_bound_evidence(
            claim_id=claim.value,
            subject_id=subject_id,
            context_sha256=context.context_sha256,
            authority=authority,
            scope_id=scope.value,
            conclusion=conclusion,
            evidence_sha256=evidence_sha256,
        )
    except ContentBoundEvidenceError as error:
        raise FilteredObstructionError(error.code, str(error)) from error


def compile_filtered_polar_tensor_factorization(
    problem: FilteredPolarTensorFactorizationProblem,
) -> FilteredPolarTensorFactorizationCertificate:
    """Close the maximal-face induction in the split tensor module.

    For ``X=s**(-h)*x**d`` and ``Z=s**nu*x**e``, the leading tensor
    adjoint preserves ``h*e+d*nu`` and changes the lattice point by
    ``(nu,e) -> (nu-h,e+d)``.  Its depth-``k`` coefficient is

        prod_i (2*e+(2*i-3)*d-5).

    A terminating positive-integer start has

        e=(3*d+5)/2-i*d > 0.

    Since ``d>=1``, this forces ``i<4`` and gives at most four resonant
    starting exponents.  The maximal face has only finitely many other
    first-defect Newton seeds, while the critical module has infinite
    support.  A nonresonant seed can therefore be selected on a fresh
    Newton invariant.  The semidirect inverse transfer
    ``z/(1-exp(-z))`` has nonzero coefficients at every positive even
    depth, so that seed produces infinitely many nonzero source-module
    coefficients.  The target cannot absorb them because its module
    coordinate is zero.

    Their parameter-order and payment-degree increments are ``d-h`` and
    ``degree_multiplier*d``.  A positive face is therefore strictly above
    ``threshold`` when the multiplier is at least the threshold.  Removing
    the finitely many positive faces reaches the separately certified
    critical terminal factorization.
    """

    if not problem.name:
        raise FilteredObstructionError(
            "empty_problem_name",
            "polar tensor factorization problem name must be nonempty",
        )
    threshold = _rational(problem.threshold)
    multiplier = _rational(problem.degree_multiplier)
    if threshold <= 0:
        raise FilteredObstructionError(
            "nonpositive_rate_threshold",
            "the asymptotic threshold must be positive",
        )
    if multiplier <= 0 or multiplier < threshold:
        raise FilteredObstructionError(
            "insufficient_polar_tensor_orbit_rate",
            "the degree multiplier must be positive and at least the "
            "declared threshold",
        )
    context = _replay_filtered_polar_tensor_context(problem.context)
    terminal_certificate = _replay_filtered_critical_two_flow_certificate(
        problem.critical_terminal_certificate
    )
    if terminal_certificate.schedule_category_id != context.category_id:
        raise FilteredObstructionError(
            "polar_tensor_terminal_category_mismatch",
            "the critical terminal certificate belongs to another schedule category",
        )
    if context.model is not (
        FilteredPolarTensorModel.WITT_DENSITY_2_NEG3_NEG5
    ):
        raise FilteredObstructionError(
            "polar_tensor_model_has_no_orbit_theorem",
            "the compiler has no orbit theorem for this tensor model",
        )
    required_claims = tuple(FilteredPolarTensorClaim)
    if len(problem.evidence) != len(required_claims):
        raise FilteredObstructionError(
            "polar_tensor_evidence_claim_set_incomplete",
            "polar tensor factorization needs exactly three proposition receipts",
        )
    receipts: dict[
        FilteredPolarTensorClaim,
        ContentBoundEvidenceReceipt,
    ] = {}
    for carried in problem.evidence:
        try:
            receipt = replay_content_bound_evidence(carried)
        except ContentBoundEvidenceError as error:
            raise FilteredObstructionError(error.code, str(error)) from error
        try:
            claim = FilteredPolarTensorClaim(receipt.claim_id)
        except ValueError as error:
            raise FilteredObstructionError(
                "polar_tensor_evidence_claim_unknown",
                f"unknown polar tensor evidence claim {receipt.claim_id!r}",
            ) from error
        if claim in receipts:
            raise FilteredObstructionError(
                "polar_tensor_evidence_claim_duplicate",
                f"polar tensor claim {claim.value!r} occurs more than once",
            )
        if receipt.context_sha256 != context.context_sha256:
            raise FilteredObstructionError(
                "polar_tensor_evidence_context_mismatch",
                f"polar tensor claim {claim.value!r} belongs to another context",
            )
        if receipt.authority is EvidenceAuthority.FINITE_EXPERIMENT:
            raise FilteredObstructionError(
                "polar_tensor_evidence_authority_insufficient",
                f"finite experiment authority cannot discharge {claim.value!r}",
            )
        receipts[claim] = receipt
    if set(receipts) != set(required_claims):
        raise FilteredObstructionError(
            "polar_tensor_evidence_claim_set_incomplete",
            "polar tensor evidence does not cover the exact required claim set",
        )
    subjects = [receipts[claim].subject_id for claim in required_claims]
    if len(subjects) != len(set(subjects)):
        raise FilteredObstructionError(
            "polar_tensor_evidence_subject_reused",
            "distinct polar tensor claims need distinct proposition subjects",
        )
    expected_scopes = {
        FilteredPolarTensorClaim.FINITE_MAXIMAL_FACE_DECOMPOSITION: (
            FilteredPolarTensorEvidenceScope.ALL_FINITE_POSITIVE_FACES
        ),
        FilteredPolarTensorClaim.CRITICAL_MODULE_INFINITE_SUPPORT: (
            FilteredPolarTensorEvidenceScope.ALL_CRITICAL_MODULE_ORDERS
        ),
        FilteredPolarTensorClaim.CRITICAL_TERMINAL_EXCLUDED: (
            FilteredPolarTensorEvidenceScope.ZERO_POSITIVE_FACE_TERMINAL
        ),
    }
    for claim in required_claims:
        receipt = receipts[claim]
        if receipt.scope_id != expected_scopes[claim].value:
            raise FilteredObstructionError(
                "polar_tensor_evidence_scope_mismatch",
                f"polar tensor claim {claim.value!r} has scope "
                f"{receipt.scope_id!r}, expected {expected_scopes[claim].value!r}",
            )
        expected_conclusion: dict[str, object] = {}
        if claim is FilteredPolarTensorClaim.CRITICAL_TERMINAL_EXCLUDED:
            expected_conclusion = {
                "terminal_certificate_schema": terminal_certificate.schema,
                "terminal_context_sha256": terminal_certificate.context_sha256,
                "terminal_certificate_sha256": (
                    terminal_certificate.critical_two_flow_certificate_sha256
                ),
                "critical_terminal_excluded": True,
            }
        if receipt.conclusion() != expected_conclusion:
            raise FilteredObstructionError(
                "polar_tensor_evidence_conclusion_malformed",
                "the polar tensor receipt names the wrong proposition",
            )

    face_receipt = receipts[
        FilteredPolarTensorClaim.FINITE_MAXIMAL_FACE_DECOMPOSITION
    ]
    adapter_digest = context.adapter_evidence_sha256
    if face_receipt.evidence_sha256 != adapter_digest:
        raise FilteredObstructionError(
            "polar_tensor_face_adapter_mismatch",
            "the maximal-face proposition must be owned by the context adapter",
        )
    module_digest = receipts[
        FilteredPolarTensorClaim.CRITICAL_MODULE_INFINITE_SUPPORT
    ].evidence_sha256
    terminal_digest = receipts[
        FilteredPolarTensorClaim.CRITICAL_TERMINAL_EXCLUDED
    ].evidence_sha256
    if terminal_digest != (
        terminal_certificate.critical_two_flow_certificate_sha256
    ):
        raise FilteredObstructionError(
            "polar_tensor_terminal_evidence_mismatch",
            "the terminal receipt does not identify the carried certificate",
        )
    rate_formula = f"{multiplier}*d/(d-h)"
    payload = {
        "problem": problem.name,
        "threshold": str(threshold),
        "degree_multiplier": str(multiplier),
        "tensor_action": "2*x*A*J'-3*x*A'*J-5*A*J",
        "monomial_orbit_coefficient": (
            "prod_(i=0)^(k-1)(2*e+(2*i-3)*d-5)"
        ),
        "newton_invariant": "h*e+d*nu",
        "maximum_resonant_start_exponents": 4,
        "semidirect_transfer": "z/(1-exp(-z))",
        "target_factor_module_zero": True,
        "orbit_order_increment": "d-h>0",
        "orbit_payment_degree_increment": f"{multiplier}*d",
        "orbit_rate_formula": rate_formula,
        "strict_rate_excess": (
            f"({multiplier}-{threshold})*d+{threshold}*h>0"
        ),
        "critical_terminal_factorization_excluded": True,
        "adapter_certificate_sha256": adapter_digest,
        "critical_module_certificate_sha256": module_digest,
        "critical_terminal_certificate_sha256": terminal_digest,
    }
    certificate_sha256 = content_sha256(payload)
    proof_payload = {
        "schema": "ztare.filtered_polar_tensor_proof_contract.v1",
        "theorem_sha256": certificate_sha256,
        "context_sha256": context.context_sha256,
        "evidence_receipt_sha256": [
            receipts[claim].receipt_sha256 for claim in required_claims
        ],
    }
    proof_contract_sha256 = content_sha256(proof_payload)
    return FilteredPolarTensorFactorizationCertificate(
        schema="ztare.filtered_polar_tensor_factorization_certificate.v3",
        problem_name=problem.name,
        threshold=str(threshold),
        degree_multiplier=str(multiplier),
        tensor_action="rho(A)J=2*x*A*J'-3*x*A'*J-5*A*J",
        monomial_orbit_coefficient=(
            "prod_(i=0)^(k-1)(2*e+(2*i-3)*d-5)"
        ),
        newton_invariant="h*e+d*nu",
        maximum_resonant_start_exponents=4,
        infinite_support_has_nonresonant_seed=True,
        semidirect_transfer="z/(1-exp(-z))",
        target_module_vanishes=True,
        orbit_order_increment="d-h>0",
        orbit_payment_degree_increment=f"{multiplier}*d",
        orbit_rate_formula=rate_formula,
        positive_face_branch_strictly_supercritical=True,
        finite_positive_prefix_induction_closed=True,
        critical_terminal_factorization_excluded=True,
        strict_subthreshold_factorization_excluded=True,
        adapter_completeness_inferred=False,
        adapter_certificate_sha256=adapter_digest,
        critical_module_certificate_sha256=module_digest,
        critical_terminal_certificate_sha256=terminal_digest,
        context_sha256=context.context_sha256,
        model=context.model.value,
        evidence_receipt_sha256=tuple(
            (claim.value, receipts[claim].receipt_sha256)
            for claim in required_claims
        ),
        evidence_authority=tuple(
            (claim.value, receipts[claim].authority.value)
            for claim in required_claims
        ),
        polar_tensor_certificate_sha256=certificate_sha256,
        proof_contract_sha256=proof_contract_sha256,
    )


def _filtered_critical_support_context_core(
    context: FilteredCriticalSupportContext,
) -> dict[str, object]:
    return {
        "schema": context.schema,
        "category_id": context.category_id,
        "support_id": context.support_id,
        "cost_id": context.cost_id,
        "slope": context.slope,
        "adapter_evidence_sha256": context.adapter_evidence_sha256,
        "compiler_kernel_sha256": context.compiler_kernel_sha256,
    }


def _replay_filtered_critical_support_context(
    context: FilteredCriticalSupportContext,
) -> FilteredCriticalSupportContext:
    if context.schema != FILTERED_CRITICAL_SUPPORT_CONTEXT_SCHEMA:
        raise FilteredObstructionError(
            "critical_support_context_schema_mismatch",
            "the critical-support context schema is not recognized",
        )
    for field_name in ("category_id", "support_id", "cost_id"):
        value = getattr(context, field_name)
        if not isinstance(value, str) or not value.strip():
            raise FilteredObstructionError(
                "critical_support_context_identity_empty",
                f"critical-support {field_name} must be nonempty",
            )
    slope = _rational(context.slope)
    if slope <= 0:
        raise FilteredObstructionError(
            "critical_support_slope_nonpositive",
            "the critical-support slope must be positive",
        )
    if context.slope != str(slope):
        raise FilteredObstructionError(
            "critical_support_slope_not_canonical",
            "the critical-support slope must use canonical rational syntax",
        )
    try:
        require_sha256_digest(
            context.adapter_evidence_sha256,
            context="critical-support adapter evidence",
        )
        require_sha256_digest(
            context.compiler_kernel_sha256,
            context="critical-support compiler kernel",
        )
        require_sha256_digest(
            context.context_sha256,
            context="critical-support context",
        )
    except ValueError as error:
        raise FilteredObstructionError(
            "invalid_critical_support_context_digest",
            str(error),
        ) from error
    expected = content_sha256(
        _filtered_critical_support_context_core(context)
    )
    if context.context_sha256 != expected:
        raise FilteredObstructionError(
            "critical_support_context_digest_mismatch",
            "the critical-support context content does not replay",
        )
    return context


def make_filtered_critical_support_context(
    *,
    category_id: str,
    support_id: str,
    cost_id: str,
    slope: RationalInput,
    adapter_evidence_sha256: str,
    compiler_kernel_sha256: str,
) -> FilteredCriticalSupportContext:
    """Create one replayable critical support/cost comparison identity."""

    provisional = FilteredCriticalSupportContext(
        schema=FILTERED_CRITICAL_SUPPORT_CONTEXT_SCHEMA,
        category_id=category_id,
        support_id=support_id,
        cost_id=cost_id,
        slope=str(_rational(slope)),
        adapter_evidence_sha256=adapter_evidence_sha256,
        compiler_kernel_sha256=compiler_kernel_sha256,
        context_sha256="0" * 64,
    )
    context = replace(
        provisional,
        context_sha256=content_sha256(
            _filtered_critical_support_context_core(provisional)
        ),
    )
    return _replay_filtered_critical_support_context(context)


def make_filtered_critical_support_evidence(
    *,
    claim: FilteredCriticalSupportClaim,
    subject_id: str,
    context: FilteredCriticalSupportContext,
    authority: EvidenceAuthority,
    scope: FilteredCriticalSupportEvidenceScope,
    evidence_sha256: str,
) -> ContentBoundEvidenceReceipt:
    """Bind one of the two non-substitutable critical-support arrows."""

    _replay_filtered_critical_support_context(context)
    if not isinstance(claim, FilteredCriticalSupportClaim):
        raise FilteredObstructionError(
            "critical_support_evidence_claim_unknown",
            "the critical-support evidence claim is not recognized",
        )
    if not isinstance(scope, FilteredCriticalSupportEvidenceScope):
        raise FilteredObstructionError(
            "critical_support_evidence_scope_unknown",
            "the critical-support evidence scope is not recognized",
        )
    relation = {
        FilteredCriticalSupportClaim.STRICT_TAIL_BOUND: (
            "cost_lt_slope_times_row_eventually"
        ),
        FilteredCriticalSupportClaim.SUPPORT_TO_COST_CHARGE: (
            "support_implies_slope_times_row_le_cost"
        ),
    }[claim]
    try:
        return make_content_bound_evidence(
            claim_id=claim.value,
            subject_id=subject_id,
            context_sha256=context.context_sha256,
            authority=authority,
            scope_id=scope.value,
            conclusion={"relation": relation, "slope": context.slope},
            evidence_sha256=evidence_sha256,
        )
    except ContentBoundEvidenceError as error:
        raise FilteredObstructionError(error.code, str(error)) from error


def compile_filtered_critical_support(
    problem: FilteredCriticalSupportProblem,
) -> FilteredCriticalSupportCertificate:
    """Compose strict tail and support charge into finite critical support."""

    if not problem.name:
        raise FilteredObstructionError(
            "empty_problem_name",
            "critical-support problem name must be nonempty",
        )
    context = _replay_filtered_critical_support_context(problem.context)
    required_claims = tuple(FilteredCriticalSupportClaim)
    if len(problem.evidence) != len(required_claims):
        raise FilteredObstructionError(
            "critical_support_evidence_claim_set_incomplete",
            "critical-support compilation needs both typed arrows",
        )
    receipts: dict[
        FilteredCriticalSupportClaim, ContentBoundEvidenceReceipt
    ] = {}
    for carried in problem.evidence:
        try:
            receipt = replay_content_bound_evidence(carried)
        except ContentBoundEvidenceError as error:
            raise FilteredObstructionError(error.code, str(error)) from error
        try:
            claim = FilteredCriticalSupportClaim(receipt.claim_id)
        except ValueError as error:
            raise FilteredObstructionError(
                "critical_support_evidence_claim_unknown",
                f"unknown critical-support claim {receipt.claim_id!r}",
            ) from error
        if claim in receipts:
            raise FilteredObstructionError(
                "critical_support_evidence_claim_duplicate",
                f"critical-support claim {claim.value!r} occurs twice",
            )
        if receipt.context_sha256 != context.context_sha256:
            raise FilteredObstructionError(
                "critical_support_evidence_context_mismatch",
                f"critical-support claim {claim.value!r} has another context",
            )
        if receipt.authority is EvidenceAuthority.FINITE_EXPERIMENT:
            raise FilteredObstructionError(
                "critical_support_evidence_authority_insufficient",
                "finite experiments cannot certify an all-row implication",
            )
        receipts[claim] = receipt
    if set(receipts) != set(required_claims):
        raise FilteredObstructionError(
            "critical_support_evidence_claim_set_incomplete",
            "critical-support evidence does not cover both typed arrows",
        )
    if len({receipt.subject_id for receipt in receipts.values()}) != 2:
        raise FilteredObstructionError(
            "critical_support_evidence_subject_reused",
            "strict-tail and support-charge arrows need distinct subjects",
        )
    expected_scopes = {
        FilteredCriticalSupportClaim.STRICT_TAIL_BOUND:
            FilteredCriticalSupportEvidenceScope.ALL_EVENTUAL_TAIL_ROWS,
        FilteredCriticalSupportClaim.SUPPORT_TO_COST_CHARGE:
            FilteredCriticalSupportEvidenceScope.ALL_CRITICAL_SUPPORT_ROWS,
    }
    expected_relations = {
        FilteredCriticalSupportClaim.STRICT_TAIL_BOUND:
            "cost_lt_slope_times_row_eventually",
        FilteredCriticalSupportClaim.SUPPORT_TO_COST_CHARGE:
            "support_implies_slope_times_row_le_cost",
    }
    for claim in required_claims:
        receipt = receipts[claim]
        if receipt.scope_id != expected_scopes[claim].value:
            raise FilteredObstructionError(
                "critical_support_evidence_scope_mismatch",
                f"critical-support claim {claim.value!r} has wrong scope",
            )
        if receipt.conclusion() != {
            "relation": expected_relations[claim],
            "slope": context.slope,
        }:
            raise FilteredObstructionError(
                "critical_support_evidence_conclusion_mismatch",
                f"critical-support claim {claim.value!r} changed relation",
            )
    evidence_rows = tuple(
        (claim.value, receipts[claim].receipt_sha256)
        for claim in required_claims
    )
    authority_rows = tuple(
        (claim.value, receipts[claim].authority.value)
        for claim in required_claims
    )
    adapter_digest = content_sha256({
        "context_sha256": context.context_sha256,
        "evidence_receipt_sha256": evidence_rows,
    })
    proof_contract_sha256 = content_sha256({
        "compiler_kernel_sha256": context.compiler_kernel_sha256,
        "strict_tail_arrow": evidence_rows[0],
        "support_to_cost_arrow": evidence_rows[1],
        "consequence": "eventual_vanishing_and_finite_support",
        "premise_removal_control": "cheap_infinite_support",
    })
    certificate_core = {
        "schema": "ztare.filtered_critical_support_certificate.v1",
        "problem_name": problem.name,
        "category_id": context.category_id,
        "support_id": context.support_id,
        "cost_id": context.cost_id,
        "slope": context.slope,
        "eventual_critical_support_vanishing": True,
        "critical_support_finite": True,
        "infinite_support_forces_late_threshold_cost": True,
        "strict_tail_alone_implies_finite_support": False,
        "premise_removal_countermodel_accepted": True,
        "adapter_completeness_inferred": False,
        "adapter_evidence_sha256": adapter_digest,
        "compiler_kernel_sha256": context.compiler_kernel_sha256,
        "context_sha256": context.context_sha256,
        "evidence_receipt_sha256": evidence_rows,
        "evidence_authority": authority_rows,
        "proof_contract_sha256": proof_contract_sha256,
    }
    certificate_sha256 = content_sha256(certificate_core)
    return FilteredCriticalSupportCertificate(
        **certificate_core,
        critical_support_certificate_sha256=certificate_sha256,
    )


def _filtered_tail_context_core(
    context: FilteredTailContext,
) -> dict[str, object]:
    occurrence_order = (
        context.occurrence_order.value
        if isinstance(context.occurrence_order, FilteredTailOccurrenceOrder)
        else context.occurrence_order
    )
    return {
        "schema": context.schema,
        "category_id": context.category_id,
        "statistic_id": context.statistic_id,
        "occurrence_order": occurrence_order,
        "adapter_evidence_sha256": context.adapter_evidence_sha256,
    }


def _replay_filtered_tail_context(
    context: FilteredTailContext,
) -> FilteredTailContext:
    if context.schema != FILTERED_TAIL_CONTEXT_SCHEMA:
        raise FilteredObstructionError(
            "tail_context_schema_mismatch",
            "the tail context schema is not recognized",
        )
    if (
        not isinstance(context.category_id, str)
        or not context.category_id.strip()
        or not isinstance(context.statistic_id, str)
        or not context.statistic_id.strip()
    ):
        raise FilteredObstructionError(
            "tail_context_identity_empty",
            "the tail category and statistic identities must be nonempty",
        )
    if not isinstance(
        context.occurrence_order,
        FilteredTailOccurrenceOrder,
    ):
        raise FilteredObstructionError(
            "tail_occurrence_order_unknown",
            "the occurrence order is not a compiler-owned well-order",
        )
    try:
        require_sha256_digest(
            context.adapter_evidence_sha256,
            context="tail adapter evidence",
        )
        require_sha256_digest(
            context.context_sha256,
            context="tail context",
        )
    except ValueError as error:
        raise FilteredObstructionError(
            "invalid_tail_context_digest",
            str(error),
        ) from error
    expected = content_sha256(_filtered_tail_context_core(context))
    if context.context_sha256 != expected:
        raise FilteredObstructionError(
            "tail_context_digest_mismatch",
            "the tail context content does not replay",
        )
    return context


def make_filtered_tail_context(
    *,
    category_id: str,
    statistic_id: str,
    occurrence_order: FilteredTailOccurrenceOrder,
    adapter_evidence_sha256: str,
) -> FilteredTailContext:
    """Create one replayable category/statistic identity for tail evidence."""

    provisional = FilteredTailContext(
        schema=FILTERED_TAIL_CONTEXT_SCHEMA,
        category_id=category_id,
        statistic_id=statistic_id,
        occurrence_order=occurrence_order,
        adapter_evidence_sha256=adapter_evidence_sha256,
        context_sha256="0" * 64,
    )
    context = replace(
        provisional,
        context_sha256=content_sha256(_filtered_tail_context_core(provisional)),
    )
    return _replay_filtered_tail_context(context)


def make_filtered_tail_evidence(
    *,
    claim: FilteredTailClaim,
    subject_id: str,
    context: FilteredTailContext,
    bound: RationalInput,
    authority: EvidenceAuthority,
    scope: FilteredTailEvidenceScope,
    evidence_sha256: str,
) -> ContentBoundEvidenceReceipt:
    """Bind one tail bound to its exact subject and mathematical context."""

    _replay_filtered_tail_context(context)
    if not isinstance(claim, FilteredTailClaim):
        raise FilteredObstructionError(
            "tail_evidence_claim_unknown",
            "the tail evidence claim is not recognized",
        )
    if not isinstance(scope, FilteredTailEvidenceScope):
        raise FilteredObstructionError(
            "tail_evidence_scope_unknown",
            "the tail evidence scope is not recognized",
        )
    try:
        return make_content_bound_evidence(
            claim_id=claim.value,
            subject_id=subject_id,
            context_sha256=context.context_sha256,
            authority=authority,
            scope_id=scope.value,
            conclusion={"bound": str(_rational(bound))},
            evidence_sha256=evidence_sha256,
        )
    except ContentBoundEvidenceError as error:
        raise FilteredObstructionError(error.code, str(error)) from error


def compile_filtered_tail_minimax_composition(
    problem: FilteredTailMinimaxCompositionProblem,
) -> FilteredTailMinimaxCompositionCertificate:
    """Compose an exact two-branch tail theorem from replayed evidence.

    For the recognized natural-parameter/positive-grade lexicographic order,
    the core derives the exhaustive alternative: positive support is empty,
    or it has a least occurrence.  The caller supplies no exhaustiveness,
    compatibility, all-order, prefix-uniformity, or admissibility Booleans.
    Those propositions are carried by an exact receipt set and checked by
    identity, scope, authority, context, and rational conclusion.
    """

    if not problem.name:
        raise FilteredObstructionError(
            "empty_problem_name",
            "tail minimax composition problem name must be nonempty",
        )
    threshold = _rational(problem.threshold)
    if threshold < 0:
        raise FilteredObstructionError(
            "negative_tail_threshold",
            "the composed tail threshold must be nonnegative",
        )
    context = _replay_filtered_tail_context(problem.context)
    if context.occurrence_order is not (
        FilteredTailOccurrenceOrder.NAT_PARAMETER_POSITIVE_GRADE_LEX
    ):
        raise FilteredObstructionError(
            "tail_occurrence_order_has_no_partition_theorem",
            "the compiler has no exhaustive partition theorem for this order",
        )

    required_claims = tuple(FilteredTailClaim)
    if len(problem.evidence) != len(required_claims):
        raise FilteredObstructionError(
            "tail_evidence_claim_set_incomplete",
            "tail composition needs exactly one receipt for each required claim",
        )
    receipts: dict[
        FilteredTailClaim,
        ContentBoundEvidenceReceipt,
    ] = {}
    for carried in problem.evidence:
        try:
            receipt = replay_content_bound_evidence(carried)
        except ContentBoundEvidenceError as error:
            raise FilteredObstructionError(error.code, str(error)) from error
        try:
            claim = FilteredTailClaim(receipt.claim_id)
        except ValueError as error:
            raise FilteredObstructionError(
                "tail_evidence_claim_unknown",
                f"unknown tail evidence claim {receipt.claim_id!r}",
            ) from error
        if claim in receipts:
            raise FilteredObstructionError(
                "tail_evidence_claim_duplicate",
                f"tail evidence claim {claim.value!r} occurs more than once",
            )
        if receipt.context_sha256 != context.context_sha256:
            raise FilteredObstructionError(
                "tail_evidence_context_mismatch",
                f"tail evidence claim {claim.value!r} belongs to another context",
            )
        if receipt.authority is EvidenceAuthority.FINITE_EXPERIMENT:
            raise FilteredObstructionError(
                "tail_evidence_authority_insufficient",
                f"finite experiment authority cannot discharge {claim.value!r}",
            )
        receipts[claim] = receipt
    if set(receipts) != set(required_claims):
        raise FilteredObstructionError(
            "tail_evidence_claim_set_incomplete",
            "tail evidence does not cover the exact required claim set",
        )
    subjects = [receipts[claim].subject_id for claim in required_claims]
    if len(subjects) != len(set(subjects)):
        raise FilteredObstructionError(
            "tail_evidence_subject_reused",
            "distinct tail claims need distinct proposition subjects",
        )

    expected_scopes = {
        FilteredTailClaim.PURE_BRANCH_LOWER: (
            FilteredTailEvidenceScope.ALL_ORDER_FINITE_PREFIX_UNIFORM
        ),
        FilteredTailClaim.LEAST_POSITIVE_BRANCH_LOWER: (
            FilteredTailEvidenceScope.ALL_ORDER_FINITE_PREFIX_UNIFORM
        ),
        FilteredTailClaim.ADMISSIBLE_UPPER: (
            FilteredTailEvidenceScope.ADMISSIBLE_ALL_ORDER_CONSTRUCTION
        ),
    }
    bounds: dict[FilteredTailClaim, sp.Rational] = {}
    for claim in required_claims:
        receipt = receipts[claim]
        if receipt.scope_id != expected_scopes[claim].value:
            raise FilteredObstructionError(
                "tail_evidence_scope_mismatch",
                f"tail evidence claim {claim.value!r} has scope "
                f"{receipt.scope_id!r}, expected {expected_scopes[claim].value!r}",
            )
        conclusion = receipt.conclusion()
        if set(conclusion) != {"bound"}:
            raise FilteredObstructionError(
                "tail_evidence_conclusion_malformed",
                f"tail evidence claim {claim.value!r} must conclude one bound",
            )
        bounds[claim] = _rational(conclusion["bound"])

    pure_lower = bounds[FilteredTailClaim.PURE_BRANCH_LOWER]
    positive_lower = bounds[
        FilteredTailClaim.LEAST_POSITIVE_BRANCH_LOWER
    ]
    upper = bounds[FilteredTailClaim.ADMISSIBLE_UPPER]
    if pure_lower < threshold:
        raise FilteredObstructionError(
            "pure_tail_lower_bound_too_weak",
            "the pure branch lower bound is below the declared threshold",
        )
    if positive_lower < threshold:
        raise FilteredObstructionError(
            "least_positive_tail_lower_bound_too_weak",
            "the least-positive branch lower bound is below the threshold",
        )
    if upper != threshold:
        raise FilteredObstructionError(
            "tail_upper_bound_does_not_match_threshold",
            "the admissible upper construction must match the lower threshold",
        )

    pure_digest = receipts[
        FilteredTailClaim.PURE_BRANCH_LOWER
    ].evidence_sha256
    positive_digest = receipts[
        FilteredTailClaim.LEAST_POSITIVE_BRANCH_LOWER
    ].evidence_sha256
    upper_digest = receipts[
        FilteredTailClaim.ADMISSIBLE_UPPER
    ].evidence_sha256
    adapter_digest = context.adapter_evidence_sha256
    theorem_payload = {
        "problem": problem.name,
        "threshold": str(threshold),
        "branch_partition": [
            "positive_support_empty",
            "least_positive_occurrence",
        ],
        "pure_branch_lower_bound": str(pure_lower),
        "least_positive_branch_lower_bound": str(positive_lower),
        "upper_construction_bound": str(upper),
        "statistics_and_category_compatible": True,
        "all_lower_branches_all_order": True,
        "finite_prefix_uniform": True,
        "upper_construction_admissible": True,
        "pure_branch_certificate_sha256": pure_digest,
        "least_positive_branch_certificate_sha256": positive_digest,
        "upper_construction_certificate_sha256": upper_digest,
        "adapter_certificate_sha256": adapter_digest,
    }
    theorem_sha256 = content_sha256(theorem_payload)
    proof_payload = {
        "schema": "ztare.filtered_tail_minimax_proof_contract.v1",
        "theorem_sha256": theorem_sha256,
        "context_sha256": context.context_sha256,
        "evidence_receipt_sha256": [
            receipts[claim].receipt_sha256 for claim in required_claims
        ],
    }
    proof_contract_sha256 = content_sha256(proof_payload)
    return FilteredTailMinimaxCompositionCertificate(
        schema="ztare.filtered_tail_minimax_composition_certificate.v2",
        problem_name=problem.name,
        threshold=str(threshold),
        branch_partition=(
            "positive_support_empty",
            "least_positive_occurrence",
        ),
        branch_partition_exhaustive=True,
        pure_branch_lower_bound=str(pure_lower),
        least_positive_branch_lower_bound=str(positive_lower),
        unrestricted_lower_bound=str(threshold),
        upper_construction_bound=str(upper),
        unrestricted_minimax_value=str(threshold),
        statistics_and_category_compatible=True,
        all_lower_branches_all_order=True,
        finite_prefix_uniform=True,
        upper_construction_admissible=True,
        adapter_completeness_inferred=False,
        pure_branch_certificate_sha256=pure_digest,
        least_positive_branch_certificate_sha256=positive_digest,
        upper_construction_certificate_sha256=upper_digest,
        adapter_certificate_sha256=adapter_digest,
        context_sha256=context.context_sha256,
        occurrence_order=context.occurrence_order.value,
        evidence_receipt_sha256=tuple(
            (claim.value, receipts[claim].receipt_sha256)
            for claim in required_claims
        ),
        evidence_authority=tuple(
            (claim.value, receipts[claim].authority.value)
            for claim in required_claims
        ),
        tail_minimax_certificate_sha256=theorem_sha256,
        proof_contract_sha256=proof_contract_sha256,
    )


def compile_filtered_quadratic_differential_obstruction(
    problem: FilteredQuadraticDifferentialProblem,
) -> FilteredQuadraticDifferentialCertificate:
    """Exclude polynomial solutions of a separated quadratic ODE.

    The two supplied rows are exact rational equations for ``(k', k)``.
    A nonzero determinant gives a unique rational candidate pair.  The core
    then checks whether the first component is the derivative of the second.
    A mismatch excludes rational solutions; a compatible unique candidate
    with a nonconstant denominator still excludes polynomial solutions.
    """

    if not problem.name:
        raise FilteredObstructionError(
            "empty_problem_name",
            "quadratic differential problem name must be nonempty",
        )
    if (
        not isinstance(problem.variable, str)
        or not problem.variable
        or not problem.variable.isidentifier()
    ):
        raise FilteredObstructionError(
            "invalid_differential_variable",
            "the differential variable must be a nonempty identifier",
        )
    variable = sp.Symbol(problem.variable)

    def parse_rational(expression: str, *, label: str) -> sp.Expr:
        if not isinstance(expression, str) or not expression:
            raise FilteredObstructionError(
                "invalid_rational_function",
                f"{label} must be a nonempty exact expression",
            )
        try:
            value = sp.cancel(sp.sympify(
                expression,
                locals={problem.variable: variable},
                rational=True,
            ))
            if value.free_symbols - {variable}:
                raise ValueError("unexpected free symbol")
            numerator, denominator = value.as_numer_denom()
            sp.Poly(numerator, variable, domain=sp.QQ)
            sp.Poly(denominator, variable, domain=sp.QQ)
        except Exception as error:
            raise FilteredObstructionError(
                "invalid_rational_function",
                f"{label} is not in QQ({problem.variable})",
            ) from error
        return value

    if len(problem.rational_row) != 3 or len(problem.radical_row) != 3:
        raise FilteredObstructionError(
            "invalid_differential_row",
            "each quadratic differential row needs coefficients (A,B,C)",
        )
    rational_row = tuple(
        parse_rational(value, label=f"rational row entry {index}")
        for index, value in enumerate(problem.rational_row)
    )
    radical_row = tuple(
        parse_rational(value, label=f"radical row entry {index}")
        for index, value in enumerate(problem.radical_row)
    )
    a0, b0, c0 = rational_row
    a1, b1, c1 = radical_row
    determinant = sp.factor(sp.cancel(a0 * b1 - a1 * b0))
    if determinant == 0:
        raise FilteredObstructionError(
            "singular_quadratic_differential_rows",
            "the two separated rows do not determine (k',k)",
        )
    candidate_derivative = sp.factor(sp.cancel(
        (c0 * b1 - c1 * b0) / determinant
    ))
    candidate = sp.factor(sp.cancel(
        (a0 * c1 - a1 * c0) / determinant
    ))
    compatibility = sp.factor(sp.cancel(
        sp.diff(candidate, variable) - candidate_derivative
    ))
    candidate_denominator = sp.Poly(
        candidate.as_numer_denom()[1], variable, domain=sp.QQ
    )
    candidate_nonpolynomial = candidate_denominator.degree() > 0
    rational_excluded = compatibility != 0
    polynomial_excluded = rational_excluded or candidate_nonpolynomial
    if not polynomial_excluded:
        raise FilteredObstructionError(
            "polynomial_differential_solution_not_excluded",
            "the separated rows have a compatible polynomial candidate",
        )

    adapter_digest = problem.adapter_certificate_sha256
    if (
        not isinstance(adapter_digest, str)
        or len(adapter_digest) != 64
        or any(
            character not in "0123456789abcdef"
            for character in adapter_digest
        )
    ):
        raise FilteredObstructionError(
            "invalid_quadratic_differential_digest",
            "the adapter needs a lowercase SHA-256 digest",
        )

    def expression_digest(expression: sp.Expr) -> str:
        return hashlib.sha256(
            str(sp.factor(expression)).encode()
        ).hexdigest()

    determinant_numerator = determinant.as_numer_denom()[0]
    compatibility_numerator = (
        None if compatibility == 0 else compatibility.as_numer_denom()[0]
    )
    determinant_digest = expression_digest(determinant)
    compatibility_digest = expression_digest(compatibility)
    candidate_digest = expression_digest(candidate)
    payload = {
        "problem": problem.name,
        "variable": problem.variable,
        "determinant_sha256": determinant_digest,
        "compatibility_sha256": compatibility_digest,
        "candidate_sha256": candidate_digest,
        "derivative_compatibility_nonzero": compatibility != 0,
        "candidate_rational_not_polynomial": candidate_nonpolynomial,
        "rational_solution_excluded": rational_excluded,
        "polynomial_solution_excluded": polynomial_excluded,
        "adapter_certificate_sha256": adapter_digest,
    }
    certificate_sha256 = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return FilteredQuadraticDifferentialCertificate(
        schema=(
            "ztare.filtered_quadratic_differential_certificate.v1"
        ),
        problem_name=problem.name,
        variable=problem.variable,
        determinant_nonzero=True,
        rational_candidate_unique=True,
        derivative_compatibility_nonzero=compatibility != 0,
        candidate_rational_not_polynomial=candidate_nonpolynomial,
        rational_solution_excluded=rational_excluded,
        polynomial_solution_excluded=polynomial_excluded,
        determinant_numerator_degree=sp.Poly(
            determinant_numerator, variable, domain=sp.QQ
        ).degree(),
        compatibility_numerator_degree=(
            None
            if compatibility_numerator is None
            else sp.Poly(
                compatibility_numerator, variable, domain=sp.QQ
            ).degree()
        ),
        candidate_denominator_degree=candidate_denominator.degree(),
        determinant_sha256=determinant_digest,
        compatibility_sha256=compatibility_digest,
        candidate_sha256=candidate_digest,
        adapter_completeness_inferred=False,
        adapter_certificate_sha256=adapter_digest,
        quadratic_differential_certificate_sha256=certificate_sha256,
    )
