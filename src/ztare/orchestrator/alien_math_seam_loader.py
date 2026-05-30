"""GP-168 alien-math seam loader.

Parses the alien-math framings out of `[internal-ref]
GP-164_ztare_v2_reframe_analogy_meta_architecture_seam.md` (Appendix:
Alien-Math Panel Framings). Returns a list of dicts in the shape that
`build_forced_reframe_briefing_block` consumes:

    {"name": str,
     "form": str,                 # Python expression (may contain
                                  # placeholder identifiers like u_0, g_*,
                                  # which are documentary, not executable)
     "field_of_origin": str,
     "what_it_captures": str}

Why a parser instead of importing the constants from the seam: the
seam is the source of truth (operator-curated). Hardcoding alternatives
in code drifts from the seam over time. The parser walks the seam's
``### Framing F<n> — <name>`` headings, captures the first fenced code
block per framing, and the descriptive sentence beneath. If the seam
file is missing, the loader returns the same hardcoded fallback that
`briefing_providers/forced_reframe.py` used to ship — so nothing
regresses if the seams directory hasn't been mounted into the run.

Cache: the parse runs once per process (alternatives don't change
within a run); subsequent calls return the cached list.
"""
from __future__ import annotations

import re
from pathlib import Path
from threading import Lock
from typing import Optional


