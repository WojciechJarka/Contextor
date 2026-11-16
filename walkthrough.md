# SP-T4-I2B1 — ImportRef semantic delta

## PREFLIGHT

DIRECT_EVIDENCE: Contextor MCP first: `get_project_architecture(fields=[])` zwrócił LIVE revision 1417, canonical_state fresh, resync_required=false, syntax_errors=0/fresh. `get_module_context` dla `contextor.core.analysis.incremental.preparation`, `contextor.core.analysis.refresh_planner`, `contextor.core.domain.imports` i `tests.test_p1d3_d2b2_type_only`: revision 1417, `workspace_sync=verified` dla wszystkich. Git HEAD `0b3cdbe3b032e047b9ac789f9b5e4ac0404dfb75`, status czysty. Potwierdzone anchory: `calculate_file_delta` w `preparation.py:62-114`, `RefreshPlanner.plan_refresh` i `has_import_changes` w `refresh_planner.py:81-278`, `ImportRef` w `domain/imports.py:11-29`. Przed edycją plan diffu obejmował wyłącznie `preparation.py` po imports_added/imports_removed, `refresh_planner.py` przy has_import_changes, dopisanie T17–T21 do `tests/test_p1d3_d2b2_type_only.py` oraz raport.

## EXACT IMPLEMENTATION

Po wyznaczeniu zbiorów nazw w `calculate_file_delta` dodano literalne porównanie `old_imports != (new_imports or [])`, które ustawia `delta.metadata_changes['import_ref_payload_changed']=True`. W `RefreshPlanner` istniejące `has_import_changes` uwzględnia tę flagę; prowadzi do już istniejących rodzin `modules` i `dependency_graph` oraz przeliczeń metryk/cykli. Nie zmieniono `imports_changed`, API FileDelta, innych gałęzi planera, resolvera ani żadnej nowej patch family.

## IMPORTREF DELTA CONTRACT

CODE_PATH_PROVED: `ImportRef` jest `@dataclass(frozen=True)` z polami `module`, `level`, `names`, `is_from_import`, `is_local`, `type_only`, `is_lazy`; równość dataclass porównuje wszystkie wartości. Porównanie list importów obejmuje też kolejność i wielość rekordów. T17: zmiana strażnika przy tych samych nazwach daje puste `imports_added`/`imports_removed`, ale nową flagę payloadu. T20 parametryzuje zmiany `level`, `names`, `is_from_import`, `is_local`, `is_lazy` przy niezmienionym `module` i potwierdza tę samą drogę; nie ma wyjątku dla TYPE_CHECKING. T21: odrębne, ale wartościowo identyczne `ImportRef` nie ustawia flagi. `FileDelta.is_empty` już uwzględnia `metadata_changes`, więc zmiana payloadu nie zostaje uznana za no-op.

## REFRESH PLAN CONTRACT

DIRECT_EVIDENCE T17/T20: plan przy flagę payloadu obejmuje `modules`, `dependency_graph` i `cycles` w graph_recomputations. T21: identyczny payload nie planuje grafu. Istniejące testy `test_2_import_add`, `test_3_import_remove`, `test_7_reexport_retarget`, `test_10_noop_delta` przeszły. Ścieżki import add/remove oraz no-op pozostają czynne.

## TARGETED TESTS

CPython 3.15.2, `C:\Temp\Contextor_Repo\.venv\Scripts\python.exe`. Wybrane T17–T21 (T18/T19 dwa kierunki, T20 pięć pól) oraz cztery testy planera: `13 passed, 249 deselected` w 10.07 s. Dodatkowo dwa istniejące testy `tests/test_incremental_equivalence.py` dla add/import delta i `test_refresh_planner.py::test_10_noop_delta`: `3 passed` w 3.74 s. Łącznie 16 zaliczonych uruchomień przypadków, bez pełnego pytest. `git diff --check` bez błędów whitespace.

## FULL/INCREMENTAL PARITY

