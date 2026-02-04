"""
Tests for the pipeline control system.
"""

import pytest
import time
from dataclasses import dataclass

from retriever import Pipeline, Flow, Rate, Latest
from retriever.flow.io import io
from retriever.rt.control import (
    Controllable,
    FlowState,
    ControlChannel,
    InProcessControlChannel,
    PipelineController,
)


@io
@dataclass
class CounterInput:
    trigger: bool = False


@io
@dataclass
class CounterOutput:
    count: int = 0


class SimpleCounterFlow(Controllable, Flow[CounterInput, CounterOutput]):
    """A simple controllable flow for testing."""

    def __init__(self):
        super().__init__()
        self.counter = 0

    def step(self, input: CounterInput) -> CounterOutput:
        self.counter += 1
        return CounterOutput(count=self.counter)

    def reset(self) -> None:
        super().reset()
        self.counter = 0

    def get_custom_state(self):
        return {"counter": self.counter}


class TestControllable:
    """Test the Controllable mixin."""

    def test_initial_state(self):
        flow = SimpleCounterFlow()
        assert flow.control_state == FlowState.UNINITIALIZED

    def test_control_init(self):
        flow = SimpleCounterFlow()
        flow.control_init()
        assert flow.control_state == FlowState.RUNNING

    def test_pause_resume(self):
        flow = SimpleCounterFlow()
        flow.control_init()

        # Pause
        flow.pause()
        assert flow.control_state == FlowState.PAUSED
        assert not flow.control_pre_step()  # Should not execute when paused

        # Resume
        flow.resume()
        assert flow.control_state == FlowState.RUNNING
        assert flow.control_pre_step()  # Should execute when running

    def test_reset(self):
        flow = SimpleCounterFlow()
        flow.control_init()

        # Increment counter
        flow.step(CounterInput())
        flow.step(CounterInput())
        assert flow.counter == 2

        # Reset
        flow.reset()
        assert flow.counter == 0
        assert flow._step_count == 0

    def test_custom_state(self):
        flow = SimpleCounterFlow()
        flow.counter = 42
        state = flow.get_custom_state()
        assert state["counter"] == 42

    def test_get_status(self):
        flow = SimpleCounterFlow()
        flow.control_init()
        flow.step(CounterInput())

        status = flow.get_status("test_node")
        assert status.node_id == "test_node"
        assert status.flow_class == "SimpleCounterFlow"
        assert status.state == FlowState.RUNNING
        assert status.step_count > 0


class TestControlChannel:
    """Test the ControlChannel implementations."""

    def test_in_process_channel(self):
        from retriever.rt.control.channel import ControlCommand, ControlMessage

        channel = InProcessControlChannel()

        # Send a command
        msg = ControlMessage(command=ControlCommand.PAUSE, target="test")
        channel.send_command(msg)

        # Receive it
        received = channel.receive_command(timeout=0.1)
        assert received is not None
        assert received.command == ControlCommand.PAUSE
        assert received.target == "test"

    def test_channel_timeout(self):
        channel = InProcessControlChannel()

        # Should return None when empty
        msg = channel.receive_command(timeout=0.01)
        assert msg is None


class TestPipelineController:
    """Test the PipelineController."""

    def test_controller_creation(self):
        pipe = Pipeline("test")
        channel = InProcessControlChannel()
        controller = PipelineController(pipe, channel)

        assert controller._name == "test"

    @pytest.mark.skip(reason="Requires full pipeline execution setup")
    def test_pause_resume_integration(self):
        """Integration test for pause/resume."""
        # This would require setting up a full pipeline with executors
        # Skipped for unit tests - see examples for integration testing
        pass


class TestPipelineIntegration:
    """Integration tests using Pipeline.step() for debugging."""

    def test_controllable_flow_in_pipeline(self):
        """Test that a controllable flow works in a pipeline."""
        pipe = Pipeline("test_control")

        with pipe:
            counter = SimpleCounterFlow() @ Rate(10)

        # Step the pipeline a few times
        for _ in range(3):
            result = pipe.step()

        # Get the flow instance
        flow = counter.flow
        assert isinstance(flow, SimpleCounterFlow)
        assert flow.counter == 3

    def test_pipeline_reset(self):
        """Test that pipeline reset calls flow reset."""
        pipe = Pipeline("test_reset")

        with pipe:
            counter = SimpleCounterFlow() @ Rate(10)

        # Step a few times
        for _ in range(5):
            pipe.step()

        flow = counter.flow
        assert flow.counter == 5

        # Reset the pipeline
        pipe.reset()

        # Counter should be reset
        assert flow.counter == 0

    def test_enable_control_creates_controller(self):
        """Test that control can be enabled via ControlConfig."""
        from retriever.rt.control import ControlConfig

        pipe = Pipeline("test_enable")

        # Enable control (without web/keyboard to avoid deps)
        config = ControlConfig(enabled=True, web_port=None, keyboard=False)
        ctrl = pipe._enable_control_from_config(config)

        assert ctrl is not None
        assert pipe.controller is ctrl
        assert pipe._control_channel is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