# Three-fallback list mirrors the prior hardcoded set in
# briefing_providers/forced_reframe.py — same content, same semantics —
# so loader-failure paths produce the same briefing as before.
# Domain-aware Lagrangian framings for modified-gravity / radial-acceleration
# substrates (gp163d-style). When rubric.substrate_domain == "modified_gravity",
# the loader returns these instead of (or alongside) the math families below.
# Each is a panel-recommended Lagrangian class — the mutator's job is to
# derive its weak-field y(g_bar, mass_log10, radius_log10) via
# Euler-Lagrange + spherical-symmetry reduction and submit that as
# PARAMETRIC_FORM. See projects/<run>/evidence.txt Set I for the full math
# (chameleon Z(phi), V(phi), A(phi) functional forms).
_MODIFIED_GRAVITY_LAGRANGIANS: list[dict] = [
    {
        "name": "Chameleon scalar-tensor (panel-recommended seed)",
        "field_of_origin": "modified gravity / Khoury-Weltman chameleon family",
        "form": (
            "# DERIVE FROM L = R/(16*pi*G) - 0.5*Z(phi)*g_munu*d_phi*d_phi - V(phi) - A(phi)*L_matter\n"
            "# with Z(phi) = 1 + (phi/M_star)**(-2),  V(phi) = (a0**2 * M_Pl**2 / (8*pi)) * (phi/M_Pl)**n  (n in {-1, -2}),\n"
            "# A(phi) = exp(phi/M_Pl), M_star ~ a0/c, a0 = 1.2e-10.\n"
            "# Compute Euler-Lagrange, reduce to spherical weak-field, integrate phi profile, output y(g_bar, m, r).\n"
            "# The derived form must satisfy: Cassini |y/g_bar - 1| < 2.3e-5, Mercury < 4e-10, A+B+C MRE matches bridge."
        ),
        "what_it_captures": (
            "non-canonical kinetic Z(phi) produces MOND-low-acceleration regime; "
            "runaway potential V(phi) gives chameleon screening passing Cassini; "
            "conformal coupling A(phi) gives matter-frame fifth force across galaxies/clusters/wide-binaries; "
            "all hardcoded sigmoid centers in the bridge form become derived expressions in {G, a0, M_Pl, M_star}"
        ),
    },
    {
        "name": "f(R) gravity with chameleon screening (Hu-Sawicki flavor)",
        "field_of_origin": "modified gravity / scalar-tensor representation of f(R)",
        "form": (
            "# DERIVE FROM L = f(R) / (16*pi*G) + L_matter,  f(R) = R - m**2 * c1 * (R/m**2)**n / (c2 * (R/m**2)**n + 1)\n"
            "# (Hu-Sawicki form with Compton-mass m, dimensionless c1, c2, n).\n"
            "# 4th-order field equations; recast in scalar-tensor (Einstein frame) for tractable EL.\n"
            "# Spherical Schwarzschild-de Sitter weak-field reduction yields y(g_bar, m, r) with chameleon screening at Solar-System scales."
        ),
        "what_it_captures": (
            "background-curvature scaling provides radius-dependent c_eff; "
            "chameleon mechanism on the scalaron passes Cassini; cosmologically "
            "the best-studied modified-gravity class with explicit perturbation-theory predictions"
        ),
    },
    {
        "name": "AQUAL with chameleon-coupled matter",
        "field_of_origin": "modified gravity / Bekenstein-Milgrom AQUAL extended with screening",
        "form": (
            "# DERIVE FROM L = R/(16*pi*G) - (a0**2 / (8*pi*G)) * F(|grad phi|**2 / a0**2) + A(phi) * L_matter\n"
            "# F(y) = (2/3) * y**(3/2)  (deep-MOND limit) or interpolated F(y) = y * (1 + y)**(-1/2)\n"
            "# A(phi) is the chameleon coupling that breaks AQUAL's local-scalar-only structure.\n"
            "# EOM: nabla*(mu(|grad phi|/a0) * grad phi) = 4*pi*G*rho;  mu = dF/dy.\n"
            "# Spherical reduction yields the standard MOND interpolation in galaxies; A(phi) screening passes Solar System."
        ),
        "what_it_captures": (
            "deep-MOND asymptote y -> sqrt(a0 * g_bar) is exact by construction; "
            "chameleon coupling A(phi) extends AQUAL with mass-dependent screening "
            "(pure AQUAL has no mass dependence — this is the panel-recommended fix)"
        ),
    },
    {
        "name": "MOG (Moffat) with running gravitational coupling",
        "field_of_origin": "modified gravity / Moffat scalar-tensor-vector",
        "form": (
            "# DERIVE FROM L = (R + 2 Lambda)/(16*pi*G(x)) + L_phi[phi, omega(phi)] + L_chi[chi, mu] + L_matter\n"
            "# G(x) = G_N * (1 + alpha) where alpha runs with mass scale; chi is a vector field with mass mu.\n"
            "# Yukawa-like correction at intermediate scales: y = g_bar * (1 + alpha * (1 - exp(-r/lambda) * (1 + r/lambda))).\n"
            "# Caveat: must pass LLR Nordtvedt bound |eta_LLR| < 4e-4 — the alpha,lambda parameters are tightly constrained."
        ),
        "what_it_captures": (
            "running G generates mass-scale-dependent boost naturally (no hidden sigmoids); "
            "vector field chi gives the cluster-scale enhancement that MOND-AQUAL cannot. "
            "But: standard MOG fails Cassini without retuning lambda to ~kpc (which is already gp163d's bridge sigmoid scale -> circular)"
        ),
    },
    {
        "name": "TeVeS-flavored disformal scalar-tensor (post-GW170817 constrained)",
        "field_of_origin": "modified gravity / Bekenstein TeVeS reduced",
        "form": (
            "# DERIVE FROM L = R/(16*pi*G) + L_phi + L_A_mu + L_matter[psi, A(phi, A_mu)*g_munu]\n"
            "# CONSTRAINT: GW170817 + GRB170817A force |c_T/c - 1| < 7e-16, killing disformal A_mu coupling.\n"
            "# Reduced TeVeS = scalar-tensor + a constrained timelike vector; the vector becomes pure-gauge in the GW limit.\n"
            "# Effectively collapses to chameleon scalar-tensor (alternative #1) — listed for completeness; recommend #1 instead."
        ),
        "what_it_captures": (
            "historical TeVeS with full disformal coupling is empirically dead; "
            "the surviving subset is essentially chameleon scalar-tensor with a non-dynamical vector. "
            "If your derivation arrives here, prefer alternative #1 directly"
        ),
    },
]


