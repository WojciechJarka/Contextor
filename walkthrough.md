# SP-T4-I2B4C — Incremental type_only evidence reclassification

## PREFLIGHT

- Repo: `C:/Temp/Contextor_Repo`.
- Contextor MCP preflight at canonical revision **1427**: canonical state fresh; target contexts for `indexer.py`, `preparation.py`, and `tests/test_p1d3_d2b2_type_only.py` reported `workspace_sync=verified`. `cycle_semantics` was stale.
- `get_project_architecture(fields=[])` reported 669 modules, syntax diagnostics 0/fresh, and `resync_required=false`.
- Read-only Git preflight: HEAD `0f353bbd6cf99d4629c182e09266f9b470109b87`; before edits only the already-modified `walkthrough.md` was in status. The requested new module did not exist.
- Canonical source anchors: `_classify_type_only_modules` in `contextor/core/symbol_engine/indexer.py:647-779`; `ImportRef` in `contextor/core/domain/imports.py:11-29`; existing target tests ended at T34.
- MCP lineage resolved `contextor.core.symbol_engine.indexer::_classify_type_only_modules` at revision 1427; implementation was complete and workspace-verified. The classifier computes the existing project-wide typing-shadow, marker-mutation, opaque-effect, skipped/unindexed, and parent-passivity gates.
- CPython interpreter used for syntax and focused tests: **3.15.2**.
- No FULL, SCC02, MCP `update_file`, restart, or Git write operation was performed.

## EXACT IMPLEMENTATION

Added `contextor/core/analysis/incremental/type_only_policy.py` (458 lines). `reclassify_incremental_type_only` is at line 211. It validates retained schema-v2 evidence, updates only the changed source facts, restores saved pre-finalization ImportRef candidates with independent `names` lists, invokes the existing `_classify_type_only_modules`, and returns a copy-on-write classification plus sorted updated evidence.

Appended T35-T48 to `tests/test_p1d3_d2b2_type_only.py:3322-3926`. The source diff contains additions only; there are no deletions or edits to T01-T34.

MCP’s post-change dependency projection reports the new helper’s imports as `domain.imports`, `symbol_engine.indexer`, and `domain.module`; its only static consumer is the target test module. This task does not wire the helper into the production incremental engine, so this result does not certify end-to-end incremental runtime adoption.

## SEMANTIC INTEGRITY CORRECTION

The supplied I2B4C corrections were applied literally:

- Baseline Module imports, persisted candidate ImportRefs, and changed ImportRefs require `type(ref.type_only) is bool`.
- Invalid current-module flags are sent to fail-closed handling.
- The fail-closed guard treats either a non-bool flag or a truthy flag as requiring normalization; it copies the Module and sets every ImportRef `type_only=False`.
- Unchanged modules must equal their previous versions before reclassification can proceed.
- Invalid Module import containers or records raise `TypeError` before flag inspection.
- Saved evidence is rejected when schema, source fingerprints, per-module records, candidate alignment, or candidate types are invalid.

The source contract for `ImportRef` is a frozen dataclass with a `type_only: bool` annotation, but annotations do not enforce runtime value types. The exact-type validation therefore checks a real runtime boundary. CPython 3.15.2 truthiness probe: `0` is falsey while `type(0) is not bool`; the corrected fail-closed guard includes the non-bool condition, so that value enters normalization instead of bypassing it.

## MALFORMED BOOL REGRESSIONS

- T45 exercises saved-candidate values `1`, `"true"`, and `0`.
- T46 exercises a malformed changed ImportRef with `type_only=1`.
- T47 exercises a malformed previous final ImportRef with `type_only=1`.
- T48 exercises unrelated-module tampering.

T45’s `0` case is in saved evidence; T46/T47 use truthy `1` values. The current-module falsey case is supported by the exact corrected code path described above, rather than directly exercised by a separate test in this allowed set. All requested focused test cases passed.

## EVIDENCE VALIDATION

- Baseline schema must be an exact `dict` with integer schema version 2 and all required fields.
- Fingerprint maps must cover exactly the baseline modules and use lowercase 64-character SHA-256 strings. Marker-mutation and opaque-effect maps must match those fingerprints; initializer-passivity entries are limited to initializer modules.
- Candidate records must be tuples of ImportRef objects aligned positionally with the final imports except for `type_only`, and each candidate module must contain at least one saved `True` candidate.
- Stored `global_policy_satisfied` is type-checked but not trusted as the outcome; the shared classifier recomputes it.
- For a changed source, its schema-v1 source facts and fingerprint update only the changed module’s maps. A successfully parsed path is removed from skipped paths. Deletion removes only that module’s evidence.
- Candidate ImportRefs are copied before the classifier runs; aliases are not reconstructed beyond fields represented by the existing ImportRef contract.

