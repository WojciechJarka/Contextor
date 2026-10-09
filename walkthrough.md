# L33/L34 snapshot fail-closed repair

## CURRENT_HEAD

`54af6542c35ab2c42e2bccb634ddc3a578f8818d` (`git rev-parse HEAD` before edits). Initial `git status --short` and both relevant file diffs were empty; the existing L33/L34 reproducer source was read before editing. Contextor MCP was used first, including deferred-tool inventory, tool documentation, `get_module_context`, `get_symbol_implementation`, `get_source_range`, and `get_symbol_lineage`. `load_snapshot` resolved at `contextor/core/live_state/store.py:1926-2333` before edits, canonical revision 116, `workspace_sync=verified`. Contextor showed store inbound module consumers including API facade, live-state export and hydration. Git source confirmed all supplied insertion anchors. No conflict with the supplied patch was found.

## FILES_CHANGED

- `contextor/core/live_state/store.py` — exact schema-1.4 embedded metadata guard and split lineage source-domain guard.
- `tests/test_live_state_store.py` — corrected canonical fixture, converted acceptance reproducers to rejection regressions, added negative matrix and positive/foreign-source boundaries.
- `walkthrough.md` is this report artifact and is excluded from production/test changed-file accounting.

## L33_DOMAIN_INVARIANT

The split loader derives the required domain from persisted `raw_state.modules`, using `Path(str(module.path)).as_posix()` (`contextor/core/live_state/store.py:2049-2059`). Its actual keys come from the loaded split lineage map (`:2061`). Foreign keys are rejected for every family (`:2063-2064`). A `fresh` family must have equality between actual and expected sets (`:2066-2071`). Deferred, stale and resource_limit may retain legitimate subset domains; not_materialized remains governed by the pre-existing lineage normalization (`:337-438`). The guard executes before `split_lineage` is assigned to the core state. It uses neither `manifest.sources` nor validation-cache keys as the expected domain.

The corrected split fixture supplies a `Module` and matching canonical re-export fact for each source key (`tests/test_live_state_store.py:45-109`). Complete zero-fact slices stay materialized and accepted (`:645-673`); an omitted `b.py` manifest entry is rejected (`:457-488`); a two-module/one-slice `deferred` generation remains loadable as deferred (`:600-621`); a foreign materialized key is rejected (`:624-642`).

## L34_METADATA_INVARIANT

In the wrapped payload branch, `embedded` must be a dict (`contextor/core/live_state/store.py:1971-1974`). For outer schema 1.4, its exact key set, value types, and values must match `asdict(metadata)` before constructing `embedded_metadata` (`:1975-1984`). Existing construction and revision/manifest comparisons remain below the new guard (`:1986-2008`). Thus missing, extra, type-changed or value-mismatched embedded generation fields fail closed before any subsequent core-state assignment. Older supported outer schemas do not enter the new strict equality block. The two executed acceptance reproducers now assert loader rejection for mismatched embedded repo_id and missing embedded state_id (`tests/test_live_state_store.py:491-533`).

## SCHEMA_12_COMPATIBILITY

`tests/test_live_state_store.py::test_schema_12_monolithic_snapshot_remains_loadable` and `::test_legacy_dict_snapshot_returns_tuple` both passed within the focused module run. The schema-1.2 fixture omits the newer lineage manifest reference, and the unwrapped legacy path remains loadable. Strict all-field equality is gated solely on outer schema 1.4. No schema version, snapshot format or API signature changed.

## NEGATIVE_TEST_MATRIX

Each of the 18 schema-1.4 parameter cases starts with its own valid committed baseline snapshot, changes exactly one embedded metadata field, calls the real loader with correct outer repo/root expectations, asserts rejection, and checks committed outer metadata is retained (`tests/test_live_state_store.py:535-597`).

| Embedded field | Missing | Value mismatch |
|---|---:|---:|
| schema_version | rejected | rejected |
| state_id | rejected | rejected |
| revision | rejected | rejected |
| writer | rejected | rejected |
| repo_id | rejected | rejected |
| root_path | rejected | rejected |
| state_file | rejected | rejected |
| file_state_file | rejected | rejected |
| lineage_manifest_file | rejected | rejected |

Additional negative regressions: omitted active source in fresh manifest, foreign lineage source key, mismatched embedded repo_id and missing embedded state_id. Positive boundaries: complete schema-1.4 split roundtrip, zero-fact materialized source, deferred partial lineage, legacy monolithic/unwrapped load, exact revision binding, lineage hydration/index construction. Existing split corruption cases remain covered.

