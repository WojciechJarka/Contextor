# S2B LIVE NEW-MODULE REGRESSION

## ROOT_CAUSE

`IncrementalAnalysisEngine.update_file` returned `UNCHANGED` solely from `FileStateManager.has_changed(file_path) == false` before resolving the module name or checking canonical membership.

That made the persisted file fingerprint an accidental gate over canonical truth. If `file_state.json` already tracked a file while `RepositoryAnalysisState.modules` did not contain its module, the engine exited before:

- `is_new = true` classification;
- `prepare_source_update`;
- the Module ADD refresh plan;
- modules/artifacts/dependency-graph materialization;
- canonical publication.

The failure is deterministic for all seven S2B production additions when file-state acknowledgement exists but canonical state is absent/skewed. Package nesting, dotted-name resolution, registry identity, excludes and report state are not involved.

Current post-investigation evidence also shows a later `desktop_analysis` publish at revision `961`; its snapshot now contains all seven S2B modules and artifacts. This does not invalidate the reproduced incremental branch that previously returned `UNCHANGED`.

## AFFECTED_PATH

```text
filesystem add/modify event
-> DesktopLiveWatcher.poll_once
-> LiveStateClient.update_file
-> _repository_updater
-> IncrementalAnalysisEngine.update_file
-> FileStateManager.has_changed == false
-> premature UNCHANGED
-> no module resolution / refresh plan / canonical materialization
```

The fix resolves `module_path` first. `UNCHANGED` is legal only when both the file fingerprint is unchanged and the module already exists in authoritative `state.modules`. A tracked file absent from canonical state continues through the existing `is_new` and Module ADD pipeline.

## FILES_CHANGED

- `C:\Temp\Contextor_Repo\contextor\core\analysis\incremental\engine.py`
- `C:\Temp\Contextor_Repo\tests\test_incremental_artifact_consumption.py`
- `C:\Temp\Contextor_Repo\walkthrough.md`

## REGRESSION_TEST

Added exactly one regression:

`test_tracked_file_absent_from_canonical_state_is_materialized_as_add`

Fixture deliberately records the new file in `FileStateManager` while canonical modules/artifacts/graph are empty. Assertions prove:

- status `UPDATED`;
- `delta.is_new == true`;
- module present;
- defined artifact present;
- dependency-graph node present.

Result: **1 passed, 0 failed** in 0.63 s.

## LIVE_PROBE

An isolated incremental probe executed without Full Analysis:

```text
ADD UPDATED MODULE True ARTIFACT True GRAPH True
DELETE DELETED MODULE False ARTIFACT False GRAPH False
```

The temporary probe source was removed. A desktop-IPC watcher probe could not complete because owner discovery returned `owner_identity_changed`; no competing owner was started and no reconnect/election code was changed.

## S2B_IMPACT

- S2B tool/runtime implementation remains unchanged.
- Ordinary new Python modules no longer require Full Analysis when file-state metadata is already ahead of canonical state.
- Existing unchanged-file fast path remains intact for modules already present in canonical RAM.
- Existing Module ADD/DELETE refresh planner and COW publication paths remain the sole materialization path.

## CONTEXTOR_POST_CHANGE_AUDIT

- Contextor fetched the complete modified `IncrementalAnalysisEngine.update_file` implementation and confirmed 19 static symbol consumers / 35 bounded test paths.
- Canonical module context identifies the implementation owner as `contextor.core.analysis.incremental.engine`.
- No new helper, parallel state owner, duplicate path or scope expansion was introduced.
- The current LIVE owner identity mismatch prevents a new watcher event/revision proof until desktop LIVE is restarted.

## FINAL_VERDICT

`PASS` for the confirmed incremental correctness fix and isolated add/delete canonical probe.

`RESTART LIVE` is required only to repeat the desktop-watcher IPC evidence against a valid owner identity.
