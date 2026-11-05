# CONTEXTOR C16-B01-B03-P0
# SAFE NAMED PACKAGE MEMBER ADMISSION / OPTIONAL CHILD SOURCE FAIL-CLOSED GATE

## PREFLIGHT

- Root: C:\Temp\Contextor_Repo. HEAD before and after: 626d427aed8477f095e354abd260a050cb4840d4.
- Initial worktree: M walkthrough.md only. It was the previous task's report and was preserved until this report replacement.
- Contextor MCP documentation and current module contexts were read before edits. The owners were confirmed: package_graph_consistency.assess_package_graph_consistency; evidence.EVIDENCE_SEMANTIC_VERSION; tests/test_p1d3_package_cycle_integration.py canonical integration helper and tests.
- Current interpreter: .venv\Scripts\python.exe, CPython 3.15.2. No dependency installation, production FULL, update_file, backend/Desktop/LIVE restart or commit.
- Source drift check: exact current named package branch and semantic version /2 matched the supplied contract. All edits used the normal patch editor.

## MCP_DISCOVERY

- Before edit the two owner modules reported canonical rev 982, canonical_state=fresh, workspace_sync=verified, cycle_semantics=fresh. Canonical structural warning count was 16, model_pass_count=0.
- package_graph_consistency inbound consumers include scenarios and the canonical integration tests; its outbound owners include model_identity and typing_guard. evidence is consumed by generation_manifest, original_worker_preparation, source_proof and other source-bound paths.
- Existing canonical graph construction and tests supplied the hard/soft invariant: hard edge to package initializer, optional named child as soft candidate, explicit relative sibling as hard. Neither graph.py nor resolver.py was edited.
- The existing scenarios call assess_package_graph_consistency with a mapping restricted to evidence_source_modules. This is the current B03 cohort limitation; direct callers can supply a wider source map, so the new gate checks both cohort membership and AST availability.

## EXACT_FILE_SCOPE

Allowed and changed:
1. contextor/core/cycle_semantics/package_graph_consistency.py — assess_package_graph_consistency named-member branch only.
2. contextor/core/cycle_semantics/evidence.py — EVIDENCE_SEMANTIC_VERSION only, from /2 to /3.
3. tests/test_p1d3_package_cycle_integration.py — focused canonical integration regressions and one local fixture helper.
4. walkthrough.md — this report.

No other source, test, docs, config, graph, package model, closure, scenario or warning-policy file changed.

## B01_IMPLEMENTATION

- For an ast.ImportFrom whose base resolves to an indexed regular package initializer, the new ordinary named-member branch retains the initializer in expected hard targets.
- It requires an ast.Module initializer source and checks every requested member and alias against the existing restricted model's identifier/dunder contract. Star imports remain rejected at the original earlier check.
- For each name it asks existing logical_to_indexed_module through the checker's target() helper over the full hard-graph key domain. It adds no named child to expected hard edges.
- The existing explicit-relative sibling branch below this new branch is unchanged in behavior; its selected existing tests pass.
- Final expected-vs-canonical hard-edge set equality at the end of assess_package_graph_consistency is unchanged. The checker does not infer that an initializer attribute is already or eventually bound; package_model determines import-time binding behavior.

## B03_FAIL_CLOSED_GATE

- If the indexed possible child exists, admission requires both child membership in evidence_source_modules and an ast.Module source in the supplied mapping.
- Missing either condition returns INDETERMINATE / OPTIONAL_NAMED_CHILD_SOURCE_UNAVAILABLE before a consistency result. The check runs even when the initializer binds the same member eventually.
- If no child is indexed, none is fabricated. The hard graph, soft graph and AST inputs are not mutated or read from disk inside the checker.
- Test P04 confirms that passing all AST sources while supplying only the hard-only evidence cohort still fails closed; the full indexed source cohort admits the named import for diagnostic model evaluation.
- The source cohort itself is not enlarged in P0. Full B03 resolution remains separate.

