# CPA_PACKAGE_INIT_CANONICAL_IMPORT_IDENTITY_DISCOVERY

STATUS=DISCOVERY_COMPLETE
HEAD=562a704fbf4c7dcde4fe8df1b880b6cfc138a6bc
WORKTREE_STATE=REPORT_ONLY_MODIFIED (walkthrough.md)
DIRECT_EVIDENCE: Before writing this report, git status --short returned no entries and git diff --stat returned no output. After writing it, git status --short reports only M walkthrough.md. No production/source/test/schema files were changed.

ACCEPTED_BASELINE=CPA_CANONICAL_STAR_IMPORT_UNIFIED_SEMANTICS
CONTRACT_PROVED: User accepted this baseline and instructed not to revert it. Current HEAD is 562a704fbf4c7dcde4fe8df1b880b6cfc138a6bc and the worktree is clean. No historical commit-provenance claim is made.

## MODULE_IDENTITY

DIRECT_EVIDENCE: Fresh full analysis of the temporary pkg/__init__.py + consumer.py fixture returned module IDs consumer and pkg.__init__. Shared re-export facts recorded exporter="pkg"; consumer star source was pkg.

CODE_PATH_PROVED: symbol_engine/indexer.py::_process_single_file derives module ID from the relative path, so the initializer becomes pkg.__init__. shared.py::_export_module_name removes the .__init__ suffix; _extract_reexport_facts uses the normalized exporter.

- INDEX_MODULE_ID=pkg.__init__
- REEXPORT_EXPORTER=pkg
- EXTERNAL_IMPORT_IDENTITY=pkg

## CANONICAL_ARTIFACT_IDENTITIES

DIRECT_EVIDENCE: Full canonical state used these package-local targets:
- pkg.__init__::PUBLIC
- pkg.__init__::_PRIVATE
- pkg.__init__::__all__

CODE_PATH_PROVED: Canonical artifact targets preserve indexed definer ID pkg.__init__, while the package export surface used external dotted spelling such as pkg.PUBLIC.

## FULL_PACKAGE_STAR_EXPLICIT

CONTRACT_PROVED: For from pkg import * with __all__ = ["PUBLIC"], PUBLIC should be consumed by consumer on api_imports; _PRIVATE should not be consumed; __all__ should be consumed as metadata by consumer on api_imports.

DIRECT_EVIDENCE: Full canonical artifact entries:
- pkg.__init__::PUBLIC = {"consumers":[],"channels":{}} — FULL_PACKAGE_STAR_PUBLIC=FAIL (expected consumer missing).
- pkg.__init__::_PRIVATE = {"consumers":[],"channels":{}} — FULL_PACKAGE_STAR_PRIVATE=PASS.
- pkg.__init__::__all__ = {"consumers":[],"channels":{}} — FULL_PACKAGE_STAR_ALL_METADATA=FAIL (expected metadata consumer missing).
- Surface: module_export_surfaces["pkg"]={"PUBLIC":"pkg.PUBLIC"}.
- Star consumer index: star_imports_by_source["pkg"]=["consumer"].

## FULL_PACKAGE_STAR_EMPTY

CONTRACT_PROVED: With __all__ = [], neither PUBLIC nor _PRIVATE should have a star consumer; __all__ remains a metadata dependency consumed on api_imports.

DIRECT_EVIDENCE: Fresh full canonical entries:
- pkg.__init__::PUBLIC = {"consumers":[],"channels":{}} — expected no consumer, PASS.
- pkg.__init__::_PRIVATE = {"consumers":[],"channels":{}} — expected no consumer, PASS.
- pkg.__init__::__all__ = {"consumers":[],"channels":{}} — expected metadata consumer missing, FAIL.

## FULL_PACKAGE_STAR_IMPLICIT

CONTRACT_PROVED: With __all__ removed, PUBLIC should be consumed on api_imports, _PRIVATE should not be consumed, and no canonical __all__ target should exist.

DIRECT_EVIDENCE: Fresh full canonical results:
- pkg.__init__::PUBLIC = {"consumers":[],"channels":{}} — expected consumer missing, FAIL.
- pkg.__init__::_PRIVATE = {"consumers":[],"channels":{}} — expected no consumer, PASS.
- pkg.__init__::__all__ target absent — PASS.

## PACKAGE_REEXPORT_PROVIDER

DIRECT_EVIDENCE: Fixture used pkg/provider.py defining run, initializer from .provider import run, and consumer from pkg import *; run().
- Canonical origin: pkg.provider::run.
- Facts at pkg.__init__: {"bindings":{"run":"pkg.provider.run"},"explicit_all":["run"],"exporter":"pkg","star_sources":[]}.
- module_export_surfaces["pkg"]={"run":"pkg.provider.run"}; re-export map contains pkg.run -> pkg.provider.run.
- Provider artifact consumers include consumer and pkg.__init__; consumer api_imports relation exists.
- No synthetic pkg.__init__::run artifact was observed.
- Call relation: called_by=[]; called_by_ambiguous=["consumer"].

PACKAGE_REEXPORT_PROVIDER=PARTIAL
INFERENCE: Re-export origin and API import resolve to provider. The direct call appears only in the ambiguous projection; this alone does not prove a broader provider re-export defect.

