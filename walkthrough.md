# CONTEXTOR_B0G2C2_COMPLETE_CANONICAL_DIFF_INVENTORY

## FILES_CHANGED

- `C:\Temp\Contextor_Repo\walkthrough.md` (report only). No production, test, snapshot or auxiliary inventory files changed.

## ACTUAL_DIFF

`ACTUAL_DIFF=DIFFS=NONE` for source/test/docs. This report replaces the prior walkthrough. The complete 12-leaf inventory fits below, so no separate machine-readable inventory was needed.

## CURRENT_SOURCE_IDENTITY

- HEAD: `cfceaded06df8b2fbabcc5feee9b43c4e207122c`. Before report write, `git status --porcelain=v1 --untracked-files=all` was empty and `git diff --check` passed.
- Contextor complete implementation retrieval with `workspace_sync=verified` at LIVE revision 356: `generate_summary_report` in `C:\Temp\Contextor_Repo\contextor\core\reporting_engine\summary_generator.py:128-202`; `build_report_header` in `C:\Temp\Contextor_Repo\contextor\core\reporting_engine\header.py:4-21`; `_project` and `_state_projection` in `C:\Temp\Contextor_Repo\tests\test_desktop_mcp_canonical_parity.py:99-179,405-411`.
- Contextor exact source ranges: `C:\Temp\Contextor_Repo\contextor\core\reporting_engine\pipeline.py:180-210,635-700`; `C:\Temp\Contextor_Repo\contextor\core\api\facade.py:975-1010`; parity test capture/assertion at lines 330-433,515-620. No retrieved complete symbol was truncated. `search_source(generated_at, limit=null, allow_large_output=true)`: 26/26 matches, untruncated.

## PRESERVED_SNAPSHOT_IDENTITY

| Capture | Preserved file | SHA-256 | Metadata |
|---|---|---|---|
| Desktop | `C:\Users\DafoO\AppData\Local\Temp\pytest-of-DafoO\pytest-550\test_real_desktop_and_mcp_full0\b0g2c_canonical_mismatch_evidence\desktop.pickle` | `4EB93D63A9C2F9E68DE5CB3B11BF04BE8857CD75AC238CD3EF3FE18128542402` | schema 1.4, writer desktop, revision 1, state_id `20261012_120948` |
| MCP | `C:\Users\DafoO\AppData\Local\Temp\pytest-of-DafoO\pytest-550\test_real_desktop_and_mcp_full0\b0g2c_canonical_mismatch_evidence\mcp.pickle` | `B0F8F710C5D11EDC83290A3306F442637E33B76DB605FCD9E1A0B16813E58923` | schema 1.4, writer mcp, revision 2, state_id `20261012_120950` |

Both captures have repo_id `ctx_1a8534b9` and root `C:\Users\DafoO\AppData\Local\Temp\pytest-of-DafoO\pytest-550\test_real_desktop_and_mcp_full0\b0g2c_repo_b6b4c0319f054dc3920d4ab94af235a6`. Each referenced versioned state, FileState and lineage manifest file exists.

## OFFLINE_COMPARISON_METHOD

DIRECT_EVIDENCE: Used repository `.venv` Python to load only the two preserved pickles; imported the existing parity test's lossless `_project` without invoking pytest or a test function. Applied it separately to all 36 declared `RepositoryAnalysisState` fields, FileState map, FileState JSON payload, source byte map, every snapshot metadata field, and the three extra state attributes `revision/state_id/provenance`. A one-time in-memory recursive walker compared complete tagged projections, preserved mapping keys by their full projected identity and sequence indices, and listed every unequal leaf. No field was excluded, ordered sequence sorted, comparator edited, or file written. The initial walker attempt accessed nonexistent `state.resync_required` and stopped with AttributeError before comparison; corrected read used the parity test's `getattr(..., False)` contract.

## COMPLETE_DIFF_COUNT

