"""
Tutorial: Symbolic Planning Types

Demonstrates the PDDL-style symbolic types for task and motion planning.
These symbolic types are part of the core `retriever.types` surface.

Components:
- ObjectType: Define object types with inheritance
- Object/Variable: Concrete vs lifted entities
- Predicate: State classifiers
- GroundAtom: Predicates with bound objects
- SkillSignature/GroundedSkill: LLM planner interface
"""

import numpy as np
from retriever.types.symbolic import (
    ObjectType, Object, Variable, Predicate, State, GroundAtom, LiftedAtom
)
from retriever.types.symbolic.skills import SkillSignature, GroundedSkill


def main():
    print("=" * 60)
    print("Part 1: ObjectType Hierarchy")
    print("=" * 60)
    
    # Define a type hierarchy
    thing = ObjectType("thing")
    container = ObjectType("container", parent=thing)
    cup = ObjectType("cup", parent=container)
    table = ObjectType("table", parent=thing)
    
    print(f"cup inherits from: {[t.name for t in cup.get_ancestors()]}")
    
    # Create objects
    red_cup = cup("red_cup_0")
    blue_cup = cup("blue_cup_1")
    kitchen_table = table("kitchen_table")
    
    print(f"\nObjects: {red_cup}, {blue_cup}, {kitchen_table}")
    
    # Create variables (for lifted predicates)
    var_x = cup("?x")
    var_y = table("?y")
    print(f"Variables: {var_x}, {var_y}")
    
    print("\n" + "=" * 60)
    print("Part 2: Predicates and Atoms")
    print("=" * 60)
    
    # Define predicate "on(cup, table)"
    on_predicate = Predicate(
        name="on",
        types=[cup, table],
        _classifier=lambda state, objs: True  # Simplified
    )
    
    # Create ground atom
    on_red_cup_table = on_predicate([red_cup, kitchen_table])
    print(f"Ground atom: {on_red_cup_table}")
    print(f"Is GroundAtom: {isinstance(on_red_cup_table, GroundAtom)}")
    
    # Create lifted atom (with variables)
    on_x_y = on_predicate([var_x, var_y])
    print(f"Lifted atom: {on_x_y}")
    print(f"Is LiftedAtom: {isinstance(on_x_y, LiftedAtom)}")
    
    print("\n" + "=" * 60)
    print("Part 3: State and Predicate Evaluation")
    print("=" * 60)
    
    # Define type with features
    obj_type = ObjectType("object", feature_names=["x", "y", "z"])
    
    # Define predicate that checks if object is at origin
    at_origin = Predicate(
        name="at_origin",
        types=[obj_type],
        _classifier=lambda state, objs: np.allclose(state[objs[0]], [0, 0, 0])
    )
    
    # Create objects with positions
    obj_a = obj_type("obj_a")
    obj_b = obj_type("obj_b")
    
    state = State(data={
        obj_a: np.array([0.0, 0.0, 0.0]),
        obj_b: np.array([1.0, 2.0, 3.0])
    })
    
    print(f"at_origin(obj_a) = {at_origin.holds(state, [obj_a])}")
    print(f"at_origin(obj_b) = {at_origin.holds(state, [obj_b])}")
    
    print("\n" + "=" * 60)
    print("Part 4: LLM Skill Interface")
    print("=" * 60)
    
    # Define skill signatures for LLM planner
    pick_skill = SkillSignature(
        name="pick",
        template="pick up {object}"
    )
    
    place_skill = SkillSignature(
        name="place",
        template="place {object} on {destination}"
    )
    
    print(f"pick skill: {pick_skill}")
    print(f"  parameters: {pick_skill.parameters}")
    print(f"place skill: {place_skill}")
    print(f"  parameters: {place_skill.parameters}")
    
    # Ground a skill with concrete object IDs
    grounded = GroundedSkill(
        signature=place_skill,
        grounded_params={"object": "red_cup_0", "destination": "kitchen_table"}
    )
    print(f"\nGrounded skill: {grounded}")
    
    # Validate grounding against perception
    perceived = {"red_cup_0": "cup", "kitchen_table": "table"}
    grounded.validate_grounding(perceived)
    print("Validation passed!")
    
    print("\n" + "=" * 60)
    print("Summary:")
    print("  - ObjectType: Define object categories with inheritance")
    print("  - Object: Concrete instances (no ? prefix)")
    print("  - Variable: Placeholders for lifted (? prefix)")
    print("  - Predicate: State -> bool classifiers")
    print("  - SkillSignature: NL templates for LLM planners")
    print("  - GroundedSkill: Executable skill with bound objects")
    print("=" * 60)


if __name__ == "__main__":
    main()
