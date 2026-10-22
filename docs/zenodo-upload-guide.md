# Uploading the ELMFIRE validation datasets to Zenodo

Publish 31 independently versioned Zenodo dataset records, one per fire: the
seven existing validation cases and the 24 additional GOFER fires.
Upload bundles are prepared under
`zenodo/dist/1.0.0/`. Retain these upload sets until the corresponding published
records have passed fresh download and checksum checks. The redundant GOFER
source collection was removed after all 469 source files were covered and
all 840 files in its 24 per-fire upload sets passed checksum checks. The small
definitions remain under `zenodo/datasets/`.

The preparation commands use Python 3.9 or later and its standard library.
Run the commands below from the repository root. These commands never upload
or publish files, run simulations, or remove tracked data.

## Step 1 Inspect the prepared files

Start with Camp as the first record, then repeat for the other six cases:

```bash
ls zenodo/dist/1.0.0/camp_fire
make zenodo-verify
```

Each case folder contains the following upload files:

| File | Purpose |
| --- | --- |
| `inputs.tar.gz` | Frozen inputs selected from the existing archive manifest |
| `observations.tar.gz` | Comparison observations with all manifest-listed sidecars |
| `provenance.tar.gz` | Original preparation records when supplied, source manifests, and current configuration snapshot |
| `historical_outputs.tar.gz`, when present | Supplied past simulation results, separate from observations |
| `legacy_inputs.tar.gz`, when present | Distinct older inputs from Camp, Thomas, or Tubbs; inactive in current runners |
| `dataset_manifest.json` | Bundle and individual-file SHA-256 hashes, relative paths, and dataset version |
| `README.txt` | Dataset contents and restoration notes |
| `stage_dataset.py` | Standalone standard-library restoration helper |
| `metadata-worksheet.json` | Human review worksheet for the Zenodo form |
| `checksums.sha256` | SHA-256 hashes of all other upload files |

The original archives and source files are not moved or recompressed in place.
Bundle member names are relative to the case root, preserving existing input
and observation paths. The new archives normalize container timestamps and
ownership while preserving file contents. Original timestamps and filesystem
permissions are not part of this dataset contract; archived preparation scripts
are retained as evidence rather than executable launchers.

Current generated results, report PDFs, figures, logs, scratch data, and macOS
metadata are excluded. The three available GOFER historical-output sets are
included as optional bundles; the missing CZU historical results are not
reconstructed. The other 24 GOFER fires each have their own dataset record,
described in Step 9.

## Step 2 Complete the metadata worksheets

Edit `zenodo/metadata/<case_id>.json`. Creator names, affiliations, and ORCIDs
are intentionally left blank for you to supply. Complete the publication date,
license, and redistribution evidence after checking the actual upstream terms.
Keep upstream creators credited separately from the creators responsible for
this prepared dataset, using the appropriate creator or contributor role.

The existing manifests do not establish redistribution terms for all supplied
inputs. Camp, Thomas, and Tubbs also have incomplete upstream product and VIIRS
collection provenance. Preserve these statements in the record description;
do not apply the repository software license automatically to the datasets.
Leave a record as a draft while its redistribution permission is unresolved.

GOFER worksheets already include the source dataset and article as related
identifiers. Credit the prepared observation rasters as derived products, while
retaining the original GOFER citation. The record description should distinguish
model inputs, observations, and historical model outputs.

After editing the worksheets, refresh their upload copies and checksums:

```bash
python3 tools/prepare_zenodo.py metadata
make zenodo-verify
```

The worksheets are not Zenodo API payloads. Copy their reviewed fields into
the web form. When the worksheet is complete, set its `review_status` to a
description of the completed review before refreshing the upload copy.

## Step 3 Create the first Zenodo draft

