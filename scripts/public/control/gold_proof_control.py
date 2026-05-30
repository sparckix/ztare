#!/usr/bin/env python3
"""gold_proof_control.py — THE decisive control the bare-file and
synthetic validations lacked: feed the fixed gate a real corpus row's
OWN ORIGINAL Mathlib proof (guaranteed correct) and check it returns
`closure`.

  closure            -> the fixed gate is SOUND on a real hard proof in
                        true module context ⇒ the rerun's 0-closures is
                        GENUINE (prior light 27/30 inflated/easier) —
                        EXPECTED, not a gate artifact.
  open / unverified  -> the gate FALSE-NEGATIVES a known-correct proof
                        ⇒ 0-closures is (partly) another gate artifact;
                        do NOT trust the rerun; fix the gate.

Row: MCB_000_hofer (Mathlib `hofer`, the Hofer lemma). Gold proof
extracted from the sandbox's own Mathlib source. Writes a full
0-asymmetry record via the gate ledger like any other attempt.

Machine-safe with no other LOCAL heavy-Lean proc (rerun1 is on VPS).
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(Path(__file__).parent))

_DECL = re.compile(r"^(theorem|lemma|def|abbrev|instance|@\[|/--|/-|"
                    r"end |namespace |section |open |variable|"
                    r"noncomputable |private |protected |public )")


def extract_mathlib_block(src_path: Path, name: str) -> str:
    """Grab `theorem <name> ... := <proof>` whole block: from the line
    that declares it to the next top-level declaration / EOF."""
    lines = src_path.read_text(errors="ignore").splitlines()
    start = None
    for i, ln in enumerate(lines):
        if re.match(rf"^(theorem|lemma)\s+{re.escape(name)}\b", ln):
            start = i
            break
    if start is None:
        raise SystemExit(f"FAIL-LOUD: `{name}` not found in {src_path}")
    end = len(lines)
    for j in range(start + 1, len(lines)):
        if _DECL.match(lines[j]) and lines[j][0] not in " \t":
            end = j
            break
    return "\n".join(lines[start:end]).rstrip() + "\n"


def main() -> int:
    import authoritative_axioms as _AX
    import coherent_rung1 as cr
    from src.ztare.formal.lean_persistent import PersistentLean

    row = cr.build_corpus()[0]            # MCB_000_hofer
    assert "hofer" in row["target_name"], row
    short = row["target_name"].split(".")[-1]
    sorried = Path(row["sorried_file"]).read_text(errors="ignore")

    src = (cr.SB / ".lake/packages/mathlib/Mathlib/Analysis/Hofer.lean")
    gold_block = extract_mathlib_block(src, short)
    print(f"[gpc] gold `{short}` block: {gold_block.count(chr(10))} "
          f"lines, {len(gold_block)} chars", flush=True)

    # replace the sorried theorem block with Mathlib's full block.
    # sorried file = leak-tight import context + `theorem hofer ... :=
    # by sorry`. Swap that whole decl for the real one.
    m = re.search(rf"(?m)^(theorem|lemma)\s+{re.escape(short)}\b",
                  sorried)
    if not m:
        raise SystemExit("FAIL-LOUD: target decl not in sorried file")
    head = sorried[:m.start()]
    rest = sorried[m.start():]
    # cut the sorried decl at the next top-level decl or EOF
    nxt = None
    for mm in re.finditer(r"(?m)^(theorem|lemma|def|end |namespace |"
                          r"section |@\[|/--)", rest[1:]):
        nxt = mm.start() + 1
        break
    tail = rest[nxt:] if nxt else ""
    gold_file = head + gold_block + ("\n" + tail if tail.strip() else "")
    Path("/tmp/rung1/_gold_hofer.lean").write_text(gold_file)
    print(f"[gpc] composed gold file ({len(gold_file)} chars); warming "
          f"REPL on {cr.SB.name} ...", flush=True)

    L = PersistentLean(cr.SB)
    L.start_tactic_proof("theorem _w : True := by sorry", 180)
    prov = _AX.govern(L, gold_file, row["target_line"],
                      row["target_name"], 300, persist=False)
    L.close()

    print("\n=== GOLD-PROOF CONTROL ===")
    print(f"verdict = {prov.get('verdict')}")
    print(f"reason  = {prov.get('reason')}")
    print(f"axioms  = {prov.get('axioms_deps')}")
    if prov.get("verdict") == "closure":
        print("RESULT: PASS — the fixed gate CLOSES Mathlib's own "
              "correct proof of a real hard row in true module "
              "context. ⇒ the gate is SOUND on real hard proofs; the "
              "rerun's 0-closures is GENUINE (codex genuinely not "
              "closing these / prior 27/30 inflated-or-easier), "
              "EXPECTED — not a gate false-negative.")
        return 0
    print("RESULT: FAIL — the fixed gate did NOT close a KNOWN-CORRECT "
          "proof (Mathlib's own). The gate still FALSE-NEGATIVES on "
          "real hard proofs ⇒ the rerun's 0-closures is (partly) a "
          "gate artifact; do NOT trust it. Inspect the gate ledger "
          "(/tmp/rung1/gate_debug) entry for this attempt — the "
          "evidence (phaseA_errors / phaseB_new_errs / axioms_raw) "
          "pinpoints the failing stage.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
