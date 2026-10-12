"""Small semantic controls for the independent GF(2) audit, no OR-Tools needed."""
import json
import sys
sys.dont_write_bytecode = True
import re
import unittest
import probe


def polynomial_multiply_mod_aes(a, b):
    # Separate polynomial convolution/reduction reference; no xtime reuse.
    z = 0
    for i in range(8):
        if (b >> i) & 1:
            z ^= a << i
    for i in range(14, 7, -1):
        if (z >> i) & 1:
            z ^= 0x11B << (i - 8)
    return z


class Controls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = (probe.HERE / "sources/aes-mixcols-xor88-depth5.circ.txt").read_text()
        cls.graph = json.loads((probe.HERE / "catalogue.json").read_text())
        cls.witness = json.loads((probe.HERE / "pool_any_depth.witness.json").read_text())

    def test_byte_field_scalar_rules(self):
        for a in range(256):
            self.assertEqual(probe.xtime(a), polynomial_multiply_mod_aes(a, 2))
            self.assertEqual(probe.xtime(a) ^ a, polynomial_multiply_mod_aes(a, 3))

    def test_baseline_exact(self):
        c = probe.parse_ncFF(self.source)
        self.assertEqual((c["gate_count"], c["depth"]), (88, 5))

    def test_wrong_wire_rejected(self):
        lines = self.source.splitlines()
        i = next(i for i, line in enumerate(lines) if line.startswith("XOR "))
        parts = lines[i].split()
        parts[-1] = "x31" if parts[-1] != "x31" else "x30"
        lines[i] = " ".join(parts)
        with self.assertRaises(ValueError):
            probe.parse_ncFF("\n".join(lines))

    def test_nonxor_rejected(self):
        with self.assertRaises(ValueError):
            probe.parse_ncFF(re.sub(r"^XOR ", "XNOR ", self.source, count=1, flags=re.MULTILINE))

    def test_future_or_unknown_wire_rejected(self):
        lines = self.source.splitlines()
        i = next(i for i, line in enumerate(lines) if line.startswith("XOR "))
        parts = lines[i].split()
        parts[-1] = "t999999"
        lines[i] = " ".join(parts)
        with self.assertRaises(ValueError):
            probe.parse_ncFF("\n".join(lines))

    def test_witness_has_no_free_helpers(self):
        copy = {"productions": self.witness["productions"][:-1]}
        with self.assertRaises(ValueError):
            probe.verify_witness(self.graph, copy)

    def test_two_independent_depth_contracts(self):
        for name, expected in (("pool_any_depth", (88, 5)), ("pool_depth3", (97, 3))):
            witness = json.loads((probe.HERE / (name + ".witness.json")).read_text())
            verified = probe.verify_witness(self.graph, witness)
            self.assertEqual((verified["gate_count"], verified["depth"]), expected)
            self.assertEqual(verified["unused_selected"], 0)


if __name__ == "__main__":
    unittest.main()
