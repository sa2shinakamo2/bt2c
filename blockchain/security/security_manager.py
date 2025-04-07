"""
Security Manager for BT2C blockchain.
"""
import os
import time
import hashlib
import logging
import ipaddress
from typing import Dict, List, Optional, Set, Tuple, Any
from .certificates import CertificateManager
from ..config import NetworkType, BT2CConfig

logger = logging.getLogger(__name__)

class SecurityManager:
    """
    Manages security features for the BT2C blockchain.
    This includes rate limiting, IP banning, and certificate management.
    """
    
    def __init__(self, node_id: str, network_type: NetworkType = NetworkType.TESTNET):
        """
        Initialize the security manager.
        
        Args:
            node_id: Unique identifier for this node
            network_type: Network type (mainnet/testnet)
        """
        self.node_id = node_id
        self.network_type = network_type
        self.config = BT2CConfig.get_config(network_type)
        
        # Initialize certificate manager
        self.cert_manager = CertificateManager(node_id)
        
        # Rate limiting
        self.request_counts: Dict[str, List[float]] = {}  # IP -> list of timestamps
        self.rate_limit = 100  # Requests per minute (from whitepaper)
        self.rate_window = 60  # 1 minute window
        
        # IP banning
        self.banned_ips: Dict[str, float] = {}  # IP -> ban expiry time
        self.ban_duration = 3600  # 1 hour ban by default
        self.max_failed_attempts = 5  # Max failed attempts before ban
        self.failed_attempts: Dict[str, int] = {}  # IP -> count of failed attempts
        
        # Allowed IPs (whitelist)
        self.allowed_ips: Set[str] = set()
        
        # Load SSL certificates
        self.cert_path, self.key_path = self.cert_manager.load_or_generate_certificates()
        
    def is_rate_limited(self, ip: str) -> bool:
        """
        Check if an IP is rate limited.
        
        Args:
            ip: IP address to check
            
        Returns:
            True if rate limited, False otherwise
        """
        now = time.time()
        
        # Initialize if not exists
        if ip not in self.request_counts:
            self.request_counts[ip] = []
            
        # Add current request
        self.request_counts[ip].append(now)
        
        # Remove old requests
        self.request_counts[ip] = [t for t in self.request_counts[ip] if now - t <= self.rate_window]
        
        # Check if over limit
        return len(self.request_counts[ip]) > self.rate_limit
        
    def is_banned(self, ip: str) -> bool:
        """
        Check if an IP is banned.
        
        Args:
            ip: IP address to check
            
        Returns:
            True if banned, False otherwise
        """
        # Whitelist check
        if ip in self.allowed_ips:
            return False
            
        # Check if banned
        if ip in self.banned_ips:
            expiry = self.banned_ips[ip]
            now = time.time()
            
            # Remove expired ban
            if now > expiry:
                del self.banned_ips[ip]
                return False
                
            return True
            
        return False
        
    def ban_ip(self, ip: str, duration: Optional[int] = None) -> None:
        """
        Ban an IP address.
        
        Args:
            ip: IP address to ban
            duration: Ban duration in seconds (None for default)
        """
        # Don't ban whitelisted IPs
        if ip in self.allowed_ips:
            return
            
        ban_time = duration or self.ban_duration
        self.banned_ips[ip] = time.time() + ban_time
        logger.warning(f"Banned IP {ip} for {ban_time} seconds")
        
    def record_failed_attempt(self, ip: str) -> bool:
        """
        Record a failed authentication attempt.
        
        Args:
            ip: IP address to record
            
        Returns:
            True if IP is now banned, False otherwise
        """
        # Initialize if not exists
        if ip not in self.failed_attempts:
            self.failed_attempts[ip] = 0
            
        # Increment count
        self.failed_attempts[ip] += 1
        
        # Ban if too many failures
        if self.failed_attempts[ip] >= self.max_failed_attempts:
            self.ban_ip(ip)
            self.failed_attempts[ip] = 0
            return True
            
        return False
        
    def reset_failed_attempts(self, ip: str) -> None:
        """
        Reset failed attempts for an IP.
        
        Args:
            ip: IP address to reset
        """
        if ip in self.failed_attempts:
            self.failed_attempts[ip] = 0
            
    def add_to_whitelist(self, ip: str) -> None:
        """
        Add an IP to the whitelist.
        
        Args:
            ip: IP address to whitelist
        """
        try:
            # Validate IP
            ipaddress.ip_address(ip)
            self.allowed_ips.add(ip)
            
            # Remove from banned list if present
            if ip in self.banned_ips:
                del self.banned_ips[ip]
                
            logger.info(f"Added {ip} to whitelist")
            
        except ValueError:
            logger.error(f"Invalid IP address: {ip}")
            
    def remove_from_whitelist(self, ip: str) -> None:
        """
        Remove an IP from the whitelist.
        
        Args:
            ip: IP address to remove
        """
        if ip in self.allowed_ips:
            self.allowed_ips.remove(ip)
            logger.info(f"Removed {ip} from whitelist")
            
    def verify_peer_certificate(self, cert_data: bytes) -> bool:
        """
        Verify a peer's certificate.
        
        Args:
            cert_data: Certificate data to verify
            
        Returns:
            True if valid, False otherwise
        """
        return self.cert_manager.verify_peer_certificate(cert_data)
        
    def hash_password(self, password: str, salt: Optional[bytes] = None) -> Tuple[bytes, bytes]:
        """
        Hash a password using PBKDF2.
        
        Args:
            password: Password to hash
            salt: Optional salt (generated if None)
            
        Returns:
            Tuple of (hash, salt)
        """
        if salt is None:
            salt = os.urandom(32)  # 32 bytes of random salt
            
        # Use PBKDF2 with 100,000 iterations (BIP39 compatible)
        password_hash = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt,
            100000
        )
        
        return password_hash, salt
        
    def verify_password(self, password: str, stored_hash: bytes, salt: bytes) -> bool:
        """
        Verify a password against a stored hash.
        
        Args:
            password: Password to verify
            stored_hash: Stored password hash
            salt: Salt used for hashing
            
        Returns:
            True if password matches, False otherwise
        """
        password_hash, _ = self.hash_password(password, salt)
        return password_hash == stored_hash
