# CONTEXTOR_CYCLE_PROOF_P1B_BYTE_AST_COHERENCE

## TASK
Applied the exact auditor-supplied P1B byte/AST coherence layer. It checks caller-supplied source bytes against declared index and model evidence, without claiming LIVE source ownership, atomic capture, Python import safety or warning suppression.

## HEAD_BEFORE
3eba8dee5ee5d65048abcf4eed80beb4c8b22cff. Clean working tree before task. source_proof.py did not exist. The exact test import and final P1 T06 anchors matched. Contextor identified P0 assessor and parse_source_snapshot owners and consumers before edit. LIVE revision 634; resync_required=false.

## HEAD_AFTER
3eba8dee5ee5d65048abcf4eed80beb4c8b22cff. No commit made.

## FILES_CHANGED
- contextor/core/cycle_semantics/source_proof.py (new)
- tests/test_cycle_semantics_evidence.py
walkthrough.md is the required report, excluded from production/test/docs changes.

## EXACT_IMPLEMENTATION
Created the exact approved source_proof.py with frozen SCCSourceByteAssessment and pure assess_scc_source_bytes. It calls P0 once, requires P0 DECLARED_INPUTS_CONSISTENT, checks every exact reachable-closure SourceSnapshot under source and total-byte budgets, recomputes SHA-256 from raw bytes, compares snapshot/index/evidence raw hashes, reparses the caller-supplied bytes with canonical parse_source_snapshot, computes AST signature, and compares it with P0 evidence. It retains only bounded model classification with BYTE_AST_CONSISTENT_NON_ATOMIC and authority CALLER_SUPPLIED_BYTES_NOT_ATOMICALLY_BOUND_TO_LIVE. Added auditor-supplied local P1B T01–T14 tests to the approved test file. No other production/test file, public warning flow, graph, SCC algorithm, persistence, GUI or MCP API changed.

## T01_T14_RESULTS
Command: .\.venv\Scripts\python.exe -m pytest -q tests/test_cycle_semantics_evidence.py -k p1b
Actual: 15 passed, 52 deselected in 1.44s, exit code 0. T01 has two parametrizations; each of T02–T14 passed. The cases cover valid pass/hazard, recomputed raw hash, changed same-AST bytes, forged AST signature/token, missing/changed reachable dependency, unrelated module, separate SCCs, unparsable bytes, budgets/types, no SCC, P0 incomplete, deterministic/no mutation, and PEP 263 encoding. Local P1B T labels were not conflated with canonical C01–C30.

## FOCUSED_NON_REGRESSION
Command: .\.venv\Scripts\python.exe -m pytest -q tests/test_cycle_semantics_evidence.py tests/test_cycle_semantics_scenarios.py tests/test_cycle_semantics_initialization_model.py tests/test_cycle_semantics_canonical_state.py tests/test_cycle_semantics_source_cohort.py
Actual: 129 passed in 4.66s, exit code 0. py_compile for both affected files: exit code 0. git diff --check for tracked test: exit code 0; new file's unified diff showed no whitespace errors. No full repository suite.

## SOURCE_BYTES_AST_BINDING
P1B checks the bytes actually supplied to this call: SHA-256(raw) must equal SourceSnapshot.source_fingerprint, the supplied indexed hash and P0 evidence raw hash. parse_source_snapshot derives the AST from those exact bytes, including PEP 263 coding declarations, and ast.dump(include_attributes=True) SHA-256 must equal the P0 AST signature. It verifies all modules in each SCC's reachable closure, not just cyclic members. T04 demonstrates that forged P0 AST signature plus recomputed evidence token passes declared-input P0 but fails P1B against independently supplied bytes.

## SOURCE_AUTHORITY_LIMITATIONS
SourceSnapshot bytes are caller-supplied. P1B does not authenticate their LIVE origin, guarantee an atomic graph/source snapshot, establish the revision that produced them, execute imports or prove runtime safety. The existing cycle_semantics LIVE family remained stale after source edits. No SAFE classification is added.

## LIVE_REVISION_BEFORE_AFTER
Before: revision 634, resync_required=false. After: revision 636, resync_required=false, continuity=continuous. Module/graph/topology/cycles and artifact-consumption families fresh; cycle_semantics stale.

## WATCHER_EVENTS
Revision 635: desktop_watcher update_file UPDATED new contextor/core/cycle_semantics/source_proof.py, blast_radius_state=fresh. Revision 636: desktop_watcher update_file UPDATED tests/test_cycle_semantics_evidence.py, blast_radius_state=fresh. get_live_events(after_revision=635) returned continuity=continuous and resync_required=false. No manual update_file.

