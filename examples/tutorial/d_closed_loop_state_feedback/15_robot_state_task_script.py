"""
Stateful robot updates with a small task script (no Eff).

Run:
  pixi run python -m examples.tutorial.d_closed_loop_state_feedback.15_robot_state_task_script --steps 8 --dt 0.1
"""

from __future__ import annotations

import argparse
import math
from dataclasses import dataclass, replace

from retriever.flow import Flow, Pipeline, Rate, Latest, io


@io
class TaskIn:
    kind: str | None = None
    x: float | None = None
    y: float | None = None
    object_id: str | None = None


@io
class RobotOut:
    kind: str | None = None
    status: str | None = None
    x: float | None = None
    y: float | None = None
    battery: float | None = None
    visible: list[str] | None = None
    held: list[str] | None = None


@dataclass(frozen=True)
class RobotState:
    x: float = 0.0
    y: float = 0.0
    battery: float = 5.0
    visible: tuple[str, ...] = ()
    held: tuple[str, ...] = ()


class TaskSource(Flow[None, TaskIn]):
    def reset(self) -> None:
        self.tasks = [
            TaskIn(kind="move", x=1.0, y=0.0),
            TaskIn(kind="scan"),
            TaskIn(kind="pick", object_id="cup"),
            TaskIn(kind="move", x=2.0, y=1.0),
            TaskIn(kind="scan"),
            TaskIn(kind="pick", object_id="bottle"),
        ]
        self.index = 0

    def step(self, _):  # type: ignore[override]
        if self.index >= len(self.tasks):
            return TaskIn()
        task = self.tasks[self.index]
        self.index += 1
        return task


class RobotController(Flow[TaskIn, RobotOut]):
    def reset(self) -> None:
        self.state = RobotState()

    def step(self, input: TaskIn) -> RobotOut:
        if input.kind is None:
            return RobotOut()

        if input.kind == "move":
            if input.x is None or input.y is None:
                return RobotOut()
            status, new_state = self._move_to(input.x, input.y)
        elif input.kind == "scan":
            status, new_state = self._scan()
        elif input.kind == "pick":
            if input.object_id is None:
                return RobotOut()
            status, new_state = self._pick(input.object_id)
        else:
            return RobotOut()
        self.state = new_state

        return RobotOut(
            kind=input.kind,
            status=status,
            x=new_state.x,
            y=new_state.y,
            battery=new_state.battery,
            visible=list(new_state.visible),
            held=list(new_state.held),
        )

    def _move_to(self, x: float, y: float) -> tuple[str, RobotState]:
        distance = math.hypot(x - self.state.x, y - self.state.y)
        cost = 0.5 * distance
        if self.state.battery < cost:
            return "move blocked", self.state
        new_state = replace(
            self.state, x=x, y=y, battery=self.state.battery - cost
        )
        return "moved", new_state

    def _scan(self) -> tuple[str, RobotState]:
        visible: tuple[str, ...] = ()
        if abs(self.state.x - 1.0) < 0.2 and abs(self.state.y - 0.0) < 0.2:
            visible = ("cup",)
        elif abs(self.state.x - 2.0) < 0.2 and abs(self.state.y - 1.0) < 0.2:
            visible = ("bottle",)

        cost = 0.2
        new_state = replace(
            self.state, visible=visible, battery=max(0.0, self.state.battery - cost)
        )
        status = f"seen: {', '.join(visible)}" if visible else "seen: none"
        return status, new_state

    def _pick(self, object_id: str) -> tuple[str, RobotState]:
        can_pick = (
            object_id in self.state.visible
            and object_id not in self.state.held
            and self.state.battery >= 0.1
        )
        if not can_pick:
            return f"pick failed: {object_id}", self.state

        held = self.state.held + (object_id,)
        visible = tuple(obj for obj in self.state.visible if obj != object_id)
        new_state = replace(
            self.state,
            held=held,
            visible=visible,
            battery=max(0.0, self.state.battery - 0.1),
        )
        return f"picked {object_id}", new_state


class Printer(Flow[RobotOut, None]):
    def step(self, input: RobotOut) -> None:
        if input.kind is None or input.status is None:
            return None
        print(
            f"{input.kind}: {input.status} | "
            f"pos=({input.x:.1f},{input.y:.1f}) "
            f"battery={input.battery:.2f} "
            f"visible={input.visible} held={input.held}"
        )
        return None


def build_pipeline(hz: float) -> Pipeline:
    pipe = Pipeline("robot_state_task_script")
    clock = Rate(hz=hz)

    with pipe:
        tasks = TaskSource() @ clock
        robot = RobotController() @ clock
        printer = Printer() @ clock
        pipe.connect(tasks, robot, sync=Latest())
        pipe.connect(robot, printer, sync=Latest())

    return pipe


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Robot state updates from a scripted task stream.")
    p.add_argument("--steps", type=int, default=8)
    p.add_argument("--dt", type=float, default=0.1)
    return p.parse_args()


def main() -> None:
    args = parse_args()
    hz = 1.0 / max(args.dt, 1e-6)
    pipe = build_pipeline(hz=hz)

    for _ in range(args.steps):
        pipe.step(dt=args.dt)

    pipe.close_stepper()


if __name__ == "__main__":
    main()
