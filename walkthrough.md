# F2L D1L4b Final Test Walkthrough

## STATUS

PASS

## SNAPSHOT_LEGACY_FALSE_PROOF

The legacy snapshot test deletes the persisted capability attribute; load normalization restores it as false.

## PAYLOAD_PRESERVATION_PROOF

The test asserts the descriptor tuple matches the payload captured before snapshot save.

## FAMILY_FRESH_PROOF

The loaded lineage family remains `fresh`.

## TESTS_RUN

```text
RUN_1: 1 passed in 1.40s
RUN_2: 75 passed in 7.43s
git diff --check -- tests/test_lineage_state_lifecycle.py: PASS
```

## ACTUAL_DIFF

```diff
diff --git a/tests/test_lineage_state_lifecycle.py b/tests/test_lineage_state_lifecycle.py
index 8259633..b441b08 100644
--- a/tests/test_lineage_state_lifecycle.py
+++ b/tests/test_lineage_state_lifecycle.py
@@ -1445,6 +1445,27 @@ def test_snapshot_legacy_flow_ownership_fails_closed(tmp_path):
     )
 
 
+def test_snapshot_legacy_interface_descriptor_capability_fails_closed_without_dropping_payload(tmp_path):
+    facts = {"pkg.py": _extracted("pkg.py", "def ping():\n    pass\n")}
+    modules = {"pkg": _module("pkg")}
+    artifacts = {"pkg": {"own_symbols": {"ping"}}}
+    registry = _LifecycleRegistry(
+        {"pkg": "M:pkg/1"}, {"pkg::ping": "A:pkg.ping/1"}
+    )
+    state = _lineage_state_for_facts(facts, registry, modules, artifacts)
+    source_slice = state.lineage_facts_by_source["pkg.py"]
+    assert source_slice.manifest.interface_descriptors_materialized is True
+    assert source_slice.interface_descriptors
+    expected_descriptors = source_slice.interface_descriptors
+    object.__delattr__(source_slice.manifest, "interface_descriptors_materialized")
+    save_snapshot(state, tmp_path, "legacy-interface-descriptors")
+    loaded, _ = load_snapshot(tmp_path, expected_state_id="legacy-interface-descriptors")
+    loaded_slice = loaded.lineage_facts_by_source["pkg.py"]
+    assert loaded.lineage_facts_state == "fresh"
+    assert loaded_slice.manifest.interface_descriptors_materialized is False
+    assert loaded_slice.interface_descriptors == expected_descriptors
+
+
 def test_ordinary_incremental_rebuilds_only_changed_callable_descriptor(
     tmp_path,
     monkeypatch,
@@ -1615,4 +1636,3 @@ def test_ordinary_incremental_rebuilds_only_changed_callable_descriptor(
         )
         for flow in changed_slice.flows
     )
-
```

