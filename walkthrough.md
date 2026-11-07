# CONTEXTOR C16-B03-P1D3G16-R1 — COMPLETE PRODUCTION AST FAILURE CENSUS

## PREFLIGHT

DIRECT_EVIDENCE — Contextor MCP first, current module contexts for `package_model.py`, `package_layout.py`, `typing_guard.py`, and `model_source_closure.py`: canonical revision 1078, canonical_state fresh, workspace_sync verified, syntax errors 0, structural DFS cycles 16, active_warning_count 16, model_pass_count 0, cycle_semantics stale. Read-only canonical snapshot/metadata: revision 1078, state_id `20261106_195021`, repo_id `ctx_8efc50d8`, root `C:\Temp\Contextor_Repo`. Git HEAD `4e1633139d655a73b49683b21b154def26126597` is a separate identity and was not equated to LIVE revision. G14 and G15 source edits are present in `package_model.py`; existing source/test worktree modifications were preserved. Current relevant code: `_safe_passive_function_definition` at `package_model.py:63`, `_safe_passive_class_definition` :141, `_pure_literal_expression` :221, `_safe_annassign` :319, `_compile` :337, Assign :558, AnnAssign :599, ClassDef :605, FunctionDef :668; `build_package_layout` at `package_layout.py:54`; `recognize_typing_guard` at `typing_guard.py:36`; optional closure builder at `model_source_closure.py:83`.

## PRODUCTION_INVENTORY

DIRECT_EVIDENCE — Filesystem rule: `contextor/**/*.py` (including every `__init__.py` and any `test_*.py` if present), plus root `main.py`; exclude tests/, virtual environments, caches, build/dist, temporary/generated copies, and dependencies by physical location. Actual count **307** = 306 under contextor/ + `main.py`, matching the user-confirmed number. Each path matched a canonical `Module.absolute_path` and unique module_id; no production file was omitted for its name. Canonical snapshot has 623 modules and hard_edges domain 623, of which 307 are production and 316 are indexed `tests/` modules. No production module is absent from hard_edges. Thus production filesystem inventory, canonical FileState/index domain and SCC source closure are distinct sets.

## CANONICAL_SOURCE_BINDING

DIRECT_EVIDENCE — Referenced FileState JSON has 623 records and `_meta` revision 1078/state_id `20261106_195021`. All 307 production files were readable, parsed, and had current byte SHA-256 equal to their FileState entry. Source-bound 307; SOURCE_UNBOUND 0; SOURCE_UNAVAILABLE 0. For each module the diagnostic used its repo-relative path, canonical module_id, SHA-256, FileState binding, hard_edges membership and both closure-membership flags. Therefore raw and source-bound compilation counts coincide. No analyzed source is presented as canonical evidence without its fingerprint match.

## SCC_CLOSURE_IDENTITIES

DIRECT_EVIDENCE — Rebuilt `compute_cycle_model_source_closures_with_optional_children` from current canonical hard_edges and `Module.imports`. A=SCC1 closure: 44 cyclic members, 201 selected modules. B=SCC2 closure: 9 members, 221 selected modules. C=A∪B: 221 unique modules; A⊆B by verified module IDs. D=ALL_PRODUCTION−C: 86 modules. C∩D=∅. Every selected module is production and FileState-bound. The 201 and 221 counts were never added as unique sources.

## ALL_PRODUCTION_COMPILATION_COVERAGE

Diagnostic calls to current `_compile` with `annotation_semantics="DEFERRED"` and `recognize_typing_guard` over the indexed production domain; no analyzed code executed. Prefix recompilation of original AST statement references located each first rejection without AST mutation. This is restricted compiler coverage only, never MODEL_PASS. Groups use their own indexed group domain for typing-guard recognition; the reported counts partition consistently.

| Group | Total | Bound | Unbound | Unavailable | Supported | Unsupported | Supported % |
|---|---:|---:|---:|---:|---:|---:|---:|
| ALL_PRODUCTION | 307 | 307 | 0 | 0 | 147 | 160 | 47.88% |
| SCC1_CLOSURE | 201 | 201 | 0 | 0 | 90 | 111 | 44.78% |
| SCC2_CLOSURE | 221 | 221 | 0 | 0 | 103 | 118 | 46.61% |
| SCC_UNION | 221 | 221 | 0 | 0 | 103 | 118 | 46.61% |
| OUTSIDE_BOTH | 86 | 86 | 0 | 0 | 44 | 42 | 51.16% |