_FALLBACK_ALTERNATIVES: list[dict] = [
    {
        "name": "RG-flow logistic with logarithmic mass running",
        "field_of_origin": "renormalization-group / statistical mechanics",
        "form": (
            "params['u0'] / (1.0 + (features['x']/params['g_star'])**(1.0 + "
            "params['gamma']*log(max(features.get('mass_log10', 1.0), 1e-9)))) "
            "* features['x'] + features['x']"
        ),
        "what_it_captures": (
            "universal logistic shape in log-log space with slow logarithmic "
            "mass running; no kernels, no piecewise switches, slow regime drift"
        ),
    },
    {
        "name": "Multifractal Legendre quadratic",
        "field_of_origin": "multifractal analysis / dynamical systems",
        "form": (
            "features['x'] * 10**(params['alpha0']*log10(features['x']/"
            "params['g_star']) + params['c2']*(log10(features['x']/"
            "params['g_star']) + params['q0'])**2)"
        ),
        "what_it_captures": (
            "parabolic structure in log-log residuals; asymmetry between "
            "regimes captured by single offset q0 (not separate kernels)"
        ),
    },
    {
        "name": "Modular q-expansion oscillation",
        "field_of_origin": "modular forms / number-theoretic harmonic analysis",
        "form": (
            "features['x'] * (1.0 + params['A']*exp(-params['kappa']*"
            "features['x']**params['p']) * cos(params['omega']*"
            "log(max(features.get('mass_log10', 1.0), 1e-9)) + params['phi']))"
        ),
        "what_it_captures": (
            "periodic structure in log-mass; cluster enhancement and any "
            "suppressed regimes appear as consecutive lobes of one oscillation"
        ),
    },
]


_CACHE_LOCK = Lock()
_CACHED: Optional[list[dict]] = None


def _candidate_seam_paths(project_dir: Optional[Path]) -> list[Path]:
    """Return the paths the loader will try, in order.

    The seam lives outside `projects/<run>/`, so we walk up from the
    project dir to find the repo root, then look at the canonical
    location. We also accept an explicit override via the project
    directory if the operator stages a copy under `projects/.../seams/`.
    """
    paths: list[Path] = []
    if project_dir is not None:
        # Walk up looking for a sibling [internal-ref] tree
        cur = project_dir.resolve()
        for _ in range(6):
            seam_root = cur / "research_areas" / "private" / "seams" / "engine"
            cand = seam_root / "GP-164_ztare_v2_reframe_analogy_meta_architecture_seam.md"
            if cand.exists():
                paths.append(cand)
                break
            if cur == cur.parent:
                break
            cur = cur.parent
    # Fallback: this module lives at src/ztare/orchestrator/, so repo
    # root is three parents up.
    here = Path(__file__).resolve()
    repo_root = here.parents[3]
    canonical = (
        repo_root / "research_areas" / "private" / "seams" / "engine"
        / "GP-164_ztare_v2_reframe_analogy_meta_architecture_seam.md"
    )
    if canonical not in paths:
        paths.append(canonical)
    return paths


# Section header for the default appendix
_APPENDIX_RE = re.compile(
    r"##\s+Appendix:\s+Alien-Math Panel Framings",
    re.IGNORECASE,
)

# Domain → appendix header mapping. Substrates declare `substrate_domain`
# in their rubric; the loader maps that to the appropriate appendix in
# the seam file. Adding a new domain = adding one entry here + one
# appendix in the seam markdown. No more hardcoded Python lists per domain.
_DOMAIN_APPENDIX_HEADERS = {
    "modified_gravity": "Modified-Gravity Lagrangians",
    "org_topology": "Organizational Topology Alternatives",
}


def _appendix_re_for_header(header_text: str) -> "re.Pattern[str]":
    """Build a regex matching `## Appendix: <header_text>` (case-insensitive)."""
    return re.compile(
        r"##\s+Appendix:\s+" + re.escape(header_text),
        re.IGNORECASE,
    )
