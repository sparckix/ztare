"""Certificates for discovered transformation actions and quotient authority.

The kernel contains no substrate transformation menu.  A substrate or search
lane proposes a finite presentation and executable maps; this module checks:

1. the declared multiplication table is a group;
2. the executable maps implement that group action on the declared evidence
   domain; and
3. a candidate carrier commutes with every proposed transformation.

Only the conjunction authorizes quotient construction.  Orbit identity and
fiber coordinates stay separate: the orbit digest identifies the object,
while transporters and the stabilizer describe its presentation/pose.

Epoch transport is intentionally absent.  Group elements are within-epoch
automorphisms.  Genesis, annihilation, fission, and fusion belong to a partial
cross-epoch correspondence (for example ``ObjectIdentityLink`` in the
worldmodel adapter), not to a group action.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
from typing import Any, Callable, Mapping, Sequence


class _Undefined:
    def __repr__(self) -> str:
        return "UNDEFINED"


UNDEFINED = _Undefined()


def _jsonable(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            str(key): _jsonable(item)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
        }
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if hasattr(value, "to_dict"):
        return _jsonable(value.to_dict())
    return {"type": type(value).__qualname__, "repr": repr(value)}


def stable_sha256(value: Any) -> str:
    payload = json.dumps(
        _jsonable(value), sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


@dataclass(frozen=True)
class FiniteGroupPresentation:
    """A named finite group, independent of any substrate representation."""

    group_id: str
    elements: tuple[str, ...]
    identity: str
    # Rows are (left, right, product), with left acting after right.
    multiplication: tuple[tuple[str, str, str], ...]

    def table(self) -> dict[tuple[str, str], str]:
        return {(left, right): product for left, right, product in self.multiplication}

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "ztare-finite-group-presentation-v1",
            "group_id": self.group_id,
            "elements": list(self.elements),
            "identity": self.identity,
            "multiplication": [list(row) for row in self.multiplication],
        }

    @property
    def sha256(self) -> str:
        return stable_sha256(self.to_dict())


def validate_group_presentation(group: FiniteGroupPresentation) -> tuple[str, ...]:
    """Return algebraic presentation failures; an empty tuple means a group."""
    failures: list[str] = []
    elements = tuple(group.elements)
    element_set = set(elements)
    if not group.group_id.strip():
        failures.append("missing_group_id")
    if not elements or len(element_set) != len(elements):
        failures.append("elements_empty_or_nonunique")
    if group.identity not in element_set:
        failures.append("identity_not_in_elements")
    table = group.table()
    if len(table) != len(group.multiplication):
        failures.append("duplicate_multiplication_pair")
    for left in elements:
        for right in elements:
            product = table.get((left, right))
            if product is None:
                failures.append(f"missing_product:{left}:{right}")
            elif product not in element_set:
                failures.append(f"product_outside_group:{left}:{right}:{product}")
    if failures:
        return tuple(failures)
    e = group.identity
    for item in elements:
        if table[(e, item)] != item or table[(item, e)] != item:
            failures.append(f"identity_law:{item}")
        if not any(
            table[(item, candidate)] == e and table[(candidate, item)] == e
            for candidate in elements
        ):
            failures.append(f"missing_inverse:{item}")
    for left in elements:
        for middle in elements:
            for right in elements:
                lhs = table[(table[(left, middle)], right)]
                rhs = table[(left, table[(middle, right)])]
                if lhs != rhs:
                    failures.append(f"nonassociative:{left}:{middle}:{right}")
    return tuple(failures)


@dataclass(frozen=True)
class TransformationAction:
    """Executable representation of one proposed group element.

    ``implementation_sha256`` binds the receipt to the map implementation.
    ``in_domain`` declares the partial action domain before any output is seen;
    returning ``UNDEFINED`` inside that domain is a certificate failure.
    """

    element_id: str
    implementation_sha256: str
    source_map: Callable[[Any], Any]
    target_map: Callable[[Any], Any]
    intervention_map: Callable[[Any], Any]
    time_map: Callable[[Any], Any]
    in_domain: Callable[["EquivarianceObservation"], bool] = field(
        default=lambda _observation: True, compare=False, repr=False
    )
    declared_domain: str = "all declared within-epoch observations"

    def __post_init__(self) -> None:
        if not self.element_id.strip():
            raise ValueError("transformation element_id is required")
        if not self.implementation_sha256.strip():
            raise ValueError("transformation implementation_sha256 is required")
        if not self.declared_domain.strip():
            raise ValueError("transformation declared_domain is required")

    def receipt_identity(self) -> dict[str, str]:
        return {
            "element_id": self.element_id,
            "implementation_sha256": self.implementation_sha256,
            "declared_domain": self.declared_domain,
        }


@dataclass(frozen=True)
class EquivarianceObservation:
    state: Any
    intervention: Any
    time: Any
    successor: Any
    observation_ref: str
    transition_kind: str = "dynamics"
    classification_authority: str = ""

    def receipt_payload(self) -> dict[str, Any]:
        return {
            "state": self.state,
            "intervention": self.intervention,
            "time": self.time,
            "successor": self.successor,
            "observation_ref": self.observation_ref,
            "transition_kind": self.transition_kind,
            "classification_authority": self.classification_authority,
        }


def _is_trusted_boundary(
    observation: EquivarianceObservation, trusted_authorities: frozenset[str]
) -> bool:
    return (
        observation.transition_kind in {"epoch_boundary", "reset_boundary"}
        and observation.classification_authority in trusted_authorities
    )


def _apply(function: Callable[[Any], Any], value: Any) -> tuple[Any, str | None]:
    try:
        return function(value), None
    except Exception as exc:  # noqa: BLE001 - exception becomes a counterexample
        return UNDEFINED, f"{type(exc).__name__}:{exc}"


@dataclass(frozen=True)
class EquivarianceCertificate:
    transformation_id: str
    status: str
    bank_sha256: str
    carrier_sha256: str
    action_identity: Mapping[str, str]
    eligible_observations: int
    domain_included: int
    tested: int
    domain_excluded: int
    boundary_excluded: int
    coverage_ratio: float
    base_law_mismatches: int
    commute_mismatches: int
    witness_digests: tuple[str, ...]
    counterexamples: tuple[Mapping[str, Any], ...]
    scope: str = "declared-domain bank only"
    schema: str = "ztare-equivariance-certificate-v1"

    @property
    def passed(self) -> bool:
        return self.status == "pass"

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "transformation_id": self.transformation_id,
            "status": self.status,
            "bank_sha256": self.bank_sha256,
            "carrier_sha256": self.carrier_sha256,
            "action_identity": dict(self.action_identity),
            "eligible_observations": self.eligible_observations,
            "domain_included": self.domain_included,
            "tested": self.tested,
            "domain_excluded": self.domain_excluded,
            "boundary_excluded": self.boundary_excluded,
            "coverage_ratio": self.coverage_ratio,
            "base_law_mismatches": self.base_law_mismatches,
            "commute_mismatches": self.commute_mismatches,
            "witness_digests": list(self.witness_digests),
            "counterexamples": [dict(row) for row in self.counterexamples],
            "scope": self.scope,
        }


def certify_equivariance(
    *,
    carrier: Callable[[Any, Any, Any], Any],
    carrier_sha256: str,
    action: TransformationAction,
    observations: Sequence[EquivarianceObservation],
    trusted_boundary_authorities: frozenset[str] = frozenset(),
    min_tested: int = 1,
    min_coverage_ratio: float = 1.0,
    counterexample_cap: int = 20,
) -> EquivarianceCertificate:
    """Check ``F(gS(s), gA(a), gT(t)) == gN(F(s,a,t))`` on a bank.

    The carrier must also fit the source observation.  This prevents a
    symmetric constant carrier from earning quotient authority over evidence
    it does not explain.  Trusted boundaries are reported and excluded; an
    untrusted boundary label has no excusal authority.
    """
    if not carrier_sha256.strip():
        raise ValueError("carrier_sha256 is required")
    if not 0.0 <= float(min_coverage_ratio) <= 1.0:
        raise ValueError("min_coverage_ratio must lie in [0, 1]")
    bank_sha = stable_sha256([row.receipt_payload() for row in observations])
    eligible = domain_included = tested = domain_excluded = boundary_excluded = 0
    base_mismatches = commute_mismatches = 0
    witnesses: list[str] = []
    counterexamples: list[dict[str, Any]] = []

    def reject(row: EquivarianceObservation, kind: str, **detail: Any) -> None:
        nonlocal commute_mismatches
        commute_mismatches += 1
        if len(counterexamples) < counterexample_cap:
            counterexamples.append(
                {
                    "kind": kind,
                    "observation_ref": row.observation_ref,
                    "observation_sha256": stable_sha256(row.receipt_payload()),
                    **{key: _jsonable(value) for key, value in detail.items()},
                }
            )

    for row in observations:
        if _is_trusted_boundary(row, trusted_boundary_authorities):
            boundary_excluded += 1
            continue
        eligible += 1
        try:
            in_domain = bool(action.in_domain(row))
        except Exception as exc:  # noqa: BLE001
            reject(row, "domain_predicate_error", error=f"{type(exc).__name__}:{exc}")
            continue
        if not in_domain:
            domain_excluded += 1
            continue
        domain_included += 1

        base_prediction, base_error = _apply(
            lambda state: carrier(state, row.intervention, row.time), row.state
        )
        if base_error is not None or base_prediction is UNDEFINED or base_prediction != row.successor:
            base_mismatches += 1
            if len(counterexamples) < counterexample_cap:
                counterexamples.append(
                    {
                        "kind": "base_law_mismatch",
                        "observation_ref": row.observation_ref,
                        "observation_sha256": stable_sha256(row.receipt_payload()),
                        "error": base_error,
                        "prediction_sha256": (
                            None if base_prediction is UNDEFINED else stable_sha256(base_prediction)
                        ),
                        "successor_sha256": stable_sha256(row.successor),
                    }
                )
            continue

        transformed_state, state_error = _apply(action.source_map, row.state)
        transformed_action, action_error = _apply(action.intervention_map, row.intervention)
        transformed_time, time_error = _apply(action.time_map, row.time)
        transformed_successor, target_error = _apply(action.target_map, row.successor)
        errors = {
            "source_map": state_error,
            "intervention_map": action_error,
            "time_map": time_error,
            "target_map": target_error,
        }
        undefined = {
            "source_map": transformed_state is UNDEFINED,
            "intervention_map": transformed_action is UNDEFINED,
            "time_map": transformed_time is UNDEFINED,
            "target_map": transformed_successor is UNDEFINED,
        }
        if any(errors.values()) or any(undefined.values()):
            reject(
                row,
                "undefined_inside_declared_domain",
                errors=errors,
                undefined=undefined,
            )
            continue

        transformed_prediction, prediction_error = _apply(
            lambda state: carrier(state, transformed_action, transformed_time),
            transformed_state,
        )
        if prediction_error is not None or transformed_prediction is UNDEFINED:
            reject(row, "transformed_carrier_undefined", error=prediction_error)
            continue
        tested += 1
        witness = {
            "observation_sha256": stable_sha256(row.receipt_payload()),
            "lhs_sha256": stable_sha256(transformed_prediction),
            "rhs_sha256": stable_sha256(transformed_successor),
        }
        witnesses.append(stable_sha256(witness))
        if transformed_prediction != transformed_successor:
            reject(row, "commuting_square_mismatch", **witness)

    coverage_ratio = domain_included / eligible if eligible else 0.0
    passed = (
        tested >= max(1, int(min_tested))
        and coverage_ratio >= float(min_coverage_ratio)
        and base_mismatches == 0
        and commute_mismatches == 0
    )
    return EquivarianceCertificate(
        transformation_id=action.element_id,
        status="pass" if passed else "fail",
        bank_sha256=bank_sha,
        carrier_sha256=carrier_sha256,
        action_identity=action.receipt_identity(),
        eligible_observations=eligible,
        domain_included=domain_included,
        tested=tested,
        domain_excluded=domain_excluded,
        boundary_excluded=boundary_excluded,
        coverage_ratio=coverage_ratio,
        base_law_mismatches=base_mismatches,
        commute_mismatches=commute_mismatches,
        witness_digests=tuple(witnesses),
        counterexamples=tuple(counterexamples),
    )


@dataclass(frozen=True)
class GroupActionCertificate:
    status: str
    group_sha256: str
    bank_sha256: str
    action_implementation_sha256s: Mapping[str, str]
    eligible_observations: int
    domain_included: int
    domain_excluded: int
    boundary_excluded: int
    coverage_ratio: float
    checked_equalities: int
    failures: tuple[Mapping[str, Any], ...]
    schema: str = "ztare-group-action-certificate-v1"

    @property
    def passed(self) -> bool:
        return self.status == "pass"


def certify_group_action(
    *,
    group: FiniteGroupPresentation,
    actions: Mapping[str, TransformationAction],
    observations: Sequence[EquivarianceObservation],
    trusted_boundary_authorities: frozenset[str] = frozenset(),
    failure_cap: int = 20,
) -> GroupActionCertificate:
    """Check that proposed executable maps realize the multiplication table."""
    presentation_failures = validate_group_presentation(group)
    bank_sha = stable_sha256([row.receipt_payload() for row in observations])
    failures: list[dict[str, Any]] = [
        {"kind": "presentation", "detail": failure}
        for failure in presentation_failures[:failure_cap]
    ]
    missing = sorted(set(group.elements) - set(actions))
    extra = sorted(set(actions) - set(group.elements))
    if missing:
        failures.append({"kind": "missing_actions", "elements": missing})
    if extra:
        failures.append({"kind": "extra_actions", "elements": extra})
    checked = 0
    if failures:
        return GroupActionCertificate(
            status="fail",
            group_sha256=group.sha256,
            bank_sha256=bank_sha,
            action_implementation_sha256s={
                key: value.implementation_sha256 for key, value in actions.items()
            },
            eligible_observations=0,
            domain_included=0,
            domain_excluded=0,
            boundary_excluded=0,
            coverage_ratio=0.0,
            checked_equalities=0,
            failures=tuple(failures[:failure_cap]),
        )

    table = group.table()
    eligible = domain_included = domain_excluded = boundary_excluded = 0
    for row in observations:
        if _is_trusted_boundary(row, trusted_boundary_authorities):
            boundary_excluded += 1
            continue
        eligible += 1
        try:
            row_in_domain = all(action.in_domain(row) for action in actions.values())
        except Exception as exc:  # noqa: BLE001
            row_in_domain = False
            if len(failures) < failure_cap:
                failures.append(
                    {
                        "kind": "domain_predicate_error",
                        "observation_ref": row.observation_ref,
                        "error": f"{type(exc).__name__}:{exc}",
                    }
                )
        if not row_in_domain:
            domain_excluded += 1
            continue
        domain_included += 1
        carriers = (
            ("source", row.state, lambda action, value: action.source_map(value)),
            ("target", row.successor, lambda action, value: action.target_map(value)),
            (
                "intervention",
                row.intervention,
                lambda action, value: action.intervention_map(value),
            ),
            ("time", row.time, lambda action, value: action.time_map(value)),
        )
        for carrier_kind, value, apply_action in carriers:
            # A group representation is a *unital* monoid homomorphism.
            # Composition preservation alone admits idempotent projections
            # (including constant/annihilating maps) as a trivial exploit.
            try:
                identity_image = apply_action(actions[group.identity], value)
            except Exception as exc:  # noqa: BLE001
                identity_image = UNDEFINED
                identity_error = f"{type(exc).__name__}:{exc}"
            else:
                identity_error = None
            checked += 1
            if identity_image is UNDEFINED or identity_image != value:
                if len(failures) < failure_cap:
                    failures.append(
                        {
                            "kind": "identity_action_mismatch",
                            "carrier_kind": carrier_kind,
                            "identity": group.identity,
                            "observation_ref": row.observation_ref,
                            "value_sha256": stable_sha256(value),
                            "identity_image_sha256": (
                                None
                                if identity_image is UNDEFINED
                                else stable_sha256(identity_image)
                            ),
                            "error": identity_error,
                        }
                    )
            for left in group.elements:
                for right in group.elements:
                    product = table[(left, right)]
                    try:
                        rhs_inner = apply_action(actions[right], value)
                        composed = (
                            UNDEFINED
                            if rhs_inner is UNDEFINED
                            else apply_action(actions[left], rhs_inner)
                        )
                        direct = apply_action(actions[product], value)
                    except Exception as exc:  # noqa: BLE001
                        composed = direct = UNDEFINED
                        error = f"{type(exc).__name__}:{exc}"
                    else:
                        error = None
                    checked += 1
                    if composed is UNDEFINED or direct is UNDEFINED or composed != direct:
                        if len(failures) < failure_cap:
                            failures.append(
                                {
                                    "kind": "action_law_mismatch",
                                    "carrier_kind": carrier_kind,
                                    "left": left,
                                    "right": right,
                                    "product": product,
                                    "observation_ref": row.observation_ref,
                                    "value_sha256": stable_sha256(value),
                                    "composed_sha256": (
                                        None if composed is UNDEFINED else stable_sha256(composed)
                                    ),
                                    "direct_sha256": (
                                        None if direct is UNDEFINED else stable_sha256(direct)
                                    ),
                                    "error": error,
                                }
                            )
    if checked == 0:
        failures.append({"kind": "no_action_equalities_checked"})
    coverage_ratio = domain_included / eligible if eligible else 0.0
    return GroupActionCertificate(
        status="pass" if not failures else "fail",
        group_sha256=group.sha256,
        bank_sha256=bank_sha,
        action_implementation_sha256s={
            key: actions[key].implementation_sha256 for key in group.elements
        },
        eligible_observations=eligible,
        domain_included=domain_included,
        domain_excluded=domain_excluded,
        boundary_excluded=boundary_excluded,
        coverage_ratio=coverage_ratio,
        checked_equalities=checked,
        failures=tuple(failures),
    )


@dataclass(frozen=True)
class QuotientAuthority:
    authority_sha256: str
    group_sha256: str
    bank_sha256: str
    carrier_sha256: str
    declared_domain: str
    action_implementation_sha256s: Mapping[str, str]
    schema: str = "ztare-quotient-authority-v1"


def authorize_quotient(
    *,
    group: FiniteGroupPresentation,
    group_action: GroupActionCertificate,
    equivariance: Mapping[str, EquivarianceCertificate],
) -> QuotientAuthority:
    """Mint quotient authority only from matching algebra/action/commutation receipts."""
    if not group_action.passed or group_action.group_sha256 != group.sha256:
        raise ValueError("group action is not certified for this presentation")
    if group_action.domain_excluded or group_action.coverage_ratio != 1.0:
        raise ValueError(
            "quotient authority requires total group action on every scored "
            "within-epoch observation"
        )
    required = set(group.elements) - {group.identity}
    if set(equivariance) != required:
        raise ValueError(
            f"equivariance certificates must exactly cover nonidentity elements: {sorted(required)}"
        )
    certificates = [equivariance[element] for element in sorted(required)]
    if any(not certificate.passed for certificate in certificates):
        raise ValueError("a proposed group element failed equivariance")
    if any(
        certificate.domain_excluded or certificate.coverage_ratio != 1.0
        for certificate in certificates
    ):
        raise ValueError(
            "quotient authority rejects candidate-owned domain exclusions; "
            "restrict the bank through an adapter-owned subobject instead"
        )
    bank_shas = {certificate.bank_sha256 for certificate in certificates}
    carrier_shas = {certificate.carrier_sha256 for certificate in certificates}
    domains = {
        str(certificate.action_identity.get("declared_domain") or "")
        for certificate in certificates
    }
    if len(bank_shas) != 1 or group_action.bank_sha256 not in bank_shas:
        raise ValueError("group-action and equivariance receipts bind different banks")
    if len(carrier_shas) != 1 or len(domains) != 1:
        raise ValueError("equivariance receipts bind different carriers or domains")
    for element, certificate in equivariance.items():
        expected = group_action.action_implementation_sha256s.get(element)
        actual = certificate.action_identity.get("implementation_sha256")
        if expected != actual:
            raise ValueError(f"action implementation mismatch for {element}")
    payload = {
        "group_sha256": group.sha256,
        "bank_sha256": next(iter(bank_shas)),
        "carrier_sha256": next(iter(carrier_shas)),
        "declared_domain": next(iter(domains)),
        "action_implementation_sha256s": dict(
            group_action.action_implementation_sha256s
        ),
    }
    return QuotientAuthority(
        authority_sha256=stable_sha256(payload),
        group_sha256=group.sha256,
        bank_sha256=payload["bank_sha256"],
        carrier_sha256=payload["carrier_sha256"],
        declared_domain=payload["declared_domain"],
        action_implementation_sha256s=payload["action_implementation_sha256s"],
    )


@dataclass(frozen=True)
class OrbitCoordinates:
    """Base/fiber decomposition under a certified finite group action."""

    orbit_identity_sha256: str
    representative: Any
    representative_sha256: str
    orbit_member_sha256s: tuple[str, ...]
    transporters_to_representative: tuple[str, ...]
    stabilizer: tuple[str, ...]
    state_schema_id: str
    canonicalizer_id: str


@dataclass(frozen=True)
class CanonicalOrder:
    """Substrate-owned, versioned order for choosing an orbit section.

    The order selects a convenient representative; it never defines orbit
    identity.  Changing state schema or ordering implementation changes an
    explicit receipt identity and therefore requires a migration rather than
    silently changing historical pose keys.
    """

    state_schema_id: str
    canonicalizer_id: str
    implementation_sha256: str
    key: Callable[[Any], Any] = field(compare=False, repr=False)

    def __post_init__(self) -> None:
        for label, value in (
            ("state_schema_id", self.state_schema_id),
            ("canonicalizer_id", self.canonicalizer_id),
            ("implementation_sha256", self.implementation_sha256),
        ):
            if not str(value).strip():
                raise ValueError(f"{label} is required")


def _canonical_key_bytes(value: Any) -> bytes:
    return json.dumps(
        _jsonable(value), sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")


def orbit_coordinates(
    value: Any,
    *,
    group: FiniteGroupPresentation,
    actions: Mapping[str, TransformationAction],
    authority: QuotientAuthority,
    canonical_order: CanonicalOrder,
) -> OrbitCoordinates:
    """Return orbit identity plus pose coset/stabilizer under certified maps."""
    if authority.group_sha256 != group.sha256:
        raise ValueError("quotient authority does not bind this group")
    for element in group.elements:
        action = actions.get(element)
        if action is None:
            raise ValueError(f"missing action for {element}")
        if (
            authority.action_implementation_sha256s.get(element)
            != action.implementation_sha256
        ):
            raise ValueError(f"uncertified action implementation for {element}")
    images: dict[str, Any] = {}
    for element in group.elements:
        image = actions[element].source_map(value)
        if image is UNDEFINED:
            raise ValueError("group action became partial inside quotient domain")
        images[element] = image
    # The kernel cannot invent a geometric/topological order without importing
    # substrate semantics.  It therefore orders only a substrate-owned,
    # versioned key.  Cryptographic hashes remain receipt binders, never an
    # ordering relation.
    representative_element = min(
        group.elements,
        key=lambda item: _canonical_key_bytes(canonical_order.key(images[item])),
    )
    representative = images[representative_element]
    representative_sha = stable_sha256(
        {
            "state_schema_id": canonical_order.state_schema_id,
            "value": representative,
        }
    )
    member_shas = tuple(
        sorted(
            {
                stable_sha256(
                    {
                        "state_schema_id": canonical_order.state_schema_id,
                        "value": image,
                    }
                )
                for image in images.values()
            }
        )
    )
    transporters = tuple(
        element
        for element in group.elements
        if images[element] == representative
    )
    stabilizer = tuple(
        element for element in group.elements if images[element] == value
    )
    orbit_identity = stable_sha256(
        {
            "group_sha256": group.sha256,
            "authority_sha256": authority.authority_sha256,
            "state_schema_id": canonical_order.state_schema_id,
            "members": member_shas,
        }
    )
    return OrbitCoordinates(
        orbit_identity_sha256=orbit_identity,
        representative=representative,
        representative_sha256=representative_sha,
        orbit_member_sha256s=member_shas,
        transporters_to_representative=transporters,
        stabilizer=stabilizer,
        state_schema_id=canonical_order.state_schema_id,
        canonicalizer_id=canonical_order.canonicalizer_id,
    )
