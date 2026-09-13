# F2L D1B — read-only canonical lineage storage seam

## STATUS

PASS

Dodano minimalny `RepositoryStateLineageBackend` nad już załadowanym canonical state. Backend zwraca te same immutable `MaterializedLineageSourceFacts` instances, nie kopiuje mappingu ani slices, i nie wykonuje source I/O, AST/extraction/materialization, registry allocation ani MCP work.

Pierwszy `FILE=` w dostarczonym bloku kończył się na katalogu; literalny import `contextor.core.lineage_query.backend` w tym samym bloku jednoznacznie wskazał utworzenie `contextor/core/lineage_query/backend.py`.

## FILES_CHANGED

- `contextor/core/lineage_query/backend.py`
- `contextor/core/lineage_query/__init__.py`
- `tests/analysis/test_lineage_query_backend.py`
- `walkthrough.md` — raport tasku; jego własny diff nie jest częścią `ACTUAL_DIFF`.

## TESTS_RUN

| Command | Result |
|---|---|
| `.\\.venv\\Scripts\\python.exe -m pytest -q tests/analysis/test_lineage_query_backend.py` | PASS — `7 passed in 28.11s` |
| `.\\.venv\\Scripts\\python.exe -m py_compile contextor/core/lineage_query/backend.py contextor/core/lineage_query/__init__.py` | PASS |
| `git diff --no-index --check -- /dev/null contextor/core/lineage_query/backend.py` | PASS — bez błędów whitespace; exit `1` oczekiwany dla nowego pliku porównywanego z `/dev/null` |
| `git diff --no-index --check -- /dev/null contextor/core/lineage_query/__init__.py` | PASS — bez błędów whitespace; exit `1` oczekiwany dla nowego pliku porównywanego z `/dev/null` |
| `git diff --no-index --check -- /dev/null tests/analysis/test_lineage_query_backend.py` | PASS — bez błędów whitespace; exit `1` oczekiwany dla nowego pliku porównywanego z `/dev/null` |

## ACTUAL_DIFF

