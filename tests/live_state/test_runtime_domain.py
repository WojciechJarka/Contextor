from __future__ import annotations

import builtins
import json
import os
from pathlib import Path

import pytest

from contextor.core.live_state.runtime_domain import (
    RuntimeDomain,
    RuntimeDomainError,
    validate_runtime_domain,
)


def _production_domain(
    tmp_path: Path,
    *,
    service_instance_id: str | None = None,
) -> RuntimeDomain:
    repo = tmp_path / "repo"
    cache = tmp_path / "production-cache" / "ctx_repo"
    return RuntimeDomain.create(
        repo_id="ctx_repo",
        repo_root=repo,
        mode="production",
        cache_root=cache,
        logs_root=tmp_path / "production-logs",
        lock_root=cache / "runtime",
        ipc_endpoint_root=cache,
        service_instance_id=service_instance_id,
    )


def _test_domain(
    tmp_path: Path,
    run_id: str = "run-1",
    *,
    service_instance_id: str | None = None,
) -> RuntimeDomain:
    context = tmp_path / "test-domain" / run_id
    cache = context / "cache" / "ctx_repo"
    return RuntimeDomain.create(
        repo_id="ctx_repo",
        repo_root=tmp_path / "repo",
        mode="test",
        cache_root=cache,
        logs_root=context / "logs",
        lock_root=cache / "runtime",
        ipc_endpoint_root=cache,
        test_run_id=run_id,
        test_context_root=context,
        service_instance_id=service_instance_id,
        known_production_roots=(tmp_path / "production-cache", tmp_path / "production-logs"),
    )


def test_production_domain_is_valid_and_immutable(tmp_path: Path):
    domain = _production_domain(tmp_path)
    assert domain.mode == "production"
    assert domain.domain_id.startswith("rd1_")
    with pytest.raises(AttributeError):
        domain.mode = "test"  # type: ignore[misc]


def test_test_domain_requires_context_and_run_id(tmp_path: Path):
    with pytest.raises(RuntimeDomainError):
        RuntimeDomain.create(
            repo_id="ctx_repo",
            repo_root=tmp_path / "repo",
            mode="test",
            cache_root=tmp_path / "cache",
            logs_root=tmp_path / "logs",
            test_context_root=tmp_path,
            known_production_roots=(tmp_path / "production",),
        )
    with pytest.raises(RuntimeDomainError):
        RuntimeDomain.create(
            repo_id="ctx_repo",
            repo_root=tmp_path / "repo",
            mode="test",
            cache_root=tmp_path / "test" / "cache",
            logs_root=tmp_path / "test" / "logs",
            test_context_root=tmp_path / "test",
            known_production_roots=(tmp_path / "production",),
            test_run_id="",
        )


def test_production_forbids_test_run_id(tmp_path: Path):
    with pytest.raises(RuntimeDomainError):
        RuntimeDomain.create(
            repo_id="ctx_repo",
            repo_root=tmp_path / "repo",
            mode="production",
            cache_root=tmp_path / "cache",
            logs_root=tmp_path / "logs",
            test_run_id="run-1",
        )


def test_domain_id_is_deterministic_and_normalizes_equivalent_paths(tmp_path: Path):
    first = _production_domain(tmp_path)
    second = RuntimeDomain.create(
        repo_id="ctx_repo",
        repo_root=tmp_path / "nested" / ".." / "repo" / ".",
        mode="production",
        cache_root=tmp_path / "production-cache" / "ctx_repo" / ".",
        logs_root=tmp_path / "production-logs" / ".",
        lock_root=tmp_path / "production-cache" / "ctx_repo" / "runtime" / ".." / "runtime",
        ipc_endpoint_root=tmp_path / "production-cache" / "ctx_repo",
    )
    assert first.domain_id == second.domain_id
    assert first.serialize() == second.serialize()


def test_service_instance_id_is_not_part_of_stable_domain_id(tmp_path: Path):
    production_ids = {
        _production_domain(tmp_path, service_instance_id=value).domain_id
        for value in (None, "service-A", "service-B")
    }
    test_ids = {
        _test_domain(tmp_path, service_instance_id=value).domain_id
        for value in (None, "service-A", "service-B")
    }
    assert len(production_ids) == 1
    assert len(test_ids) == 1
    assert RuntimeDomain.deserialize(
        _production_domain(tmp_path, service_instance_id="service-A").serialize()
    ).service_instance_id == "service-A"
    assert RuntimeDomain.deserialize(
        _test_domain(tmp_path, service_instance_id="service-B").serialize()
    ).service_instance_id == "service-B"


def test_distinct_test_runs_are_distinct_domains(tmp_path: Path):
    assert _test_domain(tmp_path, "run-1").domain_id != _test_domain(tmp_path, "run-2").domain_id


