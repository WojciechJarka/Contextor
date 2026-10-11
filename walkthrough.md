# L03_FRESH_PROCESS_LKG_PARSE_DIAGNOSTIC_DISCOVERY

## FILES_CHANGED

- `C:\Temp\Contextor_Repo\walkthrough.md` (report only). No source, test, fixture, or docs files changed.

## ACTUAL_DIFF

ACTUAL_DIFF=DIFFS=NONE for source/test/docs. This report is the only write.

## SOURCE_SYNC

DIRECT_EVIDENCE: Contextor complete symbol retrievals reported `implementation_is_complete=true`, `workspace_sync=verified`, `canonical_state=fresh`, revision 327. Complete contiguous ranges were used for large symbols. Repository `git status --short` and `git diff --stat` returned empty before report write. The second source sync request for `module_current_truth` confirmed the same implementation and revision 327. An initial malformed request used `symbol_name` instead of required `symbol`; it was corrected, with no source mutation.

## HISTORICAL_L03_CONTRACT

The requested missing proof is an end-to-end, **fresh Python process** reconstruction of one canonical generation in which last-known-good (LKG) symbol artifacts, parse-stale status, and the precise syntax diagnostic coexist after invalid source; a subsequent valid source parse must recover coherent facts and revision. Historical baseline supplied by user: L32H full suite 3358 passed, 1 skipped, 1 warning. This task does not rerun the full suite.

## CURRENT_L03_COVERAGE

- CODE_PATH_PROVED: invalid parse constructs an error result, retains prior module/artifacts, stores a syntax fact and module parse failure, then persists complete state.
- CONTRACT_PROVED by named same-process tests: stale/LKG and exact parse failure, same-process save/load, local fallback same-process rehydration, syntax fact snapshot roundtrip, revision-atomic LIVE mutation.
- NOT_COVERED: one fresh spawned interpreter loads an error-generation snapshot and jointly asserts retained symbol payload + stale parse marker + exact syntax diagnostic; no existing test then performs valid recovery in that spawned interpreter and checks public facts/revision together.
- L03_PRODUCTION_CORRECTNESS=UNKNOWN for the **fresh-process combined contract**. No production defect is proven by this discovery.
- L03_FRESH_PROCESS_REGRESSION_COVERAGE=ABSENT for the combined contract. Existing spawned-process infrastructure covers other concerns.

## EXISTING_PARSE_HYDRATION_TEST

`C:\Temp\Contextor_Repo\tests\test_live_e2e_corrections.py:451-472` saves and loads state in the same interpreter. It checks parse failure detail after load and a RECOVERED result, while reusing the original registry and FileStateManager. It does not assert post-load symbol artifacts, persisted syntax fact detail, source replacement, public query status or revision. `C:\Temp\Contextor_Repo\tests\test_mcp_incremental_hydration.py:2080-2115` clears a module-level cache then reloads in the same interpreter; it checks artifacts and stale/clean syntax status, but not exact error fields or a fresh process. The test file `tests/test_live_e2e_corrections.py` was retrieved in four contiguous Contextor ranges covering lines 1-930; no subprocess use appears in that full file.

## VALID_INVALID_VALID_STATE_MATRIX

| Phase | Production code path | Proven result | Evidence limit |
|---|---|---|---|
| Valid baseline | `_engine_for_file` indexes module/artifacts; normal update or full analysis publishes current facts | Existing tests establish baseline symbol artifacts | No fresh-process L03 baseline assertion |
| Invalid parse | `parse_source_snapshot` raises `SourceError(SYNTAX_ERROR)`; `prepare_source_update` holds empty `new_artifacts`; `engine.update_file` invokes `_commit_syntax_candidate` | CODE_PATH_PROVED: syntax fact `checked_with_errors`; parse marker `stale`; old artifacts untouched; return `SYNTAX_ERROR` | Joint fresh-process survival untested |
| Hydrated invalid | `save_engine_state` / `save_snapshot` pickle state with metadata; `load_snapshot` validates embedded metadata and reconstructs state | Same-process tests prove parse marker and/or artifacts and/or syntax fact separately | Combined fresh-process proof absent |
| Valid recovery | successful parse clears parse failure, stores `checked_and_none`, and publishes candidate artifacts or returns `RECOVERED` on semantic no-op | Same-process tests prove recovery and revision-atomic LIVE sequence | Recovery after fresh-process error-generation hydration not asserted |

## LKG_SYMBOL_ARTIFACT_RETENTION

CODE_PATH_PROVED: the syntax error branch does not call `_apply_delta_and_commit`; `_commit_syntax_candidate` clones state, sets syntax and parse metadata, and does not replace `candidate.artifacts[module]`. `_prepare_candidate_state` copies the artifact map; `execute_refresh_plan` replaces a module's artifact only in a definitions patch with new artifacts. `test_syntax_error_marks_authoritative_last_known_good_and_recovery` explicitly checks the retained `helper` symbol. `test_local_fallback_syntax_error_and_recovery_survive_snapshot_hydration` checks artifacts equal across same-process cache clear and reload. Fresh-process retention remains NOT_COVERED.

## PARSE_FRESHNESS_AND_DIAGNOSTICS

The parse marker uses `module_parse_freshness[module] = {state:'stale',error,line_number,column_number}`; `module_current_truth` exposes `available:false`, `state:'stale'`, `provenance:'last_known_good'` and those fields. Unknown/malformed entries return unavailable/untrusted. A **missing** module entry is fresh by the current legacy contract, so missing entry alone is not evidence of a valid source parse. The syntax fact is separately stored in `syntax_diagnostics_by_path` with `checked_with_errors` and an errors list. The primary hydration test checks the parse failure fields but not the syntax fact fields after load. Full-analysis syntax snapshot test checks the syntax fact independent of LKG parse state.

## SNAPSHOT_SERIALIZATION

CODE_PATH_PROVED: `save_engine_state` delegates to `save_snapshot` with state, revision, state ID, and FileState paths. The versioned snapshot payload includes `{metadata,state}` via pickle. `load_snapshot` checks metadata equality and revision/state_id coherence before returning state; it restores provenance `snapshot`. Legacy missing syntax fields default to empty/not_materialized. There is no observed independent cross-check that the parse-stale marker and syntax fact match each other; this is a coverage observation, not a proved defect.

## FRESH_PROCESS_HYDRATION_BOUNDARY

`resolve_authoritative_repository_state` selects and loads the authoritative snapshot; `hydrate_repository_engine` then constructs a new registry and FileStateManager for a new engine. A spawned-process fixture already exists at `C:\Temp\Contextor_Repo\tests\test_mcp_incremental_hydration.py:112-155`, with `multiprocessing.get_context('spawn')` used in the test at lines 752-820. Its current assertions are about competing local candidate writers, not the L03 triple-state snapshot. The small `_rehydrate_local_engine` helper at lines 100-102 only clears an in-process cache.

## RECOVERY_AND_CANONICAL_REVISION

`test_live_incremental_syntax_lifecycle_is_source_scoped_and_revision_atomic` proves valid→invalid→valid LIVE revisions 1→2→3 in one process and checks diagnostics cleanup. The primary parse hydration test does not assert canonical revision/state_id after recovery; the local fallback hydration test checks persistence flags and syntax status, but no fresh-process revision correspondence. Therefore combined fresh-process recovery and revision consistency are NOT_COVERED.

## LKG_FAIL_CLOSED_QUERY_SEMANTICS

`module_truth_unavailable` and `syntax_diagnostics_for_path` support public fail-closed projection. Existing mocked-state MCP tests show stale/unavailable public responses and no live canonical facts for parse-stale state. Those tests do not query a snapshot freshly loaded in another interpreter. No public leak is proven here.

## DIRECTLY_RELEVANT_TEST_RESULTS

Repository `.venv\Scripts\python.exe` pytest, named nodes only, no full suite:

1. Seven L03-relevant nodes: **7 passed, 1 warning in 10.49s**.
2. Two additional named nodes (one parameterized): **3 passed, 1 warning in 6.59s**.

Warning: `AuthlibDeprecationWarning` in installed FastMCP dependency. Node IDs:

```text
tests/test_live_e2e_corrections.py::test_parse_freshness_survives_snapshot_hydration_and_recovers
tests/test_live_e2e_corrections.py::test_syntax_error_marks_authoritative_last_known_good_and_recovery
tests/test_live_e2e_corrections.py::test_affected_mcp_queries_fail_closed_on_parse_stale_state
tests/test_mcp_incremental_hydration.py::test_local_fallback_syntax_error_and_recovery_survive_snapshot_hydration
tests/test_syntax_diagnostics_full_analysis.py::test_syntax_diagnostics_snapshot_roundtrip_needs_no_source_reconstruction
tests/test_syntax_diagnostics_full_analysis.py::test_legacy_snapshot_marks_syntax_family_not_materialized
tests/test_syntax_diagnostics_full_analysis.py::test_live_incremental_syntax_lifecycle_is_source_scoped_and_revision_atomic
tests/test_mcp_incremental_hydration.py::test_local_candidate_syntax_lkg_recovery_and_unchanged_publish_after_persist
tests/test_live_e2e_corrections.py::test_malformed_parse_freshness_snapshot_roundtrip_remains_untrusted
```

## PROVED_DEFECTS

NONE. The historical L03 finding is a missing integrated fresh-process proof, not a source-proven current failure.

## EVIDENCE_GAPS

| Risk/claim | Classification | Basis |
|---|---|---|
| Invalid parse replaces LKG artifacts with empty materialization | PROVED_SAFE in inspected same-process path | Error branch skips delta commit and candidate artifact replacement |
| LKG artifacts lost in same-process snapshot reload | PROVED_SAFE for named local fallback test | Artifacts equality asserted after cache clear and load |
| LKG artifacts lost in a genuinely fresh process | NOT_COVERED | Existing spawned worker does not exercise error-generation LKG snapshot |
| Exact syntax diagnostic lost in same-process snapshot | PROVED_SAFE for isolated syntax fact test | Exact fact roundtrip assertion |
| Exact syntax diagnostic lost alongside LKG in fresh process | NOT_COVERED | No combined assertion |
| Parse-stale appears fresh after same-process hydrate | PROVED_SAFE for valid stale marker | Primary hydration test checks stale failure details; function returns stale |
| Parse-stale appears fresh after fresh-process hydrate | NOT_COVERED | No spawned combined path |
| Recovery leaves diagnostic stale in same process | PROVED_SAFE for LIVE/local named tests | Checked-and-none and parse marker cleanup asserted |
| Recovery after fresh-process hydration inconsistent | NOT_COVERED | No named combined test |
| Invalid snapshot metadata silently accepted | PROVED_SAFE for inspected load path | Embedded metadata validation; separate regression exists |
| Production defect requiring patch | UNKNOWN | No failing production path established |

## EXACT_SOURCE_AND_TEST_PATHS

- `C:\Temp\Contextor_Repo\contextor\core\source.py`
- `C:\Temp\Contextor_Repo\contextor\core\analysis\incremental\preparation.py`
- `C:\Temp\Contextor_Repo\contextor\core\analysis\incremental\engine.py`
- `C:\Temp\Contextor_Repo\contextor\core\analysis\incremental\plan_executor.py`
- `C:\Temp\Contextor_Repo\contextor\core\analysis\state_manager.py`
- `C:\Temp\Contextor_Repo\contextor\core\live_state\store.py`
- `C:\Temp\Contextor_Repo\contextor\core\live_state\hydration.py`
- `C:\Temp\Contextor_Repo\tests\test_live_e2e_corrections.py`
- `C:\Temp\Contextor_Repo\tests\test_mcp_incremental_hydration.py`
- `C:\Temp\Contextor_Repo\tests\test_syntax_diagnostics_full_analysis.py`

## COMPLETE_LITERAL_SOURCE_FRAGMENTS

The following complete symbol implementations and contiguous ranges were retrieved from Contextor MCP. Large functions are represented by the entire implementation where fetched or by complete contiguous control-flow ranges. No preview/truncated response is treated as a full implementation.

### _engine_for_file

Source: `C:\Temp\Contextor_Repo\tests\test_live_e2e_corrections.py : 77-99`

```python
def _engine_for_file(tmp_path):
    source = tmp_path / "provider.py"
    source.write_text("def helper(value: int) -> int:\n    return value + 1\n")
    registry = PersistentIdentityRegistry(str(tmp_path))
    repo_index = index_repository(str(tmp_path))
    modules = repo_index.modules
    artifacts, _ = collect_module_artifacts(modules, str(tmp_path))
    trie = build_trie(modules)
    state = RepositoryAnalysisState(
        modules=dict(modules),
        reexport_facts_by_module=materialize_reexport_facts_by_module(
            modules, repo_index.reference_facts_by_module
        ),
        artifacts=artifacts,
        dependency_graph=build_graph(modules),
        trie=trie,
        package_root=detect_package_root(modules, trie),
    )
    manager = FileStateManager(str(tmp_path / ".state"))
    manager.update_state(str(source))
    return source, IncrementalAnalysisEngine(
        state, registry, manager, str(tmp_path)
    )
```

### test_syntax_error_marks_authoritative_last_known_good_and_recovery

Source: `C:\Temp\Contextor_Repo\tests\test_live_e2e_corrections.py : 226-254`

