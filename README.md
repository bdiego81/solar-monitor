Markdown
# Solar Monitor

Lightweight telemetry service written in Python/FastAPI to monitor Voltronic / Axpert solar inverters via RS232/USB. Extracted metrics are parsed and published over MQTT to InfluxDB and Grafana, with integrated alert notifications sent via Telegram.

## Features

- **Inverter Telemetry**: Polls operational data (PV input, battery status, grid voltage, load output) using `mpp-solar` / serial connection.
- **Metrics Pipeline**: Publishes JSON payloads over MQTT for continuous ingestion into InfluxDB and visualization in Grafana.
- **Telegram Alerts**: Configurable trigger thresholds for voltage drops, fault states, and grid failover notifications.
- **Docker Ready**: Multi-architecture Docker builds (`amd64`, `arm64`) for deployment on Raspberry Pi or Linux servers.

## Quickstart

### 1. Configuration

Copy the example environment file and update it with your settings:

```bash
cp .env.example .env
Set your configuration parameters:

Code snippet
SERIAL_PORT=/dev/ttyUSB0
INVERTER_MODEL=Axpert_MAX_7200
MQTT_BROKER=192.168.1.100
MQTT_PORT=1883
MQTT_TOPIC=solar/telemetry
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
POLL_INTERVAL=5
2. Docker Compose Deployment
Run the container stack using Docker Compose:

Bash
docker compose up -d
3. Local Development
Install dependencies and run the service locally:

Bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python main.py
Telemetry Payload
Sample MQTT JSON payload emitted by the daemon:

JSON
{
  "pv_input_watts": 3450,
  "battery_voltage": 52.4,
  "battery_capacity_pct": 88,
  "ac_output_watts": 1200,
  "inverter_mode": "Line",
  "temperature_c": 38.5
}
License
MIT
