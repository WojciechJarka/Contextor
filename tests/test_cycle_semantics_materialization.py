"""Synthetic, index-bound cycle semantics materialization contracts."""

from __future__ import annotations

import dataclasses
import hashlib
import pickle
import subprocess
import sys

import pytest

from contextor.core.cycle_semantics import source_cohort
from contextor.core.cycle_semantics.conditional_discovery import (
    ConditionalDiscoveryReport,
)
from contextor.core.cycle_semantics.contracts import (
    CycleSemanticsSnapshot,
    fingerprint_hard_edges,
)
from contextor.core.cycle_semantics.edge_sites import CyclicImportSiteReport
from contextor.core.cycle_semantics.materialization import (
    materialize_cycle_semantics,
)
from contextor.core.symbol_engine.indexer import index_repository


PAIR_GRAPH = {
    "pkg.__init__": set(),
    "pkg.a": {"pkg.b"},
    "pkg.b": {"pkg.a"},
}


def _write_pair(root, *, extra_source: bytes | None = None):
    package = root / "pkg"
    package.mkdir(parents=True)
    (package / "__init__.py").write_bytes(b"")
    (package / "a.py").write_bytes(b"import pkg.b\nvalue = 1\n")
    (package / "b.py").write_bytes(b"import pkg.a\nvalue = 2\n")
    if extra_source is not None:
        (package / "unrelated.py").write_bytes(extra_source)


def _paths(index):
    return {
        module_id: module.absolute_path
        for module_id, module in index.modules.items()
    }


def _index_pair(tmp_path, isolated_dirs, monkeypatch, *, extra_source=None):
    monkeypatch.setenv("CONTEXTOR_DISABLE_PROCESS_POOL", "1")
    root = tmp_path / "repo"
    root.mkdir()
    _write_pair(root, extra_source=extra_source)
    index = index_repository(str(root))
    return root, index


def test_c38c_complete_index_bound_cycle(tmp_path, isolated_dirs, monkeypatch):
    root, index = _index_pair(tmp_path, isolated_dirs, monkeypatch)
    paths = _paths(index)
    graph = {key: set(value) for key, value in PAIR_GRAPH.items()}
    result = materialize_cycle_semantics(
        root, graph, paths, index.source_fingerprints_by_module,
    )

    assert isinstance(result, CycleSemanticsSnapshot)
    assert len(result.import_sites.topology.cyclic_components) == 1
    assert result.cyclic_modules == ("pkg.a", "pkg.b")
    assert result.coverage_status == "FILESYSTEM_STABLE_NON_ATOMIC"
    assert result.observed_source_count == 2
    assert result.unobserved_source_count == 0
    assert result.source_issues == ()
    assert dict(result.observed_source_fingerprints) == {
        name: index.source_fingerprints_by_module[name]
        for name in result.cyclic_modules
    }
    assert result.graph_sha256 == fingerprint_hard_edges(graph)
    assert result.source_snapshot_binding == "NOT_ATOMICALLY_VERIFIED_BY_DISCOVERY"
    assert result.runtime_execution_status == "UNKNOWN_NOT_EVALUATED"
    assert type(result.import_sites) is CyclicImportSiteReport
    assert type(result.conditional_discovery) is ConditionalDiscoveryReport
    assert dataclasses.is_dataclass(result)
    assert result.__dataclass_params__.frozen
    assert not hasattr(result, "cycle_semantics_state")
    assert not hasattr(result, "materialized_revision")
    assert not hasattr(result, "canonical_graph_revision")


def test_c38c_source_changed_after_index_is_partial(tmp_path, isolated_dirs, monkeypatch):
    root, index = _index_pair(tmp_path, isolated_dirs, monkeypatch)
    (root / "pkg" / "a.py").write_bytes(b"import pkg.b\nvalue = 99\n")
    result = materialize_cycle_semantics(
        root, PAIR_GRAPH, _paths(index), index.source_fingerprints_by_module,
    )

    assert result.coverage_status == "PARTIAL_SOURCE_EVIDENCE"
    assert ("pkg.a", "CANONICAL_FINGERPRINT_MISMATCH") in result.source_issues
    assert dict(result.observed_source_fingerprints) == {
        "pkg.b": index.source_fingerprints_by_module["pkg.b"]
    }
    assert result.cyclic_modules == ("pkg.a", "pkg.b")
    assert len(result.import_sites.topology.cyclic_components) == 1
    edge = next(
        edge for edge in result.import_sites.components[0].internal_edges
        if edge.source == "pkg.a"
    )
    assert edge.status == "SOURCE_MISSING_OR_INVALID"
    assert edge.sites == ()
    assert result.runtime_execution_status == "UNKNOWN_NOT_EVALUATED"


