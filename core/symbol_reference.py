#~~~~~~[START PLIKU: symbol_reference.py ]~~~~~~#
# -*- coding: utf-8 -*-

"""
repo_guardian/core/symbol_reference.py


SYMBOL REFERENCE ENGINE


Warstwa:

    FACT EXTRACTION


Odpowiedzialność:

- wykrywanie użycia symboli
- wykrywanie wywołań metod/funkcji
- wykrywanie dziedziczenia
- wykrywanie importów symboli
- budowanie referencji symbol -> konsumenci


Nie robi:

- scoringu
- ryzyka
- architektury
- dead code
- raportowania


Kontrakt:


{
    "Symbol":
    {
        "called_by": [],
        "imported_from": [],
        "inherited_by": []
    }
}

"""


from pathlib import Path
import ast



# ==========================================================
# NAME RESOLUTION
# ==========================================================


def _attribute_name(
    node
):
    """
    Zamienia AST Name/Attribute
    na pełną nazwę.


    Example:

        client.run()

    becomes:

        client.run
    """


    if isinstance(
        node,
        ast.Name
    ):

        return node.id



    if isinstance(
        node,
        ast.Attribute
    ):

        parent = _attribute_name(
            node.value
        )


        if parent:

            return (
                f"{parent}.{node.attr}"
            )


        return node.attr



    return None




def _resolve_alias(
    name,
    aliases
):
    """
    Rozwiązuje lokalny alias importu.
    """


    if not name:

        return None


    return aliases.get(
        name,
        name
    )




def _match_symbol(
    value,
    symbols
):
    """
    Dopasowanie symbolu.

    Fallback po nazwie końcowej jest
    akceptowany tylko gdy istnieje
    dokładnie jeden kandydat.
    """

    if not value:
        return None


    if value in symbols:
        return value


    short = value.split(".")[-1]


    candidates = [
        symbol
        for symbol in symbols
        if symbol.split(".")[-1] == short
    ]


    if len(candidates) == 1:
        return candidates[0]


    return None



# ==========================================================
# VISITOR
# ==========================================================


