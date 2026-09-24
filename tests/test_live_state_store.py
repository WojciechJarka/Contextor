"""Unit and integration boundaries for the shared canonical LIVE snapshot store."""

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from types import SimpleNamespace

import pytest

from contextor.mcp import analysis_jobs
from contextor.core.live_state import (
    load_snapshot,
    migrate_legacy_snapshot,
    read_metadata,
    save_snapshot,
    SnapshotRevisionConflict,
)
from contextor.core.paths import app_cache_dir, legacy_repo_cache_dir, repo_cache_dir
from contextor.core.analysis.state_manager import FileStateManager, RepositoryAnalysisState
from contextor.core.domain.usage_facts import MODULE_USAGE_FACTS_SEMANTIC_VERSION
from contextor.core.reporting_engine.persistent_registry import (
    PersistentIdentityRegistry,
)

pytestmark = pytest.mark.live


def test_module_usage_manifest_roundtrips_with_repository_state(tmp_path):
    manifest={"pkg.mod":{"module_id":"pkg.mod","path":"C:/x.py","sha256":"abc","semantic_version":MODULE_USAGE_FACTS_SEMANTIC_VERSION}}
    state=RepositoryAnalysisState(module_usages_manifest=manifest)
    save_snapshot(state,tmp_path,"manifest")
    loaded,_=load_snapshot(tmp_path,"manifest")
    assert loaded.module_usages_manifest == manifest


def test_legacy_state_without_manifest_loads_with_empty_manifest(tmp_path):
    legacy=SimpleNamespace(modules={},dependency_graph=None,module_usages={})
    save_snapshot(legacy,tmp_path,"legacy-manifest")
    loaded,_=load_snapshot(tmp_path,"legacy-manifest")
    assert loaded.module_usages_manifest == {}


def _split_lineage_test_state(*source_keys):
    from contextor.core.analysis.state_manager import (
        RepositoryAnalysisState,
    )
    from contextor.core.domain.lineage_facts import (
        LINEAGE_FACTS_SEMANTIC_VERSION,
        LineageFamilyStatus,
        MaterializedLineageSourceFacts,
        SourceLineageManifest,
    )

    sources = {}

    for index, source_key in enumerate(
        source_keys
    ):
        sources[source_key] = (
            MaterializedLineageSourceFacts(
                manifest=SourceLineageManifest(
                    source_key=source_key,
                    source_fingerprint=(
                        f"source-{index}"
                    ),
                    semantic_version=(
                        LINEAGE_FACTS_SEMANTIC_VERSION
                    ),
                    status=(
                        LineageFamilyStatus.FRESH
                    ),
                    anchor_count=0,
                    flow_count=0,
                    surface_count=0,
                )
            )
        )

    return RepositoryAnalysisState(
        lineage_facts_by_source=sources,
        lineage_facts_state=(
            LineageFamilyStatus.FRESH.value
        ),
        lineage_facts_semantic_version=(
            LINEAGE_FACTS_SEMANTIC_VERSION
        ),
    )


def test_snapshot_roundtrip_increments_revision_and_records_writer(tmp_path):
    first = save_snapshot({"value": 1}, tmp_path, "state-a", writer="desktop")
    second = save_snapshot({"value": 2}, tmp_path, "state-a", writer="mcp")

    state, metadata = load_snapshot(tmp_path, "state-a")

    assert state == {"value": 2}
    assert (first.revision, second.revision, metadata.revision) == (1, 2, 2)
    assert metadata.writer == "mcp"
    assert read_metadata(tmp_path) == metadata


def test_default_snapshot_publishes_final_pickle_via_temp_replace(tmp_path, monkeypatch):
    import contextor.core.live_state.store as store

    replacements = []
    original_replace = store.os.replace
    monkeypatch.setattr(store.os, "replace", lambda source, target: (replacements.append((source, target)), original_replace(source, target))[1])
    save_snapshot({"value": 1}, tmp_path, "state-a")
    assert replacements[0][1].name == "engine_state.pkl"
    assert replacements[0][0].name != "engine_state.pkl"
    assert replacements[0][0].name.endswith(".tmp")


