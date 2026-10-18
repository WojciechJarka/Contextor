# TASK
CONTEXTOR_B0G4C38C_INDEX_BOUND_CYCLE_SEMANTICS_MATERIALIZATION — exact auditor-supplied materializer, no facade/LIVE/report integration.

## HEAD_BEFORE / HEAD_AFTER / GIT_STATUS
HEAD_BEFORE=9925c395ad4402faaed3894b9a1ae8f7eb13ab2f
HEAD_AFTER=9925c395ad4402faaed3894b9a1ae8f7eb13ab2f
GIT_STATUS before: clean. After: `?? contextor/core/cycle_semantics/materialization.py`, `?? tests/test_cycle_semantics_materialization.py`, and modified `walkthrough.md` as report only. C38B is in current HEAD: `RepositoryIndex.source_fingerprints_by_module` exists and indexes successful modules. No Git mutation.

## PRECHECK / CONTEXTOR_DISCOVERY_COVERAGE / WORKSPACE_SYNC
DIRECT_EVIDENCE: Contextor MCP first; read current tool documentation; fetched complete exact implementations and `workspace_sync=verified` at LIVE 487 for `CycleSemanticsSnapshot` (`C:\Temp\Contextor_Repo\contextor\core\cycle_semantics\contracts.py:189-427`), `fingerprint_hard_edges` (134-186), `build_cycle_source_cohort` (`...\source_cohort.py:112-412`), `analyze_cyclic_import_sites` (`...\edge_sites.py:214-383`), `discover_conditional_reexports` (`...\conditional_discovery.py:148-424`), and `RepositoryIndex` (`C:\Temp\Contextor_Repo\contextor\core\symbol_engine\indexer.py:943-971`). Module contexts supplied existing consumers/blast radius and import direction. Literal Git/source checks after discovery confirmed clean HEAD, absent new targets and C38B field. No critical source drift.
Before edit: LIVE revision 487, activity epoch `bbd40ce1942841df94718acedc12561f`, continuous event history, resync_required=false, fresh syntax 0, collisions 0, structural cycle paths 16. Authority checked read-only via endpoint and `LiveStateClient(is_owner=False)`.

## FILES_CHANGED
- `C:\Temp\Contextor_Repo\contextor\core\cycle_semantics\materialization.py` — new production module.
- `C:\Temp\Contextor_Repo\tests\test_cycle_semantics_materialization.py` — new isolated synthetic tests.
- `walkthrough.md` overwritten as current-task report; excluded from source/test changed list.

## MATERIALIZER_INPUT_CONTRACT / INDEX_FINGERPRINT_DOMAIN_VALIDATION / GRAPH_CONTENT_FINGERPRINT
CONTRACT_PROVED: `materialize_cycle_semantics(repository_root,hard_edges,module_paths,source_fingerprints_by_module,*,max_searches=256)` takes caller-supplied graph, indexed paths and exact C38B hashes. `_validate_index_source_domain` requires mapping types, nonempty exact string IDs, equality of module-path and hash key sets, and lowercase 64-hex hashes before cohort I/O. `max_searches` must be exact int 1..4096. `fingerprint_hard_edges` identifies the complete supplied hard graph content without mutating it or certifying a LIVE generation.

## CYCLIC_SOURCE_ACCEPTANCE / CANONICAL_FINGERPRINT_MISMATCH_POLICY / PARTIAL_EVIDENCE_POLICY
The existing C34 `build_cycle_source_cohort` is called with `expected_fingerprints=source_fingerprints_by_module`, never None. It reads/parses only cyclic members, rejects changed bytes against index SHA before accepting AST, and performs its own post-read drift check. Materializer fails closed if accepted parsed sources lack index hashes or match count differs. A body-only changed source after indexing yields `PARTIAL_SOURCE_EVIDENCE`, issue `CANONICAL_FINGERPRINT_MISMATCH`, no accepted fingerprint/lexical site for changed source, while structural SCC remains visible and unchanged source is accepted. Existing cohort can emit `SOURCE_CHANGED_DURING_READ`; this stage preserves that path. Source coverage completeness and conditional-search completeness remain distinct.

