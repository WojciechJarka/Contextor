# SP-T4-REMAINING-R2 — KOREKTA 7 KONTRAKTÓW

## PRECHECK

- DIRECT_EVIDENCE — Contextor MCP przed zmianą: LIVE revision 1455, provenance live, canonical state fresh, global workspace_sync unverified, resync_required=false. Syntax diagnostics 0/fresh; graph i structural cycles fresh, cycles count 16; cycle_semantics stale.
- DIRECT_EVIDENCE — per-file MCP freshness przed zmianą: wszystkie trzy test files miały workspace_sync=verified na revision 1455. Zakresy źródła odczytano z aktualnego LIVE.
- DIRECT_EVIDENCE — Git przed zmianą: HEAD 102cf6aceae0041755b6c1692d4ec2061a472882; status wskazywał wyłącznie M walkthrough.md. Trzy pliki testowe nie miały wcześniejszych zmian.
- Dokładne anchory pasowały:
  - test_cycle_semantics_canonical_state.py:168-170 — tuple pól zawierało *previous_fields, "cycle_semantics", ...
  - test_mcp_diagnostics.py:128-143, 220-234 i 705-716 — trzy wskazane słowniki availability miały dotychczas trzy klucze.
  - test_p1d3_package_cycle_integration.py:468-477 i 2275-2283 — dwie wskazane asercje oczekiwały cycle-source-manifest/2.
- Interpreter: CPython 3.15.2; pytest 9.1.1.

## EXACT_CHANGES

- test_cycle_semantics_canonical_state.py: w asercji nazw pól dodano typing_guard_evidence po previous_fields[0], zachowując kolejność reszty previous_fields. previous_fields i dalsze asercje konstruktora pozostały bez zmian.
- test_mcp_diagnostics.py: tylko oczekiwane słowniki w trzech wskazanych testach rozszerzono o soft_dependent_potential_cycles ze wskazanym stale/stale/unavailable.
- test_p1d3_package_cycle_integration.py: tylko literalne wersje w test_package_closure_and_prepared_v2 oraz test_p1d3_d2a_original_worker_prepares_v2 zmieniono z /2 na /3.
- test_c16_p0_old_evidence_semantic_version_rejected oraz test_minimal_decorator_import_effects pozostały nietknięte. Nie zmieniono produkcji, innych testów ani issues.md.

## TARGETED_RESULTS

Uruchomiono na CPython 3.15.2 dokładnie te siedem node IDs z --tb=long:

| Node ID | Wynik |
|---|---|
| tests/test_cycle_semantics_canonical_state.py::test_existing_constructor_compatibility | PASS |
| tests/test_mcp_diagnostics.py::test_resync_diagnostics_summary_hides_fresh_payloads_without_mutation | FAIL |
| tests/test_mcp_diagnostics.py::test_get_name_collisions_hides_fresh_details_during_resync | PASS |
| tests/test_mcp_diagnostics.py::test_wrapper_diagnostics_exception_cannot_replace_successful_tool_result | PASS |
| tests/test_p1d3_package_cycle_integration.py::test_package_closure_and_prepared_v2[fixture0] | PASS |
| tests/test_p1d3_package_cycle_integration.py::test_package_closure_and_prepared_v2[fixture1] | PASS |
| tests/test_p1d3_package_cycle_integration.py::test_p1d3_d2a_original_worker_prepares_v2 | PASS |

Wynik: 6 passed, 1 failed, 2 warnings in 10.55s. Ostrzeżenia to AuthlibDeprecationWarning dla Authlib/JWT i integracji Authlib HTTPX. Nie wykonano kolejnej poprawki ani dodatkowych testów.

Pełny traceback jedynego FAIL z pytest:

