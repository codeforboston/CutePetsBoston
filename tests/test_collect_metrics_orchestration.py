import json
from datetime import datetime, timedelta, timezone
import sqlite3

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


def _get_metrics(metrics_db_path, post_id):
    with sqlite3.connect(metrics_db_path) as conn:
        return conn.execute(
            "SELECT likes, reposts, comments, collected_at FROM post_metrics WHERE post_id = ? ORDER BY id",
            (post_id,),
        ).fetchall()


def test_collects_only_recent_posts_with_registered_collectors(tmp_path):
    database_path = tmp_path / "database.json"
    metrics_db_path = tmp_path / "metrics.sqlite"
    now = datetime.now(timezone.utc)
    database_path.write_text(
        json.dumps(
            {
                "posted_pets": [],
                "posts": [
                    post("recent", (now - timedelta(days=1)).isoformat()),
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

    collect_metrics([collector], database_path=database_path, metrics_db_path=metrics_db_path, window_days=14)

    assert collector.calls == [("recent", "at://recent"), ("none", "at://none")]

    recent_rows = _get_metrics(metrics_db_path, "recent")
    assert len(recent_rows) == 1
    assert recent_rows[0][0] == 9   # likes
    assert recent_rows[0][1] == 2   # reposts
    assert recent_rows[0][2] == 3   # comments
    collected_at = datetime.fromisoformat(recent_rows[0][3])
    assert collected_at.tzinfo == timezone.utc

    assert _get_metrics(metrics_db_path, "none") == []
    assert _get_metrics(metrics_db_path, "old") == []
    assert _get_metrics(metrics_db_path, "unknown") == []


def test_missing_database_is_a_noop(tmp_path):
    database_path = tmp_path / "database.json"
    metrics_db_path = tmp_path / "metrics.sqlite"

    collect_metrics([], database_path=database_path, metrics_db_path=metrics_db_path)

    assert not database_path.exists()


def test_missing_posts_key_is_a_noop(tmp_path):
    database_path = tmp_path / "database.json"
    metrics_db_path = tmp_path / "metrics.sqlite"
    original = {"posted_pets": []}
    database_path.write_text(json.dumps(original))

    collect_metrics([], database_path=database_path, metrics_db_path=metrics_db_path)

    assert json.loads(database_path.read_text()) == original


def test_collector_error_does_not_stop_other_posts(tmp_path):
    database_path = tmp_path / "database.json"
    metrics_db_path = tmp_path / "metrics.sqlite"
    recent = datetime.now(timezone.utc).isoformat()
    database_path.write_text(
        json.dumps({"posted_pets": [], "posts": [post("bad", recent), post("good", recent)]})
    )
    collector = FakeCollector(
        {"bad": RuntimeError("unreachable"), "good": snapshot(4)}
    )

    collect_metrics([collector], database_path=database_path, metrics_db_path=metrics_db_path)

    assert _get_metrics(metrics_db_path, "bad") == []
    assert _get_metrics(metrics_db_path, "good")[0][0] == 4


def test_repeated_collection_appends_snapshots_without_adding_posts(tmp_path):
    database_path = tmp_path / "database.json"
    metrics_db_path = tmp_path / "metrics.sqlite"
    recent = datetime.now(timezone.utc).isoformat()
    database_path.write_text(
        json.dumps({"posted_pets": [], "posts": [post("recent", recent)]})
    )
    collector = FakeCollector({"recent": snapshot(5)})

    collect_metrics([collector], database_path=database_path, metrics_db_path=metrics_db_path)
    collector.responses["recent"] = snapshot(7)
    collect_metrics([collector], database_path=database_path, metrics_db_path=metrics_db_path)

    rows = _get_metrics(metrics_db_path, "recent")
    assert len(rows) == 2
    assert [r[0] for r in rows] == [5, 7]

    with sqlite3.connect(metrics_db_path) as conn:
        post_count = conn.execute("SELECT COUNT(*) FROM posts").fetchone()[0]
    assert post_count == 1
