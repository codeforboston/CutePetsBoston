from abstractions import Post
from social_posters.bluesky import PosterBluesky


class TestBuildTextAndFacets:
    def setup_method(self):
        self.poster = PosterBluesky.__new__(PosterBluesky)

    def test_no_tags_produces_no_facets(self):
        post = Post(text="Hello, world!")
        text, facets = self.poster._build_text_and_facets(post)
        assert text == "Hello, world!"
        assert facets == []

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