def test_cleanup_failure_cannot_mask_persistence_failure_or_leak_lock(tmp_path, monkeypatch):
    import contextor.core.live_state.store as store

    baseline = save_snapshot({"value": 1}, tmp_path, "state-a")
    original_replace = store.os.replace
    original_unlink = type(tmp_path).unlink

    def failing_replace(source, target):
        if target.name == "engine_state.meta.json":
            raise RuntimeError("authoritative persistence failure")
        return original_replace(source, target)

    monkeypatch.setattr(store.os, "replace", failing_replace)
    def failing_unlink(self, *args, **kwargs):
        if self.name == "engine_state.lock":
            return original_unlink(self, *args, **kwargs)
        raise OSError("cleanup failure")
    monkeypatch.setattr(type(tmp_path), "unlink", failing_unlink)
    with pytest.raises(RuntimeError, match="authoritative persistence failure"):
        save_snapshot({"value": 2}, tmp_path, "state-a", exact_revision=baseline.revision + 1, file_state_payload={"_meta": {"state_id": "state-a", "revision": baseline.revision + 1}, "files": {}})
    assert read_metadata(tmp_path).revision == baseline.revision
    monkeypatch.setattr(type(tmp_path), "unlink", original_unlink)
    monkeypatch.setattr(store.os, "replace", original_replace)
    assert save_snapshot({"value": 3}, tmp_path, "state-a").revision == baseline.revision + 1


def test_exact_snapshot_revision_rules_and_disk_ahead_without_overwrite(tmp_path):
    with pytest.raises(SnapshotRevisionConflict):
        save_snapshot(SimpleNamespace(value="bad"), tmp_path, "state-a", exact_revision=11, file_state_payload={"_meta": {"state_id": "state-a", "revision": 11}, "files": {}})
    save_snapshot(SimpleNamespace(value="ahead"), tmp_path, "state-a", exact_revision=1, file_state_payload={"_meta": {"state_id": "state-a", "revision": 1}, "files": {}})
    for _ in range(9):
        save_snapshot(SimpleNamespace(value="ahead"), tmp_path, "state-a")
    with pytest.raises(SnapshotRevisionConflict):
        save_snapshot(SimpleNamespace(value="bad"), tmp_path, "state-a", exact_revision=12, file_state_payload={"_meta": {"state_id": "state-a", "revision": 12}, "files": {}})
    save_snapshot(SimpleNamespace(value="ahead"), tmp_path, "state-a", exact_revision=11, file_state_payload={"_meta": {"state_id": "state-a", "revision": 11}, "files": {}})
    candidate = SimpleNamespace(value="candidate")
    with pytest.raises(SnapshotRevisionConflict) as exc_info:
        save_snapshot(candidate, tmp_path, "state-a", exact_revision=11, file_state_payload={"_meta": {"state_id": "state-a", "revision": 11}, "files": {}})
    assert (exc_info.value.current_revision, exc_info.value.requested_revision) == (11, 11)
    with pytest.raises(SnapshotRevisionConflict):
        save_snapshot(candidate, tmp_path, "state-a", exact_revision=10, file_state_payload={"_meta": {"state_id": "state-a", "revision": 10}, "files": {}})


def test_exact_snapshot_rejects_file_state_payload_mismatches(tmp_path):
    state = SimpleNamespace(value="candidate")
    with pytest.raises(ValueError, match="state_id"):
        save_snapshot(state, tmp_path, "state-a", exact_revision=1, file_state_payload={"_meta": {"state_id": "other", "revision": 1}, "files": {}})
    with pytest.raises(ValueError, match="revision"):
        save_snapshot(state, tmp_path, "state-a", exact_revision=1, file_state_payload={"_meta": {"state_id": "state-a", "revision": 2}, "files": {}})


