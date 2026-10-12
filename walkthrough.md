# CONTEXTOR_B0G2D3_CANONICAL_CONSUMER_AND_MANIFEST_REPAIR

## FILES_CHANGED

- C:\Temp\Contextor_Repo\contextor\core\analysis\incremental\plan_executor.py
- C:\Temp\Contextor_Repo\contextor\core\analysis\incremental\engine.py
- C:\Temp\Contextor_Repo\tests\test_incremental_consumer_manifest_parity.py (new)
- C:\Temp\Contextor_Repo\walkthrough.md (report only; excluded from source diff)

## SOURCE_PRECHECK

DIRECT_EVIDENCE: Contextor MCP was used first, including deferred documentation, complete symbol retrieval and consumer blast radius. HEAD before edit: `2590372285f102627fbdf5bce4d730b53335d90b`; worktree clean. `get_symbol_implementation` returned complete, workspace_sync=verified for `_apply_delta_and_commit`, `build_symbol_references_from_canonical`, `extract_api_consumers`, `build_module_usage_baseline_with_reuse`, `validate_canonical_artifact_consumption_coverage`, `FileStateManager.update_state`, and `get_tracked_sha256`. Large `execute_refresh_plan` and `update_file` symbol requests require range retrieval; their exact relevant source anchors were confirmed in current workspace after Contextor discovery. The specified helper insertion, artifact-consumption patch branch and FileState acknowledgement anchors were present. Contextor blast radius for `execute_refresh_plan`: seven direct static consumers, including incremental engine and tests; broader module reachability is bounded static evidence. LIVE pre-edit revision 360, continuous, resync_required=false.

## CONSUMER_HELPER_IMPLEMENTATION

Added the auditor-specified `_refresh_canonical_artifact_consumers` immediately before `execute_refresh_plan`. It computes dirty definers from prior/current canonical consumption and changed module, projects references from canonical RAM via `build_symbol_references_from_canonical`, then builds `extract_api_consumers` records for every own symbol. It replaces each affected module artifact dictionary. The existing consumption rebuild and coverage validation are unchanged. The helper runs for fresh non-deletion updates and for fresh deletions over the surviving module domain. It does not claim complete ambiguous-reference coverage beyond the specified contract.

## COW_ISOLATION

The helper writes a fresh per-module artifact dictionary, leaving the original nested dictionary intact. New tests retain and compare old provider/unrelated artifact references and old manifest dictionary. `candidate.artifacts` is a shallow COW map; refreshed modules are replaced, and unrelated entries remain identical. An unsupported unmaterialized-reference fixture raises before canonical artifact/manifest publication.

## ADDED_SYMBOL_PARITY

New regression creates `NEW_SYMBOL` and checks an explicit FULL-shaped zero-consumer record, including all usage arrays and zero counts. The strict real B0G2D rerun independently confirms `state.artifacts` equal between Desktop incremental and fresh FULL A; the prior missing `pkg.__init__::child` record is present.

## REMOVED_SYMBOL_PARITY

New regression removes `REMOVE_ME`: obsolete `provider::REMOVE_ME` target and per-symbol consumer record disappear, `KEEP` remains, unrelated artifact is unchanged. A deletion regression verifies that removing a consumer module refreshes a surviving definer's record.

## CHANGED_CONSUMER_PARITY

New regression changes `consumer.py` to call an unchanged provider function. The provider's per-symbol consumer list, direct-call channel and detail evidence update from canonical RAM. Test blocks `Path.read_text` and `builtins.open` for that unchanged provider source; no read was attempted. Another regression adds a symbol already referenced by a consumer and verifies qualified-reference consumer/channel/detail evidence.

## CANONICAL_REFERENCE_PROJECTION

The new helper uses only the approved canonical reference projector and `extract_api_consumers`. It requires materialized reference evidence. New regression with one current module's `reference_evidence_materialized=False` proves a `CanonicalReferenceEvidenceUnavailable` exception before artifact/manifest commit, rather than fabricated fresh records. Existing canonical-reference projection suite passed.

