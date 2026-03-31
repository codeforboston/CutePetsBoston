from mastodon import Mastodon
import os 
from datetime import datetime

client = Mastodon(
    access_token="h_o6jBz37M5322Mb8a1PYNTA9ALjfKL15_XMY2dYwAs",
    api_base_url="https://mastodon.social"
    )

client.account_verify_credentials()
client.status_post(f"Simple Test at {datetime.now()}")
print("Success")