def test_legacy_dict_snapshot_returns_tuple(tmp_path):
    (tmp_path / "engine_state.pkl").write_bytes(__import__("pickle").dumps({"legacy": True}))
    (tmp_path / "engine_state.meta.json").write_text(
        '{"schema_version":"1.2","state_id":"legacy","revision":1}',
        encoding="utf-8",
    )
    loaded = load_snapshot(tmp_path, "legacy")
    assert loaded is not None
    assert loaded[0] == {"legacy": True}


def test_exact_snapshot_revision_binds_embedded_state_and_metadata(tmp_path):
    candidate = SimpleNamespace(value="candidate")
    metadata = save_snapshot(candidate, tmp_path, "state-a", exact_revision=1, file_state_payload={"_meta": {"state_id": "state-a", "revision": 1}, "files": {}})
    loaded, loaded_metadata = load_snapshot(tmp_path, "state-a")
    assert metadata.revision == loaded_metadata.revision == loaded.revision == 1


def test_exact_schema_13_splits_lineage_and_roundtrips(tmp_path):
    import json
    import pickle

    state = _split_lineage_test_state(
        "pkg/a.py",
        "pkg/b.py",
    )

    metadata = save_snapshot(
        state,
        tmp_path,
        "sid",
        exact_revision=1,
        file_state_payload={
            "_meta": {
                "state_id": "sid",
                "revision": 1,
            },
            "files": {},
        },
    )

    assert metadata.schema_version == "1.3"
    assert metadata.lineage_manifest_file

    with (
        tmp_path
        / metadata.state_file
    ).open("rb") as stream:
        core_payload = pickle.load(
            stream
        )

    assert (
        core_payload[
            "state"
        ].lineage_facts_by_source
        == {}
    )

    manifest = json.loads(
        (
            tmp_path
            / metadata.lineage_manifest_file
        ).read_text(
            encoding="utf-8"
        )
    )

    assert (
        manifest[
            "schema_version"
        ]
        == "1.0"
    )
    assert (
        manifest[
            "state_id"
        ]
        == "sid"
    )
    assert (
        manifest[
            "revision"
        ]
        == 1
    )
    assert set(
        manifest[
            "sources"
        ]
    ) == {
        "pkg/a.py",
        "pkg/b.py",
    }

    for entry in manifest[
        "sources"
    ].values():
        assert (
            tmp_path
            / entry[
                "file"
            ]
        ).is_file()

    loaded_state, loaded_metadata = (
        load_snapshot(
            tmp_path,
            "sid",
        )
    )

    assert loaded_metadata == metadata
    assert (
        loaded_state.lineage_facts_by_source
        == state.lineage_facts_by_source
    )


def test_exact_split_lineage_reuses_unchanged_source_chunks_by_identity(
    tmp_path,
):
    import json
    from dataclasses import replace

    state = _split_lineage_test_state(
        "pkg/a.py",
        "pkg/b.py",
    )

    first = save_snapshot(
        state,
        tmp_path,
        "sid",
        exact_revision=1,
        file_state_payload={
            "_meta": {
                "state_id": "sid",
                "revision": 1,
            },
            "files": {},
        },
    )

    first_manifest = json.loads(
        (
            tmp_path
            / first.lineage_manifest_file
        ).read_text(
            encoding="utf-8"
        )
    )

    candidate = state.clone_for_update()

    previous_b = (
        candidate.lineage_facts_by_source[
            "pkg/b.py"
        ]
    )

    candidate.lineage_facts_by_source[
        "pkg/b.py"
    ] = replace(
        previous_b,
        manifest=replace(
            previous_b.manifest,
            source_fingerprint=(
                "source-1-next"
            ),
        ),
    )

    second = save_snapshot(
        candidate,
        tmp_path,
        "sid",
        exact_revision=2,
        file_state_payload={
            "_meta": {
                "state_id": "sid",
                "revision": 2,
            },
            "files": {},
        },
        previous_state=state,
    )

    second_manifest = json.loads(
        (
            tmp_path
            / second.lineage_manifest_file
        ).read_text(
            encoding="utf-8"
        )
    )

    assert (
        second_manifest[
            "sources"
        ][
            "pkg/a.py"
        ][
            "file"
        ]
        == first_manifest[
            "sources"
        ][
            "pkg/a.py"
        ][
            "file"
        ]
    )

    assert (
        second_manifest[
            "sources"
        ][
            "pkg/b.py"
        ][
            "file"
        ]
        != first_manifest[
            "sources"
        ][
            "pkg/b.py"
        ][
            "file"
        ]
    )

    assert len(
        list(
            tmp_path.glob(
                "lineage_source.r2.*.pkl"
            )
        )
    ) == 1

    loaded_state, loaded_metadata = (
        load_snapshot(
            tmp_path,
            "sid",
        )
    )

    assert loaded_metadata == second

    assert (
        loaded_state.lineage_facts_by_source
        == candidate.lineage_facts_by_source
    )


