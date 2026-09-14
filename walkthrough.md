# P0_LINEAGE_ORACLE_SEMANTIC_DIFF

## STATUS

SUCCESS — audit only. Production, tests and oracle hashes were not changed.

## FOCUSED_PYTEST

`..venv\Scripts\python.exe -m pytest -q -vv tests\analysis\test_lineage_extraction_equivalence.py::test_lineage_extraction_equivalence_oracle tests\analysis\test_lineage_extraction_equivalence.py::test_lineage_extraction_surface_delta_preserves_legacy_anchors_and_flows`

Result: `2 failed in 1.02s`.

Both tests fail. Raw full-hash mismatch cases are identical for both oracles:

- `async_yield`
- `comprehension_runtime_walrus`
- `if_for_frame_merge`
- `imports_alias_wildcard`
- `relative_import`
- `signature_defaults_local_call`
- `try_except_finally_match`

`resource_limit` matches both stored oracles unchanged.

## RAW_MISMATCH_CASES

| Case | Full oracle current | Full oracle expected | Legacy anchor/flow current | Legacy expected |
|---|---|---|---|---|
| `signature_defaults_local_call` | `514593c03cb9b3dda00b0e2289a15781b7a7b2e131a89cb6e2f3e2fb2ad09d3c` | `97a3964dd7208f83b8200c12e7732e685ffde29f79ca7a1c001c69b2989a0122` | `c7ff95a059aeeb7c5a3dc978f6a982fda491029286e0eeb8abe937fea4a2dfb5` | `4d6984e8211918d2e84e976d5fda32f59aed9247d52821cafc688242c6f6533b` |
| `imports_alias_wildcard` | `ad52d65bb4140b3e8ea6f21781c68e749f240358b5683e8648199972db597682` | `7fbd16baf177be5d965c212678763b9a123978e62ba711950602fab6bf9ccec8` | `ad52d65bb4140b3e8ea6f21781c68e749f240358b5683e8648199972db597682` | `7fbd16baf177be5d965c212678763b9a123978e62ba711950602fab6bf9ccec8` |
| `if_for_frame_merge` | `b12603da08418eef897fe090bc05a7783fd877ed6c2bfb5a1bfdcd20c7cdc305` | `f27318c046fcadc2946c58e2e56f324b8a01fb563bd627ec7f85319c2b435b7a` | `b12603da08418eef897fe090bc05a7783fd877ed6c2bfb5a1bfdcd20c7cdc305` | `f27318c046fcadc2946c58e2e56f324b8a01fb563bd627ec7f85319c2b435b7a` |
| `try_except_finally_match` | `a1384557b901a8f8634f06da6e36c4df91007699f69b24a71d59c1b81da00299` | `ce25c00652779c30e47b06499408efe78515eda802cdd88aa2650fda6757c60f` | `a1384557b901a8f8634f06da6e36c4df91007699f69b24a71d59c1b81da00299` | `ce25c00652779c30e47b06499408efe78515eda802cdd88aa2650fda6757c60f` |
| `comprehension_runtime_walrus` | `efbd682411093e174775282b2ce9d7012106d09c5180d73f5fbdd54ec45a2a6e` | `35f7e091b7361051933afa6ae125eabb35b0e46776960955d1d45b0826d531e9` | `efbd682411093e174775282b2ce9d7012106d09c5180d73f5fbdd54ec45a2a6e` | `35f7e091b7361051933afa6ae125eabb35b0e46776960955d1d45b0826d531e9` |
| `async_yield` | `e6c709d1a5ef347b04ed888dd9fa055dbc5a24c33eb14ea1a489b60a15c7d731` | `57fe7c8ab6b6468031df1a70efa1d66320485207edf99912959977059166dab7` | `49eaf024dbbea341d333f1e705037be68c0fce45c6acaed23ad93a850d381016` | `110cd0c1d520261bffe673d6e0f1df573b68ed4653be674bcb762faacdf27bf9` |
| `relative_import` | `10ee12f15c6cfc5ecb82511e18081534eb68b9e647ae0ec3d71f3611e510fb2e` | `44e82ef594399306de449f12a46d3c8bf463d47050f454537f5c2630f976ca95` | `10ee12f15c6cfc5ecb82511e18081534eb68b9e647ae0ec3d71f3611e510fb2e` | `44e82ef594399306de449f12a46d3c8bf463d47050f454537f5c2630f976ca95` |