First-rejection breakdown for ALL_PRODUCTION: ClassDef 86, Assign 60, AnnAssign 3, If 1, FunctionDef 3, AsyncFunctionDef 4, Expr 3; total 160. The 147 supported modules are source-bound, but this does not establish package execution or runtime safety.

## SCC1_COMPILATION_COVERAGE

90 supported / 111 unsupported of 201, matching G15 baseline. First rejection: ClassDef 69, Assign 37, AnnAssign 2, If 1, FunctionDef 2. Source-bound 201/201. Representative ClassDef: `contextor/core/analysis/full_analysis_lease.py:28` decorated dataclass; `contextor/core/analysis/function_analysis.py:11` dynamic base. Representative Assign: `contextor/core/analysis/export_analysis.py:112` Name value; `contextor/core/analysis/lineage_extraction.py:81` call to frozenset. Both are refused by the actual restricted guards, not judged erroneous Python.

## SCC2_COMPILATION_COVERAGE

103 supported / 118 unsupported of 221, matching G15 baseline. First rejection: ClassDef 72, Assign 41, AnnAssign 2, If 1, FunctionDef 2. Source-bound 221/221. The SCC union is identical to this closure by exact module IDs and therefore has the same counts.

## SCC_UNION_COVERAGE

221 source-bound; 103 supported, 118 unsupported; 46.61%. First rejections ClassDef 72, Assign 41, AnnAssign 2, If 1, FunctionDef 2. This is a set union, not 201+221. `recognize_typing_guard` used the exact selected module domain in this group.

## OUTSIDE_SCC_COVERAGE

86 source-bound; 44 supported, 42 unsupported; 51.16%. First rejections Assign 19, ClassDef 14, AsyncFunctionDef 4, AnnAssign 1, FunctionDef 1, Expr 3. Examples: `contextor/cli.py:20` reserved `__version__` Assign; `contextor/core/canonical_state_query/contract.py:18` BinOp value; `contextor/mcp/tools/analyze_layer.py:7` AsyncFunctionDef; `contextor/mcp_server.py:170` call expression with an unsupported argument/attribute shape; `main.py:20` module-level call. These are static model limits, not claims about whether the real code executes safely.

## CLASSDEF_FAILURE_MATRIX

DIRECT_EVIDENCE — Among 86 modules whose *first* rejected statement is ClassDef, independent reason occurrences can overlap within a class. Guard: `_safe_passive_class_definition` (`package_model.py:141-218`); method guard `_safe_passive_function_definition` (:63-138). Counts: class decorators **59** (e.g. `contextor/core/analysis/full_analysis_lease.py:28`; no dataclass decorator is assumed passive), bases **20** (e.g. `contextor/core/analysis/function_analysis.py:11`), invalid class-body AnnAssign **35** (e.g. `contextor/core/analysis/incremental/engine.py:119` within class at :100), invalid method definitions **15** (e.g. `contextor/core/analysis/refresh_planner.py:81` within class at :70), invalid class-body Assign **2** (e.g. `contextor/core/graph/resolver.py:48`). Invalid class name, dunder class name, class keywords/metaclass, class type parameters were not observed as independent reasons among these first-rejected classes. Body statement inventory in these 86 classes: AnnAssign 415, FunctionDef 128, Expr 26, Assign 21; no direct body import, AsyncFunctionDef or Other statement was observed in this subset. Among the 15 rejected methods, **14** had decorators and **1** had a nonliteral default (`contextor/core/reporting_engine/persistent_registry.py:529`). Annotation syntax appeared in 13 rejected methods, but under explicit DEFERRED it is not itself the refusing condition. Seven had defaults of any kind; only the one nonliteral default is a confirmed default refusal. Class body executes at definition; method bodies remain deferred. This matrix does not infer execution of deferred method bodies.

## ASSIGN_FAILURE_MATRIX

DIRECT_EVIDENCE — Among 60 first-rejected Assign modules, the current `_compile` Assign guard (`package_model.py:558-597`) rejects 1 reserved name (`contextor/cli.py:20`, `__version__`) and 59 values that are neither `_pure_literal_expression` nor the supported simple ATTR form. No multi-target, non-Name target, invalid identifier, or failed special `__all__` shape occurred as the *first* Assign refusal in this production set. Value AST categories: Call 29, Subscript 13, BinOp 11, Name 4, ContainerWithUnsupportedChild 2, Attribute 0, Comprehension 0, Other 0, plus the one Constant under disallowed special name. Examples (at most five): `contextor/core/analysis/export_analysis.py:112` Name; `contextor/core/analysis/lineage_extraction.py:81` Call; `contextor/core/analysis/lineage_extraction_bindings.py:17` Subscript; `contextor/core/canonical_state_query/contract.py:18` BinOp; `contextor/cli.py:20` special name. The 59 value cases fail the exact `_pure_literal_expression`/ATTR branch. A syntactic Call is evidence of an unsupported form, not proof that its effects are harmless or actually executed on every import path.

