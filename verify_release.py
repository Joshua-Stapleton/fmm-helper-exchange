#!/usr/bin/env python3
"""Verify release integrity and run portable checks in a disposable copy.

Default checks upper-bound certificates and method controls. --full additionally
reruns complete computational lower-bound proofs. --solvers checks optional
CP methods. A quick run never claims the exhaustive proofs were rerun.
"""
from pathlib import Path
import argparse,hashlib,json,shutil,subprocess,sys,tempfile,time,zipfile
ROOT=Path(__file__).resolve().parent

def integrity():
    manifest=ROOT/'SHA256SUMS'
    if not manifest.exists():raise ValueError('SHA256SUMS missing')
    checked=0
    for line in manifest.read_text().splitlines():
        if not line.strip():continue
        digest,name=line.split(None,1);name=name.strip()
        path=ROOT/name
        if not path.resolve().is_relative_to(ROOT):raise ValueError('manifest path escapes release')
        if hashlib.sha256(path.read_bytes()).hexdigest()!=digest:raise ValueError('hash mismatch: '+name)
        checked+=1
    return checked

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--full',action='store_true');ap.add_argument('--solvers',action='store_true');ap.add_argument('--output',type=Path);a=ap.parse_args()
    hashes=integrity();results=[];started=time.monotonic()
    with tempfile.TemporaryDirectory(prefix='fmm-release-check-') as tmp:
        work=Path(tmp)/'repo'
        shutil.copytree(ROOT,work,ignore=shutil.ignore_patterns('.git','__pycache__','.venv','results','downloads'))
        with zipfile.ZipFile(work/'certificate_666_587.zip') as z:
            dest=work/'certificate_666_587'
            for n in z.namelist():
                if not (dest/n).resolve().is_relative_to(dest.resolve()):raise ValueError('unsafe archive path')
            z.extractall(dest)
        scripts=[
          ('root-wt','run.py',['--example','wt','--verify-only']),
          ('root-u','run.py',['--example','u','--verify-only']),
          ('circuit-controls','methods/circuits/test_methods.py',[]),
          ('linear-controls','methods/linear/test_methods.py',(['--with-cpp']if a.full else [])+(['--with-solvers']if a.solvers else [])),
          ('reconstruction-controls','methods/linear/reconstruction/test_reconstruction.py',['--with-cpp']if a.full else []),
          ('pooled-start-controls','methods/linear/reconstruction/test_pool_starts.py',[]),
          ('pooled-start-pilot','methods/linear/reconstruction/pooled_start_pilot/verify.py',[]),
          ('fixed-maps-20261009','certificates/fmm_maps_20261009/verify.py',[]),
          ('347-V78','certificates/fmm_maps_20261008/347_V78/verify.py',[]),
          ('558-V161','certificates/fmm_maps_20261008/558_V161/verify.py',[]),
          ('788-V401','certificates/fmm_maps_20261008/788_V401/verify.py',[]),
          ('test-archive-25','certificates/tests_archive_20261009/verify_all.py',[]),
          ('tensor-factor-controls','methods/linear/tensor_factors/verify.py',[]),
          ('projective-direction-controls','methods/circuits/direction_floor.py',['../../certificates/tests_archive_20261009/maps']),
          ('transform-controls','methods/transforms/test_transforms.py',[]),
          ('queue-controls','methods/orchestration/test_store.py',[]),
          ('555-332','methods/linear/certificate_555_332/verify.py',[]),
          ('444-169-43','methods/basis/certificate_4x4_169_43/verify.py',[]),
          ('444-204-storage','methods/storage/certificate_204_storage_19/verify.py',[]),
          ('888-1250-268','certificates/certificate_8x8_1250_268/verify.py',[]),
          ('233-36-10','methods/basis/small/certificate_233_36/verify.py',[]),
          ('323-33-10','methods/basis/small/certificate_323_33/verify.py',[]),
          ('small-uppers','methods/basis/small/certificate_small_minima/verify_upper.py',[]),
          ('segre-transform','methods/structure/segre_family.py',[]),
          ('span-move-controls','methods/decomposition/span_moves.py',[]),
          ('recurrence','methods/analysis/count_portfolio.py',[]),
          ('shear-distance','methods/analysis/support_distance.py',[]),
          ('roundoff','methods/analysis/allorders_roundoff.py',[]),
        ]
        cert=list((work/'certificate_666_587').rglob('verify.py'))
        if len(cert)!=1:raise ValueError('ambiguous 666 verifier')
        scripts.append(('666-587',str(cert[0].relative_to(work)),[]))
        if a.solvers:scripts.append(('solver-controls','methods/circuits/test_methods.py',['--solver']))
        if a.full:
            scripts.append(('native-pool-controls','methods/linear/test_fast_pool.py',[]))
            scripts.extend([
              ('fixed51','methods/basis/fixed_scheme_optimal51/verify.py',[]),
              ('grid51','methods/basis/segre_grid_floor51/verify.py',[]),
              ('rational-rigidity','methods/structure/rigidity/replay.py',[]),
              ('233-lower','methods/basis/small/certificate_233_36/verify_lower.py',[]),
              ('canonical-boundary10','methods/basis/small/certificate_canonical_boundary_10/verify.py',[]),
              ('224-lower','methods/basis/small/certificate_small_minima/verify_224.py',[]),
              ('small-lowers','methods/basis/small/certificate_small_minima/verify_lower.py',[]),
              ('orbit20','methods/basis/canonical_orbit/verify.py',[]),
              ('exchange-pool-audit','methods/basis/exchanges/audit.py',[]),
              ('exchange-neighborhoods','methods/basis/exchanges/replay.py',['--case','all']),
            ])
        for name,relative,args in scripts:
            path=work/relative;start=time.monotonic()
            try:
                run=subprocess.run([sys.executable,'-B',str(path),*args],cwd=path.parent,capture_output=True,text=True,timeout=1800)
                rec={'check':name,'status':'PASS'if run.returncode==0 else 'FAIL','seconds':round(time.monotonic()-start,3),'output_sha256':hashlib.sha256((run.stdout+run.stderr).encode()).hexdigest()}
                if run.returncode:rec['diagnostic']=(run.stdout+run.stderr)[-4000:]
            except subprocess.TimeoutExpired:rec={'check':name,'status':'TIMEOUT','seconds':1800}
            results.append(rec);print(name,rec['status'],flush=True)
            if rec['status']!='PASS':break
    report={'status':'PASS'if all(r['status']=='PASS'for r in results) else 'FAIL','file_hashes':hashes,'full_proofs_replayed':a.full and len(results)==len(scripts) and all(r['status']=='PASS'for r in results),'optional_solver_checks':a.solvers,'seconds':round(time.monotonic()-started,3),'results':results}
    if a.output:a.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
    return 0 if report['status']=='PASS'else 1
if __name__=='__main__':raise SystemExit(main())
