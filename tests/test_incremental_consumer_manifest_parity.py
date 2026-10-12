"""Focused canonical consumer-record and usage-manifest incremental regressions."""

from __future__ import annotations

import builtins
from copy import deepcopy
from dataclasses import replace
from pathlib import Path

import pytest

from contextor.core.api.facade import ContextorFacade
from contextor.core.domain.usage_facts import MODULE_USAGE_FACTS_SEMANTIC_VERSION
from contextor.core.live_state.hydration import hydrate_repository_engine
from contextor.core.reference.engine import CanonicalReferenceEvidenceUnavailable
from contextor.core.reporting_layer.artifact_usage_report import _module_own_symbols


def _engine(tmp_path: Path, sources: dict[str, str]):
    for name, content in sources.items():
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    errors, _ = ContextorFacade.analyze_project(str(tmp_path))
    assert not errors, errors
    hydrated = hydrate_repository_engine(tmp_path)
    assert hydrated is not None
    return hydrated.engine


def _assert_manifest_matches_tracked(engine, module_id: str, path: Path) -> None:
    entry = engine.state.module_usages_manifest[module_id]
    assert entry == {
        "module_id": module_id,
        "path": str(path.resolve()),
        "sha256": engine.state_manager.get_tracked_sha256(str(path)),
        "semantic_version": MODULE_USAGE_FACTS_SEMANTIC_VERSION,
    }
    assert entry["sha256"]


def test_added_unused_symbol_has_full_compatible_zero_consumer_record_and_cow(tmp_path):
    source = tmp_path / "provider.py"
    engine = _engine(tmp_path, {"provider.py": "EXISTING = 1\n"})
    previous_artifact = engine.state.artifacts["provider"]
    previous_artifact_copy = deepcopy(previous_artifact)
    previous_manifest = engine.state.module_usages_manifest

    source.write_text("EXISTING = 1\nNEW_SYMBOL = 2\n", encoding="utf-8")
    result = engine.update_file(str(source))

    assert result.status == "UPDATED"
    record = engine.state.artifacts["provider"]["consumers"]["NEW_SYMBOL"]
    assert record == {
        "signature": "",
        "consumers": [],
        "usage": {
            "direct_calls": [],
            "direct_calls_detail": [],
            "callback_calls": [],
            "callback_calls_detail": [],
            "event_bindings": [],
            "event_bindings_detail": [],
            "runtime_calls": [],
            "qualified_refs": [],
            "qualified_refs_detail": [],
            "api_imports": [],
            "inheritance": [],
            "inheritance_detail": [],
            "ambiguous_calls": [],
        },
        "consumer_count": {
            "total": 0,
            "direct_calls": 0,
            "callbacks": 0,
            "events": 0,
            "qualified_refs": 0,
            "api_imports": 0,
            "inheritance": 0,
        },
    }
    assert previous_artifact == previous_artifact_copy
    assert previous_artifact is not engine.state.artifacts["provider"]
    assert previous_manifest is not engine.state.module_usages_manifest
    _assert_manifest_matches_tracked(engine, "provider", source)


def test_removed_own_symbol_drops_record_and_preserves_unrelated_artifact(tmp_path):
    source = tmp_path / "provider.py"
    engine = _engine(
        tmp_path,
        {"provider.py": "KEEP = 1\nREMOVE_ME = 2\n", "unrelated.py": "OTHER = 3\n"},
    )
    old_provider = engine.state.artifacts["provider"]
    old_provider_copy = deepcopy(old_provider)
    unrelated = engine.state.artifacts["unrelated"]
    unrelated_copy = deepcopy(unrelated)

    source.write_text("KEEP = 1\n", encoding="utf-8")
    result = engine.update_file(str(source))

    assert result.status == "UPDATED"
    assert set(engine.state.artifacts["provider"]["consumers"]) == {"KEEP"}
    assert "provider::REMOVE_ME" not in engine.state.artifact_consumption
    assert old_provider == old_provider_copy
    assert unrelated == unrelated_copy
    assert engine.state.artifacts["unrelated"] is unrelated
    _assert_manifest_matches_tracked(engine, "provider", source)


