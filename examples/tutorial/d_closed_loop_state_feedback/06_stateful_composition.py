"""
Stateful composition using multiple flows (navigation + battery).

Run:
  pixi run python -m examples.tutorial.d_closed_loop_state_feedback.06_stateful_composition --steps 8 --dt 0.1
"""

from __future__ import annotations

import argparse

from retriever.flow import Flow, Pipeline, Rate, Latest, io


@io
class CommandIn:
    action: str | None = None
    dx: float | None = None
    dy: float | None = None
    charge: float | None = None


@io
class PoseOut:
    x: float | None = None
    y: float | None = None
    moved: bool | None = None


@io
class EnergyOut:
    energy: float | None = None
    status: str | None = None


@io
class MergeIn:
    x: float | None = None
    y: float | None = None
    moved: bool | None = None
    energy: float | None = None
    status: str | None = None


@io
class SummaryOut:
    x: float | None = None
    y: float | None = None
    energy: float | None = None
    note: str | None = None


class CommandSource(Flow[None, CommandIn]):
    def reset(self) -> None:
        self.commands = [
            CommandIn(action="move", dx=1.0, dy=0.0),
            CommandIn(action="move", dx=1.0, dy=1.0),
            CommandIn(action="charge", charge=30.0),
            CommandIn(action="move", dx=2.0, dy=0.0),
        ]
        self.idx = 0

    def step(self, _):  # type: ignore[override]
        if self.idx >= len(self.commands):
            return CommandIn()
        cmd = self.commands[self.idx]
        self.idx += 1
        return cmd


class Navigator(Flow[CommandIn, PoseOut]):
    def reset(self) -> None:
        self.x = 0.0
        self.y = 0.0

    def step(self, input: CommandIn) -> PoseOut:
        if input.action is None:
            return PoseOut()
        moved = False
        if input.action == "move" and input.dx is not None and input.dy is not None:
            self.x += float(input.dx)
            self.y += float(input.dy)
            moved = True
        return PoseOut(x=self.x, y=self.y, moved=moved)


class BatteryManager(Flow[CommandIn, EnergyOut]):
    def reset(self) -> None:
        self.energy = 50.0

    def step(self, input: CommandIn) -> EnergyOut:
        if input.action is None:
            return EnergyOut()
        status = "idle"
        if input.action == "move" and input.dx is not None and input.dy is not None:
            cost = 10.0 * (abs(input.dx) + abs(input.dy))
            if self.energy >= cost:
                self.energy -= cost
                status = "moved"
            else:
                status = "low_energy"
        elif input.action == "charge" and input.charge is not None:
            self.energy = min(100.0, self.energy + float(input.charge))
            status = "charged"
        return EnergyOut(energy=self.energy, status=status)


class Merger(Flow[MergeIn, SummaryOut]):
    def step(self, input: MergeIn) -> SummaryOut:
        if input.x is None or input.y is None or input.energy is None:
            return SummaryOut()
        note = input.status or "ok"
        if input.moved is False and input.status == "low_energy":
            note = "blocked: low energy"
        return SummaryOut(x=input.x, y=input.y, energy=input.energy, note=note)


class Printer(Flow[SummaryOut, None]):
    def step(self, input: SummaryOut) -> None:
        if input.x is None or input.y is None or input.energy is None:
            return None
        print(
            f"pos=({input.x:.1f},{input.y:.1f}) energy={input.energy:.1f} note={input.note}"
        )
        return None


def build_pipeline(hz: float) -> Pipeline:
    pipe = Pipeline("stateful_composition")
    clock = Rate(hz=hz)

    with pipe:
        src = CommandSource() @ clock
        nav = Navigator() @ clock
        batt = BatteryManager() @ clock
        merge = Merger() @ clock
        prn = Printer() @ clock

        pipe.connect(src, nav, sync=Latest())
        pipe.connect(src, batt, sync=Latest())
        pipe.connect(
            nav,
            merge,
            sync=Latest(),
            map={"x": "x", "y": "y", "moved": "moved"},
        )
        pipe.connect(
            batt,
            merge,
            sync=Latest(),
            map={"energy": "energy", "status": "status"},
        )
        pipe.connect(merge, prn, sync=Latest())

    return pipe


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Stateful composition demo.")
    p.add_argument("--steps", type=int, default=8)
    p.add_argument("--dt", type=float, default=0.1)
    return p.parse_args()


def main() -> None:
    args = parse_args()
    hz = 1.0 / max(args.dt, 1e-6)
    pipe = build_pipeline(hz)
    for _ in range(args.steps):
        pipe.step(dt=args.dt)
    pipe.close_stepper()


if __name__ == "__main__":
    main()
