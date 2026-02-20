# config.py
import os

# Centralized configuration module
SELF_FIXER_INITIAL_BACKOFF = float(os.getenv("SELF_FIXER_INITIAL_BACKOFF", 0.2))
SELF_FIXER_MAX_BACKOFF = float(os.getenv("SELF_FIXER_MAX_BACKOFF", 5.0))
SELF_FIXER_HEARTBEAT_FREQ = int(os.getenv("SELF_FIXER_HEARTBEAT_FREQ", 10))
SELF_FIXER_STATUS_FILE = os.getenv("SELF_FIXER_STATUS_FILE", "self_fixer_status.txt")
SELF_FIXER_HEARTBEAT_MAX_BACKOFF = int(os.getenv("SELF_FIXER_HEARTBEAT_MAX_BACKOFF", 10))
SELF_FIXER_IDLE_THRESHOLD = int(os.getenv("SELF_FIXER_IDLE_THRESHOLD", 5))
SELF_FIXER_LOG_MODE = os.getenv("SELF_FIXER_LOG_MODE", "file")  # 'file' or 'console'

# logging_config.py
import logging
from logging.handlers import TimedRotatingFileHandler
import sys
from config import SELF_FIXER_LOG_MODE

def configure_logging():
    logger = logging.getLogger("SelfFixerDaemon")
    logger.setLevel(logging.DEBUG)

    if SELF_FIXER_LOG_MODE == "console":
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
        logger.addHandler(handler)
    else:
        info_handler = TimedRotatingFileHandler("self_fixer_info.log", when="midnight", interval=1, backupCount=7)
        info_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
        info_handler.setLevel(logging.INFO)

        error_handler = TimedRotatingFileHandler("self_fixer_error.log", when="midnight", interval=1, backupCount=7)
        error_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
        error_handler.setLevel(logging.ERROR)

        debug_handler = TimedRotatingFileHandler("self_fixer_debug.log", when="midnight", interval=1, backupCount=7)
        debug_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
        debug_handler.setLevel(logging.DEBUG)

        logger.addHandler(info_handler)
        logger.addHandler(error_handler)
        logger.addHandler(debug_handler)

    return logger

# test/test_heartbeat_monitor.py
import asyncio
import pytest
from heartbeat_monitor import HeartbeatMonitor

@pytest.mark.asyncio
async def test_heartbeat_monitor_runs_and_stops(tmp_path):
    status_file = tmp_path / "status.txt"
    monitor = HeartbeatMonitor(freq=1, status_file=str(status_file))
    task = asyncio.create_task(monitor.run())
    await asyncio.sleep(2)
    monitor.stop()
    await asyncio.sleep(0.1)
    assert status_file.exists()

# test/test_event_scheduler.py
import asyncio
import pytest
from queue import Queue
from event_scheduler import EventScheduler

@pytest.mark.asyncio
async def test_event_scheduler_puts_events():
    q = Queue()
    scheduler = EventScheduler(q, lambda: True)
    await scheduler.schedule_events(timeout=0.5)
    assert not q.empty()

# test/test_event_processor.py
import asyncio
import pytest
from queue import Queue
from event_processor import EventProcessor
from heartbeat_monitor import HeartbeatMonitor

@pytest.mark.asyncio
async def test_event_processor_handles_event(tmp_path):
    q = Queue()
    monitor = HeartbeatMonitor(freq=1, status_file=str(tmp_path / "status.txt"))
    processor = EventProcessor(q, monitor, lambda: True, idle_threshold=2)
    q.put("test_event")
    task = asyncio.create_task(processor.process_events())
    await asyncio.sleep(1)
    processor.heartbeat_monitor.stop()
    assert not q.qsize()
    task.cancel()

# daemon.py
import asyncio
import signal
from queue import Queue
from config import (
    SELF_FIXER_HEARTBEAT_FREQ,
    SELF_FIXER_STATUS_FILE,
    SELF_FIXER_IDLE_THRESHOLD
)
from logging_config import configure_logging
from heartbeat_monitor import HeartbeatMonitor
from event_scheduler import EventScheduler
from event_processor import EventProcessor

logger = configure_logging()

class SelfFixerDaemon:
    def __init__(self):
        self.event_queue = Queue()
        self._running = False
        self._loop = None
        self._main_task = None
        self._timeout = None
        self.heartbeat_monitor = HeartbeatMonitor(SELF_FIXER_HEARTBEAT_FREQ, SELF_FIXER_STATUS_FILE)
        self.scheduler = EventScheduler(self.event_queue, self.is_running)
        self.processor = EventProcessor(self.event_queue, self.heartbeat_monitor, self.is_running, idle_threshold=SELF_FIXER_IDLE_THRESHOLD)

    def is_running(self):
        return self._running

    async def _run(self, timeout):
        async with asyncio.TaskGroup() as tg:
            tg.create_task(self.processor.process_events())
            tg.create_task(self.scheduler.schedule_events(timeout))
        logger.info("All TaskGroup tasks completed or cancelled.")

    def start(self, timeout=None):
        logger.info("Starting SelfFixerDaemon.")
        self._running = True
        self._timeout = timeout
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)

        for sig in (signal.SIGINT, signal.SIGTERM):
            self._loop.add_signal_handler(sig, lambda s=sig: self.stop())

        try:
            self._main_task = self._loop.create_task(self._run(timeout))
            self._loop.run_until_complete(self._main_task)
        except asyncio.CancelledError:
            logger.info("Main task cancelled.")
        finally:
            self.stop(wait=True)

    def stop(self, wait=False):
        if not self._running:
            return
        logger.info("Stopping SelfFixerDaemon.")
        self._running = False
        self.heartbeat_monitor.stop()

        try:
            while not self.event_queue.empty():
                self.event_queue.get_nowait()
        except Exception as e:
            logger.warning(f"Error clearing event queue: {e}")

        if self._loop:
            for task in asyncio.all_tasks(self._loop):
                task.cancel()
            if wait:
                logger.info("Waiting for all tasks to finish...")
                self._loop.run_until_complete(asyncio.gather(*asyncio.all_tasks(self._loop), return_exceptions=True))
            self._loop.stop()
            self._loop.close()
        logger.info("Daemon stopped cleanly.")

    def __enter__(self, timeout=None):
        logger.info("Entering SelfFixerDaemon context.")
        self.start(timeout=timeout)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        logger.info("Exiting SelfFixerDaemon context.")
        self.stop(wait=True)

