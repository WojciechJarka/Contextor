# CONTEXTOR_C16_P15_EXTERNAL_IMPORT_EFFECTS_F1B

## PREFLIGHT
DIRECT_EVIDENCE: obowiązujące globalne `C:\Users\DafoO\.codex\AGENTS.md` zostało odczytane w łańcuchu E1/F1 i jest stosowane. Zadana baza `4cad8cb2…` uległa zmianie przed tym etapem: aktualny HEAD `9f5ca896ea3ed40942c221dc9e32ae0d416e6c3b` (`Auto-commit: Cleanup and update`), początkowy worktree czysty, również bez zastanego `0.17.0`. Wszystkie zadane anchory testu nadal pasowały; produkcja F1 była już w HEAD. Contextor MCP first: `tests/test_p1d3_package_cycle_integration.py` i `package_model.py` przed zmianą `workspace_sync=verified`, LIVE rev 1161, syntax fresh/zero, `cycle_semantics=stale`. Nie modyfikowano produkcji ani indexera.

## REGRESSION_ROOT_CAUSE
Poprzednie testy przyjmowały, że leksykalnie rozpoznany `typing.TYPE_CHECKING` usuwa efekt wykonania samego `import typing`. Niezależny CPython witness z E1 pokazał, że taki import uruchamia kod zewnętrznego modułu; bez source/environment proof zwykły model musi zwrócić `UNKNOWN`. F1 usunęło shortcut wykonania, więc dotychczasowe `CONSISTENT`, `MODEL_PASS`, prepared manifest i receipt dla tych fixture'ów nie są uprawnione. To nie zmienia indeksowania `type_only` ani strukturalnego grafu.

## TWELVE_TEST_CLASSIFICATION
- Grupa A: `d2b_name_guard_inactive`, `d2b_attribute_guard_inactive`: brak hard SCC i pozytywne CPython execution nadal obowiązują; zwykły model dla obu wejść daje `UNKNOWN` z `reached_unmodeled_import.target=typing`, a nie hazard.
- Grupa B: `d2b_else_activates_import`, `d2b_else_reordered_safe`, `d2b2_active_import_dominates_type_only`, `d2b3_name_typed_side_import`, `d2b3_attribute_typed_side_import`, `d2b3_forged_hard_graph_rejected`: graf/closure i CPython observations pozostają; consistency ma `EXTERNAL_IMPORT_EXECUTION_UNMODELED`; scenariusz ma `INDETERMINATE`, `coverage=NONE`, bez entry assessments, ponieważ gate zatrzymuje ocenę przed agregacją. Bezpośrednie ordinary assessments pokazują `UNKNOWN`/typing. P0 ma `INCOMPLETE_EVIDENCE`, P1B `UNAVAILABLE/INCOMPLETE_MEMBER_ENTRY_ASSESSMENTS`; to nie twierdzi, że source bytes są niespójne.
- Grupa C: `d2b_original_worker_prepares_v2`, `d2b_official_isolated_full_receipt`, `d2b3_official_isolated_full_receipt`: typing-based fixture nie otrzymuje zwykłego manifestu ani co-published receipt. Pozytywny wariant wewnętrznego cyklu F1/F2 i D2A pozostaje w tym samym pliku i został uruchomiony.
- Grupa D: `d2b_forged_marker_event_rejected` przemianowano na `d2b_forged_internal_import_event_rejected`; F2 daje autentyczny dodatni model, fałszowany jest jego rzeczywisty `FROM` event, token przeliczony jak wcześniej, replay zwraca `MODEL_REPLAY_MISMATCH`.

## EXACT_TEST_CORRECTIONS
Każda zmiana expectation wynika z jednego mechanizmu: osiągnięty import `typing` ma nieznane efekty. `package_graph_consistency.py` rejestruje site i zwraca `EXTERNAL_IMPORT_EXECUTION_UNMODELED`; `package_model.py` kończy osiągnięty import `UNKNOWN`; `scenarios.py` zatrzymuje SCC przed entry assessments. `evidence.py`/`source_proof.py` odmawiają dodatniego claim z niepełnych assessments. Dla F2, który zawiera wyłącznie wewnętrzne importy, autentyczny `FROM` jest właściwym zdarzeniem do testu replay-integrity. Dodatkowe jawne porównania `SourceSnapshot.raw` z plikiem, fingerprintu z indeksem i `ast.dump(..., include_attributes=True)` z parserem CPython chronią byte/AST identity niezależnie od niedostępnego positive model claim.

