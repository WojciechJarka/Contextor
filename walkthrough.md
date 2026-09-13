# F2L D1L3a Proof Repair Walkthrough

## STATUS

PARTIAL

## FILES_CHANGED

- `contextor/core/analysis/incremental/engine.py`
- `tests/test_lineage_state_lifecycle.py`

`walkthrough.md` is excluded from its own ACTUAL_DIFF.

## CHANGED_SOURCE_ONLY_BUILD_PROOF

The repaired test monkeypatches the D1L1 builder and records exactly `[("consumer.py",)]`.

## UNTOUCHED_DESCRIPTOR_REUSE_PROOF

The provider descriptor exists before the update and remains available to resolve the imported callable return.

## UNTOUCHED_SLICE_IDENTITY_PROOF

The repaired test asserts the provider source slice is the exact same object after the ordinary consumer update.

## IMPORTED_RETURN_STRENGTHENING_PROOF

The repaired test asserts a `CALL_RESULT` source equals `SemanticEndpoint(provider_owner, build_return_slot(provider_owner))`.

## FULL_SET_FAILURE_IDS

- `tests/test_lineage_state_lifecycle.py::test_snapshot_rejects_corrupt_compact_origin[<lambda>4]`

  ```text
  assert load_snapshot(tmp_path, expected_state_id="corrupt-origin") is None
  E AssertionError: assert (RepositoryAnalysisState(...)) is None
  ```

- `tests/test_lineage_state_lifecycle.py::test_identity_sync_owner_introduction_promotes_retained_untouched_consumer_to_full_parity`

  ```text
  assert state.lineage_facts_by_source == expected
  E AssertionError: assert {'consumer.py': MaterializedLineageSourceFacts(...), 'provider.py': MaterializedLineageSourceFacts(...)} == {'consumer.py': MaterializedLineageSourceFacts(...), 'provider.py': MaterializedLineageSourceFacts(...)}
  E Differing items: provider.py; consumer.py
  ```

## TESTS_RUN

```text
RUN_1: tests/test_lineage_state_lifecycle.py::test_ordinary_incremental_rebuilds_only_changed_callable_descriptor
1 passed in 1.36s

RUN_2: tests/test_lineage_state_lifecycle.py tests/analysis/test_lineage_materialization.py tests/test_full_analysis_lineage_materialization.py
64 passed, 2 failed in 8.44s

git diff --check -- contextor/core/analysis/incremental/engine.py tests/test_lineage_state_lifecycle.py
PASS
```

## ACTUAL_DIFF