if __name__ == "__main__":
    with SelfFixerDaemon() as daemon:
        daemon.__enter__(timeout=120)
        pass
# daemon.py
import asyncio
import signal
import time
from queue import Queue
from typing import Optional
from config import (
    SELF_FIXER_HEARTBEAT_FREQ,
    SELF_FIXER_STATUS_FILE,
    SELF_FIXER_IDLE_THRESHOLD
)
from logging_config import configure_logging
from heartbeat_monitor import HeartbeatMonitor
from event_scheduler import EventScheduler
from event_processor import EventProcessor

logger = configure_logging()

class SelfFixerDaemon:
    def __init__(self, timeout: Optional[int] = None):
        self.event_queue = Queue()
        self._running = False
        self._loop = None
        self._main_task = None
        self._timeout = timeout
        self.heartbeat_monitor = HeartbeatMonitor(SELF_FIXER_HEARTBEAT_FREQ, SELF_FIXER_STATUS_FILE)
        self.scheduler = EventScheduler(self.event_queue, self.is_running)
        self.processor = EventProcessor(
            self.event_queue,
            self.heartbeat_monitor,
            self.is_running,
            idle_threshold=SELF_FIXER_IDLE_THRESHOLD
        )

    # ------------------ Utility Methods ------------------

    def is_running(self):
        return self._running

    def _clear_event_queue(self):
        """Clear all remaining events from the queue safely."""
        try:
            while not self.event_queue.empty():
                self.event_queue.get_nowait()
        except Exception as e:
            logger.warning(f"Error clearing event queue: {e}")

    async def _write_status(self):
        """Periodically write daemon status to the configured status file."""
        while self._running:
            if SELF_FIXER_HEARTBEAT_FREQ <= 0:
                await asyncio.sleep(1)
                continue
            await asyncio.sleep(SELF_FIXER_HEARTBEAT_FREQ)
            try:
                with open(SELF_FIXER_STATUS_FILE, "w") as f:
                    f.write(f"running:{self._running}|last:{time.time()}\n")
            except Exception:
                pass  # Silent fail

    async def _run_tasks(self, timeout):
        """Run all async tasks: event processor, scheduler, and status writer."""
        async with asyncio.TaskGroup() as tg:
            tg.create_task(self.processor.process_events())
            tg.create_task(self.scheduler.schedule_events(timeout))
            tg.create_task(self._write_status())
        logger.info("All TaskGroup tasks completed or cancelled.")

    # ------------------ Core Lifecycle ------------------

    def start(self, timeout=None):
        logger.info("Starting SelfFixerDaemon.")
        self._running = True
        if timeout is not None:
            self._timeout = timeout

        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)

        for sig in (signal.SIGINT, signal.SIGTERM):
            self._loop.add_signal_handler(sig, lambda s=sig: self.stop())

        try:
            self._main_task = self._loop.create_task(self._run_tasks(self._timeout))
            self._loop.run_until_complete(self._main_task)
        except asyncio.CancelledError:
            logger.info("Main task cancelled.")
        finally:
            self.stop(wait=True)

    def stop(self, wait=False):
        if not self._running:
            return
        logger.info("Stopping SelfFixerDaemon.")
        self._running = False
        self.heartbeat_monitor.stop()

        self._clear_event_queue()

        if self._loop:
            for task in asyncio.all_tasks(self._loop):
                task.cancel()
            if wait:
                logger.info("Waiting for all tasks to finish...")
                self._loop.run_until_complete(
                    asyncio.gather(*asyncio.all_tasks(self._loop), return_exceptions=True)
                )
            self._loop.stop()
            self._loop.close()
        logger.info("Daemon stopped cleanly.")

    # ------------------ Context Manager ------------------

    def __enter__(self):
        logger.info("Entering SelfFixerDaemon context.")
        self.start(timeout=self._timeout)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        logger.info("Exiting SelfFixerDaemon context.")
        self.stop(wait=True)


def main():
    """Script entry point: run SelfFixerDaemon for a fixed duration or until signal."""
    with SelfFixerDaemon(timeout=120) as daemon:
        # runs ~2 min or until signal
        pass


if __name__ == "__main__":
    main()
