CPA10L1_INCREMENTAL_CONSUMER_SLICE_COMPLEXITY_FIX

STATUS
STATUS=BLOCKED
BLOCK_REASON=LIVE synchronization gate not satisfied; targeted validation was not run.

BASELINE
HISTORICAL_INCREMENTAL_EXECUTE_PLAN_MS=304390
HISTORICAL_RECOMPUTE_COUNT=398
BASELINE_SOURCE=User-provided task contract.
LIVE_BASELINE_REVISION=1353
LIVE_FIRST_EDIT_REVISION=1354
LIVE_FIRST_EDIT_EVENT=SYNTAX_ERROR for contextor/core/analysis/incremental/plan_executor.py at line 597, column 8.
LOCAL_SOURCE_AFTER_CORRECTION=The prepopulation cleanup loop indentation is restored in the working file.
CANONICAL_LIVE_AFTER_CORRECTION=Still reports the earlier parse failure at line 597; no later canonical revision arrived in four bounded polls.
ACTIVE_MUTATION_OR_REPOSITORY_LEASE=UNKNOWN
ANALYSIS_STATUS=Most recent returned job 0259d1bbc4b34fd795d9370df0628ab7 is completed and published revision 1352; this does not establish current writer/lease inactivity.

FILES_CHANGED
- C:\Temp\Contextor_Repo\contextor\core\analysis\incremental\plan_executor.py
- C:\Temp\Contextor_Repo\tests\test_incremental_plan_executor_complexity.py
WALKTHROUGH_REPORT_ONLY=YES

