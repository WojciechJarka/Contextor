# L14_SEMANTIC_FIXPOINT_FAN_IN_REGRESSION

## CURRENT_HEAD

- `git rev-parse HEAD`: `90755ea111313ac55fc9bbdc157f25d3f54711ac`.
- Only the target test and this required report are modified. `plan_executor.py` and other production files are unchanged.
- Contextor MCP discovery preceded source/Git verification. At LIVE revision `1637`, the test module and executor module had fresh syntax diagnostics with no errors. `execute_refresh_plan` implementation was retrieved completely in source ranges `758-1015` and `1016-1273` after its symbol fetch required confirmation due to output size.
- Contextor `artifact_consumption` fact lineage identifies `RepositoryAnalysisState.artifact_consumption` as canonical owner, `_rebuild_consumer_slice` as the incremental consumer-slice producer, and `IncrementalAnalysisEngine._apply_delta_and_commit` as incremental state installer. The lineage response was LIVE, revision `1637`, `resync_required=false`; its workspace sync was `unverified` for that narrow lineage projection.

## EXACT_TEST_SCENARIO

Added `test_semantic_fan_in_recompute_is_once_only_and_order_independent` at `C:\Temp\Contextor_Repo\tests\test_completeness_freshness_parity_proof.py:1023-1234`.

Each of two independent temporary repositories starts with:

```python
# a.py

def existing():
    return 1

# z_bridge.py
import a

def bridge():
    return a.added()

# m_consumer.py
import a
import z_bridge

def run():
    return a.added(), z_bridge.bridge()
```

After all modules are initially loaded, `a.py` gains `added()`. The test first asserts `a::added` is not in the initial canonical consumption map. The real planner naturally returns `("m_consumer", "z_bridge")`; the test asserts it schedules both modules. The forward case uses that natural order. For the reverse case only, the test constructs a `RefreshPlan` preserving every other field and setting `recompute_modules=("z_bridge", "m_consumer")`. The planner implementation is not changed.

## SOURCE_EVIDENCE

`C:\Temp\Contextor_Repo\contextor\core\analysis\refresh_planner.py:270-286` selects consumers for artifact additions and sorts the initial recompute tuple. `C:\Temp\Contextor_Repo\contextor\core\domain\refresh_plan.py:39-72` defines the immutable plan fields copied by the reverse-order case.

In `C:\Temp\Contextor_Repo\contextor\core\analysis\incremental\plan_executor.py`, candidate artifacts/usages and the target indexes are prepared before the queue (`:789-887`); re-export maps and export surfaces are assembled before it (`:894-905`). The exact queue and downstream scheduling implementation is:

```python
        recompute_queue = deque(plan.recompute_modules)
        scheduled_recompute = set(plan.recompute_modules)
        processed_recompute: Set[str] = set()

        while recompute_queue:
            consumer_path = recompute_queue.popleft()

            if consumer_path in processed_recompute:
                continue

            processed_recompute.add(consumer_path)

            consumer_facts = candidate.module_usages.get(
                consumer_path
            )
            if not consumer_facts:
                continue

            previous_slice = _consumer_slice_signature(
                consumer_path,
                candidate.artifact_consumption,
                consumer_target_index,
            )

            candidate.artifact_consumption = _rebuild_consumer_slice(
                consumer=consumer_path,
                consumer_facts=consumer_facts,
                candidate_consumption=candidate.artifact_consumption,
                candidate_artifacts=candidate.artifacts,
                reexports=reexports,
                reexport_facts_by_module=candidate.reexport_facts_by_module,
                module_export_surfaces=module_export_surfaces,
                expected_targets=expected_targets,
                dotted_target_index=dotted_target_index,
                consumer_target_index=consumer_target_index,
            )

            executed_recompute.append(
                consumer_path
            )

            current_slice = _consumer_slice_signature(
                consumer_path,
                candidate.artifact_consumption,
                consumer_target_index,
            )

            if current_slice == previous_slice:
                continue

            downstream_consumers = _find_dependent_consumers(
                consumer_path,
                candidate.module_usages,
            )

            for downstream_consumer in sorted(
                downstream_consumers
            ):
                if downstream_consumer == delta.module_path:
                    continue

                if downstream_consumer in processed_recompute:
                    continue

                if downstream_consumer in scheduled_recompute:
                    continue

                scheduled_recompute.add(
                    downstream_consumer
                )
                recompute_queue.append(
                    downstream_consumer
                )
```

This excerpt is `plan_executor.py:914-986`. The only enqueue routes in this executor are the initial `deque(plan.recompute_modules)` and this changed-slice downstream branch. There is no explicit iteration limit; queue termination is bounded by `processed_recompute` and `scheduled_recompute` deduplication over discovered consumer modules. Existing `test_transitive_propagation_cycle_terminates_without_duplicate_recompute` at `tests/test_completeness_freshness_parity_proof.py:1308-1389` separately expects a full-analysis `ArchitectureCycle` and checks that the executor trace contains no duplicate module names.

