# BT2C Wallet Security Guide

## Overview

This document details the security measures implemented in the BT2C wallet system, including key generation, storage, transaction signing, key rotation, and secure backup/restore functionality.

## Wallet Creation Process

### 1. Key Generation
```python
from Crypto.PublicKey import RSA

# Generate 2048-bit RSA key pair
private_key = RSA.generate(2048)
public_key = private_key.publickey()
```

Key features:
- Uses 2048-bit RSA key pairs
- Generates cryptographically secure key pairs
- Implements secure random number generation
- Provides standardized key formats
- Creates BIP39 seed phrases for wallet recovery

### 2. Private Key Encryption

The encryption process uses multiple layers of security:

1. **Key Derivation**
```python
from Crypto.Protocol.KDF import PBKDF2
from Crypto.Hash import SHA512
import os

# Generate a random salt
salt = os.urandom(32)  # 32 bytes salt

# Derive key using PBKDF2 with SHA-512
key = PBKDF2(
    password=password.encode('utf-8'),
    salt=salt,
    dkLen=32,  # 256-bit key
    count=600000,  # 600,000 iterations
    hmac_hash_module=SHA512
)
```

2. **Encryption**
```python
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
import os

# Generate initialization vector
iv = os.urandom(16)

# Create AES cipher in CBC mode
cipher = AES.new(key, AES.MODE_CBC, iv)

# Encrypt the private key
encrypted_data = cipher.encrypt(pad(private_key_bytes, AES.block_size))

# Store encrypted data with salt and IV
wallet_data = {
    'encrypted_data': base64.b64encode(encrypted_data).decode('utf-8'),
    'salt': base64.b64encode(salt).decode('utf-8'),
    'iv': base64.b64encode(iv).decode('utf-8')
}
```
```

## Security Parameters

### Password Requirements
- Minimum length: 12 characters
- Must include at least 3 of the following character types:
  - Uppercase letters (A-Z)
  - Lowercase letters (a-z)
  - Digits (0-9)
  - Special characters (@$!%*?&#...)
- Entropy validation to ensure password strength

### Encryption Parameters
- Algorithm: AES-256-CBC with PKCS7 padding
- Key Derivation: PBKDF2 with SHA-512
- Salt Length: 32 bytes (increased from 16 bytes)
- IV Length: 16 bytes
- Derived Key Length: 32 bytes (256 bits)
- PBKDF2 Iterations: 600,000

### Key Management
- RSA Key Size: 2048 bits
- Key Rotation: Recommended every 90 days
- BIP39 Seed Phrase: 24 words (256-bit entropy)
- Secure Backup Format: AES-256 encrypted with integrity verification

## Wallet Operations

### 1. Wallet Loading
```python
@classmethod
def load(cls, wallet_name, password):
    """
    Load a wallet from file
    """
    # Validate inputs
    if not wallet_name or not isinstance(wallet_name, str):
        raise ValueError("Wallet name must be a non-empty string")
    if not password or not isinstance(password, str):
        raise ValueError("Password must be a non-empty string")
        
    # Prevent path traversal attacks
    if '..' in wallet_name or '/' in wallet_name:
        raise ValueError("Invalid wallet name")
        
    # Construct wallet path
    wallet_dir = os.path.expanduser("~/.bt2c/wallets")
    wallet_path = os.path.join(wallet_dir, f"{wallet_name}.wallet")
    
    try:
        # Read encrypted wallet file
        with open(wallet_path, 'r') as f:
            wallet_data = json.load(f)
            
        # Extract data
        encrypted_key = base64.b64decode(wallet_data['encrypted_key'])
        salt = base64.b64decode(wallet_data['salt'])
        iv = base64.b64decode(wallet_data['iv'])
        address = wallet_data['address']
        seed_phrase = wallet_data.get('seed_phrase')
        key_created_at = wallet_data.get('key_created_at', int(time.time()))
        
        # Derive key from password using PBKDF2
        key = PBKDF2(
            password=password.encode('utf-8'),
            salt=salt,
            dkLen=32,
            count=PBKDF2_ITERATIONS,
            hmac_hash_module=SHA512
        )
        
        # Decrypt private key
        cipher = AES.new(key, AES.MODE_CBC, iv)
        decrypted_key = unpad(cipher.decrypt(encrypted_key), AES.block_size)
        
        # Create wallet instance
        wallet = cls()
        wallet.private_key = RSA.import_key(decrypted_key)
        wallet.public_key = wallet.private_key.publickey()
        wallet.address = address
        wallet.seed_phrase = seed_phrase
        wallet.key_created_at = key_created_at
        
        return wallet
    except FileNotFoundError:
        raise ValueError(f"Wallet not found: {wallet_name}")
    except (ValueError, KeyError, json.JSONDecodeError) as e:
        raise ValueError(f"Invalid wallet file or password: {str(e)}")