## TARGETED_TEST_RESULTS

Exact command:

```powershell
& .\.venv\Scripts\python.exe -m pytest -q tests/test_live_state_store.py tests/test_lineage_state_lifecycle.py
```

Result: `108 passed in 27.02s`, exit code 0. No full repository pytest suite, FULL analysis, restart or manual `update_file`. `git diff --check -- contextor/core/live_state/store.py tests/test_live_state_store.py` was clean. Final source/test diff stat: 2 files, 194 insertions, 60 deletions.

## RUNTIME_RESTART_REQUIREMENT

MANUAL_LIVE_BACKEND_RESTART_REQUIRED=YES. `store.py` is production persistence code; a later runtime integration certification requires a manual LIVE/backend restart or reload and then fresh runtime identity/schema verification. No restart was performed in this task.

## REMAINING_RISKS

TARGETED_TEST_SCOPE_ONLY: The named store and lineage lifecycle modules passed; the global suite and post-restart LIVE behavior were not certified. No IPC or watcher code changed. Existing deferred/stale/resource_limit partial-domain behavior is permitted by the exact requested predicate and was directly exercised for deferred only.

## FINAL_VERDICT

TARGETED_PASS. The exact auditor-designed guards are present; the two previously accepted loader defects now fail closed in focused tests, while the specified legacy and deferred boundaries pass. Await `proceduj`.

## FULL_DIFFS

Complete raw diff for every changed production/test file follows. `walkthrough.md` is the report artifact and is not included.

