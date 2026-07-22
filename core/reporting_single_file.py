# -*- coding: utf-8 -*-

"""
repo_guardian/core/reporting_single_file.py


SINGLE MODULE REPORT ORCHESTRATOR


Warstwa:

    REPORT ASSEMBLY


Odpowiedzialność:

- zebranie wyników analiz
- złożenie raportu modułu


Nie robi:

- AST analysis
- symbol discovery
- dependency analysis
- risk calculation


Źródła prawdy:

symbol_analysis
symbol_reference
export_analysis
api_consumers
architecture_context

"""


import ast
import json
import os


from pathlib import Path
from datetime import datetime



from repo_guardian.core.symbol_analysis import (
    extract_file_symbols,
    classify_imports,
    find_symbol_usage,
    build_symbol_index,
)



from repo_guardian.core.symbol_reference import (
    build_symbol_references,
    find_import_users,
)


from repo_guardian.core.export_analysis import (
    extract_exports,
    find_unused_public_api,
    summarize_exports,
)



from repo_guardian.core.api_consumers import (
    extract_api_consumers,
    summarize_api_consumers,
)



from repo_guardian.core.api_surface import (
    extract_api_surface,
    extract_api_metadata,
)



from repo_guardian.core.public_api import (
    extract_public_api,
)



from repo_guardian.core.import_analysis import (
    extract_import_usage,
)



from repo_guardian.core.semantic_analysis import (
    analyze_module_semantics,
)

from repo_guardian.core.risk_analysis import (
    analyze_effects,
)
from repo_guardian.core.activity import (
    classify_symbol_activity,
    summarize_activity,
    STATUS_UNUSED_PUBLIC,
)
from repo_guardian.core.artifact_consumption import (
    build_artifact_consumption,
)


from repo_guardian.core.cycles import (
    detect_cycles,
)



from repo_guardian.core.metrics import (
    compute_graph_metrics,
)



from repo_guardian.core.thresholds import (
    get_thresholds,
)



from repo_guardian.core.architecture_context import (
    find_module_id,
    find_dependents,
    find_soft_dependents,
    find_cluster,
    architecture_signals,
)

from repo_guardian.core.validator.collisions import (
    validate_name_collisions,
)

# ==========================================================
# IO
# ==========================================================


def save_single_file_report(
    report,
    path
):
    """
    Zapis raportu JSON.
    """


    directory = os.path.dirname(
        path
    )


    if directory:

        os.makedirs(
            directory,
            exist_ok=True
        )



    with open(
        path,
        "w",
        encoding="utf-8"
    ) as file:


        json.dump(
            report,
            file,
            indent=2,
            ensure_ascii=False
        )



# ==========================================================
# INTERNAL HELPERS
# ==========================================================


def _read_tree(
    file_path
):

    return ast.parse(

        Path(file_path)
        .read_text(
            encoding="utf-8"
        )

    )

# ==========================================================
# FACT COLLECTION
# ==========================================================


def _collect_symbol_context(
    file_path,
    modules,
    module_id,
    root_path
):
    """
    Wszystko związane z symbolami.

    Jedno źródło prawdy.
    """


    symbols = extract_file_symbols(
        file_path
    )


    all_symbols = (

            symbols.get(
                "classes",
                []
            )

            +

            symbols.get(
                "functions",
                []
            )

            +

            symbols.get(
                "methods",
                []

            )

            +

            symbols.get(
                "globals",
                []

            )

        )


    usage = find_symbol_usage(
        modules,
        module_id,
        all_symbols,
        root_path
    )


    ecosystem = build_symbol_index(
        modules,
        root_path
    )


    ecosystem = {

        symbol: users

        for symbol, users in ecosystem.items()

        if (

            symbol in all_symbols

            or

            symbol.split(".")[-1]
            in all_symbols

        )

    }



    references = build_symbol_references(
        modules,
        all_symbols,
        root_path
    )



    consumers = extract_api_consumers(
        all_symbols,
        references
    )



    return {


        "symbols":
            symbols,


        "all_symbols":
            all_symbols,


        "usage":
            usage,


        "ecosystem":
            ecosystem,


        "references":
            references,


        "consumers":
            consumers,


        "consumer_summary":
            summarize_api_consumers(
                consumers
            ),

    }



# ==========================================================
# IMPORT CONTEXT
# ==========================================================


