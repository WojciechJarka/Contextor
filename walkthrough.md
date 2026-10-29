# CONTEXTOR P1D3-WARN-1 — verified SCC warning eligibility

## 1. PREFLIGHT

DIRECT_EVIDENCE: Contextor MCP was used first in WARN-0 to identify ownership and consumers; current local source was reread before WARN-1. `publication_binding.py:27` has receipt version `cycle-prepared-co-publication/2`; `generation_manifest.py:25` has manifest version `cycle-source-manifest/2`; `publication_binding.py:301` defines `verify_co_published_cycle_manifest`; `scenarios.py:231` produces `MODEL_ALL_FRESH_MEMBER_ENTRIES_PASS`. `state_manager.py:115,133-140` stores cycles, semantic state and receipt; `diagnostics_projection.py:139-206` continues to count structural paths. `publication_binding.py:103-132` validates all SCC components. No PREFLIGHT_MISMATCH found.

## 2. HEAD / WORKTREE

DIRECT_EVIDENCE: initial HEAD `a5b88caa024e5e9bb53a9c820b4f14ff3049da0c`; initial worktree had only ` M walkthrough.md`. Final HEAD unchanged; final status includes ` M walkthrough.md` and the two new authorized files as untracked. No Git mutation.

## 3. AUTHORITY GATE

CODE_PATH_PROVED: `warning_eligibility.py::_verified_model_pass_cycle_paths` returns `frozenset()` unless exact `CanonicalCycleManifestReceipt`, current v2 receipt/manifest versions, no resync, fresh cycle/semantic families, successful existing receipt verification, valid hard graph and matching full SCC component order. It accepts explicit expected identity from the future caller; it does not authenticate that caller.

## 4. RECEIPT V2 VERIFICATION

CONTRACT_PROVED: the function calls `verify_co_published_cycle_manifest` with expected revision, state_id, repo_id and root_path. No digest algorithm was copied. `publication_binding.py:301-358` validates the entire committed receipt, current graph, all prepared SCCs and generation identity. Tests T07–T10/T14 exercise stale, foreign, altered and forged evidence.

## 5. SCC IDENTITY

CODE_PATH_PROVED: `scc.py:25-121` pure analyzer derives canonical cyclic components from hard edges. The new function compares ordered `component.members` with validated manifest claims; it does not equate DFS path to SCC.

## 6. DFS CYCLE PATH MAPPING

CODE_PATH_PROVED: each existing `state.cycles` item must be list/tuple, closed, at least two nonempty string nodes, with all directed steps present in hard graph and nodes contained by exactly one cyclic SCC. A malformed item makes the whole result empty. All valid represented paths in a qualifying SCC are returned as tuples; no `detect_cycles` call or graph/source recomputation. T05/T15 cover multiple paths and malformed input.

## 7. POSITIVE MODEL-PASS BEHAVIOR

CONTRACT_PROVED: only exact `MODEL_ALL_FRESH_MEMBER_ENTRIES_PASS` component claim can qualify, after whole-receipt validation. T02: one committed pass path eligible; T04: pass SCC path eligible with a separate committed hazard SCC; T05: all represented paths in one pass SCC eligible. These are static committed model-claim tests, not installed LIVE generation or Python runtime-safety certification.

## 8. HAZARD AND UNKNOWN FAIL-CLOSED

CONTRACT_PROVED: hazard classification never qualifies (T03/T04). An indeterminate SCC cannot create a complete receipt (T06). Missing, malformed, stale, resync, unsupported versions and invalid paths yield empty (T01/T06–T15). No unknown is interpreted as safe.

## 9. MIXED SCC BEHAVIOR

CONTRACT_PROVED: T04 uses a legitimate complete v2 receipt containing pass and hazard SCCs and selects only pass paths. T06 uses real preparation for pass plus indeterminate SCC: per-SCC pass binding survives as a preparation result, but global digest is None and no receipt exists; eligibility is empty. `generation_manifest.py:89-164` and `original_worker_preparation.py:125-139` enforce all-SCC completeness.

## 10. FORGED / STALE / FOREIGN EVIDENCE

CONTRACT_PROVED: T07/T08 vary revision, state_id, repo_id and root_path; T09 changes graph claim or internal edge; T10 alters model classification or receipt digest; T11/T12 family freshness; T13 resync; T14 v1/unsupported version and missing typed-manifest. All return empty.

