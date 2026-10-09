# L33/L34 negative reproducer

## CURRENT_HEAD

24c5b014ce1373fb4be8cd896c42eafebdd4391b (`git rev-parse HEAD`). Initial `git status --short` was clean. Contextor MCP deferred-tool inventory, documentation, implementation previews, source range, and `get_symbol_lineage` preview were used first. Canonical `load_snapshot` and `save_snapshot` resolved in `contextor/core/live_state/store.py` at canonical revision 114, source `workspace_sync=verified`. Git-confirmed source and test anchors were inspected before editing. No production file changed.

## L33_EXECUTED_REPRODUCTION

DIRECT_EVIDENCE: `tests/test_live_state_store.py::test_reproducer_split_manifest_omitted_active_source_is_accepted` constructs two `Module` objects with paths `a.py` and `b.py`, valid canonical re-export entries, and current-version, `fresh` lineage slices for both. Both slices have zero anchors, flows and surfaces but remain explicitly materialized and listed in the baseline manifest. It saves a schema-1.4 exact revision 1 snapshot with valid file-state identity and verifies the untampered real loader returns both source keys. The only post-save tamper removes the `b.py` entry from the committed manifest's `sources` mapping. Outer metadata, core pickle, manifest identity/revision, remaining entry/chunk and the physically present `b.py` chunk are unchanged.

Real `load_snapshot(tmp_path, "sid")` returned:
```json
{"accepted": true, "expected_module_sources": ["a.py", "b.py"], "lineage_facts_state": "fresh", "lineage_query_index_state": "fresh", "loaded_sources": ["a.py"], "metadata_revision": 1}
```
Thus omission of `b.py` is accepted while both freshness fields remain `fresh`. A valid empty source is represented by the baseline `b.py` manifest entry and chunk with zero facts; the failing case is removal of the entire source entry, not an empty slice. Test anchors: `tests/test_live_state_store.py:438-507`. Code-path anchors: `contextor/core/live_state/store.py:1040-1116,1175-1393,2042-2067,337-466`.

## L34_EXECUTED_REPRODUCTION

Each parameter case starts from its own valid schema-1.4 committed snapshot with outer `repo_id=repo-original`, `state_id=sid`, `root_path=tmp_path`, and exact revision 1. Its untampered real load is asserted successful. Only the core pickle's embedded metadata mapping is then changed; outer metadata, state object, manifest, chunks and file-state generation are untouched. Calls use the correct `expected_repo_id=repo-original` and `expected_root_path=tmp_path`.

Case A changes only embedded `repo_id` to `repo-different`. Real loader returned:
```json
{"accepted": true, "case": "embedded_repo_id_mismatch", "loaded_state_id": "sid", "outer_repo_id": "repo-original", "outer_state_id": "sid", "revision": 1}
```
The test explicitly confirms the saved embedded repo_id before tamper and the differing value after tamper; the returned metadata remains the outer value.

Case B removes only embedded `state_id`. Real loader returned:
```json
{"accepted": true, "case": "embedded_state_id_missing", "loaded_state_id": "", "outer_repo_id": "repo-original", "outer_state_id": "sid", "revision": 1}
```
The preassignment core state id matches outer `sid`; after validation the loader assigns the embedded default empty string. Committed LIVE publication has a later state/metadata id parity check, so this specific result is a loader acceptance and return-time inconsistency, not evidence that committed publication accepts Case B (`contextor/core/live_state/ipc.py:1380-1391`). Test anchors: `tests/test_live_state_store.py:510-575`. Loader anchors: `contextor/core/live_state/store.py:1949-1959,1970-1994,2104-2123,2224-2229`.

## SCHEMA_14_REQUIRED_FIELDS

CONTRACT_PROVED from current loader: outer metadata `schema_version` must be a supported value, and a nonempty split `lineage_manifest_file` requires outer schema 1.4 (`contextor/core/live_state/store.py:1416-1440,2004-2009`). The split manifest itself must have current manifest schema, outer-matching state_id/revision, and a `sources` mapping (`:1040-1116`). Each *listed* source has required entry/chunk fields and identity checks (`:1222-1355`). Split raw state must be a non-dict object with `__dict__` (`:2011-2022`).

For the embedded metadata mapping of a normal positive-revision schema-1.4 split generation, the loader effectively requires `revision` equal to outer revision and `lineage_manifest_file` equal to the nonempty outer reference (`:1970-1994`). Missing embedded revision defaults to 0, which mismatches normal revision 1; missing manifest reference defaults to empty, which mismatches the split reference. Embedded `state_id`, `repo_id`, `root_path`, `schema_version`, `writer`, `state_file`, and `file_state_file` are parsed with defaults but have no embedded-versus-outer equality check. Case B executes the missing embedded state_id acceptance, and Case A executes mismatched embedded repo_id acceptance. This describes current acceptance behavior, not a proposed policy. The pickle wrapper must be a mapping with exactly `metadata` and `state` keys to enter the embedded path; a split manifest with an unwrapped payload is rejected (`:1970,2230-2231`).