```python
def test_syntax_error_marks_authoritative_last_known_good_and_recovery(tmp_path):
    source, engine = _engine_for_file(tmp_path)

    source.write_text("def helper(\n")
    failed = engine.update_file(str(source))

    assert failed.status == "SYNTAX_ERROR"
    assert module_current_truth(engine.state, "provider") == {
        "available": False,
        "state": "stale",
        "provenance": "last_known_good",
        "reason": "Current source could not be parsed; canonical facts are last-known-good.",
        "parse_failure": {
            "error": "'(' was never closed",
            "line_number": 1,
            "column_number": 11,
        },
    }
    assert "helper" in engine.state.artifacts["provider"]["own_symbols"]

    source.write_text("def helper(value: int) -> int:\n    return value + 1\n")
    recovered = engine.update_file(str(source))

    assert recovered.status == "RECOVERED"
    assert module_current_truth(engine.state, "provider") == {
        "available": True,
        "state": "fresh",
        "provenance": "current",
    }
```

### test_parse_freshness_survives_snapshot_hydration_and_recovers

Source: `C:\Temp\Contextor_Repo\tests\test_live_e2e_corrections.py : 451-472`

```python
def test_parse_freshness_survives_snapshot_hydration_and_recovers(tmp_path):
    source, engine = _engine_for_file(tmp_path)
    source.write_text("def helper(\n")
    assert engine.update_file(str(source)).status == "SYNTAX_ERROR"

    cache = tmp_path / "cache"
    assert save_engine_state(engine.state, str(cache), "state-1")
    loaded = load_engine_state(str(cache), "state-1")

    assert loaded is not None
    assert module_current_truth(loaded, "provider")["parse_failure"] == {
        "error": "'(' was never closed",
        "line_number": 1,
        "column_number": 11,
    }

    source.write_text("def helper(value: int) -> int:\n    return value + 1\n")
    hydrated_engine = IncrementalAnalysisEngine(
        loaded, engine.registry, engine.state_manager, str(tmp_path)
    )
    assert hydrated_engine.update_file(str(source)).status == "RECOVERED"
    assert module_current_truth(loaded, "provider")["provenance"] == "current"
```

### test_malformed_parse_freshness_snapshot_roundtrip_remains_untrusted

Source: `C:\Temp\Contextor_Repo\tests\test_live_e2e_corrections.py : 475-493`

```python
@pytest.mark.parametrize(
    "raw_map",
    [{"provider": {"state": "unknown"}}, ["bad"]],
    ids=["malformed_entry", "malformed_whole_map"],
)
def test_malformed_parse_freshness_snapshot_roundtrip_remains_untrusted(tmp_path, raw_map):
    _source, engine = _engine_for_file(tmp_path)
    engine.state.module_parse_freshness = raw_map
    original_map = engine.state.module_parse_freshness

    cache = tmp_path / "cache"
    assert save_engine_state(engine.state, str(cache), "state-malformed")
    loaded = load_engine_state(str(cache), "state-malformed")

    assert loaded is not None
    assert loaded.module_parse_freshness == raw_map
    assert module_current_truth(loaded, "provider")["state"] == "unavailable"
    assert module_current_truth(loaded, "provider")["provenance"] == "untrusted"
    assert engine.state.module_parse_freshness is original_map
```

### test_malformed_snapshot_map_rejects_hydrated_syntax_update

Source: `C:\Temp\Contextor_Repo\tests\test_live_e2e_corrections.py : 680-709`

```python
def test_malformed_snapshot_map_rejects_hydrated_syntax_update(tmp_path):
    source, engine = _engine_for_file(tmp_path)
    raw_map = [("provider", {"state": "stale"})]
    engine.state.module_parse_freshness = raw_map
    cache = tmp_path / "cache"
    assert save_engine_state(engine.state, str(cache), "state-malformed-update")
    loaded = load_engine_state(str(cache), "state-malformed-update")
    assert loaded is not None
    original_map = loaded.module_parse_freshness
    original_modules = loaded.modules
    source.write_text("def broken(\n")
    hydrated_engine = IncrementalAnalysisEngine(
        loaded,
        engine.registry,
        engine.state_manager,
        str(tmp_path),
    )

    with pytest.raises(
        ValueError,
        match="Canonical module_parse_freshness is invalid",
    ):
        hydrated_engine.update_file(str(source))

    assert loaded.module_parse_freshness is original_map
    assert loaded.modules is original_modules
    assert module_current_truth(loaded, "provider")["state"] == "unavailable"
    previous_generation = load_engine_state(str(cache), "state-malformed-update")
    assert previous_generation is not None
    assert previous_generation.module_parse_freshness == raw_map
```

### module_current_truth

Source: `C:\Temp\Contextor_Repo\contextor\core\analysis\state_manager.py : 227-269`

```python
def module_current_truth(state: RepositoryAnalysisState, module_name: str) -> Dict[str, Any]:
    """Return authoritative per-module parse freshness and provenance."""
    missing = object()
    freshness = getattr(state, "module_parse_freshness", missing)

    if freshness is missing:
        freshness = {}

    entry = (
        freshness.get(module_name, missing)
        if isinstance(freshness, dict)
        else None
    )

    if entry is missing:
        return {"available": True, "state": "fresh", "provenance": "current"}

    if (
        not isinstance(entry, dict)
        or type(entry.get("state")) is not str
        or entry["state"] not in {"fresh", "stale"}
    ):
        return {
            "available": False,
            "state": "unavailable",
            "provenance": "untrusted",
            "reason": "Canonical module parse freshness metadata is invalid or untrusted.",
        }

    if entry["state"] == "fresh":
        return {"available": True, "state": "fresh", "provenance": "current"}

    return {
        "available": False,
        "state": "stale",
        "provenance": "last_known_good",
        "reason": "Current source could not be parsed; canonical facts are last-known-good.",
        "parse_failure": {
            key: entry.get(key)
            for key in ("error", "line_number", "column_number")
            if entry.get(key) is not None
        },
    }
```

### mark_module_parse_failure

Source: `C:\Temp\Contextor_Repo\contextor\core\analysis\state_manager.py : 272-296`

```python
def mark_module_parse_failure(
    state: RepositoryAnalysisState,
    module_name: str,
    *,
    error: str | None,
    line_number: int | None,
    column_number: int | None,
) -> None:
    """Mark retained module facts as last-known-good after a parse failure."""
    truth = module_current_truth(state, module_name)
    if truth["state"] == "unavailable":
        raise ValueError(
            "Canonical module parse freshness is untrusted; "
            "fresh full analysis is required."
        )
    freshness = getattr(state, "module_parse_freshness", None)
    if not isinstance(freshness, dict):
        freshness = {}
        state.module_parse_freshness = freshness
    freshness[module_name] = {
        "state": "stale",
        "error": error,
        "line_number": line_number,
        "column_number": column_number,
    }
```

### clear_module_parse_failure

Source: `C:\Temp\Contextor_Repo\contextor\core\analysis\state_manager.py : 299-309`

```python
def clear_module_parse_failure(
    state: RepositoryAnalysisState, module_name: str
) -> bool:
    """Clear parse failure and report whether this is a recovery transition."""
    freshness = getattr(state, "module_parse_freshness", None)
    if not isinstance(freshness, dict):
        return False
    entry = freshness.get(module_name)
    recovered = isinstance(entry, dict) and entry.get("state") == "stale"
    freshness.pop(module_name, None)
    return recovered
```

### _commit_syntax_candidate

Source: `C:\Temp\Contextor_Repo\contextor\core\analysis\incremental\engine.py : 126-206`

```python
    def _commit_syntax_candidate(
        self,
        *,
        source_path: str,
        syntax_fact: Dict[str, Any] | None = None,
        remove_syntax_fact: bool = False,
        mark_parse_error: tuple[str | None, int | None, int | None] | None = None,
        clear_parse_module: str | None = None,
        degrade_syntax_family: bool = False,
        extracted_lineage_facts: Any | None = None,
        invalidate_lineage: bool = False,
    ) -> None:
        """Commit syntax, parse-freshness, and lineage changes through one COW candidate."""
        candidate = _prepare_candidate_state(self.state)
        if invalidate_lineage:
            from contextor.core.domain.lineage_facts import (
                LINEAGE_FACTS_SEMANTIC_VERSION,
                LineageFamilyStatus,
            )
            from contextor.core.lineage_query.index import (
                build_lineage_query_indexes,
            )

            candidate.lineage_facts_by_source.pop(source_path, None)
            if candidate.lineage_facts_state == LineageFamilyStatus.NOT_MATERIALIZED.value:
                candidate.lineage_facts_state = LineageFamilyStatus.NOT_MATERIALIZED.value
                candidate.lineage_facts_semantic_version = None
            else:
                candidate.lineage_facts_state = LineageFamilyStatus.STALE.value
                candidate.lineage_facts_semantic_version = LINEAGE_FACTS_SEMANTIC_VERSION
            (
                candidate.lineage_owner_source_index,
                candidate.lineage_source_owner_index,
                candidate.lineage_semantic_anchor_bindings_complete,
            ) = build_lineage_query_indexes(candidate.lineage_facts_by_source)
            candidate.lineage_query_index_state = (
                "not_materialized"
                if candidate.lineage_facts_state
                == LineageFamilyStatus.NOT_MATERIALIZED.value
                else "fresh"
            )
            if candidate.lineage_query_index_state != "fresh":
                candidate.lineage_semantic_anchor_bindings_complete = False
        elif extracted_lineage_facts is not None:
            with self.registry.read_transaction():
                self._update_candidate_lineage_slice(
                    candidate,
                    source_path=source_path,
                    extracted_lineage_facts=extracted_lineage_facts,
                )
        if remove_syntax_fact:
            candidate.syntax_diagnostics_by_path.pop(source_path, None)
        elif syntax_fact is not None:
            candidate.syntax_diagnostics_by_path[source_path] = syntax_fact
        if degrade_syntax_family and candidate.syntax_diagnostics_state == "fresh":
            candidate.syntax_diagnostics_state = "deferred"
        if mark_parse_error is not None:
            error, line_number, column_number = mark_parse_error
            mark_module_parse_failure(
                candidate,
                clear_parse_module or "",
                error=error,
                line_number=line_number,
                column_number=column_number,
            )
        elif clear_parse_module is not None:
            clear_module_parse_failure(candidate, clear_parse_module)
        self.state.syntax_diagnostics_by_path = candidate.syntax_diagnostics_by_path
        self.state.syntax_diagnostics_state = candidate.syntax_diagnostics_state
        self.state.module_parse_freshness = candidate.module_parse_freshness
        self.state.lineage_facts_by_source = candidate.lineage_facts_by_source
        self.state.lineage_facts_state = candidate.lineage_facts_state
        self.state.lineage_facts_semantic_version = (
            candidate.lineage_facts_semantic_version
        )
        self.state.lineage_owner_source_index = candidate.lineage_owner_source_index
        self.state.lineage_source_owner_index = candidate.lineage_source_owner_index
        self.state.lineage_query_index_state = candidate.lineage_query_index_state
        self.state.lineage_semantic_anchor_bindings_complete = (
            candidate.lineage_semantic_anchor_bindings_complete
        )
```

### save_engine_state

Source: `C:\Temp\Contextor_Repo\contextor\core\analysis\state_manager.py : 489-515`

```python
def save_engine_state(
    state: RepositoryAnalysisState,
    cache_dir: str,
    state_id: str,
    *,
    writer: str = "unknown",
    repo_id: str = "",
    root_path: str = "",
    exact_revision: int | None = None,
    file_state_payload: dict[str, Any] | None = None,
):
    from contextor.core.live_state import save_snapshot
    try:
        return save_snapshot(
            state,
            cache_dir,
            state_id,
            writer=writer,
            repo_id=repo_id,
            root_path=root_path,
            exact_revision=exact_revision,
            file_state_payload=file_state_payload,
        )
    except Exception as e:
        import sys
        print(f"Failed to save engine state: {e}", file=sys.stderr)
        return None
```

### load_engine_state

Source: `C:\Temp\Contextor_Repo\contextor\core\analysis\state_manager.py : 517-536`

```python
def load_engine_state(
    cache_dir: str,
    expected_state_id: str,
    *,
    expected_repo_id: str = "",
    expected_root_path: str = "",
) -> Optional[RepositoryAnalysisState]:
    from contextor.core.live_state import load_snapshot
    try:
        loaded = load_snapshot(
            cache_dir,
            expected_state_id,
            expected_repo_id=expected_repo_id,
            expected_root_path=expected_root_path,
        )
        return loaded[0] if loaded else None
    except Exception as e:
        import sys
        print(f"Failed to load engine state: {e}", file=sys.stderr)
        return None
```

### prepare_source_update

Source: `C:\Temp\Contextor_Repo\contextor\core\analysis\incremental\preparation.py : 147-330`