## CANONICAL_GRAPH_INVARIANTS

- Production contextor/core/graph/graph.py, resolver.py and indexer.py were untouched. No soft candidate was promoted to hard.
- P01/P02 canonical synthetic hard graph remained pkg.__init__ -> pkg.a and pkg.a -> pkg.__init__, with no soft edges; source order alone changed the model result.
- P04 canonical graph retained pkg.a -> pkg.__init__ hard and pkg.a -> pkg.value soft. The indexed child was not in hard-only evidence_source_modules.
- Forging pkg.a -> pkg.value as a hard edge or deleting the mandatory pkg.a -> pkg.__init__ hard edge yielded GRAPH_SOURCE_IMPORT_MISMATCH with the full source cohort.

## POSITIVE_REGRESSION_RESULTS

- P01: initializer from . import a then value = 1, with pkg.a importing value. Canonical hard graph consistency=CONSISTENT; scenario=MODEL_INTERNAL_EARLY_BINDING_HAZARD.
- P02: value = 1 before from . import a, same hard SCC. Consistency=CONSISTENT; scenario=MODEL_ALL_FRESH_MEMBER_ENTRIES_PASS. This is a restricted synthetic model result, not production safety.
- P03: already bound value imported as chosen, no same-name child. Consistency=CONSISTENT; scenario=MODEL_ALL_FRESH_MEMBER_ENTRIES_PASS.
- P04: indexed pkg.value child in the full source cohort. Consistency=CONSISTENT with full cohort; direct package model=MODEL_PASS; fresh synthetic CPython import succeeds. Hard-only cohort is rejected by B03 before any full scenario PASS.

## NEGATIVE_REGRESSION_RESULTS

- N01: indexed child outside hard-only cohort -> OPTIONAL_NAMED_CHILD_SOURCE_UNAVAILABLE, including when the caller passes a full sources map but a restricted cohort tuple. Scenario remains INDETERMINATE.
- N02: eventual value = 1 export plus indexed pkg.value outside the supplied cohort -> the same optional-child reason. The test avoids altering the pre-existing explicit-relative sibling contract.
- N03/N04: extra hard named child and missing mandatory initializer hard edge -> GRAPH_SOURCE_IMPORT_MISMATCH with complete source cohort.
- N05: dynamic __getattr__ initializer -> scenario INDETERMINATE, no MODEL_PASS inferred from graph admission alone.
- N06: unsupported conditional initializer assignment -> scenario INDETERMINATE.
- N07: star and restricted-invalid dunder alias -> UNSUPPORTED_IMPORT_FORM.
- N08/N09: selected existing explicit sibling, reexport, fallback and forged-graph tests pass; their outcomes were not weakened.
- N10: member absent from initializer and indexed children cannot produce MODEL_ALL_FRESH_MEMBER_ENTRIES_PASS.
- No false MODEL_PASS was observed in the missing optional-child scenario.

## TARGETED_PYTEST_RESULTS

- Initial C16-P0 selection: 11 passed, 1 failed, 119 deselected. The failed fixture combined a literal initializer assignment with a same-name indexed child; the existing restricted explicit-relative sibling validator returned AMBIGUOUS_PACKAGE_TARGET before the new B03 branch. That fixture was corrected to use a module import while preserving eventual export and hard SCC; no production branch was weakened.
- Corrected failing test alone: 1 passed.
- After the explicit cohort-membership gate was added: all 12 new C16-P0 parametrized cases passed, 119 deselected.
- Selected existing canonical reexport edges, nested initializer, initializer restrictions, forged graph, package fallback, missing member and package-layout cases: 18 passed.
- Commands used .venv\Scripts\python.exe -B -m pytest -q -rs -p no:cacheprovider with --basetemp outside the repository under C:\Temp\Contextor_C16_P0_pytest_tmp. No full suite was run.
- git diff --check exit=0.

## SOURCE_EVIDENCE_VERSION

