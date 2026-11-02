# CONTEXTOR PY315-M8B — lazy import semantics discovery

## PREFLIGHT

Contextor MCP first: sampled source, indexer, ImportRef, graph, initialization and provenance module contexts all `canonical_state=fresh`, `workspace_sync=verified`, revision 962, no advisory. HEAD `534858dfd569fb4dc27aac189a098ebc25312bd8`; worktree only pre-existing `M walkthrough.md`. Repo ID `ctx_8efc50d8`. Canonical 3.15.2, base `C:\Python315\python.exe`; production lazy mode `normal`. No production mutation.

## MCP_FIRST_DISCOVERY

Read `get_mcp_documentation` for relevant tools. Contextor module contexts are live/fresh/verified. `get_symbol_lineage` preview resolved `contextor.core.symbol_engine.indexer::read_imports` and `contextor.core.cycle_semantics.cycle_warning_projection::project_installed_cycle_warnings`, revision 962, no advisory; lineage path itself reports workspace_sync unverified by design. Exact implementation/call-chain remains incompletely traced.

## PY315_IMPORT_LANGUAGE_CONTRACT

[PEP 810](https://peps.python.org/pep-0810/) and [What's New 3.15](https://docs.python.org/3.15/whatsnew/3.15.html): explicit lazy import/from-import is potentially lazy; `normal` permits explicit and `__lazy_modules__`, `all` makes eligible ordinary module imports potentially lazy, `none` forces eager. `PYTHON_LAZY_IMPORTS`/`-X lazy_imports` set startup mode; `sys.set_lazy_imports` changes it at runtime; filter can veto potentially lazy import. `__lazy_modules__` is checked at statement execution and may be computed/changed. First use reifies; failures/side effects can be delayed. Dynamic importlib remains eager. Already loaded module and indirect reification alter timing. Source alone proves AST marker, not effective laziness when global mode/filter/runtime state unknown. Package/relative/circular details only partially probed here. [Import reference](https://docs.python.org/3.15/reference/import.html), [AST](https://docs.python.org/3.15/library/ast.html), [importlib](https://docs.python.org/3.15/library/importlib.html).

## PRODUCTION_IMPORT_CONFIGURATION

Fresh canonical subprocess reports `sys.get_lazy_imports()='normal'`; source search found no Contextor `lazy import`, `__lazy_modules__`, or `sys.set_lazy_imports`. This does not prove analyzed third-party source or process-specific filter/mode. Production processes were not modified.

## SOURCE_CAPTURE_CHAIN

Known chain: `core/source.py` tokenize decoding → ast.parse → `core/symbol_engine/indexer.py:634` read_imports/AdvancedImportVisitor → `core/domain/imports.py:12` ImportRef → `core/graph/resolver.py:254` resolve_internal → `core/graph/graph.py:93/111` build_graph → `core/graph/cycles.py:157` detect_cycles. Parallel AST → `cycle_semantics/provenance.py:322` extract_import_provenance → `execution_context.py:38` project_execution_context → binding_order/scenarios/initialization_model → evidence/worker claim → installed warning projection. Direct source checked at entry and selected consumers; complete publication/UI/MCP caller graph not proven.

## IMPORTREF_DATA_LOSS

CONFIRMED_EVIDENCE_LOSS: `AdvancedImportVisitor.visit_Import` indexer.py:264 and `visit_ImportFrom` :290 do not read `node.is_lazy`; ImportRef has module/level/names/is_from_import/is_local/type_only only. L01/L02 external probes yield same target ImportRef despite AST 0/1 and different runtime traces. Earliest observed loss is visitor conversion.

## PROVENANCE_DATA_LOSS

CONFIRMED_EVIDENCE_LOSS: `cycle_semantics/provenance.py:322-414` ImportOccurrence records location/form/module/level/aliases/scopes/controls but no `is_lazy`. L01/L02 projected execution contexts both `MODULE_OR_CLASS_CANDIDATE`, reachability `UNKNOWN`. The execution model does not claim unconditional eager execution, so no direct false safety proof at that stage.

## GRAPH_COMPATIBILITY

Structural dependency is lexical: frozen hard-edge graph should retain lazy import target; activation timing is separate. Current resolver/graph/SCC path consumes ImportRef and cannot distinguish activation. Direct end-to-end graph output for synthetic lazy repo was not run; hard-edge parity is source-level inference, not runtime confirmation.

## EXECUTION_MODEL

`execution_context.py:38` classifies lexical scope/control and leaves initialization reachability UNKNOWN. It does not store effective lazy mode, filter result, or first-use point. `normal` ordinary import eager; `all` ordinary import can be lazy despite AST is_lazy=0. This is configuration-dependent and must not be called safe or eager without authority.

## BINDING_ORDER_MODEL

`binding_order.py:163` extracts lexical candidates by position. It does not model lazy first-use. This is evidence order, not execution order. Exact impact on binding diagnosis for all L-cases untested.

## INITIALIZATION_MODEL

`initialization_model.py` explicitly restricts itself to Python 3.10 flat modules; `_compile` at :44 treats ast.Import/ImportFrom as immediate steps without is_lazy. Synthetic pure models: lazy mutual no use yielded MODEL_PASS, lazy mutual from-import yielded EARLY_BINDING_HAZARD both entries, lazy early read yielded EARLY_BINDING_HAZARD. Actual isolated `cycle_lazy_from` CPython 3.15 execution completed `MAIN_COMPLETE 1` (no first use), contradicting model's predicted eager hazard for this tested order. This proves a local semantic mismatch. `scenarios.py:177,237` accepts model assessments for flat applicable SCC; evidence.py:314+ validates them. Whether this exact fixture reaches active warning needs full source-bound installation proof; do not claim warning publication confirmed.

## PACKAGE_AND_NAMESPACE_IMPORTS

Package model, layout and namespace source-binding have separate admission/consistency checks. `scenarios.py` chooses package model only when flat model inapplicable and package consistency passes; no lazy-aware branch confirmed. L31–L34 not executed. Namespace uncertainty remains UNKNOWN, not safe.

## EXPLICIT_LAZY_CASES_L01_L12

Matrix rows below; L12 not executed. Source fixture and results are inspectable in lab JSON. For each executed case, AST contains target lazy flag as shown, Contextor ImportRef lacks it, and runtime stdout gives import order/first use. Initialization model reported UNKNOWN for these generic scripts because print/sys are outside restricted subset.

```text
CASE_ID|SOURCE_FIXTURE|INTERPRETER_MODE|AST_RESULT|RUNTIME_RESULT|CONTEXTOR_RESULT|EVIDENCE_CLASS|COVERAGE_STATUS|UNRESOLVED_QUESTION
L01|C:\Temp\Contextor_PY315_M2_Lab\M8B_lazy_discovery\L01\main.py|normal|eager AST|exit=0; TARGET_INIT → after 7|ImportRef(module='target', level=0, names=[], is_from_import=False, is_local=False, type_only=False); model=UNKNOWN|DIRECT_RUNTIME_PROOF + CODE_PATH_PROVED|NOT_COVERED in lazy Contextor projection|full cycle/publication path untested
L02|C:\Temp\Contextor_PY315_M2_Lab\M8B_lazy_discovery\L02\main.py|normal|Import:1|exit=0; after|ImportRef(module='target', level=0, names=[], is_from_import=False, is_local=False, type_only=False); model=UNKNOWN|DIRECT_RUNTIME_PROOF + CODE_PATH_PROVED|NOT_COVERED in lazy Contextor projection|full cycle/publication path untested
L03|C:\Temp\Contextor_PY315_M2_Lab\M8B_lazy_discovery\L03\main.py|normal|Import:1|exit=0; TARGET_INIT → after 7|ImportRef(module='target', level=0, names=[], is_from_import=False, is_local=False, type_only=False); model=UNKNOWN|DIRECT_RUNTIME_PROOF + CODE_PATH_PROVED|NOT_COVERED in lazy Contextor projection|full cycle/publication path untested
L04|C:\Temp\Contextor_PY315_M2_Lab\M8B_lazy_discovery\L04\main.py|normal|Import:1|exit=0; TARGET_INIT → before 7|ImportRef(module='target', level=0, names=[], is_from_import=False, is_local=False, type_only=False); model=UNKNOWN|DIRECT_RUNTIME_PROOF + CODE_PATH_PROVED|NOT_COVERED in lazy Contextor projection|full cycle/publication path untested
L05|C:\Temp\Contextor_PY315_M2_Lab\M8B_lazy_discovery\L05\main.py|normal|ImportFrom:1|exit=0; after|ImportRef(module='target', level=0, names=['value'], is_from_import=True, is_local=False, type_only=False); model=UNKNOWN|DIRECT_RUNTIME_PROOF + CODE_PATH_PROVED|NOT_COVERED in lazy Contextor projection|full cycle/publication path untested
L06|C:\Temp\Contextor_PY315_M2_Lab\M8B_lazy_discovery\L06\main.py|normal|ImportFrom:1|exit=0; TARGET_INIT → after 7|ImportRef(module='target', level=0, names=['value'], is_from_import=True, is_local=False, type_only=False); model=UNKNOWN|DIRECT_RUNTIME_PROOF + CODE_PATH_PROVED|NOT_COVERED in lazy Contextor projection|full cycle/publication path untested
L07|C:\Temp\Contextor_PY315_M2_Lab\M8B_lazy_discovery\L07\main.py|normal|ImportFrom:1|exit=0; TARGET_INIT → before 7|ImportRef(module='target', level=0, names=['value'], is_from_import=True, is_local=False, type_only=False); model=UNKNOWN|DIRECT_RUNTIME_PROOF + CODE_PATH_PROVED|NOT_COVERED in lazy Contextor projection|full cycle/publication path untested
L08|C:\Temp\Contextor_PY315_M2_Lab\M8B_lazy_discovery\L08\main.py|normal|Import:1|exit=0; OTHER_INIT → one 8 → TARGET_INIT → two 7|ImportRef(module='target', level=0, names=[], is_from_import=False, is_local=False, type_only=False); model=UNKNOWN|DIRECT_RUNTIME_PROOF + CODE_PATH_PROVED|NOT_COVERED in lazy Contextor projection|full cycle/publication path untested
L09|C:\Temp\Contextor_PY315_M2_Lab\M8B_lazy_discovery\L09\main.py|normal|Import:1|exit=0; TARGET_INIT → alias 7|ImportRef(module='target', level=0, names=[], is_from_import=False, is_local=False, type_only=False); model=UNKNOWN|DIRECT_RUNTIME_PROOF + CODE_PATH_PROVED|NOT_COVERED in lazy Contextor projection|full cycle/publication path untested
L10|C:\Temp\Contextor_PY315_M2_Lab\M8B_lazy_discovery\L10\main.py|normal|ImportFrom:1|exit=0; TARGET_INIT → alias 7|ImportRef(module='target', level=0, names=['value'], is_from_import=True, is_local=False, type_only=False); model=UNKNOWN|DIRECT_RUNTIME_PROOF + CODE_PATH_PROVED|NOT_COVERED in lazy Contextor projection|full cycle/publication path untested
L11|C:\Temp\Contextor_PY315_M2_Lab\M8B_lazy_discovery\L11\main.py|normal|Import:1|exit=0; no access|ImportRef(module='target', level=0, names=[], is_from_import=False, is_local=False, type_only=False); model=UNKNOWN|DIRECT_RUNTIME_PROOF + CODE_PATH_PROVED|NOT_COVERED in lazy Contextor projection|full cycle/publication path untested
L12|C:\Temp\Contextor_PY315_M2_Lab\M8B_lazy_discovery\L12\main.py (not created)|UNKNOWN|NOT_PROBED|NOT_PROBED|NOT_PROBED|INSUFFICIENT_EVIDENCE|NOT_COVERED|Execution/configuration and Contextor projection unresolved
```

## IMPLICIT_LAZY_CASES_L13_L24

Same matrix format. L17/L21/L24 unexecuted. L14 under all avoided target initialization; L16/L18 with literal __lazy_modules__ avoided it. L19 computed set also did so at runtime but is not statically provable. L20 runtime mode change avoided it. The current AST for ordinary imports remains is_lazy=0.

```text
L13|C:\Temp\Contextor_PY315_M2_Lab\M8B_lazy_discovery\L13\main.py|normal|eager AST|exit=0; TARGET_INIT → after|ImportRef(module='target', level=0, names=[], is_from_import=False, is_local=False, type_only=False); model=UNKNOWN|DIRECT_RUNTIME_PROOF + CODE_PATH_PROVED|NOT_COVERED in lazy Contextor projection|full cycle/publication path untested
L14|C:\Temp\Contextor_PY315_M2_Lab\M8B_lazy_discovery\L14\main.py|all|eager AST|exit=0; after|ImportRef(module='target', level=0, names=[], is_from_import=False, is_local=False, type_only=False); model=UNKNOWN|DIRECT_RUNTIME_PROOF + CODE_PATH_PROVED|NOT_COVERED in lazy Contextor projection|full cycle/publication path untested
L15|C:\Temp\Contextor_PY315_M2_Lab\M8B_lazy_discovery\L15\main.py|normal|Import:1|exit=0; after|ImportRef(module='target', level=0, names=[], is_from_import=False, is_local=False, type_only=False); model=UNKNOWN|DIRECT_RUNTIME_PROOF + CODE_PATH_PROVED|NOT_COVERED in lazy Contextor projection|full cycle/publication path untested
L16|C:\Temp\Contextor_PY315_M2_Lab\M8B_lazy_discovery\L16\main.py|normal|eager AST|exit=0; after|ImportRef(module='target', level=0, names=[], is_from_import=False, is_local=False, type_only=False); model=UNKNOWN|DIRECT_RUNTIME_PROOF + CODE_PATH_PROVED|NOT_COVERED in lazy Contextor projection|full cycle/publication path untested
L17|C:\Temp\Contextor_PY315_M2_Lab\M8B_lazy_discovery\L17\main.py (not created)|UNKNOWN|NOT_PROBED|NOT_PROBED|NOT_PROBED|INSUFFICIENT_EVIDENCE|NOT_COVERED|Execution/configuration and Contextor projection unresolved
L18|C:\Temp\Contextor_PY315_M2_Lab\M8B_lazy_discovery\L18\main.py|normal|ImportFrom:0|exit=0; after|ImportRef(module='target', level=0, names=['value'], is_from_import=True, is_local=False, type_only=False); model=UNKNOWN|DIRECT_RUNTIME_PROOF + CODE_PATH_PROVED|NOT_COVERED in lazy Contextor projection|full cycle/publication path untested
L19|C:\Temp\Contextor_PY315_M2_Lab\M8B_lazy_discovery\L19\main.py|normal|eager AST|exit=0; after|ImportRef(module='target', level=0, names=[], is_from_import=False, is_local=False, type_only=False); model=UNKNOWN|DIRECT_RUNTIME_PROOF + CODE_PATH_PROVED|NOT_COVERED in lazy Contextor projection|computed __lazy_modules__ not statically proven
L20|C:\Temp\Contextor_PY315_M2_Lab\M8B_lazy_discovery\L20\main.py|normal|eager AST|exit=0; after|ImportRef(module='target', level=0, names=[], is_from_import=False, is_local=False, type_only=False); model=UNKNOWN|DIRECT_RUNTIME_PROOF + CODE_PATH_PROVED|NOT_COVERED in lazy Contextor projection|full cycle/publication path untested
L21|C:\Temp\Contextor_PY315_M2_Lab\M8B_lazy_discovery\L21\main.py (not created)|UNKNOWN|NOT_PROBED|NOT_PROBED|NOT_PROBED|INSUFFICIENT_EVIDENCE|NOT_COVERED|Execution/configuration and Contextor projection unresolved
L22|C:\Temp\Contextor_PY315_M2_Lab\M8B_lazy_discovery\L22\main.py|normal|eager AST|exit=0; TARGET_INIT → after|ImportRef(module='target', level=0, names=[], is_from_import=False, is_local=False, type_only=False); model=UNKNOWN|DIRECT_RUNTIME_PROOF + CODE_PATH_PROVED|NOT_COVERED in lazy Contextor projection|full cycle/publication path untested
L23|C:\Temp\Contextor_PY315_M2_Lab\M8B_lazy_discovery\L23\main.py|normal|Import:1|exit=0; TARGET_INIT → after 7|ImportRef(module='target', level=0, names=[], is_from_import=False, is_local=False, type_only=False); model=UNKNOWN|DIRECT_RUNTIME_PROOF + CODE_PATH_PROVED|NOT_COVERED in lazy Contextor projection|full cycle/publication path untested
L24|C:\Temp\Contextor_PY315_M2_Lab\M8B_lazy_discovery\L24\main.py (not created)|UNKNOWN|NOT_PROBED|NOT_PROBED|NOT_PROBED|INSUFFICIENT_EVIDENCE|NOT_COVERED|Execution/configuration and Contextor projection unresolved
```

## SYNTAX_SCOPE_CASES

Important DIRECT_RUNTIME_PROOF: `ast.parse` accepts several illegal lazy placements; `compile` rejects them. Thus AST-only admission can treat syntactically non-executable source as valid. Current `read_imports` uses parsed AST without compile check on this path; full project syntax diagnostics path not traced.

|Form|AST parse|Compile|AST flags|
|---|---|---|---|
|module|VALID_AST|VALID|[["Import",1]]|
|module_from|VALID_AST|VALID|[["ImportFrom",1]]|
|function|VALID_AST|SYNTAX_ERROR: lazy import not allowed inside functions|[["Import",1]]|
|async_function|VALID_AST|SYNTAX_ERROR: lazy import not allowed inside functions|[["Import",1]]|
|class|VALID_AST|SYNTAX_ERROR: lazy import not allowed inside classes|[["Import",1]]|
|try|VALID_AST|SYNTAX_ERROR: lazy import not allowed inside try/except blocks|[["Import",1]]|
|except|VALID_AST|SYNTAX_ERROR: lazy import not allowed inside try/except blocks|[["Import",1]]|
|finally|VALID_AST|SYNTAX_ERROR: lazy import not allowed inside try/except blocks|[["Import",1]]|
|star|VALID_AST|SYNTAX_ERROR: lazy from ... import * is not allowed|[["ImportFrom",1]]|
|future|SYNTAX_ERROR|lazy from __future__ import is not allowed|[]|
|if|VALID_AST|VALID|[["Import",1]]|
|for|VALID_AST|VALID|[["Import",1]]|

## CYCLE_CASES_L25_L40

These 16 required cases were not executed as L25-L40. Separate `cycle_lazy_from` fixture proves one narrower scenario: two lazy from-imports, no first use, actual 3.15 success but restricted model EARLY_BINDING_HAZARD. Map for this tested scenario: STRUCTURE cyclic lexical dependency (inferred from sources); EXECUTION deferred until use (runtime confirmed for tested run); INITIALIZATION no failure in tested run, static model contradictory; VERIFICATION RUNTIME_REFUTED_FOR_TESTED_SCENARIO only. Other cycle outcomes INCONCLUSIVE.

```text
L25|C:\Temp\Contextor_PY315_M2_Lab\M8B_lazy_discovery\L25\main.py (not created)|UNKNOWN|NOT_PROBED|NOT_PROBED|NOT_PROBED|INSUFFICIENT_EVIDENCE|NOT_COVERED|Execution/configuration and Contextor projection unresolved
L26|C:\Temp\Contextor_PY315_M2_Lab\M8B_lazy_discovery\L26\main.py (not created)|UNKNOWN|NOT_PROBED|NOT_PROBED|NOT_PROBED|INSUFFICIENT_EVIDENCE|NOT_COVERED|Execution/configuration and Contextor projection unresolved
L27|C:\Temp\Contextor_PY315_M2_Lab\M8B_lazy_discovery\L27\main.py (not created)|UNKNOWN|NOT_PROBED|NOT_PROBED|NOT_PROBED|INSUFFICIENT_EVIDENCE|NOT_COVERED|Execution/configuration and Contextor projection unresolved
L28|C:\Temp\Contextor_PY315_M2_Lab\M8B_lazy_discovery\L28\main.py (not created)|UNKNOWN|NOT_PROBED|NOT_PROBED|NOT_PROBED|INSUFFICIENT_EVIDENCE|NOT_COVERED|Execution/configuration and Contextor projection unresolved
L29|C:\Temp\Contextor_PY315_M2_Lab\M8B_lazy_discovery\L29\main.py (not created)|UNKNOWN|NOT_PROBED|NOT_PROBED|NOT_PROBED|INSUFFICIENT_EVIDENCE|NOT_COVERED|Execution/configuration and Contextor projection unresolved
L30|C:\Temp\Contextor_PY315_M2_Lab\M8B_lazy_discovery\L30\main.py (not created)|UNKNOWN|NOT_PROBED|NOT_PROBED|NOT_PROBED|INSUFFICIENT_EVIDENCE|NOT_COVERED|Execution/configuration and Contextor projection unresolved
L31|C:\Temp\Contextor_PY315_M2_Lab\M8B_lazy_discovery\L31\main.py (not created)|UNKNOWN|NOT_PROBED|NOT_PROBED|NOT_PROBED|INSUFFICIENT_EVIDENCE|NOT_COVERED|Execution/configuration and Contextor projection unresolved
L32|C:\Temp\Contextor_PY315_M2_Lab\M8B_lazy_discovery\L32\main.py (not created)|UNKNOWN|NOT_PROBED|NOT_PROBED|NOT_PROBED|INSUFFICIENT_EVIDENCE|NOT_COVERED|Execution/configuration and Contextor projection unresolved
L33|C:\Temp\Contextor_PY315_M2_Lab\M8B_lazy_discovery\L33\main.py (not created)|UNKNOWN|NOT_PROBED|NOT_PROBED|NOT_PROBED|INSUFFICIENT_EVIDENCE|NOT_COVERED|Execution/configuration and Contextor projection unresolved
L34|C:\Temp\Contextor_PY315_M2_Lab\M8B_lazy_discovery\L34\main.py (not created)|UNKNOWN|NOT_PROBED|NOT_PROBED|NOT_PROBED|INSUFFICIENT_EVIDENCE|NOT_COVERED|Execution/configuration and Contextor projection unresolved
L35|C:\Temp\Contextor_PY315_M2_Lab\M8B_lazy_discovery\L35\main.py (not created)|UNKNOWN|NOT_PROBED|NOT_PROBED|NOT_PROBED|INSUFFICIENT_EVIDENCE|NOT_COVERED|Execution/configuration and Contextor projection unresolved
L36|C:\Temp\Contextor_PY315_M2_Lab\M8B_lazy_discovery\L36\main.py (not created)|UNKNOWN|NOT_PROBED|NOT_PROBED|NOT_PROBED|INSUFFICIENT_EVIDENCE|NOT_COVERED|Execution/configuration and Contextor projection unresolved
L37|C:\Temp\Contextor_PY315_M2_Lab\M8B_lazy_discovery\L37\main.py (not created)|UNKNOWN|NOT_PROBED|NOT_PROBED|NOT_PROBED|INSUFFICIENT_EVIDENCE|NOT_COVERED|Execution/configuration and Contextor projection unresolved
L38|C:\Temp\Contextor_PY315_M2_Lab\M8B_lazy_discovery\L38\main.py (not created)|UNKNOWN|NOT_PROBED|NOT_PROBED|NOT_PROBED|INSUFFICIENT_EVIDENCE|NOT_COVERED|Execution/configuration and Contextor projection unresolved
L39|C:\Temp\Contextor_PY315_M2_Lab\M8B_lazy_discovery\L39\main.py (not created)|UNKNOWN|NOT_PROBED|NOT_PROBED|NOT_PROBED|INSUFFICIENT_EVIDENCE|NOT_COVERED|Execution/configuration and Contextor projection unresolved
L40|C:\Temp\Contextor_PY315_M2_Lab\M8B_lazy_discovery\L40\main.py (not created)|UNKNOWN|NOT_PROBED|NOT_PROBED|NOT_PROBED|INSUFFICIENT_EVIDENCE|NOT_COVERED|Execution/configuration and Contextor projection unresolved
```

## POSITIVE_NEGATIVE_EVIDENCE

Eager L01/L13 initialized target before after marker. Lazy L02/L05/L11/L15 did not initialize without access. L03/L04/L06/L07/L09/L10 materialized on use; L08 ordered other before target according to first use. L14/L16/L18/L19/L20 deferred via configuration. Eager L23 loaded target before later lazy binding. These are per-fixture outcomes, not universal cycle safety. Error delay, filter veto and indirect materialization remain unproven.

## PY310_PARITY

M8A stdlib-only base 3.10.9 probe: explicit lazy syntax rejected, ordinary import eager, AST dump lacked is_lazy. M8B did not rerun all 3.10 scenarios. Existing interpreter coverage gate unchanged; 3.11–3.14 NOT_COVERED.

## MCP_CONSUMER_MATRIX

Potential tools named in task: analyze_project/layer/single_file feed analysis; get_project_architecture/module_context/file_edit_context/blast_radius/get_live_events/get_analysis_status read projections; update_file can mutate canonical state. Direct lazy-sensitive call path and exact warning field per tool are NOT_PROVED in this stage. No mutation tool invoked. Do not claim direct consumer impact from registration alone.

## DESKTOP_WARNING_IMPACT

`cycle_warning_projection.py:24` partitions structural paths versus verified installed partial MODEL_PASS paths; `partial_warning_eligibility.py:19` requires exact generation/state/graph/claim/authority identity. A false model HAZARD can remain an active warning if installed; local model mismatch is proven, installation for synthetic fixture is not. Desktop scan summary/presentation exact path remains untraced.

## LIVE_WARNING_IMPACT

`core/live_state/ipc.py:910,925,2936,2940` exposes locked warning projection/transitions. Eligibility is fail-closed on missing/foreign receipts. No LIVE mutation or warning transition was induced. Whether lazy evidence changes generation/source binding remains unresolved.

## AST_FINGERPRINT_DEPENDENCIES

F02 interacts: `cycle_semantics/evidence.py:563-564` hashes ast.dump with attributes; CPython 3.15 includes is_lazy=0/1. Source fingerprint follows raw bytes. Worker binding validates AST/source claim. Any F01 change to serialized evidence could affect receipts/claims; mixed-version persistence not audited. No fingerprint redesign proposed.

## STATIC_PROOF_LIMITS

UNKNOWN/INCONCLUSIVE required when global mode, dynamic __lazy_modules__, filter, sys.modules, first use, external access, alias mutation, import hooks or module __getattr__ cannot be established. ast.is_lazy=1 proves syntax marker, not actual deferred execution if mode none/filter veto. ast.is_lazy=0 does not prove eager under all/__lazy_modules__.

## IMPLEMENTATION_SEAMS

Evidence seams, not design: lexical AST capture (is_lazy lost), ImportRef and provenance (no field), graph (frozen hard-edge compatibility), execution context (scope only), binding order (lexical), restricted model admission (3.10 subset accepts lazy AST), package/namespace (unverified), claim/fingerprint (version bound), installed warning eligibility (MODEL_PASS), Desktop/MCP projections (untraced). Multiple coordinated boundaries are implicated; no one-line fix is authorized.

## EXISTING_TEST_COVERAGE

Exact nodes: `tests/test_cycle_semantics_namespace_cycle_parity.py::test_lazy_import_syntax_before_315`, `::test_315_lazy_import_defers_cycle`, `::test_315_eager_import_still_has_hazard` cover interpreter behavior, not Contextor projections. `tests/test_cycle_semantics_initialization_model.py::test_from_import_hazard` and `::test_unsupported_fail_closed` cover eager/restricted behavior. `tests/test_cycle_semantics_execution_context.py::test_module_and_class_import_candidates_not_certified_safe`; `tests/test_cycle_semantics_provenance.py::test_individual_statements_and_aliases`; `tests/test_cycle_semantics_cycle_warning_projection.py::test_t04_t05_t06_absent_partial_receipt_keeps_all_warnings` cover neighboring contracts. For each L01-L40, dedicated Contextor lazy end-to-end coverage NOT_COVERED; L01/L13 have partial eager baseline coverage. No test was run.

## MISSING_REGRESSION_CASES

At minimum: explicit lazy ImportRef/provenance retention, mode normal/all/none and __lazy_modules__ literal/dynamic/filter veto, first-use order, compile rejection after ast.parse, restricted flat model fail-closed versus lazy semantics, package/namespace/relative/reexport, source-bound claim/publication and warning eligibility, affected MCP response/desktop views. L12/L17/L21/L24/L25-L40 need direct synthetic evidence before implementation planning.

## PRODUCTION_POSTCHECK

Windows process identity refresh: backend PID 2900, Desktop 6172, LIVE 13924 unchanged, actual executable `C:\Python315\python.exe`; commands match canonical venv. HEAD unchanged; worktree only `M walkthrough.md`. Last sampled module context fresh. Authenticated backend/lease/generation full postcheck not repeated, so that portion is UNKNOWN. No production process created/terminated; external bounded subprocesses exited.

## FILES_CHANGED

Inside production repository: `walkthrough.md` only. External fixtures/probes/results under `C:\Temp\Contextor_PY315_M2_Lab\M8B_lazy_discovery`.

## FULL_DIFFS

ACTUAL_DIFF=DIFFS=NONE for production source/test/docs; report's own diff excluded.

## REMAINING_UNKNOWN

L12, L17, L21, L24 and L25-L40 direct runtime/contextor outcomes; exact complete call graph to all MCP/desktop/LIVE warning surfaces; full package/namespace behavior; filter/none/environment/indirect materialization/error timing; full syntax diagnostics admission; authenticated/lease postcheck. Therefore implementation-ready gate is not met.

## FINAL_VERDICT

**DISCOVERY_PARTIAL_F01_EXACT_GAPS**. Confirmed representation loss and a tested restricted-model mismatch, with production source unchanged. Complete mechanism, consumer and 40-case coverage evidence remains outstanding. STOP.
