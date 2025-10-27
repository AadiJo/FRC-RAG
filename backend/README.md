# FRC RAG Backend

Backend server for the FRC RAG application. Handles RAG processing, Ollama integration, and provides API endpoints.

## 🚀 Quick Start

### 1. Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 2. Configure Environment

Copy the example environment file and update it:

```bash
cp .env.example .env
```

Edit `.env` with your settings. See [Configuration](#configuration) below.

### 3. Start Ollama

Make sure Ollama is running:

```bash
ollama serve
```

Install required model:

```bash
ollama pull mistral
```

### 4. Run the Server

```bash
./start.sh
# Or manually:
python app.py
```

The backend API will be available at `http://localhost:5000`

## 📁 Structure

```
backend/
├── app.py                # Main backend server
├── vps_server.py        # Alternative VPS server (deprecated)
├── requirements.txt     # Python dependencies
├── .env.example        # Environment configuration template
├── src/                # Source code
│   ├── core/          # Core RAG components
│   │   ├── query_processor.py    # Query processing logic
│   │   └── game_piece_mapper.py  # Game piece context mapping
│   ├── server/        # Server components
│   │   ├── config.py           # Configuration management
│   │   ├── rate_limiter.py     # Rate limiting
│   │   ├── ollama_proxy.py     # Ollama proxy
│   │   └── tunnel.py           # Tunneling utilities
│   └── utils/         # Utilities
│       ├── database_setup.py   # Database initialization
│       ├── query_cache.py      # Query caching
│       ├── project_status.py   # Status monitoring
│       └── test_setup.py       # Setup testing
├── data/              # Data directory (PDFs, images)
├── db/                # ChromaDB database
└── logs/              # Log files
```

## 🔧 Configuration

### Environment Variables

| Category | Variable | Description | Default |
|----------|----------|-------------|---------|
| **Server** | `ENVIRONMENT` | Environment (development/production) | `production` |
| | `SERVER_HOST` | Host to bind to | `0.0.0.0` |
| | `SERVER_PORT` | Port to listen on | `5000` |
| | `DEBUG` | Enable debug mode | `false` |
| **Ollama** | `OLLAMA_HOST` | Ollama server host | `localhost` |
| | `OLLAMA_PORT` | Ollama server port | `11434` |
| | `OLLAMA_TIMEOUT` | Request timeout (seconds) | `30` |
| **Rate Limiting** | `RATE_LIMIT_REQUESTS` | Requests per window | `60` |
| | `RATE_LIMIT_WINDOW` | Window size (minutes) | `1` |
| **Database** | `CHROMA_PATH` | ChromaDB path | `db` |
| | `IMAGES_PATH` | Images directory | `data/images` |
| **Security** | `API_KEY_REQUIRED` | Require API key | `false` |
| | `VALID_API_KEYS` | Comma-separated API keys | `` |
| **Logging** | `LOG_LEVEL` | Logging level | `INFO` |
| | `LOG_FILE` | Log file path | `logs/backend.log` |
| **CORS** | `CORS_ORIGINS` | Allowed origins | `*` |
| **Tunneling** | `TUNNEL_SERVICE` | Tunnel service (ngrok/cloudflare) | `` |
| | `TUNNEL_AUTH_TOKEN` | Tunnel auth token | `` |

## 🌐 API Endpoints

### Query Endpoints

- `POST /api/query` - Process RAG query
- `POST /api/query/stream` - Stream RAG query response
- `POST /api/suggestions` - Get game piece suggestions

### Health & Monitoring

- `GET /health` - Comprehensive health check
- `GET /api/stats` - Server statistics
- `GET /api/cache/stats` - Cache statistics

### Cache Management

- `POST /api/cache/clear` - Clear cache (requires API key)
- `POST /api/cache/reset-stats` - Reset cache statistics

### Utility Endpoints

- `GET /api/seasons` - Get available seasons
- `POST /api/feedback` - Submit user feedback
- `GET /images/<path>` - Serve images

### Tunnel Management

- `POST /api/tunnel` - Start/stop tunnel service

## 🔒 Security

### API Key Authentication

Enable API key authentication for production:

```env
API_KEY_REQUIRED=true
VALID_API_KEYS=your-secret-key-1,your-secret-key-2
```

Include API key in requests:

```bash
curl -H "X-API-Key: your-secret-key-1" http://localhost:5000/api/query
```

### Rate Limiting

Built-in rate limiting prevents abuse:

- Default: 60 requests per minute per client
- Configurable via `RATE_LIMIT_REQUESTS` and `RATE_LIMIT_WINDOW`
- Client identified by IP address

### CORS

Configure allowed origins:

```env
# Development
CORS_ORIGINS=*

# Production
CORS_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
```

## 🚇 Tunneling

Expose local backend to the internet using ngrok or Cloudflare:

### Using ngrok

1. Install ngrok: `brew install ngrok` (or download from ngrok.com)
2. Get auth token from ngrok.com
3. Configure:
   ```env
   TUNNEL_SERVICE=ngrok
   TUNNEL_AUTH_TOKEN=your-ngrok-token
   ```
4. Start backend - tunnel URL will be displayed in logs

### Using Cloudflare

1. Install cloudflared
2. Configure:
   ```env
   TUNNEL_SERVICE=cloudflare
   ```
3. Start backend - tunnel URL will be displayed in logs

## 📊 Monitoring

### Health Check

```bash
curl http://localhost:5000/health
```

Returns:
- Component health status
- Ollama connectivity
- Database status
- Cache statistics
- Tunnel status

### Statistics

```bash
curl http://localhost:5000/api/stats
```

Returns:
- Request counts
- Rate limit stats
- Cache hit rates
- Performance metrics

## 🐛 Troubleshooting

### Ollama Connection Failed

```
Error: Ollama service is not available
```

**Solution**:
1. Check Ollama is running: `curl http://localhost:11434/api/tags`
2. Verify `OLLAMA_HOST` and `OLLAMA_PORT` in `.env`
3. Install model: `ollama pull mistral`

### Database Not Found

```
Error: Query processor not initialized
```

**Solution**:
1. Check `CHROMA_PATH` exists: `ls -la db/`
2. Run database setup: `python src/utils/database_setup.py`
3. Verify PDF files in `data/` directory

### Rate Limit Exceeded

```
Error: Rate limit exceeded
```

**Solution**:
1. Increase limits in `.env`:
   ```env
   RATE_LIMIT_REQUESTS=120
   ```
2. Wait for rate limit window to reset
3. Use API key for higher limits (if configured)

### Import Errors

```
ModuleNotFoundError: No module named 'src'
```

**Solution**:
1. Ensure you're in the backend directory: `cd backend`
2. Install dependencies: `pip install -r requirements.txt`
3. Run from backend directory: `python app.py`

## 🔄 Database Setup

### Initial Setup

```bash
cd backend
python src/utils/database_setup.py
```

This will:
1. Create ChromaDB database
2. Process PDFs in `data/` directory
3. Extract and OCR images
4. Generate embeddings

### Adding New Data

1. Add PDF files to `data/` directory
2. Run database setup again
3. Restart backend server

## 📝 Logging

Logs are written to:
- Console (stdout)
- File: `logs/backend.log` (configurable via `LOG_FILE`)

Log levels:
- `DEBUG` - Detailed information for debugging
- `INFO` - General information (default)
- `WARNING` - Warning messages
- `ERROR` - Error messages

Set log level in `.env`:
```env
LOG_LEVEL=DEBUG
```