## LEGACY_COMPATIBILITY_BOUNDARY

DIRECT_EVIDENCE: `read_metadata` accepts outer schema 1.0–1.4 and defaults absent outer generation/identity fields (`contextor/core/live_state/store.py:1416-1440`). The supported schema-1.2 monolithic test constructs outer and embedded metadata **without** `lineage_manifest_file` and successfully loads (`tests/test_live_state_store.py:2051-2125`; focused test passed). The legacy unwrapped dict snapshot test also passed (`tests/test_live_state_store.py:319-327`): with no split manifest, the loader follows the unwrapped path (`store.py:2230-2239`). Legacy monolithic snapshots therefore can lack the newer manifest reference; enforcing an embedded split reference against those supported snapshots would conflict with observed compatibility. In the wrapped legacy path, embedded revision is still compared to outer revision; absent newer embedded fields receive defaults. Caller-supplied repository/root expectations are checked against outer metadata if supplied (`:1949-1957`). This audit did not execute a permutation matrix of every missing legacy field, so acceptance beyond these code paths is CODE_PATH_PROVED rather than independently reproduced.

## EXACT_COMMANDS_AND_RESULTS

1. `git rev-parse HEAD` → `24c5b014ce1373fb4be8cd896c42eafebdd4391b`.
2. `git status --short` before change → empty.
3. `& .\.venv\Scripts\python.exe -m pytest -q -s tests/test_live_state_store.py::test_reproducer_split_manifest_omitted_active_source_is_accepted tests/test_live_state_store.py::test_reproducer_split_embedded_metadata_gap tests/test_live_state_store.py::test_current_schema_14_splits_lineage_and_roundtrips tests/test_live_state_store.py::test_split_lineage_corruption_fails_closed tests/test_live_state_store.py::test_schema_12_monolithic_snapshot_remains_loadable` → three JSON reproducer lines above; `8 passed in 2.46s`, exit 0.
4. `& .\.venv\Scripts\python.exe -m pytest -q tests/test_live_state_store.py::test_legacy_dict_snapshot_returns_tuple tests/test_live_state_store.py::test_exact_snapshot_revision_binds_embedded_state_and_metadata tests/test_live_state_store.py::test_snapshot_rejects_wrong_repository_identity_or_root` → `3 passed in 0.97s`, exit 0.
5. `& .\.venv\Scripts\python.exe -m pytest -q -s tests/test_live_state_store.py::test_reproducer_split_embedded_metadata_gap` after adding explicit embedded baseline assertions → `2 passed in 9.64s`, exit 0.
6. `git diff --check -- tests/test_live_state_store.py` → empty, exit 0. No full pytest, FULL analysis, restart, or `update_file`.

## FILES_CHANGED

- `tests/test_live_state_store.py` — three controlled acceptance reproducers; current observed behavior is asserted, no future rejection expectation.
Report artifact: `walkthrough.md` (excluded from changed source/test files).

## FULL_DIFFS

Complete raw `git diff -- tests/test_live_state_store.py` follows. No production diff.

