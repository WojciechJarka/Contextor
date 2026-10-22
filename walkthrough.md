# CONTEXTOR_CYCLE_PROOF_P1C0_PREPARED_SOURCE_MANIFEST

## TASK
Applied the exact auditor-supplied P1C0 prepared source-manifest implementation. It prepares immutable model evidence; it does not publish a canonical generation, certify source capture or runtime safety, or alter cycle warnings.

## HEAD_BEFORE
4796dc8422f19a4b41dcdecb931214faf73ffeb0; clean tree before task. generation_manifest.py did not exist and both test patch anchors matched. Contextor showed P1B source_proof assessor and its test consumer, with both target modules workspace_sync=verified at LIVE revision 636. Cycle-semantics family was stale before this task.

## HEAD_AFTER
4796dc8422f19a4b41dcdecb931214faf73ffeb0. No commit made.

## FILES_CHANGED
- contextor/core/cycle_semantics/generation_manifest.py (new)
- tests/test_cycle_semantics_evidence.py
walkthrough.md is the required report and excluded from production/test/docs changes.

## EXACT_IMPLEMENTATION
Added the supplied MANIFEST_VERSION, PREPARED_ONLY_NOT_CANONICALLY_PUBLISHED authority, frozen PreparedSCCSourceBinding and PreparedCycleSourceManifest, deterministic digest helper, and prepare_cycle_source_manifest. It delegates byte/AST verification and budgets to P1B, retains exact successful SCC source signatures, rejects missing/failed evidence or conflicting shared source signatures, and emits a global source-manifest digest only if every cyclic SCC is complete. Added the auditor-supplied local P1C0 T01–T08 tests. No publication, persistence, GUI, MCP, report, graph, SCC or warning-policy integration.

## T01_T08_RESULTS
Command: .\.venv\Scripts\python.exe -m pytest -q tests/test_cycle_semantics_evidence.py -k p1c0
Actual: 8 passed, 67 deselected in 1.63s, exit code 0.
T01 exact prepared source signatures and graph hash PASS; T02 byte drift blocks digest PASS; T03 reachable dependency included PASS; T04 missing dependency blocks digest PASS; T05 independent SCC partial failure blocks global digest PASS; T06 unrelated source does not alter digest PASS; T07 no cyclic SCC is not positive proof PASS; T08 deterministic immutable preparation without publication PASS.

## FOCUSED_NON_REGRESSION
Command: .\.venv\Scripts\python.exe -m pytest -q tests/test_cycle_semantics_evidence.py tests/test_cycle_semantics_scenarios.py tests/test_cycle_semantics_initialization_model.py tests/test_cycle_semantics_canonical_state.py tests/test_cycle_semantics_source_cohort.py
Actual: 137 passed in 6.32s, exit code 0. py_compile of both changed files: exit code 0. git diff --check for tracked test emitted no whitespace findings; git diff --no-index --check for new file emitted no whitespace findings (exit 1 reflects the expected difference from /dev/null). No full repository pytest suite.

## MANIFEST_IDENTITY_AND_SOURCE_CLOSURE
The manifest graph_sha256 is fingerprint_hard_edges of the supplied graph. For each SCC, accepted signatures are exactly the P1B-checked source_evidence component signatures for the reachable closure, including noncyclic dependencies. Shared-module signatures must agree. The deterministic digest covers manifest version, graph hash, ordered SCC member tuples and sorted accepted source signatures. It is null if there are no cyclic SCCs or if any SCC cannot be prepared. Tests T03–T07 exercise closure inclusion, missing evidence, independent components, unrelated source and empty cyclic set.

## PUBLICATION_AUTHORITY_LIMITATION
PREPARED_UNPUBLISHED means an immutable candidate only. No canonical owner has accepted the manifest, no LIVE revision is attached to it, and caller-supplied source bytes remain non-atomic with the graph. The result is not a publication receipt, SAFE classification, or permission to suppress ArchitectureCycle. Current LIVE cycle_semantics family is stale.

## LIVE_REVISION_BEFORE_AFTER
Before: revision 636, resync_required=false. After: revision 638, resync_required=false. Module, graph, topology, artifact-consumption and structural cycles are fresh; cycle_semantics remains stale.

## WATCHER_EVENTS
get_live_events(after_revision=636): revision 637, desktop_watcher update_file UPDATED new generation_manifest.py, blast_radius_state=fresh. get_live_events(after_revision=637): revision 638, desktop_watcher update_file UPDATED test_cycle_semantics_evidence.py, blast_radius_state=fresh. Continuity=continuous and resync_required=false. No manual update_file.

