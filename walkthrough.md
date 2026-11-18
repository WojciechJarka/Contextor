# SP-T4-I2B5-I4B-T64-T65 — KONTRAKTY NEGATYWNE

## PREFLIGHT

- DIRECT_EVIDENCE — HEAD przed zmianą: 8a72459e9a743fbc5cbc9c1400ebd1b3658fdc3f; Git status był czysty.
- DIRECT_EVIDENCE — Contextor MCP revision 1446, provenance=live: T63 w test_p1d3_d2b2_type_only.py:4618-4692 był workspace_sync=verified, canonical_state=fresh, syntax errors=0/fresh.
- DIRECT_EVIDENCE — MCP search nie znalazł wcześniej symboli T64 ani T65. Anchor dopisania: bezpośrednio po T63.
- DIRECT_EVIDENCE — Interpreter: CPython 3.15.2 (.venv).

## IMPLEMENTACJA

Dodano dokładnie dwa testy w tests/test_p1d3_d2b2_type_only.py:

- test_sp_t4_i2b5_i4b_t64_deletion_restores_soft, linie 4695-4744.
- test_sp_t4_i2b5_i4b_t65_invalid_baseline_fails_closed, linie 4747-4786.

DIRECT_EVIDENCE — T64 buduje FULL z mutacją w pkg/c.py, potwierdza baseline schema-v2 i hard edge, usuwa plik i wykonuje publiczne engine.update_file. T65 unieważnia baseline evidence, zmienia pkg/c.py i sprawdza fail-closed na stanie oraz grafie. Nie dodano helperów ani monkeypatchów; nie zmieniono istniejących asercji ani produkcji.

## TARGETED_TESTS

Uruchomiono wyłącznie T64 i T65 z --tb=long:

    .venv\Scripts\python.exe -m pytest -q --tb=long tests/test_p1d3_d2b2_type_only.py::test_sp_t4_i2b5_i4b_t64_deletion_restores_soft tests/test_p1d3_d2b2_type_only.py::test_sp_t4_i2b5_i4b_t65_invalid_baseline_fails_closed

Wynik: 2 failed in 5.79s, exit_code=1 — zgodnie z oczekiwaniem.

- T64 dochodzi do statusu DELETED i potwierdza usunięcie pkg.c z modules, po czym fails z KeyError: schema_version.
- T65 potwierdza status UPDATED i puste evidence; następnie guarded ImportRef zachowuje type_only=True, więc assertion oczekująca False fails.
- W T64 nie zostały osiągnięte późniejsze asercje o przywróceniu schema-v2, global_policy_satisfied=True i soft edge.
- W T65 nie zostały osiągnięte późniejsze asercje o hard edge oraz braku soft edge.

Pełne wyjście pytest z tracebackami:

~~~~text
FF                                                                       [100%]
================================== FAILURES ===================================
_______________ test_sp_t4_i2b5_i4b_t64_deletion_restores_soft ________________

tmp_path = WindowsPath('C:/Users/DafoO/AppData/Local/Temp/pytest-of-DafoO/pytest-1282/test_sp_t4_i2b5_i4b_t64_deleti0')
isolated_dirs = WindowsPath('C:/Users/DafoO/AppData/Local/Temp/pytest-of-DafoO/pytest-1282/test_sp_t4_i2b5_i4b_t64_deleti0')

    def test_sp_t4_i2b5_i4b_t64_deletion_restores_soft(
        tmp_path, isolated_dirs,
    ):
        root = write_synthetic_repository(
            tmp_path / "repo", _I1_SAFE
        )
        target = root / "pkg/c.py"
        target.write_text(
            "import typing\n"
            "typing.TYPE_CHECKING = True\n",
            encoding="utf-8",
        )
        _, engine = _i1_full_engine(root)

        assert engine.state.typing_guard_evidence[
            "schema_version"
        ] == 2
        assert engine.state.typing_guard_evidence[
            "global_policy_satisfied"
        ] is False
        assert _i1_guarded_import(
            engine.state
        ).type_only is False
        assert "pkg.b" in (
            engine.state.dependency_graph
            .hard_edges["pkg.a"]
        )

        target.unlink()
        result = engine.update_file(str(target.resolve()))

        assert result.status == "DELETED"
        assert "pkg.c" not in engine.state.modules
