# C16-B03-P1D3G18-P2-P6

## HEAD_BEFORE/AFTER

`93b208669bd8b99e9a505c83c06a724bb86176c7` before and after. Initial worktree clean. No commit or push.

## FILES_CHANGED

- `contextor/core/cycle_semantics/namespace_bound_model.py` (new)
- `tests/test_cycle_semantics_namespace_bound_model.py` (new)

No existing production or test file was edited. `walkthrough.md` was overwritten as the required report.

## CPYTHON_IDENTITY

Repository `.venv\Scripts\python.exe`: CPython 3.15.2. No interpreter switch.

## SOURCE_BOUND_CONDITIONAL_CONTRACT

DIRECT_EVIDENCE: Created the two supplied files with the exact source-bound conditional model and tests. The model first uses `bind_indexed_namespace_resolution` on caller-supplied portions, paths, fingerprints and byte snapshots. It validates the bound digest and indexed entry, reparses each verified snapshot's bytes, and invokes the P5 conditional evaluator on only those parsed ASTs. Positive outcomes retain `CONDITIONAL_`; authority disclaims runtime and LIVE proof. No existing scenario, warning, publication, graph or source closure consumer was edited. Source identity is a caller claim, not authenticated canonical provenance.

## TARGETED_TEST_RESULTS

Five specified modules: **169 passed in 19.09s**, exit code 0. `git diff --check` exited 0.

## POSITIVE_NEGATIVE_SCENARIOS

CONTRACT_PROVED by the supplied passing tests: source-bound conditional pass, conditional early-binding hazard and entry-order difference retain model-relative outcomes; finder assumption is required. Changed bytes, missing indexed source, syntax error, unindexed namespace entry, unindexed shadowing source and eager external import fail closed. Two caller-supplied namespace portions work conditionally; repeated input yields the same digest and outcome. No unqualified MODEL_PASS is returned by the new interface.

## SOURCE_SNAPSHOT_INTEGRITY

DIRECT_EVIDENCE: The new function compares `SourceSnapshot.raw` SHA-256 and snapshot fingerprint to the claimed indexed fingerprint both in the existing binder and before `parse_source_snapshot`; AST is derived from bytes. The digest describes supplied evidence only. It is not a signature or proof of the actual runtime search path, canonical LIVE generation or genuine index.

## REPOSITORY_REPLAY

DIRECT_EVIDENCE: Physical production Python inventory is 308 files (`contextor` 307 plus root `main.py`); the new module is indexed once in canonical revision 1097. Read-only current-snapshot replay: SCC1 44 members, closure 202, 607 external records, 4 namespace records, external gate `OPAQUE_EXECUTION_POSSIBLE`; SCC2 9 members, closure 222, 725 external records, 4 namespace records, same gate. Both real scenarios retain `INDETERMINATE / NAMESPACE_IMPORT_RESOLUTION_UNMODELED`, coverage NONE and 0 entry assessments. The new conditional model was not used to replace real SCC assessments. Structural DFS cycles remain 16.

## MCP_POST_CHANGE_AUDIT

DIRECT_EVIDENCE: Contextor MCP for both new modules returned revision 1097, canonical_state fresh, workspace_sync verified, advisory warning null, syntax errors 0, structural DFS cycles 16, active warning count 16, model_pass_count 0 and cycle_semantics stale. Snapshot and metadata-selected FileState agreed on revision 1097 and state_id `20261106_195021`; 222/222 selected source SHA-256 fingerprints matched FileState. No FULL, update_file or restart was performed.

## REMAINING_AUTHORITY_GAPS

Caller-supplied source and inventory cannot prove actual `sys.path`, `sys.meta_path`, `sys.modules`, loader selection, canonical LIVE freshness or warning eligibility. Real SCC namespace and external import uncertainty remains. Active runtime code adoption was not certified; replay used current repository source. No optional /3 receipt was claimed.

## FULL_DIFFS

