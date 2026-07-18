# -*- coding: utf-8 -*-

"""
repo_guardian/core/architecture_context.py

ARCHITECTURE CONTEXT ENGINE

Odpowiedzialność:
- lokalizacja modułu w indeksie
- zależności incoming/outgoing
- lokalny klaster zależności
- sygnały architektoniczne

Operuje wyłącznie na gotowym grafie.

Facts layer:
- brak scoringu
- brak refactoring advice
- brak własnych progów jakości
- brak klasyfikacji hotspotów

Źródła:
- ProjectGraph
- hotspot analysis
- cycle detection
"""


from pathlib import Path



# ==========================================================
# MODULE LOCATION
# ==========================================================


def find_module_id(
    file_path: str,
    modules: dict
) -> str | None:
    """
    Znajduje module_id na podstawie ścieżki.

    Obsługuje:
    - absolute path
    - relative path
    - fallback filename
    """

    target = Path(
        file_path
    ).resolve()


    target_name = target.name


    for module_id, module in modules.items():

        candidate = Path(
            module.path
        )


        try:

            if candidate.resolve() == target:

                return module_id

        except Exception:

            pass


        if candidate.name == target_name:

            return module_id


    return None



# ==========================================================
# DEPENDENCY LOOKUPS
# ==========================================================


def find_dependents(
    module_id: str,
    hard_edges: dict
) -> list[str]:

    result = []


    for source, targets in hard_edges.items():

        if module_id in targets:

            result.append(
                source
            )


    return sorted(
        result
    )



def find_soft_dependents(
    module_id: str,
    soft_edges: dict
) -> list[str]:

    result = []


    for source, targets in soft_edges.items():

        if module_id in targets:

            result.append(
                source
            )


    return sorted(
        result
    )



# ==========================================================
# LOCAL GRAPH CLUSTER
# ==========================================================


def find_cluster(
    module_id: str,
    hard_edges: dict
) -> list[str]:
    """
    Zwraca lokalny fragment grafu:

    - własne zależności
    - użytkownicy modułu
    """

    cluster = set()


    cluster.add(
        module_id
    )


    cluster.update(
        hard_edges.get(
            module_id,
            []
        )
    )


    for source, targets in hard_edges.items():

        if module_id in targets:

            cluster.add(
                source
            )


    return sorted(
        cluster
    )



# ==========================================================
# ARCHITECTURE SIGNALS
# ==========================================================


def architecture_signals(
    module_id,
    hard_edges,
    soft_edges,
    hotspots,
    cycles,
    node_count=None
):
    """
    Zwraca faktyczne sygnały architektoniczne.

    Ten moduł NIE:
    - liczy score
    - ustala progów
    - klasyfikuje modułów

    Klasyfikacja pochodzi z:
        hotspots.py

    """

    signals = []



    # ======================================================
    # DEPENDENCY FACTS
    # ======================================================


    incoming = find_dependents(
        module_id,
        hard_edges
    )


    outgoing = hard_edges.get(
        module_id,
        set()
    )



    if incoming:

        signals.append(
            "has_dependents"
        )


    if outgoing:

        signals.append(
            "has_dependencies"
        )



    # ======================================================
    # CYCLES
    # ======================================================


    cycle_nodes = {

        node

        for cycle in cycles or []

        for node in cycle

    }


    if module_id in cycle_nodes:

        signals.append(
            "cycle_member"
        )



    # ======================================================
    # SOFT DEPENDENCIES
    # ======================================================


    if soft_edges.get(
        module_id
    ):

        signals.append(
            "contains_soft_dependencies"
        )



    if module_id in find_soft_dependents(
        module_id,
        soft_edges
    ):

        signals.append(
            "has_soft_dependents"
        )



    # ======================================================
    # HOTSPOT FACTS
    # ======================================================


    for hotspot in hotspots or []:


        if hotspot.get(
            "module"
        ) != module_id:

            continue



        hotspot_type = hotspot.get(
            "type"
        )


        if hotspot_type in {

            "HOTSPOT",
            "OUTBOUND_HOTSPOT",
            "HUB",
            "CONFIG_HUB",

        }:

            signals.append(
                "hotspot"
            )


        if hotspot_type == "CONFIG_HUB":

            signals.append(
                "config_hub"
            )



    return sorted(
        set(signals)
    )
