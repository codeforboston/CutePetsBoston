# RFC 0002 — Animal Videos Handling for cutepetsboston.com

| | |
|---|---|
| **Status** | Draft (living doc — new thoughts land in §8) |
| **Author** | Chuck Doucette |
| **Date** | 2026-11-05 |
| **Branch** | `* document-videos-plan-227` |

---

## 1. Goals

The goal of CutePetsBoston is to advertise pets (in the Boston area) to get more of them adopted. We advertise them on various social media platforms. Every pet has a name, a breed (e.g. dog or cat) and a description. Most of them have associated pictures, and some of them have associated videos. We only advertise pets that have pictures. If there is one or more associated videos, we would like to share them also (or instead of).

---

## 2. Open Questions

1. I assume we only advertise a pet with associated media. Currently, we only advertise pets with an associated picture. If there is a pet with one or more associated videos, but **no** associated pictures - should they still be candidates for advertising? _I think pets with just video **should** be advertised, but **not** immediately._
2. If both a picture and a video are available, should we attempt to share **both** types of media, or just one or the other? _Personally, I would show just videos if they are available, and then pictures if they are also available (perhaps in a response)._
3. I assume that for each picture, we must download it from its original location and then upload it to the social media platform. Must we do the same for each video (on each social media platforn)?  _FYI - from what little sample data I saw, all associated videos are hosted on YouTube._ I would prefer **not** to download and upload the video for each social media platform.
4. On BlueSky, there is a builtin widget to watch a YouTube video within BlueSky rather than launching YouTube, and it is visible and clickable if you include the YouTube link in the post text. I think that is the quickest and easiest way to make videos available, but it would interfere with the current link to the source organization sponsering the pet for adoption (click here for more information). This may only be an issue on BlueSky - I'm not sure how YouTube videos could or should be handled on other social media platforms.

---

## 3. Plan Summary (TL;DR)

Our animal data is obtained by the Rescue Groups API. Every animal we fetch will:
- be available for adoption
- have an associated picture
It may or may *not* have some associated videos. If those videos are available, they should be displayed on each social media platform that we support.

This document will describe how to
- Obtain the URLs of any animal videos from the Rescue Groups API
- Extract and retain that video data in a DTO object (AdoptablePet)
- Present those videos as part of a post on each social media platform.

This document will describe
- the implementation plan (including whether it should be done all at once in a super branch, or piece by piece)
- the testing plan for each layer

This initial version of this document will *not* describe the particular implementation plan for each social media poster (which will be done after more research on each platform).

---

## 4. Data access layer

The primary endpoint of the Rescue Groups API is:
**GET** _/public/animals/_
which returns animals as JSON objects.

Not all animal data is encapsulated directly in animal objects. Some are returned as a set of separate but related objects.

So, for each animal object, you will see:
- **"type"** : "animals"
- **"id"** : "1234567"
- **"attributes"**
- **"relationships"** _(foreign keys to related data)_

In addition, the block of related data is returned as
- **"included"**

Every object in "included" will include:
- **"type"**
- **"id"**
- **"attributes"**

In the URL query string, we will need to adjust:
- fields[animals]=**videoCount,videoUrlCount** _(to include any video counts in attributes, and videourls in relationships)_
- included=**videourls** _(to include any related videourls objects)_

Using the existing URL with the view named _"haspic"_ (each animal has at least one associated picture), and the modified query string above, any associated videos will also be returned. It does not guarantee that any returned animal also has one or more associated videos. Use a filter like this to ensure that a returned animal has at least one associated video:

```
{
    "data": {
        "filters": [
            { "fieldName": "animals.videoCount",    "operation": "greaterthanorequal", "criteria": 1 },
            { "fieldName": "animals.videoUrlCount", "operation": "greaterthanorequal", "criteria": 1 }
        ],
        "filterProcessing": "1 OR 2"
    }
}
```

### Manual source data

Find an animal that includes associated video, and it to the file manual.json.

---

## 5. Data Transfer Objects

### AdoptablePet

Add the instance variable:
```
    video_urls: list[str] = field(default_factory=list)
```

### Post

Add the instance variable:
```
    video_urls: list[str] = field(default_factory=list)
```

To instantiate the corresponding Post instance variable video_urls, just copy the AdoptablePet instance variable video_urls.

---

## 7. Posters

- Modify Post in abstractions.py to add video_urls.
- Also, clone select_image_urls to select_video_urls. _How many videos can we post - maybe just 1?_

### BlueSky

_The following are first thougts about the implementation on BlueSky._

If a Post contains any video_urls, pick the first one and add it as a link at the bottom of the post text. Assuming the link references YouTube, BlueSky will automatically include a video preview widget, and preclude the necessity to download and upload the video. This would likely replace the link to get more information from the adoption agency. I'm not sure if a post can contain pictures *and* videos. I'm sure it can contain pictures and a link, but if the video link is to YouTube, a thumbnail image would be included.

---

## 6. Testing Plan

It appears that the existing implementation does not make a clear distinction between the data access layer (text, JSON objects, dictionaries) and the service layer with Data Transfer Objects (_AdoptablePet_). I'm saying that the code to build an _AdoptablePet_ should be the same no matter what the source of the data is. _SourceManual_ **and** _SourceRescueGroups_ should just fetch data return an array of dictionaries. That would be a _large_ refactor, and therefore is for another time. Thus, the tests cannot be completed until both layers are implemented.

### test_source_manual.py

Assert that there is at least one pet with video_urls not empty.

### test_rescue_groups.py

**I'm not sure how to alter these tests, since it is possible that no pet will have any associated video, and that is the point of this implementation.**

### bluesky_manual_test.py

In a draft PR:
- Change the source to SourceManual.
- Copy and paste the code about with_images and change the pasted code to with_videos.
- Comment out the with_images code.
- Change the random selection of a pet from with_imagage to a random selection of a pet from with_videos.
- Run the test and see the resulting video on BlueSky

**How do you run the manual tests?**

---

## 7. Rollout plan

After approving (and merging) the PR with this document, and another PR with an added animal in manual.json:

- One issue which will
-- add video_urls fields and processing to:
--- AdoptablePet
--- SourceManual
--- SourceRescueGroups
--- Post
-- Alter test_source_manual (see above), but **not** test_rescue_groups _(since it is currently not clear how to test that)_.
- A subsequent issue for each social media poster (order TBD), which includes implementation **and** tests):
-- BlueSky
-- Mastadon
-- Instagram
