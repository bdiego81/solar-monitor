# Solar Monitor Pro

Real-time solar inverter monitoring dashboard with Telegram alerts — designed for ShineMonitor-compatible inverters.

## Features

- ⚡ **Live Telemetry Dashboard** — PV power, battery level, grid status, load, and temperature updated in real time
- 📊 **Historical Charts** — Browse daily energy production and consumption trends
- 🔔 **Telegram Alerts** — Instant notifications for grid loss, overload, low battery, high temperature, and telemetry watchdog
- 📋 **Automated Daily Reports** — End-of-day summary sent to your Telegram at a configurable time
- ⚙️ **Web-Based Configuration** — Set credentials, alert thresholds, and Telegram integration entirely from the browser — no `.env` files needed
- 🔒 **Secure by Default** — API documentation (`/docs`) is disabled in production; sensitive endpoints are hidden from the OpenAPI schema

## Quick Start

### Using Docker Compose (Recommended)

Create a `docker-compose.yml` file:

```yaml
services:
  solar-monitor:
    image: bdiego81/solar-monitor:latest
    container_name: solar-monitor
    restart: unless-stopped
    ports:
      - "8000:8000"
    environment:
      - DEBUG=false
      - TZ=America/Santiago
    volumes:
      - ./data:/home/appuser/app/data
```

Then run:

```bash
docker compose up -d
```

### Using Docker Run

```bash
docker run -d --name solar-monitor --restart unless-stopped -p 8000:8000 -e DEBUG=false -e TZ=America/Santiago -v ./data:/home/appuser/app/data bdiego81/solar-monitor:latest
```

## Initial Setup

1. Open your browser and navigate to `http://<your-host-ip>:8000`
2. Go to the **Settings** tab (⚙️)
3. Enter your **ShineMonitor** username and password
4. *(Optional)* Enter your **Telegram Bot Token** and **Chat ID** to enable alerts
5. Click **Save** — all settings are persisted to `data/config.json` and survive container restarts and image updates

> **No `.env` file is required.** All configuration is managed through the web interface.

## Supported Architectures

| Architecture | Tag |
|---|---|
| `linux/amd64` | `latest` |
| `linux/arm64` | `latest` |

Tested on: Raspberry Pi 3/4/5 (64-bit OS), x86_64 servers, and NAS devices.

## Data Persistence

All configuration and runtime data is stored in a single volume:

| Container Path | Purpose |
|---|---|
| `/home/appuser/app/data` | Configuration (`config.json`) and runtime data |

Mount `./data` to this path to persist your settings across container updates.

## Environment Variables (Optional)

All settings can be configured from the web UI. Environment variables are only needed for advanced use cases:

| Variable | Default | Description |
|---|---|---|
| `DEBUG` | `false` | Set to `true` to enable Swagger UI at `/docs` and ReDoc at `/redoc` |
| `PORT` | `8000` | Internal application port |

## Enabling Debug Mode

To temporarily enable the API documentation for development or troubleshooting:

```yaml
services:
  solar-monitor:
    image: bdiego81/solar-monitor:latest
    environment:
      - DEBUG=true
    # ...
```

Then access `http://<your-host-ip>:8000/docs` for the interactive API explorer.

## Ports

| Port | Protocol | Description |
|---|---|---|
| `8000` | TCP | Web dashboard and REST API |

## Health Check

The container includes a built-in health check at `GET /health` that returns `{"status": "healthy"}`.

## Source Code

[GitHub Repository](https://github.com/bdiego81/solar-monitor)

## License

MIT
