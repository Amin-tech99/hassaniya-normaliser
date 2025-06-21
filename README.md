# Hassaniya Arabic Normalizer

[![CI](https://github.com/yourusername/hassaniya-normalizer/workflows/CI/badge.svg)](https://github.com/yourusername/hassaniya-normalizer/actions)
[![PyPI version](https://badge.fury.io/py/hassy-normalizer.svg)](https://badge.fury.io/py/hassy-normalizer)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A robust, production-ready normalizer for Hassaniya Arabic text with both CLI and web interfaces.

## Features

- **🔄 Text Normalization**: Converts Hassaniya Arabic variants to standardized forms
- **📝 CLI Tool**: Command-line interface with diff visualization
- **🌐 Web Interface**: Modern web UI with real-time normalization
- **⚡ High Performance**: Cached operations with thread-safe design
- **🔍 Diff Visualization**: Word-level highlighting of changes
- **📊 Statistics**: Track normalization metrics and unknown variants
- **🛡️ Robust**: Comprehensive error handling and validation
- **🧪 Well Tested**: Extensive test suite with CI/CD

## Quick Start

### Installation

```bash
pip install hassy-normalizer
```

### CLI Usage

```bash
# Normalize a file
hassy-normalize input.txt -o output.txt

# Show diff with colors
hassy-normalize input.txt --diff --color

# Process from stdin
echo "قال الرجل" | hassy-normalize
```

### Web Interface

```bash
# Start web server
hassy-web

# Custom port
PORT=5000 hassy-web
```

Then open http://localhost:8000 in your browser.

### Python API

```python
from hassy_normalizer import normalize_text, normalize_word

# Normalize text
original = "قال الرجل"
normalized = normalize_text(original)
print(f"{original} → {normalized}")

# Normalize single word
word = normalize_word("قال")
print(f"Normalized: {word}")

# Get diff information
from hassy_normalizer import word_diff, format_diff_html

diff = word_diff(original, normalized)
html_diff = format_diff_html(diff)
print(html_diff)
```

## Installation

### Requirements

- Python 3.9 or higher
- Windows, macOS, or Linux

### From PyPI

```bash
pip install hassy-normalizer
```

### From Source

```bash
git clone https://github.com/yourusername/hassaniya-normalizer.git
cd hassaniya-normalizer
pip install -e .
```

### Development Installation

```bash
git clone https://github.com/yourusername/hassaniya-normalizer.git
cd hassaniya-normalizer
pip install -e .[dev]
```

## Windows Setup

### Enable Long Paths (Windows 10/11)

1. Open Group Policy Editor (`gpedit.msc`)
2. Navigate to: Computer Configuration → Administrative Templates → System → Filesystem
3. Enable "Enable Win32 long paths"
4. Restart your computer

Alternatively, run as Administrator:

```powershell
New-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem" -Name "LongPathsEnabled" -Value 1 -PropertyType DWORD -Force
```

### Check Port Conflicts

```powershell
# Check if port 8000 is in use
netstat -an | findstr :8000

# Find process using port
netstat -ano | findstr :8000
```

### PowerShell Execution Policy

If you encounter script execution issues:

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

## CLI Reference

### Basic Usage

```bash
hassy-normalize [INPUT] [OPTIONS]
```

### Arguments

- `INPUT`: Input file path (default: stdin)

### Options

- `-o, --output FILE`: Output file path (default: stdout)
- `--diff`: Show word-level diff
- `--color`: Enable colored output
- `-v, --verbose`: Enable verbose logging
- `--version`: Show version information
- `-h, --help`: Show help message

### Examples

```bash
# Basic normalization
hassy-normalize text.txt -o normalized.txt

# Show changes with colors
hassy-normalize text.txt --diff --color

# Pipe processing
cat input.txt | hassy-normalize --diff

# Verbose output
hassy-normalize text.txt -v
```

## Web API Reference

### Endpoints

#### `POST /api/normalize`

Normalize text and get diff information.

**Request:**
```json
{
  "text": "قال الرجل"
}
```

**Response:**
```json
{
  "original": "قال الرجل",
  "normalized": "كال الرجل",
  "diff": "<mark class=\"change\">كال</mark> الرجل",
  "stats": {
    "total_words": 2,
    "changed_words": 1,
    "unchanged_words": 1,
    "change_percentage": 50.0,
    "processing_time_ms": 1.2
  }
}
```

#### `GET /api/stats`

Get normalizer statistics.

**Response:**
```json
{
  "variants_loaded": 1500,
  "exceptions_loaded": 7000,
  "unknown_variants": 25,
  "version": "0.1.0"
}
```

#### `GET /healthz`

Health check endpoint.

**Response:** `ok`

### Error Responses

```json
{
  "error": "Error message"
}
```

## Configuration

### Environment Variables

- `PORT`: Web server port (default: 8000)
- `FLASK_DEBUG`: Enable debug mode (default: 0)
- `HOST`: Server host (default: 0.0.0.0)

### Data Files

The normalizer uses two data files:

1. **`hassaniya_variants.jsonl`**: Variant mappings
   ```json
   {"canonical": "هذا", "variants": ["هاذ", "هاذا"]}
   ```

2. **`exception_words_g_q.json`**: Exception words (skip normalization)
   ```json
   ["قادية", "ءواثق", ...]
   ```

## Normalization Rules

The normalizer applies rules in this order:

1. **Variant Lookup**: Check if word has a known canonical form
2. **Letter Rules** (if not in exceptions):
   - `گ/ق → ك`: Replace گ and ق with ك
   - `ة → ه`: Replace word-final ة with ه

### Examples

| Original | Normalized | Rule Applied |
|----------|------------|-------------|
| قال | كال | گ/ق → ك |
| كلمة | كلمه | ة → ه |
| هاذا | هذا | Variant lookup |
| قادية | قادية | Exception (no change) |

## Development

### Project Structure

```
hassaniya-normalizer/
├── src/hassy_normalizer/          # Main package
│   ├── __init__.py               # Package exports
│   ├── data_loader.py            # Data file loading
│   ├── rules.py                  # Normalization rules
│   ├── normalizer.py             # Core normalization
│   ├── diff.py                   # Diff utilities
│   ├── cli.py                    # CLI implementation
│   ├── web_ui/                   # Web interface
│   │   ├── server.py             # Flask server
│   │   ├── templates/index.html  # Web UI template
│   │   └── static/               # CSS/JS assets
│   └── data/                     # Data files
├── tests/                        # Test suite
├── scripts/                      # Utility scripts
├── .github/workflows/            # CI/CD
└── pyproject.toml               # Project config
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=hassy_normalizer

# Run specific test file
pytest tests/test_rules.py

# Run with verbose output
pytest -v
```

### Code Quality

```bash
# Format code
black src/ tests/

# Lint code
ruff check src/ tests/

# Type checking (if using mypy)
mypy src/
```

### Data Validation

```bash
# Validate data files
python scripts/validate_data.py
```

### Building

```bash
# Build package
python -m build

# Check package
twine check dist/*
```

## Docker

### Build Image

```bash
docker build -t hassy-normalizer .
```

### Run Container

```bash
# Run web server
docker run -p 8000:8000 hassy-normalizer

# Custom port
docker run -p 5000:5000 -e PORT=5000 hassy-normalizer

# Run CLI
docker run -i hassy-normalizer hassy-normalize --help
```

### Docker Compose

```yaml
version: '3.8'
services:
  hassy-normalizer:
    build: .
    ports:
      - "8000:8000"
    environment:
      - PORT=8000
      - FLASK_DEBUG=0
```

## Performance

### Benchmarks

- **Throughput**: ~10,000 words/second (cached)
- **Memory**: ~50MB base + data files
- **Startup**: <2 seconds

### Optimization Tips

1. **Caching**: Results are cached automatically
2. **Batch Processing**: Process multiple texts together
3. **Memory**: Clear caches periodically for long-running processes

```python
from hassy_normalizer import clear_cache

# Clear all caches
clear_cache()
```

## Troubleshooting

### Common Issues

#### Import Errors

```bash
# Ensure package is installed
pip list | grep hassy

# Reinstall if needed
pip uninstall hassy-normalizer
pip install hassy-normalizer
```

#### Data File Issues

```bash
# Validate data files
python scripts/validate_data.py

# Check file permissions
ls -la src/hassy_normalizer/data/
```

#### Web Server Issues

```bash
# Check port availability
netstat -tulpn | grep :8000

# Try different port
PORT=8080 hassy-web
```

#### Memory Issues

```python
# Clear caches to free memory
from hassy_normalizer import clear_cache
clear_cache()
```

### Debug Mode

```bash
# Enable verbose logging
hassy-normalize input.txt -v

# Web server debug mode
FLASK_DEBUG=1 hassy-web
```

### Getting Help

1. Check the [Issues](https://github.com/yourusername/hassaniya-normalizer/issues) page
2. Run with `-v` flag for verbose output
3. Validate your data files
4. Check system requirements

## Contributing

### Development Setup

```bash
git clone https://github.com/yourusername/hassaniya-normalizer.git
cd hassaniya-normalizer
pip install -e .[dev]
pre-commit install
```

### Contribution Guidelines

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Follow code style guidelines
6. Submit a pull request

### Code Style

- Use [Black](https://black.readthedocs.io/) for formatting
- Use [Ruff](https://docs.astral.sh/ruff/) for linting
- Follow [Google-style docstrings](https://google.github.io/styleguide/pyguide.html#38-comments-and-docstrings)
- Add type hints where appropriate

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for version history.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Hassaniya Arabic language community
- Contributors and maintainers
- Open source libraries used in this project

## Roadmap

### v0.2.0
- CRUD API for managing variants and exceptions
- Simple authentication system
- Enhanced web UI with management interface

### v0.3.0
- SQLite persistence layer
- Database migrations with Alembic
- Advanced statistics and analytics

### v1.0.0
- FastAPI migration for better performance
- OpenAPI documentation
- Production-ready container images
- CDN integration for static assets
- Advanced caching strategies

---

**Made with ❤️ for the Hassaniya Arabic community**