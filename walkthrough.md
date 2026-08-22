# Issue 1 — closure audit

## Summary

Świeżo zrestartowany runtime publicznie udostępnia `search_source` i `get_source_range`, a dokumentacja MCP jednoznacznie rozdziela role: `search_artifacts` wyszukuje kanoniczne entities, `search_source` wykonuje canonical-scoped textual discovery, a `get_source_range` rozwija dokładnie wskazany zakres. Historyczny brak Contextora jako całości został zamknięty osobną capability, bez zmiany semantyki `search_artifacts`.

Na aktualnym repo `search_source` znalazł komplet realnych wystąpień auditowanych literalów, stringów i tekstu docstringu względem niezależnego `rg` oracle ograniczonego do plików Python. Agent może rozpocząć od samego tekstu, dostać logiczne evidence, zawężać przez `limit`, a następnie jawnie rozwinąć wybrany zakres. `grep` nie jest już wymagany w normalnym workflow refaktoru canonical Python source; pozostaje opcjonalnym zewnętrznym verifierem.

## Evidence

### Runtime and ownership

- Publiczny runtime expose'uje `search_source(repo_path, search_term, limit=20, case_sensitive=False, allow_large_output=False)` oraz `get_source_range(repo_path, file_path, start_line, end_line, allow_large_output=False)`.
- Centralne docs trzech tooli były dostępne przez runtime. `search_source` dokumentuje single-line literal substring, canonical Python scope, `read_source`, logical spans, `total_matches/truncated`, progressive line map i exact expansion.
- `search_artifacts("search_source")` -> `total_matches=3`, `truncated=false`: module `contextor.mcp.tools.search_source`, funkcja oraz binding w `contextor.mcp_server`. Entity control przechodzi.
- Contextor topology: `search_artifacts` zależy tylko od runtime/query helpers; `search_source` i `get_source_range` zależą od `contextor.core.source`, output guard, runtime/query helpers i wspólnego `source_helpers`. Consumers obu nowych tooli obejmują `mcp_server` i targeted tests. Brak tool-to-tool dependency.

### Static contract

- `search_artifacts.py` porównuje query z canonical module/artifact names (`functions/classes/methods/globals`); nie czyta source.
- `search_source.py` enumeruje wyłącznie `canonical_python_sources(root, engine.state)` i odczytuje każdy plik przez `contextor.core.source.read_source`.
- `canonical_python_sources` iteruje `state.modules`; brak `os.walk`, `rglob`, filesystem discovery i persistent text indexu. Ścieżki spoza repo oraz non-Python są odrzucane.
- Matching jest literalny, single-line, case-controlled; komentarze, docstringi, string/numeric literals i kod są zwykłym searchable source text.
- Resolver jest przejściowy per-file; nie mutuje canonical/LIVE state. Targeted regression dodatkowo potwierdza brak state mutation i wykluczenie pliku nieobecnego w canonical state.
- Zakresy >20 linii używają `line_map`; matched lines pozostają pełne, pozostałe previews mają maksymalnie 4 tokeny i 60 znaków. Metadata wskazuje dokładny `get_source_range`.

### Real-repo completeness

1. Literal `8765`:
   - `rg` Python oracle -> `contextor/mcp_server.py:416`, `tests/test_live_state_store.py:54`.
   - `search_source(limit=None)` -> dokładnie te dwa canonical pliki i `matched_lines=[416]`, `[54]`; oba jako właściwe statement spans.
   - `COMPLETENESS=COMPLETE`.
2. Docstring text `stdout MUST contain only JSON-RPC messages`:
   - `rg` Python oracle -> `contextor/mcp_server.py:10`.
   - `search_source(limit=None)` -> ten sam plik i linia, `match_kind=docstring`, span `1-111`, matched line 10 w całości.
   - `COMPLETENESS=COMPLETE`.
3. Unikalny runtime message `Source search output exceeds the recommended context size.`:
   - `rg` Python oracle -> `contextor/mcp/tools/search_source.py:109`.
   - `search_source(limit=None)` -> ten sam plik i linia, statement span `105-113`.
   - `COMPLETENESS=COMPLETE`.
