"""
MPExecutor - Process-based executor for multiprocessing backend.

Wraps a Flow for execution in a separate process using multiprocessing.Process.
"""

import multiprocessing
from contextlib import nullcontext
from typing import Dict, List, Optional, Any
from retriever.core.flow.base import Flow
from retriever.core.flow.clock import Clock
from retriever.core.flow.adapter import Adapter
from retriever.core.rt.backend.interface import Executor, Subscriber, Publisher
from retriever.core.rt.backend.multiprocessing.scheduler import MPScheduler
from retriever.core.rt.signal import Signal
from retriever.core.rt.logging.worker import configure_worker
from retriever.core.rt.logging.handlers.otel import shutdown_otel

import logging
logger = logging.getLogger(__name__)


class MPExecutor(multiprocessing.Process, Executor):
    """
    Process-based executor for multiprocessing backend.

    Each executor runs one flow in isolation with its own:
    - Scheduler (determines when to execute)
    - Input channels (receives data)
    - Output channels (publishes results)
    - Adapters (samples input data)
    """

    def __init__(
        self,
        node_id: str,
        flow: Flow,
        clock: Clock,
        inputs: Dict[str, Subscriber],
        outputs: Dict[str, List[Publisher]],
        adapters: Dict[str, Adapter],
        log_params: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize MPExecutor.

        Args:
            node_id: Unique node identifier
            flow: Flow instance to execute
            clock: Clock for scheduling
            inputs: Dict mapping input port names to Subscribers
            outputs: Dict mapping output port names to List[Publishers]
            adapters: Dict mapping input port names to Adapters
            log_params: Logging params (queue, config, log_dir)
        """
        super().__init__(name=node_id)
        self.node_id = node_id
        self.flow = flow
        self.clock = clock
        self.inputs = inputs
        self.outputs = outputs
        self.adapters = adapters
        self.log_params = log_params
        self.scheduler = MPScheduler(clock)
        self._stop_flag = multiprocessing.Event()

    @property
    def name(self) -> str:
        """Executor name/identifier."""
        return self.node_id

    def run(self):
        """
        Main process loop.

        Lifecycle:
        1. Configure logging for this worker
        2. Initialize flow (flow.init())
        3. Reset scheduler
        4. Main execution loop:
           - Advance to next execution point (scheduler.next)
           - Sample inputs using adapters (Signal.sample)
           - Transform via flow.run() (Signal.transform)
           - Publish outputs (Signal.publish)
        5. Finalize flow (flow.finalize())
        6. Shutdown OTel
        """
        # Configure logging for this worker process
        if self.log_params:
            configure_worker(
                self.node_id,
                type(self.flow).__name__,
                self.log_params['queue'],
                self.log_params['config'],
                self.log_params['log_dir'],
            )

        tracer = None
        try:
            from opentelemetry import trace  # type: ignore
            tracer = trace.get_tracer('retriever.runtime')
        except Exception:
            tracer = None

        logger.info(f"[{self.node_id}] Starting MPExecutor")

        try:
            # Initialize flow
            self.flow.init()
            logger.info(f"[{self.node_id}] Flow initialized")

            # Reset scheduler
            self.scheduler.reset()

            # Main execution loop
            while not self._stop_flag.is_set():
                # Advance to next execution point (scheduler handles drain)
                result = self.scheduler.next(self.inputs)

                if not result.should_execute:
                    continue

                # FRP Signal pipeline: sample → transform → publish
                span_cm = (
                    tracer.start_as_current_span('signal-function')
                    if tracer is not None
                    else nullcontext()
                )
                with span_cm as signal_span:
                    if signal_span is not None and hasattr(signal_span, "set_attributes"):
                        signal_span.set_attributes({
                            'node_id': self.node_id,
                            'fields': result.fields_to_sample,
                        })
                    Signal(self.inputs, result.fields_to_sample, now=result.now) \
                        .sample(self.flow.input_type, self.adapters, now=result.now) \
                        .transform(self.flow.run) \
                        .publish(self.outputs)

        except KeyboardInterrupt:
            logger.info(f"[{self.node_id}] Interrupted")
        except Exception as e:
            logger.error(f"[{self.node_id}] Error: {e}", exc_info=True)
        finally:
            # Finalize flow
            self.flow.finalize()
            logger.info(f"[{self.node_id}] MPExecutor terminated")
            # Flush OTel before exit
            shutdown_otel()

    def stop(self):
        """Signal executor to stop gracefully."""
        self._stop_flag.set()

    # join() method inherited from multiprocessing.Process
    # is_alive() method inherited from multiprocessing.Process
