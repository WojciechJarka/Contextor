# CONTEXTOR — SINGLE-FILE VS CANONICAL: API SURFACE DECISION REPORT

## 1. Executive Summary & Decision Matrix

```text
API_SURFACE_FACTS=[
  {
    FACT=functions (function names, visibility, line ranges, classmethod/staticmethod flags)
    OWNER=contextor.core.api_surface.visitor.APISurfaceVisitor.visit_FunctionDef
    OUTPUT=dict[str, dict] (keyed by function name)
    CANONICAL_EQUIVALENT=EXACT
    CANONICAL_OWNER=SymbolFacts.functions / artifacts[module]["symbols"]["functions"]
    SEMANTIC_PARITY=YES
    CONSUMERS=[contextor.core.reporting_layer.reporting_single_file, contextor.core.reporting_layer.reporting_llm]
    DECISION=KEEP_REPORT_LOCAL
  },
  {
    FACT=methods (method names qualified with class, visibility, line ranges)
    OWNER=contextor.core.api_surface.visitor.APISurfaceVisitor.visit_FunctionDef
    OUTPUT=dict[str, dict] (keyed by Class.method)
    CANONICAL_EQUIVALENT=EXACT
    CANONICAL_OWNER=SymbolFacts.methods / artifacts[module]["symbols"]["methods"]
    SEMANTIC_PARITY=YES
    CONSUMERS=[contextor.core.reporting_layer.reporting_single_file, contextor.core.reporting_layer.reporting_llm]
    DECISION=KEEP_REPORT_LOCAL
  },
  {
    FACT=classes (class names, visibility, line ranges, bases, decorators)
    OWNER=contextor.core.api_surface.visitor.APISurfaceVisitor.visit_ClassDef
    OUTPUT=dict[str, dict] (keyed by class name)
    CANONICAL_EQUIVALENT=PARTIAL (SymbolFacts stores class names; bases/decorators not stored as raw string lists in SymbolFacts)
    CANONICAL_OWNER=SymbolFacts.classes / artifacts[module]["symbols"]["classes"]
    SEMANTIC_PARITY=PARTIAL
    CONSUMERS=[contextor.core.reporting_layer.reporting_single_file, contextor.core.reporting_layer.reporting_llm]
    DECISION=KEEP_REPORT_LOCAL
  },
  {
    FACT=parameters & defaults (decomposed list of name, annotation, and default value strings)
    OWNER=contextor.core.api_surface.visitor._signature
    OUTPUT=list[dict[str, Optional[str]]]
    CANONICAL_EQUIVALENT=PARTIAL (Canonical SymbolFacts.signatures stores full typed signature string "def foo(x: int = 0) -> ..."; decomposed list-of-dicts is presentation-only)
    CANONICAL_OWNER=SymbolFacts.signatures
    SEMANTIC_PARITY=PARTIAL
    CONSUMERS=[contextor.core.reporting_layer.reporting_single_file, contextor.core.reporting_layer.reporting_llm]
    DECISION=KEEP_REPORT_LOCAL
  },
  {
    FACT=return_annotation
    OWNER=contextor.core.api_surface.visitor._annotation
    OUTPUT=Optional[str]
    CANONICAL_EQUIVALENT=PARTIAL (Included within canonical SymbolFacts.signatures string)
    CANONICAL_OWNER=SymbolFacts.signatures
    SEMANTIC_PARITY=YES
    CONSUMERS=[contextor.core.reporting_layer.reporting_single_file, contextor.core.reporting_layer.reporting_llm]
    DECISION=KEEP_REPORT_LOCAL
  },
  {
    FACT=docstrings (per-symbol docstrings for classes, functions, methods)
    OWNER=ast.get_docstring(node) in APISurfaceVisitor
    OUTPUT=Optional[str]
    CANONICAL_EQUIVALENT=NONE (Canonical state intentionally stores only module-level docstring in module_intent to minimize snapshot footprint)
    CANONICAL_OWNER=NONE
    SEMANTIC_PARITY=NO
    CONSUMERS=[contextor.core.reporting_layer.reporting_single_file, contextor.core.reporting_layer.reporting_llm]
    DECISION=KEEP_REPORT_LOCAL
  },
  {
    FACT=decorators (unparsed decorator string list)
    OWNER=contextor.core.api_surface.visitor.APISurfaceVisitor._decorator_names
    OUTPUT=list[str]
    CANONICAL_EQUIVALENT=NONE (Raw decorator lists are not stored in SymbolFacts)
    CANONICAL_OWNER=NONE
    SEMANTIC_PARITY=NO
    CONSUMERS=[contextor.core.reporting_layer.reporting_single_file, contextor.core.reporting_layer.reporting_llm]
    DECISION=KEEP_REPORT_LOCAL
  },
  {
    FACT=api_metadata (aggregate counts: total_symbols, functions, methods, classes, public/private counts)
    OWNER=contextor.core.api_surface.metadata.extract_api_metadata
    OUTPUT=dict[str, int]
    CANONICAL_EQUIVALENT=NONE (Computed directly from extract_api_surface output dictionary)
    CANONICAL_OWNER=NONE
    SEMANTIC_PARITY=NO
    CONSUMERS=[contextor.core.single_file.builders.layer0_builders.ApiSurfaceBuilder]
    DECISION=KEEP_REPORT_LOCAL
  }
]

SOURCE_READS=0 (reuses in-memory ContextPayload.module.ast_tree / ContextPayload.tree)
AST_PARSES=0 (reuses existing in-memory AST tree)
EXTRA_TREE_WALKS=1 (single in-memory traversal by APISurfaceVisitor)
CROSS_REPO_SCAN=NO

CANONICAL_OVERLAP=PARTIAL
REAL_CANONICAL_CONSUMERS=NO (neither graph, debt, incremental reconciliation, nor blast radius consume decomposed api_surface dictionaries)
API_SURFACE_QUERY_TIME_DUPLICATION=PARTIAL (symbol names and line numbers overlap with SymbolFacts, but decomposed parameter dictionaries, docstrings, and decorator lists are presentation-only)

API_SURFACE_DECISION=NO_CHANGE
RATIONALE=ApiSurfaceBuilder pełni funkcję prezentacyjną w raportach single-file (JSON i Markdown dla LLM). Wyciąga z już sparsowanego w pamięci drzewa AST (0 disk reads, 0 parse, ~0.5ms) szczegółowe struktury słownikowe parametrów, docstringi symboli i listy dekoratorów. Stan kanoniczny (SymbolFacts / RepositoryAnalysisState) celowo przechowuje zwięzłe fakty semantyczne (nazwy, linie, pełne sygnatury w stringu), rezygnując z przechowywania rozbitych struktur AST i docstringów per-symbol, by uniknąć wielomegabitowego narzutu na snapshoty całego repozytorium. Ponieważ silniki kanoniczne (graf, dług, inkrementacja) nie konsumują tych struktur, obecny podział (kanoniczne sygnatury vs lokalne słowniki prezentacyjne) jest optymalny architektonicznie.

IF_MIGRATE_BUILDER=NONE
IF_MIGRATE_CANONICAL_OWNER=NONE
IF_MIGRATE_FIELDS=[]
IF_KEEP_LOCAL_FIELDS=[functions, methods, classes, parameters, defaults, returns, docstrings, decorators, bases, api_metadata]
IF_REMOVE_LEGACY_ANALYSIS=NONE

CODE_CHANGES=NONE
VERDICT=DECIDED
```