## OWNER_STRIPPED_COMPARISON

The requested normalization recursively removes exactly the dict key `owner_local_id` and nothing else. It does **not** reproduce either oracle for any failing case. This does not expose a non-owner current semantic diff: it removes legacy `anchors[*].owner_local_id` too, and that field already existed in the historical structure hashed by the stored oracle.

| Case | Full owner-stripped hash | Full expected | Legacy owner-stripped hash | Legacy expected |
|---|---|---|---|---|
| `signature_defaults_local_call` | `b78fb7130c34aa7eb1fe115d133af71d7c80f17788571c0b39c592783b04faca` | `97a3964dd7208f83b8200c12e7732e685ffde29f79ca7a1c001c69b2989a0122` | `17e62d2e9506a69d24ea0498c032e2510835d395136b742dd3a5a1fedc04d531` | `4d6984e8211918d2e84e976d5fda32f59aed9247d52821cafc688242c6f6533b` |
| `imports_alias_wildcard` | `d23c6a8a704320a5f873f5d6598265ff1f409b6f204dec9ece1cc715df4ecdbc` | `7fbd16baf177be5d965c212678763b9a123978e62ba711950602fab6bf9ccec8` | `d23c6a8a704320a5f873f5d6598265ff1f409b6f204dec9ece1cc715df4ecdbc` | `7fbd16baf177be5d965c212678763b9a123978e62ba711950602fab6bf9ccec8` |
| `if_for_frame_merge` | `5e6a214cc79387bc79043983cb58a42e5fad6ec9e9bb4a30cbce806fcc35a0ae` | `f27318c046fcadc2946c58e2e56f324b8a01fb563bd627ec7f85319c2b435b7a` | `5e6a214cc79387bc79043983cb58a42e5fad6ec9e9bb4a30cbce806fcc35a0ae` | `f27318c046fcadc2946c58e2e56f324b8a01fb563bd627ec7f85319c2b435b7a` |
| `try_except_finally_match` | `b93a0dce4a5ab9da30b0e8d66df58245ccc89337047caf733d037db8a3872da0` | `ce25c00652779c30e47b06499408efe78515eda802cdd88aa2650fda6757c60f` | `b93a0dce4a5ab9da30b0e8d66df58245ccc89337047caf733d037db8a3872da0` | `ce25c00652779c30e47b06499408efe78515eda802cdd88aa2650fda6757c60f` |
| `comprehension_runtime_walrus` | `d8bdcc046d2efa08cafd4610a7bea01dc8f6ed28fd3cdf2621700633fb028ca3` | `35f7e091b7361051933afa6ae125eabb35b0e46776960955d1d45b0826d531e9` | `d8bdcc046d2efa08cafd4610a7bea01dc8f6ed28fd3cdf2621700633fb028ca3` | `35f7e091b7361051933afa6ae125eabb35b0e46776960955d1d45b0826d531e9` |
| `async_yield` | `e3a4de426bb1da3392b03131a3dfe6e7460bb2150d401337c536e501eaef8b25` | `57fe7c8ab6b6468031df1a70efa1d66320485207edf99912959977059166dab7` | `c11b6214d59d62ad64d883d47464cc562e1ebd928d66f5d92fc902b0ba1532f3` | `110cd0c1d520261bffe673d6e0f1df573b68ed4653be674bcb762faacdf27bf9` |
| `relative_import` | `8142d99c7a04addc97d55ddffac874fe30cda8300cbd8c04d8a8546f96867a70` | `44e82ef594399306de449f12a46d3c8bf463d47050f454537f5c2630f976ca95` | `8142d99c7a04addc97d55ddffac874fe30cda8300cbd8c04d8a8546f96867a70` | `44e82ef594399306de449f12a46d3c8bf463d47050f454537f5c2630f976ca95` |