~~~text
____ test_resync_diagnostics_summary_hides_fresh_payloads_without_mutation ____

    def test_resync_diagnostics_summary_hides_fresh_payloads_without_mutation():
        syntax_facts = {
            "broken.py": {"status": "checked_with_errors", "errors": [{"message": "bad"}]}
        }
        collisions = [_collision()]
        cycles = [["a", "b", "a"]]
        state = SimpleNamespace(
            resync_required=True,
            syntax_diagnostics_state="fresh",
            syntax_diagnostics_by_path=syntax_facts,
            collisions_state="fresh",
            collisions=collisions,
            cycles_state="fresh",
            cycles=cycles,
        )

        summary = diagnostics_summary_for_state(state)

        assert summary["availability"] == {
            "syntax_errors": "stale",
            "name_collisions": "stale",
            "cycles": "stale",
            "soft_dependent_potential_cycles": "stale",
        }
        assert summary["syntax_errors"] == {"count": None, "availability": "stale"}
        assert summary["name_collisions"] == {
            "count": None,
            "critical": None,
            "warning": None,
            "info": None,
            "availability": "stale",
        }
        assert summary["cycles"] == {
            "count": None,
            "availability": "stale",
            "count_semantics": "DFS_BACK_EDGE_PATHS_DEDUP_ROTATION_NOT_ALL_SIMPLE_CYCLES",
        }
        assert summary["attention_required"] is False
        assert state.syntax_diagnostics_by_path is syntax_facts
        assert state.collisions is collisions
        assert state.cycles is cycles

        state.resync_required = False
        recovered = diagnostics_summary_for_state(state)
>       assert recovered["availability"] == {
            "syntax_errors": "fresh",
            "name_collisions": "fresh",
            "cycles": "fresh",
        }
E       AssertionError: assert {'syntax_errors': 'fresh', 'name_collisions': 'fresh', 'cycles': 'fresh', 'soft_dependent_potential_cycles': 'unavailable'} == {'syntax_errors': 'fresh', 'name_collisions': 'fresh', 'cycles': 'fresh'}
E
E         Common items:
E         {'cycles': 'fresh', 'name_collisions': 'fresh', 'syntax_errors': 'fresh'}
E         Left contains one more item:
E         {'soft_dependent_potential_cycles': 'unavailable'}
E
E         Full diff:
E           {
E               'syntax_errors': 'fresh',
E               'name_collisions': 'fresh',
E               'cycles': 'fresh',
E         +     'soft_dependent_potential_cycles': 'unavailable',
E           }

tests\test_mcp_diagnostics.py:163: AssertionError
~~~

## CONTRACT_VERIFICATION

- CODE_PATH_PROVED — MCP class implementation contextor/core/analysis/state_manager.py:86-205 declares typing_guard_evidence as a keyword-only dataclass field after modules. The updated field-name tuple matches this declaration; the targeted constructor test passes.
- CODE_PATH_PROVED — contextor/core/diagnostics_projection.py:93-278 returns soft_dependent_potential_cycles and includes its availability in the summary availability mapping. The stale-resync branch reports stale for this family.
- CODE_PATH_PROVED — contextor/core/diagnostics_projection.py:1-92 defines _soft_dependent_cycle_diagnostic. For resync_required=True it reports stale. After recovery it requires cycles_state=fresh and dependency_graph.hard_edges/soft_edges to be Mapping objects; absent or invalid graph data returns unavailable. This test's SimpleNamespace has no dependency_graph, so the post-resync actual value unavailable is consistent with that code path.
- CODE_PATH_PROVED — contextor/core/cycle_semantics/generation_manifest.py:34 defines MANIFEST_VERSION as cycle-source-manifest/3. contextor/core/cycle_semantics/original_worker_preparation.py:43-255 validates the prepared manifest against MANIFEST_VERSION. Both package fixtures and the original-worker targeted test pass after the literal expectation changes.
- DIRECT_EVIDENCE — post-change MCP reads returned revision 1458, provenance live, canonical state fresh, global workspace_sync unverified, resync_required=false, syntax diagnostics 0/fresh, graph fresh and cycles 16/fresh. cycle_semantics remains stale.
- DIRECT_EVIDENCE — per-file MCP source reads at revision 1458 returned workspace_sync=verified for all three changed test files. MCP get_source_range returned the edited anchors exactly as requested.
- CONTRACT_PROVED — the six passing node IDs confirm their changed assertions pass against the current test/runtime paths. This is scoped test evidence, not a general semantic certification.
- INFERENCE — the test names test_package_closure_and_prepared_v2 and test_p1d3_d2a_original_worker_prepares_v2 still say v2 while their targeted assertions now require version 3; names were explicitly frozen by the prompt.
- UNKNOWN — no claim is made here about broader correctness beyond the exact changed assertions and read code paths.

## LIMITATIONS

