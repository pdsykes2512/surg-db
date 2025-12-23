# Systemd Service Files

This directory contains the systemd service configuration files for the Surgical Database application.

## Services

### surg-db-backend.service
Backend API service running on port 8000.

**Installation:**
```bash
sudo cp services/surg-db-backend.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable surg-db-backend.service
sudo systemctl start surg-db-backend.service
```

### surg-db-frontend.service
Frontend Vite dev server running on port 3000.

**Installation:**
```bash
sudo cp services/surg-db-frontend.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable surg-db-frontend.service
sudo systemctl start surg-db-frontend.service
```

## MongoDB Container

The MongoDB container should be configured with restart policy:
```bash
docker update --restart=always mongodb
```

## Service Management

**Check status:**
```bash
systemctl status surg-db-backend.service
systemctl status surg-db-frontend.service
```

**View logs:**
```bash
journalctl -u surg-db-backend.service -f
journalctl -u surg-db-frontend.service -f
```

**Restart services:**
```bash
systemctl restart surg-db-backend.service
systemctl restart surg-db-frontend.service
```

## Notes

- Backend service includes MongoDB authentication environment variables
- Both services are configured to restart automatically on failure
- Logs are written to `~/.tmp/backend.log` and `~/.tmp/frontend.log`
- Services start automatically on system boot