```python
def prepare_source_update(
    file_path: str | Path,
    module_path: str,
    is_new: bool,
    old_module: Optional[Any],
    old_artifacts: Optional[Dict[str, Any]],
    old_usage: Optional[ModuleUsageFacts],
    persistent_id: Optional[str] = None,
    old_collision_facts: Optional[List[Dict[str, Any]]] = None,
    source_key: str | None = None,
    old_reexport_facts: Optional[Dict[str, Any]] = None,
) -> PreparedSourceUpdate:
    """
    Parses and extracts all necessary facts from a changed/added source file,
    computes structural FileDelta, behavioral UsageDelta, and collision facts without mutating canonical state.
    """
    path = Path(file_path)

    # 1. Syntax validation and source reading
    try:
        parsed_input = parse_source_with_fingerprint(path)
        parsed_tree = parsed_input.tree
    except SourceError as exc:
        return PreparedSourceUpdate(
            module_path=module_path,
            is_new=is_new,
            new_imports=[],
            new_artifacts={},
            new_usage=None,
            delta=FileDelta(module_path=module_path, is_new=is_new),
            usage_delta=None,
            new_collision_facts=None,
            collision_facts_changed=(True if old_collision_facts is not None else False),
            error_status=exc.error_status,
            error_message=exc.detail_message,
            line_number=exc.line_number,
            column_number=exc.column_number,
        )

    try:
        new_reexport_facts = _extract_reexport_facts(
            module_path,
            parsed_tree,
        )
    except Exception as exc:
        return PreparedSourceUpdate(
            module_path=module_path,
            is_new=is_new,
            new_imports=[],
            new_artifacts={},
            new_usage=None,
            delta=FileDelta(module_path=module_path, is_new=is_new),
            usage_delta=None,
            error_status="ERROR",
            error_message=f"re-export extraction failed: {exc}",
        )

    extracted_lineage_facts = None
    if source_key is not None:
        try:
            extracted_lineage_facts = extract_lineage_source_facts(
                parsed_tree,
                source_key=source_key,
                source_fingerprint=parsed_input.source_fingerprint,
            )
        except Exception as exc:
            return PreparedSourceUpdate(
                module_path=module_path,
                is_new=is_new,
                new_imports=[],
                new_artifacts={},
                new_usage=None,
                delta=FileDelta(module_path=module_path, is_new=is_new),
                usage_delta=None,
                new_collision_facts=None,
                collision_facts_changed=(True if old_collision_facts is not None else False),
                error_status="ERROR",
                error_message=f"lineage extraction failed: {exc}",
            )

    # 2. Extract imports
    try:
        from contextor.core.symbol_engine.indexer import read_imports
        new_imports, error = read_imports(path, tree=parsed_tree)
        if error:
            return PreparedSourceUpdate(
                module_path=module_path,
                is_new=is_new,
                new_imports=[],
                new_artifacts={},
                new_usage=None,
                delta=FileDelta(module_path=module_path, is_new=is_new),
                usage_delta=None,
                new_collision_facts=None,
                collision_facts_changed=True if old_collision_facts is not None else False,
                error_status="SYNTAX_ERROR",
                error_message=str(error),
            )
    except Exception as exc:
        return PreparedSourceUpdate(
            module_path=module_path,
            is_new=is_new,
            new_imports=[],
            new_artifacts={},
            new_usage=None,
            delta=FileDelta(module_path=module_path, is_new=is_new),
            usage_delta=None,
            new_collision_facts=None,
            collision_facts_changed=True if old_collision_facts is not None else False,
            error_status="ERROR",
            error_message=str(exc),
        )

    # 3. Extract symbols & artifacts
    try:
        from contextor.core.reporting_layer.artifact_usage_report import (
            extract_file_symbols,
            _module_own_symbols,
        )
        raw_symbols = extract_file_symbols(str(path), tree=parsed_tree)
        own_symbols = _module_own_symbols(raw_symbols)
        old_consumers = (old_artifacts or {}).get("consumers", {})
        new_artifacts = {
            "symbols": raw_symbols,
            "own_symbols": own_symbols,
            "consumers": old_consumers,
        }
    except Exception:
        old_consumers = (old_artifacts or {}).get("consumers", {})
        new_artifacts = {"symbols": {}, "own_symbols": set(), "consumers": old_consumers}

    # 4. Extract collision facts
    from contextor.core.validator.collisions import extract_module_collision_facts
    new_collision_facts = extract_module_collision_facts(
        parsed_tree,
        module_path,
        str(path.resolve()),
    )
    if old_collision_facts is None:
        collision_facts_changed = True
    else:
        collision_facts_changed = _collision_facts_differ(old_collision_facts, new_collision_facts)

    # 5. Calculate FileDelta
    delta = calculate_file_delta(
        module_path=module_path,
        persistent_id=persistent_id,
        is_new=is_new,
        old_module=old_module,
        old_artifacts=old_artifacts,
        new_imports=new_imports,
        new_artifacts_dict=new_artifacts,
    )
    if (
        not is_new
        and old_reexport_facts != new_reexport_facts
    ):
        delta.metadata_changes[
            "reexport_facts_changed"
        ] = True

    # 6. Extract Usage facts & UsageDelta
    from contextor.core.reference.engine import extract_module_usage_facts
    new_usage = extract_module_usage_facts(
        module_path,
        parsed_tree,
        imports=new_imports,
    )
    curr_old_usage = old_usage if old_usage is not None else ModuleUsageFacts()
    usage_delta = diff_usage_facts(module_path, curr_old_usage, new_usage)

    return PreparedSourceUpdate(
        module_path=module_path,
        is_new=is_new,
        new_imports=new_imports,
        new_artifacts=new_artifacts,
        new_usage=new_usage,
        delta=delta,
        usage_delta=usage_delta,
        new_collision_facts=new_collision_facts,
        collision_facts_changed=collision_facts_changed,
        extracted_lineage_facts=extracted_lineage_facts,
        new_reexport_facts=new_reexport_facts,
    )
```

### _prepare_candidate_state

Source: `C:\Temp\Contextor_Repo\contextor\core\analysis\incremental\plan_executor.py : 681-765`

```python
def _prepare_candidate_state(state: RepositoryAnalysisState) -> CandidateState:
    """Initializes Copy-on-Write candidate state from current canonical state."""
    raw_parse_freshness = getattr(
        state,
        "module_parse_freshness",
        {},
    )
    if not isinstance(raw_parse_freshness, dict):
        raise ValueError(
            "Canonical module_parse_freshness is invalid; "
            "fresh full analysis is required."
        )
    return CandidateState(
        modules=dict(state.modules),
        reexport_facts_by_module=dict(
            getattr(
                state,
                "reexport_facts_by_module",
                {},
            )
            or {}
        ),
        artifacts=dict(state.artifacts),
        module_parse_freshness=dict(raw_parse_freshness),
        syntax_diagnostics_by_path=dict(getattr(state, "syntax_diagnostics_by_path", {}) or {}),
        syntax_diagnostics_state=getattr(state, "syntax_diagnostics_state", "not_materialized"),
        module_usages=dict(getattr(state, "module_usages", {}) or {}),
        lineage_facts_by_source=dict(
            getattr(state, "lineage_facts_by_source", {}) or {}
        ),
        lineage_facts_state=(
            getattr(state, "lineage_facts_state", "not_materialized")
            or "not_materialized"
        ),
        lineage_facts_semantic_version=getattr(
            state,
            "lineage_facts_semantic_version",
            None,
        ),
        lineage_owner_source_index=dict(
            getattr(state, "lineage_owner_source_index", {}) or {}
        ),
        lineage_source_owner_index=dict(
            getattr(state, "lineage_source_owner_index", {}) or {}
        ),
        lineage_query_index_state=getattr(
            state,
            "lineage_query_index_state",
            "not_materialized",
        ),
        lineage_semantic_anchor_bindings_complete=bool(
            getattr(state, "lineage_semantic_anchor_bindings_complete", False)
        ),
        artifact_consumption=dict(state.artifact_consumption or {}),
        dependency_graph=state.dependency_graph,
        trie=state.trie,
        package_root=state.package_root,
        metrics=state.metrics,
        topology_analytics=dict(getattr(state, "topology_analytics", {}) or {}),
        dependency_matrix=dict(
            getattr(state, "dependency_matrix", {}) or {}
        ),
        dependency_matrix_state=getattr(
            state,
            "dependency_matrix_state",
            "deferred",
        ),
        shared_usage_clusters=list(
            getattr(state, "shared_usage_clusters", []) or []
        ),
        shared_usage_clusters_state=getattr(
            state,
            "shared_usage_clusters_state",
            "deferred",
        ),
        cached_analytics=dict(getattr(state, "cached_analytics", {}) or {}),
        topology_metrics_state=getattr(state, "topology_metrics_state", "deferred"),
        cached_analytics_state=getattr(state, "cached_analytics_state", "deferred"),
        cycles=list(getattr(state, "cycles", []) or []),
        cycles_state=getattr(state, "cycles_state", "deferred"),
        collision_facts=dict(getattr(state, "collision_facts", {}) or {}),
        collisions=list(getattr(state, "collisions", []) or []),
        collisions_state=getattr(state, "collisions_state", "deferred"),
        artifact_consumption_state=getattr(state, "artifact_consumption_state", "deferred"),
    )
```

### _apply_delta_and_commit

Source: `C:\Temp\Contextor_Repo\contextor\core\analysis\incremental\engine.py : 760-1018`

