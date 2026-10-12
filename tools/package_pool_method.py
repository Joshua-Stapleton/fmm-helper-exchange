#!/usr/bin/env python3
"""Package and replay the independent pool-method study without dependencies."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
FOLDERS = ['methods/linear/reconstruction/pool_method_study',
           'methods/linear/reconstruction/pool_method_adapters']
ARCHIVE = ROOT / 'downloads/fmm_pool_method_study_20261011.zip'
README = '''Testing Perminov's weighted helper pool, 11 October 2026

This is a study of fixed linear maps, with no new addition record.
From this extracted directory, run with standard-library Python 3.10+:

python3 -I -B methods/linear/reconstruction/pool_method_study/verify.py
python3 -B -m unittest discover -s methods/linear/reconstruction/pool_method_adapters -p 'test_*.py'

NumPy scoring controls are skipped when NumPy is unavailable. Native sampling
requires a separate clean upstream checkout at the pinned commit and C++17.
Read docs/perminov-pool-method-20261011.md and the module READMEs.
Default replay checks arithmetic and the finite88 upper witness; it does not
verify an UNSAT certificate. Optional OR-Tools model reruns are separate.
'''


def verify(directory):
    script = directory / FOLDERS[0] / 'verify.py'
    run = subprocess.run([sys.executable, '-I', '-B', str(script)],
                         cwd=directory, text=True, capture_output=True, check=True)
    report = json.loads(run.stdout)
    assert report['status'] == 'PASS'
    assert report['paired_complete'] == 77
    assert report['raw_prefixes_checked'] == 1424
    assert report['complete_raw_maps_checked'] == 503
    assert report['independently_checked_unsat_proof'] is False
    return report


def main():
    verify(ROOT)
    files = sorted(p for name in FOLDERS for p in (ROOT/name).rglob('*')
                   if p.is_file() and '__pycache__' not in p.parts
                   and p.suffix not in ('.pyc', '.pyo'))
    files += [ROOT/'docs/perminov-pool-method-20261011.md', ROOT/'run.py', ROOT/'NOTICE.md']
    payload = {str(p.relative_to(ROOT)):p.read_bytes() for p in files}
    payload['README.txt'] = README.encode()
    with zipfile.ZipFile(ARCHIVE, 'w', compression=zipfile.ZIP_DEFLATED,
                         compresslevel=9) as archive:
        for name, data in sorted(payload.items()):
            info = zipfile.ZipInfo(name, (2026, 10, 11, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, data)
    sha = hashlib.sha256(ARCHIVE.read_bytes()).hexdigest()
    with tempfile.TemporaryDirectory(prefix='fmm-pool-method-') as temporary:
        destination = Path(temporary).resolve()
        with zipfile.ZipFile(ARCHIVE) as archive:
            for name in archive.namelist():
                assert (destination/name).resolve().is_relative_to(destination)
            archive.extractall(destination)
        replay = verify(destination)
    publication = ROOT/'PUBLICATION.json'
    data = json.loads(publication.read_text())
    data['latest_update']['pool_method']['bundle_sha256'] = sha
    publication.write_text(json.dumps(data, indent=2)+'\n')
    report = dict(status='PASS', archive=str(ARCHIVE.relative_to(ROOT)),
                  sha256=sha, files=len(payload), bytes=ARCHIVE.stat().st_size,
                  standalone_extraction_replayed=True, study_replay=replay)
    (ROOT/'verification/standalone-pool-method-20261011.json').write_text(
        json.dumps(report, indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k!='study_replay'}, indent=2))


if __name__ == '__main__':
    main()
