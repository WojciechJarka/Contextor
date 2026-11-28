"""Regression tests for full-analysis source fingerprint integrity."""

from __future__ import annotations

import hashlib
import importlib
from pathlib import Path

import pytest

from contextor.core.analysis.full_analysis_coordinator import (
    run_full_analysis_exclusive,
)
from contextor.core.live_state.store import (
    locked_committed_snapshot,
    read_metadata,
)
from contextor.core.paths import repo_cache_dir


def test_full_analysis_rejects_source_change_after_indexing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(
        "CONTEXTOR_CACHE_DIR", str(tmp_path / "cache")
    )
    monkeypatch.setenv(
        "CONTEXTOR_OUTPUT_DIR", str(tmp_path / "output")
    )
    monkeypatch.setenv(
        "CONTEXTOR_STATE_DIR", str(tmp_path / "state")
    )
    monkeypatch.setenv(
        "CONTEXTOR_REGISTRY_DIR", str(tmp_path / "registry")
    )
    monkeypatch.setenv("CONTEXTOR_DISABLE_PROCESS_POOL", "1")

    root = tmp_path / "repo"
    root.mkdir()

    (root / "dep_alpha.py").write_text(
        "ALPHA_VALUE = 1\n", encoding="utf-8"
    )
    (root / "dep_beta.py").write_text(
        "BETA_VALUE = 2\n", encoding="utf-8"
    )
    source = root / "consumer.py"
    source_a = (
        "import dep_alpha\n"
        "CONSUMER_VALUE = dep_alpha.ALPHA_VALUE\n"
    )
    source_b = (
        "import dep_beta\n"
        "CONSUMER_VALUE = dep_beta.BETA_VALUE\n"
    )
    source.write_text(source_a, encoding="utf-8")

    errors, result = run_full_analysis_exclusive(
        root, timeout=30.0
    )
    assert not errors, errors
    assert result is not None

    cache = repo_cache_dir(root)
    metadata_before = read_metadata(cache)
    assert metadata_before is not None

    facade_module = importlib.import_module(
        "contextor.core.api.facade"
    )
    original_index = facade_module.index_repository
    indexed_results = []

    def change_source_after_index(*args, **kwargs):
        indexed = original_index(*args, **kwargs)
        indexed_results.append(indexed)
        assert source.read_text(encoding="utf-8") == source_a
        assert indexed.source_fingerprints_by_module[
            "consumer"
        ] == hashlib.sha256(
            source.read_bytes()
        ).hexdigest()
        source.write_text(source_b, encoding="utf-8")
        return indexed

    monkeypatch.setattr(
        facade_module,
        "index_repository",
        change_source_after_index,
    )

    with pytest.raises(
        RuntimeError,
        match="Source changed during full analysis: consumer",
    ):
        run_full_analysis_exclusive(root, timeout=30.0)

    assert len(indexed_results) == 1
    assert source.read_text(encoding="utf-8") == source_b

    metadata_after = read_metadata(cache)
    assert metadata_after == metadata_before

    with locked_committed_snapshot(
        cache,
        expected_repo_id=metadata_before.repo_id,
        expected_root_path=str(root),
    ) as (state, metadata):
        assert metadata.revision == metadata_before.revision
        assert metadata.state_id == metadata_before.state_id
        assert {
            imp.module
            for imp in state.modules["consumer"].imports
        } == {"dep_alpha"}
        assert "dep_alpha" in state.dependency_graph.hard_edges[
            "consumer"
        ]
        assert "dep_beta" not in state.dependency_graph.hard_edges[
            "consumer"
        ]
