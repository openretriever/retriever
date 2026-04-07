"""
Operator mode and authority FSM tutorial.

Covers:
1) Autonomy/shared/teleop semantics
2) Enforced valid transition sequence
3) Intervention interval markers in output logs

Run:
  pixi run python -m examples.tutorial.d_closed_loop_state_feedback.03_operator_mode_and_authority_fsm
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
from enum import Enum
from pathlib import Path

from examples.tutorial._p0_utils import format_table, utc_now_iso, write_json


class AuthorityMode(str, Enum):
    AUTONOMY = "autonomy"
    SHARED = "shared"
    TELEOP = "teleop"


class OperatorEvent(str, Enum):
    REQUEST_AUTONOMY = "request_autonomy"
    REQUEST_SHARED = "request_shared"
    REQUEST_TELEOP = "request_teleop"


@dataclass
class TransitionRecord:
    timestamp_s: float
    event: str
    from_mode: str
    to_mode: str
    allowed: bool
    reason: str
    marker: str | None


@dataclass
class InterventionInterval:
    start_s: float
    end_s: float
    duration_s: float


_ALLOWED_TRANSITIONS: dict[AuthorityMode, set[AuthorityMode]] = {
    AuthorityMode.AUTONOMY: {AuthorityMode.SHARED},
    AuthorityMode.SHARED: {AuthorityMode.AUTONOMY, AuthorityMode.TELEOP},
    AuthorityMode.TELEOP: {AuthorityMode.SHARED},
}


class AuthorityFSM:
    def __init__(self, initial_mode: AuthorityMode = AuthorityMode.AUTONOMY):
        self.mode = initial_mode

    def transition(self, *, target: AuthorityMode, event: OperatorEvent, timestamp_s: float) -> TransitionRecord:
        before = self.mode
        allowed = target in _ALLOWED_TRANSITIONS[before]
        marker: str | None = None

        if not allowed:
            return TransitionRecord(
                timestamp_s=timestamp_s,
                event=event.value,
                from_mode=before.value,
                to_mode=target.value,
                allowed=False,
                reason=f"blocked: {before.value} -> {target.value} is not allowed",
                marker=None,
            )

        self.mode = target

        if before == AuthorityMode.AUTONOMY and target != AuthorityMode.AUTONOMY:
            marker = "intervention_start"
        elif before != AuthorityMode.AUTONOMY and target == AuthorityMode.AUTONOMY:
            marker = "intervention_end"

        return TransitionRecord(
            timestamp_s=timestamp_s,
            event=event.value,
            from_mode=before.value,
            to_mode=target.value,
            allowed=True,
            reason="ok",
            marker=marker,
        )


def default_script() -> list[tuple[float, OperatorEvent, AuthorityMode]]:
    # Includes one intentionally invalid transition: autonomy -> teleop.
    return [
        (1.00, OperatorEvent.REQUEST_TELEOP, AuthorityMode.TELEOP),
        (1.80, OperatorEvent.REQUEST_SHARED, AuthorityMode.SHARED),
        (2.60, OperatorEvent.REQUEST_TELEOP, AuthorityMode.TELEOP),
        (3.80, OperatorEvent.REQUEST_SHARED, AuthorityMode.SHARED),
        (4.70, OperatorEvent.REQUEST_AUTONOMY, AuthorityMode.AUTONOMY),
    ]


def run_fsm(events: list[tuple[float, OperatorEvent, AuthorityMode]]) -> tuple[list[TransitionRecord], list[InterventionInterval]]:
    fsm = AuthorityFSM(initial_mode=AuthorityMode.AUTONOMY)
    records: list[TransitionRecord] = []
    intervals: list[InterventionInterval] = []

    current_start: float | None = None

    for timestamp_s, event, target in events:
        record = fsm.transition(target=target, event=event, timestamp_s=timestamp_s)
        records.append(record)

        if record.marker == "intervention_start":
            current_start = timestamp_s
        elif record.marker == "intervention_end" and current_start is not None:
            intervals.append(
                InterventionInterval(
                    start_s=current_start,
                    end_s=timestamp_s,
                    duration_s=round(timestamp_s - current_start, 3),
                )
            )
            current_start = None

    if current_start is not None:
        end_s = events[-1][0]
        intervals.append(
            InterventionInterval(
                start_s=current_start,
                end_s=end_s,
                duration_s=round(end_s - current_start, 3),
            )
        )

    return records, intervals


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Authority transition FSM with intervention markers.")
    p.add_argument(
        "--out",
        type=Path,
        default=Path("logs/tutorial_authority/tut028_authority_log.json"),
        help="Output JSON transition log.",
    )
    return p.parse_args()


def main() -> None:
    args = parse_args()

    records, intervals = run_fsm(default_script())
    blocked = [r for r in records if not r.allowed]

    print("\n=== Authority Transition Log ===")
    rows = [
        [
            f"{r.timestamp_s:.2f}",
            r.event,
            r.from_mode,
            r.to_mode,
            "yes" if r.allowed else "no",
            r.marker or "-",
            r.reason,
        ]
        for r in records
    ]
    print(
        format_table(
            ["t_s", "event", "from", "to", "allowed", "marker", "reason"],
            rows,
        )
    )

    print("\n=== Intervention Intervals ===")
    if intervals:
        interval_rows = [[f"{it.start_s:.2f}", f"{it.end_s:.2f}", f"{it.duration_s:.2f}"] for it in intervals]
        print(format_table(["start_s", "end_s", "duration_s"], interval_rows))
    else:
        print("No intervention intervals.")

    payload = {
        "schema_version": "retriever.authority_fsm.v1",
        "created_at": utc_now_iso(),
        "initial_mode": AuthorityMode.AUTONOMY.value,
        "transitions": [asdict(r) for r in records],
        "intervention_intervals": [asdict(it) for it in intervals],
        "blocked_transition_count": len(blocked),
    }
    write_json(args.out, payload)

    print(f"\n[Artifacts] log={args.out}")
    print(
        "[Note] This run intentionally includes one blocked transition "
        "(autonomy -> teleop) to demonstrate contract enforcement."
    )


if __name__ == "__main__":
    main()
