# HexaFlake — quick start

**Goal:** build the native HCA88 component and verify that valid inputs work and invalid inputs fail closed. No model download, GPU, PyTorch or Python package installation is needed for the native test.

## 1. Prerequisites

- Linux x86-64, Python 3.10 or newer, Git, and a C11 compiler (`cc`, GCC or Clang) with the C standard library and libm.
- Landlock ABI 3 or newer (normally Linux 6.2+ with Landlock enabled), procfs, executable anonymous memory (`memfd_create`), and RAM-backed `/dev/shm` with at least 64 MiB free.
- At least 1 GiB available RAM and no active swap in the execution environment. Use a dedicated Linux VM configured accordingly if your normal machine does not meet these requirements. The runner does not change your machine configuration.

On Debian/Ubuntu, the tools can be installed through the system package manager as a deliberate administrative action:

```sh
sudo apt install git python3 build-essential
```

## 2. Clone and run

```sh
git clone https://github.com/abraxis717/HexaFlake.git
cd HexaFlake
python3 -B smoke.py
```

Expected successful output (the Landlock ABI number depends on your kernel):

```text
VOLATILE_WRITE_BOUNDARY=PASS LANDLOCK_ABI=3
HCA88_ABI=4 FSUM=PASS RECURRENT_TRANSPORT=PASS OVERLAP_REJECTION_ATOMIC=PASS
INVALID_NONFINITE_INPUT_REJECTED=PASS
HEXAFLAKE_SMOKE=PASS MODE=NATIVE
```

The smoke builds HCA88 from the actual root-level C source. It verifies compensated summation, one- and two-round transport, rejection of overlapping writes without changing the state, and rejection of non-finite bridge inputs. The last check intentionally passes `nan` to the C test and requires a nonzero exit code. The runner also checks that a write-open on the checkout README is denied, without changing its contents.

Any missing prerequisite, compilation error, unexpected result or denied executable-memory setup produces `HEXAFLAKE_SMOKE=HOLD` and a nonzero exit code. There is no fallback to unsandboxed execution. Read the error to see which prerequisite failed. The runner does not install dependencies, change swap settings, save checkpoints or log research arrays. The temporary build is removed on normal completion or handled failure.

## 3. Optional: full component suite

Use an existing Python 3.10+ environment with CPU-capable PyTorch 2.0+ installed and at least 5 GiB available RAM. The test subprocess uses a 4 GiB address-space ceiling. No models or weights are downloaded; the test uses fixed synthetic weights.

```sh
python3 -B smoke.py --full
```

This additionally checks address round trips, exact registry lookups, subtree equivalence, rejection controls, CGC120 parameter count and differentiation, GEO144K import closure and synthetic two-hop CGC→HCA88→CGC transport. The native executable is supplied automatically, so the coupling test need not be skipped. Expect `HEXAFLAKE_SMOKE=PASS MODE=FULL` after the Python tests pass.

## 4. Where to read the code

- `Hexaflag.py`: logical aperture-7 hierarchy and coordinate decomposition.
- `CGC120.py`: four independent scalar ECS channels forming a 120-parameter reference core.
- `HCA88.c` / `HCA88.h`: native window transport, reconciliation and public ABI.
- `GEO144K/`: procedural geodesic research geometry and address bridge.
- `src/registry.py`: exact flat and hierarchical relation registries.
- `tests/test_hca88.c`: native smoke and explicit rejection controls.
- `RESULTS.md` and `REFERENCES.md`: qualification results, limitations and source provenance.

The repository is a source-level research distribution. A Python wheel is not required for this quick start; the native smoke compiles the pinned C source directly. The existing `pyproject.toml` describes Python package build metadata, but no prebuilt wheel or compiled native library is claimed here.

These are component tests, not a reproduction of historical R5B checkpoints, a full 144K active runtime, a physical Yang–Mills simulation or evidence of cognitive superiority. Logical addressing does not establish exact physical nesting, connected prefixes or semantic adjacency.
