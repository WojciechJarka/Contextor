# C16-B03-P1D3G18-P2-D10 — restricted model precompilation and decorator boundary

## CURRENT_CANONICAL_STATE

- DIRECT_EVIDENCE — Contextor MCP `get_module_context` for `package_model`, `namespace_bound_model`, `full_analysis_lease`, `facade`, and `scenarios`: canonical revision **1109**, canonical_state=fresh, workspace_sync=verified, provenance=live, advisory_warning=null, graph/cycles fresh, cycle_semantics=stale, syntax_errors=0, structural DFS cycles=16, active_warning_count=16, model_pass_count=0. The MCP freshness envelope is source/index evidence, not proof of loaded runtime code.
- DIRECT_EVIDENCE — metadata-selected generation: state_id `20261106_195021`, repo_id `ctx_8efc50d8`, root `C:\Temp\Contextor_Repo`, FileState `file_state.r1109.67d19cdfd16d4a2eb4cf494ba6cc9523.json`. FileState-file SHA-256 `fe1f3c5666c4e97fc21ba83d615b4ea25ae4b2d9d2619a4eb974c08207995c12`; its embedded revision/state_id match metadata.
- DIRECT_EVIDENCE — repository interpreter Python 3.15.2. Git HEAD `3e4e3dfb7c57fba1ef6b1de64cf79bfb8f9cdb45`; worktree clean before this report overwrite. The previous P9 changes are in current HEAD, not merely an uncommitted worktree assumption.

## REPRODUCED_P9_RESULT

- DIRECT_EVIDENCE — one fresh-process source-bound call to `namespace_bound_model.py:50`, `evaluate_source_bound_conditional_namespace_import_order`, entry `contextor.core.api.facade`, full 308 physical production source inventory (tests excluded), `standard_finder_assumed=True`, `target_python_version=(3,15)`. All 308 source SHA-256 values match the current metadata-selected FileState. The source binder accepted the supplied inventory and returned digest `6ca1f598aef59e2760bcadb4fac2ba2dbf4bbb180f63de5ab46625cd161b815d`; no binding error. Conservative model cohort: 202 ASTs (`package_model.py:1706-1848`).
- DIRECT_EVIDENCE — outcome UNKNOWN, reason RESTRICTED_MODEL_UNKNOWN; nested first target `contextor.core.analysis.full_analysis_lease`, nested model event count **0**. Conditional authority remains `SOURCE_BOUND_CALLER_SUPPLIED_INVENTORY_NOT_RUNTIME_OR_LIVE_PROOF`. This reproduces P9 at revision 1109 and does not imply that the target was imported during modeled execution.

## PRECOMPILATION_EXECUTION_BOUNDARY

- CODE_PATH_PROVED — `package_model.py:914-1000`, `evaluate_package_import_order`: validates input and, if present, exact session AST identity; calls `build_package_layout` at 994 and rejects unsupported layout at 1000-1017.
- CODE_PATH_PROVED — `package_model.py:1020-1050`: calls CPython `compile(tree, ..., "exec", dont_inherit=True)` for **every selected indexed source** to check code-object validity. It does not execute the code objects. Reaching a later restricted-model refusal implies the CPython compile loop completed for the full supplied source set.
- CODE_PATH_PROVED — `package_model.py:1052-1070`: constructs logical source mapping and regular-package set. `package_model.py:1072-1129`: validates chains, then calls restricted `_compile` for **every logical source** before constructing model programs. A None return yields UNKNOWN with that source name.
- CODE_PATH_PROVED — `package_model.py:1132-1189`: checks prebinding conflicts, initializes states/namespaces and a bootstrap frame. `package_model.py:1210-1294`: starts frame processing and emits first modeled START_IMPORT only when a missing import piece is entered. The replay stopped in restricted precompilation, before bootstrap execution, hence events=().
- DISTINCT PROPERTIES — `full_analysis_lease` is in the 202-source conservative closure; its AST passed CPython compile validity; its AST did **not** pass restricted `_compile`; it was **not observed as visited by modeled import execution**. Inclusion, validity, restricted support and execution are separate claims.

## FIRST_DECORATOR_REJECTION

