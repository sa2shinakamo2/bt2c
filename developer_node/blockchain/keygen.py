import os
import base64
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization
import json

def generate_validator_keys(validator_id: str, output_dir: str) -> tuple[str, str]:
    """Generate Ed25519 keypair for a validator.
    
    Args:
        validator_id: Identifier for the validator
        output_dir: Directory to save the keys
        
    Returns:
        Tuple of (public_key_b64, private_key_path)
    """
    # Generate new Ed25519 keypair
    private_key = ed25519.Ed25519PrivateKey.generate()
    public_key = private_key.public_key()
    
    # Get public key in bytes and encode as base64
    public_bytes = public_key.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw
    )
    public_key_b64 = base64.b64encode(public_bytes).decode('utf-8')
    
    # Serialize private key
    private_bytes = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    )
    
    # Save private key to file
    key_dir = os.path.join(output_dir, 'keys')
    os.makedirs(key_dir, exist_ok=True)
    
    private_key_path = os.path.join(key_dir, f'{validator_id}_priv.pem')
    with open(private_key_path, 'wb') as f:
        f.write(private_bytes)
    
    # Set secure permissions
    os.chmod(private_key_path, 0o600)
    
    return public_key_b64, private_key_path

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Generate validator keys")
    parser.add_argument("--validator-id", required=True, help="Validator identifier")
    parser.add_argument("--output-dir", required=True, help="Output directory for keys")
    parser.add_argument("--genesis-file", required=True, help="Genesis file to update")
    
    args = parser.parse_args()
    
    # Generate keys
    public_key_b64, private_key_path = generate_validator_keys(
        args.validator_id,
        args.output_dir
    )
    
    # Update genesis file with public key
    with open(args.genesis_file, 'r') as f:
        genesis = json.load(f)
    
    for validator in genesis['validators']:
        if validator['address'] == args.validator_id:
            validator['pub_key']['value'] = public_key_b64
            break
    
    with open(args.genesis_file, 'w') as f:
        json.dump(genesis, f, indent=2)
    
    print(f"Generated validator keys:")
    print(f"Public key (base64): {public_key_b64}")
    print(f"Private key saved to: {private_key_path}")
    print(f"Updated genesis file: {args.genesis_file}")
