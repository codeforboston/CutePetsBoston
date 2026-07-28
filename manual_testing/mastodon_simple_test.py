from mastodon import Mastodon
import os
from datetime import datetime

client = Mastodon(
    access_token=os.environ.get("MASTODON_TOKEN"),
    api_base_url=os.environ.get("MASTODON_API_BASE_URL", "https://mastodon.social"),
)

client.account_verify_credentials()
client.status_post(f"Simple Test at {datetime.now()}")
print("Success")