Complete actual new-file diffs follow.

```diff
diff --git a/contextor/core/cycle_semantics/namespace_bound_model.py b/contextor/core/cycle_semantics/namespace_bound_model.py
new file mode 100644
index 0000000..20a4882
--- /dev/null
+++ b/contextor/core/cycle_semantics/namespace_bound_model.py
@@ -0,0 +1,193 @@
+"""Source-bound, conditional PEP 420 cycle-order evidence.
+
+The supplied fingerprints and path inventory remain caller claims.
+This module does not authenticate runtime import finder state,
+canonical LIVE generations or warning-suppression eligibility.
+"""
+
+from __future__ import annotations
+
+import ast
+import hashlib
+from collections.abc import Mapping
+from dataclasses import dataclass
+from pathlib import Path
+
+from contextor.core.source import (
+    SourceError,
+    SourceSnapshot,
+    parse_source_snapshot,
+)
+
+from .model_identity import indexed_to_logical_module
+from .namespace_path_model import SearchPortion
+from .namespace_source_binding import (
+    IndexedSourcePath,
+    bind_indexed_namespace_resolution,
+)
+from .package_model import (
+    ConditionalNamespaceModelAssessment,
+    evaluate_conditional_namespace_import_order,
+)
+
+
+@dataclass(frozen=True)
+class SourceBoundConditionalNamespaceAssessment:
+    entry_module: str
+    outcome: str
+    reason: str | None
+    source_evidence_sha256: str | None
+    conditional_assessment: (
+        ConditionalNamespaceModelAssessment | None
+    )
+    authority: str = (
+        "SOURCE_BOUND_CALLER_SUPPLIED_INVENTORY_"
+        "NOT_RUNTIME_OR_LIVE_PROOF"
+    )
+
+
+def evaluate_source_bound_conditional_namespace_import_order(
+    roots: tuple[SearchPortion, ...],
+    bindings: tuple[IndexedSourcePath, ...],
+    indexed_fingerprints: Mapping[str, str],
+    source_snapshots: Mapping[str, SourceSnapshot],
+    entry_module: str,
+    *,
+    standard_finder_assumed: bool = False,
+) -> SourceBoundConditionalNamespaceAssessment:
+    """Parse indexed byte snapshots and conditionally evaluate PEP 420.
+
+    Binding verifies every supplied source against its claimed
+    fingerprint before AST parsing. The AST is derived only from
+    those bytes, never accepted as independent caller evidence.
+
+    This is not an authenticated index, runtime import environment,
+    LIVE generation or permission to suppress a cycle warning.
+    """
+
+    def reject(
+        reason: str,
+        digest: str | None = None,
+    ) -> SourceBoundConditionalNamespaceAssessment:
+        return SourceBoundConditionalNamespaceAssessment(
+            entry_module=entry_module,
+            outcome="UNKNOWN",
+            reason=reason,
+            source_evidence_sha256=digest,
+            conditional_assessment=None,
+        )
+
+    if (
+        type(entry_module) is not str
+        or not entry_module
+        or any(
+            not part.isidentifier()
+            for part in entry_module.split(".")
+        )
+        or type(standard_finder_assumed) is not bool
+    ):
+        return reject("INVALID_ENTRY_OR_FINDER_POLICY")
+
+    bound = bind_indexed_namespace_resolution(
+        roots,
+        bindings,
+        indexed_fingerprints,
+        source_snapshots,
+        entry_module,
+        standard_finder_assumed=standard_finder_assumed,
+    )
+
+    if bound.status != "SOURCE_BOUND_CONDITIONAL":
+        return reject(
+            bound.reason or "SOURCE_BINDING_INDETERMINATE"
+        )
+
+    digest = bound.evidence_sha256
+
+    if (
+        type(digest) is not str
+        or len(digest) != 64
+    ):
+        return reject("SOURCE_BINDING_DIGEST_INVALID")
+
+    entry_candidates = {
+        indexed_to_logical_module(module_id)
+        for module_id in indexed_fingerprints
+    }
+
+    # An artificial namespace initializer is not an indexed
+    # physical source and cannot be a source-bound entry.
+    if entry_module not in entry_candidates:
+        return reject(
+            "ENTRY_SOURCE_NOT_INDEXED",
+            digest,
+        )
+
+    source_paths = {
+        row.module_id: row.relative_path
+        for row in bindings
+    }
+
+    parsed_sources: dict[str, ast.Module] = {}
+
+    for module_id in sorted(indexed_fingerprints):
+        snapshot = source_snapshots.get(module_id)
+        expected = indexed_fingerprints[module_id]
+        path = source_paths.get(module_id)
+
+        if (
+            type(snapshot) is not SourceSnapshot
+            or type(snapshot.raw) is not bytes
+            or type(snapshot.source_fingerprint) is not str
+            or snapshot.source_fingerprint != expected
+            or hashlib.sha256(snapshot.raw).hexdigest()
+            != expected
+            or type(path) is not str
+        ):
+            return reject(
+                "SOURCE_CHANGED_AFTER_BINDING",
+                digest,
+            )
+
+        try:
+            parsed = parse_source_snapshot(
+                snapshot,
+                Path(path),
+            )
+        except SourceError:
+            return reject(
+                "SOURCE_PARSE_FAILED:" + module_id,
+                digest,
+            )
+
+        if not isinstance(parsed.tree, ast.Module):
+            return reject(
+                "SOURCE_AST_INVALID:" + module_id,
+                digest,
+            )
+
+        if parsed.source_fingerprint != expected:
+            return reject(
+                "SOURCE_AST_FINGERPRINT_MISMATCH:"
+                + module_id,
+                digest,
+            )
+
+        parsed_sources[module_id] = parsed.tree
+
+    conditional = evaluate_conditional_namespace_import_order(
+        parsed_sources,
+        entry_module,
+        roots,
+    )
+
+    # Never convert CONDITIONAL_MODEL_PASS into MODEL_PASS.
+    # The original conditional assessment retains its
+    # restricted-model authority and complete event sequence.
+    return SourceBoundConditionalNamespaceAssessment(
+        entry_module=entry_module,
+        outcome=conditional.outcome,
+        reason=conditional.reason,
+        source_evidence_sha256=digest,
+        conditional_assessment=conditional,
+    )
diff --git a/tests/test_cycle_semantics_namespace_bound_model.py b/tests/test_cycle_semantics_namespace_bound_model.py
new file mode 100644
index 0000000..a120041
--- /dev/null
+++ b/tests/test_cycle_semantics_namespace_bound_model.py
@@ -0,0 +1,312 @@
+"""Source-bound conditional PEP 420 regression contracts."""
+
+from __future__ import annotations
+
+import hashlib
+
+from contextor.core.source import SourceSnapshot
+from contextor.core.cycle_semantics.namespace_bound_model import (
+    evaluate_source_bound_conditional_namespace_import_order,
+)
+from contextor.core.cycle_semantics.namespace_path_model import (
+    SearchPortion,
+)
+from contextor.core.cycle_semantics.namespace_source_binding import (
+    IndexedSourcePath,
+)
+
+
+def _snapshot(text):
+    raw = text.encode("utf-8")
+    return SourceSnapshot(
+        raw=raw,
+        source_fingerprint=hashlib.sha256(raw).hexdigest(),
+    )
+
+
+def _case(*, hazard=False):
+    texts = {
+        "pkg.__init__": "pass\n",
+        "pkg.ns.a": (
+            "import pkg.ns.b\n"
+            "value = 1\n"
+            if hazard
+            else
+            "value = 1\n"
+            "import pkg.ns.b\n"
+        ),
+        "pkg.ns.b": "from pkg.ns.a import value\n",
+    }
+
+    snapshots = {
+        module_id: _snapshot(text)
+        for module_id, text in texts.items()
+    }
+
+    fingerprints = {
+        module_id: snapshot.source_fingerprint
+        for module_id, snapshot in snapshots.items()
+    }
+
+    bindings = (
+        IndexedSourcePath(
+            "pkg.__init__",
+            "root",
+            "pkg/__init__.py",
+        ),
+        IndexedSourcePath(
+            "pkg.ns.a",
+            "root",
+            "pkg/ns/a.py",
+        ),
+        IndexedSourcePath(
+            "pkg.ns.b",
+            "root",
+            "pkg/ns/b.py",
+        ),
+    )
+
+    roots = (
+        SearchPortion(
+            "root",
+            frozenset({
+                "pkg/__init__.py",
+                "pkg/ns/a.py",
+                "pkg/ns/b.py",
+            }),
+        ),
+    )
+
+    return roots, bindings, fingerprints, snapshots
+
+
+def _evaluate(
+    args,
+    entry="pkg.ns.a",
+    *,
+    finder=True,
+):
+    return evaluate_source_bound_conditional_namespace_import_order(
+        *args,
+        entry,
+        standard_finder_assumed=finder,
+    )
+
+
+def test_p6_source_bound_conditional_pass():
+    result = _evaluate(_case())
+
+    assert result.outcome == "CONDITIONAL_MODEL_PASS"
+    assert result.reason is None
+    assert result.source_evidence_sha256 is not None
+    assert len(result.source_evidence_sha256) == 64
+    assert result.conditional_assessment is not None
+    assert result.conditional_assessment.outcome == (
+        "CONDITIONAL_MODEL_PASS"
+    )
+    assert result.authority == (
+        "SOURCE_BOUND_CALLER_SUPPLIED_INVENTORY_"
+        "NOT_RUNTIME_OR_LIVE_PROOF"
+    )
+
+
+def test_p6_source_bound_hazard():
+    result = _evaluate(_case(hazard=True))
+
+    assert result.outcome == (
+        "CONDITIONAL_EARLY_BINDING_HAZARD"
+    )
+    assert result.conditional_assessment is not None
+    assert result.conditional_assessment.model_assessment is not None
+    assert (
+        result.conditional_assessment
+        .model_assessment.symbol
+    ) == "value"
+
+
+def test_p6_entry_order_is_not_assumed():
+    result = _evaluate(
+        _case(hazard=True),
+        entry="pkg.ns.b",
+    )
+
+    assert result.outcome == "CONDITIONAL_MODEL_PASS"
+
+
+def test_p6_finder_assumption_is_required():
+    result = _evaluate(
+        _case(),
+        finder=False,
+    )
+
+    assert result.outcome == "UNKNOWN"
+    assert result.reason == (
+        "IMPORT_FINDER_ENVIRONMENT_NOT_PROVED"
+    )
+    assert result.conditional_assessment is None
+
+
+def test_p6_changed_bytes_fail_closed():
+    roots, bindings, hashes, snapshots = _case()
+    snapshots["pkg.ns.a"] = _snapshot(
+        "value = 99\nimport pkg.ns.b\n"
+    )
+
+    result = _evaluate(
+        (roots, bindings, hashes, snapshots)
+    )
+
+    assert result.outcome == "UNKNOWN"
+    assert result.reason == "SOURCE_FINGERPRINT_MISMATCH"
+    assert result.source_evidence_sha256 is None
+    assert result.conditional_assessment is None
+
+
+def test_p6_missing_indexed_snapshot_fails():
+    roots, bindings, hashes, snapshots = _case()
+    del snapshots["pkg.ns.a"]
+
+    result = _evaluate(
+        (roots, bindings, hashes, snapshots)
+    )
+
+    assert result.outcome == "UNKNOWN"
+    assert result.reason == "SOURCE_INDEX_DOMAIN_MISMATCH"
+
+
+def test_p6_syntax_failure_after_valid_binding():
+    roots, bindings, hashes, snapshots = _case()
+
+    snapshots["pkg.ns.a"] = _snapshot(
+        "def invalid(:\n"
+    )
+    hashes["pkg.ns.a"] = (
+        snapshots["pkg.ns.a"].source_fingerprint
+    )
+
+    result = _evaluate(
+        (roots, bindings, hashes, snapshots)
+    )
+
+    assert result.outcome == "UNKNOWN"
+    assert result.reason == (
+        "SOURCE_PARSE_FAILED:pkg.ns.a"
+    )
+    assert result.source_evidence_sha256 is not None
+    assert result.conditional_assessment is None
+
+
+def test_p6_unindexed_namespace_entry_rejected():
+    result = _evaluate(
+        _case(),
+        entry="pkg.ns",
+    )
+
+    assert result.outcome == "UNKNOWN"
+    assert result.reason == "ENTRY_SOURCE_NOT_INDEXED"
+    assert result.conditional_assessment is None
+
+
+def test_p6_unindexed_shadowing_source_rejected():
+    roots, bindings, hashes, snapshots = _case()
+
+    roots = (
+        SearchPortion(
+            "root",
+            roots[0].files | frozenset({
+                "pkg/ns/__init__.py",
+            }),
+        ),
+    )
+
+    result = _evaluate(
+        (roots, bindings, hashes, snapshots)
+    )
+
+    assert result.outcome == "UNKNOWN"
+    assert result.reason == (
+        "INVENTORY_SOURCE_BINDING_MISMATCH"
+    )
+
+
+def test_p6_eager_external_import_unknown():
+    roots, bindings, hashes, snapshots = _case()
+
+    snapshots["pkg.ns.a"] = _snapshot(
+        "import os\n"
+        "value = 1\n"
+        "import pkg.ns.b\n"
+    )
+    hashes["pkg.ns.a"] = (
+        snapshots["pkg.ns.a"].source_fingerprint
+    )
+
+    result = _evaluate(
+        (roots, bindings, hashes, snapshots)
+    )
+
+    assert result.outcome == "UNKNOWN"
+    assert result.reason == "RESTRICTED_MODEL_UNKNOWN"
+    assert result.source_evidence_sha256 is not None
+
+
+def test_p6_two_portions_source_bound():
+    roots = (
+        SearchPortion(
+            "first",
+            frozenset({"ns/a.py"}),
+        ),
+        SearchPortion(
+            "second",
+            frozenset({"ns/b.py"}),
+        ),
+    )
+
+    bindings = (
+        IndexedSourcePath(
+            "ns.a",
+            "first",
+            "ns/a.py",
+        ),
+        IndexedSourcePath(
+            "ns.b",
+            "second",
+            "ns/b.py",
+        ),
+    )
+
+    snapshots = {
+        "ns.a": _snapshot(
+            "value = 1\nimport ns.b\n"
+        ),
+        "ns.b": _snapshot(
+            "from ns.a import value\n"
+        ),
+    }
+
+    hashes = {
+        key: item.source_fingerprint
+        for key, item in snapshots.items()
+    }
+
+    result = _evaluate(
+        (roots, bindings, hashes, snapshots),
+        entry="ns.a",
+    )
+
+    assert result.outcome == "CONDITIONAL_MODEL_PASS"
+    assert result.source_evidence_sha256 is not None
+
+
+def test_p6_deterministic_digest_and_outcome():
+    args = _case()
+
+    first = _evaluate(args)
+    second = _evaluate(args)
+
+    assert first == second
+    assert first.outcome == "CONDITIONAL_MODEL_PASS"
+    assert (
+        first.source_evidence_sha256
+        == second.source_evidence_sha256
+    )
```

## FINAL_VERDICT

PASS — exact two-file source-bound conditional model, 169 targeted tests passed, both real FileState-bound SCCs remain INDETERMINATE and structural cycles remain 16.