---

## 2. Architectural Analysis & Findings

1. **Presentation Details vs Canonical Storage**:
   - `ApiSurfaceBuilder` produces detailed nested dictionaries containing parameter breakdowns `[{"name": "x", "annotation": "int", "default": "'foo'"}]`, docstring snippets, and decorator lists.
   - Canonical `SymbolFacts` intentionally stores only compact facts: symbol names (`classes`, `functions`, `methods`, `globals`) and unparsed signature strings (`"def foo(x: int = 'foo') -> bool"`).
   - Storing full decomposed AST structures for thousands of symbols across the entire repository in `RepositoryAnalysisState` would bloat memory and serialized snapshot size with no functional gain for graph or blast-radius algorithms.

2. **Performance & IO Footprint**:
   - Single-file analysis reuses the already-parsed `payload.module.ast_tree` (or `payload.tree`).
   - `APISurfaceVisitor` executes a single fast in-memory pass taking `< 1ms` per module.
   - Zero disk reads, zero file system scans, and zero cross-module dependency queries occur.

3. **Downstream Consumption**:
   - The output of `ApiSurfaceBuilder` is consumed strictly by `reporting_single_file.py` and `reporting_llm.py` to generate the file-level diagnostic JSON and Markdown context tables.
   - Core analysis engines (`IncrementalAnalysisEngine`, `DependencyGraph`, `CycleDetector`, `DebtScorer`) rely exclusively on canonical `SymbolFacts` and `ModuleUsageFacts`.
