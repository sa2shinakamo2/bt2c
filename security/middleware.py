from fastapi import Request, HTTPException
from fastapi.middleware.base import BaseHTTPMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from datetime import datetime, timedelta
import re
from typing import Optional, Dict, Any
import structlog

logger = structlog.get_logger()

class SecurityMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app,
        secret_key: str,
        allowed_hosts: list = None,
        enable_xss_protection: bool = True,
        enable_hsts: bool = True
    ):
        super().__init__(app)
        self.secret_key = secret_key
        self.allowed_hosts = allowed_hosts or ["localhost", "127.0.0.1"]
        self.enable_xss_protection = enable_xss_protection
        self.enable_hsts = enable_hsts
        self.security_headers = {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "Content-Security-Policy": "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; style-src 'self' 'unsafe-inline';",
            "X-XSS-Protection": "1; mode=block" if enable_xss_protection else "0",
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains" if enable_hsts else "",
        }

    async def dispatch(self, request: Request, call_next):
        # Host validation
        host = request.headers.get("host", "").split(":")[0]
        if host not in self.allowed_hosts:
            logger.warning("invalid_host_access_attempt", host=host)
            raise HTTPException(status_code=400, detail="Invalid host")

        # Input validation for query parameters and body
        await self.validate_request_input(request)

        # Add security headers
        response = await call_next(request)
        for header_name, header_value in self.security_headers.items():
            if header_value:  # Only set headers with non-empty values
                response.headers[header_name] = header_value

        return response

    async def validate_request_input(self, request: Request):
        """Validate request input for common attack patterns."""
        # Check query parameters
        for param, value in request.query_params.items():
            if self._contains_suspicious_patterns(value):
                logger.warning("suspicious_query_parameter", param=param)
                raise HTTPException(status_code=400, detail="Invalid input detected")

        # Check request body if it's a JSON request
        if request.headers.get("content-type") == "application/json":
            try:
                body = await request.json()
                if isinstance(body, dict):
                    self._validate_dict_values(body)
            except Exception as e:
                logger.error("request_body_validation_error", error=str(e))
                raise HTTPException(status_code=400, detail="Invalid JSON body")

    def _contains_suspicious_patterns(self, value: str) -> bool:
        """Check for common malicious patterns."""
        suspicious_patterns = [
            r"<script.*?>",  # XSS attempts
            r"../",          # Path traversal
            r";\s*drop\s+table", # SQL injection
            r"(?:union|select|insert|update|delete)\s+(?:from|into)?", # SQL keywords
        ]
        return any(re.search(pattern, str(value), re.IGNORECASE) 
                  for pattern in suspicious_patterns)

    def _validate_dict_values(self, data: Dict[str, Any], depth: int = 0):
        """Recursively validate dictionary values."""
        max_depth = 5  # Prevent deep recursion
        if depth > max_depth:
            raise HTTPException(status_code=400, detail="Input too deeply nested")

        for key, value in data.items():
            if isinstance(value, str):
                if self._contains_suspicious_patterns(value):
                    raise HTTPException(
                        status_code=400, 
                        detail=f"Suspicious pattern detected in field: {key}"
                    )
            elif isinstance(value, dict):
                self._validate_dict_values(value, depth + 1)
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, dict):
                        self._validate_dict_values(item, depth + 1)
                    elif isinstance(item, str):
                        if self._contains_suspicious_patterns(item):
                            raise HTTPException(
                                status_code=400, 
                                detail=f"Suspicious pattern detected in array field: {key}"
                            )

class JWTAuth:
    def __init__(self, secret_key: str, token_expire_minutes: int = 30):
        self.secret_key = secret_key
        self.token_expire_minutes = token_expire_minutes
        self.algorithm = "HS256"
        self.bearer = HTTPBearer()

    def create_token(self, data: dict) -> str:
        """Create a new JWT token."""
        expire = datetime.utcnow() + timedelta(minutes=self.token_expire_minutes)
        to_encode = data.copy()
        to_encode.update({"exp": expire})
        return jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)

    async def validate_token(
        self, credentials: HTTPAuthorizationCredentials
    ) -> Optional[dict]:
        """Validate JWT token."""
        try:
            payload = jwt.decode(
                credentials.credentials, 
                self.secret_key, 
                algorithms=[self.algorithm]
            )
            return payload
        except JWTError:
            raise HTTPException(
                status_code=401,
                detail="Invalid authentication credentials"
            )
