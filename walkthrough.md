# TOKEN EFFICIENCY — STEP A3.5.2: POST-RESTART RUNTIME CERTIFICATION OF DIRECTLY EXECUTABLE REPRESENTATION DECISION AND CONTINUATION DESCRIPTORS

## FILES_CHANGED=NONE

---

## TARGET_ARTIFACT

`contextor.core.reporting_engine.persistent_registry::PersistentIdentityRegistry`

---

## CURRENT_RUNTIME_TOTAL

`T = 46`

---

## COMPACT_NAMED_EXPAND_DESCRIPTOR

Wywołanie: `get_artifact_blast_radius(repo_path="C:\\Temp\\Contextor_Repo", artifact_name="contextor.core.reporting_engine.persistent_registry::PersistentIdentityRegistry", compact=True, representation="named", fields=["consumers"])`

```json
{
  "compact": false,
  "max_items": null,
  "representation": "named",
  "fields": [
    "consumers"
  ]
}
```

- **Weryfikacja:** Deskryptor `expand` zawiera representation `"named"` oraz jawną projekcję `"fields": ["consumers"]`.

---

## COMPACT_NAMED_DIRECT_EXPAND_RESULT

Wywołanie: `get_artifact_blast_radius(repo_path="C:\\Temp\\Contextor_Repo", artifact_name="contextor.core.reporting_engine.persistent_registry::PersistentIdentityRegistry", **response["consumers"]["expand"])`

- **Wynik:**
  - Top-level klucze: dokładnie `{"consumers"}` (projekcja zachowana).
  - `consumers.items`: 46 pełnych nazw modułów.
  - `truncated: false`, brak `expand`.

---

## COMPACT_INDEXED_EXPAND_DESCRIPTOR

Wywołanie: `get_artifact_blast_radius(repo_path="C:\\Temp\\Contextor_Repo", artifact_name="contextor.core.reporting_engine.persistent_registry::PersistentIdentityRegistry", compact=True, representation="indexed", fields=["consumers"])`

```json
{
  "compact": false,
  "max_items": null,
  "representation": "indexed",
  "fields": [
    "consumers"
  ]
}
```

- **Weryfikacja:** Deskryptor `expand` zawiera representation `"indexed"` oraz `"fields": ["consumers"]`.

---

## COMPACT_INDEXED_DIRECT_EXPAND_RESULT

Wywołanie: `get_artifact_blast_radius(repo_path="C:\\Temp\\Contextor_Repo", artifact_name="contextor.core.reporting_engine.persistent_registry::PersistentIdentityRegistry", **response["consumers"]["expand"])`

- **Wynik:**
  - Top-level klucze: dokładnie `{"consumers"}` (projekcja zachowana).
  - `consumers.items`: 46 identyfikatorów modułów (`"228/1"`, `"53/1"`, ...).
  - `representation: "indexed"`, `index_kind: "module"`, `resolve_via: "lookup_index_entries"`.
  - `truncated: false`, brak `expand`.

---

## COMPACT_AUTO_EXPAND_DESCRIPTOR

Wywołanie: `get_artifact_blast_radius(repo_path="C:\\Temp\\Contextor_Repo", artifact_name="contextor.core.reporting_engine.persistent_registry::PersistentIdentityRegistry", compact=True, representation="auto", fields=["consumers"])`

```json
{
  "compact": false,
  "max_items": null,
  "representation": "auto",
  "fields": [
    "consumers"
  ]
}
```

- **Weryfikacja:** Deskryptor `expand` zawiera representation `"auto"` oraz `"fields": ["consumers"]`.

---

## COMPACT_AUTO_DIRECT_EXPAND_RESULT

Wywołanie: `get_artifact_blast_radius(repo_path="C:\\Temp\\Contextor_Repo", artifact_name="contextor.core.reporting_engine.persistent_registry::PersistentIdentityRegistry", **response["consumers"]["expand"])`

- **Wynik:**
  - Top-level klucze: dokładnie `{"consumers"}` (projekcja zachowana).
  - `consumers.status: "representation_decision_required"`.
  - Opcje `options` zawierają `"fields": ["consumers"]` i nie zawierają `resolve_via`.

---

## DECISION_OPTIONS_CONSUMERS_ONLY

Opcje ponowienia wygenerowane dla `fields=["consumers"]`:

```json
{
  "named": {
    "representation": "named",
    "compact": false,
    "max_items": null,
    "fields": [
      "consumers"
    ]
  },
  "indexed": {
    "representation": "indexed",
    "compact": false,
    "max_items": null,
    "fields": [
      "consumers"
    ]
  },
  "bounded_named": {
    "representation": "named",
    "compact": false,
    "max_items": 10,
    "fields": [
      "consumers"
    ]
  }
}
```

- **Weryfikacja:**
  - Każda opcja zawiera `"fields": ["consumers"]`.
  - Żadna opcja nie zawiera `resolve_via`.
  - Wszystkie klucze należą do dozwolonych kwargs: `{"representation", "compact", "max_items", "fields"}`.

---

## DIRECT_NAMED_RETRY_RESULT

Wywołanie: `get_artifact_blast_radius(..., **options["named"])`

- **Wynik:**
  - Top-level klucze: dokładnie `{"consumers"}`.
  - 46 nazw modułów, `truncated: false`.

---

## DIRECT_INDEXED_RETRY_RESULT

Wywołanie: `get_artifact_blast_radius(..., **options["indexed"])`