## IMMUTABLE_SNAPSHOT_CONSTRUCTION / NO_AST_IN_PERSISTED_EVIDENCE / SOURCE_BINDING_LIMITATION / RUNTIME_UNCERTAINTY
The materializer feeds existing C34-C36 lexical classification and conditional discovery into existing frozen `CycleSemanticsSnapshot`; graph/cohort SCC member count is checked. The snapshot contains immutable reports, fingerprints and issue strings, not `ParsedSourceInput`, AST, raw bytes or executed modules. Source binding remains `NOT_ATOMICALLY_VERIFIED_BY_DISCOVERY`; runtime status remains `UNKNOWN_NOT_EVALUATED`. Per-worker SHA and observed cyclic-file matches do not prove a repository-wide atomic source snapshot, LIVE publication or runtime safety. No cycle_semantics_state, revision, persistence or report field was added.

## TEST_RESULTS / COLD_WARM_COMPATIBILITY / CONDITIONAL_REEXPORT_COMPATIBILITY / PICKLE_ROUNDTRIP / GUI_FREE_IMPORT
Targeted command: `.venv\Scripts\python.exe -B -m pytest -q tests/test_cycle_semantics_materialization.py tests/test_cycle_semantics_contracts.py tests/test_cycle_semantics_source_cohort.py tests/test_cycle_semantics_edge_sites.py tests/test_cycle_semantics_conditional_discovery.py tests/test_cycle_semantics_conditional_grouping.py tests/test_cycle_semantics_public_projection.py tests/test_index_fusion.py` → 119 passed in 10.22s; no skips/xfails, no full suite. Twelve new named test functions cover complete indexed cycle, changed source partial evidence, missing/extra/malformed hashes before cohort I/O, SCC-only semantic parse, empty SCC, bad limits, pickle, nonexecution of top-level RuntimeError, conditional reexports and GUI-free fresh import. COLD_WARM_COMPATIBILITY=PASS through existing `test_index_fusion.py` in same run and complete index-bound test. CONDITIONAL_REEXPORT_COMPATIBILITY=PASS: equivalent C34 synthetic indexed graph retained two candidates with provider `repo.main` and export `run_repo_generator`, hashes equal index evidence. PICKLE_ROUNDTRIP=PASS with exact report types. GUI_FREE_IMPORT=PASS in fresh interpreter; no contextor.ui or contextor.repo_generator modules loaded.

## NO_ADDITIONAL_INDEXER_IO / SEMANTIC_COHORT_IO_ACCOUNTING / NO_RUNTIME_IMPORT_EXECUTION
NO_ADDITIONAL_INDEXER_IO=PASS: no indexer file change and no new indexer read, hash or AST transport. SEMANTIC_COHORT_IO_ACCOUNTING: materializer deliberately reuses C34 cohort, which rereads and reparses cyclic SCC members and verifies file stability; C38B did not remove this separate semantic source processing. Test traced only `a.py` and `b.py` semantic parser calls, excluding indexed acyclic `unrelated.py`. No latency improvement measured or claimed. NO_RUNTIME_IMPORT_EXECUTION=PASS for synthetic top-level RuntimeError source; analysis remained static. Synthetic indexer tests do write isolated caches in tmp_path; production materializer itself has no persistence write or IPC.

## LIVE_AUTHORITY_BEFORE_AFTER / LIVE_REVISION_BEFORE_AFTER / ACTIVITY_EPOCH_BEFORE_AFTER / EVENT_CONTINUITY / WORKSPACE_SYNC
Read-only authority before/after identical: repo_id `ctx_8efc50d8`; root `C:\Temp\Contextor_Repo`; runtime_domain_id `rd1_4bb21e833272147f29727f8174356bdb3dbcba1b2d4965637b97183f8654`; service_instance_id `6f13273feccb46cb9c23fbbfee03afe1`; lease_generation 31; service_pid 11632; process_start_identity 134367226998365614; endpoint_fingerprint `1367eadf1a11448d1a74eec69518da568d80ee42be8f16ce15e54998e989fcbd`. No secrets printed. LIVE_REVISION_BEFORE_AFTER=487→489, ACTIVITY_EPOCH_BEFORE_AFTER unchanged `bbd40ce1942841df94718acedc12561f`. Contextor events after 487: 488 desktop_watcher UPDATED materialization.py; 489 desktop_watcher UPDATED test_cycle_semantics_materialization.py; continuity continuous, resync_required=false. Both new modules at revision 489 workspace_sync=verified, canonical_state=fresh, graph/topology/cycles/collisions fresh. Both are indexed. Production module outbound imports only four existing cycle_semantics modules; direct inbound only its new test module.

