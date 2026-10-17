from __future__ import annotations

import ast
import copy
import hashlib
from pathlib import Path

import pytest

from contextor.core.cycle_semantics import source_cohort
from contextor.core.cycle_semantics.conditional_discovery import (
    discover_conditional_reexports,
)
from contextor.core.cycle_semantics.edge_sites import (
    analyze_cyclic_import_sites,
)
from contextor.core.cycle_semantics.public_projection import (
    project_cycle_semantics,
)
from contextor.core.cycle_semantics.scc import (
    analyze_import_cycle_topology,
)
from contextor.core.cycle_semantics.source_cohort import (
    build_cycle_source_cohort,
)


C34_FIXTURE_GRAPH = {
    "repo.__init__": ("repo.main",),
    "repo.main": ("repo.filters", "ui.__init__"),
    "repo.filters": ("ui.__init__",),
    "ui.__init__": ("ui.gui",),
    "ui.gui": ("repo.__init__",),
}

C34_FIXTURE_SOURCES = {
    "repo.__init__": (
        "from repo.main import run_repo_generator\n"
    ),
    "repo.main": (
        "from repo.filters import FilterWindow\n"
        "from ui import theme\n"
        "def run_repo_generator(parent=None):\n"
        "    pass\n"
    ),
    "repo.filters": "from ui import theme\n",
    "ui.__init__": "from .gui import run\n",
    "ui.gui": (
        "from repo import run_repo_generator\n"
        "def run():\n"
        "    pass\n"
    ),
}


def C34_FIXTURE_write_sources(
    root: Path,
    sources: dict[str, str | bytes],
) -> dict[str, Path]:
    module_paths = {}

    for module_id, source in sources.items():
        path = root.joinpath(*module_id.split(".")).with_suffix(
            ".py"
        )
        path.parent.mkdir(parents=True, exist_ok=True)

        raw = (
            source
            if isinstance(source, bytes)
            else source.encode("utf-8")
        )
        path.write_bytes(raw)
        module_paths[module_id] = path.relative_to(root)

    return module_paths


def C34_FIXTURE_pair_graph() -> dict[str, set[str]]:
    return {
        "pkg.a": {"pkg.b"},
        "pkg.b": {"pkg.a"},
    }


def test_c34_only_cyclic_scc_files_are_read(tmp_path, monkeypatch):
    root = tmp_path / "repo"
    root.mkdir()
    graph = {
        "pkg.a": {"pkg.b"},
        "pkg.b": {"pkg.a"},
        "pkg.outside": set(),
    }
    module_paths = C34_FIXTURE_write_sources(
        root,
        {
            "pkg.a": "value = 1\n",
            "pkg.b": "value = 2\n",
            "pkg.outside": "raise RuntimeError('not read')\n",
        },
    )

    read_paths = []
    original = Path.read_bytes

    def C34_FIXTURE_tracked_read(path):
        read_paths.append(Path(path).resolve())
        return original(path)

    monkeypatch.setattr(
        Path,
        "read_bytes",
        C34_FIXTURE_tracked_read,
    )

    cohort = build_cycle_source_cohort(
        root,
        graph,
        module_paths,
    )

    assert cohort.cyclic_module_count == 2
    assert set(cohort.parsed_sources) == {"pkg.a", "pkg.b"}
    cyclic_paths = {
        (root / module_paths[module]).resolve()
        for module in ("pkg.a", "pkg.b")
    }
    outside_path = (root / module_paths["pkg.outside"]).resolve()
    assert set(read_paths) == cyclic_paths
    assert all(read_paths.count(path) == 2 for path in cyclic_paths)
    assert outside_path not in read_paths
    assert cohort.hard_edges["pkg.outside"] == ()
    assert cohort.indexed_module_ids == tuple(sorted(module_paths))


def test_c34_canonical_hard_graph_not_mutated(tmp_path):
    root = tmp_path / "repo"
    root.mkdir()
    graph = {
        "pkg.b": ["pkg.a", "pkg.a"],
        "pkg.a": {"pkg.b"},
        "pkg.outside": [],
    }
    original_graph = copy.deepcopy(graph)
    module_paths = C34_FIXTURE_write_sources(
        root,
        {
            "pkg.a": "value = 1\n",
            "pkg.b": "value = 2\n",
            "pkg.outside": "value = 3\n",
        },
    )
    original_topology = analyze_import_cycle_topology(graph)

    cohort = build_cycle_source_cohort(
        root,
        graph,
        module_paths,
    )

    assert graph == original_graph
    assert cohort.hard_edges == {
        "pkg.a": ("pkg.b",),
        "pkg.b": ("pkg.a",),
        "pkg.outside": (),
    }
    assert analyze_import_cycle_topology(
        cohort.hard_edges
    ) == original_topology