```diff
diff --git a/contextor/core/lineage_query/backend.py b/contextor/core/lineage_query/backend.py
new file mode 100644
index 0000000..8e8c204
--- /dev/null
+++ b/contextor/core/lineage_query/backend.py
@@ -0,0 +1,160 @@
+from __future__ import annotations
+
+from collections.abc import Iterable, Mapping
+from dataclasses import dataclass
+from typing import Protocol, runtime_checkable
+
+from contextor.core.domain.lineage_facts import (
+    LineageFamilyStatus,
+    MaterializedLineageSourceFacts,
+    SourceLineageManifest,
+)
+
+
+_MISSING = object()
+
+
+@dataclass(frozen=True)
+class LineageBackendMetadata:
+    revision: int | None
+    provenance: str
+    family_state: str
+    semantic_version: str | None
+    source_count: int
+
+
+@runtime_checkable
+class CanonicalLineageBackend(Protocol):
+    def metadata(self) -> LineageBackendMetadata: ...
+
+    def source_keys(self) -> tuple[str, ...]: ...
+
+    def get_source(
+        self,
+        source_key: str,
+    ) -> MaterializedLineageSourceFacts | None: ...
+
+    def get_manifest(
+        self,
+        source_key: str,
+    ) -> SourceLineageManifest | None: ...
+
+    def iter_sources(
+        self,
+        source_keys: Iterable[str] | None = None,
+    ) -> tuple[MaterializedLineageSourceFacts, ...]: ...
+
+
+class RepositoryStateLineageBackend:
+    """Read-only lineage backend over one already-hydrated canonical state."""
+
+    def __init__(self, state: object) -> None:
+        raw_sources = getattr(state, "lineage_facts_by_source", {})
+        if raw_sources is None:
+            raw_sources = {}
+        if not isinstance(raw_sources, Mapping):
+            raise TypeError("lineage_facts_by_source must be a mapping.")
+
+        for source_key in raw_sources:
+            if not isinstance(source_key, str) or not source_key:
+                raise TypeError(
+                    "lineage_facts_by_source keys must be non-empty strings."
+                )
+
+        self._state = state
+        self._sources = raw_sources
+
+    def metadata(self) -> LineageBackendMetadata:
+        raw_revision = getattr(self._state, "revision", None)
+        if raw_revision is not None and (
+            isinstance(raw_revision, bool) or not isinstance(raw_revision, int)
+        ):
+            raise TypeError("Canonical lineage revision must be an integer or None.")
+
+        raw_provenance = getattr(self._state, "provenance", "snapshot") or "snapshot"
+        if not isinstance(raw_provenance, str):
+            raise TypeError("Canonical lineage provenance must be a string.")
+
+        raw_family_state = getattr(
+            self._state,
+            "lineage_facts_state",
+            LineageFamilyStatus.NOT_MATERIALIZED.value,
+        )
+        try:
+            family_state = LineageFamilyStatus(raw_family_state).value
+        except (TypeError, ValueError) as exc:
+            raise ValueError(
+                "Canonical lineage family state is invalid."
+            ) from exc
+
+        semantic_version = getattr(
+            self._state,
+            "lineage_facts_semantic_version",
+            None,
+        )
+        if semantic_version is not None and (
+            not isinstance(semantic_version, str) or not semantic_version
+        ):
+            raise TypeError(
+                "Canonical lineage semantic version must be a non-empty string or None."
+            )
+
+        return LineageBackendMetadata(
+            revision=raw_revision,
+            provenance=raw_provenance,
+            family_state=family_state,
+            semantic_version=semantic_version,
+            source_count=len(self._sources),
+        )
+
+    def source_keys(self) -> tuple[str, ...]:
+        return tuple(sorted(self._sources))
+
+    def get_source(
+        self,
+        source_key: str,
+    ) -> MaterializedLineageSourceFacts | None:
+        if not isinstance(source_key, str) or not source_key:
+            raise ValueError("source_key must be a non-empty string.")
+
+        value = self._sources.get(source_key, _MISSING)
+        if value is _MISSING:
+            return None
+        if not isinstance(value, MaterializedLineageSourceFacts):
+            raise TypeError(
+                f"Canonical lineage slice {source_key!r} has invalid type."
+            )
+        return value
+
+    def get_manifest(
+        self,
+        source_key: str,
+    ) -> SourceLineageManifest | None:
+        source = self.get_source(source_key)
+        return source.manifest if source is not None else None
+
+    def iter_sources(
+        self,
+        source_keys: Iterable[str] | None = None,
+    ) -> tuple[MaterializedLineageSourceFacts, ...]:
+        if source_keys is None:
+            keys = self.source_keys()
+        else:
+            if isinstance(source_keys, (str, bytes)):
+                raise TypeError("source_keys must be an iterable of source-key strings.")
+
+            requested: set[str] = set()
+            for source_key in source_keys:
+                if not isinstance(source_key, str) or not source_key:
+                    raise ValueError(
+                        "source_keys must contain only non-empty strings."
+                    )
+                requested.add(source_key)
+            keys = tuple(sorted(requested))
+
+        result: list[MaterializedLineageSourceFacts] = []
+        for source_key in keys:
+            source = self.get_source(source_key)
+            if source is not None:
+                result.append(source)
+        return tuple(result)
diff --git a/contextor/core/lineage_query/__init__.py b/contextor/core/lineage_query/__init__.py
new file mode 100644
index 0000000..daddd76
--- /dev/null
+++ b/contextor/core/lineage_query/__init__.py
@@ -0,0 +1,11 @@
+from contextor.core.lineage_query.backend import (
+    CanonicalLineageBackend,
+    LineageBackendMetadata,
+    RepositoryStateLineageBackend,
+)
+
+__all__ = [
+    "CanonicalLineageBackend",
+    "LineageBackendMetadata",
+    "RepositoryStateLineageBackend",
+]
diff --git a/tests/analysis/test_lineage_query_backend.py b/tests/analysis/test_lineage_query_backend.py
new file mode 100644
index 0000000..f6ef6f0
--- /dev/null
+++ b/tests/analysis/test_lineage_query_backend.py
@@ -0,0 +1,134 @@
+from types import SimpleNamespace
+
+import pytest
+
+from contextor.core.domain.lineage_facts import (
+    LINEAGE_FACTS_SEMANTIC_VERSION,
+    LineageFamilyStatus,
+    MaterializedLineageSourceFacts,
+    SourceLineageManifest,
+)
+from contextor.core.lineage_query import (
+    CanonicalLineageBackend,
+    LineageBackendMetadata,
+    RepositoryStateLineageBackend,
+)
+
+
+def _slice(source_key: str) -> MaterializedLineageSourceFacts:
+    return MaterializedLineageSourceFacts(
+        manifest=SourceLineageManifest(
+            source_key=source_key,
+            source_fingerprint="f" * 64,
+            semantic_version=LINEAGE_FACTS_SEMANTIC_VERSION,
+            status=LineageFamilyStatus.FRESH,
+            anchor_count=0,
+            flow_count=0,
+            surface_count=0,
+        )
+    )
+
+
+def _state():
+    source_a = _slice("pkg/a.py")
+    source_b = _slice("pkg/b.py")
+    return (
+        SimpleNamespace(
+            revision=11,
+            provenance="live",
+            lineage_facts_state="fresh",
+            lineage_facts_semantic_version=LINEAGE_FACTS_SEMANTIC_VERSION,
+            lineage_facts_by_source={
+                "pkg/b.py": source_b,
+                "pkg/a.py": source_a,
+            },
+        ),
+        source_a,
+        source_b,
+    )
+
+
+def test_repository_state_backend_exposes_canonical_metadata():
+    state, _, _ = _state()
+    backend = RepositoryStateLineageBackend(state)
+
+    assert isinstance(backend, CanonicalLineageBackend)
+    assert backend.metadata() == LineageBackendMetadata(
+        revision=11,
+        provenance="live",
+        family_state="fresh",
+        semantic_version=LINEAGE_FACTS_SEMANTIC_VERSION,
+        source_count=2,
+    )
+
+
+def test_repository_state_backend_preserves_slice_identity_and_order():
+    state, source_a, source_b = _state()
+    backend = RepositoryStateLineageBackend(state)
+
+    assert backend.source_keys() == ("pkg/a.py", "pkg/b.py")
+    assert backend.get_source("pkg/a.py") is source_a
+    assert backend.get_manifest("pkg/a.py") is source_a.manifest
+    assert backend.get_source("pkg/missing.py") is None
+    assert backend.get_manifest("pkg/missing.py") is None
+
+    assert backend.iter_sources(
+        ["pkg/b.py", "pkg/a.py", "pkg/a.py", "pkg/missing.py"]
+    ) == (source_a, source_b)
+
+
+def test_repository_state_backend_defaults_to_not_materialized():
+    backend = RepositoryStateLineageBackend(SimpleNamespace())
+
+    assert backend.metadata() == LineageBackendMetadata(
+        revision=None,
+        provenance="snapshot",
+        family_state="not_materialized",
+        semantic_version=None,
+        source_count=0,
+    )
+    assert backend.source_keys() == ()
+    assert backend.iter_sources() == ()
+
+
+def test_repository_state_backend_rejects_invalid_storage_shape():
+    with pytest.raises(TypeError, match="must be a mapping"):
+        RepositoryStateLineageBackend(
+            SimpleNamespace(lineage_facts_by_source=[])
+        )
+
+    with pytest.raises(TypeError, match="non-empty strings"):
+        RepositoryStateLineageBackend(
+            SimpleNamespace(lineage_facts_by_source={1: _slice("pkg/a.py")})
+        )
+
+
+def test_repository_state_backend_fails_closed_on_invalid_slice():
+    backend = RepositoryStateLineageBackend(
+        SimpleNamespace(
+            lineage_facts_by_source={"pkg/a.py": object()}
+        )
+    )
+
+    with pytest.raises(TypeError, match="invalid type"):
+        backend.get_source("pkg/a.py")
+
+
+def test_repository_state_backend_rejects_invalid_family_state():
+    backend = RepositoryStateLineageBackend(
+        SimpleNamespace(
+            lineage_facts_state="pretend_fresh",
+            lineage_facts_by_source={},
+        )
+    )
+
+    with pytest.raises(ValueError, match="family state is invalid"):
+        backend.metadata()
+
+
+def test_repository_state_backend_rejects_string_as_source_collection():
+    state, _, _ = _state()
+    backend = RepositoryStateLineageBackend(state)
+
+    with pytest.raises(TypeError, match="iterable of source-key strings"):
+        backend.iter_sources("pkg/a.py")
```

## GATE

Zatrzymano po D1B. Oczekiwana jest komenda `proceduj` przed kolejnym krokiem.
