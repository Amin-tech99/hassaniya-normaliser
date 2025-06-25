"""Web UI server entry point for hassy-web command."""

import os
import sys
import importlib.util
from pathlib import Path

def main():
    """Main entry point for the web server."""
    try:
        # Try multiple paths to find server.py
        possible_paths = [
            # Current working directory
            Path.cwd() / "server.py",
            # Project root (4 levels up from this file)
            Path(__file__).parent.parent.parent.parent / "server.py",
            # App directory in Docker
            Path("/app/server.py"),
            # Relative to package installation
            Path(__file__).parent.parent.parent.parent.parent / "server.py"
        ]
        
        server_module = None
        for server_path in possible_paths:
            if server_path.exists():
                print(f"Found server.py at: {server_path}")
                # Load the module dynamically
                spec = importlib.util.spec_from_file_location("server", server_path)
                server_module = importlib.util.module_from_spec(spec)
                sys.modules["server"] = server_module
                spec.loader.exec_module(server_module)
                break
        
        if server_module is None:
            raise ImportError("Could not find server.py in any expected location")
        
        # Get the FastAPI app
        app = server_module.app
        import uvicorn
        
        # Get port from environment or default to 8002
        port = int(os.environ.get("PORT", 8002))
        host = os.environ.get("HOST", "0.0.0.0")
        
        print(f"Starting Hassaniya Normalizer Web Server on {host}:{port}")
        uvicorn.run(app, host=host, port=port)
        
    except ImportError as e:
        print(f"Error importing server: {e}")
        print("Searched paths:")
        for path in possible_paths:
            print(f"  - {path} (exists: {path.exists()})")
        sys.exit(1)
    except Exception as e:
        print(f"Error starting server: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()