def _collect_import_context(
    module,
    modules
):


    known_modules = (

        set(
            modules.keys()
        )

        |

        {

            key.replace(
                "core.",
                "repo_guardian.core."
            )

            for key in modules.keys()

            if key.startswith(
                "core."
            )

        }

    )



    imports = classify_imports(
        module,
        known_modules
    )


    return {

        "imports":
            imports

    }



# ==========================================================
# EXPORT CONTEXT
# ==========================================================


def _collect_export_context(
    tree,
    symbols,
    usage,
    local_calls=None,
    references=None
):


    exports = extract_exports(
        tree
    )


    unused_candidates = find_unused_public_api(
        symbols,
        usage,
        exports,
        local_calls,
        references=references
    )


    return {


        "exports":
            exports,


        "export_summary":
            summarize_exports(
                exports
            ),


        "unused_candidates":
            unused_candidates,

    }



# ==========================================================
# SEMANTIC CONTEXT
# ==========================================================


def _collect_semantic_context(
    tree
):


    semantic = analyze_module_semantics(
        tree
    )


    effects = analyze_effects(
        tree
    )


    imports = extract_import_usage(
        tree
    )


    return {


        "semantic_analysis":
        {

            **semantic,

            **effects,

            "import_usage":
                imports,

        }

    }
# ==========================================================
# ARCHITECTURE CONTEXT
# ==========================================================


def _collect_architecture_context(
    module_id,
    project_graph,
    global_report=None,
    modules=None,  # <-- Dodany argument modules
):
    hard_edges = project_graph.hard_edges
    soft_edges = project_graph.soft_edges

    cycles = detect_cycles(
        hard_edges
    )
    
    metrics = compute_graph_metrics(
        hard_edges
    )

    thresholds = get_thresholds(
        metrics["nodes"]
    )

    # Pobieramy kolizje nazw i filtrujemy te, które dotyczą bieżącego modułu (file_path / module_id)
    name_collisions = []
    if modules:
        all_collisions = validate_name_collisions(modules)
        for error in all_collisions:
            # Jeśli ścieżka modułu znajduje się w węzłach kolizji
            if any(module_id in node or node.endswith(module_id.replace(".", "/")) for node in error.nodes):
                name_collisions.append(error.message)

    hotspots = []


    if global_report:


        hotspots = (

            global_report

            .get(
                "llm_signals",
                {}
            )

            .get(
                "hotspots",
                []

            )

        )



    return {


        "hard_dependencies":

            sorted(
                hard_edges.get(
                    module_id,
                    []
                )
            ),



        "soft_dependencies":

            sorted(
                soft_edges.get(
                    module_id,
                    []
                )
            ),



        "imported_by":

            find_dependents(
                module_id,
                hard_edges
            ),



        "soft_imported_by":

            find_soft_dependents(
                module_id,
                soft_edges
            ),



        "cluster":

            find_cluster(
                module_id,
                hard_edges
            ),



        "signals": architecture_signals(
            module_id,
            hard_edges,
            soft_edges,
            hotspots,
            cycles,
            metrics["nodes"]
        ),
        "thresholds": thresholds,
        "cycles": [
            cycle for cycle in cycles
            if module_id in cycle
        ],
        "name_collisions": name_collisions,  # <-- Tutaj trafiają kolizje dla tego pliku
        "graph_metrics": metrics,
    }


# ==========================================================
# REPORT NORMALIZATION
# ==========================================================


def _build_llm_context():

    return {


        "purpose":

            "single module inspection",



        "recommended_analysis":

            [

                "review_dependencies",

                "inspect_symbol_usage",

                "evaluate_refactor_boundaries"

            ],



        "model":

            {


                "name":

                    "facts_first",


                "architecture":

                    "layered_context_extraction",

            }

    }


# ==========================================================
# PUBLIC REPORT GENERATOR
# ==========================================================