1. Sign in at [Zenodo](https://zenodo.org/).
2. Select the plus icon and **New upload**.
3. Set the resource type to **Dataset**.
4. Use the reviewed title, description, creators, publication date, version
   `1.0.0`, keywords, license, and related identifiers from Camp's worksheet.
5. Request a new DOI for this prepared dataset. Do not reuse the DOI of the
   original GOFER dataset, a paper, or the suite's software release.
6. Save the draft.

Zenodo supports reserving a DOI while the upload remains a draft; it registers
that DOI when the record is published. See
[Create new upload](https://help.zenodo.org/docs/deposit/create-new-upload/).
For practice, use [the Zenodo sandbox](https://sandbox.zenodo.org/) first; a
sandbox deposit is separate from production and does not receive a production
DOI. The repository registration command below targets production records.

## Step 4 Upload one complete case folder

Upload every file directly inside `zenodo/dist/1.0.0/camp_fire/` to Camp's draft.
Retain the file names exactly: the repository manifest uses them for downloads.
Include optional historical or legacy bundles when they are present, so each
record preserves its complete prepared snapshot. Optional means they are not
needed for the default restoration of active data.

Keep the seven active cases in separate records. Zenodo's standard allowance is
50 GB and 100 files per record; each prepared case is far below both limits.
Wait until every upload has completed before proceeding. See
[Manage files](https://help.zenodo.org/docs/deposit/manage-files/).

## Step 5 Review and publish the record

Confirm that the uploaded file names and sizes match the local folder, that
creator and license fields are complete, and that the description preserves
known provenance gaps. Preview the record and publish when ready.

Record the **specific version DOI** and its numeric record ID from the
published record URL. Also record the concept DOI if shown; it identifies the
version family and should not replace the specific version in the download
manifest. Changed scientific files should be released as a new version. See
[Manage versions](https://help.zenodo.org/docs/deposit/manage-versions/).

## Step 6 Register the published version in the repository

Replace the example identifiers with the actual production values:

```bash
python3 tools/prepare_zenodo.py register \
  --case camp_fire \
  --record-id 12345678 \
  --doi 10.5281/zenodo.12345678 \
  --concept-doi 10.5281/zenodo.12345677
```

Omit `--concept-doi` if it is not available. This command changes only the
case's tracked `data/dataset_manifest.json`, adding the version DOI and exact
bundle URLs. It does not publish anything or verify that the record is public.
The uploaded manifest can retain empty record fields: it describes the same
file hashes, and the repository manifest supplies the published location.
Do not change published bundle contents to insert their own DOI afterward.

## Step 7 Verify a fresh download

Check the published record through an empty destination, so local source data
cannot hide a missing or incorrect remote file:

```bash
CASE_DIR="$PWD/cases/Validation/landscape_scale/camp_fire"
AUDIT_CASE=$(mktemp -d /private/tmp/elmfire-zenodo-camp.XXXXXX)
python3 "$CASE_DIR/scripts/stage_dataset.py" \
  --case-dir "$AUDIT_CASE" \
  --manifest "$CASE_DIR/data/dataset_manifest.json" \
  --download --include-optional
```

The helper downloads every bundle, verifies its size and SHA-256, restores
only listed regular files, and verifies each restored file. It rejects unsafe
paths, symlinks, and differing existing files. Keep the temporary audit folder
until you have reviewed the result; remove that folder manually when finished.
On Linux, use `/tmp` in the `mktemp` command instead of `/private/tmp`.

For an offline restoration from the files prepared here:

```bash
python3 cases/Validation/landscape_scale/camp_fire/scripts/stage_dataset.py \
  --bundle-dir "$PWD/zenodo/dist/1.0.0/camp_fire" --include-optional

python3 cases/Validation/landscape_scale/camp_fire/scripts/stage_dataset.py \
  --verify --include-optional
```

Default restoration selects inputs, observations, and provenance. Add
`--include-optional` to restore supplied historical outputs and inactive older
inputs as well. The cache is under the destination case's `data/.zenodo-cache/`
and is ignored by Git. A private or restricted record needs an independently
authorized local download; this helper does not manage Zenodo access tokens.

These checks verify data integrity, not successful model execution. All seven
existing cases preprocess the extracted inputs and observations without using
the original compressed archives or the old `3_FIRES` directory. Camp, Thomas,
and Tubbs preserve the original archive hashes as provenance only; required
extracted input and observation files still undergo size and SHA-256 checks,
followed by the existing raster checks. No model settings or acceptance criteria
are changed by this work.

## Step 8 Repeat for all seven cases

Repeat Steps 2 through 7 for:

```text
caldor_2021
camp_fire
czu_lightning_complex_2020
glass_2020
kincade_2019
thomas_fire
tubbs_fire
```

Each case gets its own record ID, version DOI, metadata worksheet, and fresh
download check. The original GOFER `scripts/stage_data.py` archive restoration
commands remain available alongside the new `scripts/stage_dataset.py`.

## Step 9 Upload each additional GOFER fire separately

Each of the 24 remaining GOFER fires has its own upload folder under
`zenodo/dist/1.0.0/<fire_id>/`, matching the seven existing records. Create one
Zenodo Dataset record per folder. Each contains `inputs.tar.gz`,
`observations.tar.gz`, `provenance.tar.gz`, and five sidecars. For example,
Antelope uses `zenodo/dist/1.0.0/antelope_2021/` and the worksheet
`zenodo/metadata/antelope_2021.json`. Creator fields remain blank.

Each provenance bundle includes that fire's original launcher, the shared
preparation scripts, retrieval log, fire table, full original archive inventory,
and the fire-specific source and archive manifests. Other fires' input and
observation bytes are excluded. Shared preparation evidence is repeated in
these small provenance bundles so every record is independently usable.

Verify one record or all 24 additional records:

```bash
make zenodo-verify CASE=antelope_2021
make zenodo-verify CASE=gofer
```

After publishing Antelope, register its own version DOI:

```bash
python3 tools/prepare_zenodo.py register \
  --case antelope_2021 \
  --record-id 12345678 --doi 10.5281/zenodo.12345678
```

Replace the example identifiers. Repeat independently for every other fire.
The local definition for Antelope is
`zenodo/datasets/antelope_2021/`. It contains the tracked
`data/dataset_manifest.json`, source/archive manifests, and restore helper.
These definitions prepare future validation cases; runnable configurations,
metrics, and scientific acceptance criteria still need to be authored.

The archive paths already match a standalone future case:
`data/archive_payload/inputs/`, `data/archive_payload/observations/`, and
`data/provenance/archive/`. The redundant source collection has been removed.
Legacy `repository_source` fields identify former locations for provenance only;
both restoration and packaging use the normalized case-local paths.

Test offline restoration into an empty future case directory:

```bash
DEFINITION="$PWD/zenodo/datasets/antelope_2021"
FUTURE_CASE=$(mktemp -d /private/tmp/elmfire-antelope.XXXXXX)
python3 "$DEFINITION/scripts/stage_dataset.py" \
  --case-dir "$FUTURE_CASE" \
  --manifest "$DEFINITION/data/dataset_manifest.json" \
  --bundle-dir "$PWD/zenodo/dist/1.0.0/antelope_2021"
```

After publication, substitute `--download` for `--bundle-dir ...` to test the
actual remote files as in Step 7. Use `/tmp` instead of `/private/tmp` on Linux.
When authoring a future case, copy its dataset manifest and restoration helper
into the case's `data/` and `scripts/` folders, respectively. Restore the data
before editing provenance records; differing existing files are protected.
Use `make zenodo-verify` to check the retained upload sets without extracted
source copies; the per-fire helper verifies files at the explicitly selected
case destination. For an optional source check after restoring into a definition,
run `python3 tools/prepare_zenodo.py verify --case antelope_2021 --check-sources`.
A new version must be built from restored source files: use the same helper
with `--case-dir "$DEFINITION"` to restore into the definition directory first,
then run `make zenodo-build CASE=antelope_2021 DATASET_VERSION=1.0.1`.
The small definition files already match their archived counterparts; differing
local files are protected against overwrites.

The [dataset overview](../zenodo/README.md) lists all 31 individual fire IDs and
upload sizes. The previous combined collection upload has been retired.

## Step 10 Commit the repository metadata and finish migration

Review and commit the new tools, guides, metadata worksheets, case-local
staging scripts, and dataset manifests. `zenodo/dist/` is ignored and should
not be committed. No Zenodo token is required by the public download workflow.

Archived validation input, observation, historical-output and older-input
payloads have been removed from Git's index and are ignored. Existing local
copies are preserved. The remaining 127 tracked payload files from Camp,
Thomas and Tubbs were checked against their per-file and bundle hashes before
untracking; the GOFER payloads and upload bundles were already untracked.

Keep dataset and provenance manifests, configurations, metadata worksheets,
restore scripts and report evidence tracked. A fresh clone must restore data
before running a case. Until publication is registered, use `--bundle-dir`
with the retained upload folder; `--download` requires the actual version DOI
and record ID. Registration and fresh-download checks are still required.
Treat any Git history rewrite as a separate coordinated operation;
untracking files does not shrink old history.

## Updating a published dataset

For a change to any bundled file, choose a new dataset version and a new output
directory. A build will not replace an existing upload folder or reset a
registered record for the same version:

```bash
make zenodo-build CASE=camp_fire DATASET_VERSION=1.0.1
make zenodo-verify CASE=camp_fire DATASET_VERSION=1.0.1
```

Open Camp's existing Zenodo record and select **New version**. Upload the new
snapshot, review its metadata, publish, register the new version record in the
repo, and repeat the fresh download check. Preserve the old version's files
and DOI for earlier reproducible evaluations. To change only a worksheet
before publication, use the `metadata` action rather than rebuilding bundles.