```python
    def _apply_delta_and_commit(
        self,
        file_path: str,
        delta: FileDelta,
        usage_delta: Any,
        plan: Any,
        new_imports: list,
        mod_artifacts: dict,
        new_usage: Any,
        new_collision_facts: Optional[List[Dict[str, Any]]] = None,
        new_reexport_facts: Optional[Dict[str, Any]] = None,
        extracted_lineage_facts: Any | None = None,
        syntax_source_path: str | None = None,
        syntax_fact: Dict[str, Any] | None = None,
        remove_syntax_fact: bool = False,
        clear_parse_module: str | None = None,
    ) -> tuple[Set[str], bool, dict]:
        """
        Executes planned RefreshPlan phases and performs atomic persistent & RAM commit.
        """
        resync_required = bool(getattr(self.state, "resync_required", False))
        execute_started = time.monotonic()
        _trace_incremental_phase(
            "INCREMENTAL_EXECUTE_PLAN_START",
        )
        try:
            outcome = execute_refresh_plan(
                state=self.state,
                delta=delta,
                usage_delta=usage_delta,
                plan=plan,
                new_imports=new_imports,
                new_artifacts=mod_artifacts,
                new_usage=new_usage,
                root_path=self.root_path,
                file_path=file_path,
                new_collision_facts=new_collision_facts,
                new_reexport_facts=new_reexport_facts,
            )
        except Exception as exc:
            _trace_incremental_phase(
                "INCREMENTAL_EXECUTE_PLAN_FAIL",
                started=execute_started,
                error=str(exc),
            )
            raise
        _trace_incremental_phase(
            "INCREMENTAL_EXECUTE_PLAN_END",
            started=execute_started,
            result=(
                f"identity_sync_required="
                f"{outcome.identity_sync_required};"
                f"patch_families="
                f"{','.join(outcome.execution_trace.get('patch_families', ()))};"
                f"recompute_count="
                f"{len(outcome.execution_trace.get('recompute_modules', ()))};"
                f"graph_count="
                f"{len(outcome.execution_trace.get('graph_recomputations', ()))}"
            ),
        )

        candidate = outcome.candidate_state

        # Persistent identity sync and lineage materialization share one registry view.
        if outcome.identity_sync_required:
            try:
                with self.registry.transaction():
                    registry_started = time.monotonic()
                    _trace_incremental_phase(
                        "INCREMENTAL_REGISTRY_SYNC_START",
                        count=len(outcome.current_artifacts),
                    )
                    try:
                        self.registry.sync_with_workspace(
                            outcome.all_modules,
                            outcome.current_artifacts,
                        )
                    except Exception as exc:
                        _trace_incremental_phase(
                            "INCREMENTAL_REGISTRY_SYNC_FAIL",
                            started=registry_started,
                            error=str(exc),
                        )
                        raise
                    missing_after_sync = sorted(
                        outcome.current_artifacts
                        - set(
                            self.registry._state[
                                "artifact_registry"
                            ]["path_to_id"]
                        )
                    )
                    _trace_incremental_phase(
                        "INCREMENTAL_REGISTRY_SYNC_END",
                        started=registry_started,
                        count=len(missing_after_sync),
                        result=(
                            "missing_after_sync="
                            + ",".join(
                                missing_after_sync[:5]
                            )
                        ),
                    )

                    lineage_started = time.monotonic()
                    _trace_incremental_phase(
                        "INCREMENTAL_LINEAGE_START",
                        result="rematerialize_all=true",
                    )
                    try:
                        self._update_candidate_lineage_slice(
                            candidate,
                            source_path=(
                                syntax_source_path or ""
                            ),
                            extracted_lineage_facts=(
                                extracted_lineage_facts
                            ),
                            delete=bool(
                                getattr(
                                    delta,
                                    "is_deleted",
                                    False,
                                )
                            ),
                            rematerialize_all=True,
                        )
                    except Exception as exc:
                        _trace_incremental_phase(
                            "INCREMENTAL_LINEAGE_FAIL",
                            started=lineage_started,
                            error=str(exc),
                        )
                        raise
                    _trace_incremental_phase(
                        "INCREMENTAL_LINEAGE_END",
                        started=lineage_started,
                        result="rematerialize_all=true",
                    )
            except Exception:
                # A failed write transaction leaves no persisted commit; reload its
                # in-memory view before exposing the registry again.
                with self.registry.read_transaction():
                    pass
                raise
        elif extracted_lineage_facts is not None or bool(
            getattr(delta, "is_deleted", False)
        ):
            _trace_incremental_phase(
                "INCREMENTAL_REGISTRY_SYNC_SKIP",
                result="identity_sync_required=false",
            )
            with self.registry.read_transaction():
                lineage_started = time.monotonic()
                _trace_incremental_phase(
                    "INCREMENTAL_LINEAGE_START",
                    result="rematerialize_all=false",
                )
                try:
                    self._update_candidate_lineage_slice(
                        candidate,
                        source_path=(
                            syntax_source_path or ""
                        ),
                        extracted_lineage_facts=(
                            extracted_lineage_facts
                        ),
                        delete=bool(
                            getattr(
                                delta,
                                "is_deleted",
                                False,
                            )
                        ),
                    )
                except Exception as exc:
                    _trace_incremental_phase(
                        "INCREMENTAL_LINEAGE_FAIL",
                        started=lineage_started,
                        error=str(exc),
                    )
                    raise
                _trace_incremental_phase(
                    "INCREMENTAL_LINEAGE_END",
                    started=lineage_started,
                    result="rematerialize_all=false",
                )

        # Canonical State Publication
        if remove_syntax_fact and syntax_source_path is not None:
            candidate.syntax_diagnostics_by_path.pop(syntax_source_path, None)
        elif syntax_fact is not None and syntax_source_path is not None:
            candidate.syntax_diagnostics_by_path[syntax_source_path] = syntax_fact
        if clear_parse_module is not None:
            clear_module_parse_failure(candidate, clear_parse_module)
        self.state.modules = candidate.modules
        self.state.reexport_facts_by_module = (
            candidate.reexport_facts_by_module
        )
        self.state.artifacts = candidate.artifacts
        self.state.module_parse_freshness = candidate.module_parse_freshness
        self.state.syntax_diagnostics_by_path = candidate.syntax_diagnostics_by_path
        self.state.syntax_diagnostics_state = candidate.syntax_diagnostics_state
        self.state.dependency_graph = candidate.dependency_graph
        self.state.metrics = candidate.metrics
        self.state.topology_analytics = candidate.topology_analytics
        self.state.cached_analytics = candidate.cached_analytics
        self.state.dependency_matrix = candidate.dependency_matrix
        self.state.dependency_matrix_state = candidate.dependency_matrix_state
        self.state.shared_usage_clusters = candidate.shared_usage_clusters
        self.state.shared_usage_clusters_state = candidate.shared_usage_clusters_state
        self.state.topology_metrics_state = candidate.topology_metrics_state
        self.state.cached_analytics_state = candidate.cached_analytics_state
        self.state.cycles = candidate.cycles
        self.state.cycles_state = candidate.cycles_state
        self.state.collision_facts = candidate.collision_facts
        self.state.collisions = candidate.collisions
        self.state.collisions_state = candidate.collisions_state
        self.state.artifact_consumption = candidate.artifact_consumption
        if (
            candidate.artifact_consumption_state != "stale"
            and not resync_required
            and validate_canonical_artifact_consumption_coverage(candidate.artifact_consumption, candidate.artifacts)
        ):
            self.state.artifact_consumption_state = "fresh"
        else:
            self.state.artifact_consumption_state = "stale"
        if resync_required:
            # A lost incremental continuity is authoritative until a full
            # rebuild replaces this state; an incremental candidate cannot
            # certify it fresh again.
            self.state.resync_required = True
        self.state.module_usages = candidate.module_usages
        self.state.lineage_facts_by_source = candidate.lineage_facts_by_source
        self.state.lineage_facts_state = candidate.lineage_facts_state
        self.state.lineage_facts_semantic_version = (
            candidate.lineage_facts_semantic_version
        )
        self.state.lineage_owner_source_index = candidate.lineage_owner_source_index
        self.state.lineage_source_owner_index = candidate.lineage_source_owner_index
        self.state.lineage_query_index_state = candidate.lineage_query_index_state
        self.state.lineage_semantic_anchor_bindings_complete = (
            candidate.lineage_semantic_anchor_bindings_complete
        )
        self.state.trie = candidate.trie
        self.state.package_root = candidate.package_root

        # FileStateManager acknowledgement
        file_state_started = time.monotonic()
        _trace_incremental_phase(
            "INCREMENTAL_FILE_STATE_START",
        )
        self.state_manager.update_state(file_path)
        _trace_incremental_phase(
            "INCREMENTAL_FILE_STATE_END",
            started=file_state_started,
        )

        return outcome.affected_modules, outcome.blast_radius_complete, outcome.execution_trace
```

### save_snapshot

Source: `C:\Temp\Contextor_Repo\contextor\core\live_state\store.py : 1507-1918`

```python
def save_snapshot(
    state: Any,
    cache_dir: str | Path,
    state_id: str,
    *,
    writer: str = "unknown",
    repo_id: str = "",
    root_path: str = "",
    revision_floor: int = 0,
    exact_revision: int | None = None,
    file_state_payload: dict[str, Any] | None = None,
    previous_state: Any = None,
    migration_file_state_source: str | Path | None = None,
    migration_only_if_absent: bool = False,
) -> LiveStateMetadata:
    """Atomically publish a complete snapshot and monotonically increasing revision."""

    from contextor.core.analysis.state_manager import (
        RepositoryAnalysisState,
    )
    from contextor.core.reference.shared import (
        validate_reexport_facts_by_module,
    )

    if isinstance(state, RepositoryAnalysisState) and not validate_reexport_facts_by_module(
        getattr(
            state,
            "reexport_facts_by_module",
            None,
        ),
        state.modules,
    ):
        raise ValueError(
            "Cannot persist RepositoryAnalysisState with incomplete "
            "canonical re-export facts."
        )

    if migration_file_state_source is not None and (
        exact_revision is not None
        or not migration_only_if_absent
    ):
        raise ValueError(
            "Migration FileState source requires a non-exact "
            "migration-only snapshot commit."
        )

    state_file, meta_file, lock_file = _paths(cache_dir)
    state_file.parent.mkdir(parents=True, exist_ok=True)
    lock_fd = _acquire_lock(lock_file)
    token = uuid.uuid4().hex
    state_tmp = state_file.with_name(f".{state_file.name}.{token}.tmp")
    meta_tmp = meta_file.with_name(f".{meta_file.name}.{token}.tmp")
    generation_state = state_tmp
    generation_file_state: Path | None = None
    generation_lineage_manifest: Path | None = None
    generation_lineage_chunks: list[Path] = []
    reusable_lineage_sources: dict[str, Any] = {}
    committed = False
    migration_file_state_target = state_file.parent / "file_state.json"
    migration_file_state_temp = state_file.parent / f".file_state.{token}.tmp"
    migration_file_state_created = False

    try:
        current = read_metadata(cache_dir)
        if migration_only_if_absent and current is not None:
            return current

        normalized_root = (
            str(Path(root_path).expanduser().resolve())
            if root_path
            else ""
        )

        if (
            current
            and repo_id
            and current.repo_id
            and current.repo_id != repo_id
        ):
            raise ValueError(
                "Snapshot repository ID does not match existing metadata."
            )

        if (
            current
            and normalized_root
            and current.root_path
            and Path(current.root_path).expanduser().resolve()
            != Path(normalized_root)
        ):
            raise ValueError(
                "Snapshot repository root does not match existing metadata."
            )

        if exact_revision is not None:
            if (
                isinstance(exact_revision, bool)
                or not isinstance(exact_revision, int)
                or exact_revision < 0
            ):
                raise ValueError(
                    "exact_revision must be a non-negative integer."
                )

            current_revision = (
                current.revision
                if current is not None
                else None
            )

            if (
                current_revision is None
                and exact_revision != 1
            ):
                raise SnapshotRevisionConflict(
                    None,
                    exact_revision,
                )

            if (
                current_revision is not None
                and exact_revision
                != current_revision + 1
            ):
                raise SnapshotRevisionConflict(
                    current_revision,
                    exact_revision,
                )

            next_revision = exact_revision

            generation_state = (
                state_file.parent
                / (
                    f"engine_state.r{exact_revision}."
                    f"{token}.pkl"
                )
            )

            generation_file_state = (
                state_file.parent
                / (
                    f"file_state.r{exact_revision}."
                    f"{token}.json"
                )
            )

            if _supports_split_lineage_generation(
                state
            ):
                generation_lineage_manifest = (
                    state_file.parent
                    / (
                        f"lineage_manifest.r{exact_revision}."
                        f"{token}.json"
                    )
                )

                reusable_lineage_sources = (
                    _reusable_lineage_manifest_sources(
                        cache_dir,
                        current,
                        previous_state,
                    )
                )

        else:
            next_revision = (
                max(
                    current.revision
                    if current
                    else 0,
                    revision_floor,
                )
                + 1
            )

        metadata = LiveStateMetadata(
            state_id=state_id,
            revision=next_revision,
            writer=writer,
            repo_id=repo_id,
            root_path=normalized_root,
            state_file=(
                generation_state.name
                if exact_revision is not None
                else ""
            ),
            file_state_file=(
                generation_file_state.name
                if generation_file_state is not None
                else ""
            ),
            lineage_manifest_file=(
                generation_lineage_manifest.name
                if generation_lineage_manifest is not None
                else ""
            ),
        )

        if (
            exact_revision is not None
            and isinstance(
                state,
                dict,
            )
        ):
            state["revision"] = metadata.revision
            state["state_id"] = metadata.state_id

        elif (
            state is not None
            and hasattr(
                state,
                "__dict__",
            )
        ):
            try:
                setattr(
                    state,
                    "state_id",
                    metadata.state_id,
                )
                setattr(
                    state,
                    "revision",
                    metadata.revision,
                )
            except AttributeError:
                pass

        state_to_persist = state

        if (
            generation_lineage_manifest
            is not None
        ):
            (
                state_to_persist,
                generation_lineage_chunks,
            ) = _write_split_lineage_generation(
                state,
                generation_lineage_manifest,
                state_id=metadata.state_id,
                revision=metadata.revision,
                token=token,
                previous_state=previous_state,
                reusable_sources=reusable_lineage_sources,
            )

        with generation_state.open(
            "wb"
        ) as stream:
            pickle.dump(
                {
                    "metadata": asdict(
                        metadata
                    ),
                    "state": state_to_persist,
                },
                stream,
            )
            stream.flush()
            os.fsync(
                stream.fileno()
            )

        if generation_file_state is not None:
            if (
                not isinstance(
                    file_state_payload,
                    dict,
                )
                or not isinstance(
                    file_state_payload.get(
                        "_meta"
                    ),
                    dict,
                )
            ):
                raise ValueError(
                    "file_state_payload must contain a _meta mapping."
                )

            payload_meta = file_state_payload[
                "_meta"
            ]

            if (
                payload_meta.get(
                    "state_id",
                    "",
                )
                != state_id
            ):
                raise ValueError(
                    "FileState payload state_id does not match snapshot state_id."
                )

            if (
                payload_meta.get(
                    "revision"
                )
                != exact_revision
            ):
                raise ValueError(
                    "FileState payload revision does not match exact_revision."
                )

            with generation_file_state.open(
                "w",
                encoding="utf-8",
            ) as stream:
                json.dump(
                    file_state_payload,
                    stream,
                    indent=2,
                )
                stream.flush()
                os.fsync(
                    stream.fileno()
                )

        with meta_tmp.open(
            "w",
            encoding="utf-8",
        ) as stream:
            json.dump(
                asdict(
                    metadata
                ),
                stream,
                indent=2,
            )
            stream.flush()
            os.fsync(
                stream.fileno()
            )

        if exact_revision is None:
            os.replace(
                generation_state,
                state_file,
            )

        if migration_file_state_source is not None:
            source_file = Path(migration_file_state_source)
            if (
                source_file.is_file()
                and not migration_file_state_target.exists()
            ):
                shutil.copy2(source_file, migration_file_state_temp)
                with migration_file_state_temp.open("ab") as stream:
                    stream.flush()
                    os.fsync(stream.fileno())
                os.replace(
                    migration_file_state_temp,
                    migration_file_state_target,
                )
                migration_file_state_created = True

        os.replace(
            meta_tmp,
            meta_file,
        )

        committed = True

        return metadata

    finally:
        for temporary in (
            state_tmp,
            meta_tmp,
        ):
            try:
                temporary.unlink()
            except OSError:
                pass

        if (
            not committed
            and exact_revision is not None
        ):
            failed_generations = [
                generation_state,
                generation_file_state,
                generation_lineage_manifest,
                *generation_lineage_chunks,
            ]

            for temporary in failed_generations:
                if temporary is None:
                    continue

                try:
                    temporary.unlink()
                except OSError:
                    pass

        if not committed and migration_file_state_created:
            try:
                migration_file_state_target.unlink(missing_ok=True)
            except OSError:
                pass

        try:
            migration_file_state_temp.unlink(missing_ok=True)
        except OSError:
            pass

        _release_lock(lock_fd)
```

### RepositoryAnalysisState.clone_for_update

Source: `C:\Temp\Contextor_Repo\contextor\core\analysis\state_manager.py : 131-168`

