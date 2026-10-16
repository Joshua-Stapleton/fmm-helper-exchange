#!/usr/bin/env python3
"""Package and independently replay the 16 October 2026 hl_tests certificates.

Install this file in the public repository's tools/ directory. All inputs and
outputs resolve inside that checkout; no original experiment path is required.
Only the Python standard library is used.
"""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'certificates/hl_tests_20261016'
ARCHIVE = ROOT / 'downloads/fmm_hl_tests_certificates_20261016.zip'
STAMP = (2026, 10, 16, 0, 0, 0)


def verify(directory):
    result = subprocess.run(
        [sys.executable, '-I', '-B', str(directory / 'verify_all.py')],
        cwd=directory, text=True, capture_output=True, check=True)
    report = json.loads(result.stdout)
    assert report['status'] == 'PASS'
    assert report['basis_change'] is False
    assert len(report['schemes']) == 19
    assert all(row['status'] == 'PASS' for row in report['schemes'])
    return report


def build_archive(files):
    ARCHIVE.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(ARCHIVE, 'w', compression=zipfile.ZIP_DEFLATED,
                         compresslevel=9) as archive:
        for path in files:
            relative = path.relative_to(SOURCE).as_posix()
            assert not Path(relative).is_absolute() and '..' not in Path(relative).parts
            info = zipfile.ZipInfo(relative, STAMP)
            info.create_system = 3
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, path.read_bytes(), compresslevel=9)


def main():
    assert SOURCE.is_dir(), 'Missing certificates/hl_tests_20261016 in this checkout'
    publication = ROOT / 'PUBLICATION.json'
    data = json.loads(publication.read_text())
    update = data['latest_update']['hl_tests_20261016']
    verify(SOURCE)
    files = sorted(path for path in SOURCE.rglob('*') if path.is_file()
                   and '__pycache__' not in path.parts
                   and path.suffix not in ('.pyc', '.pyo'))
    assert files
    build_archive(files)
    digest = hashlib.sha256(ARCHIVE.read_bytes()).hexdigest()
    with tempfile.TemporaryDirectory(prefix='fmm-hl-tests-') as temporary:
        destination = Path(temporary).resolve()
        with zipfile.ZipFile(ARCHIVE) as archive:
            names = archive.namelist()
            assert len(names) == len(set(names)) == len(files)
            for name in names:
                assert not Path(name).is_absolute() and '..' not in Path(name).parts
                assert (destination / name).resolve().is_relative_to(destination)
            archive.extractall(destination)
        replay = verify(destination)
    update['bundle_sha256'] = digest
    publication.write_text(json.dumps(data, indent=2) + '\n')
    record = dict(
        status='PASS', archive=ARCHIVE.relative_to(ROOT).as_posix(),
        sha256=digest, bytes=ARCHIVE.stat().st_size, files=len(files),
        deterministic_zip_timestamp='2026-10-16T00:00:00',
        original_source_replayed=True, standalone_extraction_replayed=True,
        certificate_replay=replay)
    verification = ROOT / 'verification'
    verification.mkdir(parents=True, exist_ok=True)
    (verification / 'standalone-hl-tests-20261016.json').write_text(
        json.dumps(record, indent=2) + '\n')
    print(json.dumps({key: value for key, value in record.items()
                      if key != 'certificate_replay'}, indent=2))


if __name__ == '__main__':
    main()
