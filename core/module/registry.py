# -*- coding: utf-8 -*-

"""
repo_guardian/core/module/registry.py

Owns module contexts.
"""


from .model import (
    ModuleContext,
)



class ModuleRegistry:


    def __init__(self):

        self._modules: dict[str, ModuleContext] = {}



    def add(
        self,
        context: ModuleContext
    ):

        self._modules[
            context.identity.module_id
        ] = context



    def get(
        self,
        module_id: str
    ):

        return self._modules.get(
            module_id
        )



    def all(self):

        return self._modules.values()



    def ids(self):

        return sorted(
            self._modules.keys()
        )
