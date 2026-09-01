# 0L3A Jaccard and registry residual discovery

Discovery only; production/test code unchanged. No pytest, py_compile, or broad profiling was run.

## Domain reconciliation

Canonical state, primary `contextor`, and production source each contain 199 modules. `tests` contains 125 Python modules and is excluded from this production-layer canonical state. Thus 199/199 is 100% of the canonical production domain, not all repository Python files. Jaccard primary input is layer-produced artifact consumer data; global-primary equivalence was not proven merely from module coverage.

## Jaccard contract and repeated-work audit

`graph_analytics.build_jaccard_clusters` reads `artifact_data['artifacts']`, calls `_artifact_consumers` once for each artifact, builds `module -> artifact-id set`, then compares every sorted module pair with `_jaccard` and complete-linkage assembly. `_artifact_consumers` is an artifact-local `consumers` field lookup, filtering invalid/empty values, set construction, and deterministic sorting. It does not scan artifact data or perform a reverse-index lookup.

The 0L3 primary profile showed 55,776 `_artifact_consumers` calls and 55,776 artifact traversal iterations. Each lookup is keyed by a distinct artifact iteration; no same `(artifact, input-domain)` lookup is repeated inside this function. Consequently a local artifact-to-consumers preindex would reproduce a one-use set, not remove repeated work. The accepted global 0J5 handoff is a global shared-cluster result; layer path uses layer report artifact input and layer output semantics. Equality of module domain alone does not prove equal artifact domain, filters, thresholds, cluster output, or ordering. Global result reuse is therefore NOT_PROVEN.

## Registry accounting

`_initialize_repository_identity` constructs one `PersistentIdentityRegistry` instance, whose constructor recovers and loads all seven registry JSON files. The same instance enters `registry.transaction()` during compact/slice work. Transaction deliberately locks, recovers and calls `_load_all()` again before yielding, then atomically writes the registry state. The 0L3 near-constant primary/control cost is therefore explained by one instance with two semantic loads, not two independently constructed registries. The second load occurs inside the ownership/locking freshness boundary; reusing pre-lock memory would weaken transaction isolation/currentness. No safe run-scoped reuse is proven.

## Decision

The measured Jaccard work is required artifact-domain analytics, but repeated identical consumer-set rebuilding is not present. Registry reloading is deliberate transaction freshness. Neither meets the stated safe-removal bar.

CANONICAL_STATE_MODULE_COUNT=199
PRIMARY_LAYER_MODULE_COUNT=199
GLOBAL_JACCARD_INPUT_MODULE_COUNT=NOT_PROVEN
PRIMARY_JACCARD_INPUT_MODULE_COUNT=199
GLOBAL_PRIMARY_JACCARD_EQUIVALENCE=NOT_PROVEN
ARTIFACT_CONSUMERS_CALL_COUNT_PRIMARY=55776
UNIQUE_ARTIFACT_CONSUMER_LOOKUPS_PRIMARY=55776
REPEATED_IDENTICAL_CONSUMER_LOOKUPS_PRIMARY=0
ARTIFACT_CONSUMER_REBUILD_MEDIAN_MS=NOT_SEPARATELY_MEASURED_SINGLE_USE
LOCAL_CONSUMER_PREINDEX_SAFE=NO
LOCAL_CONSUMER_PREINDEX_EXPECTED_SAVING_MS=NONE
REGISTRY_LOAD_CALL_COUNT=2
SAME_REGISTRY_RELOADED_IN_RUN=YES
REGISTRY_REUSE_EXPECTED_SAVING_MS=NONE
TOP_LAYER_CANDIDATE=NONE
TOP_LAYER_EXPECTED_SAVING_MS=NONE
SECOND_LAYER_CANDIDATE=NONE
NEXT_TARGET=STOP_LAYER_PERFORMANCE_SERIES
FILES_CHANGED=NONE
DIFFS=NONE
WHY=199 modules is the complete production canonical domain; Jaccard consumer normalization is one-use per artifact and global semantic equivalence is not proven. The registry reload is the same instance's required under-lock transaction freshness reload, so neither residual owner offers a safe reusable duplicate.
