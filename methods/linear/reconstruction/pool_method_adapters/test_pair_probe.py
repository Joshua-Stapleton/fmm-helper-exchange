#!/usr/bin/env python3
import unittest
import pair_probe as p


@unittest.skipIf(p.m.np is None, 'NumPy lookahead scorer is optional')
class PairProbeTest(unittest.TestCase):
    def test_pair_sees_output_missed_by_closest_vector(self):
        # u=(a+d)+(b+e)+(c+f), v=d+e+f. Their actual construction
        # avoids computing a+b or a+b+c along the way.
        program = dict(inputs=6, gates=[[3,1,0,1],[4,1,1,1],[5,1,2,1],
                       [6,1,7,1],[9,1,8,1],[3,1,4,1],[11,1,5,1]])
        score = p.pair_score(program, [[1,1,1,0,0,0]])
        self.assertEqual(score['base']['closest_signed_l1_ordered_sum'], 2)
        self.assertEqual(score['exact_one_gate_unique_targets'], 1)
        self.assertEqual(score['adjusted_remaining_proxy'], 1)
        self.assertEqual(score['key'][-1], 7)

    def test_known_target_has_zero_additional_cost(self):
        program = dict(inputs=2, gates=[[0,1,1,-1]])
        score = p.pair_score(program, [[1,-1],[-1,1]])
        self.assertEqual(score['adjusted_remaining_proxy'], 0)
        self.assertEqual(score['exact_one_gate_unique_targets'], 0)
        self.assertEqual(score['base']['covered_target_unique_signed_forms'], 1)

    def test_doubling_is_one_paid_gate(self):
        score = p.pair_score(dict(inputs=2, gates=[]), [[2,0]])
        self.assertEqual(score['exact_one_gate_unique_targets'], 1)
        self.assertEqual(score['adjusted_remaining_proxy'], 1)
        self.assertEqual(score['base']['paid_initial_gates'], 0)


if __name__ == '__main__':
    unittest.main()