## COLLISIONS_BEFORE_AFTER / STRUCTURAL_CYCLES_BEFORE_AFTER
Name collisions 0→0, syntax errors 0→0, structural cycle diagnostics 16→16, all fresh. No new import cycles indicated by Contextor graph and unchanged cycle count. No diagnostic suppression, hardcoded exception, analyzed-module import, update_file, FULL analysis or restart.

MCP_SERVER_RESTART_REQUIRED=NO
DESKTOP_LIVE_RESTART_REQUIRED=NO

## FINAL_VERDICT
B0G4C38C_PASS. Approved implementation and all specified focused regressions passed; index hash domain and mismatch behavior are source- and test-proved; authority/epoch and structural diagnostics stable; both new files canonically synchronized; complete task diffs below. STOP; await `proceduj`.

## FULL_DIFFS
Complete actual new-file diffs for this task follow; no prior-task diffs.

### contextor/core/cycle_semantics/materialization.py
```diff
diff --git a/contextor/core/cycle_semantics/materialization.py b/contextor/core/cycle_semantics/materialization.py
new file mode 100644
index 0000000..be26c98
--- /dev/null
+++ b/contextor/core/cycle_semantics/materialization.py
@@ -0,0 +1,198 @@
+"""Index-bound, read-only Python cycle semantic materialization.
+
+The caller supplies a hard graph, indexed module
+paths and source hashes from one indexing result.
+
+The materializer checks each cyclic source against
+the supplied index fingerprint before accepting
+lexical evidence.
+
+This is NOT a repository-wide atomic snapshot
+transaction or a LIVE publication certificate.
+
+No state mutations, IPC, report writes or imports
+of analyzed modules occur here.
+"""
+
+from __future__ import annotations
+
+from collections.abc import Mapping
+from pathlib import Path
+
+from .conditional_discovery import (
+    discover_conditional_reexports,
+)
+from .contracts import (
+    CycleSemanticsSnapshot,
+    fingerprint_hard_edges,
+)
+from .edge_sites import analyze_cyclic_import_sites
+from .source_cohort import build_cycle_source_cohort
+
+
+def _validate_index_source_domain(
+    module_paths: Mapping[str, str | Path],
+    source_fingerprints_by_module: Mapping[str, str],
+) -> None:
+    """Require complete exact index-source identity coverage."""
+
+    if not isinstance(module_paths, Mapping):
+        raise TypeError(
+            "module_paths must be a mapping"
+        )
+
+    if not isinstance(
+        source_fingerprints_by_module,
+        Mapping,
+    ):
+        raise TypeError(
+            "source_fingerprints_by_module must be a mapping"
+        )
+
+    module_ids = set(module_paths)
+    fingerprint_ids = set(
+        source_fingerprints_by_module
+    )
+
+    if any(
+        type(module_id) is not str or not module_id
+        for module_id in module_ids | fingerprint_ids
+    ):
+        raise ValueError(
+            "Invalid indexed module identity"
+        )
+
+    if module_ids != fingerprint_ids:
+        raise ValueError(
+            "Index source fingerprint domain mismatch"
+        )
+
+    for module_id, fingerprint in (
+        source_fingerprints_by_module.items()
+    ):
+        if (
+            type(fingerprint) is not str
+            or len(fingerprint) != 64
+            or any(
+                character not in "0123456789abcdef"
+                for character in fingerprint
+            )
+        ):
+            raise ValueError(
+                "Invalid indexed source fingerprint: "
+                + module_id
+            )
+
+
+def materialize_cycle_semantics(
+    repository_root: str | Path,
+    hard_edges: Mapping[str, object],
+    module_paths: Mapping[str, str | Path],
+    source_fingerprints_by_module: Mapping[str, str],
+    *,
+    max_searches: int = 256,
+) -> CycleSemanticsSnapshot:
+    """Build immutable semantic evidence bound to index hashes.
+
+    The caller is responsible for supplying graph,
+    module paths and fingerprints associated with
+    the intended analysis generation.
+
+    Every accepted cyclic source must match its
+    indexer fingerprint.
+
+    A mismatch yields explicit partial evidence;
+    it never becomes a successful lexical match.
+
+    This function does not assign LIVE freshness
+    or a canonical publication revision.
+    """
+
+    if (
+        type(max_searches) is not int
+        or not 1 <= max_searches <= 4096
+    ):
+        raise ValueError(
+            "max_searches must be in range 1..4096"
+        )
+
+    _validate_index_source_domain(
+        module_paths,
+        source_fingerprints_by_module,
+    )
+
+    graph_sha256 = fingerprint_hard_edges(
+        hard_edges
+    )
+
+    cohort = build_cycle_source_cohort(
+        repository_root,
+        hard_edges,
+        module_paths,
+        expected_fingerprints=(
+            source_fingerprints_by_module
+        ),
+    )
+
+    if cohort.canonical_hash_missing != 0:
+        raise ValueError(
+            "Cyclic source evidence lacks index fingerprints"
+        )
+
+    if cohort.canonical_hash_matches != len(
+        cohort.parsed_sources
+    ):
+        raise ValueError(
+            "Accepted cyclic sources are not index-bound"
+        )
+
+    import_sites = analyze_cyclic_import_sites(
+        cohort.hard_edges,
+        cohort.parsed_sources,
+    )
+
+    discovery = discover_conditional_reexports(
+        import_sites,
+        cohort.parsed_sources,
+        cohort.indexed_module_ids,
+        max_searches=max_searches,
+    )
+
+    cyclic_modules = tuple(sorted({
+        module
+        for component in (
+            import_sites.topology.cyclic_components
+        )
+        for module in component.members
+    }))
+
+    if len(cyclic_modules) != (
+        cohort.cyclic_module_count
+    ):
+        raise ValueError(
+            "Cyclic cohort and graph topology differ"
+        )
+
+    return CycleSemanticsSnapshot(
+        graph_sha256=graph_sha256,
+        cyclic_modules=cyclic_modules,
+        observed_source_fingerprints=(
+            cohort.fingerprints
+        ),
+        source_issues=tuple(
+            (
+                issue.module_id,
+                issue.reason,
+            )
+            for issue in cohort.issues
+        ),
+        coverage_status=cohort.coverage_status,
+        source_snapshot_binding=(
+            cohort.source_snapshot_binding
+        ),
+        runtime_execution_status=(
+            cohort.runtime_execution_status
+        ),
+        import_sites=import_sites,
+        conditional_discovery=discovery,
+    )
```
### tests/test_cycle_semantics_materialization.py
```diff
diff --git a/tests/test_cycle_semantics_materialization.py b/tests/test_cycle_semantics_materialization.py
new file mode 100644
index 0000000..c8a3738
--- /dev/null
+++ b/tests/test_cycle_semantics_materialization.py
@@ -0,0 +1,305 @@
+"""Synthetic, index-bound cycle semantics materialization contracts."""
+
+from __future__ import annotations
+
+import dataclasses
+import hashlib
+import pickle
+import subprocess
+import sys
+
+import pytest
+
+from contextor.core.cycle_semantics import source_cohort
+from contextor.core.cycle_semantics.conditional_discovery import (
+    ConditionalDiscoveryReport,
+)
+from contextor.core.cycle_semantics.contracts import (
+    CycleSemanticsSnapshot,
+    fingerprint_hard_edges,
+)
+from contextor.core.cycle_semantics.edge_sites import CyclicImportSiteReport
+from contextor.core.cycle_semantics.materialization import (
+    materialize_cycle_semantics,
+)
+from contextor.core.symbol_engine.indexer import index_repository
+
+
+PAIR_GRAPH = {
+    "pkg.__init__": set(),
+    "pkg.a": {"pkg.b"},
+    "pkg.b": {"pkg.a"},
+}
+
+
+def _write_pair(root, *, extra_source: bytes | None = None):
+    package = root / "pkg"
+    package.mkdir(parents=True)
+    (package / "__init__.py").write_bytes(b"")
+    (package / "a.py").write_bytes(b"import pkg.b\nvalue = 1\n")
+    (package / "b.py").write_bytes(b"import pkg.a\nvalue = 2\n")
+    if extra_source is not None:
+        (package / "unrelated.py").write_bytes(extra_source)
+
+
+def _paths(index):
+    return {
+        module_id: module.absolute_path
+        for module_id, module in index.modules.items()
+    }
+
+
+def _index_pair(tmp_path, isolated_dirs, monkeypatch, *, extra_source=None):
+    monkeypatch.setenv("CONTEXTOR_DISABLE_PROCESS_POOL", "1")
+    root = tmp_path / "repo"
+    root.mkdir()
+    _write_pair(root, extra_source=extra_source)
+    index = index_repository(str(root))
+    return root, index
+
+
+def test_c38c_complete_index_bound_cycle(tmp_path, isolated_dirs, monkeypatch):
+    root, index = _index_pair(tmp_path, isolated_dirs, monkeypatch)
+    paths = _paths(index)
+    graph = {key: set(value) for key, value in PAIR_GRAPH.items()}
+    result = materialize_cycle_semantics(
+        root, graph, paths, index.source_fingerprints_by_module,
+    )
+
+    assert isinstance(result, CycleSemanticsSnapshot)
+    assert len(result.import_sites.topology.cyclic_components) == 1
+    assert result.cyclic_modules == ("pkg.a", "pkg.b")
+    assert result.coverage_status == "FILESYSTEM_STABLE_NON_ATOMIC"
+    assert result.observed_source_count == 2
+    assert result.unobserved_source_count == 0
+    assert result.source_issues == ()
+    assert dict(result.observed_source_fingerprints) == {
+        name: index.source_fingerprints_by_module[name]
+        for name in result.cyclic_modules
+    }
+    assert result.graph_sha256 == fingerprint_hard_edges(graph)
+    assert result.source_snapshot_binding == "NOT_ATOMICALLY_VERIFIED_BY_DISCOVERY"
+    assert result.runtime_execution_status == "UNKNOWN_NOT_EVALUATED"
+    assert type(result.import_sites) is CyclicImportSiteReport
+    assert type(result.conditional_discovery) is ConditionalDiscoveryReport
+    assert dataclasses.is_dataclass(result)
+    assert result.__dataclass_params__.frozen
+    assert not hasattr(result, "cycle_semantics_state")
+    assert not hasattr(result, "materialized_revision")
+    assert not hasattr(result, "canonical_graph_revision")
+
+
+def test_c38c_source_changed_after_index_is_partial(tmp_path, isolated_dirs, monkeypatch):
+    root, index = _index_pair(tmp_path, isolated_dirs, monkeypatch)
+    (root / "pkg" / "a.py").write_bytes(b"import pkg.b\nvalue = 99\n")
+    result = materialize_cycle_semantics(
+        root, PAIR_GRAPH, _paths(index), index.source_fingerprints_by_module,
+    )
+
+    assert result.coverage_status == "PARTIAL_SOURCE_EVIDENCE"
+    assert ("pkg.a", "CANONICAL_FINGERPRINT_MISMATCH") in result.source_issues
+    assert dict(result.observed_source_fingerprints) == {
+        "pkg.b": index.source_fingerprints_by_module["pkg.b"]
+    }
+    assert result.cyclic_modules == ("pkg.a", "pkg.b")
+    assert len(result.import_sites.topology.cyclic_components) == 1
+    edge = next(
+        edge for edge in result.import_sites.components[0].internal_edges
+        if edge.source == "pkg.a"
+    )
+    assert edge.status == "SOURCE_MISSING_OR_INVALID"
+    assert edge.sites == ()
+    assert result.runtime_execution_status == "UNKNOWN_NOT_EVALUATED"
+
+
+def test_c38c_missing_index_hash_rejected_before_io(tmp_path, monkeypatch):
+    called = []
+
+    def forbidden(*_args, **_kwargs):
+        called.append(True)
+        raise AssertionError("cohort builder called")
+
+    monkeypatch.setattr(
+        "contextor.core.cycle_semantics.materialization.build_cycle_source_cohort",
+        forbidden,
+    )
+    paths = {"pkg.a": "pkg/a.py", "pkg.b": "pkg/b.py"}
+    hashes = {"pkg.a": hashlib.sha256(b"a").hexdigest()}
+    with pytest.raises(ValueError, match="Index source fingerprint domain mismatch"):
+        materialize_cycle_semantics(tmp_path, PAIR_GRAPH, paths, hashes)
+    assert called == []
+
+
+def test_c38c_extra_index_hash_rejected(tmp_path, monkeypatch):
+    monkeypatch.setattr(
+        "contextor.core.cycle_semantics.materialization.build_cycle_source_cohort",
+        lambda *_a, **_k: pytest.fail("cohort builder called"),
+    )
+    paths = {"pkg.a": "pkg/a.py", "pkg.b": "pkg/b.py"}
+    digest = hashlib.sha256(b"source").hexdigest()
+    hashes = {"pkg.a": digest, "pkg.b": digest, "pkg.extra": digest}
+    with pytest.raises(ValueError, match="Index source fingerprint domain mismatch"):
+        materialize_cycle_semantics(tmp_path, PAIR_GRAPH, paths, hashes)
+
+
+@pytest.mark.parametrize("invalid", ["bad", "A" * 64, 1, "g" * 64])
+def test_c38c_invalid_index_hash_rejected(tmp_path, monkeypatch, invalid):
+    monkeypatch.setattr(
+        "contextor.core.cycle_semantics.materialization.build_cycle_source_cohort",
+        lambda *_a, **_k: pytest.fail("cohort builder called"),
+    )
+    paths = {"pkg.a": "pkg/a.py", "pkg.b": "pkg/b.py"}
+    digest = hashlib.sha256(b"source").hexdigest()
+    with pytest.raises(ValueError, match="Invalid indexed source fingerprint: pkg.a"):
+        materialize_cycle_semantics(
+            tmp_path, PAIR_GRAPH, paths, {"pkg.a": invalid, "pkg.b": digest},
+        )
+
+
+def test_c38c_only_cyclic_modules_are_parsed(tmp_path, isolated_dirs, monkeypatch):
+    root, index = _index_pair(
+        tmp_path, isolated_dirs, monkeypatch, extra_source=b"value = 7\n",
+    )
+    graph = dict(PAIR_GRAPH)
+    graph["pkg.unrelated"] = set()
+    graph_before = {name: set(targets) for name, targets in graph.items()}
+    hashes_before = dict(index.source_fingerprints_by_module)
+    calls = []
+    real_parse = source_cohort.parse_source_snapshot
+
+    def traced_parse(snapshot, path):
+        calls.append(path.name)
+        return real_parse(snapshot, path)
+
+    with monkeypatch.context() as scoped:
+        scoped.setattr(source_cohort, "parse_source_snapshot", traced_parse)
+        result = materialize_cycle_semantics(
+            root, graph, _paths(index), index.source_fingerprints_by_module,
+        )
+
+    assert sorted(calls) == ["a.py", "b.py"]
+    assert "pkg.unrelated" in index.modules
+    assert "pkg.unrelated" in index.source_fingerprints_by_module
+    assert graph == graph_before
+    assert index.source_fingerprints_by_module == hashes_before
+    assert result.cyclic_modules == ("pkg.a", "pkg.b")
+
+
+def test_c38c_empty_cyclic_graph(tmp_path, isolated_dirs, monkeypatch):
+    monkeypatch.setenv("CONTEXTOR_DISABLE_PROCESS_POOL", "1")
+    root = tmp_path / "repo"
+    root.mkdir()
+    (root / "module.py").write_bytes(b"value = 1\n")
+    index = index_repository(str(root))
+
+    with monkeypatch.context() as scoped:
+        scoped.setattr(
+            source_cohort, "read_source_snapshot",
+            lambda *_a, **_k: pytest.fail("acyclic source reread"),
+        )
+        result = materialize_cycle_semantics(
+            root, {"module": set()}, _paths(index),
+            index.source_fingerprints_by_module,
+        )
+
+    assert type(result) is CycleSemanticsSnapshot
+    assert result.cyclic_modules == ()
+    assert result.observed_source_fingerprints == ()
+    assert result.source_issues == ()
+    assert result.import_sites.topology.cyclic_components == ()
+
+
+@pytest.mark.parametrize("limit", [0, 4097, True, "256"])
+def test_c38c_rejects_invalid_search_limits(tmp_path, monkeypatch, limit):
+    monkeypatch.setattr(
+        "contextor.core.cycle_semantics.materialization.build_cycle_source_cohort",
+        lambda *_a, **_k: pytest.fail("cohort builder called"),
+    )
+    with pytest.raises(ValueError, match="max_searches must be in range 1..4096"):
+        materialize_cycle_semantics(tmp_path, {}, {}, {}, max_searches=limit)
+
+
+def test_c38c_snapshot_pickle_roundtrip(tmp_path, isolated_dirs, monkeypatch):
+    root, index = _index_pair(tmp_path, isolated_dirs, monkeypatch)
+    original = materialize_cycle_semantics(
+        root, PAIR_GRAPH, _paths(index), index.source_fingerprints_by_module,
+    )
+    restored = pickle.loads(pickle.dumps(original))
+    assert restored == original
+    assert type(restored.import_sites) is CyclicImportSiteReport
+    assert type(restored.conditional_discovery) is ConditionalDiscoveryReport
+
+
+def test_c38c_never_executes_analyzed_modules(tmp_path, isolated_dirs, monkeypatch):
+    monkeypatch.setenv("CONTEXTOR_DISABLE_PROCESS_POOL", "1")
+    root = tmp_path / "repo"
+    root.mkdir()
+    _write_pair(root)
+    (root / "pkg" / "a.py").write_bytes(
+        b"import pkg.b\nraise RuntimeError('must not execute')\n"
+    )
+    index = index_repository(str(root))
+    result = materialize_cycle_semantics(
+        root, PAIR_GRAPH, _paths(index), index.source_fingerprints_by_module,
+    )
+    assert result.coverage_status == "FILESYSTEM_STABLE_NON_ATOMIC"
+    assert result.runtime_execution_status == "UNKNOWN_NOT_EVALUATED"
+
+
+def test_c38c_conditional_reexport_evidence_preserved(
+    tmp_path, isolated_dirs, monkeypatch
+):
+    monkeypatch.setenv("CONTEXTOR_DISABLE_PROCESS_POOL", "1")
+    root = tmp_path / "repo"
+    root.mkdir()
+    sources = {
+        "repo.__init__": b"from repo.main import run_repo_generator\n",
+        "repo.main": (
+            b"from repo.filters import FilterWindow\n"
+            b"from ui import theme\n"
+            b"def run_repo_generator(parent=None):\n    pass\n"
+        ),
+        "repo.filters": b"from ui import theme\n",
+        "ui.__init__": b"from .gui import run\n",
+        "ui.gui": b"from repo import run_repo_generator\ndef run():\n    pass\n",
+    }
+    for module_id, raw in sources.items():
+        path = root.joinpath(*module_id.split(".")).with_suffix(".py")
+        path.parent.mkdir(parents=True, exist_ok=True)
+        path.write_bytes(raw)
+    graph = {
+        "repo.__init__": ("repo.main",),
+        "repo.main": ("repo.filters", "ui.__init__"),
+        "repo.filters": ("ui.__init__",),
+        "ui.__init__": ("ui.gui",),
+        "ui.gui": ("repo.__init__",),
+    }
+    index = index_repository(str(root))
+    result = materialize_cycle_semantics(
+        root, graph, _paths(index), index.source_fingerprints_by_module,
+    )
+    candidates = result.conditional_discovery.candidates
+    assert len(candidates) == 2
+    assert {candidate.provider for candidate in candidates} == {"repo.main"}
+    assert {candidate.export_name for candidate in candidates} == {"run_repo_generator"}
+    assert dict(result.observed_source_fingerprints) == {
+        module: index.source_fingerprints_by_module[module]
+        for module in result.cyclic_modules
+    }
+    assert result.runtime_execution_status == "UNKNOWN_NOT_EVALUATED"
+    assert result.coverage_status == "FILESYSTEM_STABLE_NON_ATOMIC"
+
+
+def test_c38c_materializer_cold_import_is_gui_free():
+    code = (
+        "import sys; import contextor.core.cycle_semantics.materialization; "
+        "assert not any(name.startswith(('contextor.ui', "
+        "'contextor.repo_generator')) for name in sys.modules)"
+    )
+    result = subprocess.run(
+        [sys.executable, "-B", "-c", code],
+        capture_output=True,
+        text=True,
+        check=False,
+    )
+    assert result.returncode == 0, result.stderr
```
