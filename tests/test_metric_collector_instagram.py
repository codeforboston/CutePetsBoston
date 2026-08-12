from unittest.mock import Mock, patch

import requests

from metric_collectors.instagram import CollectorInstagram
from social_posters.instagram import GRAPH_API_BASE


class TestCollectorInstagram:
    @patch("metric_collectors.instagram.requests.get")
    def test_maps_media_counts_and_marks_reposts_not_applicable(self, mock_get):
        response = Mock()
        response.json.return_value = {"like_count": 13, "comments_count": 5}
        mock_get.return_value = response

        metrics = CollectorInstagram(access_token="token").fetch_metrics("media-123")

        assert metrics.likes == 13
        assert metrics.reposts is None
        assert metrics.comments == 5
        mock_get.assert_called_once_with(
            f"{GRAPH_API_BASE}/media-123",
            params={"fields": "like_count,comments_count"},
            headers={"Authorization": "Bearer token"},
            timeout=20,
        )
        response.raise_for_status.assert_called_once_with()

    @patch("metric_collectors.instagram.requests.get")
    def test_returns_none_on_http_error(self, mock_get):
        response = Mock()
        response.raise_for_status.side_effect = requests.HTTPError("not found")
        mock_get.return_value = response

        metrics = CollectorInstagram(access_token="token").fetch_metrics(
            "media-123"
        )

        assert metrics is None

    @patch("metric_collectors.instagram.requests.get")
    def test_returns_none_without_access_token(self, mock_get, monkeypatch):
        monkeypatch.delenv("INSTAGRAM_PAGE_ACCESS_TOKEN", raising=False)
        metrics = CollectorInstagram(access_token="").fetch_metrics("media-123")

        assert metrics is None
        mock_get.assert_not_called()
