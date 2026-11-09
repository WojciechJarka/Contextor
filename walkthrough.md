# F1L — diagnostyczna atestacja F1H w procesie Desktop

## PREFLIGHT I KONTRAKT

HEAD przed edycją: `bd0638f8381bafbd9b11be0b7a1e3808a12dd7bf`. Zmodyfikowany przed zadaniem był tylko raport `walkthrough.md`; zachowano pozostałe pliki. Discovery rozpoczęto przez Contextor MCP. Potwierdzono canonical owner: `ContextorGUI._start_post_paint_tasks` (`contextor/ui/gui.py:359`) i istniejący `runtime_trace.trace_event` / `capture_trace_events`. Zwykły Desktop analysis wykonuje model w procesie GUI, w osobnym wątku; ta diagnostyka startuje w tym samym interpreterze. Sprawdzono aktualne anchory, użycie `recognize_typing_guard`, `_compile` i bezpieczny kontrakt `trace_event`.

Niezależny semantyczny preflight w osobnym CPython 3.15.2 potwierdził, że kompilacja bieżących bajtów bez wykonania modułu daje identyczny SHA256 `marshal.dumps(code)` dla `_compile`, a NAME/ATTRIBUTE dają dokładnie wymagane operacje. Był to test wykonalności metody, nie atestacja aktualnego Desktop.

## DOKŁADNY KONTRAKT ATESTACJI

Prywatna `_emit_f1h_runtime_attestation` pobiera funkcję z `scenarios.evaluate_package_import_order.__globals__["_compile"]` i wymaga identyczności z `package_model._compile`. Weryfikuje `co_filename` względem dokładnego `contextor/core/cycle_semantics/package_model.py`. Kompiluje aktualne bajty przez `compile(..., "exec", dont_inherit=True, optimize=sys.flags.optimize)`, bez wykonania module code; wymaga jednego top-level `CodeType` o `co_name="_compile"`. Porównuje SHA256 marshaled code objects.

Na rzeczywiście pobranej funkcji wykonuje syntetyczne AST NAME i ATTRIBUTE, po `package_model.recognize_typing_guard`. Wymagane operacje: NAME `("FROM","UNMODELED_STATEMENT")`; ATTRIBUTE `("IMPORT","UNMODELED_STATEMENT")`. Nie wykonuje importów analizowanych modułów. Jedno zdarzenie `GUI/F1H_LOADED_CODE_ATTESTATION` ma status `MATCH` tylko przy wszystkich zgodnych kontrolach, `MISMATCH` przy zaobserwowanej niezgodności, `UNAVAILABLE` przy wyjątku/niemożności dowodu. `result` zawiera oba hashe, obie sekwencje, `sys.version` i `sys.executable`; `path` wskazuje badany moduł. `trace_event` dodaje PID/TID/czas. Brak aktywnej sesji trace może oznaczać brak trwałego wpisu mimo wywołania funkcji; capture testowy potwierdza kontrakt zdarzenia.

`_start_post_paint_tasks` tworzy daemon thread wyłącznie przy `CONTEXTOR_F1H_ATTEST=1`. Bez flagi gałąź nie importuje modułu modelu ani nie wykonuje hashowania/AST. GUI nie jest blokowane; analizy repozytorium nie uruchomiono.

## TESTY

Celowany command:
`& .\.venv\Scripts\python.exe -m pytest -q tests/test_f1h_runtime_attestation.py tests/test_gui_live_startup.py::test_post_paint_tasks_do_not_wait_for_cache_cleanup tests/test_gui_backend_owner.py::test_post_paint_starts_backend_claim_before_cleanup_and_live`

Wynik: **6 passed**, 2 ostrzeżenia deprecation z zależności authlib/fastmcp. Nowe testy: MATCH bieżącego kodu i obu form, brak wykonania `pkg` (import spy), MISMATCH po podstawieniu innego code object, UNAVAILABLE przy błędzie odczytu źródła, brak startu diagnostyki bez flagi. Dwa istniejące testy post-paint przeszły. Bez pełnego pytest.

## MCP_POST_CHANGE_AUDIT

Po edycji Contextor MCP: `gui.py` `workspace_sync=verified`, canonical revision `1202`, `syntax_diagnostics=checked_and_none`, zero błędów. LIVE project overlay: 16 cykli strukturalnych (bez zmiany względem preflight), graph/cycles fresh, `cycle_semantics=stale`; nie przedstawiono stale jako fresh. Nie zmieniono źródła konstrukcji hard/soft graph ani modelu. Source sync i rewizja nie dowodzą, że obecny Desktop załadował nową funkcję diagnostyczną.

