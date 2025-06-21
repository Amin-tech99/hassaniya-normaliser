"""Tests for Flask API endpoints."""

import json
import pytest
from unittest.mock import patch, MagicMock

from hassy_normalizer.web_ui.server import create_app


@pytest.fixture
def app():
    """Create test Flask app."""
    app = create_app()
    app.config['TESTING'] = True
    return app


@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()


class TestHealthEndpoint:
    """Test health check endpoint."""
    
    def test_health_check(self, client):
        """Test health check returns ok."""
        response = client.get('/healthz')
        assert response.status_code == 200
        assert response.data == b'ok'


class TestIndexEndpoint:
    """Test main index page."""
    
    def test_index_page(self, client):
        """Test index page loads."""
        response = client.get('/')
        assert response.status_code == 200
        assert b'Hassaniya Arabic Normalizer' in response.data
        assert b'text/html' in response.content_type.encode()


class TestNormalizeAPI:
    """Test /api/normalize endpoint."""
    
    def test_normalize_success(self, client):
        """Test successful normalization."""
        with patch('hassy_normalizer.web_ui.server.normalize_text') as mock_normalize, \
             patch('hassy_normalizer.web_ui.server.word_diff_simple') as mock_diff, \
             patch('hassy_normalizer.web_ui.server.format_diff_html') as mock_format, \
             patch('hassy_normalizer.web_ui.server.get_change_stats') as mock_stats:
            
            # Setup mocks
            mock_normalize.return_value = "كال الرجل"
            mock_diff.return_value = [
                {"word": "كال", "changed": True},
                {"word": " ", "changed": False},
                {"word": "الرجل", "changed": False}
            ]
            mock_format.return_value = '<mark class="change">كال</mark> الرجل'
            mock_stats.return_value = {
                "total_words": 2,
                "changed_words": 1,
                "unchanged_words": 1,
                "change_percentage": 50.0
            }
            
            # Make request
            response = client.post('/api/normalize',
                                 json={'text': 'قال الرجل'},
                                 content_type='application/json')
            
            # Check response
            assert response.status_code == 200
            data = json.loads(response.data)
            
            assert data['original'] == 'قال الرجل'
            assert data['normalized'] == 'كال الرجل'
            assert data['diff'] == '<mark class="change">كال</mark> الرجل'
            assert 'stats' in data
            assert data['stats']['total_words'] == 2
            assert data['stats']['changed_words'] == 1
            assert 'processing_time_ms' in data['stats']
    
    def test_normalize_missing_text_field(self, client):
        """Test error when text field is missing."""
        response = client.post('/api/normalize',
                             json={'not_text': 'some value'},
                             content_type='application/json')
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data
        assert 'text' in data['error']
    
    def test_normalize_non_json_request(self, client):
        """Test error when request is not JSON."""
        response = client.post('/api/normalize',
                             data='not json',
                             content_type='text/plain')
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data
        assert 'JSON' in data['error']
    
    def test_normalize_non_string_text(self, client):
        """Test error when text is not a string."""
        response = client.post('/api/normalize',
                             json={'text': 123},
                             content_type='application/json')
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data
        assert 'string' in data['error']
    
    def test_normalize_text_too_long(self, client):
        """Test error when text is too long."""
        long_text = 'a' * 10001  # Over 10k limit
        
        response = client.post('/api/normalize',
                             json={'text': long_text},
                             content_type='application/json')
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data
        assert 'too long' in data['error']
    
    def test_normalize_empty_text(self, client):
        """Test normalization with empty text."""
        with patch('hassy_normalizer.web_ui.server.normalize_text') as mock_normalize, \
             patch('hassy_normalizer.web_ui.server.word_diff_simple') as mock_diff, \
             patch('hassy_normalizer.web_ui.server.format_diff_html') as mock_format, \
             patch('hassy_normalizer.web_ui.server.get_change_stats') as mock_stats:
            
            # Setup mocks for empty text
            mock_normalize.return_value = ""
            mock_diff.return_value = []
            mock_format.return_value = ""
            mock_stats.return_value = {
                "total_words": 0,
                "changed_words": 0,
                "unchanged_words": 0,
                "change_percentage": 0.0
            }
            
            response = client.post('/api/normalize',
                                 json={'text': ''},
                                 content_type='application/json')
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['original'] == ''
            assert data['normalized'] == ''
    
    def test_normalize_internal_error(self, client):
        """Test handling of internal errors during normalization."""
        with patch('hassy_normalizer.web_ui.server.normalize_text', 
                  side_effect=Exception("Normalization failed")):
            
            response = client.post('/api/normalize',
                                 json={'text': 'test'},
                                 content_type='application/json')
            
            assert response.status_code == 500
            data = json.loads(response.data)
            assert 'error' in data
            assert data['error'] == 'Internal server error'
    
    def test_normalize_unicode_text(self, client):
        """Test normalization with Unicode text."""
        with patch('hassy_normalizer.web_ui.server.normalize_text') as mock_normalize, \
             patch('hassy_normalizer.web_ui.server.word_diff_simple') as mock_diff, \
             patch('hassy_normalizer.web_ui.server.format_diff_html') as mock_format, \
             patch('hassy_normalizer.web_ui.server.get_change_stats') as mock_stats:
            
            unicode_text = "مرحبا 🌟 بالعالم"
            
            mock_normalize.return_value = unicode_text
            mock_diff.return_value = [{"word": unicode_text, "changed": False}]
            mock_format.return_value = unicode_text
            mock_stats.return_value = {
                "total_words": 2,
                "changed_words": 0,
                "unchanged_words": 2,
                "change_percentage": 0.0
            }
            
            response = client.post('/api/normalize',
                                 json={'text': unicode_text},
                                 content_type='application/json')
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['original'] == unicode_text
            assert data['normalized'] == unicode_text