- DIRECT_EVIDENCE — FileState-bound `contextor/core/analysis/full_analysis_lease.py` SHA-256 `4ce9464534019f0369fc03ff04d4780f53ad37ecf65cbc4d3cb4a17d70cbe5dd`. Under `annotation_semantics="DEFERRED"`, incremental top-level AST prefixes through index 14 compile; adding index 15 fails: `ast.ClassDef FullAnalysisLease`, line 28 column 0.
- DIRECT_EVIDENCE — Decorator line 27: `@dataclass(frozen=True, slots=True)`. AST shape `Call(func=Name('dataclass'), keywords=[frozen=True, slots=True])`; both keyword values are boolean constants. Class bases=0; class keywords=0. Body has simple annotated fields `repo_key: str`, `token: str`, `owner: str`, `lock_path: str`, `repo_id: str`, `lock_fd: int`, `owner_pid: int = 0`, `owner_process_start_identity: int | None = None` (lines 29-36).
- CODE_PATH_PROVED — `package_model.py:146-169`, `_safe_passive_class_definition`, rejects any nonempty `statement.decorator_list` before inspecting class body. The class-creation decorator is the exact first guard; it is not an annotation-only refusal. `_compile` dispatches ClassDef to this guard at `package_model.py:727-732`.
- DIRECT_EVIDENCE — lexical binding `from dataclasses import dataclass` at `full_analysis_lease.py:17`, no later top-level assignment/import alias of the name found in this source. This identifies source-level provenance only. It does not authenticate the actual runtime callable, finder, module cache or third-party interference.

## LATER_INDEPENDENT_BLOCKERS

- DIRECT_EVIDENCE — Independent single-statement restricted compilation under DEFERRED identified five rejected top-level statements: first decorated `FullAnalysisLease` ClassDef at line 28; later `FullAnalysisBusyError(RuntimeError)` ClassDef at line 39 (nonempty base); `_PROCESS_LOCKS_GUARD = threading.Lock()` Assign at line 51; `_ADMISSION_LOCKS_GUARD = threading.Lock()` Assign at line 53 (both call-valued assignments); decorated `_canonical_writer_admission` FunctionDef at line 122 (`@contextmanager`). Each is a potential independent restricted-compiler blocker. The prefix test identifies line 28 as the actual first failure.
- CODE_PATH_PROVED — class-base, class-decorator and function-decorator rejection branches are `package_model.py:146-169,67-95`; call-valued assignment is outside the pure-literal/recognized assignment forms in `package_model.py:305-435,680-722`.
- DIRECT_EVIDENCE — source has top-level `from contextlib import contextmanager`, `import json, os, threading, time, uuid`, `from dataclasses import dataclass`, `from pathlib import Path`, `from typing import ...`, and Contextor-internal imports (lines 11-23). Those imports are not automatically safe; they are potential modeled execution effects. The replay did not reach any modeled import event, so none is asserted as an observed execution failure.
- CONTRACT PROVISO — single-statement checks isolate restricted AST support; they do not prove those later statements would be reached in a real import or that removing the first refusal would yield MODEL_PASS.

## COHORT_WIDE_REJECTION_CENSUS