>       assert engine.state.typing_guard_evidence[
            "schema_version"
        ] == 2
E       KeyError: 'schema_version'

tests\test_p1d3_d2b2_type_only.py:4728: KeyError
____________ test_sp_t4_i2b5_i4b_t65_invalid_baseline_fails_closed ____________

tmp_path = WindowsPath('C:/Users/DafoO/AppData/Local/Temp/pytest-of-DafoO/pytest-1282/test_sp_t4_i2b5_i4b_t65_invali0')
isolated_dirs = WindowsPath('C:/Users/DafoO/AppData/Local/Temp/pytest-of-DafoO/pytest-1282/test_sp_t4_i2b5_i4b_t65_invali0')

    def test_sp_t4_i2b5_i4b_t65_invalid_baseline_fails_closed(
        tmp_path, isolated_dirs,
    ):
        root = write_synthetic_repository(
            tmp_path / "repo", _I1_SAFE
        )
        _, engine = _i1_full_engine(root)

        assert _i1_guarded_import(
            engine.state
        ).type_only is True
        assert "pkg.b" in (
            engine.state.dependency_graph
            .soft_edges["pkg.a"]
        )

        engine.state.typing_guard_evidence = {}

        target = root / "pkg/c.py"
        target.write_text(
            "import typing\n"
            "typing.TYPE_CHECKING = True\n",
            encoding="utf-8",
        )

        result = engine.update_file(str(target.resolve()))
        assert result.status == "UPDATED"

        assert engine.state.typing_guard_evidence == {}
>       assert _i1_guarded_import(
            engine.state
        ).type_only is False
E       AssertionError: assert True is False
E        +  where True = ImportRef(module='pkg.b', level=0, names=[], is_from_import=False, is_local=False, type_only=True, is_lazy=False).type_only
E        +    where ImportRef(module='pkg.b', level=0, names=[], is_from_import=False, is_local=False, type_only=True, is_lazy=False) = _i1_guarded_import(RepositoryAnalysisState(modules={'pkg.a': Module(module_id='pkg.a', path='pkg\\a.py', absolute_path='C:\\Users\\DafoO\...LUATED'), schema_version='1.0.0'), cycle_semantics_state='stale', cycle_semantics_invalidation_reason='SOURCE_CHANGED'))
E        +      where RepositoryAnalysisState(modules={'pkg.a': Module(module_id='pkg.a', path='pkg\\a.py', absolute_path='C:\\Users\\DafoO\...LUATED'), schema_version='1.0.0'), cycle_semantics_state='stale', cycle_semantics_invalidation_reason='SOURCE_CHANGED') = <contextor.core.analysis.incremental.engine.IncrementalAnalysisEngine object at 0x000002352CBCB4D0>.state

tests\test_p1d3_d2b2_type_only.py:4776: AssertionError
=========================== short test summary info ===========================
FAILED tests/test_p1d3_d2b2_type_only.py::test_sp_t4_i2b5_i4b_t64_deletion_restores_soft
FAILED tests/test_p1d3_d2b2_type_only.py::test_sp_t4_i2b5_i4b_t65_invalid_baseline_fails_closed
2 failed in 5.79s
~~~~

## MCP_POST_CHANGE_AUDIT

- DIRECT_EVIDENCE — Pierwsze dwa odczyty events od revision 1446 nie zawierały nowego zdarzenia. Późniejszy poll zwrócił revision 1447: origin=desktop_watcher, operation=update_file, status=UPDATED, file_path=tests/test_p1d3_d2b2_type_only.py.
- DIRECT_EVIDENCE — Event continuity=continuous, resync_required=false, resync_reason=null.
- DIRECT_EVIDENCE — MCP odczytał T64 i T65 jako kompletne symbole, workspace_sync=verified, provenance=live, canonical_revision=1447.
- DIRECT_EVIDENCE — Syntax diagnostics: 0/fresh. Families module, graph, topology i cycles: fresh; cycle_semantics: stale.
- DIRECT_EVIDENCE — Nie wykonano MCP update_file, FULL ani restartu.

