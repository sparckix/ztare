# Quantitative Precision Masking

- Primitive ID: `float_masking_v1`
- Primitive Key: `float_masking`
- Type: `attack_pattern`
- Status: `approved`
- Epistemic Role: `attack_template`
- Confidence: `high`

## Summary
An adversarial tactic where a quantitative model or argument presents a false sense of numerical precision or robustness, obscuring sensitivity, underlying uncertainties, or computational limitations through hardcoded values, premature rounding, or unsubstantiated parameter choices.

## Mechanism
The Mutator introduces or maintains numerical artifacts (e.g., hardcoded constants, premature rounding, arbitrary parameter selections, unit inconsistencies, or non-differentiable operations) that obscure the true sensitivity, instability, or uncertainty of quantitative predictions. This makes the model appear more precise or robust than it is, often leading to false positives in self-falsification tests or hiding critical dependencies.

## Scope Conditions
- Quantitative models or arguments involving numerical calculations.
- Systems making claims of specific numerical prediction, solvency, or performance metrics.
- The presence of explicit numerical parameters, constants, or assertions (e.g., `assert value == X` or `round(value) == Y`).
- Reliance on floating-point arithmetic or fixed-precision representations.

## Non-Transfer Cases
- Purely qualitative or conceptual arguments without quantitative claims.
- Models where inherent uncertainty is explicitly and transparently modeled, and precision is not misrepresented.
- Situations where numerical values are only used for categorical classification or rough order-of-magnitude estimates where specific precision is irrelevant to the core claim.

## Required Transfer Test
Conduct a numerical audit of all central variables, intermediate calculations, and final assertions. Specifically, apply small perturbations to input parameters (sensitivity analysis), examine the impact of removing `round()` functions in assertions, and trace the empirical grounding of all constants. Verify against unit consistency and identify any non-differentiable operations used for numerical manipulation.

## Mutator Guidance
To implement, introduce hardcoded numerical constants that *just barely* satisfy critical assertions, ensuring they pass during initial testing but lack real robustness. Utilize `round()` or `int()` functions at intermediate steps or in final outputs to truncate precision and mask underlying numerical instability or sensitivity to input variations. Select extreme or optimistic values for key parameters without explicit empirical justification, presenting them as definitive points. Conflate approximate ranges with exact point estimates in model inputs.

## Firing Squad Attack
1. **Numerical Discrepancy Audit:** Compare stated numerical results in the thesis with actual computed results, looking for `round()` functions or other precision truncations in assertions. Demand higher precision if inconsistencies are found. 2. **Parametric Sensitivity Test:** Systematically perturb each 'central variable' by a small epsilon (e.g., 0.1% or smallest meaningful unit) and observe the impact on terminal predictions. High sensitivity indicates masked fragility. 3. **Hardcoded Constant Exposure:** Identify any hardcoded constants used in assertions or critical calculations. Replace them with dynamically calculated values or empirically grounded ranges and re-run tests. 4. **Unit and Dimensionality Check:** Verify that all numerical quantities maintain consistent units and dimensions throughout calculations. 5. **Non-Differentiability Probe:** Scan code for `round()`, `int()`, or other non-differentiable operations applied to continuous variables, especially in learning or credit assignment mechanisms, as these can mask gradient signals and true parameter influence.

## Judge Penalty Condition
The thesis or its provided computational proof fails its own unit tests due to numerical precision issues, hardcoded assertions, or unexpected sensitivity. The thesis's quantitative claims are shown to be non-robust under small, plausible input perturbations. Evidence of 'cooked books' (parameters reverse-engineered to meet a target output) or fundamental mathematical/dimensional insolvencies is presented. The masking of critical uncertainties or limitations through arbitrary precision or rounding is demonstrated to mislead on the model's actual reliability.

## Evidence Summary
Numerous incidents demonstrate models failing their own unit tests due to precision issues (floating-point errors, rounding), reliance on hardcoded values masking sensitivity, and unsubstantiated parameter choices. Projects in financial modeling, economic impact assessment, and epistemic calibration frequently exhibited these `float_masking` behaviors, leading to non-robust predictions and self-falsification. Many `weakest_point` descriptions highlight explicit `AssertionError` with numerical mismatches after rounding or due to fundamental inconsistencies.

