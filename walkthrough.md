# CONTEXTOR_B0G2C1_DETERMINISTIC_REFERENCE_DETAILS

## FILES_CHANGED
- C:\Temp\Contextor_Repo\contextor\core\reference\shared.py
- C:\Temp\Contextor_Repo\tests\test_reference_detail_determinism.py
- C:\Temp\Contextor_Repo\walkthrough.md (report only; excluded from source/test changes)

Precheck git status showed only the prior walkthrough report modified. The approved production file had no local diff; the new test file did not exist. No other source/test files changed.

## FULL_DIFFS
Complete actual unified diffs with zero context lines for both source/test files follow. The walkthrough itself is excluded.

## SOURCE_PRECHECK
- Contextor MCP was used first. Relevant tool documentation was read, including complete symbol fetch, call context, lineage, source search/range, artifact blast radius, and LIVE event semantics.
- Contextor fetched complete pre-patch _normalize_references from C:\Temp\Contextor_Repo\contextor\core\reference\shared.py, lines 590-609; source was complete with no partial source, workspace_sync=verified, canonical revision 354.
- The approved anchor matched exactly:
if key.endswith("_detail"):
    data[key] = values[:MAX_USAGE_DETAILS]
    continue
- MAX_USAGE_DETAILS is 15. Pre-patch imports were ast and typing.Any/Mapping.
- Artifact A598/1 direct static consumers are contextor.core.reference.engine and contextor.core.reference.index (2). Module blast radius: 232 downstream modules (80 production, 152 tests); samples were bounded/truncated.
- Canonical source search found two engine normalization call sites (lines 492 and 993), one index call site (line 724), and the shared definition. Intra-module call-context returned zero edges; direct consumers above come from artifact blast-radius evidence.
- Complete extract_api_consumers was fetched from C:\Temp\Contextor_Repo\contextor\core\api\api_consumers.py, lines 66-267, workspace_sync=verified at revision 354. It receives the reference mapping and passes detail lists through _normalize_detail; it is a downstream consumer, not a direct caller of _normalize_references. Scalar consumer categories/counts remain separate.
- Pre-edit git status showed only walkthrough.md modified from the prior task. The new regression test path did not exist; authorized source/test targets were otherwise clean.

## RED_TEST_BEFORE_PATCH
Added the first reversed-order regression before changing production, then ran only:
C:\Temp\Contextor_Repo\.venv\Scripts\python.exe -m pytest -q tests/test_reference_detail_determinism.py::test_reversed_input_order_normalizes_identically

Expected RED observed: exit 1. At index 0 the forward and reverse results differed (consumer versus other). The whitespace-only pytest context line is represented by an explanatory marker below to keep this report diff whitespace-clean. Captured output:

~~~text
F                                                                        [100%]
================================== FAILURES ===================================
______________ test_reversed_input_order_normalizes_identically ________________

def test_reversed_input_order_normalizes_identically() -> None:
    consumer = {"module": "consumer", "line": 4, "context": None}
    other = {"module": "other", "line": 3, "context": None}

    forward = _normalize_details(copy.deepcopy([consumer, other]))
    reverse = _normalize_details(copy.deepcopy([other, consumer]))

>       assert forward == reverse
E       AssertionError: assert [{'module': '...ntext': None}] == [{'module': '...ntext': None}]
E [pytest whitespace-only context line]
E         At index 0 diff: {"module": "consumer", "line": 4, "context": None} != {"module": "other", "line": 3, "context": None}
E         Use -v to get more diff

tests\test_reference_detail_determinism.py:34: AssertionError
1 failed in 1.01s
~~~

## NORMALIZATION_OWNER
Canonical owner: C:\Temp\Contextor_Repo\contextor\core\reference\shared.py.
The shared normalizer is directly consumed by reference.engine and reference.index. API consumer extraction receives normalized reference mappings. The patch remained limited to the shared canonical normalizer.

## EXACT_PRODUCTION_PATCH
Applied only the approved production changes:
- imported json and heapq.nsmallest;
- added the specified _detail_sort_key;
- changed only the normalizer docstring to state deterministic bounded ordering;
- replaced input-order slicing with nsmallest(MAX_USAGE_DETAILS, values, key=_detail_sort_key).

