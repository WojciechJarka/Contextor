# TOKEN EFFICIENCY — STEP A3.1.1: EXISTING INDEX LOOKUP SURFACE

## FILES_CHANGED=NONE

---

## READ_REGISTRIES_IMPLEMENTATION

**Plik:** `C:\Temp\Contextor_Repo\contextor\mcp\query_helpers.py` (linie 19–33)

```python
def read_registries(root: Path) -> tuple[dict, dict, dict, dict]:
    from contextor.core.reporting_engine.persistent_registry import (
        PersistentIdentityRegistry,
    )

    registry = PersistentIdentityRegistry(str(root))
    with registry.transaction():
        mod_reg = registry._state.get("module_registry", {})
        art_reg = registry._state.get("artifact_registry", {})
    return (
        mod_reg.get("path_to_id", {}),
        mod_reg.get("id_to_path", {}),
        art_reg.get("path_to_id", {}),
        art_reg.get("id_to_path", {}),
    )
```

---

## LOOKUP_INDEX_ENTRIES_IMPLEMENTATION

**Plik:** `C:\Temp\Contextor_Repo\contextor\mcp\tools\lookup_index_entries.py` (linie 7–30)

```python
def lookup_index_entries(repo_path: str, ids: list[str]) -> str:
    root = Path(repo_path).expanduser().resolve()
    try:
        catalog = catalog_from_registry(str(root))
        result = {}
        for id_ in ids:
            normalized_id = str(id_)
            if normalized_id.upper().startswith("A"):
                normalized_id = normalized_id.upper()
                active = catalog.artifacts
                recovery = catalog.recovered_artifacts or {}
            else:
                active = catalog.modules
                recovery = catalog.recovered_modules or {}
            if normalized_id in active:
                entry = {"name": active[normalized_id], "status": "active"}
            elif normalized_id in recovery:
                entry = {"name": recovery[normalized_id], "status": "recovery"}
            else:
                entry = {"name": None, "status": "missing"}
            result[str(id_)] = entry
        return json.dumps(result, indent=2)
    except Exception as e:
        return f"Error resolving index entries: {e}"
```

---

## LOOKUP_ARTIFACT_BY_SYMBOL_IMPLEMENTATION

**Plik:** `C:\Temp\Contextor_Repo\contextor\mcp\tools\lookup_artifact_by_symbol.py` (linie 9–111)

```python
def lookup_artifact_by_symbol(
    repo_path: str,
    symbol_name: str,
    limit: int | None = 20,
    evidence_limit: int | None = 20,
    compact: bool = True,
    fields: list[str] | None = None,
) -> str:
    root = Path(repo_path).expanduser().resolve()
    try:
        _, _, art_path_to_id, _ = query_helpers.read_registries(root)
        engine = mcp_runtime.get_or_init_engine(root)
        if not engine or getattr(engine.state, "resync_required", False):
            return "Error: No usable canonical LIVE state. Run analyze_project first."

        state = engine.state
        term = symbol_name.casefold()
        candidates = []
        for module_name, module_data in sorted((state.artifacts or {}).items()):
            unavailable = query_helpers.module_truth_unavailable(state, module_name)
            for symbol, kind in query_helpers.canonical_symbol_catalog(module_data).items():
                if term not in symbol.casefold():
                    continue
                if unavailable:
                    return json.dumps(unavailable, indent=2)
                full_name = f"{module_name}::{symbol}"
                artifact_id = art_path_to_id.get(full_name)
                key = artifact_id or full_name
                candidates.append(
                    (symbol.casefold() != term, symbol.casefold(), full_name, key, kind)
                )

        candidates.sort()
        if candidates and not candidates[0][0]:
            candidates = [item for item in candidates if not item[0]]
        if len(candidates) > 1 and not candidates[0][0]:
            return json.dumps(
                {
                    "error": "Ambiguous canonical symbol identity.",
                    "query": symbol_name,
                    "candidates": [item[2] for item in candidates],
                    "data_source": "live_canonical_state",
                },
                indent=2,
            )
        candidates, total_matches, matches_truncated = query_helpers.bounded_items(
            candidates, limit
        )

        if not candidates:
            return f"No current artifacts found matching '{symbol_name}'."

        results: dict = {}
        for _, _, full_name, key, kind in candidates:
            module_name, symbol = full_name.split("::", 1)
            entry = {
                "symbol": symbol,
                "full_name": full_name,
                "kind": kind,
                "definer_module": module_name,
            }
            if artifact_consumption_is_fresh(state):
                resolved_consumers = query_helpers.canonical_symbol_consumers(
                    state, module_name, symbol
                )
                consumer_items, consumer_total, consumer_truncated = query_helpers.bounded_items(
                    resolved_consumers, evidence_limit
                )
                entry["consumers"] = {
                    "total": consumer_total,
                    "truncated": consumer_truncated,
                }
                if not compact:
                    entry["consumers"]["items"] = consumer_items
            else:
                entry["consumers"] = {
                    "available": False,
                    "state": getattr(state, "artifact_consumption_state", "deferred"),
                    "reason": "Canonical artifact consumption is unavailable or stale.",
                }
            results[key] = entry

        result = {
                "query": symbol_name,
                "match_count": len(results),
                "total_matches": total_matches,
                "truncated": matches_truncated,
                "data_source": "live_canonical_state",
                "artifacts": results,
            }
        if fields is not None:
            allowed_fields = set(result)
            unknown_fields = sorted(set(fields) - allowed_fields)
            if unknown_fields:
                return json.dumps({
                    "error": "Unsupported fields for lookup_artifact_by_symbol",
                    "unknown_fields": unknown_fields,
                    "allowed_fields": sorted(allowed_fields),
                }, indent=2)
            result = {field: result[field] for field in fields}
        return json.dumps(result, indent=2)
    except Exception as e:
        return f"Error searching artifacts by symbol: {e}"
```

