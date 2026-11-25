import json
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, Mock

import pytest
import requests

from database import read_database
from refresh_pet_statuses import main, refresh_statuses


def animal_response(pet_id, status_id="3", name="Adopted"):
    response = Mock()
    response.json.return_value = {
        "data": [{"type": "animals", "id": pet_id, "relationships": {"statuses": {"data": [{"id": status_id}]}}}],
        "included": [{"type": "statuses", "id": status_id, "attributes": {"name": name}}],
    }
    return response


def test_refresh_saves_status_and_observation_time_without_changing_posts(tmp_path):
    path = tmp_path / "database.json"
    posts = [{"pet_id": "123", "platform": "Bluesky", "post_id": "post-1", "metrics": []}]
    path.write_text(
        json.dumps(
            {
                "posted_pets": [{"name": "Poppy", "pet_id": "123", "posted_at": "2026-10-01T00:00:00+00:00"}],
                "posts": posts,
            }
        )
    )
    session = Mock()
    session.get.return_value = animal_response("123")

    refresh_statuses(path, session=session, now=datetime(2026, 11, 18, tzinfo=timezone.utc))

    data = read_database(path)
    assert data.get("posted_pets", [])[0].get("status_id") == "3"
    assert data.get("posted_pets", [])[0].get("status_name") == "Adopted"
    assert data.get("posted_pets", [])[0].get("status_observed_at") == "2026-11-18T00:00:00+00:00"
    assert data.get("posts", []) == posts


@pytest.mark.parametrize(
    "failure",
    [
        requests.Timeout(),
        {"data": []},
        {"data": [{"id": "123"}]},
        {
            "data": [{"id": "123", "relationships": {"statuses": {"data": {"id": "3"}}}}],
            "included": [{"type": "statuses", "id": "3", "attributes": None}],
        },
    ],
)
def test_unavailable_status_preserves_known_value_and_does_not_stop_other_pets(tmp_path, failure):
    path = tmp_path / "database.json"
    known = {
        "name": "Poppy",
        "pet_id": "123",
        "posted_at": "2026-10-01T00:00:00+00:00",
        "status_id": "1",
        "status_name": "Available",
        "status_observed_at": "2026-11-10T00:00:00+00:00",
    }
    path.write_text(
        json.dumps({"posted_pets": [known, {"name": "Spot", "pet_id": "456", "posted_at": known["posted_at"]}]})
    )
    session = Mock()
    if isinstance(failure, Exception):
        first = failure
    else:
        first = Mock()
        first.json.return_value = failure
    session.get.side_effect = [first, animal_response("456")]

    refresh_statuses(path, session=session, now=datetime(2026, 11, 18, tzinfo=timezone.utc))

    data = read_database(path)
    assert data.get("posted_pets", [])[0].get("status_name") == "Available"
    assert data.get("posted_pets", [])[0].get("status_observed_at") == "2026-11-10T00:00:00+00:00"
    assert data.get("posted_pets", [])[1].get("status_name") == "Adopted"


def test_daily_refresh_skips_adopted_missing_ids_and_pets_not_due(tmp_path):
    path = tmp_path / "database.json"
    adopted = {
        "name": "Poppy",
        "pet_id": "123",
        "posted_at": "2026-10-01T00:00:00+00:00",
        "status_name": "Adopted",
        "status_observed_at": "2026-11-01T00:00:00+00:00",
    }
    path.write_text(
        json.dumps(
            {
                "posted_pets": [
                    adopted,
                    {"name": "No ID", "pet_id": None, "posted_at": adopted["posted_at"]},
                    {"name": "Blank ID", "pet_id": " ", "posted_at": adopted["posted_at"]},
                    {
                        "name": "Spot",
                        "pet_id": "456",
                        "posted_at": adopted["posted_at"],
                        "status_checked_at": "2026-11-17T20:00:00+00:00",
                    },
                    {"name": "Rex", "pet_id": "789", "posted_at": adopted["posted_at"]},
                ]
            }
        )
    )
    session = Mock()
    session.get.return_value = animal_response("789", "1", "Available")
    now = datetime(2026, 11, 18, tzinfo=timezone.utc)

    refresh_statuses(path, session=session, now=now)
    refresh_statuses(path, session=session, now=now + timedelta(hours=4))

    assert read_database(path).get("posted_pets", [])[0] == adopted
    assert read_database(path).get("posted_pets", [])[4].get("status_name") == "Available"
    assert session.get.call_count == 1


