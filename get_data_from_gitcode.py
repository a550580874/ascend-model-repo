#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
from pathlib import Path

import requests


URL = "https://raw.gitcode.com/ming-shen/Ascend-model-search/raw/main/data/ascend_model_with_adapter.json"
OUT_DIR = Path("./data")
OUT_FILE = OUT_DIR / "ascend_model_with_adapter.json"


def download_json(url: str, out_file: Path) -> None:
    out_file.parent.mkdir(parents=True, exist_ok=True)

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept": "application/json,text/plain,*/*",
        "Referer": "https://gitcode.com/",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
    }

    session = requests.Session()
    resp = session.get(url, headers=headers, timeout=60, allow_redirects=True)

    try:
        resp.raise_for_status()
    except requests.HTTPError as e:
        print(f"[ERROR] 下载失败: {e}", file=sys.stderr)
        print(f"[ERROR] status_code={resp.status_code}", file=sys.stderr)
        print(f"[ERROR] response_text={resp.text[:500]}", file=sys.stderr)
        raise

    out_file.write_bytes(resp.content)
    print(f"[INFO] 下载成功: {url}")
    print(f"[INFO] 已保存到: {out_file.resolve()}")
    print(f"[INFO] 文件大小: {out_file.stat().st_size} bytes")


def main() -> int:
    try:
        download_json(URL, OUT_FILE)
        return 0
    except Exception as e:
        print(f"[FATAL] {type(e).__name__}: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
