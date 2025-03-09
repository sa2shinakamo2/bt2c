"""
Verifiable Random Function (VRF) implementation for BT2C blockchain.
This module provides cryptographic proof of randomness for validator selection.
"""

import hashlib
import hmac
import os
from typing import Tuple, Optional
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.utils import decode_dss_signature
from cryptography.exceptions import InvalidKey

class VRFProvider:
    def __init__(self, private_key: Optional[ec.EllipticCurvePrivateKey] = None):
        """Initialize VRF provider with an optional private key."""
        if private_key is None:
            private_key = ec.generate_private_key(ec.SECP256K1())
        self.private_key = private_key
        self.public_key = private_key.public_key()

    @staticmethod
    def generate_keypair() -> Tuple[ec.EllipticCurvePrivateKey, ec.EllipticCurvePublicKey]:
        """Generate a new VRF keypair."""
        private_key = ec.generate_private_key(ec.SECP256K1())
        public_key = private_key.public_key()
        return private_key, public_key

    def prove(self, message: bytes) -> Tuple[bytes, bytes]:
        """Generate VRF proof for the given message."""
        # Sign the message using ECDSA
        signature = self.private_key.sign(
            message,
            ec.ECDSA(hashes.SHA256())
        )

        # Convert the signature to proof
        r, s = decode_dss_signature(signature)
        proof = r.to_bytes(32, byteorder='big') + s.to_bytes(32, byteorder='big')

        # Generate the output hash
        output = self._hash_proof(message, proof)

        return proof, output

    def verify(self, message: bytes, proof: bytes, output: bytes, public_key: ec.EllipticCurvePublicKey) -> bool:
        """Verify a VRF proof."""
        try:
            # Split proof into r and s components
            r = int.from_bytes(proof[:32], byteorder='big')
            s = int.from_bytes(proof[32:], byteorder='big')

            # Reconstruct the signature
            signature = encode_dss_signature(r, s)

            # Verify the signature
            public_key.verify(
                signature,
                message,
                ec.ECDSA(hashes.SHA256())
            )

            # Verify the output
            computed_output = self._hash_proof(message, proof)
            return computed_output == output

        except (ValueError, InvalidKey):
            return False

    @staticmethod
    def _hash_proof(message: bytes, proof: bytes) -> bytes:
        """Hash the proof with the message to generate the final output."""
        h = hmac.new(proof, message, hashlib.sha256)
        return h.digest()

    def get_public_key(self) -> ec.EllipticCurvePublicKey:
        """Get the public key."""
        return self.public_key

    @staticmethod
    def proof_to_hash(proof: bytes) -> int:
        """Convert a proof to a deterministic hash value."""
        return int.from_bytes(hashlib.sha256(proof).digest(), byteorder='big')

    def compute_validator_priority(self, epoch: int, stake: int) -> int:
        """Compute validator priority for block production."""
        message = epoch.to_bytes(8, byteorder='big')
        proof, _ = self.prove(message)
        hash_value = self.proof_to_hash(proof)
        
        # Combine hash with stake to determine priority
        # Higher stake = higher chance of being selected
        return (hash_value * stake) % (2**256)
