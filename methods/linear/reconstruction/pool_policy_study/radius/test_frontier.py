#!/usr/bin/env python3
"""Graph-only safety tests for the final-insertion filter, including cyclic rules."""
import os
import random
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

def closure(n,roots,allowed,productions):
    ready=set(roots)
    while True:
        new={o for o in allowed-ready if any(a in ready and b in ready for a,b in productions.get(o,()))}
        if not new:return ready
        ready|=new

def boundary(targets,ready,allowed,productions):
    queue=list(targets-ready);seen=set();out=set()
    while queue:
        o=queue.pop()
        if o in ready or o in seen:continue
        seen.add(o)
        if o not in allowed:out.add(o);continue
        for a,b in productions.get(o,()):queue.extend([a,b])
    return out

class Safety(unittest.TestCase):
    def test_actual_cpp_matches_reference_on_random_cyclic_graphs(self):
        if os.environ.get('FMM_RADIUS_NATIVE_TESTS')!='1':self.skipTest('Set FMM_RADIUS_NATIVE_TESTS=1 to compile native comparison')
        compiler=shutil.which('c++')
        if compiler is None:self.skipTest('C++17 compiler unavailable')
        here=Path(__file__).resolve().parent;rng=random.Random(172701);cases=[];payload=[]
        for _ in range(200):
            n=12;roots={0,1,2};targets={10,11};productions={o:[(rng.randrange(n),rng.randrange(n)) for _ in range(3)] for o in range(3,n)}
            helpers={o for o in range(3,10) if rng.random()<.5};allowed=roots|targets|helpers;ready=closure(n,roots,allowed,productions)
            viable={h for h in set(range(3,n))-allowed if any(a in ready and b in ready for a,b in productions[h])};last=viable&boundary(targets,ready,allowed,productions);cases.append((ready,viable,last))
            edges=[(o,a,b) for o in sorted(productions) for a,b in productions[o]];payload.append(f'{n} 3 2 {len(helpers)} {len(edges)}\n10 11\n'+ ' '.join(map(str,sorted(helpers)))+'\n'+''.join(f'{o} {a} {b}\n' for o,a,b in edges))
        with tempfile.TemporaryDirectory() as temporary:
            binary=Path(temporary)/'probe';subprocess.run([compiler,'-O2','-std=c++17',str(here/'sources/frontier_probe.cpp'),'-o',str(binary)],check=True,capture_output=True,timeout=30)
            p=subprocess.run([str(binary)],input=''.join(payload),capture_output=True,text=True,check=True,timeout=5)
        lines=p.stdout.splitlines();self.assertEqual(len(lines),3*len(cases))
        for i,case in enumerate(cases):
            actual=tuple(set(map(int,lines[3*i+j].split()[1:])) for j in range(3));self.assertEqual(actual,case)

    def test_all_finishing_single_insertions_survive(self):
        rng=random.Random(171701);checked=0
        for _ in range(2000):
            n=12;roots={0,1,2};targets={10,11};productions={o:[(rng.randrange(n),rng.randrange(n)) for _ in range(3)] for o in range(3,n)}
            allowed=roots|targets|{o for o in range(3,10) if rng.random()<.5};ready=closure(n,roots,allowed,productions)
            if targets<=ready:continue
            frontier=boundary(targets,ready,allowed,productions)
            for h in set(range(3,n))-allowed:
                if not any(a in ready and b in ready for a,b in productions[h]):continue
                if targets<=closure(n,roots,allowed|{h},productions):self.assertIn(h,frontier);checked+=1
        self.assertGreater(checked,0)

    def test_do_not_apply_filter_to_first_of_two_insertions(self):
        # helper2 is useful only because it unlocks helper3, the boundary node.
        roots={0,1};targets={4};allowed=roots|targets;productions={2:[(0,1)],3:[(2,1)],4:[(3,0)]}
        ready=closure(5,roots,allowed,productions);self.assertEqual(boundary(targets,ready,allowed,productions),{3})
        self.assertNotIn(2,boundary(targets,ready,allowed,productions))
        self.assertTrue(targets<=closure(5,roots,allowed|{2,3},productions))

    def test_cycle_is_visited_once_and_boundary_is_preserved(self):
        roots={0};targets={4};allowed={0,2,4};productions={2:[(4,3)],4:[(2,0),(3,0)],3:[(0,0)]}
        ready=closure(5,roots,allowed,productions);self.assertEqual(boundary(targets,ready,allowed,productions),{3})
        self.assertTrue(targets<=closure(5,roots,allowed|{3},productions))

if __name__=='__main__':unittest.main()