- **Wynik:**
  - Top-level klucze: dokładnie `{"consumers"}`.
  - 46 identyfikatorów modułów, `truncated: false`.
  - Metadane kolekcji: `representation="indexed"`, `index_kind="module"`, `resolve_via="lookup_index_entries"`.

---

## DIRECT_BOUNDED_NAMED_RETRY_RESULT

Wywołanie: `get_artifact_blast_radius(..., **options["bounded_named"])`

- **Wynik:**
  - Top-level klucze: dokładnie `{"consumers"}`.
  - 10 nazw modułów, `total: 46`, `truncated: true`.
  - `expand: {"compact": false, "max_items": null, "representation": "named", "fields": ["consumers"]}`.

---

## RESPONSE_METADATA_VS_RETRY_ARGUMENTS

- `resolve_via="lookup_index_entries"` jest obecne wyłącznie jako metadana w zwróconym obiekcie kolekcji `consumers` w trybie indexed.
- `resolve_via` jest **całkowicie nieobecne** w deskryptorze `options.indexed`.
- Dzięki temu `**options["indexed"]` wykonuje się bezbłędnie bez wyjątku `unexpected keyword argument`.

---

## MULTI_FIELD_DECISION_RESULT

Wywołanie z `fields=["artifact", "consumers"]`:

- **Wynik decyzji:**
  - Top-level klucze: `{"artifact", "consumers"}`.
  - `options.named["fields"] == ["artifact", "consumers"]`
  - `options.indexed["fields"] == ["artifact", "consumers"]`
  - `options.bounded_named["fields"] == ["artifact", "consumers"]`

---

## MULTI_FIELD_DIRECT_RETRY_RESULT

Wywołanie: `get_artifact_blast_radius(..., **options["indexed"])` (dla multi-field descriptor)

- **Wynik:**
  - Top-level klucze: dokładnie `{"artifact", "consumers"}`.
  - `artifact`: `"contextor.core.reporting_engine.persistent_registry::PersistentIdentityRegistry"`.
  - `consumers`: pełna kolekcja indexed (46 identyfikatorów).

---

## BOUNDED_DECISION_RESULT

Wywołanie: `get_artifact_blast_radius(..., compact=False, max_items=30, representation="auto", fields=["consumers"])`

- **Wynik:**
  - `status: "representation_decision_required"`.
  - `decision_scope_count: 30` (`30 < 46`).
  - `expand`: `{"compact": false, "max_items": null, "representation": "auto", "fields": ["consumers"]}`.
  - `sizes`: `named_bytes=1435`, `indexed_bytes=675`, `bytes_saved=760`, `percent_saved=53.0`.

---

## BOUNDED_EXACT_SIZE_VALIDATION

Niezależne wyliczenie rozmiarów zserializowanych obiektów JSON dla rzeczywistych odpowiedzi bounded named i bounded indexed (obie z deskryptorem `expand` zawierającym `"fields": ["consumers"]`):

- `named_bytes` = 1435 B vs runtime 1435 B (**EXACT MATCH**)
- `indexed_bytes` = 675 B vs runtime 675 B (**EXACT MATCH**)
- `bytes_saved` = 760 B vs runtime 760 B (**EXACT MATCH**)
- `percent_saved` = 53.0% vs runtime 53.0% (**EXACT MATCH**)

---

## FIELDS_NONE_CONTROL

Wywołanie bez parametru `fields` (`fields=None`):

- **Wynik decyzji:**
  - `options.named`, `options.indexed`, `options.bounded_named` **nie zawierają klucza `fields`** (brak sztucznego `"fields": null`).
  - Wykonanie `**options["indexed"]` zwraca pełną odpowiedź blast radius (ze wszystkimi domyślnymi kluczami), działając w 100% zgodnie z oczekiwaniami.

---

## LIVE_SESSION_RESULT

Wywołanie Contextor MCP `get_live_events`:
- `status: "ok"`
- `revision: 1138`

---

## RUNTIME_CONTRACT_MATRIX

| Test Runtime | Kontrakt | Status |
|---|---|---|
| **CALL 1** | Compact named expand preserves fields & direct kwargs execution | **PASS** |
| **CALL 2** | Compact indexed expand preserves fields & direct kwargs execution | **PASS** |
| **CALL 3** | Compact auto expand preserves fields & direct kwargs execution | **PASS** |
| **CALL 4** | Decision options preserve consumers-only fields & direct kwargs execution for all 3 options | **PASS** |
| **CALL 4 Resolver** | `resolve_via` in response payload, omitted from retry kwargs | **PASS** |
| **CALL 5** | Multi-field decision preserves `["artifact", "consumers"]` & direct kwargs execution | **PASS** |
| **CALL 6** | Bounded auto decision with fields & exact candidate sizing (1435/675/760/53.0%) | **PASS** |
| **CALL 7** | Fields None control (no artificial `"fields": null` in options, full response) | **PASS** |
| **CALL 8** | Live session health check (`status="ok"`, revision 1138) | **PASS** |

---

## FINDINGS

- **OPEN_P0:** 0
- **OPEN_P1:** 0
- **OPEN_P2:** 0
- **OPEN_P3:** 0

---

## STEP_VERDICT

`PASS`

---

## NEXT_STEP_PROPOSAL

STEP A3.6 — close get_artifact_blast_radius consumers pilot and inspect next token-efficiency target.
