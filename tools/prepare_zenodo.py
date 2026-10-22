#!/usr/bin/env python3
"""Build reproducible per-case Zenodo bundles; verify or register a published record.

Packaging reads scientific files without modifying them. No command uploads,
publishes, removes tracked data, or runs ELMFIRE. Python standard library only.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import gzip
import json
from pathlib import Path
import re
import shutil
import subprocess
import tarfile
import tempfile

from zenodo_restore import check_file, destination, selected_bundles, sha256

ROOT = Path(__file__).resolve().parents[1]
CASE_ROOT = ROOT / 'cases/Validation/landscape_scale'
DATASET_ROOT = ROOT / 'zenodo/datasets'
ROLES = ('inputs', 'observations', 'provenance', 'historical_outputs', 'legacy_inputs')
OPTIONAL = {'historical_outputs', 'legacy_inputs'}


def identifier(case: Path) -> str:
    return case.name


def source_file(case: Path, record: dict) -> Path:
    # Legacy repository_source fields describe original locations only.
    # Rebuilds read normalized case-local files restored from the upload set.
    return destination(case, record['path'])


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n')


def upload_checksums(directory: Path) -> None:
    files = sorted(p for p in directory.iterdir() if p.is_file() and p.name != 'checksums.sha256')
    (directory / 'checksums.sha256').write_text(''.join(f'{sha256(p)}  {p.name}\n' for p in files))


def file_record(case: Path, relative: str) -> dict:
    path = destination(case, relative)
    if not path.is_file():
        raise ValueError(f'Missing source file: {path}')
    return {'path': relative, 'size': path.stat().st_size, 'sha256': sha256(path)}


def inventory(case: Path) -> dict[str, list[dict]]:
    """Use existing provenance manifests as the authoritative source inventory."""
    archive = json.loads((case / 'data/archive_manifest.json').read_text())
    if 'source_files' in archive:
        grouped = defaultdict(list)
        for record in archive['source_files']:
            check_file(source_file(case, record), record)
            grouped[record['role']].append(record)
        for name in ('archive_manifest.json', 'source_manifest.json'):
            grouped['provenance'].append(file_record(case, 'data/' + name))
        for files in grouped.values():
            files.sort(key=lambda r: r['path'])
        return grouped
    source = json.loads((case / 'data/source_manifest.json').read_text())
    records = {}
    for original in archive.get('files', archive.get('payload_files', [])):
        relative = original.get('path', original.get('relative_path'))
        check_file(destination(case, relative), original)
        role = ('observations' if '/observations/' in relative else
                'historical_outputs' if '/outputs/' in relative else
                'provenance' if '/provenance/' in relative or relative.endswith('/01-run.sh') else
                'inputs')
        records[relative] = (role, file_record(case, relative))
    for original in source.get('observation', {}).get('files', []):
        relative = original.get('path', original.get('relative_path'))
        check_file(destination(case, relative), original)
        records[relative] = ('observations', file_record(case, relative))
    # Small authored provenance/configuration records travel with the dataset.
    for path in sorted((case / 'data').glob('*.json')):
        if path.name != 'dataset_manifest.json':
            relative = path.relative_to(case).as_posix()
            records[relative] = ('provenance', file_record(case, relative))
    for relative in ('case.yaml', 'elmfire.data.in'):
        records[relative] = ('provenance', file_record(case, relative))
    # Preserve distinct, inactive historical inputs as a clearly optional bundle.
    for folder in ('fuels_and_topography', 'weather', 'misc'):
        for path in sorted((case / 'data' / folder).rglob('*')):
            if path.is_file() and not path.name.startswith(('.', '._')):
                relative = path.relative_to(case).as_posix()
                records[relative] = ('legacy_inputs', file_record(case, relative))
    # Do not silently omit unmanifested scientific payload or observation files.
    for folder in ('archive_payload', 'provenance/archive', 'viirs_observation'):
        for path in (case / 'data' / folder).rglob('*'):
            if path.is_file() and not path.name.startswith('.'):
                relative = path.relative_to(case).as_posix()
                if relative not in records:
                    raise ValueError(f'Unmanifested source file: {path}')
    grouped = defaultdict(list)
    for relative, (role, record) in sorted(records.items()):
        grouped[role].append(record)
    if not grouped['inputs'] or not grouped['observations']:
        raise ValueError(f'Missing input or observation inventory: {case.name}')
    return grouped


def write_bundle(case: Path, path: Path, files: list[dict]) -> None:
    """Normalize container metadata, preserving the exact file contents."""
    with path.open('wb') as raw:
        with gzip.GzipFile(fileobj=raw, mode='wb', filename='', mtime=0) as compressed:
            with tarfile.open(fileobj=compressed, mode='w', format=tarfile.PAX_FORMAT) as archive:
                for record in files:
                    source = source_file(case, record)
                    check_file(source, record)
                    info = tarfile.TarInfo(record['path'])
                    info.size = record['size']
                    info.mode = 0o644
                    info.mtime = 0
                    with source.open('rb') as stream:
                        archive.addfile(info, stream)


def build_case(case: Path, output: Path, version: str, source_revision: str) -> dict:
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]*', version):
        raise ValueError('Use a simple dataset version, for example 1.0.0.')
    dataset_id = identifier(case)
    target = output / dataset_id
    if target.exists():
        raise ValueError(f'Output already exists; choose a new --output directory: {target}')
    grouped = inventory(case)
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=dataset_id + '-', dir=output) as tmp:
        work = Path(tmp)
        manifest = {'schema_version': 1, 'case_id': dataset_id, 'dataset_version': version,
                    'source_revision': source_revision,
                    'source_state': 'working tree snapshot; file hashes are authoritative',
                    'zenodo': {'record_id': None, 'version_doi': None, 'concept_doi': None},
                    'bundles': []}
        definition = json.loads((case / 'data/archive_manifest.json').read_text())
        if 'source_files' in definition:
            manifest['dataset_kind'] = 'future_validation_case'
            manifest['fire_id'] = definition['fire_id']
        for key in ROLES:
            if not grouped[key]:
                continue
            role = key
            filename = key + '.tar.gz'
            write_bundle(case, work / filename, grouped[key])
            bundle = {'role': role, 'filename': filename,
                'required': role not in OPTIONAL, 'size': (work / filename).stat().st_size,
                'sha256': sha256(work / filename), 'url': None, 'files': grouped[key]}
            manifest['bundles'].append(bundle)
        write_json(work / 'dataset_manifest.json', manifest)
        (work / 'README.txt').write_text(
            f'ELMFIRE validation data: {case.name}\nDataset version: {version}\n\n'
            'Upload all files in this directory to one Zenodo dataset record.\n'
            'inputs.tar.gz: canonical frozen model inputs.\n'
            'observations.tar.gz: exact comparison observations and sidecars.\n'
            'provenance.tar.gz: source manifests, preparation evidence and configuration snapshot.\n'
            'historical_outputs.tar.gz, if present: optional supplied past simulation results.\n'
            'legacy_inputs.tar.gz, if present: optional inactive, distinct older inputs.\n\n'
            'Archive members are paths relative to the case root. Use the case-local\n'
            'scripts/stage_dataset.py to verify and restore them without overwriting\n'
            'differing files. The current case code is distributed in the GitHub repo:\n'
            'https://github.com/berkeley-firelab/ELMFIRE_VnV_Suite\n\n'
            'The dataset manifest lists SHA-256 hashes of every bundle and source file.\n'
            'The original source/archive manifests retain provenance gaps. Bundling\n'
            'does not establish an upstream license, experimental independence,\n'
            'historical executable identity, or a scientific PASS. Metadata worksheet\n'
            'fields must be completed before publication; see the repository guide.\n'
            'Original RAR/source archives are not included. No missing CZU historical\n'
            'outputs are reconstructed. Current generated simulation/report products\n'
            'Other fire datasets are published in separate records.\n')
        if manifest.get('dataset_kind') == 'future_validation_case':
            with (work / 'README.txt').open('a') as stream:
                stream.write('\nThis fire has its own independent dataset record for a future\n'
                    'validation case. Inputs restore to data/archive_payload/inputs/;\n'
                    'observations restore to data/archive_payload/observations/.\n'
                    'Original shared preparation records and this fire launcher are\n'
                    'preserved under data/provenance/archive/. No other fire payload\n'
                    'is included. Case execution scripts will be authored separately.\n')
        with (work / 'README.txt').open('a') as stream:
            stream.write('\nTo restore from this downloaded folder into a new directory:\n'
                'python3 stage_dataset.py --case-dir /path/to/restored-case '
                '--manifest dataset_manifest.json --bundle-dir . --include-optional\n')
        restore_source = ROOT / 'tools/zenodo_restore.py'
        shutil.copyfile(restore_source, work / 'stage_dataset.py')
        upload_checksums(work)
        work.rename(target)
    return manifest


def worksheet(case: Path, version: str) -> dict:
    source = json.loads((case / 'data/source_manifest.json').read_text())
    archive = json.loads((case / 'data/archive_manifest.json').read_text())
    gofer = 'archive' in archive
    return {'worksheet_format': 'human review fields; not a Zenodo API payload',
            'case_id': case.name, 'resource_type': 'Dataset',
            'title': f'ELMFIRE validation inputs and observations for {case.name.replace("_", " ")}',
            'version': version, 'creators': [], 'publication_date': None,
            'license': None, 'redistribution_permission_evidence': None,
            'description': 'Frozen model inputs, comparison observations and provenance for '
                + case.name + '. Optional bundles preserve supplied historical simulation '
                'results and distinct inactive older inputs. Source-data limitations are '
                'documented in the bundled source_manifest.json. This dataset does not '
                'establish a scientific PASS.',
            'keywords': ['ELMFIRE', 'wildfire', 'validation', case.name],
            'related_identifiers': [{'identifier': 'https://github.com/berkeley-firelab/ELMFIRE_VnV_Suite',
                                     'relation': 'is supplement to', 'resource_type': 'Software'}]
                + ([{'identifier': 'https://doi.org/10.5281/zenodo.8327264',
                     'relation': 'is derived from', 'resource_type': 'Dataset'},
                    {'identifier': 'https://doi.org/10.5194/essd-16-1395-2024',
                     'relation': 'references', 'resource_type': 'Publication'}] if gofer else []),
            'source_license_statement': archive.get('archive', {}).get('license',
                source.get('model_inputs', {}).get('license', 'unknown')),
            'known_provenance_gaps': source.get('known_provenance_gaps', []),
            'review_status': 'needs creator, attribution and redistribution review'}


def register(case: Path, record_id: str, doi: str, concept_doi: str | None) -> None:
    if not record_id.isdigit() or doi != f'10.5281/zenodo.{record_id}':
        raise ValueError('Use the production version record ID and its matching 10.5281/zenodo.ID DOI.')
    path = case / 'data/dataset_manifest.json'
    manifest = json.loads(path.read_text())
    if manifest['zenodo'].get('record_id'):
        raise ValueError('Record already registered; rebuild deliberately for a new version.')
    manifest['zenodo'] = {'record_id': record_id, 'version_doi': doi, 'concept_doi': concept_doi}
    for bundle in manifest['bundles']:
        bundle['url'] = f'https://zenodo.org/records/{record_id}/files/{bundle["filename"]}?download=1'
    write_json(path, manifest)


def verify_upload_set(case: Path, directory: Path, check_sources: bool = False) -> None:
    """Verify retained upload files without requiring a second raw-data copy."""
    manifest = json.loads((case / 'data/dataset_manifest.json').read_text())
    bundles = selected_bundles(manifest, include_optional=True)
    if check_sources:
        for bundle in bundles:
            for record in bundle['files']:
                check_file(source_file(case, record), record)
    for bundle in bundles:
        check_file(directory / bundle['filename'], bundle)
    for line in (directory / 'checksums.sha256').read_text().splitlines():
        expected, filename = line.split('  ', 1)
        if sha256(destination(directory, filename)) != expected:
            raise ValueError(f'Upload file changed: {filename}')


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('build', 'verify', 'metadata', 'register'))
    parser.add_argument('--case', default='all', help='individual fire/case ID, gofer (24 future cases), or all')
    parser.add_argument('--version', default='1.0.0')
    parser.add_argument('--output', type=Path, help='defaults to zenodo/dist/<version>')
    parser.add_argument('--record-id')
    parser.add_argument('--doi')
    parser.add_argument('--concept-doi')
    parser.add_argument('--check-sources', action='store_true',
                        help='with verify, also check restored case-local source files')
    args = parser.parse_args()
    args.output = args.output or ROOT / 'zenodo/dist' / args.version
    cases = sorted(p for p in CASE_ROOT.iterdir() if (p / 'case.yaml').is_file())
    gofer = sorted(p.parent.parent for p in DATASET_ROOT.glob('*/data/archive_manifest.json'))
    if args.case == 'gofer':
        cases = gofer
    else:
        cases += gofer
        if args.case != 'all':
            cases = [p for p in cases if identifier(p) == args.case]
    if len({p.name for p in cases}) != len(cases):
        parser.error('Dataset IDs must be unique across active and future cases.')
    if not cases:
        parser.error('Unknown case ID.')
    try:
        if args.action == 'register':
            if len(cases) != 1 or not args.record_id or not args.doi:
                parser.error('register needs one --case, --record-id and --doi')
            register(cases[0], args.record_id, args.doi, args.concept_doi)
            print(f'[OK] Registered {identifier(cases[0])}; test an actual download before untracking data.')
            return
        if args.action == 'metadata':
            for case in cases:
                directory = args.output / identifier(case)
                if not (directory / 'dataset_manifest.json').is_file():
                    raise ValueError(f'Build the upload set first: {directory}')
                metadata = ROOT / 'zenodo/metadata' / (identifier(case) + '.json')
                shutil.copyfile(metadata, directory / 'metadata-worksheet.json')
                upload_checksums(directory)
                print(f'[OK] metadata: {identifier(case)}')
            return
        revision = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
        for case in cases:
            if args.action == 'build':
                old_path = case / 'data/dataset_manifest.json'
                if old_path.exists():
                    old = json.loads(old_path.read_text())
                    if old.get('zenodo', {}).get('record_id') and old['dataset_version'] == args.version:
                        raise ValueError('Published version already registered; choose a new --version.')
                manifest = build_case(case, args.output, args.version, revision)
                write_json(case / 'data/dataset_manifest.json', manifest)
                (case / 'scripts').mkdir(exist_ok=True)
                shutil.copyfile(ROOT / 'tools/zenodo_restore.py', case / 'scripts/stage_dataset.py')
                metadata = ROOT / 'zenodo/metadata' / (identifier(case) + '.json')
                if not metadata.exists():
                    write_json(metadata, worksheet(case, args.version))
                else:
                    fields = json.loads(metadata.read_text())
                    fields['version'] = args.version
                    write_json(metadata, fields)
                shutil.copyfile(metadata, args.output / identifier(case) / 'metadata-worksheet.json')
                upload_checksums(args.output / identifier(case))
            else:
                verify_upload_set(case, args.output / identifier(case), args.check_sources)
            print(f'[OK] {args.action}: {identifier(case)}', flush=True)
    except (OSError, ValueError, KeyError, subprocess.CalledProcessError) as exc:
        raise SystemExit(str(exc)) from exc


if __name__ == '__main__':
    main()
