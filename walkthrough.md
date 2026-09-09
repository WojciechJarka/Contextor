PARAMETER_LOCAL_ID_CONTRACT=
Keep anchor kind `parameter`; local-ID kind encodes `parameter_posonly`/`parameter_poskw` with callable-local ordinal, `parameter_kwonly` with escaped name, and `parameter_vararg`/`parameter_varkw` collector kind. `ExtractedSymbolicRef(PARAMETER,module_name,callable_symbol_name,parameter_local_id)` identifies callable and parameter metadata without AST.

DOMAIN_CHANGE_REQUIRED=NO — existing structured SymbolicRef/source_local_id and Stage 1A slot builders suffice.

PARAMETER_FLOW=
PARAMETER symbolic -> parameter local occurrence is BINDS/SIGNATURE_EXACT/CONFIRMED. Default expression-result -> PARAMETER symbolic is DEFAULTS_TO_PARAMETER/SIGNATURE_EXACT/CONFIRMED. Actual call argument -> PARAMETER symbolic is ARGUMENT_TO_PARAMETER only for exact local signature and exact non-star actual binding.

CALL_RESULT_FLOW=
Local exact: RETURN symbolic `(current_module,callable_symbol_name,function_anchor_id)` -> call-result, CALL_RESULT/CALL_EXACT/CONFIRMED. Import exact: RETURN symbolic `(target_module,target_symbol,import_binding_id)` -> call-result, IMPORT_EXACT/CONFIRMED. Unresolved/dynamic: call-site -> call-result with UNRESOLVED_NAME/UNRESOLVED or DYNAMIC_RUNTIME_BOUNDARY/DYNAMIC; no RETURN symbolic target.

STAR_DSTAR_POLICY=
Normal positional maps to exact posonly/poskw and deterministic excess vararg; explicit keyword maps fixed poskw/kwonly or unmatched varkw. `*expr`/`**expr` produce zero ARGUMENT_TO_PARAMETER in v1 absent fully proven literal expansion.

LEXICAL_FRAME_MODEL=
Use only definite current-frame parameters, prior unconditional local assignments, defs, and imports. No enclosing/global/nonlocal/closure/class/MRO lookup. Missing/ambiguous is unresolved.

CONTROL_FLOW_INVALIDATION_MODEL=
Clone frame per if/loop/try/match branch; collect touched names; remove touched names on merge unless all reachable paths define identical occurrence. Branch-local use can be exact; post-branch conflicting or conditional definitions are unresolved. Loop body touches invalidate on exit. No CFG.

ASSIGNMENT_BOUNDARY_MODEL=
Name assignment, valued AnnAssign, walrus: expression-result -> binding ASSIGNS. Annotation-only: no runtime flow. AugAssign requires prior proven local plus RHS; otherwise no single-source overwrite. for/with/except use runtime-bound-local occurrence without invented iterable/context/exception producer. Attribute/Subscript deferred.

MINIMAL_OCCURRENCE_KINDS=
`expression_result`, `name_load`, `call_site`, `call_argument`, `call_result`, `runtime_bound_local`; existing binding and typed parameter IDs remain anchors.

IMPORT_EXACT_RULES=
Only same-traversal proven `from m import f as x; x()` and direct `import m; m.f()` are IMPORT_EXACT. self/cls/obj dispatch is not exact. Relative import only if source-key/package-level arithmetic resolves it without repo lookup; otherwise unresolved.

FAILURE_MODEL=
Node/depth breach => empty RESOURCE_LIMIT. Duplicate/invariant/metadata impossible state => extraction exception, never RESOURCE_LIMIT. Unsupported constructs => bounded omission or unresolved/dynamic fact.

CORRECTED_EXACT_FILES=
contextor/core/analysis/lineage_extraction.py
tests/analysis/test_lineage_extraction.py

CORRECTED_EXACT_SYMBOLS=
Extend `_ANCHOR_KINDS`, local-ID builder/parser, `_AnchorExtractor` with same-pass frame/flow collector, and `extract_lineage_source_facts`; no lifecycle/domain change.

CORRECTED_FOCUSED_TESTS=
All parameter IDs and BINDS/defaults; exact/unresolved call-result direction; normal/star arguments; local/import/method targets; branch invalidation; assignment boundaries; relative import; async/bare return; resource versus invariant failure; no deferred-family leakage.

READY_FOR_CONCRETE_STAGE_1C_PATCH=YES — only extractor and focused tests change; semantic identity remains 1F.

FILES_CHANGED=NONE
TESTS_RUN=NONE
DIFFS=NONE
