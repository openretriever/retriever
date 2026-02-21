"""
Deadline-aware mode switching (hybrid control semantics).

Covers:
1) Deterministic workload profile with periodic heavy frames
2) Deadline monitor that tracks miss streak and total misses
3) Mode manager that switches NOMINAL <-> SAFE based on deadline health

Run:
  pixi run python -m examples.tutorial.d_closed_loop_state_feedback.13_deadline_aware_mode_switch --steps 16 --deadline-ms 8 --heavy-ms 14 --heavy-every 4 --miss-streak-limit 1
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
from pathlib import Path

from retriever.flow import Flow, Latest, Pipeline, Rate, Trigger, io

from examples.tutorial._p0_utils import format_table, utc_now_iso, write_json


@io
class Tick:
    step_idx: int | None = None
    t_sim: float | None = None


@io
class WorkReport:
    step_idx: int | None = None
    t_sim: float | None = None
    work_ms: float | None = None


@io
class DeadlineStatus:
    step_idx: int | None = None
    t_sim: float | None = None
    deadline_ms: float | None = None
    work_ms: float | None = None
    missed: bool | None = None
    miss_streak: int | None = None
    miss_total: int | None = None


@io
class ModeState:
    step_idx: int | None = None
    t_sim: float | None = None
    mode: str | None = None
    reason: str | None = None
    miss_total: int | None = None


@io
class ControlAction:
    step_idx: int | None = None
    t_sim: float | None = None
    action: str | None = None
    mode: str | None = None


@dataclass
class ModeTransition:
    step_idx: int
    t_sim: float
    mode: str
    reason: str
    miss_total: int


class TickSource(Flow[None, Tick]):
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
        return Tick(step_idx=self._step, t_sim=self._step * self.dt)


class SyntheticWorkload(Flow[Tick, WorkReport]):
    """
    Emits synthetic per-step "work cost" to simulate nominal vs overloaded frames.
    """

    def __init__(self, *, base_ms: float, heavy_ms: float, heavy_every: int):
        super().__init__()
        self.base_ms = float(base_ms)
        self.heavy_ms = float(heavy_ms)
        self.heavy_every = max(1, int(heavy_every))

    def init_config(self) -> dict:
        return {
            "base_ms": self.base_ms,
            "heavy_ms": self.heavy_ms,
            "heavy_every": self.heavy_every,
        }

    def run(self, input: Tick) -> WorkReport:
        if input.step_idx is None or input.t_sim is None:
            return WorkReport()

        heavy = input.step_idx % self.heavy_every == 0
        work_ms = self.heavy_ms if heavy else self.base_ms
        return WorkReport(step_idx=input.step_idx, t_sim=input.t_sim, work_ms=work_ms)


class DeadlineMonitor(Flow[WorkReport, DeadlineStatus]):
    def __init__(self, *, deadline_ms: float):
        super().__init__()
        self.deadline_ms = float(deadline_ms)

    def init_config(self) -> dict:
        return {"deadline_ms": self.deadline_ms}

    def init(self) -> None:
        self._miss_streak = 0
        self._miss_total = 0

    def reset(self) -> None:
        self._miss_streak = 0
        self._miss_total = 0

    def run(self, input: WorkReport) -> DeadlineStatus:
        if input.step_idx is None or input.t_sim is None or input.work_ms is None:
            return DeadlineStatus()

        missed = float(input.work_ms) > self.deadline_ms
        if missed:
            self._miss_total += 1
            self._miss_streak += 1
        else:
            self._miss_streak = 0

        return DeadlineStatus(
            step_idx=input.step_idx,
            t_sim=input.t_sim,
            deadline_ms=self.deadline_ms,
            work_ms=input.work_ms,
            missed=missed,
            miss_streak=self._miss_streak,
            miss_total=self._miss_total,
        )


class ModeManager(Flow[DeadlineStatus, ModeState]):
    """
    Hybrid policy:
    - Enter SAFE when miss streak reaches threshold.
    - Return to NOMINAL after enough consecutive healthy frames.
    """

    def __init__(self, *, miss_streak_limit: int, recover_ok_streak: int):
        super().__init__()
        self.miss_streak_limit = max(1, int(miss_streak_limit))
        self.recover_ok_streak = max(1, int(recover_ok_streak))

    def init_config(self) -> dict:
        return {
            "miss_streak_limit": self.miss_streak_limit,
            "recover_ok_streak": self.recover_ok_streak,
        }

    def init(self) -> None:
        self._mode = "NOMINAL"
        self._ok_streak = 0

    def reset(self) -> None:
        self._mode = "NOMINAL"
        self._ok_streak = 0

    def run(self, input: DeadlineStatus) -> ModeState:
        if input.step_idx is None or input.t_sim is None:
            return ModeState()

        missed = bool(input.missed)
        miss_streak = int(input.miss_streak or 0)
        miss_total = int(input.miss_total or 0)
        reason = "steady_state"

        if missed:
            self._ok_streak = 0
        else:
            self._ok_streak += 1

        if self._mode == "NOMINAL" and miss_streak >= self.miss_streak_limit:
            self._mode = "SAFE"
            reason = "deadline_miss_streak"
        elif self._mode == "SAFE" and self._ok_streak >= self.recover_ok_streak:
            self._mode = "NOMINAL"
            reason = "deadline_recovered"

        return ModeState(
            step_idx=input.step_idx,
            t_sim=input.t_sim,
            mode=self._mode,
            reason=reason,
            miss_total=miss_total,
        )


class ActionPolicy(Flow[ModeState, ControlAction]):
    def run(self, input: ModeState) -> ControlAction:
        if input.step_idx is None or input.t_sim is None or input.mode is None:
            return ControlAction()

        action = "hold_nominal_profile" if input.mode == "NOMINAL" else "degrade_to_safe_profile"
        return ControlAction(
            step_idx=input.step_idx,
            t_sim=input.t_sim,
            action=action,
            mode=input.mode,
        )


class ActionPrinter(Flow[ControlAction, None]):
    def run(self, input: ControlAction) -> None:
        if input.step_idx is None or input.t_sim is None or input.action is None or input.mode is None:
            return None
        print(
            f"[deadline] step={input.step_idx:02d} t={input.t_sim:4.2f}s "
            f"mode={input.mode:7s} action={input.action}"
        )
        return None


def build_pipeline(
    *,
    dt: float,
    base_ms: float,
    heavy_ms: float,
    heavy_every: int,
    deadline_ms: float,
    miss_streak_limit: int,
    recover_ok_streak: int,
) -> tuple[Pipeline, dict[str, object]]:
    pipe = Pipeline("tut035_deadline_mode_switch")

    tick = TickSource(dt=dt) @ Rate(hz=1.0 / max(dt, 1e-6))
    workload = SyntheticWorkload(
        base_ms=base_ms, heavy_ms=heavy_ms, heavy_every=heavy_every
    ) @ Trigger("step_idx")
    monitor = DeadlineMonitor(deadline_ms=deadline_ms) @ Trigger("work_ms")
    manager = ModeManager(
        miss_streak_limit=miss_streak_limit, recover_ok_streak=recover_ok_streak
    ) @ Trigger("miss_total")
    policy = ActionPolicy() @ Trigger("mode")
    sink = ActionPrinter() @ Trigger("action")

    pipe.connect(tick, workload, sync=Latest())
    pipe.connect(workload, monitor, sync=Latest())
    pipe.connect(monitor, manager, sync=Latest())
    pipe.connect(manager, policy, sync=Latest())
    pipe.connect(policy, sink, sync=Latest())

    return pipe, {"monitor": monitor, "manager": manager}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Deadline-aware mode switching tutorial.")
    p.add_argument("--steps", type=int, default=16, help="Stepper iterations.")
    p.add_argument("--dt", type=float, default=0.1, help="Logical dt per step.")
    p.add_argument("--base-ms", type=float, default=2.0, help="Nominal work time per frame.")
    p.add_argument("--heavy-ms", type=float, default=14.0, help="Heavy frame work time.")
    p.add_argument("--heavy-every", type=int, default=4, help="Every Nth frame is heavy.")
    p.add_argument("--deadline-ms", type=float, default=8.0, help="Per-frame deadline.")
    p.add_argument("--miss-streak-limit", type=int, default=1, help="SAFE enter threshold.")
    p.add_argument("--recover-ok-streak", type=int, default=3, help="SAFE exit threshold.")
    p.add_argument(
        "--out",
        type=Path,
        default=Path("logs/tutorial_deadline/tut035_deadline_mode_switch.json"),
        help="Output summary JSON path.",
    )
    return p.parse_args()


def main() -> None:
    args = parse_args()
    pipe, handles = build_pipeline(
        dt=args.dt,
        base_ms=args.base_ms,
        heavy_ms=args.heavy_ms,
        heavy_every=args.heavy_every,
        deadline_ms=args.deadline_ms,
        miss_streak_limit=args.miss_streak_limit,
        recover_ok_streak=args.recover_ok_streak,
    )

    monitor_id = pipe.get_node_id(handles["monitor"])  # type: ignore[arg-type]
    manager_id = pipe.get_node_id(handles["manager"])  # type: ignore[arg-type]

    timeline_rows: list[list[str]] = []
    transitions: list[ModeTransition] = []
    last_mode: str | None = None
    last_total = 0

    try:
        for _ in range(args.steps):
            result = pipe.step(dt=args.dt)

            mon = result.outputs.get(monitor_id)
            mgr = result.outputs.get(manager_id)
            if mon is None or mgr is None:
                continue
            if (
                getattr(mon, "step_idx", None) is None
                or getattr(mon, "work_ms", None) is None
                or getattr(mon, "missed", None) is None
                or getattr(mon, "miss_streak", None) is None
                or getattr(mon, "miss_total", None) is None
                or getattr(mgr, "mode", None) is None
                or getattr(mgr, "reason", None) is None
            ):
                continue

            step_idx = int(mon.step_idx)
            mode = str(mgr.mode)
            reason = str(mgr.reason)
            miss_total = int(mon.miss_total)
            last_total = miss_total

            timeline_rows.append(
                [
                    str(step_idx),
                    f"{float(mon.work_ms):.1f}",
                    "yes" if bool(mon.missed) else "no",
                    str(int(mon.miss_streak)),
                    str(miss_total),
                    mode,
                    reason,
                ]
            )

            if mode != last_mode:
                t_sim = float(getattr(mgr, "t_sim", 0.0) or 0.0)
                transitions.append(
                    ModeTransition(
                        step_idx=step_idx,
                        t_sim=t_sim,
                        mode=mode,
                        reason=reason,
                        miss_total=miss_total,
                    )
                )
                last_mode = mode
    finally:
        pipe.close_stepper()

    print("\n=== Deadline Timeline ===")
    print(
        format_table(
            ["step", "work_ms", "missed", "miss_streak", "miss_total", "mode", "reason"],
            timeline_rows,
        )
    )

    summary = {
        "schema_version": "retriever.deadline_mode_switch.v1",
        "created_at": utc_now_iso(),
        "config": {
            "steps": args.steps,
            "dt": args.dt,
            "base_ms": args.base_ms,
            "heavy_ms": args.heavy_ms,
            "heavy_every": args.heavy_every,
            "deadline_ms": args.deadline_ms,
            "miss_streak_limit": args.miss_streak_limit,
            "recover_ok_streak": args.recover_ok_streak,
        },
        "miss_total": last_total,
        "transition_count": len(transitions),
        "transitions": [asdict(t) for t in transitions],
    }
    write_json(args.out, summary)
    print(f"\n[Artifacts] summary={args.out}")


if __name__ == "__main__":
    main()
