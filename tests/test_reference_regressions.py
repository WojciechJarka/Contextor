import ast

from contextor.core.reference.visitor import SymbolReferenceVisitor


def test_local_argument_with_same_short_name_is_not_confirmed_callback():
    tree = ast.parse(
        "def ensure_dir(path):\n"
        "    consume(path)\n"
    )
    visitor = SymbolReferenceVisitor({"pkg.domain.module.path"})

    visitor.visit(tree)

    assert visitor.callback_called == set()


def test_imported_target_passed_as_argument_is_confirmed_callback():
    tree = ast.parse(
        "from pkg.handlers import callback\n"
        "register(callback)\n"
    )
    visitor = SymbolReferenceVisitor({"pkg.handlers.callback"})

    visitor.visit(tree)

    assert {item[0] for item in visitor.callback_called} == {"pkg.handlers.callback"}


def test_unimported_short_base_name_is_not_confirmed_inheritance():
    tree = ast.parse("class Child(Base):\n    pass\n")
    visitor = SymbolReferenceVisitor({"pkg.model.Base"})

    visitor.visit(tree)

    assert visitor.inherited == []


def test_imported_base_is_confirmed_inheritance():
    tree = ast.parse(
        "from pkg.model import Base\n"
        "class Child(Base):\n"
        "    pass\n"
    )
    visitor = SymbolReferenceVisitor({"pkg.model.Base"})

    visitor.visit(tree)

    assert visitor.inherited[0][:2] == ("Child", "pkg.model.Base")
