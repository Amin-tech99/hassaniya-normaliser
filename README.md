# Hassaniya Arabic Text Normalizer

Python package for normalizing Hassaniya Arabic text using variant mapping and
letter-level rules.

## What This Project Does

- Normalizes known dialect variants to canonical forms.
- Applies letter rules in a deterministic order.
- Supports exception words that must not be transformed.
- Supports link fix mappings for known tokenization and linking issues.
- Includes a CLI for batch and stream processing.
- Includes a local web UI for paste-and-review workflows.

## Install

```bash
git clone https://github.com/Amin-tech99/hassaniya-normaliser.git
cd hassaniya-normaliser
python -m pip install .
```

For development:

```bash
python -m pip install -e ".[dev]"
```

## CLI Usage

Normalize a file:

```bash
hassy-normalize input.txt -o output.txt
```

Normalize from `stdin`:

```bash
cat input.txt | hassy-normalize > output.txt
```

Show inline diff for changes:

```bash
hassy-normalize input.txt --diff --color
```

## Local Web UI

Run local UI server:

```bash
hassy-normalize-ui --host 127.0.0.1 --port 8765
```

Then open:

```text
http://127.0.0.1:8765
```

UI features:

- Paste text and normalize instantly.
- Highlight changed words in the normalized output.
- Show change statistics (changed words, total words, percentage).

## Python Usage

```python
from hassy_normalizer import get_stats, normalize_text, normalize_word

text = "sample text"
print(normalize_text(text))
print(normalize_word("sample"))
print(get_stats())
```

## Rule Pipeline

Normalization order:

1. De-elongation (collapse noisy 3+ repeated Arabic letters)
2. Link fixes from `linked_words.json`
3. Variant lookup from `hassaniya_variants.jsonl`
4. Letter rules from `rules.py` (with exceptions in `exception_words_g_q.json`)

## Project Layout

```text
src/hassy_normalizer/
  __init__.py
  cli.py
  data_loader.py
  diff.py
  normalizer.py
  rules.py
  web_ui/
  data/
scripts/
  validate_data.py
tests/
```

## Development

Run tests:

```bash
pytest
```

Validate data files:

```bash
python scripts/validate_data.py
```

Lint and format:

```bash
ruff check src tests
black src tests
```

## Open Source Docs

- Contribution guide: [CONTRIBUTING.md](CONTRIBUTING.md)
- Code of conduct: [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)
- Security policy: [SECURITY.md](SECURITY.md)

## License

MIT. See [LICENSE](LICENSE).
