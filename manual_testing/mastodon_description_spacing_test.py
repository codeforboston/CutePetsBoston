"""Publish the #177 regression fixture on the Mastodon test account."""

import argparse
import json
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from adoption_sources.rescue_groups import SourceRescueGroups
from social_posters.mastodon import PosterMastodon
from tests.test_rescue_groups import (
    EXPECTED_REX, REX_HTML, REX_TEXT,
    _make_animal, _make_org, _make_species_by_id,
)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    source = SourceRescueGroups(api_key="unused-fixture")
    pet = source._parse_animal(
        _make_animal(name="Rex", descriptionHtml=REX_HTML, descriptionText=REX_TEXT),
        {"org1": _make_org()}, _make_species_by_id(),
    )
    if pet is None or pet.description != EXPECTED_REX:
        raise RuntimeError("The #177 fixture did not retain its expected spacing.")

    # Require the explicitly named test token; never fall back to a prod token.
    token = os.environ.get("MASTODON_TEST_TOKEN")
    if not args.dry_run:
        if not token:
            raise RuntimeError("MASTODON_TEST_TOKEN is required for live testing.")
        os.environ["MASTODON_TOKEN"] = token
    poster = PosterMastodon()
    post = poster.format_post(pet)
    post.text = "[TEST #177] Description spacing regression — sample data.\n\n" + post.text
    post.tags = ["CutePetsBostonTest"]
    post.alt_text = "CutePetsBoston logo; this is a formatting test using sample data."
    root, replies = poster._format_caption_thread(post)
    captions = [root, *replies]
    for index, caption in enumerate(captions):
        print(f"\nStatus {index + 1} ({len(caption)} characters):\n{caption}")
    if args.dry_run:
        return

    if not poster.authenticate():
        raise RuntimeError("Mastodon test-account authentication failed.")
    client = poster._session
    account = client.account_verify_credentials()
    print(f"Authenticated test account: {account['url']}")
    image_path = Path(__file__).resolve().parents[1] / "web" / "apple-touch-icon.png"
    media = client.media_post(str(image_path), description=post.alt_text)

    report = {"account_url": account["url"], "verified": False, "statuses": []}
    report_path = Path("mastodon-spacing-result.json")
    for (_, _, status), caption in zip(
        poster._post_thread(client, root, replies, [str(media["id"])]), captions
    ):
        report["statuses"].append({
            "id": str(status["id"]), "url": status["url"], "caption": caption,
        })
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2))
        print(f"Posted: {status['url']}")
        if len(report["statuses"]) == 1:
            output = os.environ.get("GITHUB_OUTPUT")
            if output:
                with open(output, "a") as stream:
                    stream.write(f"post_id={status['id']}\npost_url={status['url']}\n")

    for posted in report["statuses"]:
        fetched = client.status(posted["id"])
        rendered = source._clean_html_description(fetched["content"])
        posted["rendered_text"] = rendered
        # Read our own status source to avoid URL display shortening in HTML.
        # Separately verify structural breaks in the rendered HTML below.
        saved_text = client.status_source(posted["id"])["text"]
        posted["saved_text"] = saved_text
        if saved_text != posted["caption"]:
            raise RuntimeError(f"Read-back text differs for {posted['url']}")
        for boundary in (
            "VT\n\nGood with dogs:", "intros\nGood with cats:",
            "House Trained: Working on it\n\nRex is",
        ):
            if boundary in posted["caption"] and boundary not in rendered:
                raise RuntimeError(f"Line breaks were lost for {posted['url']}")

    report["verified"] = True
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2))
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a") as stream:
            stream.write("## Mastodon #177 live spacing test\n\n")
            stream.write(f"Account: {account['url']}\n\n")
            for posted in report["statuses"]:
                stream.write(f"- [View test status]({posted['url']})\n")
            stream.write("\nRead-back verification passed for text and line breaks.\n")
    print("Live read-back verification passed.")


if __name__ == "__main__":
    main()
