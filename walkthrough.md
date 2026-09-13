# F2L D1N3b4 Walkthrough

## STATUS

PASS

## FILES_CHANGED

- `contextor/mcp/lineage_response.py`
- `tests/mcp/test_lineage_response.py`

## FRESHNESS_PAYLOAD_PROOF

Supplied read-only `state_freshness` is serialized into the base candidate, neutral preview, represented payload, represented preview, and renderer output only when present.

## REPRESENTED_SIZE_PROOF

The represented-preview test compares its candidate bytes directly with the exact represented indexed fetch candidate containing freshness.

## AUTO_THRESHOLD_FRESHNESS_PROOF

A supplied 5000-character advisory envelope makes an otherwise compact canonical candidate exceed 5120 bytes and returns a represented auto preview whose candidate-byte fields agree exactly.

## NO_MUTATION_PROOF

The payload test retains equality of the supplied freshness mapping to its original shallow copy; response construction uses `dict(state_freshness)`.

## NO_QUERY_PROOF

The response layer receives only `SelectedSymbolLineageFacts`, optional names, and optional JSON-safe freshness. No runtime, backend, state, registry, source, AST, or materialization API is called.

## TESTS_RUN

```text
.\.venv\Scripts\python.exe -m pytest -q tests\mcp\test_lineage_response.py tests\analysis\test_lineage_query_service.py tests\analysis\test_lineage_query_backend.py
113 passed in 3.38s

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
index 405f5a0..c8f60af 100644
--- a/contextor/mcp/lineage_response.py
+++ b/contextor/mcp/lineage_response.py
@@ -110,15 +110,100 @@ def _section_payloads(selected: SelectedSymbolLineageFacts) -> dict[str, object]
     return {name: values[name] for name in selected.selected_sections}
 
 
-def build_symbol_lineage_payload(selected: SelectedSymbolLineageFacts) -> dict:
-    if not isinstance(selected, SelectedSymbolLineageFacts): raise TypeError("selected must be SelectedSymbolLineageFacts.")
+def build_symbol_lineage_payload(
+    selected: SelectedSymbolLineageFacts,
+    *,
+    state_freshness: Mapping[str, object] | None = None,
+) -> dict:
+    if not isinstance(
+        selected,
+        SelectedSymbolLineageFacts,
+    ):
+        raise TypeError(
+            "selected must be SelectedSymbolLineageFacts."
+        )
+    if (
+        state_freshness is not None
+        and not isinstance(state_freshness, Mapping)
+    ):
+        raise TypeError(
+            "state_freshness must be a mapping."
+        )
+
     target = selected.target
-    return {"status": "resolved", "target": {"artifact_id": target.artifact_id, "qualified_name": target.qualified_name, "module": target.module_name, "symbol": target.symbol_name, "resolution": target.resolution}, "selected_sections": list(selected.selected_sections), "complete": selected.complete, "metadata_consistent": selected.metadata_consistent, "scope_state": selected.facts.scope_state, "sections": _section_payloads(selected)}
+    result = {
+        "status": "resolved",
+        "target": {
+            "artifact_id": target.artifact_id,
+            "qualified_name": target.qualified_name,
+            "module": target.module_name,
+            "symbol": target.symbol_name,
+            "resolution": target.resolution,
+        },
+        "selected_sections": list(
+            selected.selected_sections
+        ),
+        "complete": selected.complete,
+        "metadata_consistent": (
+            selected.metadata_consistent
+        ),
+        "scope_state": selected.facts.scope_state,
+    }
 
+    if state_freshness is not None:
+        result["state_freshness"] = dict(
+            state_freshness
+        )
 
-def build_symbol_lineage_preview(selected: SelectedSymbolLineageFacts) -> dict:
-    payload = build_symbol_lineage_payload(selected)
-    return {"status": "resolved", "mode": "preview", "target": payload["target"], "available_sections": list(selected.selected_sections), "complete": selected.complete, "metadata_consistent": selected.metadata_consistent, "scope_state": selected.facts.scope_state, "candidate_response_bytes": mcp_rep.serialized_json_bytes(payload), "section_sizes": {name: {"payload_bytes": mcp_rep.serialized_json_bytes(value)} for name, value in payload["sections"].items()}}
+    result["sections"] = _section_payloads(
+        selected
+    )
+    return result
+
+
+def build_symbol_lineage_preview(
+    selected: SelectedSymbolLineageFacts,
+    *,
+    state_freshness: Mapping[str, object] | None = None,
+) -> dict:
+    payload = build_symbol_lineage_payload(
+        selected,
+        state_freshness=state_freshness,
+    )
+    result = {
+        "status": "resolved",
+        "mode": "preview",
+        "target": payload["target"],
+        "available_sections": list(
+            selected.selected_sections
+        ),
+        "complete": selected.complete,
+        "metadata_consistent": (
+            selected.metadata_consistent
+        ),
+        "scope_state": selected.facts.scope_state,
+        "candidate_response_bytes": (
+            mcp_rep.serialized_json_bytes(
+                payload
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
+            for name, value
+            in payload["sections"].items()
+        },
+    }
+    if "state_freshness" in payload:
+        result["state_freshness"] = payload[
+            "state_freshness"
+        ]
+    return result
 
 
 def _semantic_owner_ids(value: object) -> tuple[str, ...]:
@@ -143,7 +228,13 @@ def _named_semantic_owners(value: object, owner_names: Mapping[str, str]) -> obj
     return {key: _named_semantic_owners(item, owner_names) for key, item in value.items()}
 
 
-def build_symbol_lineage_represented_payload(selected: SelectedSymbolLineageFacts, *, representation: str = "auto", artifact_names: Mapping[str, str] | None = None) -> dict:
+def build_symbol_lineage_represented_payload(
+    selected: SelectedSymbolLineageFacts,
+    *,
+    representation: str = "auto",
+    artifact_names: Mapping[str, str] | None = None,
+    state_freshness: Mapping[str, object] | None = None,
+) -> dict:
     if not isinstance(selected, SelectedSymbolLineageFacts): raise TypeError("selected must be SelectedSymbolLineageFacts.")
     if not isinstance(representation, str): raise TypeError("representation must be a string.")
     requested = representation.strip().lower()
@@ -151,7 +242,10 @@ def build_symbol_lineage_represented_payload(selected: SelectedSymbolLineageFact
     if artifact_names is not None:
         if not isinstance(artifact_names, Mapping): raise TypeError("artifact_names must be a mapping.")
         if any(not isinstance(k, str) or not k or not isinstance(v, str) or not v for k, v in artifact_names.items()): raise ValueError("artifact_names must map non-empty artifact IDs to non-empty names.")
-    base = build_symbol_lineage_payload(selected)
+    base = build_symbol_lineage_payload(
+        selected,
+        state_freshness=state_freshness,
+    )
     missing = tuple(owner for owner in _semantic_owner_ids(base) if artifact_names is None or owner not in artifact_names)
     indexed = dict(base); indexed.update({"representation": "indexed", "requested_representation": requested, "resolver": {"index_kind": "artifact", "resolve_via": "lookup_index_entries"}})
     indexed_bytes = mcp_rep.serialized_json_bytes(indexed)
@@ -179,11 +273,13 @@ def _represented_response_candidate(
     mode: str,
     representation: str,
     artifact_names: Mapping[str, str] | None,
+    state_freshness: Mapping[str, object] | None,
 ) -> dict:
     result = build_symbol_lineage_represented_payload(
         selected,
         representation=representation,
         artifact_names=artifact_names,
+        state_freshness=state_freshness,
     )
     result["mode"] = mode
     return result
@@ -194,6 +290,7 @@ def build_symbol_lineage_represented_preview(
     *,
     representation: str = "auto",
     artifact_names: Mapping[str, str] | None = None,
+    state_freshness: Mapping[str, object] | None = None,
     candidate_mode: str = "fetch",
 ) -> dict:
     if candidate_mode not in {"auto", "fetch"}:
@@ -206,6 +303,7 @@ def build_symbol_lineage_represented_preview(
         mode=candidate_mode,
         representation=representation,
         artifact_names=artifact_names,
+        state_freshness=state_freshness,
     )
     sections = candidate["sections"]
 
@@ -247,6 +345,11 @@ def build_symbol_lineage_represented_preview(
         },
     }
 
+    if "state_freshness" in candidate:
+        result["state_freshness"] = candidate[
+            "state_freshness"
+        ]
+
     if "resolver" in candidate:
         result["resolver"] = candidate["resolver"]
 
@@ -260,6 +363,7 @@ def render_symbol_lineage_response(
     sections: tuple[str, ...] | None = None,
     representation: str = "auto",
     artifact_names: Mapping[str, str] | None = None,
+    state_freshness: Mapping[str, object] | None = None,
     allow_large_output: bool = False,
 ) -> str:
     if not isinstance(
@@ -293,6 +397,7 @@ def render_symbol_lineage_response(
             selected,
             representation=representation,
             artifact_names=artifact_names,
+            state_freshness=state_freshness,
             candidate_mode="fetch",
         )
         serialized = json.dumps(
@@ -319,6 +424,7 @@ def render_symbol_lineage_response(
         mode=plan.mode,
         representation=representation,
         artifact_names=artifact_names,
+        state_freshness=state_freshness,
     )
     candidate_bytes = (
         mcp_rep.serialized_json_bytes(
@@ -336,6 +442,7 @@ def render_symbol_lineage_response(
                 selected,
                 representation=representation,
                 artifact_names=artifact_names,
+                state_freshness=state_freshness,
                 candidate_mode="auto",
             )
         )
diff --git a/tests/mcp/test_lineage_response.py b/tests/mcp/test_lineage_response.py
index 5739464..d127644 100644
--- a/tests/mcp/test_lineage_response.py
+++ b/tests/mcp/test_lineage_response.py
@@ -103,6 +103,24 @@ def _with_empty_selected_sections(selected):
     )
 
 
+def _state_freshness_fixture(
+    *,
+    advisory_warning=None,
+):
+    return {
+        "canonical_state": "fresh",
+        "workspace_sync": "verified",
+        "canonical_revision": 7,
+        "provenance": "live",
+        "families": {
+            "module": "fresh",
+            "graph": "fresh",
+            "lineage": "fresh",
+        },
+        "advisory_warning": advisory_warning,
+    }
+
+
 def test_auto_plans_complete_symbol_candidate_for_size_decision():
     assert plan_symbol_lineage_response(mode=" AUTO ") == SymbolLineageResponsePlan("auto", SYMBOL_LINEAGE_SECTION_ORDER, True, True)
 
@@ -663,3 +681,96 @@ def test_symbol_lineage_renderer_validates_allow_large_output():
             _selected_lineage_fixture(),
             allow_large_output=1,
         )
+
+
+def test_symbol_lineage_payload_preserves_supplied_freshness_without_mutation():
+    selected = _selected_lineage_fixture()
+    freshness = _state_freshness_fixture()
+    original = dict(freshness)
+
+    result = build_symbol_lineage_payload(
+        selected,
+        state_freshness=freshness,
+    )
+
+    assert result["state_freshness"] == freshness
+    assert freshness == original
+
+
+def test_symbol_lineage_represented_preview_sizes_candidate_with_freshness():
+    selected = _selected_lineage_fixture()
+    freshness = _state_freshness_fixture()
+
+    preview = build_symbol_lineage_represented_preview(
+        selected,
+        representation="indexed",
+        state_freshness=freshness,
+        candidate_mode="fetch",
+    )
+    candidate = build_symbol_lineage_represented_payload(
+        selected,
+        representation="indexed",
+        state_freshness=freshness,
+    )
+    candidate["mode"] = "fetch"
+
+    assert preview["state_freshness"] == freshness
+    assert preview["candidate_response_bytes"] == (
+        mcp_rep.serialized_json_bytes(
+            candidate
+        )
+    )
+
+
+def test_symbol_lineage_auto_threshold_includes_freshness_envelope():
+    selected = _with_empty_selected_sections(
+        _selected_lineage_fixture()
+    )
+    freshness = _state_freshness_fixture(
+        advisory_warning="x" * 5000,
+    )
+
+    result = json.loads(
+        render_symbol_lineage_response(
+            selected,
+            mode="auto",
+            representation="indexed",
+            state_freshness=freshness,
+        )
+    )
+
+    assert result["mode"] == "preview"
+    assert result["state_freshness"] == freshness
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
+def test_symbol_lineage_freshness_contract_rejects_non_mapping():
+    selected = _selected_lineage_fixture()
+
+    with pytest.raises(
+        TypeError,
+        match="state_freshness must be a mapping.",
+    ):
+        build_symbol_lineage_payload(
+            selected,
+            state_freshness=[],
+        )
+
+    with pytest.raises(
+        TypeError,
+        match="state_freshness must be a mapping.",
+    ):
+        render_symbol_lineage_response(
+            selected,
+            representation="indexed",
+            state_freshness=[],
+        )
```

