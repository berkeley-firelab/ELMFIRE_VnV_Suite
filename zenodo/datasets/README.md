# Data for future validation cases

These 24 definitions retain current input data, comparison observations and
supplied input and observation-generation scripts. They are data sets for future cases, not
runnable validation configurations. Each is included as `<fire_id>.tar` in the
combined `../dist/collection-2.1.0/` record. Historical results, original model
configurations, legacy runners and source caches have been removed.

Current data restore to `data/weather/`, `data/fuels_and_topography/`, `data/misc/`
and `data/observation/`. Supplied data-generation code restores to
`scripts/generate_data/`. Archive and source manifests remain in the repository;
source metadata is embedded in each archived dataset manifest.

From the repository root:

```bash
python3 tools/restore_zenodo_collection.py --case antelope_2021 --case-dir /path/to/antelope_2021 --manifest zenodo/collection_manifest.json --archive-dir zenodo/dist/collection-2.1.0
```

See each generator README for external source requirements and limitations.
Each case includes GOFER arrival-time TIFFs and PNG previews, a CAL FIRE
final-perimeter GeoPackage, and an aligned 30 m mask TIFF. CAL FIRE generation
source is included; the GOFER arrival-time TIFF/PNG generator was not provided.
See the collection upload guide before publishing.