class SymbolReferenceVisitor(
    ast.NodeVisitor
):
    

    def __init__(
        self,
        target_symbols
    ):

        self.target_symbols = set(
            target_symbols
        )


        self.called = set()

        # Dopasowania trafione WYŁĄCZNIE przez fallback po
        # krótkiej nazwie (_match_symbol), bez potwierdzenia
        # instancją ani dokładnym dopasowaniem. To są zgadywanki
        # - "coś.add(...)" może być set.add(), nie ModuleSymbols.add().
        # Nigdy nie mieszamy ich z self.called.
        self.called_ambiguous = set()

        self.event_bound = set()

        self.inherited = []


        self.aliases = {}

        self.instances = {}

    def _detect_positional_callbacks(
        self,
        node
    ):
        """
        Wykrywa callbacki przekazywane pozycyjnie.
        Obsługiwane wzorce:
            widget.bind(event, handler)      <- tkinter
            signal.subscribe(event, handler)
            emitter.on(handler)
        Nie obsługuje (poza zakresem):
            widget.bind(event, lambda e: handler())
        Uwaga:
            "connect" celowo pominięte —
            db.connect() ma inną semantykę.
        """
        func_name = _attribute_name(
            node.func
        )
        if not func_name:
            return
        method = func_name.split(".")[-1]
        #
        # Callbacki na pozycji args[1]
        # (drugi argument pozycyjny)
        #
        EVENT_CALLBACK_METHODS = {
            "bind",
            "subscribe",
        }
        #
        # Callbacki na pozycji args[0]
        # (pierwszy argument pozycyjny)
        #
        SINGLE_ARG_CALLBACK_METHODS = {
            "on",
        }
        if method in EVENT_CALLBACK_METHODS:
            if len(node.args) >= 2:
                name = _attribute_name(
                    node.args[1]
                )
                resolved = _resolve_alias(
                    name,
                    self.aliases
                )
                match = _match_symbol(
                    resolved,
                    self.target_symbols
                )
                if match:
                    self.event_bound.add(
                        match
                    )
        elif method in SINGLE_ARG_CALLBACK_METHODS:
            if len(node.args) >= 1:
                name = _attribute_name(
                    node.args[0]
                )
                resolved = _resolve_alias(
                    name,
                    self.aliases
                )
                match = _match_symbol(
                    resolved,
                    self.target_symbols
                )
                if match:
                    self.event_bound.add(
                        match
                    )
    def _detect_callback_arguments(
        self,
        node
    ):
        callback_keys = {
            "command",
            "callback",
            "handler",
            "func",
            "on_click",
            "on_change",
            "on_submit"
        }


        for keyword in node.keywords:

            if keyword.arg not in callback_keys:
                continue


            value = keyword.value


            name = _attribute_name(
                value
            )


            resolved = _resolve_alias(
                name,
                self.aliases
            )


            match = _match_symbol(
                resolved,
                self.target_symbols
            )


            if match:

                self.event_bound.add(
                    match
                )

    # ------------------------------------------------------
    # IMPORTS
    # ------------------------------------------------------


    def visit_ImportFrom(
        self,
        node
    ):


        for item in node.names:


            local_name = (
                item.asname
                or
                item.name
            )


            imported_name = (

                f"{node.module}.{item.name}"

                if node.module

                else item.name

            )


            self.aliases[
                local_name
            ] = imported_name



        self.generic_visit(
            node
        )



    def visit_Import(
        self,
        node
    ):


        for item in node.names:


            local_name = (

                item.asname

                or

                item.name.split(
                    "."
                )[-1]

            )


            self.aliases[
                local_name
            ] = item.name



        self.generic_visit(
            node
        )



    # ------------------------------------------------------
    # INSTANCE TRACKING
    # ------------------------------------------------------


    def visit_Assign(
        self,
        node
    ):


        if isinstance(
            node.value,
            ast.Call
        ):


            constructor = _attribute_name(
                node.value.func
            )


            constructor = _resolve_alias(
                constructor,
                self.aliases
            )


            if constructor:


                for target in node.targets:


                    if isinstance(
                        target,
                        ast.Name
                    ):


                        self.instances[
                            target.id
                        ] = constructor



        self.generic_visit(
            node
        )
    # ------------------------------------------------------
    # CALL DETECTION
    # ------------------------------------------------------


    def visit_Call(
        self,
        node
    ):
        self._detect_callback_arguments(
            node
        )
        self._detect_positional_callbacks(
            node
        )
        called_name = _attribute_name(
            node.func
        )


        resolved = _resolve_alias(
            called_name,
            self.aliases
        )


        # 1) Dopasowanie dokładne (pełna kwalifikowana nazwa
        #    zgadza się 1:1 z symbolem docelowym) - najbardziej
        #    wiarygodne, priorytet najwyższy.
        if resolved in self.target_symbols:

            self.called.add(
                resolved
            )

            self.generic_visit(
                node
            )

            return


        # 2) Rozwiązanie przez instancję (var = Class(); var.method())
        #    - potwierdzone konstruktorem, więc dużo bardziej
        #    wiarygodne niż zgadywanie po samej końcówce nazwy.
        #    MUSI iść przed fallbackiem po krótkiej nazwie, bo
        #    inaczej fallback (patrz niżej) prawie zawsze "wygra"
        #    jako pierwszy trafiony kandydat i zamaskuje brak
        #    faktycznego dopasowania typu.
        if self._resolve_instance_method(
            resolved
        ):

            self.generic_visit(
                node
            )

            return


        # 3) Fallback po krótkiej nazwie - tylko gdy nic powyżej
        #    nie trafiło. To zgadywanka (np. "x.add(...)" może
        #    być set.add(), nie metodą śledzonej klasy), więc
        #    ląduje w osobnej, oznaczonej jako niepewna puli,
        #    NIGDY w self.called.
        match = _match_symbol(
            resolved,
            self.target_symbols
        )


        if match:

            self.called_ambiguous.add(
                match
            )


        self.generic_visit(
            node
        )



    def _resolve_instance_method(
        self,
        resolved
    ):
        """
        Rozwiązuje:

            instance.method()

        na podstawie:

            instance = Class()

        Zwraca True i dopisuje do self.called tylko wtedy,
        gdy udało się potwierdzić klasę instancji. W przeciwnym
        razie zwraca False, żeby wywołujący mógł spróbować
        fallbacku po krótkiej nazwie.
        """


        if not resolved:

            return False



        parts = resolved.split(
            "."
        )


        if len(parts) != 2:

            return False



        instance_name, method = parts



        constructor = self.instances.get(
            instance_name
        )


        if not constructor:

            return False



        candidate = (
            f"{constructor}.{method}"
        )


        if candidate in self.target_symbols:

            self.called.add(
                candidate
            )

            return True


        return False



    # ------------------------------------------------------
    # INHERITANCE
    # ------------------------------------------------------


    def visit_ClassDef(
        self,
        node
    ):


        for base in node.bases:


            base_name = _attribute_name(
                base
            )


            resolved = _resolve_alias(
                base_name,
                self.aliases
            )


            match = _match_symbol(
                resolved,
                self.target_symbols
            )


            if match:

                self.inherited.append(
                    (
                        node.name,
                        match
                    )
                )



        self.generic_visit(
            node
        )



