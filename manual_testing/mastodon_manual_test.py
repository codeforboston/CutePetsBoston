import argparse
import logging
import os
import sys
import time
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from abstractions import AdoptablePet
from social_posters.mastodon import PosterMastodon

logger = logging.getLogger(__name__)


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        stream=sys.stdout,
    )

def post_exceed_500_chars_limit_with_adoption_link():
    pet = AdoptablePet("Brian", 
                        "Labrador Retriever", 
                        "White Labrador", 
                        "Quahog", 
                        "I am a writer! Post exceeds limit with adoption link"*200, 
                        "http://www.davidgorman.com/4quartets/", 
                        "https://static.wikia.nocookie.net/familyguy/images/c/c2/FamilyGuy_Single_BrianWriter_R7.jpg/revision/latest?cb=20230807152447",
                        11, 
                        "Male", 
                        None, 
                        None
                    )
    return pet

def post_exceed_500_chars_limit_without_adoption_link():
    pet = AdoptablePet("Vinny", 
                        "Unknown", 
                        "Unknown", 
                        "Quahog", 
                        "I am 1/16th cat! Post exceeds word limit without adoption link."*1000, 
                        None, 
                        "https://static.wikia.nocookie.net/familyguyfanon/images/e/ec/Vinny_Griffin.png/revision/latest?cb=20161129110103",
                        None, 
                        "Male", 
                        None, 
                        None
                    )
    return pet


def post_within_500_chars_limit_with_adoption_link():
    pet = AdoptablePet("Ernie", 
                        "Chicken", 
                        "Unknown", 
                        "Quahog", 
                        "cluck. Post within word limit with adoption link.", 
                        "https://poets.org/poem/having-coke-you", 
                        "https://static.wikia.nocookie.net/villains/images/2/2e/Giant_chicken_animation.png/revision/latest?cb=20220615120124",
                        None, 
                        "Male", 
                        None, 
                        None
                    )
    return pet

def post_within_500_chars_limit_without_adoption_link():
    pet = AdoptablePet("Pouncy", 
                        "Cat", 
                        "Unknown", 
                        "Quahog", 
                        "Meow. Post within 500 limit without adoption link", 
                        None, 
                        "https://static.wikia.nocookie.net/villains/images/7/76/Pouncey.webp/revision/latest?cb=20220403224856",
                        None, 
                        "Male", 
                        None, 
                        None
                    )
    return pet

def post_about_800_chars_with_adoption_link():
    pet = AdoptablePet("Kool-Aid Man", 
                        "Unknown", 
                        "Unknown", 
                        "Quahog", 
                        "OH YEAH!"*100, 
                        None, 
                        "https://static.wikia.nocookie.net/familyguy/images/8/8b/Koolaid.jpg/revision/latest?cb=20090128174245",
                        None, 
                        "Unknown", 
                        None, 
                        None
                    )
    return pet

def post_unicode():
    pet = AdoptablePet("Vinny", 
                        "Unknown", 
                        "Unknown", 
                        "Quahog", 
                        "🐶❤️ 可爱的小狗 Friendly \"lap cat\" @ shelter #AdoptMe", 
                        None, 
                        "https://static.wikia.nocookie.net/familyguyfanon/images/e/ec/Vinny_Griffin.png/revision/latest?cb=20161129110103",
                        None, 
                        "Male", 
                        None, 
                        None
                    )
    return pet

testing_cases = [
    #post_exceed_500_chars_limit_with_adoption_link,
    post_about_800_chars_with_adoption_link,
    #post_exceed_500_chars_limit_without_adoption_link,
    #post_within_500_chars_limit_with_adoption_link,
    #post_within_500_chars_limit_without_adoption_link,
    #post_unicode,
]

def main():
    configure_logging()

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Format and split the Mastodon post without authenticating or publishing.",
    )
    args = parser.parse_args()

    poster = PosterMastodon()

    if not args.dry_run and not poster.authenticate():
        print("Authentication failed!")
        exit(1)
    
    if not args.dry_run:
        print("Authenticated to Mastodon!")

    for pet in testing_cases:
        pet_instance = pet()
        
        post = poster.format_post(pet_instance)
        target_url = pet_instance.adoption_url
        if target_url and (target_url not in post.text):
            print("Adoption link not posted!")

        if args.dry_run:
            main_caption, replies = poster._format_caption_thread(post)
            logger.info("Mastodon dry run post text: %s", post.text)
            logger.info("Mastodon dry run main caption: %s", main_caption)
            logger.info("Mastodon dry run replies: %s", replies)
            continue

        result = poster.publish(post)

        if result.success:
            print(f"Posted successfully! URL: {result.post_url}")
        else:
            print(f"Post failed: {result.error_message}")
        time.sleep(1)


if __name__ == "__main__":
    main()
