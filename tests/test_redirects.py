"""Tests for the redirect slug minting and append-only mapping (RFC 0001)."""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import redirects
from abstractions import AdoptablePet
from config import SITE_URL
from redirects import (
    DEFAULT_REDIRECTS_PATH,
    enabled,
    is_safe_target,
    load_redirects,
    mint_for_pet,
    mint_slug,
    redirect_url_for,
    register_redirect,
    save_redirects,
)


def _pet(pet_id="12345", adoption_url="https://example.com/adopt/pet"):
    return AdoptablePet(
        name="Poppy",
        species="dog",
        breed="mutt",
        location="Boston, MA",
        image_url="https://example.com/poppy.jpg",
        adoption_url=adoption_url,
        pet_id=pet_id,
    )


class MintSlugTests(unittest.TestCase):
    def test_plain_numeric_id_passes_through(self):
        self.assertEqual(mint_slug("12345"), "12345")

    def test_forbidden_characters_are_replaced(self):
        self.assertTrue(mint_slug("pet/42 x").startswith("pet-42-x-"))

    def test_url_safe_id_gets_no_suffix(self):
        # Every RescueGroups id today is URL-safe, so no minted link changes.
        self.assertEqual(mint_slug("pet-42-x"), "pet-42-x")

    def test_sanitised_ids_do_not_collide(self):
        # "pet/42 x" and "pet-42-x" both sanitise to "pet-42-x"; without the
        # digest suffix the second pet's post would link to the first pet's
        # listing.
        self.assertNotEqual(mint_slug("pet/42 x"), mint_slug("pet-42-x"))

    def test_slug_is_stable_across_processes(self):
        # Guards against reaching for the builtin hash(), which is salted per
        # process and would mint a different slug for the same pet every run.
        repo_root = Path(__file__).resolve().parent.parent
        slugs = {
            subprocess.run(
                [sys.executable, "-c", "import redirects; print(redirects.mint_slug('pet/42 x'))"],
                capture_output=True, text=True, check=True, cwd=repo_root,
                env={**os.environ, "PYTHONHASHSEED": seed},
            ).stdout.strip()
            for seed in ("0", "1", "random")
        }
        self.assertEqual(len(slugs), 1, f"slug varied across hash seeds: {slugs}")

    def test_strips_surrounding_whitespace(self):
        self.assertEqual(mint_slug(" 77 "), "77")

    def test_missing_pet_id_raises(self):
        with self.assertRaises(ValueError):
            mint_slug(None)
        with self.assertRaises(ValueError):
            mint_slug("")


class RedirectUrlTests(unittest.TestCase):
    def test_url_matches_interstitial_contract(self):
        self.assertEqual(
            redirect_url_for("42"), f"{SITE_URL}/r/?id=42"
        )


class RegisterRedirectTests(unittest.TestCase):
    def test_new_slug_is_added_and_reports_changed(self):
        mapping, changed = register_redirect({}, "42", "https://example.com/a")
        self.assertTrue(changed)
        self.assertEqual(mapping, {"42": "https://example.com/a"})

    def test_existing_slug_with_same_url_is_idempotent(self):
        original = {"42": "https://example.com/a"}
        mapping, changed = register_redirect(
            dict(original), "42", "https://example.com/a"
        )
        self.assertFalse(changed)
        self.assertEqual(mapping, original)

    def test_unsafe_target_is_rejected(self):
        mapping, changed = register_redirect({}, "42", "javascript:alert(1)")
        self.assertFalse(changed)
        self.assertEqual(mapping, {})

    def test_existing_slug_is_never_overwritten(self):
        original = {"42": "https://example.com/old"}
        mapping, changed = register_redirect(
            dict(original), "42", "https://example.com/new"
        )
        self.assertFalse(changed)
        self.assertEqual(mapping["42"], "https://example.com/old")


