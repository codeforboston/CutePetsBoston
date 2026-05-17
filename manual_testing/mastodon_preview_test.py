"""
How to use this to see each stage of the pipeline:
see pet information:
python manual_tests/mastodon_preview.py --stage pet
see post information (platform ready but not mastodon processed):
python manual_tests/mastodon_preview.py --stage post
see full formatting in mastodon:
python manual_tests/mastodon_preview.py --stage debug
see only main thread part of the formatting in mastodon:
python manual_tests/mastodon_preview.py --stage main
see only replies part of the formatting in mastodon:
python manual_tests/mastodon_preview.py --stage replies
see all stages:
python manual_tests/mastodon_preview.py --stage all (or no arg default to all)
Extend sections to be previewed by modifying the PreviewStage class and add 
an action to sections
"""
from __future__ import annotations

import argparse
import os
import sys
from dataclasses import asdict, is_dataclass
from enum import StrEnum
from pprint import pprint

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from mastodon_manual_test import post_exceed_500_chars_limit_with_adoption_link
from social_posters.mastodon import CaptionThread, MastodonPhase, PosterMastodon
from utils.pipeline import Phase, PipelineResult
from utils.pipeline_preview import PreviewSection, print_section, render_sections


class PreviewStage(StrEnum):
    PET = "pet"
    POST = "post"
    PREPARED_CAPTION = "prepared_caption"
    CAPTION_THREAD = "caption_thread"
    MAIN = "main"
    REPLIES = "replies"
    TRACE = "trace"
    ALL = "all"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Preview each stage of the Mastodon formatting pipeline."
    )
    parser.add_argument(
        "--stage",
        type=PreviewStage,
        choices=list(PreviewStage),
        default=PreviewStage.ALL,
        help="Which construction stage to preview.",
    )
    return parser.parse_args()


def find_phase(pipeline: PipelineResult, phase_name: MastodonPhase) -> Phase | None:
    for phase in pipeline.trace:
        if phase.name == phase_name:
            return phase

    return None


def value_for_phase(pipeline: PipelineResult, phase_name: MastodonPhase) -> object | None:
    phase = find_phase(pipeline, phase_name)
    return phase.value if phase else None


def print_value(value: object) -> None:
    if is_dataclass(value) and not isinstance(value, type):
        pprint(asdict(value))
    else:
        pprint(value)


def print_phase(pipeline: PipelineResult, phase_name: MastodonPhase) -> None:
    value = value_for_phase(pipeline, phase_name)

    if value is None:
        print(f"(No value recorded for {phase_name})")
        return

    print_value(value)


def print_trace(pipeline: PipelineResult) -> None:
    for i, phase in enumerate(pipeline.trace, start=1):
        print_section(f"PHASE {i}: {phase.name}")
        print_value(phase.value)

    if pipeline.errors:
        print_section("ERRORS")
        for error in pipeline.errors:
            print(f"{type(error).__name__}: {error}")


def print_main_caption(thread: CaptionThread | None) -> None:
    if thread is None:
        print("(No caption thread)")
        return

    print(thread.main_caption)
    print(f"\nLength: {len(thread.main_caption)}")


def print_replies(thread: CaptionThread | None) -> None:
    if thread is None:
        print("(No caption thread)")
        return

    if not thread.replies:
        print("(No replies)")
        return

    for i, reply in enumerate(thread.replies, start=1):
        print_section(f"REPLY {i}")
        print(reply)
        print(f"\nLength: {len(reply)}")


def main() -> None:
    args = parse_args()
    selected_stage: PreviewStage = args.stage

    poster = PosterMastodon.__new__(PosterMastodon)

    pet = post_exceed_500_chars_limit_with_adoption_link()
    pipeline = poster.build_formatting_pipeline(pet)

    thread = (
        pipeline.value
        if pipeline.ok and isinstance(pipeline.value, CaptionThread)
        else None
    )

    sections = [
        PreviewSection(
            PreviewStage.PET,
            "PET",
            lambda: print_phase(pipeline, MastodonPhase.PET),
        ),
        PreviewSection(
            PreviewStage.POST,
            "POST OBJECT",
            lambda: print_phase(pipeline, MastodonPhase.POST),
        ),
        PreviewSection(
            PreviewStage.PREPARED_CAPTION,
            "PREPARED CAPTION",
            lambda: print_phase(pipeline, MastodonPhase.PREPARED_CAPTION),
        ),
        PreviewSection(
            PreviewStage.CAPTION_THREAD,
            "CAPTION THREAD",
            lambda: print_phase(pipeline, MastodonPhase.CAPTION_THREAD),
        ),
        PreviewSection(
            PreviewStage.MAIN,
            "MAIN POST",
            lambda: print_main_caption(thread),
        ),
        PreviewSection(
            PreviewStage.REPLIES,
            "REPLIES",
            lambda: print_replies(thread),
        ),
        PreviewSection(
            PreviewStage.TRACE,
            "FULL TRACE",
            lambda: print_trace(pipeline),
        ),
    ]

    render_sections(
        sections=sections,
        selected=selected_stage,
        all_stage=PreviewStage.ALL,
    )


if __name__ == "__main__":
    main()