## Source Projects
- ai_inference_collapse_gemini_gemini
- central_station
- epistemic_engine_v3_gemini_gemini
- hbr_strategy
- recursive_bayesian_gemini_claude
- recursive_bayesian_gemini_gemini
- simulation_god_gemini_gemini
- tsmc_fragility_gemini_gemini
- tsmc_fragility_gpt4o_gemini

## Source Incident IDs
- `ai_inference_collapse_gemini_gemini:debate_log:debate_log_iter_1774998675:float_masking`
- `ai_inference_collapse_gemini_gemini:debate_log:debate_log_iter_1774998858:float_masking`
- `ai_inference_collapse_gemini_gemini:debate_log:debate_log_iter_1774999509:float_masking`
- `ai_inference_collapse_gemini_gemini:debate_log:debate_log_iter_1774999905:float_masking`
- `ai_inference_collapse_gemini_gemini:debate_log:debate_log_iter_1775000073:float_masking`
- `ai_inference_collapse_gemini_gemini:debate_log:debate_log_iter_1775001134:float_masking`
- `ai_inference_collapse_gemini_gemini:debate_log:debate_log_iter_1775001330:float_masking`
- `ai_inference_collapse_gemini_gemini:debate_log:debate_log_iter_1775001524:float_masking`
- `ai_inference_collapse_gemini_gemini:debate_log:debate_log_iter_1775001718:float_masking`
- `ai_inference_collapse_gemini_gemini:debate_log:debate_log_iter_1775001865:float_masking`
- `ai_inference_collapse_gemini_gemini:debate_log:debate_log_iter_1775002037:float_masking`
- `ai_inference_collapse_gemini_gemini:debate_log:debate_log_iter_1775006716:float_masking`
- `ai_inference_collapse_gemini_gemini:debate_log:debate_log_iter_1775007114:float_masking`
- `ai_inference_collapse_gemini_gemini:debate_log:debate_log_iter_1775007317:float_masking`
- `ai_inference_collapse_gemini_gemini:debate_log:debate_log_iter_1775007894:float_masking`
- `ai_inference_collapse_gemini_gemini:debate_log:debate_log_iter_1775008263:float_masking`
- `ai_inference_collapse_gemini_gemini:debate_log:debate_log_iter_1775008448:float_masking`
- `ai_inference_collapse_gemini_gemini:debate_log:debate_log_iter_1775008629:float_masking`
- `ai_inference_collapse_gemini_gemini:debate_log:debate_log_iter_1775009116:float_masking`
- `ai_inference_collapse_gemini_gemini:debate_log:debate_log_iter_1775009314:float_masking`
- `ai_inference_collapse_gemini_gemini:debate_log:debate_log_iter_1775009497:float_masking`
- `ai_inference_collapse_gemini_gemini:debate_log:debate_log_iter_1775012548:float_masking`
- `ai_inference_collapse_gemini_gemini:history:v1_score_50:float_masking`
- `ai_inference_collapse_gemini_gemini:history:v7_score_100:float_masking`
- `ai_inference_collapse_gemini_gemini:history:v8_score_90:float_masking`
- `central_station:debate_log:debate_log_iter_1775255779:float_masking`
- `central_station:debate_log:debate_log_iter_1775259498:float_masking`
- `central_station:debate_log:debate_log_iter_1775259965:float_masking`
- `central_station:debate_log:debate_log_iter_1775260471:float_masking`
- `central_station:debate_log:debate_log_iter_1775262756:float_masking`
- `central_station:debate_log:debate_log_iter_1775264717:float_masking`
- `central_station:debate_log:debate_log_iter_1775265322:float_masking`
- `central_station:history:1775255475_iter3_score_70_central_station:float_masking`
- `central_station:history:1775263437_iter3_score_61_central_station:float_masking`
- `epistemic_engine_v3_gemini_gemini:debate_log:debate_log_iter_1775099859:float_masking`
- `epistemic_engine_v3_gemini_gemini:debate_log:debate_log_iter_1775100108:float_masking`
- `epistemic_engine_v3_gemini_gemini:debate_log:debate_log_iter_1775100789:float_masking`
- `epistemic_engine_v3_gemini_gemini:debate_log:debate_log_iter_1775102844:float_masking`
- `epistemic_engine_v3_gemini_gemini:debate_log:debate_log_iter_1775103226:float_masking`
- `epistemic_engine_v3_gemini_gemini:debate_log:debate_log_iter_1775103528:float_masking`
- `epistemic_engine_v3_gemini_gemini:debate_log:debate_log_iter_1775110924:float_masking`
- `epistemic_engine_v3_gemini_gemini:debate_log:debate_log_iter_1775133621:float_masking`
- `epistemic_engine_v3_gemini_gemini:debate_log:debate_log_iter_1775133908:float_masking`
- `epistemic_engine_v3_gemini_gemini:debate_log:debate_log_iter_1775134373:float_masking`
- `epistemic_engine_v3_gemini_gemini:debate_log:debate_log_iter_1775134730:float_masking`
- `epistemic_engine_v3_gemini_gemini:debate_log:debate_log_iter_1775135092:float_masking`
- `epistemic_engine_v3_gemini_gemini:debate_log:debate_log_iter_1775135389:float_masking`
- `epistemic_engine_v3_gemini_gemini:debate_log:debate_log_iter_1775135811:float_masking`
- `epistemic_engine_v3_gemini_gemini:debate_log:debate_log_iter_1775136177:float_masking`
- `epistemic_engine_v3_gemini_gemini:history:v4_score_46:float_masking`
- `epistemic_engine_v3_gemini_gemini:history:v7_score_110:float_masking`
- `hbr_strategy:debate_log:debate_log_iter_1775174156:float_masking`
- `hbr_strategy:history:1775174089_iter2_score_151_hbr_strategy:float_masking`
- `recursive_bayesian_gemini_claude:debate_log:debate_log_iter_1775255181:float_masking`
- `recursive_bayesian_gemini_gemini:debate_log:debate_log_iter_1775064570:float_masking`
- `recursive_bayesian_gemini_gemini:debate_log:debate_log_iter_1775080772:float_masking`
- `recursive_bayesian_gemini_gemini:debate_log:debate_log_iter_1775082134:float_masking`
- `recursive_bayesian_gemini_gemini:debate_log:debate_log_iter_1775082820:float_masking`
- `recursive_bayesian_gemini_gemini:debate_log:debate_log_iter_1775084050:float_masking`
- `recursive_bayesian_gemini_gemini:debate_log:debate_log_iter_1775084558:float_masking`
- `recursive_bayesian_gemini_gemini:debate_log:debate_log_iter_1775085228:float_masking`
- `recursive_bayesian_gemini_gemini:debate_log:debate_log_iter_1775087617:float_masking`
- `recursive_bayesian_gemini_gemini:debate_log:debate_log_iter_1775087861:float_masking`
- `recursive_bayesian_gemini_gemini:debate_log:debate_log_iter_1775088116:float_masking`
- `recursive_bayesian_gemini_gemini:debate_log:debate_log_iter_1775088271:float_masking`
- `recursive_bayesian_gemini_gemini:debate_log:debate_log_iter_1775088449:float_masking`
- `recursive_bayesian_gemini_gemini:debate_log:debate_log_iter_1775088597:float_masking`
- `recursive_bayesian_gemini_gemini:debate_log:debate_log_iter_1775088830:float_masking`
- `recursive_bayesian_gemini_gemini:debate_log:debate_log_iter_1775089039:float_masking`
- `recursive_bayesian_gemini_gemini:debate_log:debate_log_iter_1775089223:float_masking`
- `recursive_bayesian_gemini_gemini:debate_log:debate_log_iter_1775089422:float_masking`
- `recursive_bayesian_gemini_gemini:debate_log:debate_log_iter_1775089584:float_masking`
- `recursive_bayesian_gemini_gemini:debate_log:debate_log_iter_1775089754:float_masking`
- `recursive_bayesian_gemini_gemini:debate_log:debate_log_iter_1775089951:float_masking`
- `recursive_bayesian_gemini_gemini:debate_log:debate_log_iter_1775090167:float_masking`
- `recursive_bayesian_gemini_gemini:debate_log:debate_log_iter_1775090352:float_masking`
- `recursive_bayesian_gemini_gemini:debate_log:debate_log_iter_1775090520:float_masking`
- `recursive_bayesian_gemini_gemini:test_model:test_model:float_masking`
- `simulation_god_gemini_gemini:debate_log:debate_log_iter_1774843012:float_masking`
- `simulation_god_gemini_gemini:debate_log:debate_log_iter_1774890617:float_masking`
- `simulation_god_gemini_gemini:debate_log:debate_log_iter_1774928488:float_masking`
- `simulation_god_gemini_gemini:debate_log:debate_log_iter_1774931361:float_masking`
- `simulation_god_gemini_gemini:history:v1_score_50:float_masking`
- `simulation_god_gemini_gemini:history:v1_score_70:float_masking`
- `simulation_god_gemini_gemini:history:v8_score_70:float_masking`
- `simulation_god_gemini_gemini:history:v9_score_55:float_masking`
- `simulation_god_gemini_gemini:test_model:test_model:float_masking`
- `tsmc_fragility_gemini_gemini:debate_log:debate_log_iter_1775046906:float_masking`
- `tsmc_fragility_gemini_gemini:debate_log:debate_log_iter_1775047150:float_masking`
- `tsmc_fragility_gemini_gemini:debate_log:debate_log_iter_1775047626:float_masking`
- `tsmc_fragility_gemini_gemini:debate_log:debate_log_iter_1775047809:float_masking`
- `tsmc_fragility_gemini_gemini:debate_log:debate_log_iter_1775047961:float_masking`
- `tsmc_fragility_gemini_gemini:debate_log:debate_log_iter_1775048142:float_masking`
- `tsmc_fragility_gemini_gemini:debate_log:debate_log_iter_1775048354:float_masking`
- `tsmc_fragility_gemini_gemini:debate_log:debate_log_iter_1775048486:float_masking`
- `tsmc_fragility_gemini_gemini:debate_log:debate_log_iter_1775048656:float_masking`
- `tsmc_fragility_gemini_gemini:debate_log:debate_log_iter_1775048879:float_masking`
- `tsmc_fragility_gemini_gemini:debate_log:debate_log_iter_1775049065:float_masking`
- `tsmc_fragility_gemini_gemini:debate_log:debate_log_iter_1775049249:float_masking`
- `tsmc_fragility_gemini_gemini:debate_log:debate_log_iter_1775049446:float_masking`
- `tsmc_fragility_gemini_gemini:debate_log:debate_log_iter_1775049640:float_masking`
- `tsmc_fragility_gemini_gemini:debate_log:debate_log_iter_1775096331:float_masking`
- `tsmc_fragility_gemini_gemini:debate_log:debate_log_iter_1775097100:float_masking`
- `tsmc_fragility_gemini_gemini:debate_log:debate_log_iter_1775097317:float_masking`
- `tsmc_fragility_gemini_gemini:debate_log:debate_log_iter_1775097549:float_masking`
- `tsmc_fragility_gemini_gemini:debate_log:debate_log_iter_1775097727:float_masking`
- `tsmc_fragility_gemini_gemini:history:v11_score_75:float_masking`
- `tsmc_fragility_gemini_gemini:history:v8_score_60:float_masking`
- `tsmc_fragility_gpt4o_gemini:debate_log:debate_log_iter_1775336670:float_masking`

## Tags
- `numerical_stability`
- `precision`
- `rounding`
- `hardcoding`
- `sensitivity_analysis`
- `mathematical_insolvency`
- `cooked_books`
- `falsification_failure`
- `unit_tests`

## Promotion Note
This primitive is well-supported by a large number of incidents across diverse projects. The mechanism is clear, the scope conditions are distinct, and concrete tests are identified. It is ready for human approval.