## 11. SELF-LOOP

CONTRACT_PROVED: T16 constructs a real one-node hard SCC (`a -> a`), prepares/persists a valid v2 pass claim and qualifies the exact closed path `("a","a")`.

## 12. STRUCTURAL IMMUTABILITY

CONTRACT_PROVED: T17 deep-compares hard edges, paths, semantic snapshot and receipt before/after the call. No canonical state, graph, diagnostics or event schema is changed. Only authorized new files were created.

## 13. DETERMINISM

CONTRACT_PROVED: T18 repeats identical inputs, verifies equal frozenset outputs and unchanged state dictionary.

## 14. FOCUSED TEST RESULTS

- DIRECT_EVIDENCE: `python -m py_compile` for the two new files: exit 0, no output; final run after malformed-receipt hardening also exit 0.
- DIRECT_EVIDENCE: new test module initial 30 passed in 8.87s, exit 0; final 31 passed in 9.19s, exit 0, zero skips/failures.
- DIRECT_EVIDENCE: four requested focused regression modules: 114 passed in 6.56s, exit 0, zero skips/failures. This ran before the final local malformed-receipt guard adjustment; the final adjustment only moved the new function's version/freshness gate inside its existing fail-closed try block, and the new module was rerun.
- DIRECT_EVIDENCE: `git diff --no-index --check` for each new file showed no whitespace errors. Exit code 1 is Git's expected difference status for a new file; output contained only LF/CRLF conversion warnings. No global suite, active FULL or LIVE operation ran.

## 15. POST-CHANGE MCP AUDIT

DIRECT_EVIDENCE: Contextor `get_file_edit_context` indexed `warning_eligibility.py` as module 551/1 and the test as 552/1 at canonical revision 819. Both reported `workspace_sync=verified`, fresh module/graph/topology, no syntax diagnostics, and `cycle_semantics=stale`. New module imports canonical `scc`, `generation_manifest`, `publication_binding` only, with exactly one indexed consumer: its test module. This is source synchronization evidence, not proof that any running MCP/LIVE process loaded the new module.

## 16. FILES_CHANGED

- `contextor/core/cycle_semantics/warning_eligibility.py` — new production module.
- `tests/test_cycle_semantics_warning_eligibility.py` — new focused regression module.
- `walkthrough.md` — report only, excluded from source/test diff accounting.

## 17. FULL_DIFFS

The following two code blocks are complete actual Git new-file diffs generated with `git diff --no-index -- /dev/null <file>`; no source/test lines omitted.

### Production new-file diff

