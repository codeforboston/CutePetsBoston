"""Manual CLI for exercising poster implementations with sample pet data.

Examples:
  python manually_test_post.py --poster instagram --username USER --password PASS
  python manually_test_post.py --poster instagram --username USER --session-id SESSION --settings-path session.json
  python manually_test_post.py --poster instagram --username USER --password PASS --bootstrap-settings-path session.json
"""

import argparse
import json
import sys
import time
from pathlib import Path
import os

import requests

from abstractions import AdoptablePet
# from poster_bluesky import PosterBluesky  # Temporarily disabled
from instagrapi import Client
from instagrapi.types import StoryMention, StoryMedia, StoryLink, StoryHashtag


def sample_pet():
    sample = {
        "attributes": {
            "name": "Doli",
            "breedString": "Husky / Shepherd / Mixed",
            "descriptionText": (
                "Hi hoomans, my name is Doli, and I'm in the prime of my life at about 11-years-old. "
                "Everyone comments on my sky blue eyes and thick husky-type hair that is every shade of gold you can imagine. "
                "At 50 lbs, I am a fit and healthy girl.\n\n"
                "I am very chill and quiet. That doesn't mean I don't get excited because I do! "
                "When the hoomans come home, I do a fun little wiggle dance to welcome them! "
                "I LOVE being outside and like going on walks and car rides.\n\n"
                "Hope to meet you soon! Doli"
            ),
            "pictureThumbnailUrl": "https://cdn.rescuegroups.org/8099/pictures/animals/10131/10131543/35520048.jpg?width=100",
            "slug": "adopt-doli-husky-dog",
        }
    }
    attrs = sample["attributes"]
    return AdoptablePet(
        name=attrs["name"],
        species="dog",
        breed=attrs["breedString"],
        location="Boston, MA",
        description=attrs["descriptionText"],
        adoption_url=f"https://www.rescuegroups.org/pet/{attrs['slug']}",
        image_url=attrs["pictureThumbnailUrl"],
    )


DEFAULT_SETTINGS_PATH = Path(__file__).with_name("instagrapi_settings.json")



def main():
    username = os.environ.get("INSTAGRAM_TEST_HANDLE")
    password = os.environ.get("INSTAGRAM_TEST_PASSWORD")
    print("username start")
    print(username)
    print("username end")

    cl = Client()
    cl.login(username, password)
    print("INSTA TEST")
    print(cl.media_pk_from_url("https://www.instagram.com/p/C1XPukLOXFgRKI3KqLjtD1NCUAkqloAnI_cAG00/"))
    media = cl.photo_upload(
        "https://cdn.rescuegroups.org/8099/pictures/animals/10131/10131543/35520048.jpg?width=100"
        "Test caption for photo with #hashtags and mention users such @example",
        extra_data={
            "custom_accessibility_caption": "alt text example",
            "like_and_view_counts_disabled": 1,
            "disable_comments": 1,
        }
    )
    print(media)


if __name__ == "__main__":
    sys.exit(main())