## FAIL-CLOSED CONTRACT

Missing or malformed evidence, legacy schema v1, bad fingerprints, mismatched candidates, invalid changed-source evidence, or changed unrelated modules return a copied module mapping, empty updated evidence, and no retained soft classification. Invalid current `type_only` values are normalized to literal `False`. Invalid module/import record structure raises `TypeError`. The implementation does not read files, parse AST, execute analyzed code, or build a graph.

## FULL PARITY

T35-T44 use actual synthetic FULL indexes as the baseline, call the helper directly, and compare the resulting ImportRefs and hard/soft graph edges against an independent fresh FULL of the final source tree. T36/T37 exercise adding/removing `typing.py`; T38/T39 exercise parent initializer activity/passivity; T40/T41 exercise project-wide marker mutation and opaque effects; T42 checks invalid evidence; T43 checks a corrected skipped file; T44 checks a benign change and input-copy behavior.

The parity tests pass for every selected scenario. Because no production incremental-engine caller is modified or added in this task, parity here is helper-vs-fresh-FULL evidence, not proof that an actual engine update invokes this helper.

## TARGETED TESTS

Syntax was checked by compiling both changed Python files in memory with CPython 3.15.2; neither file was executed by that syntax check.

Executed only the requested T22-T48 selection:

```text
.\.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider tests/test_p1d3_d2b2_type_only.py -k "t22 or t23 or t24 or t25 or t26 or t27 or t28 or t29 or t30 or t31 or t32 or t33 or t34 or t35 or t36 or t37 or t38 or t39 or t40 or t41 or t42 or t43 or t44 or t45 or t46 or t47 or t48"
34 passed, 249 deselected in 5.86s
```

## MCP POST-CHANGE AUDIT

- Canonical LIVE advanced from revision 1427 to **1430**; canonical state fresh; `resync_required=false`.
- Workspace-level aggregate is `unverified`; both changed targets are individually `verified` at revision 1430.
- New helper: module `670/1`, status available, syntax `checked_and_none`, module/graph/cycles fresh.
- Test module: module `550/1`, syntax `checked_and_none`, workspace verified.
- Syntax diagnostics: **0**, family fresh.
- Graph/topology/artifact-consumption/cycles families: fresh. Structural cycle diagnostic: **16** fresh paths. Soft-dependent potential-cycle diagnostic: **1** fresh component (`contextor.mcp.analysis_jobs`, `contextor.mcp.query_helpers`); it remains a potential-cycle signal, not runtime proof. `cycle_semantics` remains stale.
- `get_live_events(after_revision=1427)` returned continuous history with no resync requirement: revision 1428 was a `desktop_watcher` update for the new helper; 1429 and 1430 were `desktop_watcher` updates for the test module. The latest event reported deferred affected-module details, while the revision-1430 path-scoped reads independently confirmed both changed targets verified and syntax-fresh.
- No Contextor FULL or manual update was used.

## FINAL_VERDICT

**I2B4C_PASS** for the requested standalone evidence-reclassification helper, its fail-closed validation, and the focused helper-vs-FULL tests. This does not claim that the production incremental engine is already wired to call the helper.

## FILES_CHANGED

- `contextor/core/analysis/incremental/type_only_policy.py` — new.
- `tests/test_p1d3_d2b2_type_only.py` — appended T35-T48 only.
- `walkthrough.md` — overwritten with this report; its self-diff is omitted.

## FULL_DIFFS

### `contextor/core/analysis/incremental/type_only_policy.py`

