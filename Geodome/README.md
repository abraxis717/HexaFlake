# Geodome Reference API 1.0.0

CPU, single-thread, research reference. Core requires Python 3.10+ standard library only. The qualified interface is the fixed frequency-120 identity index and bounded state/scheduler; this release is not a learned cognitive architecture.

## Consumer example
From the repository root, run `python3 -I -B Geodome/run.py --example`. The launcher verifies source pins and reconstructs an isolated module tree in RAM. `python3 -I -B Geodome/run.py` runs the original C9 consumer with site packages disabled. For an embedding host, use the repository root and `Geodome/` on the import path inside a separately enforced volatile-write boundary. The qualification runner requires Landlock ABI >=3 and zero swap, hides the GPU and imposes address-space limits. Python objects and handles are not security capabilities against arbitrary code. The launcher never changes swap settings.

```python
import geodome as g
idx = g.build_index()
s = g.new_state(idx, width=2, capacity=2)
u = 0
v = idx.neighbors(u)[0]
a = s.acquire_address(idx.address(u))
b = s.acquire_vertex(v)
s.write(a, (7., 1.))
arc = idx.arc_id(u,v)
sch = g.SparseScheduler(s, (a,b), (arc,), max_active=2)
sch.start((u,))
while sch.status == 'RUNNING':
    sch.step(lambda arc, u, v, row: row, lambda v, old, inbox: inbox[0][1])
assert s.read(b) == (7.,1.)
s.reset()
```

## Stable surface
- `API_VERSION`, `SOURCE_PIN`, `MAPPING_SHA256`, `EDGE_SHA256`; `build_index()` verifies exact frequency-120 digests. `new_state(index, *, width=16, precision='f64', mode='sparse', capacity=None)` wraps the existing constructor.
- `GeoIndex`: vertices, edges, vertex_code, address, resolve_code, resolve, coordinate, resolve_coordinate, prefix_count, prefix_page, neighbors, arc_id, arc_endpoints, payload_bytes, mapping_sha256, edge_sha256. Prefix pages are sorted by address code, max 1024. Depth 7, capacity 823543, occupied 144002. Prefixes are logical, not necessarily connected. An arc ID is identity, not authorization.
- `NodeState`: acquire_vertex, acquire_address, handle, read, write, commit, release, reset, payload, resident, epoch. FP32/FP64, width 1..256, dense or bounded sparse. State handles are valid only in their originating instance and allocation generation/epoch. Batch 1..1024, rows immutable snapshots. Validate before commit; no whole-session rollback.
- `SparseScheduler`: explicit handles and arcs, start(vertices), step(transport, update), frontier, rounds, visits, status. Transport callback receives (arc, source, dest, source_row); update receives (vertex, old_row, ((arc,message),...)). Pure trusted callbacks only. No mutating state or scheduler in callbacks. Sources propagate old state; only changed destinations activate next round. Status NEW/RUNNING/QUIESCENT/ACTIVE_BUDGET/ARC_BUDGET/ROUND_BUDGET. Limits 4096 enrolled, 24576 arcs, 1024 touched per round (not merely sources), 256 rounds, 6291456 arc visits. Do not mutate enrolled state between rounds except under a separately defined host protocol. No automatic routing or parallelism. Atomicity is per validated round, not crash safety.
- Underscore members and mutable implementation fields are not supported integration interfaces. Treat public status/identity/configuration attributes as read-only. No cross-process serialization, checkpoint, dynamic graph mutation, or autograd guarantee.

## Optional adapter
`adapters/geodome_compute.py` is the exact C4 adapter. The CGC120 and HCA88 sources remain at the repository root, without duplication. Explicitly add `Geodome/adapters/` to the core import paths if using `geodome_compute`. PyTorch CPU float64 and a C11 HCA88 shared library (ABI 4; compile -std=c11 -O2 -ffp-contract=off -shared -fPIC -lm) are needed. Compile and load in RAM under the host write boundary (memfd on noexec tmpfs); do not create persistent binaries. `NativeHCA` accepts a validated ctypes library, `ComputeWindow` accepts admitted physical two-arc paths and width-16 FP64 state handles. Fixed synthetic shared weights and identity frames only. The adapter is not a scheduler backend qualification, trained checkpoint or general geometric transport authority. No requirement to import or use it in Elpis.

## Evidence and limitations
C1–C8 are hash-bound workstation receipts. C8 repeats C1–C7 from clean pinned sources on the same workstation, not independent hardware. C9 is a consumer smoke, not a new competence experiment. Historical pre-C1 evidence inventory incomplete, not relied on. No claim of semantic locality, learned address selection, autonomous routing, learned reasoning, geometric advantage, native scheduler throughput, concurrency safety, GPU execution or unbounded working sets. Generic scheduler is slower than task-specific BFS in C6. Runtime state remains volatile; this installation explicitly persists source and qualification records only. No token-indexed KV cache is allocated by this substrate; consumer model KV is separate. Source provenance and upstream license/notice are included. Do not change the pinned modules while retaining the same qualification identity.

