from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Callable

@dataclass(frozen=True)
class PreviewSection:
    stage: StrEnum
    title: str
    render: Callable[[], None]

def print_section(title: str) -> None:
    print("\n" + "=" * 60)
    print(title)
    print("=" * 60)

def should_render_section(
        selected: StrEnum, 
        target: StrEnum, 
        all_stage: StrEnum
        ) -> bool:
    return selected in (target, all_stage)

def render_sections(
        sections: list[PreviewSection],
        selected: StrEnum,
        all_stage: StrEnum,
) -> None:
    for section in sections:
        if should_render_section(selected, section.stage, all_stage):
            print_section(section.title)
            section.render()