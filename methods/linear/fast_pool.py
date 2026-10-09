#!/usr/bin/env python3
"""Native relation enumeration; every returned relation is replayed exactly in Python."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import tempfile

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
spec=importlib.util.spec_from_file_location('exact_pool_reference',ROOT/'make_pool.py')
reference=importlib.util.module_from_spec(spec);spec.loader.exec_module(reference)


def compile_backend(out, compiler=None):
    compiler=compiler or next((shutil.which(c) for c in ('c++','g++','clang++') if shutil.which(c)),None)
    reference.require(compiler is not None,'C++17 compiler required')
    source=HERE/'pool_relations.cpp';out=Path(out);out.parent.mkdir(parents=True,exist_ok=True)
    subprocess.run([compiler,'-O3','-std=c++17',str(source),'-o',str(out)],check=True)
    return out


def build_pool(source, *, binary=None):
    with tempfile.TemporaryDirectory(prefix='exact-pool-relations-') as tmp:
        binary=Path(binary) if binary else compile_backend(Path(tmp)/'relations')
        def relations(forms, roots):
            # Signed gates can generate arbitrary integers. Refuse overflow;
            # callers may use the unrestricted Python reference for huge forms.
            reference.require(all(type(x) is int and abs(x)<=2**61 for row in forms for x in row),
                              'Native coefficients exceed safe int64 range; use make_pool.py')
            text=f'{len(forms)} {len(forms[0])} {roots}\n'+'\n'.join(' '.join(map(str,row)) for row in forms)+'\n'
            result=subprocess.run([str(binary.resolve())],input=text,capture_output=True,text=True,check=True)
            output={i:set() for i in range(roots,len(forms))}
            for line in result.stdout.splitlines():
                out,a,sa,b,sb=map(int,line.split());output[out].add((a,sa,b,sb))
            return output
        return reference.build_pool(source,production_builder=relations)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('input',type=Path);p.add_argument('output',type=Path)
    p.add_argument('--binary',type=Path);a=p.parse_args()
    pool=build_pool(json.loads(a.input.read_text()),binary=a.binary)
    a.output.write_text(json.dumps(pool,indent=2)+'\n')
    print(json.dumps(dict(forms=len(pool['forms']),productions=sum(map(len,pool['productions'].values())),
                          exact_relations_checked=True),indent=2))
