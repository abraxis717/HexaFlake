# Modified for HexaFlake publication: historical imports rebased to public modules.
"""R3: matched relation registries for a fixed-depth logical Hexaflag tree.

This is *not* geometric adjacency, GoldbergHexa, or Yang-Mills transport.
Both registries store identical relation IDs, frozen node addresses and updates.
Hierarchical prefix buckets trade O(E*depth) auxiliary index entries for O(1)
subtree selection. Sorted flat ranges provide a strong nonhierarchical baseline.
"""
from __future__ import annotations
from bisect import bisect_left
from dataclasses import dataclass
from typing import Sequence
from Hexaflag import DIGITS, HexaflagLattice

DEPTH = 4
MAX_EDGES = 4096
MAX_LOOKUP = 1024
MAX_SUBTREE_RESULT = 4096
_NODES = 7 ** DEPTH
_DIGIT_TO_ID = {d: i for i, d in enumerate(DIGITS)}


def code_to_address(code: int, depth: int = DEPTH) -> tuple:
    if type(depth) is not int or not 0 <= depth <= DEPTH:
        raise ValueError('DEPTH_INVALID')
    if type(code) is not int or not 0 <= code < 7**depth:
        raise ValueError('CODE_OUT_OF_RANGE')
    digits = [0] * depth
    for i in range(depth - 1, -1, -1):
        code, digit = divmod(code, 7)
        digits[i] = DIGITS[digit]
    return (depth, *digits)


def address_to_code(addr: tuple, depth: int | None = None) -> int:
    if not isinstance(addr, tuple) or not addr or type(addr[0]) is not int:
        raise ValueError('ADDRESS_INVALID')
    n = addr[0]
    if type(n) is not int or not 0 <= n <= DEPTH or len(addr) != n + 1:
        raise ValueError('ADDRESS_INVALID')
    if depth is not None and n != depth:
        raise ValueError('ADDRESS_DEPTH_MISMATCH')
    result = 0
    for d in addr[1:]:
        if not isinstance(d, tuple) or d not in _DIGIT_TO_ID:
            raise ValueError('ADDRESS_DIGIT_INVALID')
        result = result * 7 + _DIGIT_TO_ID[d]
    return result


@dataclass(frozen=True)
class Relation:
    relation_id: int
    source: tuple
    target: tuple
    channel: int

    @property
    def key(self) -> tuple:
        return (self.source, self.target, self.channel)


def fixture(count: int) -> tuple[Relation, ...]:
    """First 64 fixed hotspot edges; remaining edges distributed across nodes.

    The same first 64 rows exist regardless of count. Channel ensures distinct
    relation identities even when endpoints repeat. No topology-neighbor claim.
    """
    if type(count) is not int or not 64 <= count <= MAX_EDGES:
        raise ValueError('CAPACITY_OUT_OF_BOUNDS')
    result = []
    for i in range(count):
        src = 0 if i < 64 else 1 + ((i * 37) % (_NODES - 1))
        dst = (i * 101 + 17) % _NODES
        result.append(Relation(i, code_to_address(src), code_to_address(dst), i % 8))
    return tuple(result)


def _validate_relations(relations: Sequence[Relation]) -> tuple[Relation, ...]:
    r = tuple(relations)
    if not 1 <= len(r) <= MAX_EDGES or any(type(x) is not Relation for x in r):
        raise ValueError('BAD_REGISTRY_SIZE_OR_TYPE')
    if any(x.relation_id != j for j, x in enumerate(r)):
        raise ValueError('RELATION_IDS_REQUIRE_CONTIGUOUS_ORDER')
    if len({x.key for x in r}) != len(r):
        raise ValueError('DUPLICATE_RELATION_KEY')
    for x in r:
        address_to_code(x.source, DEPTH)
        address_to_code(x.target, DEPTH)
        if type(x.channel) is not int or x.channel < 0:
            raise ValueError('INVALID_CHANNEL')
    return r


def _prefix(addr: tuple) -> tuple[int, int]:
    return addr[0], address_to_code(addr)


class FlatRegistry:
    """Direct hash lookup + strong sorted-prefix-range baseline, plus scan control."""
    def __init__(self, relations: Sequence[Relation]):
        self.relations = _validate_relations(relations)
        self.identity = {r.key: r.relation_id for r in self.relations}
        sorted_pairs = sorted((address_to_code(r.source, DEPTH), r.relation_id)
                              for r in self.relations)
        self.codes = tuple(c for c, _ in sorted_pairs)
        self.sorted_ids = tuple(i for _, i in sorted_pairs)

    def resolve(self, keys: Sequence[tuple]) -> list[int]:
        if not 1 <= len(keys) <= MAX_LOOKUP:
            raise ValueError('INVALID_LOOKUP_COUNT')
        return [self.identity[k] for k in keys]

    def subtree_sorted(self, addr: tuple) -> list[int]:
        level, p = _prefix(addr)
        factor = 7 ** (DEPTH - level)
        lo = bisect_left(self.codes, p * factor)
        hi = bisect_left(self.codes, (p + 1) * factor)
        if hi - lo > MAX_SUBTREE_RESULT:
            raise ValueError('TOO_MANY_RESULTS')
        return sorted(self.sorted_ids[lo:hi])

    def subtree_scan(self, addr: tuple) -> list[int]:
        level, p = _prefix(addr)
        factor = 7 ** (DEPTH - level)
        return [r.relation_id for r in self.relations
                if address_to_code(r.source, DEPTH) // factor == p]


class MicroRegistry:
    """Identical direct keys, additional explicit parent-prefix buckets."""
    def __init__(self, relations: Sequence[Relation]):
        self.relations = _validate_relations(relations)
        self.identity = {r.key: r.relation_id for r in self.relations}
        self.prefix = {}
        for r in self.relations:
            n = address_to_code(r.source, DEPTH)
            for level in range(DEPTH + 1):
                key = (level, n // (7 ** (DEPTH - level)))
                self.prefix.setdefault(key, []).append(r.relation_id)
        self.prefix = {k: tuple(v) for k,v in self.prefix.items()}

    def resolve(self, keys: Sequence[tuple]) -> list[int]:
        if not 1 <= len(keys) <= MAX_LOOKUP:
            raise ValueError('INVALID_LOOKUP_COUNT')
        return [self.identity[k] for k in keys]

    def subtree(self, addr: tuple) -> list[int]:
        return list(self.prefix.get(_prefix(addr), ()))

    def check_consistency(self) -> None:
        flat = FlatRegistry(self.relations)
        for key, expected in flat.identity.items():
            if self.identity.get(key) != expected:
                raise ValueError('IDENTITY_INDEX_CORRUPTED')
        expected_keys = set()
        for r in self.relations:
            n = address_to_code(r.source, DEPTH)
            for level in range(DEPTH + 1):
                p = n // (7 ** (DEPTH - level))
                expected_keys.add((level, p))
        if set(self.prefix) != expected_keys:
            raise ValueError('PREFIX_KEY_CORRUPTED')
        for level, p in expected_keys:
            addr = code_to_address(p, level)
            if self.subtree(addr) != flat.subtree_sorted(addr):
                raise ValueError('PREFIX_CONTENT_CORRUPTED')


def available_source_nodes(registry: FlatRegistry) -> int:
    return len({r.source for r in registry.relations})
