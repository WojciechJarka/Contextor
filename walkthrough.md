# F2L D1O2a Walkthrough

## STATUS

PASS

## FILES_CHANGED

- `contextor/core/lineage_query/live_query.py`
- `tests/analysis/test_lineage_live_query.py`

## EXACT_ID_INDEX_PROOF

Artifact-ID lookup uses only `source_keys_for_owner(owner_id)` and its candidate sources; the test forbids repo-wide `source_keys()`.

## QUALIFIED_SINGLE_SLICE_PROOF

Qualified lookup reads exactly the source slice identified by `state.modules[module].path`; the test forbids iterator use.

## AMBIGUITY_PRESERVATION_PROOF

Duplicate qualified identities with distinct owners are retained in the catalog for later service-level ambiguity handling.

## STALE_FAIL_CLOSED_PROOF

Stale query-index capability raises the prescribed unavailable-or-stale error before lookup.

## NO_REGISTRY_PROOF

The helper imports only canonical backend and IndexCatalog contracts, with no persistent registry or recovery catalog.

## NO_REPO_SCAN_PROOF

Tests fail if full source enumeration is attempted in either exact lookup branch.

## TESTS_RUN

```text
.\.venv\Scripts\python.exe -m pytest -q tests\analysis\test_lineage_live_query.py tests\analysis\test_lineage_query_service.py tests\analysis\test_lineage_query_backend.py
98 passed in 2.40s
```

## ACTUAL_DIFF

