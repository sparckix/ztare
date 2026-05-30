# Cold-LLM null test — GP-023 Planck substrate, GPT-4.1

> **Seam metadata** · `seam_id:` cold_llm_null_gp023_planck_gpt41 · `track:` audits · `status:` closed · `last_updated:` 2026-05-08


**Status:** closed *(inferred 2026-05-08 — needs operator review)*

**Substrate:** gp023_crucial_02_extended
**Cold model:** gpt-4.1 (zero-shot, no apparatus, no tools)
**Date:** 2026-04-26
**Tokens:** prompt=644, completion=3481

---

## Cold-LLM response

Let's analyze the data step by step to propose a closed-form expression for \( z = f(x_1, x_2) \).

---

## 1. **Data Structure**

- \( x_1 \): 0.5, 0.8, 1.0, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0, 6.0, 8.0
- \( x_2 \): 0.5, 1.0, 2.0
- For each \( x_2 \), there is a sequence of \( x_1 \) values.

---

## 2. **Initial Observations**

### **For fixed \( x_2 \), varying \( x_1 \):**
- For each \( x_2 \), as \( x_1 \) increases, \( z \) increases to a peak and then decreases.
- The peak shifts to higher \( x_1 \) as \( x_2 \) increases.

### **For fixed \( x_1 \), varying \( x_2 \):**
- For each \( x_1 \), as \( x_2 \) increases, \( z \) increases.

---

## 3. **Guessing the Functional Form**

Given the "rise and fall" with respect to \( x_1 \) for each \( x_2 \), a common form is:

\[
z = A x_1^p e^{-B x_1}
\]

But since the peak shifts with \( x_2 \), perhaps \( B \) depends on \( x_2 \), or the exponent does.

Alternatively, perhaps:

\[
z = x_1^a x_2^b e^{-c x_1 / x_2}
\]

This form is common in physics and statistics (e.g., gamma, Maxwell-Boltzmann, etc.), and allows the peak to shift with \( x_2 \).

---

## 4. **Testing the Form**

Let’s try:

\[
z = K x_1^\alpha x_2^\beta \exp\left(-\gamma \frac{x_1}{x_2}\right)
\]

- For fixed \( x_2 \), as \( x_1 \) increases, \( z \) rises (due to \( x_1^\alpha \)), peaks, then falls (due to the exponential).
- The peak occurs at \( x_1 = \frac{\alpha x_2}{\gamma} \), so as \( x_2 \) increases, the peak shifts right, matching the data.

---

## 5. **Estimating Parameters**

Let’s use the data to estimate parameters.

### **Find the peak for each \( x_2 \):**

- For \( x_2 = 0.5 \), peak at \( x_1 \approx 1.5 \)
- For \( x_2 = 1.0 \), peak at \( x_1 \approx 3.0 \)
- For \( x_2 = 2.0 \), peak at \( x_1 \approx 6.0 \)

So, the peak \( x_1^* \) is roughly proportional to \( x_2 \):

\[
x_1^* \approx 3 x_2
\]

But from the formula, the peak is at \( x_1^* = \frac{\alpha x_2}{\gamma} \implies \frac{\alpha}{\gamma} \approx 3 \implies \gamma \approx \frac{\alpha}{3} \)

---

### **Plug in values to estimate exponents**

Let’s take the value at the peak for \( x_2 = 1.0, x_1 = 3.0 \):

\[
z = 1.414737
\]
\[
z = K x_1^\alpha x_2^\beta \exp\left(-\gamma \frac{x_1}{x_2}\right)
\]
\[
1.414737 = K \cdot 3^\alpha \cdot 1^\beta \exp(-\gamma \cdot 3/1)
\]

Similarly, for \( x_2 = 2.0, x_1 = 6.0 \):

\[
z = 11.317470 = K \cdot 6^\alpha \cdot 2^\beta \exp(-\gamma \cdot 6/2)
= K \cdot 6^\alpha \cdot 2^\beta \exp(-3\gamma)
\]

