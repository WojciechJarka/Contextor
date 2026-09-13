# F2L D1C — exact-only lineage target resolution

## STATUS

PASS

Dodano `LineageQueryService.resolve_target` z exact-only resolution dla aktywnych artifact identities: syntaktyczny artifact ID oraz case-sensitive `module::symbol`. Brakujący ID kończy się `not_found`; duplicate active identity kończy się `ambiguous`; recovery catalog, plain leaf, fuzzy i lineage slices nie są używane.

## FILES_CHANGED

- `contextor/core/lineage_query/service.py`
- `contextor/core/lineage_query/__init__.py`
- `tests/analysis/test_lineage_query_service.py`
- `walkthrough.md` — raport tasku; jego własny diff nie jest częścią `ACTUAL_DIFF`.

## TESTS_RUN

| Command | Result |
|---|---|
| `.\\.venv\\Scripts\\python.exe -m pytest -q tests/analysis/test_lineage_query_service.py tests/analysis/test_lineage_query_backend.py` | PASS — `20 passed in 0.91s` |
| `.\\.venv\\Scripts\\python.exe -m py_compile contextor/core/lineage_query/service.py contextor/core/lineage_query/__init__.py` | PASS |
| `git diff --no-index --check -- /dev/null contextor/core/lineage_query/service.py` | PASS — bez błędów whitespace; exit `1` oczekiwany dla nowego pliku porównywanego z `/dev/null` |
| `git diff --no-index --check -- /dev/null contextor/core/lineage_query/__init__.py` | PASS — bez błędów whitespace; exit `1` oczekiwany dla nowego pliku porównywanego z `/dev/null` |
| `git diff --no-index --check -- /dev/null tests/analysis/test_lineage_query_service.py` | PASS — bez błędów whitespace; exit `1` oczekiwany dla nowego pliku porównywanego z `/dev/null` |

## ACTUAL_DIFF