def test_c34_source_hash_is_exact_raw_bytes(tmp_path):
    root = tmp_path / "repo"
    root.mkdir()
    raw = (
        b'# coding: latin-1\n'
        b'label = "caf\xe9"\n'
        b'raise RuntimeError("fixture must not execute")\n'
    )
    module_paths = C34_FIXTURE_write_sources(
        root,
        {"pkg.mod": raw},
    )
    cohort = build_cycle_source_cohort(
        root,
        {"pkg.mod": {"pkg.mod"}},
        module_paths,
    )
    source = cohort.parsed_sources["pkg.mod"]

    assert source.source_fingerprint == hashlib.sha256(raw).hexdigest()
    assert source.tree.body[0].value.value == "café"
    assert isinstance(source.tree.body[1], ast.Raise)
    assert cohort.issues == ()


def test_c34_expected_canonical_hash_matches(tmp_path):
    root = tmp_path / "repo"
    root.mkdir()
    module_paths = C34_FIXTURE_write_sources(
        root,
        {
            "pkg.a": "value = 1\n",
            "pkg.b": "value = 2\n",
        },
    )
    expected = {
        module: hashlib.sha256(
            (root / path).read_bytes()
        ).hexdigest()
        for module, path in module_paths.items()
    }

    cohort = build_cycle_source_cohort(
        root,
        C34_FIXTURE_pair_graph(),
        module_paths,
        expected_fingerprints=expected,
    )

    assert cohort.canonical_hash_matches == cohort.cyclic_module_count == 2
    assert cohort.canonical_hash_missing == 0
    assert cohort.issues == ()
    assert (
        cohort.source_snapshot_binding
        == "NOT_ATOMICALLY_VERIFIED_BY_DISCOVERY"
    )


def test_c34_canonical_fingerprint_mismatch_fails_closed(
    tmp_path,
):
    root = tmp_path / "repo"
    root.mkdir()
    module_paths = C34_FIXTURE_write_sources(
        root,
        {
            "pkg.a": "value = 1\n",
            "pkg.b": "value = 2\n",
        },
    )
    actual_a = hashlib.sha256(
        (root / module_paths["pkg.a"]).read_bytes()
    ).hexdigest()
    wrong = "0" * 64
    if wrong == actual_a:
        wrong = "f" * 64

    cohort = build_cycle_source_cohort(
        root,
        C34_FIXTURE_pair_graph(),
        module_paths,
        expected_fingerprints={
            "pkg.a": wrong,
            "pkg.b": hashlib.sha256(
                (root / module_paths["pkg.b"]).read_bytes()
            ).hexdigest(),
        },
    )

    assert any(
        issue.module_id == "pkg.a"
        and issue.reason == "CANONICAL_FINGERPRINT_MISMATCH"
        for issue in cohort.issues
    )
    assert "pkg.a" not in cohort.parsed_sources
    assert cohort.coverage_status == "PARTIAL_SOURCE_EVIDENCE"
    assert cohort.source_snapshot_binding == (
        "NOT_ATOMICALLY_VERIFIED_BY_DISCOVERY"
    )


def test_c34_missing_source_is_explicit(tmp_path):
    root = tmp_path / "repo"
    root.mkdir()
    module_paths = C34_FIXTURE_write_sources(
        root,
        {
            "pkg.a": "value = 1\n",
            "pkg.b": "value = 2\n",
        },
    )
    (root / module_paths["pkg.b"]).unlink()

    cohort = build_cycle_source_cohort(
        root,
        C34_FIXTURE_pair_graph(),
        module_paths,
    )

    assert any(
        issue.module_id == "pkg.b"
        and issue.reason == "SOURCE_UNREADABLE"
        for issue in cohort.issues
    )
    assert "pkg.b" not in cohort.parsed_sources
    assert analyze_import_cycle_topology(
        cohort.hard_edges
    ).cyclic_components
    assert cohort.coverage_status == "PARTIAL_SOURCE_EVIDENCE"