- DIRECT_EVIDENCE — same in-memory 202-source conservative cohort, existing `_compile` with DEFERRED semantics, no source execution or model mutation: **94 accepted, 108 rejected**. First rejected top-level AST-kind distribution: ClassDef 70, Assign 33, FunctionDef 2, AnnAssign 2, If 1 (sum 108).
- DIRECT_EVIDENCE — modules containing at least one decorated **top-level** class: 72; decorated top-level function: 6; top-level class with nonempty bases: 29. These categories overlap. Lexically eager module/class-body import targets outside selected physical/namespace source names: 467 sites across 149 modules. This is a source-domain census, not a verified classification of all 467 as external packages or evidence of execution.
- Representative first rejections, with exact source construct: `contextor.core.analysis.full_analysis_lease` ClassDef 28 `@dataclass(frozen=True, slots=True)`; `contextor.core.analysis.function_analysis` ClassDef 11 `class ControlFlowAnalyzer(ast.NodeVisitor)`; `contextor.core.analysis.import_analysis` ClassDef 17 `class ImportUsageVisitor(ast.NodeVisitor)`; `contextor.core.analysis.incremental.engine` ClassDef 100 `@dataclass`; `contextor.core.analysis.incremental.graph_ops` ClassDef 18 `@dataclass(frozen=True)`; `contextor.core.analysis.incremental.plan_executor` ClassDef 46 `@dataclass`; `contextor.core.analysis.incremental.preparation` ClassDef 25 `@dataclass(frozen=True)`; `contextor.core.analysis.lineage_extraction` Assign 81 `_LINEAGE_CACHE_TOP_LEVEL_KEYS = frozenset(...)`; `contextor.core.analysis.lineage_extraction_bindings` Assign 17 `VisitFn = Callable[[...], None]`; `contextor.core.analysis.lineage_extraction_calls` Assign 10 same alias form. For each, the cited node is the observed first restricted-compiler rejection, not a claim that the node was executed. The exact subpredicate for representatives other than the separately inspected lease class was not exhaustively classified.
- INFERENCE BOUNDARY — 202 means selected candidates, not 202 executed modules. Even a module accepted by `_compile` may later yield UNKNOWN from modeled import execution or an outside-domain target.

## ENTRY_IMPORT_CHAIN

