STATUS=DISCOVERY_COMPLETE

CONTEXTOR_EVIDENCE=
- HEAD is e24f99fbfcf730e967304b2f371c8e7f9681d782; the requested discovery made no production/test edits.
- ACTIVE-pool inspection found all Contextor tools needed: get_mcp_documentation, get_file_edit_context, get_source_range, search_source, get_symbol_implementation. Deferred-pool inspection was also performed before capability selection: no deferred Contextor capability was advertised; the only deferred-related active description was update_file, which is mutating and out of scope.
- Current MCP docs were read before discovery calls. Fresh edit contexts: production module 351/1 and tests module 352/1, canonical revision 520, provenance live, workspace_sync verified, syntax checked_and_none.
- Canonical source evidence: lineage_extraction.py 195-290 provides frame helpers; 480-635 provides Call/comprehension/NamedExpr; 675-900 provides 1C.4 conditional, loop, match, try, and handler frame invalidation. Tests 130-260 establish current call fallback assertions.

EXISTING_FRAME_MERGE_REUSE=
- Reuse is sufficient; no parallel frame model is warranted.
- _clone_frame(owner) snapshots a mapping. _replace_frame(owner, frame) atomically replaces it. _merge_frames(frames) retains a name only when it exists in every frame and points to the identical occurrence reference.
- 1C.4 already applies this exact mechanism to If body/else, For zero/body/else, While zero/body/else, Match branches, and Try reachable paths. Its known fail-closed result for diverging binding authority is absent frame entry, hence a later simple Name is UNRESOLVED rather than speculative DYNAMIC.
- Comprehension must use the same zero/body merge on the effective walrus owner. It must not merge its local target frame into the lexical enclosing frame.

CORRECTED_ACTIVE_COMPREHENSION_STATE=
- Each active record must distinguish:
  lookup_owner: comprehension anchor id;
  lexical_enclosing_owner: owner that supplies visible outer bindings/imports and evaluates outermost iterable;
  effective_walrus_owner: nearest propagated non-comprehension owner;
  walrus_entry_frame: clone of effective_walrus_owner at this comprehension entry;
  touched_walrus_names: set of names assigned by a NamedExpr during this comprehension or any currently executing nested descendant.
- At enter, lookup_owner frame is a clone of lexical_enclosing_owner frame; its import frame is copied from lexical_enclosing_owner import frame. Then runtime targets overwrite only lookup_owner entries.
- This permits enclosing reads/import calls, preserves target shadowing, and does not create synchronization anchors/flows.
- The old pair (comprehension_id, enclosing_owner) is insufficient: inner lexical_enclosing_owner can be outer comprehension while effective_walrus_owner remains the containing function.

CORRECTED_WALRUS_LIFECYCLE=
1. NamedExpr evaluates RHS first in the current lookup owner.
2. It assigns its target to effective_walrus_owner through existing assign_target, yielding one existing binding anchor and one existing ASSIGNS flow.
3. While executing, write that returned binding into lookup frames of every active record whose effective_walrus_owner is the same owner; record name as touched in those records. This includes the current inner record and outer active records sharing the containing owner.
4. On ending an inner comprehension, merge its walrus_entry_frame with the current effective owner body frame. Synchronize only its touched names in still-active matching records: set each to merged binding if present, otherwise remove it. Do not overwrite runtime targets or unrelated lookup entries.
5. On ending outer comprehension, do the same merge. Its zero path is walrus_entry_frame; its body path is effective owner state after all nested children completed their own conservative merges.
- Thus a walrus is visible within a body path that executed it, but is not definite after any possibly-zero comprehension.

NESTED_COMPREHENSION_ALGORITHM=
- Create comprehension_id.
- First iterable: visit with lexical_enclosing_owner and inherited effective walrus owner. It is outside comprehension scope.
- effective_walrus_owner = incoming walrus_owner or lexical_enclosing_owner.
- Push active record using both owners and snapshot effective owner's frame before any body evaluation.
- Clone lexical enclosing binding/import frames into comprehension lookup frame; runtime-bind first target; visit filters. For later generators visit iterable, bind target, then filters. Finally visit elt, or key then value.
- A nested comprehension uses outer comprehension as lexical_enclosing_owner, but receives its parent effective_walrus_owner. Its frame therefore sees outer targets while its NamedExpr writes/mirrors against the containing function/module.
- finally: pop record only after its effective owner zero/body merge and touched-name synchronization. Never special-case a no-generator comprehension: parsed comprehension has at least one generator.

