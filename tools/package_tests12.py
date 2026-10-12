#!/usr/bin/env python3
"""Package and independently replay the 57-map, 19-scheme certificates."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import zipfile

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'certificates/tests_archive_20261012'
ARCHIVE=ROOT/'downloads/fmm_tests_archive_certificates_20261012.zip'

def verify(directory):
    run=subprocess.run([sys.executable,'-I','-B',str(directory/'verify_all.py')],
                       cwd=directory,text=True,capture_output=True,check=True)
    report=json.loads(run.stdout)
    assert report['status']=='PASS' and len(report['schemes'])==19
    return report

def main():
    verify(SOURCE)
    files=sorted(p for p in SOURCE.rglob('*') if p.is_file()
                 and '__pycache__' not in p.parts and p.suffix not in ('.pyc','.pyo'))
    with zipfile.ZipFile(ARCHIVE,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as archive:
        for path in files:
            info=zipfile.ZipInfo(str(path.relative_to(SOURCE)),(2026,10,12,0,0,0))
            info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0o100644<<16
            archive.writestr(info,path.read_bytes())
    sha=hashlib.sha256(ARCHIVE.read_bytes()).hexdigest()
    with tempfile.TemporaryDirectory(prefix='fmm-tests12-') as tmp:
        dest=Path(tmp).resolve()
        with zipfile.ZipFile(ARCHIVE) as archive:
            for name in archive.namelist():assert (dest/name).resolve().is_relative_to(dest)
            archive.extractall(dest)
        replay=verify(dest)
    publication=ROOT/'PUBLICATION.json';data=json.loads(publication.read_text())
    data['latest_update']['tests_archive_20261012']['bundle_sha256']=sha
    publication.write_text(json.dumps(data,indent=2)+'\n')
    record=dict(status='PASS',archive=str(ARCHIVE.relative_to(ROOT)),sha256=sha,
                bytes=ARCHIVE.stat().st_size,files=len(files),standalone_extraction_replayed=True,
                certificate_replay=replay)
    (ROOT/'verification/standalone-tests12-20261012.json').write_text(json.dumps(record,indent=2)+'\n')
    print(json.dumps({k:v for k,v in record.items() if k!='certificate_replay'},indent=2))

if __name__=='__main__':main()
