STATUS=FINAL_PASS

REQUIRED_CASE_RESULTS=
1. `outer -> inner: return x; x=1`: one CAPTURES flow from the final `outer.x` binding occurrence to the inner `x` name-load; LEXICAL_EXACT/CONFIRMED. The request is queued while visiting inner and finalized only after outer completes.
2. `x=1; inner; x=2`: one CAPTURES flow from the final unconditional `x=2` occurrence, never the stale `x=1` occurrence.
3. `x=1; inner; if flag: x=2`: no CAPTURES flow. Current control merge removes x because possible paths have different occurrences; finalizer must not fall back to x=1.
4. `inner: value=x; x=2`: no CAPTURES flow for the first x. The later assignment declares x local for the whole inner function, even though it is encountered after the load.
5. `outer.x=1; class C: x=2; method: return x`: CAPTURES from outer.x, not C.x. The class owner is transparent for methods.
6. module `x=1; outer -> inner: return x`: no CAPTURES. The owner walk stops before module scope; current unresolved/global behavior is unchanged.

CLASS_SCOPE_RULE=
- Owner metadata records kind: module, class, function, async_function, lambda, comprehension.
- For a function/lambda request, class ancestors are transparent: neither their frames nor their declaration sets are candidate/blocked authority. This implements Python method lookup semantics.
- Comprehension ancestors are not candidate authorities in 1D.1. A declaration of the queried name in an intervening comprehension is a barrier (prevents a false jump to an outer function); otherwise it may be skipped to continue to a function/lambda ancestor. This preserves the 1D.1 source restriction while not fabricating an outer capture.
- Module is a hard terminal: it is never candidate capture authority. Global/nonlocal blocked names remain terminal exclusions exactly as today.

LOCAL_DECLARATION_MODEL=
- Add `_owner_parent: dict[str, str | None]`, `_owner_kind: dict[str, str]`, and `_declared_locals: dict[str, set[str]]` to the one LineageExtractionState. Owner and declaration data are transient extraction state only.
- `register_owner(owner_id, parent_owner, kind)` runs immediately after every scope anchor. `declare_local(owner, name)` is idempotent and is independent of `_bindings`, blocked names, and frame merge.
- A capture request is eligible only for a Name.Load in function/async-function/lambda owner, when name is neither a parameter/current local declaration nor current global/nonlocal blocked name. Crucially, finalization tests `_declared_locals[request.owner]`, not final frame contents.
- Function/class definition names are declared in their enclosing owner; parameters are declarations in the new function/lambda owner. Annotation-only assignment and AugAssign declare names even when they never become final frame authority.

CAPTURE_REQUEST_MODEL=
- Add frozen private `_CaptureRequest(load: ExtractedOccurrenceRef, load_node: ast.Name, request_owner: str, name: str)`; append to `state._capture_requests`.
- Change `visit_name` only as follows: retain existing Store behavior and existing current-frame BINDS emission. For an eligible Load that has no current-frame authority, call `state.request_capture(...)`; do not traverse ancestors and do not emit CAPTURES there.
- Do not enqueue request when current owner declares the name (including a declaration encountered later by the time of finalization), or when it is blocked. The fast path may enqueue before later declaration is known; finalizer is authoritative.

FINALIZATION_MODEL=
- Canonical semantic owner: `LineageExtractionState.finalize_capture_requests(paths)`. State owns scope facts/requests; a small bindings helper (for example `finalize_captures(state, paths)`) owns CAPTURES emission. Facade invokes this one helper after `self._visit(tree, None, None)` and before sorting in `_AnchorExtractor.extract`; facade remains dynamic-dispatch owner only.
- For each request, finalizer first rejects a blocked or declared-local request owner. It walks `_owner_parent`:
  1. class: skip unconditionally;
  2. comprehension: stop only if that scope declares the name, else skip;
  3. function/async_function/lambda: if blocked or declared-local without final current authority, stop; if final `state.frame(owner)[name]` exists, select it and stop; otherwise continue;
  4. module/None: stop without candidate.
- Emit CAPTURES only for the single selected final occurrence with LEXICAL_EXACT/CONFIRMED. Use the request's original Name node for source span/flow ID and the cached load occurrence as target. No dynamic or unresolved CAPTURES facts are added.
- This is one AST traversal plus an O(requests × ancestor depth) finalization over accumulated state; no AST walk, visitor, source reread, or query-time analysis occurs.

SOURCE_OCCURRENCE_SOUNDNESS=
- An existing concrete binding occurrence is safe only under this conservative final-scope rule: exactly one final frame occurrence in the first eligible enclosing function/lambda; no nearer local declaration, blocked declaration, comprehension barrier, or control-flow ambiguity.
- The final frame preserves latest unconditional authority (case 2) and removes divergent conditional authority (case 3). Thus no stale earlier occurrence can be selected.
- This does not claim runtime call-time value flow; it is a source-local lexical-cell approximation. If the existing control semantics cannot choose one occurrence, it emits no CAPTURES fact. No schema/ID/relation change is required.

