from unittest.mock import Mock, patch

import requests

from metric_collectors.bluesky import CollectorBluesky, POST_THREAD_URL


class TestCollectorBluesky:
    @patch("metric_collectors.bluesky.requests.get")
    def test_maps_post_thread_counts(self, mock_get):
        response = Mock()
        response.json.return_value = {
            "thread": {
                "post": {"likeCount": 8, "repostCount": 3, "replyCount": 2}
            }
        }
        mock_get.return_value = response

        metrics = CollectorBluesky().fetch_metrics(
            "cid-123", "at://did:plc:abc/app.bsky.feed.post/xyz"
        )

        assert metrics.likes == 8
        assert metrics.reposts == 3
        assert metrics.comments == 2
        mock_get.assert_called_once_with(
            POST_THREAD_URL,
            params={"uri": "at://did:plc:abc/app.bsky.feed.post/xyz"},
            timeout=20,
        )
        response.raise_for_status.assert_called_once_with()

    @patch("metric_collectors.bluesky.requests.get")
    def test_returns_none_on_http_error(self, mock_get):
        response = Mock()
        response.raise_for_status.side_effect = requests.HTTPError("not found")
        mock_get.return_value = response

        metrics = CollectorBluesky().fetch_metrics(
            "cid-123", "at://did:plc:abc/app.bsky.feed.post/missing"
        )

        assert metrics is None

    @patch("metric_collectors.bluesky.requests.get")
    def test_returns_none_when_post_url_is_missing(self, mock_get):
        metrics = CollectorBluesky().fetch_metrics("cid-123")

        assert metrics is None
        mock_get.assert_not_called()
