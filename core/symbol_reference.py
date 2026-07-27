"""
repo_guardian/core/symbol_reference.py

SYMBOL REFERENCE ENGINE v2.0

Warstwa:

    FACT EXTRACTION


Odpowiedzialność:

- wykrywanie użycia symboli
- wykrywanie wywołań metod/funkcji
- wykrywanie dziedziczenia
- wykrywanie importów symboli
- budowanie relacji symbol -> konsumenci
- generowanie CallResolution dla niejednoznacznych wywołań


Nie robi:

- scoringu
- ryzyka
- architektury
- raportowania


Nowy model:

confirmed_call
    |
    v
    EdgeInfo


ambiguous_call
    |
    v
    CallResolution
        - call_site
        - possible_targets
        - confidence
        - reason


"""

from __future__ import annotations


from pathlib import Path
import ast


from repo_guardian.core.domain.symbol import (
    CallResolution,
)



# ==========================================================
# CONSTANTS
# ==========================================================


CONFIDENCE_EXACT = 1.0

CONFIDENCE_INSTANCE = 0.95

CONFIDENCE_ALIAS = 0.90

CONFIDENCE_CALLBACK = 0.75

CONFIDENCE_HEURISTIC = 0.31



# ==========================================================
# NAME RESOLUTION
# ==========================================================


def _attribute_name(
    node
):
    """
    AST Name/Attribute -> dotted name.

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
    Resolve local import aliases.
    """

    if not name:

        return None


    return aliases.get(
        name,
        name
    )




def _short_name(
    value
):
    if not value:
        return None

    return value.split(".")[-1]




# ==========================================================
# SYMBOL MATCHING
# ==========================================================


def _possible_targets(
    value,
    symbols
):
    """
    Returns all possible symbol targets.

    Unlike old implementation:

        short name -> one guess

    this keeps all candidates.
    """


    if not value:

        return []



    if value in symbols:

        return [
            value
        ]



    short = _short_name(
        value
    )


    return sorted(

        symbol

        for symbol in symbols

        if _short_name(symbol) == short

    )




