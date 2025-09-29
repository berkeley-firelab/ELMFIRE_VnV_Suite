# ELMFIRE Verification and Validation Suite

The ELMFIRE Verification and Validation (V&V) Suite captures self-contained
scenarios that exercise targeted portions of the ELMFIRE wildfire spread model.
Cases are grouped first by whether they target verification or validation, and
then by their scale (for example `cases/Validation/landscape_scale/<case>/`).
Each case includes the inputs required to reproduce the simulation, a scripted
post-processing pipeline, and a LaTeX report that documents the expected
behaviour, results, and pass/fail criteria. The repository also builds a master
report (ELMFIRE Verification Guide) that aggregates every individual case report.

---

## Repository layout

```text
ELMFIRE_VnV_Suite/
├── cases/                 # Category folders plus a reusable template
│   ├── Validation/
│   │   ├── landscape_scale/
│   │   │   └── <case>/     # Landscape-scale validation studies
│   │   └── structure_scale/
│   │       └── <case>/     # Structure-scale validation studies
│   ├── Verification/
│   │   └── <case>/         # Verification cases grouped by theme
│   └── case_template/      # Template used by tools/new_case.sh
│       ├── case.yaml       # Metadata and runtime settings for run_case.sh
│       ├── elmfire.data.in # Case-specific ELMFIRE configuration
│       ├── data/           # Optional raw input rasters or tables
│       ├── scripts/        # Post-processing utilities for this case
│       ├── figures/        # Auto-generated plots (outputs)
│       ├── outputs/        # Derived metrics (JSON, rasters, etc.)
│       ├── logs/           # Runtime logs captured by run_case.sh
│       └── report/         # LaTeX sources for the case report
├── common/                 # Shared resources (plot styling, latexmkrc)
├── main_report/            # Aggregated master report (main.tex → main.pdf)
├── gcp_config/             # Dockerfile, Cloud Build + Batch templates for Google Cloud runs
├── tools/                  # Workflow helpers (create case, rebuild reports)
└── Makefile                # Convenience targets that wrap the scripts
```

---

## Prerequisites

### System packages

Install the following tools on the workstation or HPC login node where cases
will be prepared:

- **ELMFIRE binary**: a compiled executable matching the release you intend to
  verify. Store it in a shared location and/or expose it through the
  `ELMFIRE_BIN` environment variable for convenience.
- **GNU Make, Bash, Coreutils**: required for the helper scripts in `tools/` and
  the per-case `run_case.sh` pipelines (standard on Linux).
- **Python ≥ 3.9** with `pip`.
- **LaTeX**: for linux system (server/HPC), install LaTeX following the instrution at `https://www.tug.org/texlive/quickinstall.html`.
- **GDAL/RasterIO dependencies** (e.g. `gdal-bin`, `libgdal-dev`) These are required by ELMFIRE and `rasterio` in some post-processing
  scripts.

### Python packages

