# F2L D1N3b3 Walkthrough

## STATUS

PASS

## FILES_CHANGED

- `contextor/mcp/lineage_response.py`
- `tests/mcp/test_lineage_response.py`

## AUTO_FULL_PROOF

An empty canonical-section fixture produces an indexed auto candidate at or below 5120 bytes and returns the full `mode: "auto"` payload.

## AUTO_PREVIEW_PROOF

A 30-connection full canonical candidate exceeds 5120 bytes and deterministically returns a representation-aware preview with matching `candidate_response_bytes` and `auto_fetch.decision: "preview"`.

## REPRESENTED_PREVIEW_SIZE_PROOF

Explicit named preview reports bytes for the exact represented fetch candidate and every represented section; it does not include `sections`.

## FETCH_SELECTION_PROOF

Fetch accepts only the supplied canonicalized explicit section selection and returns exactly `interface` and `connections`.

## PLAN_MISMATCH_PROOF

A mismatch between supplied selected sections and the response plan fails closed with the required ValueError.

## OUTPUT_GUARD_PROOF

An 80-connection explicit fetch returns the existing 15 KiB confirmation response unless `allow_large_output=True`, which returns the full payload.

## AUTO_BEFORE_GUARD_PROOF

The 80-connection auto candidate returns a resolved preview before the 15 KiB guard can return `confirmation_required`.

## NO_QUERY_PROOF

Renderer helpers operate solely on supplied `SelectedSymbolLineageFacts` and an optional supplied artifact-name map; no query, backend, state, registry, source, AST, or materialization APIs are invoked.

## TESTS_RUN

```text
.\.venv\Scripts\python.exe -m pytest -q tests\mcp\test_lineage_response.py tests\analysis\test_lineage_query_service.py tests\analysis\test_lineage_query_backend.py
109 passed in 2.35s

.\.venv\Scripts\python.exe -m py_compile contextor\mcp\lineage_response.py tests\mcp\test_lineage_response.py
PASS

git diff --check -- contextor/mcp/lineage_response.py tests/mcp/test_lineage_response.py
PASS
```

## ACTUAL_DIFF

