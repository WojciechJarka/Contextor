# CPA5_DETERMINISTIC_PROFILE_AGGREGATOR

## STATUS

SUCCESS.

## BASE_HEAD

`5867dbb299cd623995188434077da9a0e111e466` (matches EXPECTED_BASE).

## FILES_CHANGED

- contextor/core/analysis/profile_analysis.py
- tests/test_profile_analysis.py
- walkthrough.md (this report)

## IMPLEMENTATION

Added the pure in-memory `build_analysis_profile(events, operation_id=...)` aggregator. It scopes ANALYSIS events to the supplied operation, fails closed for missing/duplicate/invalid evidence, and never starts analysis, takes leases, opens trace sessions, reads JSONL, or writes state.

## TESTS

- `& .\.venv\Scripts\python.exe -m pytest -q tests\test_profile_analysis.py`: 3 passed in 0.90s.
- `& .\.venv\Scripts\python.exe -m py_compile contextor\core\analysis\profile_analysis.py tests\test_profile_analysis.py`: passed.
- `git diff --check -- contextor/core/analysis/profile_analysis.py tests/test_profile_analysis.py`: passed.

No full analysis or benchmark ran.

## PROFILE_CONTRACT

Bottleneck ranking uses only `FULL_ANALYSIS_STAGE_END.elapsed_ms` events with `timing_semantics=critical_path_stage`, ordered deterministically by descending duration and declared stage order. `absolute_wall_authoritative` is always `False`.

## REASON_CODES

- Indexing: `source_parse_failures`, `warm_cache_still_parses_source`, `cold_or_partial_cache_work`, or `unattributed`.
- Canonical materialization: `lineage_materialization_work`, `lineage_reresolution_work`, `lineage_reuse_gate_cost`, or `unattributed`.
- All reason codes derive solely from structured event evidence.

## CRITICAL_VS_AGGREGATE_PROOF

The focused test gives aggregate worker diagnostics `source_parse_sum_ms=9000.0` and `cache_get_sum_ms=4000.0`, yet the maximum ranked critical-path stage remains `reports=200.0`. Worker sums appear only in `aggregate_worker_diagnostics`.

Post-implementation Contextor verification found no LIVE artifact for `build_analysis_profile`, expected because no refresh was run. The existing canonical `run_full_analysis_exclusive` call neighborhood remains only `acquire_full_analysis` and `release_full_analysis`; scoped Git verification found no diff in existing coordinator, facade, or trace owners.

## FULL_DIFFS

### contextor/core/analysis/profile_analysis.py