def test_c38c_missing_index_hash_rejected_before_io(tmp_path, monkeypatch):
    called = []

    def forbidden(*_args, **_kwargs):
        called.append(True)
        raise AssertionError("cohort builder called")

    monkeypatch.setattr(
        "contextor.core.cycle_semantics.materialization.build_cycle_source_cohort",
        forbidden,
    )
    paths = {"pkg.a": "pkg/a.py", "pkg.b": "pkg/b.py"}
    hashes = {"pkg.a": hashlib.sha256(b"a").hexdigest()}
    with pytest.raises(ValueError, match="Index source fingerprint domain mismatch"):
        materialize_cycle_semantics(tmp_path, PAIR_GRAPH, paths, hashes)
    assert called == []


def test_c38c_extra_index_hash_rejected(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "contextor.core.cycle_semantics.materialization.build_cycle_source_cohort",
        lambda *_a, **_k: pytest.fail("cohort builder called"),
    )
    paths = {"pkg.a": "pkg/a.py", "pkg.b": "pkg/b.py"}
    digest = hashlib.sha256(b"source").hexdigest()
    hashes = {"pkg.a": digest, "pkg.b": digest, "pkg.extra": digest}
    with pytest.raises(ValueError, match="Index source fingerprint domain mismatch"):
        materialize_cycle_semantics(tmp_path, PAIR_GRAPH, paths, hashes)


@pytest.mark.parametrize("invalid", ["bad", "A" * 64, 1, "g" * 64])
def test_c38c_invalid_index_hash_rejected(tmp_path, monkeypatch, invalid):
    monkeypatch.setattr(
        "contextor.core.cycle_semantics.materialization.build_cycle_source_cohort",
        lambda *_a, **_k: pytest.fail("cohort builder called"),
    )
    paths = {"pkg.a": "pkg/a.py", "pkg.b": "pkg/b.py"}
    digest = hashlib.sha256(b"source").hexdigest()
    with pytest.raises(ValueError, match="Invalid indexed source fingerprint: pkg.a"):
        materialize_cycle_semantics(
            tmp_path, PAIR_GRAPH, paths, {"pkg.a": invalid, "pkg.b": digest},
        )


def test_c38c_only_cyclic_modules_are_parsed(tmp_path, isolated_dirs, monkeypatch):
    root, index = _index_pair(
        tmp_path, isolated_dirs, monkeypatch, extra_source=b"value = 7\n",
    )
    graph = dict(PAIR_GRAPH)
    graph["pkg.unrelated"] = set()
    graph_before = {name: set(targets) for name, targets in graph.items()}
    hashes_before = dict(index.source_fingerprints_by_module)
    calls = []
    real_parse = source_cohort.parse_source_snapshot

    def traced_parse(snapshot, path):
        calls.append(path.name)
        return real_parse(snapshot, path)

    with monkeypatch.context() as scoped:
        scoped.setattr(source_cohort, "parse_source_snapshot", traced_parse)
        result = materialize_cycle_semantics(
            root, graph, _paths(index), index.source_fingerprints_by_module,
        )

    assert sorted(calls) == ["a.py", "b.py"]
    assert "pkg.unrelated" in index.modules
    assert "pkg.unrelated" in index.source_fingerprints_by_module
    assert graph == graph_before
    assert index.source_fingerprints_by_module == hashes_before
    assert result.cyclic_modules == ("pkg.a", "pkg.b")


def test_c38c_empty_cyclic_graph(tmp_path, isolated_dirs, monkeypatch):
    monkeypatch.setenv("CONTEXTOR_DISABLE_PROCESS_POOL", "1")
    root = tmp_path / "repo"
    root.mkdir()
    (root / "module.py").write_bytes(b"value = 1\n")
    index = index_repository(str(root))

    with monkeypatch.context() as scoped:
        scoped.setattr(
            source_cohort, "read_source_snapshot",
            lambda *_a, **_k: pytest.fail("acyclic source reread"),
        )
        result = materialize_cycle_semantics(
            root, {"module": set()}, _paths(index),
            index.source_fingerprints_by_module,
        )

    assert type(result) is CycleSemanticsSnapshot
    assert result.cyclic_modules == ()
    assert result.observed_source_fingerprints == ()
    assert result.source_issues == ()
    assert result.import_sites.topology.cyclic_components == ()


