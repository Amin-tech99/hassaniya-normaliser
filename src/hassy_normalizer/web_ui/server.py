"""Web UI server entry point for hassy-web command."""

import os
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

def main():
    """Main entry point for the web server."""
    try:
        # Import the FastAPI app from the root server.py
        from server import app
        import uvicorn
        
        # Get port from environment or default to 8002
        port = int(os.environ.get("PORT", 8002))
        host = os.environ.get("HOST", "0.0.0.0")
        
        print(f"Starting Hassaniya Normalizer Web Server on {host}:{port}")
        uvicorn.run(app, host=host, port=port)
        
    except ImportError as e:
        print(f"Error importing server: {e}")
        print("Make sure you're running from the project root directory.")
        sys.exit(1)
    except Exception as e:
        print(f"Error starting server: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()