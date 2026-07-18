# -*- coding: utf-8 -*-

"""
Semantic detectors.

AST-only extraction of factual code behavior.
No quality judgement.
"""


import ast
from collections import defaultdict


SIDE_EFFECT_RULES = {

    # process execution
    "Popen": "process_execution",
    "run": "process_execution",
    "call": "process_execution",
    "check_call": "process_execution",

    # filesystem
    "open": "filesystem_io",
    "read": "filesystem_read",
    "write": "filesystem_write",
    "glob": "filesystem_read",

    # logging
    "getLogger": "logging",
    "debug": "logging",
    "info": "logging",
    "warning": "logging",
    "error": "logging",
    "critical": "logging",

    # randomness/time
    "random": "random",
    "time": "time",

}


RISK_RULES = {

    "exec": "exec",
    "eval": "eval",

    "Popen": "subprocess",
    "run": "subprocess",

    "system": "os_command",

    "importlib": "reflection",

}


class SemanticDetector(ast.NodeVisitor):

    def __init__(self):

        self.side_effects = []
        self.risks = []

        self.exceptions = {
            "raises": [],
            "caught": []
        }

        self.import_symbols = defaultdict(
            lambda: {
                "count":0,
                "symbols":set()
            }
        )


    def visit_Call(self,node):

        name = self._call_name(node)


        if name:

            short = name.split(".")[-1]


            if short in SIDE_EFFECT_RULES:

                self.side_effects.append(
                    {
                        "type":
                            SIDE_EFFECT_RULES[short],

                        "symbol":
                            name,

                        "line":
                            node.lineno
                    }
                )


            if short in RISK_RULES:

                self.risks.append(
                    {
                        "type":
                            RISK_RULES[short],

                        "symbol":
                            name,

                        "line":
                            node.lineno
                    }
                )


        self.generic_visit(node)



    def visit_Raise(self,node):

        if node.exc:

            name = self._node_name(node.exc)

            if name:

                self.exceptions["raises"].append(
                    {
                        "type":name,
                        "line":node.lineno
                    }
                )


        self.generic_visit(node)



    def visit_ExceptHandler(self,node):

        if node.type:

            name=self._node_name(node.type)

            if name:

                self.exceptions["caught"].append(
                    {
                        "type":name,
                        "line":node.lineno
                    }
                )

        self.generic_visit(node)



    def visit_Import(self,node):

        for alias in node.names:

            self.import_symbols[
                alias.name
            ]["count"] += 1


        self.generic_visit(node)



    def visit_ImportFrom(self,node):

        module=node.module or ""

        for alias in node.names:

            self.import_symbols[module]["count"] += 1

            self.import_symbols[module]["symbols"].add(
                alias.name
            )


        self.generic_visit(node)



    def _call_name(self,node):

        if isinstance(node.func,ast.Name):

            return node.func.id


        if isinstance(node.func,ast.Attribute):

            parts=[]

            current=node.func

            while isinstance(
                current,
                ast.Attribute
            ):

                parts.append(
                    current.attr
                )

                current=current.value


            if isinstance(
                current,
                ast.Name
            ):

                parts.append(
                    current.id
                )

                return ".".join(
                    reversed(parts)
                )

        return None



    def _node_name(self,node):

        if isinstance(node,ast.Name):
            return node.id

        if isinstance(node,ast.Attribute):
            return node.attr

        return None



def analyze_semantics(source):

    tree = ast.parse(source)

    detector = SemanticDetector()

    detector.visit(tree)


    return {

        "side_effects":
            detector.side_effects,

        "risks":
            detector.risks,

        "exceptions":
            detector.exceptions,

        "import_symbols":
            {
                k:{
                    "count":v["count"],
                    "symbols":
                        sorted(v["symbols"])
                }

                for k,v
                in detector.import_symbols.items()
            }

    }