def generate_single_file_report(
    file_path: str,
    modules: dict,
    project_graph,
    global_report: dict | None = None,
    root_path: str | None = None,
):


    module_id = find_module_id(
        file_path,
        modules
    )


    if not module_id:

        raise ValueError(
            f"Module not found: {file_path}"
        )



    module = modules[
        module_id
    ]



    tree = _read_tree(
        file_path
    )



    # ------------------------------------------------------
    # FACT LAYERS
    # ------------------------------------------------------


    symbol_context = _collect_symbol_context(

        file_path,

        modules,

        module_id,

        root_path

    )



    import_context = _collect_import_context(

        module,

        modules

    )



    export_context = _collect_export_context(

        tree,

        symbol_context["all_symbols"],

        symbol_context["usage"],

        local_calls=symbol_context["symbols"].get("calls", []),

        references=symbol_context["references"]

    )



    semantic_context = _collect_semantic_context(

        tree

    )



    architecture = _collect_architecture_context(

        module_id,

        project_graph,

        global_report,

        modules=modules,  # <-- Przekazanie modules do funkcji

    )



    api_surface = {


        "surface":

            extract_api_surface(
                file_path
            ),


        "metadata":

            extract_api_metadata(
                file_path
            ),

    }

    public_api = extract_public_api(
        symbol_context["symbols"]
    )
    symbol_activity = classify_symbol_activity(
        symbol_context["all_symbols"],
        symbol_context["references"],
        public_symbols=public_api,
        local_calls=symbol_context["symbols"].get(
            "calls",
            []
        ),
        analyze_scope="all"
    )
    activity_summary = summarize_activity(
        symbol_activity
    )

    artifact_consumption = build_artifact_consumption(
        module_id,
        symbol_context["all_symbols"],
        symbol_context["consumers"],
        import_context["imports"],
        architecture["imported_by"],
        public_api,
        symbol_activity,
        activity_summary,
        modules,
        root_path,
        tree,
    )

    return {


        # --------------------------------------------------
        # IDENTITY
        # --------------------------------------------------


        "module":

            module_id,



        "file":

            str(
                file_path
            ),



        "generated_at":

            datetime.now().isoformat(),



        # --------------------------------------------------
        # SYMBOL DOMAIN
        # --------------------------------------------------


        "symbols":

            symbol_context["symbols"],



        "symbol_usage":

            symbol_context["usage"],



        "symbol_ecosystem":

            symbol_context["ecosystem"],



        "symbol_references":

            symbol_context["references"],



        "api_consumers":

            symbol_context["consumers"],



        "api_consumer_summary":

            symbol_context["consumer_summary"],



        # --------------------------------------------------
        # API DOMAIN
        # --------------------------------------------------


        "public_api":

            public_api,



        "exports":

            export_context["exports"],



        "export_summary":

            export_context["export_summary"],



        # --------------------------------------------------
        # SYMBOL ACTIVITY
        # Jedyna definicja "żywego symbolu" w raporcie.
        # Źródło prawdy dla unused_public_api.
        # --------------------------------------------------
        "symbol_activity":
            symbol_activity,
        "activity_summary":
            activity_summary,
        "unused_public_api":
            sorted([
                symbol
                for symbol, data in symbol_activity.items()
                if data["status"] == STATUS_UNUSED_PUBLIC
            ]),
        # Deprecated — zachowane dla kompatybilności wstecznej.
        # Źródło prawdy to teraz symbol_activity.
        "unused_candidates_old":
            export_context[
                "unused_candidates"
            ],


        # --------------------------------------------------
        # ARTIFACT CONSUMPTION
        # Warstwa agregacyjna "executive summary" dla LLM/człowieka.
        # NIE zastępuje symbol_references / api_consumers / imports /
        # architecture.imported_by / symbol_activity - tylko
        # składa je w jeden widok konsumpcji artefaktów modułu.
        # --------------------------------------------------
        "artifact_consumption":
            artifact_consumption,


        "api_surface":

            api_surface,



        # --------------------------------------------------
        # CODE SEMANTICS
        # --------------------------------------------------


        "semantic_analysis":

            semantic_context[
                "semantic_analysis"
            ],



        # --------------------------------------------------
        # IMPORTS
        # --------------------------------------------------


        "imports":

            import_context[
                "imports"
            ],



        "import_users":

            find_import_users(
                module_id,
                modules
            ),



        # --------------------------------------------------
        # ARCHITECTURE
        # --------------------------------------------------


        "architecture":

            architecture,



        # --------------------------------------------------
        # REPOSITORY CONTEXT
        # --------------------------------------------------


        "repository_context":

            {


                "module_count":

                    len(
                        modules
                    ),



                "graph_metrics":

                    architecture[
                        "graph_metrics"
                    ],



                "cycles":

                    architecture[
                        "cycles"
                    ]

            },



        # --------------------------------------------------
        # LLM
        # --------------------------------------------------


        "llm_context":

            _build_llm_context(),

    }