Divide the two equations:

\[
\frac{11.317470}{1.414737} = \frac{6^\alpha \cdot 2^\beta}{3^\alpha \cdot 1^\beta}
\]
\[
= 2^\alpha \cdot 2^\beta = 2^{\alpha+\beta}
\]
\[
\frac{11.317470}{1.414737} \approx 8.0
\]
\[
2^{\alpha+\beta} = 8 \implies \alpha+\beta = 3
\]

---

### **Estimate \( \alpha \) and \( \gamma \) using the peak position**

Recall: peak at \( x_1^* = \frac{\alpha x_2}{\gamma} \)

From above, \( x_1^* = 3 x_2 \implies \frac{\alpha}{\gamma} = 3 \implies \gamma = \frac{\alpha}{3} \)

---

### **Estimate \( K \) using one data point**

Let’s use \( x_2 = 1.0, x_1 = 3.0, z = 1.414737 \):

\[
z = K \cdot 3^\alpha \cdot 1^\beta \exp(-\gamma \cdot 3)
\]
\[
1.414737 = K \cdot 3^\alpha \exp(-\gamma \cdot 3)
\]

But \( \gamma = \alpha/3 \implies \gamma \cdot 3 = \alpha \)

So:

\[
1.414737 = K \cdot 3^\alpha \exp(-\alpha)
\]

---

### **Estimate \( \alpha \) and \( \beta \) using another data point**

Let’s use \( x_2 = 0.5, x_1 = 1.5, z = 0.176842 \):

\[
z = K \cdot 1.5^\alpha \cdot 0.5^\beta \exp(-\gamma \cdot 1.5/0.5)
= K \cdot 1.5^\alpha \cdot 0.5^\beta \exp(-3\gamma)
\]

But \( \gamma = \alpha/3 \implies 3\gamma = \alpha \):

\[
0.176842 = K \cdot 1.5^\alpha \cdot 0.5^\beta \exp(-\alpha)
\]

---

Now, divide the two equations:

\[
\frac{1.414737}{0.176842} = \frac{3^\alpha \cdot 1^\beta}{1.5^\alpha \cdot 0.5^\beta}
\]
\[
\approx 8.0 = \frac{3^\alpha}{1.5^\alpha} \cdot \frac{1}{0.5^\beta}
= (2)^\alpha \cdot 2^\beta = 2^{\alpha+\beta}
\]

Again, \( \alpha+\beta = 3 \), which matches our earlier result.

---

### **Estimate \( \alpha \) numerically**

Let’s try \( \alpha = 2 \), \( \beta = 1 \):

\[
\alpha + \beta = 3
\]

Now, check if this fits the peak value:

For \( x_2 = 1.0, x_1 = 3.0 \):

\[
z = K \cdot 3^2 \cdot 1^1 \cdot \exp(-2)
= K \cdot 9 \cdot e^{-2}
\]
\[
1.414737 = K \cdot 9 \cdot 0.1353 \implies K = \frac{1.414737}{1.2177} \approx 1.162
\]

Now, check for \( x_2 = 2.0, x_1 = 6.0 \):

\[
z = K \cdot 6^2 \cdot 2^1 \cdot \exp(-2 \cdot 6/2)
= K \cdot 36 \cdot 2 \cdot \exp(-6)
= K \cdot 72 \cdot 0.00247875 \approx K \cdot 0.17847
\]
\[
K = 1.162 \implies z \approx 0.207
\]

But the actual value is 11.317470, so this is way off.

---

### **Try \( \alpha = 3, \beta = 0 \):**

\[
\alpha + \beta = 3
\]

For \( x_2 = 1.0, x_1 = 3.0 \):

\[
z = K \cdot 3^3 \cdot 1^0 \cdot \exp(-3)
= K \cdot 27 \cdot 0.04979 \approx K \cdot 1.344
\]
\[
1.414737 = K \cdot 1.344 \implies K \approx 1.053
\]

