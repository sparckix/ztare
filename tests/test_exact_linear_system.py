import sympy as sp
from sympy.polys.matrices import DomainMatrix

from ztare.common.exact_linear_system import (
    ColumnSeparationCertificate,
    ExactLinearCertificateError,
    certify_column_separation,
    certify_inconsistent,
    solve_affine,
    solve_particular,
    sparse_matrix_sha256,
)


def _domain_matrix(rows: list[list[int]]) -> DomainMatrix:
    return DomainMatrix.from_Matrix(sp.Matrix(rows)).to_field()


def test_exact_affine_solution_replays_particular_and_kernel() -> None:
    matrix = _domain_matrix([
        [1, 1, 0],
        [0, 1, 1],
    ])
    rhs = _domain_matrix([[1], [2]])
    certificate, particular, kernel = solve_affine(
        matrix, rhs, prime=101
    )
    dense = matrix.to_Matrix()
    assert certificate.rational_rank == 2
    assert certificate.affine_dimension == 1
    assert dense * particular == rhs.to_Matrix()
    assert dense * kernel == sp.zeros(2, 1)


def test_exact_inconsistency_lifts_dependent_row() -> None:
    matrix = _domain_matrix([[1], [2]])
    rhs = _domain_matrix([[1], [3]])
    certificate = certify_inconsistent(
        matrix, rhs, prime=101
    )
    assert certificate.rational_row_relation_verified
    assert certificate.rational_rhs_residual_nonzero
    assert sp.Rational(certificate.rational_rhs_residual) != 0


def test_particular_solution_replays_every_row() -> None:
    matrix = _domain_matrix([
        [1, 1, 0],
        [0, 1, 1],
        [1, 2, 1],
    ])
    rhs = _domain_matrix([[1], [2], [3]])
    certificate, particular = solve_particular(
        matrix, rhs, prime=101
    )
    assert certificate.complete_rational_row_replay_verified
    assert matrix.to_Matrix() * particular == rhs.to_Matrix()


def test_consistent_system_has_no_inconsistency_certificate() -> None:
    matrix = _domain_matrix([[1], [2]])
    rhs = _domain_matrix([[1], [2]])
    try:
        certify_inconsistent(matrix, rhs, prime=101)
    except ExactLinearCertificateError:
        pass
    else:
        raise AssertionError("consistent system was certified inconsistent")


def test_sparse_fingerprint_is_representation_independent() -> None:
    dense = _domain_matrix([[1, 0], [0, 2]])
    sparse = DomainMatrix.from_dok(
        {(0, 0): dense.domain.one, (1, 1): dense.domain(2)},
        (2, 2),
        dense.domain,
    )
    assert sparse_matrix_sha256(dense) == sparse_matrix_sha256(sparse)


def test_column_separation_returns_replayable_primitive_witness() -> None:
    matrix = _domain_matrix([
        [1, 0],
        [0, 1],
        [0, 0],
    ])
    vector = _domain_matrix([[0], [0], [3]])
    certificate, witness = certify_column_separation(matrix, vector)
    assert isinstance(certificate, ColumnSeparationCertificate)
    assert certificate.rational_column_rank == 2
    assert certificate.left_nullity == 1
    assert certificate.primitive_witness == ("0", "0", "1")
    assert certificate.rational_pairing == "3"
    assert witness.transpose() * matrix.to_Matrix() == sp.zeros(1, 2)
    assert witness.transpose() * vector.to_Matrix() == sp.Matrix([[3]])


def test_column_separation_rejects_vector_in_column_span() -> None:
    matrix = _domain_matrix([
        [1, 0],
        [0, 1],
        [0, 0],
    ])
    vector = _domain_matrix([[2], [3], [0]])
    try:
        certify_column_separation(matrix, vector)
    except ExactLinearCertificateError:
        pass
    else:
        raise AssertionError("in-span vector received a separation witness")
