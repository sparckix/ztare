"""Reference capability plug-ins. Importing this package fires the `@capability` decorators (registry
discovery). Add a new capability = drop a module here that decorates a zero-arg class with
`@capability(kind, name)` and import it below."""
from ztare.scenarios.providers import (  # noqa: F401 — register on import
    covenant_recompute,
    decision_brief_renderer,
    local_files,
    markdown_renderer,
    pm_templates,
    structured_files,
)

__all__ = ["local_files", "structured_files", "markdown_renderer", "pm_templates", "decision_brief_renderer",
           "covenant_recompute"]
