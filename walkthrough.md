# CONTEXTOR C16-B03-P1D3A

## TARGETED_TESTS

The four specified modules passed: 103 passed, 0 failed. CPython 3.15.2 via .venv, -B -q -rs -p no:cacheprovider, external --basetemp C:\Temp\Contextor_C16_P1D3A_pytest_tmp. No full suite. Git diff --check for the changed production file passed.

## FILES_CHANGED

- contextor/core/cycle_semantics/generation_manifest.py
- tests/test_cycle_semantics_optional_child_manifest.py

walkthrough.md was overwritten as the report. Initial local HEAD ddb7a60d72c17a0a1df30a858fa76408dc868b4d matched the supplied base; worktree was clean. Only the supplied literal changes were applied by direct file patches.

## MCP_POST_CHANGE_AUDIT

At canonical revision 1018, generation_manifest and the new test module report canonical_state=fresh, workspace_sync=verified, advisory_warning=null. The first generation_manifest query at revision 1017 was temporarily unverified while watcher indexing was in progress; the final query was verified. Structural DFS path count remains 16; cycle_semantics remains stale. Indexed source freshness does not prove loaded backend adoption. No FULL, update_file, restart, dependency install or manual commit.

## FULL_DIFFS

```diff
diff --git a/contextor/core/cycle_semantics/generation_manifest.py b/contextor/core/cycle_semantics/generation_manifest.py
index 6ce72e1..b2522e1 100644
--- a/contextor/core/cycle_semantics/generation_manifest.py
+++ b/contextor/core/cycle_semantics/generation_manifest.py
@@ -19,11 +19,16 @@ from .contracts import (
     fingerprint_hard_edges,
 )
 from .evidence import SourceBoundCycleEvidence
-from .source_proof import assess_scc_source_bytes
+from .source_proof import (
+    assess_scc_source_bytes,
+    assess_optional_scc_source_bytes,
+)
+from .model_source_closure import CycleModelSourceClosure
 from .evidence import _scenario_fingerprint
 
 
 MANIFEST_VERSION = "cycle-source-manifest/2"
+OPTIONAL_MANIFEST_VERSION = "cycle-source-manifest/3"
 _AUTHORITY = "PREPARED_ONLY_NOT_CANONICALLY_PUBLISHED"
 
 
@@ -55,6 +60,7 @@ class PreparedCycleSourceManifest:
     components: tuple[PreparedSCCSourceBinding, ...]
     version: str = MANIFEST_VERSION
     authority: str = _AUTHORITY
+    source_selection: str = "HARD_ONLY"
 
 
 def prepare_cycle_source_manifest(
@@ -66,6 +72,10 @@ def prepare_cycle_source_manifest(
     *,
     max_source_bytes: int = 2 * 1024 * 1024,
     max_closure_bytes: int = 32 * 1024 * 1024,
+    source_selection: str = "HARD_ONLY",
+    indexed_imports_by_module: Mapping[str, object] | None = None,
+    package_root: str | None = None,
+    source_closures: tuple[CycleModelSourceClosure, ...] | None = None,
 ) -> PreparedCycleSourceManifest:
     """Prepare immutable source evidence without publication.
 
@@ -75,15 +85,57 @@ def prepare_cycle_source_manifest(
     """
     graph_hash = fingerprint_hard_edges(hard_edges)
 
-    checks = assess_scc_source_bytes(
-        hard_edges,
-        indexed_fingerprints_by_module,
-        snapshot,
-        source_evidence,
-        source_snapshots,
-        max_source_bytes=max_source_bytes,
-        max_closure_bytes=max_closure_bytes,
-    )
+    if source_selection == "HARD_ONLY":
+        if (
+            indexed_imports_by_module is not None
+            or package_root is not None
+            or source_closures is not None
+        ):
+            raise ValueError("HARD_ONLY_OPTIONAL_INPUTS_UNSUPPORTED")
+
+        manifest_version = MANIFEST_VERSION
+        checks = assess_scc_source_bytes(
+            hard_edges,
+            indexed_fingerprints_by_module,
+            snapshot,
+            source_evidence,
+            source_snapshots,
+            max_source_bytes=max_source_bytes,
+            max_closure_bytes=max_closure_bytes,
+        )
+
+    elif source_selection == "OPTIONAL_NAMED_CHILDREN":
+        if (
+            type(source_evidence) is not SourceBoundCycleEvidence
+            or not isinstance(indexed_imports_by_module, Mapping)
+            or type(source_closures) is not tuple
+            or not source_closures
+        ):
+            raise ValueError("OPTIONAL_MANIFEST_INPUT_INVALID")
+
+        manifest_version = OPTIONAL_MANIFEST_VERSION
+
+        checks = assess_optional_scc_source_bytes(
+            hard_edges,
+            indexed_fingerprints_by_module,
+            snapshot,
+            source_evidence,
+            source_snapshots,
+            indexed_imports_by_module,
+            package_root=package_root,
+            source_closures=source_closures,
+            max_source_bytes=max_source_bytes,
+            max_closure_bytes=max_closure_bytes,
+        )
+
+        if (
+            len(source_evidence.components) != len(checks)
+            or len(source_evidence.scenarios.components) != len(checks)
+        ):
+            raise ValueError("OPTIONAL_MANIFEST_COMPONENT_IDENTITY_MISMATCH")
+
+    else:
+        raise ValueError("SOURCE_SELECTION_INVALID")
 
     prepared: list[PreparedSCCSourceBinding] = []
     accepted_signatures: dict[str, tuple[str, str]] = {}
@@ -165,18 +217,36 @@ def prepare_cycle_source_manifest(
             (module, *accepted_signatures[module])
             for module in sorted(accepted_signatures)
         )
-        manifest_hash: str | None = _digest((
-            MANIFEST_VERSION,
-            graph_hash,
-            tuple((
-                component.members,
-                component.model_classification,
-                component.model_kind,
-                component.model_evidence_sha256,
-                component.source_signatures,
-            ) for component in prepared),
-            ordered_sources,
-        ))
+        if source_selection == "HARD_ONLY":
+            manifest_hash: str | None = _digest((
+                MANIFEST_VERSION,
+                graph_hash,
+                tuple((
+                    component.members,
+                    component.model_classification,
+                    component.model_kind,
+                    component.model_evidence_sha256,
+                    component.source_signatures,
+                ) for component in prepared),
+                ordered_sources,
+            ))
+        else:
+            manifest_hash = _digest((
+                OPTIONAL_MANIFEST_VERSION,
+                "OPTIONAL_NAMED_CHILDREN",
+                source_evidence.semantic_version,
+                graph_hash,
+                source_evidence.source_manifest_fingerprint,
+                tuple((
+                    component.members,
+                    component.model_classification,
+                    component.model_kind,
+                    component.model_evidence_sha256,
+                    component.source_signatures,
+                    source_evidence.components[position].evidence_token,
+                ) for position, component in enumerate(prepared)),
+                ordered_sources,
+            ))
     else:
         manifest_hash = None
 
@@ -184,4 +254,6 @@ def prepare_cycle_source_manifest(
         graph_sha256=graph_hash,
         source_manifest_sha256=manifest_hash,
         components=tuple(prepared),
+        version=manifest_version,
+        source_selection=source_selection,
     )
diff --git a/tests/test_cycle_semantics_optional_child_manifest.py b/tests/test_cycle_semantics_optional_child_manifest.py
new file mode 100644
index 0000000..88215a4
--- /dev/null
+++ b/tests/test_cycle_semantics_optional_child_manifest.py
@@ -0,0 +1,156 @@
+"""P1D3A: optional prepared manifests are not publication claims."""
+
+from dataclasses import replace
+
+import pytest
+
+from contextor.core.cycle_semantics.generation_manifest import (
+    MANIFEST_VERSION,
+    OPTIONAL_MANIFEST_VERSION,
+    prepare_cycle_source_manifest,
+)
+from contextor.core.cycle_semantics.publication_binding import (
+    _validated_claim_digest,
+)
+from tests.test_cycle_semantics_optional_child_byte_replay import (
+    _fixture,
+)
+from tests.test_cycle_semantics_optional_child_scenarios import FILES
+from tests.test_cycle_semantics_evidence import (
+    PAIR,
+    PASS,
+    _bound,
+    _p1b_snapshots,
+)
+
+
+def _prepare(case):
+    hard, index, snapshot, evidence, sources, imports, root, closures = case
+    return prepare_cycle_source_manifest(
+        hard,
+        index,
+        snapshot,
+        evidence,
+        sources,
+        source_selection="OPTIONAL_NAMED_CHILDREN",
+        indexed_imports_by_module=imports,
+        package_root=root,
+        source_closures=closures,
+    )
+
+
+def test_optional_manifest_prepared_only(tmp_path):
+    case = _fixture(tmp_path)
+
+    manifest = _prepare(case)
+
+    assert manifest.version == OPTIONAL_MANIFEST_VERSION
+    assert manifest.source_selection == "OPTIONAL_NAMED_CHILDREN"
+    assert manifest.authority == "PREPARED_ONLY_NOT_CANONICALLY_PUBLISHED"
+    assert len(manifest.source_manifest_sha256) == 64
+    assert len(manifest.components) == 1
+    assert manifest.components[0].preparation_state == (
+        "PREPARED_UNPUBLISHED"
+    )
+    assert manifest.components[0].source_signatures == (
+        case[3].components[0].source_signatures
+    )
+    assert manifest == _prepare(case)
+
+
+def test_optional_child_missing_blocks_manifest(tmp_path):
+    case = list(_fixture(tmp_path))
+    case[4] = dict(case[4])
+    case[4].pop("pkg.child")
+
+    manifest = _prepare(case)
+
+    assert manifest.version == OPTIONAL_MANIFEST_VERSION
+    assert manifest.source_manifest_sha256 is None
+    assert manifest.components[0].preparation_state == "UNAVAILABLE"
+    assert manifest.components[0].model_classification == "INDETERMINATE"
+
+
+def test_forged_optional_evidence_blocks_manifest(tmp_path):
+    case = list(_fixture(tmp_path))
+    case[3] = replace(
+        case[3],
+        source_manifest_fingerprint="0" * 64,
+    )
+
+    manifest = _prepare(case)
+
+    assert manifest.source_manifest_sha256 is None
+    assert manifest.components[0].preparation_state == "UNAVAILABLE"
+
+
+def test_wrong_source_cohort_blocks_manifest(tmp_path):
+    case = list(_fixture(tmp_path))
+    case[7] = ()
+
+    with pytest.raises(
+        ValueError, match="OPTIONAL_MANIFEST_INPUT_INVALID"
+    ):
+        _prepare(case)
+
+
+def test_unrelated_module_does_not_change_optional_manifest(tmp_path):
+    first = _fixture(
+        tmp_path / "first",
+        files={**FILES, "pkg/unrelated.py": "value=1\n"},
+    )
+    second = _fixture(
+        tmp_path / "second",
+        files={**FILES, "pkg/unrelated.py": "value=2\n"},
+    )
+
+    a = _prepare(first)
+    b = _prepare(second)
+
+    assert a.source_manifest_sha256 is not None
+    assert a.source_manifest_sha256 == b.source_manifest_sha256
+
+
+def test_two_independent_sccs(tmp_path):
+    case = _fixture(
+        tmp_path,
+        files={
+            **FILES,
+            "pkg/x.py": "import pkg.y\n",
+            "pkg/y.py": "import pkg.x\n",
+        },
+    )
+
+    manifest = _prepare(case)
+
+    assert len(manifest.components) == 2
+    assert all(
+        component.preparation_state == "PREPARED_UNPUBLISHED"
+        for component in manifest.components
+    )
+    assert manifest.source_manifest_sha256 is not None
+
+
+def test_hard_only_manifest_preserves_previous_version():
+    index, snapshot, evidence = _bound(PAIR, PASS)
+
+    manifest = prepare_cycle_source_manifest(
+        PAIR,
+        index,
+        snapshot,
+        evidence,
+        _p1b_snapshots(PASS),
+    )
+
+    assert manifest.version == MANIFEST_VERSION
+    assert manifest.source_selection == "HARD_ONLY"
+    assert manifest.source_manifest_sha256 is not None
+
+
+def test_existing_publication_rejects_optional_manifest(tmp_path):
+    manifest = _prepare(_fixture(tmp_path))
+
+    with pytest.raises(
+        ValueError, match="prepared manifest is incomplete or unsupported"
+    ):
+        _validated_claim_digest(None, manifest)
```

## FINAL_VERDICT

PASS

Optional manifests are prepared and unpublished; existing publication validation rejects them. No LIVE or claim integration was performed.
