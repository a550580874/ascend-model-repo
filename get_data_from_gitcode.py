#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


TOKEN = "k_yRB-MW4zPsQK_jSMByJCt6"
REPO_URL = "https://gitcode.com/ming-shen/Ascend-model-search.git"
BRANCH = "main"
SRC_REL_PATH = "data/ascend_model_with_adapter.json"


def run_cmd(cmd, cwd=None):
    print(f"[INFO] run: {' '.join(cmd)}")
    result = subprocess.run(
        cmd,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    if result.stdout:
        print(result.stdout.strip())
    if result.returncode != 0:
        if result.stderr:
            print(result.stderr.strip(), file=sys.stderr)
        raise RuntimeError(f"command failed: {' '.join(cmd)}")
    return result


def build_auth_repo_url(repo_url: str, token: str) -> str:
    prefix = "https://"
    if not repo_url.startswith(prefix):
        raise ValueError(f"unexpected repo url: {repo_url}")
    return f"https://oauth2:{token}@{repo_url[len(prefix):]}"


def main() -> int:
    tmp_root = Path(tempfile.mkdtemp(prefix="gitcode_pull_"))
    repo_dir = tmp_root / "repo"
    out_file = tmp_root / "ascend_model_with_adapter.json"

    print(f"[INFO] temp root: {tmp_root}")
    print(f"[INFO] repo dir: {repo_dir}")
    print(f"[INFO] out file: {out_file}")

    try:
        auth_repo_url = build_auth_repo_url(REPO_URL, TOKEN)

        run_cmd([
            "git",
            "clone",
            "--depth", "1",
            "--branch", BRANCH,
            auth_repo_url,
            str(repo_dir),
        ])

        src_file = repo_dir / SRC_REL_PATH
        if not src_file.exists():
            raise FileNotFoundError(f"source file not found: {src_file}")

        shutil.copy2(src_file, out_file)

        print(f"[INFO] copied from: {src_file}")
        print(f"[INFO] saved to: {out_file}")
        print(f"[INFO] size: {out_file.stat().st_size} bytes")

        # 给后续 GitHub Actions step 用
        github_output = None
        import os
        github_output = os.getenv("GITHUB_OUTPUT")
        if github_output:
            with open(github_output, "a", encoding="utf-8") as f:
                f.write(f"json_path={out_file}\n")

        return 0

    except Exception as e:
        print(f"[FATAL] {type(e).__name__}: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
