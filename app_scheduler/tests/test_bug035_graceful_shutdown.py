"""
BUG-035: Scheduler missing graceful shutdown with pool cleanup.

Tests that the scheduler's main() function calls close_pool() on shutdown.
"""

import os
import sys
import inspect
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


class TestGracefulShutdown:
    """BUG-035: Scheduler must clean up DB pool on shutdown."""

    def test_scheduler_imports_close_pool(self):
        """scheduler.py must import close_pool."""
        import scheduler
        source = inspect.getsource(scheduler)
        assert "close_pool" in source, "scheduler must import close_pool"

    def test_scheduler_main_has_finally_block(self):
        """main() must have a finally block for cleanup."""
        import scheduler
        source = inspect.getsource(scheduler.main)
        assert "finally" in source, "main() must have a finally block"

    def test_scheduler_calls_close_pool_in_finally(self):
        """main() must call close_pool() in the finally block."""
        import scheduler
        source = inspect.getsource(scheduler.main)

        # Find the finally block and check it contains close_pool
        finally_idx = source.index("finally")
        after_finally = source[finally_idx:]
        assert "close_pool" in after_finally, \
            "close_pool() must be called in the finally block"

    def test_scheduler_shuts_down_apscheduler(self):
        """main() should call sched.shutdown() on exit."""
        import scheduler
        source = inspect.getsource(scheduler.main)
        assert "shutdown" in source, \
            "Scheduler should call sched.shutdown() on exit"
