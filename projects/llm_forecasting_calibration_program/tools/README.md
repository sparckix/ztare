# Forecasting Program Tools

Project-local tools for the LLM forecasting calibration program.

Use this folder for GP-245 / forecasting-paper experiment packets, reports,
DB hygiene checks, and pilot-specific runners. Keep reusable forecast-pool
infrastructure in `scripts/public/control/forecast/`.

Preferred invocation is through the stable CLI surface:

```bash
PYTHONPATH=src ./venv/bin/python -m ztare.cli forecast <verb> [args...]
```

The CLI keeps command names stable while allowing the implementation to live
with the project. Tools should write experiment artifacts under the relevant
project workspace unless an explicit `--out-dir` is supplied. Tools should not
mutate the calibration DB unless their help text says so.