```python
    def clone_for_update(self) -> "RepositoryAnalysisState":
        """
        Create an execution-local LIVE update candidate using structural
        top-level Copy-On-Write.

        The outer state object is shallow-copied so dynamic runtime
        attributes such as revision, provenance, state_id, and
        resync_required are preserved on the candidate without sharing
        the state holder itself.

        Every declared top-level dict/list/set field receives its own
        shallow container. Nested values remain structurally shared and
        continue to rely on the existing family-level Copy-On-Write
        contracts in the incremental pipeline.
        """
        candidate = copy.copy(self)

        for state_field in fields(self):
            value = getattr(
                self,
                state_field.name,
            )

            if isinstance(
                value,
                (
                    dict,
                    list,
                    set,
                ),
            ):
                setattr(
                    candidate,
                    state_field.name,
                    copy.copy(value),
                )

        return candidate
```

### test_local_fallback_syntax_error_and_recovery_survive_snapshot_hydration

Source: `C:\Temp\Contextor_Repo\tests\test_mcp_incremental_hydration.py : 2080-2115`

```python
def test_local_fallback_syntax_error_and_recovery_survive_snapshot_hydration(
    tmp_path, monkeypatch
):
    repo, provider, engine = _build_local_fallback_engine(
        tmp_path, monkeypatch, "def run():\n    return 1\n"
    )
    original_module = deepcopy(engine.state.modules["provider"])
    original_artifacts = deepcopy(engine.state.artifacts["provider"])

    provider.write_text("def run(:\n    return 1\n", encoding="utf-8")
    syntax_error = _local_update(repo, provider)
    assert syntax_error["status"] == "SYNTAX_ERROR"
    assert syntax_error["live_state_persisted"] is True

    syntax_hydrated = _rehydrate_local_engine(repo)
    assert syntax_hydrated is not None
    assert syntax_hydrated.state.modules["provider"] == original_module
    assert syntax_hydrated.state.artifacts["provider"] == original_artifacts
    assert syntax_hydrated.state.module_parse_freshness["provider"]["state"] == "stale"
    assert (
        syntax_hydrated.state.syntax_diagnostics_by_path["provider.py"]["status"]
        == "checked_with_errors"
    )

    provider.write_text("def run():\n    return 2\n", encoding="utf-8")
    recovered = _local_update(repo, provider)
    assert recovered["status"] == "RECOVERED"
    assert recovered["live_state_persisted"] is True

    recovered_hydrated = _rehydrate_local_engine(repo)
    assert recovered_hydrated is not None
    assert "provider" not in recovered_hydrated.state.module_parse_freshness
    assert (
        recovered_hydrated.state.syntax_diagnostics_by_path["provider.py"]["status"]
        == "checked_and_none"
    )
```

### test_two_mcp_processes_cannot_enter_local_candidate_concurrently

Source: `C:\Temp\Contextor_Repo\tests\test_mcp_incremental_hydration.py : 752-820`

```python
def test_two_mcp_processes_cannot_enter_local_candidate_concurrently(
    tmp_path, monkeypatch
):
    repo, provider, engine = _build_local_fallback_engine(
        tmp_path, monkeypatch, "def run():\n    return 1\n"
    )
    assert update_file_module._persist_live_engine(repo, engine) is True
    provider.write_text("def run():\n    return 2\n", encoding="utf-8")
    extra = repo / "extra.py"
    extra.write_text("value = 3\n", encoding="utf-8")
    ctx = multiprocessing.get_context("spawn")
    entered = ctx.Event()
    release = ctx.Event()
    ready = ctx.Event()
    update_started = ctx.Event()
    results = ctx.Queue()
    cache_root = os.environ["CONTEXTOR_CACHE_DIR"]
    first = ctx.Process(
        target=_cross_process_local_candidate_worker,
        args=(
            str(repo), str(provider), cache_root, entered, release, ready,
            update_started, results, True,
        ),
    )
    second = ctx.Process(
        target=_cross_process_local_candidate_worker,
        args=(
            str(repo), str(extra), cache_root, entered, release, ready,
            update_started, results, False,
        ),
    )
    try:
        first.start()
        assert entered.wait(15)
        second.start()
        assert ready.wait(15)
        assert not update_started.wait(0.4)
    finally:
        release.set()
        first.join(15)
        if second.pid is not None:
            second.join(15)
        if first.is_alive():
            first.terminate()
            first.join(5)
        if second.pid is not None and second.is_alive():
            second.terminate()
            second.join(5)

    assert first.exitcode == 0
    assert second.exitcode == 0
    received = [
        results.get(timeout=5),
        results.get(timeout=5),
    ]
    by_role = {
        item["role"]: item["response"]
        for item in received
    }
    assert set(by_role) == {"first", "second"}

    first_result = by_role["first"]
    second_result = by_role["second"]

    assert first_result["status"] == "UPDATED"
    assert second_result["status"] == "ERROR"
    assert "stale" in second_result.get("error", "").lower()
    assert not update_started.is_set()
    assert read_metadata(repo_cache_dir(repo)).revision == 2
```

### test_syntax_diagnostics_snapshot_roundtrip_needs_no_source_reconstruction

Source: `C:\Temp\Contextor_Repo\tests\test_syntax_diagnostics_full_analysis.py : 89-109`

```python
def test_syntax_diagnostics_snapshot_roundtrip_needs_no_source_reconstruction(tmp_path, monkeypatch):
    facts = {
        "broken.py": {
            "status": "checked_with_errors",
            "errors": [{"message": "invalid syntax", "line_number": 2, "column_number": 4}],
        }
    }
    state = RepositoryAnalysisState(
        syntax_diagnostics_by_path=facts,
        syntax_diagnostics_state="fresh",
    )
    save_snapshot(state, tmp_path, "syntax-state")

    monkeypatch.setattr(
        "contextor.core.source.ast.parse",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("hydration must not parse source")),
    )
    loaded, _ = load_snapshot(tmp_path, "syntax-state")

    assert loaded.syntax_diagnostics_by_path == facts
    assert loaded.syntax_diagnostics_state == "fresh"
```

### test_legacy_snapshot_marks_syntax_family_not_materialized

Source: `C:\Temp\Contextor_Repo\tests\test_syntax_diagnostics_full_analysis.py : 112-119`

```python
def test_legacy_snapshot_marks_syntax_family_not_materialized(tmp_path):
    legacy = SimpleNamespace(modules={}, dependency_graph=None)
    save_snapshot(legacy, tmp_path, "legacy-syntax")

    loaded, _ = load_snapshot(tmp_path, "legacy-syntax")

    assert loaded.syntax_diagnostics_by_path == {}
    assert loaded.syntax_diagnostics_state == "not_materialized"
```

### test_live_incremental_syntax_lifecycle_is_source_scoped_and_revision_atomic

Source: `C:\Temp\Contextor_Repo\tests\test_syntax_diagnostics_full_analysis.py : 204-270`

```python
def test_live_incremental_syntax_lifecycle_is_source_scoped_and_revision_atomic(tmp_path, monkeypatch):
    monkeypatch.setenv("CONTEXTOR_DISABLE_PROCESS_POOL", "1")
    source, server, _ = _live_syntax_fixture(tmp_path)
    try:
        source.write_text("def value():\n    return 2\n", encoding="utf-8")
        valid = server._dispatch({"operation": "update_file", "file_path": str(source), "origin": "desktop_watcher"})
        assert valid["revision"] == 1
        assert valid["result"].status == "UPDATED"
        assert server._state.syntax_diagnostics_state == "fresh"
        assert server._state.syntax_diagnostics_by_path["provider.py"] == {
            "status": "checked_and_none", "errors": []
        }

        source.write_text("def value(\n", encoding="utf-8")
        broken = server._dispatch({"operation": "update_file", "file_path": str(source), "origin": "desktop_watcher"})
        assert broken["revision"] == 2
        assert broken["result"].status == "SYNTAX_ERROR"
        assert server._state.syntax_diagnostics_state == "fresh"
        assert server._state.syntax_diagnostics_by_path["provider.py"] == {
            "status": "checked_with_errors",
            "errors": [{
                "message": "'(' was never closed",
                "line_number": 1,
                "column_number": 10,
            }],
        }
        assert server._state.module_parse_freshness["provider"]["state"] == "stale"
        assert "value" in server._state.artifacts["provider"]["own_symbols"]

        source.write_text("def value():\n    return 3\n", encoding="utf-8")
        repaired = server._dispatch({"operation": "update_file", "file_path": str(source), "origin": "desktop_watcher"})
        assert repaired["revision"] == 3
        assert repaired["result"].status == "RECOVERED"
        assert server._state.syntax_diagnostics_by_path["provider.py"] == {
            "status": "checked_and_none", "errors": []
        }
        assert server._state.module_parse_freshness == {}

        added = tmp_path / "added.py"
        added.write_text("answer = 42\n", encoding="utf-8")
        new_valid = server._dispatch({"operation": "update_file", "file_path": str(added), "origin": "desktop_watcher"})
        assert new_valid["revision"] == 4
        assert server._state.syntax_diagnostics_by_path["added.py"] == {
            "status": "checked_and_none", "errors": []
        }

        broken_added = tmp_path / "new_broken.py"
        broken_added.write_text("def missing(\n", encoding="utf-8")
        new_invalid = server._dispatch({"operation": "update_file", "file_path": str(broken_added), "origin": "desktop_watcher"})
        assert new_invalid["revision"] == 5
        assert new_invalid["result"].status == "SYNTAX_ERROR"
        assert server._state.syntax_diagnostics_by_path["new_broken.py"]["status"] == "checked_with_errors"
        assert "new_broken" not in server._state.modules

        added.unlink()
        deleted = server._dispatch({"operation": "update_file", "file_path": str(added), "origin": "desktop_watcher"})
        assert deleted["revision"] == 6
        assert deleted["result"].status == "DELETED"
        assert "added.py" not in server._state.syntax_diagnostics_by_path

        events = server._dispatch({"operation": "get_events", "after_revision": 0, "limit": None})
        assert any(
            event["origin"] == "desktop_watcher" and event["status"] == "SYNTAX_ERROR"
            for event in events["events"]
        )
    finally:
        server.close()
```

### test_local_candidate_syntax_lkg_recovery_and_unchanged_publish_after_persist

Source: `C:\Temp\Contextor_Repo\tests\test_mcp_incremental_hydration.py : 1030-1092`

```python
def test_local_candidate_syntax_lkg_recovery_and_unchanged_publish_after_persist(
    tmp_path, monkeypatch
):
    repo, provider, original = _build_local_fallback_engine(
        tmp_path, monkeypatch, "def run():\n    return 1\n"
    )
    assert update_file_module._persist_live_engine(repo, original) is True
    key = str(repo.resolve())
    original_module = original.state.modules["provider"]
    real_persist = update_file_module._persist_live_engine
    calls = []

    def assert_before_publish(root, candidate):
        calls.append((mcp_runtime._live_engines[key], candidate))
        return real_persist(root, candidate)

    monkeypatch.setattr(update_file_module, "_persist_live_engine", assert_before_publish)
    early = _local_update(repo, provider)
    assert early["status"] == "UNCHANGED"
    assert early["live_state_persisted"] is True
    assert calls[-1][0] is original
    early_engine = mcp_runtime._live_engines[key]
    assert early_engine is not original

    stat = provider.stat()
    os.utime(provider, (stat.st_atime, stat.st_mtime + 2))
    reconciled = _local_update(repo, provider)
    assert reconciled["status"] in {"UPDATED", "UNCHANGED"}
    assert reconciled["live_state_persisted"] is True
    reconciled_engine = mcp_runtime._live_engines[key]
    assert reconciled_engine is not early_engine
    assert calls[-1][0] is early_engine

    stat = provider.stat()
    os.utime(provider, (stat.st_atime, stat.st_mtime + 2))
    parsed = _local_update(repo, provider)
    assert parsed["status"] == "UNCHANGED"
    assert parsed["live_state_persisted"] is True
    parsed_engine = mcp_runtime._live_engines[key]
    assert parsed_engine is not reconciled_engine
    assert calls[-1][0] is reconciled_engine

    provider.write_text("def run(:\n    return 1\n", encoding="utf-8")
    syntax = _local_update(repo, provider)
    assert syntax["status"] == "SYNTAX_ERROR"
    assert syntax["live_state_persisted"] is True
    stale_engine = mcp_runtime._live_engines[key]
    assert stale_engine is not parsed_engine
    assert calls[-1][0] is parsed_engine
    assert stale_engine.state.modules["provider"] is original_module
    assert stale_engine.state.module_parse_freshness["provider"]["state"] == "stale"
    assert "provider" not in original.state.module_parse_freshness

    provider.write_text("def run():\n    return 2\n", encoding="utf-8")
    recovered = _local_update(repo, provider)
    assert recovered["status"] == "RECOVERED"
    assert recovered["live_state_persisted"] is True
    fresh_engine = mcp_runtime._live_engines[key]
    assert fresh_engine is not stale_engine
    assert calls[-1][0] is stale_engine
    assert "provider" not in fresh_engine.state.module_parse_freshness
    assert stale_engine.state.module_parse_freshness["provider"]["state"] == "stale"
    assert read_metadata(repo_cache_dir(repo)).revision == 6
```

### IncrementalAnalysisEngine.update_file — complete contiguous implementation, part 1

