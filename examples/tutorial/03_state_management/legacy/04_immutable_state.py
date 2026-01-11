"""
Immutable state (pure state transitions).

Run:
  pixi run python -m examples.tutorial.03_state_management.04_immutable_state
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RobotState:
    x: float = 0.0
    battery: float = 1.0

    def status(self) -> str:
        return f"Robot(x={self.x:.1f}, battery={self.battery:.1f})"


def move_forward(state: RobotState, distance: float) -> RobotState:
    new_x = state.x + distance
    new_battery = max(0.0, state.battery - 0.1)
    return RobotState(x=new_x, battery=new_battery)


def charge_battery(state: RobotState, amount: float) -> RobotState:
    new_battery = min(1.0, state.battery + amount)
    return RobotState(x=state.x, battery=new_battery)


def demo_immutable_state() -> None:
    print("=== Immutable State ===")
    initial = RobotState()
    print("Start:", initial.status())

    s1 = move_forward(initial, 1.0)
    s2 = move_forward(s1, 0.5)
    print("After move 1:", s1.status())
    print("After move 2:", s2.status())
    print("Original:", initial.status())


def demo_benefits() -> None:
    print("\n=== Benefits ===")
    initial = RobotState(x=2.0, battery=0.8)
    chained = charge_battery(move_forward(initial, 1.0), 0.1)
    print("Chained:", chained.status())

    saved = [initial]
    state = initial
    for _ in range(3):
        state = move_forward(state, 1.0)
        saved.append(state)
    print("Saved step 1:", saved[1].status())


def main() -> None:
    demo_immutable_state()
    demo_benefits()
    print("\nNext: 05_eff_composition.py")


if __name__ == "__main__":
    main()
