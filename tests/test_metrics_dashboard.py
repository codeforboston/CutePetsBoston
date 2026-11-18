import json
from contextlib import chdir
from pathlib import Path
from tempfile import TemporaryDirectory

from bs4 import BeautifulSoup

from metrics_dashboard import dashboard


def test_dashboard_default_output_uses_public_analytics_name():
    with TemporaryDirectory() as temporary_directory, chdir(temporary_directory):
        dashboard()

        dashboard_path = Path("dashboard.html")
        assert dashboard_path.exists()
        assert "No analytics data available yet." in dashboard_path.read_text()
        assert not Path("analytics.html").exists()


def test_adoption_table_shows_all_pets_without_engagement_metrics(tmp_path):
    database_path = tmp_path / "database.json"
    html_path = tmp_path / "dashboard.html"
    database_path.write_text(
        json.dumps(
            {
                "posted_pets": [
                    {
                        "name": "Poppy",
                        "pet_id": "123",
                        "posted_at": "2026-10-01T00:00:00+00:00",
                        "status_name": "Adopted",
                        "status_observed_at": "2026-11-18T00:00:00+00:00",
                    },
                    {"name": "Spot", "pet_id": "456", "posted_at": "2026-10-02T00:00:00+00:00"},
                    {"name": "No ID", "pet_id": None, "posted_at": "2026-10-03T00:00:00+00:00"},
                ],
                "posts": [],
            }
        )
    )

    dashboard(html_file_path=html_path, database_path=database_path)

    document = BeautifulSoup(html_path.read_text(), "html.parser")
    table = document.select_one("#adoption-status-table_fallback table")
    assert table is not None
    assert [cell.get_text().replace("ⓘ", "").replace("🔒", "") for cell in table.select("th")] == [
        "Name",
        "Pet ID",
        "Posted date",
        "Adoption status",
        "Status last observed",
    ]
    assert [[cell.get_text() for cell in row.select("td")] for row in table.select("tbody tr")] == [
        ["Poppy", "123", "2026-10-01", "Adopted", "2026-11-18"],
        ["Spot", "456", "2026-10-02", "Unknown", ""],
        ["No ID", "", "2026-10-03", "Unknown", ""],
    ]
    summary = document.select("#adoption-status-summary tbody tr")
    assert [[cell.get_text() for cell in row.select("td")] for row in summary] == [
        ["Adopted", "1"],
        ["Unknown", "2"],
    ]


def test_adoption_table_is_one_row_per_pet_alongside_platform_charts_and_escapes_names(tmp_path):
    database_path = tmp_path / "database.json"
    html_path = tmp_path / "dashboard.html"
    name = '<img src=x onerror="alert(1)">'
    database_path.write_text(
        json.dumps(
            {
                "posted_pets": [
                    {"name": name, "pet_id": "123", "posted_at": "2026-10-01T00:00:00+00:00", "status_name": "Adopted"},
                ],
                "posts": [
                    {
                        "pet_id": "123",
                        "platform": platform,
                        "post_id": platform,
                        "post_url": "https://example.com/post",
                        "metrics": [
                            {"collected_at": "2026-10-02T00:00:00+00:00", "likes": 2, "reposts": 0, "comments": 1}
                        ],
                    }
                    for platform in ("Bluesky", "Mastodon")
                ],
            }
        )
    )

    dashboard(html_file_path=html_path, database_path=database_path)

    document = BeautifulSoup(html_path.read_text(), "html.parser")
    table = document.select_one("#adoption-status-table_fallback table")
    assert table is not None
    assert len(table.select("tbody tr")) == 1
    cell = table.select_one("td")
    assert cell is not None
    assert cell.get_text() == name
    assert table.select("img") == []
    assert [cell.get_text() for cell in document.select("#adoption-status-summary tbody td")] == ["Adopted", "1"]
    assert "Top 10 Pets by Max Likes" in html_path.read_text()
