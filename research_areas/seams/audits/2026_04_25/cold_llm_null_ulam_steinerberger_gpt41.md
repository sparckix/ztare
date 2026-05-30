# Cold-LLM null — Ulam/Steinerberger reciprocal-rotation, GPT-4.1

> **Seam metadata** · `seam_id:` cold_llm_null_ulam_steinerberger_gpt41 · `track:` audits · `status:` closed · `last_updated:` 2026-05-08


**Status:** closed *(inferred 2026-05-08 — needs operator review)*

**Model:** gpt-4.1, zero-shot, no apparatus
**Tokens:** prompt=240, completion=983

## Cold response

Let's address each question in turn, with as much precision as possible from my training data.

---

### **Question 1: Asymptotic for U(n)**

**Ulam's sequence** (defined by the sieve you describe) is notoriously irregular, but some broad asymptotic behavior is known.

- **Growth Rate:** The sequence grows roughly linearly, i.e., \( U(n) \sim c n \) for some constant \( c \).
- **Best Known Estimate:** The best rigorously established result (as of 2024) is that \( U(n) \) is asymptotically linear, but the exact value of \( c \) is not known in closed form. Numerical experiments suggest \( c \approx 13.5 \), but this is empirical.

**Summary:**  
\[
U(n) \sim c n \quad \text{with} \quad c \approx 13.5
\]
There is no known closed-form for \( c \), and the sequence is not periodic or ultimately regular.

---

### **Question 2: Shifted Reciprocal-Density and Periodicity**

**Background:**  
Steinerberger (2020) and others have observed that the sequence of reciprocals \( 1/U(n) \), when considered as a function of \( n \), exhibits a kind of "hidden periodicity" when plotted against \( n \) modulo some period.

#### **Conjectured Behavior:**

- **Periodic Modulus:**  
  Numerical and heuristic evidence suggests that the sequence \( 1/U(n) \) (or equivalently, the indicator function of Ulam numbers) exhibits a nontrivial periodic structure **modulo a certain period**. The best-known period is approximately **\( \lambda \approx 13.56 \)** (sometimes written as \( \lambda \approx 13.56... \)), which is close to the reciprocal of the density \( c \) above.

- **Precise Statement:**  
  The conjecture is that the sequence \( 1/U(n) \) (or the indicator function of Ulam numbers) **does not become equidistributed** in the integers, but instead, its density as a function of \( n \) modulo \( \lambda \) converges to a **nonconstant, periodic function**. That is, if you plot the density of Ulam numbers in intervals of length \( \lambda \), you see a repeating, non-flat pattern.

- **Residual Density:**  
  The **average density** of Ulam numbers is about \( 1/c \approx 0.074 \), but locally (modulo \( \lambda \)), the density oscillates in a nontrivial way.

- **Mathematical Formulation:**  
  There exists a function \( f: [0, \lambda) \to \mathbb{R} \) such that for large \( N \), the empirical distribution of \( U(n) \bmod \lambda \) converges to \( f \), and \( f \) is not constant.

#### **Summary Statement:**

- The sequence of Ulam numbers has **asymptotic density** \( \approx 1/13.56 \).
- The **indicator function** of Ulam numbers, when viewed modulo \( \lambda \approx 13.56 \), converges to a **nonconstant periodic function**—i.e., the sequence is "quasiperiodic" with period \( \lambda \).
- This is a **nontrivial phenomenon**: the sequence is not random, nor does it become uniformly distributed mod \( \lambda \).

---

### **What I Cannot Recall:**

- I do **not** recall a closed-form for the period \( \lambda \), nor the explicit form of the periodic function \( f \).
- I do **not** recall a rigorous proof of this behavior—it's still a conjecture, supported by numerics and heuristic arguments.

---

## **Summary Table**

| Question | Answer |
|----------|--------|
| 1. Asymptotic for \( U(n) \) | \( U(n) \sim c n \), \( c \approx 13.56 \), no closed form for \( c \) |
| 2. Shifted reciprocal-density periodicity | The density of Ulam numbers modulo \( \lambda \approx 13.56 \) converges to a nonconstant periodic function; the sequence is not equidistributed, but exhibits quasiperiodicity with this period. |

**References:**  
- Steinerberger, S. (2020), "On the regularity of Ulam sequences", and related literature.
- Empirical studies and OEIS A002858.

If you need more technical details or references, let me know!
