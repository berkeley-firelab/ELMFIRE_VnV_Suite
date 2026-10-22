# ELMFIRE validation datasets

This collection contains model inputs, fire observations, and provenance records
for 31 wildfires. Each fire has a separate dataset under
`dist/1.0.0/<fire_id>/`. Seven datasets support implemented validation cases in
`cases/Validation/landscape_scale/`. The other 24 contain data for future cases,
with dataset definitions in `datasets/<fire_id>/`.

Each dataset preserves a fixed set of source files. Model inputs, observations,
and results from earlier simulations are stored in separate compressed archives.
File inventories and SHA-256 hashes support verification and reproducible
restoration.

## Archive contents

| File | Contents |
| --- | --- |
| `inputs.tar.gz` | Model inputs, including terrain, fuels, weather, fuel moisture, and ignition data where supplied. |
| `observations.tar.gz` | Fire observations and supporting files used for model comparison. |
| `provenance.tar.gz` | Source and archive manifests, preparation records, and case configuration files where available. |
| `historical_outputs.tar.gz` | Results supplied from earlier model simulations; included only where available. |
| `legacy_inputs.tar.gz` | Older inputs retained separately from the active inputs; included only where available. |
| `dataset_manifest.json` | Dataset version, file inventory, sizes, and SHA-256 hashes for the archives and their contents. |
| `metadata-worksheet.json` | Dataset description, source citations, license, and redistribution evidence. |
| `checksums.sha256` | SHA-256 hashes of the other files in the dataset folder. |
| `stage_dataset.py` | Standalone Python script for extraction and integrity verification. |
| `README.txt` | Description of the individual dataset and its restoration procedure. |

Camp, Thomas, and Tubbs include VIIRS active-fire observations. The other 28
datasets contain arrival-time observations derived from
[GOFER](https://doi.org/10.5281/zenodo.8327264). Full GOFER attribution and
source-version limitations are recorded in their metadata worksheets. The source
manifests document known gaps in data origins and processing history.

## Dataset inventory

| Fire ID | Case status | Upload folder | Compressed size |
| --- | --- | --- | ---: |
| `antelope_2021` | Prepared data | `dist/1.0.0/antelope_2021/` | 200.35 MB |
| `august_complex_2020` | Prepared data | `dist/1.0.0/august_complex_2020/` | 1226.38 MB |
| `beckwourth_complex_2021` | Prepared data | `dist/1.0.0/beckwourth_complex_2021/` | 155.53 MB |
| `bobcat_2020` | Prepared data | `dist/1.0.0/bobcat_2020/` | 91.38 MB |
| `caldor_2021` | Implemented case | `dist/1.0.0/caldor_2021/` | 211.13 MB |
| `camp_fire` | Implemented case | `dist/1.0.0/camp_fire/` | 24.07 MB |
| `creek_2020` | Prepared data | `dist/1.0.0/creek_2020/` | 755.26 MB |
| `czu_lightning_complex_2020` | Implemented case | `dist/1.0.0/czu_lightning_complex_2020/` | 30.58 MB |
| `dixie_2021` | Prepared data | `dist/1.0.0/dixie_2021/` | 1149.70 MB |
| `dolan_2020` | Prepared data | `dist/1.0.0/dolan_2020/` | 145.91 MB |
| `glass_2020` | Implemented case | `dist/1.0.0/glass_2020/` | 43.34 MB |
| `july_complex_2020` | Prepared data | `dist/1.0.0/july_complex_2020/` | 64.94 MB |
| `kincade_2019` | Implemented case | `dist/1.0.0/kincade_2019/` | 57.98 MB |
| `knp_complex_2021` | Prepared data | `dist/1.0.0/knp_complex_2021/` | 120.24 MB |
| `lnu_lightning_complex_2020` | Prepared data | `dist/1.0.0/lnu_lightning_complex_2020/` | 252.15 MB |
| `mccash_2021` | Prepared data | `dist/1.0.0/mccash_2021/` | 207.27 MB |
| `mcfarland_2021` | Prepared data | `dist/1.0.0/mcfarland_2021/` | 124.80 MB |
| `monument_2021` | Prepared data | `dist/1.0.0/monument_2021/` | 279.47 MB |
| `north_complex_2020` | Prepared data | `dist/1.0.0/north_complex_2020/` | 385.52 MB |
| `red_salmon_complex_2020` | Prepared data | `dist/1.0.0/red_salmon_complex_2020/` | 302.29 MB |
| `river_complex_2021` | Prepared data | `dist/1.0.0/river_complex_2021/` | 389.76 MB |
| `scu_lightning_complex_2020` | Prepared data | `dist/1.0.0/scu_lightning_complex_2020/` | 146.57 MB |
| `slater_and_devil_2020` | Prepared data | `dist/1.0.0/slater_and_devil_2020/` | 101.32 MB |
| `sqf_complex_2020` | Prepared data | `dist/1.0.0/sqf_complex_2020/` | 311.29 MB |
| `tamarack_2021` | Prepared data | `dist/1.0.0/tamarack_2021/` | 83.66 MB |
| `thomas_fire` | Implemented case | `dist/1.0.0/thomas_fire/` | 22.91 MB |
| `tubbs_fire` | Implemented case | `dist/1.0.0/tubbs_fire/` | 6.03 MB |
| `w_5_cold_springs_2020` | Prepared data | `dist/1.0.0/w_5_cold_springs_2020/` | 51.48 MB |
| `walker_2019` | Prepared data | `dist/1.0.0/walker_2019/` | 30.98 MB |
| `windy_2021` | Prepared data | `dist/1.0.0/windy_2021/` | 103.02 MB |
| `zogg_2020` | Prepared data | `dist/1.0.0/zogg_2020/` | 18.73 MB |

Sizes include all files in each dataset folder and use decimal MB.

## Restore and verify

From a downloaded dataset folder, run:

```bash
python3 stage_dataset.py --case-dir /path/to/restored-case --manifest dataset_manifest.json --bundle-dir .
```

Replace `/path/to/restored-case` with the destination directory. The script
restores inputs, observations, and provenance and verifies their file sizes and
SHA-256 hashes. Add `--include-optional` to restore historical outputs and older
inputs when included. Python 3 is required; no additional packages are needed.

From the repository root, verify the retained dataset folders with:

```bash
make zenodo-verify
make zenodo-verify CASE=antelope_2021
```

After restoration, the following command also checks the extracted source files:

```bash
python3 tools/prepare_zenodo.py verify --case FIRE_ID --check-sources
```
 File integrity checks
establish agreement with the archived snapshot. Scientific validation requires
running the corresponding case and evaluating its results. The 24 datasets prepared
for future cases do not include current runnable case configurations or
evaluation criteria.

## License and provenance

The selected dataset license is CC BY 4.0. Metadata worksheets under `metadata/`
contain source citations, applicable terms, and redistribution evidence. Known
permission gaps remain documented for separately supplied inputs and other
third-party material. The archived source manifests retain the provenance
available when the files were received.

The [upload guide](../docs/zenodo-upload-guide.md) describes metadata review,
publication, DOI registration, and verification of downloaded records. To update
the README and metadata copies in the retained dataset folders and refresh their
checksums, run `python3 tools/prepare_zenodo.py metadata`. For a new dataset
version, restore its source files and run:

```bash
make zenodo-build CASE=FIRE_ID DATASET_VERSION=1.0.1
```

## Acknowledgement

OpenAI Codex assisted with archive preparation, metadata organization, and
drafting the accompanying documentation.
