# F2L D1N3b2 Walkthrough

## STATUS

PASS

## FILES_CHANGED

- `contextor/mcp/lineage_response.py`
- `tests/mcp/test_lineage_response.py`

## NAMED_SEMANTIC_OWNER_PROOF

Named representation changes semantic owner_id to the supplied canonical owner name while preserving slots.

## INDEXED_PROOF

Indexed representation requires no name map and includes the artifact resolver contract.

## SYMBOLIC_OCCURRENCE_STABILITY_PROOF

Symbolic qualified identities and occurrence source/local IDs are unchanged.

## SLOT_OPAQUE_PROOF

Semantic slot strings remain identical between representations.

## AUTO_NAMED_PROOF

Auto chooses named when indexed savings are below the existing material-saving threshold.

## AUTO_INDEXED_SAVING_PROOF

Repeated long owner names make auto select indexed when threshold is met.

## AUTO_MISSING_NAME_PROOF

Missing supplied owner names fail closed for named and make auto select indexed diagnostically.

## NO_QUERY_PROOF

Representation operates only on supplied selected facts and supplied name map.

## TESTS_RUN

```text
python -m pytest -q tests/mcp/test_lineage_response.py tests/analysis/test_lineage_query_service.py tests/analysis/test_lineage_query_backend.py: 101 passed in 2.76s
git diff --check -- contextor/mcp/lineage_response.py tests/mcp/test_lineage_response.py: PASS
```

## ACTUAL_DIFF

