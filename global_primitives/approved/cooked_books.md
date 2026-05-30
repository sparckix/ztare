# Parametric Rigging and Biased Grounding

- Primitive ID: `cooked_books_v1`
- Primitive Key: `cooked_books`
- Type: `attack_pattern`
- Status: `approved`
- Epistemic Role: `attack_template`
- Confidence: `high`

## Summary
This primitive captures the recurring pattern where quantitative models, simulations, or tests contain deliberately or inadvertently manipulated parameters, constants, or data inputs to systematically bias outcomes, obscure flaws, or ensure a predetermined result, rather than objectively reflecting reality.

## Mechanism
Manipulation or misapplication of quantitative model parameters, constants, or input data to systematically bias outcomes, obscure flaws, or ensure a predetermined result. This mechanism manifests as: 1) Hardcoding favorable constants or assumptions. 2) Circular derivation of parameters from desired output targets. 3) Arbitrary, ungrounded, or dimensionally inconsistent values. 4) Inconsistencies between stated intent (narrative) and implementation (code). 5) Omitting critical components or failing to test problematic parts of a system.

## Scope Conditions
- The system or analysis relies on quantitative models, simulations, or computations with explicit numerical parameters, constants, or defined data inputs.
- A 'truth' or 'grounding' for these quantitative values is claimed, implied, or expected (e.g., in financial models, scientific simulations, probability engines, economic impact assessments).
- There is an observable or predicted outcome that is highly sensitive to specific input parameters.

## Non-Transfer Cases
- The system or analysis is purely qualitative with no numerical models or parameters.
- The identified numerical values are explicitly stated as aggressive, ungrounded, or hypothetical assumptions for exploratory purposes, without any claim of factual representation or objective derivation.
- The identified discrepancy is a minor, unintentional typo that does not materially affect the outcome or intent.

## Required Transfer Test
Systematic audit of all 'central variables' (parameters, constants, initial conditions) against external verifiable sources, internal consistency checks (narrative vs. code, unit dimensionality), and sensitivity analysis. Examine all assertions for tautology or favorable bounding. Trace derivation paths for critical parameters to detect circular reasoning (e.g., value chosen to achieve target output). Introduce adversarial perturbations to parameters within plausible ranges to observe outcome robustness.

## Mutator Guidance
To make a thesis or model appear successful or to hide its vulnerabilities, introduce hardcoded constants that force desired outcomes. Use circular reasoning to derive key parameters from the target results. Ensure inconsistencies between narrative claims and underlying code implementation, especially in areas where direct falsification is expected. Employ simplifying assumptions or limited input ranges to mask non-linear behaviors or real-world complexities.

## Firing Squad Attack
The Firing Squad will systematically audit all central variables and constants in the Mutator's model/code. They will: 1) Cross-reference all numerical inputs against external data or established scientific/financial principles. 2) Check for logical consistency between the narrative explanation and the actual code implementation (e.g., stated formula vs. Python calculation). 3) Identify parameters that are reverse-engineered from desired outputs. 4) Run sensitivity analyses by perturbing key parameters within plausible ranges to expose fragility or artificial tuning. 5) Analyze unit tests for tautological assertions or overly narrow validation ranges.

## Judge Penalty Condition
If evidence demonstrates that the Mutator's model/code contains ungrounded, inconsistent, or deliberately manipulated parameters or data that lead to systematically biased outcomes or obscure fundamental flaws, the Mutator's thesis will receive a severe penalty for lack of quantitative rigor and potential misrepresentation. The severity will increase if the manipulation is deemed intentional or pervasive.

## Evidence Summary
Incidents consistently demonstrate 'cooked books' as a high-severity epistemic failure across all analyzed projects. The pattern frequently involves parametric inconsistencies between narrative and code, hardcoded constants that bias outcomes, circular derivation of parameters, or mathematical/dimensional insolvency in quantitative proofs. This primitive is well-supported by numerous examples of both intentional and unintentional rigging designed to achieve favorable results or mask underlying flaws.

## Source Projects
- ai_inference_collapse_gemini_gemini
- central_station
- epistemic_engine_v3_gemini_gemini
- recursive_bayesian_gemini_gemini
- simulation_god_gemini_gemini
- tsmc_fragility_gemini_gemini

