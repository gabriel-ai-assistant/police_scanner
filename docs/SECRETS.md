# Secrets & Environment Variables

All secrets are managed via environment variables (`.env` file). Copy `.env.example` to `.env` and fill in real values.

> **Never commit `.env` to version control.**

## Broadcastify

| Variable | Description | Example |
|---|---|---|
| `BROADCASTIFY_URL` | Calls API endpoint | `https://www.broadcastify.com/calls/apis/live-calls` |
| `BROADCASTIFY_PLAYLIST_UUID` | Playlist UUID to monitor | `1e4cdc91-c420-...` |
| `BROADCASTIFY_SESSION_KEY` | Session key for auth | `5fc76996-bb98` |
| `BROADCASTIFY_COOKIE__EOI` | `__eoi` cookie | |
| `BROADCASTIFY_COOKIE__GADS` | `__gads` cookie | |
| `BROADCASTIFY_COOKIE__GPI` | `__gpi` cookie | |
| `BROADCASTIFY_COOKIE_AWL` | `_awl` cookie | |
| `BROADCASTIFY_POLL_INTERVAL` | Seconds between polls | `3` |

## Signal Alerting

| Variable | Description | Example |
|---|---|---|
| `SIGNAL_FROM_NUMBER` | Sender phone number | `+14699966521` |
| `SIGNAL_RECIPIENTS` | Comma-separated recipient numbers | `+14252390792,+15551234567` |
| `SIGNAL_CLI_BIN` | Path to signal-cli binary | `/opt/scanner/signal-cli/.../signal-cli` |

## Whisper (Transcription)

| Variable | Description | Default |
|---|---|---|
| `WHISPER_MODEL` | Whisper model size | `base` |
| `WHISPER_DEVICE` | `cpu` or `cuda` | `cpu` |

## Logging

| Variable | Description | Default |
|---|---|---|
| `LOG_LEVEL` | Python log level | `INFO` |
| `LOG_CONSOLE` | Also log to stdout | `false` |
