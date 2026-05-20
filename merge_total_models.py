#!/usr/bin/env python3
"""Merge base and official model lists into the total model file.

Default behavior:
- base: data/ascend_model_with_adapter.json
- official: data/ascend_model_adapters_official.json
- output: data/ascend_model_with_adapter-1-total.json

The script appends every official model to the end of the base models list.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
DEFAULT_BASE = ROOT / "data" / "ascend_model_with_adapter.json"
DEFAULT_OUTPUT = ROOT / "data" / "ascend_model_with_adapter-1-total.json"
OFFICIAL_CANDIDATES = [
    ROOT / "data" / "ascend_model_adapters_official.json",
    ROOT / "data" / "ascend_model_with_adapters_official.json",
]


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, dict):
        raise ValueError(f"{path} is not a JSON object")
    models = data.get("models")
    if not isinstance(models, list):
        raise ValueError(f"{path} is missing a models[] list")
    return data


def resolve_official_path(explicit_path: str | None) -> Path:
    if explicit_path:
        path = Path(explicit_path)
        if not path.is_absolute():
            path = ROOT / path
        return path

    for candidate in OFFICIAL_CANDIDATES:
        if candidate.exists():
            return candidate

    names = ", ".join(str(path.relative_to(ROOT)) for path in OFFICIAL_CANDIDATES)
    raise FileNotFoundError(f"Could not find official model file. Tried: {names}")


def build_total(base_data: dict[str, Any], official_data: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base_data)
    base_models = list(base_data["models"])
    official_models = list(official_data["models"])
    merged["models"] = base_models + official_models
    merged["total_count"] = len(merged["models"])
    merged["collected_at"] = datetime.utcnow().isoformat()
    return merged


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)
        fh.write("\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", default=str(DEFAULT_BASE), help="Path to the base model JSON file")
    parser.add_argument(
        "--official",
        default=None,
        help="Path to the official model JSON file; if omitted, known filenames are auto-detected",
    )
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="Path to the merged output JSON file")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    base_path = Path(args.base)
    if not base_path.is_absolute():
        base_path = ROOT / base_path
    output_path = Path(args.output)
    if not output_path.is_absolute():
        output_path = ROOT / output_path
    official_path = resolve_official_path(args.official)

    base_data = load_json(base_path)
    official_data = load_json(official_path)
    merged = build_total(base_data, official_data)
    write_json(output_path, merged)

    print(f"Base models: {len(base_data['models'])}")
    print(f"Official models: {len(official_data['models'])}")
    print(f"Total models: {len(merged['models'])}")
    print(f"Output: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