```diff

diff --git a/tests/test_live_state_store.py b/tests/test_live_state_store.py
index 681d7a5..19a7f70 100644
--- a/tests/test_live_state_store.py
+++ b/tests/test_live_state_store.py
@@ -435,6 +435,143 @@ def test_current_schema_14_splits_lineage_and_roundtrips(tmp_path):
     )
 
 
+def test_reproducer_split_manifest_omitted_active_source_is_accepted(tmp_path):
+    import json
+
+    from contextor.core.domain.module import Module
+
+    state = _split_lineage_test_state("a.py", "b.py")
+    state.modules = {
+        source: Module(
+            module_id=source,
+            path=source,
+            absolute_path=str(tmp_path / source),
+            imports=[],
+        )
+        for source in ("a.py", "b.py")
+    }
+    state.reexport_facts_by_module = {
+        source: {
+            "exporter": source,
+            "explicit_all": None,
+            "bindings": {},
+            "star_sources": [],
+        }
+        for source in state.modules
+    }
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
+    assert metadata.schema_version == "1.4"
+    assert set(state.lineage_facts_by_source) == {"a.py", "b.py"}
+    assert all(
+        not (slice_.anchors or slice_.flows or slice_.surfaces)
+        for slice_ in state.lineage_facts_by_source.values()
+    )
+    baseline = load_snapshot(tmp_path, "sid")
+    assert baseline is not None
+    assert set(baseline[0].lineage_facts_by_source) == {"a.py", "b.py"}
+
+    manifest_path = tmp_path / metadata.lineage_manifest_file
+    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
+    assert set(manifest["sources"]) == {"a.py", "b.py"}
+    manifest["sources"].pop("b.py")
+    manifest_path.write_text(json.dumps(manifest, sort_keys=True), encoding="utf-8")
+
+    loaded = load_snapshot(tmp_path, "sid")
+    assert loaded is not None
+    loaded_state, loaded_metadata = loaded
+    actual = {
+        "accepted": True,
+        "loaded_sources": sorted(loaded_state.lineage_facts_by_source),
+        "lineage_facts_state": loaded_state.lineage_facts_state,
+        "lineage_query_index_state": loaded_state.lineage_query_index_state,
+        "expected_module_sources": sorted(module.path for module in loaded_state.modules.values()),
+        "metadata_revision": loaded_metadata.revision,
+    }
+    print(f"L33_REPRO={json.dumps(actual, sort_keys=True)}")
+    assert actual == {
+        "accepted": True,
+        "loaded_sources": ["a.py"],
+        "lineage_facts_state": "fresh",
+        "lineage_query_index_state": "fresh",
+        "expected_module_sources": ["a.py", "b.py"],
+        "metadata_revision": 1,
+    }
+
+
+@pytest.mark.parametrize("case", ["embedded_repo_id_mismatch", "embedded_state_id_missing"])
+def test_reproducer_split_embedded_metadata_gap(tmp_path, case):
+    import json
+    import pickle
+
+    state = _split_lineage_test_state("a.py")
+    metadata = save_snapshot(
+        state,
+        tmp_path,
+        "sid",
+        repo_id="repo-original",
+        root_path=str(tmp_path),
+        exact_revision=1,
+        file_state_payload={
+            "_meta": {"state_id": "sid", "revision": 1},
+            "files": {},
+        },
+    )
+    assert metadata.schema_version == "1.4"
+    baseline = load_snapshot(
+        tmp_path,
+        "sid",
+        expected_repo_id="repo-original",
+        expected_root_path=str(tmp_path),
+    )
+    assert baseline is not None
+    assert baseline[0].state_id == baseline[1].state_id == "sid"
+
+    state_path = tmp_path / metadata.state_file
+    payload = pickle.loads(state_path.read_bytes())
+    assert payload["metadata"]["repo_id"] == "repo-original"
+    assert payload["metadata"]["state_id"] == "sid"
+    if case == "embedded_repo_id_mismatch":
+        payload["metadata"]["repo_id"] = "repo-different"
+    else:
+        payload["metadata"].pop("state_id")
+    state_path.write_bytes(pickle.dumps(payload))
+
+    loaded = load_snapshot(
+        tmp_path,
+        "sid",
+        expected_repo_id="repo-original",
+        expected_root_path=str(tmp_path),
+    )
+    assert loaded is not None
+    loaded_state, loaded_metadata = loaded
+    actual = {
+        "case": case,
+        "accepted": True,
+        "outer_repo_id": loaded_metadata.repo_id,
+        "outer_state_id": loaded_metadata.state_id,
+        "loaded_state_id": loaded_state.state_id,
+        "revision": loaded_metadata.revision,
+    }
+    print(f"L34_REPRO={json.dumps(actual, sort_keys=True)}")
+    assert actual == {
+        "case": case,
+        "accepted": True,
+        "outer_repo_id": "repo-original",
+        "outer_state_id": "sid",
+        "loaded_state_id": "sid" if case == "embedded_repo_id_mismatch" else "",
+        "revision": 1,
+    }
+
+
 def test_current_schema_reexport_facts_roundtrip(tmp_path):
     facts = {
         "pkg.mod": {

```

## DESIGN_INPUT_CONTRACT

Evidence constraints for any later user-directed design stage:

- Schema-1.4 split generations have an active-module source domain derived from `Module.path`; a present zero-fact slice and a missing manifest entry are observably different.
- The loader currently checks only listed source chunks and leaves both lineage family and rebuilt query index `fresh` after an omitted required source.
- Current outer caller identity checks do not bind embedded repo_id; missing embedded state_id is accepted and assigned as empty to the returned core state.
- Current schema-1.2 monolithic and unwrapped legacy snapshots are supported; `lineage_manifest_file` is absent in the executed monolithic legacy fixture. The later committed-publish state_id parity check must be distinguished from loader acceptance.
- No implementation design, rejection policy, or future test expectation was introduced in this task.

## FINAL_VERDICT

L33=EXECUTED_PROVED_GAP: the real loader accepted an incomplete active-module lineage domain and reported both lineage freshness fields as `fresh`.

L34=EXECUTED_PROVED_GAP: the real loader accepted an embedded repo_id mismatch against correct outer repository expectations, and accepted missing embedded state_id while returning state id empty beside outer id sid.

Validation: 8 focused initial tests passed, 3 adjacent tests passed, and after strengthening the embedded fixture baseline assertions the 2 L34 parameter cases passed again. Production changes: none. Await `proceduj`.