POST_COMPREHENSION_MERGE=
- Algorithm: body_frame = clone_frame(effective_walrus_owner); merged = merge_frames((record.walrus_entry_frame, body_frame)); replace_frame(effective_walrus_owner, merged).
- For A, no prior y versus body y binding: merged has no y; use(y) produces no exact BIND and Call use receives its normal unresolved argument lookup.
- For B, y=old versus y=walrus binding: merged has no y; later y does not exact-bind to old or walrus.
- For C, y is mirrored after its NamedExpr, so second y sees the walrus binding during the same executed body path. After exit y is non-definite.
- For D/E, z is mirrored into inner lookup despite lexical enclosing owner=outer comprehension. Inner completion immediately merges inner zero/body and removes z from outer active lookup when non-definite; outer completion remains conservative.
- For F, a local callable/import binding versus walrus rebind differ, so merge removes the name. Later direct call has callee_ref None; existing Call fallback is UNRESOLVED_NAME, confidence UNRESOLVED, dynamic_boundary None. It must be neither CALL_EXACT nor IMPORT_EXACT nor speculative DYNAMIC_RUNTIME_BOUNDARY.

EXACT_CODE_INSERTION_POINTS=
- lineage_extraction.py 195-209: add active-record state.
- 246-286: add narrow lifecycle/synchronization helpers next to existing frame helpers.
- 510-528: replace comprehension visitor only.
- 555-566: return created binding from assign_target, otherwise None.
- 626-629: after assignment, synchronize returned NamedExpr binding to active records.
- tests/analysis/test_lineage_extraction.py: append 1C.7 focused tests after 1C.6 group; retain existing helpers for exact binds and call-result flows.

LITERAL_IMPLEMENTATION_PLAN=
1. Define private record:
   _ActiveComprehension(lookup_owner: str, lexical_enclosing_owner: str | None, effective_walrus_owner: str | None, walrus_entry_frame: dict[str, ExtractedOccurrenceRef], touched_walrus_names: set[str]).
   Store list self._active_comprehensions.
2. Add begin_comprehension(comprehension_id, lexical_enclosing_owner, effective_walrus_owner):
   entry = clone_frame(effective_walrus_owner);
   replace_frame(comprehension_id, clone_frame(lexical_enclosing_owner));
   import_frame(comprehension_id).clear(); import_frame(comprehension_id).update(import_frame(lexical_enclosing_owner));
   append record.
3. Change assign_target signature to return ExtractedOccurrenceRef | None. Preserve its existing anchor/flow behavior exactly.
4. Add publish_executed_walrus(name, binding, effective_walrus_owner):
   for record in active records with matching effective owner:
     record.touched_walrus_names.add(name);
     frame(record.lookup_owner)[name] = binding.
   NamedExpr calls it only after successful assign_target.
5. Add finish_comprehension(record):
   body = clone_frame(record.effective_walrus_owner);
   merged = merge_frames((record.walrus_entry_frame, body));
   replace_frame(record.effective_walrus_owner, merged);
   remove record from active stack;
   for each still-active matching record and each name in finished.touched_walrus_names:
     add name to parent touched set;
     if name in merged: frame(parent.lookup_owner)[name] = merged[name]
     else: frame(parent.lookup_owner).pop(name, None).
6. Comprehension visitor:
   add anchor; first.iter with lexical enclosing owner; effective owner = walrus_owner or owner; begin;
   try runtime_bind target and visit filters; repeat later iter/target/filter; visit values;
   finally finish.
   Keep runtime target helper separate from normal Store visit and preserve DictComp key,value order.

CORRECTED_TEST_PLAN=
- A: [(y := x) for x in xs]; use(y). Assert y inside assignment has containing owner, but post-comprehension y has no LEXICAL_EXACT BIND.
- B: y=old; [(y := x) for x in xs]; use(y). Assert post y has neither old nor walrus binding as exact source.
- C: [(y := x, y) for x in xs]. Assert second y exactly binds walrus binding within body; post y non-definite.
- D: [[((z := y), z) for y in ys] for x in xs]. Assert inner second z binds current z; post z has no exact BIND.
- E: same nested source plus owner assertions: z binding owner is containing function/module, never outer/inner comprehension; inner lookup sees z.
- F-local: def run; [(run := other) for x in xs]; run(). Assert later CALL_RESULT is UNRESOLVED_NAME/UNRESOLVED/no dynamic boundary; not CALL_EXACT.
- F-import: from pkg import run; [(run := other) for x in xs]; run(). Same UNRESOLVED fallback; not IMPORT_EXACT.
- Retain and correct prior 9-11: element/filter/nested walrus each have separate inside-executed-path visibility and after-comprehension non-definiteness assertions.
- Retain 12-13 only with corrected fallback UNRESOLVED, not dynamic.
- Retain target shadowing, outer iterable enclosing lookup, later generator/filter visibility, nested target isolation, Dict key-before-value, four comprehension forms, parser SyntaxError for iterable NamedExpr, unique flow IDs/no double traversal, and Stage 1C.1-1C.6 regression matrix.

DOMAIN_CHANGE_REQUIRED=NO
FILES_CHANGED=NONE
DIFFS=NONE
