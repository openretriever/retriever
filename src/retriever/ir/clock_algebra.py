"""
Clock algebra for groups of Flows.

A finite group of Flows behaves as one Flow on a *covering clock*: the union of the
inner Rate, Tick and Hybrid clocks and the event times of the boundary inputs that the
inner Trigger, Synchronized and Hybrid clocks read. The covering clock may tick when no inner Flow runs; the group then emits no
event. This holds when the group has no same-instant cycle, that is, no cycle made only
of activation edges (an edge into a field that triggers its destination's clock).

This module describes these objects; it does not change execution. Backends still lower
a nested group into its inner Flows, each on its own clock.

    from retriever.ir.clock_algebra import covering_clock, same_instant_cycles

    cover = covering_clock(ir, boundary={"go": ("gate", "go")})
    cover.ticks(0.0, 0.1)        # union of the inner Rate ticks in [0, 0.1)
    same_instant_cycles(ir)      # [] when the group is admissible
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Mapping, Optional, Tuple

from retriever.ir.core import IR, IRNode

_RATE_TYPES = ("Rate", "Tick")
_TRIGGER_TYPES = ("Trigger", "Synchronized")


def _clock_of(node: IRNode) -> Tuple[Optional[str], Dict]:
    clock = node.config.get("clock")
    if not isinstance(clock, dict) or not clock:
        return None, {}
    ctype = next(iter(clock.keys()))
    params = clock[ctype]
    return ctype, dict(params) if isinstance(params, dict) else {}


def _trigger_fields(ctype: Optional[str], params: Mapping) -> List[str]:
    if ctype in _TRIGGER_TYPES:
        fields = list(params.get("fields") or [])
        fields.extend(params.get("on") or [])
        return [str(f) for f in fields]
    if ctype == "Hybrid":
        return [str(f) for f in (params.get("trigger_fields") or [])]
    return []


def _rate_hz(ctype: Optional[str], params: Mapping) -> Optional[float]:
    if ctype in _RATE_TYPES or ctype == "Hybrid":
        hz = params.get("hz")
        return float(hz) if hz is not None else None
    return None


@dataclass(frozen=True)
class CoveringClock:
    """The covering clock of a group of Flows.

    Attributes:
        rates_hz: distinct frequencies of the inner Rate, Tick and Hybrid clocks.
        boundary_events: boundary input names that an inner clock reads as a trigger.
        uncovered: inner nodes whose clock is not a Rate, Tick, Trigger, Synchronized or
            Hybrid clock (for example an adaptive or timeline clock). The covering clock
            does not describe them; treat the group as dynamic when this is not empty.
    """

    rates_hz: Tuple[float, ...] = ()
    boundary_events: Tuple[str, ...] = ()
    uncovered: Tuple[str, ...] = field(default=())

    @property
    def is_static(self) -> bool:
        """True when every inner clock is covered (no adaptive or unknown clocks)."""
        return not self.uncovered

    def ticks(self, start: float, stop: float) -> List[float]:
        """Rate ticks of the covering clock in [start, stop), phase 0, sorted, merged.

        Boundary events are data-dependent and are not listed. Two Rate ticks closer
        than 1e-9 s count as one tick.
        """
        if stop <= start:
            return []
        out: List[float] = []
        for hz in self.rates_hz:
            if hz <= 0:
                continue
            period = 1.0 / hz
            # Same relative tolerance on both ends, so adjacent windows never share a tick.
            k_first = math.ceil(start / period - 1e-9)
            k_stop = math.ceil(stop / period - 1e-9)
            out.extend(k * period for k in range(k_first, k_stop))
        out.sort()
        merged: List[float] = []
        for t in out:
            if not merged or t - merged[-1] > 1e-9:
                merged.append(t)
        return merged

    def __str__(self) -> str:
        parts = [f"Rate({hz:g} Hz)" for hz in self.rates_hz]
        parts += [f"events({name})" for name in self.boundary_events]
        body = " ∪ ".join(parts) if parts else "∅"
        if self.uncovered:
            body += f" + uncovered clocks on {', '.join(self.uncovered)}"
        return f"Cover[{body}]"


def covering_clock(
    ir: IR,
    boundary: Optional[Mapping[str, Tuple[str, str]]] = None,
) -> CoveringClock:
    """Return the covering clock of the Flows in ``ir``.

    Args:
        ir: the group's IR, with nested groups already lowered.
        boundary: external input name -> (inner node id, inner port). An inner clock
            that triggers on a port fed from the boundary contributes that input's
            events. Triggers fed by inner Flows need no entry: those Flows only emit at
            ticks the covering clock already holds.
    """
    boundary = dict(boundary or {})
    by_target: Dict[Tuple[str, str], str] = {
        (node_id, IR.get_logical_port(port)): name for name, (node_id, port) in boundary.items()
    }
    rates: set = set()
    events: List[str] = []
    uncovered: List[str] = []

    for node in ir.nodes:
        ctype, params = _clock_of(node)
        hz = _rate_hz(ctype, params)
        if hz is not None:
            rates.add(hz)
        fields = _trigger_fields(ctype, params)
        for f in fields:
            name = by_target.get((node.id, f))
            if name is not None and name not in events:
                events.append(name)
        if ctype is None or (hz is None and not fields and ctype not in _TRIGGER_TYPES):
            uncovered.append(node.id)

    return CoveringClock(
        rates_hz=tuple(sorted(rates)),
        boundary_events=tuple(sorted(events)),
        uncovered=tuple(sorted(uncovered)),
    )


def activation_edges(ir: IR) -> List[Tuple[str, str]]:
    """Edges (source node, destination node) whose destination port triggers the
    destination's clock. These are the same-instant dependencies of a Retriever graph."""
    triggers: Dict[str, set] = {}
    for node in ir.nodes:
        ctype, params = _clock_of(node)
        triggers[node.id] = set(_trigger_fields(ctype, params))
    out: List[Tuple[str, str]] = []
    seen: set = set()
    for edge in ir.edges:
        dst = edge.destination.node
        if IR.get_logical_port(edge.destination.port) in triggers.get(dst, ()):
            pair = (edge.source.node, dst)
            if pair not in seen:
                seen.add(pair)
                out.append(pair)
    return out


