import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from abstractions import Post
from social_posters.mastodon import PosterMastodon



def main():
    poster = PosterMastodon()

    if not poster.authenticate():
        print("Authentication failed!")
        exit(1)
    
    print("Authenticated to Mastodon!")

    post = Post(
        text="Test post",
        image_url="https://static.wikia.nocookie.net/familyguy/images/c/c2/FamilyGuy_Single_BrianWriter_R7.jpg/revision/latest?cb=20230807152447",
        alt_text="Cute animal",
        tags=["Test", "Mastodon"],
    )

    result = poster.publish(post)

    if result.success:
        print(f"Posted successfully! URL: {result.post_url}")
    else:
        print(f"Post failed: {result.error_message}")

if __name__ == "__main__":
    main()