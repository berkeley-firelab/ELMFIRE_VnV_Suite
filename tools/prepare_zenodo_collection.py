#!/usr/bin/env python3
"""Build, verify, or register one Zenodo record containing all fire datasets."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import tarfile
import tempfile

from prepare_zenodo import ROOT, GOFER_CREDIT, upload_checksums, verify_upload_set, write_json
from zenodo_restore import check_file, sha256


def definition(case_id: str) -> Path:
    active = ROOT / 'cases/Validation/landscape_scale' / case_id
    return active if (active / 'case.yaml').is_file() else ROOT / 'zenodo/datasets' / case_id


def collection_metadata(version: str, paths: list[Path]) -> dict:
    worksheets = {path.name: json.loads((ROOT / 'zenodo/metadata' / (path.name + '.json')).read_text())
                  for path in paths}
    creators = worksheets['antelope_2021']['creators'] + worksheets['camp_fire']['creators']
    description = (
        'This collection contains model inputs, fire observations, and provenance records '
        'for 31 wildfires used in ELMFIRE validation studies. Seven datasets support '
        'implemented validation cases; 24 contain data for future cases. Each fire has '
        'a separate archive containing input, observation, and provenance bundles, '
        'file inventories, checksums, a README, and a Python restoration script. '
        'Historical model outputs and older inputs are included where available. '
        'Camp, Thomas, and Tubbs contain VIIRS active-fire observations; the other '
        '28 fires contain GOFER-derived arrival-time observations.\n\n'
        'Chris Lautenberger and Daniel San Martin are credited for the 28 GOFER-related '
        'fire datasets. Dwi M. J. Purnomo, Maria Theodori, and Kasra Shamsaei are credited '
        'for Camp, Thomas, and Tubbs.\n\n' + GOFER_CREDIT + '\n\n'
        'Known limitations: the exact GOFER source version and complete transformation '
        'history remain unverified. Upstream products and the exact VIIRS collections '
        'for Camp, Thomas, and Tubbs are incompletely identified. Redistribution terms '
        'for separately supplied model inputs and other third-party material remain '
        'under review. These limitations are documented in the per-fire metadata and '
        'source manifests. File integrity does not establish model accuracy.\n\n'
        'Acknowledgement: OpenAI Codex assisted with archive preparation, metadata '
        'organization, and drafting the accompanying documentation.'
    )
    return {'worksheet_format': 'human review fields; not a Zenodo API payload',
            'resource_type': 'Dataset',
            'title': 'ELMFIRE validation inputs and observations for 31 wildfires',
            'version': version, 'publication_date': '2026-10-22',
            'creators': creators, 'license': 'CC-BY-4.0', 'description': description,
            'keywords': ['ELMFIRE', 'wildfire', 'validation', 'GOFER', 'VIIRS'],
            'related_identifiers': worksheets['antelope_2021']['related_identifiers'],
            'redistribution_permission_evidence': {
                'GOFER': worksheets['antelope_2021']['redistribution_permission_evidence'],
                'other_sources': 'See per-fire metadata worksheets and source manifests; unresolved.'},
            'review_status': 'draft; complete-bundle redistribution review pending'}


def readme(manifest: dict) -> str:
    rows = '\n'.join(f'  {entry["filename"]}' for entry in manifest['fires'])
    return (
        f'ELMFIRE validation datasets\nCollection version: {manifest["dataset_version"]}\n\n'
        'This collection contains model inputs, fire observations, and provenance\n'
        'records for 31 wildfires. Seven datasets support implemented validation\n'
        'cases; 24 contain data for future cases. Each fire is stored in a separate\n'
        'uncompressed .tar container holding compressed data bundles and supporting\n'
        'files. Source file contents are preserved.\n\n'
        'Contents\n--------\n'
        '<fire_id>.tar: inputs.tar.gz, observations.tar.gz, provenance.tar.gz, a\n'
        'dataset manifest, metadata worksheet, README, checksums, and restoration\n'
        'script. Historical outputs and older inputs are included where available.\n'
        'collection_manifest.json: fire inventory, sizes, and SHA-256 hashes of the\n'
        'containers and their contents, including the per-fire dataset manifests.\n'
        'metadata-worksheet.json: collection description, creators, citations,\n'
        'license, and redistribution evidence.\n'
        'stage_collection.py: restores and verifies one selected fire dataset.\n'
        'stage_dataset.py: shared extraction and integrity verification functions.\n'
        'checksums.sha256: SHA-256 hashes of the other files in this record.\n\n'
        'Restoration\n-----------\n'
        'Download this README, collection_manifest.json, both Python scripts, and\n'
        'the .tar file for the desired fire. From the download folder, run:\n\n'
        'python3 stage_collection.py --case camp_fire --case-dir /path/to/camp_fire --archive-dir .\n\n'
        'Replace camp_fire with the desired fire ID. Add --include-optional for\n'
        'historical outputs or older inputs. Python 3 is required; no additional\n'
        'packages are needed. The script verifies hashes and protects differing\n'
        'existing files. It retains compressed bundles in data/.zenodo-cache/.\n\n'
        'Observations and provenance\n---------------------------\n'
        'Camp, Thomas, and Tubbs include VIIRS active-fire point observations. The\n'
        'other 28 fires include arrival-time rasters derived from GOFER. Full GOFER\n'
        'attribution and known source-version limitations are recorded in the\n'
        'collection and per-fire metadata worksheets. Source manifests describe\n'
        'data origins, preparation steps, and known provenance gaps. Historical\n'
        'model results are stored separately from observations.\n\n'
        'License: CC BY 4.0. Source-specific terms and unresolved redistribution\n'
        'permissions are documented in the metadata and provenance manifests.\n'
        'File integrity checks establish agreement with the archived snapshot;\n'
        'scientific validation requires a separate evaluation of model results.\n\n'
        'Case definitions and evaluation methods:\n'
        'https://github.com/berkeley-firelab/ELMFIRE_VnV_Suite\n\n'
        'Fire archives\n-------------\n' + rows + '\n\n'
        'Acknowledgement\n---------------\n'
        'OpenAI Codex assisted with archive preparation, metadata organization, and\n'
        'drafting the accompanying documentation.\n'
    )


def build(source: Path, output: Path, version: str) -> None:
    if output.exists():
        raise ValueError(f'Output exists; choose a new output folder: {output}')
    paths = sorted(path for path in source.iterdir() if (path / 'dataset_manifest.json').is_file())
    if len(paths) != 31:
        raise ValueError('Expected exactly 31 prepared fire datasets.')
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='collection-', dir=output.parent) as temporary:
        work = Path(temporary)
        manifest = {'schema_version': 1, 'dataset_version': version,
                    'zenodo': {'record_id': None, 'version_doi': None, 'concept_doi': None}, 'fires': []}
        for path in paths:
            verify_upload_set(definition(path.name), path)
            files = [{'path': file.name, 'size': file.stat().st_size, 'sha256': sha256(file)}
                     for file in sorted(path.iterdir()) if file.is_file()]
            target = work / (path.name + '.tar')
            with tarfile.open(target, 'w', format=tarfile.PAX_FORMAT) as archive:
                for record in files:
                    info = tarfile.TarInfo(record['path'])
                    info.size, info.mode, info.mtime = record['size'], 0o644, 0
                    with (path / record['path']).open('rb') as stream:
                        archive.addfile(info, stream)
            manifest['fires'].append({'case_id': path.name, 'filename': target.name,
                'size': target.stat().st_size, 'sha256': sha256(target), 'url': None,
                'files': files, 'dataset_manifest': json.loads((path / 'dataset_manifest.json').read_text())})
            print(f'[OK] collection archive: {path.name}', flush=True)
        write_json(work / 'collection_manifest.json', manifest)
        write_json(work / 'metadata-worksheet.json', collection_metadata(version, paths))
        (work / 'README.txt').write_text(readme(manifest))
        shutil.copyfile(ROOT / 'tools/restore_zenodo_collection.py', work / 'stage_collection.py')
        shutil.copyfile(ROOT / 'tools/zenodo_restore.py', work / 'stage_dataset.py')
        upload_checksums(work)
        work.rename(output)
    write_json(ROOT / 'zenodo/collection_manifest.json', manifest)
    write_json(ROOT / 'zenodo/collection-metadata.json', collection_metadata(version, paths))


def verify(output: Path) -> None:
    manifest = json.loads((output / 'collection_manifest.json').read_text())
    for entry in manifest['fires']:
        check_file(output / entry['filename'], entry)
        expected = {record['path']: record for record in entry['files']}
        with tarfile.open(output / entry['filename'], 'r|') as archive:
            seen = set()
            for member in archive:
                if member.name not in expected or member.name in seen or not member.isfile():
                    raise ValueError(f'Unexpected archive member: {member.name}')
                record = expected[member.name]
                import hashlib
                digest = hashlib.sha256()
                stream = archive.extractfile(member)
                for block in iter(lambda: stream.read(1024 * 1024), b''):
                    digest.update(block)
                if member.size != record['size'] or digest.hexdigest() != record['sha256']:
                    raise ValueError(f'Archive member mismatch: {member.name}')
                seen.add(member.name)
            if seen != set(expected):
                raise ValueError('Missing archive members.')
    for line in (output / 'checksums.sha256').read_text().splitlines():
        expected, name = line.split('  ', 1)
        if sha256(output / name) != expected:
            raise ValueError(f'Checksum mismatch: {name}')
    print(f'[OK] collection: verified {len(manifest["fires"])} fires')


def register(output: Path, record_id: str, doi: str) -> None:
    if not record_id.isdigit() or doi != f'10.5281/zenodo.{record_id}':
        raise ValueError('Use a production record ID and matching version DOI.')
    path = ROOT / 'zenodo/collection_manifest.json'
    manifest = json.loads(path.read_text())
    if manifest['zenodo']['record_id']:
        raise ValueError('Collection is already registered.')
    manifest['zenodo'].update(record_id=record_id, version_doi=doi)
    for entry in manifest['fires']:
        entry['url'] = f'https://zenodo.org/records/{record_id}/files/{entry["filename"]}?download=1'
        case_path = definition(entry['case_id']) / 'data/dataset_manifest.json'
        data = json.loads(case_path.read_text())
        if data['zenodo'].get('record_id'):
            raise ValueError(f'Case already registered: {entry["case_id"]}')
    for entry in manifest['fires']:
        case_path = definition(entry['case_id']) / 'data/dataset_manifest.json'
        data = json.loads(case_path.read_text())
        data['zenodo'] = dict(manifest['zenodo'], collection_archive=entry)
        write_json(case_path, data)
    write_json(path, manifest)
    print('[OK] Registered one collection DOI for all 31 fires.')


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('build', 'verify', 'register'))
    parser.add_argument('--version', default='1.0.0')
    parser.add_argument('--source', type=Path)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--record-id')
    parser.add_argument('--doi')
    args = parser.parse_args()
    output = args.output or ROOT / 'zenodo/dist' / ('collection-' + args.version)
    if args.action == 'build':
        build(args.source or ROOT / 'zenodo/dist' / args.version, output, args.version)
    elif args.action == 'verify':
        verify(output)
    else:
        if not args.record_id or not args.doi:
            parser.error('register requires --record-id and --doi')
        register(output, args.record_id, args.doi)


if __name__ == '__main__':
    main()
