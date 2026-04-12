"""Hub example: import flows/types from a module and compose them locally.

This example demonstrates whole-module import plus local pipeline assembly.
It does not import a pre-registered pipeline from Hub; see
`examples/hub/_composable_pipeline_template.py` for that shape.

Set `RETRIEVER_HUB_DETECTION_WINDOW_MODULE` to a module available in your
index before running this example.

Run:
    RETRIEVER_HUB_DETECTION_WINDOW_MODULE=your-org/detection-window-demo     pixi run python examples/hub/detection-window.py
"""

from __future__ import annotations

import os
from pathlib import Path

from retriever import hub
from retriever.flow import Flow, Pipeline, Rate, Trigger, Window, io

MODULE_REF = os.environ.get('RETRIEVER_HUB_DETECTION_WINDOW_MODULE', '').strip()
if not MODULE_REF:
    raise SystemExit(
        'Set RETRIEVER_HUB_DETECTION_WINDOW_MODULE=org/module before running this example.'
    )

dw = hub.use(MODULE_REF)

@io
class Empty:
    pass

class SaveFrame(Flow[dw.CameraData, Empty]):
    def __init__(self, output_dir: str = 'frames'):
        self._output_dir = Path(output_dir)

    def reset(self) -> None:
        self._output_dir.mkdir(parents=True, exist_ok=True)

    def step(self, input: dw.CameraData) -> Empty:
        import cv2

        path = self._output_dir / f'frame_{input.frame_id:04d}.png'
        cv2.imwrite(str(path), cv2.cvtColor(input.frame, cv2.COLOR_RGB2BGR))
        return Empty()

pipe = Pipeline('vision_detection_window')
with pipe:
    camera = dw.SyntheticCameraSource() @ Rate(hz=20)
    detector = dw.ColorBlobDetector() @ Trigger('frame')
    printer = dw.PrintWindowMean() @ Trigger('mean_count')
    saver = SaveFrame(output_dir='frames') @ Trigger('frame')

    camera >> detector
    camera >> saver
    detector.then(
        printer,
        map={'count': 'mean_count'},
        sync=Window(buffer_size=200, duration=0.5, agg='mean'),
    )

pipe.run(backend='multiprocessing', duration=3, blocking=True)
