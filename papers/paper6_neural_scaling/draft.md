# The Illusion of the Bottleneck: Architectural Invariance and Learned Coordination in Deep Residual Networks

**Daniel Alami**
Independent Researcher; MBA Candidate, Harvard Business School

*April 2026*

---

## Abstract

Recent work on transformer internal representations reports extreme low-rank "bottlenecks" in middle layers, suggesting that deep sequential computation is highly compressible. We demonstrate that this finding relies on a measurement artifact: mean-pooling over sequence positions allows the beginning-of-sequence token (whose activation norm is 35x that of regular tokens in Pythia-410M) to collapse the apparent effective rank from ~105 to 1.8.

By isolating per-token residual updates across Pythia, GPT-2, and OPT architectures, we reveal a different mechanism. Each layer applies a high-dimensional perturbation (effective rank 105-192) in a subspace nearly orthogonal to adjacent layers (cosine similarity 0.05-0.19). We introduce the Cancellation Ratio, showing that 72% of perturbation energy is lost to geometric cancellation across the bottleneck. Untrained null models exhibit 70.2% cancellation, proving this is an architectural invariant of residual streams, not a learned inefficiency.

Training does not teach layers to align. It teaches them to coordinate: residual rank increases 5x (41 to 192) and token-level magnitude correlation rises from r=0.3 to r=0.9. The layers perfectly agree on which tokens need work but operate in orthogonal subspaces to provide diverse corrections. We replicate the orthogonality finding on Mamba-370M (a state-space model), demonstrating that cross-layer orthogonality is universal to deep residual architectures.

---

## 1. The Measurement Crisis

### 1.1 The BOS Contamination Artifact

Effective rank, computed via the spectral entropy of singular values, is a standard measure of representational dimensionality in neural network analysis. Applied to transformer hidden states, it has been used to argue that middle layers operate in a narrow "bottleneck."

We replicate this finding on Pythia-410M (24 layers, 1024 hidden dimensions): mean-pooled effective rank collapses from 4.6 at the embedding layer to 1.8 at layers 6-17, recovering to 4.6 at the output. The profile is visually striking and was initially interpreted as evidence that 12 of 24 layers operate in a near one-dimensional subspace.

The measurement is correct. The interpretation is wrong.

The mean-pooled activation vector at each layer averages across all sequence positions, including position 0 (the BOS token). We measure the per-position activation norm at the bottleneck midpoint (layer 12):

| Position | Norm | Ratio to typical |
|----------|------|-----------------|
| 0 (BOS) | 741.4 | 35.4x |
| 1 | 22.1 | 1.0x |
| 2 | 20.6 | 0.9x |
| 3 | 20.5 | 0.9x |

The BOS token's norm is 35x that of every other position. In a sequence of 13 tokens, it contributes 74.6% of the mean vector's total norm. The "effective rank of the layer" is predominantly measuring "how the BOS token varies across prompts" -- a 1-2 dimensional quantity by construction.

OPT-350M (Meta), which does not exhibit this BOS anomaly (BOS norm ratio 1.1x), shows no bottleneck at all: its rank profile is flat at 6-8 across all 24 layers.

Per-token effective rank at Pythia-410M's bottleneck layers, with BOS excluded, is 103-106. The representation is high-dimensional, not a tightrope.

### 1.2 Corrected Measurements

We propose the following methodological correction for any study measuring effective rank of transformer hidden states:

1. Compute per-position activation norms. Flag any position with norm > 3x the median.
2. Exclude flagged positions from aggregation.
3. Report both mean-pooled and per-token effective ranks.

Applying this correction to Pythia-410M eliminates the sandglass bottleneck entirely.

---

## 2. Decomposing the Residual Stream

### 2.1 Carrier and Perturbation

For layer $l$, let $h_l \in \mathbb{R}^d$ be the input representation. The layer computes:

$$\Delta h_l = \text{Attn}_l(h_l) + \text{MLP}_l(h_l)$$

The output is $h_{l+1} = h_l + \Delta h_l$. We call $h_l$ the carrier and $\Delta h_l$ the perturbation.

