# CONTEXTOR P1D3-B/C — CANONICAL PACKAGE-AWARE CYCLE SEMANTICS

## 1. EXECUTIVE VERDICT

**GO for the specified restricted P1D3-B/C contract.** The shared evidence-source closure, package identity/graph checks, canonical scenario dispatch, P0 v2 claim binding, P1B byte/AST plus independent semantic replay, v2 manifest/receipt, and read-only v1 receipt verification are implemented. The final focused set passed **282 tests** in **60.56 s** (exit 0, no skips or warnings in pytest output). A later one-case addition tested forged `MODEL_PASS` as well as forged hazard events: **2 passed** in **2.09 s**. No global suite was run. No active Contextor FULL/LIVE operation was invoked.

**Git event:** Initial HEAD was `b71c70143b00968662e21070a033ddf5fdd7e279`. During this task, an external local mechanism created `51fa1dee4498038a1b71779dfcb5d8f23cf8b543` (`Auto-commit: Cleanup and update`, author `WojciechJarka`) while edits were in progress. I issued no Git mutation command. The report's raw diff is against the **initial HEAD** so the auto-committed and remaining worktree edits are both visible. Final HEAD/worktree status should be checked again before any later stage because that external mechanism may run again.

Evidence labels: **DIRECT_EVIDENCE** = observed source/test/Git output; **CODE_PATH_PROVED** = inspected implementation path; **CONTRACT_PROVED** = explicit validated type/status/version contract; **INFERENCE** = bounded deduction; **UNKNOWN** = unverified.

## 2. IMPLEMENTED SOURCE CLOSURE

**CODE_PATH_PROVED:** `model_source_closure.py` defines `MODEL_SOURCE_CLOSURE_VERSION="cycle-model-source-closure/1"`, frozen `CycleModelSourceClosure`, and `compute_cycle_model_source_closures`. It starts from canonical SCCs, preserves hard-edge reachability separately, and takes a finite fixed point over hard targets and existing indexed parent `.__init__` IDs. The evidence set is deterministic and sorted; `implicit_initializer_modules` contains only added initializer IDs. It does not alter `ProjectGraph.hard_edges`. Plan and binding now call this common function. The 16-module, 2 MiB/source and 32 MiB aggregate limits remain. F1 selects `pkg.__init__`, `pkg.a`, `pkg.b`; F2 does likewise. A 17-module selected union returns `CLOSURE_MODULE_LIMIT` before second indexing. A test checks that an initializer's hard edge is followed to another source and its parent initializer.

## 3. PACKAGE IDENTITY CONTRACT

**CONTRACT_PROVED:** `model_identity.py` maps indexed `pkg.__init__ -> pkg`, nested `pkg.sub.__init__ -> pkg.sub`, and leaves ordinary IDs unchanged. Reverse mapping returns `None` for both direct/initializer collision, missing name, namespace guess or external target. Indexed source IDs remain unchanged in closure, fingerprints and manifest. Logical names are passed only to the standalone package model and mapped back for SCC hazard attribution.

## 4. GRAPH-SOURCE CONSISTENCY CONTRACT

**CODE_PATH_PROVED:** `package_graph_consistency.py` compares supported AST import forms against exact canonical hard-edge targets for each evidence source. It supports direct indexed modules/packages, exact module from-imports, explicit relative module targets, and explicit relative sibling imports with an inert initializer. It rejects missing indexed targets, missing regular initializers, ambiguous package-member/attribute cases, unsupported/star forms, out-of-bounds relative imports, missing hard edges and contradictory extra hard edges with stable `INDETERMINATE` reasons. Soft candidate edges are not promoted. No analyzed source is executed and the graph is not mutated. F7 keeps an SCC but adds a contradictory extra hard edge; it reports `GRAPH_SOURCE_IMPORT_MISMATCH`.

## 5. FLAT/PACKAGE DISPATCH

**CODE_PATH_PROVED:** `scenarios.py` computes the shared closure and applies existing 64-entry, 4096-statement and 16384-AST-node budgets to it. Flat-ID SCCs meeting the original exact graph/AST prerequisites still call `evaluate_flat_import_order` and retain `CLOSED_FLAT_MODULE_FRESH_ENTRY_MODEL`. Dotted/package cases enter the conservative package graph check and call existing `evaluate_package_import_order` per logical SCC entry; their assessments remain `PackageImportAssessment` with `model_kind=REGULAR_PACKAGE`, `CLOSED_REGULAR_PACKAGE_FRESH_ENTRY_MODEL`. Unknown or unsupported paths remain `INDETERMINATE` with actual coverage. F1/F2 yield two package `MODEL_PASS` entries. An isolated FULL preview of F1 returned `PREPARED_UNPUBLISHED_NON_ATOMIC` with initializer source in a v2 manifest.

## 6. SCC HAZARD ATTRIBUTION

**CONTRACT_PROVED:** Package hazards require a terminal `EARLY_BINDING_HAZARD`, matching assessment target, and exact logical-to-indexed translation of source/target into the same SCC. Event sequences retain logical package names. F3 produced an internal hazard for fresh `pkg.a`; F4 kept the same hard-edge graph and produced all-entry `MODEL_PASS`. Controlled CPython F3 failed with `ImportError` and the partially initialized module message; F4 succeeded. The F3/F4 evidence tokens differed.

## 7. P0 EVIDENCE VALIDATION

**CODE_PATH_PROVED:** `evidence.py` v2 uses the shared source closure for exact signature inventory and component token. P0 still checks graph fingerprint, topology, SCC/member/internal edges, lexical import sites, index fingerprints, source cohort, scopes, assessment types and exact entry order. Flat claims require `ImportOrderAssessment`/flat scopes; package claims require `PackageImportAssessment`/package scopes. Mixed types and malformed event types fail. P0 checks the terminal hazard identity but does **not** independently replay intermediate model steps. A dedicated test substitutes a flat assessment into a package claim and gets `INCOMPLETE_MEMBER_ENTRY_ASSESSMENTS`.

## 8. P1B SEMANTIC REPLAY

**CODE_PATH_PROVED:** `source_proof.py` retains raw SHA, index SHA, source signature, reparsed AST hash and byte-budget checks. After all component bytes pass, it rebuilds canonical scenario evidence from those verified ASTs with an execution-local parsed-source cache, compares the complete component scenario, scenario fingerprint and component token, and returns `MODEL_REPLAY_MISMATCH` for discrepant claims. Budget-limited replay returns `MODEL_REPLAY_UNAVAILABLE`. Forged intermediate events on both `MODEL_PASS` and hazard claims passed limited P0 declaration checks but failed P1B replay in focused tests. No filesystem read, LIVE call or analyzed-code execution occurs in replay.

## 9. V2 EVIDENCE TOKENS

**CONTRACT_PROVED:** `EVIDENCE_SEMANTIC_VERSION="cycle-semantics-evidence/2"`. `scenario_fingerprint = sha256(canonical JSON of dataclasses.asdict(CycleComponentScenarios))`; canonical JSON uses sorted keys and compact separators. The v2 component token includes version, SCC members, hard subgraph over the expanded evidence-source closure, source signatures, model kind, scenario scope and scenario fingerprint. An intermediate event change alters the token even with identical source and graph declarations. This is declaration binding, not worker authentication.

## 10. V2 MANIFEST FORMAT

**CONTRACT_PROVED:** `MANIFEST_VERSION="cycle-source-manifest/2"`. Positive `PreparedSCCSourceBinding` rows add `model_kind` and a 64-hex `model_evidence_sha256` only after P1B success. V2 manifest digest includes component members, classification, kind, model digest, signatures and ordered unique sources. Any unavailable SCC has no model digest and suppresses the global source-manifest hash. The original prepared-only authority and `PREPARED_UNPUBLISHED_NON_ATOMIC` status are retained.

## 11. V1 LEGACY RECEIPT COMPATIBILITY

**CONTRACT_PROVED:** New sealing emits only `cycle-prepared-co-publication/2` over manifest v2. Read-only verification distinguishes v1 receipt/v1 manifest from v2/v2; mixed pairs fail. V1 verification uses old hard-edge-only closure and old manifest/claim digest formulas, with flat-only model scope. An isolated flat-state test constructed a valid v1-compatible receipt from the original formulas and verified it; mixed v1/v2 and new sealing of v1 failed. Existing snapshots were not rewritten. `LIVE_STATE_SCHEMA_VERSION` remains `1.4`. This verifies contract behavior, not the bytes of an external historical snapshot.

## 12. OFFICIAL PUBLICATION INTEGRITY

**DIRECT_EVIDENCE:** An isolated F1 test used the existing `_official_live` helper, actual `ContextorFacade.analyze_project` opt-in FULL on `tmp_path`, the canonical store, the existing queue and `LiveStateClient.verify_installed_cycle_generation`. It observed a v2 manifest/receipt, matching repo/state/revision/graph/service identity, successful queue publication and `status=ok` installed-generation verification. Tampering with the manifest model digest caused receipt verification to fail. This does not establish active Desktop adoption, active Contextor LIVE publication, source cross-file atomicity, authenticated worker provenance or arbitrary runtime safety.

## 13. SYNTHETIC REPOSITORY FIXTURES

**CODE_PATH_PROVED:** `tests/cycle_semantics_lab/__init__.py` writes deterministic UTF-8 fixtures under `tmp_path`, rejects absolute/traversing/non-Python/non-POSIX/duplicate-normalized paths, and provides a bounded `sys.executable -I -B` differential helper. New focused tests cover F1–F12 concepts: dotted/relative pass, hazard/reordering, unsupported decorator, namespace, contradictory graph, forged assessment, mixed flat/package SCCs, 17-module bound, v1 receipt and official isolated publication. The test fixture writer never imports analyzed source.

## 14. CPYTHON DIFFERENTIAL RESULTS

**DIRECT_EVIDENCE from controlled synthetic subprocesses:** F1 `pkg.a` and `pkg.b` imports succeeded; F2 `pkg.a` and `pkg.b` succeeded; F3 `pkg.a` failed with `ImportError` containing `partially initialized module`; F4 `pkg.a` succeeded. The helper captured stdout, stderr and exit code with an 8-second timeout. No arbitrary user repository was executed.

## 15. EXACT TEST COMMANDS AND RESULTS

All commands ran from `C:\Temp\Contextor_Repo` with `& .\.venv\Scripts\python.exe`.

