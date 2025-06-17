"""
Tests for Effectful Execution - Robotics State Management Examples

These tests demonstrate how to use the Eff monad and effectful execution
for robotics applications that need to track and update state. This is
essential for:

- Robot pose and joint state tracking
- World belief state management  
- Battery and resource monitoring
- Action history and logging
- Multi-robot coordination

The Eff monad provides a clean way to thread state through computations
without manually passing state parameters everywhere.
"""

from dataclasses import dataclass, replace
from typing import Dict, List, Tuple

import pytest

from retriever.core.flow import Flow, Arrow  # Flow is new, Arrow for backward compatibility
from retriever.core.executor import LocalExecutor
from retriever.core.types import Eff, pure


# ========================= Robotics State Examples =========================

@dataclass
class RobotState:
    """Complete robot state for a mobile manipulator."""
    base_x: float
    base_y: float
    base_theta: float
    arm_joints: List[float]
    gripper_open: bool
    battery_level: float
    objects_held: List[str]

    def move_base(self, dx: float, dy: float, dtheta: float) -> 'RobotState':
        """Return new state after base movement."""
        return replace(
            self,
            base_x=self.base_x + dx,
            base_y=self.base_y + dy, 
            base_theta=self.base_theta + dtheta,
            battery_level=max(0, self.battery_level - 0.1)  # Movement uses battery
        )

    def pick_object(self, object_id: str) -> 'RobotState':
        """Return new state after picking up an object."""
        return replace(
            self,
            gripper_open=False,
            objects_held=self.objects_held + [object_id],
            battery_level=max(0, self.battery_level - 0.05)  # Manipulation uses battery
        )

    def drop_object(self, object_id: str) -> 'RobotState':
        """Return new state after dropping an object."""
        new_objects = [obj for obj in self.objects_held if obj != object_id]
        return replace(
            self,
            gripper_open=True,
            objects_held=new_objects
        )


@dataclass 
class WorldState:
    """World belief state - where objects are located."""
    object_locations: Dict[str, Tuple[float, float]]  # object_id -> (x, y)
    explored_areas: List[Tuple[float, float]]  # areas the robot has seen


# ========================= Effectful Robot Operations =========================

def move_robot_eff(dx: float, dy: float, dtheta: float) -> Eff[RobotState, bool]:
    """
    Effectful robot movement that updates the robot's state.
    
    In a real system, this would send commands to the robot controller
    and update the state based on actual movement.
    """
    def run(state: RobotState) -> Tuple[bool, RobotState]:
        # Simulate movement success/failure based on battery
        success = state.battery_level > 0.1
        new_state = state.move_base(dx, dy, dtheta) if success else state
        return success, new_state
    
    return Eff(run)


def pick_object_eff(object_id: str) -> Eff[RobotState, bool]:
    """
    Effectful object picking that updates robot state.
    
    In a real system, this would control the arm and gripper.
    """
    def run(state: RobotState) -> Tuple[bool, RobotState]:
        # Can only pick if gripper is open and has battery
        can_pick = state.gripper_open and state.battery_level > 0.05
        success = can_pick and len(state.objects_held) < 2  # Max 2 objects
        new_state = state.pick_object(object_id) if success else state
        return success, new_state
    
    return Eff(run)


def scan_area_eff(x: float, y: float) -> Eff[Tuple[RobotState, WorldState], List[str]]:
    """
    Effectful area scanning that updates both robot and world state.
    
    This simulates the robot exploring an area and updating its world model.
    """
    def run(state_pair: Tuple[RobotState, WorldState]) -> Tuple[List[str], Tuple[RobotState, WorldState]]:
        robot_state, world_state = state_pair
        
        # Simulate finding objects in the scanned area
        found_objects = ["cup", "bottle"] if x > 0 else ["book"]
        
        # Update world state with newly explored area
        new_explored = world_state.explored_areas + [(x, y)]
        new_object_locations = world_state.object_locations.copy()
        for i, obj in enumerate(found_objects):
            new_object_locations[f"{obj}_{x}_{y}"] = (x + i * 0.1, y)
        
        new_world_state = WorldState(new_object_locations, new_explored)
        
        # Update robot state (scanning uses battery)
        new_robot_state = replace(robot_state, battery_level=max(0, robot_state.battery_level - 0.02))
        
        return found_objects, (new_robot_state, new_world_state)
    
    return Eff(run)