## MANIFEST_SCHEMA_PARITY

Added the exact `_updated_module_usage_manifest` schema: `module_id`, resolved absolute `path`, already tracked SHA-256, and `MODULE_USAGE_FACTS_SEMANTIC_VERSION`. It creates a new dictionary and removes the deleted module entry. The FULL usage-manifest producer's schema was confirmed pre-edit. After FileState acknowledgement, `_apply_delta_and_commit` replaces canonical `module_usages_manifest`; the parsed semantic no-op path does likewise. No new hash read was added: `get_tracked_sha256` reads FileStateManager's captured RAM record.

## MANIFEST_SHA256_PARITY

New tests compare manifest hash to `FileStateManager.get_tracked_sha256` after changed updates and compare module ID, absolute path and semantic version. In the strict real B0G2D rerun, the entire `module_usages_manifest` field equals fresh FULL A; `pkg.__init__` has changed-source SHA-256 `f00db78ab6749353708d53435633caaef82718c2d474db99949177f49a3de056`.

## DELETE_AND_NOOP_MANIFEST_CASES

New deletion regression confirms manifest entry removal and COW dictionary replacement. New parsed semantic no-op regression changes only a comment; status is UNCHANGED and manifest SHA advances to the newly acknowledged FileState hash. Early UNCHANGED, with no changed tracked file, does not rewrite the manifest. Syntax failure path is left under the existing fail-closed parse contract.

## FAIL_CLOSED_BEHAVIOR

Unmaterialized canonical reference evidence raises before candidate publication. The manifest helper raises `RuntimeError` on an absent trusted tracked hash; a focused test confirms the update does not return a success status and leaves the prior manifest dictionary in place. LIMIT: `_apply_delta_and_commit` still assigns other RAM state fields before FileState acknowledgement, as it did before this task. The missing-hash test establishes no successful result, not standalone in-process rollback of all earlier RAM assignments. This task did not alter the existing LIVE/local candidate publication boundaries.

## TARGETED_TEST_RESULTS

- New focused file `tests/test_incremental_consumer_manifest_parity.py`: **8 passed** (final run, 16.58 s). Cases cover auditor A–J, with related assertions grouped into eight tests.
- Existing targeted set: **34 passed** (37.04 s): complete `test_canonical_reference_projection.py`, `test_incremental_artifact_consumption.py`, `test_package_initializer_graph_refresh.py`, plus selected `test_refresh_plan_execution` symbol removal/module addition/parse-freshness COW and `test_parity_and_freshness_proof.py::test_copy_on_write_atomicity`.
- No full repository pytest suite was run.

## REAL_B0G2D_PARITY_RERUN

Unchanged `tests/test_desktop_mcp_live_incremental_parity.py`: **1 failed**, 1 warning, 6.45 s. This is the approved strict comparator detecting the next reserved family. Preserved rerun evidence: `C:\Users\DafoO\AppData\Local\Temp\pytest-of-DafoO\pytest-558\test_real_desktop_watcher_and_0\b0g2d_canonical_mismatch_evidence`. Offline comparison of its preserved pickles: entire `artifacts` equal; entire `module_usages_manifest` equal; `cached_analytics`, `cached_analytics_state`, and `layer_information` differ. No comparator or fixture change was made.

## FIRST_REMAINING_MISMATCH

`state.layer_information['debt']['interpretation']['breakdown']['soft_edges']`: Desktop incremental `1 soft edges (+0.5)` versus fresh FULL A `none`. The test's first-field error points to the same field. This task did not alter layer report computation.

## KNOWN_UNRESOLVED_ANALYTICS

`cached_analytics` remains eagerly populated/fresh in incremental and empty/deferred in fresh FULL. Reserved for B0G2D4; no normalization or patch here.

## KNOWN_UNRESOLVED_LAYER_INFORMATION

Incremental layer report retains the prior soft-edge summary after graph update, whereas fresh FULL reports the current graph. Reserved for B0G2D4. Only the two pre-approved timestamps are normalized by the strict comparator.

