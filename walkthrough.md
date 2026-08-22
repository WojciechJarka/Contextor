# A21.2 F2 — EXACT PATCH: REMOVE UNREQUESTED NEGATIVE after_revision RESTRICTION

## FILES_CHANGED
1. `C:\Temp\Contextor_Repo\contextor\core\live_state\ipc.py`
2. `C:\Temp\Contextor_Repo\tests\test_live_state_ipc.py`

---

## ACTUAL_DIFF
```diff
diff --git a/contextor/core/live_state/ipc.py b/contextor/core/live_state/ipc.py
index 23b7ad8..ac79be2 100644
--- a/contextor/core/live_state/ipc.py
+++ b/contextor/core/live_state/ipc.py
@@ -144,14 +144,56 @@ class CanonicalLiveServer:
             if operation == "get_events":
                 after_revision = request.get("after_revision")
                 limit = request.get("limit", 20)
+
+                if after_revision is not None and (
+                    isinstance(after_revision, bool)
+                    or not isinstance(after_revision, int)
+                ):
+                    return {"status": "error", "error": "invalid_after_revision"}
+
+                earliest_retained_revision = self._events[0]["revision"] if self._events else None
+                latest_revision = self._revision
+
+                if after_revision is None:
+                    continuity = "not_requested"
+                    resync_required = False
+                    resync_reason = None
+                elif after_revision > latest_revision:
+                    continuity = "gap"
+                    resync_required = True
+                    resync_reason = "revision_discontinuity"
+                elif not self._events:
+                    if after_revision == latest_revision:
+                        continuity = "continuous"
+                        resync_required = False
+                        resync_reason = None
+                    else:
+                        continuity = "gap"
+                        resync_required = True
+                        resync_reason = "event_retention_gap"
+                else:
+                    if after_revision < earliest_retained_revision - 1:
+                        continuity = "gap"
+                        resync_required = True
+                        resync_reason = "event_retention_gap"
+                    else:
+                        continuity = "continuous"
+                        resync_required = False
+                        resync_reason = None
+
                 events = self._events
-                if isinstance(after_revision, int) and not isinstance(after_revision, bool):
+                if after_revision is not None:
                     events = [event for event in events if event["revision"] > after_revision]
                 total = len(events)
                 selected = events if limit is None else events[:max(0, int(limit))]
                 return {
                     "status": "ok",
                     "revision": self._revision,
+                    "latest_revision": latest_revision,
+                    "earliest_retained_revision": earliest_retained_revision,
+                    "continuity": continuity,
+                    "resync_required": resync_required,
+                    "resync_reason": resync_reason,
                     "events": selected,
                     "total": total,
                     "truncated": len(selected) < total,
```

---

## NEGATIVE_CURSOR_RESTRICTION_REMOVED=YES
Usunięto warunek `or after_revision < 0`. Walidacja sprawdza wyłącznie, czy typ jest liczbą całkowitą różną od `bool` (`isinstance(after_revision, int) and not isinstance(after_revision, bool)`).

---

## INVALID_STRING_RESULT
`after_revision="1"` zwraca kontrolowany błąd `{"status": "error", "error": "invalid_after_revision"}` (bez wyjątku `TypeError`).

---

## INVALID_FLOAT_RESULT
`after_revision=1.5` zwraca kontrolowany błąd `{"status": "error", "error": "invalid_after_revision"}` (bez wyjątku `TypeError`).

---

## INVALID_BOOL_RESULT
`after_revision=True` oraz `after_revision=False` zwracają `{"status": "error", "error": "invalid_after_revision"}`.

---

## NEGATIVE_INTEGER_RESULT
`after_revision=-1` jest w pełni poprawnym kursorem całkowitym. Zwraca `status="ok"` i oblicza ciągłość względem okna retencji (dla bufora z najstarszym zdarzeniem `51` ujemny kursor poprawnie wskazuje `continuity="gap"`, `resync_required=true`, `resync_reason="event_retention_gap"`).

---

## ZERO_INTEGER_RESULT
`after_revision=0` przechodzi walidację i oblicza ciągłość zgodnie z oknem retencji.

---

## CONTINUITY_CONTRACT_PRESERVED
- `after_revision=None` => `continuity="not_requested", resync_required=false, resync_reason=null`
- `after_revision > latest_revision` => `continuity="gap", resync_required=true, resync_reason="revision_discontinuity"`
- pusty bufor + `after_revision == latest` => `continuity="continuous", resync_required=false`
- pusty bufor + `after_revision < latest` => `continuity="gap", resync_required=true, resync_reason="event_retention_gap"`
- niepusty bufor + `after_revision < earliest_retained_revision - 1` => `continuity="gap", resync_required=true, resync_reason="event_retention_gap"`
- niepusty bufor + `after_revision >= earliest_retained_revision - 1` => `continuity="continuous", resync_required=false`
- `total` i `truncated` semantyka bez zmian.

---

## RETENTION_UNCHANGED=100
Zachowano dokładnie 100 zdarzeń w buforze pamięci RAM (`del self._events[:-100]`).

---

## TARGETED_TEST_RESULTS
- `tests\test_live_state_ipc.py` oraz `tests\test_live_e2e_corrections.py`: **40 passed, 0 failed** (100% sukcesu).

---

## OPEN_P0
0

## OPEN_P1
0

## OPEN_P2
0

## OPEN_P3
0

---

## STEP_VERDICT
`PASS`

---

A21.2 SOURCE PASS — revision cursor validation protects continuity arithmetic without introducing a new integer-range restriction; manual MCP/LIVE restart required for runtime certification.
