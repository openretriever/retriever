from __future__ import annotations

from dataclasses import dataclass

from retriever.flow import Flow, Pipeline, Rate, Trigger, flow_io


@flow_io
@dataclass
class Action:
    action: int


@flow_io
@dataclass
class Observation:
    obs: int


class Env(Flow[Action, Observation]):
    def reset(self) -> None:
        self.x = 0

    def step(self, input: Action) -> Observation:
        action = 0 if input.action is None else int(input.action)
        self.x += action
        return Observation(obs=self.x)


class Controller(Flow[Observation, Action]):
    def step(self, input: Observation) -> Action:
        obs = 0 if input.obs is None else int(input.obs)
        return Action(action=1 if obs < 3 else 0)


from retriever import set_global_config


def test_cycle_pipeline_is_valid_and_reports_scc_group():
    set_global_config(default_sync="liberal")
    pipe = Pipeline("cycle_demo")

    env = Env() @ Rate(hz=10)
    ctrl = Controller() @ Trigger("obs")

    pipe.connect(env, ctrl)
    pipe.connect(ctrl, env)

    ir = pipe.validate()
    assert ir.topology.has_cycle is True
    assert any(len(group) > 1 for group in ir.topology.groups)

