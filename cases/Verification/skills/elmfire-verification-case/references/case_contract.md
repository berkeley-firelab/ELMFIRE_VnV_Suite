# Case contract and file layout

Every case includes the identity, runner, scripts, and six report source files
shown below. Add only the optional data and artifact directories meaningful to
the case.

```text
CASE##_PURPOSE/
├── case.yaml
├── case.json                  # when required by case tooling
├── elmfire.data.in
├── run_case.sh
├── compile_case.sh
├── data/
│   ├── inputs/
│   ├── misc/
│   ├── weather/
│   └── observations/
├── scripts/
│   ├── preprocess.py
│   ├── postprocess.py
│   └── metrics_to_macro.py
├── outputs/metrics.json
├── figures/
├── logs/
└── report/
    ├── case_report.tex
    ├── case_metadata.tex
    ├── case_body.tex
    ├── case_macros.tex
    ├── technical_macros.tex
    └── metrics_macros.tex
```

`preprocess.py` may be named `generate_inputs.py` when that is clearer. A capability-only case may omit `elmfire.data.in` or the ELMFIRE stage when the omission is explicit in metadata and the verification contract.

## Metadata

`case.yaml` is the discovery-facing description. Keep paths relative to the case root and include the canonical `case_id`, descriptive title, ELMFIRE configuration, variants, expected figures, and metrics path as applicable. `case.json`, when present, records the same identity and machine-readable verification contract. Conflicting metadata is an error.

For a case that executes ELMFIRE, include the compact `namelist_contract`
defined in `docs/namelist-versioning.md`. It contains only exact,
machine-checkable values essential to the test. The report remains the sole
home for scientific intent and reasoning. Do not add `scientific_intent.yaml`
unless the contract later becomes too large for `case.yaml` or must be reused
independently of case metadata.

## Input generation

Generate deterministic rasters and namelists locally. Explain grid origin, resolution, row direction, geotransform, projection, units, nodata handling, ignition placement, and buffer cells wherever applicable. Record enough metadata to reconstruct the run.

## Postprocessing

Read only this case's outputs. Distinguish missing, empty, malformed, and valid outputs. Compute named metrics, compare them with explicit tolerances, write `outputs/metrics.json`, generate only case-local figures, and emit report macros mechanically.

## Runner

Prefer a short, linear runner:

```bash
#!/usr/bin/env bash
set -euo pipefail

CASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python3}"
ELMFIRE_BIN="${ELMFIRE_BIN:-elmfire}"

mkdir -p "$CASE_DIR/outputs" "$CASE_DIR/figures" "$CASE_DIR/logs"
"$PYTHON_BIN" "$CASE_DIR/scripts/preprocess.py"
(cd "$CASE_DIR" && "$ELMFIRE_BIN" elmfire.data.in > logs/elmfire.log 2>&1)
"$PYTHON_BIN" "$CASE_DIR/scripts/postprocess.py"
"$CASE_DIR/compile_case.sh"
```

Add explicit variant invocations when the contract requires them. Finish by invoking `compile_case.sh`. The runner coordinates; scientific logic belongs in readable Python scripts and ELMFIRE configuration.