- evidence.py changes EVIDENCE_SEMANTIC_VERSION from cycle-semantics-evidence/2 to cycle-semantics-evidence/3, and nothing else.
- The new focused test replaces a freshly built /3 SourceBoundCycleEvidence semantic_version with /2 and verifies assess_index_bound_scc_models returns EVIDENCE_SEMANTIC_VERSION_MISMATCH.
- No manifest or publication schema version changed.

## POST_CHANGE_MCP_AUDIT

- Read-only Contextor MCP module contexts for package_graph_consistency, evidence and tests.test_p1d3_package_cycle_integration: each reports canonical_revision=989, canonical_state=fresh, workspace_sync=verified, advisory_warning=null.
- The current aggregate project architecture reports canonical_revision=989, canonical_state=fresh, workspace_sync=unverified, graph/cycles fresh, cycle_semantics=stale, 16 structural paths. The current cyclic SCC count is not exposed while cycle_semantics is stale; the previous two-SCC semantic projection is not asserted as freshly comparable.
- This is source/index freshness, not loaded backend code adoption. MCP/runtime reload was not performed. No warning state or canonical hard edges were deliberately changed.

## REMAINING_B03_SOURCE_COHORT_GAP

- The current hard-reachable-plus-parent-initializer cohort still omits an indexed optional named child if that child is only a soft candidate.
- P0 rejects those named member imports before model application; it does not add child source bytes, fingerprints or soft candidates to the cohort. Therefore T05-style fallback remains inapplicable to full SCC proof.
- A later B03-P1 stage must bind any newly included optional source to exact source bytes and cohort identity before claiming all-entry model success. This report does not authorize an implementation or installed claim for that stage.

## MANIFEST_AND_CLAIM_VERSION_IMPACT

- Current MANIFEST_VERSION remains cycle-source-manifest/2 and PUBLICATION_BINDING_VERSION remains cycle-prepared-co-publication/2. partial_scc_claims checks source signature rows against the current closure.evidence_source_modules; publication_binding and generation_manifest also bind current source signatures.
- The /3 evidence semantic version rejects old /2 evidence in the existing validation path. A future B03-P1 enlarged cohort would change source signature membership and may require an explicit installed-claim/manifest transition. That transition was not specified or performed in P0; whether an additional version bump is required remains to be established with its exact consumer contract.
- No old receipt was relabeled, injected or published.

## FILES_CHANGED

- contextor/core/cycle_semantics/package_graph_consistency.py
- contextor/core/cycle_semantics/evidence.py
- tests/test_p1d3_package_cycle_integration.py
- walkthrough.md (report artifact; excluded from its own diff)

## FULL_DIFFS

Complete actual Git diff for every task-changed production/test file follows. There are no unrelated historical production/test diffs.

warning: in the working copy of 'contextor/core/cycle_semantics/evidence.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'contextor/core/cycle_semantics/package_graph_consistency.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'tests/test_p1d3_package_cycle_integration.py', LF will be replaced by CRLF the next time Git touches it
diff --git a/contextor/core/cycle_semantics/evidence.py b/contextor/core/cycle_semantics/evidence.py
index 1978497..e3751df 100644
--- a/contextor/core/cycle_semantics/evidence.py
+++ b/contextor/core/cycle_semantics/evidence.py
@@ -25,7 +25,7 @@ from .scenarios import (
     CycleComponentScenarios, CycleScenarioReport, analyze_cycle_scenarios,
 )
 
-EVIDENCE_SEMANTIC_VERSION = "cycle-semantics-evidence/2"
+EVIDENCE_SEMANTIC_VERSION = "cycle-semantics-evidence/3"
 _MISSING = "MISSING"
 
 