## RUNTIME_ADOPTION_BOUNDARY

Test MATCH wykonał się w osobnym procesie pytest. **Nie certyfikuje aktualnego procesu Desktop**. Nie restartowano Desktop/backendu i nie uzyskano zdarzenia atestacji pochodzącego z aktualnego PID Desktop. Status adopcji w bieżącym Desktop: `NOT_PROVEN`. Mechanizm jest gotowy do opt-in podczas uruchomienia Desktop z `CONTEXTOR_F1H_ATTEST=1`.

## FILES_CHANGED

- `contextor/ui/gui.py`
- `tests/test_f1h_runtime_attestation.py` (nowy)

## FULL_DIFFS

### contextor/ui/gui.py

```diff
diff --git a/contextor/ui/gui.py b/contextor/ui/gui.py
index 56bf1e3..b51eb58 100644
--- a/contextor/ui/gui.py
+++ b/contextor/ui/gui.py
@@ -6,9 +6,15 @@ state persistence, sub-windows and orchestrates the analysis process.
 """
 
 import os
+import ast
+import hashlib
+import json
+import marshal
+import sys
 import threading
 import time
 import tkinter as tk
+import types
 import uuid
 from datetime import datetime
 from queue import Empty, Queue
@@ -25,6 +31,7 @@ from contextor.core.analysis.full_analysis_coordinator import (
 from contextor.core.analysis.process_pool_lifecycle import (
     terminate_active_process_pools,
 )
+from contextor.core.runtime_trace import trace_event
 from contextor.core.api.facade import ContextorFacade
 from contextor.core.live_state import (
     DesktopLiveEventFeed,
@@ -87,6 +94,89 @@ BACKEND_OWNER_CLAIM_RETRY_DELAYS_SECONDS = (
     1.0,
 )
 
+
+def _emit_f1h_runtime_attestation() -> None:
+    module_path = Path(__file__).resolve().parents[1] / (
+        "core/cycle_semantics/package_model.py"
+    )
+    status = "UNAVAILABLE"
+    loaded_hash = None
+    source_hash = None
+    name_ops = None
+    attribute_ops = None
+    try:
+        from contextor.core.cycle_semantics import package_model, scenarios
+
+        loaded = scenarios.evaluate_package_import_order.__globals__["_compile"]
+        code = loaded.__code__
+        loaded_hash = hashlib.sha256(marshal.dumps(code)).hexdigest()
+        module_code = compile(
+            module_path.read_bytes(),
+            code.co_filename,
+            "exec",
+            dont_inherit=True,
+            optimize=sys.flags.optimize,
+        )
+        candidates = tuple(
+            value
+            for value in module_code.co_consts
+            if isinstance(value, types.CodeType) and value.co_name == "_compile"
+        )
+        if len(candidates) == 1:
+            source_hash = hashlib.sha256(
+                marshal.dumps(candidates[0])
+            ).hexdigest()
+
+        observed = []
+        for source in (
+            "from typing import TYPE_CHECKING\n"
+            "if TYPE_CHECKING:\n"
+            "    import pkg.b\n"
+            "value = 1\n",
+            "import typing\n"
+            "if typing.TYPE_CHECKING:\n"
+            "    import pkg.b\n"
+            "value = 1\n",
+        ):
+            tree = ast.parse(source)
+            guard = package_model.recognize_typing_guard(
+                tree, frozenset({"pkg.a", "pkg.b"})
+            )
+            steps = loaded(tree, "pkg.a", False, typing_guard=guard)
+            observed.append(
+                tuple(step.op for step in steps) if steps is not None else None
+            )
+        name_ops, attribute_ops = observed
+        status = "MATCH" if (
+            loaded is package_model._compile
+            and module_path.resolve() == Path(code.co_filename).resolve()
+            and source_hash is not None
+            and loaded_hash == source_hash
+            and name_ops == ("FROM", "UNMODELED_STATEMENT")
+            and attribute_ops == ("IMPORT", "UNMODELED_STATEMENT")
+        ) else "MISMATCH"
+    except Exception:
+        status = "UNAVAILABLE"
+
+    trace_event(
+        "GUI",
+        "F1H_LOADED_CODE_ATTESTATION",
+        status=status,
+        path=str(module_path),
+        result=json.dumps(
+            {
+                "loaded_sha256": loaded_hash,
+                "source_sha256": source_hash,
+                "NAME": name_ops,
+                "ATTRIBUTE": attribute_ops,
+                "python": sys.version,
+                "executable": sys.executable,
+            },
+            separators=(",", ":"),
+        ),
+    )
+
+
 class ContextorGUI:
     """
     Main application controller and view wrapper.
@@ -359,6 +449,12 @@ class ContextorGUI:
     def _start_post_paint_tasks(self):
         if getattr(self, "_closing", False):
             return
+        if os.environ.get("CONTEXTOR_F1H_ATTEST") == "1":
+            threading.Thread(
+                target=_emit_f1h_runtime_attestation,
+                name="contextor-f1h-attestation",
+                daemon=True,
+            ).start()
         self._start_backend_owner_claim()
         self._set_live_status("LIVE: initializing in background")
         def cleanup_worker():
```