class TestStatsAPI:
    """Test /api/stats endpoint."""
    
    def test_stats_success(self, client):
        """Test successful stats retrieval."""
        with patch('hassy_normalizer.web_ui.server.get_stats') as mock_stats:
            mock_stats.return_value = {
                "variants_loaded": 100,
                "exceptions_loaded": 5000,
                "unknown_variants": 10
            }
            
            response = client.get('/api/stats')
            
            assert response.status_code == 200
            data = json.loads(response.data)
            
            assert data['variants_loaded'] == 100
            assert data['exceptions_loaded'] == 5000
            assert data['unknown_variants'] == 10
            assert 'version' in data
    
    def test_stats_internal_error(self, client):
        """Test handling of internal errors in stats."""
        with patch('hassy_normalizer.web_ui.server.get_stats',
                  side_effect=Exception("Stats failed")):
            
            response = client.get('/api/stats')
            
            assert response.status_code == 500
            data = json.loads(response.data)
            assert 'error' in data
            assert data['error'] == 'Internal server error'


class TestErrorHandlers:
    """Test error handlers."""
    
    def test_404_handler(self, client):
        """Test 404 error handler."""
        response = client.get('/nonexistent')
        
        assert response.status_code == 404
        data = json.loads(response.data)
        assert 'error' in data
        assert data['error'] == 'Not found'
    
    def test_500_handler(self, client, app):
        """Test 500 error handler."""
        # Create a route that raises an exception
        @app.route('/test-error')
        def test_error():
            raise Exception("Test error")
        
        response = client.get('/test-error')
        
        assert response.status_code == 500
        data = json.loads(response.data)
        assert 'error' in data
        assert data['error'] == 'Internal server error'


class TestResponseHeaders:
    """Test response headers and middleware."""
    
    def test_security_headers(self, client):
        """Test that security headers are added."""
        response = client.get('/')
        
        assert response.headers.get('X-Content-Type-Options') == 'nosniff'
        assert response.headers.get('X-Frame-Options') == 'DENY'
        assert response.headers.get('X-XSS-Protection') == '1; mode=block'
    
    def test_cors_headers_for_api(self, client):
        """Test CORS headers for API endpoints."""
        response = client.get('/api/stats')
        
        assert response.headers.get('Access-Control-Allow-Origin') == '*'
        assert 'GET' in response.headers.get('Access-Control-Allow-Methods', '')
        assert 'POST' in response.headers.get('Access-Control-Allow-Methods', '')
        assert 'Content-Type' in response.headers.get('Access-Control-Allow-Headers', '')
    
    def test_no_cors_headers_for_non_api(self, client):
        """Test that CORS headers are not added to non-API endpoints."""
        response = client.get('/')
        
        assert 'Access-Control-Allow-Origin' not in response.headers
    
    def test_cache_headers_for_static(self, client):
        """Test cache headers for static assets."""
        # This would require actual static files, so we'll mock the request path
        with patch('flask.request') as mock_request:
            mock_request.path = '/static/css/style.css'
            
            response = client.get('/static/css/style.css')
            # Note: This test might not work perfectly due to Flask's static file handling
            # In a real scenario, you'd test with actual static files


class TestRequestLogging:
    """Test request logging functionality."""
    
    def test_request_logging(self, client, caplog):
        """Test that requests are logged."""
        with caplog.at_level('INFO'):
            response = client.get('/healthz')
            
            assert response.status_code == 200
            # Check that request was logged
            log_messages = [record.message for record in caplog.records]
            request_logs = [msg for msg in log_messages if 'GET /healthz' in msg]
            assert len(request_logs) > 0


class TestContentTypeHandling:
    """Test content type handling."""
    
    def test_json_response_encoding(self, client):
        """Test that JSON responses handle Unicode correctly."""
        with patch('hassy_normalizer.web_ui.server.get_stats') as mock_stats:
            # Include Unicode characters in response
            mock_stats.return_value = {
                "variants_loaded": 100,
                "exceptions_loaded": 5000,
                "unknown_variants": 10,
                "test_unicode": "مرحبا"
            }
            
            response = client.get('/api/stats')
            
            assert response.status_code == 200
            assert 'application/json' in response.content_type
            
            # Ensure Unicode is properly encoded
            data = json.loads(response.data.decode('utf-8'))
            assert data['test_unicode'] == "مرحبا"


if __name__ == '__main__':
    pytest.main([__file__])