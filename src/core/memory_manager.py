"""
Memory Manager: Ensures AI browser stays within RAM limits.
Provides adaptive concurrency, process tracking, and emergency GC.
"""

import psutil
import asyncio
import gc
from typing import Set


class MemoryManager:
    """
    Ensures the AI browser never exceeds system RAM limits.
    Provides:
    - RAM usage monitoring
    - Adaptive concurrency (more RAM available = more concurrent ops)
    - Process-level Chromium PID tracking
    - Emergency garbage collection
    """

    def __init__(self, threshold_percent: float = 85.0):
        self.threshold_percent = threshold_percent
        self.chromium_pids: Set[int] = set()
        self.needs_cleanup = False

    # ------------------------------------------------------------------
    # RAM Monitoring
    # ------------------------------------------------------------------

    def get_usage_percent(self) -> float:
        """Get current system RAM usage as a percentage."""
        return psutil.virtual_memory().percent

    def is_memory_available(self) -> bool:
        """Check if RAM is below the safety threshold."""
        return self.get_usage_percent() <= self.threshold_percent

    def get_allowed_concurrency(self) -> int:
        """
        Returns how many concurrent operations are safe based on RAM.
        Scales from 100 (low usage) to 0 (at threshold).
        """
        mem_pct = self.get_usage_percent()
        if mem_pct >= self.threshold_percent:
            return 0
        elif mem_pct >= 80.0:
            return 5
        elif mem_pct >= 70.0:
            return 20
        elif mem_pct >= 60.0:
            return 50
        else:
            return 100

    # ------------------------------------------------------------------
    # Process Tracking
    # ------------------------------------------------------------------

    def track_pid(self, pid: int) -> None:
        """Track a Chromium process PID for memory accounting."""
        self.chromium_pids.add(pid)

    def untrack_pid(self, pid: int) -> None:
        """Stop tracking a Chromium process PID."""
        self.chromium_pids.discard(pid)

    def get_chromium_memory_mb(self) -> float:
        """Get total memory used by tracked Chromium processes in MB."""
        total = 0.0
        dead_pids = set()
        for pid in self.chromium_pids:
            try:
                proc = psutil.Process(pid)
                total += proc.memory_info().rss / (1024 * 1024)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                dead_pids.add(pid)
        # Clean up dead PIDs
        self.chromium_pids -= dead_pids
        return total

    # ------------------------------------------------------------------
    # Emergency GC & Waiting
    # ------------------------------------------------------------------

    def check_emergency_gc(self) -> bool:
        """Trigger emergency GC if RAM is critically high (>88%)."""
        if self.get_usage_percent() > 88.0:
            gc.collect()
            self.needs_cleanup = True
            return True
        return False

    async def wait_for_memory(self, check_interval: float = 0.5) -> None:
        """
        Block execution until system RAM drops below threshold.
        Performs emergency GC while waiting.
        """
        while True:
            self.check_emergency_gc()
            if self.is_memory_available():
                break
            pct = self.get_usage_percent()
            print(f"[MemoryManager] RAM at {pct:.1f}% (threshold {self.threshold_percent}%). Waiting...")
            await asyncio.sleep(check_interval)

    def get_status(self) -> dict:
        """Get comprehensive memory status."""
        return {
            "ram_percent": self.get_usage_percent(),
            "threshold": self.threshold_percent,
            "is_safe": self.is_memory_available(),
            "allowed_concurrency": self.get_allowed_concurrency(),
            "tracked_chromium_pids": len(self.chromium_pids),
            "chromium_memory_mb": self.get_chromium_memory_mb(),
            "needs_cleanup": self.needs_cleanup,
        }