```diff
diff --git a/contextor/core/cycle_semantics/warning_eligibility.py b/contextor/core/cycle_semantics/warning_eligibility.py
new file mode 100644
index 0000000..0b00b07
--- /dev/null
+++ b/contextor/core/cycle_semantics/warning_eligibility.py
@@ -0,0 +1,101 @@
+"""Pure, fail-closed eligibility for committed model-pass cycle paths.
+
+Eligibility is a claim about a validated static model, not Python runtime safety.
+This module does not change structural cycles or active diagnostics.
+"""
+
+from __future__ import annotations
+
+from collections.abc import Mapping
+
+from .generation_manifest import MANIFEST_VERSION
+from .publication_binding import (
+    PUBLICATION_BINDING_VERSION,
+    CanonicalCycleManifestReceipt,
+    verify_co_published_cycle_manifest,
+)
+from .scc import analyze_import_cycle_topology
+
+
+def _verified_model_pass_cycle_paths(
+    state,
+    *,
+    expected_revision,
+    expected_state_id,
+    expected_repo_id,
+    expected_root_path,
+) -> frozenset[tuple[str, ...]]:
+    """Return structural paths in SCCs with committed v2 model-pass claims."""
+    empty: frozenset[tuple[str, ...]] = frozenset()
+    try:
+        receipt = getattr(state, "cycle_source_publication", None)
+        if type(receipt) is not CanonicalCycleManifestReceipt:
+            return empty
+        if (
+            receipt.version != PUBLICATION_BINDING_VERSION
+            or receipt.prepared_manifest.version != MANIFEST_VERSION
+            or getattr(state, "resync_required", False) is not False
+            or getattr(state, "cycles_state", None) != "fresh"
+            or getattr(state, "cycle_semantics_state", None) != "fresh"
+        ):
+            return empty
+
+        if not verify_co_published_cycle_manifest(
+            state,
+            revision=expected_revision,
+            state_id=expected_state_id,
+            repo_id=expected_repo_id,
+            root_path=expected_root_path,
+        ):
+            return empty
+        hard_edges = state.dependency_graph.hard_edges
+        if not isinstance(hard_edges, Mapping):
+            return empty
+        topology = analyze_import_cycle_topology(hard_edges)
+        components = topology.cyclic_components
+        claims = receipt.prepared_manifest.components
+        if (
+            len(components) != len(claims)
+            or any(
+                component.members != claim.members
+                for component, claim in zip(components, claims)
+            )
+        ):
+            return empty
+
+        paths = state.cycles
+        if not isinstance(paths, (list, tuple)):
+            return empty
+        memberships = tuple(frozenset(item.members) for item in components)
+        eligible = {
+            index
+            for index, claim in enumerate(claims)
+            if claim.model_classification
+            == "MODEL_ALL_FRESH_MEMBER_ENTRIES_PASS"
+        }
+        result: set[tuple[str, ...]] = set()
+        for path in paths:
+            if (
+                not isinstance(path, (list, tuple))
+                or len(path) < 2
+                or any(type(node) is not str or not node for node in path)
+                or path[0] != path[-1]
+            ):
+                return empty
+            if any(
+                target not in hard_edges.get(source, ())
+                for source, target in zip(path, path[1:])
+            ):
+                return empty
+            nodes = frozenset(path[:-1])
+            matching = tuple(
+                index for index, members in enumerate(memberships)
+                if nodes <= members
+            )
+            if len(matching) != 1:
+                return empty
+            if matching[0] in eligible:
+                result.add(tuple(path))
+        return frozenset(result)
+    except (AttributeError, KeyError, TypeError, ValueError, IndexError):
+        return empty
```

### Test new-file diff

