"""Flask web server for Hassaniya normalizer.

Provides a web interface for text normalization with API endpoints.
"""

import json
import logging
import os
import signal
import sys
import time
from pathlib import Path
from typing import Dict, Any

from flask import Flask, request, jsonify, render_template
from werkzeug.exceptions import BadRequest, InternalServerError

from ..diff import word_diff_simple, format_diff_html, get_change_stats
from ..normalizer import normalize_text, get_stats
from ..data_loader import load_variants, load_link_fixes, clear_cache, _get_data_file_path
from .. import __version__

try:
    import portalocker
except ImportError:
    portalocker = None

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
    
    @app.route('/api/variant', methods=['POST'])
    def api_add_variant():
        """Add a new variant mapping.
        
        Expected JSON payload:
        {
            "canonical": "Canonical form",
            "variant": "Variant form"
        }
        
        Returns:
        {
            "success": true,
            "message": "Variant added successfully"
        }
        """
        try:
            # Validate request
            if not request.is_json:
                raise BadRequest("Request must be JSON")
            
            data = request.get_json()
            if not data:
                raise BadRequest("Empty request body")
            
            canonical = data.get('canonical', '').strip()
            variant = data.get('variant', '').strip()
            
            if not canonical or not variant:
                raise BadRequest("Both 'canonical' and 'variant' fields are required")
            
            # Add variant to file
            _add_variant_to_file(canonical, variant)
            
            # Clear caches to reload data
            clear_cache()
            
            logger.info(f"Added variant: '{variant}' -> '{canonical}'")
            return jsonify({
                "success": True,
                "message": "Variant added successfully"
            })
            
        except BadRequest as e:
            logger.warning(f"Bad request: {e.description}")
            return jsonify({"error": e.description}), 400
        except Exception as e:
            logger.error(f"Error adding variant: {e}", exc_info=True)
            return jsonify({"error": "Internal server error"}), 500
    
    @app.route('/api/variant', methods=['GET'])
    def api_get_variants():
        """Get variants for a canonical form or all recent variants.
        
        Query parameter:
        - canonical: The canonical form to look up (optional)
        
        If canonical is provided, returns:
        {
            "canonical": "...",
            "variants": ["...", "..."]
        }
        
        If no canonical is provided, returns all recent variants:
        {
            "variants": [
                {"canonical": "...", "variant": "..."},
                ...
            ]
        }
        """
        try:
            canonical = request.args.get('canonical', '').strip()
            
            # Load current variants
            variants_data = _load_variants_file()
            
            if canonical:
                # Return variants for specific canonical form
                for entry in variants_data:
                    if entry.get('canonical') == canonical:
                        return jsonify({
                            "canonical": canonical,
                            "variants": entry.get('variants', [])
                        })
                
                return jsonify({
                    "canonical": canonical,
                    "variants": []
                })
            else:
                # Return all recent variants (flattened for display)
                all_variants = []
                for entry in variants_data:
                    canonical_form = entry.get('canonical', '')
                    for variant in entry.get('variants', []):
                        all_variants.append({
                            "canonical": canonical_form,
                            "variant": variant
                        })
                
                # Return last 10 entries
                recent_variants = all_variants[-10:] if len(all_variants) > 10 else all_variants
                
                return jsonify({
                    "variants": recent_variants
                })
            
        except BadRequest as e:
            logger.warning(f"Bad request: {e.description}")
            return jsonify({"error": e.description}), 400
        except Exception as e:
            logger.error(f"Error getting variants: {e}", exc_info=True)
            return jsonify({"error": "Internal server error"}), 500
    
    @app.route('/api/link-fix', methods=['POST'])
    def api_add_link_fix():
        """Add a new link fix mapping.
        
        Expected JSON payload:
        {
            "wrong": "Incorrect form",
            "correct": "Correct form"
        }
        
        Returns:
        {
            "success": true,
            "message": "Link fix added successfully"
        }
        """
        try:
            # Validate request
            if not request.is_json:
                raise BadRequest("Request must be JSON")
            
            data = request.get_json()
            if not data:
                raise BadRequest("Empty request body")
            
            wrong = data.get('wrong', '').strip()
            correct = data.get('correct', '').strip()
            
            if not wrong or not correct:
                raise BadRequest("Both 'wrong' and 'correct' fields are required")
            
            # Add link fix to file
            _add_link_fix_to_file(wrong, correct)
            
            # Clear caches to reload data
            clear_cache()
            
            logger.info(f"Added link fix: '{wrong}' -> '{correct}'")
            return jsonify({
                "success": True,
                "message": "Link fix added successfully"
            })
            
        except BadRequest as e:
            logger.warning(f"Bad request: {e.description}")
            return jsonify({"error": e.description}), 400
        except Exception as e:
            logger.error(f"Error adding link fix: {e}", exc_info=True)
            return jsonify({"error": "Internal server error"}), 500
    
    @app.route('/api/link-fix', methods=['GET'])
    def api_get_link_fix():
        """Get link fix for a wrong form or all recent link fixes.
        
        Query parameter:
        - wrong: The wrong form to look up (optional)
        
        If wrong is provided, returns:
        {
            "wrong": "...",
            "correct": "..."
        }
        
        If no wrong is provided, returns all recent link fixes:
        {
            "link_fixes": [
                {"wrong": "...", "correct": "..."},
                ...
            ]
        }
        """
        try:
            wrong = request.args.get('wrong', '').strip()
            
            if wrong:
                # Return link fix for specific wrong form
                link_fixes = load_link_fixes()
                correct = link_fixes.get(wrong, '')
                
                return jsonify({
                    "wrong": wrong,
                    "correct": correct
                })
            else:
                # Return all recent link fixes
                # Resolve path to link-fixes data – may not exist yet.
                try:
                    filepath = _get_data_file_path("linked_words.json")
                except FileNotFoundError:
                    variant_path = _get_data_file_path("hassaniya_variants.jsonl")
                    filepath = variant_path.parent / "linked_words.json"

                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        link_fixes_data = json.load(f)
                except FileNotFoundError:
                    link_fixes_data = []
                
                # Return last 10 entries
                recent_link_fixes = link_fixes_data[-10:] if len(link_fixes_data) > 10 else link_fixes_data
                
                return jsonify({
                    "link_fixes": recent_link_fixes
                })
            
        except BadRequest as e:
            logger.warning(f"Bad request: {e.description}")
            return jsonify({"error": e.description}), 400
        except Exception as e:
            logger.error(f"Error getting link fix: {e}", exc_info=True)
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


