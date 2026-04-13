from __future__ import annotations

import numpy as np
import pytest

from retriever import get_type, get_type_info, resolve_schema_ref
from retriever.flow import Flow
from retriever.flow.io import is_flow_io
from retriever.rt.step import IOView
from retriever.types import SchemaRef
from retriever.types.language import (
    Caption,
    GroundedPhrase,
    PlanStepText,
    PlanText,
    Prompt,
    ReferringExpression,
    TextSpan,
    validate_caption,
    validate_grounded_phrase,
    validate_plan_step_text,
    validate_plan_text,
    validate_prompt,
    validate_referring_expression,
    validate_text_span,
)
from retriever.types.language.v1 import Caption as PinnedCaption
from retriever.types.perception import DetectionBatch, Image2D


def test_language_package_exports_canonical_surface() -> None:
    caption = Caption(text="a red cube on the table", confidence=0.9)
    assert caption.text.startswith("a red")
    assert PinnedCaption is Caption


def test_language_types_are_flow_compatible() -> None:
    assert is_flow_io(Caption)
    assert is_flow_io(ReferringExpression)
    assert is_flow_io(GroundedPhrase)
    assert is_flow_io(PlanText)


def test_language_types_register_with_registry() -> None:
    assert get_type('Caption') is Caption
    assert get_type('PlanText') is PlanText
    info = get_type_info('GroundedPhrase')
    assert info.namespace == 'language'
    assert info.schema_ref == SchemaRef(name='language/GroundedPhrase', version='v1', encoding='python')


def test_resolve_schema_ref_supports_language_types() -> None:
    msg = GroundedPhrase(text='the red cube', referent_label='red', confidence=0.8, frame_index=4)
    assert resolve_schema_ref(msg) == SchemaRef(name='language/GroundedPhrase', version='v1', encoding='python')


def test_language_validators_reject_invalid_values() -> None:
    validate_text_span(TextSpan(start=0, end=4))
    validate_caption(Caption(text='scene summary', confidence=0.5))
    validate_prompt(Prompt(text='find the red block'))
    validate_referring_expression(ReferringExpression(text='the blue object', span=TextSpan(start=4, end=8)))
    validate_grounded_phrase(GroundedPhrase(text='the red cube', referent_label='red', confidence=0.6, frame_index=0))
    validate_plan_step_text(PlanStepText(index=0, text='approach the red cube', confidence=0.7))
    validate_plan_text(PlanText(steps=(PlanStepText(index=0, text='look'), PlanStepText(index=1, text='pick')), summary='two-step'))

    with pytest.raises(ValueError):
        validate_text_span(TextSpan(start=3, end=3))
    with pytest.raises(ValueError):
        validate_caption(Caption(text='  '))
    with pytest.raises(ValueError):
        validate_prompt(Prompt(text='go', role=''))
    with pytest.raises(ValueError):
        validate_referring_expression(ReferringExpression(text='red', span=TextSpan(start=-1, end=1)))
    with pytest.raises(ValueError):
        validate_grounded_phrase(GroundedPhrase(text='red', confidence=1.2))
    with pytest.raises(ValueError):
        validate_plan_step_text(PlanStepText(index=-1, text='bad'))
    with pytest.raises(ValueError):
        validate_plan_text(PlanText(steps=(PlanStepText(index=1, text='skip zero'),)))


class GroundRefFlow(Flow[(ReferringExpression, DetectionBatch), GroundedPhrase]):
    def reset(self) -> None:
        self._detections = DetectionBatch(detections=())

    def step(self, inp):  # type: ignore[override]
        detections = getattr(inp, 'DetectionBatch', None)
        if detections is not None:
            self._detections = detections
        dets = self._detections.detections
        label = dets[0].label if dets else 'red'
        expression = getattr(inp, 'ReferringExpression', None)
        if expression is None:
            expression = inp[0] if isinstance(inp, tuple) else ReferringExpression(text='the red cube')
        return GroundedPhrase(text=expression.text, referent_label=label)


class CaptionPlanFlow(Flow[Caption, PlanText]):
    def step(self, caption: Caption) -> PlanText:
        step = PlanStepText(index=0, text=f"inspect scene: {caption.text}")
        return PlanText(steps=(step,), summary='single-step')


def test_language_primitives_work_in_composite_flow_signatures() -> None:
    assert GroundRefFlow._input_types == (ReferringExpression, DetectionBatch)
    assert GroundRefFlow._output_types == (GroundedPhrase,)

    plan = CaptionPlanFlow().step(Caption(text='red cube on the left'))
    assert plan.steps[0].index == 0


def test_language_composite_flow_runs_with_ioview() -> None:
    comp = IOView(
        [ReferringExpression, DetectionBatch],
        {
            'ReferringExpression': ReferringExpression(text='the red cube'),
            'DetectionBatch': DetectionBatch(detections=()),
        },
    )
    grounded = GroundRefFlow().step(comp)
    assert grounded.text == 'the red cube'
    assert grounded.referent_label == 'red'


class CaptionOnFrameFlow(Flow[(Image2D, Caption), PlanText]):
    def step(self, inp):  # type: ignore[override]
        frame = inp.Image2D
        caption = inp.Caption
        step = PlanStepText(index=0, text=f"frame {frame.frame_index}: {caption.text}", action_label='caption')
        return PlanText(steps=(step,), summary=caption.text, source='caption_on_frame')


def test_language_cross_family_composite_flow_runs_with_ioview() -> None:
    assert CaptionOnFrameFlow._input_types == (Image2D, Caption)
    assert CaptionOnFrameFlow._output_types == (PlanText,)

    frame = Image2D(data=np.zeros((2, 2, 3), dtype=np.uint8), frame_index=5)
    comp = IOView(
        [Image2D, Caption],
        {
            'Image2D': frame,
            'Caption': Caption(text='red cube on the table'),
        },
    )
    plan = CaptionOnFrameFlow().step(comp)
    assert plan.steps[0].text == 'frame 5: red cube on the table'
    assert plan.steps[0].action_label == 'caption'
