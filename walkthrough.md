# CONTEXTOR C16-B03-P1D2A

## PREFLIGHT

Local HEAD 85721d4ce7fd65da0dbd442f6904b8d7d179b21a, matching the supplied source reference. Initial worktree clean. Contextor MCP preflight: evidence and scenarios source verified at canonical revision 1005; structural DFS path count 16; cycle_semantics stale. Exact anchors and replacement function matched local source. New test path did not exist.

## EXACT_CHANGE

Applied the supplied literal implementation to contextor/core/cycle_semantics/evidence.py by direct apply_patch edits. Added tests/test_cycle_semantics_optional_child_evidence.py with the supplied content. HARD_ONLY remains default with semantic version /3. Optional evidence uses semantic version /4, source_selection=OPTIONAL_NAMED_CHILDREN, exact P1A closure identity, selected AST ImportRef replay, optional scenario evaluation and version-bound component token. The existing hard-only index-bound verifier rejects optional evidence, including a forged /3 version. No optional certification or publication was added.

## TARGETED_TESTS

The three specified modules passed: 95 passed, 0 failed. Command used CPython 3.15.2 .venv with -B -q -rs -p no:cacheprovider and external --basetemp C:\Temp\Contextor_C16_P1D2A_pytest_tmp. No full pytest.

## MCP_POST_CHANGE_AUDIT

At canonical revision 1008, evidence and the new test module report canonical_state=fresh, workspace_sync=verified, advisory_warning=null. Structural DFS path count remains 16. cycle_semantics=stale; current semantic SCC claims and loaded backend code adoption are unproven. No FULL, update_file, restart, dependency install or commit.

## FILES_CHANGED

- contextor/core/cycle_semantics/evidence.py
- tests/test_cycle_semantics_optional_child_evidence.py

walkthrough.md is the report.

## FULL_DIFFS

