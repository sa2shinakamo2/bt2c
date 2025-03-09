from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.asymmetric import padding
import datetime
import os
import structlog

logger = structlog.get_logger()

class CertificateManager:
    def __init__(self, node_id: str):
        self.node_id = node_id
        self.cert_dir = os.path.expanduser(f"~/.bt2c/certs/{node_id}")
        os.makedirs(self.cert_dir, exist_ok=True)
        
    def generate_node_certificates(self) -> tuple[str, str]:
        """Generate SSL certificates for node communication."""
        # Generate key
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048
        )
        
        # Generate certificate
        subject = issuer = x509.Name([
            x509.NameAttribute(NameOID.COMMON_NAME, f'BT2C Node {self.node_id}'),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, 'BT2C Network'),
        ])
        
        cert = x509.CertificateBuilder().subject_name(
            subject
        ).issuer_name(
            issuer
        ).public_key(
            private_key.public_key()
        ).serial_number(
            x509.random_serial_number()
        ).not_valid_before(
            datetime.datetime.utcnow()
        ).not_valid_after(
            datetime.datetime.utcnow() + datetime.timedelta(days=365)
        ).add_extension(
            x509.BasicConstraints(ca=True, path_length=None), critical=True,
        ).sign(private_key, hashes.SHA256())
        
        # Save certificates
        cert_path = os.path.join(self.cert_dir, "node.crt")
        key_path = os.path.join(self.cert_dir, "node.key")
        
        with open(cert_path, "wb") as f:
            f.write(cert.public_bytes(serialization.Encoding.PEM))
            
        with open(key_path, "wb") as f:
            f.write(private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            ))
            
        logger.info("certificates_generated",
                   node_id=self.node_id,
                   cert_path=cert_path,
                   key_path=key_path)
                   
        return cert_path, key_path
        
    def load_or_generate_certificates(self) -> tuple[str, str]:
        """Load existing certificates or generate new ones."""
        cert_path = os.path.join(self.cert_dir, "node.crt")
        key_path = os.path.join(self.cert_dir, "node.key")
        
        if os.path.exists(cert_path) and os.path.exists(key_path):
            logger.info("certificates_loaded",
                       node_id=self.node_id,
                       cert_path=cert_path,
                       key_path=key_path)
            return cert_path, key_path
            
        return self.generate_node_certificates()
        
    def verify_peer_certificate(self, cert_data: bytes) -> bool:
        """Verify a peer's certificate."""
        try:
            cert = x509.load_pem_x509_certificate(cert_data)
            
            # Verify certificate is not expired
            now = datetime.datetime.utcnow()
            if now < cert.not_valid_before or now > cert.not_valid_after:
                logger.warning("certificate_expired",
                             node_id=self.node_id)
                return False
                
            # Verify it's a BT2C certificate
            org_name = cert.subject.get_attributes_for_oid(NameOID.ORGANIZATION_NAME)
            if not org_name or org_name[0].value != 'BT2C Network':
                logger.warning("invalid_certificate_organization",
                             node_id=self.node_id)
                return False
                
            return True
            
        except Exception as e:
            logger.error("certificate_verification_error",
                        node_id=self.node_id,
                        error=str(e))
            return False
