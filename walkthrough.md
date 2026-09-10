STATUS=BLOCKED

STAGE=1D.1 exact lexical closure-cell CAPTURES implementation
BASE=90409963f571fcb94782f7a7b7cf9d5cd2b0cfc5

IMPLEMENTATION_RESULT=
- Added deferred capture requests and one finalization after the existing single AST traversal. Finalization resolves only a lexical enclosing function/async-function/lambda cell; module ends resolution, class is transparent, and a comprehension is a same-name barrier.
- Declared-local tracking covers stores, deletes, assignment targets, runtime targets, parameters, imports, function/class declarations, exception aliases, and match captures. global/nonlocal remain blocked and are excluded from local declarations.
- CAPTURES emits an existing-occurrence endpoint pair: a cached synthetic `closure_cell` anchor owned by the lexical scope and the original `name_load`; relation=CAPTURES, resolution=LEXICAL_EXACT, confidence=CONFIRMED.
- The one-line contracts addition admits `closure_cell` as a local-ID kind. It preserves the v1 local-ID grammar and is required because add_anchor validates every `local_kind` against that existing allowlist.

TEST_EVIDENCE=
- `& '.\\.venv\\Scripts\\python.exe' -m pytest tests/analysis/test_lineage_extraction.py -q` => PASS, 113 passed in 2.41s.
- `& '.\\.venv\\Scripts\\python.exe' -m pytest tests/analysis/test_lineage_extraction_equivalence.py -q` => PASS, 2 passed in 0.85s; expected corpus hash was not edited.
- Required combined command => BLOCKED before test collection: `tests/analysis/test_lineage_extraction_binding_resolution.py` does not exist. `rg --files tests/analysis | rg 'lineage_extraction.*(binding|validation)'` returned no matching file. No substitute test path was assumed.
- `git diff --check BASE -- <changed production/test files>` => PASS; only CRLF conversion warnings, no whitespace errors.

LIVE_CERTIFICATION=
- Pre-edit canonical revision 556: fresh, resync_required=false.
- Post-edit watcher journal is continuous through revision 566, resync_required=false. It records desktop_watcher UPDATED events for the changed extraction modules; syntax diagnostics have zero errors and fresh availability.
- Post-edit minimal contexts at revision 566 for every changed production module report warnings=[], syntax_diagnostics=checked_and_none/fresh, and no diagnostic attention required.

CHANGED_FILES=
- contextor/core/analysis/lineage_extraction.py
- contextor/core/analysis/lineage_extraction_bindings.py
- contextor/core/analysis/lineage_extraction_calls.py
- contextor/core/analysis/lineage_extraction_comprehensions.py
- contextor/core/analysis/lineage_extraction_control.py
- contextor/core/analysis/lineage_extraction_contracts.py
- contextor/core/analysis/lineage_extraction_state.py
- contextor/core/analysis/lineage_extraction_visitors.py
- tests/analysis/test_lineage_extraction.py

FULL_UNIFIED_DIFF_COMMAND=
`git diff --no-ext-diff --unified=3 90409963f571fcb94782f7a7b7cf9d5cd2b0cfc5 -- contextor/core/analysis/lineage_extraction.py contextor/core/analysis/lineage_extraction_bindings.py contextor/core/analysis/lineage_extraction_calls.py contextor/core/analysis/lineage_extraction_comprehensions.py contextor/core/analysis/lineage_extraction_control.py contextor/core/analysis/lineage_extraction_contracts.py contextor/core/analysis/lineage_extraction_state.py contextor/core/analysis/lineage_extraction_visitors.py tests/analysis/test_lineage_extraction.py`

CAPTURES_SEMANTIC_CONTRACT=
- CAPTURES identifies a lexical cell (enclosing function/async-function/lambda owner, name), never a particular ASSIGNS/BINDS occurrence or current value.
- The source is stable when the cell has sequential/conditional writes. Existing ASSIGNS, BINDS, control frames, and later value-provenance stages remain the sole representation of concrete writes/reads.
- Compile-time local declaration in the requesting function/lambda prevents ancestor capture regardless source order. Module scope is terminal; class scope is transparent for methods.

