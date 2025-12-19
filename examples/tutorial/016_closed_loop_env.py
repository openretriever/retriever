"""
Closed-loop (cyclic) pipeline demo.

This example shows a minimal "gym-like" closed loop in Retriever (distributed across processes):

    Env.step(action) -> obs
    Controller.step(obs) -> action

Key pattern (stable closed loop):
- The env/plant is **clocked**: `Env @ Rate(hz=...)` (samples the latest action each tick)
- The controller is **event-driven**: `Controller @ Trigger("obs")` (runs when a new obs arrives)

Rate lag handling:
- `Rate(..., on_lag="warn")` is the default. If a node can't keep up with its requested Hz,
  Retriever will skip missed ticks (realtime-friendly; avoids "replaying stale ticks" on Dora)
  and emit a throttled warning.
  Use `on_lag="drop"` to keep the same drop behavior but quiet.
  See: `docs/handbook.md` (Rate lag policy section).

Toy env (no extra deps):
  pixi run python -m examples.tutorial.016_closed_loop_env --env toy --backend multiprocessing --hz 10 --duration 3

Pendulum (requires `gymnasium` or `gym`):
  pixi run python -m examples.tutorial.016_closed_loop_env --env pendulum --backend multiprocessing --hz 20 --duration 5
  pixi run python -m examples.tutorial.016_closed_loop_env --env pendulum --backend dora --hz 10 --duration 5

Rate lag demo (Dora, intentionally force lag):
  pixi run python -m examples.tutorial.016_closed_loop_env --env toy --backend dora --hz 50 --duration 2 --on-lag warn
  pixi run python -m examples.tutorial.016_closed_loop_env --env toy --backend dora --hz 50 --duration 2 --on-lag panic

  # (Pendulum variant, requires gymnasium/gym)
  pixi run python -m examples.tutorial.016_closed_loop_env --env pendulum --backend dora --hz 50 --duration 5 --on-lag warn
"""

from __future__ import annotations

import argparse
import itertools
import math
import random
import time
from dataclasses import dataclass
from typing import Any, cast

from retriever.flow import Flow, Pipeline, Rate, Trigger, flow_io


@flow_io
@dataclass
class Action:
    action: float


@flow_io
@dataclass
class Observation:
    transition: "Transition"


@dataclass(frozen=True)
class Transition:
    obs: list[float]
    action: float
    reward: float
    done: bool


class ToyEnv(Flow[Action, Observation]):
    """Tiny deterministic environment: x <- x + action (integer), reward encourages reaching TARGET."""

    TARGET = 5.0
    DELAY_S = 0.10
    JITTER_S = 0.0

    def init(self) -> None:
        self.x = 0

    def run(self, input: Action) -> Observation:
        _sleep_with_jitter(self.DELAY_S, self.JITTER_S)

        u = 0.0 if input.action is None else float(input.action)
        self.x += int(round(u))

        obs = [float(self.x)]
        reward = -abs(obs[0] - self.TARGET)
        return Observation(transition=Transition(obs=obs, action=u, reward=reward, done=False))


class ToyMPCController(Flow[Observation, Action]):
    """
    Brute-force MPC for ToyEnv.

    Model: x_{t+1} = x_t + a_t, a_t in {-1,0,1}
    """

    TARGET = 5.0
    HORIZON = 5
    ACTIONS = (-1, 0, 1)
    Q = 1.0
    R = 0.05

    DELAY_S = 0.10
    JITTER_S = 0.0

    def run(self, input: Observation) -> Action:
        _sleep_with_jitter(self.DELAY_S, self.JITTER_S)

        tr = input.transition
        x0 = 0.0 if not tr.obs else float(tr.obs[0])

        best_cost = float("inf")
        best_a0 = 0

        for seq in itertools.product(self.ACTIONS, repeat=self.HORIZON):
            x = x0
            cost = 0.0
            for a in seq:
                x = x + float(a)
                err = x - self.TARGET
                cost += self.Q * (err * err) + self.R * (float(a) * float(a))
            if cost < best_cost:
                best_cost = cost
                best_a0 = int(seq[0])

        return Action(action=float(best_a0))


