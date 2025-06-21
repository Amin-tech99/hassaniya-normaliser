param([string]$Port = "8000")

# Set Flask debug mode
$Env:FLASK_DEBUG = "1"

# Activate virtual environment if it exists
if (Test-Path ".venv\Scripts\Activate.ps1") {
    Write-Host "Activating virtual environment..." -ForegroundColor Green
    & ".venv\Scripts\Activate.ps1"
}

# Start the web server
Write-Host "Starting Hassaniya normalizer web UI on port $Port..." -ForegroundColor Cyan
Write-Host "Open your browser to: http://127.0.0.1:$Port" -ForegroundColor Yellow

python -m hassy_normalizer.web_ui.server --port $Port