class SaveLoadTests(unittest.TestCase):
    def test_round_trip(self):
        mapping = {"42": "https://example.com/a", "7-x": "https://example.com/b"}
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / DEFAULT_REDIRECTS_PATH
            save_redirects(mapping, path)
            self.assertEqual(load_redirects(path), mapping)

    def test_missing_file_is_empty_mapping(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(load_redirects(Path(tmp) / "nope.json"), {})

    def test_empty_file_is_empty_mapping(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / DEFAULT_REDIRECTS_PATH
            path.write_text("")
            self.assertEqual(load_redirects(path), {})

    def test_default_path_is_resolved_at_call_time(self):
        # The default used to be bound at import, so reassigning the module
        # constant silently did not affect load_redirects/save_redirects.
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "patched.json"
            with mock.patch.object(redirects, "DEFAULT_REDIRECTS_PATH", str(path)):
                save_redirects({"42": "https://example.com/a"})
                self.assertEqual(load_redirects(), {"42": "https://example.com/a"})
            self.assertTrue(path.exists())

    def test_corrupt_file_raises_instead_of_resetting_store(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / DEFAULT_REDIRECTS_PATH
            path.write_text("{not json")
            with self.assertRaises(ValueError):
                load_redirects(path)

    def test_non_object_file_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / DEFAULT_REDIRECTS_PATH
            path.write_text("[]")
            with self.assertRaises(ValueError):
                load_redirects(path)


class MintForPetTests(unittest.TestCase):
    def test_mints_slug_and_persists_mapping(self):
        pet = _pet()
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / DEFAULT_REDIRECTS_PATH
            url = mint_for_pet(pet, redirects_path=path)
            self.assertEqual(url, f"{SITE_URL}/r/?id=12345")
            self.assertEqual(load_redirects(path), {"12345": pet.adoption_url})

    def test_reminting_same_pet_does_not_rewrite_file(self):
        pet = _pet()
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / DEFAULT_REDIRECTS_PATH
            mint_for_pet(pet, redirects_path=path)
            first_content = path.read_text()
            mint_for_pet(pet, redirects_path=path)
            self.assertEqual(path.read_text(), first_content)

    def test_relabeled_pet_keeps_existing_target(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / DEFAULT_REDIRECTS_PATH
            mint_for_pet(_pet(adoption_url="https://example.com/old"), redirects_path=path)
            url = mint_for_pet(_pet(adoption_url="https://example.com/new"), redirects_path=path)
            self.assertEqual(url, f"{SITE_URL}/r/?id=12345")
            self.assertEqual(load_redirects(path), {"12345": "https://example.com/old"})

    def test_corrupt_mapping_does_not_block_posting(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / DEFAULT_REDIRECTS_PATH
            path.write_text("{not json")
            before = path.read_bytes()
            self.assertIsNone(mint_for_pet(_pet(), redirects_path=path))
            # The damaged store is left for a human, never silently rebuilt.
            self.assertEqual(path.read_bytes(), before)

    def test_unsafe_adoption_url_is_never_minted(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / DEFAULT_REDIRECTS_PATH
            pet = _pet(adoption_url="javascript:window.__pwned=1")
            self.assertIsNone(mint_for_pet(pet, redirects_path=path))
            self.assertFalse(path.exists())

    def test_pet_without_id_returns_none_and_writes_nothing(self):
        pet = _pet(pet_id=None)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / DEFAULT_REDIRECTS_PATH
            self.assertIsNone(mint_for_pet(pet, redirects_path=path))
            self.assertFalse(path.exists())


class IsSafeTargetTests(unittest.TestCase):
    def test_http_and_https_are_allowed(self):
        self.assertTrue(is_safe_target("https://example.com/a"))
        self.assertTrue(is_safe_target("http://example.com/a"))

    def test_reconstructed_deep_link_with_fragment_is_allowed(self):
        self.assertTrue(
            is_safe_target(
                "https://sterlingshelter.org/pet-finder/#action_0=pet&animalID_0=1"
            )
        )

    def test_dangerous_and_relative_values_are_rejected(self):
        for value in (
            "javascript:alert(1)",
            "data:text/html,<script>alert(1)</script>",
            "/relative/path",
            "",
            None,
        ):
            self.assertFalse(is_safe_target(value), value)


class EnabledTests(unittest.TestCase):
    def test_env_var_gates_minting(self):
        for value in ("1", "true", "True", "yes", "on"):
            with mock.patch.dict("os.environ", {"REDIRECTS_ENABLED": value}):
                self.assertTrue(enabled())
        for value in ("", "0", "false", "no", "off"):
            with mock.patch.dict("os.environ", {"REDIRECTS_ENABLED": value}):
                self.assertFalse(enabled())
        with mock.patch.dict("os.environ", {}, clear=True):
            self.assertFalse(enabled())


if __name__ == "__main__":
    unittest.main()