class PendulumEnv(Flow[Action, Observation]):
    """
    Gym Pendulum-v1 wrapper (continuous control, classic balancing).

    Emits a reset observation first (reward=0.0), then steps with the latest action.
    Automatically resets after time-limit truncation.

    This demo intentionally resets to a *near-upright* initial condition so the focus
    is balancing (not swing-up).
    """

    ENV_ID = "Pendulum-v1"
    MAX_TORQUE = 2.0

    DELAY_S = 0.10
    JITTER_S = 0.0

    def init(self) -> None:
        gym = _import_gym()
        self._env = gym.make(self.ENV_ID)  # type: ignore[attr-defined]
        self._needs_reset = True
        self._rng = random.Random(0)

    def finalize(self) -> None:
        try:
            self._env.close()
        except Exception:
            pass

    def run(self, input: Action) -> Observation:
        _sleep_with_jitter(self.DELAY_S, self.JITTER_S)

        if self._needs_reset:
            _gym_reset(self._env)
            obs = self._reset_near_upright()
            self._needs_reset = False
            return Observation(
                transition=Transition(obs=_as_float_list(obs), action=0.0, reward=0.0, done=False)
            )

        u = 0.0 if input.action is None else float(input.action)
        u = float(_clip(u, -self.MAX_TORQUE, self.MAX_TORQUE))

        obs, reward, done = _gym_step(self._env, [u])
        if done:
            self._needs_reset = True
        return Observation(
            transition=Transition(obs=_as_float_list(obs), action=u, reward=float(reward), done=bool(done))
        )

    def _reset_near_upright(self) -> list[float]:
        theta = self._rng.uniform(-0.25, 0.25)
        theta_dot = self._rng.uniform(-0.25, 0.25)

        try:
            import numpy as np  # type: ignore

            unwrapped = getattr(self._env, "unwrapped", self._env)
            if hasattr(unwrapped, "state"):
                unwrapped.state = np.array([theta, theta_dot], dtype=np.float32)
                if hasattr(unwrapped, "last_u"):
                    unwrapped.last_u = None
        except Exception:
            pass

        return [math.cos(theta), math.sin(theta), float(theta_dot)]


class PendulumMPCController(Flow[Observation, Action]):
    """
    MPC for Pendulum-v1 using a linearized model (finite-horizon LQR).

    Observation is the Gym Pendulum vector: [cos(theta), sin(theta), theta_dot].
    We linearize dynamics around the upright equilibrium (theta ~= 0) and solve a
    quadratic finite-horizon problem (equivalent to linear MPC).
    """

    # Dynamics (from Gym's Pendulum reference env)
    G = 10.0
    M = 1.0
    L = 1.0
    DT = 0.05

    MAX_SPEED = 8.0
    MAX_TORQUE = 2.0

    # Linear MPC settings
    HORIZON = 40
    Q_THETA = 10.0
    Q_THETA_DOT = 1.0
    R_U = 0.1

    DELAY_S = 0.10
    JITTER_S = 0.0

    def init(self) -> None:
        self._k_theta, self._k_theta_dot = self._compute_lqr_gains()

    def run(self, input: Observation) -> Action:
        _sleep_with_jitter(self.DELAY_S, self.JITTER_S)

        tr = input.transition
        if tr.done or len(tr.obs) < 3:
            return Action(action=0.0)

        cos_t, sin_t, theta_dot = float(tr.obs[0]), float(tr.obs[1]), float(tr.obs[2])
        theta = math.atan2(sin_t, cos_t)

        u = -(self._k_theta * theta + self._k_theta_dot * theta_dot)
        u = float(_clip(u, -self.MAX_TORQUE, self.MAX_TORQUE))
        return Action(action=u)

    def _compute_lqr_gains(self) -> tuple[float, float]:
        """
        Solve a finite-horizon LQR around theta ~= 0.

        Continuous-time linearization:
          theta_ddot ≈ (3g/(2l)) * theta + (3/(m l^2)) * u

        Discretize with Euler at DT.
        """
        dt = self.DT
        a11, a12 = 1.0, dt
        a21, a22 = (3.0 * self.G / (2.0 * self.L)) * dt, 1.0
        b1, b2 = 0.0, (3.0 / (self.M * self.L * self.L)) * dt

        # P is symmetric 2x2: [[p11,p12],[p12,p22]]
        p11 = self.Q_THETA
        p12 = 0.0
        p22 = self.Q_THETA_DOT

        k1 = 0.0
        k2 = 0.0

        for _ in range(self.HORIZON):
            s = self.R_U + (b2 * b2) * p22
            if s <= 1e-9:
                s = 1e-9

            # K = inv(S) * B^T P A, with B=[0,b2]^T
            btpa1 = b2 * p12
            btpa2 = b2 * p22
            k1 = (btpa1 * a11 + btpa2 * a21) / s
            k2 = (btpa1 * a12 + btpa2 * a22) / s

            # P <- Q + A^T P A - A^T P B K
            # Compute A^T P A (symmetry preserved)
            pa11 = p11 * a11 + p12 * a21
            pa12 = p11 * a12 + p12 * a22
            pa21 = p12 * a11 + p22 * a21
            pa22 = p12 * a12 + p22 * a22

            ata11 = a11 * pa11 + a21 * pa21
            ata12 = a11 * pa12 + a21 * pa22
            ata22 = a12 * pa12 + a22 * pa22

            # Compute A^T P B (2x1), with B=[0,b2]^T and P symmetric
            pb1 = p12 * b2
            pb2v = p22 * b2
            atpb1 = a11 * pb1 + a21 * pb2v
            atpb2 = a12 * pb1 + a22 * pb2v

            # Outer product: (A^T P B) * K
            o11 = atpb1 * k1
            o12 = atpb1 * k2
            o22 = atpb2 * k2

            p11 = self.Q_THETA + ata11 - o11
            p12 = 0.0 + ata12 - o12
            p22 = self.Q_THETA_DOT + ata22 - o22

        # u = -K x, so return gains for theta/theta_dot
        return float(k1), float(k2)


