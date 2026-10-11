"""Regression tests for RescueGroups' joined descriptionText in issue #177."""

from unittest.mock import Mock, patch

import pytest

from adoption_sources.rescue_groups import SourceRescueGroups
from social_posters.mastodon import MASTODON_CHARACTER_LIMIT, PosterMastodon
from tests.test_rescue_groups import _make_animal, _make_org, _make_species_by_id


# Transcribed from the API log screenshots attached to #177. descriptionText
# loses the separators that are still present in descriptionHtml.
REX_HTML = (
    "<p>Adoptable in: MA, RI, NH, CT, and VT<br /><br />"
    "Good with dogs: Yes, with proper intros<br />"
    "Good with cats: Unknown, likely yes<br />"
    "Good with kids: Unknown, likely yes<br />"
    "Crate trained: Working on it<br />"
    "House Trained: Working on it<br /><br />"
    "Rex is a handsome, affectionate boy who&rsquo;s ready to "
    "wiggle his way into your heart!<br /><br />"
    "Please apply at <a href='http://www.lasthopek9.org/'>"
    "www.lasthopek9.org</a>.</p>"
)
REX_TEXT = (
    "Adoptable in: MA, RI, NH, CT, and VTGood with dogs: Yes, with proper intros"
    "Good with cats: Unknown, likely yesGood with kids: Unknown, likely yes"
    "Crate trained: Working on itHouse Trained: Working on it"
    "Rex is a handsome, affectionate boy who&rsquo;s ready to "
    "wiggle his way into your heart!Please apply at www.lasthopek9.org."
)
EXPECTED_REX = (
    "Adoptable in: MA, RI, NH, CT, and VT\n\n"
    "Good with dogs: Yes, with proper intros\n"
    "Good with cats: Unknown, likely yes\n"
    "Good with kids: Unknown, likely yes\n"
    "Crate trained: Working on it\n"
    "House Trained: Working on it\n\n"
    "Rex is a handsome, affectionate boy who’s ready to "
    "wiggle his way into your heart!\n\n"
    "Please apply at www.lasthopek9.org."
)


def parse_description(**attributes):
    pet = SourceRescueGroups(api_key="dummy")._parse_animal(
        _make_animal(**attributes), {"org1": _make_org()}, _make_species_by_id()
    )
    assert pet is not None
    return pet.description


def test_prefers_html_with_original_rex_line_breaks():
    assert parse_description(descriptionHtml=REX_HTML, descriptionText=REX_TEXT) == EXPECTED_REX


@pytest.mark.parametrize("markup", [None, "", "  ", "<p>&nbsp;</p>", "<img src='tracker'>"])
def test_falls_back_to_text_when_html_has_no_readable_content(markup):
    assert parse_description(descriptionHtml=markup, descriptionText="Meet Rex &amp; friends.") == "Meet Rex & friends."


def test_html_only_description_is_used():
    assert parse_description(descriptionHtml="<p>Meet Rex!</p><p>He loves walks.</p>") == "Meet Rex!\n\nHe loves walks."


@pytest.mark.parametrize("br", ["<br>", "<br/>", "<br />", "<BR>"])
def test_html_break_variants_separate_words(br):
    assert parse_description(descriptionHtml=f"Meet Rex!{br}Good with dogs.") == "Meet Rex!\nGood with dogs."


def test_preserves_inline_words_and_separates_blocks_and_lists():
    markup = (
        "<div>Meet <strong>Rex</strong>! He is house<span>trained</span>.</div>"
        "<ul><li>Good with dogs</li><li>Crate trained</li></ul>"
        "<p>Apply&nbsp;today: <a href='https://example.org/adopt'>adopt Rex</a>.</p>"
        "<script>tracking code</script><style>hidden styling</style><!-- comment -->"
    )
    assert parse_description(descriptionHtml=markup) == (
        "Meet Rex! He is housetrained.\n\nGood with dogs\nCrate trained\n\n"
        "Apply today: adopt Rex."
    )


def test_source_formatting_whitespace_does_not_create_extra_paragraphs():
    markup = "\n  <p>Meet\n    <b>Rex</b>!</p>\n  <p>He loves walks.</p>\n"
    assert parse_description(descriptionHtml=markup) == "Meet Rex!\n\nHe loves walks."


def test_html_entities_are_displayed_as_text_not_parsed_as_tags():
    assert parse_description(descriptionHtml="<p>Rex &lt;3 walks &amp; treats.</p>") == "Rex <3 walks & treats."


def test_rex_spacing_reaches_mastodon_status_requests():
    response = Mock()
    response.json.return_value = {
        "data": [_make_animal(name="Rex", descriptionHtml=REX_HTML, descriptionText=REX_TEXT)],
        "included": [
            {"type": "orgs", "id": "org1", "attributes": _make_org()},
            {"type": "species", "id": "8", "attributes": {"plural": "dogs"}},
        ],
    }
    with patch("adoption_sources.rescue_groups._session_with_retries") as session:
        session.return_value.post.return_value = response
        (pet,) = SourceRescueGroups(api_key="dummy").fetch_pets()

    assert pet.description == EXPECTED_REX
    poster = PosterMastodon()
    post = poster.format_post(pet)
    assert EXPECTED_REX in post.text
    root, replies = poster._format_caption_thread(post)
    client = Mock()
    client.status_post.side_effect = [{"id": str(i)} for i in range(1 + len(replies))]
    list(poster._post_thread(client, root, replies, ["media-id"]))
    payloads = [call.args[0] for call in client.status_post.call_args_list]
    assert all(len(text) <= MASTODON_CHARACTER_LIMIT for text in payloads)
    sent = "\n".join(payloads)
    assert "VT\n\nGood with dogs:" in sent
    assert "intros\nGood with cats:" in sent
    assert "House Trained: Working on it\n\nRex is" in sent
    assert "VTGood" not in sent
    assert "itHouse" not in sent
    assert "itRex" not in sent
    assert "<br" not in sent
    assert "<p>" not in sent