## DIRECT_PACKAGE_LOCAL_IMPORT

CONTRACT_PROVED: Separate fixture imported package-local PUBLIC by from pkg import PUBLIC. Failure to bind it to the package-local canonical artifact means the gap extends beyond star import.

DIRECT_EVIDENCE: pkg.__init__::PUBLIC existed with empty consumers/channels. Consumer usage contained imports=["pkg","pkg.PUBLIC"] and reference evidence targeted pkg.PUBLIC on api_imports.

DIRECT_PACKAGE_LOCAL_IMPORT=FAIL

## FULL_CODE_PATH

CODE_PATH_PROVED:
1. symbol_engine/indexer.py::_process_single_file maps initializer path to pkg.__init__.
2. shared.py::_export_module_name maps it to exporter pkg.
3. shared.py::_extract_reexport_facts creates binding targets such as pkg.PUBLIC and records literal __all__ facts.
4. _assemble_module_export_surfaces and RepositoryReferenceIndex.from_compact_facts assemble export surfaces and explicit-all module keys from indexed module facts.
5. Consumer star source is pkg; its public surface target is pkg.PUBLIC.
6. build_symbol_references tries to resolve that external dotted spelling through the canonical reference index.
7. Canonical package-local artifact target retains definer pkg.__init__.

DIRECT_EVIDENCE:
- MODULE_ID=pkg.__init__
- EXPORTER=pkg
- SURFACE_LOCAL_NAME=PUBLIC
- SURFACE_TARGET=pkg.PUBLIC
- REFERENCE_SYMBOL=pkg.__init__.PUBLIC
- CANONICAL_TARGET=pkg.__init__::PUBLIC
- EXPLICIT_ALL_MODULE_KEY=pkg.__init__
- METADATA_COMPARE_SYMBOL=pkg.__init__.__all__
- CANONICAL_ALL_TARGET=pkg.__init__::__all__

INFERENCE: Producer and consumer projections use external pkg.PUBLIC and canonical pkg.__init__::PUBLIC for the same package-local symbol; full results show they are not bridged for direct package-local consumption.

## LIVE_PARITY

DIRECT_EVIDENCE: Hydrated engine used normal engine.update_file(pkg/__init__.py) updates with fresh full oracles after each transition. Compared families: modules, reexport_facts_by_module, artifact_consumption, artifact_consumption_state.
- LIVE_PACKAGE_STAR_EXPLICIT_PARITY=PASS
- LIVE_PACKAGE_STAR_EMPTY_PARITY=PASS
- LIVE_PACKAGE_STAR_IMPLICIT_PARITY=PASS
- Transitions: __all__=["PUBLIC"] → __all__=[] → no __all__.
- For empty and no-all updates, shadow and execution recompute module tuples were both empty.

INFERENCE: Each parity PASS is structural parity only: both full and incremental states contain the same missing semantic consumer edges.

## INCREMENTAL_RESOLUTION_TRACE

DIRECT_EVIDENCE:
- STAR_SOURCE=pkg
- MODULE_EXPORT_SURFACE={"PUBLIC":"pkg.PUBLIC"}
- SURFACE_DOTTED_TARGET=pkg.PUBLIC
- AFTER_REEXPORT_RESOLUTION=pkg.PUBLIC
- EXPECTED_CANONICAL_TARGETS=["pkg.__init__::PUBLIC","pkg.__init__::_PRIVATE","pkg.__init__::__all__"]
- DOTTED_TARGET_INDEX_KEYS=["pkg.__init__.PUBLIC","pkg.__init__._PRIVATE","pkg.__init__.__all__"]
- RESOLVED_CANONICAL_TARGET_KEYS=([], "unresolved")
- METADATA_DOTTED_REQUEST=pkg.__all__
- RESOLVED_ALL_TARGET=([], "unresolved")
- Metadata facts key: pkg.__init__; external metadata spelling: pkg.__all__.
- Full metadata compare symbol: pkg.__init__.__all__; canonical target: pkg.__init__::__all__.

## PACKAGE_INIT_IDENTITY_GAP

PACKAGE_INIT_IDENTITY_GAP=GENERAL_PACKAGE_LOCAL_IMPORT_IDENTITY

DIRECT_EVIDENCE: Full star import and separate named package import both failed to attach the consumer to pkg.__init__::PUBLIC.
INFERENCE: This is the broadest demonstrated category. Provider re-export API origin resolved to pkg.provider::run, so evidence does not establish BROADER_REEXPORT_IDENTITY.

READY_FOR_DESIGN=YES

## EVIDENCE_BOUNDARIES

CONTRACT_PROVED: Semantic expectations are the Python-static contract supplied for these fixtures.
DIRECT_EVIDENCE: Full analyses ran only on temporary fixture directories. No full analysis of the actual repository and no pytest suite were run.
CODE_PATH_PROVED: Contextor source/lineage evidence traced indexing, re-export, reference, canonical artifact, and incremental paths.
UNKNOWN:
- Dynamic or non-literal __all__ behavior was not tested.
- Runtime Python import behavior beyond these static fixtures was not tested.
- The ambiguous direct-call projection for the provider re-export was not investigated further.

## FILES_CHANGED

FILES_CHANGED=NONE
DIFFS=NONE