@pytest.mark.parametrize("missing_http_status", [200, 404])
def test_missing_record_backs_off_after_a_week_and_returns_to_daily_when_found(tmp_path, missing_http_status):
    path = tmp_path / "database.json"
    path.write_text(
        json.dumps({"posted_pets": [{"name": "Poppy", "pet_id": "123", "posted_at": "2026-10-01T00:00:00+00:00"}]})
    )
    session = Mock()
    missing = Mock()
    missing.status_code = missing_http_status
    if missing_http_status == 404:
        missing.raise_for_status.side_effect = requests.HTTPError(response=missing)
    missing.json.return_value = {"data": []}
    session.get.return_value = missing
    start = datetime(2026, 11, 1, tzinfo=timezone.utc)
    for day in range(8):
        refresh_statuses(path, session=session, now=start + timedelta(days=day))

    refresh_statuses(path, session=session, now=start + timedelta(days=8))
    assert session.get.call_count == 8
    assert "status_name" not in read_database(path).get("posted_pets", [])[0]

    session.get.return_value = animal_response("123", "1", "Available")
    refresh_statuses(path, session=session, now=start + timedelta(days=14))
    refresh_statuses(path, session=session, now=start + timedelta(days=15))
    assert session.get.call_count == 10
    assert read_database(path).get("posted_pets", [])[0].get("status_observed_at") == "2026-11-16T00:00:00+00:00"


def test_status_metadata_fallback_is_cached_for_the_run(tmp_path):
    path = tmp_path / "database.json"
    path.write_text(
        json.dumps(
            {
                "posted_pets": [
                    {"name": "Poppy", "pet_id": "123", "posted_at": "2026-10-01T00:00:00+00:00"},
                    {"name": "Spot", "pet_id": "456", "posted_at": "2026-10-01T00:00:00+00:00"},
                ]
            }
        )
    )
    first, second = animal_response("123"), animal_response("456")
    first.json.return_value.pop("included")
    second.json.return_value.pop("included")
    metadata = Mock()
    metadata.json.return_value = {"data": {"type": "statuses", "id": "3", "attributes": {"name": "Adopted"}}}
    session = Mock()
    session.get.side_effect = [first, metadata, second]

    refresh_statuses(path, session=session)

    assert [pet.get("status_name") for pet in read_database(path).get("posted_pets", [])] == ["Adopted", "Adopted"]
    assert session.get.call_count == 3


def test_refresh_command_uses_only_source_credentials_and_the_supplied_database(tmp_path, monkeypatch):
    path = tmp_path / "database.json"
    path.write_text(
        json.dumps({"posted_pets": [{"name": "Poppy", "pet_id": "123", "posted_at": "2026-10-01T00:00:00+00:00"}]})
    )
    monkeypatch.setenv("CUTEPETSBOSTON_RESCUEGROUPS_API_KEY", "test-source-key")
    for key in ("BLUESKY_HANDLE", "BLUESKY_PASSWORD", "MASTODON_TOKEN", "INSTAGRAM_PAGE_ACCESS_TOKEN"):
        monkeypatch.delenv(key, raising=False)
    factory = MagicMock()
    session = factory.return_value.__enter__.return_value
    session.get.return_value = animal_response("123")
    monkeypatch.setattr(requests, "Session", factory)

    main(["--database-path", str(path)])

    assert read_database(path).get("posted_pets", [])[0].get("status_name") == "Adopted"
    session.post.assert_not_called()