```diff
diff --git a/contextor/core/cycle_semantics/evidence.py b/contextor/core/cycle_semantics/evidence.py
index e3751df..5a5a59a 100644
--- a/contextor/core/cycle_semantics/evidence.py
+++ b/contextor/core/cycle_semantics/evidence.py
@@ -19,13 +19,18 @@ from .contracts import CycleSemanticsSnapshot, fingerprint_hard_edges
 from .scc import analyze_import_cycle_topology
 from .initialization_model import ImportOrderAssessment, ModelEvent
 from .package_model import PackageImportAssessment, PackageModelEvent
-from .model_source_closure import compute_cycle_model_source_closures
+from .model_source_closure import (
+    CycleModelSourceClosure,
+    compute_cycle_model_source_closures,
+    compute_cycle_model_source_closures_with_optional_children,
+)
 from .model_identity import indexed_to_logical_module, logical_to_indexed_module
 from .scenarios import (
     CycleComponentScenarios, CycleScenarioReport, analyze_cycle_scenarios,
 )
 
 EVIDENCE_SEMANTIC_VERSION = "cycle-semantics-evidence/3"
+OPTIONAL_EVIDENCE_SEMANTIC_VERSION = "cycle-semantics-evidence/4"
 _MISSING = "MISSING"
 
 
@@ -55,10 +60,16 @@ def _component_token(
     subgraph: tuple[tuple[str, tuple[str, ...]], ...],
     signatures: tuple[tuple[str, str, str], ...],
     scenario: CycleComponentScenarios,
+    *,
+    semantic_version: str = EVIDENCE_SEMANTIC_VERSION,
 ) -> str:
     return _digest((
-        EVIDENCE_SEMANTIC_VERSION, members, subgraph, signatures,
-        scenario.model_kind, scenario.evidence_scope,
+        semantic_version,
+        members,
+        subgraph,
+        signatures,
+        scenario.model_kind,
+        scenario.evidence_scope,
         _scenario_fingerprint(scenario),
     ))
 
@@ -71,6 +82,7 @@ class SourceBoundCycleEvidence:
     components: tuple[ComponentSourceEvidence, ...]
     scenarios: CycleScenarioReport
     authority: str = "SNAPSHOT_ONLY_NOT_LIVE_FRESHNESS"
+    source_selection: str = "HARD_ONLY"
 
 
 @dataclass(frozen=True)
@@ -142,6 +154,8 @@ def assess_index_bound_scc_models(
         global_reason = "SCC_TOPOLOGY_MISMATCH"
     elif source_evidence.semantic_version != EVIDENCE_SEMANTIC_VERSION:
         global_reason = "EVIDENCE_SEMANTIC_VERSION_MISMATCH"
+    elif source_evidence.source_selection != "HARD_ONLY":
+        global_reason = "SOURCE_SELECTION_UNSUPPORTED_BY_HARD_ONLY_VERIFIER"
     elif (
         source_evidence.authority != "SNAPSHOT_ONLY_NOT_LIVE_FRESHNESS"
         or source_evidence.scenarios.evidence_scope
@@ -534,61 +548,186 @@ def assess_live_generation_scc_models(
 
 
 def build_source_bound_cycle_evidence(
-    hard_edges: Mapping[str, set[str] | frozenset[str] | list[str] | tuple[str, ...]],
+    hard_edges: Mapping[
+        str, set[str] | frozenset[str] | list[str] | tuple[str, ...]
+    ],
     parsed_sources: Mapping[str, ParsedSourceInput],
+    *,
+    source_selection: str = "HARD_ONLY",
+    indexed_imports_by_module: Mapping[str, object] | None = None,
+    package_root: str | None = None,
+    source_closures: tuple[CycleModelSourceClosure, ...] | None = None,
 ) -> SourceBoundCycleEvidence:
-    """Bind an SCC scenario report to graph and exact source-snapshot evidence.
-
-    ParsedSourceInput is expected from parse_source_snapshot/with_fingerprint.
-    In-memory AST hashes guard against inconsistent caller-provided AST objects.
-    No disk source freshness or LIVE authority is established by this function.
-    """
+    """Build snapshot-only evidence; never certify LIVE or publication."""
     if not isinstance(parsed_sources, Mapping):
         raise TypeError("parsed_sources must be a mapping")
 
     signatures: dict[str, tuple[str, str]] = {}
     trees: dict[str, ast.Module] = {}
+
     for module, source in parsed_sources.items():
         if not isinstance(module, str) or not module:
             raise ValueError("invalid source module identity")
-        if not isinstance(source, ParsedSourceInput) or not isinstance(source.tree, ast.Module):
-            raise TypeError("sources must contain parsed ast.Module snapshots")
+        if (
+            not isinstance(source, ParsedSourceInput)
+            or not isinstance(source.tree, ast.Module)
+        ):
+            raise TypeError(
+                "sources must contain parsed ast.Module snapshots"
+            )
+
         raw_fingerprint = source.source_fingerprint
         if (
             not isinstance(raw_fingerprint, str)
             or len(raw_fingerprint) != 64
-            or any(ch not in "0123456789abcdef" for ch in raw_fingerprint)
+            or any(
+                ch not in "0123456789abcdef"
+                for ch in raw_fingerprint
+            )
         ):
-            raise ValueError("source_fingerprint must be a lowercase SHA-256 digest")
+            raise ValueError(
+                "source_fingerprint must be a lowercase SHA-256 digest"
+            )
+
         ast_fingerprint = hashlib.sha256(
-            ast.dump(source.tree, include_attributes=True).encode("utf-8")
+            ast.dump(
+                source.tree, include_attributes=True
+            ).encode("utf-8")
         ).hexdigest()
+
         signatures[module] = (raw_fingerprint, ast_fingerprint)
         trees[module] = source.tree
 
-    report = analyze_cycle_scenarios(hard_edges, trees)
+    if source_selection == "HARD_ONLY":
+        if (
+            indexed_imports_by_module is not None
+            or package_root is not None
+            or source_closures is not None
+        ):
+            raise ValueError(
+                "HARD_ONLY_OPTIONAL_INPUTS_UNSUPPORTED"
+            )
+
+        closures = compute_cycle_model_source_closures(hard_edges)
+        semantic_version = EVIDENCE_SEMANTIC_VERSION
+        report = analyze_cycle_scenarios(hard_edges, trees)
+
+    elif source_selection == "OPTIONAL_NAMED_CHILDREN":
+        if (
+            not isinstance(indexed_imports_by_module, Mapping)
+            or type(source_closures) is not tuple
+            or any(
+                type(row) is not CycleModelSourceClosure
+                for row in source_closures
+            )
+        ):
+            raise ValueError(
+                "OPTIONAL_COHORT_IDENTITY_MISMATCH"
+            )
+
+        expected = (
+            compute_cycle_model_source_closures_with_optional_children(
+                hard_edges,
+                indexed_imports_by_module,
+                package_root=package_root,
+            )
+        )
+        if source_closures != expected:
+            raise ValueError(
+                "OPTIONAL_COHORT_IDENTITY_MISMATCH"
+            )
+
+        closures = expected
+        semantic_version = OPTIONAL_EVIDENCE_SEMANTIC_VERSION
+
+        # AST replay uses only supplied AST; read_imports receives
+        # tree explicitly, therefore it does not read source files.
+        from pathlib import Path
+        from contextor.core.symbol_engine.indexer import read_imports
+
+        selected = sorted({
+            module
+            for closure in closures
+            for module in closure.evidence_source_modules
+        })
+
+        for module in selected:
+            tree = trees.get(module)
+            if tree is None:
+                continue
+
+            extracted, error = read_imports(
+                Path(*module.split(".")).with_suffix(".py"),
+                tree=tree,
+            )
+            if extracted is None or error is not None:
+                raise ValueError(
+                    "OPTIONAL_IMPORT_REPLAY_UNAVAILABLE:" + module
+                )
+
+            indexed = indexed_imports_by_module[module]
+            if tuple(extracted) != tuple(indexed):
+                raise ValueError(
+                    "OPTIONAL_IMPORT_FACTS_MISMATCH:" + module
+                )
+
+        report = analyze_cycle_scenarios(
+            hard_edges,
+            trees,
+            source_selection="OPTIONAL_NAMED_CHILDREN",
+            indexed_imports_by_module=indexed_imports_by_module,
+            package_root=package_root,
+            source_closures=closures,
+        )
+
+    else:
+        raise ValueError("SOURCE_SELECTION_INVALID")
+
     adjacency: dict[str, tuple[str, ...]] = {
-        source: tuple(sorted(set(targets))) for source, targets in hard_edges.items()
+        source: tuple(sorted(set(targets)))
+        for source, targets in hard_edges.items()
     }
     for targets in tuple(adjacency.values()):
         for target in targets:
             adjacency.setdefault(target, ())
-    graph_items = tuple((node, adjacency[node]) for node in sorted(adjacency))
+
+    graph_items = tuple(
+        (node, adjacency[node])
+        for node in sorted(adjacency)
+    )
     graph_fingerprint = _digest(graph_items)
-    source_manifest = tuple((name, *signatures[name]) for name in sorted(signatures))
+
+    source_manifest = tuple(
+        (name, *signatures[name])
+        for name in sorted(signatures)
+    )
 
     components: list[ComponentSourceEvidence] = []
-    closures = compute_cycle_model_source_closures(hard_edges)
+
     for component, closure_row in zip(report.components, closures):
         closure = closure_row.evidence_source_modules
+
         source_signatures = tuple(
-            (module, *signatures.get(module, (_MISSING, _MISSING)))
+            (
+                module,
+                *signatures.get(module, (_MISSING, _MISSING)),
+            )
             for module in closure
         )
-        subgraph = tuple((node, adjacency[node]) for node in closure)
+
+        subgraph = tuple(
+            (node, adjacency[node])
+            for node in closure
+        )
+
         token = _component_token(
-            component.members, subgraph, source_signatures, component,
+            component.members,
+            subgraph,
+            source_signatures,
+            component,
+            semantic_version=semantic_version,
         )
+
         components.append(ComponentSourceEvidence(
             members=component.members,
             reachable_modules=closure,
@@ -601,11 +740,12 @@ def build_source_bound_cycle_evidence(
         ))
 
     return SourceBoundCycleEvidence(
-        semantic_version=EVIDENCE_SEMANTIC_VERSION,
+        semantic_version=semantic_version,
         graph_fingerprint=graph_fingerprint,
         source_manifest_fingerprint=_digest(source_manifest),
         components=tuple(components),
         scenarios=report,
+        source_selection=source_selection,
     )
diff --git a/tests/test_cycle_semantics_optional_child_evidence.py b/tests/test_cycle_semantics_optional_child_evidence.py
new file mode 100644
index 0000000..e95539f
--- /dev/null
+++ b/tests/test_cycle_semantics_optional_child_evidence.py
@@ -0,0 +1,212 @@
+"""P1D2A: optional source evidence remains snapshot-only."""
+
+import ast
+import hashlib
+from dataclasses import replace
+from pathlib import Path
+
+import pytest
+
+from contextor.core.source import ParsedSourceInput
+from contextor.core.cycle_semantics.evidence import (
+    EVIDENCE_SEMANTIC_VERSION,
+    OPTIONAL_EVIDENCE_SEMANTIC_VERSION,
+    assess_index_bound_scc_models,
+    build_source_bound_cycle_evidence,
+)
+from tests.test_cycle_semantics_optional_child_scenarios import _case
+from tests.test_cycle_semantics_evidence import _bound
+
+
+def _inputs(tmp_path, case):
+    parsed = {}
+    source_text = {}
+    for module, tree in case[1].items():
+        path = (
+            tmp_path / "repo"
+            / Path(*module.split(".")).with_suffix(".py")
+        )
+        raw = path.read_bytes()
+        parsed[module] = ParsedSourceInput(
+            tree, hashlib.sha256(raw).hexdigest()
+        )
+        source_text[module] = raw.decode("utf-8")
+    return parsed, source_text
+
+
+def _build(case, parsed):
+    graph, _, imports, package_root, closures = case
+    return build_source_bound_cycle_evidence(
+        graph.hard_edges,
+        parsed,
+        source_selection="OPTIONAL_NAMED_CHILDREN",
+        indexed_imports_by_module=imports,
+        package_root=package_root,
+        source_closures=closures,
+    )
+
+
+def test_optional_identity_and_selected_sources(tmp_path):
+    case = _case(tmp_path)
+    parsed, _ = _inputs(tmp_path, case)
+
+    evidence = _build(case, parsed)
+    assert evidence.semantic_version == (
+        OPTIONAL_EVIDENCE_SEMANTIC_VERSION
+    )
+    assert evidence.source_selection == "OPTIONAL_NAMED_CHILDREN"
+    assert evidence.components[0].reachable_modules == (
+        case[4][0].evidence_source_modules
+    )
+    assert "pkg.child" in evidence.components[0].reachable_modules
+    assert evidence.scenarios.evidence_scope == (
+        "OPTIONAL_NAMED_CHILDREN_SCENARIO_MODEL_NOT_RUNTIME_CERTIFICATION"
+    )
+    assert evidence == _build(case, parsed)
+
+
+def test_optional_child_byte_identity_changes_token(tmp_path):
+    case = _case(tmp_path)
+    parsed, _ = _inputs(tmp_path, case)
+    before = _build(case, parsed)
+
+    raw = b"pass\nx = 1\n"
+    changed = dict(parsed)
+    changed["pkg.child"] = ParsedSourceInput(
+        ast.parse(raw),
+        hashlib.sha256(raw).hexdigest(),
+    )
+
+    after = _build(case, changed)
+    assert (
+        before.components[0].evidence_token
+        != after.components[0].evidence_token
+    )
+    assert (
+        before.graph_fingerprint
+        == after.graph_fingerprint
+    )
+
+
+def test_old_hard_only_version_and_default(tmp_path):
+    case = _case(tmp_path)
+    parsed, _ = _inputs(tmp_path, case)
+    graph = case[0]
+
+    default = build_source_bound_cycle_evidence(
+        graph.hard_edges, parsed
+    )
+    explicit = build_source_bound_cycle_evidence(
+        graph.hard_edges, parsed,
+        source_selection="HARD_ONLY",
+    )
+
+    assert default == explicit
+    assert default.semantic_version == EVIDENCE_SEMANTIC_VERSION
+    assert default.source_selection == "HARD_ONLY"
+
+
+def test_invalid_cohort_rejected(tmp_path):
+    case = _case(tmp_path)
+    parsed, _ = _inputs(tmp_path, case)
+    graph, _, imports, root, closures = case
+
+    with pytest.raises(ValueError, match="OPTIONAL_COHORT"):
+        build_source_bound_cycle_evidence(
+            graph.hard_edges,
+            parsed,
+            source_selection="OPTIONAL_NAMED_CHILDREN",
+            indexed_imports_by_module=imports,
+            package_root=root,
+            source_closures=(),
+        )
+
+    with pytest.raises(ValueError, match="HARD_ONLY_OPTIONAL"):
+        build_source_bound_cycle_evidence(
+            graph.hard_edges,
+            parsed,
+            indexed_imports_by_module=imports,
+        )
+
+    with pytest.raises(ValueError, match="SOURCE_SELECTION_INVALID"):
+        build_source_bound_cycle_evidence(
+            graph.hard_edges,
+            parsed,
+            source_selection="UNKNOWN",
+        )
+
+
+def test_indexed_import_fact_mismatch_rejected(tmp_path):
+    case = _case(tmp_path)
+    parsed, _ = _inputs(tmp_path, case)
+    graph, _, imports, root, closures = case
+
+    corrupted = dict(imports)
+    corrupted["pkg.b"] = []
+
+    with pytest.raises(
+        ValueError, match="OPTIONAL_IMPORT_FACTS_MISMATCH:pkg.b"
+    ):
+        build_source_bound_cycle_evidence(
+            graph.hard_edges,
+            parsed,
+            source_selection="OPTIONAL_NAMED_CHILDREN",
+            indexed_imports_by_module=corrupted,
+            package_root=root,
+            source_closures=closures,
+        )
+
+
+def test_missing_selected_source_never_proves_pass(tmp_path):
+    case = _case(tmp_path)
+    parsed, _ = _inputs(tmp_path, case)
+    parsed.pop("pkg.child")
+
+    evidence = _build(case, parsed)
+    assert evidence.components[0].classification == "INDETERMINATE"
+    assert evidence.components[0].reason == "MISSING_OR_INVALID_SOURCE"
+    assert "MISSING" in evidence.components[0].source_signatures[
+        tuple(evidence.components[0].reachable_modules).index(
+            "pkg.child"
+        )
+    ]
+
+
+def test_legacy_verifier_rejects_optional_evidence(tmp_path):
+    case = _case(tmp_path)
+    parsed, sources = _inputs(tmp_path, case)
+    graph = case[0]
+
+    evidence = _build(case, parsed)
+    index, snapshot, _ = _bound(graph.hard_edges, sources)
+
+    result = assess_index_bound_scc_models(
+        graph.hard_edges,
+        index,
+        snapshot,
+        evidence,
+    )
+    assert all(
+        row.evidence_state != "DECLARED_INPUTS_CONSISTENT"
+        for row in result
+    )
+    assert all(
+        row.reason == "EVIDENCE_SEMANTIC_VERSION_MISMATCH"
+        for row in result
+    )
+
+    forged_version = replace(
+        evidence,
+        semantic_version=EVIDENCE_SEMANTIC_VERSION,
+    )
+    result = assess_index_bound_scc_models(
+        graph.hard_edges,
+        index,
+        snapshot,
+        forged_version,
+    )
+    assert all(
+        row.reason
+        == "SOURCE_SELECTION_UNSUPPORTED_BY_HARD_ONLY_VERIFIER"
+        for row in result
+    )
```

## FINAL_VERDICT

PASS

P1D2A provides snapshot-only optional evidence. It does not certify optional source bytes against a new verifier or complete P1D2.
