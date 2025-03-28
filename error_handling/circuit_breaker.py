"""Circuit breaker pattern implementation for error handling."""
import time
import threading
import functools
import structlog

logger = structlog.get_logger()

class CircuitBreaker:
    """
    Implements the Circuit Breaker pattern to prevent cascading failures.
    
    When a service is experiencing issues, calling it repeatedly can worsen the problem.
    The Circuit Breaker stops calls to failing services when they exceed a threshold,
    allowing them time to recover.
    
    Circuit states:
    - CLOSED: Normal operation, calls pass through to the service
    - OPEN: Service calls are blocked entirely to allow recovery
    - HALF-OPEN: Limited testing of service to check if it's recovered
    """
    
    STATE_CLOSED = 'closed'
    STATE_OPEN = 'open'
    STATE_HALF_OPEN = 'half-open'
    
    class CircuitBreakerError(Exception):
        """Exception raised when a circuit is open."""
        pass
    
    def __init__(self, failure_threshold=5, recovery_timeout=60, 
                 half_open_success_threshold=1):
        """
        Initialize a new Circuit Breaker.
        
        Args:
            failure_threshold: Number of failures before opening the circuit
            recovery_timeout: Time in seconds to wait before attempting recovery
            half_open_success_threshold: Number of successful calls needed to close circuit
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_success_threshold = half_open_success_threshold
        
        # Internal state
        self.state = self.STATE_CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = 0
        self._lock = threading.RLock()
    
    def __call__(self, func):
        """Use as a decorator on functions that might fail."""
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            return self.call(func, *args, **kwargs)
        return wrapper
    
    def call(self, func, *args, **kwargs):
        """
        Call the protected function with circuit breaker protection.
        
        Args:
            func: The function to call
            *args, **kwargs: Arguments to pass to the function
            
        Returns:
            The result of the function call
            
        Raises:
            CircuitBreakerError: If the circuit is open
            Exception: Any exception raised by the function
        """
        with self._lock:
            if self.state == self.STATE_OPEN:
                # Check if it's time to try recovery
                if time.time() - self.last_failure_time >= self.recovery_timeout:
                    logger.info("circuit_breaker_half_open", 
                                func=func.__name__, 
                                recovery_timeout=self.recovery_timeout)
                    self.state = self.STATE_HALF_OPEN
                    self.success_count = 0
                else:
                    # Circuit is still open, don't call the function
                    logger.warning("circuit_breaker_open", 
                                  func=func.__name__,
                                  last_failure=self.last_failure_time,
                                  seconds_remaining=self.recovery_timeout - (time.time() - self.last_failure_time))
                    raise self.CircuitBreakerError(
                        f"Circuit is open for {func.__name__}, too many failures."
                    )
        
        try:
            # Call the function
            result = func(*args, **kwargs)
            
            # Record success
            with self._lock:
                if self.state == self.STATE_HALF_OPEN:
                    self.success_count += 1
                    if self.success_count >= self.half_open_success_threshold:
                        # Service has recovered, close the circuit
                        logger.info("circuit_breaker_closed", 
                                   func=func.__name__,
                                   success_count=self.success_count)
                        self.state = self.STATE_CLOSED
                        self.failure_count = 0
                elif self.state == self.STATE_CLOSED:
                    # Reset failure count on success
                    self.failure_count = 0
            
            return result
            
        except Exception as e:
            # Record failure
            with self._lock:
                self.failure_count += 1
                self.last_failure_time = time.time()
                
                if self.state == self.STATE_CLOSED and self.failure_count >= self.failure_threshold:
                    # Too many failures, open the circuit
                    logger.warning("circuit_breaker_tripped", 
                                  func=func.__name__, 
                                  failure_count=self.failure_count,
                                  exception=str(e))
                    self.state = self.STATE_OPEN
                elif self.state == self.STATE_HALF_OPEN:
                    # Failed during recovery attempt, reopen the circuit
                    logger.warning("circuit_breaker_recovery_failed",
                                  func=func.__name__,
                                  exception=str(e))
                    self.state = self.STATE_OPEN
            
            # Re-raise the original exception
            raise
    
    def reset(self):
        """Reset the circuit breaker to closed state."""
        with self._lock:
            self.state = self.STATE_CLOSED
            self.failure_count = 0
            self.success_count = 0
            self.last_failure_time = 0
            logger.info("circuit_breaker_reset")
            
    def force_open(self):
        """Manually force the circuit into open state."""
        with self._lock:
            self.state = self.STATE_OPEN
            self.last_failure_time = time.time()
            logger.warning("circuit_breaker_forced_open")
    
    def get_state(self):
        """Get the current state of the circuit breaker."""
        with self._lock:
            return {
                'state': self.state,
                'failure_count': self.failure_count,
                'success_count': self.success_count,
                'last_failure_time': self.last_failure_time
            }


# Example usage
if __name__ == "__main__":
    # Create a circuit breaker with 3 failure threshold
    breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=5)
    
    # Create a function that will sometimes fail
    @breaker
    def unreliable_service(fail=False):
        if fail:
            raise ValueError("Service failed")
        return "Service success"
    
    # Test the circuit breaker
    try:
        # Cause 3 failures to open the circuit
        for _ in range(3):
            try:
                print(unreliable_service(fail=True))
            except ValueError as e:
                print(f"Expected error: {e}")
        
        # Now the circuit should be open
        try:
            print(unreliable_service())
        except CircuitBreaker.CircuitBreakerError as e:
            print(f"Circuit breaker error: {e}")
        
        # Wait for recovery timeout
        print("Waiting for recovery timeout...")
        time.sleep(6)
        
        # Circuit should be half-open, try with success
        print(unreliable_service())
        
        # One more success should close the circuit
        print(unreliable_service())
        
        # Circuit should be closed now
        print("Circuit should be closed now.")
        print(unreliable_service())
        
    except Exception as e:
        print(f"Unexpected error: {e}")