def same_instant_cycles(ir: IR) -> List[List[str]]:
    """Return the cycles made only of activation edges, as sorted lists of node ids.

    Such a cycle would make its Flows trigger each other again at the same instant, so
    the group has no single step sequence. An empty list means the group is admissible.
    """
    adj: Dict[str, List[str]] = {node.id: [] for node in ir.nodes}
    self_loops: set = set()
    for s, d in activation_edges(ir):
        adj.setdefault(s, []).append(d)
        adj.setdefault(d, [])
        if s == d:
            self_loops.add(s)

    index: Dict[str, int] = {}
    low: Dict[str, int] = {}
    on_stack: set = set()
    stack: List[str] = []
    sccs: List[List[str]] = []
    counter = [0]

    def visit(v: str) -> None:
        # Iterative Tarjan to avoid recursion limits on large graphs.
        work = [(v, iter(adj[v]))]
        index[v] = low[v] = counter[0]
        counter[0] += 1
        stack.append(v)
        on_stack.add(v)
        while work:
            node, it = work[-1]
            advanced = False
            for w in it:
                if w not in index:
                    index[w] = low[w] = counter[0]
                    counter[0] += 1
                    stack.append(w)
                    on_stack.add(w)
                    work.append((w, iter(adj[w])))
                    advanced = True
                    break
                if w in on_stack:
                    low[node] = min(low[node], index[w])
            if advanced:
                continue
            work.pop()
            if work:
                parent = work[-1][0]
                low[parent] = min(low[parent], low[node])
            if low[node] == index[node]:
                comp: List[str] = []
                while True:
                    w = stack.pop()
                    on_stack.discard(w)
                    comp.append(w)
                    if w == node:
                        break
                if len(comp) > 1 or node in self_loops:
                    sccs.append(sorted(comp))

    for v in list(adj.keys()):
        if v not in index:
            visit(v)
    return sorted(sccs)


__all__: Iterable[str] = ("CoveringClock", "covering_clock", "activation_edges", "same_instant_cycles")