Source: `C:\Temp\Contextor_Repo\contextor\core\analysis\incremental\engine.py : 453-600`

```python
    def update_file(self, file_path: str) -> IncrementalUpdateResult:
        """
        Updates the canonical state incrementally for a single changed file.
        Returns the update status and the freshness of the architectural model.
        """
        with self._lock:
            if getattr(self.state, "resync_required", False):
                # Every exit path, including a semantic no-op, must expose the
                # already-lost incremental continuity as fail-closed.
                self.state.artifact_consumption_state = "stale"
            path = Path(file_path)
            rel_path = path.relative_to(self.root_path)
            module_path = ".".join(rel_path.with_suffix("").parts)
            source_path = canonical_python_source_path(rel_path.as_posix())
            if source_path is None:
                raise ValueError(f"Incremental source path is not canonical Python: {file_path}")

            if (
                not self.state_manager.has_changed(file_path)
                and module_path in self.state.modules
            ):
                return IncrementalUpdateResult(
                    status="UNCHANGED",
                    file_path=file_path,
                    graph_state="fresh" if self.state.dependency_graph is not None else "stale",
                    dependencies_state="fresh",
                    blast_radius_state="deferred",
                    local_metrics_state="deferred",
                    global_metrics_state="deferred",
                    topology_metrics_state=getattr(self.state, "topology_metrics_state", "fresh" if bool(getattr(self.state, "topology_analytics", None)) else "deferred"),
                    cached_analytics_state=getattr(self.state, "cached_analytics_state", "fresh" if bool(getattr(self.state, "cached_analytics", None)) else "deferred"),
                    cycles_state=getattr(self.state, "cycles_state", "fresh" if hasattr(self.state, "cycles") else "deferred"),
                    collisions_state=getattr(self.state, "collisions_state", "deferred"),
                    artifact_consumption_state="fresh" if artifact_consumption_is_fresh(self.state) else "stale",
                )

            # 1. Handle Deletion
            current_state = self.state_manager.get_current_file_state(file_path, compute_hash=False)
            if not current_state:
                old_module = self.state.modules.get(module_path)
                old_artifacts = self.state.artifacts.get(module_path, {})
                old_usage = self.state.module_usages.get(module_path, ModuleUsageFacts()) if hasattr(self.state, "module_usages") and self.state.module_usages else ModuleUsageFacts()
                old_collision_facts = self.state.collision_facts.get(module_path) if hasattr(self.state, "collision_facts") and self.state.collision_facts else None
                delta, usage_delta, collision_facts_changed = prepare_deleted_module_update(
                    module_path,
                    old_module=old_module,
                    old_artifacts=old_artifacts,
                    old_usage=old_usage,
                    old_collision_facts=old_collision_facts,
                )

                from contextor.core.analysis.refresh_planner import RefreshPlanner
                plan = RefreshPlanner.plan_refresh(
                    delta,
                    usage_delta=usage_delta,
                    module_usages=self.state.module_usages,
                    collision_facts_changed=collision_facts_changed,
                )
                _trace_incremental_phase(
                    "INCREMENTAL_APPLY_START",
                    result=(
                        f"artifacts_added={len(delta.artifacts_added)};"
                        f"artifacts_removed={len(delta.artifacts_removed)};"
                        f"artifacts_changed={len(delta.artifacts_changed)};"
                        f"patch_families={','.join(plan.patch_families)}"
                    ),
                )
                affected_set, blast_radius_complete, execution_trace = self._apply_delta_and_commit(
                    file_path, delta, usage_delta, plan, [], {}, ModuleUsageFacts(),
                    new_collision_facts=None,
                    new_reexport_facts=None,
                    syntax_source_path=source_path,
                    remove_syntax_fact=True,
                    clear_parse_module=module_path,
                )
                blast_radius_state = "fresh" if blast_radius_complete else "deferred"
                affected_modules = sorted(affected_set) if blast_radius_complete else []
                return IncrementalUpdateResult(
                    status="DELETED",
                    file_path=file_path,
                    delta=delta,
                    graph_state="fresh",
                    dependencies_state="fresh",
                    blast_radius_state=blast_radius_state,
                    local_metrics_state="deferred",
                    global_metrics_state="deferred",
                    topology_metrics_state="fresh",
                    cached_analytics_state="fresh",
                    cycles_state="fresh",
                    collisions_state=getattr(self.state, "collisions_state", "deferred"),
                    artifact_consumption_state="fresh" if artifact_consumption_is_fresh(self.state) else "stale",
                    affected_modules=affected_modules,
                    shadow_plan=plan,
                    execution_trace=execution_trace,
                )

            # 2. Prepare Source Update
            module_id = self.registry.get_module_id(module_path)
            is_new = (module_id is None) or (module_path not in self.state.modules)
            old_module = self.state.modules.get(module_path)
            old_artifacts = self.state.artifacts.get(module_path, {})
            old_usage = self.state.module_usages.get(module_path, ModuleUsageFacts()) if hasattr(self.state, "module_usages") and self.state.module_usages else ModuleUsageFacts()
            old_collision_facts = self.state.collision_facts.get(module_path) if hasattr(self.state, "collision_facts") and self.state.collision_facts else None
            old_reexport_facts = (
                self.state.reexport_facts_by_module.get(
                    module_path
                )
            )

            prep = prepare_source_update(
                file_path=file_path,
                module_path=module_path,
                is_new=is_new,
                old_module=old_module,
                old_artifacts=old_artifacts,
                old_usage=old_usage,
                persistent_id=module_id,
                old_collision_facts=old_collision_facts,
                source_key=source_path,
                old_reexport_facts=old_reexport_facts,
            )

            if prep.has_error:
                syntax_fact = (
                    {
                        "status": "checked_with_errors",
                        "errors": [{
                            "message": prep.error_message,
                            "line_number": prep.line_number,
                            "column_number": prep.column_number,
                        }],
                    }
                    if prep.error_status == "SYNTAX_ERROR"
                    else None
                )
                self._commit_syntax_candidate(
                    source_path=source_path,
                    syntax_fact=syntax_fact,
                    mark_parse_error=(
                        prep.error_message,
                        prep.line_number,
                        prep.column_number,
                    ),
                    clear_parse_module=module_path,
                    degrade_syntax_family=prep.error_status != "SYNTAX_ERROR",
                    invalidate_lineage=True,
                )
                return IncrementalUpdateResult(
```

### IncrementalAnalysisEngine.update_file — complete contiguous implementation, part 2

Source: `C:\Temp\Contextor_Repo\contextor\core\analysis\incremental\engine.py : 601-735`

```python
                    status=prep.error_status,
                    file_path=file_path,
                    error=prep.error_message,
                    line_number=prep.line_number,
                    column_number=prep.column_number,
                )

            freshness = getattr(self.state, "module_parse_freshness", {}) or {}
            recovered_from_parse_failure = (
                isinstance(freshness.get(module_path), dict)
                and freshness[module_path].get("state") == "stale"
            )
            checked_and_none = {"status": "checked_and_none", "errors": []}

            delta = prep.delta
            usage_delta = prep.usage_delta
            new_imports = prep.new_imports
            new_artifacts = prep.new_artifacts
            new_usage = prep.new_usage
            new_collision_facts = prep.new_collision_facts
            new_reexport_facts = prep.new_reexport_facts

            from contextor.core.analysis.refresh_planner import RefreshPlanner
            plan = RefreshPlanner.plan_refresh(
                delta,
                usage_delta=usage_delta,
                module_usages=self.state.module_usages,
                collision_facts_changed=prep.collision_facts_changed,
            )

            # Check if true no-op
            if plan.is_empty and not is_new and not delta.is_deleted:
                # Parsing proved the tracked source is semantically unchanged.
                # Acknowledge its current fingerprint so restart reconciliation
                # does not repeatedly queue the same canonical module.
                self._commit_syntax_candidate(
                    source_path=source_path,
                    syntax_fact=checked_and_none,
                    clear_parse_module=module_path,
                    extracted_lineage_facts=prep.extracted_lineage_facts,
                )
                self.state_manager.update_state(file_path)
                return IncrementalUpdateResult(
                    status="RECOVERED" if recovered_from_parse_failure else "UNCHANGED",
                    file_path=file_path,
                    delta=delta,
                    graph_state="fresh",
                    dependencies_state="fresh",
                    blast_radius_state="deferred",
                    local_metrics_state="deferred",
                    global_metrics_state="deferred",
                    topology_metrics_state=getattr(self.state, "topology_metrics_state", "fresh" if bool(getattr(self.state, "topology_analytics", None)) else "deferred"),
                    cached_analytics_state=getattr(self.state, "cached_analytics_state", "fresh" if bool(getattr(self.state, "cached_analytics", None)) else "deferred"),
                    cycles_state=getattr(self.state, "cycles_state", "fresh" if hasattr(self.state, "cycles") else "deferred"),
                    collisions_state=getattr(self.state, "collisions_state", "deferred"),
                    artifact_consumption_state="fresh" if artifact_consumption_is_fresh(self.state) else "stale",
                    affected_modules=[],
                    shadow_plan=plan,
                    execution_trace={
                        "reparse_modules": (),
                        "recompute_modules": (),
                        "patch_families": (),
                        "graph_recomputations": (),
                    },
                )

            # 3. Apply and Commit driven by RefreshPlan
            _trace_incremental_phase(
                "INCREMENTAL_APPLY_START",
                result=(
                    f"artifacts_added={len(delta.artifacts_added)};"
                    f"artifacts_removed={len(delta.artifacts_removed)};"
                    f"artifacts_changed={len(delta.artifacts_changed)};"
                    f"patch_families={','.join(plan.patch_families)}"
                ),
            )
            affected_set, blast_radius_complete, execution_trace = self._apply_delta_and_commit(
                file_path, delta, usage_delta, plan, new_imports, new_artifacts, new_usage,
                new_collision_facts=new_collision_facts,
                new_reexport_facts=new_reexport_facts,
                extracted_lineage_facts=prep.extracted_lineage_facts,
                syntax_source_path=source_path,
                syntax_fact=checked_and_none,
                clear_parse_module=module_path,
            )

            if plan.refresh_completeness == "requires_resync":
                graph_state = "stale"
                dependencies_state = "stale"
                blast_radius_state = "deferred"
                topology_metrics_state = "stale"
                cached_analytics_state = "stale"
                cycles_state = "stale"
                collisions_state = "stale"
                artifact_consumption_state = "stale"
            else:
                graph_state = "fresh" if ("dependency_graph" in plan.patch_families or self.state.dependency_graph is not None) else "stale"
                dependencies_state = "fresh"
                blast_radius_state = "fresh" if blast_radius_complete else "deferred"
                if "advanced_graph_metrics" in plan.graph_recomputations:
                    topology_metrics_state = "fresh"
                else:
                    topology_metrics_state = getattr(self.state, "topology_metrics_state", "fresh" if bool(getattr(self.state, "topology_analytics", None)) else "deferred")
                if "cached_analytics" in plan.patch_families:
                    cached_analytics_state = "fresh"
                else:
                    cached_analytics_state = getattr(self.state, "cached_analytics_state", "fresh" if bool(getattr(self.state, "cached_analytics", None)) else "deferred")
                if "cycles" in plan.graph_recomputations:
                    cycles_state = "fresh"
                else:
                    cycles_state = getattr(self.state, "cycles_state", "fresh" if hasattr(self.state, "cycles") else "deferred")
                collisions_state = getattr(self.state, "collisions_state", "deferred")
                artifact_consumption_state = "fresh" if artifact_consumption_is_fresh(self.state) else "stale"

            affected_modules = sorted(affected_set) if blast_radius_complete else []

            return IncrementalUpdateResult(
                status="RECOVERED" if recovered_from_parse_failure else "UPDATED",
                file_path=file_path,
                delta=delta,
                graph_state=graph_state,
                dependencies_state=dependencies_state,
                blast_radius_state=blast_radius_state,
                local_metrics_state="deferred",
                global_metrics_state="deferred",
                topology_metrics_state=topology_metrics_state,
                cached_analytics_state=cached_analytics_state,
                cycles_state=cycles_state,
                collisions_state=collisions_state,
                artifact_consumption_state=artifact_consumption_state,
                affected_modules=affected_modules,
                shadow_plan=plan,
                execution_trace=execution_trace,
            )
```

### load_snapshot — complete contiguous implementation

Source: `C:\Temp\Contextor_Repo\contextor\core\live_state\store.py : 1970-2418`

