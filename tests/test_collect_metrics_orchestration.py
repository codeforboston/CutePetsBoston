import json
from datetime import datetime, timedelta, timezone

from abstractions import PostMetrics
from main import collect_metrics


class FakeCollector:
    platform_name = "Bluesky"

    def __init__(self, responses):
        self.responses = responses
        self.calls = []

    def fetch_metrics(self, post_id, post_url=None):
        self.calls.append((post_id, post_url))
        response = self.responses[post_id]
        if isinstance(response, Exception):
            raise response
        return response


def post(post_id, posted_at, platform="Bluesky", metrics=None):
    return {
        "pet_id": f"pet-{post_id}",
        "platform": platform,
        "post_id": post_id,
        "post_url": f"at://{post_id}",
        "posted_at": posted_at,
        "metrics": list(metrics or []),
    }


def snapshot(likes):
    return PostMetrics(
        collected_at="replaced-by-orchestrator",
        likes=likes,
        reposts=2,
        comments=3,
    )


def test_collects_only_recent_posts_with_registered_collectors(tmp_path):
    database_path = tmp_path / "database.json"
    now = datetime.now(timezone.utc)
    previous = {
        "collected_at": (now - timedelta(hours=1)).isoformat(),
        "likes": 1,
        "reposts": 0,
        "comments": 0,
    }
    database_path.write_text(
        json.dumps(
            {
                "posted_pets": [],
                "posts": [
                    post("recent", (now - timedelta(days=1)).isoformat(), metrics=[previous]),
                    post("none", (now - timedelta(days=2)).isoformat()),
                    post("old", (now - timedelta(days=15)).isoformat()),
                    post(
                        "unknown",
                        (now - timedelta(days=1)).isoformat(),
                        platform="Unknown",
                    ),
                ],
            }
        )
    )
    collector = FakeCollector({"recent": snapshot(9), "none": None})

    collect_metrics([collector], database_path=database_path, window_days=14)

    data = json.loads(database_path.read_text())
    assert collector.calls == [("recent", "at://recent"), ("none", "at://none")]
    assert data["posts"][0]["metrics"][0] == previous
    assert data["posts"][0]["metrics"][1]["likes"] == 9
    assert data["posts"][0]["metrics"][1]["reposts"] == 2
    assert data["posts"][0]["metrics"][1]["comments"] == 3
    collected_at = datetime.fromisoformat(
        data["posts"][0]["metrics"][1]["collected_at"]
    )
    assert collected_at.tzinfo == timezone.utc
    assert data["posts"][1]["metrics"] == []
    assert data["posts"][2]["metrics"] == []
    assert data["posts"][3]["metrics"] == []


def test_missing_database_is_a_noop(tmp_path):
    database_path = tmp_path / "database.json"

    collect_metrics([], database_path=database_path)

    assert not database_path.exists()


def test_missing_posts_key_is_a_noop(tmp_path):
    database_path = tmp_path / "database.json"
    original = {"posted_pets": []}
    database_path.write_text(json.dumps(original))

    collect_metrics([], database_path=database_path)

    assert json.loads(database_path.read_text()) == original


def test_collector_error_does_not_stop_other_posts(tmp_path):
    database_path = tmp_path / "database.json"
    recent = datetime.now(timezone.utc).isoformat()
    database_path.write_text(
        json.dumps({"posted_pets": [], "posts": [post("bad", recent), post("good", recent)]})
    )
    collector = FakeCollector(
        {"bad": RuntimeError("unreachable"), "good": snapshot(4)}
    )

    collect_metrics([collector], database_path=database_path)

    data = json.loads(database_path.read_text())
    assert data["posts"][0]["metrics"] == []
    assert data["posts"][1]["metrics"][0]["likes"] == 4


def test_repeated_collection_appends_snapshots_without_adding_posts(tmp_path):
    database_path = tmp_path / "database.json"
    recent = datetime.now(timezone.utc).isoformat()
    database_path.write_text(
        json.dumps({"posted_pets": [], "posts": [post("recent", recent)]})
    )
    collector = FakeCollector({"recent": snapshot(5)})

    collect_metrics([collector], database_path=database_path)
    collector.responses["recent"] = snapshot(7)
    collect_metrics([collector], database_path=database_path)

    data = json.loads(database_path.read_text())
    assert len(data["posts"]) == 1
    assert [item["likes"] for item in data["posts"][0]["metrics"]] == [5, 7]
