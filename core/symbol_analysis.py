"""
repo_guardian/core/symbol_analysis.py

SYMBOL FACT EXTRACTION ENGINE v2.0


WARSTWA:

    FACT EXTRACTION


Odpowiedzialność:

- ekstrakcja deklaracji symboli
- ekstrakcja wywołań AST
- ekstrakcja global assignments
- ekstrakcja kwalifikowanych nazw
- ekstrakcja lokalizacji wywołań


Nie:

- analizuje architektury
- nie zna grafu
- nie liczy ryzyka
- nie generuje raportów


Output:

SymbolFacts


"""

from __future__ import annotations


from dataclasses import (
    dataclass,
    field,
)

from pathlib import Path

import ast



# ==========================================================
# CALL FACT
# ==========================================================


@dataclass(
    frozen=True
)
class CallFact:
    """
    Raw AST call information.

    Jest źródłem dla późniejszego
    CallResolution.
    """

    caller: str

    callee: str

    line: int

    scope: str

    kind: str = "call"



# ==========================================================
# DOMAIN FACTS
# ==========================================================


@dataclass
class SymbolFacts:


    classes: set[str] = field(
        default_factory=set
    )


    functions: set[str] = field(
        default_factory=set
    )


    methods: set[str] = field(
        default_factory=set
    )


    globals: set[str] = field(
        default_factory=set
    )


    calls: list[CallFact] = field(
        default_factory=list
    )


    assignments: set[str] = field(
        default_factory=set
    )


    errors: list[str] = field(
        default_factory=list
    )



    def all_symbols(
        self
    ) -> set[str]:

        return (

            self.classes

            |

            self.functions

            |

            self.methods

            |

            self.globals

        )



    def to_dict(
        self
    ):

        return {


            "classes":

                sorted(
                    self.classes
                ),


            "functions":

                sorted(
                    self.functions
                ),


            "methods":

                sorted(
                    self.methods
                ),


            "globals":

                sorted(
                    self.globals
                ),


            "calls":

                [

                    {

                        "caller":
                            call.caller,

                        "callee":
                            call.callee,

                        "line":
                            call.line,

                        "scope":
                            call.scope,

                        "kind":
                            call.kind,

                    }

                    for call
                    in self.calls

                ],


            "assignments":

                sorted(
                    self.assignments
                ),


            "errors":

                self.errors,

        }



# ==========================================================
# AST NAME HELPERS
# ==========================================================


def _call_name(
    node
):


    if isinstance(
        node,
        ast.Name
    ):

        return node.id



    if isinstance(
        node,
        ast.Attribute
    ):


        parent = _call_name(
            node.value
        )


        if parent:

            return (
                f"{parent}.{node.attr}"
            )


        return node.attr



    return None



# ==========================================================
# SYMBOL VISITOR
# ==========================================================


class SymbolVisitor(
    ast.NodeVisitor
):


    def __init__(
        self
    ):

        self.facts = SymbolFacts()

        self.class_stack = []

        self.function_stack = []



    def _current_scope(
        self
    ) -> str:


        if self.function_stack:

            return ".".join(
                self.function_stack
            )


        return "<module>"



    def _current_caller(
        self
    ) -> str:


        if self.class_stack and self.function_stack:


            return (

                f"{self.class_stack[-1]}."

                f"{self.function_stack[-1]}"

            )


        if self.function_stack:

            return self.function_stack[-1]


        return "<module>"


    # ------------------------------------------------------
    # CLASS EXTRACTION
    # ------------------------------------------------------

    def visit_ClassDef(
        self,
        node
    ):


        self.facts.classes.add(
            node.name
        )


        self.class_stack.append(
            node.name
        )


        self.generic_visit(
            node
        )


        self.class_stack.pop()



    # ------------------------------------------------------
    # FUNCTION / METHOD EXTRACTION
    # ------------------------------------------------------

    def visit_FunctionDef(
        self,
        node
    ):


        if self.class_stack:


            self.facts.methods.add(

                f"{self.class_stack[-1]}."

                f"{node.name}"

            )


        else:


            self.facts.functions.add(
                node.name
            )



        self.function_stack.append(
            node.name
        )


        self.generic_visit(
            node
        )


        self.function_stack.pop()



    def visit_AsyncFunctionDef(
        self,
        node
    ):


        self.visit_FunctionDef(
            node
        )



    # ------------------------------------------------------
    # GLOBAL ASSIGNMENTS
    # ------------------------------------------------------

    def visit_Assign(
        self,
        node
    ):


        if not self.function_stack:


            for target in node.targets:


                if isinstance(
                    target,
                    ast.Name
                ):


                    self.facts.globals.add(
                        target.id
                    )


                    self.facts.assignments.add(
                        target.id
                    )



        self.generic_visit(
            node
        )



    def visit_AnnAssign(
        self,
        node
    ):


        if (

            not self.function_stack

            and

            isinstance(
                node.target,
                ast.Name
            )

        ):


            self.facts.globals.add(
                node.target.id
            )


            self.facts.assignments.add(
                node.target.id
            )



        self.generic_visit(
            node
        )



    # ------------------------------------------------------
    # CALL EXTRACTION
    # ------------------------------------------------------

    def visit_Call(
        self,
        node
    ):


        name = _call_name(
            node.func
        )


        if name:


            self.facts.calls.append(

                CallFact(

                    caller=self._current_caller(),

                    callee=name,

                    line=getattr(
                        node,
                        "lineno",
                        0
                    ),

                    scope=self._current_scope(),

                )

            )



        self.generic_visit(
            node
        )



# ==========================================================
# FILE EXTRACTION
# ==========================================================