- DIRECT_EVIDENCE — all four named source files exist and match FileState. Standard import semantics for `contextor.core.api.facade` structurally require package initialization of `contextor`, `contextor.core`, `contextor.core.api` before the facade module, subject to actual runtime finder/cache state.
- DIRECT EVIDENCE — `contextor/__init__.py` has no top-level import statement (SHA-256 `ddbb4f795e5b16add318255d352e2e199bb65be33557655f533bb916ae04f9d8`). `contextor/core/__init__.py` first explicit import is line 12 `from contextor.core.graph.graph import build_graph`; subsequent top-level imports begin lines 19, 27, 30, 33. `contextor/core/api/__init__.py` is empty (SHA-256 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`). `contextor/core/api/facade.py` first imports are `json` line 9, `os` 10, `time` 11, `pathlib.Path` 12, `typing.Any` 13, then Contextor-internal imports from line 15. Its FileState SHA-256 is `e7412c57ffabcc9ca8fc33e8a93fc882161cb34db7bd75756b94c7ce37b386d8`.
- CODE_PATH PROVED — the restricted model constructs a package chain and bootstrap frame (`package_model.py:1072-1189`), but the current replay has zero START_IMPORT events. The chain is structurally required under ordinary standard import semantics; this replay does not establish that any listed initializer or subsequent import actually ran.

## EXISTING_TEST_COVERAGE

- CONTRACT_PROVED by source inspection, not execution — `tests/test_cycle_semantics_package_model.py`: `test_p1d3_d1_unsupported_class_effects` (line 1407; parameter cases include dynamic base, metaclass, decorated class and class-body calls); `test_b0g4c5_definition_effects_updated_contract` (line 1178; decorated function UNKNOWN); `test_p1d3_d1_class_import_timing` (1331); `test_p1d3_d1_uncalled_method_import_is_deferred` (1375); `test_parent_initializer_precedes_submodule` (71); `test_package_early_from_import_hazard` (239); `test_b0g4c15_uncalled_function_local_from_supported` (1219).
- CONTRACT_PROVED by source inspection — `tests/test_cycle_semantics_package_model_annotations315.py`: `test_deferred_function_annotations_and_literal_defaults` (34), `test_class_annotations_have_separate_binding_and_import_order` (54), `test_unknown_effects_remain_unknown` (line 105; decorator calls, dynamic bases, unknown external import), `test_early_binding_hazard_survives_annotations` (156). `tests/test_cycle_semantics_namespace_path_model.py`: `test_p9_cpython315_deferred_method_annotations` (454), `test_p9_external_import_still_unknown` (551), `test_g18_p2_p8_unreachable_unsupported_module` (785), `test_g18_p2_p8_parent_initializer_not_omitted` (901). `tests/test_cycle_semantics_namespace_bound_model.py`: `test_p6_eager_external_import_unknown` (316).
- UNKNOWN / COVERAGE GAP — no focused existing test was identified that asserts full 202-source precompilation returns zero model events specifically at decorated `FullAnalysisLease`, or that distinguishes CPython code-object validity, restricted AST acceptance and modeled visit for this real module. No test was added or run.

## REAL_SCC_GATES

- DIRECT_EVIDENCE — current canonical snapshot and `compute_cycle_model_source_closures_with_optional_children`: SCC1 44 members / 202 selected sources; SCC2 9 members / 222 selected sources. All selected source SHA-256 values matched current FileState (zero mismatch for each closure).
- DIRECT_EVIDENCE — `assess_package_graph_consistency` on current closures: both status INDETERMINATE, reason NAMESPACE_IMPORT_RESOLUTION_UNMODELED, internal graph state INDEXED_AST_GRAPH_MATCH_FOR_SELECTED_SOURCES, four namespace candidates each. SCC1 has 608 opaque external candidates; SCC2 has 726. Both external execution gates are OPAQUE_EXECUTION_POSSIBLE. The canonical snapshot's cycle-semantics family is stale; these are read-only current-source diagnostics, not fresh stored semantic claims.
- DIRECT_EVIDENCE — MCP structural DFS cycles 16, active warnings 16, model_pass_count 0. No SCC was promoted to MODEL_PASS; namespace and external execution uncertainty remain fail-closed.

## SOURCE_BINDING

- DIRECT_EVIDENCE — metadata-selected FileState revision 1109/state_id `20261106_195021` agreed with snapshot metadata and all 308 physical production source hashes used by the fresh-process replay. Five primary inspected source SHA-256 values: `package_model.py` `709bbae668a5a2f9a11dbabf491e14ca28f9c5f854fa8e37dc4154b430c17b4d`; `namespace_bound_model.py` `5952eec55fe7eecfb3047826aff38e76531707d4b89af4dd53adc6c1796bcf27`; `full_analysis_lease.py` `4ce9464534019f0369fc03ff04d4780f53ad37ecf65cbc4d3cb4a17d70cbe5dd`; `facade.py` `e7412c57ffabcc9ca8fc33e8a93fc882161cb34db7bd75756b94c7ce37b386d8`; `scenarios.py` `7e2c0475427e7fbd88417ed0109feb0ef5759aa67bfd25f946d264eab464b12a`. All five matched their FileState entries.
- CONTRACT PROVED — `namespace_bound_model.py:50-196` validates supplied inventory/fingerprints and parses byte snapshots before calling the conditional evaluator. The resulting digest binds this caller-supplied inventory; it does not authenticate actual runtime import selection.

## RESTART_AND_LIVE_ADOPTION

- DIRECT EVIDENCE — no Desktop/backend restart performed. Active MCP module context has live canonical facts and verified on-disk source, but contains no process-code identity proof that the already-running backend imported P9. Runtime adoption is **UNVERIFIED**. The fresh-process replay imported the current P9 code separately.
- CONTRACT BOUNDARY — a future LIVE/MCP adoption claim would require a controlled restart and verification of interpreter, process identity, GUI ownership and LIVE authority. No such adoption was attempted here.

## UNRESOLVED_FACTS

- UNKNOWN — actual application import finder, `sys.path`, `sys.meta_path`, `sys.modules`, lexical `dataclass` callable identity at runtime, external import effects and which conservative cohort members execute. UNKNOWN is not proof of safety.
- UNKNOWN — the exact per-module subpredicate for all 108 restricted compiler rejections was not requested or established; the first AST-kind distribution and ten representative constructs are reported without promoting them to runtime failures.

## FILES_CHANGED_AND_FULL_DIFFS

FILES_CHANGED: `walkthrough.md` only (this report). No production, test or source documentation edits.

ACTUAL_DIFF=DIFFS=NONE for production/tests. FULL_DIFFS=NONE for production/tests. `walkthrough.md` is excluded from its own diff.

## FINAL_VERDICT

DISCOVERY_COMPLETE. Read-only evidence gathering ended after D10. No implementation, pytest, production FULL, update_file, restart, interpreter switch, source execution, Git mutation, dependency installation, warning suppression or MODEL_PASS promotion.