def test_exact_split_lineage_does_not_reuse_equal_distinct_slice(
    tmp_path,
):
    import json
    from dataclasses import replace

    state = _split_lineage_test_state(
        "pkg/a.py"
    )

    first = save_snapshot(
        state,
        tmp_path,
        "sid",
        exact_revision=1,
        file_state_payload={
            "_meta": {
                "state_id": "sid",
                "revision": 1,
            },
            "files": {},
        },
    )

    first_manifest = json.loads(
        (
            tmp_path
            / first.lineage_manifest_file
        ).read_text(
            encoding="utf-8"
        )
    )

    candidate = state.clone_for_update()

    previous_slice = (
        state.lineage_facts_by_source[
            "pkg/a.py"
        ]
    )

    equal_distinct = replace(
        previous_slice
    )

    assert (
        equal_distinct
        == previous_slice
    )

    assert (
        equal_distinct
        is not previous_slice
    )

    candidate.lineage_facts_by_source[
        "pkg/a.py"
    ] = equal_distinct

    second = save_snapshot(
        candidate,
        tmp_path,
        "sid",
        exact_revision=2,
        file_state_payload={
            "_meta": {
                "state_id": "sid",
                "revision": 2,
            },
            "files": {},
        },
        previous_state=state,
    )

    second_manifest = json.loads(
        (
            tmp_path
            / second.lineage_manifest_file
        ).read_text(
            encoding="utf-8"
        )
    )

    assert (
        second_manifest[
            "sources"
        ][
            "pkg/a.py"
        ][
            "file"
        ]
        != first_manifest[
            "sources"
        ][
            "pkg/a.py"
        ][
            "file"
        ]
    )

    assert len(
        list(
            tmp_path.glob(
                "lineage_source.r2.*.pkl"
            )
        )
    ) == 1


