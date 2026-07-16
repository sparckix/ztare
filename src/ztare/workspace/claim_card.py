from __future__ import annotations

import argparse
import hashlib
import html
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ztare.common.paths import REPO_ROOT
from ztare.workspace.project_file import validate_project_slug


SCHEMA = "ztare-claim-card-v1"
CLAIM_CARD_RECEIPT_SCHEMA = "ztare-forensic-workbench-claim-card-receipt-v1"


def repo_root() -> Path:
    return REPO_ROOT


def read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise SystemExit(f"not a JSON object: {path}")
    return payload


def rel_path(path: str, root: Path) -> str:
    raw = Path(path)
    try:
        return raw.resolve().relative_to(root.resolve()).as_posix()
    except (OSError, ValueError):
        return path


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def stable_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def with_card_hash(card: dict[str, Any]) -> dict[str, Any]:
    out = json.loads(json.dumps(card, sort_keys=True))
    out.setdefault("provenance", {}).pop("card_hash", None)
    card_hash = hashlib.sha256(stable_json(out).encode("utf-8")).hexdigest()
    out["provenance"]["card_hash"] = card_hash
    return out


def git_commit(root: Path) -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=root,
            check=False,
            capture_output=True,
            text=True,
        ).stdout.strip()
    except OSError:
        return ""


def contract_path(project: str, root: Path) -> Path:
    return root / "projects" / validate_project_slug(project) / "synthesis" / "report_support_contract.json"


