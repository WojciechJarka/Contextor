# CONTEXTOR C16-B03-P1D3C

## FILES_CHANGED

- contextor/core/cycle_semantics/partial_scc_claims.py
- tests/test_cycle_semantics_optional_child_partial_claims.py

## TARGETED_TESTS

DIRECT_EVIDENCE: CPython 3.15.2, five specified modules with `-B -m pytest -q -rs -p no:cacheprovider`, basetemp outside repository: 73 passed in 16.47 s. `git diff --check` passed. No full suite.

## MCP_POST_CHANGE_AUDIT

DIRECT_EVIDENCE: Contextor MCP `get_module_context` returned canonical_state=fresh, workspace_sync=verified, advisory_warning=null and syntax_errors=0 for both changed modules. Production module at revision 1023; new test at revision 1024. Cycle semantics family remains stale. No FULL, update_file, backend restart, or commit.

## FULL_DIFFS

```diff
diff --git a/contextor/core/cycle_semantics/partial_scc_claims.py b/contextor/core/cycle_semantics/partial_scc_claims.py
index 13302fc..eaa4a4b 100644
--- a/contextor/core/cycle_semantics/partial_scc_claims.py
+++ b/contextor/core/cycle_semantics/partial_scc_claims.py
@@ -6,15 +6,20 @@ This does not authenticate source bytes, publication, or runtime safety.
 from __future__ import annotations
 
 import re
+from collections.abc import Mapping
 from dataclasses import dataclass
 
 from .contracts import CycleSemanticsSnapshot, fingerprint_hard_edges
 from .generation_manifest import (
     MANIFEST_VERSION,
+    OPTIONAL_MANIFEST_VERSION,
     PreparedCycleSourceManifest,
     PreparedSCCSourceBinding,
 )
-from .model_source_closure import compute_cycle_model_source_closures
+from .model_source_closure import (
+    compute_cycle_model_source_closures,
+    compute_cycle_model_source_closures_with_optional_children,
+)
 from .original_worker_preparation import OriginalWorkerManifestPreparation
 from .scc import analyze_import_cycle_topology
 
@@ -34,6 +39,25 @@ class PreparedPartialSCCClaims:
     authority: str = PARTIAL_SCC_CLAIMS_AUTHORITY
 
 
+OPTIONAL_PARTIAL_SCC_CLAIMS_VERSION = (
+    "cycle-partial-scc-preparation/2"
+)
+OPTIONAL_PARTIAL_SCC_CLAIMS_AUTHORITY = (
+    "DECLARED_OPTIONAL_PREPARATIONS_NOT_COMMITTED_NOT_SOURCE_CERTIFIED"
+)
+
+
+@dataclass(frozen=True)
+class PreparedOptionalPartialSCCClaims:
+    graph_sha256: str
+    components: tuple[PreparedSCCSourceBinding, ...]
+    source_modules: tuple[str, ...]
+    declared_manifest_sha256: str | None
+    version: str = OPTIONAL_PARTIAL_SCC_CLAIMS_VERSION
+    source_selection: str = "OPTIONAL_NAMED_CHILDREN"
+    authority: str = OPTIONAL_PARTIAL_SCC_CLAIMS_AUTHORITY
+
+
 def validate_partial_scc_claims(
     hard_edges,
     snapshot,
@@ -43,6 +67,7 @@ def validate_partial_scc_claims(
     if (
         type(snapshot) is not CycleSemanticsSnapshot
         or type(preparation) is not OriginalWorkerManifestPreparation
+        or preparation.source_selection != "HARD_ONLY"
         or snapshot.coverage_status != "FILESYSTEM_STABLE_NON_ATOMIC"
         or snapshot.source_issues
     ):
@@ -101,6 +126,7 @@ def validate_partial_scc_claims(
                 or type(preparation.source_modules) is not tuple
                 or preparation.source_modules != expected_source_modules
                 or type(manifest) is not PreparedCycleSourceManifest
+                or manifest.source_selection != "HARD_ONLY"
                 or manifest.components != declarations
                 or manifest.version != MANIFEST_VERSION
                 or manifest.authority
@@ -183,3 +209,241 @@ def validate_partial_scc_claims(
         )
     except (AttributeError, KeyError, TypeError, ValueError, IndexError):
         return None
+
+
+def validate_optional_partial_scc_claims(
+    hard_edges,
+    snapshot,
+    preparation,
+    indexed_imports_by_module,
+    *,
+    package_root=None,
+) -> PreparedOptionalPartialSCCClaims | None:
+    """Validate optional declarations, not original byte provenance."""
+
+    if (
+        type(snapshot) is not CycleSemanticsSnapshot
+        or type(preparation) is not OriginalWorkerManifestPreparation
+        or preparation.source_selection != "OPTIONAL_NAMED_CHILDREN"
+        or not isinstance(indexed_imports_by_module, Mapping)
+        or snapshot.coverage_status != "FILESYSTEM_STABLE_NON_ATOMIC"
+        or snapshot.source_issues
+    ):
+        return None
+
+    try:
+        graph_sha256 = fingerprint_hard_edges(hard_edges)
+        topology = analyze_import_cycle_topology(hard_edges)
+        structural = topology.cyclic_components
+
+        closures = (
+            compute_cycle_model_source_closures_with_optional_children(
+                hard_edges,
+                indexed_imports_by_module,
+                package_root=package_root,
+            )
+        )
+
+        selected = tuple(sorted({
+            module
+            for closure in closures
+            for module in closure.evidence_source_modules
+        }))
+
+        cyclic_members = tuple(sorted(
+            member
+            for component in structural
+            for member in component.members
+        ))
+
+        observed_rows = snapshot.observed_source_fingerprints
+
+        if (
+            not structural
+            or graph_sha256 != snapshot.graph_sha256
+            or snapshot.import_sites.topology != topology
+            or snapshot.cyclic_modules != cyclic_members
+            or type(observed_rows) is not tuple
+            or tuple(row[0] for row in observed_rows)
+            != cyclic_members
+            or len(closures) != len(structural)
+            or tuple(row.members for row in closures)
+            != tuple(component.members for component in structural)
+        ):
+            return None
+
+        observed = dict(observed_rows)
+
+        if any(
+            type(value) is not str
+            or _SHA256_PATTERN.fullmatch(value) is None
+            for value in observed.values()
+        ):
+            return None
+
+        declarations = preparation.component_preparations
+
+        if (
+            type(declarations) is not tuple
+            or len(declarations) != len(structural)
+            or any(
+                type(row) is not PreparedSCCSourceBinding
+                for row in declarations
+            )
+            or tuple(row.members for row in declarations)
+            != tuple(component.members for component in structural)
+        ):
+            return None
+
+        manifest_hash = None
+
+        if preparation.status == "PREPARED_UNPUBLISHED_NON_ATOMIC":
+            manifest = preparation.manifest
+
+            if (
+                preparation.reason is not None
+                or type(preparation.source_modules) is not tuple
+                or preparation.source_modules != selected
+                or type(manifest) is not PreparedCycleSourceManifest
+                or manifest.source_selection != "OPTIONAL_NAMED_CHILDREN"
+                or manifest.version != OPTIONAL_MANIFEST_VERSION
+                or manifest.authority
+                != "PREPARED_ONLY_NOT_CANONICALLY_PUBLISHED"
+                or manifest.graph_sha256 != graph_sha256
+                or manifest.components != declarations
+                or type(manifest.source_manifest_sha256) is not str
+                or _SHA256_PATTERN.fullmatch(
+                    manifest.source_manifest_sha256
+                ) is None
+                or any(
+                    row.preparation_state != "PREPARED_UNPUBLISHED"
+                    for row in declarations
+                )
+            ):
+                return None
+
+            manifest_hash = manifest.source_manifest_sha256
+
+        elif preparation.status == "UNAVAILABLE":
+            if (
+                preparation.reason != "P1C0_SOURCE_EVIDENCE_UNAVAILABLE"
+                or preparation.manifest is not None
+                or preparation.source_modules != ()
+                or not any(
+                    row.preparation_state == "UNAVAILABLE"
+                    for row in declarations
+                )
+            ):
+                return None
+
+        else:
+            return None
+
+        shared_signatures: dict[str, tuple[str, str]] = {}
+
+        for structural_row, closure, item in zip(
+            structural, closures, declarations
+        ):
+            if (
+                item.members != structural_row.members
+                or closure.members != structural_row.members
+            ):
+                return None
+
+            if item.preparation_state == "PREPARED_UNPUBLISHED":
+                if (
+                    item.reason is not None
+                    or item.model_classification not in {
+                        "MODEL_ALL_FRESH_MEMBER_ENTRIES_PASS",
+                        "MODEL_INTERNAL_EARLY_BINDING_HAZARD",
+                    }
+                    or item.model_kind not in {
+                        "FLAT_MODULE", "REGULAR_PACKAGE"
+                    }
+                    or type(item.model_evidence_sha256) is not str
+                    or _SHA256_PATTERN.fullmatch(
+                        item.model_evidence_sha256
+                    ) is None
+                    or type(item.source_signatures) is not tuple
+                ):
+                    return None
+
+                rows = item.source_signatures
+
+                if (
+                    tuple(
+                        row[0]
+                        for row in rows
+                        if type(row) is tuple and len(row) == 3
+                    ) != closure.evidence_source_modules
+                    or len(rows) != len(
+                        closure.evidence_source_modules
+                    )
+                ):
+                    return None
+
+                for row in rows:
+                    if type(row) is not tuple or len(row) != 3:
+                        return None
+
+                    module, raw_hash, ast_hash = row
+
+                    if any(
+                        type(value) is not str
+                        or _SHA256_PATTERN.fullmatch(value) is None
+                        for value in (raw_hash, ast_hash)
+                    ):
+                        return None
+
+                    if (
+                        module in observed
+                        and observed[module] != raw_hash
+                    ):
+                        return None
+
+                    signature = (raw_hash, ast_hash)
+
+                    if (
+                        module in shared_signatures
+                        and shared_signatures[module] != signature
+                    ):
+                        return None
+
+                    shared_signatures[module] = signature
+
+            elif item.preparation_state == "UNAVAILABLE":
+                if (
+                    item.model_classification != "INDETERMINATE"
+                    or type(item.model_kind) is not str
+                    or item.model_kind not in {
+                        "FLAT_MODULE", "REGULAR_PACKAGE"
+                    }
+                    or type(item.reason) is not str
+                    or not item.reason
+                    or item.source_signatures != ()
+                    or item.model_evidence_sha256 is not None
+                ):
+                    return None
+            else:
+                return None
+
+        return PreparedOptionalPartialSCCClaims(
+            graph_sha256=graph_sha256,
+            components=declarations,
+            source_modules=(
+                selected
+                if manifest_hash is not None
+                else ()
+            ),
+            declared_manifest_sha256=manifest_hash,
+        )
+
+    except (
+        AttributeError,
+        KeyError,
+        TypeError,
+        ValueError,
+        IndexError,
+        RecursionError,
+    ):
+        return None

diff --git a/tests/test_cycle_semantics_optional_child_partial_claims.py b/tests/test_cycle_semantics_optional_child_partial_claims.py
new file mode 100644
index 0000000..66b883b
--- /dev/null
+++ b/tests/test_cycle_semantics_optional_child_partial_claims.py
@@ -0,0 +1,224 @@
+"""P1D3C: optional SCC declarations have no publication authority."""
+
+from dataclasses import replace
+
+import pytest
+
+from contextor.core.cycle_semantics.generation_manifest import (
+    MANIFEST_VERSION,
+)
+from contextor.core.cycle_semantics.original_worker_binding import (
+    _select_original_worker_sources,
+)
+from contextor.core.cycle_semantics.partial_scc_claims import (
+    OPTIONAL_PARTIAL_SCC_CLAIMS_VERSION,
+    OPTIONAL_PARTIAL_SCC_CLAIMS_AUTHORITY,
+    PreparedOptionalPartialSCCClaims,
+    validate_optional_partial_scc_claims,
+    validate_partial_scc_claims,
+)
+from tests.test_cycle_semantics_optional_child_worker_manifest import (
+    _pipeline,
+    _prepare,
+)
+from tests.test_cycle_semantics_optional_child_worker_capture import (
+    FILES,
+)
+
+
+@pytest.fixture(autouse=True)
+def _inline_worker(monkeypatch, isolated_dirs):
+    monkeypatch.setenv("CONTEXTOR_DISABLE_PROCESS_POOL", "1")
+
+
+def _case(tmp_path, *, files=None):
+    pipeline = _pipeline(tmp_path, files=files)
+    index, hard_edges, snapshot, _ = pipeline
+    preparation = _prepare(pipeline)
+
+    _, _, package_root = _select_original_worker_sources(
+        index,
+        hard_edges,
+        "OPTIONAL_NAMED_CHILDREN",
+    )
+
+    imports = {
+        name: module.imports
+        for name, module in index.modules.items()
+    }
+
+    return hard_edges, snapshot, preparation, imports, package_root
+
+
+def _check(case):
+    return validate_optional_partial_scc_claims(
+        case[0],
+        case[1],
+        case[2],
+        case[3],
+        package_root=case[4],
+    )
+
+
+def test_optional_declarations_are_not_published(tmp_path):
+    case = _case(tmp_path)
+    result = _check(case)
+
+    assert type(result) is PreparedOptionalPartialSCCClaims
+    assert result.version == OPTIONAL_PARTIAL_SCC_CLAIMS_VERSION
+    assert result.authority == OPTIONAL_PARTIAL_SCC_CLAIMS_AUTHORITY
+    assert result.source_selection == "OPTIONAL_NAMED_CHILDREN"
+    assert "pkg.child" in result.source_modules
+    assert result.declared_manifest_sha256 == (
+        case[2].manifest.source_manifest_sha256
+    )
+    assert result.components == case[2].component_preparations
+    assert all(
+        item.preparation_state == "PREPARED_UNPUBLISHED"
+        for item in result.components
+    )
+    assert result == _check(case)
+
+
+def test_legacy_validator_rejects_optional_preparation(tmp_path):
+    case = _case(tmp_path)
+
+    assert validate_partial_scc_claims(
+        case[0], case[1], case[2]
+    ) is None
+
+    forged = replace(
+        case[2],
+        manifest=replace(
+            case[2].manifest,
+            version=MANIFEST_VERSION,
+        ),
+    )
+
+    assert validate_partial_scc_claims(
+        case[0], case[1], forged
+    ) is None
+
+
+def test_wrong_source_selection_rejected(tmp_path):
+    case = list(_case(tmp_path))
+    case[2] = replace(case[2], source_selection="HARD_ONLY")
+    assert _check(case) is None
+
+
+def test_wrong_manifest_version_or_mode_rejected(tmp_path):
+    case = list(_case(tmp_path))
+    original = case[2].manifest
+
+    case[2] = replace(
+        case[2],
+        manifest=replace(
+            original,
+            version=MANIFEST_VERSION,
+        ),
+    )
+    assert _check(case) is None
+
+    case[2] = replace(
+        case[2],
+        manifest=replace(
+            original,
+            source_selection="HARD_ONLY",
+        ),
+    )
+    assert _check(case) is None
+
+
+def test_missing_optional_child_source_rejected(tmp_path):
+    case = list(_case(tmp_path))
+
+    case[2] = replace(
+        case[2],
+        source_modules=tuple(
+            name
+            for name in case[2].source_modules
+            if name != "pkg.child"
+        ),
+    )
+
+    assert _check(case) is None
+
+
+def test_missing_optional_child_signature_rejected(tmp_path):
+    case = list(_case(tmp_path))
+    preparation = case[2]
+    component = preparation.manifest.components[0]
+
+    changed_component = replace(
+        component,
+        source_signatures=tuple(
+            row
+            for row in component.source_signatures
+            if row[0] != "pkg.child"
+        ),
+    )
+
+    changed_manifest = replace(
+        preparation.manifest,
+        components=(changed_component,),
+    )
+
+    case[2] = replace(
+        preparation,
+        manifest=changed_manifest,
+        component_preparations=changed_manifest.components,
+    )
+
+    assert _check(case) is None
+
+
+def test_changed_import_facts_invalidate_closure(tmp_path):
+    case = list(_case(tmp_path))
+    case[3] = dict(case[3])
+    case[3]["pkg.a"] = []
+
+    assert _check(case) is None
+
+
+def test_changed_graph_identity_rejected(tmp_path):
+    case = list(_case(tmp_path))
+    case[1] = replace(
+        case[1],
+        graph_sha256="0" * 64,
+    )
+
+    assert _check(case) is None
+
+
+def test_two_independent_sccs_preserved(tmp_path):
+    case = _case(
+        tmp_path,
+        files={
+            **FILES,
+            "pkg/x.py": "import pkg.y\n",
+            "pkg/y.py": "import pkg.x\n",
+        },
+    )
+
+    result = _check(case)
+
+    assert result is not None
+    assert len(result.components) == 2
+    assert tuple(
+        item.members for item in result.components
+    ) == tuple(
+        item.members for item in case[2].component_preparations
+    )
+
+
+def test_incomplete_or_forged_manifest_hash_rejected(tmp_path):
+    case = list(_case(tmp_path))
+    case[2] = replace(
+        case[2],
+        manifest=replace(
+            case[2].manifest,
+            source_manifest_sha256=None,
+        ),
+    )
+
+    assert _check(case) is None
```

## FINAL_VERDICT

PASS
