# Uploading the ELMFIRE validation collection to Zenodo

Publish one Zenodo Dataset record containing all 31 fires. Each fire is stored in
its own `.tar` container, preserving the existing compressed bundles, metadata,
checksums, and restoration helper. The upload folder is
`zenodo/dist/collection-1.0.0/`. It contains 37 files totaling about 7.10 GB.

## Prepare and verify

The per-fire folders under `zenodo/dist/1.0.0/` are local staging inputs. To
refresh their metadata, README files, restoration scripts, and checksums, run:

```bash
python3 tools/prepare_zenodo.py metadata
python3 tools/prepare_zenodo.py verify
```

Build the combined upload from those folders:

```bash
python3 tools/prepare_zenodo_collection.py build
python3 tools/prepare_zenodo_collection.py verify
```

A build refuses to replace an existing collection folder. To rebuild an
unpublished collection, specify a new `--output` folder. For scientific changes
after publication, prepare a new version and retain the previous archives.
The outer containers do not recompress or modify the inner scientific bundles.

The tracked `zenodo/collection_manifest.json` contains the fire inventories and
hashes. The tracked `zenodo/collection-metadata.json` is the collection metadata
worksheet. Their upload copies are `collection_manifest.json` and
`metadata-worksheet.json`, respectively.

## Review the metadata

Use the collection title, date, version, creators, description, keywords, license,
and related identifiers from `zenodo/collection-metadata.json`. All five dataset
creators appear in the combined citation. The description explains their roles:
Chris Lautenberger and Daniel San Martin for 28 fires; Dwi M. J. Purnomo, Maria
Theodori, and Kasra Shamsaei for Camp, Thomas, and Tubbs. Per-fire metadata retains
these groups. Kasra's verified ORCID is `0000-0003-3396-7683`; omit the literal
`unknown` from ORCID form fields for the other creators.

The license is CC BY 4.0, matching the
[GOFER version 0.2 record](https://zenodo.org/records/14642378). Keep the full GOFER
attribution, source DOI, license link, and derived-data description. The exact
GOFER version used for the supplied rasters remains unverified; the version 0.2
record provides license evidence. Retain the all-versions source DOI until the
actual source version is established.

GOFER's license does not establish permission for separately supplied model
inputs, historical results, or the Camp, Thomas, and Tubbs source products.
Obtain original product names, versions, license URLs, or written redistribution
permission from the providers or rights holders. For VIIRS observations, identify
the exact FIRMS product and collection and retain the applicable terms and
attribution. Preserve unresolved provenance and rights statements in the record
description. Keep the record unpublished while the review remains unresolved.

## Prepare the browser draft

1. Open the existing Zenodo draft or select **New upload**.
2. Set the resource type to **Dataset** and use the collection metadata.
3. Reserve a new DOI for this prepared collection. Do not reuse the GOFER DOI.
4. Upload all 37 files directly from `zenodo/dist/collection-1.0.0/`.
5. Retain the filenames and verify that every upload reaches 100%.
6. Select **Save draft**, then preview the record. Stop here for review.

The six collection support files are `README.txt`, `collection_manifest.json`,
`metadata-worksheet.json`, `checksums.sha256`, `stage_collection.py`, and
`stage_dataset.py`. The remaining 31 files are the fire `.tar` archives. All
fires share one collection DOI and version history.

## Register after publication

Only after the collection is published, register its production record ID and
specific version DOI:

```bash
python3 tools/prepare_zenodo_collection.py register --record-id RECORD_ID --doi 10.5281/zenodo.RECORD_ID
```

This updates the tracked collection and per-case manifests with the same DOI
and each fire's archive URL. It does not publish anything. The inner uploaded
manifests may retain empty DOI fields; their file hashes describe the same data.
Do not modify published files to insert their own DOI. The original per-fire
registration command is retained for older independent deposits and is not used
for this collection.

## Restore a selected fire

For a local or manually downloaded fire archive, run:

```bash
python3 tools/restore_zenodo_collection.py --case camp_fire --case-dir /path/to/camp_fire --manifest zenodo/collection_manifest.json --archive-dir zenodo/dist/collection-1.0.0
```

The standalone upload helper `stage_collection.py` accepts the same options and
defaults to `collection_manifest.json` beside the script. Both Python scripts
must be present. Add `--include-optional` for supplied historical outputs and
older inputs. Extracted bundles are cached under the destination's
`data/.zenodo-cache/` and verified before scientific files are restored.

After publication and registration, test the shared record from an empty
destination, using an explicit download:

```bash
python3 tools/restore_zenodo_collection.py --case camp_fire --case-dir /path/to/fresh-camp --manifest zenodo/collection_manifest.json --download --include-optional
```

The standard case-local helper also supports the shared record after registration:

```bash
python3 cases/Validation/landscape_scale/camp_fire/scripts/stage_dataset.py --download --include-optional
```

Use a different destination for a fresh-download check so local source files
cannot hide missing remote files. Hash checks establish data integrity, not
successful simulation or scientific validation.

## Prepare later versions

For changed scientific files, first build each affected per-fire staging set
with a new version. Prepare all 31 staging folders for the same collection
version, then build the combined record with matching arguments:

```bash
python3 tools/prepare_zenodo_collection.py build --version 1.0.1 --source /path/to/staging/1.0.1 --output zenodo/dist/collection-1.0.1
```

Create a new version of the existing Zenodo collection, upload its full file set,
review and publish it, register the new version DOI, and repeat the download
checks. Preserve earlier versions for reproducibility.
