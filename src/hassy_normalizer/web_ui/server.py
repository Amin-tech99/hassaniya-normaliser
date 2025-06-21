"""Flask web server for Hassaniya normalizer.

Provides a web interface for text normalization with API endpoints.
"""

import json
import logging
import os
import signal
import sys
import time
from typing import Dict, Any

from flask import Flask, request, jsonify, render_template
from werkzeug.exceptions import BadRequest, InternalServerError

from ..diff import word_diff_simple, format_diff_html, get_change_stats
from ..normalizer import normalize_text, get_stats
from .. import __version__

logger = logging.getLogger(__name__)

# Global Flask app instance
app: Flask = None


def setup_logging() -> None:
    """Setup structured JSON logging for cloud environments."""
    # Configure logging format
    log_format = {
        'timestamp': '%(asctime)s',
        'level': '%(levelname)s',
        'logger': '%(name)s',
        'message': '%(message)s'
    }
    
    # Use JSON formatter if available
    try:
        import json_logging
        json_logging.init_flask(enable_json=True)
        json_logging.init_request_instrument(app)
    except ImportError:
        # Fallback to standard logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            stream=sys.stdout
        )


def handle_sigterm(signum, frame):
    """Handle SIGTERM for graceful shutdown."""
    logger.info("Received SIGTERM, shutting down gracefully")
    sys.exit(0)


def create_app() -> Flask:
    """Create and configure Flask application.
    
    Returns:
        Configured Flask app
    """
    global app
    
    app = Flask(__name__, 
                template_folder='templates',
                static_folder='static')
    
    # Configuration
    app.config['JSON_AS_ASCII'] = False  # Support Unicode in JSON responses
    app.config['MAX_CONTENT_LENGTH'] = 1024 * 1024  # 1MB max request size
    
    # Setup logging
    setup_logging()
    
    # Register signal handler for graceful shutdown
    signal.signal(signal.SIGTERM, handle_sigterm)
    
    @app.route('/')
    def index():
        """Serve the main web interface."""
        return render_template('index.html', version=__version__)
    
    @app.route('/healthz')
    def health_check():
        """Health check endpoint."""
        return 'ok'
    
    @app.route('/api/normalize', methods=['POST'])
    def api_normalize():
        """Normalize text via API.
        
        Expected JSON payload:
        {
            "text": "Text to normalize"
        }
        
        Returns:
        {
            "original": "Original text",
            "normalized": "Normalized text", 
            "diff": "HTML with highlighted changes",
            "stats": {
                "total_words": 10,
                "changed_words": 3,
                "change_percentage": 30.0,
                "processing_time_ms": 15
            }
        }
        """
        start_time = time.time()
        
        try:
            # Validate request
            if not request.is_json:
                raise BadRequest("Request must be JSON")
            
            data = request.get_json()
            if not data or 'text' not in data:
                raise BadRequest("Missing 'text' field in request")
            
            original_text = data['text']
            if not isinstance(original_text, str):
                raise BadRequest("'text' field must be a string")
            
            # Limit text length
            if len(original_text) > 10000:  # 10k characters max
                raise BadRequest("Text too long (max 10,000 characters)")
            
            # Normalize text
            normalized_text = normalize_text(original_text)
            
            # Generate diff
            diff_entries = word_diff_simple(original_text)
            diff_html = format_diff_html(diff_entries)
            
            # Get statistics
            change_stats = get_change_stats(diff_entries)
            processing_time = round((time.time() - start_time) * 1000, 1)
            
            stats = {
                **change_stats,
                "processing_time_ms": processing_time
            }
            
            response = {
                "original": original_text,
                "normalized": normalized_text,
                "diff": diff_html,
                "stats": stats
            }
            
            logger.info(f"Normalized {stats['total_words']} words, "
                       f"{stats['changed_words']} changed, "
                       f"{processing_time}ms")
            
            return jsonify(response)
        
        except BadRequest as e:
            logger.warning(f"Bad request: {e.description}")
            return jsonify({"error": e.description}), 400
        
        except Exception as e:
            logger.error(f"Normalization error: {e}", exc_info=True)
            return jsonify({"error": "Internal server error"}), 500
    
    @app.route('/api/stats')
    def api_stats():
        """Get normalizer statistics.
        
        Returns:
        {
            "variants_loaded": 100,
            "exceptions_loaded": 5000,
            "unknown_variants": 10,
            "version": "0.1.0"
        }
        """
        try:
            stats = get_stats()
            stats["version"] = __version__
            return jsonify(stats)
        
        except Exception as e:
            logger.error(f"Stats error: {e}", exc_info=True)
            return jsonify({"error": "Internal server error"}), 500
    
    @app.errorhandler(404)
    def not_found(error):
        """Handle 404 errors."""
        return jsonify({"error": "Not found"}), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        """Handle 500 errors."""
        logger.error(f"Internal server error: {error}", exc_info=True)
        return jsonify({"error": "Internal server error"}), 500
    
    @app.before_request
    def log_request():
        """Log incoming requests."""
        logger.info(f"{request.method} {request.path} from {request.remote_addr}")
    
    @app.after_request
    def add_headers(response):
        """Add security and caching headers."""
        # Security headers
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        
        # CORS for API endpoints
        if request.path.startswith('/api/'):
            response.headers['Access-Control-Allow-Origin'] = '*'
            response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
            response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        
        # Cache static assets
        if request.path.startswith('/static/'):
            response.headers['Cache-Control'] = 'public, max-age=3600'
        
        return response
    
    return app


def main() -> None:
    """Main entry point for web server."""
    # Get configuration from environment
    port = int(os.getenv("PORT", 8000))
    debug = os.getenv("FLASK_DEBUG", "0") == "1"
    host = os.getenv("HOST", "0.0.0.0")
    
    # Create app
    app = create_app()
    
    logger.info(f"Starting Hassaniya normalizer web server v{__version__}")
    logger.info(f"Server will run on http://{host}:{port}")
    
    try:
        # Run the server
        app.run(
            debug=debug,
            port=port,
            host=host,
            use_reloader=False,  # Avoid 'spooky exit 0' in production
            threaded=True
        )
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()