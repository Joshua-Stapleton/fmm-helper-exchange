#!/usr/bin/env python3
"""Build the portable ZIP and whole-repository hash manifest deterministically."""
from pathlib import Path
import hashlib,zipfile
ROOT=Path(__file__).resolve().parents[1]
EXCLUDED={'.git','__pycache__','.venv','results','build','replay','lower_replay'}
def files():
    return sorted(p for p in ROOT.rglob('*') if p.is_file() and not any(x in EXCLUDED for x in p.relative_to(ROOT).parts) and p.suffix not in ('.pyc','.pyo') and p!=ROOT/'SHA256SUMS')
def digest(data):return hashlib.sha256(data).hexdigest()
def writezip(z,name,data):
    info=zipfile.ZipInfo('fmm-helper-exchange/'+name,(2026,10,8,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0o100644<<16;z.writestr(info,data)
def main():
    archive=ROOT/'downloads/fmm_research_methods.zip'
    payload={str(p.relative_to(ROOT)):p.read_bytes()for p in files()if 'downloads'not in p.relative_to(ROOT).parts}
    manifest=''.join(digest(b)+'  '+n+'\n'for n,b in payload.items())
    with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9)as z:
        for name,data in payload.items():writezip(z,name,data)
        writezip(z,'SHA256SUMS',manifest.encode())
    (ROOT/'SHA256SUMS').write_text(''.join(digest(p.read_bytes())+'  '+str(p.relative_to(ROOT))+'\n'for p in files()))
    print('Files:',len(payload),'ZIP bytes:',archive.stat().st_size,'SHA256:',digest(archive.read_bytes()))
if __name__=='__main__':main()
