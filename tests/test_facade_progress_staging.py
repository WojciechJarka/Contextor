"""Every facade workflow must reserve visible progress for final report work."""

import pytest

from contextor.core.api.facade import ContextorFacade


@pytest.mark.parametrize(
    ("operation", "final_stage"),
    [
        ("project", "Finalizing analysis"),
        ("layer", "Finalizing layer analysis"),
        ("single_file", "Finalizing single-file analysis"),
    ],
)
def test_facade_workflows_keep_progress_below_100_until_finalization(
    sample_repo, isolated_dirs, monkeypatch, operation, final_stage
):
    monkeypatch.setenv("CONTEXTOR_DISABLE_PROCESS_POOL", "1")
    events = []

    def capture(completed, total, label):
        events.append((completed, total, label))
        return True

    if operation == "project":
        ContextorFacade.analyze_project(str(sample_repo), progress_callback=capture)
    elif operation == "layer":
        ContextorFacade.analyze_layer(
            str(sample_repo), str(sample_repo / "core"), progress_callback=capture
        )
    else:
        ContextorFacade.analyze_single_file(
            str(sample_repo / "core" / "alpha.py"),
            str(sample_repo),
            progress_callback=capture,
        )

    assert events
    assert all(completed < total for completed, total, _label in events[:-1])
    assert events[-1][0] == events[-1][1]
    assert any(final_stage in label for _completed, _total, label in events)