diff --git a/contextor/core/cycle_semantics/package_graph_consistency.py b/contextor/core/cycle_semantics/package_graph_consistency.py
index d046311..8e63ccd 100644
--- a/contextor/core/cycle_semantics/package_graph_consistency.py
+++ b/contextor/core/cycle_semantics/package_graph_consistency.py
@@ -326,11 +326,40 @@ def assess_package_graph_consistency(
                 if resolved != module_id:
                     expected.add(resolved)
                 if resolved.endswith(".__init__"):
-                    # The named-member form may be an initializer attribute or
-                    # a child. Only explicit relative sibling imports with a
-                    # provably unbound child are covered in this phase.
+                    # A named member may be an initializer attribute or child.
+                    # Preserve the initializer hard edge and require indexed
+                    # child source before admitting that bounded form.
                     if not (node.level and node.module is None):
-                        return unknown("AMBIGUOUS_PACKAGE_TARGET")
+                        initializer = sources.get(resolved)
+                        if not isinstance(initializer, ast.Module):
+                            return unknown("MISSING_REQUIRED_INITIALIZER")
+                        for alias in node.names:
+                            if (
+                                not alias.name.isidentifier()
+                                or alias.name.startswith("__")
+                                or (
+                                    alias.asname is not None
+                                    and (
+                                        not alias.asname.isidentifier()
+                                        or alias.asname.startswith("__")
+                                    )
+                                )
+                            ):
+                                return unknown("UNSUPPORTED_IMPORT_FORM")
+                            child = target(base + "." + alias.name)
+                            if (
+                                child is not None
+                                and (
+                                    child not in evidence_source_modules
+                                    or not isinstance(
+                                        sources.get(child), ast.Module
+                                    )
+                                )
+                            ):
+                                return unknown(
+                                    "OPTIONAL_NAMED_CHILD_SOURCE_UNAVAILABLE"
+                                )
+                        continue
                     initializer = sources.get(resolved)
                     if initializer is None:
                         return unknown("MISSING_REQUIRED_INITIALIZER")
diff --git a/tests/test_p1d3_package_cycle_integration.py b/tests/test_p1d3_package_cycle_integration.py
index a2ab895..fa61627 100644
--- a/tests/test_p1d3_package_cycle_integration.py
+++ b/tests/test_p1d3_package_cycle_integration.py
@@ -2796,3 +2796,235 @@ def test_p1d3_d2b3_official_isolated_full_receipt(
         )
         assert result.live_publish_status == "success"
         assert calls == [root.resolve()]
+
+
+def _c16_p0_canonical_sources(tmp_path, files):
+    root = write_synthetic_repository(tmp_path / "repo", files)
+    index, graph = _d2a_canonical_index_graph(root)
+    trees = {
+        module: ast.parse((root / item.path).read_text(encoding="utf-8"))
+        for module, item in index.modules.items()
+    }
+    closure = compute_cycle_model_source_closures(graph.hard_edges)
+    assert len(closure) == 1
+    return root, graph, trees, closure[0]
+
+
+@pytest.mark.parametrize(
+    ("initializer", "classification"),
+    [
+        (
+            "from . import a\nvalue = 1\n",
+            "MODEL_INTERNAL_EARLY_BINDING_HAZARD",
+        ),
+        (
+            "value = 1\nfrom . import a\n",
+            "MODEL_ALL_FRESH_MEMBER_ENTRIES_PASS",
+        ),
+    ],
+)
+def test_c16_p0_named_member_binding_order(
+    tmp_path, isolated_dirs, initializer, classification,
+):
+    _, graph, trees, closure = _c16_p0_canonical_sources(
+        tmp_path,
+        {"pkg/__init__.py": initializer, "pkg/a.py": "from pkg import value\n"},
+    )
+    assert graph.hard_edges == {
+        "pkg.__init__": {"pkg.a"},
+        "pkg.a": {"pkg.__init__"},
+    }
+    assert graph.soft_edges == {
+        "pkg.__init__": set(),
+        "pkg.a": set(),
+    }
+    assert assess_package_graph_consistency(
+        graph.hard_edges, trees, closure.evidence_source_modules,
+    ).status == "CONSISTENT"
+    scenario = analyze_cycle_scenarios(graph.hard_edges, trees).components[0]
+    assert scenario.classification == classification
+
+
+def test_c16_p0_bound_named_member_alias_has_no_child(
+    tmp_path, isolated_dirs,
+):
+    _, graph, trees, closure = _c16_p0_canonical_sources(
+        tmp_path,
+        {
+            "pkg/__init__.py": "value = 1\nfrom . import a\n",
+            "pkg/a.py": "from pkg import value as chosen\n",
+        },
+    )
+    assert assess_package_graph_consistency(
+        graph.hard_edges, trees, closure.evidence_source_modules,
+    ).status == "CONSISTENT"
+    scenario = analyze_cycle_scenarios(graph.hard_edges, trees).components[0]
+    assert scenario.classification == "MODEL_ALL_FRESH_MEMBER_ENTRIES_PASS"
+
+
+def test_c16_p0_indexed_child_requires_cohort_source(
+    tmp_path, isolated_dirs,
+):
+    root, graph, trees, closure = _c16_p0_canonical_sources(
+        tmp_path,
+        {
+            "pkg/__init__.py": "from . import a\n",
+            "pkg/a.py": "from pkg import value\n",
+            "pkg/value.py": "pass\n",
+        },
+    )
+    assert graph.hard_edges["pkg.a"] == {"pkg.__init__"}
+    assert graph.soft_edges["pkg.a"] == {"pkg.value"}
+    assert "pkg.value" not in closure.evidence_source_modules
+    closed = {
+        module: trees[module]
+        for module in closure.evidence_source_modules
+    }
+    assert assess_package_graph_consistency(
+        graph.hard_edges, trees, tuple(sorted(trees)),
+    ).status == "CONSISTENT"
+    result = assess_package_graph_consistency(
+        graph.hard_edges, trees, closure.evidence_source_modules,
+    )
+    assert result.status == "INDETERMINATE"
+    assert result.reason == "OPTIONAL_NAMED_CHILD_SOURCE_UNAVAILABLE"
+    result = assess_package_graph_consistency(
+        graph.hard_edges, closed, closure.evidence_source_modules,
+    )
+    assert result.status == "INDETERMINATE"
+    assert result.reason == "OPTIONAL_NAMED_CHILD_SOURCE_UNAVAILABLE"
+    assert evaluate_package_import_order(trees, "pkg").outcome == "MODEL_PASS"
+    assert run_synthetic_import(root, "pkg").returncode == 0
+    scenario = analyze_cycle_scenarios(graph.hard_edges, trees).components[0]
+    assert scenario.classification == "INDETERMINATE"
+    assert scenario.reason == "OPTIONAL_NAMED_CHILD_SOURCE_UNAVAILABLE"
+
+
+def test_c16_p0_eventual_export_does_not_hide_missing_child_source(
+    tmp_path, isolated_dirs,
+):
+    _, graph, trees, closure = _c16_p0_canonical_sources(
+        tmp_path,
+        {
+            "pkg/__init__.py": "from .a import trigger\nvalue = 1\n",
+            "pkg/a.py": "from pkg import value\ntrigger = 1\n",
+            "pkg/value.py": "pass\n",
+        },
+    )
+    assert "pkg.value" not in closure.evidence_source_modules
+    closed = {
+        module: trees[module]
+        for module in closure.evidence_source_modules
+    }
+    result = assess_package_graph_consistency(
+        graph.hard_edges, closed, closure.evidence_source_modules,
+    )
+    assert result.status == "INDETERMINATE"
+    assert result.reason == "OPTIONAL_NAMED_CHILD_SOURCE_UNAVAILABLE"
+
+
+def test_c16_p0_named_member_rejects_forged_hard_edges(
+    tmp_path, isolated_dirs,
+):
+    _, graph, trees, closure = _c16_p0_canonical_sources(
+        tmp_path,
+        {
+            "pkg/__init__.py": "from . import a\n",
+            "pkg/a.py": "from pkg import value\n",
+            "pkg/value.py": "pass\n",
+        },
+    )
+    for changed in (
+        {"pkg.a": {"pkg.__init__", "pkg.value"}},
+        {"pkg.a": set()},
+    ):
+        forged = {
+            module: set(targets)
+            for module, targets in graph.hard_edges.items()
+        }
+        forged.update(changed)
+        result = assess_package_graph_consistency(
+            forged, trees, tuple(sorted(trees)),
+        )
+        assert result.status == "INDETERMINATE"
+        assert result.reason == "GRAPH_SOURCE_IMPORT_MISMATCH"
+
+
+@pytest.mark.parametrize(
+    "source",
+    [
+        "from pkg import *\n",
+        "from pkg import value as __hidden\n",
+    ],
+)
+def test_c16_p0_unsupported_named_member_forms(
+    tmp_path, isolated_dirs, source,
+):
+    _, graph, trees, closure = _c16_p0_canonical_sources(
+        tmp_path,
+        {
+            "pkg/__init__.py": "from . import a\nvalue = 1\n",
+            "pkg/a.py": source,
+        },
+    )
+    result = assess_package_graph_consistency(
+        graph.hard_edges, trees, closure.evidence_source_modules,
+    )
+    assert result.status == "INDETERMINATE"
+    assert result.reason == "UNSUPPORTED_IMPORT_FORM"
+
+
+@pytest.mark.parametrize(
+    "initializer",
+    [
+        "from . import a\ndef __getattr__(name):\n    return 1\n",
+        "from . import a\nif condition:\n    value = 1\n",
+    ],
+)
+def test_c16_p0_unsupported_initializer_cannot_claim_pass(
+    tmp_path, isolated_dirs, initializer,
+):
+    _, graph, trees, _ = _c16_p0_canonical_sources(
+        tmp_path,
+        {
+            "pkg/__init__.py": initializer,
+            "pkg/a.py": "from pkg import value\n",
+        },
+    )
+    scenario = analyze_cycle_scenarios(graph.hard_edges, trees).components[0]
+    assert scenario.classification == "INDETERMINATE"
+
+
+def test_c16_p0_missing_member_cannot_claim_pass(tmp_path, isolated_dirs):
+    _, graph, trees, closure = _c16_p0_canonical_sources(
+        tmp_path,
+        {
+            "pkg/__init__.py": "from . import a\n",
+            "pkg/a.py": "from pkg import missing\n",
+        },
+    )
+    assert assess_package_graph_consistency(
+        graph.hard_edges, trees, closure.evidence_source_modules,
+    ).status == "CONSISTENT"
+    scenario = analyze_cycle_scenarios(graph.hard_edges, trees).components[0]
+    assert scenario.classification != "MODEL_ALL_FRESH_MEMBER_ENTRIES_PASS"
+
+
+def test_c16_p0_old_evidence_semantic_version_rejected(
+    tmp_path, isolated_dirs,
+):
+    root = write_synthetic_repository(
+        tmp_path / "repo", D2A_ACTIVE_CHAIN,
+    )
+    _, graph, captured, _, evidence, snapshot = _d2a_source_evidence(root)
+    assert evidence.semantic_version == "cycle-semantics-evidence/3"
+    previous = replace(
+        evidence, semantic_version="cycle-semantics-evidence/2",
+    )
+    assessment = assess_index_bound_scc_models(
+        graph.hard_edges,
+        captured.source_fingerprints_by_module,
+        snapshot,
+        previous,
+    )
+    assert assessment[0].reason == "EVIDENCE_SEMANTIC_VERSION_MISMATCH"


## FINAL_VERDICT

C16_B01_B03_P0_PASS

The bounded named-member branch retains canonical hard-edge equality, detects indexed optional children missing from the evidence cohort, and leaves the existing graph/relative-sibling logic intact. Focused new and selected existing regressions pass. The mandatory MCP audit was completed; its stale cycle_semantics family and lack of loaded-code adoption are reported without implying full B03 resolution.
