# -*- coding: utf-8 -*-

"""
repo_guardian/core/exposure_analysis.py

EXPOSURE ANALYSIS

Warstwa:
    FACT EXTRACTION

Odpowiedzialność:

- wykrywanie kanałów konsumpcji symbolu, których
  symbol_reference.py NIE widzi, bo nie są to zwykłe
  wywołania/importy/dziedziczenie:

    reflection      - dostęp przez getattr/setattr/hasattr/
                       delattr/globals()/locals() z nazwą
                       symbolu jako literałem stringowym
    serialization   - nazwa symbolu jako literał stringowy
                       wewnątrz wywołania funkcji serializującej
                       (json.dumps, yaml.dump, pickle.dumps,
                       dataclasses.asdict/astuple, .dict(),
                       .model_dump())
    cli_exposure    - definicja symbolu udekorowana wzorcem
                       CLI (click/typer: command/group) LUB
                       wywołana po nazwie w bloku
                       `if __name__ == "__main__":` w JEJ
                       WŁASNYM module
    api_exposure    - definicja symbolu udekorowana wzorcem
                       web-route (Flask/FastAPI: get/post/put/
                       delete/patch/route) LUB dziedziczy po
                       bazie z nazwą sugerującą web-endpoint
                       (View/Resource/Controller/Endpoint)

Nie robi:

- type inference (dopasowanie po nazwie, tak jak cały
  repo_guardian - nie wie, czy zmienna faktycznie jest
  instancją danej klasy)
- scoringu / ryzyka (to artifact_consumption.py)
- gwarancji poprawności - to SYGNAŁY TEKSTOWE, nie dowód
  wykonania. Możliwe false positive (inna funkcja też
  nazywa się "run") i false negative (dynamicznie budowany
  string).

Kontrakt:

{
    "Symbol": {
        "reflection": [modules...],
        "serialization": [modules...],
        "cli_exposure": bool,
        "api_exposure": bool
    }
}
"""


from pathlib import Path
import ast


# ==========================================================
# CONFIG
# ==========================================================

REFLECTION_FUNCS = {
    "getattr",
    "setattr",
    "hasattr",
    "delattr",
}

SERIALIZATION_FUNCS = {
    "dumps",
    "dump",
    "asdict",
    "astuple",
    "model_dump",
    "model_dump_json",
    "dict",
    "to_dict",
}

CLI_DECORATORS = {
    "command",
    "group",
}

API_DECORATORS = {
    "get",
    "post",
    "put",
    "delete",
    "patch",
    "route",
    "websocket",
}

API_BASE_HINTS = (
    "View",
    "Resource",
    "Controller",
    "Endpoint",
)


# ==========================================================
# NAME HELPERS
# ==========================================================


def _decorator_name(node):

    if isinstance(node, ast.Call):
        return _decorator_name(node.func)

    if isinstance(node, ast.Attribute):
        return node.attr

    if isinstance(node, ast.Name):
        return node.id

    return None


def _base_name(node):

    if isinstance(node, ast.Attribute):
        return node.attr

    if isinstance(node, ast.Name):
        return node.id

    return None


# ==========================================================
# PROJECT-WIDE VISITOR: REFLECTION / SERIALIZATION
# ==========================================================


class ExposureCallVisitor(ast.NodeVisitor):
    """
    Szuka literałów stringowych zgodnych z nazwami szukanych
    symboli, wewnątrz wywołań funkcji reflection/serialization.
    """

    def __init__(self, target_symbols):

        self.target_symbols = set(target_symbols)
        self.reflection_hits = set()
        self.serialization_hits = set()

    def _call_name(self, node):

        if isinstance(node.func, ast.Name):
            return node.func.id

        if isinstance(node.func, ast.Attribute):
            return node.func.attr

        return None

    def _string_literals(self, node):

        for child in ast.walk(node):

            if isinstance(child, ast.Constant) and isinstance(child.value, str):

                yield child.value

    def visit_Call(self, node):

        name = self._call_name(node)

        if name in REFLECTION_FUNCS:

            for arg in node.args:

                if isinstance(arg, ast.Constant) and isinstance(arg.value, str):

                    if arg.value in self.target_symbols:

                        self.reflection_hits.add(arg.value)

        if name in SERIALIZATION_FUNCS:

            for literal in self._string_literals(node):

                if literal in self.target_symbols:

                    self.serialization_hits.add(literal)

        self.generic_visit(node)

    def visit_Subscript(self, node):
        #
        # globals()["symbol"] / locals()["symbol"]
        #
        if not isinstance(node.value, ast.Call):
            self.generic_visit(node)
            return

        name = self._call_name(node.value)

        if name not in {"globals", "locals"}:
            self.generic_visit(node)
            return

        key = node.slice

        if isinstance(key, ast.Constant) and isinstance(key.value, str):

            if key.value in self.target_symbols:

                self.reflection_hits.add(key.value)

        self.generic_visit(node)