```diff
warning: in the working copy of 'contextor/mcp/lineage_response.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'tests/mcp/test_lineage_response.py', LF will be replaced by CRLF the next time Git touches it
diff --git a/contextor/mcp/lineage_response.py b/contextor/mcp/lineage_response.py
index a05b0dc..405f5a0 100644
--- a/contextor/mcp/lineage_response.py
+++ b/contextor/mcp/lineage_response.py
@@ -1,5 +1,6 @@
 from __future__ import annotations
 
+import json
 from dataclasses import dataclass
 from collections.abc import Mapping
 
@@ -9,9 +10,13 @@ from contextor.core.lineage_query.service import (
     LineageFlowMatch, LineageSurfaceMatch, SelectedSymbolLineageFacts, TargetInterfaceFacts,
 )
 from contextor.mcp import representation as mcp_rep
+from contextor.mcp.output_guard import (
+    guard_large_output,
+)
 
 
 SYMBOL_LINEAGE_MODES = ("auto", "preview", "fetch")
+SYMBOL_LINEAGE_AUTO_FETCH_THRESHOLD_BYTES = 5120
 
 
 @dataclass(frozen=True)
@@ -166,3 +171,216 @@ def build_symbol_lineage_represented_payload(selected: SelectedSymbolLineageFact
     if missing: decision["missing_named_owners"] = list(missing)
     result["representation_decision"] = decision
     return result
+
+
+def _represented_response_candidate(
+    selected: SelectedSymbolLineageFacts,
+    *,
+    mode: str,
+    representation: str,
+    artifact_names: Mapping[str, str] | None,
+) -> dict:
+    result = build_symbol_lineage_represented_payload(
+        selected,
+        representation=representation,
+        artifact_names=artifact_names,
+    )
+    result["mode"] = mode
+    return result
+
+
+def build_symbol_lineage_represented_preview(
+    selected: SelectedSymbolLineageFacts,
+    *,
+    representation: str = "auto",
+    artifact_names: Mapping[str, str] | None = None,
+    candidate_mode: str = "fetch",
+) -> dict:
+    if candidate_mode not in {"auto", "fetch"}:
+        raise ValueError(
+            "candidate_mode must be 'auto' or 'fetch'."
+        )
+
+    candidate = _represented_response_candidate(
+        selected,
+        mode=candidate_mode,
+        representation=representation,
+        artifact_names=artifact_names,
+    )
+    sections = candidate["sections"]
+
+    result = {
+        "status": "resolved",
+        "mode": "preview",
+        "target": candidate["target"],
+        "available_sections": list(
+            selected.selected_sections
+        ),
+        "complete": selected.complete,
+        "metadata_consistent": (
+            selected.metadata_consistent
+        ),
+        "scope_state": selected.facts.scope_state,
+        "representation": candidate[
+            "representation"
+        ],
+        "requested_representation": candidate[
+            "requested_representation"
+        ],
+        "representation_decision": candidate[
+            "representation_decision"
+        ],
+        "candidate_response_bytes": (
+            mcp_rep.serialized_json_bytes(
+                candidate
+            )
+        ),
+        "section_sizes": {
+            name: {
+                "payload_bytes": (
+                    mcp_rep.serialized_json_bytes(
+                        value
+                    )
+                ),
+            }
+            for name, value in sections.items()
+        },
+    }
+
+    if "resolver" in candidate:
+        result["resolver"] = candidate["resolver"]
+
+    return result
+
+
+def render_symbol_lineage_response(
+    selected: SelectedSymbolLineageFacts,
+    *,
+    mode: str = "auto",
+    sections: tuple[str, ...] | None = None,
+    representation: str = "auto",
+    artifact_names: Mapping[str, str] | None = None,
+    allow_large_output: bool = False,
+) -> str:
+    if not isinstance(
+        selected,
+        SelectedSymbolLineageFacts,
+    ):
+        raise TypeError(
+            "selected must be SelectedSymbolLineageFacts."
+        )
+    if not isinstance(allow_large_output, bool):
+        raise TypeError(
+            "allow_large_output must be a boolean."
+        )
+
+    plan = plan_symbol_lineage_response(
+        mode=mode,
+        sections=sections,
+    )
+
+    if (
+        selected.selected_sections
+        != plan.candidate_sections
+    ):
+        raise ValueError(
+            "selected sections do not match "
+            "the response plan."
+        )
+
+    if plan.mode == "preview":
+        result = build_symbol_lineage_represented_preview(
+            selected,
+            representation=representation,
+            artifact_names=artifact_names,
+            candidate_mode="fetch",
+        )
+        serialized = json.dumps(
+            result,
+            indent=2,
+            ensure_ascii=False,
+        )
+        return guard_large_output(
+            serialized,
+            allow_large_output=(
+                allow_large_output
+            ),
+            requested_count=len(
+                selected.selected_sections
+            ),
+            retry_instruction=(
+                "Retry preview with "
+                "allow_large_output=true."
+            ),
+        )
+
+    candidate = _represented_response_candidate(
+        selected,
+        mode=plan.mode,
+        representation=representation,
+        artifact_names=artifact_names,
+    )
+    candidate_bytes = (
+        mcp_rep.serialized_json_bytes(
+            candidate
+        )
+    )
+
+    if (
+        plan.mode == "auto"
+        and candidate_bytes
+        > SYMBOL_LINEAGE_AUTO_FETCH_THRESHOLD_BYTES
+    ):
+        preview = (
+            build_symbol_lineage_represented_preview(
+                selected,
+                representation=representation,
+                artifact_names=artifact_names,
+                candidate_mode="auto",
+            )
+        )
+        preview["auto_fetch"] = {
+            "threshold_bytes": (
+                SYMBOL_LINEAGE_AUTO_FETCH_THRESHOLD_BYTES
+            ),
+            "candidate_response_bytes": (
+                candidate_bytes
+            ),
+            "decision": "preview",
+        }
+        serialized = json.dumps(
+            preview,
+            indent=2,
+            ensure_ascii=False,
+        )
+        return guard_large_output(
+            serialized,
+            allow_large_output=(
+                allow_large_output
+            ),
+            requested_count=len(
+                selected.selected_sections
+            ),
+            retry_instruction=(
+                "Retry preview with "
+                "allow_large_output=true."
+            ),
+        )
+
+    serialized = json.dumps(
+        candidate,
+        indent=2,
+        ensure_ascii=False,
+    )
+
+    return guard_large_output(
+        serialized,
+        allow_large_output=allow_large_output,
+        requested_count=len(
+            selected.selected_sections
+        ),
+        retry_instruction=(
+            "Retry with fewer lineage sections "
+            "or allow_large_output=true."
+        ),
+    )
diff --git a/tests/mcp/test_lineage_response.py b/tests/mcp/test_lineage_response.py
index 765cb34..5739464 100644
--- a/tests/mcp/test_lineage_response.py
+++ b/tests/mcp/test_lineage_response.py
@@ -21,11 +21,14 @@ from contextor.core.lineage_query.service import (
 )
 from contextor.mcp import representation as mcp_rep
 from contextor.mcp.lineage_response import (
+    SYMBOL_LINEAGE_AUTO_FETCH_THRESHOLD_BYTES,
     SymbolLineageResponsePlan,
     build_symbol_lineage_payload,
     build_symbol_lineage_preview,
     build_symbol_lineage_represented_payload,
+    build_symbol_lineage_represented_preview,
     plan_symbol_lineage_response,
+    render_symbol_lineage_response,
 )
 
 
@@ -55,6 +58,51 @@ def _selected_lineage_fixture():
     return SelectedSymbolLineageFacts(facts, SYMBOL_LINEAGE_SECTION_ORDER, interface, SymbolLineageConnections((incoming,), ()), (binding_flow, dynamic_flow), (), (), (), (), (), LineageSurfaceSection((), (surface_match,)), (dynamic_flow,))
 
 
+def _with_repeated_connections(
+    selected,
+    count,
+):
+    template = selected.connections.incoming[0]
+    repeated = tuple(
+        replace(
+            template,
+            flow=replace(
+                template.flow,
+                local_id=f"incoming-{index:03d}",
+            ),
+        )
+        for index in range(count)
+    )
+    return replace(
+        selected,
+        connections=SymbolLineageConnections(
+            repeated,
+            (),
+        ),
+    )
+
+
+def _with_empty_selected_sections(selected):
+    return replace(
+        selected,
+        interface=replace(
+            selected.interface,
+            definitions=(),
+            descriptors=(),
+            parameter_defaults=(),
+        ),
+        connections=SymbolLineageConnections((), ()),
+        bindings=(),
+        parameter_flows=(),
+        calls_interfaces=(),
+        returns=(),
+        state=(),
+        callbacks=(),
+        surfaces=LineageSurfaceSection((), ()),
+        unresolved_dynamic_boundaries=(),
+    )
+
+
 def test_auto_plans_complete_symbol_candidate_for_size_decision():
     assert plan_symbol_lineage_response(mode=" AUTO ") == SymbolLineageResponsePlan("auto", SYMBOL_LINEAGE_SECTION_ORDER, True, True)
 
@@ -368,3 +416,250 @@ def test_symbol_lineage_representation_validates_request_contract():
                 "A17/2": "",
             },
         )
+
+
+def test_symbol_lineage_auto_returns_full_payload_below_threshold():
+    selected = _with_empty_selected_sections(
+        _selected_lineage_fixture()
+    )
+
+    rendered = render_symbol_lineage_response(
+        selected,
+        mode="auto",
+        representation="indexed",
+    )
+    result = json.loads(rendered)
+
+    assert result["status"] == "resolved"
+    assert result["mode"] == "auto"
+    assert result["representation"] == "indexed"
+    assert "sections" in result
+    assert "auto_fetch" not in result
+    assert (
+        mcp_rep.serialized_json_bytes(result)
+        <= SYMBOL_LINEAGE_AUTO_FETCH_THRESHOLD_BYTES
+    )
+
+
+def test_symbol_lineage_auto_falls_back_to_exact_representation_aware_preview():
+    selected = _with_repeated_connections(
+        _selected_lineage_fixture(),
+        30,
+    )
+
+    rendered = render_symbol_lineage_response(
+        selected,
+        mode="auto",
+        representation="indexed",
+    )
+    result = json.loads(rendered)
+
+    assert result["status"] == "resolved"
+    assert result["mode"] == "preview"
+    assert result["representation"] == "indexed"
+    assert "sections" not in result
+    assert result["auto_fetch"]["decision"] == "preview"
+    assert result["auto_fetch"]["threshold_bytes"] == (
+        SYMBOL_LINEAGE_AUTO_FETCH_THRESHOLD_BYTES
+    )
+    assert (
+        result["auto_fetch"]["candidate_response_bytes"]
+        > SYMBOL_LINEAGE_AUTO_FETCH_THRESHOLD_BYTES
+    )
+    assert (
+        result["candidate_response_bytes"]
+        == result["auto_fetch"][
+            "candidate_response_bytes"
+        ]
+    )
+
+
+def test_symbol_lineage_explicit_preview_sizes_exact_represented_fetch_candidate():
+    selected = _selected_lineage_fixture()
+    names = {
+        "A17/2": "pkg.mod::handler",
+    }
+
+    preview = build_symbol_lineage_represented_preview(
+        selected,
+        representation="named",
+        artifact_names=names,
+        candidate_mode="fetch",
+    )
+    candidate = build_symbol_lineage_represented_payload(
+        selected,
+        representation="named",
+        artifact_names=names,
+    )
+    candidate["mode"] = "fetch"
+
+    assert preview["mode"] == "preview"
+    assert preview["representation"] == "named"
+    assert "sections" not in preview
+    assert preview["candidate_response_bytes"] == (
+        mcp_rep.serialized_json_bytes(
+            candidate
+        )
+    )
+    for name, value in candidate[
+        "sections"
+    ].items():
+        assert preview["section_sizes"][name] == {
+            "payload_bytes": (
+                mcp_rep.serialized_json_bytes(
+                    value
+                )
+            )
+        }
+
+
+def test_symbol_lineage_fetch_returns_only_explicit_selected_sections():
+    selected = _selected_lineage_fixture()
+    reduced = replace(
+        selected,
+        selected_sections=(
+            "interface",
+            "connections",
+        ),
+        bindings=None,
+        parameter_flows=None,
+        calls_interfaces=None,
+        returns=None,
+        state=None,
+        callbacks=None,
+        surfaces=None,
+        unresolved_dynamic_boundaries=None,
+    )
+
+    rendered = render_symbol_lineage_response(
+        reduced,
+        mode="fetch",
+        sections=(
+            "connections",
+            "interface",
+        ),
+        representation="indexed",
+    )
+    result = json.loads(rendered)
+
+    assert result["status"] == "resolved"
+    assert result["mode"] == "fetch"
+    assert result["selected_sections"] == [
+        "interface",
+        "connections",
+    ]
+    assert tuple(result["sections"]) == (
+        "interface",
+        "connections",
+    )
+
+
+def test_symbol_lineage_renderer_fails_closed_on_selection_plan_mismatch():
+    selected = _selected_lineage_fixture()
+
+    with pytest.raises(
+        ValueError,
+        match=(
+            "selected sections do not match "
+            "the response plan."
+        ),
+    ):
+        render_symbol_lineage_response(
+            selected,
+            mode="fetch",
+            sections=("interface",),
+            representation="indexed",
+        )
+
+
+def test_symbol_lineage_fetch_uses_existing_large_output_guard():
+    selected = _with_repeated_connections(
+        _selected_lineage_fixture(),
+        80,
+    )
+    reduced = replace(
+        selected,
+        selected_sections=("connections",),
+        interface=None,
+        bindings=None,
+        parameter_flows=None,
+        calls_interfaces=None,
+        returns=None,
+        state=None,
+        callbacks=None,
+        surfaces=None,
+        unresolved_dynamic_boundaries=None,
+    )
+
+    guarded = json.loads(
+        render_symbol_lineage_response(
+            reduced,
+            mode="fetch",
+            sections=("connections",),
+            representation="indexed",
+        )
+    )
+
+    assert guarded["status"] == (
+        "confirmation_required"
+    )
+    assert guarded["warning_threshold_bytes"] == (
+        15 * 1024
+    )
+    assert guarded["retry"] == {
+        "allow_large_output": True,
+    }
+
+    full = json.loads(
+        render_symbol_lineage_response(
+            reduced,
+            mode="fetch",
+            sections=("connections",),
+            representation="indexed",
+            allow_large_output=True,
+        )
+    )
+
+    assert full["status"] == "resolved"
+    assert full["mode"] == "fetch"
+    assert "sections" in full
+    assert (
+        mcp_rep.serialized_json_bytes(full)
+        > 15 * 1024
+    )
+
+
+def test_symbol_lineage_auto_progressive_disclosure_precedes_large_output_guard():
+    selected = _with_repeated_connections(
+        _selected_lineage_fixture(),
+        80,
+    )
+
+    result = json.loads(
+        render_symbol_lineage_response(
+            selected,
+            mode="auto",
+            representation="indexed",
+        )
+    )
+
+    assert result["status"] == "resolved"
+    assert result["mode"] == "preview"
+    assert "sections" not in result
+    assert result["auto_fetch"]["decision"] == "preview"
+    assert result["status"] != (
+        "confirmation_required"
+    )
+
+
+def test_symbol_lineage_renderer_validates_allow_large_output():
+    with pytest.raises(
+        TypeError,
+        match=(
+            "allow_large_output must be a boolean."
+        ),
+    ):
+        render_symbol_lineage_response(
+            _selected_lineage_fixture(),
+            allow_large_output=1,
+        )
```

