"""Code-plugin registry — the typed complement to the filesystem-scan registries the repo already uses for
rubrics (JSON), roles (YAML), personas (MD) and primitives (JSON). A capability registers itself with
`@capability(kind, name)`; a scenario's declared names (`evidence_sources`, `renderer`, `solvers`, `rechecks`) resolve
here. Discovery is by importing the `providers` package (which fires the decorators) — no `entry_points`
machinery, no external config; adding a capability is dropping a decorated class in `scenarios/providers/`.
"""
from __future__ import annotations

from typing import Any, Callable

from ztare.scenarios.protocols import REQUIRED_METHODS

_KINDS: "tuple[str, ...]" = tuple(REQUIRED_METHODS)
_registry: "dict[str, dict[str, Any]]" = {k: {} for k in _KINDS}
_origins: "dict[str, dict[str, dict[str, str]]]" = {k: {} for k in _KINDS}
_builtin_registry: "dict[str, dict[str, Any]] | None" = None
_builtin_origins: "dict[str, dict[str, dict[str, str]]] | None" = None
_load_errors: "list[dict[str, str]]" = []
_discovered = False  # discovery is start-time + single-threaded + idempotent — no lock needed (Python's import
#                      machinery already serializes the actual import; the flag makes re-entry a no-op).


def _assert_shape(kind: str, name: str, inst: Any) -> None:
    """Structural conformance check at registration — a mis-shaped plug-in fails LOUD here, not deep in a run.
    We check required-method presence (not runtime_checkable isinstance, which is fussy about data members)."""
    if kind not in REQUIRED_METHODS:
        raise ValueError(f"unknown capability kind '{kind}' (known: {sorted(REQUIRED_METHODS)})")
    missing = [m for m in REQUIRED_METHODS[kind] if not callable(getattr(inst, m, None))]
    if missing:
        raise TypeError(f"capability {kind}:{name} ({type(inst).__name__}) is missing methods {missing}")
    if not str(getattr(inst, "name", "")):
        raise TypeError(f"capability {kind}:{name} ({type(inst).__name__}) must expose a non-empty `name`")


def _origin(obj: Any) -> dict[str, str]:
    import inspect

    cls = type(obj)
    try:
        source = inspect.getsourcefile(cls) or ""
    except (TypeError, OSError):
        source = ""
    return {
        "origin": f"{cls.__module__}.{cls.__qualname__}",
        "module": cls.__module__,
        "source": source,
    }


def register(kind: str, name: str, obj: Any) -> None:
    """Register an instantiated capability; reject ambiguous name collisions.

    Re-registering the same class origin is idempotent, which makes reload safe. A different provider claiming
    the same ``(kind, name)`` is refused so filesystem ordering can never silently change a scenario's wiring.
    """
    _assert_shape(kind, name, obj)
    incoming = _origin(obj)
    existing = _origins[kind].get(name)
    if existing is not None and existing.get("origin") != incoming["origin"]:
        raise ValueError(
            f"capability collision for {kind}:{name}: {existing.get('origin')} vs {incoming['origin']}"
        )
    _registry[kind][name] = obj
    _origins[kind][name] = incoming


def capability(kind: str, name: str) -> "Callable[[type], type]":
    """Class decorator: instantiate the decorated class (zero-arg) and register it under (kind, name)."""
    def _wrap(cls: type) -> type:
        register(kind, name, cls())
        return cls
    return _wrap


def plugin_dirs() -> "list[str]":
    """User capability-plugin directories — where a dropped `.py` (with @capability classes) is auto-loaded, so
    installing a code plugin is DROP A FILE, no editing `providers/__init__.py`. Sources: `$ZTARE_SCENARIO_PLUGINS`
    (os.pathsep-separated) + a repo-root `plugins/scenarios/` convention dir if it exists. Data plugins
    (scenarios/, rubrics/) are already filesystem registries and need no dir here."""
    import os

    dirs: "list[str]" = []
    for d in (os.environ.get("ZTARE_SCENARIO_PLUGINS", "") or "").split(os.pathsep):
        if d.strip():
            dirs.append(d.strip())
    try:
        from ztare.common.paths import REPO_ROOT
        conv = REPO_ROOT / "plugins" / "scenarios"
        if conv.is_dir():
            dirs.append(str(conv))
    except Exception:  # noqa: BLE001 — paths optional; env dirs still work
        pass
    return dirs