def evidence_hashes(paths: list[Any], root: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in paths:
        rel = rel_path(str(item), root)
        path = root / rel
        exists = path.is_file()
        rows.append(
            {
                "path": rel,
                "exists": exists,
                "sha256": sha256_file(path) if exists else "",
            }
        )
    return rows


def text_of(value: Any) -> str:
    if isinstance(value, dict):
        for key in ("claim", "reason", "why", "why_unsupported", "command", "label"):
            if str(value.get(key) or "").strip():
                return str(value[key])
        return json.dumps(value, sort_keys=True)
    return str(value or "")


def build_card(project: str, root: Path) -> dict[str, Any]:
    project = validate_project_slug(project)
    contract = read_json(contract_path(project, root))
    hardest = contract.get("hardest_conclusion") if isinstance(contract.get("hardest_conclusion"), dict) else {}
    strength = contract.get("claim_strength") if isinstance(contract.get("claim_strength"), dict) else {}
    unsupported = contract.get("unsupported_or_unresolved") if isinstance(contract.get("unsupported_or_unresolved"), list) else []
    blockers = contract.get("blockers") if isinstance(contract.get("blockers"), list) else []
    next_actions = contract.get("next_actions") if isinstance(contract.get("next_actions"), list) else []
    supported = contract.get("supported_claims") if isinstance(contract.get("supported_claims"), list) else []
    evidence = evidence_hashes(contract.get("source_artifact_paths") or [], root)
    confirmation = strength.get("confirmation_status") if isinstance(strength.get("confirmation_status"), dict) else {}
    lines = [
        {
            "tier": "model_assisted",
            "check": "synth supported claim",
            "result": text_of(row),
            "evidence_refs": [item["path"] for item in evidence],
            "evidence_hashes": evidence,
        }
        for row in supported[:8]
    ]
    lines.append(
        {
            "tier": "deterministic",
            "check": "evidence hash integrity",
            "result": "all listed evidence files are present" if all(row["exists"] for row in evidence) else "some listed evidence files are missing",
            "evidence_refs": [item["path"] for item in evidence],
            "evidence_hashes": evidence,
        }
    )
    card = {
        "schema": SCHEMA,
        "project": project,
        "bounded_claim": str(hardest.get("claim") or ""),
        "boundary": str(strength.get("epistemic_note") or confirmation.get("why") or ""),
        "verdict": str(contract.get("status") or ""),
        "weakest_link": text_of(blockers[0]) if blockers else text_of(unsupported[0]) if unsupported else "",
        "next_falsifier": text_of(next_actions[0]) if next_actions else "",
        "lines": lines,
        "non_claims": [text_of(row) for row in unsupported[:12] if text_of(row)],
        "reproduce": {
            "deterministic": f"ztare card verify --path projects/{project}/synthesis/claim_card.json",
            "full": f"ztare synth --project {project} --contract-only",
        },
        "provenance": {
            "ztare_version": "",
            "git_commit": git_commit(root),
            "created_by": "ztare card build",
            "contract": rel_path(str(contract_path(project, root)), root),
        },
    }
    return with_card_hash(card)


def render_markdown(card: dict[str, Any]) -> str:
    evidence = (card.get("lines") or [{}])[-1].get("evidence_hashes") or []
    parts = [
        f"# Claim Card: {card.get('project')}",
        "",
        f"**Bounded claim.** {card.get('bounded_claim') or 'Not recorded.'}",
        "",
        f"**Verdict.** {card.get('verdict') or 'Not recorded.'}",
        "",
        f"**Boundary.** {card.get('boundary') or 'Not recorded.'}",
        "",
        f"**Weakest link.** {card.get('weakest_link') or 'Not recorded.'}",
        "",
        f"**Next falsifier.** {card.get('next_falsifier') or 'Not recorded.'}",
        "",
        "## Evidence Files",
        "",
        *[f"- `{row['path']}` — {'present' if row['exists'] else 'missing'} `{row['sha256'][:12]}`" for row in evidence],
        "",
        "## Non-Claims",
        "",
        *[f"- {item}" for item in card.get("non_claims") or ["None recorded."]],
        "",
        "## Verify",
        "",
        f"```bash\n{card['reproduce']['deterministic']}\n```",
    ]
    return "\n".join(parts).rstrip() + "\n"


def render_html(card: dict[str, Any]) -> str:
    card_json = stable_json(card)
    return f"""<!doctype html>
<meta charset="utf-8">
<title>ZTARE Claim Card</title>
<style>
body{{font:16px/1.5 system-ui,sans-serif;margin:2rem;max-width:980px;color:#1d2523}}
.status{{padding:.35rem .6rem;border:1px solid #9db7aa;display:inline-block}}
pre{{white-space:pre-wrap;background:#f6f8f7;padding:1rem;overflow:auto}}
</style>
<h1>Claim Card: {html.escape(str(card.get('project') or 'project'))}</h1>
<p class="status" id="verify">Verifying embedded card hash...</p>
<h2>Bounded claim</h2><p>{html.escape(str(card.get('bounded_claim') or 'Not recorded.'))}</p>
<h2>Boundary</h2><p>{html.escape(str(card.get('boundary') or 'Not recorded.'))}</p>
<h2>Weakest link</h2><p>{html.escape(str(card.get('weakest_link') or 'Not recorded.'))}</p>
<h2>Next falsifier</h2><p>{html.escape(str(card.get('next_falsifier') or 'Not recorded.'))}</p>
<h2>Card JSON</h2><pre id="card"></pre>
<script type="application/json" id="payload">{html.escape(card_json)}</script>
<script>
const text = document.getElementById("payload").textContent;
const card = JSON.parse(text);
document.getElementById("card").textContent = JSON.stringify(card, null, 2);
function canonical(value) {{
  if (Array.isArray(value)) return value.map(canonical);
  if (value && typeof value === "object") {{
    return Object.fromEntries(Object.keys(value).sort().map(key => [key, canonical(value[key])]));
  }}
  return value;
}}
const clone = JSON.parse(JSON.stringify(card));
const expected = clone.provenance.card_hash;
delete clone.provenance.card_hash;
crypto.subtle.digest("SHA-256", new TextEncoder().encode(JSON.stringify(canonical(clone)))).then(buf => {{
  const actual = Array.from(new Uint8Array(buf)).map(b => b.toString(16).padStart(2, "0")).join("");
  document.getElementById("verify").textContent = actual === expected ? "Embedded card hash verified." : "Embedded card hash mismatch.";
}});
</script>
"""


def output_paths(project: str, root: Path) -> dict[str, Path]:
    base = root / "projects" / validate_project_slug(project) / "synthesis"
    return {
        "json": base / "claim_card.json",
        "md": base / "claim_card.md",
        "html": base / "claim_card.html",
    }


def write_card(card: dict[str, Any], fmt: str, out: Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    if fmt == "json":
        out.write_text(json.dumps(card, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    elif fmt == "md":
        out.write_text(render_markdown(card), encoding="utf-8")
    elif fmt == "html":
        out.write_text(render_html(card), encoding="utf-8")
    else:
        raise SystemExit(f"unsupported format: {fmt}")


def verify_card(path: Path, root: Path) -> dict[str, Any]:
    card = read_json(path)
    expected = str((card.get("provenance") or {}).get("card_hash") or "")
    actual_card = with_card_hash(card)
    card_hash_ok = expected == actual_card["provenance"]["card_hash"]
    evidence_rows = []
    for line in card.get("lines") or []:
        for row in line.get("evidence_hashes") or []:
            rel = str(row.get("path") or "")
            if not rel or rel in {item["path"] for item in evidence_rows}:
                continue
            local = root / rel
            actual = sha256_file(local) if local.is_file() else ""
            evidence_rows.append(
                {
                    "path": rel,
                    "expected": str(row.get("sha256") or ""),
                    "actual": actual,
                    "ok": bool(actual) and actual == str(row.get("sha256") or ""),
                }
            )
    return {
        "ok": card.get("schema") == SCHEMA and card_hash_ok and all(row["ok"] for row in evidence_rows),
        "schema_ok": card.get("schema") == SCHEMA,
        "card_hash_ok": card_hash_ok,
        "evidence": evidence_rows,
    }


def build_recorded_card(
    project: str,
    root: Path,
    *,
    rubric: str = "",
    intake: str = "",
) -> dict[str, Any]:
    project = validate_project_slug(project)
    card = build_card(project, root)
    paths = output_paths(project, root)
    for fmt, path in paths.items():
        write_card(card, fmt, path)
    verification = verify_card(paths["json"], root)
    workspace = root / "projects" / project / "workspace"
    workspace.mkdir(parents=True, exist_ok=True)
    ledger_path = workspace / "forensic_workbench_claim_cards.jsonl"
    latest_path = workspace / "forensic_workbench_latest_claim_card.json"
    written = [rel_path(str(paths[fmt]), root) for fmt in ("json", "md", "html")]
    receipt = {
        "schema": CLAIM_CARD_RECEIPT_SCHEMA,
        "kind": "claim_card",
        "project": project,
        "rubric": rubric or project,
        "intake": intake,
        "applied_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "status": "accepted" if verification.get("ok") else "attention",
        "summary": (
            "Built portable claim card and verified evidence hashes."
            if verification.get("ok")
            else "Built portable claim card, but verification needs attention."
        ),
        "card_hash": str((card.get("provenance") or {}).get("card_hash") or ""),
        "json_path": written[0],
        "markdown_path": written[1],
        "html_path": written[2],
        "receipt_path": rel_path(str(ledger_path), root),
        "latest_path": rel_path(str(latest_path), root),
        "verification_ok": bool(verification.get("ok")),
        "evidence_count": len(verification.get("evidence") or []),
    }
    with ledger_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(receipt, sort_keys=True) + "\n")
    latest_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_paths = [*written, receipt["receipt_path"], receipt["latest_path"]]
    return {
        "ok": bool(verification.get("ok")),
        "accepted": bool(verification.get("ok")),
        "schema": CLAIM_CARD_RECEIPT_SCHEMA,
        "project": project,
        "rubric": rubric or project,
        "intake": intake,
        "card_hash": receipt["card_hash"],
        "json_path": receipt["json_path"],
        "markdown_path": receipt["markdown_path"],
        "html_path": receipt["html_path"],
        "preview_path": receipt["html_path"],
        "receipt_path": receipt["receipt_path"],
        "latest_path": receipt["latest_path"],
        "written": written,
        "write_paths": write_paths,
        "verification": verification,
        "receipt": receipt,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build or verify portable ZTARE claim cards.")
    sub = parser.add_subparsers(dest="cmd", required=True)
    build = sub.add_parser("build", help="project synth contract into a portable card")
    build.add_argument("--project", required=True)
    build.add_argument("--format", choices=["json", "md", "html", "all"], default="json")
    build.add_argument("--out")
    build.add_argument("--repo", type=Path, default=REPO_ROOT)
    build.add_argument("--rubric", default="")
    build.add_argument("--intake", default="")
    build.add_argument("--record", action="store_true", help="Write all formats and a Workbench receipt.")
    verify = sub.add_parser("verify", help="verify a claim-card JSON file and evidence hashes")
    verify.add_argument("--path", required=True)
    verify.add_argument("--repo", type=Path, default=REPO_ROOT)
    open_cmd = sub.add_parser("open", help="build HTML and print its path")
    open_cmd.add_argument("--project", required=True)
    open_cmd.add_argument("--repo", type=Path, default=REPO_ROOT)
    args = parser.parse_args(argv)
    root = args.repo
    if args.cmd in {"build", "open"}:
        if args.cmd == "build" and args.record:
            print(json.dumps(build_recorded_card(
                args.project,
                root,
                rubric=args.rubric,
                intake=args.intake,
            ), indent=2, sort_keys=True))
            return 0
        card = build_card(args.project, root)
        formats = ["html"] if args.cmd == "open" else ["json", "md", "html"] if args.format == "all" else [args.format]
        paths = output_paths(args.project, root)
        written = []
        for fmt in formats:
            out = Path(args.out) if args.out and len(formats) == 1 else paths[fmt]
            write_card(card, fmt, out)
            written.append(str(out))
        print(json.dumps({"ok": True, "written": written, "card_hash": card["provenance"]["card_hash"]}, indent=2))
        return 0
    result = verify_card(Path(args.path), root)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
