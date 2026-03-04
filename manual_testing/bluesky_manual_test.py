import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from abstractions import Post
from social_posters.bluesky import PosterBluesky

def main():
    poster = PosterBluesky()
    
    if not poster.authenticate():
        print("Authentication failed!")
        exit(1)
    
    print("Authenticated to Bluesky!")
    
    test_post = Post(
        text="Hello from CutePetsBoston! This is a test post.",
        tags=["adoptdontshop", "CutePetsBoston", "test"]
    )
    
    result = poster.publish(test_post)
    
    if result.success:
        print(f"Posted successfully! URL: {result.post_url}")
    else:
        print(f"Post failed: {result.error_message}")

if __name__ == "__main__":
    main()