## PRESERVED_INDEXER_CONTRACTS
Testy nadal sprawdzają pierwotne `hard_edges`, `soft_edges`, `type_only`, `is_from_import`, closure membership, captured import facts i ponownie zbudowany captured graph. `typing_guard` nadal rozpoznaje składnię tam, gdzie oczekiwano. Nie zmieniono source inventory ani produkcyjnego indexera. CPython success/failure dla oryginalnych fixture'ów pozostaje osobną obserwacją, nie powodem do MODEL_PASS.

## PRESERVED_POSITIVE_RECEIPT_COVERAGE
Istniejące dodatnie testy `test_package_closure_and_prepared_v2` (F1/F2), `test_p1d3_d2a_original_worker_prepares_v2` i `test_p1d3_d2a_official_isolated_full_receipt` pozostały bez zmian i przeszły w celowanym uruchomieniu. Nadal sprawdzają wersję manifestu, source/evidence digest, model classification, canonical generation identity, seal/replay, isolated LIVE publication oraz accepted receipt dla internal-only package cycles. Nowy forged-event test używa F2 jako autentycznej dodatniej bazy. Nie wnioskuje stąd o bezpieczeństwie importu `typing`.

## NEGATIVE_AUTHORITY_TESTS
Typing-based manifest preview: `UNAVAILABLE`, manifest `None`, SCC `INDETERMINATE/EXTERNAL_IMPORT_EXECUTION_UNMODELED`. W dwóch izolowanych LIVE testach zapisany `cycle_source_publication is None` i `verify_co_published_cycle_manifest(...)` zwraca false mimo ukończonej zwykłej publikacji globalnego stanu. To odróżnia odmowę claim od powodzenia analizy projektu.

## TARGETED_TEST_RESULTS
- 8/8 wybranych Group A/B testów przeszło po świadomej migracji.
- 8/8 wybranych Group C/D oraz niezależnych dodatnich F1/F2/D2A testów przeszło.
- Wskazany typing/D2B integration subset: `70 passed, 61 deselected`.
- F1 authority tests: `4 passed` (uruchomione osobno, ponieważ `-k typing_guard or d2b` je wykluczał).
- `git diff --check`: brak błędów. Nie uruchomiono pełnego pytest.

## MCP_POST_CHANGE_AUDIT
Contextor `get_live_events(after_revision=1161)`: watcher `UPDATED` dla testowego pliku w rev 1162–1167, `continuity=continuous`, `resync_required=false`. `get_file_edit_context` po zmianie: test i niezmieniony `package_model.py` per-file `workspace_sync=verified`, rev 1167; syntax diagnostics `checked_and_none`, graph/topology/cycles fresh, `cycle_semantics=stale`. Warning view: 16 structural paths, 0 model pass, 16 active warnings, jak wcześniej. Żadnych zmian import-edge w produkcji; w pliku testu nie zmieniono import statements. LIVE structural count pozostaje 16. Nie przedstawiono stale semantics jako fresh ani nie wykonano mutacji LIVE/FULL/restartu.

## REMAINING_DEFECTS_OR_PROOF_GAPS
Brak znanych niepowodzeń w wymaganym focused subset. Globalny suite zgodnie z instrukcją nieuruchomiony. Bieżący LIVE `cycle_semantics=stale`; test-only source sync nie dowodzi adopcji runtime ani runtime safety. GitHub HEAD nie jest osobną zweryfikowaną władzą. F1B nie zmienia produkcji; pełna certyfikacja globalna poza scope.

## FILES_CHANGED
`tests/test_p1d3_package_cycle_integration.py` (jedyny source/test/docs file). `walkthrough.md` jest tylko raportem.

## FULL_DIFFS