```diff
diff --git a/contextor/core/lineage_query/service.py b/contextor/core/lineage_query/service.py
new file mode 100644
index 0000000..cf28a2a
--- /dev/null
+++ b/contextor/core/lineage_query/service.py
@@ -0,0 +1,133 @@
+from __future__ import annotations
+
+from dataclasses import dataclass
+
+from contextor.core.lineage_query.backend import CanonicalLineageBackend
+from contextor.core.report_query import ARTIFACT_ID_RE, IndexCatalog
+
+
+@dataclass(frozen=True)
+class ResolvedLineageTarget:
+    artifact_id: str
+    qualified_name: str
+    module_name: str
+    symbol_name: str
+    resolution: str
+
+
+@dataclass(frozen=True)
+class LineageTargetResolution:
+    status: str
+    query: str
+    target: ResolvedLineageTarget | None = None
+    candidates: tuple[ResolvedLineageTarget, ...] = ()
+
+
+class LineageQueryService:
+    def __init__(
+        self,
+        backend: CanonicalLineageBackend,
+        catalog: IndexCatalog,
+    ) -> None:
+        if not isinstance(backend, CanonicalLineageBackend):
+            raise TypeError("backend must implement CanonicalLineageBackend.")
+        if not isinstance(catalog, IndexCatalog):
+            raise TypeError("catalog must be IndexCatalog.")
+        self._backend = backend
+        self._catalog = catalog
+
+    def resolve_target(self, query: str) -> LineageTargetResolution:
+        if not isinstance(query, str):
+            raise TypeError("query must be a string.")
+
+        raw = query.strip()
+        if not raw:
+            return LineageTargetResolution(
+                status="invalid",
+                query=raw,
+            )
+
+        if ARTIFACT_ID_RE.fullmatch(raw):
+            artifact_id = raw[0].upper() + raw[1:]
+            qualified_name = self._catalog.artifacts.get(artifact_id)
+            if qualified_name is None:
+                return LineageTargetResolution(
+                    status="not_found",
+                    query=raw,
+                )
+            return LineageTargetResolution(
+                status="resolved",
+                query=raw,
+                target=_target(
+                    artifact_id,
+                    str(qualified_name),
+                    resolution="exact_id",
+                ),
+            )
+
+        if raw.count("::") != 1:
+            return LineageTargetResolution(
+                status="invalid",
+                query=raw,
+            )
+
+        module_name, symbol_name = raw.split("::", 1)
+        if not module_name or not symbol_name:
+            return LineageTargetResolution(
+                status="invalid",
+                query=raw,
+            )
+
+        matches = tuple(
+            _target(
+                str(artifact_id),
+                str(qualified_name),
+                resolution="exact_identity",
+            )
+            for artifact_id, qualified_name in sorted(
+                self._catalog.artifacts.items(),
+                key=lambda item: (str(item[1]), str(item[0])),
+            )
+            if str(qualified_name) == raw
+        )
+
+        if not matches:
+            return LineageTargetResolution(
+                status="not_found",
+                query=raw,
+            )
+        if len(matches) > 1:
+            return LineageTargetResolution(
+                status="ambiguous",
+                query=raw,
+                candidates=matches,
+            )
+        return LineageTargetResolution(
+            status="resolved",
+            query=raw,
+            target=matches[0],
+        )
+
+
+def _target(
+    artifact_id: str,
+    qualified_name: str,
+    *,
+    resolution: str,
+) -> ResolvedLineageTarget:
+    if qualified_name.count("::") != 1:
+        raise ValueError(
+            "Active artifact identity must be canonical module::symbol."
+        )
+    module_name, symbol_name = qualified_name.split("::", 1)
+    if not module_name or not symbol_name:
+        raise ValueError(
+            "Active artifact identity must be canonical module::symbol."
+        )
+    return ResolvedLineageTarget(
+        artifact_id=artifact_id,
+        qualified_name=qualified_name,
+        module_name=module_name,
+        symbol_name=symbol_name,
+        resolution=resolution,
+    )
diff --git a/contextor/core/lineage_query/__init__.py b/contextor/core/lineage_query/__init__.py
new file mode 100644
index 0000000..293738a
--- /dev/null
+++ b/contextor/core/lineage_query/__init__.py
@@ -0,0 +1,19 @@
+from contextor.core.lineage_query.backend import (
+    CanonicalLineageBackend,
+    LineageBackendMetadata,
+    RepositoryStateLineageBackend,
+)
+from contextor.core.lineage_query.service import (
+    LineageQueryService,
+    LineageTargetResolution,
+    ResolvedLineageTarget,
+)
+
+__all__ = [
+    "CanonicalLineageBackend",
+    "LineageBackendMetadata",
+    "LineageQueryService",
+    "LineageTargetResolution",
+    "RepositoryStateLineageBackend",
+    "ResolvedLineageTarget",
+]
diff --git a/tests/analysis/test_lineage_query_service.py b/tests/analysis/test_lineage_query_service.py
new file mode 100644
index 0000000..fcd4482
--- /dev/null
+++ b/tests/analysis/test_lineage_query_service.py
@@ -0,0 +1,180 @@
+from types import SimpleNamespace
+
+import pytest
+
+from contextor.core.lineage_query import (
+    LineageQueryService,
+    RepositoryStateLineageBackend,
+    ResolvedLineageTarget,
+)
+from contextor.core.report_query import IndexCatalog
+
+
+def _service(artifacts: dict[str, str]) -> LineageQueryService:
+    backend = RepositoryStateLineageBackend(
+        SimpleNamespace(
+            lineage_facts_state="fresh",
+            lineage_facts_by_source={},
+        )
+    )
+    return LineageQueryService(
+        backend,
+        IndexCatalog(
+            modules={},
+            artifacts=artifacts,
+        ),
+    )
+
+
+def test_resolves_active_artifact_id_exactly():
+    service = _service(
+        {"A17/2": "pkg.mod::handler"}
+    )
+
+    result = service.resolve_target("a17/2")
+
+    assert result.status == "resolved"
+    assert result.target == ResolvedLineageTarget(
+        artifact_id="A17/2",
+        qualified_name="pkg.mod::handler",
+        module_name="pkg.mod",
+        symbol_name="handler",
+        resolution="exact_id",
+    )
+    assert result.candidates == ()
+
+
+def test_resolves_exact_qualified_identity_to_same_owner():
+    service = _service(
+        {"A17/2": "pkg.mod::handler"}
+    )
+
+    result = service.resolve_target("pkg.mod::handler")
+
+    assert result.status == "resolved"
+    assert result.target == ResolvedLineageTarget(
+        artifact_id="A17/2",
+        qualified_name="pkg.mod::handler",
+        module_name="pkg.mod",
+        symbol_name="handler",
+        resolution="exact_identity",
+    )
+
+
+def test_missing_syntactic_artifact_id_never_falls_back():
+    service = _service(
+        {"A17/2": "pkg.mod::handler"}
+    )
+
+    result = service.resolve_target("A999/1")
+
+    assert result.status == "not_found"
+    assert result.target is None
+    assert result.candidates == ()
+
+
+@pytest.mark.parametrize(
+    "query",
+    [
+        "",
+        "handler",
+        "pkg.mod",
+        "pkg.mod::",
+        "::handler",
+        "pkg.mod::handler::extra",
+    ],
+)
+def test_non_exact_target_shapes_are_rejected(query):
+    service = _service(
+        {"A17/2": "pkg.mod::handler"}
+    )
+
+    result = service.resolve_target(query)
+
+    assert result.status == "invalid"
+    assert result.target is None
+
+
+def test_resolution_is_case_sensitive_for_qualified_identity():
+    service = _service(
+        {"A17/2": "pkg.mod::Handler"}
+    )
+
+    result = service.resolve_target("pkg.mod::handler")
+
+    assert result.status == "not_found"
+
+
+def test_duplicate_active_identity_fails_closed_as_ambiguous():
+    service = _service(
+        {
+            "A18/1": "pkg.mod::handler",
+            "A17/2": "pkg.mod::handler",
+        }
+    )
+
+    result = service.resolve_target("pkg.mod::handler")
+
+    assert result.status == "ambiguous"
+    assert result.target is None
+    assert tuple(item.artifact_id for item in result.candidates) == (
+        "A17/2",
+        "A18/1",
+    )
+
+
+def test_recovery_catalog_is_not_used_for_lineage_resolution():
+    backend = RepositoryStateLineageBackend(
+        SimpleNamespace(
+            lineage_facts_state="fresh",
+            lineage_facts_by_source={},
+        )
+    )
+    service = LineageQueryService(
+        backend,
+        IndexCatalog(
+            modules={},
+            artifacts={},
+            recovered_artifacts={
+                "A17/2": "pkg.mod::handler",
+            },
+        ),
+    )
+
+    by_id = service.resolve_target("A17/2")
+    by_name = service.resolve_target("pkg.mod::handler")
+
+    assert by_id.status == "not_found"
+    assert by_name.status == "not_found"
+
+
+def test_resolution_does_not_read_or_iterate_lineage_slices():
+    class ResolutionOnlyBackend:
+        def metadata(self):
+            raise AssertionError("resolution must not read lineage metadata")
+
+        def source_keys(self):
+            raise AssertionError("resolution must not enumerate lineage")
+
+        def get_source(self, source_key):
+            raise AssertionError("resolution must not read lineage")
+
+        def get_manifest(self, source_key):
+            raise AssertionError("resolution must not read lineage")
+
+        def iter_sources(self, source_keys=None):
+            raise AssertionError("resolution must not iterate lineage")
+
+    service = LineageQueryService(
+        ResolutionOnlyBackend(),
+        IndexCatalog(
+            modules={},
+            artifacts={"A17/2": "pkg.mod::handler"},
+        ),
+    )
+
+    result = service.resolve_target("pkg.mod::handler")
+
+    assert result.status == "resolved"
+    assert result.target is not None
+    assert result.target.artifact_id == "A17/2"
```

## GATE

Zatrzymano po D1C. Oczekiwana jest komenda `proceduj` przed kolejnym krokiem.
