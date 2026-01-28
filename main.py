import json
import os
import sys

import requests


api_key = os.environ.get("ACCESS_KEY")
if not api_key:
    sys.exit("CUTEPETSBOSTON_RESCUEGROUPS_API_KEY secret not set")

url = "https://api.rescuegroups.org/v5/public/animals/search/available/dogs"
payload = {
    "data": {
        "filters": [
            {
                "fieldName": "status",
                "operation": "equals",
                "criteria": "Available",
            }
        ],
        "filterRadius": {"miles": 50, "postalcode": "02108"},
        "limit": 3,
    }
}
headers = {
    "Content-Type": "application/vnd.api+json",
    "Authorization": f"{api_key}",
}

response = requests.post(url, headers=headers, json=payload["data"], timeout=15)
response.raise_for_status()
print(response)
data = response.json().get("data", [])
print("Fetched", len(data), "records")
print(json.dumps(data[:3], indent=2))