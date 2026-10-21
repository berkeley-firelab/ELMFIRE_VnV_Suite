# GOFER landscape-scale validation

One validation case per fire of the GOFER dataset (28 California fires,
2019–2021). Each case compares ELMFIRE fire arrival time with the arrival time
derived from the GOFER-Combined hourly perimeters (Liu et al., 2024,
doi:10.5194/essd-16-1395-2024; data doi:10.5281/zenodo.8327264) and follows
the report structure of `../landscape_scale/` and
`../skills/elmfire-validation-case/`.

## Case layout

```text
<fire_id>/                     e.g. kincade_2019
├── case.yaml                  discovery metadata and namelist invariants
├── elmfire.data.in            current ELMFIRE configuration (ELMFIRE 1.1)
├── run_case.sh                preprocess → ELMFIRE → postprocess → report
├── compile_case.sh            metrics → LaTeX macros → case_report.pdf
├── data/
│   ├── source_manifest.json   provenance, ignitions, timing, GOFER area series
│   └── data_paths.json        where provided inputs/observation/results are
├── scripts/                   preprocess.py, postprocess.py, metrics_to_macro.py,
│                              report_language.py (case-local copies)
├── outputs/                   input_statistics.json, metrics.json
├── figures/                   input, observation and result figures (PDF)
└── report/                    six-file LaTeX report + report_style.tex
```

## Data are provided, not stored

Large inputs and simulation results are not copied into the cases. Each case
reads them from the locations in `data/data_paths.json` (paths relative to the
case directory), which currently point to:

| Data | Default location | Override |
|---|---|---|
| Model inputs (landscape, weather, ignitions, …) | `fire_data/GOFER/ELMFIRE_GOFER_validation/<Fire_id>/inputs` | `GOFER_INPUTS_DIR` |
| GOFER arrival-time raster | `fire_data/GOFER/ELMFIRE_GOFER_validation/<Fire_id>/observations/<Fire_id>_toa.tif` | `GOFER_OBSERVATION_TOA` |
| Earlier simulation results | `~/Desktop/GOFER_val_exploratory/<Fire_id>/outputs*` | `GOFER_SIMULATIONS_DIR/<run_id>` |
| Current-configuration result | `<case>/simulation/` (written by `run_case.sh`) | — |

`preprocess.py` checks that the provided inputs exist with the sizes recorded in
`source_manifest.json` and fails clearly otherwise.

## Simulation configurations

Results from different configurations are evaluated separately:

- `baseline` — single first ignition, no spotting, default crown fire.
- `reference_spotting` — all GOFER ignitions, spotting with the Camp/Thomas/Tubbs
  settings (PER-MW, EMPIRICAL, EULERIAN, PHYSICAL).
- `current` — the case's `elmfire.data.in`: all GOFER ignitions, spotting on
  with ELMFIRE defaults, `CROWN_FIRE_MODEL = 1`.

Cases built so far are the fires with simulation results: Kincade (reference
spotting), CZU Lightning Complex (baseline and reference spotting, both from
the landscape before the offshore −10000 fill), Glass and Caldor (baseline).
The other 24 fires are added once their outputs are available: add the result
locations to `SIMULATIONS` in `tools/build_cases.py` and rerun it
(`--all` builds every fire, reporting "No simulation" where results are
missing).

## Running and rebuilding

```bash
ELMFIRE_BIN=$(which elmfire) ./kincade_2019/run_case.sh      # full case run
./kincade_2019/compile_case.sh                               # report only
python3 kincade_2019/scripts/postprocess.py                  # re-score results
```

`tools/build_cases.py` (re)creates all case folders from
`ELMFIRE_GOFER_validation/fires.csv`, its `inputs_log.csv`, the GOFER summary
and the result locations listed in the script, then runs preprocessing,
postprocessing and report compilation. It is a construction aid only; the
cases do not depend on it. Edit shared logic in `tools/case_files/` and rerun
the builder to propagate it to every case.

Requirements: Python 3 with numpy, matplotlib, rasterio and pyproj; LuaLaTeX,
latexmk and genuine Times New Roman fonts.