```diff
warning: in the working copy of 'contextor/core/lineage_query/live_query.py', LF will be replaced by CRLF the next time Git touches it
diff --git a/contextor/core/lineage_query/live_query.py b/contextor/core/lineage_query/live_query.py
new file mode 100644
index 0000000..7981346
--- /dev/null
+++ b/contextor/core/lineage_query/live_query.py
@@ -0,0 +1,163 @@
+from __future__ import annotations
+
+from collections.abc import Mapping
+
+from contextor.core.lineage_query.backend import (
+    RepositoryStateLineageBackend,
+)
+from contextor.core.report_query import (
+    ARTIFACT_ID_RE,
+    IndexCatalog,
+)
+
+
+_UNAVAILABLE_MESSAGE = (
+    "Canonical lineage target identity catalog "
+    "is unavailable or stale."
+)
+
+
+def _require_exact_identity_capability(
+    backend: RepositoryStateLineageBackend,
+) -> None:
+    metadata = backend.metadata()
+    if (
+        metadata.family_state != "fresh"
+        or metadata.query_index_state != "fresh"
+        or not metadata.semantic_anchor_bindings_complete
+    ):
+        raise ValueError(_UNAVAILABLE_MESSAGE)
+
+
+def _module_source_key(
+    state: object,
+    module_name: str,
+) -> str | None:
+    modules = getattr(state, "modules", {})
+    if not isinstance(modules, Mapping):
+        raise TypeError(
+            "Canonical state modules must be a mapping."
+        )
+
+    module = modules.get(module_name)
+    if module is None:
+        return None
+
+    raw_path = getattr(module, "path", None)
+    if raw_path is None:
+        return None
+
+    source_key = str(raw_path).replace("\\", "/")
+    while source_key.startswith("./"):
+        source_key = source_key[2:]
+
+    return source_key or None
+
+
+def _install_identity(
+    identities: dict[str, str],
+    owner_id: str,
+    qualified_name: str,
+) -> None:
+    existing = identities.get(owner_id)
+    if (
+        existing is not None
+        and existing != qualified_name
+    ):
+        raise ValueError(
+            "Canonical lineage owner identity is inconsistent."
+        )
+    identities[owner_id] = qualified_name
+
+
+def build_live_lineage_target_catalog(
+    state: object,
+    backend: RepositoryStateLineageBackend,
+    query: str,
+) -> IndexCatalog:
+    if not isinstance(
+        backend,
+        RepositoryStateLineageBackend,
+    ):
+        raise TypeError(
+            "backend must be RepositoryStateLineageBackend."
+        )
+    if not isinstance(query, str):
+        raise TypeError("query must be a string.")
+
+    _require_exact_identity_capability(backend)
+
+    raw = query.strip()
+    identities: dict[str, str] = {}
+
+    if not raw:
+        return IndexCatalog(
+            modules={},
+            artifacts={},
+        )
+
+    if ARTIFACT_ID_RE.fullmatch(raw):
+        owner_id = raw[0].upper() + raw[1:]
+        source_keys = backend.source_keys_for_owner(
+            owner_id
+        )
+        for source in backend.iter_sources(
+            source_keys
+        ):
+            for binding in source.semantic_anchors:
+                if binding.owner_id != owner_id:
+                    continue
+                _install_identity(
+                    identities,
+                    owner_id,
+                    binding.qualified_name,
+                )
+
+        return IndexCatalog(
+            modules={},
+            artifacts=dict(sorted(identities.items())),
+        )
+
+    if raw.count("::") != 1:
+        return IndexCatalog(
+            modules={},
+            artifacts={},
+        )
+
+    module_name, symbol_name = raw.split("::", 1)
+    if not module_name or not symbol_name:
+        return IndexCatalog(
+            modules={},
+            artifacts={},
+        )
+
+    source_key = _module_source_key(
+        state,
+        module_name,
+    )
+    if source_key is None:
+        return IndexCatalog(
+            modules={},
+            artifacts={},
+        )
+
+    source = backend.get_source(source_key)
+    if source is None:
+        return IndexCatalog(
+            modules={},
+            artifacts={},
+        )
+
+    for binding in source.semantic_anchors:
+        if binding.qualified_name != raw:
+            continue
+        _install_identity(
+            identities,
+            binding.owner_id,
+            binding.qualified_name,
+        )
+
+    return IndexCatalog(
+        modules={},
+        artifacts=dict(sorted(identities.items())),
+    )
warning: in the working copy of 'tests/analysis/test_lineage_live_query.py', LF will be replaced by CRLF the next time Git touches it
diff --git a/tests/analysis/test_lineage_live_query.py b/tests/analysis/test_lineage_live_query.py
new file mode 100644
index 0000000..1dd32e7
--- /dev/null
+++ b/tests/analysis/test_lineage_live_query.py
@@ -0,0 +1,342 @@
+from types import SimpleNamespace
+
+import pytest
+
+from contextor.core.domain.lineage_facts import (
+    LineageFamilyStatus,
+    MaterializedAnchorFact,
+    MaterializedLineageSourceFacts,
+    MaterializedOccurrenceRef,
+    SemanticAnchorBinding,
+    SourceLineageManifest,
+    SourceSpan,
+)
+from contextor.core.lineage_query.backend import (
+    RepositoryStateLineageBackend,
+)
+from contextor.core.lineage_query.index import (
+    build_lineage_query_indexes,
+)
+from contextor.core.lineage_query.live_query import (
+    build_live_lineage_target_catalog,
+)
+
+
+def _source(
+    source_key,
+    fingerprint,
+    identities,
+):
+    span = SourceSpan(1, 0, 1, 10)
+    anchors = []
+    bindings = []
+
+    for index, (owner_id, qualified_name) in enumerate(
+        identities
+    ):
+        local_id = f"definition-{index}"
+        reference = MaterializedOccurrenceRef(
+            source_key,
+            fingerprint,
+            local_id,
+        )
+        anchors.append(
+            MaterializedAnchorFact(
+                local_id,
+                reference,
+                "function",
+                span,
+            )
+        )
+        bindings.append(
+            SemanticAnchorBinding(
+                owner_id,
+                qualified_name,
+                reference,
+            )
+        )
+
+    return MaterializedLineageSourceFacts(
+        manifest=SourceLineageManifest(
+            source_key=source_key,
+            source_fingerprint=fingerprint,
+            semantic_version="1",
+            status=LineageFamilyStatus.FRESH,
+            anchor_count=len(anchors),
+            flow_count=0,
+            surface_count=0,
+            semantic_anchor_bindings_materialized=True,
+            anchor_ownership_materialized=True,
+            flow_ownership_materialized=True,
+        ),
+        anchors=tuple(sorted(anchors)),
+        flows=(),
+        surfaces=(),
+        semantic_anchors=tuple(sorted(bindings)),
+    )
+
+
+def _fixture():
+    provider = _source(
+        "pkg/mod.py",
+        "a" * 64,
+        (
+            ("A17/2", "pkg.mod::handler"),
+            ("A18/1", "pkg.mod::other"),
+        ),
+    )
+    unrelated = _source(
+        "pkg/other.py",
+        "b" * 64,
+        (
+            ("A99/1", "pkg.other::thing"),
+        ),
+    )
+    sources = {
+        "pkg/mod.py": provider,
+        "pkg/other.py": unrelated,
+    }
+    (
+        owner_source_index,
+        source_owner_index,
+        anchor_complete,
+    ) = build_lineage_query_indexes(sources)
+
+    state = SimpleNamespace(
+        revision=7,
+        provenance="live",
+        modules={
+            "pkg.mod": SimpleNamespace(
+                path="pkg/mod.py",
+            ),
+            "pkg.other": SimpleNamespace(
+                path="pkg/other.py",
+            ),
+        },
+        lineage_facts_state="fresh",
+        lineage_facts_semantic_version="1",
+        lineage_facts_by_source=sources,
+        lineage_owner_source_index=(
+            owner_source_index
+        ),
+        lineage_source_owner_index=(
+            source_owner_index
+        ),
+        lineage_query_index_state="fresh",
+        lineage_semantic_anchor_bindings_complete=(
+            anchor_complete
+        ),
+    )
+    return (
+        state,
+        RepositoryStateLineageBackend(state),
+    )
+
+
+def test_live_target_catalog_resolves_artifact_id_only_through_owner_index(
+    monkeypatch,
+):
+    state, backend = _fixture()
+
+    monkeypatch.setattr(
+        backend,
+        "source_keys",
+        lambda: (_ for _ in ()).throw(
+            AssertionError("repo-wide lineage scan")
+        ),
+    )
+
+    original_iter = backend.iter_sources
+    observed = {}
+
+    def iter_sources(source_keys=None):
+        observed["source_keys"] = source_keys
+        return original_iter(source_keys)
+
+    monkeypatch.setattr(
+        backend,
+        "iter_sources",
+        iter_sources,
+    )
+
+    catalog = build_live_lineage_target_catalog(
+        state,
+        backend,
+        "a17/2",
+    )
+
+    assert catalog.artifacts == {
+        "A17/2": "pkg.mod::handler",
+    }
+    assert observed["source_keys"] == (
+        "pkg/mod.py",
+    )
+
+
+def test_live_target_catalog_resolves_qualified_name_from_one_module_slice_only(
+    monkeypatch,
+):
+    state, backend = _fixture()
+
+    monkeypatch.setattr(
+        backend,
+        "source_keys",
+        lambda: (_ for _ in ()).throw(
+            AssertionError("repo-wide lineage scan")
+        ),
+    )
+    monkeypatch.setattr(
+        backend,
+        "iter_sources",
+        lambda *_args, **_kwargs: (
+            (_ for _ in ()).throw(
+                AssertionError(
+                    "qualified lookup iterated lineage"
+                )
+            )
+        ),
+    )
+
+    original_get = backend.get_source
+    observed = []
+
+    def get_source(source_key):
+        observed.append(source_key)
+        return original_get(source_key)
+
+    monkeypatch.setattr(
+        backend,
+        "get_source",
+        get_source,
+    )
+
+    catalog = build_live_lineage_target_catalog(
+        state,
+        backend,
+        "pkg.mod::handler",
+    )
+
+    assert catalog.artifacts == {
+        "A17/2": "pkg.mod::handler",
+    }
+    assert observed == ["pkg/mod.py"]
+
+
+def test_live_target_catalog_preserves_duplicate_exact_identity_for_service_ambiguity():
+    state, backend = _fixture()
+    source = _source(
+        "pkg/mod.py",
+        "c" * 64,
+        (
+            ("A17/2", "pkg.mod::handler"),
+            ("A18/1", "pkg.mod::handler"),
+        ),
+    )
+    state.lineage_facts_by_source[
+        "pkg/mod.py"
+    ] = source
+    (
+        owner_source_index,
+        source_owner_index,
+        anchor_complete,
+    ) = build_lineage_query_indexes(
+        state.lineage_facts_by_source
+    )
+    state.lineage_owner_source_index = (
+        owner_source_index
+    )
+    state.lineage_source_owner_index = (
+        source_owner_index
+    )
+    state.lineage_semantic_anchor_bindings_complete = (
+        anchor_complete
+    )
+
+    catalog = build_live_lineage_target_catalog(
+        state,
+        backend,
+        "pkg.mod::handler",
+    )
+
+    assert catalog.artifacts == {
+        "A17/2": "pkg.mod::handler",
+        "A18/1": "pkg.mod::handler",
+    }
+
+
+@pytest.mark.parametrize(
+    "query",
+    (
+        "",
+        "handler",
+        "pkg.mod",
+        "pkg.mod::",
+        "::handler",
+        "pkg.mod::handler::extra",
+        "pkg.missing::handler",
+    ),
+)
+def test_live_target_catalog_invalid_or_missing_exact_query_returns_empty_catalog(
+    query,
+):
+    state, backend = _fixture()
+
+    catalog = build_live_lineage_target_catalog(
+        state,
+        backend,
+        query,
+    )
+
+    assert catalog.artifacts == {}
+
+
+def test_live_target_catalog_fails_closed_when_identity_capability_is_not_fresh():
+    state, backend = _fixture()
+    state.lineage_query_index_state = "stale"
+
+    with pytest.raises(
+        ValueError,
+        match=(
+            "Canonical lineage target identity "
+            "catalog is unavailable or stale."
+        ),
+    ):
+        build_live_lineage_target_catalog(
+            state,
+            backend,
+            "pkg.mod::handler",
+        )
+
+
+def test_live_target_catalog_rejects_inconsistent_owner_identity():
+    state, backend = _fixture()
+
+    conflicting = _source(
+        "pkg/duplicate.py",
+        "d" * 64,
+        (
+            ("A17/2", "pkg.other::handler"),
+        ),
+    )
+    state.lineage_facts_by_source[
+        "pkg/duplicate.py"
+    ] = conflicting
+    state.lineage_owner_source_index[
+        "A17/2"
+    ] = (
+        "pkg/duplicate.py",
+        "pkg/mod.py",
+    )
+
+    with pytest.raises(
+        ValueError,
+        match=(
+            "Canonical lineage owner identity "
+            "is inconsistent."
+        ),
+    ):
+        build_live_lineage_target_catalog(
+            state,
+            backend,
+            "A17/2",
+        )
```

