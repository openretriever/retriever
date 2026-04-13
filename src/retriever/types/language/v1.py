"""Canonical primitive language payload standard v1.

This package stays intentionally small. It defines reusable text-grounding and
plan-text primitives, not model-specific request/response envelopes.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final, Iterable

from retriever.flow import io
from retriever.registry.types import register_type

_LANGUAGE_CATEGORY: Final[str] = "language"
_LANGUAGE_NAMESPACE: Final[str] = "language"
_LANGUAGE_VERSION: Final[str] = "v1"


def _register_language_type(
    name: str,
    *,
    description: str,
    tags: Iterable[str],
):
    return register_type(
        name,
        description=description,
        category=_LANGUAGE_CATEGORY,
        namespace=_LANGUAGE_NAMESPACE,
        version=_LANGUAGE_VERSION,
        kind="payload",
        tags=tags,
        schema_name=f"language/{name}",
        schema_version=_LANGUAGE_VERSION,
    )


@_register_language_type(
    "TextSpan",
    description="Half-open character span over a source string",
    tags=["language", "v1", "text", "span"],
)
@io
@dataclass(frozen=True)
class TextSpan:
    start: int
    end: int


@_register_language_type(
    "Caption",
    description="Short descriptive text about a scene, object, or frame",
    tags=["language", "v1", "caption", "text"],
)
@io
@dataclass(frozen=True)
class Caption:
    text: str
    language: str = "en"
    confidence: float | None = None
    source: str | None = None


@_register_language_type(
    "Prompt",
    description="Prompt text to a language or multimodal model",
    tags=["language", "v1", "prompt"],
)
@io
@dataclass(frozen=True)
class Prompt:
    text: str
    role: str = "user"
    language: str = "en"


@_register_language_type(
    "ReferringExpression",
    description="Natural-language reference to an entity in context",
    tags=["language", "v1", "grounding", "reference"],
)
@io
@dataclass(frozen=True)
class ReferringExpression:
    text: str
    language: str = "en"
    span: TextSpan | None = None


@_register_language_type(
    "GroundedPhrase",
    description="Language phrase tied to a resolved referent label or local frame index",
    tags=["language", "v1", "grounding", "resolved"],
)
@io
@dataclass(frozen=True)
class GroundedPhrase:
    text: str
    language: str = "en"
    referent_label: str | None = None
    confidence: float | None = None
    frame_index: int | None = None
    span: TextSpan | None = None


@_register_language_type(
    "PlanStepText",
    description="Single primitive language plan step",
    tags=["language", "v1", "plan", "step"],
)
@io
@dataclass(frozen=True)
class PlanStepText:
    index: int
    text: str
    action_label: str | None = None
    confidence: float | None = None


@_register_language_type(
    "PlanText",
    description="Ordered tuple of primitive language plan steps",
    tags=["language", "v1", "plan", "text"],
)
@io
@dataclass(frozen=True)
class PlanText:
    steps: tuple[PlanStepText, ...] = ()
    summary: str | None = None
    source: str | None = None


def _validate_non_empty_text(value: str, *, field_name: str) -> None:
    if not value or not value.strip():
        raise ValueError(f"{field_name} must be non-empty")


def _validate_language_code(value: str, *, field_name: str) -> None:
    if not value or not value.strip():
        raise ValueError(f"{field_name} must be non-empty")


def _validate_optional_confidence(value: float | None, *, field_name: str) -> None:
    if value is not None and not (0.0 <= value <= 1.0):
        raise ValueError(f"{field_name} must be within [0.0, 1.0] when provided")


def _validate_optional_frame_index(value: int | None, *, field_name: str) -> None:
    if value is not None and value < 0:
        raise ValueError(f"{field_name} must be >= 0 when provided")


def validate_text_span(msg: TextSpan) -> None:
    if msg.start < 0:
        raise ValueError("TextSpan.start must be >= 0")
    if msg.end <= msg.start:
        raise ValueError("TextSpan.end must be > start")


def validate_caption(msg: Caption) -> None:
    _validate_non_empty_text(msg.text, field_name="Caption.text")
    _validate_language_code(msg.language, field_name="Caption.language")
    _validate_optional_confidence(msg.confidence, field_name="Caption.confidence")


def validate_prompt(msg: Prompt) -> None:
    _validate_non_empty_text(msg.text, field_name="Prompt.text")
    _validate_non_empty_text(msg.role, field_name="Prompt.role")
    _validate_language_code(msg.language, field_name="Prompt.language")


def validate_referring_expression(msg: ReferringExpression) -> None:
    _validate_non_empty_text(msg.text, field_name="ReferringExpression.text")
    _validate_language_code(msg.language, field_name="ReferringExpression.language")
    if msg.span is not None:
        validate_text_span(msg.span)


def validate_grounded_phrase(msg: GroundedPhrase) -> None:
    _validate_non_empty_text(msg.text, field_name="GroundedPhrase.text")
    _validate_language_code(msg.language, field_name="GroundedPhrase.language")
    _validate_optional_confidence(msg.confidence, field_name="GroundedPhrase.confidence")
    _validate_optional_frame_index(msg.frame_index, field_name="GroundedPhrase.frame_index")
    if msg.span is not None:
        validate_text_span(msg.span)


def validate_plan_step_text(msg: PlanStepText) -> None:
    if msg.index < 0:
        raise ValueError("PlanStepText.index must be >= 0")
    _validate_non_empty_text(msg.text, field_name="PlanStepText.text")
    _validate_optional_confidence(msg.confidence, field_name="PlanStepText.confidence")


def validate_plan_text(msg: PlanText) -> None:
    for expected, step in enumerate(msg.steps):
        validate_plan_step_text(step)
        if step.index != expected:
            raise ValueError("PlanText.steps must use contiguous zero-based step indices")
