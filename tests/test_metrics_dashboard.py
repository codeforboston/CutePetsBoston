from contextlib import chdir
from pathlib import Path
from tempfile import TemporaryDirectory

from metrics_dashboard import dashboard


def test_dashboard_default_output_uses_public_analytics_name():
    with TemporaryDirectory() as temporary_directory, chdir(temporary_directory):
        dashboard()

        dashboard_path = Path("dashboard.html")
        assert dashboard_path.exists()
        assert "No analytics data available yet." in dashboard_path.read_text()
        assert not Path("analytics.html").exists()
