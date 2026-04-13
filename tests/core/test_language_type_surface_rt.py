from __future__ import annotations

import pytest

from retriever import get_type, get_type_info, resolve_schema_ref
from retriever.flow import Flow
from retriever.flow.io import is_flow_io
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
from retriever.types.perception import DetectionBatch


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
    def step(self, inp):  # type: ignore[override]
        dets = inp.DetectionBatch.detections
        label = dets[0].label if dets else None
        return GroundedPhrase(text=inp.ReferringExpression.text, referent_label=label)


class CaptionPlanFlow(Flow[Caption, PlanText]):
    def step(self, caption: Caption) -> PlanText:
        step = PlanStepText(index=0, text=f"inspect scene: {caption.text}")
        return PlanText(steps=(step,), summary='single-step')


def test_language_primitives_work_in_composite_flow_signatures() -> None:
    assert GroundRefFlow._input_types == (ReferringExpression, DetectionBatch)
    assert GroundRefFlow._output_types == (GroundedPhrase,)

    plan = CaptionPlanFlow().step(Caption(text='red cube on the left'))
    assert plan.steps[0].index == 0
