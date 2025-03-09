import os
import json
from coincurve import PrivateKey, PublicKey
from typing import Tuple, Optional

class KeyPair:
    def __init__(self, private_key: Optional[bytes] = None):
        """Initialize a keypair with an optional private key"""
        if private_key:
            self.private_key = PrivateKey(private_key)
        else:
            self.private_key = PrivateKey()
        self.public_key = self.private_key.public_key

    @classmethod
    def from_hex(cls, private_key_hex: str) -> 'KeyPair':
        """Create a keypair from a hex-encoded private key"""
        return cls(bytes.fromhex(private_key_hex))

    def sign(self, message: bytes) -> bytes:
        """Sign a message using the private key"""
        return self.private_key.sign(message)

    def verify(self, signature: bytes, message: bytes) -> bool:
        """Verify a signature using the public key"""
        return self.public_key.verify(signature, message)

    @property
    def address(self) -> str:
        """Get the address (last 20 bytes of public key hash)"""
        return self.public_key.format().hex()[-40:]

    def export_private(self) -> str:
        """Export the private key as hex"""
        return self.private_key.secret.hex()

    def export_public(self) -> str:
        """Export the public key as hex"""
        return self.public_key.format().hex()

def generate_validator_keys() -> Tuple[str, str, str]:
    """Generate a new validator keypair and return (private_key, public_key, address)"""
    keypair = KeyPair()
    return (
        keypair.export_private(),
        keypair.export_public(),
        keypair.address
    )

def sign_block(block_dict: dict, private_key_hex: str) -> str:
    """Sign a block using a validator's private key"""
    # Remove existing signature if any
    block_dict = block_dict.copy()
    block_dict.pop('signature', None)
    
    # Create message from sorted JSON
    message = json.dumps(block_dict, sort_keys=True).encode()
    
    # Sign message
    keypair = KeyPair.from_hex(private_key_hex)
    signature = keypair.sign(message)
    
    return signature.hex()

def verify_block_signature(block_dict: dict, signature_hex: str, public_key_hex: str) -> bool:
    """Verify a block's signature using a validator's public key"""
    # Remove existing signature
    block_dict = block_dict.copy()
    block_dict.pop('signature', None)
    
    # Create message from sorted JSON
    message = json.dumps(block_dict, sort_keys=True).encode()
    
    # Verify signature
    try:
        public_key = PublicKey(bytes.fromhex(public_key_hex))
        signature = bytes.fromhex(signature_hex)
        return public_key.verify(signature, message)
    except Exception:
        return False
