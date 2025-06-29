"""
Circuit Breaker implementation for BT2C blockchain.

This module provides a circuit breaker pattern implementation to prevent
cascading failures in the system by temporarily disabling operations
that are failing repeatedly.
"""

import time
import threading
from enum import Enum


class CircuitState(Enum):
    """Enum representing the possible states of a circuit breaker."""
    CLOSED = 'closed'  # Normal operation, requests pass through
    OPEN = 'open'      # Circuit is open, requests fail fast
    HALF_OPEN = 'half_open'  # Testing if service is back to normal


class CircuitBreaker:
    """
    Circuit breaker implementation to prevent cascading failures.
    
    When a service experiences repeated failures, the circuit breaker
    opens to prevent further requests to the failing service, allowing
    it time to recover.
    """
    
    def __init__(self, failure_threshold=5, recovery_timeout=60, half_open_success_threshold=2):
        """
        Initialize a new circuit breaker.
        
        Args:
            failure_threshold (int): Number of consecutive failures before opening the circuit
            recovery_timeout (int): Time in seconds to wait before trying to close the circuit
            half_open_success_threshold (int): Number of successful calls needed to close the circuit
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_success_threshold = half_open_success_threshold
        
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = 0
        self._lock = threading.RLock()
    
    def execute(self, func, *args, **kwargs):
        """
        Execute the provided function with circuit breaker protection.
        
        Args:
            func: The function to execute
            *args: Arguments to pass to the function
            **kwargs: Keyword arguments to pass to the function
            
        Returns:
            The result of the function call
            
        Raises:
            Exception: If the circuit is open or the function call fails
        """
        with self._lock:
            if self.state == CircuitState.OPEN:
                if time.time() - self.last_failure_time >= self.recovery_timeout:
                    # Transition to half-open state
                    self.state = CircuitState.HALF_OPEN
                    self.success_count = 0
                else:
                    raise Exception("Circuit is open - service unavailable")
        
        try:
            result = func(*args, **kwargs)
            
            with self._lock:
                if self.state == CircuitState.HALF_OPEN:
                    self.success_count += 1
                    if self.success_count >= self.half_open_success_threshold:
                        # Transition back to closed state
                        self.state = CircuitState.CLOSED
                        self.failure_count = 0
                elif self.state == CircuitState.CLOSED:
                    # Reset failure count on successful execution
                    self.failure_count = 0
            
            return result
            
        except Exception as e:
            with self._lock:
                self.failure_count += 1
                self.last_failure_time = time.time()
                
                if self.state == CircuitState.CLOSED and self.failure_count >= self.failure_threshold:
                    # Transition to open state
                    self.state = CircuitState.OPEN
                
                if self.state == CircuitState.HALF_OPEN:
                    # Transition back to open state on failure
                    self.state = CircuitState.OPEN
            
            # Re-raise the exception
            raise
    
    def reset(self):
        """Reset the circuit breaker to its initial closed state."""
        with self._lock:
            self.state = CircuitState.CLOSED
            self.failure_count = 0
            self.success_count = 0
            self.last_failure_time = 0
    
    @property
    def is_open(self):
        """Check if the circuit is currently open."""
        return self.state == CircuitState.OPEN
    
    @property
    def is_closed(self):
        """Check if the circuit is currently closed."""
        return self.state == CircuitState.CLOSED
    
    @property
    def is_half_open(self):
        """Check if the circuit is currently half-open."""
        return self.state == CircuitState.HALF_OPEN