DIRECT_EVIDENCE T18: bezpieczny bazowy FULL na repo syntetycznym ma `pkg.a -> pkg.b` soft i `type_only=True`; zmiana samego warunku na `if True` dała rzeczywiste `update_file` status `UPDATED`, puste lists imports_added/removal, flagę payloadu, plan modules+dependency_graph, `type_only=False` i hard edge do `pkg.b`. Świeży FULL na oddzielnym końcowym repo miał identyczne flagi oraz całe hard_edges i soft_edges. T19 w przeciwnym kierunku dał `UPDATED`, `type_only=True`, hard→soft i tę samą parity ze świeżym FULL. Testy nie mockowały resolvera. To dowód dla tych dwóch izolowanych scenariuszy, nie dla wszystkich projektowych bramek bezpieczeństwa TYPE_CHECKING.

## MCP POST-CHANGE AUDIT

DIRECT_EVIDENCE: `get_project_architecture(fields=[])` po zmianach: LIVE revision **1420**, resync_required=false, syntax_errors=0/fresh, hard cycles=16 deduplikowanych DFS paths/fresh, soft-dependent potential SCC=1/fresh; cycle_semantics stale. `get_module_context` dla preparation, refresh_planner i test file: revision 1420, `workspace_sync=verified`, graph/cycles fresh. Pełna projekcja dependencies_outbound dla preparation: 11 hard edges, bez soft; obejmuje istniejący indexer oraz typing_guard. Refresh_planner: 5 hard edges, bez soft. Nie wykonano MCP update_file, FULL Contextora ani restartu. Świeżość źródła LIVE nie atestuje loaded-code procesu.

## FINAL_VERDICT

`I2B1_PASS` dla literalnego kontraktu import payload delta, planu i wskazanych porównań incremental/FULL. Zakres pozostałych projektowych bramek type_only nie jest objęty tym etapem.

## FILES_CHANGED

- `contextor/core/analysis/incremental/preparation.py`
- `contextor/core/analysis/refresh_planner.py`
- `tests/test_p1d3_d2b2_type_only.py`
- `walkthrough.md` — raport bez własnego diffu zgodnie z AGENTS.md pkt 10.

Nie zmieniono `domain/imports.py`, `issues.md`, `audyt.txt` ani Spiral Prophet.

## FULL_DIFFS

Pełny rzeczywisty diff plików zmienionych w SP-T4-I2B1:

```diff
diff --git a/contextor/core/analysis/incremental/preparation.py b/contextor/core/analysis/incremental/preparation.py
index 438ccc8..3afde46 100644
--- a/contextor/core/analysis/incremental/preparation.py
+++ b/contextor/core/analysis/incremental/preparation.py
@@ -88,6 +88,10 @@ def calculate_file_delta(
 
     delta.imports_added = sorted(new_import_names - old_import_names)
     delta.imports_removed = sorted(old_import_names - new_import_names)
+    if old_imports != (new_imports or []):
+        delta.metadata_changes[
+            "import_ref_payload_changed"
+        ] = True
 
     new_artifact_names = extract_artifact_names(new_artifacts_dict)
     old_artifact_names = extract_artifact_names(old_artifacts or {})
diff --git a/contextor/core/analysis/refresh_planner.py b/contextor/core/analysis/refresh_planner.py
index 973211f..6cff332 100644
--- a/contextor/core/analysis/refresh_planner.py
+++ b/contextor/core/analysis/refresh_planner.py
@@ -206,6 +206,10 @@ class RefreshPlanner:
         has_import_changes = False
         if delta and (delta.imports_added or delta.imports_removed or delta.imports_changed):
             has_import_changes = True
+        if delta and delta.metadata_changes.get(
+            "import_ref_payload_changed"
+        ):
+            has_import_changes = True
         if usage_delta and (usage_delta.added_imports or usage_delta.removed_imports):
             has_import_changes = True
 
diff --git a/tests/test_p1d3_d2b2_type_only.py b/tests/test_p1d3_d2b2_type_only.py
index 81c074e..eec3654 100644
--- a/tests/test_p1d3_d2b2_type_only.py
+++ b/tests/test_p1d3_d2b2_type_only.py
@@ -13,11 +13,13 @@ import sys
 from dataclasses import replace
 from importlib.machinery import EXTENSION_SUFFIXES, SOURCE_SUFFIXES
 from pathlib import Path
+from types import SimpleNamespace
 
 import pytest
 
 from contextor.core.analysis.cache_manager import CacheManager
 from contextor.core.analysis.incremental import preparation
+from contextor.core.analysis.refresh_planner import RefreshPlanner
 from contextor.core.analysis.state_manager import RepositoryAnalysisState, load_engine_state
 from contextor.core.api.facade import ContextorFacade
 from contextor.core.live_state.hydration import hydrate_repository_engine
@@ -26,6 +28,7 @@ from contextor.core.paths import repo_cache_dir
 from contextor.core.cycle_semantics.original_worker_reindex_planning import plan_original_worker_reindex
 from contextor.core.cycle_semantics.package_model import evaluate_package_import_order
 from contextor.core.cycle_semantics.scenarios import analyze_cycle_scenarios
+from contextor.core.domain.imports import ImportRef
 from contextor.core.graph.graph import build_graph
 from contextor.core.graph.resolver import build_trie, detect_package_root
 from contextor.core.reference.shared import materialize_reexport_facts_by_module
@@ -2900,3 +2903,130 @@ def test_sp_t4_i2a_t16_guard_change_same_import_names(tmp_path):
     assert after.typing_guard_source_evidence["marker_mutation"] is False
     assert after.typing_guard_source_evidence["opaque_effects"] is False
 
+
+def _i2b1_source(*, guarded: bool) -> str:
+    condition = "TYPE_CHECKING" if guarded else "True"
+    return (
+        "from typing import TYPE_CHECKING\n"
+        f"if {condition}:\n"
+        "    import pkg.b\n"
+        "value = 1\n"
+    )
+
+
+def test_sp_t4_i2b1_t17_same_names_semantic_delta_plans_graph(
+    tmp_path, isolated_dirs,
+):
+    root = write_synthetic_repository(tmp_path / "repo", _I1_SAFE)
+    _, engine = _i1_full_engine(root)
+    target = root / "pkg/a.py"
+    target.write_text(_i2b1_source(guarded=False), encoding="utf-8")
+    prepared = preparation.prepare_source_update(
+        file_path=target,
+        module_path="pkg.a",
+        is_new=False,
+        old_module=engine.state.modules["pkg.a"],
+        old_artifacts=engine.state.artifacts.get("pkg.a"),
+        old_usage=engine.state.module_usages.get("pkg.a"),
+        persistent_id=engine.registry.get_module_id("pkg.a"),
+        old_collision_facts=engine.state.collision_facts.get("pkg.a"),
+        old_reexport_facts=engine.state.reexport_facts_by_module.get("pkg.a"),
+    )
+    assert not prepared.has_error
+    assert prepared.delta.imports_added == []
+    assert prepared.delta.imports_removed == []
+    assert prepared.delta.metadata_changes["import_ref_payload_changed"] is True
+    plan = RefreshPlanner.plan_refresh(
+        prepared.delta,
+        usage_delta=prepared.usage_delta,
+        module_usages=engine.state.module_usages,
+        collision_facts_changed=prepared.collision_facts_changed,
+    )
+    assert "modules" in plan.patch_families
+    assert "dependency_graph" in plan.patch_families
+    assert "cycles" in plan.graph_recomputations
+
+
+@pytest.mark.parametrize("initial_guarded", [True, False], ids=["t18-soft-to-hard", "t19-hard-to-soft"])
+def test_sp_t4_i2b1_t18_t19_direct_incremental_full_parity(
+    tmp_path, isolated_dirs, initial_guarded,
+):
+    initial_fixture = {
+        **_I1_SAFE,
+        "pkg/a.py": _i2b1_source(guarded=initial_guarded),
+    }
+    root = write_synthetic_repository(tmp_path / "repo", initial_fixture)
+    _, engine = _i1_full_engine(root)
+    before = _i1_guarded_import(engine.state)
+    assert before.type_only is initial_guarded
+    assert ("pkg.b" in engine.state.dependency_graph.soft_edges.get("pkg.a", set())) is initial_guarded
+    target = root / "pkg/a.py"
+    final_source = _i2b1_source(guarded=not initial_guarded)
+    target.write_text(final_source, encoding="utf-8")
+    result = engine.update_file(str(target.resolve()))
+    assert result.status == "UPDATED"
+    assert result.delta.imports_added == []
+    assert result.delta.imports_removed == []
+    assert result.delta.metadata_changes["import_ref_payload_changed"] is True
+    assert "modules" in result.shadow_plan.patch_families
+    assert "dependency_graph" in result.shadow_plan.patch_families
+    incremental = engine.state
+    assert _i1_guarded_import(incremental).type_only is not initial_guarded
+    assert ("pkg.b" in incremental.dependency_graph.hard_edges.get("pkg.a", set())) is initial_guarded
+    assert ("pkg.b" in incremental.dependency_graph.soft_edges.get("pkg.a", set())) is not initial_guarded
+
+    fresh_root = write_synthetic_repository(
+        tmp_path / "fresh", {**initial_fixture, "pkg/a.py": final_source},
+    )
+    fresh, _ = _i1_full_engine(fresh_root)
+    assert _i1_guarded_import(incremental).type_only == _i1_guarded_import(fresh).type_only
+    assert incremental.dependency_graph.hard_edges == fresh.dependency_graph.hard_edges
+    assert incremental.dependency_graph.soft_edges == fresh.dependency_graph.soft_edges
+
+
+@pytest.mark.parametrize(
+    "changes",
+    [
+        {"level": 1},
+        {"names": ["Other"]},
+        {"is_from_import": True},
+        {"is_local": True},
+        {"is_lazy": True},
+    ],
+    ids=["level", "names", "from", "local", "lazy"],
+)
+def test_sp_t4_i2b1_t20_other_import_ref_field_changes(changes):
+    original = ImportRef(
+        module="pkg.b", level=0, names=[], is_from_import=False,
+    )
+    changed = replace(original, **changes)
+    assert original != changed
+    delta = preparation.calculate_file_delta(
+        module_path="pkg.a", persistent_id="M1", is_new=False,
+        old_module=SimpleNamespace(imports=[original]),
+        old_artifacts={}, new_imports=[changed], new_artifacts_dict={},
+    )
+    assert delta.imports_added == []
+    assert delta.imports_removed == []
+    assert delta.metadata_changes["import_ref_payload_changed"] is True
+    plan = RefreshPlanner.plan_refresh(delta)
+    assert "modules" in plan.patch_families
+    assert "dependency_graph" in plan.patch_families
+
+
+def test_sp_t4_i2b1_t21_identical_import_ref_no_graph_plan():
+    original = ImportRef(
+        module="pkg.b", level=0, names=[], is_from_import=False,
+    )
+    delta = preparation.calculate_file_delta(
+        module_path="pkg.a", persistent_id="M1", is_new=False,
+        old_module=SimpleNamespace(imports=[original]),
+        old_artifacts={}, new_imports=[replace(original)], new_artifacts_dict={},
+    )
+    assert delta.imports_added == []
+    assert delta.imports_removed == []
+    assert "import_ref_payload_changed" not in delta.metadata_changes
+    plan = RefreshPlanner.plan_refresh(delta)
+    assert "dependency_graph" not in plan.patch_families
+    assert plan.graph_recomputations == ()
+
```
