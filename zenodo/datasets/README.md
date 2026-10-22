# Data for future ELMFIRE validation cases

This directory contains dataset definitions for 24 wildfires. Each fire has an
independent archive under `../dist/1.0.0/<fire_id>/`, containing model inputs,
GOFER-derived arrival-time observations, and provenance records.

Each definition contains `data/archive_manifest.json`, `data/source_manifest.json`,
`data/dataset_manifest.json`, and `scripts/stage_dataset.py`. The manifests record
file inventories, hashes, and source information. A current runnable case
configuration and scientific evaluation criteria are not included.

| Fire ID | Upload folder from repository root |
| --- | --- |
| `antelope_2021` | `zenodo/dist/1.0.0/antelope_2021/` |
| `august_complex_2020` | `zenodo/dist/1.0.0/august_complex_2020/` |
| `beckwourth_complex_2021` | `zenodo/dist/1.0.0/beckwourth_complex_2021/` |
| `bobcat_2020` | `zenodo/dist/1.0.0/bobcat_2020/` |
| `creek_2020` | `zenodo/dist/1.0.0/creek_2020/` |
| `dixie_2021` | `zenodo/dist/1.0.0/dixie_2021/` |
| `dolan_2020` | `zenodo/dist/1.0.0/dolan_2020/` |
| `july_complex_2020` | `zenodo/dist/1.0.0/july_complex_2020/` |
| `knp_complex_2021` | `zenodo/dist/1.0.0/knp_complex_2021/` |
| `lnu_lightning_complex_2020` | `zenodo/dist/1.0.0/lnu_lightning_complex_2020/` |
| `mccash_2021` | `zenodo/dist/1.0.0/mccash_2021/` |
| `mcfarland_2021` | `zenodo/dist/1.0.0/mcfarland_2021/` |
| `monument_2021` | `zenodo/dist/1.0.0/monument_2021/` |
| `north_complex_2020` | `zenodo/dist/1.0.0/north_complex_2020/` |
| `red_salmon_complex_2020` | `zenodo/dist/1.0.0/red_salmon_complex_2020/` |
| `river_complex_2021` | `zenodo/dist/1.0.0/river_complex_2021/` |
| `scu_lightning_complex_2020` | `zenodo/dist/1.0.0/scu_lightning_complex_2020/` |
| `slater_and_devil_2020` | `zenodo/dist/1.0.0/slater_and_devil_2020/` |
| `sqf_complex_2020` | `zenodo/dist/1.0.0/sqf_complex_2020/` |
| `tamarack_2021` | `zenodo/dist/1.0.0/tamarack_2021/` |
| `w_5_cold_springs_2020` | `zenodo/dist/1.0.0/w_5_cold_springs_2020/` |
| `walker_2019` | `zenodo/dist/1.0.0/walker_2019/` |
| `windy_2021` | `zenodo/dist/1.0.0/windy_2021/` |
| `zogg_2020` | `zenodo/dist/1.0.0/zogg_2020/` |

From the repository root, verify one retained archive with
`make zenodo-verify CASE=antelope_2021`. Use `CASE=gofer` to check all 24 datasets,
or omit `CASE` to check all 31 fire datasets.

To restore a dataset, run its `stage_dataset.py` helper with the archive folder
specified by `--bundle-dir`. File paths within the compressed archives are
relative to the destination case directory. Inputs and observations restore to
`data/archive_payload/`; preparation records restore to `data/provenance/archive/`.
The helper verifies the archived files and protects differing existing files.

The [collection overview](../README.md) describes the archive contents and
license. The [upload guide](../../docs/zenodo-upload-guide.md) provides commands
for restoration, versioning, and DOI registration. Source-version limitations
and redistribution evidence are recorded in the per-fire metadata worksheets.

## Acknowledgement

OpenAI Codex assisted with archive preparation, metadata organization, and
drafting the accompanying documentation.