```diff
diff --git a/contextor/core/analysis/profile_analysis.py b/contextor/core/analysis/profile_analysis.py
new file mode 100644
index 0000000..45f91a0
--- /dev/null
+++ b/contextor/core/analysis/profile_analysis.py
@@ -0,0 +1,419 @@
+from __future__ import annotations
+
+from typing import Any
+
+
+PROFILE_SCHEMA = "contextor-profile-analysis/v1"
+
+FULL_ANALYSIS_STAGES = (
+    "identity_and_setup",
+    "indexing",
+    "reference_and_collision",
+    "graph",
+    "validation",
+    "metrics",
+    "reports",
+    "canonical_materialization",
+    "persistence",
+    "live_publish",
+    "finalize",
+)
+
+_REQUIRED_SINGLE_EVENTS = (
+    "FULL_ANALYSIS_LEASE_ACQUIRED",
+    "FULL_ANALYSIS_BODY_END",
+    "FULL_ANALYSIS_END",
+    "FULL_ANALYSIS_INDEX_EVIDENCE",
+    "FULL_ANALYSIS_LINEAGE_EXTRACTION",
+    "FULL_ANALYSIS_LINEAGE_MATERIALIZATION",
+)
+
+
+def _number(event: dict[str, object], field: str) -> float:
+    value = event.get(field)
+    if isinstance(value, bool) or not isinstance(value, (int, float)):
+        raise ValueError(f"{event.get('ev', 'event')}.{field} is not numeric")
+    if value < 0:
+        raise ValueError(f"{event.get('ev', 'event')}.{field} is negative")
+    return float(value)
+
+
+def _count(event: dict[str, object], field: str) -> int:
+    value = event.get(field)
+    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
+        raise ValueError(
+            f"{event.get('ev', 'event')}.{field} is not a non-negative integer"
+        )
+    return value
+
+
+def _round_ms(value: float) -> float:
+    return round(value, 3)
+
+
+def _single_event(
+    events: list[dict[str, object]],
+    event_name: str,
+) -> tuple[dict[str, object] | None, bool]:
+    matches = [event for event in events if event.get("ev") == event_name]
+    if len(matches) == 1:
+        return matches[0], False
+    return None, len(matches) > 1
+
+
+def _incomplete_profile(
+    operation_id: str,
+    *,
+    missing: list[str],
+    duplicates: list[str],
+) -> dict[str, object]:
+    return {
+        "schema": PROFILE_SCHEMA,
+        "status": "incomplete",
+        "operation_id": operation_id,
+        "missing": sorted(missing),
+        "duplicates": sorted(duplicates),
+    }
+
+
+def _indexing_reason(
+    event: dict[str, object],
+) -> tuple[str, dict[str, object]]:
+    file_tasks = _count(event, "file_tasks")
+    source_parse_calls = _count(event, "source_parse_calls")
+    source_parse_failures = _count(event, "source_parse_failures")
+    cache_get_calls = _count(event, "cache_get_calls")
+    cache_hits = _count(event, "cache_hits")
+    cache_misses = _count(event, "cache_misses")
+    lineage_cache_hits = _count(event, "lineage_cache_hits")
+    lineage_extract_calls = _count(event, "lineage_extract_calls")
+
+    evidence = {
+        "file_tasks": file_tasks,
+        "source_parse_calls": source_parse_calls,
+        "source_parse_failures": source_parse_failures,
+        "cache_get_calls": cache_get_calls,
+        "cache_hits": cache_hits,
+        "cache_misses": cache_misses,
+        "lineage_cache_hits": lineage_cache_hits,
+        "lineage_extract_calls": lineage_extract_calls,
+    }
+
+    if source_parse_failures:
+        return "source_parse_failures", evidence
+
+    if (
+        file_tasks > 0
+        and source_parse_calls == file_tasks
+        and cache_get_calls == file_tasks
+        and cache_hits == file_tasks
+        and cache_misses == 0
+        and lineage_cache_hits == file_tasks
+        and lineage_extract_calls == 0
+    ):
+        return "warm_cache_still_parses_source", evidence
+
+    if cache_misses > 0 or lineage_extract_calls > 0:
+        return "cold_or_partial_cache_work", evidence
+
+    return "unattributed", evidence
+
+
+def _canonical_materialization_reason(
+    stage_ms: float,
+    event: dict[str, object],
+) -> tuple[str, dict[str, object]]:
+    reuse_sources = _count(event, "reuse_sources")
+    reresolve_sources = _count(event, "reresolve_sources")
+    materialize_sources = _count(event, "materialize_sources")
+    fallback_sources = _count(event, "reresolve_fallback_sources")
+    lineage_sources = _count(event, "lineage_sources")
+
+    lineage_elapsed_ms = _number(event, "elapsed_ms")
+    reuse_gate_ms = _number(event, "reuse_gate_ms")
+    reresolve_calls_ms = _number(event, "reresolve_calls_ms")
+    materialize_calls_ms = _number(event, "materialize_calls_ms")
+
+    evidence = {
+        "lineage_elapsed_ms": _round_ms(lineage_elapsed_ms),
+        "lineage_sources": lineage_sources,
+        "reuse_sources": reuse_sources,
+        "reresolve_sources": reresolve_sources,
+        "materialize_sources": materialize_sources,
+        "reresolve_fallback_sources": fallback_sources,
+        "reuse_gate_ms": _round_ms(reuse_gate_ms),
+        "reresolve_calls_ms": _round_ms(reresolve_calls_ms),
+        "materialize_calls_ms": _round_ms(materialize_calls_ms),
+    }
+
+    if materialize_sources > 0:
+        return "lineage_materialization_work", evidence
+
+    if reresolve_sources > 0 or fallback_sources > 0:
+        return "lineage_reresolution_work", evidence
+
+    if (
+        lineage_sources > 0
+        and reuse_sources == lineage_sources
+        and reresolve_sources == 0
+        and materialize_sources == 0
+        and fallback_sources == 0
+        and reuse_gate_ms > 0.0
+        and stage_ms > 0.0
+        and lineage_elapsed_ms >= stage_ms * 0.5
+    ):
+        return "lineage_reuse_gate_cost", evidence
+
+    return "unattributed", evidence
+
+
+def build_analysis_profile(
+    events: list[dict[str, object]],
+    *,
+    operation_id: str,
+) -> dict[str, object]:
+    if not isinstance(operation_id, str) or not operation_id:
+        raise ValueError("operation_id must be a non-empty string")
+
+    scoped = [
+        event
+        for event in events
+        if event.get("d") == "ANALYSIS"
+        and event.get("op") == operation_id
+    ]
+
+    missing: list[str] = []
+    duplicates: list[str] = []
+    single_events: dict[str, dict[str, object]] = {}
+
+    for event_name in _REQUIRED_SINGLE_EVENTS:
+        event, duplicate = _single_event(scoped, event_name)
+        if duplicate:
+            duplicates.append(event_name)
+        elif event is None:
+            missing.append(event_name)
+        else:
+            single_events[event_name] = event
+
+    stage_events: dict[str, dict[str, object]] = {}
+    for stage in FULL_ANALYSIS_STAGES:
+        matches = [
+            event
+            for event in scoped
+            if event.get("ev") == "FULL_ANALYSIS_STAGE_END"
+            and event.get("stage") == stage
+        ]
+        label = f"FULL_ANALYSIS_STAGE_END:{stage}"
+        if len(matches) > 1:
+            duplicates.append(label)
+        elif not matches:
+            missing.append(label)
+        else:
+            stage_events[stage] = matches[0]
+
+    if missing or duplicates:
+        return _incomplete_profile(
+            operation_id,
+            missing=missing,
+            duplicates=duplicates,
+        )
+
+    try:
+        lease_event = single_events["FULL_ANALYSIS_LEASE_ACQUIRED"]
+        body_event = single_events["FULL_ANALYSIS_BODY_END"]
+        end_event = single_events["FULL_ANALYSIS_END"]
+        index_event = single_events["FULL_ANALYSIS_INDEX_EVIDENCE"]
+        lineage_extract_event = single_events["FULL_ANALYSIS_LINEAGE_EXTRACTION"]
+        lineage_materialization_event = single_events[
+            "FULL_ANALYSIS_LINEAGE_MATERIALIZATION"
+        ]
+
+        lease_wait_ms = _number(lease_event, "wait_ms")
+        analysis_ms = _number(body_event, "analysis_ms")
+        body_elapsed_ms = _number(body_event, "elapsed_ms")
+        total_before_release_ms = _number(
+            body_event,
+            "total_before_release_ms",
+        )
+        total_ms = _number(end_event, "total_ms")
+        total_elapsed_ms = _number(end_event, "elapsed_ms")
+
+        if body_elapsed_ms != analysis_ms:
+            raise ValueError(
+                "FULL_ANALYSIS_BODY_END.elapsed_ms must equal analysis_ms"
+            )
+        if total_elapsed_ms != total_ms:
+            raise ValueError(
+                "FULL_ANALYSIS_END.elapsed_ms must equal total_ms"
+            )
+        if total_before_release_ms < analysis_ms:
+            raise ValueError(
+                "total_before_release_ms cannot be shorter than analysis_ms"
+            )
+        if total_ms < total_before_release_ms:
+            raise ValueError(
+                "total_ms cannot be shorter than total_before_release_ms"
+            )
+
+        stage_values: dict[str, float] = {}
+        for stage, event in stage_events.items():
+            if event.get("timing_semantics") != "critical_path_stage":
+                raise ValueError(
+                    f"FULL_ANALYSIS_STAGE_END:{stage} has invalid timing_semantics"
+                )
+            stage_values[stage] = _number(event, "elapsed_ms")
+
+        if (
+            index_event.get("timing_semantics")
+            != "aggregate_file_task_not_critical_path"
+        ):
+            raise ValueError(
+                "FULL_ANALYSIS_INDEX_EVIDENCE has invalid timing_semantics"
+            )
+        if (
+            lineage_extract_event.get("timing_semantics")
+            != "aggregate_file_task_not_critical_path"
+        ):
+            raise ValueError(
+                "FULL_ANALYSIS_LINEAGE_EXTRACTION has invalid timing_semantics"
+            )
+        if (
+            lineage_materialization_event.get("timing_semantics")
+            != "critical_path_subphase_with_nested_components"
+        ):
+            raise ValueError(
+                "FULL_ANALYSIS_LINEAGE_MATERIALIZATION has invalid timing_semantics"
+            )
+
+        index_reason, index_reason_evidence = _indexing_reason(index_event)
+        canonical_reason, canonical_reason_evidence = (
+            _canonical_materialization_reason(
+                stage_values["canonical_materialization"],
+                lineage_materialization_event,
+            )
+        )
+
+        stage_breakdown = [
+            {
+                "stage": stage,
+                "critical_path_ms": _round_ms(stage_values[stage]),
+            }
+            for stage in FULL_ANALYSIS_STAGES
+        ]
+
+        ranked = sorted(
+            FULL_ANALYSIS_STAGES,
+            key=lambda stage: (
+                -stage_values[stage],
+                FULL_ANALYSIS_STAGES.index(stage),
+            ),
+        )
+
+        bottlenecks: list[dict[str, object]] = []
+        for rank, stage in enumerate(ranked[:5], start=1):
+            reason_code = "unattributed"
+            reason_evidence: dict[str, object] = {}
+
+            if stage == "indexing":
+                reason_code = index_reason
+                reason_evidence = index_reason_evidence
+            elif stage == "canonical_materialization":
+                reason_code = canonical_reason
+                reason_evidence = canonical_reason_evidence
+
+            share = (
+                (stage_values[stage] / analysis_ms) * 100.0
+                if analysis_ms > 0.0
+                else 0.0
+            )
+
+            bottlenecks.append(
+                {
+                    "rank": rank,
+                    "stage": stage,
+                    "critical_path_ms": _round_ms(stage_values[stage]),
+                    "share_of_analysis_pct": round(share, 2),
+                    "reason_code": reason_code,
+                    "evidence": reason_evidence,
+                }
+            )
+
+        source_parse_sum_ms = _number(
+            index_event,
+            "source_parse_sum_ms",
+        )
+        cache_get_sum_ms = _number(
+            index_event,
+            "cache_get_sum_ms",
+        )
+        lineage_extract_sum_ms = _number(
+            index_event,
+            "lineage_extract_sum_ms",
+        )
+        lineage_event_sum_ms = _number(
+            lineage_extract_event,
+            "elapsed_ms",
+        )
+
+        stage_sum_ms = sum(stage_values.values())
+
+        return {
+            "schema": PROFILE_SCHEMA,
+            "status": "ok",
+            "operation_id": operation_id,
+            "measurement": {
+                "purpose": "diagnostic_profile_not_benchmark",
+                "absolute_wall_authoritative": False,
+                "lease_wait_ms": _round_ms(lease_wait_ms),
+                "analysis_body_ms": _round_ms(analysis_ms),
+                "total_before_release_ms": _round_ms(
+                    total_before_release_ms
+                ),
+                "total_ms": _round_ms(total_ms),
+                "stage_sum_ms": _round_ms(stage_sum_ms),
+                "unattributed_analysis_ms": _round_ms(
+                    max(0.0, analysis_ms - stage_sum_ms)
+                ),
+            },
+            "stage_breakdown": stage_breakdown,
+            "bottlenecks": bottlenecks,
+            "indexing_evidence": {
+                "reason_code": index_reason,
+                **index_reason_evidence,
+            },
+            "lineage_materialization_evidence": {
+                "reason_code": canonical_reason,
+                **canonical_reason_evidence,
+            },
+            "aggregate_worker_diagnostics": {
+                "timing_semantics": (
+                    "aggregate_file_task_not_critical_path"
+                ),
+                "source_parse_sum_ms": _round_ms(
+                    source_parse_sum_ms
+                ),
+                "cache_get_sum_ms": _round_ms(
+                    cache_get_sum_ms
+                ),
+                "lineage_extract_sum_ms": _round_ms(
+                    lineage_extract_sum_ms
+                ),
+                "lineage_extract_event_sum_ms": _round_ms(
+                    lineage_event_sum_ms
+                ),
+            },
+        }
+    except ValueError as exc:
+        return {
+            "schema": PROFILE_SCHEMA,
+            "status": "invalid_evidence",
+            "operation_id": operation_id,
+            "error": str(exc),
+        }
+
+
+__all__ = [
+    "PROFILE_SCHEMA",
+    "FULL_ANALYSIS_STAGES",
+    "build_analysis_profile",
+]
```