class PrintObs(Flow[Observation, None]):
    """Sink: print reward (gym-style) and a readable angle."""

    def run(self, input: Observation) -> None:
        tr = input.transition
        angle_deg = float("nan")
        if len(tr.obs) >= 2:
            angle_deg = math.degrees(math.atan2(float(tr.obs[1]), float(tr.obs[0])))
        print(
            f"[step] u={tr.action:+.2f} reward={tr.reward:+.3f} done={tr.done} angle_deg={angle_deg:+.1f}"
        )
        return None


def _import_gym():
    try:
        import gymnasium as gym  # type: ignore

        return gym
    except Exception:
        try:
            import gym  # type: ignore

            return gym
        except Exception as e:
            raise RuntimeError(
                "Pendulum demo requires `gymnasium` (preferred) or `gym`.\n"
                "Install one of:\n"
                "  - pixi add gymnasium\n"
                "  - pip install gymnasium\n"
            ) from e


def _gym_reset(env: Any):
    out = env.reset()
    if isinstance(out, tuple) and len(out) == 2:
        obs, _info = out
        return obs
    return out


def _gym_step(env: Any, action: Any) -> tuple[Any, float, bool]:
    out = env.step(action)

    # Gymnasium: (obs, reward, terminated, truncated, info)
    if isinstance(out, tuple) and len(out) == 5:
        obs, reward, terminated, truncated, _info = cast(tuple[Any, Any, Any, Any, Any], out)
        return obs, float(reward), bool(terminated) or bool(truncated)

    # Gym: (obs, reward, done, info)
    if isinstance(out, tuple) and len(out) == 4:
        obs, reward, done, _info = cast(tuple[Any, Any, Any, Any], out)
        return obs, float(reward), bool(done)

    raise RuntimeError(f"Unexpected env.step(...) return: {type(out).__name__} {out!r}")


def _as_float_list(obs: Any) -> list[float]:
    try:
        return [float(x) for x in obs.tolist()]  # type: ignore[union-attr]
    except Exception:
        try:
            return [float(x) for x in obs]
        except Exception:
            return [float(obs)]


def _default_env_choice() -> str:
    try:
        _import_gym()
        return "pendulum"
    except Exception:
        return "toy"


def _sleep_with_jitter(base_s: float, jitter_s: float) -> None:
    delay = base_s + random.uniform(-jitter_s, jitter_s)
    if delay > 0:
        time.sleep(delay)


def _clip(x: float, lo: float, hi: float) -> float:
    return lo if x < lo else hi if x > hi else x


def _angle_normalize(x: float) -> float:
    return ((x + math.pi) % (2.0 * math.pi)) - math.pi


def build_pipeline(*, hz: float, env: str, on_lag: str = "warn") -> Pipeline:
    pipe = Pipeline("closed_loop_env")

    if env == "toy":
        # The env is the "clock" of the closed-loop: it ticks periodically and samples the latest action.
        env_node = ToyEnv() @ Rate(hz=hz, on_lag=on_lag)
        ctrl_node = ToyMPCController() @ Trigger("transition")
    elif env == "pendulum":
        env_node = PendulumEnv() @ Rate(hz=hz, on_lag=on_lag)
        ctrl_node = PendulumMPCController() @ Trigger("transition")
    else:
        raise ValueError(f"Unknown env: {env!r}")

    printer = PrintObs() @ Trigger("transition")

    # Closed-loop wiring:
    #   env -> controller (observation)
    #   controller -> env (action)
    pipe.connect(env_node, ctrl_node)  # obs -> obs
    pipe.connect(ctrl_node, env_node)  # action -> action
    pipe.connect(env_node, printer)  # obs -> obs

    return pipe


def main() -> None:
    ap = argparse.ArgumentParser(description="Retriever closed-loop env demo (MPC)")
    ap.add_argument("--backend", default="multiprocessing", choices=["multiprocessing", "dora"])
    ap.add_argument("--env", default=_default_env_choice(), choices=["toy", "pendulum"])
    ap.add_argument("--hz", type=float, default=10.0, help="Environment tick rate (Hz)")
    ap.add_argument(
        "--on-lag",
        default="warn",
        choices=["drop", "warn", "error", "panic", "catch_up"],
        help="Rate lag policy for the env clock (panic is an alias for error)",
    )
    ap.add_argument("--duration", type=float, default=3.0, help="Run duration (seconds)")
    args = ap.parse_args()
    args.on_lag = Rate._normalize_on_lag(args.on_lag)

    if args.env == "pendulum":
        _import_gym()  # fail fast with a clear message if missing

    print(
        f"[config] env={args.env} backend={args.backend} hz={args.hz:g} on_lag={args.on_lag} "
        f"(env_delay={PendulumEnv.DELAY_S if args.env == 'pendulum' else ToyEnv.DELAY_S:.2f}s, "
        f"ctrl_delay={PendulumMPCController.DELAY_S if args.env == 'pendulum' else ToyMPCController.DELAY_S:.2f}s)"
    )

    pipe = build_pipeline(hz=args.hz, env=args.env, on_lag=args.on_lag)
    pipe.run(backend=args.backend, duration=args.duration, blocking=True)


if __name__ == "__main__":
    main()
