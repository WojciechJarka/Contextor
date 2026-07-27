# -*- coding: utf-8 -*-

"""
repo_guardian/core/symbol_analysis.py

SYMBOL FACT EXTRACTION ENGINE

Odpowiedzialność:

- ekstrakcja deklaracji symboli
- ekstrakcja wywołań
- ekstrakcja global assignments
- ekstrakcja nazw AST

Nie:
- analizuje architektury
- nie zna grafu
- nie liczy ryzyka
- nie interpretuje API


Output:
SymbolFacts
"""


from dataclasses import dataclass, field
from pathlib import Path
import ast



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

    calls: set[str] = field(
        default_factory=set
    )

    assignments: set[str] = field(
        default_factory=set
    )

    errors: list[str] = field(
        default_factory=list
    )


    def all_symbols(self) -> set[str]:

        return (
            self.classes
            |
            self.functions
            |
            self.methods
            |
            self.globals
        )


    def to_dict(self):

        return {

            "classes":
                sorted(self.classes),

            "functions":
                sorted(self.functions),

            "methods":
                sorted(self.methods),

            "globals":
                sorted(self.globals),

            "calls":
                sorted(self.calls),

            "assignments":
                sorted(self.assignments),

            "errors":
                self.errors,
        }



# ==========================================================
# AST HELPERS
# ==========================================================


def _call_name(node):

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
# VISITOR
# ==========================================================


class SymbolVisitor(
    ast.NodeVisitor
):


    def __init__(self):

        self.facts = SymbolFacts()

        self.class_stack = []

        self.function_depth = 0



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



    def visit_FunctionDef(
        self,
        node
    ):

        if self.class_stack:

            self.facts.methods.add(
                f"{self.class_stack[-1]}.{node.name}"
            )

        else:

            self.facts.functions.add(
                node.name
            )


        self.function_depth += 1


        self.generic_visit(
            node
        )


        self.function_depth -= 1



    def visit_AsyncFunctionDef(
        self,
        node
    ):

        self.visit_FunctionDef(
            node
        )



    def visit_Assign(
        self,
        node
    ):


        if self.function_depth == 0:


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

            self.function_depth == 0

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



    def visit_Call(
        self,
        node
    ):


        name = _call_name(
            node.func
        )


        if name:

            self.facts.calls.add(
                name
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
    Główny extractor facts.
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
    Kompatybilny adapter.

    Stare warstwy nadal dostają dict.

    Nowe warstwy powinny używać
    extract_symbol_facts().
    """


    facts = extract_symbol_facts(
        file_path
    )


    return facts.to_dict()

# ==========================================================
# IMPORT FACTS
# ==========================================================


def _module_candidates(
    name: str
) -> set[str]:

    """
    Tworzy możliwe prefiksy modułu.

    np.

    repo_guardian.core.foo.bar

    =>
    repo_guardian
    repo_guardian.core
    repo_guardian.core.foo
    repo_guardian.core.foo.bar

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
            len(parts) + 1
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
    Klasyfikuje import facts.

    Nie rozwiązuje importów.
    Nie ocenia jakości.
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
            sorted(
                internal
            ),


        "external":
            sorted(
                external
            ),


        "local":
            sorted(
                local
            ),


        "global":
            sorted(
                global_imports
            ),
    }

# ==========================================================
# SYMBOL USAGE FACTS
# ==========================================================


class UsageVisitor(
    ast.NodeVisitor
):


    def __init__(
        self,
        wanted_symbols
    ):

        self.wanted = set(
            wanted_symbols
        )

        self.used = set()



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
    Facts:

    symbol -> modules using it
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

        for key, value in usage.items()

    }



# ==========================================================
# SYMBOL INDEX
# ==========================================================


def build_symbol_index(
    modules,
    root_path=None
):

    """
    Buduje globalny indeks:

    symbol
        ->
    moduły posiadające symbol
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
    symbol: sorted(modules)
    for symbol, modules in index.items()
}




# ==========================================================
# PUBLIC EXPORTS
# ==========================================================


__all__ = [

    "SymbolFacts",

    "extract_symbol_facts",

    "extract_file_symbols",

    "classify_imports",

    "find_symbol_usage",

    "build_symbol_index",

]
