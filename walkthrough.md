# CONTEXTOR P1D3-WARN-2B-2-R1 — implementer report

## PREFLIGHT

DIRECT_EVIDENCE: Initial HEAD `d2e5a1b7db7af6af1d11855bc12a8ffbbabfa9b4`, clean worktree. Contextor MCP inspected both production modules before editing. Local WARN-2B-2 receipt, validator and test anchors matched the supplied R1 preflight. No material drift was found.

## HEAD / WORKTREE

DIRECT_EVIDENCE: Final HEAD remains `d2e5a1b7db7af6af1d11855bc12a8ffbbabfa9b4`. Four allowlisted Python files and `walkthrough.md` changed. No Git mutation, service restart or active FULL/LIVE occurred.

## ROOT CAUSE

CODE_PATH_PROVED: Complete preparations did not bind `source_modules` to closure-derived sources; UNAVAILABLE component `model_kind` lacked an exact type/domain gate. Malformed recursive declarations could reach `asdict` during sealing/verification; the verifier's exception boundary did not include `RecursionError` or `OverflowError`.

## COMPLETE PREPARATION SOURCE DOMAIN

CODE_PATH_PROVED: Validator now derives the sorted union of `closure.evidence_source_modules` from already computed closures and requires an exact tuple match for `PREPARED_UNPUBLISHED_NON_ATOMIC`. The existing UNAVAILABLE `source_modules == ()` rule remains.

## UNAVAILABLE MODEL-KIND VALIDATION

CODE_PATH_PROVED: UNAVAILABLE components now require exact `str` and membership in `FLAT_MODULE` or `REGULAR_PACKAGE`. Existing INDETERMINATE outcome and PREPARED branch were not changed.

## RECEIPT VERIFIER EXCEPTION BOUNDARY

CODE_PATH_PROVED: The existing verifier exception tuple now also contains `RecursionError` and `OverflowError`; those failures return `False`. Receipt fields, digest, version, authority and identity remain unchanged.

## MALFORMED DECLARATION REGRESSIONS

CONTRACT_PROVED: R1-T01 rejects an incorrect complete source tuple. R1-T02 and T03 reject self-referencing lists for complete `source_modules` and UNAVAILABLE `model_kind` without exception. R1-T04 rejects both at seal.

## TAMPERED SNAPSHOT HYDRATION

CONTRACT_PROVED: R1-T05/T06 direct verification returned `False` for recursively tampered embedded preparations. R1-T07 persisted both tampered receipt forms through isolated snapshot fixtures; `load_snapshot` returned normally, cleared the optional receipt and preserved hard edges, cycles and fresh cycle state.

## PRESERVED VALID PUBLICATION

CONTRACT_PROVED: Genuine PASS/INDETERMINATE and PASS/HAZARD preparations still validate and survive hydration (R1-T08). No valid digest was fabricated.

## V2 COMPATIBILITY

CONTRACT_PROVED: R1-T09 persisted valid v2 and partial receipts together; each verified against the same committed generation. R1-T10 repeated partial verification without state mutation.

## FOCUSED TEST RESULTS

DIRECT_EVIDENCE: `py_compile` on all four authorized Python files exited 0. Initial focused run: 125 passed, one test-fixture failure caused by reusing `tmp_path/repo` twice. The fixture test was parameterized, then the exact requested five-module command passed: 127 passed, 0 failed, 0 skipped, 42.00 s, exit 0. `git diff --check` exited 0. No global pytest.

## POST-CHANGE MCP AUDIT

DIRECT_EVIDENCE: Contextor `get_module_context` examined all four changed files. Final canonical revision 836, live provenance, `workspace_sync=verified` for all four. Module/graph/topology/cycles families fresh; cycle_semantics stale. Structural DFS back-edge cycle count remained 16, the same as prechange. No new production imports or hard dependency edges were added; Contextor's bounded outbound evidence showed existing dependencies. This is no active loaded-code adoption claim.

## FILES_CHANGED

- `contextor/core/cycle_semantics/partial_scc_claims.py`
- `contextor/core/cycle_semantics/partial_scc_publication.py`
- `tests/test_cycle_semantics_partial_scc_claims.py`
- `tests/test_cycle_semantics_partial_scc_publication.py`

`walkthrough.md` is this report. Complete actual diffs for the four Python files follow.

## FULL_DIFFS


