#!/usr/bin/env python3
"""Consistent Hashing — minimal implementation with virtual nodes."""

import hashlib
import bisect


class ConsistentHashRing:
    def __init__(self, num_vnodes=150):
        self.num_vnodes = num_vnodes
        self.ring = {}          # hash_value → node_name
        self.sorted_keys = []   # sorted hash positions for binary search
        self.nodes = set()

    def _hash(self, key: str) -> int:
        return int(hashlib.md5(key.encode()).hexdigest()[:8], 16)

    def add_node(self, node: str):
        if node in self.nodes:
            return
        self.nodes.add(node)
        for i in range(self.num_vnodes):
            h = self._hash(f"{node}#vnode{i}")
            self.ring[h] = node
            bisect.insort(self.sorted_keys, h)

    def remove_node(self, node: str):
        if node not in self.nodes:
            return
        self.nodes.discard(node)
        for i in range(self.num_vnodes):
            h = self._hash(f"{node}#vnode{i}")
            del self.ring[h]
            self.sorted_keys.remove(h)

    def get_node(self, key: str) -> str:
        if not self.ring:
            raise ValueError("empty ring")
        h = self._hash(key)
        idx = bisect.bisect_right(self.sorted_keys, h) % len(self.sorted_keys)
        return self.ring[self.sorted_keys[idx]]


# ---------------------------------------------------------------------------
# Demo
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    nodes = ["cache-1", "cache-2", "cache-3"]
    ring = ConsistentHashRing(num_vnodes=150)
    for n in nodes:
        ring.add_node(n)

    test_keys = [f"user:{i}" for i in range(1, 11)]

    # 1) Initial mapping
    print("=== Initial mapping (3 nodes) ===")
    before = {}
    for key in test_keys:
        node = ring.get_node(key)
        before[key] = node
        print(f"  {key:>10} → {node}")

    # 2) Remove a node — show minimal remapping
    ring.remove_node("cache-3")
    print("\n=== After removing cache-3 ===")
    moved = 0
    for key in test_keys:
        node = ring.get_node(key)
        tag = " ← MOVED" if node != before[key] else ""
        if tag:
            moved += 1
        print(f"  {key:>10} → {node}{tag}")
    print(f"\nMoved: {moved}/{len(test_keys)} ({moved/len(test_keys)*100:.0f}%)  |  Ideal 1/N: {1/len(nodes)*100:.0f}%")

    # 3) Add a new node — show minimal remapping
    before_add = {key: ring.get_node(key) for key in test_keys}
    ring.add_node("cache-4")
    print("\n=== After adding cache-4 ===")
    moved = 0
    for key in test_keys:
        node = ring.get_node(key)
        tag = " ← MOVED" if node != before_add[key] else ""
        if tag:
            moved += 1
        print(f"  {key:>10} → {node}{tag}")
    print(f"\nMoved: {moved}/{len(test_keys)} ({moved/len(test_keys)*100:.0f}%)")