## Reproduction

From a clean checkout of this release, on Linux x86-64 with Landlock ABI >=3, zero swap and at least 64 MiB free RAM-backed shared memory:

```sh
# Minimal consumer, no third-party packages; at least 1 GiB available RAM.
python3 -I -B Geodome/run.py --example
# Original C9 consumer, exact fingerprints, stdlib only.
python3 -I -B Geodome/run.py
# C1–C3, C5–C7 plus C9; skips optional neural C4 explicitly.
python3 -I -B Geodome/run.py --stdlib-replay
# Full C1–C7 deterministic replay plus C9, using CPU PyTorch and a C11 compiler.
# Requires at least 5 GiB available RAM; each process capped at 1 GiB except C4 (4 GiB).
python3 -I -B Geodome/run.py --replay
```

Use Python 3.10+; original replay used Python 3.11.9 and GCC 16.2.1. Full replay needs an already installed CPU-capable PyTorch in the selected interpreter's system/venv site packages. No package install or GPU access is performed by the runner. On unsupported hosts use a dedicated compatible Linux VM; do not weaken the write boundary. On a different machine deterministic comparison may fail; that is a HOLD, not a substituted pass. Timings and RSS are excluded from deterministic comparison. C1–C7 replay programs, comparator and C9 consumer are unchanged; `run.py` replaces only workstation orchestration. C8 is the prior clean-source replay receipt, not another numerical kernel. Runtime scratch and logs are removed automatically. Original receipts are in `evidence/` (one per gate); original archive manifests in `provenance/` retain historical relative paths for provenance, not direct verification of this reorganized tree. `PUBLIC.sha256` binds the actual public layout.

## Architecture

```text
Host-supplied computation / activation / authorization
                        |
                Geodome API (stdlib)
    +-------------------+-------------------+
    |                   |                   |
Hexaflag identity   GEO144K physical   Bounded volatile state
                    arc index           and sparse scheduler
                        |
          Optional explicit C4 interoperability
              CGC120 / HCA88 / PyTorch
```

Physical arcs and logical prefixes are identities, not admission or semantic evidence. C1 found 236/343 occupied depth-three prefix groups disconnected. C7 exact distributed composition used host-supplied physical trees and deterministic sufficient-statistics functions. No learned competence, autonomous routing, GPU execution, concurrency or superiority over transformers is established.

## Memory characterization

C2 identity payload: 11,502,238 bytes (10.97 MiB). C3 dense FP64 width 16: state plus logical metadata 20,160,408 bytes; combined with the index 31,662,646 bytes (30.20 MiB). Dense FP32 width 64: 38,592,792 bytes state plus metadata; combined 50,095,030 bytes (47.77 MiB). These are logical array payloads, excluding allocator slack, Python objects and temporary construction buffers; original C9 process peak RSS was 74,387,456 bytes (~70.94 MiB). C6 recorded whole-process RSS, not isolated per-arm peak. Fixed tested working-region execution cost was approximately invariant with total substrate capacity; Python scheduler is slower than specialized flat BFS and synchronous-sweep baselines. No substrate KV cache is allocated; external model KV is separate.

## Source and qualification identity

Frozen upstream commit: `993429cc94e9e3dcfd42df40502fa5b57175d883`. Release manifest: `07fa86bb3b6b88b0efe6c49e91e260e825678450e58c2dd10ffbff2750164e90`. C9 receipt: `44864c28986334de5a2da6abca095ba76aced07cf95dd160ba3204d7ae5b752c`. Original C8 source bundle: `a60a92e765d0a398461d25063f8cf66aa3d96d1e2f5a61b7b96dcbd75a33509d`.

| Fingerprint | SHA-256 |
|---|---|
| Mapping | `abe96202b554608bd8f5e702b70459daaaf4ab33eb7dfd058723fd4d1724f51b` |
| Edges | `712a8fc3d94685aeb614456ba8c88f6df7e6c6ea8a4c19e86d4d3865ad014231` |
| C7 deterministic computation | `7791820908c50b27b31c94848079c53d91091d5bb44e858a9d4b0a5555370260` |
| C9 consumer | `405ad9f3fe94258cd227f9b1823e974b6b91bdf10567b54c4ec759ab7c4c4c89` |

See [root results](../RESULTS.md), [provenance](../REFERENCES.md), [license](../LICENSE) and [notice](../NOTICE). Original HexaFlake concept and geometric architecture: [@Akitti](https://x.com/Akitti).
