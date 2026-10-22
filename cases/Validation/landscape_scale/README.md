# Landscape-scale validation

These seven cases compare ELMFIRE landscape reconstructions with independent
fire observations. Each case owns its current configuration, runner, processing
scripts, input metadata, metrics and report sources.

| Case | Comparison observations |
| --- | --- |
| `camp_fire` | VIIRS active-fire points |
| `thomas_fire` | VIIRS active-fire points |
| `tubbs_fire` | VIIRS active-fire points |
| `kincade_2019` | GOFER-derived arrival times |
| `czu_lightning_complex_2020` | GOFER-derived arrival times |
| `glass_2020` | GOFER-derived arrival times |
| `caldor_2021` | GOFER-derived arrival times |

## Current layout

```text
<case>/
  case.yaml
  elmfire.data.in
  run_case.sh
  compile_case.sh
  data/
    weather/                 wind and fuel-moisture rasters
    fuels_and_topography/    terrain, fuel, canopy, WUI and ignition rasters
    misc/                    required fuel-model and ignition tables
    observation/             comparison observations and supporting components
    archive_manifest.json    source identity and pinned data/generation files
    source_manifest.json     sources, units, time conventions and known gaps
    dataset_manifest.json    Zenodo bundle inventory and hashes
    data_paths.json          GOFER data locations, where applicable
  scripts/
    preprocess.py
    postprocess.py
    metrics_to_macro.py
    stage_dataset.py
    generate_data/           GOFER input-generation code, where supplied
  outputs/                   ELMFIRE results, input statistics and evaluation status
  figures/                   input/observation figures and future result figures
  report/                    standalone report source
```

All prior simulation outputs, historical runners and original model
configurations have been removed. The seven current case runners and namelists
remain in the repository. Evaluation status is **NOT EVALUABLE** until new
simulation results are supplied or generated. Old result figures and compiled
reports have been removed; input and observation characterizations remain.

## Restore the data

The combined local upload is `zenodo/dist/collection-2.1.0/`. It contains 31 fire
archives, including data for 24 future cases defined under `zenodo/datasets/`.
The archive contains current input data, comparison observations and supplied
data-generation code. It excludes simulation outputs, runners, model
configurations, reports, legacy inputs and caches. Metadata and restoration
support files accompany the data.

```bash
python3 tools/restore_zenodo_collection.py --case camp_fire --case-dir cases/Validation/landscape_scale/camp_fire --manifest zenodo/collection_manifest.json --archive-dir zenodo/dist/collection-2.1.0
```

A copied case can use `scripts/stage_dataset.py --bundle-dir /path/to/fire-bundles`
or `--verify`. Use `--download` only after registering a published version DOI.
Restoration is explicit, verifies hashes and refuses differing existing files.
Current case configurations come from the repository, not the data archive.
The four GOFER `stage_data.py` scripts can also restore the updated data from
the supplied directory, using `--source-dir /path/to/ELMFIRE_GOFER_validation`.
They verify all source files before copying missing files.

## Generate data where source code was supplied

The 28 GOFER datasets retain adapted input-generation code in
`scripts/generate_data/`. It fetches terrain, fuel and weather data, stacks
landscape bands, and creates ignition coordinates. It writes only data to a
new destination and does not create runners or model configurations.

```bash
python3 scripts/generate_data/prepare_inputs.py --output-dir /path/to/new-case --gofer-ignitions /path/to/GOFERC_fireIg.shp
```

See the local generator README for dependencies. External CloudFire access and
upstream GOFER files are required; regeneration has not been verified against
the frozen input hashes. `generate_observations.py` uses the supplied CAL FIRE
perimeter-generation functions with explicit upstream vector paths. The four
GOFER cases include arrival-time TIFFs, PNG previews, perimeter GeoPackages and
aligned 30 m mask TIFFs in `data/observation/`. No generator for the GOFER
arrival-time TIFF/PNG was supplied. No input-generation script was supplied
for Camp, Thomas or Tubbs.
These limitations remain recorded in the source metadata.

## Run and evaluate a current case

```bash
ELMFIRE_BIN=/path/to/elmfire PYTHON_BIN=/path/to/python cases/Validation/landscape_scale/camp_fire/run_case.sh
```

The runner preprocesses the case-local data, runs ELMFIRE, evaluates available
outputs and compiles the report. Camp, Thomas and Tubbs use their documented
ensemble setup; GOFER cases launch one process. All seven cases write ELMFIRE
results to `outputs/`, and postprocessors read that folder. Standard output and error logs remain in `logs/`, with temporary
files in `logs/scratch/`. No earlier run is selected automatically. Source
rasters and current scientific settings were not changed by the cleanup. Cases with no results report **NOT EVALUABLE**.

Preprocessing requires the scientific Python packages listed by each script;
VIIRS characterization also requires GDAL's `ogr2ogr`. Reports require LuaLaTeX,
latexmk and genuine Times New Roman fonts. Reports can be compiled from retained
input evidence and the current status without running ELMFIRE.

GOFER source: Liu et al. (2024), doi:10.5194/essd-16-1395-2024; dataset
doi:10.5281/zenodo.8327264. Full attribution, license evidence and unresolved
source-version and redistribution questions are retained in the metadata.
For case construction, follow the repository's validation-case skill.