- Negative query `__CONTEXTOR_ISSUE_1_NEGATIVE_8f34d__` -> `status=ok`, `total_matches=0`, `matches=[]`, `truncated=false`.
- `search_artifacts("109.9")` i `search_artifacts(docstring text)` nadal zwracają brak entity — zgodnie z kontraktem, nie jest to bug.

### Bounding, preview and expansion

- Multi-hit `SourceError`, `limit=1` -> `total_matches=36`, jeden result, `truncated=true`.
- Ten sam query z `limit=None` bez zgody -> `confirmation_required`, `requested_count=36`, `estimated_output_bytes=15683`, threshold `15360`.
- Jawny retry `allow_large_output=true` -> `status=ok`, wszystkie 36 logical matches, `truncated=false`.
- Docstring span `1-111` -> `content_mode=line_map`, pełna matched line 10, bounded previews wszystkich pozostałych linii, exact expand metadata.
- `get_source_range(contextor/mcp_server.py, 1, 20)` -> dokładnie linie 1-20 wraz z tekstem trafienia.
- Duże świadome rozwinięcie `graph_analytics.py:1-2295` -> `confirmation_required`, `estimated_output_bytes=65030`; module jest potwierdzonym canonical entity.

### Old workflow comparison

- A. Start od samego query text: **YES**.
- B. Wszystkie canonical Python locations: **YES**, kompletność potwierdzona dla literal/string oraz docstring.
- C. Logical evidence bez czytania całych plików: **YES**.
- D. Jawne rozwinięcie wybranego exact range: **YES**.
- E. Grep wymagany: **NO**; w audycie użyty wyłącznie jako niezależny oracle.

Naturalny excluded/non-canonical Python fixture nie był potrzebny ani tworzony w READ ONLY audit. Canonical scope control opiera się na runtime ownership, static enumeration z `state.modules` oraz przechodzącym targeted regression wykluczającym non-canonical plik.

## Tests

- `python -m pytest -q tests/test_search_source.py tests/test_mcp_split_s2c.py tests/test_mcp_documentation.py` -> `27 passed, 1 warning in 13.02s`.
- `python -m pytest -q tests/test_mcp_regressions.py::test_live_artifact_search_handles_list_based_symbol_state` -> `1 passed, 1 warning in 10.63s`.
- Full pytest nie został uruchomiony.
- Warning to istniejąca deprecacja FastMCP/Authlib, niezwiązana z Issue 1.

## Decision

`HISTORICAL_SEARCH_ARTIFACTS_CRITIQUE_STATUS=CLOSED_BY_SEPARATE_CAPABILITY`

`SEARCH_ARTIFACTS_ENTITY_ROLE=PASS`

`SOURCE_DISCOVERY=PASS`

`REAL_REPO_LITERAL_COMPLETENESS=PASS`

`REAL_REPO_COMMENT_DOCSTRING_COMPLETENESS=PASS`

`CANONICAL_SCOPE_INVARIANT=PASS`

`PROGRESSIVE_CONTEXT_CONTROL=PASS`

`EXACT_EXPANSION=PASS`

`GREP_REQUIRED_FOR_NORMAL_CANONICAL_PYTHON_TEXT_DISCOVERY=NO`

`OPEN_P0=NONE`

`OPEN_P1=NONE`

`OPEN_P2=NONE`

`ISSUE_1_FINAL_VERDICT=CLOSED`

Zdanie „musisz fallbackować na grep” nie jest już prawdziwe: `search_source` rozpoczyna workflow od nieznanego tekstu, znajduje komplet canonical Python locations i daje bounded logical evidence, a `get_source_range` zapewnia kontrolowane exact expansion.

## Diffs

Audyt był READ ONLY. Nie zmieniono kodu, dokumentacji produkcyjnej, testów ani canonical/LIVE state. `walkthrough.md` jest wymaganym automatycznym artefaktem raportowym i nie jest liczony jako modyfikacja repozytorium produkcyjnego.

`FILES_CHANGED=NONE`

`DIFFS=NONE`
