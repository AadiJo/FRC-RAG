"""
Frontend Server for FRC RAG
Simple Flask server to serve the frontend and proxy API requests to backend
"""

import os
import logging
from flask import Flask, request, jsonify, render_template, send_from_directory, Response, stream_with_context
from flask_cors import CORS
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
class FrontendConfig:
    # Frontend server settings
    HOST = os.getenv('FRONTEND_HOST', '0.0.0.0')
    PORT = int(os.getenv('FRONTEND_PORT', 80))
    
    # Backend API URL
    BACKEND_URL = os.getenv('BACKEND_URL', 'http://localhost:5000')
    
    # Logging
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    
    # Security
    ALLOWED_ORIGINS = os.getenv('ALLOWED_ORIGINS', '*').split(',')

# Configure logging
logging.basicConfig(
    level=getattr(logging, FrontendConfig.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__, template_folder='templates', static_folder='static')
CORS(app, origins=FrontendConfig.ALLOWED_ORIGINS)

@app.route('/')
def index():
    """Serve the main chat interface"""
    return render_template('index.html')

@app.route('/health')
def health():
    """Health check endpoint"""
    try:
        # Check backend health
        backend_health = requests.get(
            f"{FrontendConfig.BACKEND_URL}/health",
            timeout=5
        )
        return jsonify({
            "status": "healthy",
            "frontend": "ok",
            "backend": backend_health.json() if backend_health.ok else "unavailable"
        })
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({
            "status": "degraded",
            "frontend": "ok",
            "backend": "unavailable",
            "error": str(e)
        }), 503

@app.route('/api/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE'])
def proxy_api(path):
    """Proxy all API requests to backend"""
    try:
        url = f"{FrontendConfig.BACKEND_URL}/api/{path}"
        
        # Prepare request
        headers = {k: v for k, v in request.headers if k.lower() != 'host'}
        
        # Check if this is a streaming endpoint
        is_streaming = 'stream' in path or request.args.get('stream') == 'true'
        
        # Forward request to backend
        if request.method == 'GET':
            response = requests.get(url, headers=headers, params=request.args, stream=is_streaming, timeout=120)
        elif request.method == 'POST':
            response = requests.post(url, headers=headers, json=request.get_json(), params=request.args, stream=is_streaming, timeout=120)
        elif request.method == 'PUT':
            response = requests.put(url, headers=headers, json=request.get_json(), params=request.args, stream=is_streaming, timeout=120)
        elif request.method == 'DELETE':
            response = requests.delete(url, headers=headers, params=request.args, stream=is_streaming, timeout=120)
        else:
            return jsonify({"error": "Method not allowed"}), 405
        
        # Handle streaming responses (SSE)
        if is_streaming:
            def generate():
                """Stream the response from backend"""
                try:
                    for line in response.iter_lines(decode_unicode=True):
                        if line:
                            # Ensure line ends with newline for SSE format
                            yield line + '\n'
                        else:
                            # Empty line (SSE event separator)
                            yield '\n'
                except Exception as e:
                    logger.error(f"Streaming error: {e}")
                    yield f"data: {{'type': 'error', 'error': 'Streaming error: {str(e)}'}}\n\n"
            
            return Response(
                stream_with_context(generate()),
                mimetype='text/event-stream',
                headers={
                    'Cache-Control': 'no-cache',
                    'X-Accel-Buffering': 'no',
                    'Connection': 'keep-alive'
                }
            )
        else:
            # Return regular response
            return (response.content, response.status_code, response.headers.items())
    
    except requests.exceptions.Timeout:
        return jsonify({"error": "Backend timeout"}), 504
    except requests.exceptions.ConnectionError:
        logger.error(f"Backend connection error for {path}")
        return jsonify({"error": "Backend unavailable"}), 503
    except Exception as e:
        logger.error(f"Proxy error for {path}: {e}")
        return jsonify({"error": f"Proxy error: {str(e)}"}), 500

@app.route('/images/<path:filepath>')
def serve_image(filepath):
    """Proxy image requests to backend"""
    try:
        url = f"{FrontendConfig.BACKEND_URL}/images/{filepath}"
        response = requests.get(url, timeout=30)
        return (response.content, response.status_code, response.headers.items())
    except Exception as e:
        logger.error(f"Image proxy error: {e}")
        return jsonify({"error": "Image not found"}), 404

if __name__ == '__main__':
    logger.info("="*60)
    logger.info("Starting FRC RAG Frontend Server")
    logger.info(f"Host: {FrontendConfig.HOST}:{FrontendConfig.PORT}")
    logger.info(f"Backend URL: {FrontendConfig.BACKEND_URL}")
    logger.info("="*60)
    
    app.run(
        host=FrontendConfig.HOST,
        port=FrontendConfig.PORT,
        debug=False
    )
