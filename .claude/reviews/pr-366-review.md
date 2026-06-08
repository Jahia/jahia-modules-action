# PR Review: #366 — fix(integration-tests): upgrade ncc and automate signal patch

**Reviewed**: 2026-05-27
**Author**: Fgerthoffert
**Branch**: fix/integration-tests-build-pipeline → main
**Decision**: APPROVE with comments

## Summary

Well-structured PR that addresses two documented pain points (OpenSSL legacy provider requirement and manual signal patching). The approach is sound — upgrading ncc to eliminate the crypto issue and automating the post-build patch with proper idempotency. The CI check adds a safety net.

## Findings

### CRITICAL
None

### HIGH
None

### MEDIUM

1. **Pattern compliance: `actions/checkout` not SHA-pinned** (`.github/workflows/on-code-change.yml:14`)
   - All other workflows in this repo pin actions to commit SHAs (e.g., `actions/checkout@de0fac2e4500dabe0009e67214ff5f5447ce83dd #v6.0.2`)
   - Using `@v4` is less secure (tag can be moved) and inconsistent with repo conventions
   - **Suggestion**: Pin to SHA like the rest of the repo, and use the same version (v6.0.2)

### LOW

1. **Fragility of `grep -A 10` in CI check** (`.github/workflows/on-code-change.yml:19`)
   - If the `_getSpawnOptions` method structure changes (e.g., more lines added before `result.signal`), the 10-line window might miss it
   - Acceptable for now given the bundled output is deterministic, but could use a wider window (e.g., `-A 20`) for resilience

2. **`String.replace()` replaces only first occurrence** (`integration-tests/scripts/patch-signal.js:35`)
   - Not a bug — there is exactly one `_getSpawnOptions` in the bundled output — but worth documenting with a comment if the pattern could appear elsewhere in future

## Validation Results

| Check | Result |
|---|---|
| Type check (tsc) | ✅ Pass |
| Lint | ⚠️ Pre-existing errors (not introduced by this PR) |
| Tests | ⚠️ Pre-existing failure (references non-existent `wait.ts` module) |
| Build + Package | ✅ Pass (no openssl-legacy-provider needed) |
| Signal patch applied | ✅ Verified in dist/index.js |
| Audit reduction | ✅ ~40 → 8 advisories (remaining are upstream) |

## Files Reviewed

| File | Change Type | Notes |
|---|---|---|
| `.github/workflows/on-code-change.yml` | Added | CI check for signal patch |
| `integration-tests/README.md` | Modified | Updated build instructions + manual fallback |
| `integration-tests/package.json` | Modified | Dependency upgrades |
| `integration-tests/scripts/patch-signal.js` | Added | Automated signal patching |
| `integration-tests/dist/index.js` | Modified | Rebuilt (generated) |
| `integration-tests/dist/index.js.map` | Modified | Rebuilt (generated) |
| `integration-tests/dist/licenses.txt` | Modified | Rebuilt (generated) |
| `integration-tests/dist/sourcemap-register.js` | Modified | Rebuilt (generated) |
| `integration-tests/yarn.lock` | Modified | Updated lockfile |