`_rebuild_consumer_slice` is at `plan_executor.py:401-678`; it rebuilds one module's consumption from that module's `ModuleUsageFacts` plus candidate artifact/re-export inputs, updates the copy-on-write `artifact_consumption` map, and updates the execution-local consumer-to-target index. `_resolve_canonical_target_keys` at `plan_executor.py:277-356` resolves through `candidate_artifacts`, `expected_targets`, and `dotted_target_index`. Although `candidate_consumption` is an argument, the helper does not read it. This is direct source evidence that one consumer's rebuilt consumption entries do not supply the target identities used to resolve another consumer's slice in this scenario. The test establishes this specific once-only behavior; it does not claim a universal theorem for all future fact families or executor inputs.

## REVISIT_SKIP_EVIDENCE

The regression instruments the planner, `_rebuild_consumer_slice`, `_consumer_slice_signature`, and `_find_dependent_consumers` without changing production logic (`test...:1088-1172`). It records both signature values around each fan-in rebuild and the order of rebuild, post-rebuild signature, and downstream discovery.

For the required forward run, assertions at `tests/test_completeness_freshness_parity_proof.py:1174-1198` establish:

- The initial natural planner tuple and executor trace are `("m_consumer", "z_bridge")`.
- Each fan-in module is rebuilt exactly once; the recorded fan-in rebuild order equals the requested queue order.
- Both `m_consumer` and `z_bridge` have differing before/after slice signatures.
- `z_bridge`'s rebuild precedes its changed post-rebuild signature, which precedes discovery of `("m_consumer",)` downstream from `z_bridge`.
- At that discovery point, source lines `924-925` show `m_consumer` has already been added to `processed_recompute`; source lines `975-976` skip it. The observed trace contains only one `m_consumer` rebuild.

In the reverse run, `m_consumer` is already in `scheduled_recompute` when `z_bridge` discovers it, so source lines `978-985` avoid a duplicate enqueue while its original queue item still executes afterward. The trace proves each ordering executes each fan-in consumer once.

## FULL_VS_INCREMENTAL_PARITY

The independent oracle is the existing `_build_full_static_state` helper at `tests/test_completeness_freshness_parity_proof.py:40-49`: it runs `ContextorFacade.analyze_project` and hydrates the resulting repository engine. The existing `_assert_full_parity` helper at `:52-112` checks canonical target-key equality, consumers, channel consumer keys and channel sets, as well as other plan-controlled state.

The new test additionally compares a whole-map canonical snapshot retaining every target key, sorted consumer value, channel-consumer key, and sorted channel value (`:1036-1049`, `:1200-1212`). It asserts the exact full-oracle entry:

```python
"a::added": {
    "consumers": ["m_consumer", "z_bridge"],
    "channels": {
        "m_consumer": ["direct_calls"],
        "z_bridge": ["direct_calls"],
    },
}
```

Each incremental result matches its independently built full oracle and passes `_assert_full_parity`.

## ORDER_INDEPENDENCE_RESULT

Both full canonical snapshots compare equal (`tests/test_completeness_freshness_parity_proof.py:1215-1226`):

- Natural order: `("m_consumer", "z_bridge")`.
- Explicit executor-level order: `("z_bridge", "m_consumer")`.

Each order also matches its own independently constructed FULL oracle across exact canonical target, consumer, and channel values. No planner or production edit was needed.

## NEGATIVE_CONTROL_RESULT

At `tests/test_completeness_freshness_parity_proof.py:1228-1234`, the test deep-copies the incremental state and replaces `m_consumer`'s `a::added` channel with `invented_channel`. The canonical snapshot then differs, and `_assert_full_parity` raises an assertion containing `channel mismatch`. This confirms the oracle comparison detects a concrete canonical `artifact_consumption` error.

## TARGETED_TEST_RESULTS

Command:

```text
& .\.venv\Scripts\python.exe -m pytest tests/test_completeness_freshness_parity_proof.py::test_semantic_fan_in_recompute_is_once_only_and_order_independent -q
```

Result: `1 passed in 8.69s`.

No other tests and no full repository pytest run were performed.

Closest existing focused coverage:

- `test_transitive_reexport_late_provider_matches_full_oracle` at `tests/test_completeness_freshness_parity_proof.py:954-1020` covers late provider propagation and full parity, but does not observe a processed consumer being rediscovered or run opposite queue orders.
- `test_transitive_propagation_stops_when_direct_consumer_slice_is_unchanged` at `:1237-1307` covers stopping propagation on an unchanged direct slice, not fan-in after a changed slice.
- `test_transitive_propagation_cycle_terminates_without_duplicate_recompute` at `:1308-1389` covers cycle diagnostics and duplicate-free execution, but not this changed-slice fan-in order.
- `test_execute_refresh_plan_builds_full_indexes_once_for_many_consumers` at `tests/test_incremental_plan_executor_complexity.py:170` covers index construction, not downstream rediscovery/revisit ordering.

