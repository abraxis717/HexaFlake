"""CPU synthetic smoke; no pretrained parameters or external local projects."""
import importlib
import unittest

class Components(unittest.TestCase):
    def test_cgc120(self):
        import torch
        from CGC120 import CGC120
        w = torch.full((4,5,6), .1, dtype=torch.float64, device='cpu')
        m = CGC120(w)
        self.assertEqual(sum(p.numel() for p in m.parameters()),120)
        x = torch.full((2,5), .2, dtype=torch.float64, device='cpu')
        y = m(x)
        self.assertEqual(tuple(y.shape),(2,4))
        self.assertTrue(torch.allclose(y, torch.full_like(y,.333),rtol=0,atol=1e-14))
        y.sum().backward()
        self.assertTrue(all(p.grad is not None and bool(torch.isfinite(p.grad).all()) for p in m.parameters()))
    def test_geo_imports(self):
        # Import closure only; not a topology/144K execution qualification.
        importlib.import_module('GEO144K.g1c_compact')
        importlib.import_module('GEO144K.g2b_bridge')
