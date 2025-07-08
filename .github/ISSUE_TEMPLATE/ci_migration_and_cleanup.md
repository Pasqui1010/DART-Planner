---
name: CI & Migration Cleanup
about: Consolidate CI workflows and complete DI/config migration
labels: ["tech debt", "ci", "refactor"]
---

# CI Workflow Consolidation & DI/Config Migration Cleanup

## Background
Recent refactors introduced compatibility shims for the DI container and configuration system to unblock development after the migration to `di_container_v2` and `frozen_config`. To ensure long-term maintainability and reduce CI redundancy, we need to:

## Tasks

### 1. CI Workflow Consolidation
- [ ] Merge `fast-checks`, `quality-pipeline`, and other redundant jobs into a single, unified workflow for linting, type-checking, and fast tests.
- [ ] Retain only one comprehensive nightly/weekly suite for slow/integration tests.
- [ ] Remove or archive legacy/duplicate workflows.

### 2. Codebase Migration
- [ ] Refactor all imports to use `di_container_v2` and `frozen_config` directly.
- [ ] Remove all references to the legacy `di_container` and `settings` modules.
- [ ] Delete the compatibility shims after all usages are migrated.

### 3. Documentation
- [ ] Update developer docs to reference only the new DI and config APIs.
- [ ] Add migration notes and deprecation warnings to the changelog.

## Acceptance Criteria
- No code references the legacy DI or config modules.
- CI runs are faster and less redundant.
- All tests pass with shims removed.
- Documentation is up to date. 