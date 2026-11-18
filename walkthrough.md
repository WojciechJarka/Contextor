# SP-T4-I2B5-I4B-T62 — REGRESJA PRODUKCYJNA

## PREFLIGHT

- DIRECT_EVIDENCE — HEAD przed edycją: ecca01b8ae74ba983fbfee6d30bf76762742f736; po walidacji nadal ten sam.
- DIRECT_EVIDENCE — Git status przed edycją: jedynie M walkthrough.md z poprzedniego raportu; brak zmian w teście i produkcji.
- DIRECT_EVIDENCE — Contextor MCP, canonical revision 1444, provenance=live: workspace_sync=verified dla test_p1d3_d2b2_type_only.py; syntax errors=0/fresh. MCP potwierdził T06 w liniach 2722-2736, T60 w 4401-4524 i T61 do końca pliku.
- DIRECT_EVIDENCE — Anchor dopisania: koniec T61 w test_p1d3_d2b2_type_only.py:4568-4569.
- DIRECT_EVIDENCE — Interpreter: CPython 3.15.2 (.venv).

## IMPLEMENTACJA

Dodano jeden test: test_sp_t4_i2b5_i4b_t62_engine_global_reclassification, w test_p1d3_d2b2_type_only.py:4571-4615.

- DIRECT_EVIDENCE — Test tworzy repozytorium z _I1_SAFE i baseline przez _i1_full_engine(root), jak T60.
- DIRECT_EVIDENCE — Zachowuje referencje modules, evidence i graph; potwierdza schema-v2, początkową type_only=True oraz soft edge pkg.a -> pkg.b.
- DIRECT_EVIDENCE — Zapisuje wskazane źródło pkg/c.py i wywołuje publiczne engine.update_file bezpośrednio w linii 4598. Nie stosuje monkeypatch.
- DIRECT_EVIDENCE — Po wyniku UPDATED sprawdza schema-v2, global_policy_satisfied=False, type_only=False, hard edge bez soft edge oraz niezależną tożsamość trzech opublikowanych obiektów. Na końcu potwierdza zachowanie wcześniejszej kandydatury, evidence i soft edge przez zachowane referencje.
- DIRECT_EVIDENCE — Nie zmieniono plików produkcyjnych ani innych testów.

## TARGETED_TESTS

Uruchomiono wyłącznie nowy node ID:

    .venv\Scripts\python.exe -m pytest -q --tb=long tests/test_p1d3_d2b2_type_only.py::test_sp_t4_i2b5_i4b_t62_engine_global_reclassification

Wynik: oczekiwany FAIL, exit_code=1. Publiczne update_file zwróciło UPDATED. Następna asercja otrzymała KeyError, ponieważ typing_guard_evidence nie zawiera schema_version.

Pełny traceback pytest:

~~~~text
F                                                                        [100%]
================================== FAILURES ===================================
___________ test_sp_t4_i2b5_i4b_t62_engine_global_reclassification ____________

tmp_path = WindowsPath('C:/Users/DafoO/AppData/Local/Temp/pytest-of-DafoO/pytest-1280/test_sp_t4_i2b5_i4b_t62_engine0')
isolated_dirs = WindowsPath('C:/Users/DafoO/AppData/Local/Temp/pytest-of-DafoO/pytest-1280/test_sp_t4_i2b5_i4b_t62_engine0')

    def test_sp_t4_i2b5_i4b_t62_engine_global_reclassification(
        tmp_path, isolated_dirs,
    ):
        root = write_synthetic_repository(
            tmp_path / "repo", _I1_SAFE
        )
        _, engine = _i1_full_engine(root)

        before_modules = engine.state.modules
        before_evidence = engine.state.typing_guard_evidence
        before_graph = engine.state.dependency_graph

        assert before_evidence["schema_version"] == 2
        assert _i1_guarded_import(engine.state).type_only is True
        assert "pkg.b" in before_graph.soft_edges["pkg.a"]

        before_guarded = next(
            ref for ref in before_modules["pkg.a"].imports
            if ref.module == "pkg.b"
        )
        assert before_guarded.type_only is True

        target = root / "pkg/c.py"
        target.write_text(
            "import typing\ntyping.TYPE_CHECKING = True\n",
            encoding="utf-8",
        )
        result = engine.update_file(str(target.resolve()))
        assert result.status == "UPDATED"

