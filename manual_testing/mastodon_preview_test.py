import os, sys 
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from social_posters.mastodon import PosterMastodon
from mastodon_manual_test import post_exceed_500_chars_limit_with_adoption_link

poster = PosterMastodon.__new__(PosterMastodon)

pet = post_exceed_500_chars_limit_with_adoption_link()
post = poster.format_post(pet)

main_caption, replies = poster._format_caption_thread(post)

print("\n" + "=" * 60)
print("MAIN POST")
print("=" * 60)
print(main_caption)
print(f"\nLength: {len(main_caption)}")

for i, reply in enumerate(replies, start=1):
    print("\n" + "=" * 60)
    print(f"REPLY {i}")
    print("=" * 60)
    print(reply)
    print(f"\nLength: {len(reply)}")