def test_c34_invalid_compilation_is_explicit(tmp_path):
    root = tmp_path / "repo"
    root.mkdir()
    module_paths = C34_FIXTURE_write_sources(
        root,
        {
            "pkg.a": "def invalid_scope():\n    from math import *\n",
            "pkg.b": "value = 2\n",
        },
    )

    cohort = build_cycle_source_cohort(
        root,
        C34_FIXTURE_pair_graph(),
        module_paths,
    )

    assert any(
        issue.module_id == "pkg.a"
        and issue.reason == "SOURCE_NOT_COMPILABLE"
        for issue in cohort.issues
    )
    assert "pkg.a" not in cohort.parsed_sources
    assert cohort.coverage_status == "PARTIAL_SOURCE_EVIDENCE"


def test_c34_repository_escape_rejected(tmp_path, monkeypatch):
    root = tmp_path / "repo"
    root.mkdir()
    outside = tmp_path / "outside.py"
    outside.write_text("value = 1\n", encoding="utf-8")

    read_paths = []
    original = Path.read_bytes

    def C34_FIXTURE_tracked_bytes(path):
        read_paths.append(Path(path).resolve())
        return original(path)

    monkeypatch.setattr(Path, "read_bytes", C34_FIXTURE_tracked_bytes)

    direct = build_cycle_source_cohort(
        root,
        {"pkg.a": {"pkg.a"}},
        {"pkg.a": outside},
    )
    assert any(
        issue.reason == "MISSING_OR_INVALID_CANONICAL_PATH"
        for issue in direct.issues
    )
    assert read_paths == []

    symlink = root / "pkg" / "link.py"
    symlink.parent.mkdir(parents=True)
    try:
        symlink.symlink_to(outside)
    except (OSError, NotImplementedError):
        return

    linked = build_cycle_source_cohort(
        root,
        {"pkg.a": {"pkg.a"}},
        {"pkg.a": symlink.relative_to(root)},
    )
    assert any(
        issue.reason == "MISSING_OR_INVALID_CANONICAL_PATH"
        for issue in linked.issues
    )
    assert read_paths == []


def test_c34_source_file_and_cohort_limits(tmp_path):
    root = tmp_path / "repo"
    root.mkdir()
    module_paths = C34_FIXTURE_write_sources(
        root,
        {
            "pkg.a": "value = 'a source that exceeds the file limit'\n",
            "pkg.b": "value = 'another source that exceeds the cohort limit'\n",
        },
    )
    graph = C34_FIXTURE_pair_graph()

    file_limited = build_cycle_source_cohort(
        root,
        graph,
        module_paths,
        max_source_bytes=16,
        max_total_source_bytes=1024,
    )
    assert any(
        issue.reason == "SOURCE_FILE_LIMIT"
        for issue in file_limited.issues
    )
    assert all(
        module not in file_limited.parsed_sources
        for module in ("pkg.a", "pkg.b")
    )
    assert analyze_import_cycle_topology(
        file_limited.hard_edges
    ).cyclic_components

    cohort_limited = build_cycle_source_cohort(
        root,
        graph,
        module_paths,
        max_source_bytes=1024,
        max_total_source_bytes=64,
    )
    assert any(
        issue.reason == "SOURCE_COHORT_BYTE_LIMIT"
        for issue in cohort_limited.issues
    )
    assert analyze_import_cycle_topology(
        cohort_limited.hard_edges
    ).cyclic_components
    assert cohort_limited.coverage_status == "PARTIAL_SOURCE_EVIDENCE"


