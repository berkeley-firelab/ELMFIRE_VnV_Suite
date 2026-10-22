# GOFER datasets for future validation cases

Each fire below has an independent Zenodo upload folder and metadata worksheet.
The redundant source collection has been removed after checking archive contents.
These small definitions retain the manifests and independent restore helpers;
source bytes are preserved in the per-fire upload sets under `../dist/1.0.0/`.

Each definition contains `data/archive_manifest.json`, `data/source_manifest.json`,
`data/dataset_manifest.json`, and `scripts/stage_dataset.py`. No run configuration
or scientific acceptance basis is implied by preparing a dataset definition.

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

For one dataset, run `make zenodo-verify CASE=antelope_2021` from the repository
root. Use `CASE=gofer` for all 24 future cases, or omit CASE for all 31 datasets.
The [upload guide](../../docs/zenodo-upload-guide.md) describes registering
a separate DOI per fire and restoring into a chosen future case directory.

A future validation case can own the dataset manifest and restoration helper
without importing any other case or relying on the original collection at runtime.
Legacy `repository_source` fields identify the original locations only; no tool
uses them to find source bytes. To build a new dataset version, restore its
bundles into this definition directory first, using its helper, then build from
the normalized case-local paths. Restored bulk files are ignored by Git.
Author its configuration,
processing, scientific rationale, metrics, and report separately.
