import os
from datetime import datetime, timedelta
from typing import Tuple, Dict, Optional
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPrivateKey, RSAPublicKey
import structlog
import time
from collections import defaultdict, deque
import ipaddress
import json

logger = structlog.get_logger()

class RateLimiter:
    """Rate limiter using token bucket algorithm"""
    def __init__(self, rate: float, burst: int):
        self.rate = rate  # tokens per second
        self.burst = burst  # maximum bucket size
        self.tokens = burst  # current tokens
        self.last_update = time.time()
        
    def allow(self) -> bool:
        now = time.time()
        # Add tokens based on time passed
        self.tokens = min(
            self.burst,
            self.tokens + (now - self.last_update) * self.rate
        )
        self.last_update = now
        
        if self.tokens >= 1:
            self.tokens -= 1
            return True
        return False

class DDoSProtection:
    """DDoS protection using connection tracking and IP reputation"""
    def __init__(self):
        self.connections = defaultdict(int)  # IP -> connection count
        self.blacklist = set()  # Blacklisted IPs
        self.suspicious = defaultdict(int)  # IP -> suspicious activity count
        self.request_history = defaultdict(lambda: deque(maxlen=1000))  # IP -> recent requests
        
    def is_allowed(self, ip: str) -> bool:
        try:
            # Validate IP
            ipaddress.ip_address(ip)
        except ValueError:
            return False
            
        # Check blacklist
        if ip in self.blacklist:
            return False
            
        # Check connection limit
        if self.connections[ip] > 100:  # Max 100 concurrent connections
            self.suspicious[ip] += 1
            return False
            
        # Check request rate
        requests = self.request_history[ip]
        now = time.time()
        recent = sum(1 for t in requests if now - t < 60)  # Requests in last minute
        
        if recent > 1000:  # Max 1000 requests per minute
            self.suspicious[ip] += 1
            if self.suspicious[ip] > 3:
                self.blacklist.add(ip)
            return False
            
        requests.append(now)
        return True
        
    def add_connection(self, ip: str):
        self.connections[ip] += 1
        
    def remove_connection(self, ip: str):
        self.connections[ip] = max(0, self.connections[ip] - 1)

class SecurityManager:
    def __init__(self, cert_path: str = "certs"):
        self.cert_path = cert_path
        os.makedirs(cert_path, exist_ok=True)
        
        # Initialize security components
        self.rate_limiters = defaultdict(lambda: RateLimiter(10, 50))  # 10 req/s, burst of 50
        self.ddos_protection = DDoSProtection()
        
        # Load blacklist if exists
        self.blacklist_file = os.path.join(cert_path, "blacklist.json")
        self.load_blacklist()
        
    def load_blacklist(self):
        """Load IP blacklist from file"""
        if os.path.exists(self.blacklist_file):
            try:
                with open(self.blacklist_file) as f:
                    data = json.load(f)
                    self.ddos_protection.blacklist = set(data.get("blacklist", []))
            except Exception as e:
                logger.error("blacklist_load_error", error=str(e))
                
    def save_blacklist(self):
        """Save IP blacklist to file"""
        try:
            with open(self.blacklist_file, "w") as f:
                json.dump({
                    "blacklist": list(self.ddos_protection.blacklist),
                    "updated_at": datetime.utcnow().isoformat()
                }, f, indent=2)
        except Exception as e:
            logger.error("blacklist_save_error", error=str(e))
            
    def check_request(self, ip: str, endpoint: str) -> bool:
        """Check if request should be allowed"""
        # First check DDoS protection
        if not self.ddos_protection.is_allowed(ip):
            logger.warning("request_blocked_ddos", ip=ip)
            return False
            
        # Then check rate limit for endpoint
        if not self.rate_limiters[endpoint].allow():
            logger.warning("request_blocked_rate_limit", ip=ip, endpoint=endpoint)
            return False
            
        return True
        
    def add_connection(self, ip: str):
        """Track new connection"""
        self.ddos_protection.add_connection(ip)
        
    def remove_connection(self, ip: str):
        """Remove tracked connection"""
        self.ddos_protection.remove_connection(ip)
        
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