## WORKSPACE_SYNC
Contextor get_module_context reports source_proof.py workspace_sync=verified at revision 635. At revision 636, get_module_context reports test_cycle_semantics_evidence.py workspace_sync=verified; blast radius for assess_scc_source_bytes also reports workspace_sync=verified and one confirmed test consumer. Global architecture workspace_sync can be unverified by its aggregate read scope; exact edited files are verified.

## RESTART_REQUIREMENTS
No restart performed. New production helper has only a confirmed test consumer; it was not part of an existing serving MCP import path. A future process that must use this new module must import it; current MCP/LIVE restarts are not required for the test-only consumption path. No runtime-loaded-code certification is claimed.

## FULL_DIFFS
The two complete actual unified diffs follow. The new file diff is against /dev/null because it is untracked.

```diff
diff --git a/tests/test_cycle_semantics_evidence.py b/tests/test_cycle_semantics_evidence.py
index 951b475..a44937d 100644
--- a/tests/test_cycle_semantics_evidence.py
+++ b/tests/test_cycle_semantics_evidence.py
@@ -6,8 +6,14 @@ from types import SimpleNamespace
 
 import pytest
 
-from contextor.core.source import ParsedSourceInput
+from contextor.core.source import (
+    ParsedSourceInput,
+    SourceSnapshot,
+    parse_source_snapshot,
+)
 from contextor.core.cycle_semantics.evidence import (
+    EVIDENCE_SEMANTIC_VERSION,
+    _digest,
     SCCModelEvidenceAssessment,
     SCCGenerationModelAssessment,
     assess_index_bound_scc_models as assess,
@@ -15,6 +21,9 @@ from contextor.core.cycle_semantics.evidence import (
     build_source_bound_cycle_evidence as build,
     compare_source_bound_cycle_evidence as compare,
 )
+from contextor.core.cycle_semantics.source_proof import (
+    assess_scc_source_bytes,
+)
 from contextor.core.cycle_semantics.contracts import (
     CycleSemanticsSnapshot, fingerprint_hard_edges,
 )
@@ -609,3 +618,365 @@ def test_p1_t06_deterministic_and_no_mutation():
         repr(evidence),
     )
     json.dumps(asdict(first[0]))
+
+
+# P1B test IDs are local, NOT canonical C01-C30 IDs.
+def _p1b_snapshots(sources):
+    result = {}
+    for module, text in sources.items():
+        raw = text.encode("utf-8")
+        result[module] = SourceSnapshot(
+            raw,
+            hashlib.sha256(raw).hexdigest(),
+        )
+    return result
+
+
+@pytest.mark.parametrize("sources,expected", (
+    (PASS, "MODEL_ALL_FRESH_MEMBER_ENTRIES_PASS"),
+    (HAZARD, "MODEL_INTERNAL_EARLY_BINDING_HAZARD"),
+))
+def test_p1b_t01_bytes_ast_match_preserves_model_only(
+    sources, expected,
+):
+    index, snapshot, evidence = _bound(PAIR, sources)
+    result = assess_scc_source_bytes(
+        PAIR, index, snapshot, evidence,
+        _p1b_snapshots(sources),
+    )
+    assert len(result) == 1
+    assert result[0].model_classification == expected
+    assert result[0].bytes_state == (
+        "BYTE_AST_CONSISTENT_NON_ATOMIC"
+    )
+    assert result[0].authority == (
+        "CALLER_SUPPLIED_BYTES_NOT_ATOMICALLY_BOUND_TO_LIVE"
+    )
+
+
+def test_p1b_t02_source_snapshot_hash_is_recomputed():
+    index, snapshot, evidence = _bound(PAIR, PASS)
+    sources = _p1b_snapshots(PASS)
+    sources["a"] = SourceSnapshot(
+        b"import b\nx=1\n# changed", index["a"]
+    )
+    result = assess_scc_source_bytes(
+        PAIR, index, snapshot, evidence, sources,
+    )
+    assert result[0].model_classification == "INDETERMINATE"
+    assert result[0].bytes_state == "EVIDENCE_MISMATCH"
+    assert result[0].reason == (
+        "SOURCE_SNAPSHOT_HASH_MISMATCH:a"
+    )
+
+
+def test_p1b_t03_changed_bytes_even_with_same_ast():
+    index, snapshot, evidence = _bound(PAIR, PASS)
+    sources = _p1b_snapshots(PASS)
+    raw = (PASS["a"] + "\n# changed").encode("utf-8")
+    sources["a"] = SourceSnapshot(
+        raw, hashlib.sha256(raw).hexdigest()
+    )
+    result = assess_scc_source_bytes(
+        PAIR, index, snapshot, evidence, sources,
+    )
+    assert result[0].reason == (
+        "SOURCE_INDEX_BYTES_MISMATCH:a"
+    )
+
+
+def test_p1b_t04_forged_ast_signature_and_token():
+    index, snapshot, evidence = _bound(PAIR, PASS)
+    component = evidence.components[0]
+    forged = tuple(
+        (
+            module,
+            raw,
+            "f" * 64 if module == "a" else ast_hash,
+        )
+        for module, raw, ast_hash
+        in component.source_signatures
+    )
+    subgraph = tuple(
+        (module, tuple(sorted(PAIR[module])))
+        for module in component.reachable_modules
+    )
+    altered = replace(
+        component,
+        source_signatures=forged,
+        evidence_token=_digest((
+            EVIDENCE_SEMANTIC_VERSION,
+            component.members,
+            subgraph,
+            forged,
+        )),
+    )
+    spoofed = replace(
+        evidence, components=(altered,),
+    )
+
+    # P0 checks consistent declarations but does not
+    # rederive the AST from independently supplied bytes.
+    assert assess(
+        PAIR, index, snapshot, spoofed,
+    )[0].evidence_state == "DECLARED_INPUTS_CONSISTENT"
+
+    result = assess_scc_source_bytes(
+        PAIR, index, snapshot, spoofed,
+        _p1b_snapshots(PASS),
+    )
+    assert result[0].model_classification == "INDETERMINATE"
+    assert result[0].reason == (
+        "SOURCE_AST_BYTES_MISMATCH:a"
+    )
+
+
+def test_p1b_t05_missing_reachable_dependency():
+    graph = {
+        "a": {"b", "dep"},
+        "b": {"a"},
+        "dep": set(),
+    }
+    inputs = {
+        "a": "import b\nimport dep",
+        "b": "import a",
+        "dep": "x=1",
+    }
+    index, snapshot, evidence = _bound(graph, inputs)
+    sources = _p1b_snapshots(inputs)
+    del sources["dep"]
+    result = assess_scc_source_bytes(
+        graph, index, snapshot, evidence, sources,
+    )
+    assert result[0].bytes_state == "UNAVAILABLE"
+    assert result[0].reason == (
+        "SOURCE_BYTES_UNAVAILABLE:dep"
+    )
+
+
+def test_p1b_t06_changed_noncyclic_reachable_dependency():
+    graph = {
+        "a": {"b", "dep"},
+        "b": {"a"},
+        "dep": set(),
+    }
+    inputs = {
+        "a": "import b\nimport dep",
+        "b": "import a",
+        "dep": "x=1",
+    }
+    index, snapshot, evidence = _bound(graph, inputs)
+    sources = _p1b_snapshots(inputs)
+    sources["dep"] = _p1b_snapshots(
+        {"dep": "x=2"}
+    )["dep"]
+    result = assess_scc_source_bytes(
+        graph, index, snapshot, evidence, sources,
+    )
+    assert result[0].reason == (
+        "SOURCE_INDEX_BYTES_MISMATCH:dep"
+    )
+
+
+def test_p1b_t07_unrelated_module_is_not_required():
+    graph = {
+        "a": {"b"},
+        "b": {"a"},
+        "unrelated": set(),
+    }
+    inputs = dict(PASS, unrelated="x=1")
+    index, snapshot, evidence = _bound(graph, inputs)
+    result = assess_scc_source_bytes(
+        graph, index, snapshot, evidence,
+        _p1b_snapshots(PASS),
+    )
+    assert result[0].bytes_state == (
+        "BYTE_AST_CONSISTENT_NON_ATOMIC"
+    )
+
+
+def test_p1b_t08_independent_sccs():
+    graph = {
+        "a": {"b"},
+        "b": {"a"},
+        "x": {"y"},
+        "y": {"x"},
+    }
+    inputs = dict(
+        PASS,
+        x="import y\nn=1",
+        y="import x\nm=2",
+    )
+    index, snapshot, evidence = _bound(graph, inputs)
+    sources = _p1b_snapshots(inputs)
+    sources["x"] = _p1b_snapshots(
+        {"x": "import y\nn=4"}
+    )["x"]
+    result = assess_scc_source_bytes(
+        graph, index, snapshot, evidence, sources,
+    )
+    assert [
+        (item.members, item.bytes_state)
+        for item in result
+    ] == [
+        (("a", "b"), "BYTE_AST_CONSISTENT_NON_ATOMIC"),
+        (("x", "y"), "EVIDENCE_MISMATCH"),
+    ]
+
+
+def test_p1b_t09_invalid_source_bytes_fail_closed():
+    index, snapshot, evidence = _bound(PAIR, PASS)
+    sources = _p1b_snapshots(PASS)
+    invalid = b"import b\nx=)"
+    forged_hash = hashlib.sha256(invalid).hexdigest()
+
+    parsed = _sources(**PASS)
+    parsed["a"] = ParsedSourceInput(
+        parsed["a"].tree, forged_hash,
+    )
+    forged_evidence = build(PAIR, parsed)
+    forged_index = dict(index, a=forged_hash)
+    forged_snapshot = replace(
+        snapshot,
+        observed_source_fingerprints=tuple(
+            sorted(forged_index.items())
+        ),
+        import_sites=analyze_cyclic_import_sites(
+            PAIR, parsed,
+        ),
+    )
+    assert assess(
+        PAIR, forged_index,
+        forged_snapshot, forged_evidence,
+    )[0].evidence_state == "DECLARED_INPUTS_CONSISTENT"
+
+    sources["a"] = SourceSnapshot(
+        invalid, forged_hash,
+    )
+    result = assess_scc_source_bytes(
+        PAIR, forged_index,
+        forged_snapshot, forged_evidence, sources,
+    )
+    assert result[0].reason == (
+        "SOURCE_BYTES_UNPARSABLE:a"
+    )
+
+
+def test_p1b_t10_byte_budgets_and_invalid_arguments():
+    index, snapshot, evidence = _bound(PAIR, PASS)
+    sources = _p1b_snapshots(PASS)
+    result = assess_scc_source_bytes(
+        PAIR, index, snapshot, evidence, sources,
+        max_source_bytes=1,
+    )
+    assert result[0].reason == (
+        "SOURCE_BYTE_BUDGET_EXCEEDED:a"
+    )
+
+    with pytest.raises(TypeError):
+        assess_scc_source_bytes(
+            PAIR, index, snapshot, evidence, None,
+        )
+
+    with pytest.raises(ValueError):
+        assess_scc_source_bytes(
+            PAIR, index, snapshot, evidence, sources,
+            max_source_bytes=True,
+        )
+
+
+def test_p1b_t11_no_cyclic_scc():
+    graph = {"a": {"b"}, "b": set()}
+    inputs = {"a": "import b", "b": "pass"}
+    index, snapshot, evidence = _bound(graph, inputs)
+    assert assess_scc_source_bytes(
+        graph, index, snapshot, evidence, {},
+    ) == ()
+
+
+def test_p1b_t12_p0_incomplete_remains_unavailable():
+    index, snapshot, evidence = _bound(PAIR, PASS)
+    partial = replace(
+        snapshot,
+        coverage_status="PARTIAL_SOURCE_EVIDENCE",
+        observed_source_fingerprints=(
+            ("a", index["a"]),
+        ),
+    )
+    result = assess_scc_source_bytes(
+        PAIR, index, partial, evidence,
+        _p1b_snapshots(PASS),
+    )
+    assert result[0].model_classification == "INDETERMINATE"
+    assert result[0].bytes_state == "UNAVAILABLE"
+    assert result[0].reason == (
+        "INCOMPLETE_CYCLIC_SOURCE_COHORT"
+    )
+
+
+def test_p1b_t13_deterministic_and_immutable_inputs():
+    index, snapshot, evidence = _bound(PAIR, PASS)
+    sources = _p1b_snapshots(PASS)
+    before = repr((index, snapshot, evidence, sources))
+    first = assess_scc_source_bytes(
+        PAIR, index, snapshot, evidence, sources,
+    )
+    assert first == assess_scc_source_bytes(
+        PAIR, index, snapshot, evidence, sources,
+    )
+    assert repr((index, snapshot, evidence, sources)) == before
+    json.dumps(asdict(first[0]))
+
+
+def test_p1b_t14_pep263_encoding_from_exact_bytes():
+    raw_sources = {
+        "a": (
+            b"# coding: latin-1\n"
+            b"import b\n"
+            b"label = '\xe9'\n"
+        ),
+        "b": b"import a\nx=1\n",
+    }
+    sources = {
+        module: SourceSnapshot(
+            raw, hashlib.sha256(raw).hexdigest(),
+        )
+        for module, raw in raw_sources.items()
+    }
+    parsed = {
+        module: parse_source_snapshot(source, module)
+        for module, source in sources.items()
+    }
+    index = {
+        module: source.source_fingerprint
+        for module, source in sources.items()
+    }
+    evidence = build(PAIR, parsed)
+    snapshot = CycleSemanticsSnapshot(
+        graph_sha256=fingerprint_hard_edges(PAIR),
+        cyclic_modules=("a", "b"),
+        observed_source_fingerprints=tuple(
+            sorted(index.items())
+        ),
+        source_issues=(),
+        coverage_status="FILESYSTEM_STABLE_NON_ATOMIC",
+        source_snapshot_binding=(
+            "NOT_ATOMICALLY_VERIFIED_BY_DISCOVERY"
+        ),
+        runtime_execution_status="UNKNOWN_NOT_EVALUATED",
+        import_sites=analyze_cyclic_import_sites(
+            PAIR, parsed,
+        ),
+        conditional_discovery=ConditionalDiscoveryReport(
+            (), 0, (), 0, "COMPLETE",
+        ),
+    )
+    result = assess_scc_source_bytes(
+        PAIR, index, snapshot, evidence, sources,
+    )
+    assert result[0].model_classification == (
+        "MODEL_ALL_FRESH_MEMBER_ENTRIES_PASS"
+    )
+    assert result[0].bytes_state == (
+        "BYTE_AST_CONSISTENT_NON_ATOMIC"
+    )
diff --git a/contextor/core/cycle_semantics/source_proof.py b/contextor/core/cycle_semantics/source_proof.py
new file mode 100644
index 0000000..6c27363
--- /dev/null
+++ b/contextor/core/cycle_semantics/source_proof.py
@@ -0,0 +1,220 @@
+"""Bounded source-byte checks for SCC model evidence.
+
+Caller-supplied byte snapshots are checked against declared index fingerprints
+and AST signatures. This module cannot authenticate LIVE generation or prove
+atomic source capture, import execution, or runtime safety.
+"""
+
+from __future__ import annotations
+
+import ast
+import hashlib
+from collections.abc import Mapping
+from dataclasses import dataclass
+
+from contextor.core.source import (
+    SourceError,
+    SourceSnapshot,
+    parse_source_snapshot,
+)
+
+from .contracts import CycleSemanticsSnapshot
+from .evidence import (
+    SourceBoundCycleEvidence,
+    assess_index_bound_scc_models,
+)
+
+
+_BYTE_AUTHORITY = (
+    "CALLER_SUPPLIED_BYTES_NOT_ATOMICALLY_BOUND_TO_LIVE"
+)
+
+
+@dataclass(frozen=True)
+class SCCSourceByteAssessment:
+    members: tuple[str, ...]
+    model_classification: str
+    bytes_state: str
+    reason: str | None
+    authority: str = _BYTE_AUTHORITY
+
+
+def assess_scc_source_bytes(
+    hard_edges: Mapping[str, object],
+    indexed_fingerprints_by_module: Mapping[str, str],
+    snapshot: CycleSemanticsSnapshot,
+    source_evidence: SourceBoundCycleEvidence,
+    source_snapshots: Mapping[str, SourceSnapshot],
+    *,
+    max_source_bytes: int = 2 * 1024 * 1024,
+    max_closure_bytes: int = 32 * 1024 * 1024,
+) -> tuple[SCCSourceByteAssessment, ...]:
+    """Verify actual source bytes against P0 AST and index evidence.
+
+    Source snapshots are caller-supplied, not authenticated LIVE data.
+    No disk I/O, IPC, analyzed-module imports or model execution.
+    """
+    if not isinstance(source_snapshots, Mapping):
+        raise TypeError("source_snapshots must be a mapping")
+
+    if (
+        type(max_source_bytes) is not int
+        or not 1 <= max_source_bytes <= 64 * 1024 * 1024
+    ):
+        raise ValueError("max_source_bytes out of range")
+
+    if (
+        type(max_closure_bytes) is not int
+        or not 1 <= max_closure_bytes <= 256 * 1024 * 1024
+    ):
+        raise ValueError("max_closure_bytes out of range")
+
+    # P0 remains the sole owner of declared graph/index/model
+    # consistency. P1B verifies bytes and reconstructed AST.
+    model_results = assess_index_bound_scc_models(
+        hard_edges,
+        indexed_fingerprints_by_module,
+        snapshot,
+        source_evidence,
+    )
+
+    assessments: list[SCCSourceByteAssessment] = []
+
+    # Reuse parsed hashes for closure members shared by SCCs.
+    # Cache is execution-local and does not certify generation.
+    cache: dict[str, tuple[str, str | None]] = {}
+
+    for position, model in enumerate(model_results):
+        members = model.members
+
+        def unavailable(reason: str) -> SCCSourceByteAssessment:
+            return SCCSourceByteAssessment(
+                members,
+                "INDETERMINATE",
+                "UNAVAILABLE",
+                reason,
+            )
+
+        def mismatch(reason: str) -> SCCSourceByteAssessment:
+            return SCCSourceByteAssessment(
+                members,
+                "INDETERMINATE",
+                "EVIDENCE_MISMATCH",
+                reason,
+            )
+
+        if model.evidence_state != "DECLARED_INPUTS_CONSISTENT":
+            assessments.append(unavailable(
+                model.reason or "P0_MODEL_EVIDENCE_UNAVAILABLE"
+            ))
+            continue
+
+        # P0 has already verified exact component ordering,
+        # SCC membership, closure identity and evidence tokens.
+        component = source_evidence.components[position]
+        closure = component.reachable_modules
+        signatures = {
+            module: (raw_hash, ast_hash)
+            for module, raw_hash, ast_hash
+            in component.source_signatures
+        }
+
+        total_bytes = 0
+        outcome: SCCSourceByteAssessment | None = None
+
+        for module in closure:
+            supplied = source_snapshots.get(module)
+
+            if (
+                not isinstance(supplied, SourceSnapshot)
+                or type(supplied.raw) is not bytes
+            ):
+                outcome = unavailable(
+                    "SOURCE_BYTES_UNAVAILABLE:" + module
+                )
+                break
+
+            size = len(supplied.raw)
+
+            if (
+                size > max_source_bytes
+                or total_bytes + size > max_closure_bytes
+            ):
+                outcome = unavailable(
+                    "SOURCE_BYTE_BUDGET_EXCEEDED:" + module
+                )
+                break
+
+            total_bytes += size
+
+            # Do not trust the SourceSnapshot fingerprint
+            # until it has been recomputed from its raw bytes.
+            actual = hashlib.sha256(
+                supplied.raw
+            ).hexdigest()
+
+            if actual != supplied.source_fingerprint:
+                outcome = mismatch(
+                    "SOURCE_SNAPSHOT_HASH_MISMATCH:" + module
+                )
+                break
+
+            if actual != indexed_fingerprints_by_module.get(
+                module
+            ):
+                outcome = mismatch(
+                    "SOURCE_INDEX_BYTES_MISMATCH:" + module
+                )
+                break
+
+            if actual != signatures[module][0]:
+                outcome = mismatch(
+                    "SOURCE_EVIDENCE_BYTES_MISMATCH:" + module
+                )
+                break
+
+            cached = cache.get(module)
+
+            if cached is None or cached[0] != actual:
+                try:
+                    parsed = parse_source_snapshot(
+                        supplied,
+                        module,
+                    )
+                except SourceError:
+                    cache[module] = (actual, None)
+                else:
+                    ast_hash = hashlib.sha256(
+                        ast.dump(
+                            parsed.tree,
+                            include_attributes=True,
+                        ).encode("utf-8")
+                    ).hexdigest()
+
+                    cache[module] = (actual, ast_hash)
+
+            observed_ast = cache[module][1]
+
+            if observed_ast is None:
+                outcome = unavailable(
+                    "SOURCE_BYTES_UNPARSABLE:" + module
+                )
+                break
+
+            if observed_ast != signatures[module][1]:
+                outcome = mismatch(
+                    "SOURCE_AST_BYTES_MISMATCH:" + module
+                )
+                break
+
+        if outcome is not None:
+            assessments.append(outcome)
+        else:
+            assessments.append(SCCSourceByteAssessment(
+                members,
+                model.model_classification,
+                "BYTE_AST_CONSISTENT_NON_ATOMIC",
+                None,
+            ))
+
+    return tuple(assessments)
```

## FINAL_VERDICT
PASS for the exact P1B implementation, targeted and focused tests, source/test watcher adoption, and verified per-file workspace synchronization. The result remains caller-supplied, non-atomic byte/AST model evidence.
