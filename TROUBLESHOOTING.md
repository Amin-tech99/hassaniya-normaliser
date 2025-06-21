# Troubleshooting Guide

## Web UI Not Working After Git Clone

If you've cloned the repository and the web UI isn't working, follow these steps:

### 1. Install Dependencies

After cloning, you need to install the package and its dependencies:

```bash
# Navigate to the project directory
cd hassaniya-normalizer

# Install in development mode with web dependencies
pip install -e .[web]

# OR install with all dependencies
pip install -e .[dev,web]
```

### 2. Verify Installation

Check if the installation was successful:

```bash
# Test CLI command
hassy-normalize --help

# Test web command
hassy-web --help
```

### 3. Common Issues and Solutions

#### Issue: "Command not found" or "Module not found"

**Solution:**
```bash
# Make sure you're in the project directory
cd hassaniya-normalizer

# Install in editable mode
pip install -e .

# If still not working, try:
python -m pip install -e .
```

#### Issue: "Flask not found" or "ImportError"

**Solution:**
```bash
# Install web dependencies specifically
pip install flask>=2.3.0 werkzeug>=2.3.0

# OR install with web extras
pip install -e .[web]
```

#### Issue: Web server starts but immediately exits

**Solution:**
```bash
# Try running with explicit Python module
python -m hassy_normalizer.web_ui.server

# OR with debug mode
FLASK_DEBUG=1 python -m hassy_normalizer.web_ui.server

# OR using the PowerShell script
.\run-ui.ps1
```

#### Issue: "Permission denied" on Windows

**Solution:**
```powershell
# Run PowerShell as Administrator, then:
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# Then try again:
.\run-ui.ps1
```

#### Issue: Port already in use

**Solution:**
```bash
# Use a different port
PORT=8080 hassy-web

# OR
python -m hassy_normalizer.web_ui.server --port 8080

# OR with PowerShell script
.\run-ui.ps1 8080
```

### 4. Step-by-Step Setup (Windows)

```powershell
# 1. Clone the repository
git clone https://github.com/yourusername/hassaniya-normalizer.git
cd hassaniya-normalizer

# 2. Create virtual environment (recommended)
python -m venv .venv
.venv\Scripts\Activate.ps1

# 3. Install the package
pip install -e .[web]

# 4. Start the web UI
hassy-web
# OR
.\run-ui.ps1

# 5. Open browser to http://localhost:8000
```

### 5. Step-by-Step Setup (Linux/Mac)

```bash
# 1. Clone the repository
git clone https://github.com/yourusername/hassaniya-normalizer.git
cd hassaniya-normalizer

# 2. Create virtual environment (recommended)
python3 -m venv .venv
source .venv/bin/activate

# 3. Install the package
pip install -e .[web]

# 4. Start the web UI
hassy-web

# 5. Open browser to http://localhost:8000
```

### 6. Alternative: Use Docker

If local installation doesn't work, use Docker:

```bash
# Build the Docker image
docker build -t hassy-normalizer .

# Run the container
docker run -p 8000:8000 hassy-normalizer

# Access at http://localhost:8000
```

### 7. Debugging Steps

#### Check Python Version
```bash
python --version
# Should be 3.9 or higher
```

#### Check Package Installation
```bash
pip list | grep hassy
# Should show hassy-normalizer
```

#### Test Import
```bash
python -c "import hassy_normalizer; print('Import successful')"
```

#### Check Web UI Module
```bash
python -c "from hassy_normalizer.web_ui import server; print('Web UI module found')"
```

#### Run with Verbose Output
```bash
# Enable debug logging
FLASK_DEBUG=1 python -m hassy_normalizer.web_ui.server
```

### 8. Environment Variables

You can customize the web server behavior:

```bash
# Set port
export PORT=8080

# Enable debug mode
export FLASK_DEBUG=1

# Set host (for external access)
export HOST=0.0.0.0

# Then start
hassy-web
```

### 9. Still Not Working?

#### Option 1: Use the GitHub Pages Version
If local setup is problematic, use the online version:
- Go to `https://yourusername.github.io/hassaniya-normalizer/`
- This runs entirely in your browser
- No installation required

#### Option 2: Manual Module Execution
```bash
# Navigate to the src directory
cd src

# Run the server directly
python -m hassy_normalizer.web_ui.server
```

#### Option 3: Check Dependencies
```bash
# Install all dependencies manually
pip install flask>=2.3.0 werkzeug>=2.3.0 rich>=10.0.0

# Then try again
python -m hassy_normalizer.web_ui.server
```

### 10. Getting Help

If none of these solutions work:

1. **Check the Issues**: Look at the GitHub repository issues
2. **Create an Issue**: Include:
   - Your operating system
   - Python version (`python --version`)
   - Error messages (full traceback)
   - Steps you've tried
3. **Use Docker**: As a last resort, Docker should always work

### 11. Success Checklist

- [ ] Python 3.9+ installed
- [ ] Repository cloned
- [ ] Dependencies installed (`pip install -e .[web]`)
- [ ] Commands available (`hassy-normalize --help` works)
- [ ] Web server starts (`hassy-web` or `python -m hassy_normalizer.web_ui.server`)
- [ ] Browser opens to http://localhost:8000
- [ ] Web interface loads and works

If all items are checked, the setup is successful!