## FINAL_VERDICT

T64_T65_FAIL_AS_EXPECTED — oba publiczne testy zostały dodane literalnie. Bieżąca produkcja nie odtwarza wymaganej klasyfikacji po deletion i nie fail-close klasyfikacji nieedytowanego modułu przy pustym baseline. Produkcja pozostała bez zmian.

## FILES_CHANGED

- tests/test_p1d3_d2b2_type_only.py — dopisano T64 i T65; pełny diff poniżej.
- walkthrough.md — nadpisany raport; własny diff pominięty.

## FULL_DIFFS

~~~~diff
diff --git a/tests/test_p1d3_d2b2_type_only.py b/tests/test_p1d3_d2b2_type_only.py
index 2f0b46b..39435a5 100644
--- a/tests/test_p1d3_d2b2_type_only.py
+++ b/tests/test_p1d3_d2b2_type_only.py
@@ -4693,0 +4694,94 @@ def test_sp_t4_i2b5_i4b_t63_consecutive_updates(
+
+def test_sp_t4_i2b5_i4b_t64_deletion_restores_soft(
+    tmp_path, isolated_dirs,
+):
+    root = write_synthetic_repository(
+        tmp_path / "repo", _I1_SAFE
+    )
+    target = root / "pkg/c.py"
+    target.write_text(
+        "import typing\n"
+        "typing.TYPE_CHECKING = True\n",
+        encoding="utf-8",
+    )
+    _, engine = _i1_full_engine(root)
+
+    assert engine.state.typing_guard_evidence[
+        "schema_version"
+    ] == 2
+    assert engine.state.typing_guard_evidence[
+        "global_policy_satisfied"
+    ] is False
+    assert _i1_guarded_import(
+        engine.state
+    ).type_only is False
+    assert "pkg.b" in (
+        engine.state.dependency_graph
+        .hard_edges["pkg.a"]
+    )
+
+    target.unlink()
+    result = engine.update_file(str(target.resolve()))
+
+    assert result.status == "DELETED"
+    assert "pkg.c" not in engine.state.modules
+    assert engine.state.typing_guard_evidence[
+        "schema_version"
+    ] == 2
+    assert engine.state.typing_guard_evidence[
+        "global_policy_satisfied"
+    ] is True
+    assert _i1_guarded_import(
+        engine.state
+    ).type_only is True
+    assert "pkg.b" in (
+        engine.state.dependency_graph
+        .soft_edges["pkg.a"]
+    )
+    assert "pkg.b" not in (
+        engine.state.dependency_graph
+        .hard_edges["pkg.a"]
+    )
+
+
+def test_sp_t4_i2b5_i4b_t65_invalid_baseline_fails_closed(
+    tmp_path, isolated_dirs,
+):
+    root = write_synthetic_repository(
+        tmp_path / "repo", _I1_SAFE
+    )
+    _, engine = _i1_full_engine(root)
+
+    assert _i1_guarded_import(
+        engine.state
+    ).type_only is True
+    assert "pkg.b" in (
+        engine.state.dependency_graph
+        .soft_edges["pkg.a"]
+    )
+
+    engine.state.typing_guard_evidence = {}
+
+    target = root / "pkg/c.py"
+    target.write_text(
+        "import typing\n"
+        "typing.TYPE_CHECKING = True\n",
+        encoding="utf-8",
+    )
+
+    result = engine.update_file(str(target.resolve()))
+    assert result.status == "UPDATED"
+
+    assert engine.state.typing_guard_evidence == {}
+    assert _i1_guarded_import(
+        engine.state
+    ).type_only is False
+    assert "pkg.b" in (
+        engine.state.dependency_graph
+        .hard_edges["pkg.a"]
+    )
+    assert "pkg.b" not in (
+        engine.state.dependency_graph
+        .soft_edges["pkg.a"]
+    )
+
~~~~
