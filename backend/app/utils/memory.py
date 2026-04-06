"""
Memory monitoring utilities for Raspberry Pi 3.
Track and enforce memory limits.
"""
import logging
import resource
from typing import Optional

logger = logging.getLogger(__name__)


class MemoryMonitor:
    """
    Monitor process memory usage.
    Optimized for low overhead (no external dependencies).
    """

    def __init__(self, max_mb: int = 512):
        self.max_bytes = max_mb * 1024 * 1024

    def get_current_memory(self) -> int:
        """Get current process memory in bytes."""
        usage = resource.getrusage(resource.RUSAGE_SELF)
        # maxrss is in KB on Linux
        return usage.ru_maxrss * 1024

    def get_memory_mb(self) -> float:
        """Get current memory in MB."""
        return self.get_current_memory() / (1024 * 1024)

    def is_within_limit(self) -> bool:
        """Check if memory usage is within limit."""
        return self.get_current_memory() < self.max_bytes

    def log_status(self) -> None:
        """Log current memory status."""
        current_mb = self.get_memory_mb()
        limit_mb = self.max_bytes / (1024 * 1024)
        percent = (current_mb / limit_mb) * 100
        logger.info(f"Memory: {current_mb:.1f}MB / {limit_mb}MB ({percent:.1f}%)")


# Global monitor instance
_monitor: Optional[MemoryMonitor] = None


def get_monitor(max_mb: int = 512) -> MemoryMonitor:
    """Get or create global memory monitor."""
    global _monitor
    if _monitor is None:
        _monitor = MemoryMonitor(max_mb)
    return _monitor


def check_memory() -> bool:
    """Quick check if memory is within limits."""
    return get_monitor().is_within_limit()


def log_memory() -> None:
    """Log current memory status."""
    get_monitor().log_status()
