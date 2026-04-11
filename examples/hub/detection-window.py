from pathlib import Path
from dataclasses import dataclass

from retriever import hub
from retriever.flow import Flow, Pipeline, Rate, Trigger, Window, io

dw = hub.use("openretriever/detection-window-demo")


@io
@dataclass
class Empty:
    pass


class SaveFrame(Flow[dw.CameraData, Empty]):
    def __init__(self, output_dir: str = "frames"):
        self._output_dir = Path(output_dir)

    def init(self) -> None:
        self._output_dir.mkdir(parents=True, exist_ok=True)

    def run(self, input):
        from PIL import Image

        img = Image.fromarray(input.frame)
        img.save(self._output_dir / f"frame_{input.frame_id:04d}.png")
        return Empty()


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

pipe.run(backend="multiprocessing", duration=3, blocking=True)
