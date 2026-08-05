"""Exact rational linear-system certificates with modular pivot selection.

Finite-field arithmetic is used only to select candidate pivot rows and
columns.  Consistency, inconsistency, particular solutions, and affine
kernels are all verified over the rationals against every original row.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from math import gcd

import sympy as sp
from sympy.polys.domains import GF, QQ
from sympy.polys.matrices import DomainMatrix


class ExactLinearCertificateError(RuntimeError):
    """The selected modular pivots did not lift to the requested proof."""


@dataclass(frozen=True)
class InconsistencyCertificate:
    """A rational dependent-row functional with a nonzero RHS residual."""

    prime_used_only_for_pivot_selection: int
    matrix_shape: tuple[int, int]
    rational_row_rank: int
    pivot_row_count: int
    pivot_column_count: int
    dependent_row: int
    rational_rhs_residual: str
    rational_row_relation_verified: bool
    rational_rhs_residual_nonzero: bool
    matrix_sha256: str
    rhs_sha256: str

    def to_dict(self) -> dict[str, object]:
        result = asdict(self)
        result["matrix_shape"] = list(self.matrix_shape)
        return result


@dataclass(frozen=True)
class AffineSolutionCertificate:
    """A complete rational particular solution and homogeneous kernel."""

    prime_used_only_for_pivot_selection: int
    matrix_shape: tuple[int, int]
    rational_rank: int
    affine_dimension: int
    multi_rhs_count: int
    complete_particular_replay: bool
    complete_kernel_replay: bool
    matrix_sha256: str
    rhs_sha256: str

    def to_dict(self) -> dict[str, object]:
        result = asdict(self)
        result["matrix_shape"] = list(self.matrix_shape)
        return result


@dataclass(frozen=True)
class ParticularSolutionCertificate:
    """One rational solution verified against every original row."""

    prime_used_only_for_pivot_selection: int
    matrix_shape: tuple[int, int]
    selected_pivot_rank: int
    pivot_row_count: int
    pivot_column_count: int
    rational_square_solve_verified: bool
    complete_rational_row_replay_verified: bool
    nonzero_solution_coordinates: int
    matrix_sha256: str
    rhs_sha256: str

    def to_dict(self) -> dict[str, object]:
        result = asdict(self)
        result["matrix_shape"] = list(self.matrix_shape)
        return result


@dataclass(frozen=True)
class ColumnSeparationCertificate:
    """An exact row functional separating a vector from a column span."""

    matrix_shape: tuple[int, int]
    rational_column_rank: int
    left_nullity: int
    primitive_witness: tuple[str, ...]
    rational_pairing: str
    complete_annihilation_replay: bool
    rational_pairing_nonzero: bool
    matrix_sha256: str
    vector_sha256: str

    def to_dict(self) -> dict[str, object]:
        result = asdict(self)
        result["matrix_shape"] = list(self.matrix_shape)
        result["primitive_witness"] = list(self.primitive_witness)
        return result


def sparse_matrix_sha256(matrix: DomainMatrix) -> str:
    """Hash shape and nonzero rational entries in deterministic order."""

    rational = _to_rational_domain(matrix)
    sparse_entries = sorted(
        (row, column, str(value))
        for (row, column), value in rational.to_dok().items()
    )
    payload = {
        "shape": list(rational.shape),
        "entries": sparse_entries,
    }
    return hashlib.sha256(
        json.dumps(payload, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _to_rational_domain(matrix: DomainMatrix) -> DomainMatrix:
    if matrix.domain == QQ:
        return matrix
    try:
        return matrix.convert_to(QQ)
    except Exception as error:
        raise ValueError(
            "matrix entries must convert exactly to QQ"
        ) from error


def _validate_system(
    matrix: DomainMatrix,
    rhs: DomainMatrix,
) -> tuple[DomainMatrix, DomainMatrix]:
    rational_matrix = _to_rational_domain(matrix)
    rational_rhs = _to_rational_domain(rhs)
    if rational_rhs.shape != (rational_matrix.shape[0], 1):
        raise ValueError("rhs must be a single column matching matrix rows")
    return rational_matrix, rational_rhs


def _to_prime_field(
    matrix: DomainMatrix,
    prime: int,
) -> DomainMatrix:
    if prime <= 2 or not sp.isprime(prime):
        raise ValueError("prime must be an odd prime")
    rational = _to_rational_domain(matrix)
    field = GF(prime)
    entries = {}
    for location, value in rational.to_dok().items():
        numerator = int(value.numerator)
        denominator = int(value.denominator)
        if denominator % prime == 0:
            raise ZeroDivisionError(
                f"matrix denominator is zero modulo {prime}"
            )
        entries[location] = field(numerator) / field(denominator)
    return DomainMatrix.from_dok(entries, rational.shape, field)


def _pivot_minor(
    matrix: DomainMatrix,
    prime: int,
) -> tuple[list[int], list[int], DomainMatrix]:
    modular = _to_prime_field(matrix, prime)
    _rref, pivot_columns = modular.rref()
    columns = list(pivot_columns)
    column_basis = modular.extract(
        list(range(modular.shape[0])), columns
    )
    _transpose_rref, pivot_rows = column_basis.transpose().rref()
    rows = list(pivot_rows)
    if len(rows) != len(columns):
        raise ExactLinearCertificateError(
            "modular row and column pivot counts differ"
        )
    modular_square = modular.extract(rows, columns)
    if modular_square.det() == 0:
        raise ExactLinearCertificateError(
            "selected modular pivot minor is singular"
        )
    return rows, columns, modular


def _solve_square(
    square: DomainMatrix,
    rhs: DomainMatrix,
) -> tuple[DomainMatrix, object]:
    numerator, denominator = square.solve_den(rhs)
    if square.matmul(numerator) != rhs.scalarmul(denominator):
        raise ExactLinearCertificateError(
            "rational square solve failed exact replay"
        )
    return numerator, denominator


def _domain_denominator_to_sympy(value: object) -> sp.Rational:
    return sp.Rational(
        int(value.numerator),  # type: ignore[attr-defined]
        int(value.denominator),  # type: ignore[attr-defined]
    )


def certify_inconsistent(
    matrix: DomainMatrix,
    rhs: DomainMatrix,
    *,
    prime: int = 1_000_003,
) -> InconsistencyCertificate:
    """Lift a modularly selected dependent row to an exact contradiction."""

    matrix, rhs = _validate_system(matrix, rhs)
    rows, columns, modular = _pivot_minor(matrix, prime)
    modular_rhs = _to_prime_field(rhs, prime)
    square_modular = modular.extract(rows, columns)
    inverse_modular = square_modular.inv()
    basis_rhs_modular = modular_rhs.extract(rows, [0])
    basis_set = set(rows)
    candidate_row = None
    for row in range(matrix.shape[0]):
        if row in basis_set:
            continue
        row_on_columns = modular.extract([row], columns)
        coefficients = row_on_columns.matmul(inverse_modular)
        predicted = coefficients.matmul(basis_rhs_modular)[0, 0]
        if predicted != modular_rhs[row, 0]:
            candidate_row = row
            break
    if candidate_row is None:
        raise ExactLinearCertificateError(
            "selected prime did not expose an inconsistent row"
        )

    square = matrix.extract(rows, columns)
    candidate_on_columns = matrix.extract(
        [candidate_row], columns
    )
    alpha_numerator, alpha_denominator = _solve_square(
        square.transpose(),
        candidate_on_columns.transpose(),
    )
    alpha_row = alpha_numerator.transpose()
    basis_matrix = matrix.extract(
        rows, list(range(matrix.shape[1]))
    )
    candidate_matrix_row = matrix.extract(
        [candidate_row], list(range(matrix.shape[1]))
    )
    if (
        alpha_row.matmul(basis_matrix)
        != candidate_matrix_row.scalarmul(alpha_denominator)
    ):
        raise ExactLinearCertificateError(
            "dependent-row relation failed rational replay"
        )

    predicted_rhs = alpha_row.matmul(
        rhs.extract(rows, [0])
    )[0, 0].to_sympy()
    actual_rhs = (
        rhs[candidate_row, 0].to_sympy()
        * _domain_denominator_to_sympy(alpha_denominator)
    )
    residual = sp.cancel(predicted_rhs - actual_rhs)
    if residual == 0:
        raise ExactLinearCertificateError(
            "lifted dependent row has zero rational RHS residual"
        )
    return InconsistencyCertificate(
        prime_used_only_for_pivot_selection=prime,
        matrix_shape=matrix.shape,
        rational_row_rank=len(columns),
        pivot_row_count=len(rows),
        pivot_column_count=len(columns),
        dependent_row=candidate_row,
        rational_rhs_residual=str(residual),
        rational_row_relation_verified=True,
        rational_rhs_residual_nonzero=True,
        matrix_sha256=sparse_matrix_sha256(matrix),
        rhs_sha256=sparse_matrix_sha256(rhs),
    )


def solve_affine(
    matrix: DomainMatrix,
    rhs: DomainMatrix,
    *,
    prime: int = 1_000_003,
) -> tuple[
    AffineSolutionCertificate,
    sp.Matrix,
    sp.Matrix,
]:
    """Return an exact particular solution and full homogeneous kernel."""

    matrix, rhs = _validate_system(matrix, rhs)
    rows, pivot_columns, _modular = _pivot_minor(matrix, prime)
    pivot_set = set(pivot_columns)
    free_columns = [
        column
        for column in range(matrix.shape[1])
        if column not in pivot_set
    ]
    square = matrix.extract(rows, pivot_columns)
    selected_rhs = rhs.extract(rows, [0])
    selected_free = matrix.extract(rows, free_columns)
    multiple_rhs = DomainMatrix.hstack(
        selected_rhs,
        selected_free.scalarmul(matrix.domain.convert(-1)),
    )
    numerator, denominator = _solve_square(square, multiple_rhs)

    numerator_entries = {}
    for (local_row, column), value in numerator.to_dok().items():
        numerator_entries[(pivot_columns[local_row], column)] = value
    for local_column, free_column in enumerate(free_columns):
        numerator_entries[(free_column, local_column + 1)] = denominator
    solution_numerators = DomainMatrix.from_dok(
        numerator_entries,
        (matrix.shape[1], len(free_columns) + 1),
        matrix.domain,
    )
    zero_columns = DomainMatrix.from_dok(
        {},
        (rhs.shape[0], len(free_columns)),
        matrix.domain,
    )
    expected = DomainMatrix.hstack(
        rhs, zero_columns
    ).scalarmul(denominator)
    if matrix.matmul(solution_numerators) != expected:
        raise ExactLinearCertificateError(
            "affine solution failed complete rational row replay"
        )

    rational_denominator = _domain_denominator_to_sympy(
        denominator
    )
    rational = solution_numerators.to_Matrix().applyfunc(
        lambda value: sp.cancel(value / rational_denominator)
    )
    particular = rational[:, 0]
    kernel = rational[:, 1:]
    return (
        AffineSolutionCertificate(
            prime_used_only_for_pivot_selection=prime,
            matrix_shape=matrix.shape,
            rational_rank=len(pivot_columns),
            affine_dimension=len(free_columns),
            multi_rhs_count=len(free_columns) + 1,
            complete_particular_replay=True,
            complete_kernel_replay=True,
            matrix_sha256=sparse_matrix_sha256(matrix),
            rhs_sha256=sparse_matrix_sha256(rhs),
        ),
        particular,
        kernel,
    )


def solve_particular(
    matrix: DomainMatrix,
    rhs: DomainMatrix,
    *,
    prime: int = 1_000_003,
) -> tuple[ParticularSolutionCertificate, sp.Matrix]:
    """Return one rational solution with a complete original-row replay."""

    matrix, rhs = _validate_system(matrix, rhs)
    rows, columns, _modular = _pivot_minor(matrix, prime)
    square = matrix.extract(rows, columns)
    selected_rhs = rhs.extract(rows, [0])
    numerator, denominator = _solve_square(square, selected_rhs)
    column_basis = matrix.extract(
        list(range(matrix.shape[0])), columns
    )
    if column_basis.matmul(numerator) != rhs.scalarmul(denominator):
        raise ExactLinearCertificateError(
            "particular solution failed complete rational row replay"
        )

    solution = sp.zeros(matrix.shape[1], 1)
    numerator_matrix = numerator.to_Matrix()
    rational_denominator = _domain_denominator_to_sympy(
        denominator
    )
    for local_index, column in enumerate(columns):
        solution[column, 0] = sp.cancel(
            numerator_matrix[local_index, 0]
            / rational_denominator
        )
    return (
        ParticularSolutionCertificate(
            prime_used_only_for_pivot_selection=prime,
            matrix_shape=matrix.shape,
            selected_pivot_rank=len(columns),
            pivot_row_count=len(rows),
            pivot_column_count=len(columns),
            rational_square_solve_verified=True,
            complete_rational_row_replay_verified=True,
            nonzero_solution_coordinates=sum(
                value != 0 for value in solution
            ),
            matrix_sha256=sparse_matrix_sha256(matrix),
            rhs_sha256=sparse_matrix_sha256(rhs),
        ),
        solution,
    )


def _primitive_integer_column(vector: sp.Matrix) -> sp.Matrix:
    """Normalize one nonzero rational column to coprime integers."""

    if vector.cols != 1 or vector.rows == 0:
        raise ValueError("vector must be a nonempty column")
    rationals = [sp.Rational(value) for value in vector]
    if not any(value != 0 for value in rationals):
        raise ValueError("vector must be nonzero")
    denominator_lcm = 1
    for value in rationals:
        denominator_lcm = int(sp.ilcm(denominator_lcm, value.q))
    integers = [int(value * denominator_lcm) for value in rationals]
    common = 0
    for value in integers:
        common = gcd(common, abs(value))
    common = max(common, 1)
    integers = [value // common for value in integers]
    first_nonzero = next(value for value in integers if value)
    if first_nonzero < 0:
        integers = [-value for value in integers]
    return sp.Matrix(integers)


def certify_column_separation(
    matrix: DomainMatrix,
    vector: DomainMatrix,
) -> tuple[ColumnSeparationCertificate, sp.Matrix]:
    """Certify that ``vector`` is outside the rational column span.

    The returned primitive row-functional witness annihilates every matrix
    column and pairs nontrivially with ``vector``.  This complements
    :func:`solve_particular`: callers receive an exact witness on either side
    of column-span membership rather than inferring inconsistency from ranks.
    """

    rational_matrix = _to_rational_domain(matrix)
    rational_vector = _to_rational_domain(vector)
    if rational_vector.shape != (rational_matrix.shape[0], 1):
        raise ValueError(
            "vector must be a single column matching matrix rows"
        )
    dense_matrix = rational_matrix.to_Matrix()
    dense_vector = rational_vector.to_Matrix()
    left_kernel = dense_matrix.transpose().nullspace()
    witness = None
    pairing = None
    for candidate in left_kernel:
        candidate_pairing = sp.cancel(
            (candidate.transpose() * dense_vector)[0, 0]
        )
        if candidate_pairing != 0:
            witness = _primitive_integer_column(candidate)
            pairing = sp.cancel(
                (witness.transpose() * dense_vector)[0, 0]
            )
            break
    if witness is None or pairing is None:
        raise ExactLinearCertificateError(
            "vector lies in the rational column span"
        )
    if witness.transpose() * dense_matrix != sp.zeros(
        1, dense_matrix.cols
    ):
        raise ExactLinearCertificateError(
            "column-separation witness failed complete annihilation replay"
        )
    if pairing == 0:
        raise ExactLinearCertificateError(
            "column-separation witness has zero pairing"
        )
    return (
        ColumnSeparationCertificate(
            matrix_shape=rational_matrix.shape,
            rational_column_rank=rational_matrix.rank(),
            left_nullity=len(left_kernel),
            primitive_witness=tuple(str(value) for value in witness),
            rational_pairing=str(pairing),
            complete_annihilation_replay=True,
            rational_pairing_nonzero=True,
            matrix_sha256=sparse_matrix_sha256(rational_matrix),
            vector_sha256=sparse_matrix_sha256(rational_vector),
        ),
        witness,
    )
