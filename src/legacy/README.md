# `src.legacy` Package

The modules in this namespace are **frozen snapshots** of deprecated implementations that have been superseded by refactored components elsewhere in `src/`.

They remain in the repository primarily to:

1. Provide historical context for architectural decisions.
2. Allow researchers to reproduce earlier benchmarks published alongside the project.

No active code depends on `src.legacy` (verified by automated grep across `src/` and `tests/`).  If you need functionality that appears here, please port it to a maintained module rather than importing it directly. 