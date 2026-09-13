# F2L D1L3a Final Test Repair Walkthrough

## STATUS

PARTIAL

## SNAPSHOT_TEST_REPAIR_PROOF

The corrupt-origin parameter now swaps the selected origin role between `FLOW_SOURCE` and `FLOW_TARGET`; RUN_1 passed all five parameter cases.

## FULL_SET_FAILURE_IDS

- `tests/test_lineage_state_lifecycle.py::test_identity_sync_owner_introduction_promotes_retained_untouched_consumer_to_full_parity`

  ```text
  assert state.lineage_facts_by_source == expected
  E AssertionError: differing items: provider.py; consumer.py
  ```

This is the only RUN_2 failure.

## TESTS_RUN

```text
RUN_1: 5 passed in 1.44s
RUN_2: 66 passed, 1 failed in 6.56s
git diff --check: PASS
```

## ACTUAL_DIFF

```diff
diff --git a/tests/test_lineage_state_lifecycle.py b/tests/test_lineage_state_lifecycle.py
index a983ad4..8259633 100644
--- a/tests/test_lineage_state_lifecycle.py
+++ b/tests/test_lineage_state_lifecycle.py
@@ -747,7 +747,17 @@ def test_snapshot_round_trip_compact_origin_reresolves_without_source_work(tmp_p
         lambda origin: (replace(origin, source_key="other.py"),),
         lambda origin: (replace(origin, source_fingerprint="other"),),
         lambda origin: (replace(origin, fact_local_id="missing"),),
-        lambda origin: (replace(origin, endpoint_role=SemanticEndpointRole.FLOW_SOURCE),),
+        lambda origin: (
+            replace(
+                origin,
+                endpoint_role=(
+                    SemanticEndpointRole.FLOW_TARGET
+                    if origin.endpoint_role
+                    is SemanticEndpointRole.FLOW_SOURCE
+                    else SemanticEndpointRole.FLOW_SOURCE
+                ),
+            ),
+        ),
     ],
 )
 def test_snapshot_rejects_corrupt_compact_origin(tmp_path, origins):
@@ -1606,4 +1616,3 @@ def test_ordinary_incremental_rebuilds_only_changed_callable_descriptor(
         for flow in changed_slice.flows
     )
 
-
```