def test_split_lineage_reuse_failure_preserves_previous_chunk(
    tmp_path,
    monkeypatch,
):
    import json
    from dataclasses import replace

    import contextor.core.live_state.store as store

    state = _split_lineage_test_state(
        "pkg/a.py",
        "pkg/b.py",
    )

    first = save_snapshot(
        state,
        tmp_path,
        "sid",
        exact_revision=1,
        file_state_payload={
            "_meta": {
                "state_id": "sid",
                "revision": 1,
            },
            "files": {},
        },
    )

    first_manifest = json.loads(
        (
            tmp_path
            / first.lineage_manifest_file
        ).read_text(
            encoding="utf-8"
        )
    )

    reused_chunk = (
        tmp_path
        / first_manifest[
            "sources"
        ][
            "pkg/a.py"
        ][
            "file"
        ]
    )

    candidate = state.clone_for_update()

    previous_b = (
        candidate.lineage_facts_by_source[
            "pkg/b.py"
        ]
    )

    candidate.lineage_facts_by_source[
        "pkg/b.py"
    ] = replace(
        previous_b,
        manifest=replace(
            previous_b.manifest,
            source_fingerprint=(
                "source-1-next"
            ),
        ),
    )

    original_replace = store.os.replace

    def fail_metadata_replace(
        source,
        target,
    ):
        if (
            Path(
                target
            ).name
            == "engine_state.meta.json"
        ):
            raise RuntimeError(
                "synthetic metadata commit failure"
            )

        return original_replace(
            source,
            target,
        )

    monkeypatch.setattr(
        store.os,
        "replace",
        fail_metadata_replace,
    )

    with pytest.raises(
        RuntimeError,
        match=(
            "^synthetic metadata commit failure$"
        ),
    ):
        save_snapshot(
            candidate,
            tmp_path,
            "sid",
            exact_revision=2,
            file_state_payload={
                "_meta": {
                    "state_id": "sid",
                    "revision": 2,
                },
                "files": {},
            },
            previous_state=state,
        )

    assert reused_chunk.is_file()

    assert (
        read_metadata(
            tmp_path
        ).revision
        == 1
    )

    assert not list(
        tmp_path.glob(
            "engine_state.r2.*.pkl"
        )
    )

    assert not list(
        tmp_path.glob(
            "file_state.r2.*.json"
        )
    )

    assert not list(
        tmp_path.glob(
            "lineage_manifest.r2.*.json"
        )
    )

    assert not list(
        tmp_path.glob(
            "lineage_source.r2.*.pkl"
        )
    )


@pytest.mark.parametrize(
    "failure",
    [
        "missing_chunk",
        "manifest_revision",
        "corrupt_chunk",
    ],
)
def test_split_lineage_corruption_fails_closed(
    tmp_path,
    failure,
):
    import json

    state = _split_lineage_test_state(
        "pkg/a.py"
    )

    metadata = save_snapshot(
        state,
        tmp_path,
        "sid",
        exact_revision=1,
        file_state_payload={
            "_meta": {
                "state_id": "sid",
                "revision": 1,
            },
            "files": {},
        },
    )

    manifest_path = (
        tmp_path
        / metadata.lineage_manifest_file
    )

    manifest = json.loads(
        manifest_path.read_text(
            encoding="utf-8"
        )
    )

    entry = manifest[
        "sources"
    ][
        "pkg/a.py"
    ]

    chunk_path = (
        tmp_path
        / entry[
            "file"
        ]
    )

    if failure == "missing_chunk":
        chunk_path.unlink()

    elif failure == "manifest_revision":
        manifest[
            "revision"
        ] = 2
        manifest_path.write_text(
            json.dumps(
                manifest,
                indent=2,
                sort_keys=True,
            ),
            encoding="utf-8",
        )

    elif failure == "corrupt_chunk":
        chunk_path.write_bytes(
            b"not-a-pickle"
        )

    assert (
        load_snapshot(
            tmp_path,
            "sid",
        )
        is None
    )


