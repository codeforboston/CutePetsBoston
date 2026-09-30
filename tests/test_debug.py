from io import StringIO

from abstractions import Post
from social_posters.debug import PosterDebug


def test_debug_poster_writes_to_a_text_stream() -> None:
    stream = StringIO()

    result = PosterDebug(stream=stream).publish(Post(text="Meet Poppy!"))

    assert result.success
    assert result.post_id == "debug"
    assert "Meet Poppy!" in stream.getvalue()
