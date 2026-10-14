# CONTEXTOR_B0G4B7_SOURCE_BOUND_CYCLE_EVIDENCE

## HEAD_BEFORE
3057087843d24572992f52fd8d08f47272543653. Git status clean. B0G4B6 scenarios.py and prior cycle_semantics components existed. Both B0G4B7 target files were absent. Contextor resolved ParsedSourceInput to contextor.core.source, with a frozen dataclass containing tree: ast.AST and source_fingerprint: str; its source was complete and workspace_sync=verified.

## HEAD_AFTER
3057087843d24572992f52fd8d08f47272543653. No commit. Git status shows only the two new task files as untracked.

## LIVE_REVISION_BEFORE
416; activity_epoch=1beab26da2ff4932852caa7db6ff4242; continuity=continuous; resync_required=false; canonical_state=fresh; name_collisions=0 fresh; structural cycles=16 fresh. Global workspace_sync=unverified. Contextor identified scenarios.py as the existing SCC scenario owner with only its targeted test as direct consumer and no downstream consumers.

## LIVE_REVISION_AFTER
418; same activity_epoch; continuity=continuous; resync_required=false; canonical_state=fresh; all reported families fresh; no parse-stale modules; name_collisions=0; structural cycles=16. Desktop watcher revision 417 UPDATED evidence.py and revision 418 UPDATED test_cycle_semantics_evidence.py, both blast_radius_state=fresh. New production module workspace_sync=verified by full get_file_edit_context at revision 418; global project overlay remains unverified.

## FILES_CHANGED
- contextor/core/cycle_semantics/evidence.py (new)
- tests/test_cycle_semantics_evidence.py (new)

No existing production/test file or __init__.py changed. walkthrough.md is this report and excluded from source/test diff accounting.

## IMPLEMENTATION_CONTRACT
CONTRACT_PROVED: The exact auditor-supplied two files were written with one final newline. build_source_bound_cycle_evidence accepts an in-memory hard-edge graph and ParsedSourceInput snapshots, validates source identity and lowercase SHA-256 fingerprints, hashes the supplied AST including attributes, joins the existing SCC scenario report, computes graph and source-manifest fingerprints, and issues per-SCC tokens from semantic version, members, reachable subgraph and complete closure source signatures. Missing reachable sources remain explicit MISSING values. compare_source_bound_cycle_evidence emits only MODEL_CLASSIFICATION_CHANGED, EVIDENCE_REVISED, STRUCTURE_ADDED and STRUCTURE_REMOVED when appropriate. Output dataclasses are frozen.
CODE_PATH_PROVED: Production code uses caller-supplied graph and AST snapshots; it does not read disk source, execute analyzed AST, mutate the canonical graph, publish warnings or emit LIVE diagnostic_changes. Contextor reports the new module's only direct consumer as tests.test_cycle_semantics_evidence, with zero downstream consumers.

## TEST_COMMAND
Pre-edit: `& .\.venv\Scripts\python.exe -m pytest -q tests/test_cycle_semantics_scenarios.py tests/test_cycle_semantics_scc.py tests/test_cycle_semantics_initialization_model.py tests/test_cycle_semantics_binding_order.py tests/test_cycle_semantics_guards.py tests/test_cycle_semantics_execution_context.py tests/test_cycle_semantics_provenance.py`
Post-edit: `& .\.venv\Scripts\python.exe -m pytest -q tests/test_cycle_semantics_evidence.py tests/test_cycle_semantics_scenarios.py tests/test_cycle_semantics_scc.py tests/test_cycle_semantics_initialization_model.py tests/test_cycle_semantics_binding_order.py tests/test_cycle_semantics_guards.py tests/test_cycle_semantics_execution_context.py tests/test_cycle_semantics_provenance.py`

## TEST_RESULTS
Repository Python 3.10.9. Pre-edit exit 0: 108 passed in 3.19s. Post-edit exit 0: 121 passed in 3.94s (13 new plus 108 existing). No other tests, full suite or FULL analysis run. New production syntax diagnostics are fresh and empty at revision 418.

## SOURCE_FINGERPRINT_EVIDENCE
CONTRACT_PROVED: Graph identity uses normalized sorted hard-edge adjacency. Source manifest uses raw SHA-256 and AST SHA-256 for each supplied module. Per-SCC evidence token covers the component's complete reachable dependency closure, including explicit MISSING signatures. A source-only binding-order edit changes the token despite unchanged graph; AST attribute tampering changes the AST fingerprint even with a spoofed unchanged raw hash. Tests cover both. The caller remains responsible for snapshot provenance and disk freshness.