```diff
diff --git a/tests/test_p1d3_package_cycle_integration.py b/tests/test_p1d3_package_cycle_integration.py
index fa61627..e149079 100644
--- a/tests/test_p1d3_package_cycle_integration.py
+++ b/tests/test_p1d3_package_cycle_integration.py
@@ -1146,6 +1146,12 @@ def _d2a_source_evidence(root):
 
 def _assert_d2b3_typed_side_evidence(root):
     index, graph, captured, parsed, evidence, snapshot = _d2a_source_evidence(root)
+    for module_id, source in captured.original_worker_source_snapshots.items():
+        assert source.raw == Path(root, index.modules[module_id].path).read_bytes()
+        assert source.source_fingerprint == index.source_fingerprints_by_module[module_id]
+        assert ast.dump(parsed[module_id].tree, include_attributes=True) == ast.dump(
+            ast.parse(source.raw), include_attributes=True,
+        )
     assert graph.hard_edges == {
         "pkg.__init__": set(),
         "pkg.a": {"pkg.b"},
@@ -1195,19 +1201,23 @@ def _assert_d2b3_typed_side_evidence(root):
         {module_id: source.tree for module_id, source in parsed.items()},
         closure[0].evidence_source_modules,
     )
-    assert consistency.status == "CONSISTENT"
-    assert consistency.reason is None
+    assert consistency.status == "INDETERMINATE"
+    assert consistency.reason == "EXTERNAL_IMPORT_EXECUTION_UNMODELED"
+    assert any(site[3] == "typing" for site in consistency.unmodeled_external_imports)
 
     scenario = evidence.scenarios.components[0]
     assert scenario.members == ("pkg.a", "pkg.b")
     assert scenario.model_kind == "REGULAR_PACKAGE"
-    assert scenario.classification == "MODEL_ALL_FRESH_MEMBER_ENTRIES_PASS"
-    assert scenario.coverage == "COMPLETE_FRESH_MEMBER_ENTRIES"
-    assert not any(
-        event.operation == "START_IMPORT" and event.target == "pkg.c"
-        for assessment in scenario.entry_assessments
-        for event in assessment.events
-    )
+    assert scenario.classification == "INDETERMINATE"
+    assert scenario.coverage == "NONE"
+    assert scenario.reason == "EXTERNAL_IMPORT_EXECUTION_UNMODELED"
+    for entry in scenario.members:
+        assessment = evaluate_package_import_order(
+            {module_id: source.tree for module_id, source in parsed.items()},
+            entry,
+        )
+        assert assessment.outcome == "UNKNOWN"
+        assert assessment.reached_unmodeled_import.target == "typing"
     for entry in ("pkg.a", "pkg.b"):
         assert run_synthetic_import(root, entry).returncode == 0
 
@@ -1218,7 +1228,7 @@ def _assert_d2b3_typed_side_evidence(root):
         evidence,
     )
     assert len(p0) == 1
-    assert p0[0].evidence_state == "DECLARED_INPUTS_CONSISTENT"
+    assert p0[0].evidence_state == "INCOMPLETE_EVIDENCE"
     p1b = assess_scc_source_bytes(
         graph.hard_edges,
         captured.source_fingerprints_by_module,
@@ -1227,7 +1237,8 @@ def _assert_d2b3_typed_side_evidence(root):
         captured.original_worker_source_snapshots,
     )
     assert len(p1b) == 1
-    assert p1b[0].bytes_state == "BYTE_AST_CONSISTENT_NON_ATOMIC"
+    assert p1b[0].bytes_state == "UNAVAILABLE"
+    assert p1b[0].reason == "INCOMPLETE_MEMBER_ENTRY_ASSESSMENTS"
 
     captured_facts = materialize_reexport_facts_by_module(
         captured.modules,
@@ -1911,10 +1922,11 @@ def _assert_d2b2_inactive_no_hard_scc(
     for entry, succeeds in expected.items():
         modeled = evaluate_package_import_order(source_trees, entry)
         actual = run_synthetic_import(root, entry)
-        assert (modeled.outcome == "MODEL_PASS") is succeeds
+        assert modeled.outcome == "UNKNOWN"
+        assert modeled.reached_unmodeled_import.target == "typing"
         assert (actual.returncode == 0) is succeeds
         if entry == "pkg.a":
-            assert any(
+            assert not any(
                 event.operation == "TYPING_MARKER_IMPORT"
                 for event in modeled.events
             )
@@ -2363,6 +2375,12 @@ def _assert_p1d3_d2b_supported_fixture(
 
     root = write_synthetic_repository(tmp_path / "repo", fixture)
     index, graph, captured, parsed, evidence, snapshot = _d2a_source_evidence(root)
+    for module_id, source in captured.original_worker_source_snapshots.items():
+        assert source.raw == Path(root, index.modules[module_id].path).read_bytes()
+        assert source.source_fingerprint == index.source_fingerprints_by_module[module_id]
+        assert ast.dump(parsed[module_id].tree, include_attributes=True) == ast.dump(
+            ast.parse(source.raw), include_attributes=True,
+        )
     assert graph.hard_edges == {
         "pkg.__init__": set(),
         "pkg.a": {"pkg.b"},
@@ -2388,55 +2406,35 @@ def _assert_p1d3_d2b_supported_fixture(
     assert set(evidence.scenarios.components[0].members) == {"pkg.a", "pkg.b"}
     scenario = evidence.scenarios.components[0]
     assert scenario.model_kind == "REGULAR_PACKAGE"
-    assert scenario.coverage == "COMPLETE_FRESH_MEMBER_ENTRIES"
-    if fixture is D2B_ELSE_HAZARD:
-        assert scenario.classification == "MODEL_INTERNAL_EARLY_BINDING_HAZARD"
-    else:
-        assert scenario.classification == "MODEL_ALL_FRESH_MEMBER_ENTRIES_PASS"
+    assert scenario.coverage == "NONE"
+    assert scenario.classification == "INDETERMINATE"
+    assert scenario.reason == "EXTERNAL_IMPORT_EXECUTION_UNMODELED"
+    assert scenario.entry_assessments == ()
     guard = recognize_typing_guard(
         parsed["pkg.a"].tree,
         frozenset(index.modules),
     )
     assert guard is not None
-    assert any(
-        event.operation == "TYPING_MARKER_IMPORT"
-        and event.target == "typing"
-        and event.symbol == "TYPE_CHECKING"
-        for assessment in scenario.entry_assessments
-        for event in assessment.events
-    )
-    assessment_a = next(
-        item for item in scenario.entry_assessments
-        if item.entry_module == "pkg.a"
-    )
-    starts_b = any(
-        event.operation == "START_IMPORT" and event.target == "pkg.b"
-        for event in assessment_a.events
-    )
-    assert starts_b is any(
-        fixture is candidate
-        for candidate in (D2B_ELSE_HAZARD, D2B_ELSE_SAFE)
-    )
+    trees = {module_id: source.tree for module_id, source in parsed.items()}
     for entry, succeeds in expected.items():
         actual = run_synthetic_import(root, entry)
         assert (actual.returncode == 0) is succeeds
-        modeled = next(
-            item for item in scenario.entry_assessments
-            if item.entry_module == entry
-        )
-        assert (modeled.outcome == "MODEL_PASS") is succeeds
+        modeled = evaluate_package_import_order(trees, entry)
+        assert modeled.outcome == "UNKNOWN"
+        assert modeled.reached_unmodeled_import.target == "typing"
         if fixture is D2B_ELSE_HAZARD and entry == "pkg.a":
             assert "partially initialized module" in actual.stderr
     p0 = assess_index_bound_scc_models(
         graph.hard_edges, captured.source_fingerprints_by_module,
         snapshot, evidence,
     )
-    assert p0[0].evidence_state == "DECLARED_INPUTS_CONSISTENT"
+    assert p0[0].evidence_state == "INCOMPLETE_EVIDENCE"
     p1b = assess_scc_source_bytes(
         graph.hard_edges, captured.source_fingerprints_by_module,
         snapshot, evidence, captured.original_worker_source_snapshots,
     )
-    assert p1b[0].bytes_state == "BYTE_AST_CONSISTENT_NON_ATOMIC"
+    assert p1b[0].bytes_state == "UNAVAILABLE"
+    assert p1b[0].reason == "INCOMPLETE_MEMBER_ENTRY_ASSESSMENTS"
 
 
 def test_p1d3_d2b_name_guard_inactive(tmp_path, isolated_dirs):
@@ -2530,35 +2528,33 @@ def test_p1d3_d2b_original_worker_prepares_v2(tmp_path, isolated_dirs):
     prepared = prepare_original_worker_cycle_manifest(
         captured, graph.hard_edges, snapshot,
     )
-    assert prepared.status == "PREPARED_UNPUBLISHED_NON_ATOMIC"
-    assert prepared.manifest.version == "cycle-source-manifest/2"
-    component = prepared.manifest.components[0]
-    assert component.model_kind == "REGULAR_PACKAGE"
-    assert component.model_classification == "MODEL_ALL_FRESH_MEMBER_ENTRIES_PASS"
-    assert tuple(row[0] for row in component.source_signatures) == (
-        "pkg.__init__", "pkg.a", "pkg.b",
+    assert prepared.status == "UNAVAILABLE"
+    assert prepared.manifest is None
+    assert evidence.scenarios.components[0].classification == "INDETERMINATE"
+    assert evidence.scenarios.components[0].reason == (
+        "EXTERNAL_IMPORT_EXECUTION_UNMODELED"
     )
-    assert component.model_evidence_sha256
 
 
-def test_p1d3_d2b_forged_marker_event_rejected(
+def test_p1d3_d2b_forged_internal_import_event_rejected(
     tmp_path, isolated_dirs,
 ):
-    root = write_synthetic_repository(tmp_path / "repo", D2B_ELSE_SAFE)
+    root = write_synthetic_repository(tmp_path / "repo", F2)
     _, graph, captured, _, evidence, snapshot = _d2a_source_evidence(root)
     scenario = evidence.scenarios.components[0]
+    assert scenario.classification == "MODEL_ALL_FRESH_MEMBER_ENTRIES_PASS"
     assessment = next(
         item for item in scenario.entry_assessments
-        if any(event.operation == "TYPING_MARKER_IMPORT" for event in item.events)
+        if any(event.operation == "FROM" for event in item.events)
     )
     event = next(
         item for item in assessment.events
-        if item.operation == "TYPING_MARKER_IMPORT"
+        if item.operation == "FROM"
     )
     forged_assessment = replace(
         assessment,
         events=tuple(
-            replace(item, operation="FORGED_TYPING_MARKER_IMPORT")
+            replace(item, operation="FORGED_INTERNAL_IMPORT")
             if item is event else item
             for item in assessment.events
         ),
@@ -2609,17 +2605,10 @@ def test_p1d3_d2b_official_isolated_full_receipt(
             str(root), cycle_source_preparation_preview=True,
             cycle_source_publication_opt_in=True,
         )
-        assert result.cycle_source_preparation_preview.status == (
-            "PREPARED_UNPUBLISHED_NON_ATOMIC"
-        )
+        assert result.cycle_source_preparation_preview.status == "UNAVAILABLE"
         state, metadata = _persisted(root)
-        receipt = state.cycle_source_publication
-        assert receipt.version == PUBLICATION_BINDING_VERSION
-        assert receipt.prepared_manifest.version == MANIFEST_VERSION
-        component = receipt.prepared_manifest.components[0]
-        assert component.model_kind == "REGULAR_PACKAGE"
-        assert component.model_classification == "MODEL_ALL_FRESH_MEMBER_ENTRIES_PASS"
-        assert verify_co_published_cycle_manifest(
+        assert state.cycle_source_publication is None
+        assert not verify_co_published_cycle_manifest(
             state, revision=metadata.revision,
             state_id=metadata.state_id, repo_id=metadata.repo_id,
             root_path=metadata.root_path,
@@ -2672,8 +2661,9 @@ def test_p1d3_d2b2_active_import_dominates_type_only(
         {module_id: source.tree for module_id, source in parsed.items()},
         closure[0].evidence_source_modules,
     )
-    assert consistency.status == "CONSISTENT"
-    assert consistency.reason is None
+    assert consistency.status == "INDETERMINATE"
+    assert consistency.reason == "EXTERNAL_IMPORT_EXECUTION_UNMODELED"
+    assert any(site[3] == "typing" for site in consistency.unmodeled_external_imports)
     assert captured.original_worker_capture_status == (
         "ALL_SELECTED_CAPTURED_NON_ATOMIC"
     )
@@ -2698,18 +2688,14 @@ def test_p1d3_d2b2_active_import_dominates_type_only(
     assert captured.modules["pkg.a"].imports == index.modules["pkg.a"].imports
 
     scenario = evidence.scenarios.components[0]
-    assert scenario.classification == "MODEL_INTERNAL_EARLY_BINDING_HAZARD"
-    assert scenario.coverage == "COMPLETE_FRESH_MEMBER_ENTRIES"
-    assessment_a = next(
-        item for item in scenario.entry_assessments
-        if item.entry_module == "pkg.a"
-    )
-    assessment_b = next(
-        item for item in scenario.entry_assessments
-        if item.entry_module == "pkg.b"
-    )
-    assert assessment_a.outcome == "EARLY_BINDING_HAZARD"
-    assert assessment_b.outcome == "MODEL_PASS"
+    assert scenario.classification == "INDETERMINATE"
+    assert scenario.coverage == "NONE"
+    assert scenario.reason == "EXTERNAL_IMPORT_EXECUTION_UNMODELED"
+    trees = {module_id: source.tree for module_id, source in parsed.items()}
+    for entry in scenario.members:
+        assessment = evaluate_package_import_order(trees, entry)
+        assert assessment.outcome == "UNKNOWN"
+        assert assessment.reached_unmodeled_import.target == "typing"
     actual_a = run_synthetic_import(root, "pkg.a")
     actual_b = run_synthetic_import(root, "pkg.b")
     assert actual_a.returncode != 0
@@ -2723,7 +2709,7 @@ def test_p1d3_d2b2_active_import_dominates_type_only(
         evidence,
     )
     assert len(p0) == 1
-    assert p0[0].evidence_state == "DECLARED_INPUTS_CONSISTENT"
+    assert p0[0].evidence_state == "INCOMPLETE_EVIDENCE"
     p1b = assess_scc_source_bytes(
         graph.hard_edges,
         captured.source_fingerprints_by_module,
@@ -2732,7 +2718,8 @@ def test_p1d3_d2b2_active_import_dominates_type_only(
         captured.original_worker_source_snapshots,
     )
     assert len(p1b) == 1
-    assert p1b[0].bytes_state == "BYTE_AST_CONSISTENT_NON_ATOMIC"
+    assert p1b[0].bytes_state == "UNAVAILABLE"
+    assert p1b[0].reason == "INCOMPLETE_MEMBER_ENTRY_ASSESSMENTS"
 
 
 @pytest.mark.live
@@ -2773,23 +2760,10 @@ def test_p1d3_d2b3_official_isolated_full_receipt(
             str(root), cycle_source_preparation_preview=True,
             cycle_source_publication_opt_in=True,
         )
-        assert result.cycle_source_preparation_preview.status == (
-            "PREPARED_UNPUBLISHED_NON_ATOMIC"
-        )
+        assert result.cycle_source_preparation_preview.status == "UNAVAILABLE"
         state, metadata = _persisted(root)
-        receipt = state.cycle_source_publication
-        assert receipt.version == PUBLICATION_BINDING_VERSION == (
-            "cycle-prepared-co-publication/2"
-        )
-        assert receipt.prepared_manifest.version == MANIFEST_VERSION == (
-            "cycle-source-manifest/2"
-        )
-        component = receipt.prepared_manifest.components[0]
-        assert component.model_kind == "REGULAR_PACKAGE"
-        assert component.model_classification == (
-            "MODEL_ALL_FRESH_MEMBER_ENTRIES_PASS"
-        )
-        assert verify_co_published_cycle_manifest(
+        assert state.cycle_source_publication is None
+        assert not verify_co_published_cycle_manifest(
             state, revision=metadata.revision,
             state_id=metadata.state_id, repo_id=metadata.repo_id,
             root_path=metadata.root_path,
```

## FINAL_VERDICT
F1B focused regression repair: PASS dla wymaganego kontraktu testowego i źródłowego. Nie ogłaszam globalnej certyfikacji ani runtime safety; `cycle_semantics` w LIVE jest stale. STOP, oczekiwanie na przegląd audytora.