1. `-m py_compile` on the ten changed production modules: exit 0, no output. Repeated after final source edits: exit 0.
2. `-m pytest -q tests/test_p1d3_package_cycle_integration.py -x`: 9 passed in 9.31 s, exit 0 at that checkpoint.
3. `-m pytest -q tests/test_p1d3_package_cycle_integration.py::test_official_isolated_package_publication`: 1 passed in 3.93 s, exit 0.
4. Initial five-module focused run with `-x`: 39 passed, 1 failed in 2.98 s, exit 1. The failure was the old P0 expectation for a modified entry without a recomputed v2 token.
5. Full five-module focused run: 115 passed, 5 failed in 12.20 s, exit 1. Four failures were v2 token/version-sensitive test expectations; one expected the formerly unsupported package fixture to remain negative. The negative fixture was changed to an unsupported decorator; no negative regression was deleted.
6. P0 and FULL preparation rerun with `-x`: 32 passed, 1 failed in 22.62 s, exit 1, due remaining old T18 reason expectation; corrected to the v2 component-token mismatch.
7. `-m pytest -q tests/test_cycle_semantics_evidence.py tests/test_original_worker_full_preparation_optin.py tests/test_original_worker_full_receipt_optin.py -x`: 93 passed in 18.51 s, exit 0.
8. Initial broad focused run covering scenarios, package model/layout, evidence, manifest, worker, FULL, receipt, isolated official LIVE, IPC and parity: 279 passed, 1 failed in 66.70 s, exit 1. The one old dotted-import negative used a now-supported form; it was retained as a negative test with an unsupported decorator.
9. `-m pytest -q tests/test_original_worker_real_pipeline_preparation.py::test_p1d2d_t08_unsupported_dotted_package_remains_fail_closed`: 1 passed in 1.84 s, exit 0.
10. `-m pytest -q tests/test_cycle_semantics_evidence.py tests/test_p1d3_package_cycle_integration.py`: 87 passed in 10.86 s, exit 0 after event-type validation.
11. `-m pytest -q tests/test_p1d3_package_cycle_integration.py tests/test_cycle_semantics_scenarios.py tests/test_original_worker_real_pipeline_preparation.py::test_p1d2d_t08_unsupported_dotted_package_remains_fail_closed`: 30 passed in 7.42 s, exit 0 after closure correction.
12. Final broad focused command: `-m pytest -q tests/test_cycle_semantics_scenarios.py tests/test_cycle_semantics_package_model.py tests/test_cycle_semantics_package_layout.py tests/test_cycle_semantics_evidence.py tests/test_original_worker_manifest_preparation.py tests/test_original_worker_reindex_planning.py tests/test_original_worker_cycle_closure_binding.py tests/test_original_worker_real_pipeline_preparation.py tests/test_original_worker_full_preparation_optin.py tests/test_original_worker_full_receipt_optin.py tests/test_original_worker_official_full_live_publication.py tests/test_original_worker_real_ipc_generation.py tests/test_cycle_semantics_full_integration.py tests/test_cycle_semantics_publication_live_integration.py tests/test_p1d3_package_cycle_integration.py`: **282 passed in 60.56 s**, exit 0, no skips/warnings reported.
13. Final targeted forged-event parameterization: `-m pytest -q tests/test_p1d3_package_cycle_integration.py::test_p1b_replay_rejects_forged_event`: **2 passed in 2.09 s**, exit 0.
14. `git diff --check` against initial HEAD: exit 0; Git printed only CRLF normalization warnings, no whitespace errors.

Focused validations only. The global suite was not run.

## 16. ACTUAL FILES CHANGED

All paths below are relative to `C:\Temp\Contextor_Repo`; their **complete actual diff against initial HEAD** follows in section 21. `walkthrough.md` is the report and excluded from production/test accounting.

1. `contextor/core/cycle_semantics/evidence.py`
2. `contextor/core/cycle_semantics/generation_manifest.py`
3. `contextor/core/cycle_semantics/model_identity.py` (new)
4. `contextor/core/cycle_semantics/model_source_closure.py` (new)
5. `contextor/core/cycle_semantics/original_worker_binding.py`
6. `contextor/core/cycle_semantics/original_worker_reindex_planning.py`
7. `contextor/core/cycle_semantics/package_graph_consistency.py` (new)
8. `contextor/core/cycle_semantics/publication_binding.py`
9. `contextor/core/cycle_semantics/scenarios.py`
10. `contextor/core/cycle_semantics/source_proof.py`
11. `tests/cycle_semantics_lab/__init__.py` (new)
12. `tests/test_cycle_semantics_evidence.py`
13. `tests/test_original_worker_full_preparation_optin.py`
14. `tests/test_original_worker_real_pipeline_preparation.py`
15. `tests/test_p1d3_package_cycle_integration.py` (new)

## 17. KNOWN UNSUPPORTED SEMANTICS

Arbitrary decorators, metaclasses, import hooks, dynamic imports, namespace/ambiguous package layouts, package attribute shadowing in `from package import member`, and unproven control-flow execution remain `INDETERMINATE`. `from . import b` is positive only with an inert initializer and exact indexed child. The package model still covers its explicitly restricted subset; no general Python runtime-safety certification is made.

## 18. BLOCKERS OR CONTRACT CONFLICTS

No production-contract blocker remained. The external auto-commit changed HEAD during the turn despite the task's no-Git-mutation instruction; no agent-issued Git mutation was used. The full raw diff is therefore anchored to the initial HEAD. No active LIVE/MCP loaded-code adoption was tested or claimed.

## 19. P1D3-B/C VERDICT

**GO** for G01–G20 within the restricted contract and focused evidence above. `DIRECT_EVIDENCE`: F1/F2 package prepared manifests, F3/F4 differential behavior, F8 replay rejection, F10 bound, F11 legacy in-memory verification, F12 isolated official publication and the 282-test passing run. `CONTRACT_PROVED`: v2 hashes, scopes, types, receipt identity and fail-closed statuses. `UNKNOWN`: global-suite result, external historical v1 snapshot bytes and active Desktop loaded-code adoption.

## 20. NEXT RECOMMENDATION

Stop at P1D3-B/C. Await the architect's next explicit `proceduj`. Do not start P1D3-D/E or active LIVE certification from this report.

## 21. ACTUAL_DIFF / FULL_DIFF

The following fenced patch is the complete `git diff --no-ext-diff --no-color b71c70143b00968662e21070a033ddf5fdd7e279 -- contextor tests`. It includes changes already caught by the external auto-commit and changes still in the worktree.

