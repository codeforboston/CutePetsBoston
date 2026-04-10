"""Test script to verify Meta/Instagram API access."""

import requests

USER_TOKEN = "EAAeTXquCfa0BQZCslgXMt0CCMZATqzmOtf9BZAvROb16VDOdqONm4g3hnJ9iYnZAa2LSwmqlB4AB56Wd0dQkGlgQP5ZCBclci4CHEOkgpZAVMNVLq7f6NXQ301GPuk9PPEH0EenVdAJdxwjKqgHbw8ASBVkUtfZBN9qxJg9tAZBrlNpHKyMpvfY9iDFBvPDhwStnhQGePZAQ0BSYaUtiBho7i0SwJLmC3mjYBZCIDIoQ22QBBZBostZCLxtaZAobx5mGNPSEoq9XTeZCA3ZAodUhtyEk4iwEq5N1gZDZD"
PAGE_ID = "987663194437618"

# Step 1: Query the page directly for linked Instagram account
print("=== Instagram Business Account ===")
ig_url = f"https://graph.facebook.com/v21.0/{PAGE_ID}"
response = requests.get(ig_url, params={
    "fields": "instagram_business_account,name",
    "access_token": USER_TOKEN,
})
print("Status:", response.status_code)
print(response.json())