```diff
diff --git a/contextor/core/analysis/incremental/type_only_policy.py b/contextor/core/analysis/incremental/type_only_policy.py
new file mode 100644
index 0000000..78521d7
--- /dev/null
+++ b/contextor/core/analysis/incremental/type_only_policy.py
@@ -0,0 +1,458 @@
+"""Pure reconciliation of retained type-only import evidence."""
+
+from dataclasses import replace
+import re
+
+from contextor.core.domain.imports import ImportRef
+from contextor.core.domain.module import Module
+from contextor.core.symbol_engine.indexer import (
+    _classify_type_only_modules,
+)
+
+
+def _copy_refs(refs):
+    return [
+        replace(ref, names=list(ref.names))
+        for ref in refs
+    ]
+
+
+def _valid_fingerprint(value):
+    return (
+        type(value) is str
+        and re.fullmatch(r"[0-9a-f]{64}", value) is not None
+    )
+
+
+def _valid_record_map(records, fingerprints, required):
+    if type(records) is not dict or set(records) != required:
+        return False
+
+    return all(
+        type(record) is tuple
+        and len(record) == 2
+        and type(record[0]) is bool
+        and record[1] == fingerprints[module_id]
+        for module_id, record in records.items()
+    )
+
+
+def _valid_baseline(modules, evidence):
+    if (
+        type(evidence) is not dict
+        or type(evidence.get("schema_version")) is not int
+        or evidence["schema_version"] != 2
+    ):
+        return False
+
+    required = (
+        "candidate_imports_by_module",
+        "source_fingerprints_by_module",
+        "initializer_passivity_by_module",
+        "marker_mutation_by_module",
+        "opaque_effects_by_module",
+        "skipped_source_paths",
+        "unindexed_python_sources_present",
+        "unindexed_import_artifacts_present",
+        "global_policy_satisfied",
+    )
+
+    if any(key not in evidence for key in required):
+        return False
+
+    if any(
+        type(evidence[key]) is not bool
+        for key in (
+            "unindexed_python_sources_present",
+            "unindexed_import_artifacts_present",
+            "global_policy_satisfied",
+        )
+    ):
+        return False
+
+    if (
+        type(modules) is not dict
+        or any(
+            type(key) is not str or type(value) is not Module
+            for key, value in modules.items()
+        )
+    ):
+        return False
+
+    ids = set(modules)
+    fingerprints = evidence["source_fingerprints_by_module"]
+
+    if (
+        type(fingerprints) is not dict
+        or set(fingerprints) != ids
+        or not all(
+            _valid_fingerprint(value)
+            for value in fingerprints.values()
+        )
+    ):
+        return False
+
+    for key in (
+        "marker_mutation_by_module",
+        "opaque_effects_by_module",
+    ):
+        if not _valid_record_map(
+            evidence[key], fingerprints, ids
+        ):
+            return False
+
+    initializer_ids = {
+        module_id
+        for module_id in ids
+        if module_id.endswith(".__init__")
+    }
+
+    if not _valid_record_map(
+        evidence["initializer_passivity_by_module"],
+        fingerprints,
+        initializer_ids,
+    ):
+        return False
+
+    skipped = evidence["skipped_source_paths"]
+
+    if (
+        type(skipped) is not tuple
+        or any(
+            type(path) is not str or not path
+            for path in skipped
+        )
+        or tuple(sorted(set(skipped))) != skipped
+    ):
+        return False
+
+    candidates = evidence["candidate_imports_by_module"]
+
+    if (
+        type(candidates) is not dict
+        or not set(candidates).issubset(ids)
+    ):
+        return False
+
+    for module_id, module in modules.items():
+        if (
+            type(module.imports) is not list
+            or any(
+                type(ref) is not ImportRef
+                or type(ref.names) is not list
+                or type(ref.type_only) is not bool
+                for ref in module.imports
+            )
+        ):
+            return False
+
+        if module_id not in candidates:
+            if any(ref.type_only for ref in module.imports):
+                return False
+            continue
+
+        raw = candidates[module_id]
+
+        if (
+            type(raw) is not tuple
+            or len(raw) != len(module.imports)
+        ):
+            return False
+
+        if any(
+            type(ref) is not ImportRef
+            or type(ref.names) is not list
+            or type(ref.type_only) is not bool
+            for ref in raw
+        ):
+            return False
+
+        if not any(ref.type_only for ref in raw):
+            return False
+
+        for candidate_ref, final_ref in zip(
+            raw, module.imports
+        ):
+            if final_ref.type_only and not candidate_ref.type_only:
+                return False
+
+            if replace(
+                candidate_ref,
+                type_only=final_ref.type_only,
+            ) != final_ref:
+                return False
+
+    return True
+
+
+def _fail_closed(modules):
+    result = dict(modules)
+
+    for module_id, module in modules.items():
+        if any(
+            type(ref.type_only) is not bool or ref.type_only
+            for ref in module.imports
+        ):
+            result[module_id] = replace(
+                module,
+                imports=[
+                    replace(
+                        ref,
+                        type_only=False,
+                        names=list(ref.names),
+                    )
+                    for ref in module.imports
+                ],
+            )
+
+    return result, {}
+
+
+def reclassify_incremental_type_only(
+    modules,
+    *,
+    previous_modules,
+    previous_evidence,
+    changed_module_id,
+    changed_source_path,
+    changed_imports,
+    changed_source_evidence,
+    deleted=False,
+):
+    """Reclassify one change using retained project evidence."""
+
+    if (
+        type(modules) is not dict
+        or any(
+            type(value) is not Module
+            for value in modules.values()
+        )
+    ):
+        raise TypeError("modules must be a module mapping")
+
+    if any(
+        type(module.imports) is not list
+        or any(
+            type(ref) is not ImportRef
+            or type(ref.names) is not list
+            for ref in module.imports
+        )
+        for module in modules.values()
+    ):
+        raise TypeError("modules contain invalid import records")
+
+    if any(
+        type(ref.type_only) is not bool
+        for module in modules.values()
+        for ref in module.imports
+    ):
+        return _fail_closed(modules)
+
+    if not _valid_baseline(
+        previous_modules, previous_evidence
+    ):
+        return _fail_closed(modules)
+
+    if (
+        type(changed_module_id) is not str
+        or not changed_module_id
+        or type(changed_source_path) is not str
+        or not changed_source_path
+        or type(deleted) is not bool
+        or (
+            set(modules) - {changed_module_id}
+        ) != (
+            set(previous_modules) - {changed_module_id}
+        )
+    ):
+        return _fail_closed(modules)
+
+    if any(
+        modules[module_id] != previous_modules[module_id]
+        for module_id in (
+            set(modules) & set(previous_modules)
+        ) - {changed_module_id}
+    ):
+        return _fail_closed(modules)
+
+    if deleted:
+        if changed_module_id in modules:
+            return _fail_closed(modules)
+    else:
+        if (
+            changed_module_id not in modules
+            or type(changed_imports) is not list
+            or any(
+                type(ref) is not ImportRef
+                or type(ref.names) is not list
+                or type(ref.type_only) is not bool
+                for ref in changed_imports
+            )
+            or type(changed_source_evidence) is not dict
+            or type(
+                changed_source_evidence.get("schema_version")
+            ) is not int
+            or changed_source_evidence["schema_version"] != 1
+            or not _valid_fingerprint(
+                changed_source_evidence.get(
+                    "source_fingerprint"
+                )
+            )
+            or any(
+                type(changed_source_evidence.get(key)) is not bool
+                for key in (
+                    "initializer_passive",
+                    "marker_mutation",
+                    "opaque_effects",
+                )
+            )
+        ):
+            return _fail_closed(modules)
+
+    evidence = {
+        "schema_version": 2,
+        "candidate_imports_by_module": {
+            key: tuple(_copy_refs(refs))
+            for key, refs in previous_evidence[
+                "candidate_imports_by_module"
+            ].items()
+        },
+        "source_fingerprints_by_module": dict(
+            previous_evidence["source_fingerprints_by_module"]
+        ),
+        "initializer_passivity_by_module": dict(
+            previous_evidence["initializer_passivity_by_module"]
+        ),
+        "marker_mutation_by_module": dict(
+            previous_evidence["marker_mutation_by_module"]
+        ),
+        "opaque_effects_by_module": dict(
+            previous_evidence["opaque_effects_by_module"]
+        ),
+        "skipped_source_paths": tuple(
+            previous_evidence["skipped_source_paths"]
+        ),
+        "unindexed_python_sources_present": (
+            previous_evidence[
+                "unindexed_python_sources_present"
+            ]
+        ),
+        "unindexed_import_artifacts_present": (
+            previous_evidence[
+                "unindexed_import_artifacts_present"
+            ]
+        ),
+    }
+
+    evidence_maps = (
+        "candidate_imports_by_module",
+        "source_fingerprints_by_module",
+        "initializer_passivity_by_module",
+        "marker_mutation_by_module",
+        "opaque_effects_by_module",
+    )
+
+    if deleted:
+        for key in evidence_maps:
+            evidence[key].pop(changed_module_id, None)
+    else:
+        fingerprint = changed_source_evidence[
+            "source_fingerprint"
+        ]
+
+        evidence[
+            "source_fingerprints_by_module"
+        ][changed_module_id] = fingerprint
+
+        evidence[
+            "marker_mutation_by_module"
+        ][changed_module_id] = (
+            changed_source_evidence["marker_mutation"],
+            fingerprint,
+        )
+
+        evidence[
+            "opaque_effects_by_module"
+        ][changed_module_id] = (
+            changed_source_evidence["opaque_effects"],
+            fingerprint,
+        )
+
+        if changed_module_id.endswith(".__init__"):
+            evidence[
+                "initializer_passivity_by_module"
+            ][changed_module_id] = (
+                changed_source_evidence["initializer_passive"],
+                fingerprint,
+            )
+        else:
+            evidence[
+                "initializer_passivity_by_module"
+            ].pop(changed_module_id, None)
+
+        if any(ref.type_only for ref in changed_imports):
+            evidence[
+                "candidate_imports_by_module"
+            ][changed_module_id] = tuple(
+                _copy_refs(changed_imports)
+            )
+        else:
+            evidence[
+                "candidate_imports_by_module"
+            ].pop(changed_module_id, None)
+
+    evidence["skipped_source_paths"] = tuple(
+        path
+        for path in evidence["skipped_source_paths"]
+        if path != changed_source_path
+    )
+
+    restored = dict(modules)
+
+    for module_id, refs in evidence[
+        "candidate_imports_by_module"
+    ].items():
+        restored[module_id] = replace(
+            restored[module_id],
+            imports=_copy_refs(refs),
+        )
+
+    if not deleted:
+        restored[changed_module_id] = replace(
+            restored[changed_module_id],
+            imports=_copy_refs(changed_imports),
+        )
+
+    classified, global_policy = (
+        _classify_type_only_modules(
+            restored,
+            source_fingerprints_by_module=evidence[
+                "source_fingerprints_by_module"
+            ],
+            initializer_passivity_by_module=evidence[
+                "initializer_passivity_by_module"
+            ],
+            marker_mutation_by_module=evidence[
+                "marker_mutation_by_module"
+            ],
+            opaque_effects_by_module=evidence[
+                "opaque_effects_by_module"
+            ],
+            skipped_source_paths=evidence[
+                "skipped_source_paths"
+            ],
+            unindexed_python_sources_present=evidence[
+                "unindexed_python_sources_present"
+            ],
+            unindexed_import_artifacts_present=evidence[
+                "unindexed_import_artifacts_present"
+            ],
+        )
+    )
+
+    evidence["global_policy_satisfied"] = global_policy
+
+    for key in evidence_maps:
+        evidence[key] = dict(sorted(evidence[key].items()))
+
+    return classified, evidence
```

