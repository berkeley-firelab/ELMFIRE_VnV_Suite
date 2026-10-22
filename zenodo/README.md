# Zenodo validation datasets

Prepare one independently versioned Zenodo Dataset record per fire. All 31
fires have their own upload folder under `dist/1.0.0/<fire_id>/`, metadata
worksheet, checksum manifest, and restoration helper. Generated upload files
are ignored by Git. The combined GOFER upload has been retired.

The archived validation inputs, observations and optional historical/legacy
payloads are also untracked and ignored. Local copies are preserved. Git keeps
the 31 dataset manifests (bundle and file SHA-256 hashes plus publication
fields), source provenance, metadata worksheets and independent restore helpers.
Record IDs and version DOIs remain blank until publication is registered;
offline restoration uses the retained upload folders in the meantime.

Follow [the upload guide](../docs/zenodo-upload-guide.md) for metadata review,
publication, DOI registration, and fresh-download checks. Creator fields remain
blank. The worksheets are human review aids, not Zenodo API requests; license
and redistribution fields also require completion.

| Fire ID | Case status | Upload folder | Compressed size |
| --- | --- | --- | ---: |
| `antelope_2021` | Data for future case | `dist/1.0.0/antelope_2021/` | 200.35 MB |
| `august_complex_2020` | Data for future case | `dist/1.0.0/august_complex_2020/` | 1226.38 MB |
| `beckwourth_complex_2021` | Data for future case | `dist/1.0.0/beckwourth_complex_2021/` | 155.53 MB |
| `bobcat_2020` | Data for future case | `dist/1.0.0/bobcat_2020/` | 91.38 MB |
| `caldor_2021` | Implemented case | `dist/1.0.0/caldor_2021/` | 211.12 MB |
| `camp_fire` | Implemented case | `dist/1.0.0/camp_fire/` | 24.07 MB |
| `creek_2020` | Data for future case | `dist/1.0.0/creek_2020/` | 755.26 MB |
| `czu_lightning_complex_2020` | Implemented case | `dist/1.0.0/czu_lightning_complex_2020/` | 30.58 MB |
| `dixie_2021` | Data for future case | `dist/1.0.0/dixie_2021/` | 1149.70 MB |
| `dolan_2020` | Data for future case | `dist/1.0.0/dolan_2020/` | 145.90 MB |
| `glass_2020` | Implemented case | `dist/1.0.0/glass_2020/` | 43.33 MB |
| `july_complex_2020` | Data for future case | `dist/1.0.0/july_complex_2020/` | 64.94 MB |
| `kincade_2019` | Implemented case | `dist/1.0.0/kincade_2019/` | 57.98 MB |
| `knp_complex_2021` | Data for future case | `dist/1.0.0/knp_complex_2021/` | 120.23 MB |
| `lnu_lightning_complex_2020` | Data for future case | `dist/1.0.0/lnu_lightning_complex_2020/` | 252.15 MB |
| `mccash_2021` | Data for future case | `dist/1.0.0/mccash_2021/` | 207.26 MB |
| `mcfarland_2021` | Data for future case | `dist/1.0.0/mcfarland_2021/` | 124.79 MB |
| `monument_2021` | Data for future case | `dist/1.0.0/monument_2021/` | 279.47 MB |
| `north_complex_2020` | Data for future case | `dist/1.0.0/north_complex_2020/` | 385.52 MB |
| `red_salmon_complex_2020` | Data for future case | `dist/1.0.0/red_salmon_complex_2020/` | 302.29 MB |
| `river_complex_2021` | Data for future case | `dist/1.0.0/river_complex_2021/` | 389.75 MB |
| `scu_lightning_complex_2020` | Data for future case | `dist/1.0.0/scu_lightning_complex_2020/` | 146.57 MB |
| `slater_and_devil_2020` | Data for future case | `dist/1.0.0/slater_and_devil_2020/` | 101.32 MB |
| `sqf_complex_2020` | Data for future case | `dist/1.0.0/sqf_complex_2020/` | 311.29 MB |
| `tamarack_2021` | Data for future case | `dist/1.0.0/tamarack_2021/` | 83.66 MB |
| `thomas_fire` | Implemented case | `dist/1.0.0/thomas_fire/` | 22.91 MB |
| `tubbs_fire` | Implemented case | `dist/1.0.0/tubbs_fire/` | 6.03 MB |
| `w_5_cold_springs_2020` | Data for future case | `dist/1.0.0/w_5_cold_springs_2020/` | 51.48 MB |
| `walker_2019` | Data for future case | `dist/1.0.0/walker_2019/` | 30.97 MB |
| `windy_2021` | Data for future case | `dist/1.0.0/windy_2021/` | 103.02 MB |
| `zogg_2020` | Data for future case | `dist/1.0.0/zogg_2020/` | 18.73 MB |

The 31 upload sets total about 7.09 GB and contain 1178
archived source files, counting the small shared provenance copied into each
independent record. Sizes use decimal MB/GB and include upload sidecars.
Metadata edits can slightly change these sizes.

The seven implemented cases retain their definitions in `cases/Validation/landscape_scale/`.
The 24 additional fires have definitions under
`zenodo/datasets/<fire_id>/`. Those definitions prepare data for
future validation cases without adding runnable configurations or acceptance
criteria. Every additional record has `inputs.tar.gz`, `observations.tar.gz`,
`provenance.tar.gz`, and five sidecars. Shared preparation evidence is included
in each small provenance bundle; other fires' scientific payloads are excluded.

```bash
# Verify all 31 records from the repository root.
make zenodo-verify

# Verify one fire or the 24 additional GOFER fires.
make zenodo-verify CASE=antelope_2021
make zenodo-verify CASE=gofer

# Build a new version for one fire, preserving previous uploads.
make zenodo-build CASE=antelope_2021 DATASET_VERSION=1.0.1
```

The initial upload sets already exist locally. Builds refuse to replace an
existing upload folder. The redundant GOFER collection has been removed after all its source files
were checked against the prepared archives. Its inventory is retained under
`provenance/gofer_archive_inventory.json`. Historical `repository_source`
fields are provenance only; packaging reads restored case-local files.
`make zenodo-verify` checks retained upload files without needing extracted
source copies. For an additional source check after restoration, run
`python3 tools/prepare_zenodo.py verify --case FIRE_ID --check-sources`.
To build a new version of a future-case dataset, restore its bundles into
`zenodo/datasets/<fire_id>/` first, then use `make zenodo-build`. Use a separate version DOI for every fire record.
