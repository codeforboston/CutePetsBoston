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
