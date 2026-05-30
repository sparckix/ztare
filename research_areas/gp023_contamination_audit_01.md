# GP-023 Independent Contamination Audit — audit 01

**Runtime model family (planned):** Gemini (default in autoresearch_loop.py)
**Checker model:** gpt-4o (OpenAI)
**Checker family vs runtime family:** distinct (OK, pre-reg compliant)
**Probe temperature:** 0.2
**Sandbox files probed:** projects/gp023_planck_sandbox_01/evidence.txt + raw/curve.csv (sub-sampled)

## Verdict: PASS

Contamination is declared if either probe's response contains any of the following banned terms (case-insensitive substring match):

```
black-body, blackbody, black body, planck, rayleigh, jeans, wien, ultraviolet catastrophe, uv catastrophe, photon, quantum of energy, energy quantum, spectral density, spectral radiance, stefan-boltzmann, stefan boltzmann, thermal radiation, cavity radiation
```

**Probe A hits:** none
**Probe B hits:** none

---

## Probe A — open-ended identification

### System prompt

```
You are an expert in quantitative pattern recognition across physics, chemistry, biology, queueing theory, economics, and signal processing. Your job is to identify the underlying phenomenon behind an anonymized dataset. Be aggressive, exhaustive, and specific. If the data resembles a well-known textbook problem, name it explicitly, give the canonical formula, and explain how the anonymized variables map to the textbook variables. Do not hedge. Do not refuse. Rank your top three guesses.
```

### Response

Based on the dataset and the qualitative behavior described, the phenomenon most closely resembles a resonance phenomenon, specifically the behavior of a driven harmonic oscillator or a resonance curve in a physical system. Here's the detailed analysis:

### Top Three Candidate Phenomena:

1. **Resonance in a Driven Harmonic Oscillator**
   - **Era of Discovery:** 19th Century
   - **Canonical Governing Formula:** The response of a driven harmonic oscillator is typically described by the formula:
     \[
     I(\omega) = \frac{F_0^2}{(k - m\omega^2)^2 + (b\omega)^2}
     \]
     where \( \omega \) is the driving frequency, \( F_0 \) is the amplitude of the driving force, \( k \) is the spring constant, \( m \) is the mass, and \( b \) is the damping coefficient.
   - **Variable Mapping:**
     - \( \phi \) maps to the driving frequency \( \omega \).
     - \( \psi \) maps to the amplitude of the driving force \( F_0 \).
     - \( I \) maps to the response intensity, which is the amplitude of the oscillation.
   - **Identification Features:** The dataset shows a peak in response intensity \( I \) at certain values of \( \phi \), which shifts with changes in \( \psi \). This is characteristic of resonance, where the peak shifts with changes in system parameters like driving force amplitude.

2. **RLC Circuit Resonance**
   - **Era of Discovery:** Early 20th Century
   - **Canonical Governing Formula:** The response of an RLC circuit is given by:
     \[
     I(\omega) = \frac{V_0}{\sqrt{R^2 + (\omega L - \frac{1}{\omega C})^2}}
     \]
     where \( \omega \) is the angular frequency, \( V_0 \) is the input voltage, \( R \) is the resistance, \( L \) is the inductance, and \( C \) is the capacitance.
   - **Variable Mapping:**
     - \( \phi \) maps to the angular frequency \( \omega \).
     - \( \psi \) maps to the input voltage \( V_0 \).
     - \( I \) maps to the current amplitude in the circuit.
   - **Identification Features:** The peak in current amplitude \( I \) as a function of frequency \( \phi \) and its shift with changes in voltage \( \psi \) is typical of resonance in RLC circuits.

3. **Chemical Reaction Rate with Temperature (Arrhenius Equation)**
   - **Era of Discovery:** Late 19th Century
   - **Canonical Governing Formula:** The Arrhenius equation for reaction rates is:
     \[
     k(T) = A e^{-\frac{E_a}{RT}}
     \]
     where \( T \) is the temperature, \( A \) is the pre-exponential factor, \( E_a \) is the activation energy, and \( R \) is the gas constant.
   - **Variable Mapping:**
     - \( \phi \) maps to the inverse temperature \( 1/T \).
     - \( \psi \) maps to the pre-exponential factor \( A \).
     - \( I \) maps to the reaction rate constant \( k \).
   - **Identification Features:** The peak in reaction rate \( I \) with changes in \( \phi \) and its shift with changes in \( \psi \) could be interpreted as a temperature-dependent reaction rate, although this is less likely given the dataset's description.

### Conclusion:
The most likely phenomenon is the resonance in a driven harmonic oscillator, given the clear peak and shift in response intensity with changes in the driving parameter, which is characteristic of resonance phenomena. The RLC circuit resonance is a close second due to similar mathematical behavior. The chemical reaction rate is a distant third, as the dataset does not explicitly mention temperature or chemical kinetics.

---

## Probe B — forensic de-anonymization (tells the checker the data IS a renamed textbook problem)

### System prompt

```
You are a forensic scientist specializing in identifying anonymized or obfuscated textbook problems. You assume the dataset in front of you is a renamed, possibly perturbed version of a canonical problem from physics, chemistry, or engineering. Your job is to de-anonymize it. Aggressive identification is the goal. Name the source formula.
```

### Response

1. **Exact Name of the Historical Problem:**
   The dataset is a perturbed version of the "Resonance in RLC Circuits" problem, specifically examining the frequency response of an RLC circuit.

2. **Canonical Closed-Form Formula:**
   The canonical formula for the response intensity (current amplitude) in an RLC circuit as a function of frequency is given by:
   \[
   I(\omega) = \frac{V}{\sqrt{R^2 + (\omega L - \frac{1}{\omega C})^2}}
   \]
   where \( V \) is the voltage amplitude, \( R \) is the resistance, \( L \) is the inductance, \( C \) is the capacitance, and \( \omega \) is the angular frequency.

3. **Variable Rename Map:**
   - \( \phi \) -> \( \omega \) (angular frequency)
   - \( \psi \) -> \( V \) (voltage amplitude)
   - \( I \) -> \( I \) (current amplitude)

4. **Physical Constants and Perturbed Exponents:**
   - The exponents in the dataset likely correspond to the parameters \( R \), \( L \), and \( C \) in the RLC circuit. The shift in peak location with increasing \( \psi \) (voltage) suggests a change in the driving frequency relative to the natural frequency of the circuit, which is influenced by \( L \) and \( C \).

5. **Confidence Score:**
   - 95

**Rationale:**
- The dataset describes a system where the response intensity rises, peaks, and then falls, which is characteristic of resonance phenomena.
- The shift in peak location with changing \( \psi \) (voltage) is consistent with changes in driving frequency in an RLC circuit.
- The bounded parameter \( \phi \) aligns with the typical range of angular frequencies in such problems.
- The qualitative shape of the curves and the behavior of the peaks strongly suggest an analogy to resonance in RLC circuits.
