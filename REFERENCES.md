# Source provenance and attribution

Original HexaFlake concept and geometric architecture: [@Akitti](https://x.com/Akitti). Computational implementation and experimental development: Elpis / [abraxis717](https://github.com/abraxis717).

This is a component-level research source distribution, not a released integrated runtime. Source SHA-256 values refer to upstream bytes before any import-path change.

CGC upstream: https://github.com/abraxis717/CGC/tree/13ccb7e828237e56bebcc42ef02cacb6a1519d73
YM source revision: `eafdb15293c6e47010c159c9adb8d7977e22e868`. Native source redistributed under its upstream Apache-2.0 terms, with upstream NOTICE retained.
The maintainer has authorized redistribution of the project contributions under Apache-2.0.

| File | Original SHA-256 | Staged SHA-256 | Origin / change |
|---|---|---|---|
| `Hexaflag.py` | `190ddd3128d646135dcdc3553968edf798a30d43835e5d51e281d068249b2648` | `190ddd3128d646135dcdc3553968edf798a30d43835e5d51e281d068249b2648` | unchanged |
| `src/registry.py` | `26fc5b01a436002bd5ff41ade0ffcd64ac96662d89bcf3a55110ea842fa0e9aa` | `2ef5f2d127457316389e4b103d5ba5fc0e24f98cc78211a6206a1a17066c62b4` | import-path rebase; publication modification comment |
| `HCA88.c` | `87b53392c475fe2bb15290a52f73c9dfb6acb04294d2c22a859e5fc2d0e31e54` | `87b53392c475fe2bb15290a52f73c9dfb6acb04294d2c22a859e5fc2d0e31e54` | unchanged |
| `GEO144K/g1c_compact.py` | `4961c9f346dc4061aa2a7db61ea7a59fe700636e86f4490ff33fce2e162a2087` | `4961c9f346dc4061aa2a7db61ea7a59fe700636e86f4490ff33fce2e162a2087` | unchanged |
| `GEO144K/g2b_bridge.py` | `b751218b478be5f954ea2e2b2972d9857aa9e9b1ac5f62a035a17ba85cb059c1` | `18d226749b3c74b8b4d62f961c027414c3d1783b7c2101a8010c1b239a870d39` | unchanged; portable sibling and root-module imports; publication modification comment |
| `CGC120.py` | `a3b807adb30699df9c8279e2d19be2acc7cd6e856bb462730cff7e6c33273249` | `63c92263ba057a91d13580a57bec4fd0f5bfe8563d571ca2e2d88b282ad991b9` | CGC 13ccb7e828237e56bebcc42ef02cacb6a1519d73 src/cgc/four_channel.py (import-path rebase) |
| `src/ecsg_e0.py` | `92c987e0fb54d80193fd60ecc9a3e31088f0f9b7cd2cfe8e08c4636a198d7084` | `92c987e0fb54d80193fd60ecc9a3e31088f0f9b7cd2cfe8e08c4636a198d7084` | CGC 13ccb7e828237e56bebcc42ef02cacb6a1519d73 src/cgc/ecsg_e0.py |
| `LICENSE` | `c71d239df91726fc519c6eb72d318ec65820627232b2f796219e87dcf35d0ab4` | `c71d239df91726fc519c6eb72d318ec65820627232b2f796219e87dcf35d0ab4` | Consolidated Apache-2.0; CGC original hash, Elpis license distributed |

`HCA88.h` contains declarations extracted from the pinned native source; it is not a new numerical kernel.
The CGC and Elpis Apache-2.0 texts have been consolidated into `LICENSE`. See `NOTICE` and `licenses/CPython.txt` for additional attribution and license information.
The R5B bridge and complete native host/registry interface require dependency closure and separate clean-checkout qualification before inclusion.

CPython `math.fsum` reference: https://github.com/python/cpython/blob/v3.11.9/Modules/mathmodule.c (comparison reference; exact historical source revision was not recorded). `HCA88.c` is byte-identical to the pinned Elpis source.
