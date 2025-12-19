"""
Performance Benchmarking Infrastructure for Retriever Runtime.

This module provides tools to measure and compare performance between
different execution backends (e.g. Multiprocessing vs Dora).
"""

import time
import psutil
import statistics
import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union
from contextlib import contextmanager

from retriever.rt.runtime import execute_ir
from retriever.ir.struct import IRStruct
from retriever.ir.execution import ExecutionGraph


@dataclass
class BenchmarkResult:
    """Container for benchmark execution results."""
    name: str
    backend: str
    duration: float
    memory_peak_mb: float
    memory_avg_mb: float
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BenchmarkSuite:
    """Collection of benchmark results for comparison."""
    results: List[BenchmarkResult] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: time.strftime("%Y-%m-%d %H:%M:%S"))

    def add_result(self, result: BenchmarkResult) -> None:
        self.results.append(result)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "results": [
                {
                    "name": r.name,
                    "backend": r.backend,
                    "duration": r.duration,
                    "memory_peak_mb": r.memory_peak_mb,
                    "memory_avg_mb": r.memory_avg_mb,
                    "metadata": r.metadata
                }
                for r in self.results
            ]
        }


class PerformanceBenchmarker:
    """
    Benchmarking system for comparing runtime backends.
    """

    def __init__(self, output_file: Optional[str] = None):
        self.suite = BenchmarkSuite()
        self.output_file = output_file

    def benchmark_pipeline(
        self,
        ir: Union[IRStruct, ExecutionGraph],
        name: str,
        duration: float = 5.0,
        backends: List[str] = None,
    ):
        """
        Benchmark a pipeline execution on multiple backends.

        Args:
            ir: Pipeline definition (IRStruct or ExecutionGraph)
            name: Benchmark name
            duration: Time to run the pipeline in seconds
            backends: List of backends to test (default: ['multiprocessing', 'dora'])
        """
        if backends is None:
            backends = ["multiprocessing", "dora"]

        print(f"\nBenchmarking Pipeline: {name}")
        print("-" * 40)

        for backend in backends:
            print(f"Testing backend: {backend}...")
            
            try:
                result = self._run_benchmark(ir, name, backend, duration)
                self.suite.add_result(result)
                print(f"  Duration: {result.duration:.2f}s")
                print(f"  Memory Peak: {result.memory_peak_mb:.1f} MB")
            except Exception as e:
                print(f"  FAILED: {e}")

        if self.output_file:
            self._save_results()

    def _run_benchmark(
        self,
        ir: Union[IRStruct, ExecutionGraph],
        name: str,
        backend: str,
        duration: float
    ) -> BenchmarkResult:
        with self._memory_monitor() as mem_tracker:
            start_time = time.time()
            
            # Execute pipeline
            engine = execute_ir(
                ir,
                backend=backend,
                duration=duration,
                blocking=True,
                log_config=None  # Default logging
            )
            
            actual_duration = time.time() - start_time

        # Calculate metrics
        peak_mb = max(mem_tracker.measurements) if mem_tracker.measurements else 0.0
        avg_mb = statistics.mean(mem_tracker.measurements) if mem_tracker.measurements else 0.0

        return BenchmarkResult(
            name=name,
            backend=backend,
            duration=actual_duration,
            memory_peak_mb=peak_mb,
            memory_avg_mb=avg_mb,
            metadata={"requested_duration": duration}
        )

    @contextmanager
    def _memory_monitor(self):
        """Monitor memory usage of current process and children."""
        class MemoryTracker:
            def __init__(self):
                self.measurements = []
                self.process = psutil.Process()
                self._stop = False

            def start(self):
                import threading
                def monitor():
                    while not self._stop:
                        mem = self.process.memory_info().rss / 1024 / 1024
                        # Add child processes
                        for child in self.process.children(recursive=True):
                            try:
                                mem += child.memory_info().rss / 1024 / 1024
                            except (psutil.NoSuchProcess, psutil.AccessDenied):
                                pass
                        self.measurements.append(mem)
                        time.sleep(0.1)

                self.thread = threading.Thread(target=monitor)
                self.thread.start()

            def stop(self):
                self._stop = True
                self.thread.join()

        tracker = MemoryTracker()
        tracker.start()
        try:
            yield tracker
        finally:
            tracker.stop()

    def _save_results(self):
        if not self.output_file:
            return
        with open(self.output_file, "w") as f:
            json.dump(self.suite.to_dict(), f, indent=2)
        print(f"Results saved to {self.output_file}")