For \( x_2 = 2.0, x_1 = 6.0 \):

\[
z = K \cdot 6^3 \cdot 2^0 \cdot \exp(-3 \cdot 6/2)
= K \cdot 216 \cdot \exp(-9)
= K \cdot 216 \cdot 0.0001234 \approx K \cdot 0.0267
\]
\[
K = 1.053 \implies z \approx 0.028
\]

Still way off from 11.3.

---

### **Try \( \alpha = 2, \beta = 1 \), but adjust the exponential argument**

Maybe the exponential should be \( -\gamma x_1 \), not \( x_1/x_2 \).

Let’s try:

\[
z = K x_1^\alpha x_2^\beta \exp(-\gamma x_1)
\]

For \( x_2 = 1.0, x_1 = 3.0 \):

\[
z = K \cdot 9 \cdot 1 \cdot \exp(-3\gamma)
\]
\[
1.414737 = K \cdot 9 \cdot \exp(-3\gamma)
\]

For \( x_2 = 2.0, x_1 = 6.0 \):

\[
z = K \cdot 36 \cdot 2 \cdot \exp(-6\gamma)
= K \cdot 72 \cdot \exp(-6\gamma)
\]
\[
11.317470 = K \cdot 72 \cdot \exp(-6\gamma)
\]

Divide:

\[
\frac{11.317470}{1.414737} = \frac{72}{9} \cdot \frac{\exp(-6\gamma)}{\exp(-3\gamma)}
= 8 \cdot \exp(-3\gamma)
\]
\[
8.0 = 8 \cdot \exp(-3\gamma) \implies \exp(-3\gamma) = 1 \implies \gamma = 0
\]

But if \( \gamma = 0 \), then the function is just a power law, but the data falls off at large \( x_1 \).

---

### **Try a function of the form \( z = K x_1^\alpha x_2^\beta \exp(-\gamma x_1 / x_2) \) again**

Let’s try to estimate \( \gamma \) directly.

Recall, the peak occurs at \( x_1^* = \frac{\alpha x_2}{\gamma} \). From data, \( x_1^* \approx 3 x_2 \implies \gamma = \frac{\alpha}{3} \).

Let’s try \( \alpha = 6 \implies \gamma = 2 \).

Now, for \( x_2 = 1.0, x_1 = 3.0 \):

\[
z = K \cdot 3^6 \cdot 1^\beta \cdot \exp(-2 \cdot 3/1)
= K \cdot 729 \cdot \exp(-6)
= K \cdot 729 \cdot 0.00247875 \approx K \cdot 1.807
\]
\[
1.414737 = K \cdot 1.807 \implies K \approx 0.783
\]

For \( x_2 = 2.0, x_1 = 6.0 \):

\[
z = K \cdot 6^6 \cdot 2^\beta \cdot \exp(-2 \cdot 6/2)
= K \cdot 46,656 \cdot 2^\beta \cdot \exp(-6)
= K \cdot 46,656 \cdot 2^\beta \cdot 0.00247875 \approx K \cdot 115.6 \cdot 2^\beta
\]
\[
z = 11.317470
\]
\[
11.317470 = 0.783 \cdot 115.6 \cdot 2^\beta \implies 11.317470 = 90.5 \cdot 2^\beta \implies 2^\beta = 0.125 \implies \beta = -3
\]

So, \( \alpha = 6, \gamma = 2, \beta = -3, K = 0.783 \).

---

## 6. **Final Proposed Formula**

\[
\boxed{
z = 0.783 \cdot x_1^6 \cdot x_2^{-3} \cdot \exp\left(-2 \frac{x_1}{x_2}\right)
}
\]

---

## 7. **Estimate the Sum of Squared Residuals**

Given the data is noise-free and the formula was fit to match the peaks, and the functional form matches the data's qualitative behavior, the sum of squared residuals should be **very small** (but not exactly zero, since the fit is not perfect).

