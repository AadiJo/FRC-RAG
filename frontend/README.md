# FRC RAG Frontend

Frontend server for the FRC RAG application. This is a lightweight Flask server that serves the web interface and proxies API requests to the backend.

## 🚀 Quick Start

### 1. Install Dependencies

```bash
cd frontend
pip install -r requirements.txt
```

### 2. Configure Environment

Copy the example environment file and update it:

```bash
cp .env.example .env
```

Edit `.env` and set the `BACKEND_URL` to point to your backend server:

- **Local development**: `http://localhost:5000`
- **Remote backend**: `https://your-backend-url.com`
- **Tunnel URL**: Use your ngrok/cloudflare tunnel URL

### 3. Run the Server

```bash
./start.sh
# Or manually:
python server.py
```

The frontend will be available at:
- Default: `http://localhost:80`
- Custom port: Set `FRONTEND_PORT` in `.env`

## 📁 Structure

```
frontend/
├── server.py          # Frontend server with API proxy
├── requirements.txt   # Python dependencies
├── .env.example      # Environment configuration template
├── templates/        # HTML templates
│   └── index.html   # Main chat interface
└── static/          # Static assets
    └── style.css    # Styles
```

## 🔧 Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `FRONTEND_HOST` | Host to bind to | `0.0.0.0` |
| `FRONTEND_PORT` | Port to listen on | `80` |
| `BACKEND_URL` | Backend API URL | `http://localhost:5000` |
| `LOG_LEVEL` | Logging level | `INFO` |
| `ALLOWED_ORIGINS` | CORS allowed origins | `*` |

## 🌐 Deployment

### Deploy to VPS

This is the **only** folder you need to deploy to your VPS!

1. **Use the deployment script**:
   ```bash
   ./deploy.sh
   ```

2. **Or manually upload frontend folder to VPS**:
   ```bash
   rsync -avz --progress . user@your-vps-ip:/var/www/frc-rag
   ```

3. **SSH into VPS and setup**:
   ```bash
   ssh user@your-vps-ip
   cd /var/www/frc-rag
   pip install -r requirements.txt
   cp .env.example .env
   ```

3. **Configure .env**:
   - Set `BACKEND_URL` to your backend server URL (could be your local PC via tunnel)
   - Set `FRONTEND_PORT=80` (or `443` for HTTPS)

4. **Run with systemd** (recommended):
   ```bash
   sudo systemctl start frc-rag-frontend
   ```

### Using with Tunnels

If your backend is on your local PC and exposed via ngrok/cloudflare:

1. Start backend with tunnel on your PC
2. Copy the tunnel URL (e.g., `https://abc123.ngrok.io`)
3. Set `BACKEND_URL=https://abc123.ngrok.io` in frontend `.env`
4. Deploy only the frontend folder to VPS

## 🔒 Security

For production:

1. **Update CORS origins**:
   ```env
   ALLOWED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
   ```

2. **Use HTTPS**: Configure reverse proxy (nginx/caddy) for SSL

3. **Rate limiting**: Handled by backend, but consider adding nginx rate limiting

## 📝 API Proxy

The frontend server automatically proxies all `/api/*` requests to the backend:

- Frontend: `https://yourdomain.com/api/query`
- → Backend: `http://localhost:5000/api/query`

This allows you to:
- Keep backend private (only accessible via tunnel/VPN)
- Deploy frontend separately from backend
- Change backend location without updating frontend code

## 🐛 Troubleshooting

### Backend Unavailable
```
Error: Backend unavailable
```
**Solution**: Check `BACKEND_URL` in `.env` and ensure backend is running

### CORS Errors
```
Error: CORS policy blocked
```
**Solution**: Update `ALLOWED_ORIGINS` in `.env` to include your domain

### Port 80 Requires Root
```
Error: Permission denied
```
**Solution**: Either:
- Run as root: `sudo python server.py`
- Use port > 1024: Set `FRONTEND_PORT=8080`
- Use reverse proxy (nginx/caddy)