---

## ID_FORMATS

- **Module IDs:** Ciąg znaków w formacie `<liczba_całkowita>/<generacja_lub_wersja>` bez prefiksu `A` (np. `"259/1"`, `"1/1"`).
- **Artifact IDs:** Ciąg znaków z prefiksem `A` (case-insensitive przy dopasowywaniu, normalizowany do wielkich liter) w formacie `A<liczba_całkowita>/<generacja_lub_wersja>` (np. `"A2225/1"`, `"A1/1"`).

---

## NAME_ID_MAPS

Funkcja `read_registries(root)` zwraca krotkę 4 map:
1. `mod_path_to_id`: `dict[str, str]` (`module_name -> module_id`, np. `"contextor.mcp.runtime" -> "259/1"`).
2. `mod_id_to_path`: `dict[str, str]` (`module_id -> module_name`, np. `"259/1" -> "contextor.mcp.runtime"`).
3. `art_path_to_id`: `dict[str, str]` (`artifact_name -> artifact_id`, np. `"contextor.mcp.runtime::get_or_init_engine" -> "A2225/1"`).
4. `art_id_to_path`: `dict[str, str]` (`artifact_id -> artifact_name`, np. `"A2225/1" -> "contextor.mcp.runtime::get_or_init_engine"`).

---

## BATCH_RESOLUTION_CAPABILITY

- **Pełne wsparcie wsadowe (batch):** Narzędzie `lookup_index_entries(repo_path, ids)` przyjmuje listę `ids: list[str]`.
- Umożliwia rozwiązanie dowolnej liczby module IDs i artifact IDs jednocześnie w jednym wywołaniu MCP.
- Kolejność wejściowych ID jest zachowywana w wynikowym słowniku `result[str(id_)]`.

---

## MISSING_ID_SEMANTICS

- Nieznane lub brakujące ID nie powodują rzucenia wyjątku.
- Dla każdego nieodnalezionego identyfikatora zwracany jest wpis:
  ```json
  "<unknown_id>": {
    "name": null,
    "status": "missing"
  }
  ```

---

## RECOVERY_VISIBILITY

- Narzędzie sprawdza słowniki odzyskanych wpisów `catalog.recovered_artifacts` oraz `catalog.recovered_modules`.
- W przypadku znalezienia wpisu w recovery zwraca:
  ```json
  "<id>": {
    "name": "<recovered_name>",
    "status": "recovery"
  }
  ```

---

## REPOSITORY_GENERATION_SAFETY_VISIBLE_HERE

- **Brak jawnych metadanych generacji na poziomie lookup tools:**
  - Narzędzie `lookup_index_entries` opiera się na `catalog_from_registry(str(root))`, ale w zwracanym obiekcie JSON nie ujawnia `generation_id`, `repo_root_fingerprint` ani metadanych izolacji repozytorium.
  - Z samego kodu tych trzech symboli nie można jednoznacznie wywnioskować cyklu życia generacji (`/1`, `/2`), trwałości na dysku ani warunków unieważniania indeksów.

---

## PUBLIC_RESOLVER_SUITABILITY

- `lookup_index_entries` stanowi gotowy, publiczny punkt rozstrzygania indeksów (`resolve_via`) dla przyszłych skompresowanych kolekcji zawierających `module_id` lub `artifact_id`.
- `lookup_artifact_by_symbol` jest narzędziem wyszukiwania tekstowego po symbolach i nie jest potrzebny jako dekoder wire-representation.

---

## NEEDS_DEEPER_REGISTRY_AUDIT=YES

---

## WHY

1. **Niewidoczne semantyki generacji i odzyskiwania:** Zbadane 3 symbole są konsumentami struktur `PersistentIdentityRegistry` i `IndexCatalog`, ale nie definiują zasad przydzielania ID, przyrostu generacji (`/1`), zapisu w katalogu `.contextor/` ani mechanizmu `recovery`.
2. **Bezpieczeństwo negocjacji reprezentacji:** Przed wdrożeniem reprezentacji indeksowanej (`indexed`) należy upewnić się, czy ID są niezmienne w czasie życia sesji/procesu, jak reagują na modyfikacje plików (`update_file`) oraz czy nie ma ryzyka kolizji generacji.

---

## STEP_VERDICT

`PASS`

---

## NEXT_STEP_PROPOSAL

STEP A3.1.2 — inspect authoritative PersistentIdentityRegistry and recovery semantics.
