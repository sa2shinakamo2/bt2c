"""
Merkle tree implementation for BT2C blockchain using Python's built-in hashlib
"""
import hashlib
from typing import List, Optional

class MerkleTree:
    def __init__(self, leaves: List[bytes]):
        """Initialize a Merkle tree with the given leaves."""
        if not leaves:
            raise ValueError("Cannot create a Merkle tree with no leaves")
        
        # Ensure even number of leaves by duplicating last leaf if necessary
        if len(leaves) % 2 == 1:
            leaves = leaves + [leaves[-1]]
            
        self.leaves = leaves
        self.layers = [leaves]
        self._build_tree()
        
    def _hash_pair(self, left: bytes, right: bytes) -> bytes:
        """Hash a pair of nodes using SHA3-256."""
        combined = left + right
        return hashlib.sha3_256(combined).digest()
        
    def _build_tree(self):
        """Build the Merkle tree from leaves to root."""
        current_layer = self.leaves
        
        while len(current_layer) > 1:
            next_layer = []
            for i in range(0, len(current_layer), 2):
                left = current_layer[i]
                right = current_layer[i + 1] if i + 1 < len(current_layer) else current_layer[i]
                parent = self._hash_pair(left, right)
                next_layer.append(parent)
            self.layers.append(next_layer)
            current_layer = next_layer
            
    def get_root(self) -> bytes:
        """Get the Merkle root hash."""
        return self.layers[-1][0]
    
    def get_proof(self, leaf_index: int) -> List[bytes]:
        """Get the Merkle proof for a leaf at the given index."""
        if leaf_index < 0 or leaf_index >= len(self.leaves):
            raise ValueError("Leaf index out of range")
            
        proof = []
        current_index = leaf_index
        
        for layer in self.layers[:-1]:  # Exclude root layer
            is_right = current_index % 2 == 0
            pair_index = current_index - 1 if is_right else current_index + 1
            
            if pair_index < len(layer):
                proof.append(layer[pair_index])
                
            current_index //= 2
            
        return proof
    
    def verify_proof(self, leaf: bytes, proof: List[bytes], leaf_index: int) -> bool:
        """Verify a Merkle proof for the given leaf."""
        current = leaf
        current_index = leaf_index
        
        for sibling in proof:
            if current_index % 2 == 0:
                current = self._hash_pair(current, sibling)
            else:
                current = self._hash_pair(sibling, current)
            current_index //= 2
            
        return current == self.get_root()
