"""Public surface candidate tests; only pinned R1/R3 source is exercised."""
import unittest
from Hexaflag import HexaflagLattice, DIGITS
from src.registry import (Relation, fixture, FlatRegistry,
                       MicroRegistry, code_to_address, address_to_code)

class CanonicalSurface(unittest.TestCase):
    def test_all_registry_address_roundtrips(self):
        for i in range(7 ** 4):
            self.assertEqual(address_to_code(code_to_address(i)), i)
    def test_rooted_hexaflag_roundtrips(self):
        lattice = HexaflagLattice(max_depth=4)
        for a in ((0,), (1, DIGITS[0]), (2, DIGITS[1], DIGITS[4]),
                  (4, DIGITS[0], DIGITS[3], DIGITS[5], DIGITS[2])):
            self.assertEqual(lattice.encode(lattice.decode(a), a[0]), a)
    def test_registry_construction_and_identity(self):
        rel = fixture(64)
        f, m = FlatRegistry(rel), MicroRegistry(rel)
        keys = tuple(r.key for r in rel)
        self.assertEqual(f.resolve(keys), list(range(64)))
        self.assertEqual(m.resolve(keys), list(range(64)))
        m.check_consistency()
    def test_subtree_equivalence(self):
        for n in (64,128):
            f, m = FlatRegistry(fixture(n)), MicroRegistry(fixture(n))
            for level in range(5):
                for code in range(7 ** level):
                    a = code_to_address(code,level)
                    self.assertEqual(f.subtree_scan(a),f.subtree_sorted(a))
                    self.assertEqual(f.subtree_sorted(a),m.subtree(a))
            m.check_consistency()
    def test_contract_rejection(self):
        with self.assertRaisesRegex(ValueError,'CAPACITY_OUT_OF_BOUNDS'):
            fixture(8)
        with self.assertRaisesRegex(ValueError,'BAD_REGISTRY_SIZE_OR_TYPE'):
            FlatRegistry([])
        with self.assertRaises(ValueError):
            code_to_address(7**4)
        with self.assertRaises(ValueError):
            MicroRegistry([])

if __name__=='__main__': unittest.main()
