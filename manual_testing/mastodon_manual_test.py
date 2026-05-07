import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from abstractions import Post, AdoptablePet
from social_posters.mastodon import PosterMastodon



def main():
    poster = PosterMastodon()
    pet = AdoptablePet("Brian", 
                        "Labrador Retriever", 
                        "White Labrador", 
                        "Quahog", 
                        "I am a writer!"*500, 
                        "http://www.davidgorman.com/4quartets/", 
                        "https://static.wikia.nocookie.net/familyguy/images/c/c2/FamilyGuy_Single_BrianWriter_R7.jpg/revision/latest?cb=20230807152447",
                        11, 
                        "Male", 
                        None, 
                        None
                    )

    if not poster.authenticate():
        print("Authentication failed!")
        exit(1)
    
    print("Authenticated to Mastodon!")

    post = poster.format_post(pet)

    target_url = "http://www.davidgorman.com/4quartets/"

    if target_url not in post.text:
        print("Adoption link not posted!")

    result = poster.publish(post)

    if result.success:
        print(f"Posted successfully! URL: {result.post_url}")
    else:
        print(f"Post failed: {result.error_message}")

if __name__ == "__main__":
    main()