MATERIALIZER_ENDPOINT_SUPPORT=
- Extracted flow endpoints allow only ExtractedOccurrenceRef or ExtractedSymbolicRef; extracted anchors use free-form kind:str and a source-local ID. A synthetic source-local anchor/reference therefore fits the extracted contract unchanged.
- Materialized flow/anchor endpoints allow MaterializedOccurrenceRef or SemanticEndpoint; a same-slice occurrence is explicitly canonical. Its local ID is preserved under the source manifest. Live-store revalidation validates endpoint types, source-slice membership, relation/resolution/confidence, and provider, not an anchor-kind allowlist.
- Current production has extraction transport (indexer, PreparedSourceUpdate) and typed state fields (lineage_facts_by_source), but no discovered producer converting extracted lineage to materialized lineage. Existing persistence supports generic materialized occurrence anchors when that phase is activated; 1D.1 remains extraction-only.

CANDIDATE_1=
REJECT. ExtractedSymbolicKind.STATE has no named function-local-cell producer or materializer. It contains only kind,module_name,symbol_name,source_local_id; tests explicitly establish no persistent owner identity. Reusing it would overload state semantics and cannot distinguish lexical owner+name safely.

CANDIDATE_2=
ACCEPT. Add one synthetic extracted anchor with kind=closure_cell and deterministic local kind=closure_cell, built from the lexical owner's defining AST path plus variable name. The anchor is owned by the enclosing function/lambda anchor and its source span is that owner's defining node. State caches (owner_id,name) to ExtractedOccurrenceRef; it is created only when finalization proves that exact cell is captured.

CANDIDATE_3=
REJECT FOR 1D.1. A new symbolic kind or SemanticSlotKind would require domain parser/validator/builders, materializer, persistence validation, semantic-version migration, and tests. Candidate 2 already preserves owner+name without semantic overloading and uses current source-slice endpoint rules.

SELECTED_ENDPOINT_MODEL=
- CAPTURES source: ExtractedOccurrenceRef with deterministic closure_cell local ID, referring to an ExtractedAnchorFact(kind=closure_cell, owner_local_id=outer function/lambda anchor).
- Identity is the anchor's owner_local_id plus local-ID name component: lexical outer::x; it is neither x=1 nor x=2.
- CAPTURES target: the existing original inner name_load ExtractedOccurrenceRef; evidence is the inner Name.Load span; relation=CAPTURES; resolution=LEXICAL_EXACT; confidence=CONFIRMED.
- The generated cell anchor is source-local and revision-local, just like all extracted anchors. If/when materialized, it becomes the same-slice MaterializedOccurrenceRef, not a cross-source semantic endpoint.

REQUIRED_CASE_RESULTS=
A. Source=one closure_cell(outer,x), target=inner x load. Exactly one CAPTURES; x=1 and x=2 retain ordinary assignment/bind provenance only.
B. Same exact source closure_cell(outer,x) and target despite conditional x=2. Conditional frame merge may make value provenance ambiguous but cannot remove lexical cell identity.
C. Same exact closure_cell(outer,x) although x declaration is visited after inner. Deferred request finalization sees the complete declaration set.
D. No CAPTURES. Inner's later x assignment places x in declared_locals[inner], so its earlier load cannot request/resolve outer x.
E. Source=closure_cell(outer,x), target=method x load. Class C.x is skipped and is never source identity.
F. No CAPTURES. Owner walk reaches module and terminates; existing module/global semantics remain unchanged.