@pytest.mark.parametrize("limit", [0, 4097, True, "256"])
def test_c38c_rejects_invalid_search_limits(tmp_path, monkeypatch, limit):
    monkeypatch.setattr(
        "contextor.core.cycle_semantics.materialization.build_cycle_source_cohort",
        lambda *_a, **_k: pytest.fail("cohort builder called"),
    )
    with pytest.raises(ValueError, match="max_searches must be in range 1..4096"):
        materialize_cycle_semantics(tmp_path, {}, {}, {}, max_searches=limit)


def test_c38c_snapshot_pickle_roundtrip(tmp_path, isolated_dirs, monkeypatch):
    root, index = _index_pair(tmp_path, isolated_dirs, monkeypatch)
    original = materialize_cycle_semantics(
        root, PAIR_GRAPH, _paths(index), index.source_fingerprints_by_module,
    )
    restored = pickle.loads(pickle.dumps(original))
    assert restored == original
    assert type(restored.import_sites) is CyclicImportSiteReport
    assert type(restored.conditional_discovery) is ConditionalDiscoveryReport


def test_c38c_never_executes_analyzed_modules(tmp_path, isolated_dirs, monkeypatch):
    monkeypatch.setenv("CONTEXTOR_DISABLE_PROCESS_POOL", "1")
    root = tmp_path / "repo"
    root.mkdir()
    _write_pair(root)
    (root / "pkg" / "a.py").write_bytes(
        b"import pkg.b\nraise RuntimeError('must not execute')\n"
    )
    index = index_repository(str(root))
    result = materialize_cycle_semantics(
        root, PAIR_GRAPH, _paths(index), index.source_fingerprints_by_module,
    )
    assert result.coverage_status == "FILESYSTEM_STABLE_NON_ATOMIC"
    assert result.runtime_execution_status == "UNKNOWN_NOT_EVALUATED"


def test_c38c_conditional_reexport_evidence_preserved(
    tmp_path, isolated_dirs, monkeypatch
):
    monkeypatch.setenv("CONTEXTOR_DISABLE_PROCESS_POOL", "1")
    root = tmp_path / "repo"
    root.mkdir()
    sources = {
        "repo.__init__": b"from repo.main import run_repo_generator\n",
        "repo.main": (
            b"from repo.filters import FilterWindow\n"
            b"from ui import theme\n"
            b"def run_repo_generator(parent=None):\n    pass\n"
        ),
        "repo.filters": b"from ui import theme\n",
        "ui.__init__": b"from .gui import run\n",
        "ui.gui": b"from repo import run_repo_generator\ndef run():\n    pass\n",
    }
    for module_id, raw in sources.items():
        path = root.joinpath(*module_id.split(".")).with_suffix(".py")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
    graph = {
        "repo.__init__": ("repo.main",),
        "repo.main": ("repo.filters", "ui.__init__"),
        "repo.filters": ("ui.__init__",),
        "ui.__init__": ("ui.gui",),
        "ui.gui": ("repo.__init__",),
    }
    index = index_repository(str(root))
    result = materialize_cycle_semantics(
        root, graph, _paths(index), index.source_fingerprints_by_module,
    )
    candidates = result.conditional_discovery.candidates
    assert len(candidates) == 2
    assert {candidate.provider for candidate in candidates} == {"repo.main"}
    assert {candidate.export_name for candidate in candidates} == {"run_repo_generator"}
    assert dict(result.observed_source_fingerprints) == {
        module: index.source_fingerprints_by_module[module]
        for module in result.cyclic_modules
    }
    assert result.runtime_execution_status == "UNKNOWN_NOT_EVALUATED"
    assert result.coverage_status == "FILESYSTEM_STABLE_NON_ATOMIC"


def test_c38c_materializer_cold_import_is_gui_free():
    code = (
        "import sys; import contextor.core.cycle_semantics.materialization; "
        "assert not any(name.startswith(('contextor.ui', "
        "'contextor.repo_generator')) for name in sys.modules)"
    )
    result = subprocess.run(
        [sys.executable, "-B", "-c", code],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
