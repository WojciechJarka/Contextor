# TOKEN EFFICIENCY — STEP A17.1: MEASURE AND CLASSIFY describe_canonical_state

## FILES_CHANGED=NONE
Krok pomiarowy i klasyfikacyjny typu read-only. Nie zmodyfikowano żadnych plików produkcyjnych, dokumentacji ani testów.

---

## PUBLIC_SIGNATURE
`def describe_canonical_state(schema_version: str = "1.0", language_version: str = "1.0") -> str:`

---

## AUTHORITATIVE_IMPLEMENTATION
`C:\Temp\Contextor_Repo\contextor\mcp\tools\describe_canonical_state.py`

---

## AUTHORITATIVE_CORE_OWNER
`C:\Temp\Contextor_Repo\contextor\core\canonical_state_query\contract.py`

---

## SUPPORTED_VERSION_PAIRS
- `("1.0", "1.0")` — kontrakt bazowy (legacy)
- `("1.1", "1.1")` — kontrakt z progressive disclosure

---

## STATE_DEPENDENCE
`NO`
Wynik narzędzia jest w 100% statycznym opisem specyfikacji schematu i języka zapytań zadeklarowanym w stałych w kodzie. Narzędzie nie przyjmuje parametru `repo_path`, nie wykonuje żadnych operacji wejścia/wyjścia (I/O), analizy kodu ani odczytu rejestrów.

---

## DEFAULT_1_0_BYTES
**8,941 bajtów** UTF-8 (~8.73 KiB)

---

## EXPLICIT_1_0_BYTES
**8,941 bajtów** UTF-8 (~8.73 KiB)

---

## EXPLICIT_1_1_BYTES
**9,752 bajty** UTF-8 (~9.52 KiB)

---

## V1_1_VS_V1_0_DELTA
- Różnica bezwzględna: **+811 bajtów**
- Wzrost procentowy: **+9.07%** (wynika z dodania opisu `default_evidence_limit`, `supported_evidence_limits` oraz pól towarzyszących `imports_truncated` i `consumers_truncated`).

---

## CROSS_PAIR_ERROR_BYTES
**435 bajtów** UTF-8 (odpowiedź błędu `unsupported_version_pair`).

---

## UNKNOWN_PAIR_ERROR_BYTES
**435 bajtów** UTF-8 (odpowiedź błędu `unsupported_schema_version`).

---

## V1_1_SECTION_BREAKDOWN
Pomiary sekcji wykonane jako standalone serialization (rozmiar wyizolowanego JSON dla każdej sekcji):
- **Modules Root Schema**: 2,288 bajtów (8 pól, typy, operatory, filtry, computeds)
- **Artifacts Root Schema**: 3,715 bajtów (14 pól, typy, operatory, filtry, computeds)
- **Dependencies Root Schema**: 1,321 bajtów (6 pól, typy, operatory)
- **Language Contract**: 1,121 bajtów (filtry, operatory, limity, sortowanie)
- **Envelope / Version Metadata**: 85 bajtów (`schema_version`, `language_version`, `supported_pairs`)
- **Pełny łączny payload 1.1**: **9,752 bajty**

*Metoda pomiaru:* Rozmiary standalone mierzą wyizolowany ślad bajtowy każdego poddrzewa w formacie JSON z wcięciem 2 spacji; łączny dokument 1.1 (9,752 B) łączy te sekcje w jeden wspólny obiekt JSON.

---

## PAYLOAD_COST_DRIVERS
- **R1**: Dokładne definicje pól, typów i dopuszczalnych operatorów w schemacie.
- **R2**: Flagi strukturalne per pole (`type`, `filterable`, `selectable`, `nullable`, `computed`).
- **R3**: Tekstowe opisy semantyczne pól (`description`).
- **R5**: Metadane możliwości języka i reguł dowodowych (`limits`, `operators`).
- Największy udział w rozmiarze mają definicje schematów `artifacts` (3.72 KB) oraz `modules` (2.29 KB).

---

## EXISTING_DISCLOSURE_CONTROLS
- Tylko jeden root: `NO`
- Tylko schema: `NO`
- Tylko language: `NO`
- Tylko field metadata: `NO`
- Tylko version metadata: `NO`

Narzędzie zwraca pełny kontrakt dla żądanej pary wersji.

---

## USAGE_MODEL
- `describe_canonical_state` służy jako jednorazowe narzędzie typu discovery/introspekcja, wywoływane przez agenta przed konstruowaniem zapytań do `query_canonical_projection`.
- Narzędzie nie jest wywoływane w pętlach ani na poziomie poszczególnych encji.
- Kompletny kontrakt (9.52 KiB) mieści się w standardowym budżecie kontekstu jednorazowego wywołania.
- Dokumentacja MCP jasno kieruje do wywołania `describe_canonical_state(schema_version="1.1", language_version="1.1")` w celu odkrycia możliwości wersji 1.1.

---

## SECTION_SCOPING_SIMULATION
`N/A` (Pełny payload 1.1 wynosi 9,752 bajty, co jest poniżej progu 10 KiB / 10,240 B. Brak niekontrolowanego wzrostu i brak zbędnej redundancji w naturalnym użyciu).

---

## PROGRESSIVE_DISCLOSURE_CANDIDATE
`NO`
Narzędzie opisuje stały, statyczny kontrakt o łącznym rozmiarze poniżej 10 KiB. Rozbijanie statycznego opisu na drobne zapytania zwiększyłoby liczbę rund i łączny narzut tokenowy komunikacji LLM-MCP.

---

## REPRESENTATION_CANDIDATE
`NO`
Narzędzie opisuje specyfikację schematu/języka, dla której alternatywne skrócone reprezentacje nie mają zastosowania.

---

## MEASURED_OPTIMIZATION_OPPORTUNITY
Brak uzasadnionej przestrzeni optymalizacyjnej. Ładunek ~9.5 KB jest optymalny dla pełnego opisu schematu trzech domen oraz reguł języka zapytań.

---

## NON_TOKEN_CONTRACT_RISKS
`NONE`
Zasady walidacji par wersji (`SUPPORTED_PAIRS`), obsługa błędów, domyślna para `(1.0, 1.0)` oraz odkrywalność `(1.1, 1.1)` zostały w pełni przetestowane i certyfikowane w krokach A15.3–A15.4.

---

## FINAL_CLASSIFICATION
`A` (NO CHANGE)

---

## JUSTIFICATION
1. Narzędzie zwraca wyłącznie statyczny kontrakt specyfikacji (0 I/O, brak zależności od stanu projektu).
2. Pełny rozmiar odpowiedzi wynosi 8.94 KB (1.0) oraz 9.75 KB (1.1), co mieści się poniżej progu 10 KiB.
3. Wywołanie jest jednorazowym discovery; brak narastającego fanoutu lub redundancji danych.
4. Żadna refaktoryzacja tokenowa nie jest uzasadniona.

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

## NEXT_STEP_PROPOSAL
STEP A17 CLOSED — describe_canonical_state is sufficiently token-efficient; no implementation justified.