CORRECTED_FINALIZATION=
1. register_owner(owner_id,parent_id,kind,scope_node) records parent, kind, and defining node. State retains owner-parent, owner-kind, owner-nodes, declared-locals, lexical-cells, and capture-requests.
2. Every local-declaration producer calls declare_local(owner,name) independently of bindings and frame merge. Existing global/nonlocal only retain blocked-name behavior; they do not create a local cell.
3. visit_name preserves current immediate local BINDS behavior. For an eligible function/async/lambda Name.Load with no current local resolution, it stores CaptureRequest(load_ref,node,request_owner,name); it does not select a concrete binding.
4. After sole visit(tree), finalize_captures(state,paths) processes requests. Reject if requesting scope is blocked or declares name. Walk owner parents: skip class; for a comprehension that declares name, stop, otherwise skip; at an enclosing function/async/lambda, blocked means stop and declared local means select lexical cell; module/None means stop.
5. ensure_lexical_cell(state,paths,owner,name) gets registered owner AST node, calls existing add_anchor with kind closure_cell and owner, caches ExtractedOccurrenceRef, and finalizer emits CAPTURES to saved load ref.
6. No final bindings lookup participates in cell selection. It continues independently for value provenance only. This is one traversal plus state-only post-finalization; no secondary AST traversal/walk/visitor/source read.

FILES_AND_SYMBOLS=
- contextor/core/analysis/lineage_extraction_state.py: CaptureRequest; owner/declaration/cell/request fields and registration/query methods.
- contextor/core/analysis/lineage_extraction_bindings.py: visit_name, assign_target, runtime_bind_target, visit_aug_assign; declaration recording and finalize_captures / ensure_lexical_cell.
- contextor/core/analysis/lineage_extraction_calls.py: parameter_anchors, register_import_binding declaration registration.
- contextor/core/analysis/lineage_extraction_visitors.py: visit_module, visit_class_def, visit_function, visit_lambda owner registration; definition-name declaration in parent.
- contextor/core/analysis/lineage_extraction_control.py: except-alias and MatchAs/MatchStar/MatchMapping declaration registration.
- contextor/core/analysis/lineage_extraction.py: only AnchorExtractor.extract, invoking finalizer after existing visit.
- tests/analysis/test_lineage_extraction.py: 1D.1 endpoint/semantic behavior matrix.
- No change: lineage_extraction_emit.py, lineage_facts.py, materialized domain contracts, live store, state manager, query APIs, IDs outside synthetic extracted local kind.

TEST_MATRIX=
- A: assert one closure_cell anchor owned by outer; CAPTURES source equals it, not either assignment binding; unchanged ASSIGNS remain separately present.
- B: assert same cell CAPTURES through branch rebind; assert no source assignment identity is used.
- C: late declaration capture.
- D: local-before/after assignment, AnnAssign-without-value, AugAssign, parameter, import, for/with/except/match and nested definition/class shadow cases: no ancestor CAPTURES.
- E: class transparency plus class x shadow; lambda/function through a class; no class-cell anchor.
- F: module/global terminal plus existing global/nonlocal freeze.
- Comprehension target barrier and walrus target owner; ensure no fabricated outer capture.
- Determinism/equivalence: fixed cell IDs/anchor count and immutable equivalence output; existing resource-limit behavior unchanged.

VERSION_SCHEMA_IMPACT=
- Extraction schema: no domain dataclass, enum, ID grammar, relation, semantic-slot, materializer, persistence, or public API change. closure_cell is a new value in existing free string ExtractedAnchorFact.kind, paired with existing occurrence ref.
- LINEAGE_FACTS_SEMANTIC_VERSION remains unchanged. Do not claim materialized persistence certification until a separate materializer exists and is exercised.

RISKS_AND_BANS=
- Never emit CAPTURES from an assignment/binding anchor or consult final frame authority for lexical-cell identity.
- Never overload STATE, MODULE_GLOBAL, CLASS_ATTRIBUTE, PARAMETER_VALUE, or semantic slots.
- Do not create cells for module/class/comprehension source authority in 1D.1; class is transparent, comprehension may only be a barrier.
- No second AST traversal, AST node visitor, compatibility path, query-time analysis, schema/version bump, test/oracle regeneration, commit, or push.

DIFFS=NONE