def test_c34_changed_source_during_read_detected(
    tmp_path,
    monkeypatch,
):
    root = tmp_path / "repo"
    root.mkdir()
    module_paths = C34_FIXTURE_write_sources(
        root,
        {"pkg.a": "value = 1\n"},
    )
    original = source_cohort.read_source_snapshot
    changed_path = root / module_paths["pkg.a"]

    def C34_FIXTURE_change_after_snapshot(path):
        snapshot = original(path)
        Path(path).write_bytes(b"value = 2\n")
        return snapshot

    monkeypatch.setattr(
        source_cohort,
        "read_source_snapshot",
        C34_FIXTURE_change_after_snapshot,
    )
    cohort = build_cycle_source_cohort(
        root,
        {"pkg.a": {"pkg.a"}},
        module_paths,
    )

    assert changed_path.read_bytes() == b"value = 2\n"
    assert any(
        issue.module_id == "pkg.a"
        and issue.reason == "SOURCE_CHANGED_DURING_READ"
        for issue in cohort.issues
    )
    assert "pkg.a" not in cohort.parsed_sources
    assert cohort.coverage_status == "PARTIAL_SOURCE_EVIDENCE"
    assert cohort.source_snapshot_binding == (
        "NOT_ATOMICALLY_VERIFIED_BY_DISCOVERY"
    )


def test_c34_full_pure_pipeline_compatibility(tmp_path):
    root = tmp_path / "repo"
    root.mkdir()
    module_paths = C34_FIXTURE_write_sources(
        root,
        C34_FIXTURE_SOURCES,
    )
    cohort = build_cycle_source_cohort(
        root,
        C34_FIXTURE_GRAPH,
        module_paths,
    )
    topology = analyze_import_cycle_topology(cohort.hard_edges)
    import_sites = analyze_cyclic_import_sites(
        cohort.hard_edges,
        cohort.parsed_sources,
    )
    discovery = discover_conditional_reexports(
        import_sites,
        cohort.parsed_sources,
        cohort.indexed_module_ids,
    )
    projected = project_cycle_semantics(
        import_sites,
        discovery,
    )

    assert len(topology.cyclic_components) == 1
    assert cohort.cyclic_module_count == 5
    assert len(discovery.candidates) == 2
    assert projected["summary"]["cyclic_scc_total"] == 1
    assert projected["summary"]["conditional_witness_total"] == 2
    assert projected["summary"]["conditional_group_total"] == 1
    assert projected["runtime_execution_status"] == (
        "UNKNOWN_NOT_EVALUATED"
    )
    assert projected["source_snapshot_binding"] == (
        "NOT_ATOMICALLY_VERIFIED_BY_DISCOVERY"
    )


def test_c34_input_validation_and_determinism(tmp_path):
    root = tmp_path / "repo"
    root.mkdir()

    with pytest.raises(ValueError):
        build_cycle_source_cohort(
            root,
            {},
            {},
            max_cyclic_modules=0,
        )
    with pytest.raises(ValueError):
        build_cycle_source_cohort(
            root,
            {},
            {},
            max_source_bytes=True,
        )
    with pytest.raises(ValueError):
        build_cycle_source_cohort(
            root,
            {"": []},
            {},
        )
    with pytest.raises(TypeError):
        build_cycle_source_cohort(
            root,
            {"pkg.a": "pkg.b"},
            {},
        )
    with pytest.raises(ValueError):
        build_cycle_source_cohort(
            root,
            {},
            {"": "pkg/invalid.py"},
        )

    invalid_paths = C34_FIXTURE_write_sources(
        root,
        {"pkg.invalid": "value = 1\n"},
    )
    invalid_hash = build_cycle_source_cohort(
        root,
        {"pkg.invalid": {"pkg.invalid"}},
        invalid_paths,
        expected_fingerprints={"pkg.invalid": "not-a-sha256"},
    )
    assert any(
        issue.reason == "INVALID_CANONICAL_FINGERPRINT"
        for issue in invalid_hash.issues
    )
    assert "pkg.invalid" not in invalid_hash.parsed_sources

    deterministic_paths = C34_FIXTURE_write_sources(
        root,
        {
            "pkg.a": "value = 1\n",
            "pkg.b": "value = 2\n",
        },
    )
    first = build_cycle_source_cohort(
        root,
        {
            "pkg.b": {"pkg.a"},
            "pkg.a": {"pkg.b"},
        },
        deterministic_paths,
    )
    second = build_cycle_source_cohort(
        root,
        {
            "pkg.a": {"pkg.b"},
            "pkg.b": {"pkg.a"},
        },
        dict(reversed(tuple(deterministic_paths.items()))),
    )

    assert first.hard_edges == second.hard_edges
    assert first.indexed_module_ids == second.indexed_module_ids
    assert first.fingerprints == second.fingerprints
    assert first.issues == second.issues
    assert first.coverage_status == second.coverage_status
