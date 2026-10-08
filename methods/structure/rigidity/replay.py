#!/usr/bin/env python3
"""Full portable exact replay; native outputs are created in a temporary copy."""
from pathlib import Path
import argparse,hashlib,json,subprocess,sys,tempfile,shutil
H=Path(__file__).resolve().parent
p=argparse.ArgumentParser();p.add_argument('--rational-only',action='store_true',help='check rational premises but trust saved scan summaries; not full replay');a=p.parse_args()
for f,digest in json.loads((H/'certificate_manifest.json').read_text()).items():
 assert hashlib.sha256((H/f).read_bytes()).hexdigest()==digest,f
with tempfile.TemporaryDirectory(prefix='fmm-rigidity-')as td:
 D=Path(td)/'rigidity';shutil.copytree(H,D)
 if not a.rational_only:
  subprocess.run(['c++','-O3','-std=c++17',str(D/'independent_scan.cpp'),'-o',str(D/'independent_scan')],check=True)
  subprocess.run([sys.executable,'-B',str(D/'run_independent.py')],check=True)
 subprocess.run([sys.executable,'-B',str(D/'verify_rigidity.py')],check=True)
print('RATIONAL_ONLY_PASS' if a.rational_only else 'FULL_REPLAY_PASS')