### tests/test_profile_analysis.py

```diff
diff --git a/tests/test_profile_analysis.py b/tests/test_profile_analysis.py
new file mode 100644
index 0000000..6d81b6a
--- /dev/null
+++ b/tests/test_profile_analysis.py
@@ -0,0 +1,226 @@
+from contextor.core.analysis.profile_analysis import (
+    FULL_ANALYSIS_STAGES,
+    PROFILE_SCHEMA,
+    build_analysis_profile,
+)
+
+
+def _profile_events(operation_id: str = "profile-test"):
+    stage_ms = {
+        "identity_and_setup": 20.0,
+        "indexing": 100.0,
+        "reference_and_collision": 30.0,
+        "graph": 25.0,
+        "validation": 10.0,
+        "metrics": 15.0,
+        "reports": 200.0,
+        "canonical_materialization": 80.0,
+        "persistence": 40.0,
+        "live_publish": 35.0,
+        "finalize": 5.0,
+    }
+
+    events = [
+        {
+            "d": "ANALYSIS",
+            "ev": "FULL_ANALYSIS_LEASE_ACQUIRED",
+            "op": operation_id,
+            "wait_ms": 3.0,
+            "timing_semantics": "critical_path_lease_wait",
+        },
+        {
+            "d": "ANALYSIS",
+            "ev": "FULL_ANALYSIS_BODY_END",
+            "op": operation_id,
+            "analysis_ms": 600.0,
+            "total_before_release_ms": 603.0,
+            "elapsed_ms": 600.0,
+            "timing_semantics": "critical_path_analysis_body",
+        },
+        {
+            "d": "ANALYSIS",
+            "ev": "FULL_ANALYSIS_END",
+            "op": operation_id,
+            "total_ms": 605.0,
+            "elapsed_ms": 605.0,
+            "timing_semantics": "critical_path_total",
+        },
+        {
+            "d": "ANALYSIS",
+            "ev": "FULL_ANALYSIS_INDEX_EVIDENCE",
+            "op": operation_id,
+            "timing_semantics": (
+                "aggregate_file_task_not_critical_path"
+            ),
+            "file_tasks": 2,
+            "source_parse_calls": 2,
+            "source_parse_failures": 0,
+            "cache_get_calls": 2,
+            "cache_hits": 2,
+            "cache_misses": 0,
+            "lineage_cache_hits": 2,
+            "lineage_extract_calls": 0,
+            "source_parse_sum_ms": 9000.0,
+            "cache_get_sum_ms": 4000.0,
+            "lineage_extract_sum_ms": 0.0,
+        },
+        {
+            "d": "ANALYSIS",
+            "ev": "FULL_ANALYSIS_LINEAGE_EXTRACTION",
+            "op": operation_id,
+            "elapsed_ms": 0.0,
+            "timing_semantics": (
+                "aggregate_file_task_not_critical_path"
+            ),
+            "lineage_extract_calls": 0,
+            "lineage_cache_hits": 2,
+        },
+        {
+            "d": "ANALYSIS",
+            "ev": "FULL_ANALYSIS_LINEAGE_MATERIALIZATION",
+            "op": operation_id,
+            "elapsed_ms": 70.0,
+            "timing_semantics": (
+                "critical_path_subphase_with_nested_components"
+            ),
+            "reuse_sources": 2,
+            "reresolve_sources": 0,
+            "materialize_sources": 0,
+            "reresolve_fallback_sources": 0,
+            "reuse_gate_ms": 60.0,
+            "reresolve_calls_ms": 0.0,
+            "materialize_calls_ms": 0.0,
+            "lineage_sources": 2,
+            "lineage_anchors": 10,
+            "lineage_flows": 20,
+            "lineage_surfaces": 2,
+            "lineage_descriptors": 2,
+        },
+    ]
+
+    events.extend(
+        {
+            "d": "ANALYSIS",
+            "ev": "FULL_ANALYSIS_STAGE_END",
+            "op": operation_id,
+            "stage": stage,
+            "elapsed_ms": elapsed_ms,
+            "timing_semantics": "critical_path_stage",
+        }
+        for stage, elapsed_ms in stage_ms.items()
+    )
+    return events
+
+
+def test_profile_ranks_only_critical_path_and_attributes_known_causes():
+    events = _profile_events()
+    events.append(
+        {
+            "d": "ANALYSIS",
+            "ev": "FULL_ANALYSIS_STAGE_END",
+            "op": "other-operation",
+            "stage": "indexing",
+            "elapsed_ms": 99999.0,
+            "timing_semantics": "critical_path_stage",
+        }
+    )
+
+    profile = build_analysis_profile(
+        events,
+        operation_id="profile-test",
+    )
+
+    assert profile["schema"] == PROFILE_SCHEMA
+    assert profile["status"] == "ok"
+    assert profile["measurement"]["absolute_wall_authoritative"] is False
+    assert (
+        profile["measurement"]["purpose"]
+        == "diagnostic_profile_not_benchmark"
+    )
+
+    assert [item["stage"] for item in profile["bottlenecks"][:3]] == [
+        "reports",
+        "indexing",
+        "canonical_materialization",
+    ]
+    assert [
+        item["critical_path_ms"]
+        for item in profile["bottlenecks"][:3]
+    ] == [200.0, 100.0, 80.0]
+
+    indexing = next(
+        item
+        for item in profile["bottlenecks"]
+        if item["stage"] == "indexing"
+    )
+    assert indexing["reason_code"] == "warm_cache_still_parses_source"
+    assert indexing["evidence"]["source_parse_calls"] == 2
+    assert indexing["evidence"]["cache_hits"] == 2
+    assert indexing["evidence"]["lineage_extract_calls"] == 0
+
+    canonical = next(
+        item
+        for item in profile["bottlenecks"]
+        if item["stage"] == "canonical_materialization"
+    )
+    assert canonical["reason_code"] == "lineage_reuse_gate_cost"
+    assert canonical["evidence"]["lineage_elapsed_ms"] == 70.0
+    assert canonical["evidence"]["reuse_gate_ms"] == 60.0
+
+    aggregate = profile["aggregate_worker_diagnostics"]
+    assert aggregate["timing_semantics"] == (
+        "aggregate_file_task_not_critical_path"
+    )
+    assert aggregate["source_parse_sum_ms"] == 9000.0
+    assert aggregate["cache_get_sum_ms"] == 4000.0
+
+    assert max(
+        item["critical_path_ms"]
+        for item in profile["bottlenecks"]
+    ) == 200.0
+    assert len(profile["stage_breakdown"]) == len(
+        FULL_ANALYSIS_STAGES
+    )
+
+
+def test_profile_fails_closed_when_required_evidence_is_missing():
+    events = [
+        event
+        for event in _profile_events()
+        if event["ev"] != "FULL_ANALYSIS_INDEX_EVIDENCE"
+    ]
+
+    profile = build_analysis_profile(
+        events,
+        operation_id="profile-test",
+    )
+
+    assert profile == {
+        "schema": PROFILE_SCHEMA,
+        "status": "incomplete",
+        "operation_id": "profile-test",
+        "missing": ["FULL_ANALYSIS_INDEX_EVIDENCE"],
+        "duplicates": [],
+    }
+
+
+def test_profile_rejects_invalid_overlapping_coordinator_contract():
+    events = _profile_events()
+    body = next(
+        event
+        for event in events
+        if event["ev"] == "FULL_ANALYSIS_BODY_END"
+    )
+    body["total_before_release_ms"] = 10.0
+
+    profile = build_analysis_profile(
+        events,
+        operation_id="profile-test",
+    )
+
+    assert profile["schema"] == PROFILE_SCHEMA
+    assert profile["status"] == "invalid_evidence"
+    assert (
+        profile["error"]
+        == "total_before_release_ms cannot be shorter than analysis_ms"
+    )
```

## COMMIT_SHA

Not created (no commit requested).

## RUNTIME_RESTART_REQUIRED

NO. CPA5 adds an uncalled pure aggregator; MCP and Desktop/LIVE were not restarted.

