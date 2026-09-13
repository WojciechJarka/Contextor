# F2L D1O2c1 — selected canonical owner-name projection

STATUS: PASS

FILES_CHANGED:
- `contextor/core/lineage_query/live_query.py`
- `tests/analysis/test_lineage_live_query.py`
- `walkthrough.md` (this report; its own diff intentionally excluded)

MODULE_OWNER_ORIGIN_PROOF:
A selected STATE-origin endpoint with owner ID `17/2` resolves only through its exact `SemanticEndpointOrigin.kind == ExtractedSymbolicKind.STATE`, producing `pkg.mod`. No owner-ID-prefix or slot inference is used.

ARTIFACT_OWNER_ORIGIN_PROOF:
A selected non-STATE CALLEE-origin endpoint with owner ID `A18/1` resolves from its exact canonical origin to `pkg.mod::other`.

SELECTED_ONLY_PROOF:
The selected query contains `calls_interfaces` and `state`; an unselected callback endpoint `A99/1` is present in the source slice but is absent from the result.

NO_REPO_SCAN_PROOF:
The focused test replaces `backend.source_keys` and `backend.iter_sources` with failures. The helper passes while calling cached `backend.get_source` exactly once for `pkg/mod.py`.

MISSING_ORIGIN_FAIL_CLOSED_PROOF:
Removing the selected `state-read` origin raises `ValueError: Canonical semantic owner name origin is unavailable.`

CONFLICT_FAIL_CLOSED_PROOF:
Two selected origins resolving `A18/1` to different names raise `ValueError: Canonical semantic owner identity is inconsistent.`

TESTS_RUN:
- `.\\.venv\\Scripts\\python.exe -m pytest -q tests\\analysis\\test_lineage_live_query.py tests\\analysis\\test_lineage_query_service.py tests\\analysis\\test_lineage_query_backend.py tests\\mcp\\test_lineage_response.py` — **139 passed in 3.36s**
- `.\\.venv\\Scripts\\python.exe -m py_compile contextor\\core\\lineage_query\\live_query.py tests\\analysis\\test_lineage_live_query.py` — passed
- `git diff --check -- contextor/core/lineage_query/live_query.py tests/analysis/test_lineage_live_query.py` — passed

RUNTIME_RESTART_REQUIRED: STILL_YES_FROM_D1O1_BUT_DO_NOT_RESTART_YET.

## ACTUAL_DIFF