# Per-framing header: "### Framing F1 — <name>" (em dash or hyphen)
_FRAMING_RE = re.compile(
    r"^###\s+Framing\s+(F\d+)\s+[—\-]\s+(.+?)\s*$",
    re.MULTILINE,
)
# Fenced code block (``` … ```), greedy-stops at next fence
_CODEBLOCK_RE = re.compile(r"```[\w]*\n(.*?)\n```", re.DOTALL)


def _split_framings(appendix_body: str) -> list[tuple[str, str, str]]:
    """Return a list of (framing_id, framing_name, body_text) tuples
    from the appendix body. Body_text covers the framing heading
    through the next ``### Framing`` heading or ``###`` of any kind."""
    matches = list(_FRAMING_RE.finditer(appendix_body))
    out: list[tuple[str, str, str]] = []
    for i, m in enumerate(matches):
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(appendix_body)
        # Stop early at next H3 of any kind so a non-framing ### doesn't
        # bleed in.
        rest = appendix_body[start:end]
        next_h3 = re.search(r"^###\s+", rest, re.MULTILINE)
        if next_h3:
            rest = rest[: next_h3.start()]
        out.append((m.group(1), m.group(2).strip(), rest))
    return out


def _extract_form_string(framing_body: str) -> Optional[str]:
    """Pull the closed-form expression from the *last* fenced code
    block in the framing body. The seam convention places a leading
    ``du/dt = β(u)`` block followed by the ``Closed-form integration``
    block; the closed-form is the one we want."""
    blocks = _CODEBLOCK_RE.findall(framing_body)
    if not blocks:
        return None
    return blocks[-1].strip()


def _extract_what_it_captures(framing_body: str) -> str:
    """Heuristic: the last paragraph in the framing body, stripped of
    bold markers and the K_law=… header. The seam pattern always
    closes a framing with a one-paragraph "Predicts …" sentence."""
    # Strip code blocks
    stripped = _CODEBLOCK_RE.sub("", framing_body)
    # Take the longest non-empty line
    candidates = [ln.strip() for ln in stripped.splitlines() if ln.strip()]
    if not candidates:
        return ""
    # Prefer a sentence starting with "Predicts" or "Captures" if present
    for ln in candidates:
        if ln.lower().startswith(("predicts", "captures")):
            return _clean(ln)
    # Else take the last non-empty line
    return _clean(candidates[-1])