# ==========================================================
# REFERENCE BUILDING
# ==========================================================


def _empty_reference():

    return {

        "called_by": [],

        # Moduły, w których znaleziono wywołanie pasujące
        # TYLKO przez zgadywanie po krótkiej nazwie (np.
        # x.add(...) bez potwierdzenia, że x to instancja
        # śledzonej klasy). Nie liczy się do konsumentów -
        # to sygnał "może", nie "na pewno".
        "called_by_ambiguous": [],

        "event_bound_by": [],

        "imported_from": [],

        "inherited_by": [],

    }




def _load_tree(
    root_path,
    module
):


    try:

        path = (
            Path(root_path)
            /
            module.path
        )


        return ast.parse(
            path.read_text(
                encoding="utf-8"
            )
        )


    except Exception:

        return None



def build_symbol_references(
    modules,
    target_symbols,
    root_path
):
    """
    Buduje referencje symboli.


    Facts only.
    """


    target_symbols = set(
        target_symbols
    )


    references = {

        symbol:
            _empty_reference()

        for symbol in target_symbols

    }



    for module_id, module in modules.items():


        tree = _load_tree(
            root_path,
            module
        )


        if tree is None:

            continue



        visitor = SymbolReferenceVisitor(
            target_symbols
        )


        visitor.visit(
            tree
        )



        # --------------------------------------------------
        # CALLS
        # --------------------------------------------------


        for symbol in visitor.called:


            if symbol in references:

                references[symbol][
                    "called_by"
                ].append(
                    module_id
                )

        # --------------------------------------------------
        # CALLS (AMBIGUOUS - short-name fallback only)
        # --------------------------------------------------

        for symbol in visitor.called_ambiguous:

            if symbol in references:

                references[symbol][
                    "called_by_ambiguous"
                ].append(
                    module_id
                )

        # --------------------------------------------------
        # EVENT CALLBACKS
        # --------------------------------------------------

        for symbol in visitor.event_bound:

            if symbol in references:

                references[symbol][
                    "event_bound_by"
                ].append(
                    module_id
                )


        # --------------------------------------------------
        # INHERITANCE
        # --------------------------------------------------


        for child in visitor.inherited:


            for child_name, symbol in visitor.inherited:

                if symbol in references:

                    references[symbol][
                        "inherited_by"
                    ].append(
                        module_id
                    )



        # --------------------------------------------------
        # IMPORTS
        # --------------------------------------------------


        for imp in module.imports:

            for imported_name in imp.names:

                for symbol in target_symbols:

                    if _import_matches_symbol(
                        imported_name,
                        symbol
                    ):

                        references[symbol][
                            "imported_from"
                        ].append(
                            module_id
                        )


    return _normalize_references(
        references
    )
# ==========================================================
# IMPORT MATCHING
# ==========================================================


def _import_matches_symbol(
    imported,
    symbol
):
    """
    Sprawdza czy import wskazuje na symbol.
    """


    if not imported:

        return False



    if imported == symbol:

        return True



    if imported.endswith(
        "." + symbol
    ):

        return True



    if symbol.endswith(
        "." + imported
    ):

        return True



    return False



# ==========================================================
# NORMALIZATION
# ==========================================================


def _normalize_references(
    references
):
    """
    Stabilizuje wynik.

    Każdy consumer występuje
    tylko raz i jest sortowany.
    """


    for symbol, data in references.items():


        for key, values in data.items():


            data[key] = sorted(
                set(values)
            )



    return references



# ==========================================================
# MODULE IMPORT USERS
# ==========================================================


def find_import_users(
    target_module_id,
    modules
):
    """
    Znajduje moduły importujące
    dany moduł.


    Facts only.
    """


    users = []



    short_name = (
        target_module_id
        .split(".")[-1]
    )



    for module_id, module in modules.items():


        if module_id == target_module_id:

            continue



        for imp in module.imports:


            imported = imp.module



            if not imported:

                continue



            if (
                imported == target_module_id
                or
                imported.endswith(
                    "." + short_name
                )
            ):

                users.append(
                    module_id
                )


                break



    return sorted(
        set(users)
    )



# ==========================================================
# COMPATIBILITY ALIASES
# ==========================================================


build_references = (
    build_symbol_references
)



# ==========================================================
# EXPORTS
# ==========================================================


__all__ = [

    "build_symbol_references",

    "build_references",

    "find_import_users",

    "SymbolReferenceVisitor",

]