# ========================= Robotics Effectful Tests =========================

def test_robot_movement_with_state():
    """
    Test: Basic robot movement with state tracking
    
    Shows how effectful operations automatically handle state updates.
    The robot's position and battery level are tracked through the operation.
    """
    executor = LocalExecutor()
    
    # Create a simple movement flow (new preferred syntax)
    move_flow = Flow.from_module(lambda _: move_robot_eff(1.0, 0.5, 0.1))
    
    initial_state = RobotState(
        base_x=0.0, base_y=0.0, base_theta=0.0,
        arm_joints=[0.0, 0.0, 0.0], gripper_open=True,
        battery_level=1.0, objects_held=[]
    )
    
    # Execute movement
    success, final_state = executor.run_eff(move_flow, None, initial_state)
    
    # Verify movement succeeded and state was updated
    assert success is True
    assert final_state.base_x == 1.0
    assert final_state.base_y == 0.5
    assert final_state.base_theta == 0.1
    assert final_state.battery_level == 0.9  # Battery decreased


def test_sequential_robot_actions():
    """
    Test: Sequential robot actions with state threading
    
    Shows how multiple robot actions can be chained, with state automatically
    threaded through each operation. Common pattern: move → scan → pick.
    """
    executor = LocalExecutor()
    
    # Chain of robot actions: move then pick (using Flow)
    move_then_pick = (
        Flow.from_module(lambda _: move_robot_eff(1.0, 0.0, 0.0))
        .then(Flow.from_module(lambda _: pick_object_eff("target_cup")))
    )
    
    initial_state = RobotState(
        base_x=0.0, base_y=0.0, base_theta=0.0,
        arm_joints=[0.0, 0.0, 0.0], gripper_open=True,
        battery_level=1.0, objects_held=[]
    )
    
    # Execute the sequence
    success, final_state = executor.run_eff(move_then_pick, None, initial_state)
    
    # Verify both actions succeeded and state reflects both operations
    assert success is True
    assert final_state.base_x == 1.0  # Moved
    assert not final_state.gripper_open  # Picked object
    assert "target_cup" in final_state.objects_held
    assert final_state.battery_level == 0.85  # Battery used for both operations


def test_robot_exploration_with_world_state():
    """
    Test: Robot exploration updating world belief state
    
    Shows how to manage complex state (robot + world) through exploration.
    The robot scans areas and builds a map of discovered objects.
    """
    executor = LocalExecutor()
    
    # Exploration flow that scans an area
    explore_flow = Flow.from_module(lambda _: scan_area_eff(2.0, 1.0))
    
    initial_robot = RobotState(
        base_x=0.0, base_y=0.0, base_theta=0.0,
        arm_joints=[0.0, 0.0, 0.0], gripper_open=True,
        battery_level=1.0, objects_held=[]
    )
    
    initial_world = WorldState(object_locations={}, explored_areas=[])
    combined_state = (initial_robot, initial_world)
    
    # Execute exploration
    found_objects, (final_robot, final_world) = executor.run_eff(
        explore_flow, None, combined_state
    )
    
    # Verify exploration results
    assert len(found_objects) == 2  # Found cup and bottle
    assert len(final_world.explored_areas) == 1  # One area explored
    assert len(final_world.object_locations) == 2  # Two objects mapped
    assert final_robot.battery_level < 1.0  # Battery used for scanning


