"""Ad-hoc headless smoke test for issue #190's new homepage.

Serves the web/ directory with a locally generated pets.json and clicks
through the states a happy pipeline run wouldn't cover: filters, the
photo-less mascot fallback, and the empty/missing-feed states.

    # from the repo root, first:
    cp pets.json web/                      # after a local pipeline run
    uv run --locked python -m http.server 8765  (from web/)
    uv run --locked python manual_testing/smoke_homepage.py
"""

import json
import os
import time

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait

BASE = "http://127.0.0.1:8765/"
PETS_PATH = "web/pets.json"
HIDDEN_PATH = "web/pets.json.hidden"


def make_driver():
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    # No explicit Service: Selenium Manager downloads a driver matching
    # the installed Chrome itself.
    return webdriver.Chrome(options=options)


def card_texts(driver):
    cards = driver.find_elements(By.CSS_SELECTOR, "#pet-grid a.pet-card")
    return [
        {
            "name": card.find_element(By.CLASS_NAME, "pet-name").text,
            "location": card.find_element(By.CLASS_NAME, "pet-location").text.strip(),
            "date": card.find_element(By.CLASS_NAME, "pet-date-pill").text,
            "href": card.get_attribute("href"),
            "has_photo": bool(card.find_elements(By.CSS_SELECTOR, ".pet-photo img")),
            "has_mascot": bool(card.find_elements(By.CSS_SELECTOR, ".pet-mascot")),
            "chips": [c.text for c in card.find_elements(By.CLASS_NAME, "pet-chip")],
        }
        for card in cards
    ]


def wait_for_feed(driver, timeout=5):
    """Wait until the grid settles on either cards or the empty-state note."""
    WebDriverWait(driver, timeout).until(
        lambda d: (
            d.find_elements(By.CSS_SELECTOR, "#pet-grid a.pet-card")
            or "No recent posts yet" in d.find_element(By.ID, "pet-grid").text
        )
    )


def load_page(driver):
    # http.server serves no Cache-Control, so Chrome may serve a stale
    # pets.json between state changes; drop the cache to force a fresh fetch.
    try:
        driver.execute_cdp_cmd("Network.enable", {})
        driver.execute_cdp_cmd("Network.clearBrowserCache", {})
    except Exception:
        pass  # cache clearing is best effort
    driver.get(BASE)
    wait_for_feed(driver)


def filter_pill(driver, value):
    pills = driver.find_elements(By.CLASS_NAME, "filter-pill")
    return next(p for p in pills if p.get_attribute("data-filter") == value)


def check_cards_and_filters(driver):
    # 1. Happy path: cards with real names, photos, dates and links.
    load_page(driver)
    cards = card_texts(driver)
    print("1. cards:", json.dumps(cards, indent=2))
    assert cards, "expected at least one card"
    assert all(c["has_photo"] for c in cards if c["name"] == cards[0]["name"]) or cards[0]["has_photo"]
    assert cards[0]["href"].startswith("http")
    assert cards[0]["date"]
    assert cards[0]["location"]

    # 2. Filters: toggle Dogs and Cats; the active pill styling follows.
    filter_pill(driver, "cat").click()
    time.sleep(0.2)
    print("2. cats filter ->", [c["name"] for c in card_texts(driver)])
    filter_pill(driver, "dog").click()
    time.sleep(0.2)
    print("   dogs filter ->", [c["name"] for c in card_texts(driver)])
    active = [p.text for p in driver.find_elements(By.CSS_SELECTOR, ".filter-pill.is-active")]
    assert active == ["Dogs"]

    # 3. Shelter pills render name + location and link out.
    pills = driver.find_elements(By.CSS_SELECTOR, "#shelter-list a.shelter-pill")
    print("3. shelter pills:", [p.text.replace("\n", " | ") for p in pills])
    assert pills
    assert all(p.get_attribute("href").startswith("https") for p in pills)


def main():
    driver = make_driver()
    pets = json.load(open(PETS_PATH))
    try:
        check_cards_and_filters(driver)

        # 4. Photo-less entries -> the species mascot illustration.
        json.dump([dict(pet, image_url=None) for pet in pets], open(PETS_PATH, "w"))
        load_page(driver)
        fallback = card_texts(driver)
        print("4. photo-less card has_mascot:", [c["has_mascot"] for c in fallback])
        assert all(c["has_mascot"] for c in fallback)

        # 5. Empty array -> the empty state.
        json.dump([], open(PETS_PATH, "w"))
        load_page(driver)
        note = driver.find_element(By.ID, "pet-grid").text
        print("5. empty-feed note:", note.strip())
        assert "No recent posts yet" in note

        # 6. Missing pets.json (404 fetch) -> the same empty-state handler.
        os.rename(PETS_PATH, HIDDEN_PATH)
        load_page(driver)
        note = driver.find_element(By.ID, "pet-grid").text
        print("6. missing-feed note:", note.strip())
        assert "No recent posts yet" in note
    finally:
        driver.quit()
        # Always leave web/pets.json holding the real feed.
        if os.path.exists(HIDDEN_PATH):
            os.rename(HIDDEN_PATH, PETS_PATH)
        json.dump(pets, open(PETS_PATH, "w"))

    print("ALL SMOKE CHECKS PASSED")


if __name__ == "__main__":
    main()
