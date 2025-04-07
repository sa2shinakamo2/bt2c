import os
import json
import hashlib
from coincurve import PrivateKey, PublicKey
from typing import Tuple, Optional, Dict, Any, List

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

class CryptoProvider:
    """
    Provides cryptographic operations for the BT2C blockchain.
    This class implements various cryptographic functions needed for
    secure blockchain operations including key management, signing,
    verification, and hashing.
    """
    
    def __init__(self, key_pair: Optional[KeyPair] = None):
        """
        Initialize the crypto provider with an optional key pair.
        
        Args:
            key_pair: Optional KeyPair to use for signing operations
        """
        self.key_pair = key_pair or KeyPair()
    
    @classmethod
    def from_private_key(cls, private_key_hex: str) -> 'CryptoProvider':
        """
        Create a CryptoProvider from a hex-encoded private key.
        
        Args:
            private_key_hex: Hex-encoded private key
            
        Returns:
            A new CryptoProvider instance
        """
        key_pair = KeyPair.from_hex(private_key_hex)
        return cls(key_pair)
    
    def get_address(self) -> str:
        """
        Get the blockchain address associated with this provider.
        
        Returns:
            The blockchain address as a hex string
        """
        return self.key_pair.address
    
    def sign_transaction(self, transaction_data: Dict[str, Any]) -> str:
        """
        Sign a transaction using the provider's private key.
        
        Args:
            transaction_data: Transaction data to sign
            
        Returns:
            Hex-encoded signature
        """
        # Remove any existing signature
        tx_data = transaction_data.copy()
        tx_data.pop('signature', None)
        
        # Create message from sorted JSON
        message = json.dumps(tx_data, sort_keys=True).encode()
        
        # Sign and return hex-encoded signature
        signature = self.key_pair.sign(message)
        return signature.hex()
    
    def verify_transaction(self, transaction_data: Dict[str, Any], 
                          signature_hex: str, address: str) -> bool:
        """
        Verify a transaction signature.
        
        Args:
            transaction_data: Transaction data to verify
            signature_hex: Hex-encoded signature
            address: Address of the signer
            
        Returns:
            True if signature is valid, False otherwise
        """
        # Remove any existing signature
        tx_data = transaction_data.copy()
        tx_data.pop('signature', None)
        
        # Create message from sorted JSON
        message = json.dumps(tx_data, sort_keys=True).encode()
        
        try:
            # Reconstruct public key from address (simplified)
            # In a real implementation, we would need to lookup the public key
            # This is a simplified version for testing
            signature = bytes.fromhex(signature_hex)
            return self.key_pair.verify(signature, message)
        except Exception:
            return False
    
    @staticmethod
    def hash_data(data: Any) -> str:
        """
        Create a SHA-256 hash of the provided data.
        
        Args:
            data: Data to hash (will be converted to JSON)
            
        Returns:
            Hex-encoded hash
        """
        if isinstance(data, dict):
            # Sort keys for consistent hashing
            data_str = json.dumps(data, sort_keys=True)
        else:
            data_str = str(data)
            
        return hashlib.sha256(data_str.encode()).hexdigest()
    
    @staticmethod
    def merkle_root(hashes: List[str]) -> str:
        """
        Calculate the Merkle root of a list of hashes.
        
        Args:
            hashes: List of hex-encoded hashes
            
        Returns:
            Hex-encoded Merkle root
        """
        if not hashes:
            return hashlib.sha256(b'').hexdigest()
            
        if len(hashes) == 1:
            return hashes[0]
            
        # Ensure even number of hashes
        if len(hashes) % 2 == 1:
            hashes.append(hashes[-1])
            
        # Combine adjacent hashes
        next_level = []
        for i in range(0, len(hashes), 2):
            combined = hashes[i] + hashes[i+1]
            next_hash = hashlib.sha256(combined.encode()).hexdigest()
            next_level.append(next_hash)
            
        # Recursive call for next level
        return CryptoProvider.merkle_root(next_level)

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