def test_serialization_round_trip_preserves_identity(tmp_path: Path):
    original = _test_domain(tmp_path)
    restored = RuntimeDomain.deserialize(original.serialize())
    assert restored == original
    assert restored.test_context_root == original.test_context_root
    assert restored.serialize() == original.serialize()


def test_deserialize_rejects_test_root_outside_serialized_context(tmp_path: Path):
    payload = json.loads(_test_domain(tmp_path).serialize())
    payload["cache_root"] = str(tmp_path / "outside-cache")
    with pytest.raises(RuntimeDomainError):
        RuntimeDomain.deserialize(payload)


def test_production_and_test_resources_are_mechanically_separate(tmp_path: Path):
    production = _production_domain(tmp_path)
    test = _test_domain(tmp_path)
    assert production.domain_id != test.domain_id
    validate_runtime_domain(test, expected_mode="test", test_context_root=tmp_path / "test-domain" / "run-1", known_production_roots=(tmp_path / "production-cache", tmp_path / "production-logs"))
    validate_runtime_domain(production, expected_mode="production")


def test_test_domain_rejects_explicit_production_resource(tmp_path: Path):
    production = _production_domain(tmp_path)
    context = tmp_path / "test-domain" / "run-1"
    with pytest.raises(RuntimeDomainError):
        RuntimeDomain.create(
            repo_id="ctx_repo",
            repo_root=tmp_path / "repo",
            mode="test",
            cache_root=production.cache_root,
            logs_root=context / "logs",
            lock_root=production.lock_root,
            ipc_endpoint_root=production.ipc_endpoint_root,
            test_run_id="run-1",
            test_context_root=context,
            known_production_roots=(production.cache_root, production.logs_root),
        )


def test_production_domain_rejects_explicit_test_resource(tmp_path: Path):
    test = _test_domain(tmp_path)
    with pytest.raises(RuntimeDomainError):
        RuntimeDomain.create(
            repo_id="ctx_repo",
            repo_root=tmp_path / "repo",
            mode="production",
            cache_root=test.cache_root,
            logs_root=test.logs_root,
            lock_root=test.lock_root,
            ipc_endpoint_root=test.ipc_endpoint_root,
            known_test_roots=(tmp_path / "test-domain" / "run-1" ,),
        )


def test_illegal_root_overlap_is_rejected(tmp_path: Path):
    with pytest.raises(RuntimeDomainError):
        RuntimeDomain.create(
            repo_id="ctx_repo",
            repo_root=tmp_path / "repo",
            mode="production",
            cache_root=tmp_path / "cache",
            logs_root=tmp_path / "cache",
            lock_root=tmp_path / "cache" / "runtime",
            ipc_endpoint_root=tmp_path / "cache",
        )
    with pytest.raises(RuntimeDomainError):
        RuntimeDomain.create(
            repo_id="ctx_repo",
            repo_root=tmp_path / "repo",
            mode="production",
            cache_root=tmp_path / "cache",
            logs_root=tmp_path / "logs",
            lock_root=tmp_path / "cache" / "runtime",
            ipc_endpoint_root=tmp_path / "cache" / "runtime",
        )


def test_symlink_equivalent_root_overlap_is_rejected(tmp_path: Path):
    cache = tmp_path / "cache"
    cache.mkdir()
    alias = tmp_path / "cache-alias"
    try:
        alias.symlink_to(cache, target_is_directory=True)
    except NotImplementedError as exc:
        pytest.skip(f"symlink creation denied: {exc}")
    except OSError as exc:
        if getattr(exc, "winerror", None) == 1314:
            pytest.skip(f"symlink creation denied: {exc}")
        raise
    with pytest.raises(RuntimeDomainError):
        RuntimeDomain.create(
            repo_id="ctx_repo",
            repo_root=tmp_path / "repo",
            mode="production",
            cache_root=cache,
            logs_root=alias,
            lock_root=cache / "runtime",
            ipc_endpoint_root=cache,
        )


def test_validation_failure_does_not_open_resources(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    def fail(*_args, **_kwargs):
        raise AssertionError("resource opened during RuntimeDomain validation")

    monkeypatch.setattr(builtins, "open", fail)
    monkeypatch.setattr(os, "open", fail)
    monkeypatch.setattr(Path, "open", fail)
    with pytest.raises(RuntimeDomainError):
        RuntimeDomain.create(
            repo_id="ctx_repo",
            repo_root=tmp_path / "repo",
            mode="test",
            cache_root=tmp_path / "production" / "cache",
            logs_root=tmp_path / "test" / "logs",
            lock_root=tmp_path / "production" / "cache" / "runtime",
            ipc_endpoint_root=tmp_path / "production" / "cache",
            test_run_id="run-1",
            test_context_root=tmp_path / "test",
            known_production_roots=(tmp_path / "production",),
        )
