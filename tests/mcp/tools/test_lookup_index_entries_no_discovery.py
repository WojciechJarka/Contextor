import json

from contextor.core.report_query import catalog_from_registry
from contextor.core.reporting_engine.persistent_registry import PersistentIdentityRegistry
from contextor.mcp.tools.lookup_index_entries import lookup_index_entries


def _serialize_lookup(catalog, ids):
    result = {}
    for id_ in ids:
        normalized_id = str(id_)
        if normalized_id.upper().startswith("A"):
            normalized_id = normalized_id.upper()
            active = catalog.artifacts
            recovery = catalog.recovered_artifacts or {}
        else:
            active = catalog.modules
            recovery = catalog.recovered_modules or {}
        if normalized_id in active:
            entry = {"name": active[normalized_id], "status": "active"}
        elif normalized_id in recovery:
            entry = {"name": recovery[normalized_id], "status": "recovery"}
        else:
            entry = {"name": None, "status": "missing"}
        result[str(id_)] = entry
    return json.dumps(result, indent=2)


def test_lookup_index_entries_skips_discovery_with_exact_identity_parity(
    tmp_path, monkeypatch
):
    registry = PersistentIdentityRegistry(str(tmp_path))
    with registry.transaction():
        registry.sync_with_workspace(
            {"active.module", "recovery.module"},
            {"active.module::run", "recovery.module::run"},
        )
    active_module_id = registry.get_module_id("active.module")
    active_artifact_id = registry.get_artifact_id("active.module::run")
    recovery_module_id = registry.get_module_id("recovery.module")
    recovery_artifact_id = registry.get_artifact_id("recovery.module::run")
    with registry.transaction():
        registry.sync_with_workspace({"active.module"}, {"active.module::run"})

    ids = [
        active_module_id,
        active_artifact_id.lower(),
        recovery_module_id,
        recovery_artifact_id.lower(),
        "404/1",
    ]
    baseline = _serialize_lookup(catalog_from_registry(str(tmp_path)), ids)
    discovery_calls = {"count": 0}

    def fail_if_discovered(*_args, **_kwargs):
        discovery_calls["count"] += 1
        raise AssertionError("lookup_index_entries must not discover module paths")

    monkeypatch.setattr(
        "contextor.core.report_query.discover_module_paths", fail_if_discovered
    )

    actual = lookup_index_entries(str(tmp_path), ids)

    assert discovery_calls == {"count": 0}
    assert actual == baseline
    assert json.loads(actual) == {
        active_module_id: {"name": "active.module", "status": "active"},
        active_artifact_id.lower(): {
            "name": "active.module::run",
            "status": "active",
        },
        recovery_module_id: {"name": "recovery.module", "status": "recovery"},
        recovery_artifact_id.lower(): {
            "name": "recovery.module::run",
            "status": "recovery",
        },
        "404/1": {"name": None, "status": "missing"},
    }
