# 🚀 Deployment Guide

This guide helps you publish the Hassaniya normalizer to GitHub and run it completely offline on Windows.

## Prerequisites

- Windows 10/11 with PowerShell
- Python 3.9+ installed
- Git installed
- GitHub account (`Amin-tech99`)
- GitHub CLI (`gh`) or personal access token

## 1. Publish to GitHub (One-time Setup)

### Option A: Using GitHub CLI (Recommended)

```powershell
# 1. Open PowerShell in the project root
PS> cd "C:\Users\LENOVO\Desktop\hassaniya-normalizer"

# 2. Initialize Git (skip if already done)
PS> git init
PS> git add .
PS> git commit -m "🎉 Initial working release"

# 3. Create repo on GitHub and push
PS> gh repo create Amin-tech99/hassaniya-normalizer `
        --public --source=. --remote=origin

# 4. Push code + tags
PS> git push -u origin main
# Later: PS> git tag v0.1.0 && git push origin v0.1.0
```

### Option B: Manual GitHub Setup

If you don't have GitHub CLI:

1. Create repo manually at https://github.com/new
2. Name it `hassaniya-normalizer`
3. Make it public
4. Then run:

```powershell
PS> git remote add origin https://github.com/Amin-tech99/hassaniya-normalizer.git
PS> git push -u origin main
```

## 2. Install Locally (Offline-Ready)

Once the repo is on your disk, you don't need internet:

```powershell
# Still in the repo directory
PS> python -m venv .venv
PS> .\.venv\Scripts\Activate

# Editable install with web extras from local source
(.venv) PS> python -m pip install -e .[web]
```

*The `[web]` extra installs Flask & dependencies. Pip uses wheel cache if offline.*

## 3. Run Web UI (Fully Offline)

### Quick Start

```powershell
# Activate venv if not already active
PS> .\.venv\Scripts\Activate

# Start the server
(.venv) PS> hassy-web
# OR
(.venv) PS> python -m hassy_normalizer.web_ui.server

# Console output:
#  * Running on http://127.0.0.1:8000

# Open in browser
PS> start http://127.0.0.1:8000
```

### Using the PowerShell Shortcut

For convenience, use the included `run-ui.ps1`:

```powershell
PS> .\run-ui.ps1        # defaults to port 8000
PS> .\run-ui.ps1 9000   # custom port
```

## 4. Command Line Usage (No Browser)

```powershell
# Direct text normalization
(.venv) PS> hassy-normalize "قناعة القضية"
كناعه القضيه

# From stdin
(.venv) PS> hassy-normalize - <<< "قناعة القضية"
كناعه القضيه

# File processing
(.venv) PS> hassy-normalize input.txt output.txt

# Show colored diff
(.venv) PS> hassy-normalize input.txt --diff
```

## 5. Offline Operation

✅ **Fully offline after initial setup:**
- Flask serves everything from your laptop
- No external API calls
- Works with Wi-Fi disabled
- All processing happens locally

## 6. Development Workflow

```powershell
# Run tests
(.venv) PS> pytest tests/ -v

# Code quality checks
(.venv) PS> ruff check src/ tests/
(.venv) PS> ruff format src/ tests/

# Update version and push
(.venv) PS> git add .
(.venv) PS> git commit -m "feat: new feature"
(.venv) PS> git tag v0.2.0
(.venv) PS> git push origin main --tags
```

## 7. Troubleshooting

### Port Already in Use
```powershell
# Use different port
PS> .\run-ui.ps1 9000
```

### Virtual Environment Issues
```powershell
# Recreate venv
PS> Remove-Item .venv -Recurse -Force
PS> python -m venv .venv
PS> .\.venv\Scripts\Activate
PS> python -m pip install -e .[web]
```

### Import Errors
```powershell
# Reinstall in development mode
(.venv) PS> pip install -e .
```

## 8. Project Structure

```
hassaniya-normalizer/
├── src/hassy_normalizer/          # Main package
│   ├── web_ui/                    # Web interface
│   │   ├── server.py             # Flask server
│   │   ├── templates/            # HTML templates
│   │   └── static/               # CSS/JS assets
│   ├── cli.py                    # Command line interface
│   └── ...                       # Core normalizer code
├── tests/                        # Test suite
├── pyproject.toml               # Package configuration
├── run-ui.ps1                   # PowerShell shortcut
└── DEPLOYMENT.md                # This guide
```

---

## ✅ Success Checklist

- [ ] Repo published to GitHub
- [ ] Local installation works: `pip install -e .[web]`
- [ ] Web UI starts: `hassy-web`
- [ ] Browser opens to http://127.0.0.1:8000
- [ ] CLI works: `hassy-normalize "test text"`
- [ ] Offline operation confirmed (disable Wi-Fi and test)

**🎉 You're ready to go! The normalizer runs completely offline on any Windows machine.**