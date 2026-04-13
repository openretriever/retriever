"""Language grounding composition tutorial.

Covers:
1) canonical language + perception primitive imports
2) composite Flow signatures without example-only envelopes
3) explicit buffered grounding over the latest scene snapshot

Run:
  pixi run python -m examples.tutorial.g_operations_interfaces.07_language_grounding_composition
"""

from __future__ import annotations

from pathlib import Path

from retriever.flow import Flow, Latest, Pipeline, Rate, Trigger
from retriever.types.language import GroundedPhrase, ReferringExpression
from retriever.types.perception import BBox2D, Detection2D, DetectionBatch

from examples.tutorial._p0_utils import format_table, utc_now_iso, write_json


class DetectionSource(Flow[None, DetectionBatch]):
    def reset(self) -> None:
        self._frame = 0

    def step(self, _):  # type: ignore[override]
        self._frame += 1
        if self._frame % 2 == 1:
            detections = (
                Detection2D(label='red', bbox=BBox2D(x=8.0, y=6.0, width=10.0, height=10.0), confidence=0.92),
                Detection2D(label='blue', bbox=BBox2D(x=28.0, y=8.0, width=9.0, height=9.0), confidence=0.81),
            )
        else:
            detections = (
                Detection2D(label='blue', bbox=BBox2D(x=30.0, y=8.0, width=9.0, height=9.0), confidence=0.84),
                Detection2D(label='red', bbox=BBox2D(x=10.0, y=6.0, width=10.0, height=10.0), confidence=0.90),
            )
        return DetectionBatch(detections=detections, frame_index=self._frame)


class ExpressionSource(Flow[None, ReferringExpression]):
    def __init__(self) -> None:
        super().__init__()
        self._expressions = (
            'the red object',
            'the blue object',
            'the left target',
        )

    def reset(self) -> None:
        self._index = 0

    def step(self, _):  # type: ignore[override]
        text = self._expressions[self._index % len(self._expressions)]
        self._index += 1
        return ReferringExpression(text=text)


class GroundExpression(Flow[(ReferringExpression, DetectionBatch), GroundedPhrase]):
    def reset(self) -> None:
        self._latest_batch = DetectionBatch(detections=())

    def step(self, inp):  # type: ignore[override]
        batch = getattr(inp, 'DetectionBatch', None)
        if batch is not None:
            self._latest_batch = batch

        expression = getattr(inp, 'ReferringExpression', None)
        if expression is None:
            return GroundedPhrase()

        batch = self._latest_batch
        text = expression.text.lower()
        chosen = None
        for det in batch.detections:
            if det.label.lower() in text:
                chosen = det
                break
        if chosen is None and 'left' in text and batch.detections:
            chosen = min(batch.detections, key=lambda det: det.bbox.x)
        if chosen is None and batch.detections:
            chosen = batch.detections[0]
        return GroundedPhrase(
            text=expression.text,
            referent_label=None if chosen is None else chosen.label,
            confidence=None if chosen is None else chosen.confidence,
            frame_index=batch.frame_index,
        )


def main() -> None:
    out_path = Path('logs/tutorial_language_grounding/tut040_language_grounding_summary.json')

    pipe = Pipeline('tut040_language_grounding')
    detections = DetectionSource() @ Rate(hz=5)
    expressions = ExpressionSource() @ Rate(hz=5)
    grounder = GroundExpression() @ Trigger('text')
    pipe.connect(expressions, grounder, sync=Latest())
    pipe.connect(detections, grounder, sync=Latest())

    grounder_id = pipe.get_node_id(grounder)
    rows: list[list[str]] = []
    outputs: list[dict[str, object]] = []
    try:
        for step_idx in range(3):
            result = pipe.step(dt=0.2)
            phrase = result.outputs.get(grounder_id)
            if phrase is None:
                continue
            rows.append([
                str(step_idx + 1),
                phrase.text,
                str(phrase.frame_index),
                str(phrase.referent_label),
            ])
            outputs.append({
                'step': step_idx + 1,
                'text': phrase.text,
                'frame_index': phrase.frame_index,
                'referent_label': phrase.referent_label,
                'confidence': phrase.confidence,
            })
    finally:
        pipe.close_stepper()

    print('=== Language Grounding Composition ===')
    print(format_table(['step', 'expression', 'frame_index', 'referent'], rows))

    write_json(
        out_path,
        {
            'generated_at': utc_now_iso(),
            'outputs': outputs,
        },
    )
    print(f"\n[artifact] wrote {out_path}")


if __name__ == '__main__':
    main()