The carrier is what the skip connection preserves. The perturbation is what the attention and MLP blocks actually compute. Prior rank analyses measured the carrier (total activation); we measure the perturbation (the layer's contribution).

### 2.2 Perturbation Properties

Across 1200 tokens (100 prompts, BOS excluded) at each bottleneck layer pair (6-7 through 16-17):

| Property | Value | Interpretation |
|----------|-------|----------------|
| Perturbation effective rank | 190-201 | High-dimensional computation |
| Perturbation magnitude (\|delta\|/\|input\|) | 0.42-0.51 | Each layer adds 42-51% of input norm |
| Overlap with input SVD basis | 0.6-5.3% | Perturbation lives in an orthogonal subspace |

The perturbation rank (192) is far higher than the carrier's apparent rank (1.8 mean-pooled, 105 per-token). Each layer is computing something genuinely high-dimensional in a subspace nearly orthogonal to the input's dominant variance.

### 2.3 Cross-Layer Orthogonality

The cosine similarity between the top-10 singular vectors of adjacent layers' perturbations:

$$\text{Sim}(l, l+1) = \text{mean}_{i} \max_{j} \left| \mathbf{v}^{(l)}_i \cdot \mathbf{v}^{(l+1)}_j \right|$$

| Layer pair | Cosine similarity | Magnitude correlation | Verdict |
|-----------|-------------------|----------------------|---------|
| L6-L7 | 0.209 | r=0.866 | Orthogonal subspaces, correlated magnitudes |
| L9-L10 | 0.000 | r=0.844 | Perfectly orthogonal |
| L12-L13 | 0.010 | r=0.777 | Perfectly orthogonal |
| L15-L16 | 0.089 | r=0.092 | Phase boundary |

Adjacent layers compute perturbations in orthogonal subspaces (cosine 0.00-0.21), but apply them to the same tokens (magnitude correlation r=0.78-0.93). We term this "Parallel Firefighting": the layers agree on which tokens need correction but disagree on the direction.

The L15-L16 boundary shows a sharp decorrelation (magnitude correlation drops from r=0.66 to r=0.09), marking the transition from bottleneck to output processing.

---

## 3. The Cancellation Invariant

### 3.1 Definition

For a block of layers from $a$ to $b$, the Cancellation Ratio measures how much perturbation energy survives summation:

$$CR = 1 - \frac{\left\|\sum_{l=a}^{b} \Delta h_l\right\|}{\sum_{l=a}^{b} \|\Delta h_l\|}$$

When $CR = 0$, all perturbations are aligned (perfect constructive interference). When $CR = 1$, they cancel completely.

### 3.2 The Null Model Test

If the 72% cancellation observed in trained Pythia-410M is a learned property, an untrained model (random initialization) should show a different cancellation rate. If it is architectural, the rates should match.

| Metric | Untrained | Trained | Delta |
|--------|-----------|---------|-------|
| Cancellation ratio | **70.2%** | **72.2%** | 2.0 pp |
| Residual effective rank | 41 | 192 | +371% |
| Magnitude correlation | r=0.13-0.47 | r=0.78-0.93 | +0.46 |
| BOS norm ratio | 1.1x | 35x | Training creates anomaly |

The cancellation ratio is unchanged by training (70.2% vs 72.2%, a 2 percentage point difference within noise). The ~70% cancellation is a geometric consequence of summing high-dimensional orthogonal vectors in a residual stream. It is not learnable and is not a target of gradient descent.

What training does change: residual rank (41 to 192, a 5x increase in computational diversity), magnitude correlation (0.3 to 0.9, perfect token-level coordination), and the BOS anomaly (1.1x to 35x, cross-prompt variance concentration).

### 3.3 Training Teaches WHAT and WHERE, Not HOW EFFICIENTLY

Three laws emerge from the null model comparison:

**Law 1: The Cancellation Floor.** Deep residual networks pay a fixed ~70% geometric tax on perturbation energy. This is the cost of depth in a residual architecture.

**Law 2: Learned Diversity.** Training increases the effective rank of each layer's perturbation from 41 to 192 (5x). The network learns to compute more diverse corrections, not more aligned ones.

**Law 3: Learned Coordination.** Training increases token-level magnitude correlation from r=0.3 to r=0.9. The network learns which tokens need the most correction and coordinates across layers to apply it, despite the corrections being orthogonal.

---

## 4. Cross-Architecture Comparison

### 4.1 Three Model Families

We replicate the diagnostic suite on GPT-2-medium (355M, 24 layers, OpenAI) and OPT-350M (350M, 24 layers, Meta):

| Metric | Pythia-410M | GPT-2-medium | OPT-350M |
|--------|-------------|--------------|----------|
| Cross-layer cosine | 0.10-0.19 | 0.11-0.26 | 0.12-0.32 |
| Orthogonality verdict | All ORTH | PART→ORTH | PART→ORTH |

Cross-layer orthogonality replicates across all three transformer families.

### 4.2 Mamba (State-Space Model)

Mamba-370M (48 layers, 1024 hidden, state-space architecture with no attention mechanism):

| Metric | Pythia-410M (Transformer) | Mamba-370M (SSM) |
|--------|--------------------------|------------------|
| Residual rank | 192 | 99 |
| Cross-layer cosine | 0.10-0.19 | 0.05-0.15 |
| Cancellation | 72% | 62% |
| \|delta\|/\|input\| | 0.45-0.51 | 0.22-0.41 |

Mamba also exhibits orthogonal cross-layer perturbations -- more orthogonal than transformers (cosine 0.05-0.15). The cancellation ratio is lower (62% vs 72%).

A null model comparison on Mamba reveals why. Untrained Mamba shows 76.0% cancellation -- HIGHER than untrained Pythia (70.2%). But trained Mamba drops to 62.0%, a 14 percentage point reduction. In contrast, trained Pythia remains at 72.2% (unchanged from its untrained 70.2%).

| Model | Untrained | Trained | Training Effect |
|-------|-----------|---------|-----------------|
| Pythia-410M | 70.2% | 72.2% | +2pp (invariant) |
| Mamba-370M | 76.0% | 62.0% | -14pp (learned alignment) |

Training REDUCES cancellation in Mamba but not in Pythia. The SSM's selective state-space mechanism learns to align its perturbations during training; the transformer's attention mechanism does not. This is the most architecturally informative finding in the cross-architecture comparison: the two architectures differ not in their untrained geometry (both ~70-76% cancellation) but in whether training can improve that geometry. The SSM's inductive bias permits learned perturbation alignment. Attention's does not.

---

## 5. The U-Shaped Ablation Curve

### 5.1 Layer-by-Layer Importance

To test whether the orthogonal perturbations are functionally load-bearing despite the 72% cancellation, we ablate each layer individually (skip the layer's computation, passing the input directly to the next layer) and measure next-token cross-entropy loss:

| Phase | Layers | Loss increase | Interpretation |
|-------|--------|--------------|----------------|
| Embedding | 0-1 | +137-218% | Parsing: irreplaceable |
| Early bottleneck | 6-8 | +10-16% | Active computation |
| Mid bottleneck | 9-12, 14-15 | +1.5-4.5% | Minimum useful work |
| Late bottleneck | 13, 16-17 | +7-14% | Output preparation |
| Output | 22 | +23% | Projection: irreplaceable |

Every layer contributes measurably. No layer has zero impact. The surviving 28% of perturbation energy (after 72% cancellation) carries 1.5-16% of the loss per layer.

### 5.2 Interpretation

The ablation profile is U-shaped: critical at the edges of the network, minimal in the belly (layers 14-15: 1.5%), with moderate contributions elsewhere. This is consistent with the carrier-perturbation decomposition: early layers build the carrier (high impact), middle layers refine it (low impact per layer but cumulative), and late layers project to the output vocabulary (high impact).

The U-shape constrains any successor architecture: compute must be concentrated at the edges and can be thinned in the middle, but cannot be eliminated.

---

## 6. Compressible Observables

### 6.1 Residual Magnitude Decay (Within-Model)

Within Pythia-410M, the perturbation magnitude |delta_L|/|input_L| across belly layers (6-16) follows a compressible functional form. Applying ZTARE's template enumeration and holdout gates:

**Champion:** $z = a \cdot \sqrt{\ln(n)} + b$, where $a = -0.150$, $b = 0.699$

This k=2 form passes visible gates (max residual 0.035, BIC = -80.5). However, holdout prediction at layers 18-21 fails (max residual 0.063, threshold 0.05): the decay accelerates in the recovery phase, confirming a phase transition at the bottleneck-to-output boundary that the single-regime law cannot capture.

### 6.2 Cross-Scale: Perturbation Magnitude vs Depth (Falsified Power Law)

Cross-scale analysis on Pythia-70M (6 layers), Pythia-160M (12 layers), Pythia-410M (24 layers), and Pythia-1B (16 layers) was conducted to test whether the within-model decay generalizes.

| Model | Params | Layers | Hidden | Belly Mean |
|-------|--------|--------|--------|------------|
| 70M | 70M | 6 | 512 | 1.197 |
| 160M | 160M | 12 | 768 | 0.425 |
| 410M | 410M | 24 | 1024 | 0.114 |
| 1B | 1000M | 16 | 2048 | 0.119 |

The first three points suggested a parameter-scaling power law ($N^{-0.6}$, $R^2 = 0.99$). The Pythia-1B point falsified this: the power law predicts 0.046 for 1B, but the actual value is 0.119 (2.6x higher). The confound: in Pythia-70M/160M/410M, layer count and parameter count are correlated (6/12/24 layers). The 1B model has only 16 layers despite 2.5x more parameters, breaking the confound.

The perturbation ratio scales with **layer depth**, not parameter count, and appears to hit a **floor around 0.11-0.12** beyond approximately 16 layers. This floor is consistent with the null model finding: training compresses the perturbation ratio from the untrained value (~0.5) to ~0.11, and this floor is set by the residual stream geometry (residual connections + layer normalization), not by depth past a saturation point.

### 6.3 The Alignment Enigma: An Unsolved Classification

The cross-architecture null model comparison reveals that some model families learn perturbation alignment during training and others do not. The discriminating variable is unknown.

| Model | Arch | Year | Untrained | Trained | Delta | Learns? |
|-------|------|------|-----------|---------|-------|---------|
| Pythia-410M | GPTNeoX (full MHA) | 2023 | 70.2% | 72.2% | +2pp | **No** |
| Pythia-160M | GPTNeoX (full MHA) | 2023 | 59.4% | 58.6% | -0.8pp | **No** |
| Qwen2-0.5B | Qwen2 (GQA 14H/2KV) | 2024 | 71.1% | 71.6% | +0.5pp | **No** |
| GPT-2 Small | GPT-2 (full MHA) | 2019 | 58.4% | 38.1% | -20pp | **Yes** |
| SmolLM-135M | Llama (GQA 9H/3KV) | 2024 | 73.7% | 67.7% | -6pp | **Yes** |
| SmolLM-360M | Llama (GQA 15H/5KV) | 2024 | 74.8% | 56.8% | -18pp | **Yes** |
| Mamba-370M | SSM (selective scan) | 2024 | 76.0% | 62.0% | -14pp | **Yes** |

The initial hypothesis (recurrent state compression predicts alignment) was falsified by SmolLM-360M, a Llama-family transformer with GQA that learns alignment (-18pp) despite having no recurrent state. GPT-2 Small (full MHA, 2019) also learns alignment (-20pp) while Pythia-160M (same architecture type) does not.

A secondary hypothesis (mean weight norm predicts alignment) identified perfect separation: YES group norms 167-278, NO group norms 25-59. However, a direct weight-scaling test showed cancellation is invariant under 3x weight scaling (LayerNorm strips the uniform factor). Weight norm is a proxy, not a cause.

A controlled continue-training experiment (400 steps, weight_decay=0 vs 0.1 on Pythia-410M) showed no difference between arms. The weight decay causal claim did not replicate in continue-training, though the test may be too weak (memorization of 144KB corpus, model already locked in trained basin).

The correlational evidence remains: models trained on curated data (WebText, Cosmopedia) learn alignment; models trained on raw web crawls (The Pile, Alibaba data) do not. Whether this reflects data quality, optimizer configuration, initialization scheme, or their interaction is an open question that requires from-scratch controlled training experiments.

---

## 7. Discussion

### 7.1 What This Paper Does Not Claim

We do not claim that the 72% cancellation is "waste" in a normative sense. The portfolio analogy is apt: a portfolio of uncorrelated bets that nets 28% of gross notional is not "72% inefficient" -- it is diversified. The cancellation is the geometric price of diverse computation in a residual architecture.

We do not claim to have identified the causal variable for learnable alignment. The YES/NO split across 7 models correlates with training data quality and weight norm, but neither has been established as causal. The alignment enigma remains open.

We do not prescribe a successor architecture. The measurements constrain what any successor must achieve but do not specify how to achieve it.

### 7.2 What This Paper Does Claim

1. **The BOS contamination artifact** is widespread and produces false low-rank bottleneck profiles. Any study reporting effective rank of transformer hidden states without per-position norm analysis may be affected.

2. **Cancellation invariance is architecture-dependent.** In some model families (Pythia, Qwen2), the ~70% cancellation is invariant to training. In others (GPT-2, SmolLM, Mamba), training reduces cancellation by 6-20pp. The discriminating variable is unknown.

3. **Training teaches coordination, not alignment (in some architectures).** The five-fold increase in residual rank and the r=0.9 magnitude correlation are learned. Whether the cancellation ratio also changes is model-family-dependent.

4. **Cross-layer orthogonality is universal** across all tested architectures (transformers and SSMs). The layers compute in different subspaces regardless of mechanism, training data, or model size.

5. **Weight norm separates but does not cause.** Mean weight norm perfectly classifies YES/NO alignment groups but is not causal (invariant under scaling, LayerNorm strips magnitude). The weight norm is an epiphenomenon of the true causal variable.

### 7.3 Prior Work Survived (from earlier analyses)

Power-law scaling (Kaplan/Chinchilla) was rejected by holdout gates on Pythia cross-model loss data. The compositional form $\sqrt{n/\ln(n)}$ wins BIC. Approximately half (48%) of benchmark capabilities freeze in the first third of training compute. These findings are independent of the bottleneck analysis and do not depend on the BOS correction.

---

## 8. Methods

All measurements use Pythia-410M (EleutherAI, 24 layers, 1024 hidden) unless stated otherwise. Hidden states are extracted via `output_hidden_states=True` with float32 precision. SVD uses numpy's `linalg.svd`. BOS (position 0) is excluded from all per-token analyses. Effective rank is computed as $\exp(H)$ where $H = -\sum_i \hat{s}_i \ln \hat{s}_i$ and $\hat{s}_i = s_i / \sum_j s_j$ are normalized singular values. The untrained null model uses `AutoModelForCausalLM.from_config()` with no weight loading.

Cross-family replication uses GPT-2-medium (OpenAI, 24 layers, 1024 hidden), OPT-350M (Meta, 24 layers, 1024 hidden), and Mamba-370M (state-spaces, 48 layers, 1024 hidden).

All scripts are available at `projects/gp116_cot_exchange/` in the repository.

---


## 9. The Compute Bottleneck Is Also an Illusion: Discovery Is Bottlenecked by Grammar

The first eight sections of this paper showed that the *measurement* of an internal-representation bottleneck in deep residual networks was an artifact (BOS contamination), and that the underlying mechanism is cross-layer orthogonality with cancellation, not compression. The bottleneck claim was a measurement illusion.

A structurally identical claim can be made about the *discovery* bottleneck in LLM-driven scientific research. The dominant narrative holds that scientific discovery will emerge as an automatic byproduct of scaling raw compute: bigger models, longer chains-of-thought, larger context windows, more search iterations. We tested this assumption empirically against an alternative. The alternative is that discovery is bottlenecked by the rigidity of the hypothesis grammar and the strictness of the verification environment. We find that the alternative is correct.

### 9.1 The controlled experiment

We constructed a substrate (`gp023_crucial`) presenting an LLM-driven symbolic-regression apparatus with 33 noise-free observations of the function $z = f(x_1, x_2)$ where the ground truth is

$$z = \frac{x_1^3}{\exp(x_1/x_2) - 1}$$

(Planck's spectral radiance, with cold variable names; named-entity denylist enforced (no reference to "Planck", "blackbody", "radiation", "photon", "Bose-Einstein", "Wien", or "Rayleigh-Jeans" permitted in any artifact)).

We pre-registered two hypotheses:

**H-COMPUTE-01 (compute is the binding constraint).** Run the apparatus under a bounded grammar (the standard primitive set, without `UNIVERSAL_DENOMINATOR`) for 32 iterations, a 2× extension beyond the original 16-iter budget. Predict: the score increases monotonically and eventually recovers the true form.

**H-GRAMMAR-01 (grammar is the binding constraint).** Run the same apparatus with the SAME compute budget (16 iterations, original allotment), but expand the grammar to include `UNIVERSAL_DENOMINATOR`. Predict: the apparatus recovers the true form structurally, with farther-tail discriminator passing.

### 9.2 Result

H-COMPUTE-01 was confirmed in the rejection direction. After 32 iterations, the apparatus's champion score plateaued at 93. Of the final 15 emergency-pivot iterations beyond stagnation, *zero* produced structural progress. The champion at iter 17 was a high-fitting Padé-style rational approximation that satisfied the holdout gate but, on the farther-tail discriminator (a held-out tail region not used during fitting), diverged from the true Planck curve by factors that grew rapidly with $x_1$.

H-GRAMMAR-01 was confirmed in the positive direction. With `UNIVERSAL_DENOMINATOR` available, the apparatus recovered the true form $z = x_1^3 / (\exp(x_1/x_2) - 1)$ to four decimal places at iter 6 of the same compute budget. All six farther-tail discriminator points passed at < 0.13% relative error.

The differential is the load-bearing observation: doubling compute under bounded grammar yielded zero structural progress; adding one grammar primitive at baseline compute yielded the true law in 6 iterations.

### 9.3 The cold-LLM null

A reviewer panel will reasonably ask: did the apparatus add anything that a frontier zero-shot LLM does not already produce? We tested this directly. We presented a fresh `gpt-4.1` instance with the exact same 33 observations under cold variable names, no apparatus, no tools, no chain-of-thought scaffold beyond the model's standard inference. Single-shot. The model produced

$$z = 0.783 \cdot x_1^6 \cdot x_2^{-3} \cdot \exp(-2 \cdot x_1/x_2)$$

This is **Wien's approximation**, the high-frequency limit of Planck's law. The form is structurally distinct from the true form. There is no $(\exp(z) - 1)$ denominator, different power dependence on $x_1$ and $x_2$. On the same 33 visible points, this form has SSE = 71.855, against the true Planck form's SSE = 7.45 × 10⁻⁶. The cold model's self-estimate of its own SSE was "< 1, likely 0.1," over-confident by a factor of ~700. On simple extrapolation to $x_1 = 20$, the model's prediction was 3.6% of the true value; the model is 25× wrong, and the relative error is increasing monotonically.

The cold-LLM null is therefore *structurally separated* from the apparatus output: the cold model produces a Padé/Wien-class approximation that fits visible regimes adequately and diverges in extrapolation; the apparatus, given the right grammar primitive, produces the true structural form.

### 9.4 Evolutionary-epistemology framing

The differential result admits a precise account in the language of selectionist epistemology [@campbell1960; @popper1972; @hull1988]. The LLM is a high-variance combinatorial hypothesis generator; we treat its proposal stream as analogous to mutation in a Darwinian process. The verification stack (the holdout gate, the parsimony-penalized BIC, the farther-tail discriminator, the adversarial judge) is the selection environment. Within this frame:

- **Compute scaling** corresponds to *increasing the mutation rate*. More mutations sampled per generation. But under a fixed ontology, mutation alone does not introduce structurally novel forms; it only explores the existing hypothesis space more densely.
- **Grammar expansion** corresponds to *introducing a new genetic locus*. A previously unrepresentable structural family becomes expressible. The selection environment can now test forms that were unreachable in principle.

The empirical claim is that under bounded grammar, the apparatus saturates a *score ceiling* $C(G)$ determined by the grammar's expressive capacity relative to the true structural class, and this ceiling is unmoved by additional compute. Crossing the ceiling requires modifying the grammar. The cold-LLM null demonstrates that an unconstrained generator (no apparatus, no grammar, no selection environment) does not transcend this constraint either; it produces forms drawn from its training distribution that may approximate the data within the visible regime but fail under the apparatus's farther-tail discriminator.

This inverts the prevailing assumption. Discovery is not the automatic byproduct of compute. It is the joint product of hypothesis variation, ontological expressivity, and selection discipline. Under our apparatus, the binding constraint between those three is grammar; under the cold-LLM null, it is the absence of selection discipline. In both regimes, raw compute is not the binding constraint.

### 9.5 The two illusions, jointly

The bottleneck illusion documented in §1–§8 (the "30D bottleneck" in Pythia-410M) was a measurement artifact: BOS contamination caused a low-rank readout where the underlying computation was high-rank. The bottleneck illusion documented in §9.1–§9.4 (the "compute ceiling" in LLM-driven discovery) is a *framing* artifact: scaling compute under bounded grammar produces no structural progress, so the apparent ceiling is real but its identification with compute is wrong.

Both illusions disappear under the same epistemic move: *measure the right variable*. For internal representations, that means per-token rather than mean-pooled rank. For LLM-driven discovery, that means grammar-conditional rather than compute-conditional plateau detection. Future work in both domains will benefit from the same discipline: name the variable that is actually binding before publishing claims about the variable that is incidentally measured.


---

## Acknowledgments

The panel pre-registration review identified five critical flaws in the initial extraction methodology (residual stream confound, BOS contamination, independent centering, missing stratification, quantile binning distortion). All five were corrected before analysis. The untrained null model test was recommended by the Popper persona in the adversarial review panel.