## FILES_CHANGED

- `C:\Temp\Contextor_Repo\tests\test_completeness_freshness_parity_proof.py` — added the targeted regression only.
- `C:\Temp\Contextor_Repo\walkthrough.md` — this required task report.
- Production files changed: none.

## FULL_DIFFS

The complete Git diff for the changed test file follows. `walkthrough.md` is the required report itself and is not repeated as a self-diff. No production diff exists.
```diff
diff --git a/tests/test_completeness_freshness_parity_proof.py b/tests/test_completeness_freshness_parity_proof.py
index f8e2bac..ebda63e 100644
--- a/tests/test_completeness_freshness_parity_proof.py
+++ b/tests/test_completeness_freshness_parity_proof.py
@@ -1020,6 +1020,220 @@ def test_transitive_reexport_late_provider_matches_full_oracle(tmp_path):
     _assert_full_parity(engine.state, oracle)
 
 
+def test_semantic_fan_in_recompute_is_once_only_and_order_independent(tmp_path):
+    from contextor.core.analysis.incremental import plan_executor
+    from contextor.core.analysis.incremental.plan_executor import (
+        _consumer_slice_signature as original_slice_signature,
+        _rebuild_consumer_slice as original_rebuild_consumer_slice,
+    )
+    from contextor.core.analysis.refresh_planner import (
+        _find_dependent_consumers as original_find_dependent_consumers,
+    )
+
+    fan_in_modules = {"m_consumer", "z_bridge"}
+
+    def artifact_consumption_snapshot(state):
+        return {
+            target: {
+                "consumers": tuple(sorted(entry.get("consumers", ()))),
+                "channels": {
+                    consumer: tuple(sorted(channels))
+                    for consumer, channels in sorted(
+                        entry.get("channels", {}).items()
+                    )
+                },
+            }
+            for target, entry in sorted(state.artifact_consumption.items())
+        }
+
+    def run_ordered_case(case_name, requested_order):
+        repo_dir = tmp_path / case_name
+        repo_dir.mkdir()
+
+        provider = repo_dir / "a.py"
+        bridge = repo_dir / "z_bridge.py"
+        consumer = repo_dir / "m_consumer.py"
+        provider.write_text(
+            "def existing():\n"
+            "    return 1\n",
+            encoding="utf-8",
+        )
+        bridge.write_text(
+            "import a\n"
+            "\n"
+            "def bridge():\n"
+            "    return a.added()\n",
+            encoding="utf-8",
+        )
+        consumer.write_text(
+            "import a\n"
+            "import z_bridge\n"
+            "\n"
+            "def run():\n"
+            "    return a.added(), z_bridge.bridge()\n",
+            encoding="utf-8",
+        )
+
+        cache_dir = repo_dir / "cache"
+        cache_dir.mkdir()
+        engine = IncrementalAnalysisEngine(
+            RepositoryAnalysisState(modules={}),
+            PersistentIdentityRegistry(str(repo_dir)),
+            FileStateManager(str(cache_dir)),
+            str(repo_dir),
+        )
+        for source_path in (provider, bridge, consumer):
+            engine.update_file(str(source_path))
+
+        assert "a::added" not in engine.state.artifact_consumption
+        provider.write_text(
+            "def existing():\n"
+            "    return 1\n"
+            "\n"
+            "def added():\n"
+            "    return 2\n",
+            encoding="utf-8",
+        )
+
+        natural_orders = []
+        scheduled_orders = []
+        rebuild_order = []
+        signature_values = {}
+        discoveries = []
+        event_trace = []
+        original_plan_refresh = RefreshPlanner.plan_refresh
+
+        def ordered_plan_refresh(*args, **kwargs):
+            natural_plan = original_plan_refresh(*args, **kwargs)
+            delta = args[0] if args else kwargs.get("delta")
+            if delta is not None and delta.module_path == "a":
+                natural_orders.append(natural_plan.recompute_modules)
+                assert set(natural_plan.recompute_modules) == fan_in_modules
+                if natural_plan.recompute_modules == requested_order:
+                    scheduled_plan = natural_plan
+                else:
+                    scheduled_plan = RefreshPlan(
+                        reparse_modules=natural_plan.reparse_modules,
+                        recompute_modules=requested_order,
+                        patch_families=natural_plan.patch_families,
+                        graph_recomputations=natural_plan.graph_recomputations,
+                        refresh_completeness=natural_plan.refresh_completeness,
+                        semantic_certainty=natural_plan.semantic_certainty,
+                        reason=natural_plan.reason,
+                    )
+                scheduled_orders.append(scheduled_plan.recompute_modules)
+                return scheduled_plan
+            return natural_plan
+
+        def traced_rebuild(*args, **kwargs):
+            consumer_path = kwargs.get("consumer", args[0] if args else None)
+            rebuild_order.append(consumer_path)
+            event_trace.append(("rebuild", consumer_path))
+            return original_rebuild_consumer_slice(*args, **kwargs)
+
+        def traced_signature(consumer_path, *args, **kwargs):
+            signature = original_slice_signature(
+                consumer_path,
+                *args,
+                **kwargs,
+            )
+            signature_values.setdefault(consumer_path, []).append(signature)
+            event_trace.append(("signature", consumer_path, signature))
+            return signature
+
+        def traced_discovery(module_path, usages):
+            downstream = original_find_dependent_consumers(module_path, usages)
+            ordered_downstream = tuple(sorted(downstream))
+            discoveries.append((module_path, ordered_downstream))
+            event_trace.append(("discover", module_path, ordered_downstream))
+            return downstream
+
+        with (
+            patch.object(
+                RefreshPlanner,
+                "plan_refresh",
+                side_effect=ordered_plan_refresh,
+            ),
+            patch(
+                "contextor.core.analysis.refresh_planner._find_dependent_consumers",
+                side_effect=traced_discovery,
+            ),
+            patch.object(
+                plan_executor,
+                "_rebuild_consumer_slice",
+                side_effect=traced_rebuild,
+            ),
+            patch.object(
+                plan_executor,
+                "_consumer_slice_signature",
+                side_effect=traced_signature,
+            ),
+        ):
+            result = engine.update_file(str(provider))
+
+        assert natural_orders == [("m_consumer", "z_bridge")]
+        assert scheduled_orders == [requested_order]
+        assert result.execution_trace["recompute_modules"] == requested_order
+
+        fan_in_rebuild_order = tuple(
+            module for module in rebuild_order if module in fan_in_modules
+        )
+        assert fan_in_rebuild_order == requested_order
+        assert fan_in_rebuild_order.count("m_consumer") == 1
+        assert fan_in_rebuild_order.count("z_bridge") == 1
+
+        assert signature_values["m_consumer"][0] != signature_values["m_consumer"][1]
+        assert signature_values["z_bridge"][0] != signature_values["z_bridge"][1]
+        z_bridge_rebuild = event_trace.index(("rebuild", "z_bridge"))
+        z_bridge_signatures = [
+            index
+            for index, event in enumerate(event_trace)
+            if event[:2] == ("signature", "z_bridge")
+        ]
+        z_bridge_discovery = event_trace.index(
+            ("discover", "z_bridge", ("m_consumer",))
+        )
+        assert len(z_bridge_signatures) == 2
+        assert z_bridge_rebuild < z_bridge_signatures[1] < z_bridge_discovery
+        assert ("z_bridge", ("m_consumer",)) in discoveries
+
+        oracle = _build_full_static_state(repo_dir)
+        _assert_full_parity(engine.state, oracle)
+        incremental_snapshot = artifact_consumption_snapshot(engine.state)
+        oracle_snapshot = artifact_consumption_snapshot(oracle)
+        assert incremental_snapshot == oracle_snapshot
+        assert oracle.artifact_consumption["a::added"] == {
+            "consumers": ["m_consumer", "z_bridge"],
+            "channels": {
+                "m_consumer": ["direct_calls"],
+                "z_bridge": ["direct_calls"],
+            },
+        }
+
+        return engine.state, oracle, incremental_snapshot
+
+    forward_state, forward_oracle, forward_snapshot = run_ordered_case(
+        "m_before_z",
+        ("m_consumer", "z_bridge"),
+    )
+    reverse_state, reverse_oracle, reverse_snapshot = run_ordered_case(
+        "z_before_m",
+        ("z_bridge", "m_consumer"),
+    )
+
+    assert forward_snapshot == artifact_consumption_snapshot(forward_oracle)
+    assert reverse_snapshot == artifact_consumption_snapshot(reverse_oracle)
+    assert forward_snapshot == reverse_snapshot
+
+    negative_state = deepcopy(forward_state)
+    negative_state.artifact_consumption["a::added"]["channels"][
+        "m_consumer"
+    ] = ["invented_channel"]
+    assert artifact_consumption_snapshot(negative_state) != forward_snapshot
+    with pytest.raises(AssertionError, match="channel mismatch"):
+        _assert_full_parity(negative_state, forward_oracle)
+
+
 def test_transitive_propagation_stops_when_direct_consumer_slice_is_unchanged(
     tmp_path,
 ):
```

## ACTUAL_DIFF

- Test file: full actual diff is included above.
- Production/tests other than the target test: NONE.
- Walkthrough: report file only; its self-diff is omitted.
