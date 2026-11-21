# HexaFlake

**Original HexaFlake concept and geometric architecture: [@Akitti](https://x.com/Akitti).**

Bounded hierarchical geometry for sparse relational computation. HexaFlake combines exact logical aperture-7 addressing with a frequency-120 icosahedral geodesic research track, local Cubic Geometric Core (CGC) computation, and authorized equivariant relational transport. It is a computational research substrate, not a physical Yang–Mills simulation or a qualified cognitive swarm.

## Source map

| Component | Location | Scope |
|---|---|---|
| Hexaflag | [`Hexaflag.py`](Hexaflag.py) | Exact integer hierarchy; seven residue classes per refinement |
| CGC120 | [`CGC120.py`](CGC120.py) | Four 5×6 float64 channels; 120 trainable parameters, upstream reference |
| HCA88 | [`HCA88.c`](HCA88.c), [`HCA88.h`](HCA88.h) | Pinned native 88-parameter sparse-window kernel and ABI declarations |
| GEO144K | [`GEO144K/`](GEO144K/) | Procedural topology and logical address bridge |
| Supporting execution | [`src/`](src/) | Exact relation registry and scalar CGC implementation |
| Geometry regression | [`tests/`](tests/) | Address, registry and rejection checks |

The intended frequency-120 mesh contains 144,002 vertices, 432,000 edges and 288,000 faces. Logical addressing does not imply exact nested physical hexagons, connected prefixes or semantic adjacency. CGC and HCA88 reference implementations are separately qualified in bounded experiments; this initial source layout is not an end-to-end runtime or a claim of common checkpoint/host compatibility.

See [RESULTS](RESULTS.md) for the consolidated research findings and [REFERENCES](REFERENCES.md) for source pins, attribution and publication gates.

Runtime changes must remain volatile; active state, relations, recurrence, trial count and memory must be explicitly bounded. No unattended storage mutation or unbounded materialization. Runtime testing requires a fail-closed write sandbox; disabling Python bytecode alone is insufficient.

## Component tests

Python 3.10+ and PyTorch 2.0+ are declared in `pyproject.toml`; native tests need a C11 compiler and libm. Run from the repository root in an externally enforced volatile-write sandbox. Set `scratch` to an existing writable, executable volatile directory before running the following commands (on no-exec tmpfs, use an operator-provided in-memory executable host).

```sh
cc -std=c11 -O2 -ffp-contract=off -I. HCA88.c tests/test_hca88.c -lm -o "$scratch/native-smoke"
"$scratch/native-smoke"
HEXAFLAKE_NATIVE_SMOKE="$scratch/native-smoke" python -B -m unittest discover -s tests -v
```

The synthetic coupling test uses fixed CPU CGC weights, a bounded two-window native recurrence and a CGC readout. It checks a two-hop response and a zero-input control. It is not the historical R5B host or a learned swarm. Without the native executable, that particular test is skipped.

## License and attribution

The project software is distributed under [Apache-2.0](LICENSE), except for the CPython-derived summation routine, whose applicable Python license is retained in [licenses/CPython.txt](licenses/CPython.txt). See [NOTICE](NOTICE) for credit and source provenance. This repository is a component-level research snapshot; the historical R5B host is deliberately excluded. No full-scale swarm or production runtime qualification is claimed.