```diff
warning: in the working copy of 'contextor/mcp/lineage_response.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'tests/mcp/test_lineage_response.py', LF will be replaced by CRLF the next time Git touches it
diff --git a/contextor/mcp/lineage_response.py b/contextor/mcp/lineage_response.py
index 3920a40..a05b0dc 100644
--- a/contextor/mcp/lineage_response.py
+++ b/contextor/mcp/lineage_response.py
@@ -1,13 +1,14 @@
 from __future__ import annotations
 
 from dataclasses import dataclass
+from collections.abc import Mapping
 
 from contextor.core.domain.lineage_facts import MaterializedOccurrenceRef, MaterializedSymbolicRef, SemanticEndpoint
 from contextor.core.lineage_query.service import (
     SYMBOL_LINEAGE_SECTION_ORDER,
     LineageFlowMatch, LineageSurfaceMatch, SelectedSymbolLineageFacts, TargetInterfaceFacts,
 )
-from contextor.mcp.representation import serialized_json_bytes
+from contextor.mcp import representation as mcp_rep
 
 
 SYMBOL_LINEAGE_MODES = ("auto", "preview", "fetch")
@@ -112,4 +113,56 @@ def build_symbol_lineage_payload(selected: SelectedSymbolLineageFacts) -> dict:
 
 def build_symbol_lineage_preview(selected: SelectedSymbolLineageFacts) -> dict:
     payload = build_symbol_lineage_payload(selected)
-    return {"status": "resolved", "mode": "preview", "target": payload["target"], "available_sections": list(selected.selected_sections), "complete": selected.complete, "metadata_consistent": selected.metadata_consistent, "scope_state": selected.facts.scope_state, "candidate_response_bytes": serialized_json_bytes(payload), "section_sizes": {name: {"payload_bytes": serialized_json_bytes(value)} for name, value in payload["sections"].items()}}
+    return {"status": "resolved", "mode": "preview", "target": payload["target"], "available_sections": list(selected.selected_sections), "complete": selected.complete, "metadata_consistent": selected.metadata_consistent, "scope_state": selected.facts.scope_state, "candidate_response_bytes": mcp_rep.serialized_json_bytes(payload), "section_sizes": {name: {"payload_bytes": mcp_rep.serialized_json_bytes(value)} for name, value in payload["sections"].items()}}
+
+
+def _semantic_owner_ids(value: object) -> tuple[str, ...]:
+    owners: set[str] = set()
+    def visit(item: object) -> None:
+        if isinstance(item, dict):
+            if item.get("kind") == "semantic" and isinstance(item.get("owner_id"), str): owners.add(item["owner_id"])
+            for child in item.values(): visit(child)
+        elif isinstance(item, list):
+            for child in item: visit(child)
+    visit(value)
+    return tuple(sorted(owners))
+
+
+def _named_semantic_owners(value: object, owner_names: Mapping[str, str]) -> object:
+    if isinstance(value, list): return [_named_semantic_owners(item, owner_names) for item in value]
+    if not isinstance(value, dict): return value
+    if value.get("kind") == "semantic" and isinstance(value.get("owner_id"), str):
+        result: dict[str, object] = {"kind": "semantic", "owner": owner_names[value["owner_id"]]}
+        if "slot" in value: result["slot"] = value["slot"]
+        return result
+    return {key: _named_semantic_owners(item, owner_names) for key, item in value.items()}
+
+
+def build_symbol_lineage_represented_payload(selected: SelectedSymbolLineageFacts, *, representation: str = "auto", artifact_names: Mapping[str, str] | None = None) -> dict:
+    if not isinstance(selected, SelectedSymbolLineageFacts): raise TypeError("selected must be SelectedSymbolLineageFacts.")
+    if not isinstance(representation, str): raise TypeError("representation must be a string.")
+    requested = representation.strip().lower()
+    if not mcp_rep.is_supported_representation(requested): raise ValueError("representation must be 'auto', 'indexed', or 'named'.")
+    if artifact_names is not None:
+        if not isinstance(artifact_names, Mapping): raise TypeError("artifact_names must be a mapping.")
+        if any(not isinstance(k, str) or not k or not isinstance(v, str) or not v for k, v in artifact_names.items()): raise ValueError("artifact_names must map non-empty artifact IDs to non-empty names.")
+    base = build_symbol_lineage_payload(selected)
+    missing = tuple(owner for owner in _semantic_owner_ids(base) if artifact_names is None or owner not in artifact_names)
+    indexed = dict(base); indexed.update({"representation": "indexed", "requested_representation": requested, "resolver": {"index_kind": "artifact", "resolve_via": "lookup_index_entries"}})
+    indexed_bytes = mcp_rep.serialized_json_bytes(indexed)
+    named = None if missing else _named_semantic_owners(base, artifact_names or {})
+    if named is not None:
+        assert isinstance(named, dict); named.update({"representation": "named", "requested_representation": requested})
+    named_bytes = mcp_rep.serialized_json_bytes(named) if named is not None else None
+    if requested == "named":
+        if named is None: raise ValueError("Named lineage representation unavailable for semantic owners: " + ", ".join(missing))
+        result, reason = named, "explicit_named"
+    elif requested == "indexed": result, reason = indexed, "explicit_indexed"
+    elif named is None: result, reason = indexed, "auto_indexed_named_identity_unavailable"
+    elif named_bytes - indexed_bytes >= mcp_rep.AUTO_NEGOTIATION_MIN_BYTES_SAVED: result, reason = indexed, "auto_indexed_material_saving"
+    else: result, reason = named, "auto_named"
+    decision: dict[str, object] = {"selected": result["representation"], "reason": reason, "indexed_candidate_bytes": indexed_bytes, "named_candidate_bytes": named_bytes, "minimum_auto_saving_bytes": mcp_rep.AUTO_NEGOTIATION_MIN_BYTES_SAVED}
+    if named_bytes is not None: decision["bytes_saved_by_indexed"] = named_bytes - indexed_bytes
+    if missing: decision["missing_named_owners"] = list(missing)
+    result["representation_decision"] = decision
+    return result
diff --git a/tests/mcp/test_lineage_response.py b/tests/mcp/test_lineage_response.py
index cf89085..a39d29c 100644
--- a/tests/mcp/test_lineage_response.py
+++ b/tests/mcp/test_lineage_response.py
@@ -24,6 +24,7 @@ from contextor.mcp.lineage_response import (
     SymbolLineageResponsePlan,
     build_symbol_lineage_payload,
     build_symbol_lineage_preview,
+    build_symbol_lineage_represented_payload,
     plan_symbol_lineage_response,
 )
 
@@ -142,3 +143,42 @@ def test_symbol_lineage_payload_preserves_selected_empty_vs_omitted_and_preview_
     assert preview["candidate_response_bytes"] == serialized_json_bytes(payload)
     for name, value in payload["sections"].items():
         assert preview["section_sizes"][name] == {"payload_bytes": serialized_json_bytes(value)}
+
+
+def test_symbol_lineage_named_and_indexed_representations_preserve_nonsemantic_identities():
+    selected = _selected_lineage_fixture()
+    named = build_symbol_lineage_represented_payload(selected, representation="named", artifact_names={"A17/2": "pkg.mod::handler"})
+    assert named["sections"]["connections"]["incoming"][0]["target"] == {"kind": "semantic", "owner": "pkg.mod::handler", "slot": build_return_slot("A17/2")}
+    assert named["sections"]["bindings"][0]["source"]["kind"] == "symbolic"
+    indexed = build_symbol_lineage_represented_payload(selected, representation="indexed")
+    assert indexed["resolver"] == {"index_kind": "artifact", "resolve_via": "lookup_index_entries"}
+    assert indexed["representation_decision"]["reason"] == "explicit_indexed"
+
+
+def test_symbol_lineage_representation_fails_closed_and_auto_falls_back():
+    selected = _selected_lineage_fixture()
+    with pytest.raises(ValueError, match="Named lineage representation unavailable for semantic owners: A17/2"):
+        build_symbol_lineage_represented_payload(selected, representation="named", artifact_names={})
+    result = build_symbol_lineage_represented_payload(selected, representation="auto", artifact_names={})
+    assert result["representation"] == "indexed"
+    assert result["representation_decision"]["missing_named_owners"] == ["A17/2"]
+
+
+def test_symbol_lineage_auto_named_and_material_indexed_saving():
+    selected = _selected_lineage_fixture()
+    named = build_symbol_lineage_represented_payload(selected, representation="auto", artifact_names={"A17/2": "pkg.mod::handler"})
+    assert named["representation"] == "named"
+    repeated = tuple(replace(selected.connections.incoming[0], flow=replace(selected.connections.incoming[0].flow, local_id=f"incoming-{i}")) for i in range(20))
+    expanded = replace(selected, connections=SymbolLineageConnections(repeated, ()))
+    indexed = build_symbol_lineage_represented_payload(expanded, representation="auto", artifact_names={"A17/2": "pkg." + ("very_long_component." * 8) + "handler"})
+    assert indexed["representation"] == "indexed"
+
+
+def test_symbol_lineage_representation_validates_request_contract():
+    selected = _selected_lineage_fixture()
+    with pytest.raises(TypeError, match="representation must be a string."):
+        build_symbol_lineage_represented_payload(selected, representation=object())
+    with pytest.raises(ValueError, match="representation must be 'auto', 'indexed', or 'named'."):
+        build_symbol_lineage_represented_payload(selected, representation="other")
+    with pytest.raises(TypeError, match="artifact_names must be a mapping."):
+        build_symbol_lineage_represented_payload(selected, representation="named", artifact_names=[])
```