def test_confirmed_consumer_change_refreshes_unchanged_definer_from_ram(tmp_path, monkeypatch):
    provider = tmp_path / "provider.py"
    consumer = tmp_path / "consumer.py"
    engine = _engine(
        tmp_path,
        {
            "provider.py": "def shared_function():\n    return 1\n",
            "consumer.py": "from provider import shared_function\n",
        },
    )
    old_provider = engine.state.artifacts["provider"]
    old_provider_copy = deepcopy(old_provider)
    provider_reads = []
    original_read_text = Path.read_text
    original_open = builtins.open

    def tracked_read_text(path, *args, **kwargs):
        if path.resolve() == provider.resolve():
            provider_reads.append(str(path))
            raise AssertionError("unchanged provider source was reread")
        return original_read_text(path, *args, **kwargs)

    def tracked_open(file, *args, **kwargs):
        if isinstance(file, (str, Path)) and Path(file).resolve() == provider.resolve():
            provider_reads.append(str(file))
            raise AssertionError("unchanged provider source was reopened")
        return original_open(file, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", tracked_read_text)
    monkeypatch.setattr(builtins, "open", tracked_open)
    consumer.write_text(
        "from provider import shared_function\nshared_function()\n",
        encoding="utf-8",
    )
    result = engine.update_file(str(consumer))

    assert result.status == "UPDATED"
    assert provider_reads == []
    record = engine.state.artifacts["provider"]["consumers"]["shared_function"]
    assert "consumer" in record["consumers"]
    assert record["usage"]["direct_calls"] == ["consumer"]
    assert record["consumer_count"]["direct_calls"] == 1
    assert record["usage"]["direct_calls_detail"]
    assert old_provider == old_provider_copy
    assert old_provider is not engine.state.artifacts["provider"]
    _assert_manifest_matches_tracked(engine, "consumer", consumer)


def test_added_symbol_with_existing_confirmed_consumer_has_exact_record(tmp_path):
    provider = tmp_path / "provider.py"
    engine = _engine(
        tmp_path,
        {
            "provider.py": "EXISTING = 1\n",
            "consumer.py": "import provider\nCONSUMED = provider.NEW_VALUE\n",
        },
    )
    provider.write_text("EXISTING = 1\nNEW_VALUE = 2\n", encoding="utf-8")
    result = engine.update_file(str(provider))

    assert result.status == "UPDATED"
    assert "NEW_VALUE" in _module_own_symbols(
        engine.state.artifacts["provider"]["symbols"]
    )
    assert "consumer" in engine.state.artifact_consumption[
        "provider::NEW_VALUE"
    ]["consumers"]
    record = engine.state.artifacts["provider"]["consumers"]["NEW_VALUE"]
    assert record["consumers"] == ["consumer"]
    assert record["usage"]["qualified_refs"] == ["consumer"]
    assert record["usage"]["qualified_refs_detail"]
    _assert_manifest_matches_tracked(engine, "provider", provider)


def test_deleted_module_drops_manifest_and_surviving_consumer_record(tmp_path):
    provider = tmp_path / "provider.py"
    consumer = tmp_path / "consumer.py"
    engine = _engine(
        tmp_path,
        {
            "provider.py": "def shared_function():\n    return 1\n",
            "consumer.py": "from provider import shared_function\nshared_function()\n",
        },
    )
    assert "consumer" in engine.state.artifacts["provider"]["consumers"][
        "shared_function"
    ]["consumers"]
    old_manifest = engine.state.module_usages_manifest
    consumer.unlink()
    result = engine.update_file(str(consumer))

    assert result.status == "DELETED"
    assert "consumer" not in engine.state.module_usages_manifest
    assert old_manifest is not engine.state.module_usages_manifest
    assert "consumer" not in engine.state.artifacts["provider"]["consumers"][
        "shared_function"
    ]["consumers"]
    assert engine.state.artifact_consumption["provider::shared_function"][
        "consumers"
    ] == []


def test_semantic_noop_acknowledges_new_source_hash_in_manifest(tmp_path):
    source = tmp_path / "provider.py"
    engine = _engine(tmp_path, {"provider.py": "VALUE = 1\n"})
    previous_sha = engine.state.module_usages_manifest["provider"]["sha256"]
    previous_manifest = engine.state.module_usages_manifest
    source.write_text("VALUE = 1\n# nonsemantic comment\n", encoding="utf-8")
    result = engine.update_file(str(source))

    assert result.status == "UNCHANGED"
    assert engine.state.module_usages_manifest["provider"]["sha256"] != previous_sha
    assert previous_manifest is not engine.state.module_usages_manifest
    _assert_manifest_matches_tracked(engine, "provider", source)


def test_unmaterialized_reference_evidence_fails_before_canonical_commit(tmp_path):
    source = tmp_path / "provider.py"
    engine = _engine(
        tmp_path,
        {"provider.py": "EXISTING = 1\n", "other.py": "OTHER = 2\n"},
    )
    engine.state.module_usages["other"] = replace(
        engine.state.module_usages["other"],
        reference_evidence_materialized=False,
    )
    old_artifacts = engine.state.artifacts
    old_manifest = engine.state.module_usages_manifest
    source.write_text("EXISTING = 1\nNEW_SYMBOL = 2\n", encoding="utf-8")

    with pytest.raises(CanonicalReferenceEvidenceUnavailable):
        engine.update_file(str(source))

    assert engine.state.artifacts is old_artifacts
    assert engine.state.module_usages_manifest is old_manifest
    assert "NEW_SYMBOL" not in engine.state.artifacts["provider"]["consumers"]


def test_missing_tracked_hash_cannot_return_successful_update(tmp_path, monkeypatch):
    source = tmp_path / "provider.py"
    engine = _engine(tmp_path, {"provider.py": "EXISTING = 1\n"})
    old_manifest = engine.state.module_usages_manifest
    monkeypatch.setattr(engine.state_manager, "get_tracked_sha256", lambda _path: "")
    source.write_text("EXISTING = 1\nNEW_SYMBOL = 2\n", encoding="utf-8")

    with pytest.raises(RuntimeError, match="Missing trusted source SHA-256"):
        engine.update_file(str(source))

    assert engine.state.module_usages_manifest is old_manifest