```python
def load_snapshot(
    cache_dir: str | Path,
    expected_state_id: str = "",
    *,
    expected_repo_id: str = "",
    expected_root_path: str = "",
) -> tuple[Any, LiveStateMetadata] | None:
    """Load one complete published snapshot, rejecting incompatible identities."""

    state_file, _, _ = _paths(cache_dir)

    phase_started = time.monotonic()
    metadata = read_metadata(cache_dir)
    _trace_snapshot_load_phase(
        "metadata_read",
        phase_started,
        repo_id=expected_repo_id,
    )
    normalized_root = (
        str(Path(expected_root_path).expanduser().resolve())
        if expected_root_path
        else ""
    )
    if metadata is None or (expected_state_id and metadata.state_id != expected_state_id):
        return None
    if expected_repo_id and metadata.repo_id != expected_repo_id:
        return None
    if normalized_root and (
        not metadata.root_path
        or Path(metadata.root_path).expanduser().resolve() != Path(normalized_root)
    ):
        return None
    if metadata.state_file:
        state_file = state_file.parent / metadata.state_file
    try:
        phase_started = time.monotonic()
        with state_file.open("rb") as stream:
            payload = _SnapshotUnpickler(stream).load()
        _trace_snapshot_load_phase(
            "core_pickle_unpickle",
            phase_started,
            repo_id=expected_repo_id,
        )

        if isinstance(payload, dict) and set(payload) == {"metadata", "state"}:
            embedded = payload["metadata"]
            if not isinstance(embedded, dict):
                return None

            if metadata.schema_version == LIVE_STATE_SCHEMA_VERSION:
                expected_embedded = asdict(metadata)
                if set(embedded) != set(expected_embedded):
                    return None
                if any(
                    type(embedded[key]) is not type(expected_value)
                    or embedded[key] != expected_value
                    for key, expected_value in expected_embedded.items()
                ):
                    return None

            embedded_metadata = LiveStateMetadata(
                schema_version=str(embedded.get("schema_version", "1.0")),
                state_id=str(embedded.get("state_id", "")),
                revision=int(embedded.get("revision", 0)),
                writer=str(embedded.get("writer", "unknown")),
                repo_id=str(embedded.get("repo_id", "")),
                root_path=str(embedded.get("root_path", "")),
                state_file=str(embedded.get("state_file", "")),
                file_state_file=str(embedded.get("file_state_file", "")),
                lineage_manifest_file=str(
                    embedded.get(
                        "lineage_manifest_file",
                        "",
                    )
                ),
            )
            if embedded_metadata.revision != metadata.revision:
                return None
            if (
                embedded_metadata.lineage_manifest_file
                != metadata.lineage_manifest_file
            ):
                return None

            raw_state = payload[
                "state"
            ]

            lineage_validation_trusted_source_keys: set[str] = set()
            lineage_validation_cache_matches_current_chunks = False
            lineage_validation_chunks = None

            if metadata.lineage_manifest_file:
                if (
                    metadata.schema_version
                    != LIVE_STATE_SCHEMA_VERSION
                ):
                    return None

                if (
                    raw_state is None
                    or isinstance(
                        raw_state,
                        dict,
                    )
                    or not hasattr(
                        raw_state,
                        "__dict__",
                    )
                ):
                    return None

                phase_started = time.monotonic()
                (
                    split_lineage,
                    lineage_validation_trusted_source_keys,
                    lineage_validation_chunks,
                    lineage_validation_cache_matches_current_chunks,
                ) = _load_split_lineage_generation(
                    cache_dir,
                    metadata,
                )

                raw_modules = getattr(raw_state, "modules", None)
                if not isinstance(raw_modules, dict):
                    return None

                try:
                    expected_source_keys = {
                        Path(str(module.path)).as_posix()
                        for module in raw_modules.values()
                    }
                except (AttributeError, TypeError, ValueError):
                    return None

                actual_source_keys = set(split_lineage)

                if not actual_source_keys.issubset(expected_source_keys):
                    return None

                if (
                    getattr(raw_state, "lineage_facts_state", None)
                    == LineageFamilyStatus.FRESH.value
                    and actual_source_keys != expected_source_keys
                ):
                    return None

                _trace_snapshot_load_phase(
                    "split_lineage_load",
                    phase_started,
                    repo_id=expected_repo_id,
                    count=len(split_lineage),
                )

                try:
                    setattr(
                        raw_state,
                        "lineage_facts_by_source",
                        split_lineage,
                    )
                except AttributeError:
                    return None

            phase_started = time.monotonic()
            state_obj = _normalize_symbol_call_facts(
                raw_state
            )
            _trace_snapshot_load_phase(
                "normalize_symbol_call_facts",
                phase_started,
                repo_id=expected_repo_id,
            )

            phase_started = time.monotonic()
            state_obj = _normalize_lineage_facts_state(
                state_obj,
                trusted_source_keys=(
                    lineage_validation_trusted_source_keys
                ),
            )
            _trace_snapshot_load_phase(
                "normalize_lineage_facts_state",
                phase_started,
                repo_id=expected_repo_id,
                count=len(
                    getattr(
                        state_obj,
                        "lineage_facts_by_source",
                        {},
                    )
                    or {}
                ),
            )

            phase_started = time.monotonic()
            state_obj = (
                _normalize_lineage_query_index_state(
                    state_obj
                )
            )
            _trace_snapshot_load_phase(
                "normalize_lineage_query_index_state",
                phase_started,
                repo_id=expected_repo_id,
            )

            phase_started = time.monotonic()
            state_obj = _normalize_reexport_facts_state(
                state_obj
            )
            _trace_snapshot_load_phase(
                "normalize_reexport_facts_state",
                phase_started,
                repo_id=expected_repo_id,
            )

            phase_started = time.monotonic()
            state_revision = (
                state_obj.get("revision") if isinstance(state_obj, dict)
                else getattr(state_obj, "revision", None)
            )
            state_id_value = (
                state_obj.get("state_id") if isinstance(state_obj, dict)
                else getattr(state_obj, "state_id", None)
            )
            if state_obj is not None and state_revision is not None and int(state_revision) != metadata.revision:
                return None
            if state_obj is not None and state_id_value is not None and str(state_id_value) != metadata.state_id:
                return None
            if state_obj is not None and hasattr(state_obj, "__dict__"):
                try:
                    setattr(state_obj, "state_id", embedded_metadata.state_id)
                    setattr(state_obj, "revision", embedded_metadata.revision)
                    setattr(state_obj, "provenance", "snapshot")
                except AttributeError:
                    pass
                if not hasattr(state_obj, "module_usages"):
                    try:
                        setattr(state_obj, "module_usages", {})
                    except AttributeError:
                        pass
                if not hasattr(state_obj, "syntax_diagnostics_by_path"):
                    try:
                        setattr(state_obj, "syntax_diagnostics_by_path", {})
                    except AttributeError:
                        pass
                if not hasattr(state_obj, "syntax_diagnostics_state"):
                    try:
                        setattr(state_obj, "syntax_diagnostics_state", "not_materialized")
                    except AttributeError:
                        pass
                if not hasattr(state_obj, "module_usages_manifest"):
                    try:
                        setattr(state_obj, "module_usages_manifest", {})
                    except AttributeError:
                        pass
                if not hasattr(state_obj, "topology_analytics"):
                    try:
                        setattr(state_obj, "topology_analytics", {})
                    except AttributeError:
                        pass
                if not hasattr(state_obj, "topology_metrics_state"):
                    try:
                        setattr(state_obj, "topology_metrics_state", "deferred")
                    except AttributeError:
                        pass
                if not hasattr(state_obj, "cached_analytics"):
                    try:
                        setattr(state_obj, "cached_analytics", {})
                    except AttributeError:
                        pass
                if not hasattr(state_obj, "cached_analytics_state"):
                    try:
                        setattr(state_obj, "cached_analytics_state", "deferred")
                    except AttributeError:
                        pass
                if not hasattr(state_obj, "cycles"):
                    try:
                        setattr(state_obj, "cycles", [])
                    except AttributeError:
                        pass
                if not hasattr(state_obj, "cycles_state"):
                    try:
                        setattr(state_obj, "cycles_state", "deferred")
                    except AttributeError:
                        pass
                if not hasattr(state_obj, "collision_facts"):
                    try:
                        setattr(state_obj, "collision_facts", {})
                    except AttributeError:
                        pass
                if not hasattr(state_obj, "collisions"):
                    try:
                        setattr(state_obj, "collisions", [])
                    except AttributeError:
                        pass
                if not hasattr(state_obj, "collisions_state"):
                    try:
                        setattr(state_obj, "collisions_state", "deferred")
                    except AttributeError:
                        pass
                if not hasattr(state_obj, "dependency_matrix"):
                    try:
                        setattr(state_obj, "dependency_matrix", {})
                    except AttributeError:
                        pass
                if not hasattr(state_obj, "dependency_matrix_state"):
                    try:
                        setattr(state_obj, "dependency_matrix_state", "deferred")
                    except AttributeError:
                        pass
                if not hasattr(state_obj, "shared_usage_clusters"):
                    try:
                        setattr(state_obj, "shared_usage_clusters", [])
                    except AttributeError:
                        pass
                if not hasattr(state_obj, "shared_usage_clusters_state"):
                    try:
                        setattr(state_obj, "shared_usage_clusters_state", "deferred")
                    except AttributeError:
                        pass

            if (
                metadata.lineage_manifest_file
                and not lineage_validation_cache_matches_current_chunks
                and lineage_validation_chunks
                is not None
            ):
                _write_lineage_validation_cache(
                    cache_dir,
                    metadata=metadata,
                    chunks=(
                        lineage_validation_chunks
                    ),
                )

            _trace_snapshot_load_phase(
                "post_normalization_finalize",
                phase_started,
                repo_id=expected_repo_id,
            )
            return state_obj, metadata
        if metadata.lineage_manifest_file:
            return None

        payload = _normalize_lineage_query_index_state(
            _normalize_lineage_facts_state(
                _normalize_symbol_call_facts(payload)
            )
        )
        payload = _normalize_reexport_facts_state(
            payload
        )
        if payload is not None and hasattr(payload, "__dict__"):
            if not hasattr(payload, "module_usages"):
                try:
                    setattr(payload, "module_usages", {})
                except AttributeError:
                    pass
            if not hasattr(payload, "syntax_diagnostics_by_path"):
                try:
                    setattr(payload, "syntax_diagnostics_by_path", {})
                except AttributeError:
                    pass
            if not hasattr(payload, "syntax_diagnostics_state"):
                try:
                    setattr(payload, "syntax_diagnostics_state", "not_materialized")
                except AttributeError:
                    pass
            if not hasattr(payload, "module_usages_manifest"):
                try:
                    setattr(payload, "module_usages_manifest", {})
                except AttributeError:
                    pass
            if not hasattr(payload, "topology_analytics"):
                try:
                    setattr(payload, "topology_analytics", {})
                except AttributeError:
                    pass
            if not hasattr(payload, "topology_metrics_state"):
                try:
                    setattr(payload, "topology_metrics_state", "deferred")
                except AttributeError:
                    pass
            if not hasattr(payload, "cached_analytics"):
                try:
                    setattr(payload, "cached_analytics", {})
                except AttributeError:
                    pass
            if not hasattr(payload, "cached_analytics_state"):
                try:
                    setattr(payload, "cached_analytics_state", "deferred")
                except AttributeError:
                    pass
            if not hasattr(payload, "cycles"):
                try:
                    setattr(payload, "cycles", [])
                except AttributeError:
                    pass
            if not hasattr(payload, "cycles_state"):
                try:
                    setattr(payload, "cycles_state", "deferred")
                except AttributeError:
                    pass
            if not hasattr(payload, "collision_facts"):
                try:
                    setattr(payload, "collision_facts", {})
                except AttributeError:
                    pass
            if not hasattr(payload, "collisions"):
                try:
                    setattr(payload, "collisions", [])
                except AttributeError:
                    pass
            if not hasattr(payload, "collisions_state"):
                try:
                    setattr(payload, "collisions_state", "deferred")
                except AttributeError:
                    pass
            if not hasattr(payload, "dependency_matrix"):
                try:
                    setattr(payload, "dependency_matrix", {})
                except AttributeError:
                    pass
            if not hasattr(payload, "dependency_matrix_state"):
                try:
                    setattr(payload, "dependency_matrix_state", "deferred")
                except AttributeError:
                    pass
            if not hasattr(payload, "shared_usage_clusters"):
                try:
                    setattr(payload, "shared_usage_clusters", [])
                except AttributeError:
                    pass
            if not hasattr(payload, "shared_usage_clusters_state"):
                try:
                    setattr(payload, "shared_usage_clusters_state", "deferred")
                except AttributeError:
                    pass
        return payload, metadata




    except (OSError, pickle.PickleError, EOFError):
        return None
```

### resolve_authoritative_repository_state

Source: `C:\Temp\Contextor_Repo\contextor\core\live_state\hydration.py : 29-84`

```python
def resolve_authoritative_repository_state(
    repo_path: str | Path,
    *,
    _lease_held: bool = False,
) -> AuthoritativeRepositoryState | None:
    """Resolve the same LIVE-first, validated canonical state used by hydration."""

    from contextor.core.analysis.state_manager import load_engine_state
    from contextor.core.live_state.runtime import connect
    from contextor.core.live_state.store import migrate_legacy_snapshot, read_metadata
    from contextor.core.repository_identity import read_repository_identity

    root = Path(repo_path).resolve()
    identity = read_repository_identity(root)
    if identity is None:
        return None

    cache_dir = migrate_legacy_snapshot(root, _lease_held=_lease_held)
    client = connect(root)
    state = None
    revision = 0
    source = ""
    if client is not None:
        try:
            ping = client.ping()
            snapshot = client.snapshot()
            state = snapshot.get("state")
            revision = int(snapshot.get("revision", ping.get("revision", 0)))
            source = "live_service"
        except (TimeoutError, OSError, EOFError, ConnectionError, RuntimeError):
            client = None

    if state is None:
        metadata = read_metadata(cache_dir)
        state = load_engine_state(
            str(cache_dir),
            metadata.state_id if metadata else "",
            expected_repo_id=identity.repo_id,
            expected_root_path=identity.root_path,
        )
        source = "snapshot" if state is not None else ""

    if (
        state is None
        or not getattr(state, "modules", None)
        or getattr(state, "dependency_graph", None) is None
    ):
        return None

    return AuthoritativeRepositoryState(
        state=state,
        client=client,
        revision=revision,
        source=source,
        cache_dir=cache_dir,
    )
```