## SEMANTIC_TRANSITION_EVIDENCE
CONTRACT_PROVED: With identical hard edges, moving a binding before an import changes the model classification and emits MODEL_CLASSIFICATION_CHANGED. A comment-only source change revises evidence without changing classification and emits EVIDENCE_REVISED. A graph change removing a cyclic SCC emits STRUCTURE_REMOVED. These are model evidence transitions, not user-visible warning ADD/RESOLVE events. Tests confirm no RESOLVED action is emitted.

## UNRELATED_CHANGE_ISOLATION
CONTRACT_PROVED: A source change outside the SCC's reachable closure changes the global source-manifest fingerprint but leaves that SCC's token unchanged and produces no per-SCC transition. A reachable noncyclic dependency change does revise the SCC token. Tests cover independent SCCs so only the affected component changes.

## COLLISION_COUNT_BEFORE_AFTER
0 -> 0 from fresh canonical get_name_collisions at revisions 416 and 418. No new name collision.

## STRUCTURAL_CYCLE_COUNT_BEFORE_AFTER
16 -> 16 from fresh canonical diagnostics. Existing graph and cycle detection code were untouched. Watcher indexing of two new modules may add ordinary dependency edges; a byte-identical whole-repository graph is not claimed.

## NO_SAFETY_CERTIFICATION
CODE_PATH_PROVED: Authority is SNAPSHOT_ONLY_NOT_LIVE_FRESHNESS, and scenario evidence_scope remains SCENARIO_MODEL_NOT_RUNTIME_CERTIFICATION. No SAFE, RUNTIME_CONFIRMED or NO_INITIALIZATION_HAZARD state is emitted. Missing and mismatched source scenarios remain INDETERMINATE.

## NO_WARNING_SUPPRESSION
CODE_PATH_PROVED: ArchitectureCycle/warning publication code was neither edited nor called. No LIVE_DIAGNOSTIC_CYCLE_RESOLVED action is emitted. Canonical structural cycles remain 16.

## NO_DIRECT_LIVE_PUBLICATION
CODE_PATH_PROVED: The new module is imported only by its targeted test and is not exported from __init__.py or integrated with FULL/incremental, MCP, LIVE, Desktop or snapshots. Desktop watcher indexing is external observation. No direct update_file, restart or commit.

## UNRESOLVED_LIMITATIONS
UNKNOWN: This component cannot verify that the caller's ParsedSourceInput matches current disk bytes or LIVE authority. It cannot certify runtime safety or failure from model evidence. Global project workspace_sync is unverified in the overlay, although the new production file was verified against disk. Only closed, supported scenario inputs yield determinate model classifications.

## FINAL_VERDICT
B0G4B7_PASS — exact isolated two-file implementation, 121 focused tests passed, both watcher events observed, fresh canonical state, zero name collisions and unchanged structural cycle count. Await `proceduj`.

## FULL_DIFFS

### FULL_DIFF: contextor/core/cycle_semantics/evidence.py

