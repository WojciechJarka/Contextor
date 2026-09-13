# F2L D1N3b2 Walkthrough

## STATUS

PASS

## FILES_CHANGED

- `tests/mcp/test_lineage_response.py`

## NAMED_SEMANTIC_OWNER_PROOF

Named changes the canonical semantic endpoint from `owner_id: "A17/2"` to `owner: "pkg.mod::handler"`; indexed preserves `owner_id`.

## SYMBOLIC_STABILITY_PROOF

The test asserts the same symbolic `symbol_kind` and `qualified_name` in named and indexed responses.

## OCCURRENCE_STABILITY_PROOF

The test asserts the same occurrence `source` and `local_id` in named and indexed responses.

## SLOT_OPAQUE_PROOF

The test asserts the same canonical `build_return_slot("A17/2")` string in both representations.

## TARGET_ANCHOR_PROOF

The test asserts top-level `target.artifact_id` and `target.qualified_name` remain `A17/2` and `pkg.mod::handler` in both representations.

## AUTO_NAMED_THRESHOLD_PROOF

The auto-named test asserts `bytes_saved_by_indexed < mcp_rep.AUTO_NEGOTIATION_MIN_BYTES_SAVED` and the same decision threshold.

## AUTO_INDEXED_THRESHOLD_PROOF

The long-owner fixture asserts `bytes_saved_by_indexed >= mcp_rep.AUTO_NEGOTIATION_MIN_BYTES_SAVED`, exact candidate-byte subtraction, and `auto_indexed_material_saving`.

## AUTO_MISSING_NAME_PROOF

Named fails closed with the exact owner diagnostic; auto selects indexed with `auto_indexed_named_identity_unavailable`, `missing_named_owners == ["A17/2"]`, and `named_candidate_bytes is None`.

## TESTS_RUN

```text
.\.venv\Scripts\python.exe -m pytest -q tests\mcp\test_lineage_response.py tests\analysis\test_lineage_query_service.py tests\analysis\test_lineage_query_backend.py
101 passed in 2.58s

.\.venv\Scripts\python.exe -m py_compile tests\mcp\test_lineage_response.py
PASS

git diff --check -- tests/mcp/test_lineage_response.py
PASS
```

## ACTUAL_DIFF