def _load_plugin_file(path: str) -> None:
    """Import a single plugin `.py` by file path so its @capability decorators fire. Isolated + guarded — a
    broken plugin is logged, never blocks the others or the kernel."""
    import hashlib
    import importlib.util
    import os

    try:
        path_key = hashlib.sha256(os.path.abspath(path).encode("utf-8")).hexdigest()[:12]
        mod_name = f"_ztare_scenario_plugin_{os.path.splitext(os.path.basename(path))[0]}_{path_key}"
        spec = importlib.util.spec_from_file_location(mod_name, path)
        if spec and spec.loader:
            spec.loader.exec_module(importlib.util.module_from_spec(spec))
    except Exception as exc:  # noqa: BLE001 — a broken user plugin must not brick discovery
        message = f"{type(exc).__name__}: {exc}"
        _load_errors.append({"path": path, "error": message})
        print(f"[scenario] plugin load warning ({path}): {message}", flush=True)


def _scan_external_plugins() -> None:
    import glob
    import os

    for directory in plugin_dirs():
        for path in sorted(glob.glob(os.path.join(directory, "*.py"))):
            if not os.path.basename(path).startswith("_"):
                _load_plugin_file(path)


def _discover() -> None:
    """Import the built-in providers package + any user plugin dirs once, so @capability decorators fire. A
    broken provider/plugin is logged but never blocks the others (a bad plug-in must not brick the kernel)."""
    global _builtin_origins, _builtin_registry, _discovered
    if _discovered:
        return
    _discovered = True  # set BEFORE imports so a @capability -> register() during discovery can't re-enter here
    try:
        import ztare.scenarios.providers  # noqa: F401 — importing fires the @capability decorators
    except Exception as exc:  # noqa: BLE001 — a broken provider must not block resolution of the others
        print(f"[scenario] provider discovery warning: {type(exc).__name__}: {exc}", flush=True)
    if _builtin_registry is None:
        _builtin_registry = {
            kind: {name: obj for name, obj in _registry[kind].items()
                   if _origins[kind][name].get("module", "").startswith("ztare.scenarios.providers.")}
            for kind in _KINDS
        }
        _builtin_origins = {
            kind: {name: dict(_origins[kind][name]) for name in _builtin_registry[kind]}
            for kind in _KINDS
        }
    _scan_external_plugins()


def reload() -> None:
    """Rebuild external discovery so added, changed, and deleted plugin files all take effect."""
    global _discovered
    _discover()
    for kind in _KINDS:
        _registry[kind] = dict((_builtin_registry or {}).get(kind, {}))
        _origins[kind] = {name: dict(details)
                          for name, details in ((_builtin_origins or {}).get(kind, {})).items()}
    _load_errors.clear()
    _discovered = True
    _scan_external_plugins()


def get(kind: str, name: str) -> Any:
    """Resolve (kind, name) to a registered capability, or None."""
    _discover()
    return _registry.get(kind, {}).get(name)


def available(kind: str) -> "list[str]":
    """Registered capability names for a kind (after discovery)."""
    _discover()
    return sorted(_registry.get(kind, {}))


def installed() -> "dict[str, list[str]]":
    """Every registered capability, by kind — the code-plugin half of the installed-plugins view (the UI/CLI
    pairs this with the scenario + rubric filesystem registries for the full picture)."""
    _discover()
    return {kind: sorted(_registry.get(kind, {})) for kind in _KINDS}


def descriptors() -> "dict[str, list[dict[str, str]]]":
    """Inspectable identity and source for every active capability."""
    _discover()
    return {
        kind: [
            {"name": name, **_origins[kind][name],
             "distribution": ("built_in" if _origins[kind][name].get("module", "").startswith(
                 "ztare.scenarios.providers.") else "external")}
            for name in sorted(_registry[kind])
        ]
        for kind in _KINDS
    }


def diagnostics() -> dict[str, Any]:
    """Health payload for CLI and Workbench plugin inspection."""
    _discover()
    return {"capabilities": descriptors(), "load_errors": [dict(row) for row in _load_errors]}
