import unittest
from account_forms import account


class FormAccountingTests(unittest.TestCase):
    def setUp(self):
        self.original = dict(inputs=4, gates=[[0,1,1,1],[4,1,2,1],[1,1,2,1],[6,1,3,1]],
                             outputs=[[5,1],[7,1]])
        self.better = dict(inputs=4, gates=[[1,1,2,1],[0,1,4,1],[4,1,3,1]],
                           outputs=[[5,1],[6,1]])

    def test_removed_helper_stays_absent(self):
        r = account(self.original, self.better, [0])
        self.assertEqual((r['omitted_hint_count_k'],r['unused_survivor_count_d'],
                          r['recreated_omission_count_b'],r['novel_helper_count_q']), (1,0,0,0))
        self.assertEqual(r['normalized_gain'], 1)

    def test_native_may_recreate_omission_and_drop_survivor(self):
        # The identical improved circuit is also a possible outcome after
        # omitting t1: it recreates t1 and abandons surviving hint t0.
        r = account(self.original, self.better, [1])
        self.assertEqual((r['omitted_hint_count_k'],r['unused_survivor_count_d'],
                          r['recreated_omission_count_b'],r['novel_helper_count_q']), (1,1,1,0))
        self.assertEqual(r['normalized_gain'], 1)

    def test_duplicate_signed_alias_does_not_change_normalized_count(self):
        alias = dict(inputs=4, gates=self.better['gates']+[[0,-1,4,-1]],
                     outputs=[[7,-1],[6,1]])
        r = account(self.original, alias, [0])
        self.assertEqual(r['reconstructed_live_raw_gates'], 3)
        self.assertEqual(r['reconstructed_signed_normalized_gates'], 3)


if __name__ == '__main__':
    unittest.main()
