# SP-T4-REMAINING-R4 — OLD EVIDENCE REJECTION

## PRECHECK

- DIRECT_EVIDENCE — Contextor MCP przed zmianą: LIVE revision 1459, provenance live, canonical state fresh, global workspace_sync unverified, resync_required=false. Syntax diagnostics 0/fresh; graph fresh; cycles 16/fresh; cycle_semantics stale.
- DIRECT_EVIDENCE — test_c16_p0_old_evidence_semantic_version_rejected miał per-file workspace_sync=verified na revision 1459. Dokładny anchor zgadzał się z promptem.
- DIRECT_EVIDENCE — Git przed zmianą: HEAD 1b5900d351a5c2d0263bf331d7087846d392082d. Zmieniany test nie miał wcześniejszego diffu; status zawierał wcześniejsze M walkthrough.md.
- Interpreter docelowy: CPython 3.15.2.

## EXACT_CHANGE

W tests/test_p1d3_package_cycle_integration.py, wyłącznie w test_c16_p0_old_evidence_semantic_version_rejected:
- zmieniono asercję baseline z cycle-semantics-evidence/3 na cycle-semantics-evidence/4;
- pozostawiono OLD jako cycle-semantics-evidence/2;
- bezpośrednio po asercji reason dodano sprawdzenia evidence_state=EVIDENCE_MISMATCH oraz model_classification=INDETERMINATE.

Nie zmieniono innych testów, fixture, produkcji ani issues.md.

## TARGETED_RESULT

Uruchomiono wyłącznie:
tests/test_p1d3_package_cycle_integration.py::test_c16_p0_old_evidence_semantic_version_rejected

Komenda użyła CPython 3.15.2 z --tb=long. Wynik: 1 passed in 1.88s. Brak tracebacku. Nie uruchomiono pełnego pytest ani FULL.

## CONTRACT_VERIFICATION

- CODE_PATH_PROVED — bieżący Contextor MCP odczytał contextor/core/cycle_semantics/evidence.py na revision 1460, workspace_sync=verified. EVIDENCE_SEMANTIC_VERSION w linii 32 wynosi cycle-semantics-evidence/4.
- CODE_PATH_PROVED — assess_index_bound_scc_models w liniach 107-363 porównuje source_evidence.semantic_version z EVIDENCE_SEMANTIC_VERSION po wcześniejszych kontrolach graph fingerprint i topology. Różnica ustawia reason EVIDENCE_SEMANTIC_VERSION_MISMATCH.
- CODE_PATH_PROVED — dla global_reason assessor tworzy SCCModelEvidenceAssessment z model_classification=INDETERMINATE, domyślnym evidence_state=EVIDENCE_MISMATCH i podanym reason.
- DIRECT_EVIDENCE — test pozostawia OLD=/2, a PASS potwierdza końcowe asercje reason, evidence_state i model_classification dla tego syntetycznego przypadku.
- MCP post-change audit: LIVE revision 1460, provenance live, canonical state fresh, global workspace_sync unverified, resync_required=false; syntax diagnostics 0/fresh; graph fresh; cycles 16/fresh.
- Per-file MCP audit: tests/test_p1d3_package_cycle_integration.py ma workspace_sync=verified na revision 1460. MCP source range zwrócił dokładnie zmieniony test.
- HEAD pozostał 1b5900d351a5c2d0263bf331d7087846d392082d. Nie wykonywano staging, commit ani push.

## FILES_CHANGED

- tests/test_p1d3_package_cycle_integration.py
- walkthrough.md — nadpisany raport; wyłączony z własnego diffu.

## FULL_DIFFS

~~~diff
diff --git a/tests/test_p1d3_package_cycle_integration.py b/tests/test_p1d3_package_cycle_integration.py
index 4456279..5e69606 100644
--- a/tests/test_p1d3_package_cycle_integration.py
+++ b/tests/test_p1d3_package_cycle_integration.py
@@ -2991,7 +2991,7 @@ def test_c16_p0_old_evidence_semantic_version_rejected(
         tmp_path / "repo", D2A_ACTIVE_CHAIN,
     )
     _, graph, captured, _, evidence, snapshot = _d2a_source_evidence(root)
-    assert evidence.semantic_version == "cycle-semantics-evidence/3"
+    assert evidence.semantic_version == "cycle-semantics-evidence/4"
     previous = replace(
         evidence, semantic_version="cycle-semantics-evidence/2",
     )
@@ -3002,3 +3002,5 @@ def test_c16_p0_old_evidence_semantic_version_rejected(
         previous,
     )
     assert assessment[0].reason == "EVIDENCE_SEMANTIC_VERSION_MISMATCH"
+    assert assessment[0].evidence_state == "EVIDENCE_MISMATCH"
+    assert assessment[0].model_classification == "INDETERMINATE"
~~~