**Estimated sum of squared residuals:**  
\[
\boxed{\text{On the order of } 0.1 \text{ or less}}
\]
(If you compute it exactly, it might be a bit higher, but likely less than 1.)

---

## **Summary**

### **Formula:**
\[
\boxed{
z = 0.783 \cdot x_1^6 \cdot x_2^{-3} \cdot \exp\left(-2 \frac{x_1}{x_2}\right)
}
\]

### **Estimated sum of squared residuals:**
\[
\boxed{< 1}
\]
(Likely much less, perhaps around 0.1)

---

**Reasoning:**  
- The data shows a peak in \( x_1 \) that shifts linearly with \( x_2 \).
- The functional form \( x_1^\alpha x_2^\beta \exp(-\gamma x_1 / x_2) \) captures this.
- Fitting the peaks yields \( \alpha = 6, \gamma = 2, \beta = -3, K = 0.783 \).
- The formula should fit the data closely, with small residuals.

---

## Residual analysis vs ground truth (added 2026-04-26)

True form (ZTARE recovered with UNIVERSAL_DENOMINATOR primitive at iter 6 of `gp023_crucial_03`):

    z = x₁³ / (exp(x₁/x₂) - 1)     # Planck spectral radiance (cold variables)

Cold GPT-4.1 form (zero-shot, no apparatus):

    z = 0.783 · x₁^6 · x₂^(-3) · exp(-2 · x₁/x₂)     # Wien-style approximation

### Visible-set SSE comparison (n=33 rows)

| Form | SSE | mean |res| |
|---|---|---|
| Cold GPT-4.1 form | **71.855** | (catastrophic on rising edge) |
| True Planck form | **7.45e-06** | <0.001% per row |
| **Gap** | **~10⁷× worse** | — |

GPT-4.1's self-estimated SSE was "< 1, likely ~0.1" — overconfident by **~700×**.

### Worst per-row residuals from GPT-4.1's form

| x₁ | x₂ | actual z | GPT-4.1 pred | rel err |
|---|---|---|---|---|
| 1.5 | 2.0 | 3.022 | 0.249 | **91.8%** |
| 2.0 | 2.0 | 4.658 | 0.848 | 81.8% |
| 2.5 | 2.0 | 6.275 | 1.961 | 68.7% |
| 3.0 | 2.0 | 7.756 | 3.552 | 54.2% |

The Wien-style form has no rising edge — it underestimates dramatically below the peak.

### Extrapolation (x₁ > 8, beyond visible)

| x₁ | x₂ | GPT-4.1 | True Planck | GPT-4.1 / True |
|---|---|---|---|---|
| 12.0 | 2.0 | 1.796 | 4.294 | 0.42 |
| 16.0 | 2.0 | 0.185 | 1.375 | 0.13 |
| 20.0 | 2.0 | 0.013 | 0.363 | **0.036** |

GPT-4.1's form diverges to ~3.6% of the true value by x₁=20. **A farther-tail discriminator at MRE<30% catches this immediately.**

## Bucket verdict

**Bucket C — apparatus-only.** A frontier zero-shot LLM (GPT-4.1, model id `gpt-4.1`) with cold variable names produces a structurally-wrong Padé/Wien-class approximation that:

1. Fits visible 10⁷× worse than the true form
2. Has 91.8% relative error on the rising edge
3. Diverges 25× in modest extrapolation

ZTARE with UNIVERSAL_DENOMINATOR primitive recovered the structurally-correct form to SSE 7.45e-06. The gap is not closeable by frontier scale alone — it is closed by the *apparatus's bounded grammar with the right primitive*, which is the GCH claim made empirically falsifiable.

This single result, paired with the H-COMPUTE-01 / H-GRAMMAR-01 differential (gp023_crucial_02_extended at 32 iters → 93 plateau, gp023_crucial_03 at 6 iters → 88 with structurally correct form), makes the GCH paper claim defensible against the strongest cold-LLM-null reviewer attack.