`resource_limit` has no owner field and remains identical in full and stripped forms: `40c592a9bfb86c5f6d4fe747fa2714a92794dafbc204e601ea4b475c07e06adb` for both oracles.

## SEMANTIC_DIFF

The stored values were reproduced exactly from historical revision `3ca8555^`; therefore its canonical JSON is the recoverable expected structure. Bieżący-vs-historyczny literal structural diff has zero non-owner paths in every corpus case.

| Case | Added paths |
|---|---|
| `signature_defaults_local_call` | 19 × `$.flows[*].owner_local_id` |
| `imports_alias_wildcard` | 3 × `$.flows[*].owner_local_id` |
| `if_for_frame_merge` | 5 × `$.flows[*].owner_local_id` |
| `try_except_finally_match` | 7 × `$.flows[*].owner_local_id` |
| `comprehension_runtime_walrus` | 9 × `$.flows[*].owner_local_id` |
| `async_yield` | 7 × `$.flows[*].owner_local_id` |
| `relative_import` | 2 × `$.flows[*].owner_local_id` |
| `resource_limit` | none |

For every listed path: `expected/history = <MISSING>` and `current = owning anchor local id`. Examples: `async_yield` flows point to `occ:v1:async_function:0:i:0:n:worker`; module-scope flows point to `occ:v1:module:root:i:0:n:-`; function-scope flows point to their function anchor. No endpoint, span, relation, resolution kind, confidence, surface, status, fingerprint, ordering, or non-owner field differs.

## PROVENANCE

- Commit `3ca8555dd89bb406bce73e24a42336dded7b0fd6` (2026-09-13) added `ExtractedFlowFact.owner_local_id` and propagated an owner argument through flow emission. Its diff also introduced `SourceLineageManifest.flow_ownership_materialized` and the materialized-slice completeness check: this is intentional canonical lineage ownership materialization, not an incidental serializer change.
- Current production confirms this wiring: `contextor/core/analysis/lineage_extraction_emit.py:34-62` requires `owner_local_id` in `emit_flow` and stores it on `ExtractedFlowFact`; binding, signature/default and visitor call paths pass their lexical owner. `contextor/core/domain/lineage_facts.py:268-285` defines and validates the flow field; `:439-455` and `:556-559` model/enforce flow ownership materialization.
- `ExtractedAnchorFact.owner_local_id` predates this flow-ownership change. It is present in the historical canonical structure and is emitted in current code at `lineage_extraction_emit.py:16`. Hence deleting every key named `owner_local_id` also deletes expected, pre-existing anchor ownership and necessarily invalidates the requested stripped-hash equality.
- The stored expected hashes themselves were introduced for surface-aware full results by commit `4787a229314cfd64b9055155d7ba24f7435752db` (2026-09-10). The historical `3ca8555^` execution matches all of them exactly, including the two specialized legacy anchor/flow values.

## DECISION

ADDITIONAL_INTENTIONAL_SEMANTIC_CHANGE

Strict `OWNER_ONLY_INTENTIONAL` is not permitted by the supplied rule because the prescribed recursive removal does not produce the old hashes: it removes historical anchor ownership as well as newly-added flow ownership. The remaining mismatch is nonetheless fully explained and historically verified: the only actual current-vs-expected structural addition is intentional `ExtractedFlowFact.owner_local_id` ownership materialization; there is no unexplained non-owner regression.

## FILES_CHANGED

NONE

## DIFFS

NONE
