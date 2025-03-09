from enum import Enum
import time
import asyncio
from typing import Any, Callable, Optional, Dict
import structlog
from functools import wraps

logger = structlog.get_logger()

class CircuitState(Enum):
    CLOSED = "closed"      # Normal operation
    OPEN = "open"         # No operations allowed
    HALF_OPEN = "half_open"  # Testing if service is back

class CircuitBreaker:
    """Circuit breaker pattern implementation."""
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        half_open_timeout: int = 30,
        error_types: tuple = (Exception,)
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_timeout = half_open_timeout
        self.error_types = error_types
        
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time = 0
        self.last_test_time = 0

    def can_execute(self) -> bool:
        """Check if operation can be executed."""
        if self.state == CircuitState.CLOSED:
            return True

        if self.state == CircuitState.OPEN:
            if time.time() - self.last_failure_time >= self.recovery_timeout:
                self.state = CircuitState.HALF_OPEN
                self.last_test_time = time.time()
                return True
            return False

        if self.state == CircuitState.HALF_OPEN:
            if time.time() - self.last_test_time >= self.half_open_timeout:
                return True
            return False

        return False

    def record_success(self):
        """Record a successful operation."""
        self.failure_count = 0
        self.state = CircuitState.CLOSED
        logger.info("circuit_breaker_success", state=self.state.value)

    def record_failure(self):
        """Record a failed operation."""
        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.state == CircuitState.HALF_OPEN or \
           self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
            logger.warning(
                "circuit_breaker_opened",
                failures=self.failure_count,
                last_failure=self.last_failure_time
            )

class CircuitBreakerRegistry:
    """Registry for managing multiple circuit breakers."""
    
    _instance = None
    _breakers: Dict[str, CircuitBreaker] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def get_breaker(cls, name: str) -> CircuitBreaker:
        """Get or create a circuit breaker."""
        if name not in cls._breakers:
            cls._breakers[name] = CircuitBreaker()
        return cls._breakers[name]

def with_circuit_breaker(
    breaker_name: str,
    fallback_function: Optional[Callable] = None
):
    """Decorator to apply circuit breaker pattern."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            breaker = CircuitBreakerRegistry.get_breaker(breaker_name)
            
            if not breaker.can_execute():
                logger.warning(
                    "circuit_breaker_blocked",
                    breaker=breaker_name,
                    state=breaker.state.value
                )
                if fallback_function:
                    return await fallback_function(*args, **kwargs)
                raise RuntimeError(f"Circuit breaker {breaker_name} is {breaker.state.value}")

            try:
                result = await func(*args, **kwargs)
                breaker.record_success()
                return result
            except Exception as e:
                breaker.record_failure()
                logger.error(
                    "circuit_breaker_failure",
                    breaker=breaker_name,
                    error=str(e)
                )
                if fallback_function:
                    return await fallback_function(*args, **kwargs)
                raise
        return wrapper
    return decorator

class RetryWithBackoff:
    """Implements exponential backoff retry logic."""
    
    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 10.0,
        exponential_base: float = 2.0
    ):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base

    async def execute(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with retry logic."""
        last_exception = None
        
        for attempt in range(self.max_retries):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                if attempt < self.max_retries - 1:
                    delay = min(
                        self.base_delay * (self.exponential_base ** attempt),
                        self.max_delay
                    )
                    logger.warning(
                        "retry_attempt",
                        attempt=attempt + 1,
                        delay=delay,
                        error=str(e)
                    )
                    await asyncio.sleep(delay)

        logger.error(
            "retry_exhausted",
            max_retries=self.max_retries,
            error=str(last_exception)
        )
        raise last_exception

def with_retry(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 10.0
):
    """Decorator to apply retry logic."""
    retry_handler = RetryWithBackoff(
        max_retries=max_retries,
        base_delay=base_delay,
        max_delay=max_delay
    )
    
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            return await retry_handler.execute(func, *args, **kwargs)
        return wrapper
    return decorator