def test_complex_robot_mission():
    """
    Test: Complex multi-stage robot mission
    
    Demonstrates a realistic robotics scenario:
    1. Move to search area
    2. Scan for objects
    3. Pick up discovered objects
    4. Move to delivery location
    
    Shows how complex state flows through multi-stage operations.
    """
    executor = LocalExecutor()
    
    # Simplified mission: just move then scan
    def simple_mission(_) -> Eff[Tuple[RobotState, WorldState], str]:
        # Move to search area
        def move_combined(state_pair):
            robot_state, world_state = state_pair
            move_eff = move_robot_eff(2.0, 1.0, 0.0)
            success, new_robot = move_eff.run(robot_state)
            return success, (new_robot, world_state)
        
        move_eff = Eff(move_combined)
        
        # Then scan the area
        def scan_then_report(success):
            if success:
                return scan_area_eff(2.0, 1.0) >> (lambda found: pure("Mission completed"))  # type: ignore
            else:
                return pure("Mission failed - movement failed")
        
        return move_eff >> scan_then_report  # type: ignore
    
    mission_arrow = Arrow.arr(simple_mission)
    
    initial_robot = RobotState(
        base_x=0.0, base_y=0.0, base_theta=0.0,
        arm_joints=[0.0, 0.0, 0.0], gripper_open=True,
        battery_level=1.0, objects_held=[]
    )
    
    initial_world = WorldState(object_locations={}, explored_areas=[])
    combined_state = (initial_robot, initial_world)
    
    # Execute the mission
    result, (final_robot, final_world) = executor.execute_eff(
        mission_arrow, None, combined_state
    )
    
    # Verify mission success
    assert result == "Mission completed"
    assert final_robot.base_x == 2.0  # Moved to target
    assert len(final_world.object_locations) >= 1  # Objects discovered
    assert final_robot.battery_level < 1.0  # Battery used


def test_battery_constraint_handling():
    """
    Test: Robot operations respect battery constraints
    
    Shows how effectful operations can enforce physical constraints
    like battery levels, joint limits, etc.
    """
    executor = LocalExecutor()
    
    # Try to move with low battery
    move_arrow = Arrow.arr(lambda _: move_robot_eff(5.0, 5.0, 1.0))
    
    low_battery_state = RobotState(
        base_x=0.0, base_y=0.0, base_theta=0.0,
        arm_joints=[0.0, 0.0, 0.0], gripper_open=True,
        battery_level=0.05,  # Very low battery
        objects_held=[]
    )
    
    # Execute movement with insufficient battery
    success, final_state = executor.execute_eff(move_arrow, None, low_battery_state)
    
    # Movement should fail due to low battery
    assert success is False
    assert final_state.base_x == 0.0  # Robot didn't move
    assert final_state.battery_level == 0.05  # Battery unchanged


# ========================= Original Simple Tests =========================
# Keep original tests for backward compatibility

@dataclass
class CounterState:
    """A simple state object for testing."""
    value: int


def increment(s: CounterState) -> tuple[None, CounterState]:
    """An effectful function that increments the state."""
    return (None, CounterState(s.value + 1))


def get_value(s: CounterState) -> tuple[int, CounterState]:
    """An effectful function that gets a value from the state."""
    return (s.value, s)


def add_to_state(x: int) -> Eff[CounterState, None]:
    """Returns an Eff that adds x to the state."""
    def run(s: CounterState) -> tuple[None, CounterState]:
        return (None, CounterState(s.value + x))
    return Eff(run)


def test_simple_effectful_arrow():
    """Tests a single effectful arrow."""
    executor = LocalExecutor()
    arrow = Arrow.arr(lambda _: Eff(increment))
    initial_state = CounterState(10)

    _, final_state = executor.execute_eff(arrow, None, initial_state)
    assert final_state.value == 11


def test_effectful_then_composition():
    """Tests sequential composition with effects."""
    executor = LocalExecutor()
    # First, increment the state. Then, get the new value.
    arrow = Arrow.arr(lambda _: Eff(increment)).then(Arrow.arr(lambda _: Eff(get_value)))
    initial_state = CounterState(10)

    result, final_state = executor.execute_eff(arrow, None, initial_state)
    # The result should be the value *after* incrementing.
    assert result == 11
    assert final_state.value == 11


def test_effectful_fanout_composition():
    """Tests parallel composition with effects, ensuring state is threaded correctly."""
    executor = LocalExecutor()

    # Left branch adds 5, right branch adds 10.
    # The input to both is a pure value (1), which they ignore.
    arrow = Arrow.arr(lambda _: add_to_state(5)).fanout(
        Arrow.arr(lambda _: add_to_state(10))
    )
    initial_state = CounterState(100)

    # State is threaded from left to right.
    # 1. Start with state = 100.
    # 2. Left branch runs: add_to_state(5). New state = 105. Result is None.
    # 3. Right branch runs with the *new* state: add_to_state(10). New state = 115. Result is None.
    # 4. Final result is (None, None), final state is 115.
    result, final_state = executor.execute_eff(arrow, 1, initial_state)

    assert result == (None, None)
    assert final_state.value == 115 