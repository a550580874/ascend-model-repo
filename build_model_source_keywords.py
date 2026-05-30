#!/usr/bin/env python3
"""Build a normalized keyword list from ascend model source data."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
DEFAULT_INPUT = ROOT / "data" / "ascend_model_with_adapter-1-total.json"
DEFAULT_OUTPUT = ROOT / "data" / "ascend_model_source_key_word.json"
KEY_FIELDS = ("name", "adapter_framework", "adapter_hardware")
SPLIT_PATTERN = re.compile(r"[-_\s]+")


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as fh:
        payload = json.load(fh)
    if not isinstance(payload, dict):
        raise ValueError(f"{path} is not a JSON object")
    models = payload.get("models")
    if not isinstance(models, list):
        raise ValueError(f"{path} is missing a models[] list")
    return payload


def extract_keywords(raw_value: Any) -> set[str]:
    if not isinstance(raw_value, str):
        return set()

    normalized = raw_value.strip().lower()
    if not normalized:
        return set()

    parts = [part for part in SPLIT_PATTERN.split(normalized) if part]
    if len(parts) > 1:
        return set(parts)
    return {normalized}


def build_keywords(models: list[dict[str, Any]]) -> list[str]:
    keywords: set[str] = set()
    for model in models:
        if not isinstance(model, dict):
            continue
        for field in KEY_FIELDS:
            keywords.update(extract_keywords(model.get(field)))
    return sorted(keywords)


def write_json(path: Path, keywords: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        json.dump(keywords, fh, ensure_ascii=False, indent=2)
        fh.write("\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default=str(DEFAULT_INPUT), help="Path to the source model JSON file")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="Path to the keyword JSON file")
    return parser.parse_args()


def resolve_path(raw_path: str) -> Path:
    path = Path(raw_path)
    if not path.is_absolute():
        path = ROOT / path
    return path


def main() -> int:
    args = parse_args()
    input_path = resolve_path(args.input)
    output_path = resolve_path(args.output)

    source_data = load_json(input_path)
    keywords = build_keywords(source_data["models"])
    write_json(output_path, keywords)

    print(f"Models processed: {len(source_data['models'])}")
    print(f"Keywords written: {len(keywords)}")
    print(f"Output: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
