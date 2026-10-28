"""Publishing contract for the append-only redirect mapping merge."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

from tools import merge_redirects as implementation


@pytest.fixture
def paths(tmp_path):
    return tmp_path / "minted.json", tmp_path / "existing.json", tmp_path / "merged.json"


def test_merge_preserves_existing_targets_and_reports_additions(paths, capsys):
    minted, existing, output = paths
    minted.write_text(json.dumps({"same": "https://new.example", "new": "https://example.com/é?q=%2f"}))
    existing.write_text(json.dumps({"same": "https://OLD.example:443", "old": "https://old.example"}))

    merged = implementation.merge_files(*paths)

    assert merged == {
        "same": "https://OLD.example:443",
        "old": "https://old.example",
        "new": "https://example.com/é?q=%2f",
    }
    assert json.loads(output.read_text()) == merged
    assert capsys.readouterr().out == "New redirects: new\nMapping now holds 3 redirect(s).\n"
    assert json.loads(existing.read_text())["same"] == "https://OLD.example:443"


@pytest.mark.parametrize("new_text", [None, "", " \n", "{}"])
def test_missing_or_empty_minted_mapping_is_noop(paths, new_text, capsys):
    minted, existing, output = paths
    if new_text is not None:
        minted.write_text(new_text)
    existing.write_text('{"saved": "https://example.com/pet"}')
    assert implementation.merge_files(*paths) == {"saved": "https://example.com/pet"}
    assert "No new redirects." in capsys.readouterr().out


def test_first_deployment_without_inputs(paths):
    assert implementation.merge_files(*paths) == {}
    assert json.loads(paths[2].read_text()) == {}


def test_first_deployment_with_minted_entries(paths):
    paths[0].write_text('{"new": "https://example.com/pet"}')
    assert implementation.merge_files(*paths) == {"new": "https://example.com/pet"}


@pytest.mark.parametrize(
    "bad_text",
    ["{broken", "[]", "null", '"text"', '{"pet": 42}', '{"pet": null}', '{"pet": {"url": "https://example.com"}}'],
)
@pytest.mark.parametrize("input_index", [0, 1], ids=["minted", "existing"])
def test_invalid_input_cannot_replace_output(paths, bad_text, input_index):
    paths[0].write_text("{}")
    paths[1].write_text("{}")
    paths[input_index].write_text(bad_text)
    paths[2].write_text("previous output")
    with pytest.raises(ValueError, match=str(paths[input_index])) as error:
        implementation.merge_files(*paths)
    assert f"input text: {bad_text!r}" in str(error.value)
    assert paths[2].read_text() == "previous output"
    assert not paths[2].with_suffix(".json.tmp").exists()


@pytest.mark.parametrize("slug, url", [(42, "https://example.com"), ("pet", 42), ("pet", None)])
def test_validation_error_identifies_invalid_entry(slug, url):
    with pytest.raises(ValueError) as error:
        implementation.validate_mapping({slug: url})
    assert f"slug {slug!r} -> URL {url!r}" in str(error.value)


def test_load_mapping_accepts_positional_allow_empty(paths):
    paths[0].write_text("")
    assert implementation.load_mapping(paths[0], True) == {}


@pytest.mark.parametrize("empty_text", ["", " \n"])
def test_empty_authoritative_file_is_corruption(paths, empty_text):
    paths[1].write_text(empty_text)
    with pytest.raises(ValueError):
        implementation.merge_files(*paths)
    assert not paths[2].exists()


def test_identical_merge_is_repeatable(paths):
    paths[0].write_text('{"b": "https://example.com/b", "a": "https://example.com/a"}')
    implementation.merge_files(*paths)
    first = paths[2].read_bytes()
    implementation.merge_files(*paths)
    assert paths[2].read_bytes() == first


def test_cli_success_and_failure(paths):
    script = Path(implementation.__file__)
    # Publishing installs no dependencies; disable site-packages to prove it works.
    command = [sys.executable, "-S", str(script), *map(str, paths)]
    success = subprocess.run(command, capture_output=True, text=True)
    assert success.returncode == 0, success.stderr
    assert json.loads(paths[2].read_text()) == {}
    paths[1].write_text("{broken")
    failure = subprocess.run(command, capture_output=True, text=True)
    assert failure.returncode == 1
    assert "Redirect merge failed:" in failure.stderr
    assert str(paths[1]) in failure.stderr
    assert json.loads(paths[2].read_text()) == {}