```diff

diff --git a/contextor/core/live_state/store.py b/contextor/core/live_state/store.py
index 69bc7fe..4db0456 100644
--- a/contextor/core/live_state/store.py
+++ b/contextor/core/live_state/store.py
@@ -1969,6 +1969,20 @@ def load_snapshot(
 
         if isinstance(payload, dict) and set(payload) == {"metadata", "state"}:
             embedded = payload["metadata"]
+            if not isinstance(embedded, dict):
+                return None
+
+            if metadata.schema_version == LIVE_STATE_SCHEMA_VERSION:
+                expected_embedded = asdict(metadata)
+                if set(embedded) != set(expected_embedded):
+                    return None
+                if any(
+                    type(embedded[key]) is not type(expected_value)
+                    or embedded[key] != expected_value
+                    for key, expected_value in expected_embedded.items()
+                ):
+                    return None
+
             embedded_metadata = LiveStateMetadata(
                 schema_version=str(embedded.get("schema_version", "1.0")),
                 state_id=str(embedded.get("state_id", "")),
@@ -2032,6 +2046,30 @@ def load_snapshot(
                     metadata,
                 )
 
+                raw_modules = getattr(raw_state, "modules", None)
+                if not isinstance(raw_modules, dict):
+                    return None
+
+                try:
+                    expected_source_keys = {
+                        Path(str(module.path)).as_posix()
+                        for module in raw_modules.values()
+                    }
+                except (AttributeError, TypeError, ValueError):
+                    return None
+
+                actual_source_keys = set(split_lineage)
+
+                if not actual_source_keys.issubset(expected_source_keys):
+                    return None
+
+                if (
+                    getattr(raw_state, "lineage_facts_state", None)
+                    == LineageFamilyStatus.FRESH.value
+                    and actual_source_keys != expected_source_keys
+                ):
+                    return None
+
                 _trace_snapshot_load_phase(
                     "split_lineage_load",
                     phase_started,
diff --git a/tests/test_live_state_store.py b/tests/test_live_state_store.py
index 19a7f70..72853a5 100644
--- a/tests/test_live_state_store.py
+++ b/tests/test_live_state_store.py
@@ -46,6 +46,7 @@ def _split_lineage_test_state(*source_keys):
     from contextor.core.analysis.state_manager import (
         RepositoryAnalysisState,
     )
+    from contextor.core.domain.module import Module
     from contextor.core.domain.lineage_facts import (
         LINEAGE_FACTS_SEMANTIC_VERSION,
         LineageFamilyStatus,
@@ -79,6 +80,24 @@ def _split_lineage_test_state(*source_keys):
         )
 
     return RepositoryAnalysisState(
+        modules={
+            source_key: Module(
+                module_id=source_key,
+                path=source_key,
+                absolute_path=str(Path(source_key).resolve()),
+                imports=[],
+            )
+            for source_key in source_keys
+        },
+        reexport_facts_by_module={
+            source_key: {
+                "exporter": source_key,
+                "explicit_all": None,
+                "bindings": {},
+                "star_sources": [],
+            }
+            for source_key in source_keys
+        },
         lineage_facts_by_source=sources,
         lineage_facts_state=(
             LineageFamilyStatus.FRESH.value
@@ -435,30 +454,10 @@ def test_current_schema_14_splits_lineage_and_roundtrips(tmp_path):
     )
 
 
-def test_reproducer_split_manifest_omitted_active_source_is_accepted(tmp_path):
+def test_split_manifest_omitted_active_source_is_rejected(tmp_path):
     import json
 
-    from contextor.core.domain.module import Module
-
     state = _split_lineage_test_state("a.py", "b.py")
-    state.modules = {
-        source: Module(
-            module_id=source,
-            path=source,
-            absolute_path=str(tmp_path / source),
-            imports=[],
-        )
-        for source in ("a.py", "b.py")
-    }
-    state.reexport_facts_by_module = {
-        source: {
-            "exporter": source,
-            "explicit_all": None,
-            "bindings": {},
-            "star_sources": [],
-        }
-        for source in state.modules
-    }
     metadata = save_snapshot(
         state,
         tmp_path,
@@ -485,31 +484,12 @@ def test_reproducer_split_manifest_omitted_active_source_is_accepted(tmp_path):
     manifest["sources"].pop("b.py")
     manifest_path.write_text(json.dumps(manifest, sort_keys=True), encoding="utf-8")
 
-    loaded = load_snapshot(tmp_path, "sid")
-    assert loaded is not None
-    loaded_state, loaded_metadata = loaded
-    actual = {
-        "accepted": True,
-        "loaded_sources": sorted(loaded_state.lineage_facts_by_source),
-        "lineage_facts_state": loaded_state.lineage_facts_state,
-        "lineage_query_index_state": loaded_state.lineage_query_index_state,
-        "expected_module_sources": sorted(module.path for module in loaded_state.modules.values()),
-        "metadata_revision": loaded_metadata.revision,
-    }
-    print(f"L33_REPRO={json.dumps(actual, sort_keys=True)}")
-    assert actual == {
-        "accepted": True,
-        "loaded_sources": ["a.py"],
-        "lineage_facts_state": "fresh",
-        "lineage_query_index_state": "fresh",
-        "expected_module_sources": ["a.py", "b.py"],
-        "metadata_revision": 1,
-    }
+    assert load_snapshot(tmp_path, "sid") is None
+    assert read_metadata(tmp_path) == metadata
 
 
 @pytest.mark.parametrize("case", ["embedded_repo_id_mismatch", "embedded_state_id_missing"])
 def test_reproducer_split_embedded_metadata_gap(tmp_path, case):
-    import json
     import pickle
 
     state = _split_lineage_test_state("a.py")
@@ -545,31 +525,147 @@ def test_reproducer_split_embedded_metadata_gap(tmp_path, case):
         payload["metadata"].pop("state_id")
     state_path.write_bytes(pickle.dumps(payload))
 
-    loaded = load_snapshot(
+    assert load_snapshot(
         tmp_path,
         "sid",
         expected_repo_id="repo-original",
         expected_root_path=str(tmp_path),
+    ) is None
+    assert read_metadata(tmp_path) == metadata
+
+
+@pytest.mark.parametrize(
+    "field",
+    [
+        "schema_version",
+        "state_id",
+        "revision",
+        "writer",
+        "repo_id",
+        "root_path",
+        "state_file",
+        "file_state_file",
+        "lineage_manifest_file",
+    ],
+)
+@pytest.mark.parametrize("tamper", ["missing", "mismatched"])
+def test_schema_14_rejects_missing_or_mismatched_embedded_field(tmp_path, field, tamper):
+    import pickle
+
+    state = _split_lineage_test_state("a.py")
+    metadata = save_snapshot(
+        state,
+        tmp_path,
+        "sid",
+        writer="desktop",
+        repo_id="repo-original",
+        root_path=str(tmp_path),
+        exact_revision=1,
+        file_state_payload={
+            "_meta": {"state_id": "sid", "revision": 1},
+            "files": {},
+        },
+    )
+    assert metadata.schema_version == "1.4"
+    expected_load = {
+        "expected_repo_id": "repo-original",
+        "expected_root_path": str(tmp_path),
+    }
+    assert load_snapshot(tmp_path, "sid", **expected_load) is not None
+
+    state_path = tmp_path / metadata.state_file
+    payload = pickle.loads(state_path.read_bytes())
+    assert payload["metadata"][field] == getattr(metadata, field)
+    if tamper == "missing":
+        payload["metadata"].pop(field)
+    else:
+        mismatched = {
+            "schema_version": "1.3",
+            "state_id": "other-sid",
+            "revision": 2,
+            "writer": "other-writer",
+            "repo_id": "other-repo",
+            "root_path": str(tmp_path / "other-root"),
+            "state_file": "other-state.pkl",
+            "file_state_file": "other-file-state.json",
+            "lineage_manifest_file": "other-manifest.json",
+        }
+        payload["metadata"][field] = mismatched[field]
+    state_path.write_bytes(pickle.dumps(payload))
+
+    assert load_snapshot(tmp_path, "sid", **expected_load) is None
+    assert read_metadata(tmp_path) == metadata
+
+
+def test_split_deferred_lineage_allows_missing_active_source(tmp_path):
+    state = _split_lineage_test_state("a.py", "b.py")
+    state.lineage_facts_by_source.pop("b.py")
+    state.lineage_facts_state = "deferred"
+    metadata = save_snapshot(
+        state,
+        tmp_path,
+        "sid",
+        exact_revision=1,
+        file_state_payload={
+            "_meta": {"state_id": "sid", "revision": 1},
+            "files": {},
+        },
     )
+
+    loaded = load_snapshot(tmp_path, "sid")
     assert loaded is not None
     loaded_state, loaded_metadata = loaded
-    actual = {
-        "case": case,
-        "accepted": True,
-        "outer_repo_id": loaded_metadata.repo_id,
-        "outer_state_id": loaded_metadata.state_id,
-        "loaded_state_id": loaded_state.state_id,
-        "revision": loaded_metadata.revision,
-    }
-    print(f"L34_REPRO={json.dumps(actual, sort_keys=True)}")
-    assert actual == {
-        "case": case,
-        "accepted": True,
-        "outer_repo_id": "repo-original",
-        "outer_state_id": "sid",
-        "loaded_state_id": "sid" if case == "embedded_repo_id_mismatch" else "",
-        "revision": 1,
-    }
+    assert loaded_metadata == metadata
+    assert {module.path for module in loaded_state.modules.values()} == {"a.py", "b.py"}
+    assert set(loaded_state.lineage_facts_by_source) == {"a.py"}
+    assert loaded_state.lineage_facts_state == "deferred"
+
+
+def test_split_lineage_rejects_foreign_source_key(tmp_path):
+    state = _split_lineage_test_state("a.py", "b.py")
+    state.modules.pop("b.py")
+    state.reexport_facts_by_module.pop("b.py")
+    metadata = save_snapshot(
+        state,
+        tmp_path,
+        "sid",
+        exact_revision=1,
+        file_state_payload={
+            "_meta": {"state_id": "sid", "revision": 1},
+            "files": {},
+        },
+    )
+    assert metadata.lineage_manifest_file
+    assert set(state.lineage_facts_by_source) == {"a.py", "b.py"}
+    assert {module.path for module in state.modules.values()} == {"a.py"}
+
+    assert load_snapshot(tmp_path, "sid") is None
+
+
+def test_split_lineage_accepts_valid_zero_fact_slice(tmp_path):
+    state = _split_lineage_test_state("a.py")
+    source_slice = state.lineage_facts_by_source["a.py"]
+    assert source_slice.manifest.anchor_count == 0
+    assert source_slice.manifest.flow_count == 0
+    assert source_slice.manifest.surface_count == 0
+    metadata = save_snapshot(
+        state,
+        tmp_path,
+        "sid",
+        exact_revision=1,
+        file_state_payload={
+            "_meta": {"state_id": "sid", "revision": 1},
+            "files": {},
+        },
+    )
+
+    loaded = load_snapshot(tmp_path, "sid")
+    assert loaded is not None
+    loaded_state, loaded_metadata = loaded
+    assert loaded_metadata == metadata
+    assert loaded_state.lineage_facts_by_source == {"a.py": source_slice}
+    assert loaded_state.lineage_facts_state == "fresh"
+    assert loaded_state.lineage_query_index_state == "fresh"
 
 
 def test_current_schema_reexport_facts_roundtrip(tmp_path):
```
