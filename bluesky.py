import json
import os
import sys
from datetime import datetime

import requests

# ============ CONFIG ============
api_key = os.environ.get("ACCESS_KEY")
bsky_handle = os.environ.get("BLUESKY_TEST_HANDLE")
bsky_password = os.environ.get("BLUESKY_TEST_PASSWORD")

if not api_key:
    sys.exit("ACCESS_KEY not set")
if not bsky_handle or not bsky_password:
    sys.exit("Bluesky credentials not set")

# ============ FETCH PETS ============
url = "https://api.rescuegroups.org/v5/public/animals/search/available/dogs"
payload = {
    "data": {
        "filters": [
            {
                "fieldName": "status",
                "operation": "equals",
                "criteria": "Available",
            }
        ],
        "filterRadius": {"miles": 50, "postalcode": "02108"},
        "limit": 1,
    }
}
headers = {
    "Content-Type": "application/vnd.api+json",
    "Authorization": f"{api_key}",
}

response = requests.post(url, headers=headers, json=payload["data"], timeout=15)
response.raise_for_status()
data = response.json().get("data", [])
print("Fetched", len(data), "records")

if not data:
    sys.exit("No pets found")

# ============ EXTRACT PET INFO ============
pet = data[0]
attrs = pet["attributes"]

name = attrs.get("name", "Unknown")
if "*" in name:
    name = name.split("*")[0].strip()

pet_info = {
    "id": pet["id"],
    "name": name,
    "breed": attrs.get("breedString", "Unknown breed"),
    "age": attrs.get("ageString", "Unknown age"),
    "sex": attrs.get("sex", ""),
    "size": attrs.get("sizeGroup", ""),
    "photo_url": attrs.get("pictureThumbnailUrl"),
    "url": f"https://www.rescuegroups.org/pet/{pet['id']}",
}

print(f"Pet: {pet_info['name']}")

# ============ CREATE POST TEXT ============
post_text = f"""🐾 Meet {pet_info['name']}!

{pet_info['breed']} · {pet_info['age']} · {pet_info['sex']} · {pet_info['size']}

Adopt: {pet_info['url']}

#AdoptDontShop #Boston #DogsOfBluesky"""[:300]

print(f"Post:\n{post_text}\n")

# ============ BLUESKY LOGIN ============
login_response = requests.post(
    "https://bsky.social/xrpc/com.atproto.server.createSession",
    json={"identifier": bsky_handle, "password": bsky_password},
)
login_response.raise_for_status()
session = login_response.json()
access_token = session["accessJwt"]
did = session["did"]
print("Logged into Bluesky")

# ============ UPLOAD IMAGE ============
bsky_headers = {"Authorization": f"Bearer {access_token}"}
image_blob = None

if pet_info["photo_url"]:
    img_response = requests.get(pet_info["photo_url"])
    if img_response.status_code == 200:
        upload = requests.post(
            "https://bsky.social/xrpc/com.atproto.repo.uploadBlob",
            headers={**bsky_headers, "Content-Type": "image/jpeg"},
            data=img_response.content,
        )
        if upload.status_code == 200:
            image_blob = upload.json().get("blob")
            print("Image uploaded")

# ============ CREATE POST ============
record = {
    "$type": "app.bsky.feed.post",
    "text": post_text,
    "createdAt": datetime.utcnow().isoformat() + "Z",
}

if image_blob:
    record["embed"] = {
        "$type": "app.bsky.embed.images",
        "images": [{"alt": f"Photo of {pet_info['name']}", "image": image_blob}],
    }

post_response = requests.post(
    "https://bsky.social/xrpc/com.atproto.repo.createRecord",
    headers=bsky_headers,
    json={"repo": did, "collection": "app.bsky.feed.post", "record": record},
)
post_response.raise_for_status()

print(f"✅ Posted to Bluesky!")
print(json.dumps(post_response.json(), indent=2))