`12` differing projected leaves: two among the 36 canonical fields and ten in separately checked generation/identity metadata. No missing keys, fields, indices, or set elements. Every path and value is listed below.

## DIFF_COUNTS_BY_CANONICAL_FAMILY

| Family | Leaves | Result |
|---|---:|---|
| `state.layer_information` | 2 | PROVED_OPERATIONAL_METADATA |
| Other 35 declared canonical fields, including modules, hard/soft graph, references, consumers, lineage, metrics, analytics, freshness, cycles, trie | 0 | EQUAL |
| `file_states` | 0 | EQUAL |
| `file_state_payload` | 2 | Expected generation metadata |
| `source_bytes` | 0 | EQUAL |
| Extra state attributes | 2 | Expected generation identity |
| Snapshot metadata | 6 | Expected writer/generation identity |

## OPERATIONAL_METADATA_DIFFERENCES

| Exact logical path | Desktop | MCP | Classification |
|---|---|---|---|
| `state.layer_information['summary_data']['generated_at']` | `2026-10-12T12:09:48.838009` | `2026-10-12T12:09:50.608340` | PROVED_OPERATIONAL_METADATA |
| `state.layer_information['summary_data']['report_header']['generated_at']` | `2026-10-12T12:09:48.623010` | `2026-10-12T12:09:50.357250` | PROVED_OPERATIONAL_METADATA |

Both projected leaf paths end in `.value`; that tag is the projection representation, not a canonical field. Both values are ISO datetime strings. CODE_PATH_PROVED: `pipeline.py:190-206` builds header, then summary; `summary_generator.py:170,184-185` assigns summary timestamp and embeds header; `pipeline.py:647-648,693-697` returns them; `facade.py:993-999` stores summary in canonical `layer_information`. The timestamps are assigned after graph/metric inputs have been computed. Contextor's complete 26-match source search found timestamp use for report metadata/display and copying to layer reports (`layer_slicer.py:299,315-316`), with no observed edge, lineage, consumer, freshness, or identity decision using these exact timestamps. This supports only exact path-level nonsemantic classification, not a blanket `generated_at` exemption.

## SEMANTIC_CANONICAL_DIFFERENCES

None in this preserved pair. All other declared state fields, including graph and reference details, compare equal under the lossless projection. This is an offline pairwise finding, not a claim about every future run.

## ORDERING_NONDETERMINISM_DIFFERENCES

None. Every sequence was compared by index. The earlier `direct_calls_detail` order mismatch is absent from both preserved captures.

## PERSISTENCE_IDENTITY_DIFFERENCES

These ten differences are expected for independent persisted generations. They are **not** canonical-field metadata exemptions; strict per-generation linkage is required.

| Exact projected leaf path | Desktop | MCP |
|---|---|---|
| `file_state_payload['_meta']['revision'].value` | `1` | `2` |
| `file_state_payload['_meta']['state_id'].value` | `20261012_120948` | `20261012_120950` |
| `state_meta.revision.value` | `1` | `2` |
| `state_meta.state_id.value` | `20261012_120948` | `20261012_120950` |
| `metadata.revision.value` | `1` | `2` |
| `metadata.state_id.value` | `20261012_120948` | `20261012_120950` |
| `metadata.writer.value` | `desktop` | `mcp` |
| `metadata.state_file.value` | `engine_state.r1.652c9babc5df4396a3025189b9ffa850.pkl` | `engine_state.r2.66c3c60e18e9426686def25eb8c0ec34.pkl` |
| `metadata.file_state_file.value` | `file_state.r1.652c9babc5df4396a3025189b9ffa850.json` | `file_state.r2.66c3c60e18e9426686def25eb8c0ec34.json` |
| `metadata.lineage_manifest_file.value` | `lineage_manifest.r1.652c9babc5df4396a3025189b9ffa850.json` | `lineage_manifest.r2.66c3c60e18e9426686def25eb8c0ec34.json` |

