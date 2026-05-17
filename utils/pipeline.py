from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Callable, Generic, TypeVar


T = TypeVar("T")
U = TypeVar("U")


@dataclass(frozen=True)
class Phase:
    name: StrEnum
    value: object


@dataclass
class PipelineResult(Generic[T]):
    value: T | None
    trace: list[Phase] = field(default_factory=list)
    errors: list[Exception] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


def start_pipeline(name: StrEnum, value: T) -> PipelineResult[T]:
    return PipelineResult(
        value=value,
        trace=[Phase(name, value)],
    )


def add_phase(
    pipeline: PipelineResult[T],
    name: StrEnum,
    fn: Callable[[T], U],
) -> PipelineResult[U]:
    if not pipeline.ok:
        return PipelineResult(
            value=None,
            trace=pipeline.trace,
            errors=pipeline.errors,
        )

    try:
        assert pipeline.value is not None
        new_value = fn(pipeline.value)
        return PipelineResult(
            value=new_value,
            trace=pipeline.trace + [Phase(name, new_value)],
        )
    except Exception as exc:
        return PipelineResult(
            value=None,
            trace=pipeline.trace,
            errors=pipeline.errors + [exc],
        )