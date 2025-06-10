
# BT2C Wallet Key Management Implementation Guide

## Issue
The current BT2C wallet implementation has a key derivation consistency issue:
- The same seed phrase generates different private keys and addresses each time
- This prevents reliable wallet recovery using seed phrases

## Fix
Implement deterministic key derivation to ensure that the same seed phrase always 
produces the same keys and addresses:

1. Modify the `Wallet.generate` method to use deterministic key generation:
   ```python
   @classmethod
   def generate(cls, seed_phrase=None):
       try:
           wallet = cls()
           
           # Generate mnemonic if not provided
           if not seed_phrase:
               m = Mnemonic("english")
               seed_phrase = m.generate(strength=256)
           
           wallet.seed_phrase = seed_phrase
           
           # Derive deterministic seed from mnemonic
           m = Mnemonic("english")
           seed_bytes = m.to_seed(seed_phrase)
           
           # Create a deterministic seed for RSA key generation
           key_seed = hashlib.sha256(seed_bytes).digest()
           
           # Save the state of the random generator
           state = random.getstate()
           
           try:
               # Seed the random generator deterministically
               random.seed(int.from_bytes(key_seed, byteorder='big'))
               
               # Generate RSA key
               private_key = RSA.generate(2048)
               public_key = private_key.publickey()
               
               wallet.private_key = private_key
               wallet.public_key = public_key
               
               # Generate address from public key
               wallet.address = wallet._generate_address(wallet.public_key)
               
               return wallet
           finally:
               # Restore the random generator state
               random.setstate(state)
               
       except Exception as e:
           import structlog
           logger = structlog.get_logger()
           logger.error("wallet_generation_failed", error=str(e))
           raise ValueError(f"Failed to generate wallet: {str(e)}")
   ```

2. Update the `Wallet.recover` method to use the deterministic key generation:
   ```python
   @classmethod
   def recover(cls, seed_phrase, password=None):
       # Generate a wallet with the given seed phrase
       wallet = cls.generate(seed_phrase)
       
       # If a password is provided, try to find and load the wallet file
       if password:
           # Implementation of file search and loading
           pass
       
       return wallet
   ```

3. Add comprehensive tests to verify key derivation consistency:
   - Test that the same seed phrase produces the same keys
   - Test that recovered wallets have the same address as the original
   - Test that signatures from recovered wallets match the original

## Migration
For existing wallets, provide a migration path:
1. Create a tool to re-generate wallet files with deterministic keys
2. Ensure that users can recover their wallets using their seed phrases
3. Update documentation to reflect the changes

## Security Considerations
1. The deterministic key generation must be cryptographically secure
2. Private keys must still be properly encrypted in wallet files
3. Password protection must be maintained for wallet files
