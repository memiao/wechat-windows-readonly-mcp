"""Convert wechat4-db-decrypt's all_keys.json to wxq's expected format.

wechat4-db-decrypt writes all_keys.json with a "_meta" entry plus per-DB
entries. wxq expects only the {path: {enc_key, salt, ...}} mapping.
"""

from __future__ import annotations

import json
import os
import sys


def main() -> None:
    src = sys.argv[1] if len(sys.argv) > 1 else "all_keys.json"
    dst = os.path.expanduser("~/.wxq/all_keys.json")

    with open(src, encoding="utf-8") as f:
        keys = json.load(f)

    meta = keys.pop("_meta", {})
    if meta:
        print(f"db_dir: {meta.get('db_dir', '?')}")
        print(f"version: {meta.get('version', '?')}")

    os.makedirs(os.path.dirname(dst), exist_ok=True)
    with open(dst, "w", encoding="utf-8") as f:
        json.dump(keys, f, indent=2, ensure_ascii=False)

    print(f"Converted {len(keys)} keys -> {dst}")


if __name__ == "__main__":
    main()
