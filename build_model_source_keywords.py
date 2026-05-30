#!/usr/bin/env python3
"""Build normalized keyword and model-name indexes from ascend model source data."""

from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
DEFAULT_INPUT = ROOT / "data" / "ascend_model_with_adapter-1-total.json"
DEFAULT_KEYWORD_OUTPUT = ROOT / "data" / "ascend_model_source_key_word.json"
DEFAULT_MODEL_NAME_OUTPUT = ROOT / "data" / "ascend_mode_source_model_name.json"
KEY_FIELDS = ("name", "adapter_framework", "adapter_hardware")
SPLIT_PATTERN = re.compile(r"[-_\s]+")
TRAILING_NUMBER_PATTERN = re.compile(r"[0-9.]+$")


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


def extract_model_name(raw_value: Any) -> str | None:
    if not isinstance(raw_value, str):
        return None

    normalized = raw_value.strip().lower()
    if not normalized:
        return None

    parts = [part for part in SPLIT_PATTERN.split(normalized) if part]
    if not parts:
        return None

    model_name = TRAILING_NUMBER_PATTERN.sub("", parts[0]).strip(".")
    return model_name or None


def normalize_id(raw_value: Any) -> int | None:
    if isinstance(raw_value, int):
        return raw_value
    return None


def build_indexes(models: list[dict[str, Any]]) -> tuple[dict[str, list[int]], dict[str, list[int]]]:
    model_name_index: dict[str, set[int]] = defaultdict(set)
    keyword_index: dict[str, set[int]] = defaultdict(set)

    for model in models:
        if not isinstance(model, dict):
            continue

        model_id = normalize_id(model.get("id"))
        if model_id is None:
            continue

        model_name = extract_model_name(model.get("name"))
        if model_name:
            model_name_index[model_name].add(model_id)

        for field in KEY_FIELDS:
            for keyword in extract_keywords(model.get(field)):
                keyword_index[keyword].add(model_id)

    for model_name in model_name_index:
        keyword_index.pop(model_name, None)

    sorted_model_name_index = {
        key: sorted(ids) for key, ids in sorted(model_name_index.items())
    }
    sorted_keyword_index = {
        key: sorted(ids) for key, ids in sorted(keyword_index.items())
    }
    return sorted_model_name_index, sorted_keyword_index


def write_json(path: Path, payload: dict[str, list[int]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)
        fh.write("\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default=str(DEFAULT_INPUT), help="Path to the source model JSON file")
    parser.add_argument(
        "--keyword-output",
        default=str(DEFAULT_KEYWORD_OUTPUT),
        help="Path to the keyword JSON file",
    )
    parser.add_argument(
        "--model-name-output",
        default=str(DEFAULT_MODEL_NAME_OUTPUT),
        help="Path to the model-name JSON file",
    )
    return parser.parse_args()


def resolve_path(raw_path: str) -> Path:
    path = Path(raw_path)
    if not path.is_absolute():
        path = ROOT / path
    return path


def main() -> int:
    args = parse_args()
    input_path = resolve_path(args.input)
    keyword_output_path = resolve_path(args.keyword_output)
    model_name_output_path = resolve_path(args.model_name_output)

    source_data = load_json(input_path)
    model_name_index, keyword_index = build_indexes(source_data["models"])
    write_json(keyword_output_path, keyword_index)
    write_json(model_name_output_path, model_name_index)

    print(f"Models processed: {len(source_data['models'])}")
    print(f"Keyword keys written: {len(keyword_index)}")
    print(f"Model name keys written: {len(model_name_index)}")
    print(f"Keyword output: {keyword_output_path}")
    print(f"Model name output: {model_name_output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
