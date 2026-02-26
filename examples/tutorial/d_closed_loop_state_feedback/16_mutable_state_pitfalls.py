"""
State basics (mutable state pitfalls).

Run:
  pixi run python -m examples.tutorial.d_closed_loop_state_feedback.16_mutable_state_pitfalls
"""

from __future__ import annotations


class SimpleRobot:
    def __init__(self) -> None:
        self.x = 0.0
        self.battery = 1.0

    def move_forward(self, distance: float) -> None:
        self.x += distance
        self.battery -= 0.1

    def status(self) -> str:
        return f"Robot(x={self.x:.1f}, battery={self.battery:.1f})"


def demo_mutable_state() -> None:
    print("=== Mutable State ===")
    robot = SimpleRobot()
    print("Start:", robot.status())

    robot.move_forward(1.0)
    robot.move_forward(0.5)
    print("End:", robot.status())


def demo_hidden_changes() -> None:
    print("\n=== Hidden State Changes ===")
    robot = SimpleRobot()

    def move_twice(r: SimpleRobot) -> None:
        r.move_forward(1.0)
        r.move_forward(1.0)

    print("Before:", robot.status())
    move_twice(robot)
    print("After:", robot.status())
    print("Issue: state mutated inside helper (harder to test/undo).")


def main() -> None:
    demo_mutable_state()
    demo_hidden_changes()
    print("\nNext: 17_immutable_state_transitions.py")


if __name__ == "__main__":
    main()
