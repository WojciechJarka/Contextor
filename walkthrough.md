# P17-F3-I1-R2 — Windows registry ACL validator

## Findings

- **DIRECT_EVIDENCE:** The candidate owner check was placed inside `for directory in chain`, immediately after obtaining the security descriptor and before `GetSecurityDescriptorDacl()`. The helper rejects `None` and owner SIDs outside the supplied dynamic set.
- **DIRECT_EVIDENCE:** The isolated real-Windows reparse-point probe reported `os.lstat`'s reparse flag, `os.path.abspath` preserving the symlink path, and the `..` component remaining visible. The isolated CPython probe also showed that resolving a symlink removes the symlink status from the resolved path.
- **DIRECT_EVIDENCE:** The candidate implementation and both requested contract test files passed the exact focused run: `33 passed in 159.46s`. A separate AST parse succeeded for both files.
- **DIRECT_EVIDENCE:** A temporary registry directory on the current C: volume was rejected at `C:\` because that root's owner did not match the dynamically computed current-user, SYSTEM, or Builtin Administrators SIDs. No ACL was changed. Under this exact allowlist, the validator cannot accept a path whose ancestor chain includes this C: root.
- **DIRECT_EVIDENCE:** In an isolated temporary tree, a regular directory component was renamed and replaced by a different ordinary directory at the same lexical path. The old and new directories were not the same filesystem object, while `_path_without_reparse_points()` returned equal chains before and after replacement.
- **CODE_PATH_PROVED:** The final validation compares only the tuple of lexical `Path` values. It does not compare filesystem object identities. Therefore it cannot detect the demonstrated ordinary-directory replacement, despite the adjacent comment claiming it detects a path-component replacement already visible at the end. The documented TOCTOU limitation does not make that specific detection claim true. This is the blocking specification defect; no alternative was designed.
- **UNKNOWN:** No production registry path was validated or modified, and the validator was not integrated into production reads.

## Actions and results

- Created the two candidate files exactly from R2 and ran the requested new test plus both existing contract test files. The 33 tests passed.
- Ran isolated Windows filesystem checks and a read-only ACL check on a temporary directory. The latter failed closed at `C:\` due to the explicit owner allowlist.
- After the ordinary-directory replacement check demonstrated the final-check defect, removed the candidate source and test files rather than leaving the blocked implementation in the worktree.
- Contextor MCP was not called: the implementation was stopped at the concrete blocker, and local tests plus isolated Windows API behavior supplied the relevant evidence.
- No production source, existing tests, active registry, committed store, or ACL remains changed.

## FILES_CHANGED

- Source/test/docs: NONE.
- `walkthrough.md` is this requested report and is excluded from source/test/docs diff accounting.

## FULL_DIFFS

`ACTUAL_DIFF=DIFFS=NONE` — both candidate implementation files were removed after the blocker; there are no source/test/docs diffs to deliver.

## Werdykt I1

`BLOCKED_SEMANTIC_INTEGRITY` — the specified final recheck does not detect ordinary directory replacement at the same path. The candidate owner policy also rejects the tested C: path at its root. The implementation was withdrawn; no corrective design was proposed.