diff --git a/contextor/core/cycle_semantics/evidence.py b/contextor/core/cycle_semantics/evidence.py
new file mode 100644
index 0000000..b691410
--- /dev/null
+++ b/contextor/core/cycle_semantics/evidence.py
@@ -0,0 +1,179 @@
+"""Source-bound, snapshot-only evidence for cyclic SCC scenario assessments.
+
+Tokens invalidate on source-only semantic changes, even with identical hard edges.
+This module neither establishes current LIVE freshness nor publishes warnings.
+"""
+
+from __future__ import annotations
+
+import ast
+import hashlib
+import json
+from collections.abc import Mapping
+from dataclasses import dataclass
+
+from contextor.core.source import ParsedSourceInput
+
+from .scenarios import CycleScenarioReport, analyze_cycle_scenarios
+
+EVIDENCE_SEMANTIC_VERSION = "cycle-semantics-evidence/1"
+_MISSING = "MISSING"
+
+
+def _digest(value: object) -> str:
+    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
+    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
+
+
+@dataclass(frozen=True)
+class ComponentSourceEvidence:
+    members: tuple[str, ...]
+    reachable_modules: tuple[str, ...]
+    source_signatures: tuple[tuple[str, str, str], ...]
+    evidence_token: str
+    classification: str
+    coverage: str
+    reason: str | None
+
+
+@dataclass(frozen=True)
+class SourceBoundCycleEvidence:
+    semantic_version: str
+    graph_fingerprint: str
+    source_manifest_fingerprint: str
+    components: tuple[ComponentSourceEvidence, ...]
+    scenarios: CycleScenarioReport
+    authority: str = "SNAPSHOT_ONLY_NOT_LIVE_FRESHNESS"
+
+
+@dataclass(frozen=True)
+class CycleEvidenceChange:
+    members: tuple[str, ...]
+    change: str
+    before: str | None
+    after: str | None
+    before_token: str | None
+    after_token: str | None
+
+
+def build_source_bound_cycle_evidence(
+    hard_edges: Mapping[str, set[str] | frozenset[str] | list[str] | tuple[str, ...]],
+    parsed_sources: Mapping[str, ParsedSourceInput],
+) -> SourceBoundCycleEvidence:
+    """Bind an SCC scenario report to graph and exact source-snapshot evidence.
+
+    ParsedSourceInput is expected from parse_source_snapshot/with_fingerprint.
+    In-memory AST hashes guard against inconsistent caller-provided AST objects.
+    No disk source freshness or LIVE authority is established by this function.
+    """
+    if not isinstance(parsed_sources, Mapping):
+        raise TypeError("parsed_sources must be a mapping")
+
+    signatures: dict[str, tuple[str, str]] = {}
+    trees: dict[str, ast.Module] = {}
+    for module, source in parsed_sources.items():
+        if not isinstance(module, str) or not module:
+            raise ValueError("invalid source module identity")
+        if not isinstance(source, ParsedSourceInput) or not isinstance(source.tree, ast.Module):
+            raise TypeError("sources must contain parsed ast.Module snapshots")
+        raw_fingerprint = source.source_fingerprint
+        if (
+            not isinstance(raw_fingerprint, str)
+            or len(raw_fingerprint) != 64
+            or any(ch not in "0123456789abcdef" for ch in raw_fingerprint)
+        ):
+            raise ValueError("source_fingerprint must be a lowercase SHA-256 digest")
+        ast_fingerprint = hashlib.sha256(
+            ast.dump(source.tree, include_attributes=True).encode("utf-8")
+        ).hexdigest()
+        signatures[module] = (raw_fingerprint, ast_fingerprint)
+        trees[module] = source.tree
+
+    report = analyze_cycle_scenarios(hard_edges, trees)
+    adjacency: dict[str, tuple[str, ...]] = {
+        source: tuple(sorted(set(targets))) for source, targets in hard_edges.items()
+    }
+    for targets in tuple(adjacency.values()):
+        for target in targets:
+            adjacency.setdefault(target, ())
+    graph_items = tuple((node, adjacency[node]) for node in sorted(adjacency))
+    graph_fingerprint = _digest(graph_items)
+    source_manifest = tuple((name, *signatures[name]) for name in sorted(signatures))
+
+    components: list[ComponentSourceEvidence] = []
+    for component in report.components:
+        visited = set(component.members)
+        pending = list(component.members)
+        while pending:
+            for target in adjacency[pending.pop()]:
+                if target not in visited:
+                    visited.add(target)
+                    pending.append(target)
+        closure = tuple(sorted(visited))
+        source_signatures = tuple(
+            (module, *signatures.get(module, (_MISSING, _MISSING)))
+            for module in closure
+        )
+        subgraph = tuple((node, adjacency[node]) for node in closure)
+        token = _digest((
+            EVIDENCE_SEMANTIC_VERSION,
+            component.members,
+            subgraph,
+            source_signatures,
+        ))
+        components.append(ComponentSourceEvidence(
+            members=component.members,
+            reachable_modules=closure,
+            source_signatures=source_signatures,
+            evidence_token=token,
+            classification=component.classification,
+            coverage=component.coverage,
+            reason=component.reason,
+        ))
+
+    return SourceBoundCycleEvidence(
+        semantic_version=EVIDENCE_SEMANTIC_VERSION,
+        graph_fingerprint=graph_fingerprint,
+        source_manifest_fingerprint=_digest(source_manifest),
+        components=tuple(components),
+        scenarios=report,
+    )
+
+
+def compare_source_bound_cycle_evidence(
+    before: SourceBoundCycleEvidence,
+    after: SourceBoundCycleEvidence,
+) -> tuple[CycleEvidenceChange, ...]:
+    """Report model evidence transitions, never LIVE warning ADD/RESOLVE.
+
+    Stable SCC member identities survive source-only edits and DFS cycle changes.
+    Equal evidence tokens do not generate noise from unrelated module changes.
+    """
+    if not isinstance(before, SourceBoundCycleEvidence) or not isinstance(after, SourceBoundCycleEvidence):
+        raise TypeError("comparison requires source-bound evidence snapshots")
+    old = {component.members: component for component in before.components}
+    new = {component.members: component for component in after.components}
+    changes: list[CycleEvidenceChange] = []
+    for members in sorted(old.keys() | new.keys()):
+        past, current = old.get(members), new.get(members)
+        if past is None:
+            kind = "STRUCTURE_ADDED"
+        elif current is None:
+            kind = "STRUCTURE_REMOVED"
+        elif past.classification != current.classification:
+            kind = "MODEL_CLASSIFICATION_CHANGED"
+        elif (past.evidence_token != current.evidence_token
+              or past.coverage != current.coverage or past.reason != current.reason
+              or before.semantic_version != after.semantic_version):
+            kind = "EVIDENCE_REVISED"
+        else:
+            continue
+        changes.append(CycleEvidenceChange(
+            members=members,
+            change=kind,
+            before=past.classification if past is not None else None,
+            after=current.classification if current is not None else None,
+            before_token=past.evidence_token if past is not None else None,
+            after_token=current.evidence_token if current is not None else None,
+        ))
+    return tuple(changes)

