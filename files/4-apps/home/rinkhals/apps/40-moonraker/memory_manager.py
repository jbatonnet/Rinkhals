# Memory Manager Component for Moonraker
# Prevents unbounded memory growth on RAM-constrained systems (213 MB total)
#
# Features:
# - Periodic garbage collection (every 5 minutes)
# - Memory usage logging
# - Prevents memory creep over long runtimes

import gc
import logging
import asyncio
import os


class MemoryManager:
    def __init__(self, config):
        self.server = config.get_server()
        self.eventloop = self.server.get_event_loop()

        # Configuration
        self.gc_interval = config.getint('gc_interval', 300)  # 5 minutes default
        self.log_stats = config.getboolean('log_stats', True)

        # Start periodic GC task
        self.eventloop.create_task(self._periodic_gc())

        logging.info(f"Memory Manager initialized (GC interval: {self.gc_interval}s)")

    async def _periodic_gc(self):
        """
        Periodically run garbage collection to prevent memory creep.

        On RAM-constrained systems, Python's automatic GC may not be
        aggressive enough, leading to gradual memory growth over days.
        This task explicitly triggers GC every few minutes.
        """
        while True:
            try:
                await asyncio.sleep(self.gc_interval)

                # Get memory before GC (if available)
                mem_before_mb = None
                try:
                    # Try to get RSS memory without psutil dependency
                    with open('/proc/self/status', 'r') as f:
                        for line in f:
                            if line.startswith('VmRSS:'):
                                mem_kb = int(line.split()[1])
                                mem_before_mb = mem_kb / 1024
                                break
                except:
                    pass

                # Run garbage collection for all generations
                collected = gc.collect()

                # Get memory after GC
                mem_after_mb = None
                try:
                    with open('/proc/self/status', 'r') as f:
                        for line in f:
                            if line.startswith('VmRSS:'):
                                mem_kb = int(line.split()[1])
                                mem_after_mb = mem_kb / 1024
                                break
                except:
                    pass

                # Log results
                if self.log_stats:
                    if mem_before_mb and mem_after_mb:
                        freed_mb = mem_before_mb - mem_after_mb
                        logging.info(
                            f"GC: Collected {collected} objects, "
                            f"Memory: {mem_before_mb:.1f} MB → {mem_after_mb:.1f} MB "
                            f"(freed {freed_mb:.1f} MB)"
                        )
                    else:
                        logging.info(f"GC: Collected {collected} objects")

            except asyncio.CancelledError:
                logging.info("Memory Manager: Periodic GC task cancelled")
                break
            except Exception as e:
                logging.error(f"Memory Manager: Error during GC: {e}")
                # Continue running despite errors


def load_component(config):
    return MemoryManager(config)
