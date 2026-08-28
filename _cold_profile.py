import importlib
import time

started = time.perf_counter()
gm = importlib.import_module("contextor.mcp.tools.get_module_context")
module_import_ms = (time.perf_counter() - started) * 1000

started = time.perf_counter()
q = importlib.import_module("contextor.mcp.query_helpers")
rq = importlib.import_module("contextor.core.report_query")
rt = importlib.import_module("contextor.mcp.runtime")
lazy_imports_ms = (time.perf_counter() - started) * 1000

timings = {}
def instrument(mod, name):
    original = getattr(mod, name)
    def wrapped(*args, **kwargs):
        t = time.perf_counter()
        value = original(*args, **kwargs)
        timings.setdefault(name, []).append((time.perf_counter() - t) * 1000)
        return value
    setattr(mod, name, wrapped)

for mod, name in ((q, "read_registries"), (rq, "catalog_from_registry"),
                  (rq, "resolve_index_query")):
    instrument(mod, name)
instrument(rt, "get_or_init_engine")

started = time.perf_counter()
result = gm.get_module_context(
    "C:/Temp/Contextor_Repo",
    module_name="contextor.mcp.tools.get_name_collisions",
    compact=True,
    max_items=5,
)
call_ms = (time.perf_counter() - started) * 1000
print("MODULE_IMPORT_MS", round(module_import_ms, 1))
print("LAZY_IMPORTS_MS", round(lazy_imports_ms, 1))
print("CALL_MS", round(call_ms, 1))
print("STAGES", {key: [round(value, 1) for value in values] for key, values in timings.items()})
print("RESULT_BYTES", len(result.encode("utf-8")))
