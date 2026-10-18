"""In-memory timing spans for one measured operation iteration."""

from contextlib import contextmanager, nullcontext
from time import perf_counter_ns


MAX_RECORDS = 30


class AtomicRecorder:
    def __init__(self, scope: str, selected_presets: frozenset[str], iteration: int):
        from contextor.core.profiling.registry import get_scope

        spec = get_scope(scope)
        if spec is None or not selected_presets.issubset(spec.presets):
            raise ValueError("Unknown scope or preset.")
        if type(iteration) is not int or iteration < 0:
            raise ValueError("Invalid iteration.")
        self.scope = scope
        self.selected_presets = selected_presets
        self.iteration = iteration
        self._records: list[dict[str, object]] = []

    def span(self, preset_name: str):
        from contextor.core.profiling.registry import get_scope

        if preset_name not in get_scope(self.scope).presets:
            raise ValueError("Unknown preset.")
        if preset_name not in self.selected_presets:
            return nullcontext()

        @contextmanager
        def measured():
            if len(self._records) >= MAX_RECORDS:
                raise RuntimeError("Atomic record limit exceeded.")
            start = perf_counter_ns()
            status = "ok"
            try:
                yield
            except BaseException:
                status = "failed"
                raise
            finally:
                self._records.append({
                    "preset": preset_name,
                    "iteration": self.iteration,
                    "duration_ns": perf_counter_ns() - start,
                    "status": status,
                })

        return measured()

    def records(self) -> tuple[dict[str, object], ...]:
        return tuple(dict(record) for record in self._records)