## WORKSPACE_SYNC
At revision 637, Contextor get_module_context reported generation_manifest.py workspace_sync=verified. At revision 638, get_module_context reported test_cycle_semantics_evidence.py workspace_sync=verified; blast radius for prepare_cycle_source_manifest also reported workspace_sync=verified with one confirmed test consumer. Project aggregate workspace_sync remains a separate, potentially unverified read scope.

## RESTART_REQUIREMENTS
No restart performed. The new pure helper has only a confirmed test consumer; it is not integrated into serving MCP/LIVE code. An existing process would need to import this new module before calling it. No restart is required for the current test-only consumption path.

## FULL_DIFFS
Complete actual unified diff of both changed files follows. The new file is diffed against /dev/null because it is untracked.

```diff
diff --git a/tests/test_cycle_semantics_evidence.py b/tests/test_cycle_semantics_evidence.py
index a44937d..6389e6a 100644
--- a/tests/test_cycle_semantics_evidence.py
+++ b/tests/test_cycle_semantics_evidence.py
@@ -24,6 +24,10 @@ from contextor.core.cycle_semantics.evidence import (
 from contextor.core.cycle_semantics.source_proof import (
     assess_scc_source_bytes,
 )
+from contextor.core.cycle_semantics.generation_manifest import (
+    PreparedCycleSourceManifest,
+    prepare_cycle_source_manifest,
+)
 from contextor.core.cycle_semantics.contracts import (
     CycleSemanticsSnapshot, fingerprint_hard_edges,
 )
@@ -980,3 +984,165 @@ def test_p1b_t14_pep263_encoding_from_exact_bytes():
     assert result[0].bytes_state == (
         "BYTE_AST_CONSISTENT_NON_ATOMIC"
     )
+
+
+def test_p1c0_t01_prepared_manifest_contains_exact_sources():
+    index, snapshot, evidence = _bound(PAIR, PASS)
+    result = prepare_cycle_source_manifest(
+        PAIR, index, snapshot, evidence,
+        _p1b_snapshots(PASS),
+    )
+    assert isinstance(result, PreparedCycleSourceManifest)
+    assert result.graph_sha256 == fingerprint_hard_edges(PAIR)
+    assert len(result.source_manifest_sha256) == 64
+    assert result.components[0].members == ("a", "b")
+    assert result.components[0].preparation_state == (
+        "PREPARED_UNPUBLISHED"
+    )
+    assert result.components[0].source_signatures == (
+        evidence.components[0].source_signatures
+    )
+    assert result.authority == (
+        "PREPARED_ONLY_NOT_CANONICALLY_PUBLISHED"
+    )
+
+
+def test_p1c0_t02_byte_drift_cannot_prepare_manifest():
+    index, snapshot, evidence = _bound(PAIR, PASS)
+    sources = _p1b_snapshots(PASS)
+    sources["a"] = _p1b_snapshots(
+        {"a": PASS["a"] + "\n# changed"}
+    )["a"]
+    result = prepare_cycle_source_manifest(
+        PAIR, index, snapshot, evidence, sources,
+    )
+    assert result.source_manifest_sha256 is None
+    assert result.components[0].preparation_state == "UNAVAILABLE"
+    assert result.components[0].model_classification == "INDETERMINATE"
+
+
+def test_p1c0_t03_reachable_dependency_is_in_manifest():
+    graph = {
+        "a": {"b", "dep"},
+        "b": {"a"},
+        "dep": set(),
+    }
+    sources = {
+        "a": "import b\nimport dep",
+        "b": "import a",
+        "dep": "x=1",
+    }
+    index, snapshot, evidence = _bound(graph, sources)
+    result = prepare_cycle_source_manifest(
+        graph, index, snapshot, evidence,
+        _p1b_snapshots(sources),
+    )
+    assert result.components[0].preparation_state == (
+        "PREPARED_UNPUBLISHED"
+    )
+    assert tuple(
+        item[0]
+        for item in result.components[0].source_signatures
+    ) == ("a", "b", "dep")
+
+
+def test_p1c0_t04_missing_dependency_blocks_digest():
+    graph = {
+        "a": {"b", "dep"},
+        "b": {"a"},
+        "dep": set(),
+    }
+    sources = {
+        "a": "import b\nimport dep",
+        "b": "import a",
+        "dep": "x=1",
+    }
+    index, snapshot, evidence = _bound(graph, sources)
+    raw = _p1b_snapshots(sources)
+    del raw["dep"]
+    result = prepare_cycle_source_manifest(
+        graph, index, snapshot, evidence, raw,
+    )
+    assert result.source_manifest_sha256 is None
+    assert result.components[0].reason == (
+        "SOURCE_BYTES_UNAVAILABLE:dep"
+    )
+
+
+def test_p1c0_t05_independent_scc_partial_failure():
+    graph = {
+        "a": {"b"},
+        "b": {"a"},
+        "x": {"y"},
+        "y": {"x"},
+    }
+    sources = dict(
+        PASS,
+        x="import y\nn=1",
+        y="import x\nm=2",
+    )
+    index, snapshot, evidence = _bound(graph, sources)
+    raw = _p1b_snapshots(sources)
+    del raw["x"]
+    result = prepare_cycle_source_manifest(
+        graph, index, snapshot, evidence, raw,
+    )
+    assert [
+        item.preparation_state
+        for item in result.components
+    ] == ["PREPARED_UNPUBLISHED", "UNAVAILABLE"]
+    assert result.source_manifest_sha256 is None
+
+
+def test_p1c0_t06_unrelated_source_does_not_affect_digest():
+    graph = {
+        "a": {"b"},
+        "b": {"a"},
+        "other": set(),
+    }
+    first = dict(PASS, other="x=1")
+    second = dict(PASS, other="x=2")
+    a_index, a_snapshot, a_evidence = _bound(graph, first)
+    b_index, b_snapshot, b_evidence = _bound(graph, second)
+    a = prepare_cycle_source_manifest(
+        graph, a_index, a_snapshot, a_evidence,
+        _p1b_snapshots(PASS),
+    )
+    b = prepare_cycle_source_manifest(
+        graph, b_index, b_snapshot, b_evidence,
+        _p1b_snapshots(PASS),
+    )
+    assert a.source_manifest_sha256 == b.source_manifest_sha256
+
+
+def test_p1c0_t07_no_cycles_is_not_positive_proof():
+    graph = {"a": {"b"}, "b": set()}
+    sources = {"a": "import b", "b": "pass"}
+    index, snapshot, evidence = _bound(graph, sources)
+    result = prepare_cycle_source_manifest(
+        graph, index, snapshot, evidence, {},
+    )
+    assert result.components == ()
+    assert result.source_manifest_sha256 is None
+
+
+def test_p1c0_t08_deterministic_and_never_published():
+    index, snapshot, evidence = _bound(PAIR, PASS)
+    sources = _p1b_snapshots(PASS)
+    before = repr((index, snapshot, evidence, sources))
+    a = prepare_cycle_source_manifest(
+        PAIR, index, snapshot, evidence, sources,
+    )
+    b = prepare_cycle_source_manifest(
+        PAIR, index, snapshot, evidence, sources,
+    )
+    assert a == b
+    assert before == repr((index, snapshot, evidence, sources))
+    assert a.authority == (
+        "PREPARED_ONLY_NOT_CANONICALLY_PUBLISHED"
+    )
+    assert "SAFE" not in a.authority
+    assert "PUBLISHED" not in a.components[0].preparation_state.replace(
+        "UNPUBLISHED", ""
+    )
+    json.dumps(asdict(a))
diff --git a/contextor/core/cycle_semantics/generation_manifest.py b/contextor/core/cycle_semantics/generation_manifest.py
new file mode 100644
index 0000000..afd2372
--- /dev/null
+++ b/contextor/core/cycle_semantics/generation_manifest.py
@@ -0,0 +1,173 @@
+"""Prepared source manifests for cyclic SCC model evidence.
+
+The manifest binds graph identity, reachable source fingerprints,
+AST fingerprints and successful P1B assessments. Preparation is
+not canonical publication, atomic source capture or runtime safety.
+"""
+
+from __future__ import annotations
+
+import hashlib
+import json
+from collections.abc import Mapping
+from dataclasses import dataclass
+
+from contextor.core.source import SourceSnapshot
+
+from .contracts import (
+    CycleSemanticsSnapshot,
+    fingerprint_hard_edges,
+)
+from .evidence import SourceBoundCycleEvidence
+from .source_proof import assess_scc_source_bytes
+
+
+MANIFEST_VERSION = "cycle-source-manifest/1"
+_AUTHORITY = "PREPARED_ONLY_NOT_CANONICALLY_PUBLISHED"
+
+
+def _digest(value: object) -> str:
+    payload = json.dumps(
+        value,
+        ensure_ascii=True,
+        sort_keys=True,
+        separators=(",", ":"),
+    ).encode("utf-8")
+    return hashlib.sha256(payload).hexdigest()
+
+
+@dataclass(frozen=True)
+class PreparedSCCSourceBinding:
+    members: tuple[str, ...]
+    source_signatures: tuple[tuple[str, str, str], ...]
+    model_classification: str
+    preparation_state: str
+    reason: str | None
+
+
+@dataclass(frozen=True)
+class PreparedCycleSourceManifest:
+    graph_sha256: str
+    source_manifest_sha256: str | None
+    components: tuple[PreparedSCCSourceBinding, ...]
+    version: str = MANIFEST_VERSION
+    authority: str = _AUTHORITY
+
+
+def prepare_cycle_source_manifest(
+    hard_edges: Mapping[str, object],
+    indexed_fingerprints_by_module: Mapping[str, str],
+    snapshot: CycleSemanticsSnapshot,
+    source_evidence: SourceBoundCycleEvidence,
+    source_snapshots: Mapping[str, SourceSnapshot],
+    *,
+    max_source_bytes: int = 2 * 1024 * 1024,
+    max_closure_bytes: int = 32 * 1024 * 1024,
+) -> PreparedCycleSourceManifest:
+    """Prepare immutable source evidence without publication.
+
+    P1B owns byte-to-AST consistency and source budget checks.
+    This operation never asserts that a canonical owner accepted
+    these inputs or that they belong to a published revision.
+    """
+    graph_hash = fingerprint_hard_edges(hard_edges)
+
+    checks = assess_scc_source_bytes(
+        hard_edges,
+        indexed_fingerprints_by_module,
+        snapshot,
+        source_evidence,
+        source_snapshots,
+        max_source_bytes=max_source_bytes,
+        max_closure_bytes=max_closure_bytes,
+    )
+
+    prepared: list[PreparedSCCSourceBinding] = []
+    accepted_signatures: dict[str, tuple[str, str]] = {}
+    all_complete = bool(checks)
+
+    for position, check in enumerate(checks):
+        complete = (
+            check.bytes_state == "BYTE_AST_CONSISTENT_NON_ATOMIC"
+            and check.authority
+            == "CALLER_SUPPLIED_BYTES_NOT_ATOMICALLY_BOUND_TO_LIVE"
+            and check.model_classification
+            in {
+                "MODEL_ALL_FRESH_MEMBER_ENTRIES_PASS",
+                "MODEL_INTERNAL_EARLY_BINDING_HAZARD",
+            }
+        )
+
+        if not complete:
+            all_complete = False
+            prepared.append(PreparedSCCSourceBinding(
+                members=check.members,
+                source_signatures=(),
+                model_classification="INDETERMINATE",
+                preparation_state="UNAVAILABLE",
+                reason=check.reason or "P1B_EVIDENCE_UNAVAILABLE",
+            ))
+            continue
+
+        source_component = source_evidence.components[position]
+
+        # P1B has already validated the exact component,
+        # its reachable closure, source hashes and AST hashes.
+        signatures = source_component.source_signatures
+
+        conflict = next((
+            module
+            for module, raw_hash, ast_hash in signatures
+            if (
+                module in accepted_signatures
+                and accepted_signatures[module]
+                != (raw_hash, ast_hash)
+            )
+        ), None)
+
+        if conflict is not None:
+            all_complete = False
+            prepared.append(PreparedSCCSourceBinding(
+                members=check.members,
+                source_signatures=(),
+                model_classification="INDETERMINATE",
+                preparation_state="UNAVAILABLE",
+                reason="SOURCE_MANIFEST_CONFLICT:" + conflict,
+            ))
+            continue
+
+        for module, raw_hash, ast_hash in signatures:
+            accepted_signatures[module] = (raw_hash, ast_hash)
+
+        prepared.append(PreparedSCCSourceBinding(
+            members=check.members,
+            source_signatures=signatures,
+            model_classification=check.model_classification,
+            preparation_state="PREPARED_UNPUBLISHED",
+            reason=None,
+        ))
+
+    # A global manifest digest must not imply completeness
+    # when even one SCC lacks sufficient evidence.
+    if all_complete:
+        ordered_sources = tuple(
+            (module, *accepted_signatures[module])
+            for module in sorted(accepted_signatures)
+        )
+        manifest_hash: str | None = _digest((
+            MANIFEST_VERSION,
+            graph_hash,
+            tuple(
+                component.members
+                for component in prepared
+            ),
+            ordered_sources,
+        ))
+    else:
+        manifest_hash = None
+
+    return PreparedCycleSourceManifest(
+        graph_sha256=graph_hash,
+        source_manifest_sha256=manifest_hash,
+        components=tuple(prepared),
+    )
```

## FINAL_VERDICT
PASS for the exact P1C0 patch, targeted and focused tests, source/test watcher events and verified per-file workspace synchronization. The manifest remains prepared and unpublished.
