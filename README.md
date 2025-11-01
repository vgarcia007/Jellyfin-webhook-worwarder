# Jellyfin Webhook Forwarder

A Flask-based webhook forwarder that receives Jellyfin webhooks and sends notifications via ntfy.

## Features

- Receives Jellyfin webhooks
- Processes various event types (ItemAdded, etc.)
- Sends notifications via ntfy
- Optional file logging
- Docker support

## Installation

### Docker Compose (recommended)

1. Clone repository:
```bash
git clone <repository-url>
cd webhook_forwarder
```

2. Create your environment file:
```bash
cp .env.example .env
# Edit .env with your actual values
```

3. Start service:
```bash
docker-compose up -d
```

### Manual

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set environment variables:
```bash
export NTFY_SERVER=https://your-ntfy-server.com
export NTFY_TOPIC=your-topic
export NTFY_USER=your-username
export NTFY_PASS=your-password
```

3. Start application:
```bash
python app.py
```

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `NTFY_ENABLED` | `true` | Enables/disables ntfy notifications |
| `NTFY_SERVER` | `https://ntfy.sh` | ntfy server URL |
| `NTFY_TOPIC` | `jellyfin-media` | ntfy topic for notifications |
| `NTFY_USER` | - | Username for ntfy authentication |
| `NTFY_PASS` | - | Password for ntfy authentication |
| `NTFY_ICON` | `https://freilinger.ws/jellyfin.png` | Icon URL for notifications |
| `FILE_LOGS` | `false` | Enables file logging in `logs/` |

### Jellyfin Webhook Configuration

1. Go to Jellyfin **Dashboard** > **Plugins** > **Webhooks**
2. Add new webhook URL: `http://your-server:8080/webhook`
3. Select events to monitor (e.g. Item Added)

## API Endpoints

- `POST /webhook` - Receives Jellyfin webhooks
- `GET /health` - Health check endpoint

## Logs

When `FILE_LOGS=true` is set, all received requests are stored in `logs/`:
- `.json` files contain processed webhook data
- `.meta.json` files contain metadata (headers, IP, etc.)
- `.body.bin` files contain raw data when parsing fails

## Development

### Local Development

1. Create virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate     # Windows
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Start application in debug mode:
```bash
export FLASK_ENV=development
python app.py
```

### Docker Build

```bash
docker build -t webhook-forwarder .
docker run -p 8080:8080 webhook-forwarder
```

## Troubleshooting

- **No notifications**: Check ntfy configuration and network connection
- **Webhook errors**: Enable `FILE_LOGS=true` to analyze request details
- **Docker issues**: Check port mappings and volume mounts

## License

MIT License
