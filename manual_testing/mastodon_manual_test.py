import sys, os
import time
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from abstractions import AdoptablePet
from social_posters.mastodon import PosterMastodon

def postExceed500CharsLimitWithAdoptionLink():
    pet = AdoptablePet("Brian", 
                        "Labrador Retriever", 
                        "White Labrador", 
                        "Quahog", 
                        "I am a writer! Post exceeds limit with adoption link"*1000, 
                        "http://www.davidgorman.com/4quartets/", 
                        "https://static.wikia.nocookie.net/familyguy/images/c/c2/FamilyGuy_Single_BrianWriter_R7.jpg/revision/latest?cb=20230807152447",
                        11, 
                        "Male", 
                        None, 
                        None
                    )
    return pet

def postExceed500CharsLimitWithoutAdoptionLink():
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


def postWithin500CharsLimitWithAdoptionLink():
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

def postWithin500CharsLimitWithoutAdoptionLink():
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

def postUnicode():
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

testingCases = [
    postExceed500CharsLimitWithAdoptionLink,
    postExceed500CharsLimitWithoutAdoptionLink,
    postWithin500CharsLimitWithAdoptionLink,
    postWithin500CharsLimitWithoutAdoptionLink,
    postUnicode
]

def main():
    poster = PosterMastodon()

    if not poster.authenticate():
        print("Authentication failed!")
        exit(1)
    
    print("Authenticated to Mastodon!")

    for pet in testingCases:
        pet_instance = pet()
        
        post = poster.format_post(pet_instance)
        target_url = pet_instance.adoption_url
        if target_url and (target_url not in post.text):
            print("Adoption link not posted!")

        result = poster.publish(post)

        if result.success:
            print(f"Posted successfully! URL: {result.post_url}")
        else:
            print(f"Post failed: {result.error_message}")
        time.sleep(1)


if __name__ == "__main__":
    main()