DECLARATION_PRODUCERS=
- Parameters: `lineage_extraction_calls.parameter_anchors` -> declare each parameter in function/lambda owner.
- Assign / non-value AnnAssign / NamedExpr: `lineage_extraction_bindings.assign_target`; declare every Name target recursively. For NamedExpr, declare `target_owner = walrus_owner or owner`.
- AugAssign: `visit_aug_assign`; declare Name target even when prior authority is absent.
- Definition declarations: `lineage_extraction_visitors.visit_function` and `visit_class_def`; declare node.name in parent owner before traversing its body. Lambda has no enclosing name declaration.
- Imports: `lineage_extraction_calls.register_import_binding`; declare local_name even if blocked/star semantics prevents frame authority.
- For/AsyncFor and With/AsyncWith targets: `runtime_bind_target`, recursively through Name, Tuple/List, Starred; owner passed by control/comprehension helper decides declaration scope.
- Except alias: `lineage_extraction_control.visit_except_handler`; declare alias even though it is removed from exit frame.
- Match names: `visit_match_as`, `visit_match_star`, `visit_match_mapping`; declare their respective names even though current implementation may only anchor them.
- Comprehension targets: same `runtime_bind_target` but owner is comprehension_id. They must not be declared in the outer function. Comprehension walrus target is instead declared by `assign_target` in effective_walrus_owner.
- Existing `visit_name(Store)` is only a fallback anchor path; it must call declaration recording when used, but cannot substitute for the above paths because `assign_target`/runtime/match paths often create anchors directly.

FILES_AND_SYMBOLS=
- Change `contextor/core/analysis/lineage_extraction_state.py`: private request dataclass; state fields/methods `register_owner`, `declare_local`, `request_capture`, final-scope resolver.
- Change `contextor/core/analysis/lineage_extraction_bindings.py`: `visit_name`, `assign_target`, `runtime_bind_target`, `visit_aug_assign`; add capture-finalization helper only.
- Change `contextor/core/analysis/lineage_extraction_calls.py`: `register_import_binding`, `parameter_anchors`.
- Change `contextor/core/analysis/lineage_extraction_visitors.py`: `visit_module`, `visit_class_def`, `visit_function`, `visit_lambda`.
- Change `contextor/core/analysis/lineage_extraction_control.py`: `visit_except_handler`, `visit_match_as`, `visit_match_star`, `visit_match_mapping`.
- Change `tests/analysis/test_lineage_extraction.py`: focused behavior-named 1D.1 matrix below.
- Minimal facade change: `contextor/core/analysis/lineage_extraction.py::_AnchorExtractor.extract` invokes finalization after its existing sole `_visit`.
- No change: `lineage_extraction_emit.py`, domain facts/schema/enums/IDs/version, control frame merge behavior, materialization, state manager, live store, MCP/query API, equivalence oracle.

EXACT_1D1_DESIGN=
1. Register scope owner kind/parent at anchor creation; never infer from anchor string later.
2. Record compile-time local declarations at every listed producer, regardless of branch execution, final frame membership, or whether a name is blocked.
3. Keep current immediate BINDS behavior unchanged. Enqueue only potential captures.
4. After traversal, resolve requests only against final canonical frames and declared-local metadata using the stated class/comprehension/module rules.
5. Emit CAPTURES from one selected existing occurrence to original load; sort using existing extractor output contract.

TEST_MATRIX=
- Positive: required cases 1, 2, and 5; assert CAPTURES source/target local IDs, LEXICAL_EXACT, CONFIRMED, evidence line.
- Negative: required cases 3, 4, 6; assert no CAPTURES; existing global/nonlocal no-capture behavior unchanged.
- Declarations: parameter shadow; Assign/AnnAssign-without-value/AugAssign; NamedExpr including comprehension walrus; nested def/class name; import; for/async-for; with/async-with; except alias; MatchAs/MatchStar/MatchMapping; tuple/starred targets.
- Scope boundaries: class transparent; comprehension target barrier; nested lambda/function capture through a transparent class; module stop.
- Stability: unconditional later rebind selects latest; branch/loop/try/match ambiguity emits no stale capture; deterministic extraction/equivalence remains intact.

RISKS_AND_BANS=
- Do not implement immediate parent lookup in visit_name; it is wrong for late enclosing bindings and inner declarations encountered later.
- Do not reuse final _bindings as localness; control merge and except cleanup erase required compile-time declaration facts.
- Do not make classes authorities or treat module globals/nonlocal as 1D.1 captures.
- No second AST traversal, ast.walk, NodeVisitor, secondary extractor, schema/semantic-version change, materialization/query work, test/oracle regeneration, commit, or push.

DIFFS=NONE