After watcher propagation, complete Contextor fetches for _detail_sort_key (lines 592-615) and _normalize_references (lines 618-642) both reported implementation_is_complete=true, no_partial_symbol_source=true, workspace_sync=verified at canonical revision 356. The complete actual source diff is included below.

## ORDERING_STABILITY
PASS. The reversed input regression is green after patch. The key orders by module, line (missing/non-integer/bool before concrete lines), then complete JSON payload with sorted keys and compact separators.

## CAP_MEMBERSHIP_STABILITY
PASS. Twenty records (> MAX_USAGE_DETAILS=15) in ascending and reversed input order selected the same first 15 canonical modules. Both outputs contained exactly 15 entries; input lists and contained record dictionaries remained unchanged.

## DUPLICATE_PRESERVATION
PASS. Eighteen identical observations yielded 15 identical entries. Detail records were not deduplicated through a set.

## DETAIL_FAMILY_PARITY
PASS. The regression covers called_by_detail, callback_called_detail, event_bound_by_detail, qualified_refs_detail, inherited_by_detail, and called_by_ambiguous_detail. Reversed inputs yield identical per-family output; None line/context/child/reason values remain and stay in their original family.

## API_CONSUMER_SEMANTICS
PASS in targeted regression. extract_api_consumers receives normalized references in opposite detail orders and returns identical direct_calls_detail. Scalar consumers remain ["consumer", "other"]; consumer_count remains total=2 and direct_calls=2, with other categories zero. Extra JSON-compatible detail keys remain present and participate in the deterministic tie-break. A non-dictionary detail payload raises the specified TypeError.

## REAL_DESKTOP_MCP_PARITY_RERUN
The unchanged real parity test was run once after the patch. Both entrypoints completed and persisted independent snapshots for the same isolated temporary repository, repository identity, fixture sources, and effective filters:
- Headless ContextorGUI.analyze executed the real task through a synchronous progress adapter; no analysis errors; snapshot writer=desktop.
- Public analyze_project created a non-reused MCP project job; its real worker completed; snapshot writer=mcp.
- Snapshot assertions passed: same root/repo_id ctx_1a8534b9/schema 1.4; Desktop revision 1/state_id 20261012_120948; MCP revision 2/state_id 20261012_120950; each state and FileState metadata matched its own state_id/revision; both provenance=snapshot and resync_required=false.
- Preserved evidence directory: C:\Users\DafoO\AppData\Local\Temp\pytest-of-DafoO\pytest-550\test_real_desktop_and_mcp_full0\b0g2c_canonical_mismatch_evidence.
- Preserved snapshots show direct_calls_detail equal in canonical order: consumer.py line 4, then other.py line 3.

## FIRST_REMAINING_MISMATCH_IF_ANY
The test stopped at its next first difference. Exact failure line:
Desktop/MCP canonical state mismatch: first_field=state.layer_information[{'kind': 'primitive', 'type': 'builtins.str', 'value': 'summary_data'}][{'kind': 'primitive', 'type': 'builtins.str', 'value': 'generated_at'}]; desktop='2026-10-12T12:09:48.838009'; mcp='2026-10-12T12:09:50.608340'; evidence=C:\Users\DafoO\AppData\Local\Temp\pytest-of-DafoO\pytest-550\test_real_desktop_and_mcp_full0\b0g2c_canonical_mismatch_evidence

The preserved values confirm the first difference is summary_data.generated_at. The original direct_calls_detail difference is resolved. No further mismatch was inspected. Per instruction, no second correction or comparator change was made.

Complete captured parity-test output:

~~~text
[PROGRESS] Step 1/8: Initializing repository identity
Starting directory indexing...
[PROGRESS] Step 2/8: Indexing repository files
Found 5 modules. Fetching graph...
[PROGRESS] Step 3/8: Resolving dependency graph
Graph validation (cache_hit=True)...
[PROGRESS] Step 4/8: Validating dependency graph
[PROGRESS] Step 5/8: Computing metrics, cycles and debt
[PROGRESS] Step 6/8: Generating architectural reports
Starting sequential report generation...
Generating name collisions report...
Generating artifact usage report...
Generating compact version of artifacts report...
Generating graph analytics report...
Serializing and saving: graph structure report (C:\Users\DafoO\AppData\Local\Temp\pytest-of-DafoO\pytest-550\test_real_desktop_and_mcp_full0\output\b0g2c_repo_b6b4c0319f054dc3920d4ab94af235a6_structure.json)...
Successfully saved: graph structure report
Serializing and saving: graph structure snapshot (C:\Users\DafoO\AppData\Local\Temp\pytest-of-DafoO\pytest-550\test_real_desktop_and_mcp_full0\output\b0g2c_repo_b6b4c0319f054dc3920d4ab94af235a6_20261012_120950\b0g2c_repo_b6b4c0319f054dc3920d4ab94af235a6_structure.json)...
Successfully saved: graph structure snapshot
Serializing and saving: name collisions report (C:\Users\DafoO\AppData\Local\Temp\pytest-of-DafoO\pytest-550\test_real_desktop_and_mcp_full0\output\b0g2c_repo_b6b4c0319f054dc3920d4ab94af235a6_name_collisions.json)...
Successfully saved: name collisions report
Serializing and saving: name collisions snapshot (C:\Users\DafoO\AppData\Local\Temp\pytest-of-DafoO\pytest-550\test_real_desktop_and_mcp_full0\output\b0g2c_repo_b6b4c0319f054dc3920d4ab94af235a6_20261012_120950\b0g2c_repo_b6b4c0319f054dc3920d4ab94af235a6_name_collisions.json)...
Successfully saved: name collisions snapshot
Serializing and saving: artifact snapshot (C:\Users\DafoO\AppData\Local\Temp\pytest-of-DafoO\pytest-550\test_real_desktop_and_mcp_full0\output\b0g2c_repo_b6b4c0319f054dc3920d4ab94af235a6_20261012_120950\b0g2c_repo_b6b4c0319f054dc3920d4ab94af235a6_artifacts_compact.json)...
Successfully saved: artifact snapshot
Serializing and saving: graph analytics report (C:\Users\DafoO\AppData\Local\Temp\pytest-of-DafoO\pytest-550\test_real_desktop_and_mcp_full0\output\b0g2c_repo_b6b4c0319f054dc3920d4ab94af235a6_graph_analytics.json)...
Successfully saved: graph analytics report
Serializing and saving: graph analytics snapshot (C:\Users\DafoO\AppData\Local\Temp\pytest-of-DafoO\pytest-550\test_real_desktop_and_mcp_full0\output\b0g2c_repo_b6b4c0319f054dc3920d4ab94af235a6_20261012_120950\b0g2c_repo_b6b4c0319f054dc3920d4ab94af235a6_graph_analytics.json)...
Successfully saved: graph analytics snapshot
Serializing and saving: report diff (C:\Users\DafoO\AppData\Local\Temp\pytest-of-DafoO\pytest-550\test_real_desktop_and_mcp_full0\output\b0g2c_repo_b6b4c0319f054dc3920d4ab94af235a6_report_diff.json)...
Successfully saved: report diff
Serializing and saving: report diff snapshot (C:\Users\DafoO\AppData\Local\Temp\pytest-of-DafoO\pytest-550\test_real_desktop_and_mcp_full0\output\b0g2c_repo_b6b4c0319f054dc3920d4ab94af235a6_20261012_120950\b0g2c_repo_b6b4c0319f054dc3920d4ab94af235a6_report_diff.json)...
Successfully saved: report diff
Serializing and saving: summary report (C:\Users\DafoO\AppData\Local\Temp\pytest-of-DafoO\pytest-550\test_real_desktop_and_mcp_full0\output\b0g2c_repo_b6b4c0319f054dc3920d4ab94af235a6_summary.json)...
Successfully saved: summary report
Serializing and saving: summary snapshot (C:\Users\DafoO\AppData\Local\Temp\pytest-of-DafoO\pytest-550\test_real_desktop_and_mcp_full0\output\b0g2c_repo_b6b4c0319f054dc3920d4ab94af235a6_20261012_120950\b0g2c_repo_b6b4c0319f054dc3920d4ab94af235a6_summary.json)...
Successfully saved: summary snapshot
All reports have been successfully generated and saved.
Initializing incremental cache...
[PROGRESS] Step 7/8: Persisting canonical LIVE snapshot
[PROGRESS] Step 8/8: Finalizing analysis
F
================================== FAILURES ===================================
__ test_real_desktop_and_mcp_full_entrypoints_have_identical_canonical_state __
Desktop/MCP canonical state mismatch: first_field=state.layer_information[{'kind': 'primitive', 'type': 'builtins.str', 'value': 'summary_data'}][{'kind': 'primitive', 'type': 'builtins.str', 'value': 'generated_at'}]; desktop='2026-10-12T12:09:48.838009'; mcp='2026-10-12T12:09:50.608340'; evidence=C:\Users\DafoO\AppData\Local\Temp\pytest-of-DafoO\pytest-550\test_real_desktop_and_mcp_full0\b0g2c_canonical_mismatch_evidence
============================== warnings summary ==============================
.venv\lib\site-packages\fastmcp\server\auth\providers\jwt.py:10
  C:\Temp\Contextor_Repo\.venv\lib\site-packages\fastmcp\server\auth\providers\jwt.py:10: AuthlibDeprecationWarning: authlib.jose module is deprecated, please use joserfc instead.
  It will be compatible before version 2.0.0.