```

### 2. Transaction Signing
```python
def sign(self, data):
    """
    Sign data with the wallet's private key
    """
    if not self.private_key:
        raise ValueError("No private key available for signing")
    
    # Validate input
    if not isinstance(data, (bytes, str)):
        raise TypeError("Data must be bytes or string")
        
    if isinstance(data, str):
        data = data.encode('utf-8')
        
    h = SHA256.new(data)
    signature = pkcs1_15.new(self.private_key).sign(h)
    return base64.b64encode(signature).decode('utf-8')
```

### 3. Address Generation
```python
def _generate_address(self, public_key):
    """
    Generate a wallet address from a public key
    """
    # Get DER format of public key
    public_key_bytes = public_key.export_key(format='DER')
    
    # Hash the public key with SHA256
    h = hashlib.sha256(public_key_bytes).digest()
    
    # Encode with base32 and format
    addr = base64.b32encode(h[:16]).decode('utf-8').lower()
    return f"bt2c_{addr}"
```

### 4. Key Rotation
```python
def rotate_keys(self, password):
    """
    Generate new key pair while preserving wallet address and seed phrase
    Maintains signature validity for transactions signed with previous keys
    """
    if not self.private_key or not self.seed_phrase:
        raise ValueError("Cannot rotate keys: wallet not fully initialized")
        
    # Store old key for verification
    old_private_key = self.private_key
    old_public_key = self.public_key
    
    # Export old public key in PEM format for future verification
    old_public_key_pem = old_public_key.export_key(format='PEM')
    
    # Generate new key pair from seed phrase
    self.private_key, self.public_key = self._generate_keys_from_seed(self.seed_phrase)
    self.key_created_at = int(time.time())
    
    # Save with new keys and old public key for verification
    self.previous_public_keys = self.previous_public_keys or []
    self.previous_public_keys.append(old_public_key_pem.decode('utf-8'))
    self.save(password)
    
    logger.info("wallet_keys_rotated", address=self.address)
    return True
```

### 5. Secure Backup Creation
```python
def create_secure_backup(self, password, backup_dir=None):
    """
    Create an encrypted backup of the wallet
    """
    if not self.private_key or not self.seed_phrase:
        raise ValueError("Cannot backup: wallet not fully initialized")
        
    # Set default backup directory
    if not backup_dir:
        backup_dir = os.path.expanduser("~/.bt2c/backups")
        
    # Ensure directory exists
    os.makedirs(backup_dir, exist_ok=True)
    
    # Generate salt and IV
    salt = os.urandom(32)
    iv = os.urandom(16)
    
    # Derive key from password
    key = PBKDF2(
        password=password.encode('utf-8'),
        salt=salt,
        dkLen=32,
        count=PBKDF2_ITERATIONS,
        hmac_hash_module=SHA512
    )
    
    # Prepare data for encryption
    private_key_data = self.private_key.export_key()
    data_to_encrypt = private_key_data + b"||SEPARATOR||" + self.seed_phrase.encode('utf-8')
    
    # Encrypt data
    cipher = AES.new(key, AES.MODE_CBC, iv)
    encrypted_data = cipher.encrypt(pad(data_to_encrypt, AES.block_size))
    
    # Create backup data structure
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    backup_data = {
        "version": "1.0",
        "address": self.address,
        "encrypted_data": base64.b64encode(encrypted_data).decode('utf-8'),
        "salt": base64.b64encode(salt).decode('utf-8'),
        "iv": base64.b64encode(iv).decode('utf-8'),
        "created_at": int(time.time()),
        "key_created_at": self.key_created_at
    }
    
    # Write backup file
    backup_file = os.path.join(backup_dir, f"{self.address}-{timestamp}.backup")
    with open(backup_file, 'w') as f:
        json.dump(backup_data, f, indent=2)
        
    logger.info("wallet_backup_created", address=self.address, backup_file=backup_file)
    return backup_file
