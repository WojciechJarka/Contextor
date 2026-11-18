# SP-T4-I2B5-I4B-T63 — KOLEJNE COMMITY SCHEMA-V2

## PREFLIGHT

- DIRECT_EVIDENCE — HEAD przed zmianą: d00c759a1487e0b0732356737e64f9fa475e1eaf. Git status był czysty.
- DIRECT_EVIDENCE — Contextor MCP, revision 1445, provenance=live: T62 w test_p1d3_d2b2_type_only.py:4571-4615 miał workspace_sync=verified, canonical_state=fresh, syntax errors=0/fresh.
- DIRECT_EVIDENCE — MCP search nie znalazł wcześniej symbolu T63. Anchor dopisania: bezpośrednio po T62 na końcu testowego pliku.
- DIRECT_EVIDENCE — Interpreter docelowy: CPython 3.15.2 (.venv).

## IMPLEMENTACJA

Dodano wyłącznie jeden test, test_sp_t4_i2b5_i4b_t63_consecutive_updates, w test_p1d3_d2b2_type_only.py:4618-4692.

- DIRECT_EVIDENCE — Test odtwarza baseline z _I1_SAFE i _i1_full_engine, zachowuje pierwotne bajty pkg/c.py, wykonuje publiczne engine.update_file po zmianie źródła, a następnie ponawia update po przywróceniu oryginalnych bajtów.
- DIRECT_EVIDENCE — Nie dodano helperów, monkeypatchów, fallbacków ani alternatywnych przypadków. Produkcja nie została zmieniona.

## TARGETED_TEST

Uruchomiono wyłącznie nowy test:

    .venv\Scripts\python.exe -m pytest -q --tb=long tests/test_p1d3_d2b2_type_only.py::test_sp_t4_i2b5_i4b_t63_consecutive_updates

Wynik: FAIL, exit_code=1 — zgodnie z oczekiwaniem. Pierwsze engine.update_file zwróciło UPDATED, a następnie odczyt schema_version zgłosił KeyError. Test zatrzymał się przed zapisaniem first_evidence i przed drugim update; dlatego bieżący przebieg nie dostarcza runtime wyniku dla drugiego commitu.

Pełny traceback:

~~~~text
F                                                                        [100%]
================================== FAILURES ===================================
_________________ test_sp_t4_i2b5_i4b_t63_consecutive_updates _________________

tmp_path = WindowsPath('C:/Users/DafoO/AppData/Local/Temp/pytest-of-DafoO/pytest-1281/test_sp_t4_i2b5_i4b_t63_consec0')
isolated_dirs = WindowsPath('C:/Users/DafoO/AppData/Local/Temp/pytest-of-DafoO/pytest-1281/test_sp_t4_i2b5_i4b_t63_consec0')

    def test_sp_t4_i2b5_i4b_t63_consecutive_updates(
        tmp_path, isolated_dirs,
    ):
        root = write_synthetic_repository(
            tmp_path / "repo", _I1_SAFE
        )
        _, engine = _i1_full_engine(root)

        target = root / "pkg/c.py"
        original_source = target.read_bytes()

        assert engine.state.typing_guard_evidence[
            "schema_version"
        ] == 2
        assert _i1_guarded_import(
            engine.state
        ).type_only is True

        target.write_text(
            "import typing\n"
            "typing.TYPE_CHECKING = True\n",
            encoding="utf-8",
        )

        first = engine.update_file(str(target.resolve()))
        assert first.status == "UPDATED"

>       assert engine.state.typing_guard_evidence[
            "schema_version"
        ] == 2
E       KeyError: 'schema_version'

tests\test_p1d3_d2b2_type_only.py:4645: KeyError
=========================== short test summary info ============================
FAILED tests/test_p1d3_d2b2_type_only.py::test_sp_t4_i2b5_i4b_t63_consecutive_updates
1 failed in 3.80s
~~~~

