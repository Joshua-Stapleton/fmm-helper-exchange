#!/usr/bin/env python3
"""Build and independently replay the standalone 5x7x7 certificate archive."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'certificates/scheme_5x7x7_176'
ARCHIVE = ROOT / 'downloads/fmm_5x7x7_176_certificates_20261010.zip'


def verify(directory):
    result = subprocess.run([sys.executable, '-I', '-B', str(directory / 'verify.py')],
                            cwd=directory, text=True, capture_output=True, check=True)
    report = json.loads(result.stdout)
    assert report['status'] == 'PASS' and report['additions_after'] == 701
    return report


def main():
    verify(SOURCE)
    files = sorted(p for p in SOURCE.rglob('*') if p.is_file())
    with zipfile.ZipFile(ARCHIVE, 'w', compression=zipfile.ZIP_DEFLATED,
                         compresslevel=9) as archive:
        for path in files:
            name = str(path.relative_to(SOURCE))
            info = zipfile.ZipInfo(name, (2026, 10, 10, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, path.read_bytes())
    sha = hashlib.sha256(ARCHIVE.read_bytes()).hexdigest()
    with tempfile.TemporaryDirectory(prefix='fmm-577-standalone-') as temporary:
        destination = Path(temporary).resolve()
        with zipfile.ZipFile(ARCHIVE) as archive:
            for name in archive.namelist():
                assert (destination / name).resolve().is_relative_to(destination)
            archive.extractall(destination)
        replay = verify(destination)
    publication = ROOT / 'PUBLICATION.json'
    data = json.loads(publication.read_text())
    data['latest_update']['residual_forest']['bundle_sha256'] = sha
    publication.write_text(json.dumps(data, indent=2) + '\n')
    report = dict(status='PASS', archive=str(ARCHIVE.relative_to(ROOT)), sha256=sha,
                  files=len(files), bytes=ARCHIVE.stat().st_size,
                  standalone_extraction_replayed=True, certificate=replay)
    (ROOT / 'verification/standalone-577-20261010.json').write_text(
        json.dumps(report, indent=2) + '\n')
    print(json.dumps({key: value for key, value in report.items()
                      if key != 'certificate'}, indent=2))


if __name__ == '__main__':
    main()