```
```

## Security Best Practices

### 1. Private Key Management
- Never store unencrypted private keys
- Implement automatic key rotation every 90 days
- Use the `needs_rotation()` method to check if keys are due for rotation
- Create regular secure backups with `create_secure_backup()`
- Store backups in secure, offline locations

### 2. Password Management
- Enforce strong password policy (min 12 chars, 3 character types)
- Use entropy calculation to ensure password strength
- Implement password change functionality during key rotation
- Maintain separate passwords for wallet access and backups
- Consider using a password manager for secure storage

### 3. Transaction Security
- Verify transaction details before signing
- Implement transaction nonce to prevent replay attacks
- Add transaction expiry to limit validity period (maximum 86400 seconds)
- Include chain ID in transaction signatures
- Verify signatures before broadcasting transactions
- Support signature verification with previous keys after key rotation
- Validate transaction hash during signature verification

## Recovery Procedures

### 1. Backup Creation
```python
# Create a secure backup of your wallet
wallet = Wallet.load("my_wallet", "strong-password-123")
backup_file = wallet.create_secure_backup("backup-password-456")
print(f"Backup created at: {backup_file}")
```

### 2. Wallet Recovery from Backup
```python
# Restore a wallet from backup
backup_file = "/path/to/bt2c_address-20250624-220149.backup"
restored_wallet = Wallet.restore_from_backup(backup_file, "backup-password-456")
print(f"Restored wallet address: {restored_wallet.address}")
```

### 3. Wallet Recovery from Seed Phrase
```python
# Recover wallet from seed phrase
seed_phrase = "word1 word2 word3 ... word24"  # 24-word BIP39 seed phrase
wallet = Wallet.recover_from_seed(seed_phrase, "new-strong-password-789")
print(f"Recovered wallet address: {wallet.address}")
```

## Security Checklist

### Implementation
- [x] Password validation with entropy checks
- [x] Key encryption with PBKDF2 and AES-256
- [x] Secure storage with path traversal protection
- [x] Transaction signing with RSA-2048
- [x] Address validation
- [x] Key rotation mechanism with signature verification
- [x] Secure backup and restore with key history preservation
- [x] Transaction replay protection with nonce and expiry

### Testing
- [x] Unit tests for password validation
- [x] Unit tests for key rotation
- [x] Unit tests for backup/restore
- [x] Integration tests for transaction signing and verification
- [x] Integration tests for key rotation signature verification
- [x] Integration tests for mempool transaction acceptance
- [ ] Security audits
- [ ] Penetration testing
- [ ] Stress testing

### Monitoring
- [x] Key lifecycle event logging
- [x] Wallet creation/loading logging
- [x] Backup/restore operation logging
- [ ] Failed attempts logging
- [ ] Suspicious activity detection

## Emergency Procedures

### 1. Compromised Wallet
1. Stop using the compromised wallet immediately
2. Create a new wallet with `Wallet.generate()`
3. If you have your seed phrase, recover funds using `Wallet.recover_from_seed()`
4. If you have a backup, restore using `Wallet.restore_from_backup()`
5. Transfer any remaining funds to the new wallet
6. Report the incident to the BT2C security team

### 2. Lost Password
1. If you have your seed phrase, recover your wallet:
   ```python
   wallet = Wallet.recover_from_seed(seed_phrase, new_password)
   ```
2. If you have a backup with a different password, restore from it:
   ```python
   wallet = Wallet.restore_from_backup(backup_file, backup_password)
   ```
3. If neither option is available, your funds may be unrecoverable

## Contact Information

For security-related issues:
- Email: security@bt2c.net
- Bug bounty program: https://bt2c.net/security
- Emergency: emergency@bt2c.com
- Support: support@bt2c.com
- Bug Reports: security@bt2c.com

## Updates

This documentation should be reviewed and updated with each security enhancement or wallet feature update.
