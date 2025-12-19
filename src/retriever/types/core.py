from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Generic, Tuple, TypeVar, runtime_checkable, Protocol

S = TypeVar("S")
A = TypeVar("A")
B = TypeVar("B")
I = TypeVar("I")
O = TypeVar("O")


@runtime_checkable
class Module(Protocol, Generic[I, O]):
    """
    A typed, side-effect-free operator in the Retriever graph.
    
    This is the core protocol for any component that can be part of a Retriever
    computation graph. It's a simple, typed, callable object.
    """
    def __call__(self, inp: I) -> O:
        ...


@dataclass(frozen=True)
class Eff(Generic[S, A]):
    """
    A class for handling state and side effects in a functional way.

    The name "Eff" is short for "Effect". This is a "State Monad," a well-known
    functional programming pattern. It encapsulates a computation that threads
    a state `S` through a series of operations, ultimately producing a result `A`.

    The core idea is to make state management explicit. Instead of functions
    modifying a global or shared state, they take the current state as input
    and return the new state along with their result. The Eff class wraps this
    `S -> (A, S)` function, and the `>>` (bind) operator chains these
    computations together, hiding the state-passing boilerplate.
    """

    run: Callable[[S], Tuple[A, S]]

    def __rshift__(self, k: Callable[[A], Eff[S, B]]) -> Eff[S, B]:
        """
        The "bind" operator (often written as `>>=` in Haskell or `flatMap`
        in Scala/Spark). It chains an effectful computation `k` after this one.

        Args:
            k: A function that takes the result of this computation (`A`) and
               returns the next computation (`Eff[S, B]`). This is also known
               as a "continuation."
        """

        def new_run(s0: S) -> Tuple[B, S]:
            a, s1 = self.run(s0)
            return k(a).run(s1)

        return Eff(new_run)


def pure(x: A) -> Eff[S, A]:
    """
    Lifts a pure, stateless value `x` into the Eff monad.

    It creates a computation that, when run, returns the value `x` without
    modifying the state at all.
    """
    return Eff(lambda s: (x, s))


def bind(e: Eff[S, A], k: Callable[[A], Eff[S, B]]) -> Eff[S, B]:
    """
    The implementation of the bind operator for the Eff monad.
    """

    def new_run(s0: S) -> tuple[B, S]:
        a, s1 = e.run(s0)
        return k(a).run(s1)

    return Eff(new_run)
