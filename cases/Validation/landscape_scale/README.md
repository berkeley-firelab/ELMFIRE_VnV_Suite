# Landscape-scale validation

These cases compare ELMFIRE landscape reconstructions with historical-fire
evidence. Each case owns its runtime scripts, supporting functions,
configuration, provenance records, metrics, figures, and standalone report.
No case imports or sources runtime logic from another case or the GOFER
construction tools. A case can be copied and run separately with its documented
software dependencies and source datasets supplied.

## Cases and evidence

| Case | Event | Reference evidence |
|---|---|---|
| `camp_fire/` | 2018 Camp Fire | Archive-derived inputs and VIIRS observations |
| `thomas_fire/` | 2017 Thomas Fire | Archive-derived inputs and VIIRS observations |
| `tubbs_fire/` | 2017 Tubbs Fire | Archive-derived inputs and VIIRS observations |
| `kincade_2019/` | 2019 Kincade Fire | GOFER-Combined hourly perimeters |
| `czu_lightning_complex_2020/` | 2020 CZU Lightning Complex | GOFER-Combined hourly perimeters |
| `glass_2020/` | 2020 Glass Fire | GOFER-Combined hourly perimeters |
| `caldor_2021/` | 2021 Caldor Fire | GOFER-Combined hourly perimeters |

GOFER covers 28 California fires in 2019–2021. The four cases here compare
ELMFIRE arrival time with arrival time derived from hourly perimeters:
Liu et al. (2024), doi:10.5194/essd-16-1395-2024; dataset
doi:10.5281/zenodo.8327264. The other 24 fires are not implemented here.

## Independent case layout

```text
<case_id>/
├── case.yaml                  discovery metadata and namelist invariants
├── elmfire.data.in            version-specific ELMFIRE configuration
├── run_case.sh                preprocess → ELMFIRE → postprocess → report
├── compile_case.sh            metrics → LaTeX macros → case_report.pdf
├── data/
│   ├── source_manifest.json   source and observation provenance
│   ├── archive_manifest.json  archive-input SHA-256 records, where available
│   └── data_paths.json        external data locations, for GOFER cases
├── scripts/                   all case-local processing and supporting functions
├── outputs/                   input_statistics.json and metrics.json
├── figures/                   input, observation, and result figures
├── logs/                      created by the runner
└── report/                    six-file LaTeX project and local report_style.tex
```

Use `${ELMFIRE_BIN:-elmfire}` for the executable and `${PYTHON_BIN:-python3}`
for Python. Reports require LuaLaTeX, latexmk, and genuine Times New Roman
fonts. Compilation reads saved evidence; it does not run ELMFIRE or require
another case or the aggregate guide.

## Camp, Thomas, and Tubbs reconstructions

These cases were assembled from RAR archives historically tracked under
`cases/Validation/3_FIRES/`. Extracted inputs and SHA-256 integrity manifests
are retained inside each case. The original archives and legacy notebook are
absent from the current working tree; repository history retains their
provenance. The notebook is not part of the active workflow because it contains
hard-coded paths and destructive file operations.

Each case includes an archive-derived configuration, a source/observation
manifest, a read-only preprocessor, and a non-destructive postprocessor.
From the repository root:

```bash
ELMFIRE_BIN=/path/to/elmfire \
  cases/Validation/landscape_scale/camp_fire/run_case.sh
```

An absolute runner path works from any directory. The default launch uses
50 MPI ranks, one per ensemble member, with a smaller positive override through
`ELMFIRE_MPI_RANKS`. Optional suite-level Savio submission uses a header that
keeps those ranks on one node and disables PROJ network caching to avoid
contention for a shared user-cache database. Preprocessing requires Python,
NumPy, Matplotlib, Rasterio, PyYAML, and GDAL's `ogr2ogr`. Comparison additionally
requires Pandas, GeoPandas, and Shapely with their geospatial runtime libraries.

The current saved metrics say `CHARACTERIZED`. Earlier repository-completion
reports said `NOT EVALUABLE` before simulation evidence was supplied. The
archives contain no justified acceptance thresholds, and VIIRS hull uncertainty
is not quantified, so these cases do not claim PASS/FAIL.

## GOFER data and configurations

The four GOFER cases were relocated from `../GOFER/`. Their source data are now
case-local, extracted unchanged from the user-supplied
`ELMFIRE_GOFER_validation.tar.gz` archive. `data/data_paths.json` uses paths
relative to the case root, so copying the complete case preserves its data
references. Environment overrides remain available for verified copies.

| Data | Case-local location | Optional override |
|---|---|---|
| Model inputs | `data/archive_payload/inputs/` | `GOFER_INPUTS_DIR` |
| Arrival-time observation | `data/archive_payload/observations/<Fire_id>_toa.tif` | `GOFER_OBSERVATION_TOA` |
| Supplied historical results | `data/archive_payload/outputs/` (Kincade, Glass, Caldor) | `GOFER_SIMULATIONS_DIR/<run_id>/` |
| Missing CZU historical results | `data/historical_outputs/<run_id>/` (not supplied) | `GOFER_SIMULATIONS_DIR/<run_id>/` |
| Current result | `<case>/simulation/` | Written by `run_case.sh` |
| Original preparation records | `data/provenance/archive/` | None; immutable evidence |

The archive supplies inputs and observations for all four active cases and
historical outputs for Kincade, Glass, and Caldor. It contains neither historical
CZU run. The other 24 fires' source data are retained under
`../GOFER/data/archive_payload/`; current cases do not depend on that directory.