```diff
diff --git a/tests/test_cycle_semantics_warning_eligibility.py b/tests/test_cycle_semantics_warning_eligibility.py
new file mode 100644
index 0000000..21bd38d
--- /dev/null
+++ b/tests/test_cycle_semantics_warning_eligibility.py
@@ -0,0 +1,235 @@
+"""WARN-1: committed static model claims, never LIVE or runtime safety."""
+
+from __future__ import annotations
+
+import copy
+from dataclasses import replace
+
+import pytest
+
+from contextor.core.analysis.state_manager import RepositoryAnalysisState
+from contextor.core.cycle_semantics.generation_manifest import (
+    prepare_cycle_source_manifest,
+)
+from contextor.core.cycle_semantics.warning_eligibility import (
+    _verified_model_pass_cycle_paths,
+)
+from contextor.core.domain.graph import ProjectGraph
+from contextor.core.live_state.store import load_snapshot, save_snapshot
+from tests.test_cycle_semantics_evidence import (
+    HAZARD,
+    PAIR,
+    PASS,
+    _bound,
+    _p1b_snapshots,
+)
+
+
+def _prepared_state(edges, sources, paths):
+    index, snapshot, evidence = _bound(edges, sources)
+    manifest = prepare_cycle_source_manifest(
+        edges, index, snapshot, evidence, _p1b_snapshots(sources),
+    )
+    state = RepositoryAnalysisState(
+        dependency_graph=ProjectGraph(
+            hard_edges={name: set(targets) for name, targets in edges.items()},
+            soft_edges={},
+        ),
+        cycles=[list(path) for path in paths],
+        cycles_state="fresh",
+        cycle_semantics=snapshot,
+        cycle_semantics_state="fresh",
+    )
+    return state, manifest
+
+
+def _committed(tmp_path, edges=PAIR, sources=PASS, paths=(("a", "b", "a"),)):
+    state, manifest = _prepared_state(edges, sources, paths)
+    assert manifest.source_manifest_sha256 is not None
+    save_snapshot(
+        state, tmp_path, "warn-state", exact_revision=1,
+        file_state_payload={
+            "_meta": {"state_id": "warn-state", "revision": 1},
+            "files": {},
+        },
+        prepared_cycle_manifest=manifest,
+    )
+    loaded, metadata = load_snapshot(tmp_path, "warn-state")
+    assert loaded.cycle_source_publication is not None
+    expected = dict(
+        expected_revision=metadata.revision,
+        expected_state_id=metadata.state_id,
+        expected_repo_id=metadata.repo_id,
+        expected_root_path=metadata.root_path,
+    )
+    return loaded, expected
+
+
+def _eligible(state, expected):
+    return _verified_model_pass_cycle_paths(state, **expected)
+
+
+def test_t01_no_receipt(tmp_path):
+    state, _ = _prepared_state(PAIR, PASS, (("a", "b", "a"),))
+    assert _eligible(state, dict(
+        expected_revision=1, expected_state_id="warn-state",
+        expected_repo_id="", expected_root_path="",
+    )) == frozenset()
+
+
+def test_t02_committed_pass_claim_is_eligible(tmp_path):
+    state, expected = _committed(tmp_path)
+    assert _eligible(state, expected) == frozenset({("a", "b", "a")})
+    assert state.cycles == [["a", "b", "a"]]
+
+
+def test_t03_committed_hazard_is_not_eligible(tmp_path):
+    state, expected = _committed(tmp_path, sources=HAZARD)
+    assert _eligible(state, expected) == frozenset()
+
+
+def test_t04_two_scc_pass_and_hazard(tmp_path):
+    edges = {"a": {"b"}, "b": {"a"}, "x": {"y"}, "y": {"x"}}
+    sources = {**PASS, "x": "import y\nvalue=1", "y": "from x import value"}
+    paths = (("a", "b", "a"), ("x", "y", "x"))
+    state, expected = _committed(tmp_path, edges, sources, paths)
+    assert _eligible(state, expected) == frozenset({paths[0]})
+
+
+def test_t05_all_paths_in_one_pass_scc(tmp_path):
+    edges = {"a": {"b", "c"}, "b": {"a"}, "c": {"a"}}
+    sources = {"a": "import b\nimport c", "b": "import a", "c": "import a"}
+    paths = (("a", "b", "a"), ("a", "c", "a"))
+    state, expected = _committed(tmp_path, edges, sources, paths)
+    assert _eligible(state, expected) == frozenset(paths)
+
+
+def test_t06_mixed_pass_indeterminate_has_no_committed_receipt(tmp_path):
+    edges = {"a": {"b"}, "b": {"a"}, "x": {"y"}, "y": {"x"}}
+    sources = {**PASS, "x": "import y\nimport unknown", "y": "import x"}
+    state, manifest = _prepared_state(
+        edges, sources, (("a", "b", "a"), ("x", "y", "x")),
+    )
+    assert manifest.components[0].model_classification == "MODEL_ALL_FRESH_MEMBER_ENTRIES_PASS"
+    assert manifest.components[1].model_classification == "INDETERMINATE"
+    assert manifest.source_manifest_sha256 is None
+    assert _eligible(state, dict(
+        expected_revision=1, expected_state_id="warn-state",
+        expected_repo_id="", expected_root_path="",
+    )) == frozenset()
+
+
+@pytest.mark.parametrize("field,value", [
+    ("expected_revision", 2), ("expected_state_id", "other"),
+])
+def test_t07_foreign_generation(tmp_path, field, value):
+    state, expected = _committed(tmp_path)
+    assert _eligible(state, {**expected, field: value}) == frozenset()
+
+
+@pytest.mark.parametrize("field,value", [
+    ("expected_repo_id", "other"), ("expected_root_path", "other"),
+])
+def test_t08_foreign_repository(tmp_path, field, value):
+    state, expected = _committed(tmp_path)
+    assert _eligible(state, {**expected, field: value}) == frozenset()
+
+
+@pytest.mark.parametrize("mutation", ["graph_hash", "internal_edge"])
+def test_t09_changed_graph_fails_closed(tmp_path, mutation):
+    state, expected = _committed(tmp_path)
+    if mutation == "graph_hash":
+        receipt = state.cycle_source_publication
+        state.cycle_source_publication = replace(
+            receipt,
+            prepared_manifest=replace(receipt.prepared_manifest, graph_sha256="0" * 64),
+        )
+    else:
+        state.dependency_graph.hard_edges["a"].add("a")
+    assert _eligible(state, expected) == frozenset()
+
+
+@pytest.mark.parametrize("mutation", ["classification", "digest"])
+def test_t10_forged_claim_fails_closed(tmp_path, mutation):
+    state, expected = _committed(tmp_path)
+    receipt = state.cycle_source_publication
+    if mutation == "classification":
+        component = replace(
+            receipt.prepared_manifest.components[0],
+            model_classification="MODEL_INTERNAL_EARLY_BINDING_HAZARD",
+        )
+        manifest = replace(receipt.prepared_manifest, components=(component,))
+        state.cycle_source_publication = replace(receipt, prepared_manifest=manifest)
+    else:
+        state.cycle_source_publication = replace(receipt, model_claims_sha256="0" * 64)
+    assert _eligible(state, expected) == frozenset()
+
+
+@pytest.mark.parametrize("freshness", ["stale", "deferred"])
+def test_t11_semantics_not_fresh(tmp_path, freshness):
+    state, expected = _committed(tmp_path)
+    state.cycle_semantics_state = freshness
+    assert _eligible(state, expected) == frozenset()
+
+
+@pytest.mark.parametrize("freshness", ["stale", "unavailable"])
+def test_t12_cycles_not_fresh(tmp_path, freshness):
+    state, expected = _committed(tmp_path)
+    state.cycles_state = freshness
+    assert _eligible(state, expected) == frozenset()
+
+
+def test_t13_resync_required(tmp_path):
+    state, expected = _committed(tmp_path)
+    state.resync_required = True
+    assert _eligible(state, expected) == frozenset()
+
+
+@pytest.mark.parametrize("version", ["cycle-prepared-co-publication/1", "other"])
+def test_t14_legacy_or_unsupported_receipt(tmp_path, version):
+    state, expected = _committed(tmp_path)
+    state.cycle_source_publication = replace(state.cycle_source_publication, version=version)
+    assert _eligible(state, expected) == frozenset()
+
+
+def test_t14_missing_manifest_in_typed_receipt_fails_closed(tmp_path):
+    state, expected = _committed(tmp_path)
+    state.cycle_source_publication = replace(
+        state.cycle_source_publication, prepared_manifest=None,
+    )
+    assert _eligible(state, expected) == frozenset()
+
+
+@pytest.mark.parametrize("path", [
+    ["a", "b"], ["a", "b", "a", ""], ["a", "z", "a"],
+    ["a", 2, "a"], "aba", ["a", "a"],
+])
+def test_t15_malformed_path_fails_closed(tmp_path, path):
+    state, expected = _committed(tmp_path)
+    state.cycles = [["a", "b", "a"], path]
+    assert _eligible(state, expected) == frozenset()
+
+
+def test_t16_self_loop_with_committed_pass(tmp_path):
+    edges = {"a": {"a"}}
+    sources = {"a": "import a"}
+    state, expected = _committed(tmp_path, edges, sources, (("a", "a"),))
+    assert _eligible(state, expected) == frozenset({("a", "a")})
+
+
+def test_t17_structural_state_is_unchanged(tmp_path):
+    state, expected = _committed(tmp_path)
+    before = copy.deepcopy((state.dependency_graph.hard_edges, state.cycles,
+                            state.cycle_semantics, state.cycle_source_publication))
+    assert _eligible(state, expected) == frozenset({("a", "b", "a")})
+    assert (state.dependency_graph.hard_edges, state.cycles,
+            state.cycle_semantics, state.cycle_source_publication) == before
+
+
+def test_t18_repeatable_without_state_mutation(tmp_path):
+    state, expected = _committed(tmp_path)
+    before = copy.deepcopy(state.__dict__)
+    first = _eligible(state, expected)
+    second = _eligible(state, expected)
+    assert first == second == frozenset({("a", "b", "a")})
+    assert state.__dict__ == before
```

## 18. CONTRACT_CONFLICTS

NONE observed. The required positive fixtures were constructed through existing `_bound`, `prepare_cycle_source_manifest`, `save_snapshot` and `load_snapshot` helpers, without manual receipt digests.

## 19. REMAINING UNKNOWN

The future authoritative caller and active warning integration are outside WARN-1. No installed-generation operation, active loaded-code adoption, or Python runtime-safety certification was performed. LIVE semantic family reported stale during MCP audit.

## 20. FINAL IMPLEMENTER OBSERVATION

CODE_PATH_PROVED: the new pure function returns only eligible path identities under an all-SCC committed v2 receipt. Active structural warnings, counts, events, Desktop messages and MCP schemas remain unchanged. Architectural GO remains with ChatGPT.


