"""Progress staging must reserve the final range for finalization work."""

from contextor.core.api.facade import _StagedProgress


def test_stage_progress_is_monotonic_and_reaches_100_only_on_finish():
    events = []
    progress = _StagedProgress(
        lambda completed, total, label: events.append((completed, total, label)),
        total_stages=3,
    )

    first = progress.begin("Indexing")
    first(5, 5, "module.py")
    progress.begin("Writing reports")
    progress.begin("Finalizing")

    assert [event[0] for event in events] == sorted(event[0] for event in events)
    assert all(completed < total for completed, total, _ in events)
    assert events[-1][2].startswith("Step 3/3: Finalizing")

    progress.finish()

    assert events[-1][0] == events[-1][1]
    assert "Analysis complete" in events[-1][2]


def test_stage_progress_propagates_cancellation_from_item_callback():
    calls = []

    def callback(*_args):
        calls.append(True)
        return len(calls) == 1

    progress = _StagedProgress(callback, total_stages=2)

    item_progress = progress.begin("Indexing")

    assert item_progress(1, 2, "module.py") is False


def test_stage_start_honours_stop_before_an_opaque_operation():
    import pytest

    from contextor.core.errors import AnalysisCancelled

    progress = _StagedProgress(lambda *_args: False, total_stages=1)

    with pytest.raises(AnalysisCancelled):
        progress.begin("Writing one atomic report")


def test_stage_progress_emits_one_readable_operation_log_per_stage():
    logs = []
    progress = _StagedProgress(None, total_stages=2, log=logs.append)

    progress.begin("Writing JSON report snapshots")
    progress.begin("Finalizing analysis")

    assert logs == [
        "[PROGRESS] Step 1/2: Writing JSON report snapshots",
        "[PROGRESS] Step 2/2: Finalizing analysis",
    ]
