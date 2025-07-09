# CONTRIBUTING

## Code Style & Linting

This project enforces code style and quality using Black, isort, Flake8 (with docstring and annotation checks), yamllint, markdownlint, and import-linter.

### Local Pre-commit Hooks

We use [pre-commit](https://pre-commit.com/) to provide fast feedback before you push code.

**Setup:**

```bash
pip install pre-commit
pre-commit install
```

This will automatically run formatters and linters on changed files before each commit.

**To run all hooks on all files:**

```bash
pre-commit run --all-files
```

### Manual Linting/Formatting

- **Black:** `black src/ tests/ scripts/`
- **isort:** `isort src/ tests/ scripts/`
- **Flake8:** `flake8 src/ tests/ scripts/`
- **Yamllint:** `yamllint .`
- **Markdownlint:** `markdownlint *.md docs/`
- **Import-linter:** `lint-imports --config importlinter.ini`

### Architectural Boundaries

We use [import-linter](https://import-linter.readthedocs.io/) to enforce architectural boundaries. For example:
- `control` and `planning` modules **cannot import** from `hardware`.
- See `importlinter.ini` for all contracts.

### Docstring & Type Annotation Checks

- **Docstrings:** Enforced via `flake8-docstrings`.
- **Type Annotations:** Enforced via `flake8-annotations`.

## CI/CD

All linters and formatters are also run in CI. Please ensure your code passes all checks locally before pushing.
