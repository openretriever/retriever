"""
Placement Rules - Strategies for grouping IR nodes into execution partitions.

This module defines:
1. `PlacementRule`: Base class for compatibility checks.
2. Built-in rules: Clock, Rate, Adapter, and Topology checks.
3. Standard Policies: Conservative, Aggressive, and Strict fusion policies.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Set, Tuple, Union, TYPE_CHECKING
from abc import ABC, abstractmethod
from dataclasses import dataclass
import logging

if TYPE_CHECKING:
    from retriever.ir.core import IR, IRAnalysis

logger = logging.getLogger(__name__)


# ==============================================================================
# Base Classes
# ==============================================================================

class PlacementRule(ABC):
    """
    Base class for placement rules.

    A rule checks if two nodes can be grouped/co-located together based on
    specific criteria (clock compatibility, adapter type, topology, etc.)
    """

    name: str = "base_rule"
    description: str = "Base placement rule"
    category: str = "general"

    @abstractmethod
    def check(self, ir: IR, node_a: str, node_b: str,
              analysis: IRAnalysis) -> bool:
        """
        Check if two nodes can be grouped/co-located.

        Args:
            ir: IR graph
            node_a: First node ID
            node_b: Second node ID
            analysis: Analysis results

        Returns:
            True if nodes can be fused/co-located, False otherwise
        """
        raise NotImplementedError

    def __call__(self, ir: IR, node_a: str, node_b: str,
                 analysis: IRAnalysis) -> bool:
        """Allow rule to be called like a function"""
        return self.check(ir, node_a, node_b, analysis)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name='{self.name}')"


# ==============================================================================
# Rule Registry
# ==============================================================================

class RuleRegistry:
    """Registry for managing placement rules."""

    def __init__(self):
        self._rules: Dict[str, PlacementRule] = {}

    def register(self, rule: PlacementRule) -> None:
        if rule.name in self._rules:
            raise ValueError(f"Rule '{rule.name}' already registered")
        self._rules[rule.name] = rule

    def get(self, name: str) -> PlacementRule:
        if name not in self._rules:
            raise KeyError(f"Rule '{name}' not found. Available: {list(self._rules.keys())}")
        return self._rules[name]

    def list_all(self, category: Optional[str] = None) -> List[PlacementRule]:
        if category:
            return [p for p in self._rules.values() if p.category == category]
        return list(self._rules.values())


_registry = RuleRegistry()


def register_rule(rule: Union[PlacementRule, type]) -> PlacementRule:
    """Register a placement rule."""
    if isinstance(rule, type):
        rule = rule()  # type: ignore
    _registry.register(rule)
    return rule


@dataclass
class RuleConfig:
    """Configuration for placement rules."""
    name: str = "aggressive"
    # Future: allow customizing specific rules or parameters
    
    @classmethod
    def from_preset(cls, name: str) -> "RuleConfig":
        return cls(name=name)

def get_placement_rule(config: RuleConfig) -> PlacementRule:
    """Get placement rule from config."""
    if config.name == "aggressive":
        return aggressive_fusion_rule()
    elif config.name == "conservative":
        return conservative_fusion_rule()
    elif config.name == "strict":
        return strict_fusion_rule()
    else:
        # Fallback: try to look up by name directly
        try:
            return get_rule(config.name)
        except KeyError:
            raise ValueError(f"Unknown placement policy: {config.name}")

def get_rule(name: str) -> PlacementRule:
    """Get rule by name."""
    return _registry.get(name)


# ==============================================================================
# Core Built-in Rules
# ==============================================================================

class SameExplicitClockRule(PlacementRule):
    """Check if two nodes have the same explicit clock type and parameters"""
    name = "same_explicit_clock"
    description = "Nodes have identical clock configurations"
    category = "clock"

    def check(self, ir: IR, node_a: str, node_b: str, analysis: IRAnalysis) -> bool:
        if analysis.clock_types.get(node_a) != analysis.clock_types.get(node_b):
            return False
        node_a_obj = ir.get_node(node_a)
        node_b_obj = ir.get_node(node_b)
        if node_a_obj is None or node_b_obj is None:
            return False
        clock_a = node_a_obj.config.get('clock', {})
        clock_b = node_b_obj.config.get('clock', {})
        return clock_a == clock_b


class SameEffectiveRateRule(PlacementRule):
    """Check if two nodes have the same effective rate (with rate tracking)"""
    name = "same_effective_rate"
    description = "Nodes have same effective execution rate (uses rate tracking)"
    category = "clock"

    def check(self, ir: IR, node_a: str, node_b: str, analysis: IRAnalysis) -> bool:
        rate_a = analysis.effective_rates.get(node_a)
        rate_b = analysis.effective_rates.get(node_b)
        if rate_a is None or rate_b is None:
            return False
        return rate_a == rate_b


class LatestAdapterRule(PlacementRule):
    """Check if edge between nodes uses Latest adapter"""
    name = "latest_adapter"
    description = "Edge uses Latest adapter"
    category = "adapter"

    def check(self, ir: IR, node_a: str, node_b: str, analysis: IRAnalysis) -> bool:
        adapter = analysis.adapter_types.get((node_a, node_b))
        return adapter is not None and adapter.lower() == 'latest'


class LinearChainRule(PlacementRule):
    """Check if nodes form a linear chain (1 successor, 1 predecessor)"""
    name = "linear_chain"
    description = "Nodes form linear chain (1-to-1 connection)"
    category = "topology"

    def check(self, ir: IR, node_a: str, node_b: str, analysis: IRAnalysis) -> bool:
        node_a_obj = ir.get_node(node_a)
        node_b_obj = ir.get_node(node_b)
        if node_a_obj is None or node_b_obj is None:
            return False
        if len(node_a_obj.successors) != 1 or node_a_obj.successors[0] != node_b:
            return False
        if len(node_b_obj.predecessors) != 1 or node_b_obj.predecessors[0] != node_a:
            return False
        return True


class CompatibleResourceRule(PlacementRule):
    """Check if resource constraints are compatible"""
    name = "compatible_resource"
    description = "Resource constraints are compatible"
    category = "config"

    def check(self, ir: IR, node_a: str, node_b: str, analysis: IRAnalysis) -> bool:
        node_a_obj = ir.get_node(node_a)
        node_b_obj = ir.get_node(node_b)
        if node_a_obj is None or node_b_obj is None:
            return False
        
        priority_a = node_a_obj.config.get('priority')
        priority_b = node_b_obj.config.get('priority')
        if priority_a is not None and priority_b is not None and priority_a != priority_b:
            return False

        affinity_a = node_a_obj.config.get('cpu_affinity')
        affinity_b = node_b_obj.config.get('cpu_affinity')
        if affinity_a is not None and affinity_b is not None:
            if not (set(affinity_a) & set(affinity_b)):
                return False
        return True


class NotInCycleRule(PlacementRule):
    """Check if nodes are not in cycles"""
    name = "not_in_cycle"
    description = "Nodes are not in cycles"
    category = "topology"

    def check(self, ir: IR, node_a: str, node_b: str, analysis: IRAnalysis) -> bool:
        return not (analysis.in_cycle.get(node_a, False) or analysis.in_cycle.get(node_b, False))


class NoServiceRule(PlacementRule):
    """Check if nodes have no service handlers or callers"""
    name = "no_service"
    description = "Nodes have no service handlers or callers"
    category = "service"

    def check(self, ir: IR, node_a: str, node_b: str, analysis: IRAnalysis) -> bool:
        node_a_obj = ir.get_node(node_a)
        node_b_obj = ir.get_node(node_b)
        if node_a_obj is None or node_b_obj is None:
            return False
        if node_a_obj.service_handlers or node_b_obj.service_handlers:
            return False
        if node_a_obj.service_callers or node_b_obj.service_callers:
            return False
        return True


# Rule Combinators
class AndRule(PlacementRule):
    def __init__(self, *rules: PlacementRule):
        self.rules = rules
        names = [p.name for p in rules]
        self.name = f"and({', '.join(names)})"
        self.category = "combinator"

    def check(self, ir: IR, node_a: str, node_b: str, analysis: IRAnalysis) -> bool:
        for rule in self.rules:
            if not rule.check(ir, node_a, node_b, analysis):
                return False
        return True


def make_and(*rules: PlacementRule) -> AndRule:
    return AndRule(*rules)


# Auto-register
register_rule(SameExplicitClockRule())
register_rule(SameEffectiveRateRule())
register_rule(LatestAdapterRule())
register_rule(LinearChainRule())
register_rule(CompatibleResourceRule())
register_rule(NotInCycleRule())
register_rule(NoServiceRule())


# Standard Policies
def conservative_fusion_rule() -> PlacementRule:
    return make_and(
        get_rule('linear_chain'),
        get_rule('not_in_cycle'),
        get_rule('no_service'),
        get_rule('same_explicit_clock'),
        get_rule('latest_adapter')
    )


def aggressive_fusion_rule() -> PlacementRule:
    return make_and(
        get_rule('linear_chain'),
        get_rule('not_in_cycle'),
        get_rule('no_service'),
        get_rule('same_effective_rate'),
        get_rule('latest_adapter')
    )


def strict_fusion_rule() -> PlacementRule:
    return make_and(
        get_rule('linear_chain'),
        get_rule('not_in_cycle'),
        get_rule('no_service'),
        get_rule('same_effective_rate'),
        get_rule('latest_adapter'),
        get_rule('compatible_resource')
    )