## OTHER_STATEMENT_FAILURES

All remaining 14 first refusals, with exact rejecting code path:

| Type | Count | Locations and condition |
|---|---:|---|
| AnnAssign | 3 | `contextor/core/analysis/lineage_extraction_contracts.py:17`; `contextor/core/graph/incremental.py:56`; `contextor/mcp/tools/contextor_fact_lineage.py:27`. Each value is not a pure literal under `_safe_annassign` (`package_model.py:319-334`); DEFERRED is already supplied. |
| If | 1 | `contextor/core/cycle_semantics/contracts.py:21`, TYPE_CHECKING branch not accepted by the current whole-module recognizer/selected-condition gate (`package_model.py:492-556`; `typing_guard.py:36-257`). This does not imply the guarded body runs at import. |
| FunctionDef | 3 | `contextor/core/domain/module.py:17` decorator; `contextor/core/reporting_layer/artifact_usage_report.py:408` nonliteral default; `contextor/mcp/tools/describe_canonical_state.py:10` nonliteral default. `_safe_passive_function_definition` (`package_model.py:63-138`) rejects definition-time effects; function bodies remain deferred. |
| AsyncFunctionDef | 4 | `contextor/mcp/tools/analyze_layer.py:7`, `analyze_project.py:7`, `analyze_single_file.py:7`, `contextor_profile_analysis.py:21`; unmatched top-level statement reaches `_compile` final fallback (`package_model.py:760-763`). |
| Expr | 3 | `contextor/mcp_server.py:170`, `contextor/mcp_worker.py:12`, `main.py:20`; call shape fails the narrow zero-argument direct-name Expr rule (`package_model.py:749-759`). |

The 14 cases are 3+1+3+4+3. Nested class-body execution and deferred function bodies were separately classified in the ClassDef matrix; unsupported conditional effects remain UNKNOWN.

## CROSS_GROUP_CONSISTENCY

DIRECT_EVIDENCE — A⊆ALL_PRODUCTION and B⊆ALL_PRODUCTION; A⊆B; C=A∪B=221; D=ALL_PRODUCTION−C=86; C∩D=∅; 221+86=307. Supported counts also partition: 103+44=147; unsupported: 118+42=160. Indexed hard_edges has 316 IDs outside production, all from `tests/`, e.g. `tests.analysis.test_cache_manager_content_hash` and `tests.analysis.test_lineage_cache_codec`. There are 0 production IDs outside hard_edges. Snapshot hard-edge SHA-256 before/after read-only census: `1c75f969783051dffde00dcb3d65c68c1f93f5a65f2e141de0db42884e016afa`; unchanged. Metadata revision remained 1078; no optional /3 receipt appeared.

## REMAINING_MODEL_LIMITS

This is static `_compile` coverage, not `evaluate_package_import_order` or `analyze_cycle_scenarios` acceptance. It does not bypass namespace, external import, package layout, target interpreter, or source-binding gates. G13/G15 real SCCs still have namespace and opaque external execution uncertainty; no new MODEL_PASS is derived. The current cycle_semantics snapshot is stale despite fresh source/index/graph. No warning suppression or production LIVE publication was performed.

## MCP_POST_DISCOVERY_AUDIT

Read-only Contextor MCP after census: canonical revision 1078, canonical_state fresh, workspace_sync verified for package_model, syntax errors 0, structural DFS cycles 16 (fresh), active_warning_count 16, model_pass_count 0, cycle_semantics stale, advisory_warning null. No production/full analysis, pytest, restart, update_file, source/test edit, manual commit or LIVE publication.

## FULL_DIFFS

FILES_CHANGED: `walkthrough.md` only for this task. FULL_DIFFS=NONE for code/tests/docs. Pre-existing uncommitted G14/G15 source/test changes were preserved and are not claimed as G16-R1 edits. This report is excluded from its own diff.

## FINAL_VERDICT

DISCOVERY_COMPLETE — 307 production modules were inventoried and FileState-bound, both SCC closures and all five group counts are consistent, and all 160 first `_compile` refusals were categorized without changing production LIVE.
