import json
import tempfile
import unittest
from pathlib import Path

from abstractions import Post, PostResult
from adoption_sources.rescue_groups import SourceRescueGroups
from manual_testing.pipeline_inspector import inspect_rescuegroups_pipeline


class FakeResponse:
    status_code = 200

    def __init__(self, body):
        self._body = body

    def raise_for_status(self):
        return None

    def json(self):
        return self._body


class FakeHttpClient:
    def __init__(self, body):
        self.body = body
        self.calls = []

    def post(self, url, json, headers, timeout):
        self.calls.append(
            {
                "url": url,
                "json": json,
                "headers": headers,
                "timeout": timeout,
            }
        )
        return FakeResponse(self.body)


class FakePoster:
    platform_name = "Fake"

    def __init__(self):
        self.formatted = []
        self.published = []

    def format_post(self, pet):
        self.formatted.append(pet)
        return Post(
            text=f"Meet {pet.name}",
            image_url=pet.image_url,
            link=pet.adoption_url,
            tags=["test"],
        )

    def publish(self, post):
        self.published.append(post)
        return PostResult(success=True)


def _animal(animal_id, name, adoption_url="https://example.com/adopt"):
    attrs = {
        "name": name,
        "breedString": "Lab Mix",
        "descriptionText": "Friendly dog",
        "pictureThumbnailUrl": "https://example.com/dog.jpg?width=100",
    }
    if adoption_url is not None:
        attrs["adoptionUrl"] = adoption_url
    return {
        "type": "animals",
        "id": animal_id,
        "attributes": attrs,
        "relationships": {"orgs": {"data": [{"type": "orgs", "id": "org1"}]}},
    }


def _body(*animals, org_url="https://example.com/org"):
    org_attrs = {
        "city": "Boston",
        "state": "MA",
    }
    if org_url is not None:
        org_attrs["url"] = org_url

    return {
        "data": list(animals),
        "included": [
            {
                "type": "orgs",
                "id": "org1",
                "attributes": org_attrs,
            }
        ],
    }


def _stage(recorder, name):
    for stage in recorder.stages:
        if stage.name == name:
            return stage.data
    raise AssertionError(f"stage not found: {name}")


class PipelineInspectorTests(unittest.TestCase):
    def test_inspection_is_read_only_and_does_not_publish(self):
        source = SourceRescueGroups(api_key="secret-key", limit=2)
        http_client = FakeHttpClient(
            _body(
                _animal("pet-1", "Buddy"),
                _animal("pet-2", "More Dogs Soon!"),
            )
        )
        poster = FakePoster()

        with tempfile.TemporaryDirectory() as tmpdir:
            database_path = Path(tmpdir) / "database.json"
            original_database = {
                "posted_pets": [
                    {
                        "name": "Old Dog",
                        "pet_id": "old-pet",
                        "posted_at": "2020-01-01T00:00:00+00:00",
                    }
                ]
            }
            database_path.write_text(json.dumps(original_database), encoding="utf-8")

            recorder = inspect_rescuegroups_pipeline(
                source=source,
                posters=[poster],
                database_path=database_path,
                http_client=http_client,
                sample_size=None,
            )

            self.assertEqual(
                json.loads(database_path.read_text(encoding="utf-8")),
                original_database,
            )

        self.assertEqual(len(http_client.calls), 1)
        self.assertEqual(http_client.calls[0]["headers"]["Authorization"], "secret-key")
        self.assertEqual([pet.pet_id for pet in poster.formatted], ["pet-1"])
        self.assertEqual(poster.published, [])

        output = recorder.to_json()
        self.assertNotIn("secret-key", output)
        self.assertIn("<redacted>", output)

        filter_stage = _stage(recorder, "filter.placeholder")
        self.assertEqual(filter_stage[1]["name"], "More Dogs Soon!")
        self.assertFalse(filter_stage[1]["keep"])

    def test_database_ids_drive_eligibility_without_calling_pick_pet(self):
        source = SourceRescueGroups(api_key="secret-key", limit=2)
        http_client = FakeHttpClient(
            _body(
                _animal("pet-1", "Buddy"),
                _animal("pet-2", "Luna", adoption_url=None),
                org_url=None,
            )
        )
        poster = FakePoster()

        with tempfile.TemporaryDirectory() as tmpdir:
            database_path = Path(tmpdir) / "database.json"
            database_path.write_text(
                json.dumps(
                    {
                        "posted_pets": [
                            {
                                "name": "Buddy",
                                "pet_id": "pet-1",
                                "posted_at": "2026-01-01T00:00:00+00:00",
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )

            recorder = inspect_rescuegroups_pipeline(
                source=source,
                posters=[poster],
                database_path=database_path,
                http_client=http_client,
                sample_size=None,
            )

        eligibility = _stage(recorder, "eligibility.result")
        self.assertEqual(eligibility["eligible_count"], 0)
        self.assertEqual(
            eligibility["records"][0]["skip_reasons"],
            ["not_already_posted"],
        )
        self.assertEqual(
            eligibility["records"][1]["skip_reasons"],
            ["has_adoption_url"],
        )
        self.assertEqual(poster.formatted, [])
        self.assertEqual(poster.published, [])


if __name__ == "__main__":
    unittest.main()
