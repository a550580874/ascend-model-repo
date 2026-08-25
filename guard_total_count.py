#!/usr/bin/env python3
"""镜像更新降级守护：拒绝 total_count 大幅下降的更新。

用于 main5.yml 镜像上游 JSON 时：新下载文件的 total_count 相对仓库现有版本
大幅下降（默认超 20%）时，恢复仓库旧版本并跳过该文件的本次更新；
不变或增加则放行。脚本永远以 0 退出（不阻断工作流），仅在拒绝时恢复文件。

用法:
  python guard_total_count.py [json_path ...]
"""

import json
import subprocess
import sys

DROP_RATIO = 0.8  # 新值低于旧值的 80%（下降超 20%）视为大幅下降，拒绝本次更新

# 只守护官方适配器文件（上游横跳缩水的是它）；其他镜像文件不做守护
DEFAULT_FILES = [
    "data/ascend_model_adapters_official.json",
]


def main(paths):
    for path in paths:
        try:
            with open(path, encoding="utf-8") as f:
                new = json.load(f).get("total_count")
        except Exception as e:  # noqa: BLE001
            print(f"[guard] {path}: 读取新文件失败（{e}），放行")
            continue

        old_raw = subprocess.run(
            ["git", "show", f"HEAD:{path}"],
            capture_output=True, text=True,
        )
        if old_raw.returncode != 0:
            print(f"[guard] {path}: 仓库无旧版本（首次出现，total={new}），放行")
            continue

        try:
            old = json.loads(old_raw.stdout).get("total_count")
        except Exception:  # noqa: BLE001
            old = None
        if not isinstance(old, int) or not isinstance(new, int):
            print(f"[guard] {path}: total_count 缺失/异常（old={old!r} new={new!r}），放行")
            continue

        if new < old * DROP_RATIO:
            print(
                f"[guard] REJECT {path}: total_count 大幅下降 {old} -> {new}"
                f"（下降 {(1 - new / old) * 100:.1f}%），恢复仓库旧版本并跳过本次更新"
            )
            subprocess.run(["git", "checkout", "--", path], check=True)
        else:
            print(f"[guard] ACCEPT {path}: total_count {old} -> {new}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:] or DEFAULT_FILES))