## MCP_POST_CHANGE_AUDIT

- DIRECT_EVIDENCE — Pierwszy odczyt po edycji nadal pokazywał revision 1445 i workspace_sync=out_of_sync; zdarzenie watcher nie było jeszcze opublikowane.
- DIRECT_EVIDENCE — Po odczytowym pollu MCP LIVE events od revision 1445 zwrócił revision 1446: origin=desktop_watcher, operation=update_file, status=UPDATED, file_path=test_p1d3_d2b2_type_only.py.
- DIRECT_EVIDENCE — Event continuity=continuous, resync_required=false, resync_reason=null.
- DIRECT_EVIDENCE — Ponowny odczyt symbolu T63: canonical_revision=1446, provenance=live, canonical_state=fresh, workspace_sync=verified; zakres 4618-4692.
- DIRECT_EVIDENCE — Syntax diagnostics: 0/fresh. Families module, graph, topology i cycles: fresh; cycle_semantics: stale.
- DIRECT_EVIDENCE — Nie użyto MCP update_file, nie wykonano FULL ani restartu.

## FINAL_VERDICT

T63_FAIL_AS_EXPECTED — test został dodany zgodnie z podanym kontraktem i wykonał pierwszy publiczny update. Obecna produkcja nie utrzymała schema-v2 evidence po tym commicie; drugi update nie został osiągnięty. Brak zmian produkcyjnych.

## FILES_CHANGED

- tests/test_p1d3_d2b2_type_only.py — dodano T63; pełny diff poniżej.
- walkthrough.md — nadpisany raport; własny diff pominięty.

## FULL_DIFFS

~~~~diff
diff --git a/tests/test_p1d3_d2b2_type_only.py b/tests/test_p1d3_d2b2_type_only.py
index 7da3511..2f0b46b 100644
--- a/tests/test_p1d3_d2b2_type_only.py
+++ b/tests/test_p1d3_d2b2_type_only.py
@@ -4616,0 +4617,77 @@ def test_sp_t4_i2b5_i4b_t62_engine_global_reclassification(
+
+def test_sp_t4_i2b5_i4b_t63_consecutive_updates(
+    tmp_path, isolated_dirs,
+):
+    root = write_synthetic_repository(
+        tmp_path / "repo", _I1_SAFE
+    )
+    _, engine = _i1_full_engine(root)
+
+    target = root / "pkg/c.py"
+    original_source = target.read_bytes()
+
+    assert engine.state.typing_guard_evidence[
+        "schema_version"
+    ] == 2
+    assert _i1_guarded_import(
+        engine.state
+    ).type_only is True
+
+    target.write_text(
+        "import typing\n"
+        "typing.TYPE_CHECKING = True\n",
+        encoding="utf-8",
+    )
+
+    first = engine.update_file(str(target.resolve()))
+    assert first.status == "UPDATED"
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
+
+    assert "pkg.b" in (
+        engine.state.dependency_graph
+        .hard_edges["pkg.a"]
+    )
+
+    first_evidence = engine.state.typing_guard_evidence
+
+    target.write_bytes(original_source)
+
+    second = engine.update_file(str(target.resolve()))
+    assert second.status == "UPDATED"
+
+    assert engine.state.typing_guard_evidence[
+        "schema_version"
+    ] == 2
+    assert engine.state.typing_guard_evidence[
+        "global_policy_satisfied"
+    ] is True
+    assert _i1_guarded_import(
+        engine.state
+    ).type_only is True
+
+    assert "pkg.b" in (
+        engine.state.dependency_graph
+        .soft_edges["pkg.a"]
+    )
+    assert "pkg.b" not in (
+        engine.state.dependency_graph
+        .hard_edges["pkg.a"]
+    )
+
+    assert (
+        engine.state.typing_guard_evidence
+        is not first_evidence
+    )
+    assert first_evidence[
+        "global_policy_satisfied"
+    ] is False
+
~~~~