```diff
diff --git a/tests/test_lineage_state_lifecycle.py b/tests/test_lineage_state_lifecycle.py
index 0591eeb..a983ad4 100644
--- a/tests/test_lineage_state_lifecycle.py
+++ b/tests/test_lineage_state_lifecycle.py
@@ -1435,39 +1435,175 @@ def test_snapshot_legacy_flow_ownership_fails_closed(tmp_path):
     )
 
 
-def test_ordinary_incremental_rebuilds_only_changed_callable_descriptor(tmp_path):
+def test_ordinary_incremental_rebuilds_only_changed_callable_descriptor(
+    tmp_path,
+    monkeypatch,
+):
+    provider_source = (
+        "def target():\n"
+        "    return 1\n"
+    )
+    consumer_before = (
+        "from provider import target\n"
+        "\n"
+        "def local(value):\n"
+        "    return value\n"
+        "\n"
+        "old = target()\n"
+    )
+    consumer_after = (
+        "from provider import target\n"
+        "\n"
+        "def local(value, *, mode=None):\n"
+        "    return value\n"
+        "\n"
+        "new = target()\n"
+    )
+
     facts = {
-        "provider.py": _extracted("provider.py", "def target():\n    return 1\n"),
-        "consumer.py": _extracted("consumer.py", "def local(value):\n    return value\n"),
+        "provider.py": _extracted(
+            "provider.py",
+            provider_source,
+        ),
+        "consumer.py": _extracted(
+            "consumer.py",
+            consumer_before,
+        ),
+    }
+    modules = {
+        "provider": _module("provider"),
+        "consumer": _module("consumer"),
     }
-    modules = {name: _module(name) for name in ("provider", "consumer")}
     artifacts = {
-        "provider": {"own_symbols": {"target"}},
-        "consumer": {"own_symbols": {"local"}},
+        "provider": {
+            "own_symbols": {"target"},
+        },
+        "consumer": {
+            "own_symbols": {"local"},
+        },
     }
-    provider_owner, local_owner = "A:provider/1", "A:consumer.local/1"
+    provider_owner = "A:provider/1"
+    local_owner = "A:consumer.local/1"
     registry = _LifecycleRegistry(
-        {"provider": "M:provider/1", "consumer": "M:consumer/1"},
-        {"provider::target": provider_owner, "consumer::local": local_owner},
+        {
+            "provider": "M:provider/1",
+            "consumer": "M:consumer/1",
+        },
+        {
+            "provider::target": provider_owner,
+            "consumer::local": local_owner,
+        },
+    )
+
+    state = _lineage_state_for_facts(
+        facts,
+        registry,
+        modules,
+        artifacts,
+    )
+    provider_slice = (
+        state.lineage_facts_by_source["provider.py"]
+    )
+    old_consumer_slice = (
+        state.lineage_facts_by_source["consumer.py"]
+    )
+
+    assert any(
+        descriptor.owner_id == provider_owner
+        for descriptor
+        in provider_slice.interface_descriptors
+    )
+
+    engine, _ = _lineage_engine(
+        state,
+        registry,
+        tmp_path,
     )
-    state = _lineage_state_for_facts(facts, registry, modules, artifacts)
-    provider_slice = state.lineage_facts_by_source["provider.py"]
-    engine, _ = _lineage_engine(state, registry, tmp_path)
     candidate = _prepare_candidate_state(state)
-    changed = _extracted("consumer.py", "def local(value, *, mode=None):\n    return value\n")
+
+    from contextor.core.analysis import (
+        lineage_materialization as materialization_module,
+    )
+
+    original_builder = (
+        materialization_module
+        .build_extracted_callable_interface_descriptors
+    )
+    builder_source_sets = []
+
+    def counted_builder(
+        sources,
+        active_artifact_ids,
+    ):
+        builder_source_sets.append(
+            tuple(sorted(sources))
+        )
+        return original_builder(
+            sources,
+            active_artifact_ids,
+        )
+
+    monkeypatch.setattr(
+        materialization_module,
+        "build_extracted_callable_interface_descriptors",
+        counted_builder,
+    )
+
+    changed = _extracted(
+        "consumer.py",
+        consumer_after,
+    )
+
     with registry.read_transaction():
         engine._update_candidate_lineage_slice(
-            candidate, source_path="consumer.py", extracted_lineage_facts=changed,
+            candidate,
+            source_path="consumer.py",
+            extracted_lineage_facts=changed,
             rematerialize_all=False,
         )
-    assert candidate.lineage_facts_by_source["provider.py"] is provider_slice
-    descriptor = next(
-        item for item in candidate.lineage_facts_by_source["consumer.py"].interface_descriptors
-        if item.owner_id == local_owner
+
+    assert builder_source_sets == [
+        ("consumer.py",),
+    ]
+    assert (
+        candidate.lineage_facts_by_source[
+            "provider.py"
+        ]
+        is provider_slice
+    )
+
+    changed_slice = (
+        candidate.lineage_facts_by_source[
+            "consumer.py"
+        ]
+    )
+    assert changed_slice is not old_consumer_slice
+
+    local_descriptor = next(
+        descriptor
+        for descriptor
+        in changed_slice.interface_descriptors
+        if descriptor.owner_id == local_owner
     )
     assert build_parameter_value_slot(
-        local_owner, ParameterKind.KEYWORD_ONLY, name="mode"
-    ) in descriptor.slots
+        local_owner,
+        ParameterKind.KEYWORD_ONLY,
+        name="mode",
+    ) in local_descriptor.slots
     assert build_keyword_binding_slot(
-        local_owner, ParameterKind.KEYWORD_ONLY, name="mode"
-    ) in descriptor.slots
+        local_owner,
+        ParameterKind.KEYWORD_ONLY,
+        name="mode",
+    ) in local_descriptor.slots
+
+    assert any(
+        flow.relation is LineageRelation.CALL_RESULT
+        and flow.source
+        == SemanticEndpoint(
+            provider_owner,
+            build_return_slot(provider_owner),
+        )
+        for flow in changed_slice.flows
+    )
+
+
```

