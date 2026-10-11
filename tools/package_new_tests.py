#!/usr/bin/env python3
"""Build and independently replay the 18-map new-test certificate archive."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'certificates/new_tests_20261011'
ARCHIVE = ROOT / 'downloads/fmm_new_tests_certificates_20261011.zip'
EXPECTED = {'5x5x11':765, '5x6x8':669, '5x6x9':755,
            '5x7x7':697, '6x7x7':848, '7x7x7':1020}


def verify(directory):
    result = subprocess.run([sys.executable, '-I', '-B', str(directory / 'verify_all.py')],
                            cwd=directory, text=True, capture_output=True, check=True)
    report = json.loads(result.stdout)
    assert report['status'] == 'PASS'
    actual={'x'.join(map(str,r['dimensions'])):r['additions'] for r in report['schemes']}
    assert actual == EXPECTED, 'Unexpected certified addition totals'
    return report


def main():
    verify(SOURCE)
    files = sorted(p for p in SOURCE.rglob('*') if p.is_file()
                   and '__pycache__' not in p.parts and p.suffix not in ('.pyc','.pyo'))
    with zipfile.ZipFile(ARCHIVE, 'w', compression=zipfile.ZIP_DEFLATED,
                         compresslevel=9) as archive:
        for path in files:
            info = zipfile.ZipInfo(str(path.relative_to(SOURCE)), (2026,10,11,0,0,0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, path.read_bytes())
    sha = hashlib.sha256(ARCHIVE.read_bytes()).hexdigest()
    with tempfile.TemporaryDirectory(prefix='fmm-new-tests-') as temporary:
        destination = Path(temporary).resolve()
        with zipfile.ZipFile(ARCHIVE) as archive:
            for name in archive.namelist():
                assert (destination/name).resolve().is_relative_to(destination)
            archive.extractall(destination)
        replay = verify(destination)
    publication = ROOT/'PUBLICATION.json'
    data = json.loads(publication.read_text())
    data['latest_update']['new_tests']['bundle_sha256'] = sha
    publication.write_text(json.dumps(data,indent=2)+'\n')
    report = dict(status='PASS', archive=str(ARCHIVE.relative_to(ROOT)),sha256=sha,
                  files=len(files),bytes=ARCHIVE.stat().st_size,
                  standalone_extraction_replayed=True,certificate=replay)
    (ROOT/'verification/standalone-new-tests-20261011.json').write_text(
        json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items()if k!='certificate'},indent=2))


if __name__=='__main__':
    main()
