"""Security middleware for BT2C blockchain API and P2P communication."""
import time
import re
import json
import hashlib
import structlog
from typing import Dict, Any, Optional, List, Union

logger = structlog.get_logger()

class SecurityMiddleware:
    """
    Security middleware for validating and sanitizing inputs and communications.
    Implements various security checks to protect against common attacks.
    """
    
    def __init__(self):
        """Initialize the security middleware."""
        # Common patterns for detecting malicious inputs
        self.sql_injection_patterns = [
            r"(?i)SELECT\s+.*\s+FROM",
            r"(?i)INSERT\s+INTO",
            r"(?i)UPDATE\s+.*\s+SET",
            r"(?i)DELETE\s+FROM",
            r"(?i)DROP\s+TABLE",
            r"(?i)UNION\s+SELECT",
            r"(?i)--",
            r"(?i);.*SELECT",
        ]
        
        self.command_injection_patterns = [
            r"(?i)(?:;|\||\|\||&|&&|\n|\r)",
            r"(?i)(?:`.*?`)",
            r"(?i)(?:\$\(.*?\))",
            r"(?i)(?:\${.*?})",
            r"(?i)(?:>\s*[a-zA-Z0-9]+)",
            r"(?i)(?:<\s*[a-zA-Z0-9]+)"
        ]
        
        # Allowed P2P message types for validation
        self.allowed_message_types = [
            "block", "transaction", "peer", "ping", "pong",
            "get_blocks", "get_transactions", "sync"
        ]
        
        # Logging setup
        self.enable_extended_logging = True
    
    def sanitize_input(self, input_string: str) -> str:
        """
        Sanitize input string to prevent injection attacks.
        
        Args:
            input_string: The input string to sanitize
        
        Returns:
            Sanitized string
        """
        if not isinstance(input_string, str):
            return ""
            
        # Escape special characters
        sanitized = input_string.replace("&", "&amp;")
        sanitized = sanitized.replace("<", "&lt;")
        sanitized = sanitized.replace(">", "&gt;")
        sanitized = sanitized.replace("\"", "&quot;")
        sanitized = sanitized.replace("'", "&#x27;")
        
        return sanitized
    
    def validate_input(self, input_string: str) -> bool:
        """
        Validate input string against known attack patterns.
        
        Args:
            input_string: The input string to validate
        
        Returns:
            True if input is safe, False otherwise
        """
        if not isinstance(input_string, str):
            return False
            
        # Check for SQL injection patterns
        for pattern in self.sql_injection_patterns:
            if re.search(pattern, input_string):
                logger.warning("potential_sql_injection", pattern=pattern, input=input_string[:50])
                return False
                
        # Check for command injection patterns
        for pattern in self.command_injection_patterns:
            if re.search(pattern, input_string):
                logger.warning("potential_command_injection", pattern=pattern, input=input_string[:50])
                return False
                
        return True
    
    def validate_json(self, json_string: str) -> Optional[Dict[str, Any]]:
        """
        Validate and parse JSON input.
        
        Args:
            json_string: JSON string to validate
        
        Returns:
            Parsed JSON object if valid, None otherwise
        """
        try:
            # Attempt to parse JSON
            data = json.loads(json_string)
            
            # Ensure result is a dict
            if not isinstance(data, dict):
                logger.warning("invalid_json_format", error="Result is not a dictionary")
                return None
                
            return data
            
        except json.JSONDecodeError as e:
            logger.warning("invalid_json", error=str(e))
            return None
        except Exception as e:
            logger.error("json_validation_error", error=str(e))
            return None
    
    def validate_p2p_message(self, message: Any) -> bool:
        """
        Validate P2P message structure and content.
        
        Args:
            message: The message object to validate
        
        Returns:
            True if message is valid, False otherwise
        """
        try:
            # Basic type checking
            if not isinstance(message, dict):
                logger.warning("invalid_p2p_message", error="Message is not a dictionary")
                return False
                
            # Check required fields
            if "type" not in message:
                logger.warning("invalid_p2p_message", error="Missing 'type' field")
                return False
                
            if "data" not in message:
                logger.warning("invalid_p2p_message", error="Missing 'data' field")
                return False
                
            # Validate message type
            if message["type"] not in self.allowed_message_types:
                logger.warning("invalid_p2p_message_type", type=message["type"])
                return False
                
            # Validate timestamp if present
            if "timestamp" in message:
                current_time = int(time.time())
                msg_time = message["timestamp"]
                
                # Check if timestamp is an integer
                if not isinstance(msg_time, int):
                    logger.warning("invalid_p2p_timestamp", error="Timestamp is not an integer")
                    return False
                    
                # Check if timestamp is in the future
                if msg_time > current_time + 300:  # Allow 5 min clock skew
                    logger.warning("future_p2p_timestamp", 
                                  msg_time=msg_time, 
                                  current_time=current_time,
                                  diff=msg_time - current_time)
                    return False
                    
                # Check if timestamp is too old
                if msg_time < current_time - 86400:  # Older than 1 day
                    logger.warning("old_p2p_timestamp", 
                                  msg_time=msg_time, 
                                  current_time=current_time,
                                  diff=current_time - msg_time)
                    return False
            
            # Additional message type-specific validation
            if message["type"] == "transaction":
                return self._validate_transaction_message(message["data"])
            elif message["type"] == "block":
                return self._validate_block_message(message["data"])
            
            return True
            
        except Exception as e:
            logger.error("p2p_message_validation_error", error=str(e))
            return False
    
    def _validate_transaction_message(self, data: Dict[str, Any]) -> bool:
        """
        Validate transaction message data.
        
        Args:
            data: Transaction data to validate
        
        Returns:
            True if valid, False otherwise
        """
        required_fields = ["hash", "sender", "recipient", "amount", "timestamp"]
        for field in required_fields:
            if field not in data:
                logger.warning("invalid_transaction_message", error=f"Missing field: {field}")
                return False
        
        # Validate transaction hash format
        if not re.match(r"^[a-fA-F0-9]{64}$", data["hash"]):
            logger.warning("invalid_transaction_hash", hash=data["hash"])
            return False
            
        return True
    
    def _validate_block_message(self, data: Dict[str, Any]) -> bool:
        """
        Validate block message data.
        
        Args:
            data: Block data to validate
        
        Returns:
            True if valid, False otherwise
        """
        required_fields = ["hash", "index", "previous_hash", "timestamp"]
        for field in required_fields:
            if field not in data:
                logger.warning("invalid_block_message", error=f"Missing field: {field}")
                return False
        
        # Validate block hash format
        if not re.match(r"^[a-fA-F0-9]{64}$", data["hash"]):
            logger.warning("invalid_block_hash", hash=data["hash"])
            return False
            
        # Validate previous hash format
        if not re.match(r"^[a-fA-F0-9]{64}$", data["previous_hash"]):
            logger.warning("invalid_previous_hash", previous_hash=data["previous_hash"])
            return False
            
        return True
    
    def validate_url(self, url: str) -> bool:
        """
        Validate URL for security.
        
        Args:
            url: URL string to validate
        
        Returns:
            True if URL is safe, False otherwise
        """
        try:
            import urllib.parse
            parsed = urllib.parse.urlparse(url)
            
            # Check scheme
            if parsed.scheme not in ["http", "https"]:
                logger.warning("invalid_url_scheme", scheme=parsed.scheme)
                return False
                
            # Check for localhost/internal addresses
            if parsed.netloc in ["localhost", "127.0.0.1", "0.0.0.0"]:
                logger.warning("blocked_internal_url", netloc=parsed.netloc)
                return False
                
            # Check for internal domains
            if parsed.netloc.endswith((".local", ".internal", ".localhost")):
                logger.warning("blocked_internal_domain", netloc=parsed.netloc)
                return False
                
            # Prevent IPv4 address access
            ipv4_pattern = r"^(?:[0-9]{1,3}\.){3}[0-9]{1,3}$"
            if re.match(ipv4_pattern, parsed.netloc):
                segments = parsed.netloc.split(".")
                # Check for private IP ranges
                if segments[0] == "10" or \
                   (segments[0] == "172" and 16 <= int(segments[1]) <= 31) or \
                   (segments[0] == "192" and segments[1] == "168"):
                    logger.warning("blocked_private_ip", netloc=parsed.netloc)
                    return False
            
            return True
            
        except Exception as e:
            logger.error("url_validation_error", error=str(e), url=url)
            return False
    
    def generate_csrf_token(self, session_id: str) -> str:
        """
        Generate a CSRF token for the given session.
        
        Args:
            session_id: Session identifier
        
        Returns:
            CSRF token string
        """
        timestamp = int(time.time())
        data = f"{session_id}:{timestamp}"
        
        # Use a server-side secret key
        secret_key = b"bf2c_secure_key_change_in_production"
        
        # Create HMAC-based token
        token_hash = hashlib.hmac_sha256(secret_key, data.encode()).hexdigest()
        return f"{timestamp}:{token_hash}"
    
    def validate_csrf_token(self, token: str, session_id: str, max_age: int = 3600) -> bool:
        """
        Validate a CSRF token.
        
        Args:
            token: The token to validate
            session_id: Session identifier
            max_age: Maximum token age in seconds
            
        Returns:
            True if token is valid, False otherwise
        """
        try:
            # Parse token
            timestamp_str, token_hash = token.split(":", 1)
            timestamp = int(timestamp_str)
            
            # Check token age
            current_time = int(time.time())
            if current_time - timestamp > max_age:
                logger.warning("expired_csrf_token", 
                              age=current_time - timestamp,
                              max_age=max_age)
                return False
                
            # Verify token hash
            secret_key = b"bf2c_secure_key_change_in_production"
            data = f"{session_id}:{timestamp}"
            expected_hash = hashlib.hmac_sha256(secret_key, data.encode()).hexdigest()
            
            # Constant-time comparison to prevent timing attacks
            return self._constant_time_compare(token_hash, expected_hash)
            
        except Exception as e:
            logger.error("csrf_token_validation_error", error=str(e))
            return False
    
    def _constant_time_compare(self, a: str, b: str) -> bool:
        """
        Compare two strings in constant time to prevent timing attacks.
        
        Args:
            a: First string
            b: Second string
            
        Returns:
            True if strings are equal, False otherwise
        """
        if len(a) != len(b):
            return False
            
        result = 0
        for x, y in zip(a, b):
            result |= ord(x) ^ ord(y)
        return result == 0
            
    def log_security_event(self, event_type: str, details: Dict[str, Any]) -> None:
        """
        Log a security event.
        
        Args:
            event_type: Type of security event
            details: Additional details about the event
        """
        if not self.enable_extended_logging:
            return
            
        log = logger.bind(
            security_event=event_type,
            timestamp=int(time.time()),
            **details
        )
        
        if event_type.startswith("error"):
            log.error("security_event")
        elif event_type.startswith("warning"):
            log.warning("security_event")
        else:
            log.info("security_event")


# Helper function for HMAC SHA-256
def hashlib_hmac_sha256(key: bytes, msg: bytes) -> str:
    """
    Calculate HMAC SHA-256 hash.
    
    Args:
        key: Secret key
        msg: Message to hash
        
    Returns:
        Hexadecimal hash string
    """
    import hmac
    return hmac.new(key, msg, hashlib.sha256).hexdigest()


# Attach hmac_sha256 to hashlib for convenience
if not hasattr(hashlib, 'hmac_sha256'):
    hashlib.hmac_sha256 = hashlib_hmac_sha256