Create and activate a virtual environment, then install the baseline Python
libraries used by the template and current cases:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install numpy matplotlib rasterio
```

Individual cases may require additional dependencies—inspect
`cases/<category>/<case>/scripts/*.py` and install any extras (for example `scipy` or
`pandas`). Keep the virtual environment activated while running cases so the
correct packages and versions are available.

---

## Initial setup and environment configuration

1. **Clone the repository** and change into it:
   ```bash
   git clone https://github.com/berkeley-firelab/ELMFIRE_VnV_Suite.git
   cd ELMFIRE_VnV_Suite
   ```
2. **Point to the ELMFIRE executable**. Either set `ELMFIRE_BIN` globally:
   ```bash
   export ELMFIRE_BIN=/opt/elmfire/bin/elmfire_2025.0717
   ```
   or edit `cases/<category>/<case>/case.yaml` to reference the absolute path under the
   `elmfire.bin` key. Using the environment variable keeps the YAML portable.
3. **Configure path to GDAL for all test cases** run `make configure PATH_TO_GDAL=/opt/my-gdal/bin` 
   to update the PATH_TO_GDAL namelist for all test cases.
4. **Activate the Python virtual environment** prepared in the previous section
   before running any scripts.

---

## Running an existing case

Each case ships with a `run_case.sh` orchestrator that executes the simulation,
post-processes the results, and rebuilds the LaTeX report.

```bash
# From the repository root (specify the category + case ID):
make run CASE=Verification/wue_transient_heatflux
# or
./cases/Verification/wue_transient_heatflux/run_case.sh
```

The script performs the following steps:

1. Reads `case.yaml` to discover the ELMFIRE binary, input configuration, runtime
   guard (`runtime_limit_s`), and optional paths.
2. Creates `outputs/`, `figures/`, and `logs/` folders under the case directory.
3. Runs the ELMFIRE executable with the referenced `elmfire.data.in` file.
4. Launches the Python post-processing pipeline (`scripts/postprocess.py`). This
   script is expected to write plots into `figures/`, metrics into
   `outputs/metrics.json`, and any LaTeX fragments needed by the report.
5. (When present) converts metrics into reusable LaTeX macros, e.g.
   `scripts/metrics_to_macro.py` → `report/metrics_macros.tex`.
6. Builds the per-case LaTeX report (`report/case_report.tex` → PDF) and refreshes
   the master report index via `tools/refresh_main.sh`.

Inspect `logs/elmfire.stderr` if the simulation fails. Outputs are kept inside
`cases/<category>/<case>/` so they can be version-controlled when appropriate.

---

## Running multiple cases automatically

Use `tools/run_all.py` when you need to execute every case sequentially (or
shard the workload across multiple workers). The helper script discovers all
`run_case.sh` files under `cases/`, even when they live inside nested
category folders, skips the template, and honors optional
sharding environment variables so it can be reused on Slurm or in cloud
batch jobs.

```bash
# Run every case sequentially on the local workstation
python3 tools/run_all.py

# Show the planned commands without executing them
python3 tools/run_all.py --dry-run

# Submit via Slurm using the shared header at common/slurm_head.txt
python3 tools/run_all.py --slurm
```

Cloud environments set `CLOUD_RUN_TASK_*`, `BATCH_TASK_*`, or `TASK_COUNT`
automatically. You can also override the shard layout explicitly:

```bash
# Run only shard 1/4 locally
python3 tools/run_all.py --shard-index 1 --shard-count 4
```

---

## Creating a new verification case

1. **Bootstrap from the template** using the helper script or Makefile target:
   ```bash
   ./tools/new_case.sh Verification/my_new_case
   # or
   make new CASE=Verification/my_new_case
   ```
   Replace `Verification/` with the appropriate category (e.g.,
   `Validation/landscape_scale/`). The helper copies `cases/case_template/`
   into `cases/<category>/my_new_case/` and expands the `{{CASE_ID}}` tokens in
   the YAML and report macros.

2. **Edit case metadata**:
   - `case.yaml` — update `case_title`, set path to the elmfire excutable (or rely on
     `ELMFIRE_BIN`), choose `elmfire.data.in`, and list any figures your
     post-processing will create.
   - `report/case_macros.tex` — fill in `\CaseTitle`, `\CaseOwner`,
     `\CaseVersion`, and `\CaseDate` so the report documents the targeted
     ELMFIRE release.

3. **Prepare the simulation inputs**:
   - Place the tailored `elmfire.data.in` and any required rasters or tables
     (or scripts for generating the input data) inside the case directory (`data/` is provided for convenience).
   - Document important parameters in `report/case_body.tex` under the
     “Simulation Setup” and “Assumptions” subsections.

4. **Implement post-processing** in `scripts/postprocess.py`:
   - Import helpers from `common/` if desired (e.g. `plot_styles.py`).
   - Write figures to `figures/`, capture numerical metrics in a dictionary, and
     save them to `outputs/metrics.json`.
   - If you need LaTeX-ready macros, either extend the script to write them or
     add a helper like `metrics_to_macro.py` (see the
     `wue_transient_heatflux` case for an example).

5. **Draft the case report**:
   - Use `report/case_body.tex` to describe the problem, expected results, and
     acceptance criteria.
   - Reference generated figures via standard LaTeX commands. Additional macros
     can be created in `report/case_macros.tex`.

6. **Run the end-to-end pipeline**:
   ```bash
   ./cases/Verification/my_new_case/run_case.sh
   ```
   Swap in the category path you selected in step 1.
   Iterate on the configuration, post-processing, or report content until the
   outputs and PDF look correct.

7. **Version-control the case** by adding new inputs, scripts, figures, metrics,
   and report sources to Git. Large raw rasters can be excluded if they are
   reproducible elsewhere (scripts should be provided); otherwise coordinate storage with the team.

---

## Running the suite in Google Cloud

The `gcp_config/` folder contains everything required to build a container that
packages the ELMFIRE source tree together with the V&V suite and to launch a
Google Cloud Batch job that executes `tools/run_all.py` across all cases.

### 1. Prepare infrastructure

1. Create an Artifact Registry Docker repository (for example
   `${REGION}-docker.pkg.dev/${PROJECT_ID}/elmfire-vnv-suite`).
2. Provision a Google Cloud Storage bucket that will receive the generated
   figures, metrics, and PDFs (e.g., `gs://elmfire_vnv_reports`). Grant the
   Cloud Build and Batch service accounts permission to write to the bucket.
3. Identify or create a service account that can submit Batch jobs and access
   Artifact Registry and the results bucket. Update the `_JOB_SA` substitution in
   `gcp_config/cloudbuild.yaml` accordingly.

### 2. Build the ELMFIRE + V&V image

The multi-stage Dockerfile at `gcp_config/Dockerfile` compiles ELMFIRE from
source and installs the suite dependencies. Build it with Cloud Build so the
image lands in Artifact Registry:

```bash
gcloud builds submit \
  --config gcp_config/cloudbuild.yaml \
  --substitutions _REGION=us-central1,_REPO=elmfire-vnv-suite,_IMAGE=elmfire-vnv,_JOB_NAME=elmfire-vnv,_RESULTS_BUCKET=gs://elmfire_vnv_reports,_JOB_SA=SERVICE_ACCOUNT_EMAIL,_TASK_COUNT=4,_PARALLELISM=4 \
  .
```

The build step renders `gcp_config/infra/batch_job.json` with the provided
substitutions and automatically submits a Cloud Batch job named
`elmfire-vnv-<commit>` that executes `python3 tools/run_all.py`. Adjust the
`_TASK_COUNT` and `_PARALLELISM` substitutions to control how many shards the
suite is split into.

### 3. Monitor and collect results

Once submitted, track the Batch job from the Cloud Console:

```
https://console.cloud.google.com/batch/jobs/details/${REGION}/elmfire-vnv-<commit>?project=${PROJECT_ID}
```

Each task uploads a snapshot of the suite (including generated reports) to the
`RESULTS_BUCKET`, using the commit SHA as a prefix. Download the artifacts with
`gsutil rsync` or from the console. Logs for each task are forwarded to Cloud
Logging for troubleshooting.

If you prefer Cloud Run Jobs instead of Batch, a template is also provided at
`gcp_config/infra/job.yaml`. Render it with `sed` (mirroring the Batch step in
`cloudbuild.yaml`) and deploy it via `gcloud run jobs replace` followed by
`gcloud run jobs execute`.

---

## Updating cases for a new ELMFIRE release

When validating a new target version of ELMFIRE, follow this standard process
for each affected case:

1. **Acquire or build the updated ELMFIRE executable** and update the path used
   by the case (`ELMFIRE_BIN` or `elmfire.bin` in `case.yaml`).
2. **Record the version in the report** by updating `\CaseVersion` (and
   optionally `\CaseDate`) within `report/case_macros.tex`.
3. **Review acceptance criteria** in `report/case_body.tex` to confirm they still
   apply. Adjust tolerances if model changes warrant it and document the
   rationale in the “Discussion” section.
4. **Re-run** `./cases/<category>/<case>/run_case.sh` to generate fresh outputs, metrics,
   and the updated PDF.
5. **Inspect diffs** in `outputs/metrics.json`, plots under `figures/`, and the
   LaTeX report. Highlight notable changes in the Discussion section.
6. **Regenerate the master report** (especially after multiple cases are
   refreshed):
   ```bash
   ./tools/build_all.sh
   # or
   make build-all
   ```
   This rebuilds every case report, rewrites `main_report/cases.tex`, and
   produces an updated `main_report/main.pdf` aggregating all cases.
7. **Commit and tag** the refreshed results. Include the ELMFIRE version number
   in your commit message or Git tag to keep an auditable history.

---

## Workflow summary

- Activate the Python environment and ensure the desired ELMFIRE binary is on
  hand before running any case scripts.
- Use `make run CASE=<category>/<id>` for spot checks, `./tools/new_case.sh` to seed new
  cases, and `./tools/build_all.sh` to rebuild everything (case PDFs + master
  report).
- Keep `outputs/metrics.json`, generated figures, and LaTeX sources under
  version control. Logs can be cleared if they grow too large.
- Document all assumptions and parameter choices in the case report so future
  maintainers can understand and reproduce the verification scenario.
- Prefer referencing the executable via `ELMFIRE_BIN` to avoid hard-coding
  machine-specific paths in `case.yaml`.