>       assert engine.state.typing_guard_evidence["schema_version"] == 2
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E       KeyError: 'schema_version'

tests\test_p1d3_d2b2_type_only.py:4601: KeyError
=========================== short test summary info ============================
FAILED tests/test_p1d3_d2b2_type_only.py::test_sp_t4_i2b5_i4b_t62_engine_global_reclassification
1 failed in 3.96s
~~~~

## MCP_POST_CHANGE_AUDIT

- DIRECT_EVIDENCE — Pierwszy odczyt po edycji wskazał canonical_revision=1444 i workspace_sync=out_of_sync.
- DIRECT_EVIDENCE — Bez MCP update_file odczytano LIVE events od revision 1444. Desktop watcher opublikował revision 1445: operation=update_file, origin=desktop_watcher, status=UPDATED, file_path=test_p1d3_d2b2_type_only.py.
- DIRECT_EVIDENCE — Ciągłość zdarzeń: continuous; resync_required=false; resync_reason=null.
- DIRECT_EVIDENCE — Ponowny odczyt symbolu T62: canonical_revision=1445, provenance=live, canonical_state=fresh, workspace_sync=verified, linie 4571-4615.
- DIRECT_EVIDENCE — Syntax diagnostics: 0/fresh. Families module, graph, topology i cycles: fresh; cycle_semantics: stale.
- DIRECT_EVIDENCE — Nie wykonano MCP update_file, FULL ani restartu.

## FINAL_VERDICT

T62_FAIL_AS_EXPECTED — test odtwarza publiczny przepływ engine.update_file i wykazuje brak opublikowanego schema-v2 evidence po statusie UPDATED. Oczekiwane asercje grafu i zachowania starych referencji nie zostały osiągnięte, ponieważ test zatrzymał się na KeyError. Produkcja pozostała bez zmian.

## FILES_CHANGED

- tests/test_p1d3_d2b2_type_only.py — dodano jeden wskazany test; pełny diff poniżej.
- walkthrough.md — nadpisany raport; jego własny diff jest pominięty.
- Pliki produkcyjne — bez zmian.

## FULL_DIFFS

~~~~diff
diff --git a/tests/test_p1d3_d2b2_type_only.py b/tests/test_p1d3_d2b2_type_only.py
index 2e882b7..7da3511 100644
--- a/tests/test_p1d3_d2b2_type_only.py
+++ b/tests/test_p1d3_d2b2_type_only.py
@@ -4569,0 +4570,47 @@ def test_sp_t4_i2b5_i4a_t61_invalid_candidate_payload(
+
+def test_sp_t4_i2b5_i4b_t62_engine_global_reclassification(
+    tmp_path, isolated_dirs,
+):
+    root = write_synthetic_repository(
+        tmp_path / "repo", _I1_SAFE
+    )
+    _, engine = _i1_full_engine(root)
+
+    before_modules = engine.state.modules
+    before_evidence = engine.state.typing_guard_evidence
+    before_graph = engine.state.dependency_graph
+
+    assert before_evidence["schema_version"] == 2
+    assert _i1_guarded_import(engine.state).type_only is True
+    assert "pkg.b" in before_graph.soft_edges["pkg.a"]
+
+    before_guarded = next(
+        ref for ref in before_modules["pkg.a"].imports
+        if ref.module == "pkg.b"
+    )
+    assert before_guarded.type_only is True
+
+    target = root / "pkg/c.py"
+    target.write_text(
+        "import typing\ntyping.TYPE_CHECKING = True\n",
+        encoding="utf-8",
+    )
+    result = engine.update_file(str(target.resolve()))
+    assert result.status == "UPDATED"
+
+    assert engine.state.typing_guard_evidence["schema_version"] == 2
+    assert engine.state.typing_guard_evidence[
+        "global_policy_satisfied"
+    ] is False
+    assert _i1_guarded_import(engine.state).type_only is False
+    assert "pkg.b" in engine.state.dependency_graph.hard_edges["pkg.a"]
+    assert "pkg.b" not in engine.state.dependency_graph.soft_edges["pkg.a"]
+
+    assert engine.state.modules is not before_modules
+    assert engine.state.typing_guard_evidence is not before_evidence
+    assert engine.state.dependency_graph is not before_graph
+
+    assert before_evidence["schema_version"] == 2
+    assert before_guarded.type_only is True
+    assert "pkg.b" in before_graph.soft_edges["pkg.a"]
~~~~