def _load_variants_file() -> list:
    """Load variants file as list of entries.
    
    Returns:
        List of variant entries
    """
    # Use the same path resolution as data_loader
    filepath = _get_data_file_path("hassaniya_variants.jsonl")
    
    variants_data = []
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    variants_data.append(json.loads(line))
    except FileNotFoundError:
        logger.warning(f"Variants file not found: {filepath}")
        pass  # File doesn't exist yet
    
    return variants_data


def _add_variant_to_file(canonical: str, variant: str) -> None:
    """Add a variant to the variants file.
    
    Args:
        canonical: Canonical form
        variant: Variant form
    """
    # Use the same path resolution as data_loader
    filepath = _get_data_file_path("hassaniya_variants.jsonl")
    
    # Load existing data
    variants_data = _load_variants_file()
    
    # Find existing entry or create new one and move it to the end of the list so the
    # API can easily return the most recently modified canonical entry.
    moved_entry = None
    for idx, entry in enumerate(variants_data):
        if entry.get('canonical') == canonical:
            # Append the new variant if it's new for this canonical form
            if variant not in entry.get('variants', []):
                entry['variants'].append(variant)
            # Remove the entry so that we can append it to the end and mark it as the
            # most recently updated item.
            moved_entry = variants_data.pop(idx)
            break

    if moved_entry is not None:
        variants_data.append(moved_entry)
    else:
        # New canonical form – append a fresh entry to the end
        variants_data.append({
            "canonical": canonical,
            "variants": [variant]
        })
    
    # Write back to file with locking
    _write_variants_file(filepath, variants_data)


def _write_variants_file(filepath: Path, variants_data: list) -> None:
    """Write variants data to file with locking.
    
    Args:
        filepath: Path to variants file
        variants_data: List of variant entries
    """
    # Ensure parent directory exists
    filepath.parent.mkdir(parents=True, exist_ok=True)
    
    # Write with file locking if available
    with open(filepath, 'w', encoding='utf-8') as f:
        if portalocker:
            portalocker.lock(f, portalocker.LOCK_EX)
        
        for entry in variants_data:
            json.dump(entry, f, ensure_ascii=False)
            f.write('\n')
        
        if portalocker:
            portalocker.unlock(f)


def _add_link_fix_to_file(wrong: str, correct: str) -> None:
    """Add a link fix to the link fixes file.
    
    Args:
        wrong: Wrong form
        correct: Correct form
    """
    # Resolve path to link-fixes data – may not exist yet on first run.
    try:
        filepath = _get_data_file_path("linked_words.json")
    except FileNotFoundError:
        variant_path = _get_data_file_path("hassaniya_variants.jsonl")
        filepath = variant_path.parent / "linked_words.json"
    
    # Load existing data
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            link_fixes_data = json.load(f)
    except FileNotFoundError:
        link_fixes_data = []
    
    # Remove existing entry with same wrong form
    link_fixes_data = [item for item in link_fixes_data if item.get('wrong') != wrong]
    
    # Add new entry
    link_fixes_data.append({
        "wrong": wrong,
        "correct": correct
    })
    
    # Write back to file with locking
    _write_link_fixes_file(filepath, link_fixes_data)


def _write_link_fixes_file(filepath: Path, link_fixes_data: list) -> None:
    """Write link fixes data to file with locking.
    
    Args:
        filepath: Path to link fixes file
        link_fixes_data: List of link fix entries
    """
    # Ensure parent directory exists
    filepath.parent.mkdir(parents=True, exist_ok=True)
    
    # Write with file locking if available
    with open(filepath, 'w', encoding='utf-8') as f:
        if portalocker:
            portalocker.lock(f, portalocker.LOCK_EX)
        
        json.dump(link_fixes_data, f, ensure_ascii=False, indent=2)
        
        if portalocker:
            portalocker.unlock(f)


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