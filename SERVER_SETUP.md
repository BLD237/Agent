# Server Setup Guide

## Quick Start

### Option 1: Run Directly (Development/Testing)

```bash
cd /var/www/Agent
source venv/bin/activate
python3 run_server.py
```

The server will start on port 8004 and the scheduler will run daily at 5 AM (GMT+1 / Africa/Douala timezone).

### Option 2: Run with Uvicorn Directly

```bash
cd /var/www/Agent
source venv/bin/activate
uvicorn main:app --host 0.0.0.0 --port 8004
```

### Option 3: Run as Systemd Service (Production - Recommended)

1. **Copy the service file to systemd:**
   ```bash
   sudo cp /var/www/Agent/job-opportunity-bot.service /etc/systemd/system/
   ```

2. **Update the service file paths if needed:**
   ```bash
   sudo nano /etc/systemd/system/job-opportunity-bot.service
   ```
   Make sure `WorkingDirectory` and `ExecStart` paths match your installation.

3. **Reload systemd:**
   ```bash
   sudo systemctl daemon-reload
   ```

4. **Start the service:**
   ```bash
   sudo systemctl start job-opportunity-bot
   ```

5. **Enable it to start on boot:**
   ```bash
   sudo systemctl enable job-opportunity-bot
   ```

6. **Check status:**
   ```bash
   sudo systemctl status job-opportunity-bot
   ```

7. **View logs:**
   ```bash
   sudo journalctl -u job-opportunity-bot -f
   ```

## Configuration

### Environment Variables

Make sure your `.env` file in `/var/www/Agent/` contains:

```bash
# Google Gemini API
GOOGLE_API_KEY=your-api-key-here

# SMTP Email Configuration
SMTP_EMAIL=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587

# Optional: Override port
PORT=8004
```

### Email Recipients

Edit `/var/www/Agent/job_config.py` and add email addresses to `DAILY_JOB_CONFIG["emails"]`:

```python
DAILY_JOB_CONFIG = {
    "emails": [
        "recipient1@example.com",
        "recipient2@example.com",
    ]
}
```

## Scheduler Configuration

The scheduler runs daily at **5:00 AM** in the **Africa/Douala timezone** (GMT+1).

To change the schedule, edit `/var/www/Agent/scheduler.py`:

```python
scheduler.add_job(
    daily_job_search,
    CronTrigger(hour=5, minute=0)  # Change hour and minute here
)
```

## Port Configuration

The server runs on port **8004** by default.

To change the port:
- Set `PORT` environment variable in `.env`
- Or edit `run_server.py` and change the default port

## Testing

1. **Test the API:**
   ```bash
   curl http://localhost:8004/metrics
   ```

2. **Test search endpoint:**
   ```bash
   curl -X POST http://localhost:8004/search-opportunities \
     -H "Content-Type: application/json" \
     -d '{"query": "test", "email": "your-email@example.com"}'
   ```

3. **Check if scheduler is running:**
   The scheduler starts automatically when the FastAPI app starts. Check logs to confirm.

## Troubleshooting

1. **Service won't start:**
   - Check logs: `sudo journalctl -u job-opportunity-bot -n 50`
   - Verify paths in service file
   - Check environment variables

2. **Scheduler not running:**
   - Check logs for scheduler startup message
   - Verify timezone is correct
   - Check that emails are configured in `job_config.py`

3. **Port already in use:**
   - Check what's using port 8004: `sudo lsof -i :8004`
   - Change port in `.env` or `run_server.py`

## Firewall (if needed)

If you need to expose the API externally:

```bash
sudo ufw allow 8004/tcp
```

