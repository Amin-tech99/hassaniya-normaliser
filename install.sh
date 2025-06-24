#!/bin/bash
# This script sets up the Hassaniya Normalizer application.

# Check for Python
if ! command -v python3 &> /dev/null
then
    echo "Python 3 is not installed or not in PATH."
    echo "Please install Python 3.9+."
    exit 1
fi

# Create a virtual environment
echo "Creating virtual environment..."
python3 -m venv .venv

# Activate the virtual environment and install dependencies
echo "Activating virtual environment and installing dependencies..."
source .venv/bin/activate

# Install dependencies
pip install -e .[web]

echo
echo "Setup complete. You can now run the application using the run-ui.ps1 script (for Windows) or by running 'source .venv/bin/activate' and then 'hassy-web'."