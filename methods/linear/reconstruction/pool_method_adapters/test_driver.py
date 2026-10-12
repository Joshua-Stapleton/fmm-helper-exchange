#!/usr/bin/env python3
"""Guard tests; --binary or --leo adds actual pinned native toy controls."""
import argparse
import copy
import importlib.util
import json
import math
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('native_adapter', HERE/'run.py')
adapter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(adapter)
NATIVE = None

def gate(i, j, ai=1, aj=1):
    return dict(i=i, j=j, ai=ai, aj=aj)

def term(i, value=1):
    return dict(index=i, value=value)

def toy_bank():
    # The union contains ab <- abc-c and abc <- ab+c, a real producer cycle.
    return [
        dict(dimension=3, additions=2, substitutions=[gate(0,1)],
             expressions=[[term(3),term(2)],[term(3)]]),
        dict(dimension=3, additions=3,
             substitutions=[gate(1,2),gate(0,3),gate(4,2,1,-1)],
             expressions=[[term(4)],[term(5)]]),
        dict(dimension=3, additions=2,
             substitutions=[gate(0,1),gate(3,2)],
             expressions=[[term(4)],[term(3)]])]

def parameters(**changes):
    values = dict(best=2, seed=1, draws=1, gate_limit=-1, temperature=1,
                  epsilon=.01, retention=.5, seconds=5, min_start_ratio=.1,
                  max_start_ratio=.5, preset='distance', strategy_index=0,
                  bound=None, binary=Path('external_binary'), leo=None)
    values.update(changes)
    return SimpleNamespace(**values)