```diff
diff --git a/tests/mcp/test_lineage_response.py b/tests/mcp/test_lineage_response.py
index a39d29c..765cb34 100644
--- a/tests/mcp/test_lineage_response.py
+++ b/tests/mcp/test_lineage_response.py
@@ -19,7 +19,7 @@ from contextor.core.lineage_query.service import (
     SelectedSymbolLineageFacts, SemanticLineageSections, SymbolLineageConnections,
     SymbolLineageFacts, TargetInterfaceFacts,
 )
-from contextor.mcp.representation import serialized_json_bytes
+from contextor.mcp import representation as mcp_rep
 from contextor.mcp.lineage_response import (
     SymbolLineageResponsePlan,
     build_symbol_lineage_payload,
@@ -140,38 +140,210 @@ def test_symbol_lineage_payload_preserves_selected_empty_vs_omitted_and_preview_
     assert preview["available_sections"] == list(SYMBOL_LINEAGE_SECTION_ORDER)
     assert "unresolved_dynamic_boundaries" in preview["section_sizes"]
     assert "surfaces" in preview["section_sizes"]
-    assert preview["candidate_response_bytes"] == serialized_json_bytes(payload)
+    assert preview["candidate_response_bytes"] == mcp_rep.serialized_json_bytes(payload)
     for name, value in payload["sections"].items():
-        assert preview["section_sizes"][name] == {"payload_bytes": serialized_json_bytes(value)}
+        assert preview["section_sizes"][name] == {"payload_bytes": mcp_rep.serialized_json_bytes(value)}
 
 
 def test_symbol_lineage_named_and_indexed_representations_preserve_nonsemantic_identities():
     selected = _selected_lineage_fixture()
-    named = build_symbol_lineage_represented_payload(selected, representation="named", artifact_names={"A17/2": "pkg.mod::handler"})
-    assert named["sections"]["connections"]["incoming"][0]["target"] == {"kind": "semantic", "owner": "pkg.mod::handler", "slot": build_return_slot("A17/2")}
-    assert named["sections"]["bindings"][0]["source"]["kind"] == "symbolic"
-    indexed = build_symbol_lineage_represented_payload(selected, representation="indexed")
-    assert indexed["resolver"] == {"index_kind": "artifact", "resolve_via": "lookup_index_entries"}
-    assert indexed["representation_decision"]["reason"] == "explicit_indexed"
+    named = build_symbol_lineage_represented_payload(
+        selected,
+        representation="named",
+        artifact_names={
+            "A17/2": "pkg.mod::handler",
+        },
+    )
+    indexed = build_symbol_lineage_represented_payload(
+        selected,
+        representation="indexed",
+    )
+
+    named_semantic = named["sections"][
+        "connections"
+    ]["incoming"][0]["target"]
+    indexed_semantic = indexed["sections"][
+        "connections"
+    ]["incoming"][0]["target"]
+
+    assert named_semantic == {
+        "kind": "semantic",
+        "owner": "pkg.mod::handler",
+        "slot": build_return_slot("A17/2"),
+    }
+    assert indexed_semantic == {
+        "kind": "semantic",
+        "owner_id": "A17/2",
+        "slot": build_return_slot("A17/2"),
+    }
+
+    assert (
+        named_semantic["slot"]
+        == indexed_semantic["slot"]
+        == build_return_slot("A17/2")
+    )
+
+    expected_symbolic = {
+        "kind": "symbolic",
+        "symbol_kind": "import",
+        "qualified_name": "pkg.dep::value",
+    }
+    assert (
+        named["sections"]["bindings"][0]["source"]
+        == expected_symbolic
+    )
+    assert (
+        indexed["sections"]["bindings"][0]["source"]
+        == expected_symbolic
+    )
+
+    expected_occurrence = {
+        "kind": "occurrence",
+        "source": "pkg/mod.py",
+        "local_id": "local",
+    }
+    assert (
+        named["sections"]["bindings"][0]["target"]
+        == expected_occurrence
+    )
+    assert (
+        indexed["sections"]["bindings"][0]["target"]
+        == expected_occurrence
+    )
+
+    assert named["target"]["artifact_id"] == "A17/2"
+    assert indexed["target"]["artifact_id"] == "A17/2"
+    assert (
+        named["target"]["qualified_name"]
+        == indexed["target"]["qualified_name"]
+        == "pkg.mod::handler"
+    )
+
+    assert named["representation"] == "named"
+    assert (
+        named["representation_decision"]["reason"]
+        == "explicit_named"
+    )
+    assert "resolver" not in named
+
+    assert indexed["representation"] == "indexed"
+    assert indexed["resolver"] == {
+        "index_kind": "artifact",
+        "resolve_via": "lookup_index_entries",
+    }
+    assert (
+        indexed["representation_decision"]["reason"]
+        == "explicit_indexed"
+    )
 
 
 def test_symbol_lineage_representation_fails_closed_and_auto_falls_back():
     selected = _selected_lineage_fixture()
-    with pytest.raises(ValueError, match="Named lineage representation unavailable for semantic owners: A17/2"):
-        build_symbol_lineage_represented_payload(selected, representation="named", artifact_names={})
-    result = build_symbol_lineage_represented_payload(selected, representation="auto", artifact_names={})
+    with pytest.raises(
+        ValueError,
+        match=(
+            "Named lineage representation unavailable "
+            "for semantic owners: A17/2"
+        ),
+    ):
+        build_symbol_lineage_represented_payload(
+            selected,
+            representation="named",
+            artifact_names={},
+        )
+
+    result = build_symbol_lineage_represented_payload(
+        selected,
+        representation="auto",
+        artifact_names={},
+    )
+
     assert result["representation"] == "indexed"
-    assert result["representation_decision"]["missing_named_owners"] == ["A17/2"]
+    assert (
+        result["representation_decision"]["reason"]
+        == "auto_indexed_named_identity_unavailable"
+    )
+    assert result["representation_decision"][
+        "missing_named_owners"
+    ] == ["A17/2"]
+    assert (
+        result["representation_decision"][
+            "named_candidate_bytes"
+        ]
+        is None
+    )
 
 
 def test_symbol_lineage_auto_named_and_material_indexed_saving():
     selected = _selected_lineage_fixture()
-    named = build_symbol_lineage_represented_payload(selected, representation="auto", artifact_names={"A17/2": "pkg.mod::handler"})
+    named = build_symbol_lineage_represented_payload(
+        selected,
+        representation="auto",
+        artifact_names={
+            "A17/2": "pkg.mod::handler",
+        },
+    )
+
+    named_decision = named["representation_decision"]
     assert named["representation"] == "named"
-    repeated = tuple(replace(selected.connections.incoming[0], flow=replace(selected.connections.incoming[0].flow, local_id=f"incoming-{i}")) for i in range(20))
-    expanded = replace(selected, connections=SymbolLineageConnections(repeated, ()))
-    indexed = build_symbol_lineage_represented_payload(expanded, representation="auto", artifact_names={"A17/2": "pkg." + ("very_long_component." * 8) + "handler"})
+    assert named_decision["reason"] == "auto_named"
+    assert (
+        named_decision["bytes_saved_by_indexed"]
+        < mcp_rep.AUTO_NEGOTIATION_MIN_BYTES_SAVED
+    )
+    assert (
+        named_decision["minimum_auto_saving_bytes"]
+        == mcp_rep.AUTO_NEGOTIATION_MIN_BYTES_SAVED
+    )
+
+    repeated = tuple(
+        replace(
+            selected.connections.incoming[0],
+            flow=replace(
+                selected.connections.incoming[0].flow,
+                local_id=f"incoming-{index:02d}",
+            ),
+        )
+        for index in range(20)
+    )
+    expanded = replace(
+        selected,
+        connections=SymbolLineageConnections(
+            repeated,
+            (),
+        ),
+    )
+    long_name = (
+        "pkg."
+        + ("very_long_component." * 8)
+        + "handler"
+    )
+
+    indexed = build_symbol_lineage_represented_payload(
+        expanded,
+        representation="auto",
+        artifact_names={
+            "A17/2": long_name,
+        },
+    )
+
+    indexed_decision = (
+        indexed["representation_decision"]
+    )
     assert indexed["representation"] == "indexed"
+    assert (
+        indexed_decision["reason"]
+        == "auto_indexed_material_saving"
+    )
+    assert (
+        indexed_decision["bytes_saved_by_indexed"]
+        >= mcp_rep.AUTO_NEGOTIATION_MIN_BYTES_SAVED
+    )
+    assert (
+        indexed_decision["named_candidate_bytes"]
+        - indexed_decision["indexed_candidate_bytes"]
+        == indexed_decision["bytes_saved_by_indexed"]
+    )
 
 
 def test_symbol_lineage_representation_validates_request_contract():
@@ -182,3 +354,17 @@ def test_symbol_lineage_representation_validates_request_contract():
         build_symbol_lineage_represented_payload(selected, representation="other")
     with pytest.raises(TypeError, match="artifact_names must be a mapping."):
         build_symbol_lineage_represented_payload(selected, representation="named", artifact_names=[])
+    with pytest.raises(
+        ValueError,
+        match=(
+            "artifact_names must map non-empty "
+            "artifact IDs to non-empty names."
+        ),
+    ):
+        build_symbol_lineage_represented_payload(
+            selected,
+            representation="named",
+            artifact_names={
+                "A17/2": "",
+            },
+        )
```
