# Hassaniya Normalizer Setup Instructions

This guide provides instructions on how to set up and run the Hassaniya Normalizer application on both Windows and Ubuntu/Linux.

## Prerequisites

Before you begin, ensure you have the following installed on your system:

- [Python](https://www.python.org/downloads/) (version 3.9 or higher)
- [Git](https://git-scm.com/downloads/)

## Installation

### Windows

1.  **Run the installer:** Open a Command Prompt or PowerShell and navigate to the project directory. Then, run the `install.bat` script:

    ```bash
    install.bat
    ```

2.  **Follow the prompts:** The script will create a virtual environment and install all the necessary dependencies.

### Ubuntu/Linux

1.  **Make the script executable:** Open a terminal, navigate to the project directory, and make the `install.sh` script executable:

    ```bash
    chmod +x install.sh
    ```

2.  **Run the installer:** Run the `install.sh` script:

    ```bash
    ./install.sh
    ```

3.  **Follow the prompts:** The script will create a virtual environment and install all the necessary dependencies.

## Running the Application

### Windows

1.  **Run the UI:** After the installation is complete, you can start the web interface by running the `run-ui.ps1` script in PowerShell:

    ```powershell
    .\run-ui.ps1
    ```

### Ubuntu/Linux

1.  **Activate the virtual environment:**

    ```bash
    source .venv/bin/activate
    ```

2.  **Start the web server:**

    ```bash
    hassy-web
    ```

Once the server is running, you can access the application by opening your web browser and navigating to `http://127.0.0.1:5000`.