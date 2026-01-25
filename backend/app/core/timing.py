"""Timing utilities for latency measurement and profiling.

This module provides tools to measure operation durations and log timing breakdowns
for identifying performance bottlenecks.
"""

import time
from contextlib import contextmanager, asynccontextmanager
from typing import Dict, Optional
from app.core.logging import logger


class TimingContext:
    """Collects timing measurements for a request or operation.
    
    Usage:
        timing = TimingContext(request_id="abc123")
        
        with timing.measure("operation_name"):
            # code to measure
            
        timing.log_summary()
    """
    
    def __init__(self, request_id: str, prefix: str = ""):
        """Initialize timing context.
        
        Args:
            request_id: Unique identifier for correlating measurements.
            prefix: Optional prefix for operation names.
        """
        self.request_id = request_id
        self.prefix = prefix
        self.timings: Dict[str, float] = {}
        self._start_time = time.perf_counter()
    
    def _get_operation_name(self, operation: str) -> str:
        """Get full operation name with optional prefix."""
        if self.prefix:
            return f"{self.prefix}.{operation}"
        return operation
    
    @contextmanager
    def measure(self, operation: str):
        """Context manager to measure operation duration.
        
        Args:
            operation: Name of the operation being measured.
            
        Yields:
            None
        """
        full_name = self._get_operation_name(operation)
        start = time.perf_counter()
        try:
            yield
        finally:
            duration = time.perf_counter() - start
            self.timings[full_name] = duration
            logger.info(
                "timing_measurement",
                request_id=self.request_id,
                operation=full_name,
                duration_ms=round(duration * 1000, 2),
            )
    
    @asynccontextmanager
    async def measure_async(self, operation: str):
        """Async context manager to measure operation duration.
        
        Args:
            operation: Name of the operation being measured.
            
        Yields:
            None
        """
        full_name = self._get_operation_name(operation)
        start = time.perf_counter()
        try:
            yield
        finally:
            duration = time.perf_counter() - start
            self.timings[full_name] = duration
            logger.info(
                "timing_measurement",
                request_id=self.request_id,
                operation=full_name,
                duration_ms=round(duration * 1000, 2),
            )
    
    def record(self, operation: str, duration: float):
        """Manually record a timing measurement.
        
        Args:
            operation: Name of the operation.
            duration: Duration in seconds.
        """
        full_name = self._get_operation_name(operation)
        self.timings[full_name] = duration
        logger.info(
            "timing_measurement",
            request_id=self.request_id,
            operation=full_name,
            duration_ms=round(duration * 1000, 2),
        )
    
    def log_summary(self):
        """Log summary of all collected timings."""
        total_elapsed = time.perf_counter() - self._start_time
        measured_total = sum(self.timings.values())
        
        # Sort by duration descending for easier analysis
        sorted_timings = dict(
            sorted(self.timings.items(), key=lambda x: x[1], reverse=True)
        )
        
        logger.info(
            "timing_summary",
            request_id=self.request_id,
            total_elapsed_ms=round(total_elapsed * 1000, 2),
            measured_total_ms=round(measured_total * 1000, 2),
            breakdown_ms={k: round(v * 1000, 2) for k, v in sorted_timings.items()},
        )
    
    def get_duration(self, operation: str) -> Optional[float]:
        """Get the recorded duration for an operation.
        
        Args:
            operation: Name of the operation.
            
        Returns:
            Duration in seconds, or None if not recorded.
        """
        full_name = self._get_operation_name(operation)
        return self.timings.get(full_name)


# Global timing context for operations that span multiple function calls
# Use thread-local storage for thread safety
import threading

_timing_context_local = threading.local()


def get_current_timing() -> Optional[TimingContext]:
    """Get the current timing context for this thread."""
    return getattr(_timing_context_local, "timing", None)


def set_current_timing(timing: Optional[TimingContext]):
    """Set the current timing context for this thread."""
    _timing_context_local.timing = timing


@contextmanager
def timing_scope(request_id: str, prefix: str = ""):
    """Context manager to establish a timing scope.
    
    Args:
        request_id: Unique identifier for correlating measurements.
        prefix: Optional prefix for operation names.
        
    Yields:
        TimingContext: The timing context for this scope.
    """
    timing = TimingContext(request_id=request_id, prefix=prefix)
    previous = get_current_timing()
    set_current_timing(timing)
    try:
        yield timing
    finally:
        timing.log_summary()
        set_current_timing(previous)


def measure_operation(operation: str):
    """Decorator to measure function execution time.
    
    Uses the current thread's timing context if available.
    
    Args:
        operation: Name of the operation being measured.
    """
    def decorator(func):
        async def async_wrapper(*args, **kwargs):
            timing = get_current_timing()
            if timing:
                async with timing.measure_async(operation):
                    return await func(*args, **kwargs)
            else:
                return await func(*args, **kwargs)
        
        def sync_wrapper(*args, **kwargs):
            timing = get_current_timing()
            if timing:
                with timing.measure(operation):
                    return func(*args, **kwargs)
            else:
                return func(*args, **kwargs)
        
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    
    return decorator