def _load_tree(root_path, module):

    try:

        path = Path(root_path) / module.path

        return ast.parse(path.read_text(encoding="utf-8"))

    except Exception:

        return None


def build_reflection_and_serialization(modules, target_symbols, root_path):
    """
    Skan CAŁEGO projektu: czy nazwa szukanego symbolu
    pojawia się jako literał stringowy w wywołaniu
    reflection/serialization.

    Facts only - dopasowanie po identyczności stringa.
    """

    target_symbols = set(target_symbols)

    reflection = {symbol: [] for symbol in target_symbols}
    serialization = {symbol: [] for symbol in target_symbols}

    for module_id, module in modules.items():

        tree = _load_tree(root_path, module)

        if tree is None:
            continue

        visitor = ExposureCallVisitor(target_symbols)
        visitor.visit(tree)

        for symbol in visitor.reflection_hits:
            reflection[symbol].append(module_id)

        for symbol in visitor.serialization_hits:
            serialization[symbol].append(module_id)

    for symbol in target_symbols:
        reflection[symbol] = sorted(set(reflection[symbol]))
        serialization[symbol] = sorted(set(serialization[symbol]))

    return reflection, serialization


# ==========================================================
# LOCAL VISITOR: CLI / API EXPOSURE (własny moduł symbolu)
# ==========================================================


def _walk_stmts(stmts):

    for stmt in stmts:

        yield from ast.walk(stmt)


def _has_main_guard_call(tree, symbol):
    """
    Sprawdza czy symbol jest wywoływany po nazwie wewnątrz
    `if __name__ == "__main__":` w TYM module.
    """

    for node in ast.walk(tree):

        if not isinstance(node, ast.If):
            continue

        test = node.test

        is_main_guard = (
            isinstance(test, ast.Compare)
            and isinstance(test.left, ast.Name)
            and test.left.id == "__name__"
        )

        if not is_main_guard:
            continue

        for inner in _walk_stmts(node.body):

            if not isinstance(inner, ast.Call):
                continue

            name = None

            if isinstance(inner.func, ast.Name):
                name = inner.func.id
            elif isinstance(inner.func, ast.Attribute):
                name = inner.func.attr

            if name == symbol:
                return True

    return False


def build_cli_and_api_exposure(tree, symbols):
    """
    Skan WŁASNEGO modułu symbolu (nie projektu) - cli/api
    exposure to cecha definicji, nie użycia gdzie indziej.
    """

    symbols = set(symbols)

    cli_exposure = {symbol: False for symbol in symbols}
    api_exposure = {symbol: False for symbol in symbols}

    for node in ast.walk(tree):

        if not isinstance(
            node,
            (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef),
        ):
            continue

        if node.name not in symbols:
            continue

        decorator_names = {
            _decorator_name(dec)
            for dec in getattr(node, "decorator_list", [])
        }

        if decorator_names & CLI_DECORATORS:
            cli_exposure[node.name] = True

        if decorator_names & API_DECORATORS:
            api_exposure[node.name] = True

        if isinstance(node, ast.ClassDef):

            base_names = {
                _base_name(base) or ""
                for base in node.bases
            }

            if any(
                hint in name
                for name in base_names
                for hint in API_BASE_HINTS
            ):
                api_exposure[node.name] = True

    for symbol in symbols:

        if _has_main_guard_call(tree, symbol):
            cli_exposure[symbol] = True

    return cli_exposure, api_exposure


# ==========================================================
# PUBLIC ENTRY POINT
# ==========================================================


def analyze_symbol_exposure(modules, target_symbols, root_path, tree):
    """
    Łączy project-wide reflection/serialization z lokalnym
    cli/api exposure w jeden kontrakt per symbol.
    """

    reflection, serialization = build_reflection_and_serialization(
        modules,
        target_symbols,
        root_path,
    )

    cli_exposure, api_exposure = build_cli_and_api_exposure(
        tree,
        target_symbols,
    )

    result = {}

    for symbol in target_symbols:

        result[symbol] = {

            "reflection":
                reflection.get(symbol, []),

            "serialization":
                serialization.get(symbol, []),

            "cli_exposure":
                cli_exposure.get(symbol, False),

            "api_exposure":
                api_exposure.get(symbol, False),
        }

    return result


# ==========================================================
# EXPORTS
# ==========================================================


__all__ = [
    "build_reflection_and_serialization",
    "build_cli_and_api_exposure",
    "analyze_symbol_exposure",
]