def test_split_lineage_failed_metadata_commit_cleans_new_generation(
    tmp_path,
    monkeypatch,
):
    import contextor.core.live_state.store as store

    state = _split_lineage_test_state(
        "pkg/a.py",
        "pkg/b.py",
    )

    baseline = save_snapshot(
        state,
        tmp_path,
        "sid",
        exact_revision=1,
        file_state_payload={
            "_meta": {
                "state_id": "sid",
                "revision": 1,
            },
            "files": {},
        },
    )

    candidate = state.clone_for_update()

    original_replace = (
        store.os.replace
    )

    def fail_metadata_replace(
        source,
        target,
    ):
        if (
            Path(
                target
            ).name
            == "engine_state.meta.json"
        ):
            raise RuntimeError(
                "synthetic metadata commit failure"
            )

        return original_replace(
            source,
            target,
        )

    monkeypatch.setattr(
        store.os,
        "replace",
        fail_metadata_replace,
    )

    with pytest.raises(
        RuntimeError,
        match=(
            "^synthetic metadata commit failure$"
        ),
    ):
        save_snapshot(
            candidate,
            tmp_path,
            "sid",
            exact_revision=2,
            file_state_payload={
                "_meta": {
                    "state_id": "sid",
                    "revision": 2,
                },
                "files": {},
            },
        )

    assert (
        read_metadata(
            tmp_path
        ).revision
        == baseline.revision
    )

    assert not list(
        tmp_path.glob(
            "engine_state.r2.*.pkl"
        )
    )
    assert not list(
        tmp_path.glob(
            "file_state.r2.*.json"
        )
    )
    assert not list(
        tmp_path.glob(
            "lineage_manifest.r2.*.json"
        )
    )
    assert not list(
        tmp_path.glob(
            "lineage_source.r2.*.pkl"
        )
    )


def test_schema_12_monolithic_snapshot_remains_loadable(
    tmp_path,
):
    import json
    import pickle

    from contextor.core.analysis.state_manager import (
        RepositoryAnalysisState,
    )

    state = RepositoryAnalysisState()
    state.state_id = "legacy-sid"
    state.revision = 1

    state_file = (
        "engine_state.r1.legacy.pkl"
    )

    metadata = {
        "schema_version": "1.2",
        "state_id": "legacy-sid",
        "revision": 1,
        "writer": "legacy",
        "repo_id": "",
        "root_path": "",
        "state_file": state_file,
        "file_state_file": "",
    }

    with (
        tmp_path
        / state_file
    ).open("wb") as stream:
        pickle.dump(
            {
                "metadata": metadata,
                "state": state,
            },
            stream,
        )

    (
        tmp_path
        / "engine_state.meta.json"
    ).write_text(
        json.dumps(
            metadata,
            indent=2,
        ),
        encoding="utf-8",
    )

    loaded_state, loaded_metadata = (
        load_snapshot(
            tmp_path,
            "legacy-sid",
        )
    )

    assert (
        loaded_metadata.schema_version
        == "1.2"
    )
    assert (
        loaded_metadata.lineage_manifest_file
        == ""
    )
    assert (
        loaded_state.state_id
        == "legacy-sid"
    )
    assert (
        loaded_state.revision
        == 1
    )


def test_build_payload_is_side_effect_free(tmp_path):
    manager = FileStateManager(str(tmp_path))
    manager.state_id = "sid-r1"
    manager.revision = 1
    payload = manager.build_payload("sid-r2", 2)
    assert manager.state_id == "sid-r1"
    assert manager.revision == 1
    assert payload["_meta"] == {"state_id": "sid-r2", "revision": 2}


@pytest.mark.parametrize("failure", ["missing", "invalid", "oserror"])
def test_referenced_filestate_generation_fail_closed_without_legacy_fallback(tmp_path, monkeypatch, failure):
    import builtins
    import json

    manager = FileStateManager(str(tmp_path))
    manager._state = {}
    manager.save("sid", revision=1)
    metadata = {
        "schema_version": "1.2",
        "state_id": "sid",
        "revision": 2,
        "file_state_file": "file_state.r2.test.json",
    }
    (tmp_path / "engine_state.meta.json").write_text(json.dumps(metadata), encoding="utf-8")
    (tmp_path / "file_state.json").write_text(json.dumps({"files": {"legacy.py": {"size": 1}}}), encoding="utf-8")
    referenced = tmp_path / "file_state.r2.test.json"
    if failure == "invalid":
        referenced.write_text("{not-json", encoding="utf-8")
    elif failure == "oserror":
        original_open = builtins.open
        def raising_open(path, *args, **kwargs):
            if str(path).endswith("file_state.r2.test.json"):
                raise OSError("synthetic read failure")
            return original_open(path, *args, **kwargs)
        monkeypatch.setattr(builtins, "open", raising_open)
    reloaded = FileStateManager(str(tmp_path))
    assert reloaded._state == {}
    assert reloaded.revision is None


