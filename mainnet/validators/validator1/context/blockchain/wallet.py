from Crypto.PublicKey import RSA
from Crypto.Signature import pkcs1_15
from Crypto.Hash import SHA256
import base64

class Wallet:
    def __init__(self):
        self.key_pair = RSA.generate(2048)

    @property
    def address(self) -> str:
        """Generate wallet address from public key"""
        public_key_bytes = self.key_pair.publickey().export_key()
        return base64.b64encode(SHA256.new(public_key_bytes).digest()).decode('utf-8')[:40]

    def sign_transaction(self, transaction) -> str:
        """Sign a transaction with the wallet's private key"""
        transaction_hash = SHA256.new(str(transaction.to_dict()).encode())
        signature = pkcs1_15.new(self.key_pair).sign(transaction_hash)
        return base64.b64encode(signature).decode('utf-8')

    def verify_signature(self, transaction, signature: str) -> bool:
        """Verify a transaction signature"""
        try:
            signature_bytes = base64.b64decode(signature)
            transaction_hash = SHA256.new(str(transaction.to_dict()).encode())
            pkcs1_15.new(self.key_pair.publickey()).verify(transaction_hash, signature_bytes)
            return True
        except (ValueError, TypeError):
            return False

    def export_public_key(self) -> str:
        """Export the public key"""
        return self.key_pair.publickey().export_key().decode('utf-8')

    def export_private_key(self) -> str:
        """Export the private key securely"""
        return self.key_pair.export_key().decode('utf-8')

    def import_private_key(self, private_key: str):
        """Import a private key"""
        self.key_pair = RSA.import_key(private_key)

    @classmethod
    def load_from_private_key(cls, private_key: str) -> 'Wallet':
        """Create a wallet instance from a private key"""
        wallet = cls()
        wallet.import_private_key(private_key)
        return wallet

    @staticmethod
    def verify_transaction_signature(transaction, public_key_str: str, signature: str) -> bool:
        """Verify a transaction signature with a public key"""
        try:
            public_key = RSA.import_key(public_key_str)
            signature_bytes = base64.b64decode(signature)
            transaction_hash = SHA256.new(str(transaction.to_dict()).encode())
            pkcs1_15.new(public_key).verify(transaction_hash, signature_bytes)
            return True
        except (ValueError, TypeError):
            return False
