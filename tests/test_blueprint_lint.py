"""Blueprint linter (§4.2a REPORTER): each rule fires on its minimal bad blueprint; a well-formed blueprint
(the real ftap_hard structure: ## Domain + ## Target + ## Idea, no ## Lemmas) is CLEAN; cues are section-scoped
(no "unique" flag in ## Idea, no define-verb flag outside ## Lemmas). Runnable: `python tests/test_blueprint_lint.py`.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
from ztare.leanmill.blueprint_lint import lint_blueprint  # noqa: E402


def _rules(text):
    return [w["rule"] for w in lint_blueprint(text)]


def test_each_rule_fires():
    # a. missing_domain + b. missing_target
    assert "missing_domain" in _rules("# T\n\n## Target\nSomething provable.\n")
    assert "missing_target" in _rules("# T\n\n## Domain\nstrategy\n")

    # c. definition_bullet_in_lemmas — a definition posed as a lemma (the tautology trap)
    ws = lint_blueprint("## Domain\nd\n## Target\nt\n## Lemmas\n"
                        "- Introduce the increasing-differences predicate on the objective.\n"
                        "- **(named)** Define the round-trip return.\n")
    defs = [w for w in ws if w["rule"] == "definition_bullet_in_lemmas"]
    assert len(defs) == 2, ws
    assert defs[0]["line"] == 6 and defs[1]["line"] == 7, defs   # line numbers point at the bullets

    # d. define_and_show_bullet — def + property fused in one bullet (must be split)
    ws = lint_blueprint("## Domain\nd\n## Target\nt\n## Lemmas\n"
                        "- **(k_mono)** We define the swap rule and show it never decreases k.\n")
    assert [w["rule"] for w in ws] == ["define_and_show_bullet"], ws

    # e. ambition_restriction_cue — formalization choices typed into ## Target (the Topkis trap)
    ws = lint_blueprint("## Domain\nd\n## Target\nOver a linearly ordered type of choices,\n"
                        "the unique maximizer rises with the parameter.\n")
    cues = [w for w in ws if w["rule"] == "ambition_restriction_cue"]
    assert len(cues) == 2 and cues[0]["line"] == 4 and cues[1]["line"] == 5, ws

    # f. fixed_tiny_instance — a concrete tiny carrier as THE type of the claim
    assert "fixed_tiny_instance" in _rules("## Domain\nd\n## Target\nOver ZMod 2, xor is involutive.\n")
    assert "fixed_tiny_instance" in _rules("## Domain\nd\n## Target\nFor all f : Fin 3 → Bool, something.\n")
    # `Fin 25` / a parameterized `Fin n` are NOT tiny fixed instances
    assert "fixed_tiny_instance" not in _rules("## Domain\nd\n## Target\nOver Fin 25 and Fin n, something.\n")
    print("OK: each rule fires on its minimal bad blueprint")


def test_clean_blueprint_and_section_scoping():
    # the real ftap_hard shape: Domain + Theory file + Target + Idea, no Lemmas → ZERO warnings
    clean = (
        "# Finite FTAP — HARD direction\n\nPreamble prose.\n\n"
        "## Domain\nformalization-nonmath\n\n"
        "## Theory file\nftap_hard_theory.lean\n\nNo bespoke definition is required.\n\n"
        "## Target\nIf the market admits no arbitrage, there exists a state-price vector q with q(s) > 0\n"
        "for every state s such that p(i) = sum_s q(s)*D(i, s) for all assets i.\n\n"
        "## Idea\nA finite separating-hyperplane / Farkas argument yields a strictly positive functional.\n"
    )
    assert lint_blueprint(clean) == [], lint_blueprint(clean)

    # ambition cues are ## Target-scoped: "the unique"/"exactly one" in ## Idea must NOT flag
    idea_only = ("## Domain\nd\n## Target\nA fully general claim.\n"
                 "## Idea\nEvery secret pins exactly one polynomial — the unique interpolant does the work.\n")
    assert "ambition_restriction_cue" not in _rules(idea_only), lint_blueprint(idea_only)

    # tiny instances are ## Target-scoped too (## Idea may discuss toys)
    assert "fixed_tiny_instance" not in _rules("## Domain\nd\n## Target\nGeneral n.\n## Idea\nTry ZMod 2 first.\n")

    # define-verbs outside ## Lemmas (Theory file / Target prose) must NOT flag
    define_elsewhere = ("## Domain\nd\n"
                        "## Theory file\nt.lean\n- Introduce the strong set order (Veinott) on sets.\n"
                        "## Target\nDefine the VCG mechanism and prove it is dominant-strategy incentive compatible.\n")
    for r in _rules(define_elsewhere):
        assert r not in ("definition_bullet_in_lemmas", "define_and_show_bullet"), lint_blueprint(define_elsewhere)
    print("OK: clean blueprint zero warnings; cues correctly section-scoped")


if __name__ == "__main__":
    test_each_rule_fires()
    test_clean_blueprint_and_section_scoping()