## PY_COMPILE

PASS: `.venv\Scripts\python.exe -m py_compile` on both modified production files and the new test file, after final test edit.

## GIT_DIFF_CHECK

PASS for tracked production diff: `git diff --check` exit 0, no whitespace errors. New-file `git diff --no-index --check /dev/null tests/test_incremental_consumer_manifest_parity.py` emitted no whitespace errors; its exit 1 denotes the expected file difference. Git emitted only LF-to-CRLF advisory warnings. No source/test files outside the approved scope are changed.

## LIVE_REVISION_BEFORE_AFTER

DIRECT_EVIDENCE: revision 360 before edits; latest revision 366 after edits and tests. `get_live_events(after_revision=360)` recorded Desktop watcher updates for `plan_executor.py` rev 361, `engine.py` rev 362, test file revs 363–365; final test edit rev 366. Continuity is continuous, no resync. No manual MCP update_file call, full Contextor_Repo analysis or process restart.

## WORKSPACE_SYNC_POSTCHECK

Contextor `get_symbol_implementation` on new `_refresh_canonical_artifact_consumers` at rev 365 and `_updated_module_usage_manifest` at rev 366 returned complete source contract and `workspace_sync=verified`. This proves indexed workspace source identity, not imported-code reload of existing serving processes.

## RESYNC_REQUIRED

False at final Contextor LIVE query.

## RESTART_REQUIRED

YES, manual MCP/LIVE/Desktop serving-process reload boundary before runtime certification of the changed production code. No process was restarted in this task. Source indexing and pytest in a new interpreter do not certify imported code in existing processes.

## FINAL_VERDICT

B0G2D3_NEXT_MISMATCH_CONFIRMED. Both in-scope canonical fields match the fresh FULL oracle in the real transport rerun; strict full canonical parity remains blocked at the reserved `layer_information` field, with analytics differences also retained. Await auditor command `proceduj`.

## FULL_DIFFS

The following are complete actual diffs of every changed source/test file. `walkthrough.md` is the report and excluded from this list.

