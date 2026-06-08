"""Thin CLI shim — the solver CORE was extracted to src/ztare/leanmill/solver/solver_core.py
(task #42). This control-plane entrypoint keeps ONLY the CLI; ALL solver logic lives in src/ now,
so src/ no longer depends on a control SCRIPT (the autoformalizer importlib hack is gone)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "src"))
from ztare.leanmill.solver.solver_core import *  # noqa: F401,F403,E402
from ztare.leanmill.solver.solver_core import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
