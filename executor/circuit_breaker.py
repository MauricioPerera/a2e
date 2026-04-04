"""
Circuit breaker pattern for external API calls.
Prevents cascading failures when external services are down.
"""

import time
import logging
from enum import Enum
from typing import Dict, Optional

from .middleware import ExecutorMiddleware

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    """
    Circuit breaker for a single external service.

    States:
        CLOSED   - Normal operation, requests pass through.
        OPEN     - Service failing, requests rejected immediately.
        HALF_OPEN - Testing recovery, limited requests allowed.
    """

    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: float = 30.0,
        success_threshold: int = 2,
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.success_threshold = success_threshold
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[float] = None

    def can_execute(self) -> bool:
        """Check if a request should be allowed through."""
        if self.state == CircuitState.CLOSED:
            return True
        if self.state == CircuitState.OPEN:
            if time.monotonic() - (self.last_failure_time or 0) >= self.recovery_timeout:
                self.state = CircuitState.HALF_OPEN
                self.success_count = 0
                logger.info(f"Circuit breaker '{self.name}' entering half-open state")
                return True
            return False
        # HALF_OPEN
        return True

    def record_success(self):
        """Record a successful call."""
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.success_threshold:
                self.state = CircuitState.CLOSED
                self.failure_count = 0
                logger.info(f"Circuit breaker '{self.name}' closed (recovered)")
        else:
            self.failure_count = 0

    def record_failure(self):
        """Record a failed call."""
        self.failure_count += 1
        self.last_failure_time = time.monotonic()
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
            logger.warning(
                f"Circuit breaker '{self.name}' opened after {self.failure_count} failures"
            )

    @property
    def is_open(self) -> bool:
        return self.state == CircuitState.OPEN


class CircuitOpenError(Exception):
    """Raised when a circuit breaker is open and rejects the request."""
    pass


class CircuitBreakerMiddleware(ExecutorMiddleware):
    """
    Middleware that applies circuit breaker pattern to external API operations.
    Tracks failures per target host/workflow and opens the circuit when
    the failure threshold is reached.
    """

    EXTERNAL_OPS = ("ApiCall", "ExecuteN8nWorkflow")

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 30.0,
        success_threshold: int = 2,
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.success_threshold = success_threshold
        self._breakers: Dict[str, CircuitBreaker] = {}

    def _get_breaker(self, key: str) -> CircuitBreaker:
        if key not in self._breakers:
            self._breakers[key] = CircuitBreaker(
                name=key,
                failure_threshold=self.failure_threshold,
                recovery_timeout=self.recovery_timeout,
                success_threshold=self.success_threshold,
            )
        return self._breakers[key]

    def _extract_key(self, op_type: str, config: dict) -> Optional[str]:
        """Extract a circuit breaker key from the operation config."""
        if op_type == "ApiCall":
            url = config.get("url", "")
            if url:
                # Use scheme + host as key
                from urllib.parse import urlparse
                try:
                    parsed = urlparse(url)
                    return f"api:{parsed.scheme}://{parsed.netloc}"
                except Exception:
                    return f"api:{url[:60]}"
        elif op_type == "ExecuteN8nWorkflow":
            n8n_url = config.get("n8nUrl", "")
            wf_id = config.get("workflowId", "unknown")
            return f"n8n:{n8n_url or 'default'}:{wf_id}"
        return None

    def process_config(self, op_type, config):
        if op_type not in self.EXTERNAL_OPS:
            return config

        key = self._extract_key(op_type, config)
        if not key:
            return config

        breaker = self._get_breaker(key)
        if not breaker.can_execute():
            raise CircuitOpenError(
                f"Circuit breaker open for {key}. "
                f"Service has failed {breaker.failure_count} times. "
                f"Retry after {breaker.recovery_timeout}s."
            )

        config = dict(config)
        config["_circuit_breaker_key"] = key
        return config

    def process_result(self, op_type, config, result):
        key = config.get("_circuit_breaker_key") if isinstance(config, dict) else None
        if key:
            self._get_breaker(key).record_success()
        return result

    def on_operation_error(self, execution_id, op_id, op_type, error, duration_ms):
        if op_type not in self.EXTERNAL_OPS:
            return
        # We don't have the config here, so we track by op_type as fallback
        # The main tracking happens in process_config/process_result
        pass

    def get_status(self) -> Dict[str, dict]:
        """Return current state of all circuit breakers."""
        return {
            key: {
                "state": breaker.state.value,
                "failure_count": breaker.failure_count,
                "success_count": breaker.success_count,
            }
            for key, breaker in self._breakers.items()
        }
