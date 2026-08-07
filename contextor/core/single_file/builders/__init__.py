from .registry import BuilderRegistry, ContextPayload, BuildState

from .layer0_builders import (
    ModuleIntentBuilder, SymbolContextBuilder, ImportContextBuilder,
    SemanticContextBuilder, FunctionContextBuilder, StateContextBuilder,
    ArchitectureContextBuilder, ApiSurfaceBuilder, ImportUsersBuilder,
    GitContextBuilder
)
from .layer1_builders import PublicApiBuilder, ExportContextBuilder
from .layer2_builders import TestContextBuilder, ActivityBuilder
from .layer3_builders import ArtifactConsumptionBuilder

def _setup_default_registry() -> BuilderRegistry:
    registry = BuilderRegistry()
    
    # Layer 0
    registry.register(ModuleIntentBuilder())
    registry.register(SymbolContextBuilder())
    registry.register(ImportContextBuilder())
    registry.register(SemanticContextBuilder())
    registry.register(FunctionContextBuilder())
    registry.register(StateContextBuilder())
    registry.register(ArchitectureContextBuilder())
    registry.register(ApiSurfaceBuilder())
    registry.register(ImportUsersBuilder())
    registry.register(GitContextBuilder())
    
    # Layer 1
    registry.register(PublicApiBuilder())
    registry.register(ExportContextBuilder())
    
    # Layer 2
    registry.register(TestContextBuilder())
    registry.register(ActivityBuilder())
    
    # Layer 3
    registry.register(ArtifactConsumptionBuilder())
    
    return registry

default_registry = _setup_default_registry()