from authlib.jose import JsonWebKey, JsonWebToken

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
=========================== short test summary info ============================
FAILED tests/test_desktop_mcp_canonical_parity.py::test_real_desktop_and_mcp_full_entrypoints_have_identical_canonical_state
1 failed, 1 warning in 9.56s

## TARGETED_TEST_RESULTS
- New deterministic detail regressions: PASS, 8 passed in 0.87s.
- Unchanged real Desktop/MCP full parity test: FAIL, 1 failed in 9.56s at summary_data.generated_at.
- Further reference index/engine and named B0G1/B0G2 regressions: NOT RUN, because the parity test found the next first difference and the task requires stopping.

## PY_COMPILE
PASS. The requested .venv python -m py_compile command for shared.py and the new test file exited 0.

## GIT_DIFF_CHECK
Final post-report git diff --check: PASS, exit 0. Git emitted only a working-copy LF-to-CRLF notice for shared.py. The earlier check against the prior walkthrough found whitespace there; after overwriting it, no source/test/report whitespace errors remain.

## LIVE_REVISION_BEFORE_AFTER
- Before edits: revision 354.
- Desktop watcher event for new test: revision 355, origin=desktop_watcher, status=UPDATED, affected module tests.test_reference_detail_determinism.
- Desktop watcher event for production source: revision 356, origin=desktop_watcher, status=UPDATED, affected_modules total 244 (event sample bounded).
- After edits: revision 356, continuity=continuous, no further revisioned events after 356; resync_required=false and activity_resync_required=false. No manual update_file or full analysis was performed.

## WORKSPACE_SYNC_POSTCHECK
PASS. At revision 356, complete Contextor retrievals for _normalize_references and _detail_sort_key reported workspace_sync=verified and complete source with no partial symbol.

## RESYNC_REQUIRED
false at latest LIVE revision 356.

## RESTART_REQUIRED
YES before later Desktop/MCP live certification of the changed production module. No restart was performed.

## FINAL_VERDICT
B0G2C1_NEXT_MISMATCH_DISCOVERED

The requested deterministic reference normalization patch and its eight targeted regressions pass. The real entrypoint parity run resolves the original direct_calls_detail order difference and stops at summary_data.generated_at, whose persisted timestamp values differ. No further correction, comparator change, or additional regression run was made.

=== contextor/core/reference/shared.py ===
diff --git a/contextor/core/reference/shared.py b/contextor/core/reference/shared.py
index 2f578ad..75a9846 100644
--- a/contextor/core/reference/shared.py
+++ b/contextor/core/reference/shared.py
@@ -13,0 +14,2 @@ import ast
+import json
+from heapq import nsmallest
@@ -589,0 +592,26 @@ def _empty_reference() -> dict[str, list]:
+def _detail_sort_key(detail: dict[str, Any]) -> tuple:
+    """Canonical ordering for source reference evidence."""
+    if not isinstance(detail, dict):
+        raise TypeError(
+            "Reference detail must be a dictionary"
+        )
+
+    line = detail.get("line")
+    canonical_line = (
+        line
+        if isinstance(line, int) and not isinstance(line, bool)
+        else -1
+    )
+
+    return (
+        str(detail.get("module") or ""),
+        canonical_line,
+        json.dumps(
+            detail,
+            sort_keys=True,
+            ensure_ascii=False,
+            separators=(",", ":"),
+        ),
+    )
+
+
@@ -592 +620,2 @@ def _normalize_references(references: dict[str, Any]) -> dict[str, Any]:
-    Deduplicates scalar consumer lists and caps detail lists.
+    Deduplicates scalar consumer lists and caps detail lists with
+    deterministic bounded ordering.
@@ -594,2 +623,2 @@ def _normalize_references(references: dict[str, Any]) -> dict[str, Any]:
-    Detail records remain dictionaries and therefore are not
-    converted through set().
+    Detail records are ordered by module, line, and complete payload
+    before the cap is applied; they are not converted through set().
@@ -603 +632,5 @@ def _normalize_references(references: dict[str, Any]) -> dict[str, Any]:
-                data[key] = values[:MAX_USAGE_DETAILS]
+                data[key] = nsmallest(
+                    MAX_USAGE_DETAILS,
+                    values,
+                    key=_detail_sort_key,
+                )

