#!/usr/bin/env python3
"""
Consistent Hashing Implementation

This module provides a complete implementation of consistent hashing
with virtual nodes for better load distribution.
"""

import hashlib
import bisect
from typing import List, Optional, Tuple
from dataclasses import dataclass


@dataclass
class Node:
    """Represents a physical node in the consistent hash ring."""
    name: str
    virtual_nodes: int = 1


class ConsistentHashRing:
    """
    A consistent hash ring implementation with virtual nodes support.
    
    Features:
    - Virtual nodes for better load distribution
    - Automatic rebalancing when nodes are added/removed
    - Fault tolerance through node replication
    """
    
    def __init__(self, virtual_nodes_per_physical: int = 3):
        """
        Initialize the consistent hash ring.
        
        Args:
            virtual_nodes_per_physical: Number of virtual nodes per physical node
        """
        self.virtual_nodes_per_physical = virtual_nodes_per_physical
        self.ring: List[Tuple[int, str]] = []  # (hash_value, node_name)
        self.nodes: dict[str, Node] = {}
        self.replicas: int = 2  # Number of replicas for fault tolerance
    
    def _hash(self, key: str) -> int:
        """
        Generate a hash value for a given key.
        
        Args:
            key: The key to hash
            
        Returns:
            A 32-bit hash value
        """
        return int(hashlib.md5(key.encode()).hexdigest(), 16) % (2**32)
    
    def add_node(self, node_name: str, virtual_nodes: Optional[int] = None) -> None:
        """
        Add a physical node to the hash ring.
        
        Args:
            node_name: Name of the physical node
            virtual_nodes: Number of virtual nodes (defaults to configured value)
        """
        if virtual_nodes is None:
            virtual_nodes = self.virtual_nodes_per_physical
        
        node = Node(name=node_name, virtual_nodes=virtual_nodes)
        self.nodes[node_name] = node
        
        # Add virtual nodes
        for i in range(virtual_nodes):
            virtual_key = f"{node_name}#{i}"
            hash_value = self._hash(virtual_key)
            bisect.insort(self.ring, (hash_value, node_name))
        
        print(f"Added node '{node_name}' with {virtual_nodes} virtual nodes")
    
    def remove_node(self, node_name: str) -> None:
        """
        Remove a physical node from the hash ring.
        
        Args:
            node_name: Name of the node to remove
        """
        if node_name not in self.nodes:
            print(f"Node '{node_name}' not found")
            return
        
        # Remove all virtual nodes for this physical node
        self.ring = [(h, n) for h, n in self.ring if n != node_name]
        del self.nodes[node_name]
        
        print(f"Removed node '{node_name}'")
    
    def get_node(self, key: str) -> str:
        """
        Get the primary node for a given key.
        
        Args:
            key: The key to look up
            
        Returns:
            Name of the primary node
        """
        if not self.ring:
            raise ValueError("No nodes in the ring")
        
        hash_value = self._hash(key)
        
        # Find the first node with hash >= key's hash
        index = bisect.bisect_left(self.ring, (hash_value, ""))
        
        # Wrap around if we're at the end
        if index == len(self.ring):
            index = 0
        
        return self.ring[index][1]
    
    def get_replicas(self, key: str) -> List[str]:
        """
        Get replica nodes for a given key (for fault tolerance).
        
        Args:
            key: The key to look up
            
        Returns:
            List of replica node names
        """
        if not self.ring:
            raise ValueError("No nodes in the ring")
        
        hash_value = self._hash(key)
        replicas = []
        
        # Find the starting position
        index = bisect.bisect_left(self.ring, (hash_value, ""))
        if index == len(self.ring):
            index = 0
        
        # Collect unique nodes (skip duplicates)
        seen = set()
        current_index = index
        attempts = 0
        max_attempts = len(self.ring) * 2  # Prevent infinite loop
        
        while len(replicas) < self.replicas and attempts < max_attempts:
            node_name = self.ring[current_index][1]
            if node_name not in seen:
                replicas.append(node_name)
                seen.add(node_name)
            
            current_index = (current_index + 1) % len(self.ring)
            attempts += 1
        
        return replicas
    
    def get_load_distribution(self) -> dict[str, int]:
        """
        Get the load distribution across all nodes.
        
        Returns:
            Dictionary mapping node names to their load (number of keys)
        """
        load = {node_name: 0 for node_name in self.nodes.keys()}
        
        # Simulate key distribution by checking every possible hash position
        for i in range(0, 2**32, 2**20):  # Sample every 2^20 positions for efficiency
            index = bisect.bisect_left(self.ring, (i, ""))
            if index == len(self.ring):
                index = 0
            node_name = self.ring[index][1]
            load[node_name] += 1
        
        return load
    
    def print_ring(self) -> None:
        """Print the current state of the hash ring."""
        print("\nHash Ring State:")
        print("-" * 50)
        for hash_value, node_name in self.ring:
            print(f"Hash: {hash_value:10d} -> Node: {node_name}")
        print("-" * 50)


def demonstrate_consistent_hashing():
    """Demonstrate consistent hashing with examples."""
    print("Consistent Hashing Demonstration")
    print("=" * 50)
    
    # Create a hash ring
    ring = ConsistentHashRing(virtual_nodes_per_physical=3)
    
    # Add some nodes
    nodes = ["Node-A", "Node-B", "Node-C", "Node-D"]
    for node in nodes:
        ring.add_node(node)
    
    print(f"\nRing after adding {len(nodes)} nodes:")
    ring.print_ring()
    
    # Test key distribution
    test_keys = ["user:123", "session:456", "data:789", "cache:101", "temp:202"]
    
    print(f"\nKey Distribution:")
    print("-" * 30)
    for key in test_keys:
        primary = ring.get_node(key)
        replicas = ring.get_replicas(key)
        print(f"Key: {key:12} -> Primary: {primary:8} | Replicas: {replicas}")
    
    # Show load distribution
    print(f"\nLoad Distribution (sampled):")
    print("-" * 30)
    load = ring.get_load_distribution()
    for node, count in sorted(load.items()):
        print(f"{node}: {count} keys")
    
    # Demonstrate adding a new node
    print(f"\nAdding new node 'Node-E':")
    ring.add_node("Node-E")
    
    print(f"\nKey Distribution after adding Node-E:")
    print("-" * 40)
    for key in test_keys:
        primary = ring.get_node(key)
        replicas = ring.get_replicas(key)
        print(f"Key: {key:12} -> Primary: {primary:8} | Replicas: {replicas}")
    
    # Show new load distribution
    print(f"\nNew Load Distribution (sampled):")
    print("-" * 35)
    load = ring.get_load_distribution()
    for node, count in sorted(load.items()):
        print(f"{node}: {count} keys")
    
    # Demonstrate node removal
    print(f"\nRemoving node 'Node-B':")
    ring.remove_node("Node-B")
    
    print(f"\nKey Distribution after removing Node-B:")
    print("-" * 42)
    for key in test_keys:
        primary = ring.get_node(key)
        replicas = ring.get_replicas(key)
        print(f"Key: {key:12} -> Primary: {primary:8} | Replicas: {replicas}")


if __name__ == "__main__":
    demonstrate_consistent_hashing()