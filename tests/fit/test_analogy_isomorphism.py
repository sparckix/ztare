from ztare.common.constraint_isomorphism import SurfacedIsomorphism
from ztare.fit.analogy import query_analogy


def test_structural_analogy_mode_uses_constraint_isomorphism_typed_mapping() -> None:
    seen = {}

    def mock_query(fp, n):
        seen["fingerprint"] = fp
        seen["n"] = n
        return [
            SurfacedIsomorphism(
                theorem="Dual certificate transport",
                field="convex optimization",
                mechanism="separating hyperplane gives a target-side certificate",
                mapping_hint="residual branch -> separating certificate",
                invariant_map={
                    "residual_shape": "certificate residual",
                    "monotonicity": "dual ordering",
                    "regime_break": "active constraint boundary",
                    "heavy_tail": "unbounded ray",
                    "sign_pattern": "certificate sign",
                    "asymptotic_failure": "boundary condition",
                    "class_asymmetry": "case split",
                    "unreferenced_correlation_count": "missing feature count",
                },
            ),
            SurfacedIsomorphism(
                theorem="Decorative analogy",
                field="physics",
                mechanism="sounds similar",
                mapping_hint="",
                invariant_map={"residual_shape": "only one mapped invariant"},
            ),
        ]

    response = query_analogy(
        {
            "residual_topology": {
                "shape": "monotone",
                "monotonicity": "increasing",
                "regime_break_likely": True,
                "heavy_tail": False,
                "sign_pattern": "uniform_pos",
            },
            "asymptotic_profile": {"asymptotic_failure": "high_tail_dominant"},
            "residual_topology_by_class": {"class_0": {}},
            "unreferenced_correlations": [{"feature_idx": 1}],
        },
        model_id="mock-model",
        structural_mode=True,
        isomorphism_query=mock_query,
    )

    assert response.error is None
    assert seen["n"] == 5
    assert seen["fingerprint"].constraint_class == "autoresearch residual structural transfer"
    assert response.candidate_forms == ["residual branch -> separating certificate"]
    assert "constraint_isomorphism typed mapping survivors" in response.reasoning
    assert "rejected 1" in response.reasoning
    assert "Dual certificate transport" in response.raw_response
    assert "Decorative analogy" not in response.candidate_forms
