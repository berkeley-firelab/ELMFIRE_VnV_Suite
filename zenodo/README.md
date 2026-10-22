# ELMFIRE validation datasets

This collection contains model inputs, fire observations, and provenance records
for 31 wildfires in one Zenodo dataset record. Seven datasets support implemented
validation cases; 24 contain data for future cases. Each fire has its own `.tar`
file within the combined record. The complete upload is prepared in
`dist/collection-1.0.0/`: 31 fire archives and six supporting files, about 7.10 GB.

## Contents

Each fire archive contains compressed input, observation, and provenance bundles,
a dataset manifest, a metadata worksheet, a README, checksums, and a restoration
script. Historical model results and older inputs are included where available.
Source file contents and the inner bundle hashes are preserved.

The collection also contains `README.txt`, `collection_manifest.json`,
`metadata-worksheet.json`, `checksums.sha256`, `stage_collection.py`, and
`stage_dataset.py`. The collection manifest records each fire archive's size,
SHA-256 hash, member inventory, and original dataset manifest. The metadata
worksheet describes the collection and credits the dataset and upstream authors.

Camp, Thomas, and Tubbs contain VIIRS active-fire point observations. The other
28 fires contain arrival-time observations derived from
[GOFER](https://doi.org/10.5281/zenodo.8327264). Full GOFER attribution and source
limitations are retained in the collection and per-fire metadata. The selected
license is CC BY 4.0; source-specific terms and unresolved redistribution
permissions remain documented.

## Fire inventory

| Fire ID | File in the combined record | Archive size |
| --- | --- | ---: |
| `antelope_2021` | `antelope_2021.tar` | 200.37 MB |
| `august_complex_2020` | `august_complex_2020.tar` | 1226.39 MB |
| `beckwourth_complex_2021` | `beckwourth_complex_2021.tar` | 155.55 MB |
| `bobcat_2020` | `bobcat_2020.tar` | 91.39 MB |
| `caldor_2021` | `caldor_2021.tar` | 211.14 MB |
| `camp_fire` | `camp_fire.tar` | 24.08 MB |
| `creek_2020` | `creek_2020.tar` | 755.27 MB |
| `czu_lightning_complex_2020` | `czu_lightning_complex_2020.tar` | 30.60 MB |
| `dixie_2021` | `dixie_2021.tar` | 1149.72 MB |
| `dolan_2020` | `dolan_2020.tar` | 145.92 MB |
| `glass_2020` | `glass_2020.tar` | 43.35 MB |
| `july_complex_2020` | `july_complex_2020.tar` | 64.95 MB |
| `kincade_2019` | `kincade_2019.tar` | 57.99 MB |
| `knp_complex_2021` | `knp_complex_2021.tar` | 120.25 MB |
| `lnu_lightning_complex_2020` | `lnu_lightning_complex_2020.tar` | 252.17 MB |
| `mccash_2021` | `mccash_2021.tar` | 207.28 MB |
| `mcfarland_2021` | `mcfarland_2021.tar` | 124.81 MB |
| `monument_2021` | `monument_2021.tar` | 279.48 MB |
| `north_complex_2020` | `north_complex_2020.tar` | 385.54 MB |
| `red_salmon_complex_2020` | `red_salmon_complex_2020.tar` | 302.31 MB |
| `river_complex_2021` | `river_complex_2021.tar` | 389.77 MB |
| `scu_lightning_complex_2020` | `scu_lightning_complex_2020.tar` | 146.59 MB |
| `slater_and_devil_2020` | `slater_and_devil_2020.tar` | 101.34 MB |
| `sqf_complex_2020` | `sqf_complex_2020.tar` | 311.30 MB |
| `tamarack_2021` | `tamarack_2021.tar` | 83.67 MB |
| `thomas_fire` | `thomas_fire.tar` | 22.93 MB |
| `tubbs_fire` | `tubbs_fire.tar` | 6.04 MB |
| `w_5_cold_springs_2020` | `w_5_cold_springs_2020.tar` | 51.50 MB |
| `walker_2019` | `walker_2019.tar` | 30.99 MB |
| `windy_2021` | `windy_2021.tar` | 103.03 MB |
| `zogg_2020` | `zogg_2020.tar` | 18.74 MB |

Sizes use decimal MB. The outer `.tar` files contain already compressed bundles.

## Restore and verify

Download the desired fire archive, `collection_manifest.json`, and both Python
scripts. From the download folder, run:

```bash
python3 stage_collection.py --case camp_fire --case-dir /path/to/camp_fire --archive-dir .
```

Replace `camp_fire` with the desired fire ID. Add `--include-optional` for supplied
historical model results or older inputs. The script verifies hashes and
protects differing existing files. Python 3 is required; no additional packages
are needed. File integrity establishes agreement with the archived snapshot;
scientific validation requires a separate evaluation of model results.

From the repository root, verify the complete upload with:

```bash
python3 tools/prepare_zenodo_collection.py verify
```

The original per-fire folders under `dist/1.0.0/` are local staging material.
They are preserved for rebuilding the collection; they are not separate Zenodo
records. Dataset definitions remain in `cases/Validation/landscape_scale/` for
the seven implemented cases and `datasets/` for the 24 future cases.

The [upload guide](../docs/zenodo-upload-guide.md) describes preparing the single
record, registering its version DOI after publication, and downloading selected
fires. The tracked `collection_manifest.json` supplies download locations after
registration. Each case's standard restoration helper then downloads its fire
archive from the shared record.

## Acknowledgement

OpenAI Codex assisted with archive preparation, metadata organization, and
drafting the accompanying documentation.
