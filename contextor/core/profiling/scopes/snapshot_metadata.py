"""Validated observation of committed metadata without snapshot hydration."""

import json
from pathlib import Path

from contextor.core.paths import repo_cache_dir
from contextor.core.repository_identity import read_repository_identity
from contextor.core.live_state.store import LIVE_STATE_SCHEMA_VERSION, read_metadata

PRESETS = ("resolve_cache", "read_metadata", "validate_identity")
SCHEMAS = frozenset({"1.0", "1.1", "1.2", "1.3", LIVE_STATE_SCHEMA_VERSION})


def run_scope(root: Path, recorder) -> dict[str, object]:
    with recorder.span("resolve_cache"):
        identity = read_repository_identity(root)
        if identity is None:
            return {"status": "unavailable", "reason": "repository_not_registered"}
        cache_dir = repo_cache_dir(root)
    with recorder.span("read_metadata"):
        try:
            metadata = read_metadata(cache_dir)
        except (AttributeError, OSError, TypeError, ValueError):
            return {"status": "invalid_data", "reason": "metadata_unreadable"}
    if metadata is None:
        return {"status": "unavailable", "reason": "metadata_unavailable"}
    with recorder.span("validate_identity"):
        path = cache_dir / "engine_state.meta.json"
        try:
            first = path.read_bytes()
            second = path.read_bytes()
        except OSError:
            return {"status": "invalid_data", "reason": "metadata_unreadable"}
        if first != second:
            return {"status": "changed_during_read", "reason": "metadata_changed"}
        try:
            raw = json.loads(first.decode("utf-8"))
        except (UnicodeError, json.JSONDecodeError):
            return {"status": "invalid_data", "reason": "metadata_unreadable"}
        if not isinstance(raw, dict):
            return {"status": "invalid_data", "reason": "metadata_not_object"}
        revision = raw.get("revision")
        if type(revision) is not int or revision <= 0 or revision != metadata.revision:
            return {"status": "invalid_data", "reason": "invalid_raw_revision"}
        defaults = {
            "schema_version": "1.0", "state_id": "", "writer": "legacy",
            "repo_id": "", "root_path": "", "state_file": "",
            "file_state_file": "", "lineage_manifest_file": "",
        }
        if any(raw.get(key, default) != getattr(metadata, key)
               for key, default in defaults.items()):
            return {"status": "invalid_identity", "reason": "metadata_field_mismatch"}
        if not metadata.state_id or metadata.schema_version not in SCHEMAS:
            return {"status": "invalid_identity", "reason": "metadata_identity_invalid"}
        try:
            matches = metadata.repo_id == identity.repo_id and Path(metadata.root_path).expanduser().resolve() == root.resolve()
        except (OSError, ValueError, TypeError):
            matches = False
        if not matches:
            return {"status": "invalid_identity", "reason": "metadata_identity_mismatch"}
    return {
        "status": "ok",
        "durable_revision": revision,
        "snapshot_schema_version": metadata.schema_version,
        "identity_verified": True,
        "data_source": "durable_snapshot_metadata",
    }
