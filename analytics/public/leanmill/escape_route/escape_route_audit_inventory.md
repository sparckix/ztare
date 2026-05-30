# Escape Route Audit Inventory

- rows: `5`
- raw closures: `0`
- natural control: `v32_route_c_replay_results.json (0/10 closed)`
- credit_boundary: `advisory_only_no_factory_credit; closures require the existing governance and matched-negative-control receipt path before credit-ready status`

## Missing Lemma Hints

| row | verdict | typed exit | missing lemma hints | next lever |
|---|---|---|---|---|
| ER_SIE1_intervalIntegral_pow_exp | OPEN_GAP_REPORT | gap_report | integral_exp_neg_mul_induction, integral_exp_neg_mul_by_parts, integral_exp_neg_mul_by_parts | prove_missing_lemma |
| ER_SIE2_sum_Ico_pow_exp | OPEN_GAP_REPORT | gap_report | sum_ico_pow_exp_induction, sum_ico_pow_exp_induction, sum_ico_pow_exp_induction | prove_missing_lemma |
| ER_SIE3_sum_Iic_pow_exp | OPEN_GAP_REPORT | gap_report | sum_pow_exp_induction_upper_bound, sum_pow_exp_induction_upper_bound, sum_pow_exp_induction_upper_bound | prove_missing_lemma |
| ER_SIE4_sum_Iic_pow_twopow | OPEN_GAP_REPORT | gap_report | sum_pow_mul_exp_negc_induction_bound, sum_pow_mul_exp_negc_induction_bound, sum_pow_mul_exp_negc_induction_bound | prove_missing_lemma |
| ER_PENT_strictMonoOn | OPEN_GAP_REPORT | gap_report | int_normalization_exists, int_normalization_exists, int_normalization_exists | prove_missing_lemma |
