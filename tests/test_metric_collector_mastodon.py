from unittest.mock import Mock, patch

import pytest

from metric_collectors.mastodon import CollectorMastodon, StatusCounts


class FakeStatusClient:
    def __init__(self, counts: StatusCounts) -> None:
        self.counts = counts
        self.calls: list[str] = []

    def status(self, post_id: str, /) -> StatusCounts:
        self.calls.append(post_id)
        return self.counts


def test_accepts_a_structural_status_client() -> None:
    client = FakeStatusClient({"favourites_count": 0})

    metrics = CollectorMastodon(client=client).fetch_metrics("status-123")

    assert metrics is not None
    assert metrics.likes == 0
    assert metrics.reposts is None
    assert metrics.comments is None
    assert client.calls == ["status-123"]


@pytest.mark.parametrize(
    ("counts", "expected"),
    [
        (
            {"favourites_count": 11, "reblogs_count": 4, "replies_count": 6},
            (11, 4, 6),
        ),
        ({}, (None, None, None)),
        ({"favourites_count": 0, "reblogs_count": None}, (0, None, None)),
    ],
)
def test_default_client_adapts_sdk_status(
    counts: StatusCounts, expected: tuple[int | None, int | None, int | None]
) -> None:
    with patch("metric_collectors.mastodon.Mastodon") as sdk_factory:
        sdk = sdk_factory.return_value
        sdk.status.return_value = counts

        metrics = CollectorMastodon().fetch_metrics("status-123")

    assert metrics is not None
    assert (metrics.likes, metrics.reposts, metrics.comments) == expected
    sdk.status.assert_called_once_with("status-123")


def test_default_client_preserves_sdk_error_handling() -> None:
    with patch("metric_collectors.mastodon.Mastodon") as sdk_factory:
        sdk_factory.return_value.status.side_effect = RuntimeError("unavailable")

        assert CollectorMastodon().fetch_metrics("status-123") is None


class TestCollectorMastodon:
    def test_maps_status_counts(self):
        client = Mock()
        client.status.return_value = {
            "favourites_count": 11,
            "reblogs_count": 4,
            "replies_count": 6,
        }

        metrics = CollectorMastodon(client=client).fetch_metrics("status-123")

        assert metrics is not None
        assert metrics.likes == 11
        assert metrics.reposts == 4
        assert metrics.comments == 6
        client.status.assert_called_once_with("status-123")

    def test_returns_none_on_sdk_error(self):
        client = Mock()
        client.status.side_effect = RuntimeError("mastodon unavailable")

        metrics = CollectorMastodon(client=client).fetch_metrics("status-123")

        assert metrics is None