IMPLEMENTATION_RESULT
TRANSIENT_CONSUMER_TARGET_INDEX_IMPLEMENTED=YES
TARGET_DOMAIN_PRECOMPUTED_ONCE=YES (one full candidate target-domain precompute is present; the exact supplied test's global call counter also counts the existing changed-module prepopulation call, see COMPLEXITY_CONTRACT)
CANONICAL_STATE_SCHEMA_CHANGED=NO
PERSISTENCE_CHANGED=NO
PLANNER_SEMANTICS_CHANGED=NO
AMBIGUITY_SEMANTICS_CHANGED=NO
COW_ENTRY_COPY_PRESERVED=YES
FIX_DESIGNED_BY_AGENT=NO
The requested helper, resolver/rebuild replacements, execution-local index, both call-site arguments, and ambiguity-path index cleanup are present in the source diff. No source/test files beyond the two authorized paths were changed.

COMPLEXITY_CONTRACT
INDEXED_REBUILD_FULL_MAP_SCAN=NO
INDEXED_REBUILD_TOP_LEVEL_COPY=NO
INDEXED_REBUILD_TARGET_DOMAIN_REBUILD=NO
The indexed branch uses only the consumer's reverse-index targets and passes the precomputed expected_targets into target resolution.
STATIC_TEST_CONTRACT_CONFLICT=YES
The exact test asserts target_domain_calls == 1. In its execute_refresh_plan fixture, delta.module_path is "changed" and candidate.artifacts has no "changed" entry. The existing candidate prepopulation block therefore obtains the default empty dict and calls canonical_artifact_consumption_targets once; the newly required full-domain precompute calls it again. The exact test's wrapper counts both calls, so the source path appears to produce 2 calls. This was not run because the LIVE gate failed. No adaptation was made.

COW_CONTRACT
COW_ENTRY_COPY_PRESERVED=YES
With consumer_target_index supplied, _rebuild_consumer_slice reuses the already-isolated candidate top-level mapping. Entries being mutated are copied through _get_copy_of_entry. The fallback without an index retains a top-level copy and full-map key fallback.

TARGETED_TEST_RESULTS
PERFORMANCE_REGRESSION_TEST_ADDED=YES
TARGETED_TESTS=NOT_RUN
PY_COMPILE=NOT_RUN
VALIDATION_GATE=workspace_sync=verified was not established for both files.
FULL_SUITE_RUN=NO

CONTEXTOR_VERIFICATION
WORKSPACE_SYNC=unverified
PRODUCTION_FILE_CONTEXT=stale; Contextor returned last-known-good state and the prior parse failure at line 597, column 8.
TEST_FILE_CONTEXT=unavailable; tests.test_incremental_plan_executor_complexity is not present in canonical LIVE state.
NAME_COLLISIONS=0 (fresh direct get_name_collisions projection)
SYNTAX_ERRORS=1 (fresh canonical summary still reflects the earlier line 597 parse failure)
CYCLES=0 (fresh canonical diagnostics summary)
POST_TEST_VERIFICATION=NOT_RUN
The local production file contains the corrected indentation, but Contextor did not publish a newer revision. No pytest or py_compile was run. The bounded LIVE polling allowance was exhausted; no update_file or full-analysis recovery was started. The available completed analysis status did not prove that a mutation worker or repository lease was inactive, so recovery was not safe to start.

FULL_DIFFS

FULL_DIFF: C:\Temp\Contextor_Repo\contextor\core\analysis\incremental\plan_executor.py

FULL_DIFF: C:\Temp\Contextor_Repo\tests\test_incremental_plan_executor_complexity.py

CODE_CHANGED=YES
TEST_CODE_CHANGED=YES
FIX_DESIGNED_BY_AGENT=NO
GIT_COMMIT_PERFORMED=NO
GIT_PUSH_PERFORMED=NO
GIT_MUTATION_PERFORMED=NO

diff --git a/contextor/core/analysis/incremental/plan_executor.py b/contextor/core/analysis/incremental/plan_executor.py
index a45710b..c04a55a 100644
--- a/contextor/core/analysis/incremental/plan_executor.py
+++ b/contextor/core/analysis/incremental/plan_executor.py
@@ -98,10 +98,63 @@ def _get_copy_of_entry(raw_entry: dict) -> dict:
     return {"consumers": consumers, "channels": channels}
 
 
+def _build_consumer_target_index(
+    consumption: Mapping[str, Any],
+) -> Dict[str, Set[str]]:
+    """
+    Builds one transient reverse lookup for the current plan execution.
+
+    This is execution-local acceleration only. It is not canonical state
+    and is never persisted.
+    """
+    index: Dict[str, Set[str]] = {}
+
+    for target, raw_entry in consumption.items():
+        if not isinstance(raw_entry, dict):
+            continue
+
+        consumers = raw_entry.get("consumers", ())
+        if isinstance(
+            consumers,
+            (
+                list,
+                tuple,
+                set,
+            ),
+        ):
+            for consumer in consumers:
+                if (
+                    isinstance(consumer, str)
+                    and consumer
+                ):
+                    index.setdefault(
+                        consumer,
+                        set(),
+                    ).add(target)
+
+        channels = raw_entry.get(
+            "channels",
+            {},
+        )
+        if isinstance(channels, dict):
+            for consumer in channels:
+                if (
+                    isinstance(consumer, str)
+                    and consumer
+                ):
+                    index.setdefault(
+                        consumer,
+                        set(),
+                    ).add(target)
+
+    return index
+
+
 def _resolve_canonical_target_key(
     target: Optional[str],
     candidate_consumption: Mapping[str, Any],
     candidate_artifacts: Mapping[str, Any],
+    expected_targets: Optional[Set[str]] = None,
 ) -> Tuple[Optional[str], str]:
     """
     Resolves a target string against the canonical target domain.
@@ -113,7 +166,10 @@ def _resolve_canonical_target_key(
     if not target:
         return None, "unresolved"
 
-    expected_targets = canonical_artifact_consumption_targets(candidate_artifacts)
+    if expected_targets is None:
+        expected_targets = canonical_artifact_consumption_targets(
+            candidate_artifacts
+        )
 
     # Already canonical format
     if "::" in target:
@@ -155,60 +211,205 @@ def _rebuild_consumer_slice(
     candidate_consumption: Dict[str, Any],
     candidate_artifacts: Mapping[str, Any],
     reexports: Mapping[str, str],
+    expected_targets: Optional[Set[str]] = None,
+    consumer_target_index: Optional[Dict[str, Set[str]]] = None,
 ) -> Tuple[Dict[str, Any], bool]:
     """
-    Rebuilds the entire artifact_consumption slice for a single consumer in Copy-On-Write fashion.
-    Inspects all canonical usage families: direct_calls, runtime_calls, qualified_refs,
-    callback_calls, event_bindings, api_imports, inheritance.
-    Returns (updated_consumption_dict, is_ambiguous). If is_ambiguous is True, returns original container.
+    Rebuilds the entire artifact_consumption slice for a single consumer.
+
+    When an execution-local reverse index is supplied, the candidate
+    top-level mapping is already Copy-On-Write and only entries known to
+    contain the consumer are inspected. Nested entries are still copied
+    before mutation.
+
+    Without the execution-local index, the legacy full-map fallback is
+    preserved.
+
+    Returns (updated_consumption_dict, is_ambiguous). If is_ambiguous is
+    True, returns the original container without mutation.
     """
     c_aliases = dict(consumer_facts.aliases)
     c_tagged = (
-        [(sym, "direct_calls") for sym in consumer_facts.direct_calls]
-        + [(sym, "runtime_calls") for sym in consumer_facts.runtime_calls]
-        + [(sym, "qualified_refs") for sym in consumer_facts.qualified_refs]
-        + [(sym, "callback_calls") for sym in consumer_facts.callback_calls]
-        + [(sym, "event_bindings") for sym in consumer_facts.event_bindings]
-        + [(sym, "api_imports") for sym in consumer_facts.imports]
-        + [(item[1], "inheritance") for item in consumer_facts.inheritance_refs if len(item) >= 2 and item[1]]
+        [
+            (sym, "direct_calls")
+            for sym in consumer_facts.direct_calls
+        ]
+        + [
+            (sym, "runtime_calls")
+            for sym in consumer_facts.runtime_calls
+        ]
+        + [
+            (sym, "qualified_refs")
+            for sym in consumer_facts.qualified_refs
+        ]
+        + [
+            (sym, "callback_calls")
+            for sym in consumer_facts.callback_calls
+        ]
+        + [
+            (sym, "event_bindings")
+            for sym in consumer_facts.event_bindings
+        ]
+        + [
+            (sym, "api_imports")
+            for sym in consumer_facts.imports
+        ]
+        + [
+            (item[1], "inheritance")
+            for item in consumer_facts.inheritance_refs
+            if len(item) >= 2 and item[1]
+        ]
     )
 
     rebuilt_targets: Dict[str, Set[str]] = {}
     is_ambiguous = False
 
     for sym, ch_name in c_tagged:
-        raw_t = _resolve_reexport(_resolve_alias(sym, c_aliases), reexports)
-        target, status = _resolve_canonical_target_key(raw_t, candidate_consumption, candidate_artifacts)
+        raw_t = _resolve_reexport(
+            _resolve_alias(
+                sym,
+                c_aliases,
+            ),
+            reexports,
+        )
+        target, status = _resolve_canonical_target_key(
+            raw_t,
+            candidate_consumption,
+            candidate_artifacts,
+            expected_targets=expected_targets,
+        )
+
         if status == "ambiguous":
             is_ambiguous = True
-        elif status == "resolved" and target:
+
+        elif (
+            status == "resolved"
+            and target
+        ):
             if target not in rebuilt_targets:
                 rebuilt_targets[target] = set()
-            rebuilt_targets[target].add(ch_name)
+
+            rebuilt_targets[target].add(
+                ch_name
+            )
 
     if is_ambiguous:
         return candidate_consumption, True
 
-    # Copy-on-Write update of candidate_consumption container and entries
-    new_consumption = dict(candidate_consumption)
+    if consumer_target_index is None:
+        new_consumption = dict(
+            candidate_consumption
+        )
+        previous_targets = tuple(
+            new_consumption.keys()
+        )
+    else:
+        new_consumption = candidate_consumption
+        previous_targets = tuple(
+            consumer_target_index.get(
+                consumer,
+                (),
+            )
+        )
 
-    # 1. Remove consumer from all previous target entries
-    for t_key, entry in list(new_consumption.items()):
-        if consumer in entry.get("consumers", []) or consumer in entry.get("channels", {}):
-            copied_entry = _get_copy_of_entry(entry)
-            if consumer in copied_entry["consumers"]:
-                copied_entry["consumers"].remove(consumer)
-            copied_entry["channels"].pop(consumer, None)
-            new_consumption[t_key] = copied_entry
+    # Remove the consumer only from entries known to contain its old slice.
+    for t_key in previous_targets:
+        entry = new_consumption.get(
+            t_key
+        )
+        if not isinstance(entry, dict):
+            continue
 
-    # 2. Install rebuilt exact slice
+        if (
+            consumer in entry.get(
+                "consumers",
+                [],
+            )
+            or consumer
+            in entry.get(
+                "channels",
+                {},
+            )
+        ):
+            copied_entry = _get_copy_of_entry(
+                entry
+            )
+
+            if consumer in copied_entry[
+                "consumers"
+            ]:
+                copied_entry[
+                    "consumers"
+                ].remove(
+                    consumer
+                )
+
+            copied_entry[
+                "channels"
+            ].pop(
+                consumer,
+                None,
+            )
+
+            new_consumption[
+                t_key
+            ] = copied_entry
+
+    # Install rebuilt exact slice.
     for target, channels in rebuilt_targets.items():
-        entry = _get_copy_of_entry(new_consumption.get(target, {"consumers": [], "channels": {}}))
-        if consumer not in entry["consumers"]:
-            entry["consumers"].append(consumer)
-        entry["consumers"] = sorted(set(entry["consumers"]))
-        entry["channels"][consumer] = sorted(channels)
-        new_consumption[target] = entry
+        entry = _get_copy_of_entry(
+            new_consumption.get(
+                target,
+                {
+                    "consumers": [],
+                    "channels": {},
+                },
+            )
+        )
+
+        if consumer not in entry[
+            "consumers"
+        ]:
+            entry[
+                "consumers"
+            ].append(
+                consumer
+            )
+
+        entry[
+            "consumers"
+        ] = sorted(
+            set(
+                entry[
+                    "consumers"
+                ]
+            )
+        )
+
+        entry[
+            "channels"
+        ][
+            consumer
+        ] = sorted(
+            channels
+        )
+
+        new_consumption[
+            target
+        ] = entry
+
+    if consumer_target_index is not None:
+        if rebuilt_targets:
+            consumer_target_index[
+                consumer
+            ] = set(
+                rebuilt_targets
+            )
+        else:
+            consumer_target_index.pop(
+                consumer,
+                None,
+            )
 
     return new_consumption, False
 
@@ -399,6 +600,13 @@ def execute_refresh_plan(
                 ) and art_key not in current_targets:
                     candidate.artifact_consumption.pop(art_key, None)
 
+    expected_targets = canonical_artifact_consumption_targets(
+        candidate.artifacts
+    )
+    consumer_target_index = _build_consumer_target_index(
+        candidate.artifact_consumption
+    )
+
     # 2. REPARSE - record planned reparse modules (trace-only, no secondary source I/O)
     executed_reparse: List[str] = []
     for reparse_mod in plan.reparse_modules:
@@ -418,12 +626,18 @@ def execute_refresh_plan(
                     candidate_consumption=candidate.artifact_consumption,
                     candidate_artifacts=candidate.artifacts,
                     reexports=new_reexports,
+                    expected_targets=expected_targets,
+                    consumer_target_index=consumer_target_index,
                 )
                 if is_ambig:
                     candidate.artifact_consumption = _remove_consumer_slice(
                         candidate.artifact_consumption,
                         consumer_path,
                     )
+                    consumer_target_index.pop(
+                        consumer_path,
+                        None,
+                    )
                     artifact_consumption_failed = True
                     candidate.artifact_consumption_state = "stale"
                     break
@@ -479,12 +693,18 @@ def execute_refresh_plan(
                     candidate_consumption=candidate.artifact_consumption,
                     candidate_artifacts=candidate.artifacts,
                     reexports=new_reexports,
+                    expected_targets=expected_targets,
+                    consumer_target_index=consumer_target_index,
                 )
                 if is_ambig:
                     candidate.artifact_consumption = _remove_consumer_slice(
                         candidate.artifact_consumption,
                         delta.module_path,
                     )
+                    consumer_target_index.pop(
+                        delta.module_path,
+                        None,
+                    )
                     artifact_consumption_failed = True
                     candidate.artifact_consumption_state = "stale"
                 else:

diff --git a/tests/test_incremental_plan_executor_complexity.py b/tests/test_incremental_plan_executor_complexity.py
new file mode 100644
index 0000000..17f0793
--- /dev/null
+++ b/tests/test_incremental_plan_executor_complexity.py
@@ -0,0 +1,258 @@
+from pathlib import Path
+
+import pytest
+
+from contextor.core.analysis.incremental import (
+    plan_executor,
+)
+from contextor.core.analysis.state_manager import (
+    FileDelta,
+    RepositoryAnalysisState,
+)
+from contextor.core.domain.refresh_plan import (
+    RefreshPlan,
+)
+from contextor.core.domain.usage_facts import (
+    ModuleUsageFacts,
+)
+
+
+class _NoFullScanDict(dict):
+    def items(self):
+        raise AssertionError(
+            "indexed rebuild must not scan the full "
+            "artifact_consumption mapping"
+        )
+
+
+def test_indexed_rebuild_uses_precomputed_domain_without_full_scan(
+    monkeypatch: pytest.MonkeyPatch,
+) -> None:
+    consumption = _NoFullScanDict(
+        {
+            "provider::foo": {
+                "consumers": [
+                    "consumer",
+                ],
+                "channels": {
+                    "consumer": [
+                        "direct_calls",
+                    ],
+                },
+            },
+            "provider::bar": {
+                "consumers": [],
+                "channels": {},
+            },
+        }
+    )
+
+    usage = ModuleUsageFacts(
+        direct_calls=(
+            "provider.bar",
+        ),
+    )
+
+    consumer_target_index = {
+        "consumer": {
+            "provider::foo",
+        },
+    }
+
+    def fail_target_rebuild(
+        artifacts,
+    ):
+        pytest.fail(
+            "precomputed target domain must be reused"
+        )
+
+    monkeypatch.setattr(
+        plan_executor,
+        "canonical_artifact_consumption_targets",
+        fail_target_rebuild,
+    )
+
+    rebuilt, is_ambiguous = (
+        plan_executor._rebuild_consumer_slice(
+            consumer="consumer",
+            consumer_facts=usage,
+            candidate_consumption=consumption,
+            candidate_artifacts={
+                "provider": {
+                    "own_symbols": [
+                        "foo",
+                        "bar",
+                    ],
+                },
+            },
+            reexports={},
+            expected_targets={
+                "provider::foo",
+                "provider::bar",
+            },
+            consumer_target_index=consumer_target_index,
+        )
+    )
+
+    assert is_ambiguous is False
+    assert rebuilt is consumption
+
+    assert rebuilt[
+        "provider::foo"
+    ] == {
+        "consumers": [],
+        "channels": {},
+    }
+
+    assert rebuilt[
+        "provider::bar"
+    ] == {
+        "consumers": [
+            "consumer",
+        ],
+        "channels": {
+            "consumer": [
+                "direct_calls",
+            ],
+        },
+    }
+
+    assert consumer_target_index == {
+        "consumer": {
+            "provider::bar",
+        },
+    }
+
+
+def test_execute_refresh_plan_builds_target_domain_once_for_many_consumers(
+    monkeypatch: pytest.MonkeyPatch,
+    tmp_path: Path,
+) -> None:
+    state = RepositoryAnalysisState(
+        artifacts={
+            "provider": {
+                "own_symbols": [
+                    "foo",
+                    "bar",
+                ],
+            },
+        },
+        artifact_consumption={
+            "provider::foo": {
+                "consumers": [
+                    "consumer_a",
+                    "consumer_b",
+                ],
+                "channels": {
+                    "consumer_a": [
+                        "direct_calls",
+                    ],
+                    "consumer_b": [
+                        "direct_calls",
+                    ],
+                },
+            },
+            "provider::bar": {
+                "consumers": [],
+                "channels": {},
+            },
+        },
+        artifact_consumption_state="fresh",
+        module_usages={
+            "consumer_a": ModuleUsageFacts(
+                direct_calls=(
+                    "provider.bar",
+                ),
+            ),
+            "consumer_b": ModuleUsageFacts(
+                direct_calls=(
+                    "provider.bar",
+                ),
+            ),
+        },
+    )
+
+    original_targets = (
+        plan_executor
+        .canonical_artifact_consumption_targets
+    )
+    target_domain_calls = 0
+
+    def counted_targets(
+        artifacts,
+    ):
+        nonlocal target_domain_calls
+        target_domain_calls += 1
+        return original_targets(
+            artifacts
+        )
+
+    monkeypatch.setattr(
+        plan_executor,
+        "canonical_artifact_consumption_targets",
+        counted_targets,
+    )
+
+    outcome = plan_executor.execute_refresh_plan(
+        state=state,
+        delta=FileDelta(
+            module_path="changed",
+        ),
+        usage_delta=None,
+        plan=RefreshPlan(
+            recompute_modules=(
+                "consumer_a",
+                "consumer_b",
+            ),
+        ),
+        new_imports=None,
+        new_artifacts=None,
+        new_usage=None,
+        root_path=tmp_path,
+        file_path=str(
+            tmp_path
+            / "changed.py"
+        ),
+    )
+
+    assert target_domain_calls == 1
+
+    assert state.artifact_consumption[
+        "provider::foo"
+    ][
+        "consumers"
+    ] == [
+        "consumer_a",
+        "consumer_b",
+    ]
+
+    assert outcome.candidate_state.artifact_consumption[
+        "provider::foo"
+    ] == {
+        "consumers": [],
+        "channels": {},
+    }
+
+    assert outcome.candidate_state.artifact_consumption[
+        "provider::bar"
+    ] == {
+        "consumers": [
+            "consumer_a",
+            "consumer_b",
+        ],
+        "channels": {
+            "consumer_a": [
+                "direct_calls",
+            ],
+            "consumer_b": [
+                "direct_calls",
+            ],
+        },
+    }
+
+    assert outcome.execution_trace[
+        "recompute_modules"
+    ] == (
+        "consumer_a",
+        "consumer_b",
+    )