def extract_symbol_facts(
    file_path: Path | str
) -> SymbolFacts:
    """
    Main AST facts extractor.
    """


    path = Path(
        file_path
    )


    facts = SymbolFacts()



    try:

        tree = ast.parse(

            path.read_text(
                encoding="utf-8"
            )

        )


    except Exception as exc:


        facts.errors.append(
            str(exc)
        )


        return facts



    visitor = SymbolVisitor()


    visitor.visit(
        tree
    )


    return visitor.facts



# ==========================================================
# LEGACY COMPATIBILITY
# ==========================================================


def extract_file_symbols(
    file_path: Path | str
) -> dict:
    """
    Compatibility adapter.

    Old consumers receive dict.

    New layers should use
    extract_symbol_facts().
    """


    facts = extract_symbol_facts(
        file_path
    )


    return facts.to_dict()



# ==========================================================
# IMPORT CLASSIFICATION
# ==========================================================


def _module_candidates(
    name: str
) -> set[str]:
    """
    Creates possible module prefixes.
    """


    if not name:

        return set()



    parts = name.split(".")


    return {

        ".".join(
            parts[:index]
        )

        for index in range(
            1,
            len(parts)+1
        )

    }



def _is_internal_import(
    name: str,
    known_modules: set[str]
) -> bool:


    candidates = _module_candidates(
        name
    )


    if candidates.intersection(
        known_modules
    ):

        return True



    return any(

        module.startswith(
            name + "."
        )

        for module in known_modules

    )



def classify_imports(
    module,
    known_modules: set
) -> dict:
    """
    Classifies imports.

    Facts only.
    """


    internal = set()

    external = set()

    local = set()

    global_imports = set()



    for imp in module.imports:


        name = imp.module


        if not name:

            continue



        if _is_internal_import(
            name,
            known_modules
        ):


            internal.add(
                name
            )


            if getattr(
                imp,
                "is_local",
                False
            ):

                local.add(
                    name
                )


        else:

            external.add(
                name
            )

            global_imports.add(
                name
            )



    return {

        "internal":
            sorted(internal),

        "external":
            sorted(external),

        "local":
            sorted(local),

        "global":
            sorted(global_imports),

    }


# ==========================================================
# SYMBOL USAGE FACTS
# ==========================================================


class UsageVisitor(
    ast.NodeVisitor
):
    """
    Finds symbol usage.

    Works on raw facts.
    Does not resolve architecture.
    """


    def __init__(
        self,
        wanted_symbols
    ):

        self.wanted = set(
            wanted_symbols
        )


        self.used = set()


        self.calls: list[CallFact] = []

        self.scope_stack = []



    def _scope(
        self
    ):

        if self.scope_stack:

            return ".".join(
                self.scope_stack
            )

        return "<module>"



    def visit_FunctionDef(
        self,
        node
    ):

        self.scope_stack.append(
            node.name
        )


        self.generic_visit(
            node
        )


        self.scope_stack.pop()



    def visit_AsyncFunctionDef(
        self,
        node
    ):

        self.visit_FunctionDef(
            node
        )



    def visit_Name(
        self,
        node
    ):


        if node.id in self.wanted:

            self.used.add(
                node.id
            )


        self.generic_visit(
            node
        )



    def visit_Attribute(
        self,
        node
    ):


        name = _call_name(
            node
        )


        if name in self.wanted:

            self.used.add(
                name
            )


        short = (

            name.split(".")[-1]

            if name

            else None

        )


        if short in self.wanted:

            self.used.add(
                short
            )


        self.generic_visit(
            node
        )



    def visit_Call(
        self,
        node
    ):


        name = _call_name(
            node.func
        )


        if name:


            self.calls.append(

                CallFact(

                    caller="<usage>",

                    callee=name,

                    line=getattr(
                        node,
                        "lineno",
                        0
                    ),

                    scope=self._scope(),

                )

            )


        self.generic_visit(
            node
        )



def _read_module_tree(
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



def find_symbol_usage(
    modules,
    target_module,
    symbols,
    root_path
):
    """
    Finds modules using symbols.

    Returns:

        symbol:
            modules

    """

    usage = {}


    wanted = set(
        symbols
    )


    if not wanted:

        return usage



    for module_id, module in modules.items():


        if module_id == target_module:

            continue



        tree = _read_module_tree(
            root_path,
            module
        )


        if tree is None:

            continue



        visitor = UsageVisitor(
            wanted
        )


        visitor.visit(
            tree
        )



        for symbol in visitor.used:


            usage.setdefault(
                symbol,
                []
            ).append(
                module_id
            )



    return {

        key:

            sorted(
                set(value)
            )

        for key, value

        in usage.items()

    }



# ==========================================================
# SYMBOL INDEX
# ==========================================================


def build_symbol_index(
    modules,
    root_path=None
):
    """
    Builds:

        symbol
            ->
        defining modules
    """


    index = {}



    for module_id, module in modules.items():


        if root_path:


            facts = extract_symbol_facts(

                Path(root_path)
                /
                module.path

            )


        else:


            facts = extract_symbol_facts(

                module.path

            )



        if facts.errors:

            continue



        for symbol in facts.all_symbols():


            index.setdefault(
                symbol,
                []
            ).append(
                module_id
            )



    return {

        symbol:

            sorted(
                modules
            )

        for symbol, modules

        in index.items()

    }



# ==========================================================
# PUBLIC EXPORTS
# ==========================================================


__all__ = [

    "CallFact",

    "SymbolFacts",

    "extract_symbol_facts",

    "extract_file_symbols",

    "classify_imports",

    "find_symbol_usage",

    "build_symbol_index",

]