```diff
warning: in the working copy of 'contextor/core/lineage_query/live_query.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'tests/analysis/test_lineage_live_query.py', LF will be replaced by CRLF the next time Git touches it
diff --git a/contextor/core/lineage_query/live_query.py b/contextor/core/lineage_query/live_query.py
index 349be12..dd952d9 100644
--- a/contextor/core/lineage_query/live_query.py
+++ b/contextor/core/lineage_query/live_query.py
@@ -6,9 +6,16 @@ from collections.abc import Mapping
 from contextor.core.lineage_query.backend import (
     RepositoryStateLineageBackend,
 )
+from contextor.core.domain.lineage_facts import (
+    ExtractedSymbolicKind,
+    SemanticEndpoint,
+    SemanticEndpointRole,
+)
 from contextor.core.lineage_query.service import (
     SYMBOL_LINEAGE_SECTION_ORDER,
+    LineageFlowMatch,
     LineageQueryService,
+    LineageSurfaceMatch,
     LineageTargetResolution,
     SelectedSymbolLineageFacts,
 )
@@ -23,6 +30,13 @@ _UNAVAILABLE_MESSAGE = (
     "is unavailable or stale."
 )

+_OWNER_NAME_ORIGIN_UNAVAILABLE = (
+    "Canonical semantic owner name origin is unavailable."
+)
+_OWNER_NAME_INCONSISTENT = (
+    "Canonical semantic owner identity is inconsistent."
+)
+

 @dataclass(frozen=True)
 class LiveSymbolLineageQueryResult:
@@ -31,6 +45,178 @@ class LiveSymbolLineageQueryResult:
     unavailable_reason: str | None = None


+def _selected_lineage_flow_matches(
+    selected: SelectedSymbolLineageFacts,
+) -> tuple[LineageFlowMatch, ...]:
+    matches: dict[tuple[str, str, str], LineageFlowMatch] = {}
+
+    def add(items: tuple[LineageFlowMatch, ...]) -> None:
+        for match in items:
+            key = (
+                match.source_key,
+                match.source_fingerprint,
+                match.flow.local_id,
+            )
+            existing = matches.get(key)
+            if existing is not None and existing != match:
+                raise ValueError(
+                    "Selected lineage flow identity is inconsistent."
+                )
+            matches[key] = match
+
+    if selected.interface is not None:
+        add(selected.interface.parameter_defaults)
+    if selected.connections is not None:
+        add(selected.connections.incoming)
+        add(selected.connections.outgoing)
+    for name in (
+        "bindings",
+        "parameter_flows",
+        "calls_interfaces",
+        "returns",
+        "state",
+        "callbacks",
+        "unresolved_dynamic_boundaries",
+    ):
+        value = getattr(selected, name)
+        if value is not None:
+            add(value)
+    if selected.surfaces is not None:
+        add(selected.surfaces.flows)
+    return tuple(matches[key] for key in sorted(matches))
+
+
+def _selected_lineage_surface_matches(
+    selected: SelectedSymbolLineageFacts,
+) -> tuple[LineageSurfaceMatch, ...]:
+    if selected.surfaces is None:
+        return ()
+    return tuple(
+        sorted(
+            selected.surfaces.facts,
+            key=lambda match: (
+                match.source_key,
+                match.source_fingerprint,
+                match.surface.local_id,
+            ),
+        )
+    )
+
+
+def _owner_name_from_origin(origin) -> str:
+    if origin.kind is ExtractedSymbolicKind.STATE:
+        return origin.module_name
+    return f"{origin.module_name}::{origin.symbol_name}"
+
+
+def _install_owner_name(
+    owner_names: dict[str, str],
+    owner_id: str,
+    owner_name: str,
+) -> None:
+    existing = owner_names.get(owner_id)
+    if existing is not None and existing != owner_name:
+        raise ValueError(_OWNER_NAME_INCONSISTENT)
+    owner_names[owner_id] = owner_name
+
+
+def build_selected_lineage_owner_names(
+    backend: RepositoryStateLineageBackend,
+    selected: SelectedSymbolLineageFacts,
+) -> dict[str, str]:
+    if not isinstance(backend, RepositoryStateLineageBackend):
+        raise TypeError("backend must be RepositoryStateLineageBackend.")
+    if not isinstance(selected, SelectedSymbolLineageFacts):
+        raise TypeError("selected must be SelectedSymbolLineageFacts.")
+
+    owner_names: dict[str, str] = {}
+    source_cache = {}
+    origin_cache = {}
+
+    def origin_for(
+        source_key: str,
+        source_fingerprint: str,
+        fact_local_id: str,
+        endpoint_role: SemanticEndpointRole,
+    ):
+        source = source_cache.get(source_key)
+        if source is None:
+            source = backend.get_source(source_key)
+            if source is None:
+                raise ValueError(_OWNER_NAME_ORIGIN_UNAVAILABLE)
+            source_cache[source_key] = source
+        if source.manifest.source_fingerprint != source_fingerprint:
+            raise ValueError(_OWNER_NAME_ORIGIN_UNAVAILABLE)
+        cache_key = (
+            source_key,
+            source_fingerprint,
+            fact_local_id,
+            endpoint_role,
+        )
+        cached = origin_cache.get(cache_key)
+        if cached is not None:
+            return cached
+        matches = tuple(
+            origin
+            for origin in source.semantic_endpoint_origins
+            if (
+                origin.fact_local_id == fact_local_id
+                and origin.endpoint_role is endpoint_role
+            )
+        )
+        if len(matches) != 1:
+            raise ValueError(_OWNER_NAME_ORIGIN_UNAVAILABLE)
+        origin_cache[cache_key] = matches[0]
+        return matches[0]
+
+    def resolve(
+        endpoint,
+        *,
+        source_key: str,
+        source_fingerprint: str,
+        fact_local_id: str,
+        endpoint_role: SemanticEndpointRole,
+    ) -> None:
+        if not isinstance(endpoint, SemanticEndpoint):
+            return
+        origin = origin_for(
+            source_key,
+            source_fingerprint,
+            fact_local_id,
+            endpoint_role,
+        )
+        _install_owner_name(
+            owner_names,
+            endpoint.owner_id,
+            _owner_name_from_origin(origin),
+        )
+
+    for match in _selected_lineage_flow_matches(selected):
+        resolve(
+            match.flow.source,
+            source_key=match.source_key,
+            source_fingerprint=match.source_fingerprint,
+            fact_local_id=match.flow.local_id,
+            endpoint_role=SemanticEndpointRole.FLOW_SOURCE,
+        )
+        resolve(
+            match.flow.target,
+            source_key=match.source_key,
+            source_fingerprint=match.source_fingerprint,
+            fact_local_id=match.flow.local_id,
+            endpoint_role=SemanticEndpointRole.FLOW_TARGET,
+        )
+    for match in _selected_lineage_surface_matches(selected):
+        resolve(
+            match.surface.exposed,
+            source_key=match.source_key,
+            source_fingerprint=match.source_fingerprint,
+            fact_local_id=match.surface.local_id,
+            endpoint_role=SemanticEndpointRole.SURFACE_EXPOSED,
+        )
+    return dict(sorted(owner_names.items()))
+
+
 def _require_exact_identity_capability(
     backend: RepositoryStateLineageBackend,
 ) -> None:
diff --git a/tests/analysis/test_lineage_live_query.py b/tests/analysis/test_lineage_live_query.py
index 17fc892..f02a65b 100644
--- a/tests/analysis/test_lineage_live_query.py
+++ b/tests/analysis/test_lineage_live_query.py
@@ -1,15 +1,25 @@
+from dataclasses import replace
 from types import SimpleNamespace
 
 import pytest
 
 from contextor.core.domain.lineage_facts import (
+    ExtractedSymbolicKind,
+    LineageConfidence,
     LineageFamilyStatus,
+    LineageRelation,
     MaterializedAnchorFact,
+    MaterializedFlowFact,
     MaterializedLineageSourceFacts,
     MaterializedOccurrenceRef,
+    ResolutionKind,
+    SemanticEndpoint,
     SemanticAnchorBinding,
+    SemanticEndpointOrigin,
+    SemanticEndpointRole,
     SourceLineageManifest,
     SourceSpan,
+    build_module_global_slot,
 )
 from contextor.core.lineage_query.backend import (
     RepositoryStateLineageBackend,
@@ -19,6 +29,7 @@ from contextor.core.lineage_query.index import (
 )
 from contextor.core.lineage_query.live_query import (
     LiveSymbolLineageQueryResult,
+    build_selected_lineage_owner_names,
     build_live_lineage_target_catalog,
     query_live_symbol_lineage,
 )
@@ -675,3 +686,241 @@ def test_live_symbol_lineage_query_allows_empty_core_selection():
     assert result.selected is not None
     assert result.selected.selected_sections == ()
     assert result.selected.complete is True
+
+
+def _owner_name_projection_fixture():
+    source_key = "pkg/mod.py"
+    fingerprint = "e" * 64
+    span = SourceSpan(1, 0, 1, 10)
+    target_ref = MaterializedOccurrenceRef(
+        source_key, fingerprint, "definition-0"
+    )
+    local_ref = MaterializedOccurrenceRef(
+        source_key, fingerprint, "local"
+    )
+    target_anchor = MaterializedAnchorFact(
+        "definition-0", target_ref, "function", span
+    )
+    target_binding = SemanticAnchorBinding(
+        "A17/2", "pkg.mod::handler", target_ref
+    )
+    state_flow = MaterializedFlowFact(
+        "state-read",
+        SemanticEndpoint(
+            "17/2", build_module_global_slot("17/2", "CACHE")
+        ),
+        local_ref,
+        LineageRelation.READS_STATE,
+        span,
+        ResolutionKind.LEXICAL_EXACT,
+        LineageConfidence.CONFIRMED,
+        owner_local_id="definition-0",
+    )
+    call_flow = MaterializedFlowFact(
+        "call-other",
+        local_ref,
+        SemanticEndpoint("A18/1"),
+        LineageRelation.CALL_RESULT,
+        span,
+        ResolutionKind.CALL_EXACT,
+        LineageConfidence.CONFIRMED,
+        owner_local_id="definition-0",
+    )
+    unselected_flow = MaterializedFlowFact(
+        "callback-hidden",
+        local_ref,
+        SemanticEndpoint("A99/1"),
+        LineageRelation.CALLBACK_INVOKES,
+        span,
+        ResolutionKind.CALL_EXACT,
+        LineageConfidence.CONFIRMED,
+        owner_local_id="definition-0",
+    )
+    origins = (
+        SemanticEndpointOrigin(
+            source_key,
+            fingerprint,
+            "state-read",
+            SemanticEndpointRole.FLOW_SOURCE,
+            ExtractedSymbolicKind.STATE,
+            "pkg.mod",
+            "CACHE",
+        ),
+        SemanticEndpointOrigin(
+            source_key,
+            fingerprint,
+            "call-other",
+            SemanticEndpointRole.FLOW_TARGET,
+            ExtractedSymbolicKind.CALLEE,
+            "pkg.mod",
+            "other",
+        ),
+        SemanticEndpointOrigin(
+            source_key,
+            fingerprint,
+            "callback-hidden",
+            SemanticEndpointRole.FLOW_TARGET,
+            ExtractedSymbolicKind.CALLEE,
+            "pkg.callbacks",
+            "hidden",
+        ),
+    )
+    source = MaterializedLineageSourceFacts(
+        manifest=SourceLineageManifest(
+            source_key=source_key,
+            source_fingerprint=fingerprint,
+            semantic_version="1",
+            status=LineageFamilyStatus.FRESH,
+            anchor_count=1,
+            flow_count=3,
+            surface_count=0,
+            semantic_anchor_bindings_materialized=True,
+            anchor_ownership_materialized=True,
+            flow_ownership_materialized=True,
+        ),
+        anchors=(target_anchor,),
+        flows=tuple(sorted((
+            state_flow, call_flow, unselected_flow,
+        ))),
+        surfaces=(),
+        semantic_endpoint_origins=tuple(sorted(origins)),
+        semantic_anchors=(target_binding,),
+    )
+    sources = {source_key: source}
+    (
+        owner_source_index,
+        source_owner_index,
+        anchor_complete,
+    ) = build_lineage_query_indexes(sources)
+    state = SimpleNamespace(
+        revision=11,
+        provenance="live",
+        modules={"pkg.mod": SimpleNamespace(path=source_key)},
+        lineage_facts_state="fresh",
+        lineage_facts_semantic_version="1",
+        lineage_facts_by_source=sources,
+        lineage_owner_source_index=owner_source_index,
+        lineage_source_owner_index=source_owner_index,
+        lineage_query_index_state="fresh",
+        lineage_semantic_anchor_bindings_complete=anchor_complete,
+    )
+    backend = RepositoryStateLineageBackend(state)
+    result = query_live_symbol_lineage(
+        state, "A17/2", ("calls_interfaces", "state")
+    )
+    assert result.resolution.status == "resolved"
+    assert result.selected is not None
+    return state, backend, result.selected
+
+
+def test_selected_owner_names_use_canonical_origins_for_module_and_artifact_owners_only(
+    monkeypatch,
+):
+    _state, backend, selected = _owner_name_projection_fixture()
+    monkeypatch.setattr(
+        backend,
+        "source_keys",
+        lambda: (_ for _ in ()).throw(
+            AssertionError("owner-name projection scanned lineage")
+        ),
+    )
+    monkeypatch.setattr(
+        backend,
+        "iter_sources",
+        lambda *_args, **_kwargs: (
+            (_ for _ in ()).throw(
+                AssertionError("owner-name projection iterated lineage")
+            )
+        ),
+    )
+    original_get = backend.get_source
+    observed = []
+
+    def get_source(source_key):
+        observed.append(source_key)
+        return original_get(source_key)
+
+    monkeypatch.setattr(backend, "get_source", get_source)
+    owner_names = build_selected_lineage_owner_names(backend, selected)
+
+    assert owner_names == {
+        "17/2": "pkg.mod",
+        "A18/1": "pkg.mod::other",
+    }
+    assert "A99/1" not in owner_names
+    assert observed == ["pkg/mod.py"]
+
+
+def test_selected_owner_names_fail_closed_when_selected_semantic_origin_is_missing():
+    state, _backend, selected = _owner_name_projection_fixture()
+    source = state.lineage_facts_by_source["pkg/mod.py"]
+    state.lineage_facts_by_source["pkg/mod.py"] = replace(
+        source,
+        semantic_endpoint_origins=tuple(
+            origin
+            for origin in source.semantic_endpoint_origins
+            if origin.fact_local_id != "state-read"
+        ),
+    )
+    backend = RepositoryStateLineageBackend(state)
+
+    with pytest.raises(
+        ValueError,
+        match="Canonical semantic owner name origin is unavailable.",
+    ):
+        build_selected_lineage_owner_names(backend, selected)
+
+
+def test_selected_owner_names_reject_conflicting_canonical_name_for_same_owner():
+    state, _backend, _selected = _owner_name_projection_fixture()
+    source = state.lineage_facts_by_source["pkg/mod.py"]
+    span = SourceSpan(2, 0, 2, 10)
+    local_ref = MaterializedOccurrenceRef(
+        "pkg/mod.py", "e" * 64, "local-conflict"
+    )
+    conflict_flow = MaterializedFlowFact(
+        "call-conflict",
+        local_ref,
+        SemanticEndpoint("A18/1"),
+        LineageRelation.CALL_RESULT,
+        span,
+        ResolutionKind.CALL_EXACT,
+        LineageConfidence.CONFIRMED,
+        owner_local_id="definition-0",
+    )
+    conflict_origin = SemanticEndpointOrigin(
+        "pkg/mod.py",
+        "e" * 64,
+        "call-conflict",
+        SemanticEndpointRole.FLOW_TARGET,
+        ExtractedSymbolicKind.CALLEE,
+        "pkg.other",
+        "other",
+    )
+    state.lineage_facts_by_source["pkg/mod.py"] = replace(
+        source,
+        manifest=replace(source.manifest, flow_count=4),
+        flows=tuple(sorted((*source.flows, conflict_flow))),
+        semantic_endpoint_origins=tuple(
+            sorted((*source.semantic_endpoint_origins, conflict_origin))
+        ),
+    )
+    (
+        owner_source_index,
+        source_owner_index,
+        anchor_complete,
+    ) = build_lineage_query_indexes(state.lineage_facts_by_source)
+    state.lineage_owner_source_index = owner_source_index
+    state.lineage_source_owner_index = source_owner_index
+    state.lineage_semantic_anchor_bindings_complete = anchor_complete
+    result = query_live_symbol_lineage(
+        state, "A17/2", ("calls_interfaces",)
+    )
+    assert result.selected is not None
+    backend = RepositoryStateLineageBackend(state)
+
+    with pytest.raises(
+        ValueError,
+        match="Canonical semantic owner identity is inconsistent.",
+    ):
+        build_selected_lineage_owner_names(backend, result.selected)
```
