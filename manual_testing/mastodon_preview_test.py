import argparse
import os
import sys
from dataclasses import asdict
from enum import StrEnum
from pprint import pprint

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


def should_show(selected: PreviewStage, target: PreviewStage) -> bool:
    return selected in (target, PreviewStage.ALL)


def main() -> None:
    args = parse_args()
    stage: PreviewStage = args.stage

    poster = PosterMastodon.__new__(PosterMastodon)

    pet = post_exceed_500_chars_limit_with_adoption_link()
    post = poster.format_post(pet)

    main_caption, replies, debug = poster._format_caption_thread_with_trace(post)

    if should_show(stage, PreviewStage.PET):
        print_section("PET")
        pprint(pet)

    if should_show(stage, PreviewStage.POST):
        print_section("POST OBJECT")
        pprint(post)

    if should_show(stage, PreviewStage.DEBUG):
        print_section("DEBUG PIPELINE")
        pprint(asdict(debug))

    if should_show(stage, PreviewStage.MAIN):
        print_section("MAIN POST")
        print(main_caption)
        print(f"\nLength: {len(main_caption)}")

    if should_show(stage, PreviewStage.REPLIES):
        for i, reply in enumerate(replies, start=1):
            print_section(f"REPLY {i}")
            print(reply)
            print(f"\nLength: {len(reply)}")


if __name__ == "__main__":
    main()