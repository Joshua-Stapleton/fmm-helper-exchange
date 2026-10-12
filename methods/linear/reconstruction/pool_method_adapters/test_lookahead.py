#!/usr/bin/env python3
"""Adversarial and deterministic controls for whole-prefix scoring."""
import copy
import json
from pathlib import Path
import tempfile
import unittest

import lookahead as m


class TestLookahead(unittest.TestCase):
    @unittest.skipIf(m.np is None, 'NumPy lookahead scorer is optional')
    def test_signed_coverage_and_paid_gates(self):
        program = dict(inputs=3, gates=[[0, 1, 1, -1]])
        target = [[-1, 1, 0], [1, -1, 0], [1, 0, 1]]
        score = m.score_prefix(program, target, 1)
        self.assertEqual(score['selection_key'], [1, -1, 1])
        self.assertEqual(score['covered_target_ordered_rows_up_to_sign'], 2)
        self.assertEqual(score['closest_signed_l1_unique_sum'], 1)

    @unittest.skipIf(m.np is None, 'NumPy lookahead scorer is optional')
    def test_magnitude_not_divided_out(self):
        program = dict(inputs=2, gates=[[0, 1, 0, 1]])
        score = m.score_prefix(program, [[2, 0]], 1)
        self.assertEqual(score['covered_target_unique_signed_forms'], 1)
        self.assertEqual(len(m.expanded_values(program)), 3)
        root = m.score_prefix(dict(inputs=2, gates=[]), [[2, 0]], 0)
        self.assertEqual(root['covered_target_unique_signed_forms'], 0)
        self.assertEqual(root['closest_signed_l1_ordered_sum'], 1)

    def test_no_free_helpers_or_forward_reference(self):
        for gates in ([[[2, 1, 0, 1]]], [[[0, 2, 1, 1]]], [[[0, 1, 0, -1]]]):
            with self.assertRaises(ValueError):
                m.score_prefix(dict(inputs=2, gates=gates[0]), [[1, 1]])
        with self.assertRaises(ValueError):
            m.score_prefix(dict(inputs=2, gates=[[0, 1, 1, 1]]), [[1, 1]], 0)

    def test_int64_range_guard(self):
        with self.assertRaisesRegex(ValueError, 'int64'):
            m.score_prefix(dict(inputs=2, gates=[]), [[1 << 62, 1]])

    def test_native_terminals_are_paid(self):
        raw = dict(dimension=3, additions=2,
                   substitutions=[dict(i=0, j=1, ai=1, aj=-1)],
                   expressions=[[dict(index=3, value=1), dict(index=2, value=-1)]])
        program, check = m.native_complete_program(raw, [[1, -1, -1]])
        self.assertEqual(len(program['gates']), 2)
        self.assertTrue(check['complete_exact_map_verified'])
        bad = copy.deepcopy(raw)
        bad['expressions'][0][1]['value'] = 2
        with self.assertRaises(ValueError):
            m.native_complete_program(bad, [[1, -1, 2]])

    def test_prefix_writer_preserves_order(self):
        raw = dict(dimension=2, additions=1,
                   substitutions=[dict(i=0, j=1, ai=-1, aj=1)], expressions=[])
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'prefix.txt'
            m.write_prefix(path, raw)
            self.assertEqual(path.read_text(), '2 1\n0 1 -1 1\n')

    def test_native_input_boundary_preserved(self):
        raw = dict(additions=2,
                   substitutions=[dict(i=0, j=1, ai=1, aj=-1)],
                   expressions=[[dict(index=3, value=1), dict(index=2, value=-1)]])
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'input.txt'
            m.write_input(path, dict(inputs=3, solutions=[raw]), [[1, -1, -1]], 2)
            self.assertEqual(path.read_text(), '3 1 2 1\n1 -1 -1\n3 1 1\n0 1 1 -1\n2 3 1 2 -1\n')


if __name__ == '__main__':
    unittest.main()
