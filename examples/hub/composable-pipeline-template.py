"""Hub template for composable pipelines, shared types, and transforms.

This file is a copy-paste template, not a guaranteed runnable demo as-is.
Replace the placeholder module/export names with your actual Hub module.

Run after editing:
    pixi run python examples/hub/composable-pipeline-template.py
"""

from retriever import hub
from retriever.flow import Latest, Pipeline, Rate

MODULE = "company-abc/lidar-slam"


def main() -> None:
    if MODULE.startswith("company-abc/"):
        raise SystemExit(
            "Edit MODULE and export names in examples/hub/composable-pipeline-template.py first."
        )

    mod = hub.use(MODULE)

    # 1) Extend an imported live pipeline.
    pipe = mod.BuildSlamPipeline()
    frontend = pipe.select_flow("frontend")
    pipe.replace(frontend, mod.ReplayFrontend() @ Rate(hz=10))

    pose = mod.SE3Pose(x=1.0, y=2.0, z=3.0)
    threshold = mod.pose_to_threshold(pose)
    pipe.inject_input("frontend", "threshold", threshold, timestamp=0.0)

    # 2) Treat the same imported pipeline as one reusable stage.
    outer = Pipeline("hub_outer")
    with outer:
        source = mod.CameraSource() @ Rate(hz=10)
        stage = (mod.BuildSlamPipelineFlow() @ Rate(hz=10)).named("slam")
        sink = mod.PrintPose() @ Rate(hz=10)
        source.then(stage, sync=Latest())
        stage.then(sink, sync=Latest())

    print("Imported live pipeline:", pipe.get_flow_dict().keys())
    print("Wrapped stage node ids:", [node.id for node in outer.validate().nodes])


if __name__ == "__main__":
    main()
