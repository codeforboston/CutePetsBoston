"""Merge redirect mappings using only the Python standard library.

Run: python tools/merge_redirects.py MINTED EXISTING OUTPUT
Existing entries always win; no saved redirect is overwritten or removed.
"""

import argparse
import json
from pathlib import Path


def validate_mapping(data: object) -> dict[str, str]:
    if not isinstance(data, dict):
        raise ValueError(f"expected a JSON object of slug -> URL strings; got {type(data).__name__}: {data!r}")
    for slug, url in data.items():
        if not isinstance(slug, str) or not isinstance(url, str):
            raise ValueError(f"redirect keys and values must be strings; got slug {slug!r} -> URL {url!r}")
    return data


def load_mapping(path: Path, allow_empty: bool = False) -> dict[str, str]:
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return {}  # Missing inputs are valid on the first deployment.
    if allow_empty and not text.strip():
        return {}
    try:
        return validate_mapping(json.loads(text))
    except (ValueError, UnicodeError) as exc:
        raise ValueError(f"{path}: {exc}; input text: {text!r}") from exc


def merge_files(minted_path: Path, existing_path: Path, output_path: Path) -> dict[str, str]:
    minted = load_mapping(minted_path, allow_empty=True)
    existing = load_mapping(existing_path)
    merged = minted | existing
    # Validate both inputs before touching the output. Replace it atomically.
    temporary_path = output_path.with_name(output_path.name + ".tmp")
    try:
        temporary_path.write_text(json.dumps(merged, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        temporary_path.replace(output_path)
    finally:
        temporary_path.unlink(missing_ok=True)
    added = sorted(merged.keys() - existing.keys())
    print("New redirects: " + ", ".join(added) if added else "No new redirects.")
    print(f"Mapping now holds {len(merged)} redirect(s).")
    return merged


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("minted", type=Path)
    parser.add_argument("existing", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    try:
        merge_files(args.minted, args.existing, args.output)
    except (OSError, ValueError) as exc:
        parser.exit(1, f"Redirect merge failed: {exc}\n")


if __name__ == "__main__":
    main()
