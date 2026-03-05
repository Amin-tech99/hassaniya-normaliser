# Contributing

Thanks for contributing to `hassy-normalizer`.

## Development Setup

1. Fork and clone the repository.
2. Install development dependencies:

```bash
python -m pip install -e ".[dev]"
```

## Before You Open a PR

Run these checks locally:

```bash
pytest
python scripts/validate_data.py
ruff check src tests
black src tests
```

## Contribution Scope

Useful contributions include:

- New or improved Hassaniya variant mappings.
- Better exception-word coverage.
- Rule improvements with tests.
- Documentation and examples.

## Pull Request Guidelines

- Keep PRs focused and small when possible.
- Add or update tests for behavior changes.
- Explain the linguistic reasoning for mapping/rule changes.
- Update docs when CLI or API behavior changes.

## Data Changes

If you edit files in `src/hassy_normalizer/data/`:

- Keep JSON and JSONL formats valid.
- Avoid duplicate or contradictory mappings.
- Run `python scripts/validate_data.py` before submitting.
