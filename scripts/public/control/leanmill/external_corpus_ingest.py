"""External corpus ingest — plugin-driven, config-loadable, project-agnostic.

Code is generic. Per-corpus knowledge (URL, target dir, mandates,
anti-laundering rules, install gates) lives in
`analytics/.../factory_dashboard_data/corpus_plugins/<plugin_id>.json`
descriptor files. The CLI loads a plugin by id and applies its descriptor;
this script contains zero hardcoded references to specific projects or
substrates.

Plugin descriptor schema: `leanmill-corpus-plugin-v1`. Adding a new
ingestable corpus = dropping a JSON descriptor in the corpus_plugins
directory. No code change required.

CLI verbs (registered via `ztare leanmill corpus`):
  list                          — show registered plugins
  describe <plugin_id>          — show full descriptor
  install <plugin_id>           — fetch source + register mandates as draft
  status                        — show install state of every plugin
  uninstall <plugin_id>         — remove mandates (does not delete fetched files)

Each plugin descriptor declares its own install gates (e.g.
`do_not_install_before`, `operator_approval_required_to_activate`); the
ingester honors them but never enforces a hardcoded one.
"""
from __future__ import annotations
import argparse
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
DASH = REPO / "analytics" / "public" / "leanmill" / "dashboard_data"
PLUGINS_DIR = DASH / "corpus_plugins"
MANDATE_REGISTRY = DASH / "corpus_mandates.json"


def _read_json(p: Path) -> dict:
    return json.loads(p.read_text()) if p.exists() else {}


def list_plugins() -> list[dict]:
    if not PLUGINS_DIR.exists():
        return []
    out = []
    for f in sorted(PLUGINS_DIR.glob("*.json")):
        try:
            d = _read_json(f)
            out.append({
                "plugin_id": d.get("plugin_id") or f.stem,
                "display_name": d.get("display_name") or f.stem,
                "summary": d.get("summary") or "",
                "descriptor_path": str(f.relative_to(REPO)),
            })
        except Exception as exc:
            out.append({"plugin_id": f.stem, "error": repr(exc)})
    return out


def describe_plugin(plugin_id: str) -> dict | None:
    p = PLUGINS_DIR / f"{plugin_id}.json"
    return _read_json(p) if p.exists() else None


def _registered_mandate_ids() -> set[str]:
    reg = _read_json(MANDATE_REGISTRY)
    return {m.get("mandate_id") for m in (reg.get("mandates") or [])}


def _fetch_source(target: Path, src: dict, *, force: bool) -> int:
    """Generic source fetcher. Supported source.kind values:
        git           — git clone (url, depth)
        local_path    — no fetch; expects target to already exist
    """
    target.parent.mkdir(parents=True, exist_ok=True)
    kind = src.get("kind")
    if kind == "git":
        url = src.get("url")
        if not url:
            print("[ingest] source.kind=git requires source.url", file=sys.stderr); return 3
        if target.exists() and not force:
            print(f"[ingest] {target} exists — skipping clone (use --force to re-clone)"); return 0
        if target.exists() and force:
            shutil.rmtree(target)
        cmd = ["git", "clone"]
        if src.get("depth"): cmd.extend(["--depth", str(src["depth"])])
        cmd.extend([url, str(target)])
        print(f"[ingest] $ {' '.join(cmd)}")
        r = subprocess.run(cmd, check=False)
        return 0 if r.returncode == 0 else 4
    if kind == "local_path":
        if not target.exists():
            print(f"[ingest] local_path expected at {target}; not found", file=sys.stderr); return 5
        return 0
    print(f"[ingest] unsupported source.kind: {kind!r}", file=sys.stderr); return 6


