# Service Management

## Quick Reference

### Start/Stop/Restart Services
```bash
# Start both services
sudo systemctl start surg-db-backend.service surg-db-frontend.service

# Stop both services
sudo systemctl stop surg-db-backend.service surg-db-frontend.service

# Restart both services (after data updates)
sudo systemctl restart surg-db-backend.service surg-db-frontend.service

# Check status
sudo systemctl status surg-db-backend.service surg-db-frontend.service
```

### View Logs
```bash
# Backend logs
tail -f ~/.tmp/backend.log

# Frontend logs  
tail -f ~/.tmp/frontend.log

# Systemd journal logs
journalctl -u surg-db-backend.service -f
journalctl -u surg-db-frontend.service -f
```

### Test Endpoints
```bash
# Test backend API
curl http://localhost:8000/api/patients/?limit=1

# Test frontend
curl http://localhost:3000
```

### Troubleshooting

#### Port Already in Use
If you get "address already in use" errors:
```bash
# Find process on port 8000
lsof -ti:8000

# Kill specific process
kill -9 $(lsof -ti:8000)

# Or kill all uvicorn processes
pkill -9 uvicorn
```

#### Service Won't Start
```bash
# Stop service completely
sudo systemctl stop surg-db-backend.service

# Kill any remaining processes
pkill -9 uvicorn
pkill -9 python3

# Clear port
kill -9 $(lsof -ti:8000)

# Start service
sudo systemctl start surg-db-backend.service
```

## Service Configuration

### Backend Service
- File: `/etc/systemd/system/surg-db-backend.service`
- Working Directory: `/root/surg-db`
- Port: 8000
- Logs: `~/.tmp/backend.log`
- Environment: Loads from `/root/surg-db/.env`

### Frontend Service
- File: `/etc/systemd/system/surg-db-frontend.service`
- Working Directory: `/root/surg-db/frontend`
- Port: 3000
- Logs: `~/.tmp/frontend.log`

## After Data Migration or Updates

When you update data in MongoDB (e.g., running migration scripts), restart the backend service to ensure it picks up the changes:

```bash
sudo systemctl restart surg-db-backend.service
```

## Enable Services on Boot

Services are already enabled to start automatically on system boot. To verify:
```bash
sudo systemctl is-enabled surg-db-backend.service
sudo systemctl is-enabled surg-db-frontend.service
```
