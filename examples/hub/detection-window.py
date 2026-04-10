"""Hub example: import flows/types from a module and compose them locally.

Set `RETRIEVER_HUB_DETECTION_WINDOW_MODULE` to a published Hub module ref that
exports the camera/detector/window demo surface.

This example demonstrates whole-module import plus local pipeline assembly. It
imports flow and IO definitions from Hub, then builds a local pipeline around
those exports.

Run:
    RETRIEVER_HUB_DETECTION_WINDOW_MODULE=your-org/detection-window-demo pixi run python examples/hub/detection-window.py
"""

import os
from pathlib import Path

from retriever import hub
from retriever.flow import Flow, Pipeline, Rate, Trigger, Window, io

module_ref = os.environ.get("RETRIEVER_HUB_DETECTION_WINDOW_MODULE", "").strip()
if not module_ref:
    raise SystemExit(
        "Set RETRIEVER_HUB_DETECTION_WINDOW_MODULE to a published Hub module ref, "
        "for example 'your-org/detection-window-demo'."
    )

dw = hub.use(module_ref)


@io
class Empty:
    pass


class SaveFrame(Flow[dw.CameraData, Empty]):
    def __init__(self, output_dir: str = "frames"):
        super().__init__()
        self._output_dir = Path(output_dir)

    def reset(self) -> None:
        self._output_dir.mkdir(parents=True, exist_ok=True)

    def step(self, input: dw.CameraData) -> Empty:
        from PIL import Image

        img = Image.fromarray(input.frame)
        img.save(self._output_dir / f"frame_{input.frame_id:04d}.png")
        return Empty()


def build_demo() -> Pipeline:
    pipe = Pipeline("vision_detection_window")
    with pipe:
        camera = dw.SyntheticCameraSource() @ Rate(hz=20)
        detector = dw.ColorBlobDetector() @ Trigger("frame")
        printer = dw.PrintWindowMean() @ Trigger("mean_count")
        saver = SaveFrame(output_dir="frames") @ Trigger("frame")

        camera >> detector
        camera >> saver
        detector.then(
            printer,
            map={"count": "mean_count"},
            sync=Window(buffer_size=200, duration=0.5, agg="mean"),
        )
    return pipe


if __name__ == "__main__":
    build_demo().run(backend="multiprocessing", duration=3.0, blocking=True)
