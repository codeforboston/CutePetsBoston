import argparse
import os
import sys
from dataclasses import asdict
from enum import StrEnum
from pprint import pprint
from typing import Callable

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from mastodon_manual_test import post_exceed_500_chars_limit_with_adoption_link
from social_posters.mastodon import PosterMastodon

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
"""
class PreviewStage(StrEnum):
    PET = "pet"
    POST = "post"
    DEBUG = "debug"
    MAIN = "main"
    REPLIES = "replies"
    ALL = "all"


def print_section(title: str) -> None:
    print("\n" + "=" * 60)
    print(title)
    print("=" * 60)


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


def includes_stage(selected: PreviewStage, target: PreviewStage) -> bool:
    return selected in (target, PreviewStage.ALL)


def main() -> None:
    args = parse_args()
    stage: PreviewStage = args.stage

    poster = PosterMastodon.__new__(PosterMastodon)

    pet = post_exceed_500_chars_limit_with_adoption_link()
    post = poster.format_post(pet)

    main_caption, replies, trace = poster._format_caption_thread_with_trace(post)

    sections: list[tuple[PreviewStage, str, Callable[[], None]]] = [
        (
            PreviewStage.PET,
            "PET",
            lambda: pprint(pet),
        ),
        (
            PreviewStage.POST,
            "POST OBJECT",
            lambda: pprint(post),
        ),
        (
            PreviewStage.DEBUG,
            "DEBUG PIPELINE",
            lambda: pprint(asdict(trace)),
        ),
        (
            PreviewStage.MAIN,
            "MAIN POST",
            lambda: print_main_caption(main_caption),
        ),
        (
            PreviewStage.REPLIES,
            "REPLIES",
            lambda: print_replies(replies),
        ),
    ]

    for target_stage, title, renderer in sections:
        if includes_stage(stage, target_stage):
            print_section(title)
            renderer()


def print_main_caption(main_caption: str) -> None:
    print(main_caption)
    print(f"\nLength: {len(main_caption)}")


def print_replies(replies: list[str]) -> None:
    if not replies:
        print("(No replies)")

    for i, reply in enumerate(replies, start=1):
        print_section(f"REPLY {i}")
        print(reply)
        print(f"\nLength: {len(reply)}")


if __name__ == "__main__":
    main()