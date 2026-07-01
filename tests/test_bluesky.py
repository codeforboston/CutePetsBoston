from abstractions import Post
from social_posters.bluesky import PosterBluesky


class TestBuildTextAndFacets:
    def setup_method(self):
        self.poster = PosterBluesky.__new__(PosterBluesky)

    def test_no_tags_no_link_produces_no_facets(self):
        post = Post(text="Hello, world!")
        text, facets = self.poster._build_text_and_facets(post)
        assert text == "Hello, world!"
        assert facets == []

    def test_link_without_tags_produces_link_facet(self):
        url = "https://example.com/adopt"
        post = Post(text=f"Meet Poppy!\n\n{url}", link=url)
        text, facets = self.poster._build_text_and_facets(post)

        assert text == post.text
        assert len(facets) == 1
        enc = text.encode("utf-8")
        f = facets[0]
        assert enc[f["index"]["byteStart"] : f["index"]["byteEnd"]] == url.encode("utf-8")
        assert f["features"][0]["$type"] == "app.bsky.richtext.facet#link"
        assert f["features"][0]["uri"] == url

    def test_link_and_tags_facets_sorted_by_byte_start(self):
        url = "https://rg.org/pet/1"
        post = Post(
            text=f"Adopt me!\n\n{url}",
            tags=["AdoptDontShop", "Boston", "DogsOfBluesky"],
            link=url,
        )
        text, facets = self.poster._build_text_and_facets(post)

        assert text.endswith("\n\n#AdoptDontShop #Boston #DogsOfBluesky")
        assert len(facets) == 4
        assert facets[0]["features"][0]["$type"] == "app.bsky.richtext.facet#link"
        assert facets[0]["features"][0]["uri"] == url
        for facet in facets[1:]:
            assert facet["features"][0]["$type"] == "app.bsky.richtext.facet#tag"

    def test_long_body_still_includes_full_url_and_link_facet_with_tags(self):
        """Without preserving the URL suffix, body[:max_body] would drop the link entirely."""
        url = "https://www.rescuegroups.org/html/sa_details.html?id=12345"
        tags = ["AdoptDontShop", "Boston", "DogsOfBluesky"]
        tags_section = " ".join(f"#{t}" for t in tags)
        filler = "x" * 400
        post = Post(text=f"{filler}\n\n{url}", tags=tags, link=url)
        text, facets = self.poster._build_text_and_facets(post)

        assert url in text
        assert text.endswith(f"\n\n{tags_section}")
        assert len(text) <= 300
        link_facets = [f for f in facets if f["features"][0]["$type"] == "app.bsky.richtext.facet#link"]
        assert len(link_facets) == 1
        assert link_facets[0]["features"][0]["uri"] == url

    def test_url_that_crosses_body_limit_is_preserved_with_tags(self):
        url = "https://www.smalldogrescuene.org/adoptable-dogs/#action_0=pet&animalID_0=22537020&petIndex_0=-1"
        tags = ["AdoptDontShop", "Boston", "Cranston", "DogsOfBluesky"]
        tags_section = " ".join(f"#{t}" for t in tags)
        body = (
            "Hi, I'm Glandis in TX! I'm a Chihuahua / Mixed (short coat) "
            "looking for a forever home in Cranston, RI.\n\n"
            "8 Months - Female - Small size\n\n"
            f"Learn more and adopt me: {url}"
        )
        post = Post(text=body, tags=tags, link=url)
        text, facets = self.poster._build_text_and_facets(post)

        assert url in text
        assert "petIndex_0=-1" in text
        assert "Learn more and ado " not in text
        assert text.endswith(f"\n\n{tags_section}")
        assert len(text) <= 300
        link_facets = [f for f in facets if f["features"][0]["$type"] == "app.bsky.richtext.facet#link"]
        assert len(link_facets) == 1
        assert link_facets[0]["features"][0]["uri"] == url

    def test_tags_produce_facets_with_correct_byte_offsets(self):
        post = Post(text="Adopt me!", tags=["AdoptDontShop", "Boston", "DogsOfBluesky"])
        text, facets = self.poster._build_text_and_facets(post)

        assert text == "Adopt me!\n\n#AdoptDontShop #Boston #DogsOfBluesky"
        assert len(facets) == 3

        encoded = text.encode("utf-8")

        for facet, tag_name in zip(facets, ["AdoptDontShop", "Boston", "DogsOfBluesky"]):
            start = facet["index"]["byteStart"]
            end = facet["index"]["byteEnd"]
            assert encoded[start:end] == f"#{tag_name}".encode("utf-8")
            assert facet["features"][0]["$type"] == "app.bsky.richtext.facet#tag"
            assert facet["features"][0]["tag"] == tag_name
