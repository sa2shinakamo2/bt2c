import os
from datetime import datetime, timedelta
from typing import Tuple
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPrivateKey, RSAPublicKey
import structlog

logger = structlog.get_logger()

class SecurityManager:
    def __init__(self, cert_path: str = "certs"):
        self.cert_path = cert_path
        os.makedirs(cert_path, exist_ok=True)
        
    def generate_node_certificates(self, node_id: str) -> Tuple[str, str]:
        """Generate SSL certificates for a node."""
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048
        )
        
        # Generate public key
        public_key = private_key.public_key()
        
        # Generate self-signed certificate
        subject = issuer = x509.Name([
            x509.NameAttribute(NameOID.COMMON_NAME, f"BT2C-Node-{node_id}")
        ])
        
        cert = x509.CertificateBuilder().subject_name(
            subject
        ).issuer_name(
            issuer
        ).public_key(
            public_key
        ).serial_number(
            x509.random_serial_number()
        ).not_valid_before(
            datetime.utcnow()
        ).not_valid_after(
            datetime.utcnow() + timedelta(days=365)
        ).add_extension(
            x509.BasicConstraints(ca=True, path_length=None),
            critical=True
        ).sign(private_key, hashes.SHA256())
        
        # Save private key
        private_key_path = os.path.join(self.cert_path, f"{node_id}_private.pem")
        with open(private_key_path, "wb") as f:
            f.write(private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            ))
            
        # Save certificate
        cert_path = os.path.join(self.cert_path, f"{node_id}_cert.pem")
        with open(cert_path, "wb") as f:
            f.write(cert.public_bytes(serialization.Encoding.PEM))
            
        logger.info("generated_node_certificates",
                   node_id=node_id,
                   private_key_path=private_key_path,
                   cert_path=cert_path)
            
        return cert_path, private_key_path
    
    def load_node_certificates(self, node_id: str) -> Tuple[str, str]:
        """Load existing node certificates or generate new ones."""
        cert_path = os.path.join(self.cert_path, f"{node_id}_cert.pem")
        private_key_path = os.path.join(self.cert_path, f"{node_id}_private.pem")
        
        if not (os.path.exists(cert_path) and os.path.exists(private_key_path)):
            return self.generate_node_certificates(node_id)
            
        return cert_path, private_key_path
