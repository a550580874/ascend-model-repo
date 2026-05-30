#!/usr/bin/env python3
"""Build normalized keyword and model-name indexes from ascend model source data."""

from __future__ import annotations

import argparse
import json
import random
import re
from collections import defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
DEFAULT_INPUT = ROOT / "data" / "ascend_model_with_adapter-1-total.json"
DEFAULT_KEYWORD_OUTPUT = ROOT / "data" / "ascend_model_source_key_word.json"
DEFAULT_MODEL_NAME_OUTPUT = ROOT / "data" / "ascend_mode_source_model_name.json"
DEFAULT_FRAMEWORK_OUTPUT = ROOT / "data" / "ascend_model_source_framework.json"
DEFAULT_HARDWARE_OUTPUT = ROOT / "data" / "ascend_model_source_hardware.json"
KEY_FIELDS = ("name", "adapter_framework", "adapter_hardware")
SPLIT_PATTERN = re.compile(r"[-_\s]+")
TRAILING_NUMBER_PATTERN = re.compile(r"[0-9.]+$")
ID_PREFIX = "55058087"


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
    if len(model_name) <= 2:
        return None
    return model_name or None


def normalize_id(raw_value: Any) -> int | None:
    if isinstance(raw_value, int):
        return raw_value
    if isinstance(raw_value, str):
        normalized = raw_value.strip()
        if normalized.isdigit():
            return int(normalized)
    return None


def normalize_value(raw_value: Any) -> str | None:
    if not isinstance(raw_value, str):
        return None
    normalized = raw_value.strip().lower()
    return normalized or None


def resolve_name_value(model: dict[str, Any]) -> Any:
    return model.get("name") or model.get("model_name")


def assign_missing_ids(source_data: dict[str, Any]) -> int:
    models = source_data["models"]
    existing_ids = {
        model_id
        for model in models
        if isinstance(model, dict)
        for model_id in [normalize_id(model.get("id"))]
        if model_id is not None
    }
    assigned_count = 0

    for model in models:
        if not isinstance(model, dict):
            continue
        if normalize_id(model.get("id")) is not None:
            continue
        if not model.get("open_date"):
            continue

        while True:
            random_suffix = random.randint(1000, 9999)
            synthetic_id = int(f"{ID_PREFIX}{random_suffix}")
            if synthetic_id not in existing_ids:
                existing_ids.add(synthetic_id)
                model["id"] = synthetic_id
                assigned_count += 1
                break

    return assigned_count


def build_indexes(
    models: list[dict[str, Any]]
) -> tuple[dict[str, list[int]], dict[str, list[int]], dict[str, list[int]], dict[str, list[int]]]:
    model_name_index: dict[str, set[int]] = defaultdict(set)
    keyword_index: dict[str, set[int]] = defaultdict(set)
    framework_index: dict[str, set[int]] = defaultdict(set)
    hardware_index: dict[str, set[int]] = defaultdict(set)

    for model in models:
        if not isinstance(model, dict):
            continue

        model_id = normalize_id(model.get("id"))
        if model_id is None:
            continue

        name_value = resolve_name_value(model)
        model_name = extract_model_name(name_value)
        if model_name:
            model_name_index[model_name].add(model_id)

        framework = normalize_value(model.get("adapter_framework"))
        if framework:
            framework_index[framework].add(model_id)

        hardware = normalize_value(model.get("adapter_hardware"))
        if hardware:
            hardware_index[hardware].add(model_id)

        model_keywords: set[str] = set()
        for field in KEY_FIELDS:
            if field == "name":
                model_keywords.update(extract_keywords(name_value))
            else:
                model_keywords.update(extract_keywords(model.get(field)))

        if model_name:
            model_keywords.discard(model_name)

        for keyword in model_keywords:
            keyword_index[keyword].add(model_id)

    sorted_model_name_index = {
        key: sorted(ids) for key, ids in sorted(model_name_index.items())
    }
    sorted_keyword_index = {
        key: sorted(ids) for key, ids in sorted(keyword_index.items())
    }
    sorted_framework_index = {
        key: sorted(ids) for key, ids in sorted(framework_index.items())
    }
    sorted_hardware_index = {
        key: sorted(ids) for key, ids in sorted(hardware_index.items())
    }
    return sorted_model_name_index, sorted_keyword_index, sorted_framework_index, sorted_hardware_index


def write_json(path: Path, payload: Any) -> None:
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
    parser.add_argument(
        "--framework-output",
        default=str(DEFAULT_FRAMEWORK_OUTPUT),
        help="Path to the framework JSON file",
    )
    parser.add_argument(
        "--hardware-output",
        default=str(DEFAULT_HARDWARE_OUTPUT),
        help="Path to the hardware JSON file",
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
    framework_output_path = resolve_path(args.framework_output)
    hardware_output_path = resolve_path(args.hardware_output)

    source_data = load_json(input_path)
    assigned_count = assign_missing_ids(source_data)
    if assigned_count:
        write_json(input_path, source_data)
    model_name_index, keyword_index, framework_index, hardware_index = build_indexes(source_data["models"])
    write_json(keyword_output_path, keyword_index)
    write_json(model_name_output_path, model_name_index)
    write_json(framework_output_path, framework_index)
    write_json(hardware_output_path, hardware_index)

    print(f"Models processed: {len(source_data['models'])}")
    print(f"Missing ids assigned: {assigned_count}")
    print(f"Keyword keys written: {len(keyword_index)}")
    print(f"Model name keys written: {len(model_name_index)}")
    print(f"Framework keys written: {len(framework_index)}")
    print(f"Hardware keys written: {len(hardware_index)}")
    print(f"Keyword output: {keyword_output_path}")
    print(f"Model name output: {model_name_output_path}")
    print(f"Framework output: {framework_output_path}")
    print(f"Hardware output: {hardware_output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