```diff
diff --git a/contextor/core/cycle_semantics/evidence.py b/contextor/core/cycle_semantics/evidence.py
index 3d2c966..1978497 100644
--- a/contextor/core/cycle_semantics/evidence.py
+++ b/contextor/core/cycle_semantics/evidence.py
@@ -10,19 +10,22 @@ import ast
 import hashlib
 import json
 from collections.abc import Mapping
-from dataclasses import dataclass
+from dataclasses import asdict, dataclass
 from typing import Any
 
 from contextor.core.source import ParsedSourceInput
 
 from .contracts import CycleSemanticsSnapshot, fingerprint_hard_edges
 from .scc import analyze_import_cycle_topology
-from .initialization_model import ImportOrderAssessment
+from .initialization_model import ImportOrderAssessment, ModelEvent
+from .package_model import PackageImportAssessment, PackageModelEvent
+from .model_source_closure import compute_cycle_model_source_closures
+from .model_identity import indexed_to_logical_module, logical_to_indexed_module
 from .scenarios import (
     CycleComponentScenarios, CycleScenarioReport, analyze_cycle_scenarios,
 )
 
-EVIDENCE_SEMANTIC_VERSION = "cycle-semantics-evidence/1"
+EVIDENCE_SEMANTIC_VERSION = "cycle-semantics-evidence/2"
 _MISSING = "MISSING"
 
 
@@ -40,6 +43,24 @@ class ComponentSourceEvidence:
     classification: str
     coverage: str
     reason: str | None
+    model_kind: str = "FLAT_MODULE"
+
+
+def _scenario_fingerprint(scenario: CycleComponentScenarios) -> str:
+    return _digest(asdict(scenario))
+
+
+def _component_token(
+    members: tuple[str, ...],
+    subgraph: tuple[tuple[str, tuple[str, ...]], ...],
+    signatures: tuple[tuple[str, str, str], ...],
+    scenario: CycleComponentScenarios,
+) -> str:
+    return _digest((
+        EVIDENCE_SEMANTIC_VERSION, members, subgraph, signatures,
+        scenario.model_kind, scenario.evidence_scope,
+        _scenario_fingerprint(scenario),
+    ))
 
 
 @dataclass(frozen=True)
@@ -153,6 +174,7 @@ def assess_index_bound_scc_models(
     cyclic_members = tuple(sorted(
         member for component in components for member in component.members
     ))
+    closures = compute_cycle_model_source_closures(hard_edges)
     outputs: list[SCCModelEvidenceAssessment] = []
     for position, (structural, scenario, evidence) in enumerate(zip(
         components, source_evidence.scenarios.components,
@@ -191,14 +213,7 @@ def assess_index_bound_scc_models(
             outputs.append(result(members, "SCENARIO_EVIDENCE_MISMATCH"))
             continue
 
-        closure = set(members)
-        pending = list(members)
-        while pending:
-            for target in adjacency[pending.pop()]:
-                if target not in closure:
-                    closure.add(target)
-                    pending.append(target)
-        expected_closure = tuple(sorted(closure))
+        expected_closure = closures[position].evidence_source_modules
         signatures = evidence.source_signatures
         if not isinstance(signatures, tuple) or any(
             not isinstance(row, tuple) or len(row) != 3
@@ -231,9 +246,7 @@ def assess_index_bound_scc_models(
             outputs.append(result(members, "SOURCE_INDEX_FINGERPRINT_MISMATCH:" + bad_source))
             continue
         subgraph = tuple((node, adjacency[node]) for node in expected_closure)
-        expected_token = _digest((
-            EVIDENCE_SEMANTIC_VERSION, members, subgraph, signatures,
-        ))
+        expected_token = _component_token(members, subgraph, signatures, scenario)
         if evidence.evidence_token != expected_token:
             outputs.append(result(members, "COMPONENT_EVIDENCE_TOKEN_MISMATCH"))
             continue
@@ -253,15 +266,43 @@ def assess_index_bound_scc_models(
         ):
             outputs.append(result(members, "SNAPSHOT_SOURCE_IDENTITY_MISMATCH"))
             continue
+        model_contracts = {
+            "FLAT_MODULE": (
+                ImportOrderAssessment,
+                "RESTRICTED_FLAT_MODULE_MODEL",
+                "CLOSED_FLAT_MODULE_FRESH_ENTRY_MODEL",
+                members,
+            ),
+            "REGULAR_PACKAGE": (
+                PackageImportAssessment,
+                "RESTRICTED_REGULAR_PACKAGE_MODEL",
+                "CLOSED_REGULAR_PACKAGE_FRESH_ENTRY_MODEL",
+                tuple(indexed_to_logical_module(member) for member in members),
+            ),
+        }
+        contract = model_contracts.get(scenario.model_kind)
         if (
-            scenario.evidence_scope != "CLOSED_FLAT_MODULE_FRESH_ENTRY_MODEL"
+            contract is None
+            or evidence.model_kind != scenario.model_kind
+            or scenario.evidence_scope != contract[2]
             or scenario.coverage != "COMPLETE_FRESH_MEMBER_ENTRIES"
             or not isinstance(scenario.entry_assessments, tuple)
-            or any(not isinstance(a, ImportOrderAssessment)
-                   for a in scenario.entry_assessments)
-            or tuple(a.entry_module for a in scenario.entry_assessments) != members
-            or any(a.evidence_scope != "RESTRICTED_FLAT_MODULE_MODEL"
+            or any(type(a) is not contract[0] for a in scenario.entry_assessments)
+            or tuple(a.entry_module for a in scenario.entry_assessments) != contract[3]
+            or len(set(contract[3])) != len(contract[3])
+            or any(a.evidence_scope != contract[1]
                    for a in scenario.entry_assessments)
+            or any(
+                type(a.events) is not tuple
+                or any(
+                    type(event) is not (
+                        ModelEvent if scenario.model_kind == "FLAT_MODULE"
+                        else PackageModelEvent
+                    )
+                    for event in a.events
+                )
+                for a in scenario.entry_assessments
+            )
             or any(a.outcome == "UNKNOWN" for a in scenario.entry_assessments)
         ):
             outputs.append(result(
@@ -283,8 +324,15 @@ def assess_index_bound_scc_models(
                 a.outcome == "EARLY_BINDING_HAZARD"
                 and a.events
                 and a.events[-1].operation == "EARLY_BINDING_HAZARD"
-                and a.events[-1].module in member_set
-                and a.events[-1].target in member_set
+                and a.events[-1].target == a.target_module
+                and (
+                    logical_to_indexed_module(a.events[-1].module, frozenset(adjacency))
+                    if scenario.model_kind == "REGULAR_PACKAGE" else a.events[-1].module
+                ) in member_set
+                and (
+                    logical_to_indexed_module(a.events[-1].target, frozenset(adjacency))
+                    if scenario.model_kind == "REGULAR_PACKAGE" else a.events[-1].target
+                ) in member_set
                 for a in scenario.entry_assessments
             ):
                 outputs.append(SCCModelEvidenceAssessment(
@@ -530,26 +578,17 @@ def build_source_bound_cycle_evidence(
     source_manifest = tuple((name, *signatures[name]) for name in sorted(signatures))
 
     components: list[ComponentSourceEvidence] = []
-    for component in report.components:
-        visited = set(component.members)
-        pending = list(component.members)
-        while pending:
-            for target in adjacency[pending.pop()]:
-                if target not in visited:
-                    visited.add(target)
-                    pending.append(target)
-        closure = tuple(sorted(visited))
+    closures = compute_cycle_model_source_closures(hard_edges)
+    for component, closure_row in zip(report.components, closures):
+        closure = closure_row.evidence_source_modules
         source_signatures = tuple(
             (module, *signatures.get(module, (_MISSING, _MISSING)))
             for module in closure
         )
         subgraph = tuple((node, adjacency[node]) for node in closure)
-        token = _digest((
-            EVIDENCE_SEMANTIC_VERSION,
-            component.members,
-            subgraph,
-            source_signatures,
-        ))
+        token = _component_token(
+            component.members, subgraph, source_signatures, component,
+        )
         components.append(ComponentSourceEvidence(
             members=component.members,
             reachable_modules=closure,
@@ -558,6 +597,7 @@ def build_source_bound_cycle_evidence(
             classification=component.classification,
             coverage=component.coverage,
             reason=component.reason,
+            model_kind=component.model_kind,
         ))
 
     return SourceBoundCycleEvidence(
diff --git a/contextor/core/cycle_semantics/generation_manifest.py b/contextor/core/cycle_semantics/generation_manifest.py
index afd2372..6ce72e1 100644
--- a/contextor/core/cycle_semantics/generation_manifest.py
+++ b/contextor/core/cycle_semantics/generation_manifest.py
@@ -20,9 +20,10 @@ from .contracts import (
 )
 from .evidence import SourceBoundCycleEvidence
 from .source_proof import assess_scc_source_bytes
+from .evidence import _scenario_fingerprint
 
 
-MANIFEST_VERSION = "cycle-source-manifest/1"
+MANIFEST_VERSION = "cycle-source-manifest/2"
 _AUTHORITY = "PREPARED_ONLY_NOT_CANONICALLY_PUBLISHED"
 
 
@@ -43,6 +44,8 @@ class PreparedSCCSourceBinding:
     model_classification: str
     preparation_state: str
     reason: str | None
+    model_kind: str = "FLAT_MODULE"
+    model_evidence_sha256: str | None = None
 
 
 @dataclass(frozen=True)
@@ -106,6 +109,8 @@ def prepare_cycle_source_manifest(
                 model_classification="INDETERMINATE",
                 preparation_state="UNAVAILABLE",
                 reason=check.reason or "P1B_EVIDENCE_UNAVAILABLE",
+                model_kind=source_evidence.scenarios.components[position].model_kind,
+                model_evidence_sha256=None,
             ))
             continue
 
@@ -133,6 +138,8 @@ def prepare_cycle_source_manifest(
                 model_classification="INDETERMINATE",
                 preparation_state="UNAVAILABLE",
                 reason="SOURCE_MANIFEST_CONFLICT:" + conflict,
+                model_kind=source_evidence.scenarios.components[position].model_kind,
+                model_evidence_sha256=None,
             ))
             continue
 
@@ -145,6 +152,10 @@ def prepare_cycle_source_manifest(
             model_classification=check.model_classification,
             preparation_state="PREPARED_UNPUBLISHED",
             reason=None,
+            model_kind=source_evidence.scenarios.components[position].model_kind,
+            model_evidence_sha256=_scenario_fingerprint(
+                source_evidence.scenarios.components[position]
+            ),
         ))
 
     # A global manifest digest must not imply completeness
@@ -157,10 +168,13 @@ def prepare_cycle_source_manifest(
         manifest_hash: str | None = _digest((
             MANIFEST_VERSION,
             graph_hash,
-            tuple(
-                component.members
-                for component in prepared
-            ),
+            tuple((
+                component.members,
+                component.model_classification,
+                component.model_kind,
+                component.model_evidence_sha256,
+                component.source_signatures,
+            ) for component in prepared),
             ordered_sources,
         ))
     else:
diff --git a/contextor/core/cycle_semantics/model_identity.py b/contextor/core/cycle_semantics/model_identity.py
new file mode 100644
index 0000000..7c3cc7c
--- /dev/null
+++ b/contextor/core/cycle_semantics/model_identity.py
@@ -0,0 +1,25 @@
+"""Identity translation within an explicitly indexed regular-package model."""
+
+from __future__ import annotations
+
+
+def indexed_to_logical_module(module_id: str) -> str:
+    if module_id.endswith(".__init__"):
+        return module_id.removesuffix(".__init__")
+    return module_id
+
+
+def logical_to_indexed_module(
+    logical_name: str,
+    indexed_ids: frozenset[str],
+) -> str | None:
+    initializer = logical_name + ".__init__"
+    direct = logical_name in indexed_ids
+    package = initializer in indexed_ids
+    if direct and package:
+        return None
+    if direct:
+        return logical_name
+    if package:
+        return initializer
+    return None
diff --git a/contextor/core/cycle_semantics/model_source_closure.py b/contextor/core/cycle_semantics/model_source_closure.py
new file mode 100644
index 0000000..47ad7de
--- /dev/null
+++ b/contextor/core/cycle_semantics/model_source_closure.py
@@ -0,0 +1,77 @@
+"""Deterministic source closure for a cyclic SCC's restricted import model.
+
+This does not add edges to the canonical structural graph.
+"""
+
+from __future__ import annotations
+
+from collections.abc import Mapping
+from dataclasses import dataclass
+
+from .scc import analyze_import_cycle_topology
+
+
+MODEL_SOURCE_CLOSURE_VERSION = "cycle-model-source-closure/1"
+
+
+@dataclass(frozen=True)
+class CycleModelSourceClosure:
+    members: tuple[str, ...]
+    hard_reachable_modules: tuple[str, ...]
+    evidence_source_modules: tuple[str, ...]
+    implicit_initializer_modules: tuple[str, ...]
+
+
+def compute_cycle_model_source_closures(
+    hard_edges: Mapping[str, object],
+) -> tuple[CycleModelSourceClosure, ...]:
+    """Close each cyclic SCC over hard targets and indexed parent initializers."""
+    topology = analyze_import_cycle_topology(hard_edges)
+    adjacency = {
+        source: tuple(sorted(set(targets)))
+        for source, targets in hard_edges.items()
+    }
+    for targets in tuple(adjacency.values()):
+        for target in targets:
+            adjacency.setdefault(target, ())
+    indexed = frozenset(adjacency)
+
+    def initializers(module_id: str) -> tuple[str, ...]:
+        parts = module_id.split(".")
+        if parts[-1] == "__init__":
+            parts = parts[:-1]
+        return tuple(
+            ".".join(parts[:length]) + ".__init__"
+            for length in range(1, len(parts))
+            if ".".join(parts[:length]) + ".__init__" in indexed
+        )
+
+    rows: list[CycleModelSourceClosure] = []
+    for component in topology.cyclic_components:
+        hard = set(component.members)
+        pending = list(component.members)
+        while pending:
+            for target in adjacency[pending.pop()]:
+                if target not in hard:
+                    hard.add(target)
+                    pending.append(target)
+
+        evidence = set(component.members)
+        pending = list(component.members)
+        while pending:
+            module_id = pending.pop()
+            for target in (*adjacency[module_id], *initializers(module_id)):
+                if target not in evidence:
+                    evidence.add(target)
+                    pending.append(target)
+
+        rows.append(CycleModelSourceClosure(
+            members=component.members,
+            hard_reachable_modules=tuple(sorted(hard)),
+            evidence_source_modules=tuple(sorted(evidence)),
+            implicit_initializer_modules=tuple(sorted(
+                module_id for module_id in evidence - hard
+                if module_id.endswith(".__init__")
+            )),
+        ))
+    return tuple(rows)
diff --git a/contextor/core/cycle_semantics/original_worker_binding.py b/contextor/core/cycle_semantics/original_worker_binding.py
index d469b86..9bba63e 100644
--- a/contextor/core/cycle_semantics/original_worker_binding.py
+++ b/contextor/core/cycle_semantics/original_worker_binding.py
@@ -13,6 +13,7 @@ from dataclasses import dataclass
 from contextor.core.source import SourceSnapshot
 
 from .scc import analyze_import_cycle_topology
+from .model_source_closure import compute_cycle_model_source_closures
 
 
 _CAPTURE_STATUS = "ALL_SELECTED_CAPTURED_NON_ATOMIC"
@@ -30,7 +31,7 @@ class OriginalWorkerCycleClosureBinding:
     status: str
     reason: str | None
     cyclic_components: tuple[tuple[str, ...], ...]
-    reachable_modules: tuple[str, ...]
+    reachable_modules: tuple[str, ...]  # Evidence-source closure, including initializers.
     source_snapshots: dict[str, SourceSnapshot]
     ast_modes: tuple[tuple[str, str], ...]
     retained_raw_bytes: int
@@ -94,26 +95,11 @@ def assess_original_worker_cycle_closure(
     ):
         return unavailable("INDEX_CAPTURE_SHAPE_INVALID")
 
-    adjacency: dict[str, tuple[str, ...]] = {}
-    for module_id, targets in hard_edges.items():
-        adjacency[module_id] = tuple(sorted(set(targets)))
-    for targets in tuple(adjacency.values()):
-        for target in targets:
-            adjacency.setdefault(target, ())
-
     required: set[str] = set()
-    components = tuple(
-        component.members
-        for component in topology.cyclic_components
-    )
-    for members in components:
-        pending = list(members)
-        required.update(members)
-        while pending:
-            for target in adjacency[pending.pop()]:
-                if target not in required:
-                    required.add(target)
-                    pending.append(target)
+    closures = compute_cycle_model_source_closures(hard_edges)
+    components = tuple(closure.members for closure in closures)
+    for closure in closures:
+        required.update(closure.evidence_source_modules)
         if len(required) > _MAX_MODULES:
             return unavailable("CLOSURE_MODULE_LIMIT")
 
diff --git a/contextor/core/cycle_semantics/original_worker_reindex_planning.py b/contextor/core/cycle_semantics/original_worker_reindex_planning.py
index ecdb6e2..a99a484 100644
--- a/contextor/core/cycle_semantics/original_worker_reindex_planning.py
+++ b/contextor/core/cycle_semantics/original_worker_reindex_planning.py
@@ -14,6 +14,7 @@ from .contracts import fingerprint_hard_edges
 from .original_worker_binding import (
     assess_original_worker_cycle_closure,
 )
+from .model_source_closure import compute_cycle_model_source_closures
 from .scc import analyze_import_cycle_topology
 
 
@@ -96,25 +97,9 @@ def plan_original_worker_reindex(
     if not topology.cyclic_components:
         return unavailable("NO_CYCLIC_COMPONENTS")
 
-    adjacency = {
-        name: tuple(sorted(set(targets)))
-        for name, targets in hard_edges.items()
-    }
-    for targets in tuple(adjacency.values()):
-        for target in targets:
-            adjacency.setdefault(target, ())
-
     selected: set[str] = set()
-
-    for component in topology.cyclic_components:
-        pending = list(component.members)
-        selected.update(component.members)
-
-        while pending:
-            for target in adjacency[pending.pop()]:
-                if target not in selected:
-                    selected.add(target)
-                    pending.append(target)
+    for closure in compute_cycle_model_source_closures(hard_edges):
+        selected.update(closure.evidence_source_modules)
 
         if len(selected) > _MAX_SELECTED:
             return unavailable("CLOSURE_MODULE_LIMIT")
diff --git a/contextor/core/cycle_semantics/package_graph_consistency.py b/contextor/core/cycle_semantics/package_graph_consistency.py
new file mode 100644
index 0000000..69b67ad
--- /dev/null
+++ b/contextor/core/cycle_semantics/package_graph_consistency.py
@@ -0,0 +1,122 @@
+"""Conservative graph/source agreement for restricted regular-package imports."""
+
+from __future__ import annotations
+
+import ast
+from collections.abc import Mapping
+from dataclasses import dataclass
+
+from .model_identity import indexed_to_logical_module, logical_to_indexed_module
+
+
+@dataclass(frozen=True)
+class PackageGraphConsistency:
+    status: str
+    reason: str | None
+
+
+def assess_package_graph_consistency(
+    hard_edges: Mapping[str, object],
+    sources: Mapping[str, ast.Module],
+    evidence_source_modules: tuple[str, ...],
+) -> PackageGraphConsistency:
+    """Require exact indexed targets for every supported source import."""
+    def unknown(reason: str) -> PackageGraphConsistency:
+        return PackageGraphConsistency("INDETERMINATE", reason)
+
+    if not isinstance(hard_edges, Mapping) or not isinstance(sources, Mapping):
+        return unknown("GRAPH_SOURCE_IMPORT_MISMATCH")
+    indexed = frozenset(hard_edges)
+    if any(name not in indexed or not isinstance(sources.get(name), ast.Module)
+           for name in evidence_source_modules):
+        return unknown("MISSING_INDEXED_TARGET")
+
+    def target(name: str) -> str | None:
+        return logical_to_indexed_module(name, indexed)
+
+    def regular_parents(name: str) -> bool:
+        parts = name.split(".")
+        return all(
+            target(".".join(parts[:length]))
+            == ".".join(parts[:length]) + ".__init__"
+            and ".".join(parts[:length]) + ".__init__" in sources
+            for length in range(1, len(parts))
+        )
+
+    def relative_base(module_id: str, level: int, named: str | None) -> str | None:
+        logical = indexed_to_logical_module(module_id)
+        context = logical if module_id.endswith(".__init__") else logical.rpartition(".")[0]
+        parts = context.split(".") if context else []
+        if level < 1 or level > len(parts):
+            return None
+        prefix = ".".join(parts[:len(parts) - level + 1])
+        return prefix + ("." + named if named else "")
+
+    for module_id in evidence_source_modules:
+        expected: set[str] = set()
+        for node in ast.walk(sources[module_id]):
+            if isinstance(node, ast.Import):
+                for alias in node.names:
+                    if not all(part.isidentifier() for part in alias.name.split(".")):
+                        return unknown("UNSUPPORTED_IMPORT_FORM")
+                    resolved = target(alias.name)
+                    if resolved is None:
+                        return unknown("MISSING_INDEXED_TARGET")
+                    if resolved != alias.name and resolved != alias.name + ".__init__":
+                        return unknown("AMBIGUOUS_PACKAGE_TARGET")
+                    if "." in alias.name and not regular_parents(alias.name):
+                        return unknown("MISSING_REQUIRED_INITIALIZER")
+                    if resolved != module_id:
+                        expected.add(resolved)
+            elif isinstance(node, ast.ImportFrom):
+                if any(alias.name == "*" for alias in node.names):
+                    return unknown("UNSUPPORTED_IMPORT_FORM")
+                if node.level:
+                    base = relative_base(module_id, node.level, node.module)
+                    if base is None:
+                        return unknown("RELATIVE_IMPORT_OUT_OF_BOUNDS")
+                else:
+                    base = node.module
+                if not base or not all(part.isidentifier() for part in base.split(".")):
+                    return unknown("UNSUPPORTED_IMPORT_FORM")
+                resolved = target(base)
+                if resolved is None:
+                    return unknown("MISSING_INDEXED_TARGET")
+                if "." in base and not regular_parents(base):
+                    return unknown("MISSING_REQUIRED_INITIALIZER")
+                if resolved != module_id:
+                    expected.add(resolved)
+                if resolved.endswith(".__init__"):
+                    # The named-member form may be an initializer attribute or
+                    # a child. Only explicit relative sibling imports with a
+                    # provably unbound child are covered in this phase.
+                    if not (node.level and node.module is None):
+                        return unknown("AMBIGUOUS_PACKAGE_TARGET")
+                    initializer = sources.get(resolved)
+                    if initializer is None:
+                        return unknown("MISSING_REQUIRED_INITIALIZER")
+                    # Only an inert initializer proves that the imported
+                    # name cannot be a pre-existing package attribute.
+                    if any(
+                        not isinstance(statement, ast.Pass)
+                        and not (
+                            isinstance(statement, ast.Expr)
+                            and isinstance(statement.value, ast.Constant)
+                            and isinstance(statement.value.value, str)
+                        )
+                        for statement in initializer.body
+                    ):
+                        return unknown("AMBIGUOUS_PACKAGE_TARGET")
+                    for alias in node.names:
+                        if not alias.name.isidentifier():
+                            return unknown("AMBIGUOUS_PACKAGE_TARGET")
+                        child = target(base + "." + alias.name)
+                        if child is None:
+                            return unknown("MISSING_INDEXED_TARGET")
+                        if child != module_id:
+                            expected.add(child)
+
+        if expected != set(hard_edges[module_id]):
+            return unknown("GRAPH_SOURCE_IMPORT_MISMATCH")
+
+    return PackageGraphConsistency("CONSISTENT", None)
diff --git a/contextor/core/cycle_semantics/publication_binding.py b/contextor/core/cycle_semantics/publication_binding.py
index 935e4cb..39237e8 100644
--- a/contextor/core/cycle_semantics/publication_binding.py
+++ b/contextor/core/cycle_semantics/publication_binding.py
@@ -21,9 +21,12 @@ from .generation_manifest import (
     _digest,
 )
 from .scc import analyze_import_cycle_topology
+from .model_source_closure import compute_cycle_model_source_closures
 
 
-PUBLICATION_BINDING_VERSION = "cycle-prepared-co-publication/1"
+PUBLICATION_BINDING_VERSION = "cycle-prepared-co-publication/2"
+_LEGACY_MANIFEST_VERSION = "cycle-source-manifest/1"
+_LEGACY_BINDING_VERSION = "cycle-prepared-co-publication/1"
 PUBLICATION_AUTHORITY = (
     "COMMITTED_PREPARED_CLAIMS_NOT_SOURCE_CERTIFIED"
 )
@@ -48,12 +51,16 @@ class CanonicalCycleManifestReceipt:
 def _validated_claim_digest(
     state: Any,
     manifest: PreparedCycleSourceManifest,
+    *,
+    legacy: bool = False,
 ) -> str:
     """Validate declarations, not source-byte authenticity."""
     if type(manifest) is not PreparedCycleSourceManifest:
         raise ValueError("prepared manifest contract missing")
     if (
-        manifest.version != MANIFEST_VERSION
+        manifest.version != (
+            _LEGACY_MANIFEST_VERSION if legacy else MANIFEST_VERSION
+        )
         or manifest.authority
         != "PREPARED_ONLY_NOT_CANONICALLY_PUBLISHED"
         or not isinstance(manifest.source_manifest_sha256, str)
@@ -112,7 +119,8 @@ def _validated_claim_digest(
     accepted: dict[str, tuple[str, str]] = {}
     claims = []
 
-    for structural, prepared in zip(cyclic, manifest.components):
+    closures = compute_cycle_model_source_closures(hard_edges)
+    for position, (structural, prepared) in enumerate(zip(cyclic, manifest.components)):
         if (
             type(prepared) is not PreparedSCCSourceBinding
             or prepared.members != structural.members
@@ -121,19 +129,36 @@ def _validated_claim_digest(
             or prepared.reason is not None
             or prepared.model_classification not in _ALLOWED_MODELS
             or type(prepared.source_signatures) is not tuple
+            or (
+                legacy and (
+                    prepared.model_kind != "FLAT_MODULE"
+                    or prepared.model_evidence_sha256 is not None
+                )
+            )
+            or (
+                not legacy and (
+                    prepared.model_kind not in {"FLAT_MODULE", "REGULAR_PACKAGE"}
+                    or type(prepared.model_evidence_sha256) is not str
+                    or len(prepared.model_evidence_sha256) != 64
+                    or any(c not in "0123456789abcdef"
+                           for c in prepared.model_evidence_sha256)
+                )
+            )
         ):
             raise ValueError(
                 "prepared SCC claims are inconsistent"
             )
 
-        closure = set(structural.members)
-        pending = list(structural.members)
-
-        while pending:
-            for target in adjacency[pending.pop()]:
-                if target not in closure:
-                    closure.add(target)
-                    pending.append(target)
+        if legacy:
+            closure = set(structural.members)
+            pending = list(structural.members)
+            while pending:
+                for target in adjacency[pending.pop()]:
+                    if target not in closure:
+                        closure.add(target)
+                        pending.append(target)
+        else:
+            closure = set(closures[position].evidence_source_modules)
 
         rows = prepared.source_signatures
         if (
@@ -175,9 +200,10 @@ def _validated_claim_digest(
             accepted[name] = signature
 
         claims.append((
-            prepared.members,
-            prepared.model_classification,
-            rows,
+            (prepared.members, prepared.model_classification, rows)
+            if legacy else
+            (prepared.members, prepared.model_classification,
+             prepared.model_kind, prepared.model_evidence_sha256, rows)
         ))
 
     observed = dict(snapshot.observed_source_fingerprints)
@@ -204,9 +230,12 @@ def _validated_claim_digest(
         for name in sorted(accepted)
     )
     expected_manifest_hash = _digest((
-        MANIFEST_VERSION,
+        _LEGACY_MANIFEST_VERSION if legacy else MANIFEST_VERSION,
         graph_hash,
-        tuple(component.members for component in cyclic),
+        (
+            tuple(component.members for component in cyclic)
+            if legacy else tuple(claims)
+        ),
         ordered_sources,
     ))
     if manifest.source_manifest_sha256 != expected_manifest_hash:
@@ -217,7 +246,7 @@ def _validated_claim_digest(
     # Bind model CLAIMS independently of the source digest.
     # This does not authenticate model execution or source origin.
     return _digest((
-        PUBLICATION_BINDING_VERSION,
+        _LEGACY_BINDING_VERSION if legacy else PUBLICATION_BINDING_VERSION,
         graph_hash,
         expected_manifest_hash,
         tuple(claims),
@@ -286,14 +315,37 @@ def verify_co_published_cycle_manifest(
     if type(receipt) is not CanonicalCycleManifestReceipt:
         return False
 
+    if (
+        type(revision) is not int or revision < 1
+        or type(state_id) is not str or not state_id
+        or type(repo_id) is not str
+        or type(root_path) is not str
+        or getattr(state, "revision", None) != revision
+        or getattr(state, "state_id", None) != state_id
+    ):
+        return False
+
+    if receipt.version not in {
+        PUBLICATION_BINDING_VERSION, _LEGACY_BINDING_VERSION,
+    }:
+        return False
+    legacy = receipt.version == _LEGACY_BINDING_VERSION
+    if receipt.prepared_manifest.version != (
+        _LEGACY_MANIFEST_VERSION if legacy else MANIFEST_VERSION
+    ):
+        return False
     try:
-        expected = seal_prepared_cycle_manifest(
-            state,
-            receipt.prepared_manifest,
+        digest = _validated_claim_digest(
+            state, receipt.prepared_manifest, legacy=legacy,
+        )
+        expected = CanonicalCycleManifestReceipt(
+            prepared_manifest=receipt.prepared_manifest,
+            model_claims_sha256=digest,
             revision=revision,
             state_id=state_id,
             repo_id=repo_id,
             root_path=root_path,
+            version=receipt.version,
         )
     except (
         TypeError,
diff --git a/contextor/core/cycle_semantics/scenarios.py b/contextor/core/cycle_semantics/scenarios.py
index 25b839b..0959757 100644
--- a/contextor/core/cycle_semantics/scenarios.py
+++ b/contextor/core/cycle_semantics/scenarios.py
@@ -10,6 +10,10 @@ from collections.abc import Mapping
 from dataclasses import dataclass
 
 from .initialization_model import ImportOrderAssessment, evaluate_flat_import_order
+from .package_model import PackageImportAssessment, evaluate_package_import_order
+from .model_source_closure import compute_cycle_model_source_closures
+from .model_identity import indexed_to_logical_module, logical_to_indexed_module
+from .package_graph_consistency import assess_package_graph_consistency
 from .scc import CyclicImportComponent, ImportCycleTopology, analyze_import_cycle_topology
 
 MAX_COMPONENT_ENTRIES = 64
@@ -24,8 +28,9 @@ class CycleComponentScenarios:
     classification: str
     coverage: str
     reason: str | None
-    entry_assessments: tuple[ImportOrderAssessment, ...]
+    entry_assessments: tuple[ImportOrderAssessment | PackageImportAssessment, ...]
     evidence_scope: str = "CLOSED_FLAT_MODULE_FRESH_ENTRY_MODEL"
+    model_kind: str = "FLAT_MODULE"
 
 
 @dataclass(frozen=True)
@@ -72,7 +77,8 @@ def _component_result(
     *,
     coverage: str,
     reason: str | None = None,
-    assessments: tuple[ImportOrderAssessment, ...] = (),
+    assessments: tuple[ImportOrderAssessment | PackageImportAssessment, ...] = (),
+    model_kind: str = "FLAT_MODULE",
 ) -> CycleComponentScenarios:
     return CycleComponentScenarios(
         members=component.members,
@@ -81,6 +87,12 @@ def _component_result(
         coverage=coverage,
         reason=reason,
         entry_assessments=assessments,
+        evidence_scope=(
+            "CLOSED_REGULAR_PACKAGE_FRESH_ENTRY_MODEL"
+            if model_kind == "REGULAR_PACKAGE"
+            else "CLOSED_FLAT_MODULE_FRESH_ENTRY_MODEL"
+        ),
+        model_kind=model_kind,
     )
 
 
@@ -103,7 +115,8 @@ def analyze_cycle_scenarios(
             adjacency.setdefault(target, frozenset())
 
     output: list[CycleComponentScenarios] = []
-    for component in topology.cyclic_components:
+    closures = compute_cycle_model_source_closures(hard_edges)
+    for component, source_closure in zip(topology.cyclic_components, closures):
         if len(component.members) > MAX_COMPONENT_ENTRIES:
             output.append(_component_result(
                 component, "INDETERMINATE", coverage="NONE",
@@ -111,7 +124,7 @@ def analyze_cycle_scenarios(
             ))
             continue
 
-        reachable = _closure(component.members, adjacency)
+        reachable = set(source_closure.evidence_source_modules)
         if any(name not in modules or not isinstance(modules[name], ast.Module)
                for name in reachable):
             output.append(_component_result(
@@ -145,28 +158,71 @@ def analyze_cycle_scenarios(
 
         # The graph and AST must describe the exact same import targets.
         # No name-based exceptions and no guessed package resolution.
-        if any(
+        flat_applicable = all(
+            name.isidentifier() and not name.startswith("__")
+            for name in reachable
+        ) and not any(
             _declared_import_targets(modules[name]) != set(adjacency[name])
             for name in reachable
-        ):
-            output.append(_component_result(
-                component, "INDETERMINATE", coverage="NONE",
-                reason="GRAPH_SOURCE_IMPORT_MISMATCH",
-            ))
-            continue
+        )
 
         sources = {name: modules[name] for name in sorted(reachable)}
-        assessments = tuple(
-            evaluate_flat_import_order(sources, entry)
-            for entry in component.members
-        )
+        model_kind = "FLAT_MODULE"
+        if flat_applicable:
+            assessments = tuple(
+                evaluate_flat_import_order(sources, entry)
+                for entry in component.members
+            )
+        else:
+            if not any("." in name for name in reachable):
+                output.append(_component_result(
+                    component, "INDETERMINATE", coverage="NONE",
+                    reason="GRAPH_SOURCE_IMPORT_MISMATCH",
+                ))
+                continue
+            consistency = assess_package_graph_consistency(
+                hard_edges, sources, source_closure.evidence_source_modules,
+            )
+            if consistency.status != "CONSISTENT":
+                output.append(_component_result(
+                    component, "INDETERMINATE", coverage="NONE",
+                    reason=consistency.reason,
+                    model_kind="REGULAR_PACKAGE",
+                ))
+                continue
+            indexed = frozenset(hard_edges)
+            if any(
+                logical_to_indexed_module(indexed_to_logical_module(member), indexed)
+                != member
+                for member in component.members
+            ):
+                output.append(_component_result(
+                    component, "INDETERMINATE", coverage="NONE",
+                    reason="AMBIGUOUS_PACKAGE_TARGET",
+                    model_kind="REGULAR_PACKAGE",
+                ))
+                continue
+            model_kind = "REGULAR_PACKAGE"
+            assessments = tuple(
+                evaluate_package_import_order(
+                    sources, indexed_to_logical_module(entry),
+                )
+                for entry in component.members
+            )
         member_set = set(component.members)
         internal_hazard = any(
             result.outcome == "EARLY_BINDING_HAZARD"
             and result.events
             and result.events[-1].operation == "EARLY_BINDING_HAZARD"
-            and result.events[-1].module in member_set
-            and result.events[-1].target in member_set
+            and (
+                logical_to_indexed_module(result.events[-1].module, frozenset(hard_edges))
+                if model_kind == "REGULAR_PACKAGE" else result.events[-1].module
+            ) in member_set
+            and (
+                logical_to_indexed_module(result.events[-1].target, frozenset(hard_edges))
+                if model_kind == "REGULAR_PACKAGE" else result.events[-1].target
+            ) in member_set
+            and result.events[-1].target == result.target_module
             for result in assessments
         )
         if internal_hazard:
@@ -189,6 +245,7 @@ def analyze_cycle_scenarios(
         output.append(_component_result(
             component, classification, coverage=coverage,
             reason=reason, assessments=assessments,
+            model_kind=model_kind,
         ))
 
     return CycleScenarioReport(topology, tuple(output))
diff --git a/contextor/core/cycle_semantics/source_proof.py b/contextor/core/cycle_semantics/source_proof.py
index 6c27363..36e7d1e 100644
--- a/contextor/core/cycle_semantics/source_proof.py
+++ b/contextor/core/cycle_semantics/source_proof.py
@@ -13,6 +13,7 @@ from collections.abc import Mapping
 from dataclasses import dataclass
 
 from contextor.core.source import (
+    ParsedSourceInput,
     SourceError,
     SourceSnapshot,
     parse_source_snapshot,
@@ -22,6 +23,8 @@ from .contracts import CycleSemanticsSnapshot
 from .evidence import (
     SourceBoundCycleEvidence,
     assess_index_bound_scc_models,
+    build_source_bound_cycle_evidence,
+    _scenario_fingerprint,
 )
 
 
@@ -82,7 +85,7 @@ def assess_scc_source_bytes(
 
     # Reuse parsed hashes for closure members shared by SCCs.
     # Cache is execution-local and does not certify generation.
-    cache: dict[str, tuple[str, str | None]] = {}
+    cache: dict[str, tuple[str, str | None, ParsedSourceInput | None]] = {}
 
     for position, model in enumerate(model_results):
         members = model.members
@@ -182,7 +185,7 @@ def assess_scc_source_bytes(
                         module,
                     )
                 except SourceError:
-                    cache[module] = (actual, None)
+                    cache[module] = (actual, None, None)
                 else:
                     ast_hash = hashlib.sha256(
                         ast.dump(
@@ -191,7 +194,7 @@ def assess_scc_source_bytes(
                         ).encode("utf-8")
                     ).hexdigest()
 
-                    cache[module] = (actual, ast_hash)
+                    cache[module] = (actual, ast_hash, parsed)
 
             observed_ast = cache[module][1]
 
@@ -207,6 +210,37 @@ def assess_scc_source_bytes(
                 )
                 break
 
+        if outcome is None:
+            parsed_sources = {
+                module: cache[module][2]
+                for module in closure
+            }
+            try:
+                replay = build_source_bound_cycle_evidence(
+                    hard_edges, parsed_sources,
+                )
+                replay_scenario = replay.scenarios.components[position]
+                supplied_scenario = source_evidence.scenarios.components[position]
+                replay_component = replay.components[position]
+                supplied_component = source_evidence.components[position]
+            except (TypeError, ValueError, KeyError, IndexError, RecursionError, OverflowError):
+                outcome = unavailable("MODEL_REPLAY_UNAVAILABLE")
+            else:
+                if replay_scenario.reason in {
+                    "ENTRY_BUDGET_EXCEEDED",
+                    "STATEMENT_BUDGET_EXCEEDED",
+                    "AST_NODE_BUDGET_EXCEEDED",
+                }:
+                    outcome = unavailable("MODEL_REPLAY_UNAVAILABLE")
+                elif (
+                    replay_scenario != supplied_scenario
+                    or _scenario_fingerprint(replay_scenario)
+                    != _scenario_fingerprint(supplied_scenario)
+                    or replay_component.evidence_token
+                    != supplied_component.evidence_token
+                ):
+                    outcome = mismatch("MODEL_REPLAY_MISMATCH")
+
         if outcome is not None:
             assessments.append(outcome)
         else:
diff --git a/tests/cycle_semantics_lab/__init__.py b/tests/cycle_semantics_lab/__init__.py
new file mode 100644
index 0000000..7f24f39
--- /dev/null
+++ b/tests/cycle_semantics_lab/__init__.py
@@ -0,0 +1,59 @@
+"""Small isolated source fixtures for cycle-semantics tests."""
+
+from __future__ import annotations
+
+import subprocess
+import sys
+from collections.abc import Mapping
+from pathlib import Path, PurePosixPath
+
+
+def write_synthetic_repository(
+    root: Path,
+    sources: Mapping[str, str],
+) -> Path:
+    """Write exact UTF-8 Python fixture sources below one test root."""
+    root = Path(root).resolve()
+    root.mkdir(parents=True, exist_ok=True)
+    planned: dict[Path, str] = {}
+    for name, source in sources.items():
+        if not isinstance(name, str) or "\\" in name or not isinstance(source, str):
+            raise ValueError("invalid synthetic source")
+        relative = PurePosixPath(name)
+        if (
+            relative.is_absolute()
+            or not relative.parts
+            or any(part in {"", ".", ".."} for part in name.split("/"))
+            or relative.suffix != ".py"
+        ):
+            raise ValueError("invalid synthetic path")
+        target = root.joinpath(*relative.parts).resolve()
+        if target == root or root not in target.parents or target in planned:
+            raise ValueError("duplicate or escaping synthetic path")
+        planned[target] = source
+    for target, source in planned.items():
+        target.parent.mkdir(parents=True, exist_ok=True)
+        target.write_bytes(source.encode("utf-8"))
+    return root
+
+
+def run_synthetic_import(
+    root: Path,
+    module: str,
+    *,
+    timeout: float = 8,
+) -> subprocess.CompletedProcess[str]:
+    """Run only an authored temporary fixture in a fresh isolated CPython."""
+    if not isinstance(module, str) or not all(
+        part.isidentifier() for part in module.split(".")
+    ):
+        raise ValueError("invalid synthetic entry module")
+    return subprocess.run(
+        [
+            sys.executable, "-I", "-B", "-c",
+            "import importlib,sys;sys.path.insert(0,sys.argv[1]);"
+            "importlib.import_module(sys.argv[2])",
+            str(Path(root).resolve()), module,
+        ],
+        capture_output=True, text=True, timeout=timeout, check=False,
+    )
diff --git a/tests/test_cycle_semantics_evidence.py b/tests/test_cycle_semantics_evidence.py
index 6389e6a..5fbf4f9 100644
--- a/tests/test_cycle_semantics_evidence.py
+++ b/tests/test_cycle_semantics_evidence.py
@@ -14,6 +14,7 @@ from contextor.core.source import (
 from contextor.core.cycle_semantics.evidence import (
     EVIDENCE_SEMANTIC_VERSION,
     _digest,
+    _component_token,
     SCCModelEvidenceAssessment,
     SCCGenerationModelAssessment,
     assess_index_bound_scc_models as assess,
@@ -322,7 +323,7 @@ def test_p0_t11_unknown_entry_in_scc():
     source = replace(evidence, scenarios=report)
     result = assess(PAIR, index, snapshot, source)
     assert result[0].model_classification == "INDETERMINATE"
-    assert result[0].evidence_state == "INCOMPLETE_EVIDENCE"
+    assert result[0].evidence_state == "EVIDENCE_MISMATCH"
 
 
 def test_p0_t12_independent_sccs_do_not_share_pass():
@@ -446,8 +447,8 @@ def test_p0_t18_entry_model_scope_must_match(sources):
 
     result = assess(PAIR, index, snapshot, changed_evidence)
     assert result[0].model_classification == "INDETERMINATE"
-    assert result[0].evidence_state == "INCOMPLETE_EVIDENCE"
-    assert result[0].reason == "INCOMPLETE_MEMBER_ENTRY_ASSESSMENTS"
+    assert result[0].evidence_state == "EVIDENCE_MISMATCH"
+    assert result[0].reason == "COMPONENT_EVIDENCE_TOKEN_MISMATCH"
 
 
 def _p1_case(sources=PASS):
@@ -708,12 +709,12 @@ def test_p1b_t04_forged_ast_signature_and_token():
     altered = replace(
         component,
         source_signatures=forged,
-        evidence_token=_digest((
-            EVIDENCE_SEMANTIC_VERSION,
+        evidence_token=_component_token(
             component.members,
             subgraph,
             forged,
-        )),
+            evidence.scenarios.components[0],
+        ),
     )
     spoofed = replace(
         evidence, components=(altered,),
diff --git a/tests/test_original_worker_full_preparation_optin.py b/tests/test_original_worker_full_preparation_optin.py
index 66f6ed2..98ed54f 100644
--- a/tests/test_original_worker_full_preparation_optin.py
+++ b/tests/test_original_worker_full_preparation_optin.py
@@ -43,6 +43,7 @@ def _package_repo(tmp_path):
     (pkg / "__init__.py").write_bytes(b"")
     (pkg / "a.py").write_bytes(
         b"import pkg.b\n"
+        b"@unknown_decorator\n"
         b"def fa():\n"
         b"    return 1\n"
     )
diff --git a/tests/test_original_worker_real_pipeline_preparation.py b/tests/test_original_worker_real_pipeline_preparation.py
index 7e8f0b2..0569ddd 100644
--- a/tests/test_original_worker_real_pipeline_preparation.py
+++ b/tests/test_original_worker_real_pipeline_preparation.py
@@ -250,7 +250,7 @@ def test_p1d2d_t07_real_process_pool_component_chain(
         terminate_active_process_pools(timeout=1.0)
 
 
-def test_p1d2d_t08_dotted_imports_remain_fail_closed(
+def test_p1d2d_t08_unsupported_dotted_package_remains_fail_closed(
     tmp_path, isolated_dirs,
 ):
     root = tmp_path / "package_repo"
@@ -260,6 +260,9 @@ def test_p1d2d_t08_dotted_imports_remain_fail_closed(
     (package / "__init__.py").write_bytes(b"")
     (package / "a.py").write_bytes(
         b"import pkg.b\n"
+        b"@unknown_decorator\n"
+        b"def f():\n"
+        b"    pass\n"
     )
     (package / "b.py").write_bytes(
         b"import pkg.a\n"
diff --git a/tests/test_p1d3_package_cycle_integration.py b/tests/test_p1d3_package_cycle_integration.py
new file mode 100644
index 0000000..0e65109
--- /dev/null
+++ b/tests/test_p1d3_package_cycle_integration.py
@@ -0,0 +1,432 @@
+"""P1D3-B/C package SCC evidence through real isolated index and store paths."""
+
+from __future__ import annotations
+
+import copy
+from dataclasses import replace
+
+import pytest
+
+from contextor.core.api.facade import ContextorFacade
+from contextor.core.cycle_semantics.evidence import (
+    _component_token,
+    _digest,
+    assess_index_bound_scc_models,
+    build_source_bound_cycle_evidence,
+)
+from contextor.core.cycle_semantics.generation_manifest import MANIFEST_VERSION
+from contextor.core.cycle_semantics.initialization_model import ImportOrderAssessment
+from contextor.core.cycle_semantics.materialization import materialize_cycle_semantics
+from contextor.core.cycle_semantics.model_identity import (
+    indexed_to_logical_module,
+    logical_to_indexed_module,
+)
+from contextor.core.cycle_semantics.model_source_closure import compute_cycle_model_source_closures
+from contextor.core.cycle_semantics.original_worker_preparation import prepare_original_worker_cycle_manifest
+from contextor.core.cycle_semantics.original_worker_reindex_planning import plan_original_worker_reindex
+from contextor.core.cycle_semantics.publication_binding import (
+    PUBLICATION_BINDING_VERSION,
+    seal_prepared_cycle_manifest,
+    verify_co_published_cycle_manifest,
+)
+from contextor.core.cycle_semantics.scenarios import analyze_cycle_scenarios
+from contextor.core.cycle_semantics.source_proof import assess_scc_source_bytes
+from contextor.core.graph.graph import build_graph
+from contextor.core.source import parse_source_snapshot
+from contextor.core.symbol_engine.indexer import index_repository
+from tests.cycle_semantics_lab import run_synthetic_import, write_synthetic_repository
+from tests.test_original_worker_full_receipt_optin import _persisted
+from tests.test_original_worker_official_full_live_publication import _official_live
+
+
+F1 = {
+    "pkg/__init__.py": "pass\n",
+    "pkg/a.py": "import pkg.b\ndef fa():\n    return 1\n",
+    "pkg/b.py": "import pkg.a\ndef fb():\n    return 2\n",
+}
+F2 = {
+    "pkg/__init__.py": "pass\n",
+    "pkg/a.py": "from . import b\nvalue = 1\n",
+    "pkg/b.py": "from . import a\nvalue = 2\n",
+}
+F3 = {
+    "pkg/__init__.py": "pass\n",
+    "pkg/a.py": "import pkg.b\nvalue = 1\n",
+    "pkg/b.py": "from pkg.a import value\n",
+}
+F4 = {
+    **F3,
+    "pkg/a.py": "value = 1\nimport pkg.b\n",
+}
+
+
+@pytest.fixture(autouse=True)
+def _inline(monkeypatch):
+    monkeypatch.setenv("CONTEXTOR_DISABLE_PROCESS_POOL", "1")
+
+
+def _indexed(root):
+    index = index_repository(str(root))
+    graph = build_graph(index.modules)
+    return index, graph
+
+
+def _captured(root, index, graph):
+    plan = plan_original_worker_reindex(index, graph.hard_edges)
+    assert plan.status == "READY_FOR_REINDEX_NON_ATOMIC"
+    captured = index_repository(str(root), source_capture_module_ids=plan.selected_module_ids)
+    return plan, captured
+
+
+def _snapshot(root, index, graph):
+    return materialize_cycle_semantics(
+        root, graph.hard_edges,
+        {name: module.path for name, module in index.modules.items()},
+        index.source_fingerprints_by_module,
+    )
+
+
+@pytest.mark.parametrize("fixture", [F1, F2])
+def test_package_closure_and_prepared_v2(tmp_path, isolated_dirs, fixture):
+    root = write_synthetic_repository(tmp_path / "repo", fixture)
+    index, graph = _indexed(root)
+    closure = compute_cycle_model_source_closures(graph.hard_edges)
+    assert len(closure) == 1
+    assert closure[0].members == ("pkg.a", "pkg.b")
+    assert closure[0].evidence_source_modules == (
+        "pkg.__init__", "pkg.a", "pkg.b",
+    )
+    if fixture is F1:
+        assert closure[0].implicit_initializer_modules == ("pkg.__init__",)
+    plan, captured = _captured(root, index, graph)
+    assert plan.selected_module_ids == frozenset(closure[0].evidence_source_modules)
+    snapshot = _snapshot(root, index, graph)
+    prepared = prepare_original_worker_cycle_manifest(captured, graph.hard_edges, snapshot)
+    assert prepared.status == "PREPARED_UNPUBLISHED_NON_ATOMIC"
+    assert prepared.source_modules == closure[0].evidence_source_modules
+    manifest = prepared.manifest
+    assert manifest.version == MANIFEST_VERSION == "cycle-source-manifest/2"
+    assert manifest.source_manifest_sha256 is not None
+    component = manifest.components[0]
+    assert component.model_kind == "REGULAR_PACKAGE"
+    assert component.model_classification == "MODEL_ALL_FRESH_MEMBER_ENTRIES_PASS"
+    assert len(component.model_evidence_sha256) == 64
+    assert tuple(row[0] for row in component.source_signatures) == closure[0].evidence_source_modules
+    for entry in ("pkg.a", "pkg.b"):
+        assert run_synthetic_import(root, entry).returncode == 0
+
+
+def test_identity_mapping_and_ambiguous_layout():
+    assert indexed_to_logical_module("pkg.sub.__init__") == "pkg.sub"
+    assert indexed_to_logical_module("pkg.a") == "pkg.a"
+    assert logical_to_indexed_module("pkg", frozenset({"pkg.__init__"})) == "pkg.__init__"
+    assert logical_to_indexed_module("pkg", frozenset({"pkg", "pkg.__init__"})) is None
+    assert logical_to_indexed_module("external", frozenset({"pkg.a"})) is None
+
+
+def test_initializer_hard_edges_reach_fixed_point():
+    edges = {
+        "pkg.a": {"pkg.b"},
+        "pkg.b": {"pkg.a"},
+        "pkg.__init__": {"pkg.sub.child"},
+        "pkg.sub.__init__": set(),
+        "pkg.sub.child": set(),
+    }
+    closure = compute_cycle_model_source_closures(edges)[0]
+    assert closure.hard_reachable_modules == ("pkg.a", "pkg.b")
+    assert closure.evidence_source_modules == (
+        "pkg.__init__", "pkg.a", "pkg.b", "pkg.sub.__init__", "pkg.sub.child",
+    )
+    assert closure.implicit_initializer_modules == (
+        "pkg.__init__", "pkg.sub.__init__",
+    )
+
+
+def test_early_hazard_and_safe_reordering(tmp_path, isolated_dirs):
+    outcomes = []
+    for name, fixture in (("hazard", F3), ("safe", F4)):
+        root = write_synthetic_repository(tmp_path / name, fixture)
+        index, graph = _indexed(root)
+        _, captured = _captured(root, index, graph)
+        parsed = {
+            module: parse_source_snapshot(source, module)
+            for module, source in captured.original_worker_source_snapshots.items()
+        }
+        evidence = build_source_bound_cycle_evidence(graph.hard_edges, parsed)
+        scenario = evidence.scenarios.components[0]
+        outcomes.append((graph.hard_edges, scenario.classification, evidence.components[0].evidence_token))
+        prepared = prepare_original_worker_cycle_manifest(
+            captured, graph.hard_edges, _snapshot(root, index, graph),
+        )
+        assert prepared.status == "PREPARED_UNPUBLISHED_NON_ATOMIC"
+        actual = run_synthetic_import(root, "pkg.a")
+        if name == "hazard":
+            assert scenario.classification == "MODEL_INTERNAL_EARLY_BINDING_HAZARD"
+            assert actual.returncode != 0
+            assert "ImportError" in actual.stderr
+            assert "partially initialized module" in actual.stderr
+        else:
+            assert scenario.classification == "MODEL_ALL_FRESH_MEMBER_ENTRIES_PASS"
+            assert actual.returncode == 0
+    assert outcomes[0][0] == outcomes[1][0]
+    assert outcomes[0][2] != outcomes[1][2]
+
+
+def test_unsupported_namespace_and_contradictory_graph(tmp_path, isolated_dirs):
+    decorated = dict(F1)
+    decorated["pkg/a.py"] = "import pkg.b\n@unknown_decorator\ndef fa():\n    return 1\n"
+    for name, fixture in (("decorated", decorated), ("namespace", {
+        "pkg/a.py": F1["pkg/a.py"], "pkg/b.py": F1["pkg/b.py"],
+    })):
+        root = write_synthetic_repository(tmp_path / name, fixture)
+        index, graph = _indexed(root)
+        _, captured = _captured(root, index, graph)
+        result = prepare_original_worker_cycle_manifest(
+            captured, graph.hard_edges, _snapshot(root, index, graph),
+        )
+        assert result.status == "UNAVAILABLE"
+        assert result.manifest is None
+
+    root = write_synthetic_repository(tmp_path / "contradictory", F1)
+    index, graph = _indexed(root)
+    broken = {name: set(targets) for name, targets in graph.hard_edges.items()}
+    broken["pkg.a"].add("pkg.__init__")
+    captured = index_repository(
+        str(root), source_capture_module_ids=frozenset(index.modules),
+    )
+    trees = {
+        name: parse_source_snapshot(snapshot, name).tree
+        for name, snapshot in captured.original_worker_source_snapshots.items()
+    }
+    report = analyze_cycle_scenarios(broken, trees)
+    assert len(report.components) == 1
+    assert report.components[0].classification == "INDETERMINATE"
+    assert report.components[0].reason == "GRAPH_SOURCE_IMPORT_MISMATCH"
+
+
+@pytest.mark.parametrize("fixture", [F1, F3])
+def test_p1b_replay_rejects_forged_event(tmp_path, isolated_dirs, fixture):
+    root = write_synthetic_repository(tmp_path / "repo", fixture)
+    index, graph = _indexed(root)
+    _, captured = _captured(root, index, graph)
+    sources = captured.original_worker_source_snapshots
+    parsed = {name: parse_source_snapshot(snapshot, name) for name, snapshot in sources.items()}
+    evidence = build_source_bound_cycle_evidence(graph.hard_edges, parsed)
+    scenario = evidence.scenarios.components[0]
+    assessment = scenario.entry_assessments[0]
+    assert assessment.outcome in {"MODEL_PASS", "EARLY_BINDING_HAZARD"}
+    forged_events = (replace(assessment.events[0], operation="FORGED"), *assessment.events[1:])
+    forged_scenario = replace(scenario, entry_assessments=(
+        replace(assessment, events=forged_events), *scenario.entry_assessments[1:],
+    ))
+    graph_items = tuple(
+        (name, tuple(sorted(graph.hard_edges[name])))
+        for name in evidence.components[0].reachable_modules
+    )
+    forged_component = replace(
+        evidence.components[0],
+        evidence_token=_component_token(
+            scenario.members, graph_items,
+            evidence.components[0].source_signatures, forged_scenario,
+        ),
+    )
+    forged = replace(
+        evidence,
+        components=(forged_component,),
+        scenarios=replace(evidence.scenarios, components=(forged_scenario,)),
+    )
+    snapshot = _snapshot(root, index, graph)
+    p0 = assess_index_bound_scc_models(
+        graph.hard_edges, captured.source_fingerprints_by_module, snapshot, forged,
+    )
+    assert p0[0].evidence_state == "DECLARED_INPUTS_CONSISTENT"
+    p1b = assess_scc_source_bytes(
+        graph.hard_edges, captured.source_fingerprints_by_module,
+        snapshot, forged, sources,
+    )
+    assert p1b[0].reason == "MODEL_REPLAY_MISMATCH"
+
+
+def test_p0_rejects_package_assessment_disguised_as_flat(tmp_path, isolated_dirs):
+    root = write_synthetic_repository(tmp_path / "repo", F1)
+    index, graph = _indexed(root)
+    _, captured = _captured(root, index, graph)
+    parsed = {
+        name: parse_source_snapshot(snapshot, name)
+        for name, snapshot in captured.original_worker_source_snapshots.items()
+    }
+    evidence = build_source_bound_cycle_evidence(graph.hard_edges, parsed)
+    scenario = evidence.scenarios.components[0]
+    fake = ImportOrderAssessment("pkg.a", "MODEL_PASS", None, None, ())
+    changed = replace(scenario, entry_assessments=(fake, scenario.entry_assessments[1]))
+    component = evidence.components[0]
+    subgraph = tuple(
+        (name, tuple(sorted(graph.hard_edges[name])))
+        for name in component.reachable_modules
+    )
+    altered = replace(
+        evidence,
+        scenarios=replace(evidence.scenarios, components=(changed,)),
+        components=(replace(component, evidence_token=_component_token(
+            component.members, subgraph, component.source_signatures, changed,
+        )),),
+    )
+    result = assess_index_bound_scc_models(
+        graph.hard_edges, captured.source_fingerprints_by_module,
+        _snapshot(root, index, graph), altered,
+    )
+    assert result[0].evidence_state == "INCOMPLETE_EVIDENCE"
+    assert result[0].reason == "INCOMPLETE_MEMBER_ENTRY_ASSESSMENTS"
+
+
+def test_seventeen_selected_modules_fail_before_capture(tmp_path, isolated_dirs):
+    sources = {"a.py": "import b\n" + "".join(
+        f"import m{i:02d}\n" for i in range(15)
+    ), "b.py": "import a\n"}
+    sources.update({f"m{i:02d}.py": "pass\n" for i in range(15)})
+    root = write_synthetic_repository(tmp_path / "repo", sources)
+    index, graph = _indexed(root)
+    plan = plan_original_worker_reindex(index, graph.hard_edges)
+    assert plan.status == "UNAVAILABLE"
+    assert plan.reason == "CLOSURE_MODULE_LIMIT"
+    assert not plan.selected_module_ids
+
+
+def test_flat_and_package_components_remain_independent(tmp_path, isolated_dirs):
+    root = write_synthetic_repository(tmp_path / "repo", {
+        **F1,
+        "flat_a.py": "import flat_b\nvalue=1\n",
+        "flat_b.py": "import flat_a\nvalue=2\n",
+    })
+    index, graph = _indexed(root)
+    plan, captured = _captured(root, index, graph)
+    assert plan.selected_module_ids == frozenset({
+        "flat_a", "flat_b", "pkg.__init__", "pkg.a", "pkg.b",
+    })
+    parsed = {
+        name: parse_source_snapshot(snapshot, name)
+        for name, snapshot in captured.original_worker_source_snapshots.items()
+    }
+    evidence = build_source_bound_cycle_evidence(graph.hard_edges, parsed)
+    assert tuple(c.model_kind for c in evidence.scenarios.components) == (
+        "FLAT_MODULE", "REGULAR_PACKAGE",
+    )
+    assert all(
+        c.classification == "MODEL_ALL_FRESH_MEMBER_ENTRIES_PASS"
+        for c in evidence.scenarios.components
+    )
+    prepared = prepare_original_worker_cycle_manifest(
+        captured, graph.hard_edges, _snapshot(root, index, graph),
+    )
+    assert prepared.status == "PREPARED_UNPUBLISHED_NON_ATOMIC"
+    assert tuple(c.model_kind for c in prepared.manifest.components) == (
+        "FLAT_MODULE", "REGULAR_PACKAGE",
+    )
+
+
+def test_legacy_v1_receipt_read_only(tmp_path, isolated_dirs):
+    sources = {"a.py": "import b\nvalue=1\n", "b.py": "import a\nvalue=2\n"}
+    root = write_synthetic_repository(tmp_path / "repo", sources)
+    _, result = ContextorFacade.analyze_project(
+        str(root), cycle_source_preparation_preview=True,
+        cycle_source_publication_opt_in=True,
+    )
+    assert result is not None
+    state, metadata = _persisted(root)
+    current = state.cycle_source_publication
+    assert current.version == PUBLICATION_BINDING_VERSION
+    manifest = current.prepared_manifest
+    old_components = tuple(replace(c, model_evidence_sha256=None) for c in manifest.components)
+    ordered_sources = tuple(sorted({row for c in old_components for row in c.source_signatures}))
+    old_manifest_hash = _digest((
+        "cycle-source-manifest/1", manifest.graph_sha256,
+        tuple(c.members for c in old_components), ordered_sources,
+    ))
+    old_manifest = replace(
+        manifest, components=old_components,
+        version="cycle-source-manifest/1",
+        source_manifest_sha256=old_manifest_hash,
+    )
+    old_claims = _digest((
+        "cycle-prepared-co-publication/1", manifest.graph_sha256,
+        old_manifest_hash,
+        tuple((c.members, c.model_classification, c.source_signatures)
+              for c in old_components),
+    ))
+    old_receipt = replace(
+        current, prepared_manifest=old_manifest,
+        model_claims_sha256=old_claims,
+        version="cycle-prepared-co-publication/1",
+    )
+    legacy_state = copy.copy(state)
+    legacy_state.cycle_source_publication = old_receipt
+    identity = dict(
+        revision=metadata.revision, state_id=metadata.state_id,
+        repo_id=metadata.repo_id, root_path=metadata.root_path,
+    )
+    assert verify_co_published_cycle_manifest(legacy_state, **identity)
+    legacy_state.cycle_source_publication = replace(old_receipt, version=PUBLICATION_BINDING_VERSION)
+    assert not verify_co_published_cycle_manifest(legacy_state, **identity)
+    legacy_state.cycle_source_publication = replace(old_receipt, prepared_manifest=manifest)
+    assert not verify_co_published_cycle_manifest(legacy_state, **identity)
+    with pytest.raises(ValueError):
+        seal_prepared_cycle_manifest(state, old_manifest, **identity)
+
+
+def test_fixture_writer_rejects_escaping_paths(tmp_path):
+    root = tmp_path / "repo"
+    for name in ("../out.py", "/absolute.py", "a.txt", "a//b.py", "a/./b.py"):
+        with pytest.raises(ValueError):
+            write_synthetic_repository(root, {name: "pass\n"})
+
+
+@pytest.mark.live
+def test_official_isolated_package_publication(tmp_path, isolated_dirs, monkeypatch):
+    root = write_synthetic_repository(tmp_path / "repo", F1)
+    with _official_live(root, monkeypatch) as (client, server, identity, calls):
+        _, result = ContextorFacade.analyze_project(
+            str(root), cycle_source_preparation_preview=True,
+            cycle_source_publication_opt_in=True,
+        )
+        assert result is not None
+        assert result.cycle_source_preparation_preview.status == (
+            "PREPARED_UNPUBLISHED_NON_ATOMIC"
+        )
+        state, metadata = _persisted(root)
+        receipt = state.cycle_source_publication
+        assert receipt is not None
+        assert receipt.version == PUBLICATION_BINDING_VERSION
+        assert receipt.prepared_manifest.version == MANIFEST_VERSION
+        assert receipt.prepared_manifest.components[0].model_kind == "REGULAR_PACKAGE"
+        assert metadata.repo_id == identity.repo_id
+        assert calls == [root.resolve()]
+        assert result.live_publish_status == "success"
+        assert result.live_publish_revision == metadata.revision
+        verified = client.verify_installed_cycle_generation(
+            expected_revision=metadata.revision,
+            expected_state_id=metadata.state_id,
+            expected_repo_id=metadata.repo_id,
+            expected_root_path=metadata.root_path,
+            expected_graph_sha256=state.cycle_semantics.graph_sha256,
+        )
+        assert verified["status"] == "ok"
+        assert verified["service_instance_id"] == server.endpoint.service_instance_id
+        assert verified["source_manifest_sha256"] == (
+            receipt.prepared_manifest.source_manifest_sha256
+        )
+        altered = copy.copy(state)
+        altered_manifest = replace(
+            receipt.prepared_manifest,
+            components=(replace(
+                receipt.prepared_manifest.components[0],
+                model_evidence_sha256="f" * 64,
+            ),),
+        )
+        altered.cycle_source_publication = replace(
+            receipt, prepared_manifest=altered_manifest,
+        )
+        assert not verify_co_published_cycle_manifest(
+            altered, revision=metadata.revision,
+            state_id=metadata.state_id, repo_id=metadata.repo_id,
+            root_path=metadata.root_path,
+        )
```