- One targeted test remains FAIL at its separate post-resync recovery assertion. The prompt limited the edit to adding stale to the first expected dictionary and prohibited changing the remaining recovery assertions; no second edit was made.
- The actual recovered availability contains soft_dependent_potential_cycles=unavailable because this synthetic state has no dependency_graph, as confirmed by the current helper. The remaining exact three-key expectation does not include this value.
- No source/test modifications were made outside the three requested test assertions. No full pytest, production FULL, restart, staging, commit or push was performed.

## FILES_CHANGED

- tests/test_cycle_semantics_canonical_state.py
- tests/test_mcp_diagnostics.py
- tests/test_p1d3_package_cycle_integration.py
- walkthrough.md — overwritten report; excluded from its own diff.

## FULL_DIFFS

~~~diff
diff --git a/tests/test_cycle_semantics_canonical_state.py b/tests/test_cycle_semantics_canonical_state.py
index beb0efb..30f9454 100644
--- a/tests/test_cycle_semantics_canonical_state.py
+++ b/tests/test_cycle_semantics_canonical_state.py
@@ -165,7 +165,8 @@ def test_existing_constructor_compatibility() -> None:
         "shared_usage_clusters_state", "trie", "package_root",
     )
     assert tuple(field.name for field in fields(RepositoryAnalysisState)) == (
-        *previous_fields, "cycle_semantics", "cycle_semantics_state",
+        previous_fields[0], "typing_guard_evidence",
+        *previous_fields[1:], "cycle_semantics", "cycle_semantics_state",
         "cycle_semantics_invalidation_reason",
     )
     seed = RepositoryAnalysisState()
diff --git a/tests/test_mcp_diagnostics.py b/tests/test_mcp_diagnostics.py
index 1c7de24..d92f950 100644
--- a/tests/test_mcp_diagnostics.py
+++ b/tests/test_mcp_diagnostics.py
@@ -138,6 +138,7 @@ def test_resync_diagnostics_summary_hides_fresh_payloads_without_mutation():
         "syntax_errors": "stale",
         "name_collisions": "stale",
         "cycles": "stale",
+        "soft_dependent_potential_cycles": "stale",
     }
     assert summary["syntax_errors"] == {"count": None, "availability": "stale"}
     assert summary["name_collisions"] == {
@@ -227,6 +228,7 @@ def test_get_name_collisions_hides_fresh_details_during_resync(tmp_path, monkeyp
         "syntax_errors": "stale",
         "name_collisions": "stale",
         "cycles": "stale",
+        "soft_dependent_potential_cycles": "stale",
     }
     assert result["diagnostics_summary"]["name_collisions"]["count"] is None
     assert state.collisions is collisions
@@ -713,5 +715,6 @@ def test_wrapper_diagnostics_exception_cannot_replace_successful_tool_result(
         "syntax_errors": "unavailable",
         "name_collisions": "unavailable",
         "cycles": "unavailable",
+        "soft_dependent_potential_cycles": "unavailable",
     }
     assert result["diagnostics_attention_required"] is False
diff --git a/tests/test_p1d3_package_cycle_integration.py b/tests/test_p1d3_package_cycle_integration.py
index e149079..4456279 100644
--- a/tests/test_p1d3_package_cycle_integration.py
+++ b/tests/test_p1d3_package_cycle_integration.py
@@ -470,7 +470,7 @@ def test_package_closure_and_prepared_v2(tmp_path, isolated_dirs, fixture):
     assert prepared.status == "PREPARED_UNPUBLISHED_NON_ATOMIC"
     assert prepared.source_modules == closure[0].evidence_source_modules
     manifest = prepared.manifest
-    assert manifest.version == MANIFEST_VERSION == "cycle-source-manifest/2"
+    assert manifest.version == MANIFEST_VERSION == "cycle-source-manifest/3"
     assert manifest.source_manifest_sha256 is not None
     component = manifest.components[0]
     assert component.model_kind == "REGULAR_PACKAGE"
@@ -2277,7 +2277,7 @@ def test_p1d3_d2a_original_worker_prepares_v2(tmp_path, isolated_dirs):
         captured, graph.hard_edges, snapshot,
     )
     assert prepared.status == "PREPARED_UNPUBLISHED_NON_ATOMIC"
-    assert prepared.manifest.version == "cycle-source-manifest/2"
+    assert prepared.manifest.version == "cycle-source-manifest/3"
     component = prepared.manifest.components[0]
     assert component.model_kind == "REGULAR_PACKAGE"
     assert component.model_classification == "MODEL_ALL_FRESH_MEMBER_ENTRIES_PASS"
~~~
