"""Retriever Hub safety-monitoring example.

Loads the SafetyMonitor, SafetyActionMapper, and ActionPrinter flows from
the `openretriever/safety-monitor` hub module. SafetyScenario is defined
locally since it's the demo-specific signal source.

    pixi run python examples/hub/safety-monitoring.py --steps 12 --dt 0.1
"""

from __future__ import annotations

import argparse

from retriever import hub
from retriever.flow import Flow, Pipeline, Rate, Trigger, Latest

sm = hub.use("openretriever/safety-monitor")


class SafetyScenario(Flow[None, sm.SafetySample]):
    """Deterministic safety scenario with one warning and one emergency spike."""

    def __init__(self, *, dt: float):
        super().__init__()
        self.dt = float(dt)

    def init_config(self) -> dict:
        return {"dt": self.dt}

    def init(self) -> None:
        self._step = 0

    def reset(self) -> None:
        self._step = 0

    def run(self, _):  # type: ignore[override]
        self._step += 1
        t_sim = self._step * self.dt

        velocity = 1.0
        force = 25.0

        if 4 <= self._step <= 5:
            velocity = 2.6
        if self._step == 9:
            force = 92.0

        return sm.SafetySample(t_sim=t_sim, velocity=velocity, force=force)


def build_pipeline(*, dt: float) -> Pipeline:
    pipe = Pipeline("safety_monitoring")
    hz = 1.0 / max(dt, 1e-6)

    scenario = SafetyScenario(dt=dt) @ Rate(hz=hz)
    monitor = sm.SafetyMonitor() @ Rate(hz=hz)
    mapper = sm.SafetyActionMapper() @ Trigger("level")
    printer = sm.ActionPrinter() @ Trigger("action")

    pipe.connect(scenario, monitor, sync=Latest())
    pipe.connect(monitor, mapper, sync=Latest())
    pipe.connect(mapper, printer, sync=Latest())

    return pipe


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Safety monitoring demo (event-driven actions).")
    p.add_argument("--steps", type=int, default=12)
    p.add_argument("--dt", type=float, default=0.1)
    return p.parse_args()


def main() -> None:
    args = parse_args()
    pipe = build_pipeline(dt=args.dt)

    for _ in range(args.steps):
        pipe.step(dt=args.dt)

    pipe.close_stepper()


if __name__ == "__main__":
    main()