def test_referenced_filestate_without_meta_fails_closed(tmp_path):
    import json

    (tmp_path / "engine_state.meta.json").write_text(
        json.dumps({"state_id": "sid", "revision": 2, "file_state_file": "file_state.r2.json"}),
        encoding="utf-8",
    )
    (tmp_path / "file_state.r2.json").write_text(
        json.dumps({"files": {"current.py": {"size": 4}}}),
        encoding="utf-8",
    )
    manager = FileStateManager(str(tmp_path))
    assert manager._state == {}
    assert manager.state_id == ""
    assert manager.revision is None


def test_legacy_filestate_without_meta_loads_entries_but_remains_unverified(tmp_path):
    import json

    (tmp_path / "engine_state.meta.json").write_text(
        json.dumps({"state_id": "sid", "revision": 2}),
        encoding="utf-8",
    )
    (tmp_path / "file_state.json").write_text(
        json.dumps({"legacy.py": {"size": 4}}),
        encoding="utf-8",
    )
    manager = FileStateManager(str(tmp_path))
    assert "legacy.py" in manager._state
    assert manager.state_id == ""
    assert manager.revision is None


def test_snapshot_rejects_a_different_state_identity(tmp_path):
    save_snapshot(SimpleNamespace(value=1), tmp_path, "current")

    assert load_snapshot(tmp_path, "stale") is None


def test_snapshot_rejects_wrong_repository_identity_or_root(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    save_snapshot(
        {"value": 1},
        tmp_path / "cache",
        "current",
        repo_id="ctx_12345678",
        root_path=str(repo),
    )

    assert load_snapshot(
        tmp_path / "cache",
        expected_repo_id="ctx_87654321",
        expected_root_path=str(repo),
    ) is None
    assert load_snapshot(
        tmp_path / "cache",
        expected_repo_id="ctx_12345678",
        expected_root_path=str(tmp_path / "other"),
    ) is None


def test_legacy_snapshot_migrates_to_repo_id_cache_without_deleting_source(
    tmp_path, monkeypatch
):
    cache_root = tmp_path / "cache"
    monkeypatch.setenv("CONTEXTOR_CACHE_DIR", str(cache_root))
    repo = tmp_path / "repo"
    repo.mkdir()
    legacy = legacy_repo_cache_dir(repo)
    save_snapshot({"value": 7}, legacy, "legacy-state", writer="desktop")
    (legacy / "file_state.json").write_text('{"files": {}}', encoding="utf-8")
    registry = PersistentIdentityRegistry(str(repo))

    target = migrate_legacy_snapshot(repo)
    loaded = load_snapshot(
        target,
        expected_repo_id=registry.repo_id,
        expected_root_path=str(repo),
    )

    assert target == repo_cache_dir(repo)
    assert loaded is not None and loaded[0] == {"value": 7}
    assert loaded[1].repo_id == registry.repo_id
    assert (target / "file_state.json").is_file()
    assert (legacy / "engine_state.pkl").is_file()


def test_concurrent_writers_publish_complete_monotonic_snapshots(tmp_path):
    def publish(value):
        return save_snapshot({"value": value}, tmp_path, "same", writer=str(value)).revision

    with ThreadPoolExecutor(max_workers=4) as pool:
        revisions = sorted(pool.map(publish, range(8)))

    state, metadata = load_snapshot(tmp_path, "same")
    assert revisions == list(range(1, 9))
    assert metadata.revision == 8
    assert state["value"] in range(8)


def test_mcp_and_desktop_resolve_the_same_repository_cache(monkeypatch, tmp_path):
    monkeypatch.setattr("contextor.core.paths.app_cache_dir", lambda: tmp_path)

    assert analysis_jobs._mcp_cache_root(tmp_path / "repo") == tmp_path
