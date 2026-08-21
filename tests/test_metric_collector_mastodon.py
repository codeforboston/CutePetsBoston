from unittest.mock import Mock

from metric_collectors.mastodon import CollectorMastodon


class TestCollectorMastodon:
    def test_maps_status_counts(self):
        client = Mock()
        client.status.return_value = {
            "favourites_count": 11,
            "reblogs_count": 4,
            "replies_count": 6,
        }

        metrics = CollectorMastodon(client=client).fetch_metrics("status-123")

        assert metrics.likes == 11
        assert metrics.reposts == 4
        assert metrics.comments == 6
        client.status.assert_called_once_with("status-123")

    def test_returns_none_on_sdk_error(self):
        client = Mock()
        client.status.side_effect = RuntimeError("mastodon unavailable")

        metrics = CollectorMastodon(client=client).fetch_metrics("status-123")

        assert metrics is None