### tests/test_f1h_runtime_attestation.py

```diff
diff --git a/tests/test_f1h_runtime_attestation.py b/tests/test_f1h_runtime_attestation.py
new file mode 100644
index 0000000..d3d2422
--- /dev/null
+++ b/tests/test_f1h_runtime_attestation.py
@@ -0,0 +1,96 @@
+import builtins
+import json
+import threading
+from pathlib import Path
+from types import SimpleNamespace
+from unittest.mock import Mock
+
+from contextor.core.cycle_semantics import package_model
+from contextor.core.runtime_trace import capture_trace_events
+from contextor.ui import gui
+
+
+def _attestation_event():
+    with capture_trace_events() as events:
+        gui._emit_f1h_runtime_attestation()
+    matches = [
+        event for event in events
+        if event["ev"] == "F1H_LOADED_CODE_ATTESTATION"
+    ]
+    assert len(matches) == 1
+    return matches[0], json.loads(matches[0]["result"])
+
+
+def test_current_loaded_code_matches_both_typing_guard_forms_without_importing_pkg(
+    monkeypatch,
+):
+    original_import = builtins.__import__
+    attempted = []
+
+    def guarded_import(name, *args, **kwargs):
+        if name == "pkg" or name.startswith("pkg."):
+            attempted.append(name)
+            raise AssertionError("analyzed import was executed")
+        return original_import(name, *args, **kwargs)
+
+    monkeypatch.setattr(builtins, "__import__", guarded_import)
+    event, result = _attestation_event()
+
+    assert event["d"] == "GUI"
+    assert event["status"] == "MATCH"
+    assert result["loaded_sha256"] == result["source_sha256"]
+    assert len(result["loaded_sha256"]) == 64
+    assert result["NAME"] == ["FROM", "UNMODELED_STATEMENT"]
+    assert result["ATTRIBUTE"] == ["IMPORT", "UNMODELED_STATEMENT"]
+    assert not attempted
+
+
+def test_different_loaded_code_object_is_mismatch(monkeypatch):
+    def substituted(*args, **kwargs):
+        return ()
+
+    monkeypatch.setattr(package_model, "_compile", substituted)
+    event, result = _attestation_event()
+
+    assert event["status"] == "MISMATCH"
+    assert result["loaded_sha256"] != result["source_sha256"]
+
+
+def test_source_read_failure_is_unavailable(monkeypatch):
+    original_read = Path.read_bytes
+
+    def failed_read(path):
+        if path.name == "package_model.py":
+            raise OSError("source unavailable")
+        return original_read(path)
+
+    monkeypatch.setattr(Path, "read_bytes", failed_read)
+    event, result = _attestation_event()
+
+    assert event["status"] == "UNAVAILABLE"
+    assert result["source_sha256"] is None
+
+
+def test_post_paint_does_not_start_attestation_without_flag(monkeypatch, tmp_path):
+    monkeypatch.delenv("CONTEXTOR_F1H_ATTEST", raising=False)
+    attestation = Mock()
+    cleanup_done = threading.Event()
+    monkeypatch.setattr(gui, "_emit_f1h_runtime_attestation", attestation)
+    monkeypatch.setattr(
+        gui,
+        "prune_startup_caches",
+        lambda: cleanup_done.set() or {"cache": {"errors": []}},
+    )
+    controller = SimpleNamespace(
+        _closing=False,
+        _start_backend_owner_claim=Mock(),
+        _set_live_status=Mock(),
+        _check_stale_excludes=Mock(),
+        repo_path_var=SimpleNamespace(get=lambda: str(tmp_path)),
+        _start_live_watcher=Mock(),
+    )
+
+    gui.ContextorGUI._start_post_paint_tasks(controller)
+
+    assert cleanup_done.wait(2)
+    attestation.assert_not_called()
```

## FINAL_VERDICT

Implementacja diagnostyczna i celowane testy: `PASS`. Atestacja F1H w aktualnym procesie Desktop: `NOT_PROVEN` do chwili otrzymania zdarzenia od tego procesu. Nie zmieniono modelu, LIVE, MCP ani innych plików produkcyjnych. Bez restartu, FULL, commitów i push.



