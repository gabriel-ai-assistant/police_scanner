# Police Scanner Web Frontend - Quick Start Guide

## 🚀 30-Second Setup

```bash
cd p:\Git\police_scanner
docker-compose up -d
```

Wait 30-60 seconds, then open browser to:

- **🖥️ Frontend**: http://localhost
- **📚 API Docs**: http://localhost:8000/docs
- **🗄️ Database**: http://localhost:8081
- **💾 MinIO**: http://localhost:9001

---

## 🎯 What You Get

### Admin Panel (Click "Admin" in sidebar)
1. **Geographic Sync** - Enable/disable countries, states, counties
2. **Playlist Manager** - Manage which playlists to monitor
3. **Processing Pipeline** - Watch call processing status

### Dashboard
- Real-time call statistics
- Transcription metrics
- Processing pipeline status
- System health

---

## 🔧 Troubleshooting

### Services won't start
```bash
# Check logs
docker-compose logs -f app_api

# Verify ports are available
# If not, edit docker-compose.yml to use different ports
```

### Frontend shows errors
```bash
# Rebuild frontend
docker-compose rebuild frontend
docker-compose restart frontend

# Or reinstall deps
cd frontend && npm install @radix-ui/react-tabs && cd ..
```

### API returns 500 errors
```bash
# Check database connection
docker-compose logs postgres

# Verify .env has correct credentials
```

---

## 📋 Service Ports

| Service | Port | URL |
|---------|------|-----|
| Frontend | 80 | http://localhost |
| API | 8000 | http://localhost:8000 |
| Database | 5432 | localhost:5432 |
| Redis | 6379 | localhost:6379 |
| MinIO | 9000 | localhost:9000 |
| Adminer | 8081 | http://localhost:8081 |

---

## 🛑 Stop Services

```bash
docker-compose down        # Stop and remove containers
docker-compose down -v     # Also remove volumes
```

---

## 📖 Full Documentation

- See `DEPLOYMENT.md` for complete setup guide
- See `IMPLEMENTATION_SUMMARY.md` for architecture details
- See http://localhost:8000/docs for API documentation

---

## 🆘 Key Admin Panel Features

### Geographic Sync (Admin → Geographic Sync)
✅ Enable/disable countries, states, counties for data sync
✅ Real-time toggle switches
✅ Hierarchical tree view

### Playlist Manager (Admin → Playlists)
✅ List all Broadcastify playlists
✅ Enable/disable monitoring per playlist
✅ Filter and search playlists

### Processing Pipeline (Admin → Monitoring)
✅ Watch calls through pipeline stages
✅ Visual status breakdown
✅ System statistics

---

## 🔗 API Examples

```bash
# Get health status
curl http://localhost:8000/api/health | jq

# Get dashboard metrics
curl http://localhost:8000/api/analytics/dashboard | jq

# List recent calls
curl http://localhost:8000/api/calls?limit=5 | jq

# Search transcripts
curl "http://localhost:8000/api/transcripts/search?q=police" | jq

# Get processing state
curl http://localhost:8000/api/system/processing-state | jq

# List countries
curl http://localhost:8000/api/geography/countries | jq
```

---

## ✨ Key Features

✅ **Web Interface** - Access scanner from browser
✅ **Admin Panel** - Configure sync settings
✅ **Dashboard** - Real-time metrics
✅ **Full-Text Search** - Search transcripts
✅ **API Documentation** - Interactive Swagger UI
✅ **Docker Deployment** - One-command setup

---

## 🎉 You're Ready!

Your Police Scanner web frontend is now running. Navigate to http://localhost and start monitoring!

For detailed information, see DEPLOYMENT.md or IMPLEMENTATION_SUMMARY.md
