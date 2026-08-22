# A21.4 — FINAL MCP RUNTIME CERTIFICATION AFTER ADAPTER VALIDATION FIX

## FILES_CHANGED=NONE
Krok certyfikacji runtime typu read-only. Nie zmodyfikowano żadnych plików produkcyjnych, dokumentacji ani testów.

---

## RUNTIME_PUBLIC_SIGNATURE
`def get_live_events(repo_path: str, after_revision: int | None = None, limit: int | None = 20) -> str:`

---

## INVALID_STRING_RESULT
`after_revision="1"` zwraca kontrolowaną odpowiedź błędu:
```json
{
  "status": "error",
  "error": "invalid_after_revision"
}
```
(TypeError został całkowicie wyeliminowany; adapter poprawnie waliduje typ wejściowy).

---

## INVALID_FLOAT_RESULT
`after_revision=1.5` zwraca kontrolowany błąd:
```json
{
  "status": "error",
  "error": "invalid_after_revision"
}
```

---

## INVALID_TRUE_RESULT
`after_revision=True` zwraca kontrolowany błąd:
```json
{
  "status": "error",
  "error": "invalid_after_revision"
}
```

---

## INVALID_FALSE_RESULT
`after_revision=False` zwraca kontrolowany błąd:
```json
{
  "status": "error",
  "error": "invalid_after_revision"
}
```

---

## NEGATIVE_INTEGER_RESULT
`after_revision=-1`:
Adapter pomyślnie przepuszcza ujemny kursor całkowity do silnika LIVE. Zapytanie zwraca `status="ok"` i prawidłowo oblicza ciągłość względem okna retencji:
```json
{
  "status": "ok",
  "revision": 1245,
  "latest_revision": 1245,
  "earliest_retained_revision": 1243,
  "continuity": "gap",
  "resync_required": true,
  "resync_reason": "event_retention_gap"
}
```

---

## ZERO_INTEGER_RESULT
`after_revision=0`:
Adapter pomyślnie przepuszcza kursor `0` do silnika LIVE. Zapytanie zwraca `status="ok"` oraz pola ciągłości wyliczone względem okna retencji:
```json
{
  "status": "ok",
  "revision": 1245,
  "latest_revision": 1245,
  "earliest_retained_revision": 1243,
  "continuity": "gap",
  "resync_required": true,
  "resync_reason": "event_retention_gap"
}
```

---

## CONTINUITY_FIELDS_PRESENT
**YES** (wszystkie 5 pól metadanych ciągłości: `latest_revision`, `earliest_retained_revision`, `continuity`, `resync_required`, `resync_reason` są obecne i spójne w odpowiedzi).

---

## CONTEXTOR_RUNTIME_SANITY
- `contextor/mcp/tools/get_live_events.py`: `module_id="249/1"`, `layer="adapter"`, `public_api.total=1`, `imports.total=1`, `consumers.total=2`.

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

A21 CLOSED — public get_live_events validation and LIVE continuity semantics are fully source- and runtime-certified.