### `tests/test_p1d3_d2b2_type_only.py`

```diff
diff --git a/tests/test_p1d3_d2b2_type_only.py b/tests/test_p1d3_d2b2_type_only.py
index 0f1caef..4280887 100644
--- a/tests/test_p1d3_d2b2_type_only.py
+++ b/tests/test_p1d3_d2b2_type_only.py
@@ -3318,3 +3318,609 @@ def test_sp_t4_i2b3_t34_classifier_is_copy_on_write(
             assert classified[module_id] is modules[module_id]
     assert _i2b3_guarded_import(modules).type_only is True
 
+
+def _i2b4_verify_case(
+    tmp_path, initial, final, changed_path, *, deleted=False
+):
+    from contextor.core.analysis.incremental.type_only_policy import (
+        reclassify_incremental_type_only,
+    )
+    from contextor.core.domain.module import Module
+
+    old_root = write_synthetic_repository(
+        tmp_path / "initial", initial
+    )
+    old_index, _ = _index_graph(old_root)
+
+    new_root = write_synthetic_repository(
+        tmp_path / "final", final
+    )
+    new_index, new_graph = _index_graph(new_root)
+
+    module_id = ".".join(
+        Path(changed_path).with_suffix("").parts
+    )
+
+    candidate_modules = dict(old_index.modules)
+    changed_imports = []
+    source_evidence = None
+
+    if deleted:
+        candidate_modules.pop(module_id, None)
+    else:
+        prepared = _i2a_prepare(
+            new_root / changed_path, module_id
+        )
+        assert not prepared.has_error
+
+        changed_imports = prepared.new_imports
+        source_evidence = (
+            prepared.typing_guard_source_evidence
+        )
+
+        prior = candidate_modules.get(module_id)
+
+        if prior is None:
+            candidate_modules[module_id] = Module(
+                module_id=module_id,
+                path=changed_path,
+                absolute_path=str(
+                    (new_root / changed_path).resolve()
+                ),
+                imports=changed_imports,
+            )
+        else:
+            candidate_modules[module_id] = replace(
+                prior,
+                imports=list(changed_imports),
+            )
+
+    previous_imports = {
+        key: tuple(
+            (ref, tuple(ref.names))
+            for ref in module.imports
+        )
+        for key, module in old_index.modules.items()
+    }
+
+    previous_evidence = old_index.typing_guard_evidence
+
+    before_candidate_names = {
+        key: tuple(
+            tuple(ref.names)
+            for ref in refs
+        )
+        for key, refs in previous_evidence[
+            "candidate_imports_by_module"
+        ].items()
+    }
+
+    classified, evidence = (
+        reclassify_incremental_type_only(
+            candidate_modules,
+            previous_modules=old_index.modules,
+            previous_evidence=previous_evidence,
+            changed_module_id=module_id,
+            changed_source_path=changed_path,
+            changed_imports=changed_imports,
+            changed_source_evidence=source_evidence,
+            deleted=deleted,
+        )
+    )
+
+    assert evidence["schema_version"] == 2
+    assert set(classified) == set(new_index.modules)
+
+    assert all(
+        classified[key].imports
+        == new_index.modules[key].imports
+        for key in new_index.modules
+    )
+
+    trie = build_trie(classified.keys())
+    package_root = detect_package_root(classified, trie)
+
+    candidate_graph = build_graph(
+        classified,
+        trie=trie,
+        package_root=package_root,
+        reexport_facts_by_module=(
+            materialize_reexport_facts_by_module(
+                classified,
+                new_index.reference_facts_by_module,
+            )
+        ),
+    )
+
+    assert (
+        candidate_graph.hard_edges
+        == new_graph.hard_edges
+    )
+    assert (
+        candidate_graph.soft_edges
+        == new_graph.soft_edges
+    )
+
+    assert evidence[
+        "global_policy_satisfied"
+    ] == new_index.typing_guard_evidence[
+        "global_policy_satisfied"
+    ]
+
+    assert (
+        old_index.typing_guard_evidence
+        == previous_evidence
+    )
+
+    assert all(
+        tuple(
+            (ref, tuple(ref.nawarning: in the working copy of 'tests/test_p1d3_d2b2_type_only.py', LF will be replaced by CRLF the next time Git touches it
mes))
+            for ref in old_index.modules[key].imports
+        ) == old_imports
+        for key, old_imports in previous_imports.items()
+    )
+
+    assert {
+        key: tuple(
+            tuple(ref.names)
+            for ref in refs
+        )
+        for key, refs in previous_evidence[
+            "candidate_imports_by_module"
+        ].items()
+    } == before_candidate_names
+
+    return classified, evidence, old_index, new_index
+
+
+def test_sp_t4_i2b4_t35_safe_module_change(
+    tmp_path, isolated_dirs
+):
+    final = {
+        **_I1_SAFE,
+        "pkg/c.py": "pass\nVALUE = 2\n",
+    }
+    _i2b4_verify_case(
+        tmp_path, _I1_SAFE, final, "pkg/c.py"
+    )
+
+
+def test_sp_t4_i2b4_t36_new_typing_shadow(
+    tmp_path, isolated_dirs
+):
+    final = {
+        **_I1_SAFE,
+        "typing.py": "pass\n",
+    }
+    classified, _, _, _ = _i2b4_verify_case(
+        tmp_path, _I1_SAFE, final, "typing.py"
+    )
+    assert not _i2b3_guarded_import(
+        classified
+    ).type_only
+
+
+def test_sp_t4_i2b4_t37_deleted_shadow_restores_soft(
+    tmp_path, isolated_dirs
+):
+    initial = {
+        **_I1_SAFE,
+        "typing.py": "pass\n",
+    }
+    classified, _, _, _ = _i2b4_verify_case(
+        tmp_path,
+        initial,
+        _I1_SAFE,
+        "typing.py",
+        deleted=True,
+    )
+    assert _i2b3_guarded_import(
+        classified
+    ).type_only
+
+
+def test_sp_t4_i2b4_t38_parent_becomes_active(
+    tmp_path, isolated_dirs
+):
+    final = {
+        **_I1_SAFE,
+        "pkg/__init__.py": "import typing\n",
+    }
+    classified, _, _, _ = _i2b4_verify_case(
+        tmp_path,
+        _I1_SAFE,
+        final,
+        "pkg/__init__.py",
+    )
+    assert not _i2b3_guarded_import(
+        classified
+    ).type_only
+
+
+def test_sp_t4_i2b4_t39_parent_restored(
+    tmp_path, isolated_dirs
+):
+    initial = {
+        **_I1_SAFE,
+        "pkg/__init__.py": "import typing\n",
+    }
+    classified, _, _, _ = _i2b4_verify_case(
+        tmp_path,
+        initial,
+        _I1_SAFE,
+        "pkg/__init__.py",
+    )
+    assert _i2b3_guarded_import(
+        classified
+    ).type_only
+
+
+def test_sp_t4_i2b4_t40_marker_mutation_other_module(
+    tmp_path, isolated_dirs
+):
+    final = {
+        **_I1_SAFE,
+        "pkg/c.py": (
+            "import typing\n"
+            "typing.TYPE_CHECKING = True\n"
+        ),
+    }
+    classified, evidence, _, _ = _i2b4_verify_case(
+        tmp_path, _I1_SAFE, final, "pkg/c.py"
+    )
+    assert not evidence["global_policy_satisfied"]
+    assert not _i2b3_guarded_import(
+        classified
+    ).type_only
+
+
+def test_sp_t4_i2b4_t41_opaque_effect_other_module(
+    tmp_path, isolated_dirs
+):
+    final = {
+        **_I1_SAFE,
+        "pkg/c.py": "eval('0')\n",
+    }
+    classified, evidence, _, _ = _i2b4_verify_case(
+        tmp_path, _I1_SAFE, final, "pkg/c.py"
+    )
+    assert not evidence["global_policy_satisfied"]
+    assert not _i2b3_guarded_import(
+        classified
+    ).type_only
+
+
+@pytest.mark.parametrize(
+    "damage",
+    [
+        "missing",
+        "legacy",
+        "wrong-fingerprint",
+        "wrong-candidate",
+    ],
+    ids=[
+        "missing",
+        "legacy",
+        "fingerprint",
+        "candidate",
+    ],
+)
+def test_sp_t4_i2b4_t42_invalid_evidence_fails_closed(
+    tmp_path, isolated_dirs, damage
+):
+    from contextor.core.analysis.incremental.type_only_policy import (
+        reclassify_incremental_type_only,
+    )
+
+    root = write_synthetic_repository(
+        tmp_path / "repo", _I1_SAFE
+    )
+    baseline, _ = _index_graph(root)
+    evidence = dict(baseline.typing_guard_evidence)
+
+    if damage == "missing":
+        evidence = None
+    elif damage == "legacy":
+        evidence["schema_version"] = 1
+    elif damage == "wrong-fingerprint":
+        marker = dict(
+            evidence["marker_mutation_by_module"]
+        )
+        marker["pkg.a"] = (False, "invalid")
+        evidence["marker_mutation_by_module"] = marker
+    else:
+        raw = dict(
+            evidence["candidate_imports_by_module"]
+        )
+        raw["pkg.a"] = (
+            ImportRef(
+                "pkg.z",
+                0,
+                [],
+                False,
+                type_only=True,
+            ),
+        )
+        evidence["candidate_imports_by_module"] = raw
+
+    changed = root / "pkg/c.py"
+    changed.write_text(
+        "pass\nVALUE = 2\n", encoding="utf-8"
+    )
+
+    prepared = _i2a_prepare(changed, "pkg.c")
+    assert not prepared.has_error
+
+    candidate = dict(baseline.modules)
+    candidate["pkg.c"] = replace(
+        candidate["pkg.c"],
+        imports=list(prepared.new_imports),
+    )
+
+    classified, new_evidence = (
+        reclassify_incremental_type_only(
+            candidate,
+            previous_modules=baseline.modules,
+            previous_evidence=evidence,
+            changed_module_id="pkg.c",
+            changed_source_path="pkg/c.py",
+            changed_imports=prepared.new_imports,
+            changed_source_evidence=(
+                prepared.typing_guard_source_evidence
+            ),
+        )
+    )
+
+    assert new_evidence == {}
+    assert not any(
+        ref.type_only
+        for module in classified.values()
+        for ref in module.imports
+    )
+    assert _i2b3_guarded_import(
+        baseline.modules
+    ).type_only
+
+
+def test_sp_t4_i2b4_t43_skipped_recovers(
+    tmp_path, isolated_dirs
+):
+    initial = {
+        **_I1_SAFE,
+        "broken.py": "def invalid(:\n",
+    }
+    final = {
+        **_I1_SAFE,
+        "broken.py": "pass\n",
+    }
+
+    classified, evidence, _, _ = _i2b4_verify_case(
+        tmp_path,
+        initial,
+        final,
+        "broken.py",
+    )
+
+    assert evidence["skipped_source_paths"] == ()
+    assert _i2b3_guarded_import(
+        classified
+    ).type_only
+
+
+def test_sp_t4_i2b4_t44_no_input_mutation_on_benign_change(
+    tmp_path, isolated_dirs
+):
+    final = {
+        **_I1_SAFE,
+        "pkg/c.py": "pass\nVALUE = 2\n",
+    }
+
+    classified, evidence, old, _ = (
+        _i2b4_verify_case(
+            tmp_path,
+            _I1_SAFE,
+            final,
+            "pkg/c.py",
+        )
+    )
+
+    assert evidence is not old.typing_guard_evidence
+
+    assert (
+        evidence["candidate_imports_by_module"]
+        is not old.typing_guard_evidence[
+            "candidate_imports_by_module"
+        ]
+    )
+
+    assert _i2b3_guarded_import(
+        classified
+    ).type_only
+
+
+@pytest.mark.parametrize(
+    "invalid_value", [1, "true", 0],
+)
+def test_sp_t4_i2b4c_t45_malformed_saved_candidate(
+    tmp_path, isolated_dirs, invalid_value,
+):
+    from contextor.core.analysis.incremental.type_only_policy import (
+        reclassify_incremental_type_only,
+    )
+
+    initial = {
+        **_I1_SAFE,
+        "typing.py": "pass\n",
+    }
+    root = write_synthetic_repository(
+        tmp_path / "repo", initial
+    )
+    baseline, _ = _index_graph(root)
+
+    evidence = dict(baseline.typing_guard_evidence)
+    candidates = dict(
+        evidence["candidate_imports_by_module"]
+    )
+    candidates["pkg.a"] = tuple(
+        replace(ref, type_only=invalid_value)
+        if ref.type_only else ref
+        for ref in candidates["pkg.a"]
+    )
+    evidence["candidate_imports_by_module"] = candidates
+
+    modules = dict(baseline.modules)
+    modules.pop("typing")
+
+    classified, updated = reclassify_incremental_type_only(
+        modules,
+        previous_modules=baseline.modules,
+        previous_evidence=evidence,
+        changed_module_id="typing",
+        changed_source_path="typing.py",
+        changed_imports=[],
+        changed_source_evidence=None,
+        deleted=True,
+    )
+
+    assert updated == {}
+    assert all(
+        ref.type_only is False
+        for module in classified.values()
+        for ref in module.imports
+    )
+
+
+def test_sp_t4_i2b4c_t46_malformed_changed_import(
+    tmp_path, isolated_dirs,
+):
+    from contextor.core.analysis.incremental.type_only_policy import (
+        reclassify_incremental_type_only,
+    )
+
+    root = write_synthetic_repository(
+        tmp_path / "repo", _I1_SAFE
+    )
+    baseline, _ = _index_graph(root)
+    prepared = _i2a_prepare(root / "pkg/a.py", "pkg.a")
+
+    malformed = [
+        replace(ref, type_only=1)
+        if ref.type_only else ref
+        for ref in prepared.new_imports
+    ]
+    assert any(
+        type(ref.type_only) is int
+        for ref in malformed
+    )
+
+    modules = dict(baseline.modules)
+    modules["pkg.a"] = replace(
+        modules["pkg.a"],
+        imports=list(malformed),
+    )
+
+    classified, updated = reclassify_incremental_type_only(
+        modules,
+        previous_modules=baseline.modules,
+        previous_evidence=baseline.typing_guard_evidence,
+        changed_module_id="pkg.a",
+        changed_source_path="pkg/a.py",
+        changed_imports=malformed,
+        changed_source_evidence=(
+            prepared.typing_guard_source_evidence
+        ),
+    )
+
+    assert updated == {}
+    assert all(
+        ref.type_only is False
+        for module in classified.values()
+        for ref in module.imports
+    )
+
+
+def test_sp_t4_i2b4c_t47_malformed_previous_final(
+    tmp_path, isolated_dirs,
+):
+    from contextor.core.analysis.incremental.type_only_policy import (
+        reclassify_incremental_type_only,
+    )
+
+    root = write_synthetic_repository(
+        tmp_path / "repo", _I1_SAFE
+    )
+    baseline, _ = _index_graph(root)
+
+    previous = dict(baseline.modules)
+    previous["pkg.a"] = replace(
+        previous["pkg.a"],
+        imports=[
+            replace(ref, type_only=1)
+            if ref.type_only else ref
+            for ref in previous["pkg.a"].imports
+        ],
+    )
+
+    prepared = _i2a_prepare(root / "pkg/c.py", "pkg.c")
+    classified, updated = reclassify_incremental_type_only(
+        dict(previous),
+        previous_modules=previous,
+        previous_evidence=baseline.typing_guard_evidence,
+        changed_module_id="pkg.c",
+        changed_source_path="pkg/c.py",
+        changed_imports=prepared.new_imports,
+        changed_source_evidence=(
+            prepared.typing_guard_source_evidence
+        ),
+    )
+
+    assert updated == {}
+    assert all(
+        ref.type_only is False
+        for module in classified.values()
+        for ref in module.imports
+    )
+
+
+def test_sp_t4_i2b4c_t48_unrelated_module_tampering(
+    tmp_path, isolated_dirs,
+):
+    from contextor.core.analysis.incremental.type_only_policy import (
+        reclassify_incremental_type_only,
+    )
+
+    root = write_synthetic_repository(
+        tmp_path / "repo", _I1_SAFE
+    )
+    baseline, _ = _index_graph(root)
+
+    modules = dict(baseline.modules)
+    modules["pkg.a"] = replace(
+        modules["pkg.a"],
+        imports=[
+            replace(ref, type_only=False)
+            if ref.type_only else ref
+            for ref in modules["pkg.a"].imports
+        ],
+    )
+
+    prepared = _i2a_prepare(root / "pkg/c.py", "pkg.c")
+    classified, updated = reclassify_incremental_type_only(
+        modules,
+        previous_modules=baseline.modules,
+        previous_evidence=baseline.typing_guard_evidence,
+        changed_module_id="pkg.c",
+        changed_source_path="pkg/c.py",
+        changed_imports=prepared.new_imports,
+        changed_source_evidence=(
+            prepared.typing_guard_source_evidence
+        ),
+    )
+
+    assert updated == {}
+    assert all(
+        ref.type_only is False
+        for module in classified.values()
+        for ref in module.imports
+    )
+
```

