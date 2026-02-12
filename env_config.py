"""
Centralized configuration loader.
Reads from environment variables (preferred) with fallback to config.yaml.
"""
import os

import yaml

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(SCRIPT_DIR, "config.yaml")


def _load_yaml():
    """Load config.yaml as fallback, return empty dict if missing."""
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH) as f:
            return yaml.safe_load(f) or {}
    return {}


def _env(key, default=None):
    """Get env var, stripping whitespace."""
    val = os.getenv(key)
    return val.strip() if val else default


def load_config():
    """
    Build unified config dict. Environment variables take precedence
    over config.yaml values for all secrets/credentials.
    """
    yml = _load_yaml()
    b = yml.get("broadcastify", {})
    d = yml.get("data", {})
    k = yml.get("keywords", {})
    s = yml.get("signal", {})
    w = yml.get("whisper", {})
    log_cfg = yml.get("logging", {})

    return {
        "broadcastify": {
            "url": _env("BROADCASTIFY_URL", b.get("url", "https://www.broadcastify.com/calls/apis/live-calls")),
            "playlist_uuid": _env("BROADCASTIFY_PLAYLIST_UUID", b.get("playlist_uuid", "")),
            "sessionKey": _env("BROADCASTIFY_SESSION_KEY", b.get("sessionKey", "")),
            "cookies": {
                "__eoi": _env("BROADCASTIFY_COOKIE__EOI", (b.get("cookies") or {}).get("__eoi", "")),
                "__gads": _env("BROADCASTIFY_COOKIE__GADS", (b.get("cookies") or {}).get("__gads", "")),
                "__gpi": _env("BROADCASTIFY_COOKIE__GPI", (b.get("cookies") or {}).get("__gpi", "")),
                "_awl": _env("BROADCASTIFY_COOKIE_AWL", (b.get("cookies") or {}).get("_awl", "")),
            },
            "headers": b.get("headers", {
                "Accept": "*/*",
                "Accept-Language": "en-US,en;q=0.9",
                "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                "Origin": "https://www.broadcastify.com",
                "Referer": "https://www.broadcastify.com/calls/playlists/",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
                "X-Requested-With": "XMLHttpRequest",
            }),
            "last_pos": b.get("last_pos", 0),
            "poll_interval_seconds": int(_env("BROADCASTIFY_POLL_INTERVAL", b.get("poll_interval_seconds", 3))),
        },
        "data": {
            "audio_dir": d.get("audio_dir", "data/audio"),
            "transcript_dir": d.get("transcript_dir", "data/transcripts"),
            "seen_calls_file": d.get("seen_calls_file", "data/seen_calls.txt"),
            "delete_audio_after_transcribe": d.get("delete_audio_after_transcribe", True),
        },
        "keywords": {
            "file": k.get("file", "keywords.txt"),
            "case_sensitive": k.get("case_sensitive", False),
            "min_hits": k.get("min_hits", 1),
        },
        "signal": {
            "from_number": _env("SIGNAL_FROM_NUMBER", s.get("from_number", "")),
            "recipients": [
                r.strip()
                for r in _env("SIGNAL_RECIPIENTS", ",".join(s.get("recipients", []))).split(",")
                if r.strip()
            ],
            "signal_cli_bin": _env("SIGNAL_CLI_BIN", s.get("signal_cli_bin", "signal-cli")),
            "message_template": s.get("message_template",
                "[Police Scanner]\nKeyword(s): {keywords}\nCall ID: {call_id}\nTranscript:\n{transcript}\n"),
        },
        "whisper": {
            "model": _env("WHISPER_MODEL", w.get("model", "base")),
            "device": _env("WHISPER_DEVICE", w.get("device", "cpu")),
            "language": w.get("language", "en"),
        },
        "logging": {
            "level": _env("LOG_LEVEL", log_cfg.get("level", "INFO")),
            "console": _env("LOG_CONSOLE", str(log_cfg.get("console", False))).lower() in ("true", "1", "yes"),
            "logfile": log_cfg.get("logfile", "data/logs/scanner.log"),
        },
    }