### hydrate_repository_engine

Source: `C:\Temp\Contextor_Repo\contextor\core\live_state\hydration.py : 87-116`

```python
def hydrate_repository_engine(
    repo_path: str | Path,
    *,
    _lease_held: bool = False,
) -> HydratedRepositoryEngine | None:
    """Load a complete engine without triggering a repository analysis."""

    from contextor.core.analysis.incremental_engine import IncrementalAnalysisEngine
    from contextor.core.analysis.state_manager import FileStateManager
    from contextor.core.reporting_engine.persistent_registry import (
        PersistentIdentityRegistry,
    )

    root = Path(repo_path).resolve()
    resolved = resolve_authoritative_repository_state(root, _lease_held=_lease_held)
    if resolved is None:
        return None

    engine = IncrementalAnalysisEngine(
        resolved.state,
        PersistentIdentityRegistry(str(root)),
        FileStateManager(str(resolved.cache_dir)),
        str(root),
    )
    return HydratedRepositoryEngine(
        engine=engine,
        client=resolved.client,
        revision=resolved.revision,
        source=resolved.source,
    )
```

### Relevant bounded source range

Source: `C:\Temp\Contextor_Repo\contextor\core\live_state\store.py : 1680-1773`

```python
                )
                + 1
            )

        metadata = LiveStateMetadata(
            state_id=state_id,
            revision=next_revision,
            writer=writer,
            repo_id=repo_id,
            root_path=normalized_root,
            state_file=(
                generation_state.name
                if exact_revision is not None
                else ""
            ),
            file_state_file=(
                generation_file_state.name
                if generation_file_state is not None
                else ""
            ),
            lineage_manifest_file=(
                generation_lineage_manifest.name
                if generation_lineage_manifest is not None
                else ""
            ),
        )

        if (
            exact_revision is not None
            and isinstance(
                state,
                dict,
            )
        ):
            state["revision"] = metadata.revision
            state["state_id"] = metadata.state_id

        elif (
            state is not None
            and hasattr(
                state,
                "__dict__",
            )
        ):
            try:
                setattr(
                    state,
                    "state_id",
                    metadata.state_id,
                )
                setattr(
                    state,
                    "revision",
                    metadata.revision,
                )
            except AttributeError:
                pass

        state_to_persist = state

        if (
            generation_lineage_manifest
            is not None
        ):
            (
                state_to_persist,
                generation_lineage_chunks,
            ) = _write_split_lineage_generation(
                state,
                generation_lineage_manifest,
                state_id=metadata.state_id,
                revision=metadata.revision,
                token=token,
                previous_state=previous_state,
                reusable_sources=reusable_lineage_sources,
            )

        with generation_state.open(
            "wb"
        ) as stream:
            pickle.dump(
                {
                    "metadata": asdict(
                        metadata
                    ),
                    "state": state_to_persist,
                },
                stream,
            )
            stream.flush()
            os.fsync(
                stream.fileno()
            )
```

### Relevant bounded source range

Source: `C:\Temp\Contextor_Repo\contextor\core\live_state\store.py : 1970-2060`

```python
def load_snapshot(
    cache_dir: str | Path,
    expected_state_id: str = "",
    *,
    expected_repo_id: str = "",
    expected_root_path: str = "",
) -> tuple[Any, LiveStateMetadata] | None:
    """Load one complete published snapshot, rejecting incompatible identities."""

    state_file, _, _ = _paths(cache_dir)

    phase_started = time.monotonic()
    metadata = read_metadata(cache_dir)
    _trace_snapshot_load_phase(
        "metadata_read",
        phase_started,
        repo_id=expected_repo_id,
    )
    normalized_root = (
        str(Path(expected_root_path).expanduser().resolve())
        if expected_root_path
        else ""
    )
    if metadata is None or (expected_state_id and metadata.state_id != expected_state_id):
        return None
    if expected_repo_id and metadata.repo_id != expected_repo_id:
        return None
    if normalized_root and (
        not metadata.root_path
        or Path(metadata.root_path).expanduser().resolve() != Path(normalized_root)
    ):
        return None
    if metadata.state_file:
        state_file = state_file.parent / metadata.state_file
    try:
        phase_started = time.monotonic()
        with state_file.open("rb") as stream:
            payload = _SnapshotUnpickler(stream).load()
        _trace_snapshot_load_phase(
            "core_pickle_unpickle",
            phase_started,
            repo_id=expected_repo_id,
        )

        if isinstance(payload, dict) and set(payload) == {"metadata", "state"}:
            embedded = payload["metadata"]
            if not isinstance(embedded, dict):
                return None

            if metadata.schema_version == LIVE_STATE_SCHEMA_VERSION:
                expected_embedded = asdict(metadata)
                if set(embedded) != set(expected_embedded):
                    return None
                if any(
                    type(embedded[key]) is not type(expected_value)
                    or embedded[key] != expected_value
                    for key, expected_value in expected_embedded.items()
                ):
                    return None

            embedded_metadata = LiveStateMetadata(
                schema_version=str(embedded.get("schema_version", "1.0")),
                state_id=str(embedded.get("state_id", "")),
                revision=int(embedded.get("revision", 0)),
                writer=str(embedded.get("writer", "unknown")),
                repo_id=str(embedded.get("repo_id", "")),
                root_path=str(embedded.get("root_path", "")),
                state_file=str(embedded.get("state_file", "")),
                file_state_file=str(embedded.get("file_state_file", "")),
                lineage_manifest_file=str(
                    embedded.get(
                        "lineage_manifest_file",
                        "",
                    )
                ),
            )
            if embedded_metadata.revision != metadata.revision:
                return None
            if (
                embedded_metadata.lineage_manifest_file
                != metadata.lineage_manifest_file
            ):
                return None

            raw_state = payload[
                "state"
            ]

            lineage_validation_trusted_source_keys: set[str] = set()
            lineage_validation_cache_matches_current_chunks = False
            lineage_validation_chunks = None
```

### Relevant bounded source range

Source: `C:\Temp\Contextor_Repo\contextor\core\live_state\store.py : 2183-2224`

```python
                repo_id=expected_repo_id,
            )

            phase_started = time.monotonic()
            state_revision = (
                state_obj.get("revision") if isinstance(state_obj, dict)
                else getattr(state_obj, "revision", None)
            )
            state_id_value = (
                state_obj.get("state_id") if isinstance(state_obj, dict)
                else getattr(state_obj, "state_id", None)
            )
            if state_obj is not None and state_revision is not None and int(state_revision) != metadata.revision:
                return None
            if state_obj is not None and state_id_value is not None and str(state_id_value) != metadata.state_id:
                return None
            if state_obj is not None and hasattr(state_obj, "__dict__"):
                try:
                    setattr(state_obj, "state_id", embedded_metadata.state_id)
                    setattr(state_obj, "revision", embedded_metadata.revision)
                    setattr(state_obj, "provenance", "snapshot")
                except AttributeError:
                    pass
                if not hasattr(state_obj, "module_usages"):
                    try:
                        setattr(state_obj, "module_usages", {})
                    except AttributeError:
                        pass
                if not hasattr(state_obj, "syntax_diagnostics_by_path"):
                    try:
                        setattr(state_obj, "syntax_diagnostics_by_path", {})
                    except AttributeError:
                        pass
                if not hasattr(state_obj, "syntax_diagnostics_state"):
                    try:
                        setattr(state_obj, "syntax_diagnostics_state", "not_materialized")
                    except AttributeError:
                        pass
                if not hasattr(state_obj, "module_usages_manifest"):
                    try:
                        setattr(state_obj, "module_usages_manifest", {})
                    except AttributeError:
```

### Relevant bounded source range

Source: `C:\Temp\Contextor_Repo\contextor\core\live_state\store.py : 2310-2418`

```python
            )
            return state_obj, metadata
        if metadata.lineage_manifest_file:
            return None

        payload = _normalize_lineage_query_index_state(
            _normalize_lineage_facts_state(
                _normalize_symbol_call_facts(payload)
            )
        )
        payload = _normalize_reexport_facts_state(
            payload
        )
        if payload is not None and hasattr(payload, "__dict__"):
            if not hasattr(payload, "module_usages"):
                try:
                    setattr(payload, "module_usages", {})
                except AttributeError:
                    pass
            if not hasattr(payload, "syntax_diagnostics_by_path"):
                try:
                    setattr(payload, "syntax_diagnostics_by_path", {})
                except AttributeError:
                    pass
            if not hasattr(payload, "syntax_diagnostics_state"):
                try:
                    setattr(payload, "syntax_diagnostics_state", "not_materialized")
                except AttributeError:
                    pass
            if not hasattr(payload, "module_usages_manifest"):
                try:
                    setattr(payload, "module_usages_manifest", {})
                except AttributeError:
                    pass
            if not hasattr(payload, "topology_analytics"):
                try:
                    setattr(payload, "topology_analytics", {})
                except AttributeError:
                    pass
            if not hasattr(payload, "topology_metrics_state"):
                try:
                    setattr(payload, "topology_metrics_state", "deferred")
                except AttributeError:
                    pass
            if not hasattr(payload, "cached_analytics"):
                try:
                    setattr(payload, "cached_analytics", {})
                except AttributeError:
                    pass
            if not hasattr(payload, "cached_analytics_state"):
                try:
                    setattr(payload, "cached_analytics_state", "deferred")
                except AttributeError:
                    pass
            if not hasattr(payload, "cycles"):
                try:
                    setattr(payload, "cycles", [])
                except AttributeError:
                    pass
            if not hasattr(payload, "cycles_state"):
                try:
                    setattr(payload, "cycles_state", "deferred")
                except AttributeError:
                    pass
            if not hasattr(payload, "collision_facts"):
                try:
                    setattr(payload, "collision_facts", {})
                except AttributeError:
                    pass
            if not hasattr(payload, "collisions"):
                try:
                    setattr(payload, "collisions", [])
                except AttributeError:
                    pass
            if not hasattr(payload, "collisions_state"):
                try:
                    setattr(payload, "collisions_state", "deferred")
                except AttributeError:
                    pass
            if not hasattr(payload, "dependency_matrix"):
                try:
                    setattr(payload, "dependency_matrix", {})
                except AttributeError:
                    pass
            if not hasattr(payload, "dependency_matrix_state"):
                try:
                    setattr(payload, "dependency_matrix_state", "deferred")
                except AttributeError:
                    pass
            if not hasattr(payload, "shared_usage_clusters"):
                try:
                    setattr(payload, "shared_usage_clusters", [])
                except AttributeError:
                    pass
            if not hasattr(payload, "shared_usage_clusters_state"):
                try:
                    setattr(payload, "shared_usage_clusters_state", "deferred")
                except AttributeError:
                    pass
        return payload, metadata




    except (OSError, pickle.PickleError, EOFError):
        return None
```

## MINIMUM_TEST_INSERTION_BOUNDARY

The nearest current test location is `C:\Temp\Contextor_Repo\tests\test_live_e2e_corrections.py:451-472` (existing parse hydration test), immediately before the malformed snapshot marker test at line 475. A separate spawned-process fixture exists in `C:\Temp\Contextor_Repo\tests\test_mcp_incremental_hydration.py:112-155` and the process test at lines 752-820. This identifies test owners only; no implementation design or test edit is proposed.

## REQUIRED_ASSERTION_MATRIX

A future literal regression would need to demonstrate, in a fresh interpreter: valid baseline symbol artifact; invalid-source update status and exact error/line/column; same generation's retained LKG artifact, stale parse marker and exact syntax fact after snapshot load; fail-closed public response; corrected source reparse with fresh current marker, expected new artifact, cleared syntax error, coherent canonical revision/state_id and persisted state. These are proof obligations from the user's contract, not an implementation patch.

## PRODUCTION_PATCH_REQUIRED

UNKNOWN. No source defect was proved. Do not change production based on this discovery alone.

## SOURCE_SYNC_POSTCHECK

Contextor second `module_current_truth` fetch: `status=resolved`, `implementation_is_complete=true`, `workspace_sync=verified`, `canonical_state=fresh`, revision 327. Git status/diff before report: empty.

## LIVE_REVISION_BEFORE_AFTER

Before: 327. After read-only targeted tests and final `get_live_events(after_revision=327)`: revision 327, no events, `continuity=continuous`, `resync_required=false`. No manual update_file, analysis, publish, or restart.

## RESTART_REQUIRED

NO. No production or test source changed.

## FINAL_VERDICT

L03_PRODUCTION_CORRECTNESS=UNKNOWN for the required integrated fresh-process scenario. L03_FRESH_PROCESS_REGRESSION_COVERAGE=ABSENT for that scenario. Existing code paths and focused tests establish important same-process pieces; they do not establish the requested combined fresh-process behavior. **READY_FOR_L03_LITERAL_REGRESSION_DESIGN**.