=== tests/test_reference_detail_determinism.py ===
diff --git a/tests/test_reference_detail_determinism.py b/tests/test_reference_detail_determinism.py
new file mode 100644
index 0000000..7b1fdd0
--- /dev/null
+++ b/tests/test_reference_detail_determinism.py
@@ -0,0 +1,197 @@
+"""Deterministic normalization of bounded reference evidence."""
+
+from __future__ import annotations
+
+import copy
+
+import pytest
+
+from contextor.core.api.api_consumers import extract_api_consumers
+from contextor.core.reference.shared import (
+    MAX_USAGE_DETAILS,
+    _empty_reference,
+    _normalize_references,
+)
+
+
+def _normalize_details(details: list[dict]) -> list[dict]:
+    references = {
+        "pkg.api::service": {
+            "called_by_detail": details,
+        }
+    }
+    _normalize_references(references)
+    return references["pkg.api::service"]["called_by_detail"]
+
+
+def test_reversed_input_order_normalizes_identically() -> None:
+    consumer = {"module": "consumer", "line": 4, "context": None}
+    other = {"module": "other", "line": 3, "context": None}
+
+    forward = _normalize_details(copy.deepcopy([consumer, other]))
+    reverse = _normalize_details(copy.deepcopy([other, consumer]))
+
+    assert forward == reverse
+    assert forward == [consumer, other]
+
+
+def test_cap_membership_is_stable_and_source_records_are_unchanged() -> None:
+    records = [
+        {"module": f"consumer_{index:02d}", "line": index, "context": None}
+        for index in range(MAX_USAGE_DETAILS + 5)
+    ]
+    ascending_input = copy.deepcopy(records)
+    descending_input = copy.deepcopy(list(reversed(records)))
+    ascending_before = copy.deepcopy(ascending_input)
+    descending_before = copy.deepcopy(descending_input)
+
+    ascending_output = _normalize_details(ascending_input)
+    descending_output = _normalize_details(descending_input)
+
+    expected = records[:MAX_USAGE_DETAILS]
+    assert ascending_output == expected
+    assert descending_output == expected
+    assert len(ascending_output) == MAX_USAGE_DETAILS
+    assert len(descending_output) == MAX_USAGE_DETAILS
+    assert ascending_input == ascending_before
+    assert descending_input == descending_before
+
+
+def test_identical_detail_duplicates_are_preserved_up_to_cap() -> None:
+    duplicate = {"module": "consumer", "line": 7, "context": "call"}
+    output = _normalize_details(copy.deepcopy([duplicate] * (MAX_USAGE_DETAILS + 3)))
+
+    assert len(output) == MAX_USAGE_DETAILS
+    assert output == [duplicate] * MAX_USAGE_DETAILS
+
+
+def test_all_detail_families_are_individually_deterministic() -> None:
+    details = {
+        "called_by_detail": [
+            {"module": "z_consumer", "line": 4, "context": None},
+            {"module": "a_consumer", "line": 8, "context": "call"},
+        ],
+        "callback_called_detail": [
+            {"module": "same_callback", "line": 3, "context": "argument"},
+            {"module": "same_callback", "line": None, "context": None, "child": None},
+        ],
+        "event_bound_by_detail": [
+            {"module": "z_event", "line": None, "context": "bind", "reason": None},
+            {"module": "a_event", "line": 2, "context": None},
+        ],
+        "qualified_refs_detail": [
+            {"module": "z_qualified", "line": 6, "context": None},
+            {"module": "a_qualified", "line": 1, "context": "attribute"},
+        ],
+        "inherited_by_detail": [
+            {"module": "z_subclass", "line": 5, "context": None, "child": "Base"},
+            {"module": "a_subclass", "line": None, "context": None, "child": None},
+        ],
+        "called_by_ambiguous_detail": [
+            {"module": "z_ambiguous", "line": None, "context": None, "reason": "dynamic"},
+            {"module": "a_ambiguous", "line": 7, "context": "call", "reason": None},
+        ],
+    }
+    expected = {
+        "called_by_detail": [details["called_by_detail"][1], details["called_by_detail"][0]],
+        "callback_called_detail": [details["callback_called_detail"][1], details["callback_called_detail"][0]],
+        "event_bound_by_detail": [details["event_bound_by_detail"][1], details["event_bound_by_detail"][0]],
+        "qualified_refs_detail": [details["qualified_refs_detail"][1], details["qualified_refs_detail"][0]],
+        "inherited_by_detail": [details["inherited_by_detail"][1], details["inherited_by_detail"][0]],
+        "called_by_ambiguous_detail": [details["called_by_ambiguous_detail"][1], details["called_by_ambiguous_detail"][0]],
+    }
+
+    forward_references = _empty_reference()
+    reverse_references = _empty_reference()
+    for key, records in details.items():
+        forward_references[key] = copy.deepcopy(records)
+        reverse_references[key] = copy.deepcopy(list(reversed(records)))
+    forward = {"target": forward_references}
+    reverse = {"target": reverse_references}
+
+    _normalize_references(forward)
+    _normalize_references(reverse)
+
+    assert forward == reverse
+    assert forward["target"].keys() == _empty_reference().keys()
+    for key, expected_records in expected.items():
+        assert forward["target"][key] == expected_records
+        assert reverse["target"][key] == expected_records
+
+
+def test_scalar_consumer_lists_keep_sorted_deduplicated_behavior() -> None:
+    reference = _empty_reference()
+    reference["called_by"] = ["z_consumer", "a_consumer", "z_consumer"]
+    reference["inherited_by"] = ["subclass_b", "subclass_a", "subclass_b"]
+    references = {"target": reference}
+
+    _normalize_references(references)
+
+    assert reference["called_by"] == ["a_consumer", "z_consumer"]
+    assert reference["inherited_by"] == ["subclass_a", "subclass_b"]
+
+
+def test_api_consumer_details_are_order_independent_without_count_changes() -> None:
+    consumer = {"module": "consumer", "line": 4, "context": None}
+    other = {"module": "other", "line": 3, "context": None}
+
+    def extract(records: list[dict]) -> dict:
+        reference = _empty_reference()
+        reference["called_by"] = ["other", "consumer"]
+        reference["called_by_detail"] = copy.deepcopy(records)
+        normalized = {"pkg.api::service": reference}
+        _normalize_references(normalized)
+        return extract_api_consumers(["pkg.api::service"], normalized)["pkg.api::service"]
+
+    forward = extract([consumer, other])
+    reverse = extract([other, consumer])
+
+    assert forward == reverse
+    assert forward["usage"]["direct_calls_detail"] == [consumer, other]
+    assert forward["consumers"] == ["consumer", "other"]
+    assert forward["consumer_count"] == {
+        "total": 2,
+        "direct_calls": 2,
+        "callbacks": 0,
+        "events": 0,
+        "qualified_refs": 0,
+        "api_imports": 0,
+        "inheritance": 0,
+    }
+
+
+def test_complete_payload_tie_breaker_preserves_extra_json_fields() -> None:
+    first = {
+        "module": "same_consumer",
+        "line": 4,
+        "context": None,
+        "extra": {"value": 1},
+    }
+    second = {
+        "module": "same_consumer",
+        "line": 4,
+        "context": None,
+        "extra": {"value": 2},
+    }
+
+    forward = _normalize_details(copy.deepcopy([second, first]))
+    reverse = _normalize_details(copy.deepcopy([first, second]))
+
+    assert forward == reverse
+    assert forward == [first, second]
+    assert forward[0]["extra"] == {"value": 1}
+    assert forward[1]["extra"] == {"value": 2}
+
+
+def test_non_dictionary_detail_payload_fails_explicitly() -> None:
+    references = {
+        "target": {
+            "called_by_detail": [
+                {"module": "valid", "line": 1, "context": None},
+                "unsupported",
+            ]
+        }
+    }
+
+    with pytest.raises(TypeError, match="Reference detail must be a dictionary"):
+        _normalize_references(references)
