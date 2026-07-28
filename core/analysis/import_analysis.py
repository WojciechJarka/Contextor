# -*- coding: utf-8 -*-

"""
repo_guardian/core/import_analysis.py

AST import usage extractor.

Extracts:
- imports
- aliases
- runtime usage
- type checking usage
- import classification
"""

import ast


class ImportUsageVisitor(ast.NodeVisitor):

    def __init__(self):

        self.names = {}

        self.type_checking_depth = 0


    def _is_type_checking_condition(self, node):

        if isinstance(node, ast.Name):

            return node.id == "TYPE_CHECKING"


        if isinstance(node, ast.Attribute):

            return node.attr == "TYPE_CHECKING"


        if isinstance(node, ast.BoolOp):

            return any(
                self._is_type_checking_condition(value)
                for value in node.values
            )


        return False



    def _register(
        self,
        name,
        data
    ):

        if name not in self.names:

            self.names[name] = {

                "runtime_usage": 0,

                "type_usage": 0,

                "sources": []

            }


        self.names[name]["sources"].append(
            data
        )



    def visit_Import(
        self,
        node
    ):

        for alias in node.names:

            local_name = (
                alias.asname
                or
                alias.name.split(".")[0]
            )


            self._register(
                local_name,
                {

                    "import_type": "module",

                    "module": alias.name,

                    "symbol": None,

                    "alias": alias.asname,

                }
            )



    def visit_ImportFrom(
        self,
        node
    ):

        module = node.module or ""


        for alias in node.names:

            local_name = (
                alias.asname
                or
                alias.name
            )


            self._register(
                local_name,
                {

                    "import_type": "from",

                    "module": module,

                    "symbol": alias.name,

                    "alias": alias.asname,

                }
            )



    def visit_If(
        self,
        node
    ):


        if self._is_type_checking_condition(
            node.test
        ):

            self.type_checking_depth += 1


            for item in node.body:

                self.visit(item)


            self.type_checking_depth -= 1


            for item in node.orelse:

                self.visit(item)


            return


        self.generic_visit(node)



    def visit_Name(
        self,
        node
    ):

        if isinstance(
            node.ctx,
            ast.Load
        ):

            if node.id in self.names:


                if self.type_checking_depth:

                    self.names[node.id]["type_usage"] += 1


                else:

                    self.names[node.id]["runtime_usage"] += 1



        self.generic_visit(node)



def extract_import_usage(tree):


    visitor = ImportUsageVisitor()


    visitor.visit(tree)



    result = {}



    for name,data in visitor.names.items():


        runtime = data["runtime_usage"]

        type_usage = data["type_usage"]



        if runtime:

            classification = "runtime"

        elif type_usage:

            classification = "type_only"

        else:

            classification = "unused"



        result[name] = {


            **data,


            "classification":
                classification,


            "confidence":

                "high"

                if runtime

                else

                "medium"

                if type_usage

                else

                "low",


            "runtime_available":
                bool(runtime)

        }



    return result
