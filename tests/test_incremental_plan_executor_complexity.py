from pathlib import Path

import pytest

from contextor.core.analysis.incremental import (
    plan_executor,
)
from contextor.core.analysis.state_manager import (
    FileDelta,
    RepositoryAnalysisState,
)
from contextor.core.domain.refresh_plan import (
    RefreshPlan,
)
from contextor.core.domain.usage_facts import (
    ModuleUsageFacts,
)


class _NoFullScanDict(dict):
    def items(self):
        raise AssertionError(
            "indexed rebuild must not scan the full "
            "artifact_consumption mapping"
        )


def test_indexed_rebuild_uses_precomputed_domain_without_full_scan(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    consumption = _NoFullScanDict(
        {
            "provider::foo": {
                "consumers": [
                    "consumer",
                ],
                "channels": {
                    "consumer": [
                        "direct_calls",
                    ],
                },
            },
            "provider::bar": {
                "consumers": [],
                "channels": {},
            },
        }
    )

    usage = ModuleUsageFacts(
        direct_calls=(
            "provider.bar",
        ),
    )

    consumer_target_index = {
        "consumer": {
            "provider::foo",
        },
    }

    def fail_target_rebuild(
        artifacts,
    ):
        pytest.fail(
            "precomputed target domain must be reused"
        )

    monkeypatch.setattr(
        plan_executor,
        "canonical_artifact_consumption_targets",
        fail_target_rebuild,
    )

    rebuilt, is_ambiguous = (
        plan_executor._rebuild_consumer_slice(
            consumer="consumer",
            consumer_facts=usage,
            candidate_consumption=consumption,
            candidate_artifacts={
                "provider": {
                    "own_symbols": [
                        "foo",
                        "bar",
                    ],
                },
            },
            reexports={},
            expected_targets={
                "provider::foo",
                "provider::bar",
            },
            consumer_target_index=consumer_target_index,
        )
    )

    assert is_ambiguous is False
    assert rebuilt is consumption

    assert rebuilt[
        "provider::foo"
    ] == {
        "consumers": [],
        "channels": {},
    }

    assert rebuilt[
        "provider::bar"
    ] == {
        "consumers": [
            "consumer",
        ],
        "channels": {
            "consumer": [
                "direct_calls",
            ],
        },
    }

    assert consumer_target_index == {
        "consumer": {
            "provider::bar",
        },
    }


def test_execute_refresh_plan_builds_target_domain_once_for_many_consumers(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    state = RepositoryAnalysisState(
        artifacts={
            "provider": {
                "own_symbols": [
                    "foo",
                    "bar",
                ],
            },
        },
        artifact_consumption={
            "provider::foo": {
                "consumers": [
                    "consumer_a",
                    "consumer_b",
                ],
                "channels": {
                    "consumer_a": [
                        "direct_calls",
                    ],
                    "consumer_b": [
                        "direct_calls",
                    ],
                },
            },
            "provider::bar": {
                "consumers": [],
                "channels": {},
            },
        },
        artifact_consumption_state="fresh",
        module_usages={
            "consumer_a": ModuleUsageFacts(
                direct_calls=(
                    "provider.bar",
                ),
            ),
            "consumer_b": ModuleUsageFacts(
                direct_calls=(
                    "provider.bar",
                ),
            ),
        },
    )

    original_targets = (
        plan_executor
        .canonical_artifact_consumption_targets
    )
    target_domain_calls = 0

    def counted_targets(
        artifacts,
    ):
        nonlocal target_domain_calls
        target_domain_calls += 1
        return original_targets(
            artifacts
        )

    monkeypatch.setattr(
        plan_executor,
        "canonical_artifact_consumption_targets",
        counted_targets,
    )

    outcome = plan_executor.execute_refresh_plan(
        state=state,
        delta=FileDelta(
            module_path="changed",
        ),
        usage_delta=None,
        plan=RefreshPlan(
            recompute_modules=(
                "consumer_a",
                "consumer_b",
            ),
        ),
        new_imports=None,
        new_artifacts=None,
        new_usage=None,
        root_path=tmp_path,
        file_path=str(
            tmp_path
            / "changed.py"
        ),
    )

    assert target_domain_calls == 1

    assert state.artifact_consumption[
        "provider::foo"
    ][
        "consumers"
    ] == [
        "consumer_a",
        "consumer_b",
    ]

    assert outcome.candidate_state.artifact_consumption[
        "provider::foo"
    ] == {
        "consumers": [],
        "channels": {},
    }

    assert outcome.candidate_state.artifact_consumption[
        "provider::bar"
    ] == {
        "consumers": [
            "consumer_a",
            "consumer_b",
        ],
        "channels": {
            "consumer_a": [
                "direct_calls",
            ],
            "consumer_b": [
                "direct_calls",
            ],
        },
    }

    assert outcome.execution_trace[
        "recompute_modules"
    ] == (
        "consumer_a",
        "consumer_b",
    )