## Source Incident IDs
- `ai_inference_collapse_gemini_gemini:debate_log:debate_log_iter_1774998442:cooked_books`
- `ai_inference_collapse_gemini_gemini:debate_log:debate_log_iter_1774998675:cooked_books`
- `ai_inference_collapse_gemini_gemini:debate_log:debate_log_iter_1774998858:cooked_books`
- `ai_inference_collapse_gemini_gemini:debate_log:debate_log_iter_1774999069:cooked_books`
- `ai_inference_collapse_gemini_gemini:debate_log:debate_log_iter_1774999280:cooked_books`
- `ai_inference_collapse_gemini_gemini:debate_log:debate_log_iter_1774999509:cooked_books`
- `ai_inference_collapse_gemini_gemini:debate_log:debate_log_iter_1774999725:cooked_books`
- `ai_inference_collapse_gemini_gemini:debate_log:debate_log_iter_1774999905:cooked_books`
- `ai_inference_collapse_gemini_gemini:debate_log:debate_log_iter_1775000073:cooked_books`
- `ai_inference_collapse_gemini_gemini:debate_log:debate_log_iter_1775000239:cooked_books`
- `ai_inference_collapse_gemini_gemini:debate_log:debate_log_iter_1775000466:cooked_books`
- `ai_inference_collapse_gemini_gemini:debate_log:debate_log_iter_1775000739:cooked_books`
- `ai_inference_collapse_gemini_gemini:debate_log:debate_log_iter_1775000923:cooked_books`
- `ai_inference_collapse_gemini_gemini:debate_log:debate_log_iter_1775001134:cooked_books`
- `ai_inference_collapse_gemini_gemini:debate_log:debate_log_iter_1775001330:cooked_books`
- `ai_inference_collapse_gemini_gemini:debate_log:debate_log_iter_1775001524:cooked_books`
- `ai_inference_collapse_gemini_gemini:debate_log:debate_log_iter_1775001718:cooked_books`
- `ai_inference_collapse_gemini_gemini:debate_log:debate_log_iter_1775001865:cooked_books`
- `ai_inference_collapse_gemini_gemini:debate_log:debate_log_iter_1775002037:cooked_books`
- `ai_inference_collapse_gemini_gemini:debate_log:debate_log_iter_1775006716:cooked_books`
- `ai_inference_collapse_gemini_gemini:debate_log:debate_log_iter_1775006907:cooked_books`
- `ai_inference_collapse_gemini_gemini:debate_log:debate_log_iter_1775007114:cooked_books`
- `ai_inference_collapse_gemini_gemini:debate_log:debate_log_iter_1775007317:cooked_books`
- `ai_inference_collapse_gemini_gemini:debate_log:debate_log_iter_1775007590:cooked_books`
- `ai_inference_collapse_gemini_gemini:debate_log:debate_log_iter_1775007894:cooked_books`
- `ai_inference_collapse_gemini_gemini:debate_log:debate_log_iter_1775008121:cooked_books`
- `ai_inference_collapse_gemini_gemini:debate_log:debate_log_iter_1775008263:cooked_books`
- `ai_inference_collapse_gemini_gemini:debate_log:debate_log_iter_1775008448:cooked_books`
- `ai_inference_collapse_gemini_gemini:debate_log:debate_log_iter_1775008629:cooked_books`
- `ai_inference_collapse_gemini_gemini:debate_log:debate_log_iter_1775008955:cooked_books`
- `ai_inference_collapse_gemini_gemini:debate_log:debate_log_iter_1775009116:cooked_books`
- `ai_inference_collapse_gemini_gemini:debate_log:debate_log_iter_1775009314:cooked_books`
- `ai_inference_collapse_gemini_gemini:debate_log:debate_log_iter_1775009497:cooked_books`
- `central_station:debate_log:debate_log_iter_1775259498:cooked_books`
- `central_station:debate_log:debate_log_iter_1775259965:cooked_books`
- `central_station:debate_log:debate_log_iter_1775260471:cooked_books`
- `epistemic_engine_v3_gemini_gemini:debate_log:debate_log_iter_1775099293:cooked_books`
- `epistemic_engine_v3_gemini_gemini:debate_log:debate_log_iter_1775099455:cooked_books`
- `epistemic_engine_v3_gemini_gemini:debate_log:debate_log_iter_1775099644:cooked_books`
- `epistemic_engine_v3_gemini_gemini:debate_log:debate_log_iter_1775099859:cooked_books`
- `epistemic_engine_v3_gemini_gemini:debate_log:debate_log_iter_1775100108:cooked_books`
- `epistemic_engine_v3_gemini_gemini:debate_log:debate_log_iter_1775100329:cooked_books`
- `epistemic_engine_v3_gemini_gemini:debate_log:debate_log_iter_1775100566:cooked_books`
- `epistemic_engine_v3_gemini_gemini:debate_log:debate_log_iter_1775100789:cooked_books`
- `epistemic_engine_v3_gemini_gemini:debate_log:debate_log_iter_1775101023:cooked_books`
- `epistemic_engine_v3_gemini_gemini:debate_log:debate_log_iter_1775102844:cooked_books`
- `epistemic_engine_v3_gemini_gemini:debate_log:debate_log_iter_1775103085:cooked_books`
- `epistemic_engine_v3_gemini_gemini:debate_log:debate_log_iter_1775103226:cooked_books`
- `epistemic_engine_v3_gemini_gemini:debate_log:debate_log_iter_1775103528:cooked_books`
- `epistemic_engine_v3_gemini_gemini:debate_log:debate_log_iter_1775110924:cooked_books`
- `epistemic_engine_v3_gemini_gemini:debate_log:debate_log_iter_1775133621:cooked_books`
- `epistemic_engine_v3_gemini_gemini:debate_log:debate_log_iter_1775133908:cooked_books`
- `epistemic_engine_v3_gemini_gemini:debate_log:debate_log_iter_1775134373:cooked_books`
- `epistemic_engine_v3_gemini_gemini:debate_log:debate_log_iter_1775134730:cooked_books`
- `epistemic_engine_v3_gemini_gemini:debate_log:debate_log_iter_1775135092:cooked_books`
- `epistemic_engine_v3_gemini_gemini:debate_log:debate_log_iter_1775135389:cooked_books`
- `epistemic_engine_v3_gemini_gemini:debate_log:debate_log_iter_1775135811:cooked_books`
- `epistemic_engine_v3_gemini_gemini:debate_log:debate_log_iter_1775136177:cooked_books`
- `epistemic_engine_v3_gemini_gemini:history:v4_score_46:cooked_books`
- `recursive_bayesian_gemini_gemini:debate_log:debate_log_iter_1775064375:cooked_books`
- `recursive_bayesian_gemini_gemini:debate_log:debate_log_iter_1775064570:cooked_books`
- `recursive_bayesian_gemini_gemini:debate_log:debate_log_iter_1775064840:cooked_books`
- `recursive_bayesian_gemini_gemini:debate_log:debate_log_iter_1775065067:cooked_books`
- `recursive_bayesian_gemini_gemini:debate_log:debate_log_iter_1775080772:cooked_books`
- `recursive_bayesian_gemini_gemini:debate_log:debate_log_iter_1775081304:cooked_books`
- `recursive_bayesian_gemini_gemini:debate_log:debate_log_iter_1775081591:cooked_books`
- `recursive_bayesian_gemini_gemini:debate_log:debate_log_iter_1775081836:cooked_books`
- `recursive_bayesian_gemini_gemini:debate_log:debate_log_iter_1775082134:cooked_books`
- `recursive_bayesian_gemini_gemini:debate_log:debate_log_iter_1775082480:cooked_books`
- `recursive_bayesian_gemini_gemini:debate_log:debate_log_iter_1775082820:cooked_books`
- `recursive_bayesian_gemini_gemini:debate_log:debate_log_iter_1775083184:cooked_books`
- `recursive_bayesian_gemini_gemini:debate_log:debate_log_iter_1775083558:cooked_books`
- `recursive_bayesian_gemini_gemini:debate_log:debate_log_iter_1775083843:cooked_books`
- `recursive_bayesian_gemini_gemini:debate_log:debate_log_iter_1775084050:cooked_books`
- `recursive_bayesian_gemini_gemini:debate_log:debate_log_iter_1775084280:cooked_books`
- `recursive_bayesian_gemini_gemini:debate_log:debate_log_iter_1775084558:cooked_books`
- `recursive_bayesian_gemini_gemini:debate_log:debate_log_iter_1775084825:cooked_books`
- `recursive_bayesian_gemini_gemini:debate_log:debate_log_iter_1775085026:cooked_books`
- `recursive_bayesian_gemini_gemini:debate_log:debate_log_iter_1775085228:cooked_books`
- `recursive_bayesian_gemini_gemini:debate_log:debate_log_iter_1775087617:cooked_books`
- `recursive_bayesian_gemini_gemini:debate_log:debate_log_iter_1775087861:cooked_books`
- `recursive_bayesian_gemini_gemini:debate_log:debate_log_iter_1775088116:cooked_books`
- `recursive_bayesian_gemini_gemini:debate_log:debate_log_iter_1775088271:cooked_books`
- `recursive_bayesian_gemini_gemini:debate_log:debate_log_iter_1775088449:cooked_books`
- `recursive_bayesian_gemini_gemini:debate_log:debate_log_iter_1775088597:cooked_books`
- `recursive_bayesian_gemini_gemini:debate_log:debate_log_iter_1775088830:cooked_books`
- `recursive_bayesian_gemini_gemini:debate_log:debate_log_iter_1775089039:cooked_books`
- `recursive_bayesian_gemini_gemini:debate_log:debate_log_iter_1775089223:cooked_books`
- `recursive_bayesian_gemini_gemini:debate_log:debate_log_iter_1775089422:cooked_books`
- `recursive_bayesian_gemini_gemini:debate_log:debate_log_iter_1775089584:cooked_books`
- `recursive_bayesian_gemini_gemini:debate_log:debate_log_iter_1775089754:cooked_books`
- `recursive_bayesian_gemini_gemini:debate_log:debate_log_iter_1775089951:cooked_books`
- `recursive_bayesian_gemini_gemini:debate_log:debate_log_iter_1775090167:cooked_books`
- `recursive_bayesian_gemini_gemini:debate_log:debate_log_iter_1775090352:cooked_books`
- `recursive_bayesian_gemini_gemini:debate_log:debate_log_iter_1775090520:cooked_books`
- `recursive_bayesian_gemini_gemini:history:v2_score_20:cooked_books`
- `simulation_god_gemini_gemini:debate_log:debate_log_iter_1774842558:cooked_books`
- `simulation_god_gemini_gemini:debate_log:debate_log_iter_1774843012:cooked_books`
- `simulation_god_gemini_gemini:debate_log:debate_log_iter_1774871799:cooked_books`
- `simulation_god_gemini_gemini:debate_log:debate_log_iter_1774875372:cooked_books`
- `simulation_god_gemini_gemini:debate_log:debate_log_iter_1774928488:cooked_books`
- `simulation_god_gemini_gemini:debate_log:debate_log_iter_1774929222:cooked_books`
- `simulation_god_gemini_gemini:debate_log:debate_log_iter_1774930584:cooked_books`
- `tsmc_fragility_gemini_gemini:debate_log:debate_log_iter_1775046590:cooked_books`
- `tsmc_fragility_gemini_gemini:debate_log:debate_log_iter_1775046906:cooked_books`
- `tsmc_fragility_gemini_gemini:debate_log:debate_log_iter_1775047150:cooked_books`
- `tsmc_fragility_gemini_gemini:debate_log:debate_log_iter_1775047352:cooked_books`
- `tsmc_fragility_gemini_gemini:debate_log:debate_log_iter_1775047626:cooked_books`
- `tsmc_fragility_gemini_gemini:debate_log:debate_log_iter_1775047809:cooked_books`
- `tsmc_fragility_gemini_gemini:debate_log:debate_log_iter_1775047961:cooked_books`
- `tsmc_fragility_gemini_gemini:debate_log:debate_log_iter_1775048142:cooked_books`
- `tsmc_fragility_gemini_gemini:debate_log:debate_log_iter_1775048354:cooked_books`
- `tsmc_fragility_gemini_gemini:debate_log:debate_log_iter_1775048486:cooked_books`
- `tsmc_fragility_gemini_gemini:debate_log:debate_log_iter_1775048656:cooked_books`
- `tsmc_fragility_gemini_gemini:debate_log:debate_log_iter_1775048879:cooked_books`
- `tsmc_fragility_gemini_gemini:debate_log:debate_log_iter_1775049065:cooked_books`
- `tsmc_fragility_gemini_gemini:debate_log:debate_log_iter_1775049249:cooked_books`
- `tsmc_fragility_gemini_gemini:debate_log:debate_log_iter_1775049446:cooked_books`
- `tsmc_fragility_gemini_gemini:debate_log:debate_log_iter_1775049640:cooked_books`
- `tsmc_fragility_gemini_gemini:debate_log:debate_log_iter_1775096331:cooked_books`
- `tsmc_fragility_gemini_gemini:debate_log:debate_log_iter_1775096587:cooked_books`
- `tsmc_fragility_gemini_gemini:debate_log:debate_log_iter_1775097100:cooked_books`
- `tsmc_fragility_gemini_gemini:debate_log:debate_log_iter_1775097317:cooked_books`
- `tsmc_fragility_gemini_gemini:debate_log:debate_log_iter_1775097549:cooked_books`
- `tsmc_fragility_gemini_gemini:debate_log:debate_log_iter_1775097727:cooked_books`

## Tags
- `Quantitative Rigor`
- `Model Validation`
- `Parameter Sensitivity`
- `Bias`
- `Deception`
- `Auditing`
- `Numerical Consistency`
- `Epistemic Rigor`

## Promotion Note
This primitive is strongly supported by a high volume of incidents across diverse projects. The mechanism is clear, consistent, and highly operationalizable as an attack pattern and test template. It is ready for human approval.