def install_plugin(plugin_id: str, *, force: bool = False) -> int:
    desc = describe_plugin(plugin_id)
    if desc is None:
        print(f"[ingest] plugin not found: {plugin_id}", file=sys.stderr); return 2
    print(json.dumps({"installing": plugin_id, "display_name": desc.get("display_name")}, indent=2))
    target = REPO / (desc.get("target_dir") or f"projects/{plugin_id}")
    rc = _fetch_source(target, desc.get("source") or {}, force=force)
    if rc != 0: return rc
    if not MANDATE_REGISTRY.exists():
        print(f"[ingest] mandate registry missing at {MANDATE_REGISTRY}", file=sys.stderr); return 7
    reg = _read_json(MANDATE_REGISTRY)
    existing = _registered_mandate_ids()
    initial_status = (desc.get("gates") or {}).get("install_status_initial") or "draft"
    added = 0
    for m in desc.get("mandates") or []:
        mid = m.get("mandate_id")
        if not mid:
            print("[ingest] skipping mandate without mandate_id", file=sys.stderr); continue
        if mid in existing and not force:
            print(f"[ingest] mandate already registered: {mid} (skip)"); continue
        if mid in existing and force:
            reg["mandates"] = [x for x in reg["mandates"] if x.get("mandate_id") != mid]
        entry = {
            "mandate_id": mid,
            "status": initial_status,
            "purpose": m.get("purpose") or "",
            "corpus_path": str(target.relative_to(REPO)),
            "lane_eligibility": m.get("lane_eligibility") or [],
            "credit_lanes_allowed": m.get("credit_lanes_allowed") or [],
            "anti_laundering_rule": m.get("anti_laundering_rule") or "",
            "row_count": m.get("estimated_target_count"),
            "installed_by_plugin": plugin_id,
            "installed_at": datetime.now(timezone.utc).isoformat(),
        }
        reg.setdefault("mandates", []).append(entry)
        added += 1
        print(f"[ingest] registered mandate: {mid}  status={initial_status}")
    MANDATE_REGISTRY.write_text(json.dumps(reg, indent=2) + "\n")
    print(f"\n[ingest] DONE — {added} mandates added under plugin {plugin_id}")
    gates = desc.get("gates") or {}
    if gates.get("operator_approval_required_to_activate"):
        print(f"[ingest] operator must flip status `{initial_status}` → `active` in corpus_mandates.json before any worker consumes the mandate.")
    if gates.get("do_not_install_before"):
        print(f"[ingest] advisory gate: {gates['do_not_install_before']}")
    return 0


def uninstall_plugin(plugin_id: str) -> int:
    desc = describe_plugin(plugin_id)
    if desc is None:
        print(f"[ingest] plugin not found: {plugin_id}", file=sys.stderr); return 2
    mandate_ids = {m.get("mandate_id") for m in (desc.get("mandates") or []) if m.get("mandate_id")}
    reg = _read_json(MANDATE_REGISTRY)
    before = len(reg.get("mandates") or [])
    reg["mandates"] = [m for m in (reg.get("mandates") or []) if m.get("mandate_id") not in mandate_ids]
    MANDATE_REGISTRY.write_text(json.dumps(reg, indent=2) + "\n")
    print(f"[ingest] uninstalled {plugin_id}: removed {before - len(reg['mandates'])} mandates (fetched files at {desc.get('target_dir')} left intact)")
    return 0


def show_status() -> int:
    plugins = list_plugins()
    reg = _read_json(MANDATE_REGISTRY)
    registered = {m.get("mandate_id"): m for m in (reg.get("mandates") or [])}
    print(f"{'plugin_id':<24} {'state':<22} {'display_name'}")
    print("-" * 96)
    for p in plugins:
        desc = describe_plugin(p["plugin_id"]) or {}
        ids = [m.get("mandate_id") for m in (desc.get("mandates") or [])]
        installed = sum(1 for mid in ids if mid in registered)
        active = sum(1 for mid in ids if registered.get(mid, {}).get("status") == "active")
        state = (
            f"active {active}/{len(ids)}" if active else
            f"installed {installed}/{len(ids)}" if installed else
            "uninstalled"
        )
        print(f"{p['plugin_id']:<24} {state:<22} {p['display_name']}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd")
    sub.add_parser("list")
    p_desc = sub.add_parser("describe"); p_desc.add_argument("plugin_id")
    p_inst = sub.add_parser("install"); p_inst.add_argument("plugin_id"); p_inst.add_argument("--force", action="store_true")
    p_uni = sub.add_parser("uninstall"); p_uni.add_argument("plugin_id")
    sub.add_parser("status")
    args = ap.parse_args()
    if args.cmd == "list":
        for p in list_plugins():
            print(f"  {p['plugin_id']:<24} {p['display_name']}")
            if p.get("summary"): print(f"    {p['summary'][:140]}")
        return 0
    if args.cmd == "describe":
        d = describe_plugin(args.plugin_id)
        if d is None:
            print(f"plugin not found: {args.plugin_id}", file=sys.stderr); return 2
        print(json.dumps(d, indent=2)); return 0
    if args.cmd == "install": return install_plugin(args.plugin_id, force=args.force)
    if args.cmd == "uninstall": return uninstall_plugin(args.plugin_id)
    if args.cmd == "status": return show_status()
    ap.print_help(); return 1


if __name__ == "__main__":
    sys.exit(main())