class Guards(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.directory = Path(self.temp.name)
        self.bank = self.directory/'bank.json'
        self.matrix = self.directory/'matrix.json'
        self.bank.write_text(json.dumps(toy_bank()))
        self.matrix.write_text(json.dumps([[1,1,1],[1,1,0]]))

    def tearDown(self):
        self.temp.cleanup()

    def test_raw_terminal_boundary_and_paid_count(self):
        raw = adapter.raw_solution(toy_bank()[0],3)
        self.assertEqual(len(raw['substitutions']),1)
        self.assertEqual(raw['additions'],2)
        self.assertEqual(adapter.replay_raw(raw),[[1,1,1],[1,1,0]])

    def test_paid_root_alias_and_unit_sign_are_preserved(self):
        raw = dict(dimension=2,additions=2,
                   substitutions=[gate(0,1),gate(2,1,1,-1)],
                   expressions=[[term(3,-1)]])
        checked=adapter.raw_solution(raw,2)
        self.assertEqual(checked['additions'],2)
        self.assertEqual(adapter.replay_raw(checked),[[-1,0]])

    def test_nonunit_gate_scalar_rejected(self):
        raw=toy_bank()[0];raw['substitutions'][0]['ai']=2
        with self.assertRaises(ValueError):adapter.raw_solution(raw,3)

    def test_nonunit_terminal_scalar_rejected(self):
        raw=toy_bank()[0];raw['expressions'][0][0]['value']=2
        with self.assertRaises(ValueError):adapter.raw_solution(raw,3)

    def test_bool_dimension_and_indices_rejected(self):
        one=dict(dimension=True,substitutions=[],expressions=[[term(0)]],additions=0)
        with self.assertRaises(ValueError):adapter.raw_solution(one,1)
        raw=toy_bank()[0];raw['substitutions'][0]['i']=False
        with self.assertRaises(ValueError):adapter.raw_solution(raw,3)

    def test_future_parent_and_output_rejected(self):
        raw=toy_bank()[0];raw['substitutions'][0]['i']=3
        with self.assertRaises(ValueError):adapter.raw_solution(raw,3)
        raw=toy_bank()[0];raw['expressions'][0][0]['index']=4
        with self.assertRaises(ValueError):adapter.raw_solution(raw,3)

    def test_bool_addition_count_rejected(self):
        raw=toy_bank()[0];raw['additions']=True
        with self.assertRaises(ValueError):adapter.raw_solution(raw,3)

    def test_hidden_intermediate_overflow_rejected(self):
        # Final output is merely the input; unused doubling chain still executes.
        raw=dict(dimension=1,substitutions=[gate(k,k)for k in range(31)],
                 expressions=[[term(0)]],additions=31)
        with self.assertRaises(ValueError):adapter.replay_raw(adapter.raw_solution(raw,1))

    def test_terminal_overflow_before_cancellation_rejected(self):
        row=[term(29)]*8+[term(29,-1)]*8+[term(0)]
        raw=dict(dimension=1,substitutions=[gate(k,k)for k in range(29)],
                 expressions=[row],additions=45)
        with self.assertRaises(ValueError):adapter.replay_raw(adapter.raw_solution(raw,1))

    def test_duplicate_json_keys_and_nonfinite_constants_rejected(self):
        path=self.directory/'invalid.json'
        for text in ['{"dimension":3,"dimension":3}',
                     '{"s":{"i":0,"i":1}}','{"temperature":NaN}']:
            path.write_text(text)
            with self.assertRaises(ValueError):adapter.read_json(path)

    def test_best_reference_unsigned_underflow_rejected_before_write(self):
        output=self.directory/'payload.txt'
        with self.assertRaises(ValueError):adapter.prepare(self.bank,self.matrix,output,3)
        self.assertFalse(output.exists())

    def test_materialized_intake_requires_explicit_label(self):
        raw=dict(gates=[[0,1,1,1],[3,1,2,1]],outputs=[[4,1],[3,1]])
        with self.assertRaises(ValueError):adapter.raw_solution(raw,3)
        checked=adapter.raw_solution(raw,3,allow_materialized=True)
        self.assertEqual(adapter.replay_raw(checked),[[1,1,1],[1,1,0]])

    def test_finite_parameters_and_seed_range(self):
        for change in [dict(temperature=float('nan')),dict(epsilon=float('inf')),
                       dict(retention=1.1),dict(min_start_ratio=.6,max_start_ratio=.5),
                       dict(seed=2**32),dict(seed=2**32-1,draws=2),dict(best=True),
                       dict(strategy_index=2),dict(gate_limit=-2)]:
            with self.subTest(change=change):
                with self.assertRaises(ValueError):adapter.validate_parameters(parameters(**change))
        adapter.validate_parameters(parameters())

    def test_invalid_cli_parameters_do_not_create_output(self):
        output=self.directory/'must_not_exist'
        command=[sys.executable,'-B',str(HERE/'run.py'),'--bank',str(self.bank),
                 '--matrix',str(self.matrix),'--best','2','--seed','1',
                 '--output',str(output),'--leo',str(self.directory/'missing'),
                 '--temperature','nan']
        result=subprocess.run(command,capture_output=True,text=True)
        self.assertNotEqual(result.returncode,0)
        self.assertFalse(output.exists())

    def test_quality_total_underflow_rejected_without_reweighting(self):
        with self.assertRaises(ValueError):adapter.validate_quality_total([200,201],0,.001)
        expected=1+math.exp(-1)
        self.assertAlmostEqual(adapter.validate_quality_total([2,3,2],2,1),expected,14)

@unittest.skipIf(NATIVE is None,'Supply --binary or --leo for native API fixture controls')
class NativeFixtures(unittest.TestCase):
    def call(self, bank, **options):
        with tempfile.TemporaryDirectory() as temp:
            directory=Path(temp);b=directory/'bank.json';m=directory/'matrix.json';i=directory/'input.txt'
            b.write_text(json.dumps(bank));m.write_text(json.dumps([[1,1,1],[1,1,0]]))
            adapter.prepare(b,m,i,2)
            command=[str(NATIVE),'--input',str(i),'--mode','weighted','--seed','11102000',
                     '--draws','50','--gate-limit','2','--sample-only']
            for key,value in options.items():command.extend(['--'+key.replace('_','-'),str(value)])
            result=subprocess.run(command,capture_output=True,text=True,check=True,timeout=30)
            return json.loads(result.stdout)

    def test_quality_weighting_balances_cost_classes(self):
        data=self.call(toy_bank());denominator=1+math.exp(-1)
        expected=[.99*.5/denominator+.01/3,.99*math.exp(-1)/denominator+.01/3,
                  .99*.5/denominator+.01/3]
        for actual,wanted in zip(data['weights'],expected):self.assertAlmostEqual(actual,wanted,14)

    def test_terminal_only_form_is_not_imported(self):
        data=self.call(toy_bank()[:1]);self.assertEqual(data['helpers'],1)
        self.assertTrue(all(draw['prefix_gates']<=1 for draw in data['draws']))

    def test_union_cycle_does_not_create_unpaid_or_forward_gates(self):
        data=self.call(toy_bank());self.assertEqual(data['helpers'],3)
        for draw in data['draws']:
            prefix=adapter.raw_solution(draw['prefix'],3)
            adapter.replay_raw(prefix)
            self.assertLessEqual(len(prefix['substitutions']),2)
            values=[(1,0,0),(0,1,0),(0,0,1)];known=set(values)
            for s in prefix['substitutions']:
                v=tuple(s['ai']*a+s['aj']*b for a,b in zip(values[s['i']],values[s['j']]))
                sign=next(1 if x>0 else -1 for x in v if x);canonical=tuple(sign*x for x in v)
                self.assertNotIn(canonical,known);known.add(canonical);values.append(v)

    def test_direct_native_prefix_cannot_charge_scalar2_as_one_addition(self):
        with tempfile.TemporaryDirectory() as temp:
            d=Path(temp);b=d/'bank.json';m=d/'matrix.json';i=d/'input.txt';p=d/'prefix.txt'
            b.write_text(json.dumps(toy_bank()));m.write_text(json.dumps([[1,1,1],[1,1,0]]))
            adapter.prepare(b,m,i,2);p.write_text('3 1\n0 1 2 1\n')
            result=subprocess.run([str(NATIVE),'--input',str(i),'--prefix-file',str(p),
                                   '--seed','1','--sample-only'],capture_output=True,text=True)
            self.assertNotEqual(result.returncode,0)
            self.assertIn('nonunit',result.stderr)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--binary',type=Path);parser.add_argument('--leo',type=Path)
    args,remaining=parser.parse_known_args();temporary=None
    if args.binary:
        NATIVE=args.binary.resolve()
        report=adapter.read_json(NATIVE.with_suffix('.build.json'))
        adapter.require(report['upstream_commit']==adapter.PIN and report['executable_sha256']==adapter.digest(NATIVE), 'Invalid native binary')
        adapter.require(report['driver_sha256']==adapter.digest(HERE/'pool_driver.cpp'),'Different adapter binary')
    elif args.leo:
        temporary=tempfile.TemporaryDirectory();NATIVE=Path(temporary.name)/'pool_driver';adapter.build(args.leo,NATIVE)
    if NATIVE is not None:
        NativeFixtures.__unittest_skip__=False
    unittest.main(argv=[sys.argv[0],*remaining],verbosity=2)