Every extracted file is recorded by original archive member, case-local path,
byte size, and SHA-256 in `data/archive_manifest.json`. The source manifest also
pins input and observation hashes. The archive itself is pinned to SHA-256
`714b9f2b3c3417336ea200bfc6f2bba2955376bf3088d675a811a11d28b0fffe`.
macOS resource-fork files and `.DS_Store` were omitted. Files in the archive
payload and provenance snapshot are immutable; generate new data elsewhere.
The original archived launcher is retained as evidence and is not the active
case runner. In particular, the prepared input namelist does not establish
which configuration produced the historical outputs.

Bulk extracted data are ignored by Git because the complete collection expands
to about 7.55 GB. A clone can restore each case independently using its own
standard-library-only staging script and the exact original archive:

```bash
python3 cases/Validation/landscape_scale/kincade_2019/scripts/stage_data.py \
  /path/to/ELMFIRE_GOFER_validation.tar.gz
python3 cases/Validation/landscape_scale/kincade_2019/scripts/stage_data.py --verify
```

Staging verifies the archive checksum, restores only that case's files, and
refuses to replace differing existing files. Archive manifests and staging
scripts are retained in Git. The archive's upstream redistribution terms are
not documented; no new license is inferred.

The configurations are evaluated separately:

- `baseline`: single first ignition, no spotting, default crown fire.
- `reference_spotting`: all GOFER ignitions and Camp/Thomas/Tubbs spotting
  settings (PER-MW, EMPIRICAL, EULERIAN, PHYSICAL), documented locally in each
  GOFER source manifest and report; those other cases are not runtime dependencies.
- `current`: the case's own configuration, targeting ELMFIRE 1.1, all GOFER
  ignitions, spotting enabled with ELMFIRE defaults, and `CROWN_FIRE_MODEL = 1`.

Saved evidence covers reference spotting for Kincade, baseline and reference
spotting for CZU, and baseline runs for Glass and Caldor. Both historical CZU
results precede correction of the offshore −10000 fill. Kincade and CZU reports
disclose dependence on spotting choices informed by these fires. All four saved
statuses are `CHARACTERIZED`; none includes a simulation of the current case
configuration. Historical CZU numerical comparisons remain unreproducible until
its two output sets are supplied. The retained metrics, figures, and reports
are not replaced by the data-staging operation.

From the repository root, with the case data staged:

```bash
# Complete case; the executable may be supplied inside the user's container.
ELMFIRE_BIN=/path/to/elmfire \
  cases/Validation/landscape_scale/kincade_2019/run_case.sh

# Compile retained metrics and figures without a simulation.
cases/Validation/landscape_scale/kincade_2019/compile_case.sh

# Re-score supplied results; replaces calculated metrics and figures.
python3 cases/Validation/landscape_scale/kincade_2019/scripts/postprocess.py
```

The GOFER runner launches one ELMFIRE process. Python dependencies include
NumPy, Matplotlib, Rasterio, and PyProj. Preprocessing checks input existence,
recorded byte sizes, SHA-256 hashes, and selected raster properties, and fails
when required data are absent or have changed.

### Remaining reproducibility requirements

The archive staging preserves scientific settings and retained results. Input
and observation checksums and a deterministic staging procedure are now
available. The full upstream observation-generation history, access/license
records, and historical executable identity remain incompletely documented.
The supplied source checkout supports configuration compatibility checks;
compatibility alone does not identify the executable inside the user's container.
Each moved case's `data/configuration_audit.json` records the checked source
revision and dirty state, namelist hash, and static validation result. All four
passed the source-schema and seven declared-invariant checks against revision
`8981f14e0170ced6cc28c4d308d4545ba925f5ef`; this differs from the historical
result revision `5ea7460d514b24bf9a1cdda571c16f4f03de603f`.

Each case's postprocessor now enforces a single member (member 1), unique
member/time identities, and landscape-to-simulation grid alignment. It accepts identical transforms or
coordinates exactly reproduced by ELMFIRE's single-precision pixel-center
calculation and two-decimal BIL header serialization. This documented exception
accounts for the supplied outputs' sub-decimeter origin differences; it neither
resamples the landscape nor changes the simulation or observation transforms. It
reports `NOT EVALUABLE` for ambiguous outputs, missing or invalid landscape
masks, or no finite observed arrivals in the comparison region. Automated
tests exercise these checks in all four independent implementations, including
an exact synthetic comparison. Relative historical-result overrides are
resolved from the case root consistently with the other data paths.

These stricter checks identify future calculations as `gofer_validation_v3`.
Retained metrics and figures remain the original `gofer_validation_v1`
calculations and have not been overwritten. `data/archive_validation.json`
records read-only input checks and comparisons with the retained historical
metrics, including differences at floating-point rounding precision and the
missing CZU runs. Observation coverage/censoring and simulation completeness
still require scientific review. Synthetic software tests do not establish
scientific validation of these fires.

### Legacy construction tools

The builder and templates remain at `../GOFER/tools/`. They are legacy
construction material, not dependencies of any current case. The builder
historically reads the fire list, retrieval log, GOFER summary, and hard-coded
result locations, then generates case files. **Do not use it to rebuild the
relocated cases:** it still targets `../GOFER/` and would recreate duplicate
cases there. Maintain each case's own files directly. Future cases should
follow the validation skill and be created independently in `landscape_scale/`.

## Suite discovery and reports

From the repository root:

```bash
python3 tools/run_all.py --suite validation --dry-run
make validation-report
```

Discovery should find all seven cases exactly once under `landscape_scale/`.
The aggregate guide consumes standalone PDFs; cases do not depend on the guide.
For new cases or scientific revisions, follow
[`elmfire-validation-case`](../skills/elmfire-validation-case/SKILL.md), which
requires traceable provenance, justified settings, input characterization,
case-local processing, observation-aware metrics, representative fields, and
independently compilable reports. A successful build is not a scientific PASS.