def _clean(text: str) -> str:
    text = re.sub(r"\*\*", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    # Soft cap so we don't blow out the briefing
    if len(text) > 280:
        text = text[:277].rstrip() + "..."
    return text


# Field-of-origin tags inferred from framing names. Defensive — we
# default to "uncategorized" rather than guess and lie.
_FIELD_TAGS = {
    "RG-flow": "renormalization-group / statistical mechanics",
    "Renormalization": "renormalization-group / statistical mechanics",
    "Modular": "modular forms / number-theoretic harmonic analysis",
    "Multifractal": "multifractal analysis / dynamical systems",
}


def _infer_field(framing_name: str) -> str:
    for key, tag in _FIELD_TAGS.items():
        if key.lower() in framing_name.lower():
            return tag
    return "uncategorized cross-domain framing"


def _parse_seam_file(
    seam_path: Path,
    appendix_re: "Optional[re.Pattern[str]]" = None,
) -> Optional[list[dict]]:
    """Parse one seam file. Returns None on parse failure (caller
    should fall back).

    `appendix_re` overrides the default appendix header — used by
    domain-keyed dispatch. When None, the original Alien-Math
    appendix is parsed (backward-compatible behaviour).
    """
    re_to_use = appendix_re if appendix_re is not None else _APPENDIX_RE
    try:
        text = seam_path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return None
    m = re_to_use.search(text)
    if not m:
        return None
    # Body covers from the matched appendix heading up to the next
    # `## Appendix:` heading or EOF. Without this stop, multiple
    # appendices in the same seam file bleed into each other.
    body_start = m.end()
    next_appendix = re.search(r"^##\s+Appendix:\s+", text[body_start:], re.MULTILINE)
    if next_appendix:
        body = text[body_start: body_start + next_appendix.start()]
    else:
        body = text[body_start:]
    framings = _split_framings(body)
    if not framings:
        return None
    out: list[dict] = []
    for fid, fname, fbody in framings:
        form = _extract_form_string(fbody)
        if not form:
            continue
        out.append({
            "name": f"{fid} — {fname}",
            "form": form,
            "field_of_origin": _infer_field(fname),
            "what_it_captures": _extract_what_it_captures(fbody),
        })
    return out or None


def load_alien_math_alternatives(
    project_dir: Optional[Path] = None,
    *,
    use_cache: bool = True,
    domain: Optional[str] = None,
) -> list[dict]:
    """Return alien-math alternatives, domain-aware.

    Args:
        project_dir: project run directory (used to resolve repo root).
        use_cache: caching of parsed seam alternatives.
        domain: optional substrate domain key. When set to
            "modified_gravity" (or aliases), returns
            `_MODIFIED_GRAVITY_LAGRANGIANS` directly — the math-family
            seam doesn't apply to physics-derivation substrates.
            When None or unknown, falls through to the original
            math-family seam (RG-flow / multifractal / modular).

    Domain-aware dispatch was added 2026-04-27 after gp163d v3.2.2 iter-1
    showed the mutator picking path-a (bridge refit) over path-b
    (Lagrangian derivation) because the alien-math fallback offered only
    cross-math-family candidates, not physics Lagrangians. For physics
    substrates (modified gravity, gauge theory, etc.) the apparatus
    needs to surface domain-appropriate Lagrangian classes as REFRAME
    alternatives. See evidence Set I in projects/gp163d_unified_accel/
    for the panel-curated chameleon seed.
    """
    # Domain-aware override: physics-Lagrangian alternatives short-circuit
    # the math-seam parse path entirely. Aliases for common spellings.
    _modified_gravity_aliases = {
        "modified_gravity",
        "modgrav",
        "radial_acceleration",
        "rar",
        "gravity_test",
    }
    if domain and str(domain).strip().lower() in _modified_gravity_aliases:
        return list(_MODIFIED_GRAVITY_LAGRANGIANS)

    # Domain-keyed appendix dispatch. If `substrate_domain` maps to a
    # named appendix in _DOMAIN_APPENDIX_HEADERS, walk the seam paths
    # parsing that appendix specifically. Falls through to default
    # Alien-Math appendix when the domain-specific appendix is missing
    # or empty (resilient to an under-populated seam file).
    paths = _candidate_seam_paths(project_dir)
    domain_key = (str(domain).strip().lower() if domain else None)
    if domain_key and domain_key in _DOMAIN_APPENDIX_HEADERS:
        header = _DOMAIN_APPENDIX_HEADERS[domain_key]
        appendix_re = _appendix_re_for_header(header)
        for p in paths:
            parsed = _parse_seam_file(p, appendix_re=appendix_re)
            if parsed and len(parsed) >= 2:
                # Domain-specific match — do NOT cache (cache key is
                # domain-naive; mixing domains across calls would poison it).
                return list(parsed)
        # Domain-specific appendix not found — log-and-fall-through to default.

    global _CACHED
    if use_cache:
        with _CACHE_LOCK:
            if _CACHED is not None:
                return list(_CACHED)
    parsed: Optional[list[dict]] = None
    for p in paths:
        parsed = _parse_seam_file(p)
        if parsed and len(parsed) >= 2:
            break
    result = parsed if parsed and len(parsed) >= 2 else list(_FALLBACK_ALTERNATIVES)
    if use_cache:
        with _CACHE_LOCK:
            _CACHED = list(result)
    return result


def clear_cache() -> None:
    """Reset the parse cache. Test helper."""
    global _CACHED
    with _CACHE_LOCK:
        _CACHED = None
