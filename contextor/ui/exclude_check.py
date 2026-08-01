import json
from pathlib import Path


def check_stale_excludes(repo_root):

    repo_root = Path(repo_root)

    manifest = repo_root / "temporary" / "manifest.json"

    if not manifest.exists():
        return []

    with open(manifest, encoding="utf-8") as f:
        data = json.load(f)

    conflicts = []

    for item in data.get("items", []):
        original = repo_root / item["original"]

        if original.exists():
            conflicts.append(item["original"])

    return conflicts
