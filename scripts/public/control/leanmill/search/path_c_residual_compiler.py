#!/usr/bin/env python3
"""Compile Residual Compiler streams into executable repair work.

This is the bridge between "we logged residuals" and "the Residual Compiler is
operating." It reads factory residual JSONL streams, classifies each
row into one of three buckets:

  - executable canary: a bounded test can be run now.
  - needs template: useful residual, but no safe generic action exists.
  - retire/control: likely backend artifact, contaminated row, or weak signal.

It does not prove anything and it does not award credit. It emits a packet that
`leansearch_repair_canary_drain.py` can consume plus a decision ledger for the
non-executable rows.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
import leanmill_family_specs as family_specs  # noqa: E402


DEFAULT_OUT = "/tmp/rung1/residual_compiler_compiled_canaries.json"
DEFAULT_DECISIONS = "/tmp/rung1/residual_compiler_compiled_decisions.json"
FAMILY_SPECS = family_specs.load_specs()
SPEC_REPAIR_TEMPLATES = family_specs.templates_by_row(FAMILY_SPECS)

GOLD_CONTAMINATED_ROWS = {
    # Current Mathlib source contains the exact proof body below the target.
    # Use only as a template/debug control, never as clean source-discovery credit.
    "MCB_012_contDiffOn_univBall_symm",
}

CSTAR_SELFADJOINT_SPECTRAL_RADIUS_TEMPLATES: list[dict[str, Any]] = [
    {
        "packet_id_suffix": "cstar_selfadjoint_pow_limit_positive_v1",
        "repair_family": "cstar_selfadjoint_spectral_radius_planner",
        "test_kind": "positive",
        "expected_outcome": "governed_repair_canary_closure",
        "backend": "repl_file",
        "timeout": 120,
        "extra_body": [
            "cstar_selfadjoint_pow_limit_v1::have hconst : "
            "Tendsto (fun _n : ℕ => (‖a‖₊ : ℝ≥0∞)) atTop _ := tendsto_const_nhds\n"
            "refine tendsto_nhds_unique ?_ hconst\n"
            "convert\n"
            "  (spectrum.pow_nnnorm_pow_one_div_tendsto_nhds_spectralRadius (a : A)).comp\n"
            "    (tendsto_pow_atTop_atTop_of_one_lt one_lt_two) using 1\n"
            "refine funext fun n => ?_\n"
            "rw [Function.comp_apply, ha.nnnorm_pow_two_pow, ENNReal.coe_pow, ← rpow_natCast, ← rpow_mul]\n"
            "simp"
        ],
    },
    {
        "packet_id_suffix": "cstar_selfadjoint_missing_power_bridge_negative_v1",
        "repair_family": "cstar_selfadjoint_spectral_radius_planner",
        "test_kind": "negative_control",
        "expected_outcome": "must_fail_without_selfadjoint_power_norm_bridge",
        "backend": "repl_file",
        "timeout": 80,
        "extra_body": [
            "cstar_selfadjoint_missing_power_bridge_negative::have hconst : "
            "Tendsto (fun _n : ℕ => (‖a‖₊ : ℝ≥0∞)) atTop _ := tendsto_const_nhds\n"
            "refine tendsto_nhds_unique ?_ hconst\n"
            "convert\n"
            "  (spectrum.pow_nnnorm_pow_one_div_tendsto_nhds_spectralRadius (a : A)).comp\n"
            "    (tendsto_pow_atTop_atTop_of_one_lt one_lt_two) using 1\n"
            "refine funext fun n => ?_\n"
            "rw [Function.comp_apply, ENNReal.coe_pow, ← rpow_natCast, ← rpow_mul]\n"
            "simp"
        ],
    },
]

SPECTRAL_CLUSTER_REPAIR_TEMPLATES: dict[str, list[dict[str, Any]]] = {
    "MCB_060_posDef_gram_of_linearIndependent": [
        {
            "packet_id_suffix": "gram_posdef_from_linear_independent_positive_v1",
            "repair_family": "gram_posdef_linear_independent_planner",
            "test_kind": "positive",
            "expected_outcome": "governed_repair_canary_closure",
            "backend": "repl_file",
            "timeout": 140,
            "extra_body": [
                "gram_posdef_from_linear_independent_v1::have := Fintype.ofFinite n\n"
                "rw [Fintype.linearIndependent_iff] at h_li\n"
                "refine .of_dotProduct_mulVec_pos (isHermitian_gram _ _) fun x hx =>\n"
                "  ((posSemidef_gram ..).dotProduct_mulVec_nonneg _).lt_of_ne' ?_\n"
                "rw [star_dotProduct_gram_mulVec, inner_self_eq_zero.ne]\n"
                "exact mt (h_li x) (mt funext hx)"
            ],
        },
        {
            "packet_id_suffix": "gram_posdef_missing_linear_independent_negative_v1",
            "repair_family": "gram_posdef_linear_independent_planner",
            "test_kind": "negative_control",
            "expected_outcome": "must_fail_without_linear_independent_kernel_argument",
            "backend": "repl_file",
            "timeout": 80,
            "extra_body": [
                "gram_posdef_missing_li_negative::have := Fintype.ofFinite n\n"
                "refine .of_dotProduct_mulVec_pos (isHermitian_gram _ _) fun x hx =>\n"
                "  ((posSemidef_gram ..).dotProduct_mulVec_nonneg _).lt_of_ne' ?_\n"
                "rw [star_dotProduct_gram_mulVec, inner_self_eq_zero.ne]\n"
                "exact mt (fun _ => by simp) (mt funext hx)"
            ],
        },
    ],
    "MCB_074_eigenvalue_nonneg_of_nonneg": [
        {
            "packet_id_suffix": "eigenvalue_nonneg_via_eigenvector_inner_positive_v1",
            "repair_family": "spectral_eigenvalue_nonneg_planner",
            "test_kind": "positive",
            "expected_outcome": "governed_repair_canary_closure",
            "backend": "repl_file",
            "timeout": 140,
            "extra_body": [
                "eigenvalue_nonneg_via_eigenvector_inner_v1::obtain ⟨v, hv₁, hv₂⟩ := hμ.exists_hasEigenvector\n"
                "have hpos : (0 : ℝ) < ‖v‖ ^ 2 := by simpa only [sq_pos_iff, norm_ne_zero_iff] using hv₂\n"
                "simp only [mem_genEigenspace_one] at hv₁\n"
                "have : RCLike.re ⟪v, T v⟫ = μ * ‖v‖ ^ 2 :=\n"
                "  mod_cast congr_arg RCLike.re (inner_product_apply_eigenvector hv₁)\n"
                "exact (mul_nonneg_iff_of_pos_right hpos).mp (this ▸ hnn v)"
            ],
        },
        {
            "packet_id_suffix": "eigenvalue_nonneg_missing_eigenvector_equation_negative_v1",
            "repair_family": "spectral_eigenvalue_nonneg_planner",
            "test_kind": "negative_control",
            "expected_outcome": "must_fail_without_eigenvector_inner_identity",
            "backend": "repl_file",
            "timeout": 80,
            "extra_body": [
                "eigenvalue_nonneg_missing_inner_identity_negative::obtain ⟨v, hv₁, hv₂⟩ := hμ.exists_hasEigenvector\n"
                "have hpos : (0 : ℝ) < ‖v‖ ^ 2 := by simpa only [sq_pos_iff, norm_ne_zero_iff] using hv₂\n"
                "simp only [mem_genEigenspace_one] at hv₁\n"
                "exact (mul_nonneg_iff_of_pos_right hpos).mp (hnn v)"
            ],
        },
    ],
    "MCB_081_Unitary": [
        {
            "packet_id_suffix": "unitary_spectrum_subset_circle_positive_v1",
            "repair_family": "cstar_unitary_spectrum_circle_planner",
            "test_kind": "positive",
            "expected_outcome": "governed_repair_canary_closure",
            "backend": "repl_file",
            "timeout": 140,
            "extra_body": [
                "unitary_spectrum_subset_circle_v1::nontriviality E\n"
                "refine fun k hk => mem_sphere_zero_iff_norm.mpr (le_antisymm ?_ ?_)\n"
                "· simpa only [CStarRing.norm_coe_unitary u] using norm_le_norm_of_mem hk\n"
                "· rw [← Unitary.val_toUnits_apply u] at hk\n"
                "  have hnk := ne_zero_of_mem_of_unit hk\n"
                "  rw [← inv_inv (Unitary.toUnits u), ← spectrum.map_inv, Set.mem_inv] at hk\n"
                "  have : ‖k‖⁻¹ ≤ ‖(↑(Unitary.toUnits u)⁻¹ : E)‖ := by\n"
                "    simpa only [norm_inv] using norm_le_norm_of_mem hk\n"
                "  simpa using inv_le_of_inv_le₀ (norm_pos_iff.mpr hnk) this"
            ],
        },
        {
            "packet_id_suffix": "unitary_spectrum_missing_inverse_bound_negative_v1",
            "repair_family": "cstar_unitary_spectrum_circle_planner",
            "test_kind": "negative_control",
            "expected_outcome": "must_fail_without_inverse_spectral_bound",
            "backend": "repl_file",
            "timeout": 80,
            "extra_body": [
                "unitary_spectrum_missing_inverse_bound_negative::nontriviality E\n"
                "refine fun k hk => mem_sphere_zero_iff_norm.mpr (le_antisymm ?_ ?_)\n"
                "· simpa only [CStarRing.norm_coe_unitary u] using norm_le_norm_of_mem hk\n"
                "· simpa using norm_nonneg k"
            ],
        },
    ],
}

LIMIT_CAUSEQ_COMPLEX_TEMPLATES: dict[str, list[dict[str, Any]]] = {
    "MCB_105_equiv_limAux": [
        {
            "packet_id_suffix": "complex_equiv_limAux_positive_v1",
            "repair_family": "complex_limit_causeq_planner",
            "test_kind": "positive",
            "expected_outcome": "governed_repair_canary_closure",
            "backend": "repl_file",
            "timeout": 120,
            "extra_body": [
                "complex_equiv_limAux_v1::intro ε ε0\n"
                "exact\n"
                "  (exists_forall_ge_and\n"
                "    (CauSeq.equiv_lim ⟨_, isCauSeq_re f⟩ _ (half_pos ε0))\n"
                "    (CauSeq.equiv_lim ⟨_, isCauSeq_im f⟩ _ (half_pos ε0))).imp\n"
                "    fun _ H j ij => by\n"
                "      obtain ⟨H₁, H₂⟩ := H _ ij\n"
                "      apply lt_of_le_of_lt (norm_le_abs_re_add_abs_im _)\n"
                "      dsimp [limAux] at *\n"
                "      have := add_lt_add H₁ H₂\n"
                "      rwa [add_halves] at this"
            ],
        },
        {
            "packet_id_suffix": "complex_equiv_limAux_missing_im_negative_v1",
            "repair_family": "complex_limit_causeq_planner",
            "test_kind": "negative_control",
            "expected_outcome": "must_fail_without_imaginary_limit_half",
            "backend": "repl_file",
            "timeout": 80,
            "extra_body": [
                "complex_equiv_limAux_missing_im_negative::intro ε ε0\n"
                "obtain ⟨i, hi⟩ := CauSeq.equiv_lim ⟨_, isCauSeq_re f⟩ _ (half_pos ε0)\n"
                "refine ⟨i, ?_⟩\n"
                "intro j hj\n"
                "apply lt_of_le_of_lt (norm_le_abs_re_add_abs_im _)\n"
                "simpa [limAux] using hi j hj"
            ],
        },
    ],
    "MCB_106_lim_eq_lim_im_add_lim_re": [
        {
            "packet_id_suffix": "complex_lim_eq_re_im_positive_v1",
            "repair_family": "complex_limit_causeq_planner",
            "test_kind": "positive",
            "expected_outcome": "governed_repair_canary_closure",
            "backend": "repl_file",
            "timeout": 120,
            "extra_body": [
                "complex_lim_eq_re_im_v1::refine lim_eq_of_equiv_const ?_\n"
                "letI : IsAbsoluteValue (‖·‖ : ℂ → ℝ) := inferInstance\n"
                "calc\n"
                "  f ≈ _ := equiv_limAux f\n"
                "  _ = CauSeq.const (‖·‖) (↑(lim (cauSeqRe f)) + ↑(lim (cauSeqIm f)) * I) := by\n"
                "    exact CauSeq.ext fun _ =>\n"
                "      Complex.ext (by simp [limAux, cauSeqRe, ofReal]) (by simp [limAux, cauSeqIm, ofReal])"
            ],
        },
        {
            "packet_id_suffix": "complex_lim_eq_re_im_missing_equiv_negative_v1",
            "repair_family": "complex_limit_causeq_planner",
            "test_kind": "negative_control",
            "expected_outcome": "must_fail_without_equiv_limAux_bridge",
            "backend": "repl_file",
            "timeout": 80,
            "extra_body": [
                "complex_lim_eq_re_im_missing_equiv_negative::refine lim_eq_of_equiv_const ?_\n"
                "exact CauSeq.ext fun _ =>\n"
                "  Complex.ext (by simp [limAux, cauSeqRe, ofReal]) (by simp [limAux, cauSeqIm, ofReal])"
            ],
        },
    ],
    "MCB_107_lim_conj": [
        {
            "packet_id_suffix": "complex_lim_conj_positive_v1",
            "repair_family": "complex_limit_causeq_planner",
            "test_kind": "positive",
            "expected_outcome": "governed_repair_canary_closure",
            "backend": "repl_file",
            "timeout": 120,
            "extra_body": [
                "complex_lim_conj_v1::exact\n"
                "  Complex.ext (by simp [cauSeqConj, (lim_re _).symm, cauSeqRe])\n"
                "    (by simp [cauSeqConj, (lim_im _).symm, cauSeqIm, (lim_neg _).symm]; rfl)"
            ],
        },
        {
            "packet_id_suffix": "complex_lim_conj_missing_im_transport_negative_v1",
            "repair_family": "complex_limit_causeq_planner",
            "test_kind": "negative_control",
            "expected_outcome": "must_fail_without_imaginary_limit_transport",
            "backend": "repl_file",
            "timeout": 80,
            "extra_body": [
                "complex_lim_conj_missing_im_transport_negative::exact\n"
                "  Complex.ext (by simp [cauSeqConj, (lim_re _).symm, cauSeqRe])\n"
                "    (by simp [cauSeqConj, cauSeqIm]; rfl)"
            ],
        },
    ],
}

ZPOW_COVERING_TEMPLATES: dict[str, list[dict[str, Any]]] = {
    "MCB_138_isCoveringMapOn_zpow": [
        {
            "packet_id_suffix": "zpow_covering_on_from_subtype_positive_v1",
            "repair_family": "zpow_covering_subtype_transport_planner",
            "test_kind": "positive",
            "expected_outcome": "governed_repair_canary_closure",
            "backend": "repl_file",
            "timeout": 140,
            "extra_body": [
                "zpow_covering_on_from_subtype_v1::have (x : 𝕜) : x ^ n = 0 ↔ x = 0 := "
                "zpow_eq_zero_iff (by aesop)\n"
                "refine .of_isCoveringMap_restrictPreimage _ (by simp) ?_ ?_\n"
                "· convert isClosed_singleton (x := (0 : 𝕜)).isOpen_compl using 1\n"
                "  ext; simp [this]\n"
                "· convert (isCoveringMap_zpow n hn).comp_homeomorph (.setCongr _) using 1\n"
                "  ext; simpa using (this _).not"
            ],
        },
        {
            "packet_id_suffix": "zpow_covering_missing_zero_locus_negative_v1",
            "repair_family": "zpow_covering_subtype_transport_planner",
            "test_kind": "negative_control",
            "expected_outcome": "must_fail_without_zpow_zero_locus_transport",
            "backend": "repl_file",
            "timeout": 80,
            "extra_body": [
                "zpow_covering_missing_zero_locus_negative::refine "
                ".of_isCoveringMap_restrictPreimage _ (by simp) ?_ ?_\n"
                "· exact isClosed_singleton (x := (0 : 𝕜)).isOpen_compl\n"
                "· convert (isCoveringMap_zpow n hn).comp_homeomorph (.setCongr _) using 1\n"
                "  ext; simp"
            ],
        },
    ],
    "MCB_139_isQuotientCoveringMap_zpow": [
        {
            "packet_id_suffix": "zpow_quotient_covering_nat_neg_split_positive_v1",
            "repair_family": "zpow_quotient_covering_nat_neg_split_planner",
            "test_kind": "positive",
            "expected_outcome": "governed_repair_canary_closure",
            "backend": "repl_file",
            "timeout": 140,
            "extra_body": [
                "zpow_quotient_covering_nat_neg_split_v1::obtain ⟨n, rfl | rfl⟩ := n.eq_nat_or_neg\n"
                "· exact isQuotientCoveringMap_npow n (by aesop) (by simpa using surj)\n"
                "rw [show (zpowGroupHom (α := 𝕜ˣ) (-n)).ker = (powMonoidHom n).ker by ext; simp]\n"
                "convert (isQuotientCoveringMap_npow n (by aesop) _).homeomorph_comp (.inv 𝕜ˣ) using 1\n"
                "· ext; simp\n"
                "convert inv_involutive.surjective.comp surj; simp"
            ],
        },
        {
            "packet_id_suffix": "zpow_quotient_missing_negative_branch_negative_v1",
            "repair_family": "zpow_quotient_covering_nat_neg_split_planner",
            "test_kind": "negative_control",
            "expected_outcome": "must_fail_without_negative_exponent_homeomorph_transport",
            "backend": "repl_file",
            "timeout": 80,
            "extra_body": [
                "zpow_quotient_missing_negative_branch_negative::obtain ⟨n, rfl | rfl⟩ := n.eq_nat_or_neg\n"
                "· exact isQuotientCoveringMap_npow n (by aesop) (by simpa using surj)\n"
                "· exact isQuotientCoveringMap_npow n (by aesop) (by simpa using surj)"
            ],
        },
    ],
}

QPARAM_CUSP_TEMPLATES: dict[str, list[dict[str, Any]]] = {
    "MCB_140_qParam_tendsto": [
        {
            "packet_id_suffix": "qparam_tendsto_norm_exp_positive_v1",
            "repair_family": "qparam_tendsto_norm_exp_planner",
            "test_kind": "positive",
            "expected_outcome": "governed_repair_canary_closure",
            "backend": "repl_file",
            "timeout": 140,
            "extra_body": [
                "qparam_tendsto_norm_exp_v1::refine tendsto_nhdsWithin_of_tendsto_nhds_of_eventually_within _ ?_\n"
                "  (.of_forall fun q ↦ exp_ne_zero _)\n"
                "rw [tendsto_zero_iff_norm_tendsto_zero]\n"
                "simp only [norm_qParam]\n"
                "apply (tendsto_comap'_iff (m := fun y ↦ Real.exp (-2 * π * y / h)) (range_im ▸ univ_mem)).mpr\n"
                "refine Real.tendsto_exp_atBot.comp (.atBot_div_const hh (tendsto_id.const_mul_atTop_of_neg ?_))\n"
                "simpa using Real.pi_pos"
            ],
        },
        {
            "packet_id_suffix": "qparam_tendsto_missing_norm_exp_negative_v1",
            "repair_family": "qparam_tendsto_norm_exp_planner",
            "test_kind": "negative_control",
            "expected_outcome": "must_fail_without_norm_qparam_exp_decay_bridge",
            "backend": "repl_file",
            "timeout": 80,
            "extra_body": [
                "qparam_tendsto_missing_norm_exp_negative::refine "
                "tendsto_nhdsWithin_of_tendsto_nhds_of_eventually_within _ ?_\n"
                "  (.of_forall fun q ↦ exp_ne_zero _)\n"
                "rw [tendsto_zero_iff_norm_tendsto_zero]\n"
                "exact tendsto_const_nhds"
            ],
        },
    ],
    "MCB_141_eq_cuspFunction": [
        {
            "packet_id_suffix": "cusp_function_qparam_left_inverse_positive_v1",
            "repair_family": "cusp_function_qparam_periodic_planner",
            "test_kind": "positive",
            "expected_outcome": "governed_repair_canary_closure",
            "backend": "repl_file",
            "timeout": 120,
            "extra_body": [
                "cusp_function_qparam_left_inverse_v1::have : (cuspFunction h f) (𝕢 h z) = "
                "f (invQParam h (𝕢 h z)) := by\n"
                "  rw [cuspFunction, update_of_ne, comp_apply]\n"
                "  exact exp_ne_zero _\n"
                "obtain ⟨m, hm⟩ := qParam_left_inv_mod_period hh z\n"
                "simpa only [this, hm] using hf.int_mul m z"
            ],
        },
        {
            "packet_id_suffix": "cusp_function_missing_periodicity_negative_v1",
            "repair_family": "cusp_function_qparam_periodic_planner",
            "test_kind": "negative_control",
            "expected_outcome": "must_fail_without_periodicity_transport_from_inverse_qparam",
            "backend": "repl_file",
            "timeout": 70,
            "extra_body": [
                "cusp_function_missing_periodicity_negative::have : (cuspFunction h f) (𝕢 h z) = "
                "f (invQParam h (𝕢 h z)) := by\n"
                "  rw [cuspFunction, update_of_ne, comp_apply]\n"
                "  exact exp_ne_zero _\n"
                "obtain ⟨m, hm⟩ := qParam_left_inv_mod_period hh z\n"
                "simpa only [this, hm]"
            ],
        },
    ],
}

ASYMPTOTICS_BIGO_TEMPLATES: dict[str, list[dict[str, Any]]] = {
    "MCB_158_isBigOWith_of_eq_mul": [
        {
            "packet_id_suffix": "bigo_with_eq_mul_positive_v1",
            "repair_family": "asymptotics_bigo_eq_mul_planner",
            "test_kind": "positive",
            "expected_outcome": "governed_repair_canary_closure",
            "backend": "repl_file",
            "timeout": 120,
            "extra_body": [
                "bigo_with_eq_mul_v1::simp only [IsBigOWith_def]\n"
                "refine h.symm.rw (fun x a => ‖a‖ ≤ c * ‖v x‖) (hφ.mono fun x hx => ?_)\n"
                "simp only [Pi.mul_apply]\n"
                "refine (norm_mul_le _ _).trans ?_\n"
                "gcongr"
            ],
        },
        {
            "packet_id_suffix": "bigo_with_missing_eq_mul_negative_v1",
            "repair_family": "asymptotics_bigo_eq_mul_planner",
            "test_kind": "negative_control",
            "expected_outcome": "must_fail_without_eventual_eq_mul_transport",
            "backend": "repl_file",
            "timeout": 70,
            "extra_body": [
                "bigo_with_missing_eq_mul_negative::simp only [IsBigOWith_def]\n"
                "exact hφ"
            ],
        },
    ],
    "MCB_159_isBigOWith_iff_exists_eq_mul": [
        {
            "packet_id_suffix": "bigo_with_exists_eq_mul_positive_v1",
            "repair_family": "asymptotics_bigo_eq_mul_planner",
            "test_kind": "positive",
            "expected_outcome": "governed_repair_canary_closure",
            "backend": "repl_file",
            "timeout": 140,
            "extra_body": [
                "bigo_with_exists_eq_mul_v1::constructor\n"
                "· intro h\n"
                "  use fun x => u x / v x\n"
                "  refine ⟨Eventually.mono h.bound fun y hy => ?_, h.eventually_mul_div_cancel.symm⟩\n"
                "  simpa using div_le_of_le_mul₀ (norm_nonneg _) hc hy\n"
                "· rintro ⟨φ, hφ, h⟩\n"
                "  exact isBigOWith_of_eq_mul φ hφ h"
            ],
        },
        {
            "packet_id_suffix": "bigo_with_exists_missing_nonneg_negative_v1",
            "repair_family": "asymptotics_bigo_eq_mul_planner",
            "test_kind": "negative_control",
            "expected_outcome": "must_fail_without_nonnegative_constant_transport",
            "backend": "repl_file",
            "timeout": 90,
            "extra_body": [
                "bigo_with_exists_missing_nonneg_negative::constructor\n"
                "· intro h\n"
                "  use fun x => u x / v x\n"
                "  refine ⟨Eventually.mono h.bound fun y hy => ?_, h.eventually_mul_div_cancel.symm⟩\n"
                "  simpa using hy\n"
                "· rintro ⟨φ, hφ, h⟩\n"
                "  exact isBigOWith_of_eq_mul φ hφ h"
            ],
        },
    ],
}

CONVOLUTION_ARGUMENT_TEMPLATES: dict[str, list[dict[str, Any]]] = {
    "MCB_003_convolution_mono_right_of_nonneg": [
        {
            "packet_id_suffix": "convolution_mono_right_nonneg_split_positive_v1",
            "repair_family": "convolution_argument_planner",
            "test_kind": "positive",
            "expected_outcome": "governed_repair_canary_closure",
            "backend": "repl_file",
            "timeout": 140,
            "extra_body": [
                "convolution_mono_right_nonneg_split_v1::by_cases hfg : "
                "ConvolutionExistsAt f g x (lsmul ℝ ℝ) μ\n"
                "· exact convolution_mono_right hfg hfg' hf hg\n"
                "· rw [ConvolutionExistsAt] at hfg\n"
                "  rw [convolution_def, integral_undef hfg]\n"
                "  exact integral_nonneg fun y => mul_nonneg (hf _) (hg' _)"
            ],
        },
        {
            "packet_id_suffix": "convolution_mono_right_missing_undef_branch_negative_v1",
            "repair_family": "convolution_argument_planner",
            "test_kind": "negative_control",
            "expected_outcome": "must_fail_without_missing_convolution_undef_branch",
            "backend": "repl_file",
            "timeout": 80,
            "extra_body": [
                "convolution_mono_right_missing_undef_branch_negative::exact "
                "convolution_mono_right hfg' hfg' hf hg"
            ],
        },
    ],
}

ENNREAL_TSUM_CONDENSATION_TEMPLATES: dict[str, list[dict[str, Any]]] = {
    "MCB_017_le_tsum_condensed": [
        {
            "packet_id_suffix": "ennreal_le_tsum_condensed_positive_v1",
            "repair_family": "ennreal_tsum_condensation_planner",
            "test_kind": "positive",
            "expected_outcome": "governed_repair_canary_closure",
            "backend": "repl_file",
            "timeout": 140,
            "extra_body": [
                "ennreal_le_tsum_condensed_v1::rw "
                "[ENNReal.tsum_eq_iSup_nat' (tendsto_pow_atTop_atTop_of_one_lt _root_.one_lt_two)]\n"
                "refine iSup_le fun n => (Finset.le_sum_condensed hf n).trans ?_\n"
                "simp only [nsmul_eq_mul, Nat.cast_pow, Nat.cast_two]\n"
                "grw [ENNReal.sum_le_tsum]"
            ],
        },
        {
            "packet_id_suffix": "ennreal_le_tsum_condensed_missing_tsum_bridge_negative_v1",
            "repair_family": "ennreal_tsum_condensation_planner",
            "test_kind": "negative_control",
            "expected_outcome": "must_fail_without_finite_sum_to_tsum_bridge",
            "backend": "repl_file",
            "timeout": 80,
            "extra_body": [
                "ennreal_le_tsum_condensed_missing_tsum_bridge_negative::rw "
                "[ENNReal.tsum_eq_iSup_nat' (tendsto_pow_atTop_atTop_of_one_lt _root_.one_lt_two)]\n"
                "refine iSup_le fun n => ?_\n"
                "simpa only [nsmul_eq_mul, Nat.cast_pow, Nat.cast_two] using Finset.le_sum_condensed hf n"
            ],
        },
    ],
    "MCB_018_summable_condensed_iff": [
        {
            "packet_id_suffix": "nnreal_summable_condensed_positive_v1",
            "repair_family": "ennreal_tsum_condensation_planner",
            "test_kind": "positive",
            "expected_outcome": "governed_repair_canary_closure",
            "backend": "repl_file",
            "timeout": 140,
            "extra_body": [
                "nnreal_summable_condensed_v1::have h_succ_diff : SuccDiffBounded 2 (2 ^ ·) := by\n"
                "  intro n\n"
                "  simp [pow_succ, mul_two, two_mul]\n"
                "convert summable_schlomilch_iff hf (pow_pos zero_lt_two) "
                "(pow_right_strictMono₀ _root_.one_lt_two) two_ne_zero h_succ_diff\n"
                "simp [pow_succ, mul_two]"
            ],
        },
        {
            "packet_id_suffix": "nnreal_summable_condensed_missing_diff_normalization_negative_v1",
            "repair_family": "ennreal_tsum_condensation_planner",
            "test_kind": "negative_control",
            "expected_outcome": "must_fail_without_power_succ_difference_normalization",
            "backend": "repl_file",
            "timeout": 80,
            "extra_body": [
                "nnreal_summable_condensed_missing_diff_normalization_negative::have h_succ_diff : "
                "SuccDiffBounded 2 (2 ^ ·) := by\n"
                "  intro n\n"
                "  simp [pow_succ, mul_two, two_mul]\n"
                "exact summable_schlomilch_iff hf (pow_pos zero_lt_two) "
                "(pow_right_strictMono₀ _root_.one_lt_two) two_ne_zero h_succ_diff"
            ],
        },
    ],
    "MCB_019_summable_condensed_iff_of_nonneg": [
        {
            "packet_id_suffix": "real_summable_condensed_nonneg_positive_v1",
            "repair_family": "ennreal_tsum_condensation_planner",
            "test_kind": "positive",
            "expected_outcome": "governed_repair_canary_closure",
            "backend": "repl_file",
            "timeout": 140,
            "extra_body": [
                "real_summable_condensed_nonneg_v1::have h_succ_diff : SuccDiffBounded 2 (2 ^ ·) := by\n"
                "  intro n\n"
                "  simp [pow_succ, mul_two, two_mul]\n"
                "convert summable_schlomilch_iff_of_nonneg h_nonneg h_mono (pow_pos zero_lt_two) "
                "(pow_right_strictMono₀ _root_.one_lt_two) two_ne_zero h_succ_diff\n"
                "simp [pow_succ, mul_two]"
            ],
        },
        {
            "packet_id_suffix": "real_summable_condensed_missing_nonneg_lift_negative_v1",
            "repair_family": "ennreal_tsum_condensation_planner",
            "test_kind": "negative_control",
            "expected_outcome": "must_fail_without_real_to_nnreal_nonnegative_lift",
            "backend": "repl_file",
            "timeout": 80,
            "extra_body": [
                "real_summable_condensed_missing_nonneg_lift_negative::have h_succ_diff : "
                "SuccDiffBounded 2 (2 ^ ·) := by\n"
                "  intro n\n"
                "  simp [pow_succ, mul_two, two_mul]\n"
                "exact_mod_cast NNReal.summable_condensed_iff h_mono"
            ],
        },
    ],
}

INTERVAL_ALIGNMENT_TEMPLATES: dict[str, list[dict[str, Any]]] = {
    "MCB_022_sum_Ioo_inv_sq_le": [
        {
            "packet_id_suffix": "sum_ioo_inv_sq_interval_alignment_positive_v1",
            "repair_family": "interval_alignment_planner",
            "test_kind": "positive",
            "expected_outcome": "governed_repair_canary_closure",
            "backend": "repl_file",
            "timeout": 160,
            "extra_body": [
                "sum_ioo_inv_sq_interval_alignment_v1::calc\n"
                "  (∑ i ∈ Ioo k n, ((i : α) ^ 2)⁻¹) ≤ ∑ i ∈ Ioc k (max (k + 1) n), "
                "((i : α) ^ 2)⁻¹ := by\n"
                "    apply sum_le_sum_of_subset_of_nonneg\n"
                "    · intro x hx\n"
                "      simp only [mem_Ioo] at hx\n"
                "      simp only [hx, hx.2.le, mem_Ioc, le_max_iff, or_true, and_self_iff]\n"
                "    · intro i _hi _hident\n"
                "      positivity\n"
                "  _ ≤ ((k + 1 : α) ^ 2)⁻¹ + ∑ i ∈ Ioc k.succ (max (k + 1) n), "
                "((i : α) ^ 2)⁻¹ := by\n"
                "    rw [← Icc_add_one_left_eq_Ioc, ← Ico_add_one_right_eq_Icc, sum_eq_sum_Ico_succ_bot]\n"
                "    swap; · exact Nat.succ_lt_succ ((Nat.lt_succ_self k).trans_le (le_max_left _ _))\n"
                "    rw [Ico_add_one_right_eq_Icc, Icc_add_one_left_eq_Ioc]\n"
                "    norm_cast\n"
                "  _ ≤ ((k + 1 : α) ^ 2)⁻¹ + (k + 1 : α)⁻¹ := by\n"
                "    refine add_le_add le_rfl ((sum_Ioc_inv_sq_le_sub ?_ (le_max_left _ _)).trans ?_)\n"
                "    · simp only [Ne, Nat.succ_ne_zero, not_false_iff]\n"
                "    · simp only [Nat.cast_succ, sub_le_self_iff, inv_nonneg, Nat.cast_nonneg]\n"
                "  _ ≤ 1 / (k + 1) + 1 / (k + 1) := by\n"
                "    have A : (1 : α) ≤ k + 1 := by simp only [le_add_iff_nonneg_left, Nat.cast_nonneg]\n"
                "    simp_rw [← one_div]\n"
                "    gcongr\n"
                "    simpa using pow_right_mono₀ A one_le_two\n"
                "  _ = 2 / (k + 1) := by ring"
            ],
        },
        {
            "packet_id_suffix": "sum_ioo_inv_sq_wrong_endpoint_negative_v1",
            "repair_family": "interval_alignment_planner",
            "test_kind": "negative_control",
            "expected_outcome": "must_fail_without_max_endpoint_widening",
            "backend": "repl_file",
            "timeout": 80,
            "extra_body": [
                "sum_ioo_inv_sq_wrong_endpoint_negative::calc\n"
                "  (∑ i ∈ Ioo k n, ((i : α) ^ 2)⁻¹) ≤ ∑ i ∈ Ioc k n, ((i : α) ^ 2)⁻¹ := by\n"
                "    apply sum_le_sum_of_subset_of_nonneg\n"
                "    · intro x hx\n"
                "      simp only [mem_Ioo] at hx\n"
                "      simp only [hx, hx.2.le, mem_Ioc, and_self_iff]\n"
                "    · intro i _hi _hident\n"
                "      positivity\n"
                "  _ ≤ (k : α)⁻¹ - (n : α)⁻¹ := by\n"
                "    exact sum_Ioc_inv_sq_le_sub (by simp) (Nat.zero_le n)\n"
                "  _ ≤ 2 / (k + 1) := by positivity"
            ],
        },
    ],
}

CURATED_REPAIR_TEMPLATES: dict[str, list[dict[str, Any]]] = {
    **SPECTRAL_CLUSTER_REPAIR_TEMPLATES,
    **LIMIT_CAUSEQ_COMPLEX_TEMPLATES,
    **ZPOW_COVERING_TEMPLATES,
    **QPARAM_CUSP_TEMPLATES,
    **ASYMPTOTICS_BIGO_TEMPLATES,
    **CONVOLUTION_ARGUMENT_TEMPLATES,
    **ENNREAL_TSUM_CONDENSATION_TEMPLATES,
    **INTERVAL_ALIGNMENT_TEMPLATES,
    **SPEC_REPAIR_TEMPLATES,
    "MCB_083_IsSelfAdjoint": CSTAR_SELFADJOINT_SPECTRAL_RADIUS_TEMPLATES,
    "MCB_084_IsSelfAdjoint": CSTAR_SELFADJOINT_SPECTRAL_RADIUS_TEMPLATES,
    "MCB_009_kerFun_dense": [
        {
            "packet_id_suffix": "rkhs_density_orthogonal_positive_v1",
            "repair_family": "rkhs_density_orthogonal_complement_planner",
            "test_kind": "positive",
            "expected_outcome": "governed_repair_canary_closure",
            "backend": "repl_file",
            "timeout": 120,
            "extra_body": [
                "rkhs_dense_orthogonal_v2::rw [Submodule.topologicalClosure_eq_top_iff]\n"
                "rw [Submodule.eq_bot_iff]\n"
                "intro f hf\n"
                "ext x\n"
                "refine ext_inner_left 𝕜 fun v => ?_\n"
                "have hmem : kerFun H x v ∈ span 𝕜 {kerFun H x v | (x) (v)} := by\n"
                "  exact subset_span ⟨x, v, rfl⟩\n"
                "have horth := hf (kerFun H x v) hmem\n"
                "simpa [inner_kerFun] using horth"
            ],
        },
        {
            "packet_id_suffix": "rkhs_density_missing_membership_negative_v1",
            "repair_family": "rkhs_density_orthogonal_complement_planner",
            "test_kind": "negative_control",
            "expected_outcome": "must_fail_without_kernel_span_membership",
            "backend": "repl_file",
            "timeout": 60,
            "extra_body": [
                "rkhs_dense_missing_membership_negative::rw [Submodule.topologicalClosure_eq_top_iff]\n"
                "rw [Submodule.eq_bot_iff]\n"
                "intro f hf\n"
                "ext x\n"
                "refine ext_inner_left 𝕜 fun v => ?_\n"
                "have horth := hf (kerFun H x v) (by simp)\n"
                "simpa [inner_kerFun] using horth"
            ],
        },
    ],
    "MCB_006_hasConstantSpeedOnWith_of_subsin": [
        {
            "packet_id_suffix": "metric_speed_subsingleton_positive_v1",
            "repair_family": "metric_speed_subsingleton_planner",
            "test_kind": "positive",
            "expected_outcome": "governed_repair_canary_closure",
            "backend": "repl_file",
            "timeout": 120,
            "extra_body": [
                "metric_speed_subsingleton_v1::rintro x hx y hy\n"
                "cases hs hx hy\n"
                "rw [eVariationOn.subsingleton]\n"
                "· simp\n"
                "· intro z hz w hw\n"
                "  exact (le_antisymm hz.2.2 hz.2.1).trans (le_antisymm hw.2.2 hw.2.1).symm"
            ],
        },
        {
            "packet_id_suffix": "metric_speed_missing_hs_negative_v1",
            "repair_family": "metric_speed_subsingleton_planner",
            "test_kind": "negative_control",
            "expected_outcome": "must_fail_without_using_subsingleton_hypothesis",
            "backend": "repl_file",
            "timeout": 60,
            "extra_body": [
                "metric_speed_missing_subsingleton_negative::rintro x hx y hy\n"
                "rw [eVariationOn.subsingleton]\n"
                "· simp\n"
                "· intro z hz w hw\n"
                "  exact (le_antisymm hz.2.2 hz.2.1).trans (le_antisymm hw.2.2 hw.2.1).symm"
            ],
        },
    ],
}


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    out: list[dict[str, Any]] = []
    for line in path.read_text(errors="ignore").splitlines():
        if not line.strip():
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            out.append({
                "event": "malformed_jsonl",
                "sample_tail": line[-500:],
                "row_id": "",
                "lane": path.parent.parent.name,
            })
    return out


def _residual_paths(root: Path) -> list[Path]:
    if root.is_file():
        return [root]
    paths = list(root.glob("*/events/residual_compiler_residuals.jsonl"))
    paths.extend(root.glob("*/events/path_c_residuals.jsonl"))
    return sorted({str(path): path for path in paths}.values())


def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _packet_id(rec: dict[str, Any], suffix: str, *, repair_family: str | None = None) -> str:
    family = str(repair_family or rec.get("repair_family") or "unfamilied")
    return f"{rec.get('lane')}:{rec.get('row_id')}:{rec.get('residual_class')}:{family}:{suffix}"


def _infer_repair_family(*, row_id: str, lane: str, residual: str, tail: str) -> str | None:
    """Coarse residual-family routing for non-curated rows.

    This does not create proof credit or executable canaries. It only prevents
    new residual streams from falling into an anonymous `needs_template` pile.
    """
    hay = f"{row_id}\n{lane}\n{residual}\n{tail}"
    if lane == "bigo_specialization" or "Asymptotics.IsBigO" in hay or "IsLittleO_def" in hay:
        return "asymptotics_bigo_def_unfold_planner"
    if "abel_aux" in hay or "stolzSet" in hay or "powerSeries" in hay:
        return "abel_stolz_power_series_planner"
    if lane == "mellin_fourier_transport":
        return "mellin_fourier_transport_planner"
    if lane == "limit_tendsto_transport" or "Tendsto" in hay:
        return "limit_tendsto_transport_planner"
    if lane == "rpow_inequality_transport":
        return "rpow_inequality_transport_planner"
    if (
        lane == "iff_direction"
        or row_id in {
            "MCB_025_geom_mean_eq_arith_mean_weighted",
            "MCB_026_geom_mean_eq_arith_mean_weighted",
        }
        or "geom_mean_eq_arith_mean_weighted" in hay
    ):
        return "iff_direction_planner"
    return None


def _compile_one(rec: dict[str, Any], *, static_filter: str) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    row_id = str(rec.get("row_id") or "")
    lane = str(rec.get("lane") or "")
    residual = str(rec.get("residual_class") or "unknown")
    tail = str(rec.get("sample_tail") or "")
    inferred_family = _infer_repair_family(row_id=row_id, lane=lane, residual=residual, tail=tail)
    base_decision = {
        "row_id": row_id,
        "lane": lane,
        "residual_class": residual,
        "repair_family": inferred_family,
        "evidence_tail": tail[-700:],
        "created_at": _now_iso(),
    }

    if row_id in GOLD_CONTAMINATED_ROWS:
        return None, {
            **base_decision,
            "decision": "quarantine_practice_control",
            "reason": "gold_proof_body_visible_in_current_mathlib_source",
            "next_lever": "extract abstract template only; no clean credit",
        }

    if row_id in CURATED_REPAIR_TEMPLATES:
        first = CURATED_REPAIR_TEMPLATES[row_id][0]
        return {
            "packet_id": _packet_id(rec, str(first["packet_id_suffix"]), repair_family=str(first["repair_family"])),
            "repair_family": first["repair_family"],
            "row_id": row_id,
            "candidate_name": None,
            "action_family": "manual_extra",
            "test_kind": first["test_kind"],
            "expected_outcome": first["expected_outcome"],
            "backend": first["backend"],
            "timeout": first["timeout"],
            "max_candidates": 1,
            "max_actions": 1,
            "score_candidates": False,
            "require_positive_source_action": False,
            "source_credit_eligible": bool(first.get("source_credit_eligible", False)),
            "clean_solver_credit_eligible": bool(first.get("clean_solver_credit_eligible", False)),
            "static_filter": static_filter,
            "extra_body": first["extra_body"],
            "family_spec_path": first.get("spec_path"),
        }, {
            **base_decision,
            "decision": "executable_curated_repair_canary",
            "reason": "row matches a governed residual-template family",
            "next_lever": f"run curated {first['repair_family']} canary with governance and negative control",
        }

    if residual == "repl_step_context_gap":
        return {
            "packet_id": _packet_id(rec, "file_backend_calibration"),
            "repair_family": "backend_context_fallback_planner",
            "row_id": row_id,
            "candidate_name": None,
            "action_family": "apply_easy",
            "test_kind": "positive",
            "expected_outcome": "file_backend_distinguishes_backend_artifact_from_typed_gap",
            "backend": "repl_file",
            "timeout": 90,
            "max_candidates": 1,
            "max_actions": 1,
            "score_candidates": False,
            "require_positive_source_action": False,
            "source_credit_eligible": False,
            "clean_solver_credit_eligible": False,
            "static_filter": static_filter,
        }, {
            **base_decision,
            "decision": "executable_canary",
            "reason": "fast backend reported context gap; file backend calibration is bounded and informative",
            "next_lever": "run repl_file one-candidate fallback",
        }

    if residual == "timeout":
        return None, {
            **base_decision,
            "decision": "decompose_before_retry",
        "reason": "row exceeded hard Proof Execution wall budget",
            "next_lever": "reduce candidate/action breadth or build smaller row-local canary",
        }

    if residual == "directional_iff_gap":
        return None, {
            **base_decision,
            "decision": "needs_template",
            "reason": "cheap source action produced a subgoal; generic retry risks gold/template laundering",
            "next_lever": "write row-family direction split with negative control, then run as repair_canary",
        }

    if residual in {"no_positive_source_action", "no_candidate_action_generated"}:
        return None, {
            **base_decision,
            "decision": "needs_template_or_source",
            "reason": "source resolved but exact/simpa/apply had no positive kernel delta",
            "next_lever": "source typed adapter or multistep repair; do not rerun generic apply",
        }

    if residual in {"source_action_mismatch", "type_mismatch", "missing_instance", "lean_error"}:
        next_lever = str(rec.get("next_lever") or "compile a typed adapter canary")
        if inferred_family == "asymptotics_bigo_def_unfold_planner":
            next_lever = (
                "write a guarded asymptotics-definition/unfold canary: positive uses the exact "
                "IsBigO/IsBigOWith/IsLittleO definitional bridge; negative removes the required "
                "bound/tendsto witness or uses the wrong direction"
            )
        elif inferred_family == "abel_stolz_power_series_planner":
            next_lever = (
                "decompose Abel/Stolz power-series target into the missing bridge from abel_aux "
                "output shape to the target Tendsto statement; negative should omit the partial-sum "
                "Tendsto hypothesis"
            )
            return None, {
                **base_decision,
                "decision": "exact_gap_candidate",
                "reason": "abel_aux is only the pointwise source; target needs the full Abel/Stolz estimate bridge",
                "next_lever": next_lever,
            }
        elif inferred_family == "iff_direction_planner":
            next_lever = (
                "exact-gap packet: the available constant/equality lemmas cover one direction, but the target "
                "iff needs the positive-weight AM-GM equality characterization, including zero-case splitting "
                "and strict-convexity equality transport; do not run a broad constructor/apply retry"
            )
            return None, {
                **base_decision,
                "decision": "exact_gap_candidate",
                "reason": "source candidates identify the equality-condition surface, but the missing object is the full iff proof skeleton",
                "next_lever": next_lever,
            }
        return None, {
            **base_decision,
            "decision": "needs_template",
            "reason": "kernel produced a typed mismatch/subgoal rather than closure",
            "next_lever": next_lever,
        }

    return None, {
        **base_decision,
        "decision": "hold_for_recurrence",
        "reason": "single weak residual; no safe generic executable canary",
        "next_lever": "wait for recurrence or source a family-specific template",
    }


def build(args: argparse.Namespace) -> dict[str, Any]:
    residuals: list[dict[str, Any]] = []
    for root_s in args.root:
        root = Path(root_s)
        for path in _residual_paths(root):
            for rec in _read_jsonl(path):
                rec = dict(rec)
                rec.setdefault("source_path", str(path))
                residuals.append(rec)

    tests: list[dict[str, Any]] = []
    decisions: list[dict[str, Any]] = []
    seen_tests: set[str] = set()
    seen_decisions: set[tuple[str, str, str]] = set()
    for rec in residuals:
        test, decision = _compile_one(rec, static_filter=args.static_filter)
        dkey = (
            str(decision.get("row_id") or ""),
            str(decision.get("residual_class") or ""),
            str(decision.get("decision") or ""),
        )
        if dkey not in seen_decisions:
            seen_decisions.add(dkey)
            decisions.append(decision)
        if test:
            tid = str(test.get("packet_id"))
            if tid not in seen_tests:
                seen_tests.add(tid)
                tests.append(test)
            row_id = str(test.get("row_id") or "")
            rec_like = dict(rec)
            for extra in CURATED_REPAIR_TEMPLATES.get(row_id, [])[1:]:
                extra_test = {
                    **test,
                    "packet_id": _packet_id(rec_like, str(extra["packet_id_suffix"]), repair_family=str(extra["repair_family"])),
                    "repair_family": extra["repair_family"],
                    "test_kind": extra["test_kind"],
                    "expected_outcome": extra["expected_outcome"],
                    "backend": extra["backend"],
                    "timeout": extra["timeout"],
                    "extra_body": extra["extra_body"],
                    "source_credit_eligible": bool(extra.get("source_credit_eligible", test.get("source_credit_eligible", False))),
                    "clean_solver_credit_eligible": bool(extra.get("clean_solver_credit_eligible", test.get("clean_solver_credit_eligible", False))),
                    "family_spec_path": extra.get("spec_path", test.get("family_spec_path")),
                }
                tid = str(extra_test.get("packet_id"))
                if tid not in seen_tests:
                    seen_tests.add(tid)
                    tests.append(extra_test)

    by_decision: dict[str, int] = {}
    for d in decisions:
        key = str(d.get("decision") or "unknown")
        by_decision[key] = by_decision.get(key, 0) + 1
    packet = {
        "schema": "leanmill-residual-compiler-compiled-canaries-v1",
        "generated_at": _now_iso(),
        "residual_event_count": len(residuals),
        "test_count": len(tests),
        "decision_count": len(decisions),
        "packets": [{
            "repair_family": "compiled_residual_compiler_residuals",
            "tests": tests,
            "state": "ready_for_drain" if tests else "no_executable_tests",
            "science_rule": "Executable canaries are WIP only; value credit requires Governance Gate ratification or exact-gap/falsifier adjudication.",
        }],
    }
    decisions_obj = {
        "schema": "leanmill-residual-compiler-decisions-v1",
        "generated_at": packet["generated_at"],
        "roots": args.root,
        "by_decision": by_decision,
        "decisions": decisions,
    }
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(packet, indent=2, sort_keys=True) + "\n")
    if args.decisions_out:
        Path(args.decisions_out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.decisions_out).write_text(json.dumps(decisions_obj, indent=2, sort_keys=True) + "\n")
    return {"packet": packet, "decisions": decisions_obj}


def _self_test() -> int:
    test, decision = _compile_one(
        {"lane": "x", "row_id": "r", "residual_class": "repl_step_context_gap", "sample_tail": "Unknown"},
        static_filter="f.json",
    )
    assert test and test["backend"] == "repl_file"
    assert decision["decision"] == "executable_canary"
    test, decision = _compile_one(
        {"lane": "x", "row_id": "MCB_012_contDiffOn_univBall_symm", "residual_class": "directional_iff_gap"},
        static_filter="f.json",
    )
    assert test is None and decision["decision"] == "quarantine_practice_control"
    test, decision = _compile_one(
        {"lane": "x", "row_id": "MCB_009_kerFun_dense", "residual_class": "no_positive_source_action"},
        static_filter="f.json",
    )
    assert test and test["action_family"] == "manual_extra"
    assert decision["decision"] == "executable_curated_repair_canary"
    test, decision = _compile_one(
        {"lane": "x", "row_id": "MCB_083_IsSelfAdjoint", "residual_class": "no_positive_source_action"},
        static_filter="f.json",
    )
    assert test and test["repair_family"] == "cstar_selfadjoint_spectral_radius_planner"
    assert test["source_credit_eligible"] is False
    assert test["clean_solver_credit_eligible"] is False
    assert decision["decision"] == "executable_curated_repair_canary"
    test, decision = _compile_one(
        {"lane": "x", "row_id": "MCB_081_Unitary", "residual_class": "source_action_mismatch"},
        static_filter="f.json",
    )
    assert test and test["repair_family"] == "cstar_unitary_spectrum_circle_planner"
    assert test["action_family"] == "manual_extra"
    assert test["source_credit_eligible"] is False
    assert test["clean_solver_credit_eligible"] is False
    assert decision["decision"] == "executable_curated_repair_canary"
    test, decision = _compile_one(
        {"lane": "x", "row_id": "MCB_107_lim_conj", "residual_class": "no_positive_source_action"},
        static_filter="f.json",
    )
    assert test and test["repair_family"] == "complex_limit_causeq_planner"
    assert test["action_family"] == "manual_extra"
    assert test["source_credit_eligible"] is False
    assert test["clean_solver_credit_eligible"] is False
    assert decision["decision"] == "executable_curated_repair_canary"
    for spectral_row in (
        "MCB_060_posDef_gram_of_linearIndependent",
        "MCB_074_eigenvalue_nonneg_of_nonneg",
        "MCB_081_Unitary",
    ):
        assert len(CURATED_REPAIR_TEMPLATES[spectral_row]) == 2
        assert CURATED_REPAIR_TEMPLATES[spectral_row][0]["test_kind"] == "positive"
        assert CURATED_REPAIR_TEMPLATES[spectral_row][1]["test_kind"] == "negative_control"
    for limit_row in LIMIT_CAUSEQ_COMPLEX_TEMPLATES:
        assert len(CURATED_REPAIR_TEMPLATES[limit_row]) == 2
        assert CURATED_REPAIR_TEMPLATES[limit_row][0]["test_kind"] == "positive"
        assert CURATED_REPAIR_TEMPLATES[limit_row][1]["test_kind"] == "negative_control"
    for row in (
        "MCB_138_isCoveringMapOn_zpow",
        "MCB_139_isQuotientCoveringMap_zpow",
        "MCB_140_qParam_tendsto",
        "MCB_141_eq_cuspFunction",
    ):
        assert len(CURATED_REPAIR_TEMPLATES[row]) == 2
        assert CURATED_REPAIR_TEMPLATES[row][0]["test_kind"] == "positive"
        assert CURATED_REPAIR_TEMPLATES[row][1]["test_kind"] == "negative_control"
        test, decision = _compile_one(
            {"lane": "x", "row_id": row, "residual_class": "source_action_mismatch"},
            static_filter="f.json",
        )
        assert test and test["action_family"] == "manual_extra"
        assert test["source_credit_eligible"] is False
        assert test["clean_solver_credit_eligible"] is False
        assert decision["decision"] == "executable_curated_repair_canary"
    test, decision = _compile_one(
        {"lane": "bigo_specialization", "row_id": "MCB_158_isBigOWith_of_eq_mul", "residual_class": "source_action_mismatch"},
        static_filter="f.json",
    )
    assert test and test["repair_family"] == "asymptotics_bigo_eq_mul_planner"
    assert test["source_credit_eligible"] is False
    assert decision["decision"] == "executable_curated_repair_canary"
    test, decision = _compile_one(
        {
            "lane": "bigo_specialization",
            "row_id": "MCB_159_isBigOWith_iff_exists_eq_mul",
            "residual_class": "source_action_mismatch",
        },
        static_filter="f.json",
    )
    assert test and test["repair_family"] == "asymptotics_bigo_eq_mul_planner"
    assert test["source_credit_eligible"] is False
    assert decision["decision"] == "executable_curated_repair_canary"
    test, decision = _compile_one(
        {
            "lane": "bigo_specialization",
            "row_id": "MCB_x",
            "residual_class": "source_action_mismatch",
            "sample_tail": "Tactic `apply` failed: could not unify `Asymptotics.IsBigOWith_def`",
        },
        static_filter="f.json",
    )
    assert test is None and decision["repair_family"] == "asymptotics_bigo_def_unfold_planner"
    for row in (
        "MCB_017_le_tsum_condensed",
        "MCB_018_summable_condensed_iff",
        "MCB_019_summable_condensed_iff_of_nonneg",
        "MCB_022_sum_Ioo_inv_sq_le",
    ):
        kinds = {str(t.get("test_kind") or "") for t in CURATED_REPAIR_TEMPLATES[row]}
        assert "positive" in kinds
        assert "negative_control" in kinds
        test, decision = _compile_one(
            {"lane": "interval_alignment", "row_id": row, "residual_class": "source_action_mismatch"},
            static_filter="f.json",
        )
        assert test and test["repair_family"] in {
            "convolution_argument_planner",
            "ennreal_tsum_condensation_planner",
            "interval_alignment_planner",
        }
        assert test["source_credit_eligible"] is False
        assert decision["decision"] == "executable_curated_repair_canary"
    test, decision = _compile_one(
        {
            "lane": "source_action_shape",
            "row_id": "MCB_003_convolution_mono_right_of_nonneg",
            "residual_class": "source_action_mismatch",
        },
        static_filter="f.json",
    )
    assert test and test["repair_family"] == "convolution_argument_planner"
    assert decision["decision"] == "executable_curated_repair_canary"
    test, decision = _compile_one(
        {
            "lane": "ennreal_tsum",
            "row_id": "MCB_y_powerSeries",
            "residual_class": "source_action_mismatch",
            "sample_tail": "could not unify the conclusion of `@abel_aux` with a Tendsto over stolzSet",
        },
        static_filter="f.json",
    )
    assert test is None and decision["repair_family"] == "abel_stolz_power_series_planner"
    assert decision["decision"] == "exact_gap_candidate"
    test, decision = _compile_one(
        {
            "lane": "iff_direction",
            "row_id": "MCB_025_geom_mean_eq_arith_mean_weighted",
            "residual_class": "source_action_mismatch",
        },
        static_filter="f.json",
    )
    assert test is None and decision["repair_family"] == "iff_direction_planner"
    assert decision["decision"] == "exact_gap_candidate"
    print("leansearch_path_c_residual_compiler self-test PASS")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", action="append", required=False, default=[])
    ap.add_argument("--static-filter", required=False, default="")
    ap.add_argument("--out", default=DEFAULT_OUT)
    ap.add_argument("--decisions-out", default=DEFAULT_DECISIONS)
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return _self_test()
    if not args.root:
        raise SystemExit("--root is required")
    if not args.static_filter:
        raise SystemExit("--static-filter is required")
    obj = build(args)
    print(json.dumps({
        "out": args.out,
        "decisions_out": args.decisions_out,
        "test_count": obj["packet"]["test_count"],
        "by_decision": obj["decisions"]["by_decision"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