### FULL_DIFF: tests/test_cycle_semantics_evidence.py

diff --git a/tests/test_cycle_semantics_evidence.py b/tests/test_cycle_semantics_evidence.py
new file mode 100644
index 0000000..2f3e6dc
--- /dev/null
+++ b/tests/test_cycle_semantics_evidence.py
@@ -0,0 +1,161 @@
+import ast
+import hashlib
+import json
+from dataclasses import asdict
+
+import pytest
+
+from contextor.core.source import ParsedSourceInput
+from contextor.core.cycle_semantics.evidence import (
+    build_source_bound_cycle_evidence as build,
+    compare_source_bound_cycle_evidence as compare,
+)
+
+
+def _sources(**source_map):
+    return {
+        name: ParsedSourceInput(
+            ast.parse(text),
+            hashlib.sha256(text.encode()).hexdigest(),
+        )
+        for name, text in source_map.items()
+    }
+
+
+def _fixture(order=False):
+    edges = {"a": {"b"}, "b": {"a"}}
+    if order:
+        return build(edges, _sources(
+            a="value=1\nimport b\n",
+            b="import a\nx=a.value\n",
+        ))
+    return build(edges, _sources(
+        a="import b\nvalue=1\n",
+        b="import a\nx=a.value\n",
+    ))
+
+
+def test_unmodified_deterministic_and_immutable():
+    a = _fixture()
+    assert a == _fixture()
+    assert compare(a, a) == ()
+    assert a.components[0].classification == "MODEL_INTERNAL_EARLY_BINDING_HAZARD"
+    with pytest.raises(Exception):
+        a.components[0].classification = "fake"
+    json.dumps(asdict(a))
+
+
+def test_same_graph_semantic_flip_visible():
+    a, b = _fixture(), _fixture(True)
+    assert a.graph_fingerprint == b.graph_fingerprint
+    assert a.source_manifest_fingerprint != b.source_manifest_fingerprint
+    assert a.components[0].evidence_token != b.components[0].evidence_token
+    changes = compare(a, b)
+    assert len(changes) == 1
+    assert changes[0].members == ("a", "b")
+    assert changes[0].change == "MODEL_CLASSIFICATION_CHANGED"
+    assert changes[0].before == "MODEL_INTERNAL_EARLY_BINDING_HAZARD"
+    assert changes[0].after == "MODEL_ALL_FRESH_MEMBER_ENTRIES_PASS"
+    assert all(c.change != "RESOLVED" for c in changes)
+    assert compare(b, a)[0].change == "MODEL_CLASSIFICATION_CHANGED"
+
+
+def test_comment_only_edit_revises_evidence_not_outcome():
+    edges = {"a": {"b"}, "b": {"a"}}
+    before = build(edges, _sources(a="import b\nx=1\n", b="import a\ny=2\n"))
+    after = build(edges, _sources(a="import b\nx=1\n# note\n", b="import a\ny=2\n"))
+    assert before.components[0].classification == after.components[0].classification
+    assert compare(before, after)[0].change == "EVIDENCE_REVISED"
+
+
+def test_unrelated_source_edit_does_not_spam_scc_evidence():
+    edges = {"a": {"b"}, "b": {"a"}, "unrelated": set()}
+    old = build(edges, _sources(a="import b", b="import a", unrelated="x=1"))
+    new = build(edges, _sources(a="import b", b="import a", unrelated="x=2"))
+    assert old.source_manifest_fingerprint != new.source_manifest_fingerprint
+    assert old.components[0].evidence_token == new.components[0].evidence_token
+    assert compare(old, new) == ()
+
+
+def test_reachable_dependency_change_revises_evidence():
+    edges = {"a": {"b", "dep"}, "b": {"a"}, "dep": set()}
+    old = build(edges, _sources(a="import b\nimport dep", b="import a", dep="x=1"))
+    new = build(edges, _sources(a="import b\nimport dep", b="import a", dep="x=2"))
+    assert compare(old, new)[0].change == "EVIDENCE_REVISED"
+
+
+def test_graph_source_mismatch_fails_closed_and_transition():
+    edges = {"a": {"b"}, "b": {"a"}}
+    old = build(edges, _sources(a="import b", b="import a"))
+    new = build(edges, _sources(a="import b\nimport unknown", b="import a"))
+    assert new.components[0].classification == "INDETERMINATE"
+    assert new.components[0].reason == "GRAPH_SOURCE_IMPORT_MISMATCH"
+    assert compare(old, new)[0].change == "MODEL_CLASSIFICATION_CHANGED"
+
+
+def test_missing_source_and_addition():
+    edges = {"a": {"b"}, "b": {"a"}}
+    old = build(edges, _sources(a="import b"))
+    new = build(edges, _sources(a="import b", b="import a"))
+    assert old.components[0].source_signatures[1] == ("b", "MISSING", "MISSING")
+    assert old.components[0].classification == "INDETERMINATE"
+    assert new.components[0].classification == "MODEL_ALL_FRESH_MEMBER_ENTRIES_PASS"
+    assert compare(old, new)[0].change == "MODEL_CLASSIFICATION_CHANGED"
+
+
+def test_graph_internal_edge_change_reclassifies():
+    sources = _sources(a="import b", b="import a")
+    before = build({"a": {"b"}, "b": {"a"}}, sources)
+    after = build({"a": {"b"}, "b": set()}, sources)
+    c = compare(before, after)[0]
+    assert c.change == "STRUCTURE_REMOVED"
+
+
+def test_two_independent_sccs_only_one_changed():
+    edges = {"a": {"b"}, "b": {"a"}, "x": {"y"}, "y": {"x"}}
+    old = build(edges, _sources(
+        a="import b", b="import a", x="import y", y="import x",
+    ))
+    new = build(edges, _sources(
+        a="import b\n# extra", b="import a", x="import y", y="import x",
+    ))
+    changes = compare(old, new)
+    assert len(changes) == 1 and changes[0].members == ("a", "b")
+
+
+def test_ast_tamper_even_if_spoofed_same_raw_hash():
+    edges = {"a": {"b"}, "b": {"a"}}
+    sources = _sources(a="import b", b="import a")
+    before = build(edges, sources)
+    sources["a"].tree.body[0].lineno = 12
+    after = build(edges, sources)
+    assert before.source_manifest_fingerprint != after.source_manifest_fingerprint
+    assert compare(before, after)[0].change == "EVIDENCE_REVISED"
+
+
+def test_no_components():
+    e = build(
+        {"a": {"b"}, "b": set()},
+        _sources(a="import b", b="pass"),
+    )
+    assert e.components == () and compare(e, e) == ()
+
+
+def test_bad_input_fail_closed():
+    with pytest.raises(TypeError):
+        build({"a": {"a"}}, None)
+    with pytest.raises(TypeError):
+        build({"a": {"a"}}, {"a": ast.parse("import a")})
+    with pytest.raises(ValueError):
+        build({"a": {"a"}}, {
+            "a": ParsedSourceInput(ast.parse("import a"), "foo")
+        })
+    with pytest.raises(TypeError):
+        compare(None, None)
+
+
+def test_snapshot_only_authority_no_warning_action():
+    x = _fixture()
+    assert x.authority == "SNAPSHOT_ONLY_NOT_LIVE_FRESHNESS"
+    assert x.scenarios.evidence_scope == "SCENARIO_MODEL_NOT_RUNTIME_CERTIFICATION"
+    assert "SAFE" not in x.components[0].classification