```diff
diff --git a/contextor/core/analysis/incremental/engine.py b/contextor/core/analysis/incremental/engine.py
index 1c0a03b..f0132a6 100644
--- a/contextor/core/analysis/incremental/engine.py
+++ b/contextor/core/analysis/incremental/engine.py
@@ -59,6 +59,38 @@ def _trace_incremental_phase(
     )
 
 
+def _updated_module_usage_manifest(
+    previous_manifest: dict,
+    module_path: str,
+    file_path: str,
+    *,
+    is_deleted: bool,
+    tracked_sha256: str,
+) -> dict:
+    from contextor.core.domain.usage_facts import (
+        MODULE_USAGE_FACTS_SEMANTIC_VERSION,
+    )
+
+    updated = dict(previous_manifest or {})
+
+    if is_deleted:
+        updated.pop(module_path, None)
+        return updated
+
+    if not tracked_sha256:
+        raise RuntimeError(
+            f"Missing trusted source SHA-256 for {module_path}"
+        )
+
+    updated[module_path] = {
+        "module_id": module_path,
+        "path": str(Path(file_path).resolve()),
+        "sha256": tracked_sha256,
+        "semantic_version": MODULE_USAGE_FACTS_SEMANTIC_VERSION,
+    }
+    return updated
+
+
 @dataclass
 class IncrementalUpdateResult:
     """Contract for what the incremental engine returns to MCP/IDE."""
@@ -640,6 +672,13 @@ class IncrementalAnalysisEngine:
                     extracted_lineage_facts=prep.extracted_lineage_facts,
                 )
                 self.state_manager.update_state(file_path)
+                self.state.module_usages_manifest = _updated_module_usage_manifest(
+                    self.state.module_usages_manifest,
+                    module_path,
+                    file_path,
+                    is_deleted=False,
+                    tracked_sha256=self.state_manager.get_tracked_sha256(file_path),
+                )
                 return IncrementalUpdateResult(
                     status="RECOVERED" if recovered_from_parse_failure else "UNCHANGED",
                     file_path=file_path,
@@ -1010,6 +1049,13 @@ class IncrementalAnalysisEngine:
             "INCREMENTAL_FILE_STATE_START",
         )
         self.state_manager.update_state(file_path)
+        self.state.module_usages_manifest = _updated_module_usage_manifest(
+            self.state.module_usages_manifest,
+            delta.module_path,
+            file_path,
+            is_deleted=delta.is_deleted,
+            tracked_sha256=self.state_manager.get_tracked_sha256(file_path),
+        )
         _trace_incremental_phase(
             "INCREMENTAL_FILE_STATE_END",
             started=file_state_started,
diff --git a/contextor/core/analysis/incremental/plan_executor.py b/contextor/core/analysis/incremental/plan_executor.py
index b039797..94d1595 100644
--- a/contextor/core/analysis/incremental/plan_executor.py
+++ b/contextor/core/analysis/incremental/plan_executor.py
@@ -765,6 +765,87 @@ def _prepare_candidate_state(state: RepositoryAnalysisState) -> CandidateState:
     )
 
 
+def _refresh_canonical_artifact_consumers(
+    candidate: CandidateState,
+    previous_consumption: Mapping[str, Any],
+    changed_module: str,
+) -> None:
+    """Refresh affected per-symbol consumer views from canonical RAM facts."""
+    from contextor.core.api.api_consumers import extract_api_consumers
+    from contextor.core.reference.engine import (
+        build_symbol_references_from_canonical,
+    )
+
+    current_modules = set(candidate.modules)
+    dirty_definers = {changed_module}
+
+    previous_targets = previous_consumption or {}
+    current_targets = candidate.artifact_consumption or {}
+
+    for target in set(previous_targets) | set(current_targets):
+        if "::" not in target:
+            continue
+
+        before = previous_targets.get(target, {})
+        after = current_targets.get(target, {})
+
+        if not isinstance(before, dict):
+            before = {}
+        if not isinstance(after, dict):
+            after = {}
+
+        if (
+            before != after
+            or changed_module in before.get("consumers", ())
+            or changed_module in after.get("consumers", ())
+            or changed_module in before.get("channels", {})
+            or changed_module in after.get("channels", {})
+        ):
+            dirty_definers.add(target.split("::", 1)[0])
+
+    for module_id in sorted(dirty_definers & current_modules):
+        artifact = candidate.artifacts.get(module_id)
+        if not isinstance(artifact, dict):
+            raise RuntimeError(
+                f"Missing canonical artifact record for {module_id}"
+            )
+
+        own_symbols = list(artifact.get("own_symbols", ()))
+
+        if own_symbols:
+            references = build_symbol_references_from_canonical(
+                definer_module=module_id,
+                symbols=own_symbols,
+                artifact_consumption=candidate.artifact_consumption,
+                module_usages=candidate.module_usages,
+                current_modules=current_modules,
+            )
+
+            symbols = artifact.get("symbols", {})
+            if not isinstance(symbols, dict):
+                raise RuntimeError(
+                    f"Invalid canonical symbol facts for {module_id}"
+                )
+
+            refreshed_consumers = extract_api_consumers(
+                own_symbols,
+                references,
+                signatures=symbols.get("signatures", {}),
+            )
+        else:
+            refreshed_consumers = {}
+
+        if set(refreshed_consumers) != set(own_symbols):
+            raise RuntimeError(
+                f"Incomplete consumer materialization for {module_id}"
+            )
+
+        candidate.artifacts[module_id] = {
+            **artifact,
+            "consumers": refreshed_consumers,
+        }
+
+
 def execute_refresh_plan(
     state: RepositoryAnalysisState,
     delta: FileDelta,
@@ -1084,6 +1165,25 @@ def execute_refresh_plan(
             else:
                 candidate.artifact_consumption_state = "stale"
 
+            if (
+                candidate.artifact_consumption_state == "fresh"
+                and not delta.is_deleted
+            ):
+                _refresh_canonical_artifact_consumers(
+                    candidate,
+                    state.artifact_consumption,
+                    delta.module_path,
+                )
+            elif (
+                candidate.artifact_consumption_state == "fresh"
+                and delta.is_deleted
+            ):
+                _refresh_canonical_artifact_consumers(
+                    candidate,
+                    state.artifact_consumption,
+                    delta.module_path,
+                )
+
             executed_patch_families.append("artifact_consumption")
 
         elif family == "identity_registry":
diff --git a/tests/test_incremental_consumer_manifest_parity.py b/tests/test_incremental_consumer_manifest_parity.py
new file mode 100644
index 0000000..9896f98
--- /dev/null
+++ b/tests/test_incremental_consumer_manifest_parity.py
@@ -0,0 +1,259 @@
+"""Focused canonical consumer-record and usage-manifest incremental regressions."""
+
+from __future__ import annotations
+
+import builtins
+from copy import deepcopy
+from dataclasses import replace
+from pathlib import Path
+
+import pytest
+
+from contextor.core.api.facade import ContextorFacade
+from contextor.core.domain.usage_facts import MODULE_USAGE_FACTS_SEMANTIC_VERSION
+from contextor.core.live_state.hydration import hydrate_repository_engine
+from contextor.core.reference.engine import CanonicalReferenceEvidenceUnavailable
+from contextor.core.reporting_layer.artifact_usage_report import _module_own_symbols
+
+
+def _engine(tmp_path: Path, sources: dict[str, str]):
+    for name, content in sources.items():
+        path = tmp_path / name
+        path.parent.mkdir(parents=True, exist_ok=True)
+        path.write_text(content, encoding="utf-8")
+    errors, _ = ContextorFacade.analyze_project(str(tmp_path))
+    assert not errors, errors
+    hydrated = hydrate_repository_engine(tmp_path)
+    assert hydrated is not None
+    return hydrated.engine
+
+
+def _assert_manifest_matches_tracked(engine, module_id: str, path: Path) -> None:
+    entry = engine.state.module_usages_manifest[module_id]
+    assert entry == {
+        "module_id": module_id,
+        "path": str(path.resolve()),
+        "sha256": engine.state_manager.get_tracked_sha256(str(path)),
+        "semantic_version": MODULE_USAGE_FACTS_SEMANTIC_VERSION,
+    }
+    assert entry["sha256"]
+
+
+def test_added_unused_symbol_has_full_compatible_zero_consumer_record_and_cow(tmp_path):
+    source = tmp_path / "provider.py"
+    engine = _engine(tmp_path, {"provider.py": "EXISTING = 1\n"})
+    previous_artifact = engine.state.artifacts["provider"]
+    previous_artifact_copy = deepcopy(previous_artifact)
+    previous_manifest = engine.state.module_usages_manifest
+
+    source.write_text("EXISTING = 1\nNEW_SYMBOL = 2\n", encoding="utf-8")
+    result = engine.update_file(str(source))
+
+    assert result.status == "UPDATED"
+    record = engine.state.artifacts["provider"]["consumers"]["NEW_SYMBOL"]
+    assert record == {
+        "signature": "",
+        "consumers": [],
+        "usage": {
+            "direct_calls": [],
+            "direct_calls_detail": [],
+            "callback_calls": [],
+            "callback_calls_detail": [],
+            "event_bindings": [],
+            "event_bindings_detail": [],
+            "runtime_calls": [],
+            "qualified_refs": [],
+            "qualified_refs_detail": [],
+            "api_imports": [],
+            "inheritance": [],
+            "inheritance_detail": [],
+            "ambiguous_calls": [],
+        },
+        "consumer_count": {
+            "total": 0,
+            "direct_calls": 0,
+            "callbacks": 0,
+            "events": 0,
+            "qualified_refs": 0,
+            "api_imports": 0,
+            "inheritance": 0,
+        },
+    }
+    assert previous_artifact == previous_artifact_copy
+    assert previous_artifact is not engine.state.artifacts["provider"]
+    assert previous_manifest is not engine.state.module_usages_manifest
+    _assert_manifest_matches_tracked(engine, "provider", source)
+
+
+def test_removed_own_symbol_drops_record_and_preserves_unrelated_artifact(tmp_path):
+    source = tmp_path / "provider.py"
+    engine = _engine(
+        tmp_path,
+        {"provider.py": "KEEP = 1\nREMOVE_ME = 2\n", "unrelated.py": "OTHER = 3\n"},
+    )
+    old_provider = engine.state.artifacts["provider"]
+    old_provider_copy = deepcopy(old_provider)
+    unrelated = engine.state.artifacts["unrelated"]
+    unrelated_copy = deepcopy(unrelated)
+
+    source.write_text("KEEP = 1\n", encoding="utf-8")
+    result = engine.update_file(str(source))
+
+    assert result.status == "UPDATED"
+    assert set(engine.state.artifacts["provider"]["consumers"]) == {"KEEP"}
+    assert "provider::REMOVE_ME" not in engine.state.artifact_consumption
+    assert old_provider == old_provider_copy
+    assert unrelated == unrelated_copy
+    assert engine.state.artifacts["unrelated"] is unrelated
+    _assert_manifest_matches_tracked(engine, "provider", source)
+
+
+def test_confirmed_consumer_change_refreshes_unchanged_definer_from_ram(tmp_path, monkeypatch):
+    provider = tmp_path / "provider.py"
+    consumer = tmp_path / "consumer.py"
+    engine = _engine(
+        tmp_path,
+        {
+            "provider.py": "def shared_function():\n    return 1\n",
+            "consumer.py": "from provider import shared_function\n",
+        },
+    )
+    old_provider = engine.state.artifacts["provider"]
+    old_provider_copy = deepcopy(old_provider)
+    provider_reads = []
+    original_read_text = Path.read_text
+    original_open = builtins.open
+
+    def tracked_read_text(path, *args, **kwargs):
+        if path.resolve() == provider.resolve():
+            provider_reads.append(str(path))
+            raise AssertionError("unchanged provider source was reread")
+        return original_read_text(path, *args, **kwargs)
+
+    def tracked_open(file, *args, **kwargs):
+        if isinstance(file, (str, Path)) and Path(file).resolve() == provider.resolve():
+            provider_reads.append(str(file))
+            raise AssertionError("unchanged provider source was reopened")
+        return original_open(file, *args, **kwargs)
+
+    monkeypatch.setattr(Path, "read_text", tracked_read_text)
+    monkeypatch.setattr(builtins, "open", tracked_open)
+    consumer.write_text(
+        "from provider import shared_function\nshared_function()\n",
+        encoding="utf-8",
+    )
+    result = engine.update_file(str(consumer))
+
+    assert result.status == "UPDATED"
+    assert provider_reads == []
+    record = engine.state.artifacts["provider"]["consumers"]["shared_function"]
+    assert "consumer" in record["consumers"]
+    assert record["usage"]["direct_calls"] == ["consumer"]
+    assert record["consumer_count"]["direct_calls"] == 1
+    assert record["usage"]["direct_calls_detail"]
+    assert old_provider == old_provider_copy
+    assert old_provider is not engine.state.artifacts["provider"]
+    _assert_manifest_matches_tracked(engine, "consumer", consumer)
+
+
+def test_added_symbol_with_existing_confirmed_consumer_has_exact_record(tmp_path):
+    provider = tmp_path / "provider.py"
+    engine = _engine(
+        tmp_path,
+        {
+            "provider.py": "EXISTING = 1\n",
+            "consumer.py": "import provider\nCONSUMED = provider.NEW_VALUE\n",
+        },
+    )
+    provider.write_text("EXISTING = 1\nNEW_VALUE = 2\n", encoding="utf-8")
+    result = engine.update_file(str(provider))
+
+    assert result.status == "UPDATED"
+    assert "NEW_VALUE" in _module_own_symbols(
+        engine.state.artifacts["provider"]["symbols"]
+    )
+    assert "consumer" in engine.state.artifact_consumption[
+        "provider::NEW_VALUE"
+    ]["consumers"]
+    record = engine.state.artifacts["provider"]["consumers"]["NEW_VALUE"]
+    assert record["consumers"] == ["consumer"]
+    assert record["usage"]["qualified_refs"] == ["consumer"]
+    assert record["usage"]["qualified_refs_detail"]
+    _assert_manifest_matches_tracked(engine, "provider", provider)
+
+
+def test_deleted_module_drops_manifest_and_surviving_consumer_record(tmp_path):
+    provider = tmp_path / "provider.py"
+    consumer = tmp_path / "consumer.py"
+    engine = _engine(
+        tmp_path,
+        {
+            "provider.py": "def shared_function():\n    return 1\n",
+            "consumer.py": "from provider import shared_function\nshared_function()\n",
+        },
+    )
+    assert "consumer" in engine.state.artifacts["provider"]["consumers"][
+        "shared_function"
+    ]["consumers"]
+    old_manifest = engine.state.module_usages_manifest
+    consumer.unlink()
+    result = engine.update_file(str(consumer))
+
+    assert result.status == "DELETED"
+    assert "consumer" not in engine.state.module_usages_manifest
+    assert old_manifest is not engine.state.module_usages_manifest
+    assert "consumer" not in engine.state.artifacts["provider"]["consumers"][
+        "shared_function"
+    ]["consumers"]
+    assert engine.state.artifact_consumption["provider::shared_function"][
+        "consumers"
+    ] == []
+
+
+def test_semantic_noop_acknowledges_new_source_hash_in_manifest(tmp_path):
+    source = tmp_path / "provider.py"
+    engine = _engine(tmp_path, {"provider.py": "VALUE = 1\n"})
+    previous_sha = engine.state.module_usages_manifest["provider"]["sha256"]
+    previous_manifest = engine.state.module_usages_manifest
+    source.write_text("VALUE = 1\n# nonsemantic comment\n", encoding="utf-8")
+    result = engine.update_file(str(source))
+
+    assert result.status == "UNCHANGED"
+    assert engine.state.module_usages_manifest["provider"]["sha256"] != previous_sha
+    assert previous_manifest is not engine.state.module_usages_manifest
+    _assert_manifest_matches_tracked(engine, "provider", source)
+
+
+def test_unmaterialized_reference_evidence_fails_before_canonical_commit(tmp_path):
+    source = tmp_path / "provider.py"
+    engine = _engine(
+        tmp_path,
+        {"provider.py": "EXISTING = 1\n", "other.py": "OTHER = 2\n"},
+    )
+    engine.state.module_usages["other"] = replace(
+        engine.state.module_usages["other"],
+        reference_evidence_materialized=False,
+    )
+    old_artifacts = engine.state.artifacts
+    old_manifest = engine.state.module_usages_manifest
+    source.write_text("EXISTING = 1\nNEW_SYMBOL = 2\n", encoding="utf-8")
+
+    with pytest.raises(CanonicalReferenceEvidenceUnavailable):
+        engine.update_file(str(source))
+
+    assert engine.state.artifacts is old_artifacts
+    assert engine.state.module_usages_manifest is old_manifest
+    assert "NEW_SYMBOL" not in engine.state.artifacts["provider"]["consumers"]
+
+
+def test_missing_tracked_hash_cannot_return_successful_update(tmp_path, monkeypatch):
+    source = tmp_path / "provider.py"
+    engine = _engine(tmp_path, {"provider.py": "EXISTING = 1\n"})
+    old_manifest = engine.state.module_usages_manifest
+    monkeypatch.setattr(engine.state_manager, "get_tracked_sha256", lambda _path: "")
+    source.write_text("EXISTING = 1\nNEW_SYMBOL = 2\n", encoding="utf-8")
+
+    with pytest.raises(RuntimeError, match="Missing trusted source SHA-256"):
+        engine.update_file(str(source))
+
+    assert engine.state.module_usages_manifest is old_manifest
```
