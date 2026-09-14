# P1A2 — Lineage cache codec fail-closed

## STATUS

SUCCESS

Schema version now rejects bool and float values explicitly. The codec rejects malformed payloads fail-closed without changing JSON shape, indexer, CacheManager, __all__, or codec architecture.

## VALIDATION

.\\.venv\\Scripts\\python.exe -m pytest -q tests\\analysis\\test_lineage_cache_codec.py tests\\analysis\\test_lineage_extraction_equivalence.py

16 passed in 1.44s

git diff --check -- contextor/core/analysis/lineage_extraction.py tests/analysis/test_lineage_cache_codec.py passed.

## FILES_CHANGED

- contextor/core/analysis/lineage_extraction.py
- tests/analysis/test_lineage_cache_codec.py

## FULL_DIFFS

\`\`\`diff
warning: in the working copy of 'contextor/core/analysis/lineage_extraction.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'tests/analysis/test_lineage_cache_codec.py', LF will be replaced by CRLF the next time Git touches it
diff --git a/contextor/core/analysis/lineage_extraction.py b/contextor/core/analysis/lineage_extraction.py
index bb8e1aa..551e57a 100644
--- a/contextor/core/analysis/lineage_extraction.py
+++ b/contextor/core/analysis/lineage_extraction.py
@@ -291,7 +291,12 @@ def deserialize_extracted_lineage_source_facts(
             return None
         if set(payload) != _LINEAGE_CACHE_TOP_LEVEL_KEYS:
             return None
-        if payload["schema_version"] != LINEAGE_EXTRACTION_CACHE_SCHEMA_VERSION:
+        schema_version = payload["schema_version"]
+        if (
+            isinstance(schema_version, bool)
+            or not isinstance(schema_version, int)
+            or schema_version != LINEAGE_EXTRACTION_CACHE_SCHEMA_VERSION
+        ):
             return None
         if payload["source_key"] != source_key:
             return None
diff --git a/tests/analysis/test_lineage_cache_codec.py b/tests/analysis/test_lineage_cache_codec.py
index 37b5e4c..0118316 100644
--- a/tests/analysis/test_lineage_cache_codec.py
+++ b/tests/analysis/test_lineage_cache_codec.py
@@ -1,3 +1,7 @@
+import copy
+
+import pytest
+
 from contextor.core.analysis.lineage_extraction import (
     LINEAGE_EXTRACTION_CACHE_SCHEMA_VERSION,
     deserialize_extracted_lineage_source_facts,
@@ -37,6 +41,7 @@ def test_extracted_lineage_cache_codec_round_trip_fresh() -> None:
                 local_id="module",
                 kind="module",
                 span=span,
+                owner_local_id="root",
             ),
         ),
         flows=(
@@ -123,3 +128,77 @@ def test_extracted_lineage_cache_codec_rejects_wrong_schema() -> None:
         )
         is None
     )
+
+
+@pytest.mark.parametrize(
+    "mutate",
+    [
+        lambda payload: payload.__setitem__("schema_version", True),
+        lambda payload: payload.__setitem__("schema_version", 1.0),
+        lambda payload: payload.__setitem__("source_key", "other.py"),
+        lambda payload: payload.__setitem__("source_fingerprint", "2" * 64),
+        lambda payload: payload.pop("status"),
+        lambda payload: payload.__setitem__("unexpected", "value"),
+        lambda payload: payload["flows"][0]["source"].__setitem__("type", "unknown"),
+        lambda payload: payload["flows"][0].__setitem__("relation", "UNKNOWN"),
+        lambda payload: payload["flows"][0].__setitem__("evidence", [1, 0, 1]),
+        lambda payload: payload["flows"][0].__setitem__(
+            "provider",
+            {"provider_id": "fixture-provider"},
+        ),
+    ],
+    ids=[
+        "boolean-schema",
+        "float-schema",
+        "wrong-source-key",
+        "wrong-source-fingerprint",
+        "missing-top-level-key",
+        "extra-top-level-key",
+        "unknown-ref-type",
+        "unknown-enum",
+        "malformed-span",
+        "malformed-provider",
+    ],
+)
+def test_extracted_lineage_cache_codec_rejects_malformed_payloads(mutate) -> None:
+    span = SourceSpan(1, 0, 1, 8)
+    facts = ExtractedLineageSourceFacts(
+        source_key="pkg/mod.py",
+        source_fingerprint=_FINGERPRINT,
+        anchors=(
+            ExtractedAnchorFact(
+                local_id="module",
+                kind="module",
+                span=span,
+            ),
+        ),
+        flows=(
+            ExtractedFlowFact(
+                local_id="flow",
+                source=ExtractedOccurrenceRef("local"),
+                target=ExtractedSymbolicRef(
+                    ExtractedSymbolicKind.IMPORT,
+                    "pkg.dep",
+                    "value",
+                    "local",
+                ),
+                relation=LineageRelation.BINDS,
+                evidence=span,
+                resolution_kind=ResolutionKind.IMPORT_EXACT,
+                confidence=LineageConfidence.CONFIRMED,
+                provider=ProviderRef("fixture-provider", "1"),
+                owner_local_id="module",
+            ),
+        ),
+    )
+    payload = copy.deepcopy(serialize_extracted_lineage_source_facts(facts))
+    mutate(payload)
+
+    assert (
+        deserialize_extracted_lineage_source_facts(
+            payload,
+            source_key="pkg/mod.py",
+            source_fingerprint=_FINGERPRINT,
+        )
+        is None
+    )

\`\`\`