def _resolve_match(
    name,
    resolved,
    target_symbols,
    aliases,
):
    """
    Returns:

    (
        resolution_type,
        targets,
        confidence,
        reason
    )
    """


    if not resolved:

        return (
            None,
            [],
            0.0,
            None,
        )



    # ------------------------------------------------------
    # exact qualified match
    # ------------------------------------------------------

    if resolved in target_symbols:

        return (
            "confirmed",
            [resolved],
            CONFIDENCE_EXACT,
            "exact_match",
        )



    # ------------------------------------------------------
    # imported alias pointing elsewhere
    # ------------------------------------------------------

    if name in aliases:

        return (
            None,
            [],
            0.0,
            None,
        )



    # ------------------------------------------------------
    # possible short-name matches
    # ------------------------------------------------------

    candidates = _possible_targets(
        resolved,
        target_symbols,
    )


    if candidates:

        return (
            "ambiguous",
            candidates,
            CONFIDENCE_HEURISTIC,
            "short_name_fallback",
        )



    return (
        None,
        [],
        0.0,
        None,
    )



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


        self.call_resolutions = []


        self.event_bound = set()


        self.inherited = []


        self.aliases = {}


        self.instances = {}



        self.current_scope = None



    # ------------------------------------------------------
    # HELPERS
    # ------------------------------------------------------


    def _record_resolution(
        self,
        node,
        symbol,
        targets,
        confidence,
        reason,
    ):

        self.call_resolutions.append(

            CallResolution(

                call_site=(
                    f"{self.current_scope or '<module>'}:"
                    f"{getattr(node, 'lineno', 0)}"
                ),

                symbol=symbol,

                possible_targets=list(
                    targets
                ),

                confidence=confidence,

                resolution="ambiguous",

                reason=reason,

            )

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


            imported = (

                f"{node.module}.{item.name}"

                if node.module

                else item.name

            )


            self.aliases[
                local_name
            ] = imported



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

                item.name.split(".")[-1]

            )


            self.aliases[
                local_name
            ] = item.name



        self.generic_visit(
            node
        )


    # ------------------------------------------------------
    # SCOPE TRACKING
    # ------------------------------------------------------

    def visit_FunctionDef(
        self,
        node
    ):

        previous = self.current_scope

        self.current_scope = node.name


        self.generic_visit(
            node
        )


        self.current_scope = previous



    def visit_AsyncFunctionDef(
        self,
        node
    ):

        self.visit_FunctionDef(
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
    # INSTANCE METHOD RESOLUTION
    # ------------------------------------------------------

    def _resolve_instance_method(
        self,
        resolved
    ):

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
    # CALL DETECTION
    # ------------------------------------------------------

    def visit_Call(
        self,
        node
    ):


        called_name = _attribute_name(
            node.func
        )


        resolved = _resolve_alias(
            called_name,
            self.aliases
        )


        # --------------------------------------------------
        # Exact qualified call
        # --------------------------------------------------

        if resolved in self.target_symbols:


            self.called.add(
                resolved
            )


            self.generic_visit(
                node
            )


            return



        # --------------------------------------------------
        # Instance method
        # --------------------------------------------------

        if self._resolve_instance_method(
            resolved
        ):


            self.generic_visit(
                node
            )


            return



        # --------------------------------------------------
        # Ambiguous resolution
        # --------------------------------------------------

        kind, targets, confidence, reason = (
            _resolve_match(
                called_name,
                resolved,
                self.target_symbols,
                self.aliases,
            )
        )


        if kind == "ambiguous":


            self._record_resolution(

                node,

                called_name,

                targets,

                confidence,

                reason,

            )



        self.generic_visit(
            node
        )



    # ------------------------------------------------------
    # CALLBACK DETECTION
    # ------------------------------------------------------

    def _detect_callback(
        self,
        node
    ):


        callback_keys = {

            "callback",
            "handler",
            "func",
            "command",
            "on_click",
            "on_change",
            "on_submit",

        }



        for keyword in node.keywords:


            if keyword.arg not in callback_keys:

                continue



            name = _attribute_name(
                keyword.value
            )


            resolved = _resolve_alias(
                name,
                self.aliases
            )


            _, targets, _, _ = (
                _resolve_match(
                    name,
                    resolved,
                    self.target_symbols,
                    self.aliases,
                )
            )


            if len(targets) == 1:

                self.event_bound.add(
                    targets[0]
                )



    def _detect_positional_callback(
        self,
        node
    ):


        name = _attribute_name(
            node.func
        )


        if not name:

            return



        method = name.split(".")[-1]


        callback_methods = {

            "bind": 1,

            "subscribe": 1,

            "on": 0,

        }



        if method not in callback_methods:

            return



        index = callback_methods[
            method
        ]



        if len(node.args) <= index:

            return



        callback = _attribute_name(
            node.args[index]
        )


        resolved = _resolve_alias(
            callback,
            self.aliases
        )


        _, targets, _, _ = (
            _resolve_match(
                callback,
                resolved,
                self.target_symbols,
                self.aliases,
            )
        )


        if len(targets) == 1:

            self.event_bound.add(
                targets[0]
            )



    # ------------------------------------------------------
    # CALLBACK WRAPPER
    # ------------------------------------------------------

    def visit_Call(
        self,
        node
    ):

        self._detect_callback(
            node
        )

        self._detect_positional_callback(
            node
        )


        called_name = _attribute_name(
            node.func
        )


        resolved = _resolve_alias(
            called_name,
            self.aliases
        )



        if resolved in self.target_symbols:

            self.called.add(
                resolved
            )


            self.generic_visit(
                node
            )

            return



        if self._resolve_instance_method(
            resolved
        ):

            self.generic_visit(
                node
            )

            return



        kind, targets, confidence, reason = (
            _resolve_match(
                called_name,
                resolved,
                self.target_symbols,
                self.aliases,
            )
        )



        if kind == "ambiguous":

            self._record_resolution(
                node,
                called_name,
                targets,
                confidence,
                reason,
            )


        self.generic_visit(
            node
        )



    # ------------------------------------------------------
    # INHERITANCE
    # ------------------------------------------------------

    def visit_ClassDef(
        self,
        node
    ):


        for base in node.bases:


            name = _attribute_name(
                base
            )


            resolved = _resolve_alias(
                name,
                self.aliases
            )


            _, targets, _, _ = (
                _resolve_match(
                    name,
                    resolved,
                    self.target_symbols,
                    self.aliases,
                )
            )


            for target in targets:


                self.inherited.append(

                    (
                        node.name,
                        target
                    )

                )



        self.generic_visit(
            node
        )

# ==========================================================
# REFERENCE BUILDING
# ==========================================================


def _empty_reference():
    """
    Initial reference container.

    Legacy fields are preserved where possible,
    but ambiguous calls are now represented
    through CallResolution objects.
    """

    return {

        "called_by": [],

        "event_bound_by": [],

        "imported_from": [],

        "inherited_by": [],

        "call_resolutions": [],

    }



def _load_tree(
    root_path,
    module
):
    """
    Load module AST tree.
    """

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



def _import_matches_symbol(
    imported,
    symbol
):
    """
    Checks whether import points
    to requested symbol.
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



def _normalize_references(
    references
):
    """
    Deterministic output ordering.
    """

    for symbol, data in references.items():

        for key, value in data.items():

            if isinstance(
                value,
                list
            ):

                if key == "call_resolutions":

                    continue


                data[key] = sorted(
                    set(value)
                )


    return references



def build_symbol_references(
    modules,
    target_symbols,
    root_path,
    definer_module=None
):
    """
    Builds symbol references.

    Output:

    symbol:
        called_by
        event_bound_by
        imported_from
        inherited_by
        call_resolutions


    New behaviour:

    ambiguous calls are no longer
    stored as a guessed consumer.

    They become:

        CallResolution

    containing:

        call_site
        possible_targets
        confidence
        reason
    """


    bare_symbols = set(
        target_symbols
    )


    if definer_module:

        qualified_map = {

            f"{definer_module}.{symbol}":
                symbol

            for symbol in bare_symbols

        }


    else:

        qualified_map = {

            symbol:
                symbol

            for symbol in bare_symbols

        }



    qualified_symbols = set(
        qualified_map.keys()
    )



    references = {

        symbol:
            _empty_reference()

        for symbol in qualified_symbols

    }



    for module_id, module in modules.items():


        tree = _load_tree(
            root_path,
            module
        )


        if tree is None:

            continue



        visitor = SymbolReferenceVisitor(
            qualified_symbols
        )


        visitor.visit(
            tree
        )



        # --------------------------------------------------
        # Confirmed calls
        # --------------------------------------------------

        for symbol in visitor.called:


            if symbol in references:


                references[symbol][
                    "called_by"
                ].append(
                    module_id
                )



        # --------------------------------------------------
        # Ambiguous calls
        # --------------------------------------------------

        for resolution in visitor.call_resolutions:


            for target in resolution.possible_targets:


                if target in references:


                    references[target][
                        "call_resolutions"
                    ].append(
                        resolution
                    )



        # --------------------------------------------------
        # Events
        # --------------------------------------------------

        for symbol in visitor.event_bound:


            if symbol in references:


                references[symbol][
                    "event_bound_by"
                ].append(
                    module_id
                )



        # --------------------------------------------------
        # Inheritance
        # --------------------------------------------------

        for child_name, symbol in visitor.inherited:


            if symbol in references:


                references[symbol][
                    "inherited_by"
                ].append(
                    module_id
                )



        # --------------------------------------------------
        # Imports
        # --------------------------------------------------

        for imp in module.imports:


            imported_module = getattr(
                imp,
                "module",
                None
            )


            if definer_module:

                if not _import_matches_symbol(
                    imported_module or "",
                    definer_module,
                ):

                    continue



            for imported_name in imp.names:


                for qualified in qualified_symbols:


                    bare = qualified_map[
                        qualified
                    ]


                    if imported_name == bare:


                        references[qualified][
                            "imported_from"
                        ].append(
                            module_id
                        )



    references = _normalize_references(
        references
    )



    # Restore old API:
    # qualified symbol -> bare symbol

    return {

        qualified_map[key]:
            value

        for key, value
        in references.items()

    }



# ==========================================================
# MODULE IMPORT USERS
# ==========================================================


def find_import_users(
    target_module_id,
    modules
):
    """
    Finds modules importing target module.
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
# COMPATIBILITY
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