CONTRACT_PROVED on the captures: each has equal revision across state/metadata/FileState `_meta`, equal state_id across those same three, and MCP revision equals Desktop revision plus one. Repo ID, root, schema, state provenance `snapshot`, five FileState records, and all five source byte contents are equal across captures. Each FileState SHA-256 matches captured source bytes. FileState payload excluding `_meta` is equal. Both captures report `resync_required=False` through the test's `getattr` contract.

## UNRESOLVED_DIFFERENCES

None for this preserved pair. UNKNOWN: a historical two-run comparison cannot prove general future determinism. No new full analysis was allowed.

## SUMMARY_GENERATED_AT_PROVENANCE

`C:\Temp\Contextor_Repo\contextor\core\reporting_engine\summary_generator.py:128-202`: complete Contextor implementation, workspace sync verified. At line 170, `generate_summary_report` sets `"generated_at": datetime.now().isoformat()` independently of its inputs. It is report generation time, not source hash, canonical revision, or graph fact. `C:\Temp\Contextor_Repo\contextor\core\reporting_engine\pipeline.py:199-206` calls it; `C:\Temp\Contextor_Repo\contextor\core\api\facade.py:997` stores result in canonical state.

## REPORT_HEADER_GENERATED_AT_PROVENANCE

`C:\Temp\Contextor_Repo\contextor\core\reporting_engine\header.py:4-21`: complete Contextor implementation, workspace sync verified. At line 10, `build_report_header` independently sets `"generated_at": datetime.now().isoformat()` before optional Git branch/commit lookup. `pipeline.py:190-206` passes it to summary generator, which embeds it at `summary_generator.py:184-185`. This timestamp is independent of the summary timestamp.

## PROPOSED_EXACT_METADATA_ALLOWLIST

Evidence supports only these logical paths for the auditor's later comparator decision:

1. `RepositoryAnalysisState.layer_information['summary_data']['generated_at']`
2. `RepositoryAnalysisState.layer_information['summary_data']['report_header']['generated_at']`

Retain type/format validation. No wildcard timestamp exemption, blanket layer/report exclusion, or ordered-sequence sorting is supported. This report does not modify the comparator.

## REQUIRED_COMPARATOR_ASSERTIONS

Retain exact structural equality for all other declared canonical fields and full mapping/sequence identity. Separately retain revision progression; state_id/revision linkage across state, metadata and FileState payload; expected writer; repository ID/root/schema; provenance; resync state; versioned generation file presence; full FileState equality; and source-byte SHA-256 linkage. Existing capture and identity code in `C:\Temp\Contextor_Repo\tests\test_desktop_mcp_canonical_parity.py:330-411,515-620` already asserts these before first-difference comparison.

## LIVE_REVISION_BEFORE_AFTER

356 before, 356 after. Contextor `get_live_events(after_revision=356)` returned `continuity=continuous`, no events and `resync_required=false` on both observations. No analysis or mutation was invoked.

## WORKSPACE_SYNC_POSTCHECK

`verified` for current fetched summary, header and comparator symbols at revision 356. Exact pipeline/facade ranges came from Contextor and matched clean workspace source. `get_source_range` itself has no freshness envelope. No source used as complete symbol evidence was a preview/truncated response.

## RESYNC_REQUIRED

Current Contextor_Repo LIVE: false. Historical isolated captures: false via the parity test's `getattr` contract. These are distinct repositories/states.

## RESTART_REQUIRED

No. No production/test source changed.

## FINAL_VERDICT

`B0G2C2_ONLY_OPERATIONAL_METADATA_DIFFERENCES` within the 36 declared canonical fields. Ten other differences are expected and strictly linkable generation/identity metadata. Semantic canonical differences: 0. Ordering nondeterminism differences: 0. Unresolved differences in preserved pair: 0.

STOP. Await `proceduj`.