```diff
diff --git a/contextor/core/cycle_semantics/partial_scc_claims.py b/contextor/core/cycle_semantics/partial_scc_claims.py
index 09822d7..13302fc 100644
--- a/contextor/core/cycle_semantics/partial_scc_claims.py
+++ b/contextor/core/cycle_semantics/partial_scc_claims.py
@@ -52,6 +52,11 @@ def validate_partial_scc_claims(
         graph_sha256 = fingerprint_hard_edges(hard_edges)
         topology = analyze_import_cycle_topology(hard_edges)
         closures = compute_cycle_model_source_closures(hard_edges)
+        expected_source_modules = tuple(sorted({
+            module_id
+            for closure in closures
+            for module_id in closure.evidence_source_modules
+        }))
         components = topology.cyclic_components
         cyclic_members = tuple(sorted(
             member for component in components for member in component.members
@@ -93,6 +98,8 @@ def validate_partial_scc_claims(
             manifest = preparation.manifest
             if (
                 preparation.reason is not None
+                or type(preparation.source_modules) is not tuple
+                or preparation.source_modules != expected_source_modules
                 or type(manifest) is not PreparedCycleSourceManifest
                 or manifest.components != declarations
                 or manifest.version != MANIFEST_VERSION
@@ -160,6 +167,8 @@ def validate_partial_scc_claims(
             elif item.preparation_state == "UNAVAILABLE":
                 if (
                     item.model_classification != "INDETERMINATE"
+                    or type(item.model_kind) is not str
+                    or item.model_kind not in {"FLAT_MODULE", "REGULAR_PACKAGE"}
                     or type(item.reason) is not str or not item.reason
                     or item.source_signatures != ()
                     or item.model_evidence_sha256 is not None
diff --git a/contextor/core/cycle_semantics/partial_scc_publication.py b/contextor/core/cycle_semantics/partial_scc_publication.py
index b77cbaa..9ee5c21 100644
--- a/contextor/core/cycle_semantics/partial_scc_publication.py
+++ b/contextor/core/cycle_semantics/partial_scc_publication.py
@@ -122,6 +122,7 @@ def verify_co_published_partial_scc_preparation(
             repo_id=repo_id,
             root_path=root_path,
         )
-    except (AttributeError, KeyError, TypeError, ValueError, IndexError):
+    except (AttributeError, KeyError, TypeError, ValueError, IndexError,
+            RecursionError, OverflowError):
         return False
     return receipt == expected
diff --git a/tests/test_cycle_semantics_partial_scc_claims.py b/tests/test_cycle_semantics_partial_scc_claims.py
index c13289f..c44b78b 100644
--- a/tests/test_cycle_semantics_partial_scc_claims.py
+++ b/tests/test_cycle_semantics_partial_scc_claims.py
@@ -255,3 +255,33 @@ def test_t18_prepared_claims_are_not_manifest_or_receipt(tmp_path, isolated_dirs
         expected_repo_id="repo",
         expected_root_path="root",
     ) == frozenset()
+
+
+def test_r1_t01_complete_source_domain_mismatch_rejected(tmp_path, isolated_dirs):
+    edges, snapshot, preparation = _case(tmp_path, TWO_PASS)
+    assert preparation.status == "PREPARED_UNPUBLISHED_NON_ATOMIC"
+    assert _validated(edges, snapshot, preparation) is not None
+    changed = replace(preparation, source_modules=("foreign",))
+    assert _validated(edges, snapshot, changed) is None
+
+
+def test_r1_t02_recursive_complete_source_modules_rejected(tmp_path, isolated_dirs):
+    edges, snapshot, preparation = _case(tmp_path, TWO_PASS)
+    recursive = []
+    recursive.append(recursive)
+    changed = replace(preparation, source_modules=recursive)
+    assert _validated(edges, snapshot, changed) is None
+
+
+def test_r1_t03_recursive_unavailable_model_kind_rejected(tmp_path, isolated_dirs):
+    edges, snapshot, preparation = _case(tmp_path)
+    recursive = []
+    recursive.append(recursive)
+    changed = _replace_component(preparation, 1, model_kind=recursive)
+    assert _validated(edges, snapshot, changed) is None
+
+
+@pytest.mark.parametrize("sources", [PASS_AND_UNKNOWN, PASS_AND_HAZARD])
+def test_r1_t08_valid_preparations_still_validate(tmp_path, isolated_dirs, sources):
+    edges, snapshot, preparation = _case(tmp_path, sources)
+    assert _validated(edges, snapshot, preparation) is not None
diff --git a/tests/test_cycle_semantics_partial_scc_publication.py b/tests/test_cycle_semantics_partial_scc_publication.py
index a382678..97df07b 100644
--- a/tests/test_cycle_semantics_partial_scc_publication.py
+++ b/tests/test_cycle_semantics_partial_scc_publication.py
@@ -329,3 +329,93 @@ def test_t20_tampered_receipt_preserves_structural_diagnostics(tmp_path, isolate
     assert loaded.cycles_state == "fresh"
     assert loaded.cycles == [["a", "b", "a"], ["x", "y", "x"]]
     assert loaded.dependency_graph.hard_edges == state.dependency_graph.hard_edges
+
+
+def _recursive_declaration(preparation, kind):
+    recursive = []
+    recursive.append(recursive)
+    if kind == "source_modules":
+        return replace(preparation, source_modules=recursive)
+    components = list(preparation.component_preparations)
+    components[1] = replace(components[1], model_kind=recursive)
+    return replace(preparation, component_preparations=tuple(components))
+
+
+@pytest.mark.parametrize("kind,sources", [
+    ("source_modules", TWO_PASS),
+    ("model_kind", PASS_AND_UNKNOWN),
+])
+def test_r1_t04_malformed_declaration_cannot_be_sealed(
+    tmp_path, isolated_dirs, kind, sources,
+):
+    state, preparation = _case(tmp_path, sources)
+    state.revision = 1
+    state.state_id = "partial-state"
+    malformed = _recursive_declaration(preparation, kind)
+    with pytest.raises((ValueError, TypeError)):
+        seal_partial_scc_preparation(
+            state, malformed, revision=1, state_id="partial-state",
+            repo_id="", root_path="",
+        )
+    assert state.cycle_partial_source_publication is None
+
+
+@pytest.mark.parametrize("kind,sources", [
+    ("source_modules", TWO_PASS),
+    ("model_kind", PASS_AND_UNKNOWN),
+])
+def test_r1_t05_t06_t07_recursive_receipt_fails_verify_and_hydration(
+    tmp_path, isolated_dirs, kind, sources,
+):
+    state, preparation = _case(tmp_path, sources)
+    metadata = _save(state, tmp_path, partial=preparation)
+    loaded, _ = load_snapshot(tmp_path, "partial-state")
+    receipt = loaded.cycle_partial_source_publication
+    loaded.cycle_partial_source_publication = replace(
+        receipt,
+        preparation=_recursive_declaration(receipt.preparation, kind),
+    )
+    before_edges = copy.deepcopy(loaded.dependency_graph.hard_edges)
+    before_cycles = copy.deepcopy(loaded.cycles)
+    assert _verify(loaded, metadata) is False
+    assert loaded.dependency_graph.hard_edges == before_edges
+    assert loaded.cycles == before_cycles
+
+    _tamper(tmp_path, metadata, lambda stored: setattr(
+        stored,
+        "cycle_partial_source_publication",
+        replace(
+            stored.cycle_partial_source_publication,
+            preparation=_recursive_declaration(
+                stored.cycle_partial_source_publication.preparation, kind,
+            ),
+        ),
+    ))
+    hydrated, _ = load_snapshot(tmp_path, "partial-state")
+    assert hydrated.cycle_partial_source_publication is None
+    assert hydrated.dependency_graph.hard_edges == before_edges
+    assert hydrated.cycles == before_cycles
+    assert hydrated.cycles_state == "fresh"
+
+
+@pytest.mark.parametrize("sources", [PASS_AND_UNKNOWN, PASS_AND_HAZARD])
+def test_r1_t08_valid_publication_survives_hydration(tmp_path, isolated_dirs, sources):
+    state, preparation = _case(tmp_path, sources)
+    metadata = _save(state, tmp_path, partial=preparation)
+    loaded, _ = load_snapshot(tmp_path, "partial-state")
+    assert _verify(loaded, metadata)
+    assert loaded.cycle_partial_source_publication.preparation == preparation
+
+
+def test_r1_t09_t10_v2_coexistence_and_repeat_verification(tmp_path, isolated_dirs):
+    state, preparation = _case(tmp_path, TWO_PASS)
+    metadata = _save(state, tmp_path, partial=preparation, manifest=preparation.manifest)
+    loaded, _ = load_snapshot(tmp_path, "partial-state")
+    before = copy.deepcopy(loaded.__dict__)
+    assert _verify(loaded, metadata) is True
+    assert _verify(loaded, metadata) is True
+    assert verify_co_published_cycle_manifest(
+        loaded, revision=metadata.revision, state_id=metadata.state_id,
+        repo_id=metadata.repo_id, root_path=metadata.root_path,
+    )
+    assert loaded.__dict__ == before
```

## CONTRACT_CONFLICTS

NONE observed.

## REMAINING UNKNOWN

UNKNOWN: Active LIVE loaded-code adoption, active warning behavior and runtime import safety. No active FULL/LIVE or backend restart was performed.

## FINAL IMPLEMENTER OBSERVATION

CONTRACT_PROVED: The specified malformed-declaration gates and verifier exception boundary pass the focused regressions. Architectural GO remains with ChatGPT.

