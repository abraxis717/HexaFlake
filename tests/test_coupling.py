"""Synthetic CPU CGC -> native HCA88 -> CGC integration; not R5B reproduction."""
import os
import subprocess
import unittest

class SyntheticCoupling(unittest.TestCase):
    def test_cgc_hca_cgc(self):
        import torch
        from CGC120 import CGC120
        executable = os.environ.get('HEXAFLAKE_NATIVE_SMOKE')
        if not executable:
            self.skipTest('Set HEXAFLAKE_NATIVE_SMOKE to the separately built C smoke executable')
        inherited = os.environ.get('HEXAFLAKE_NATIVE_FD')
        kw = {'pass_fds': (int(inherited),)} if inherited else {}
        model = CGC120(torch.full((4,5,6), .1, dtype=torch.float64, device='cpu'))
        def chain(x):
            source = model(x).detach().reshape(4)
            result = subprocess.run([executable, *[format(v.item(), '.17g') for v in source]],
                                    capture_output=True, text=True, check=True, timeout=5, **kw)
            actual = torch.tensor([float(v) for v in result.stdout.split()], dtype=torch.float64)
            self.assertEqual(actual.shape, (4,))
            self.assertTrue(torch.allclose(actual, source/8, rtol=0, atol=1e-14))
            readout = model(torch.cat((actual, torch.tensor([.2], dtype=torch.float64)))[None,:])
            return readout.detach()
        x = torch.zeros((1,5), dtype=torch.float64)
        control = chain(x)
        active = chain(torch.full_like(x,.2))
        self.assertTrue(bool((active > control).all()))
