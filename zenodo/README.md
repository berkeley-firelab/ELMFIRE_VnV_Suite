# ELMFIRE validation data collection

Version 2.1.0 contains data for 31 wildfires in one combined record. The local
upload is `dist/collection-2.1.0/`: 31 fire archives and six metadata/restoration
support files, totaling about 7.05 GB.

Each fire archive contains input rasters, required fuel-model and ignition
tables, comparison observations, and supplied data-generation code. Historical
simulation outputs, runners, model configurations, reports, superseded inputs
and caches are excluded. Case workflows and current configurations remain in
the repository. Source metadata, hashes, attribution and source limitations
are retained in the dataset manifests and metadata worksheets.

Inputs restore to `data/weather/`, `data/fuels_and_topography/` and `data/misc/`.
Comparison observations restore to `data/observation/`. Generation source code
restores to `scripts/generate_data/` for the 28 GOFER datasets. Those scripts
include input preparation and CAL FIRE final-perimeter generation. All 28
GOFER fires contain arrival-time TIFFs and PNG previews, final-perimeter
GeoPackages and aligned 30 m mask TIFFs. The original sources and case-local
entry points are included. They need upstream source data and CloudFire access;
regeneration from those sources has not been verified against frozen hashes.
The GOFER arrival-time TIFF/PNG generator was not provided. Camp, Thomas and
Tubbs have no supplied input generator.

## Restore and verify

```bash
python3 stage_collection.py --case camp_fire --case-dir /path/to/restored-data --archive-dir .
```

Download the desired fire archive, collection_manifest.json and both Python
helpers first. Restoration verifies hashes and refuses differing existing
files. To run a case, restore into a clone containing the current workflow.

From the repository root:

```bash
python3 tools/prepare_zenodo_collection.py verify --version 2.1.0
```

The per-fire folders under `dist/2.1.0/` are local staging inputs for the combined
record. The browser draft has not been replaced with this new file set.
See the [upload guide](../docs/zenodo-upload-guide.md) before publication.

## Fire archives

| Fire ID | Archive | Size |
| --- | --- | ---: |
| `antelope_2021` | `antelope_2021.tar` | 201.08 MB |
| `august_complex_2020` | `august_complex_2020.tar` | 1228.69 MB |
| `beckwourth_complex_2021` | `beckwourth_complex_2021.tar` | 155.69 MB |
| `bobcat_2020` | `bobcat_2020.tar` | 91.79 MB |
| `caldor_2021` | `caldor_2021.tar` | 196.28 MB |
| `camp_fire` | `camp_fire.tar` | 10.84 MB |
| `creek_2020` | `creek_2020.tar` | 756.66 MB |
| `czu_lightning_complex_2020` | `czu_lightning_complex_2020.tar` | 30.83 MB |
| `dixie_2021` | `dixie_2021.tar` | 1152.01 MB |
| `dolan_2020` | `dolan_2020.tar` | 146.06 MB |
| `glass_2020` | `glass_2020.tar` | 35.25 MB |
| `july_complex_2020` | `july_complex_2020.tar` | 65.01 MB |
| `kincade_2019` | `kincade_2019.tar` | 29.64 MB |
| `knp_complex_2021` | `knp_complex_2021.tar` | 120.84 MB |
| `lnu_lightning_complex_2020` | `lnu_lightning_complex_2020.tar` | 252.83 MB |
| `mccash_2021` | `mccash_2021.tar` | 208.97 MB |
| `mcfarland_2021` | `mcfarland_2021.tar` | 125.02 MB |
| `monument_2021` | `monument_2021.tar` | 280.09 MB |
| `north_complex_2020` | `north_complex_2020.tar` | 386.03 MB |
| `red_salmon_complex_2020` | `red_salmon_complex_2020.tar` | 302.96 MB |
| `river_complex_2021` | `river_complex_2021.tar` | 392.55 MB |
| `scu_lightning_complex_2020` | `scu_lightning_complex_2020.tar` | 146.89 MB |
| `slater_and_devil_2020` | `slater_and_devil_2020.tar` | 101.78 MB |
| `sqf_complex_2020` | `sqf_complex_2020.tar` | 312.84 MB |
| `tamarack_2021` | `tamarack_2021.tar` | 84.09 MB |
| `thomas_fire` | `thomas_fire.tar` | 22.07 MB |
| `tubbs_fire` | `tubbs_fire.tar` | 4.61 MB |
| `w_5_cold_springs_2020` | `w_5_cold_springs_2020.tar` | 51.81 MB |
| `walker_2019` | `walker_2019.tar` | 31.18 MB |
| `windy_2021` | `windy_2021.tar` | 103.52 MB |
| `zogg_2020` | `zogg_2020.tar` | 18.88 MB |

The selected license is CC BY 4.0. Full GOFER attribution, source-specific terms,
and unresolved redistribution evidence are retained in the metadata worksheets.

## Acknowledgement

OpenAI Codex assisted with archive preparation, metadata organization, and
drafting the accompanying documentation.
