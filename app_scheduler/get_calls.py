#!/usr/bin/env python3
"""
Broadcastify Calls Downloader + Audio Optimizer (env-driven)
Pulls new calls, converts each MP3 → optimized 16-kHz WAV,
uploads to MinIO, and logs ingestion.
"""

import asyncio, aiohttp, asyncpg, os, json, time, boto3, logging, subprocess, sys
from botocore.client import Config
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
import librosa, numpy as np

# Import JWT token cache for efficient token reuse
sys.path.insert(0, '/app/shared_bcfy')
from token_cache import get_jwt_token

# Import database connection pool
from db_pool import get_connection, release_connection

# =========================================================
# Logging
# =========================================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
log = logging.getLogger("bcfy_ingest")

# =========================================================
# Environment
# =========================================================
load_dotenv()

PGUSER         = os.getenv("PGUSER")
PGPASSWORD     = os.getenv("PGPASSWORD")
PGDATABASE     = os.getenv("PGDATABASE")
PGHOST         = os.getenv("PGHOST", "localhost")
PGPORT         = os.getenv("PGPORT", "5432")
DB_URL         = f"postgresql://{PGUSER}:{PGPASSWORD}@{PGHOST}:{PGPORT}/{PGDATABASE}"

BCFY_BASE      = os.getenv("BCFY_BASE_URL", "https://api.bcfy.io")
CALLS_BASE     = f"{BCFY_BASE}/calls/v1"
COLLECT_INTERVAL_SEC = int(os.getenv("COLLECT_INTERVAL_SEC", "30"))

MINIO_ENDPOINT       = os.getenv("MINIO_ENDPOINT", "localhost:9000")
MINIO_ROOT_USER      = os.getenv("MINIO_ROOT_USER", "admin")
MINIO_ROOT_PASSWORD  = os.getenv("MINIO_ROOT_PASSWORD", "adminadmin")
MINIO_BUCKET         = os.getenv("MINIO_BUCKET", "feeds")
MINIO_BUCKET_PATH    = os.getenv("AUDIO_BUCKET_PATH", "calls")
MINIO_USE_SSL        = os.getenv("MINIO_USE_SSL", "false").lower() == "true"

TEMP_DIR        = os.getenv("TEMP_AUDIO_DIR", "/app/shared_bcfy/tmp")
AUDIO_SR        = int(os.getenv("AUDIO_SAMPLE_RATE", "16000"))
AUDIO_TARGET_DB = float(os.getenv("AUDIO_TARGET_DB", "-20"))

os.makedirs(TEMP_DIR, exist_ok=True)
log.info(f"Temp audio directory: {TEMP_DIR}")

# =========================================================
# MinIO Client
# =========================================================
log.info(f"Connecting to MinIO endpoint: {MINIO_ENDPOINT}")
s3 = boto3.client(
    "s3",
    endpoint_url=f"http{'s' if MINIO_USE_SSL else ''}://{MINIO_ENDPOINT}",
    aws_access_key_id=MINIO_ROOT_USER,
    aws_secret_access_key=MINIO_ROOT_PASSWORD,
    config=Config(signature_version="s3v4"),
    region_name="us-east-1",
)
try:
    s3.head_bucket(Bucket=MINIO_BUCKET)
except Exception:
    s3.create_bucket(Bucket=MINIO_BUCKET)

# =========================================================
# Database
# =========================================================
async def verify_schema():
    """Verify required columns exist before starting ingestion.

    Checks for columns added in migration 005_s3_hierarchical.sql.
    Raises RuntimeError if required columns are missing.
    """
    conn = await get_connection()
    try:
        result = await conn.fetch("""
            SELECT column_name FROM information_schema.columns
            WHERE table_name = 'bcfy_calls_raw'
            AND column_name IN ('playlist_uuid', 's3_key_v2')
        """)
        columns = [r['column_name'] for r in result]

        missing = []
        if 'playlist_uuid' not in columns:
            missing.append('playlist_uuid')
        if 's3_key_v2' not in columns:
            missing.append('s3_key_v2')

        if missing:
            raise RuntimeError(f"Missing required columns: {missing} - run migration 005_s3_hierarchical.sql")

        log.info("Schema verification passed: playlist_uuid and s3_key_v2 columns exist")
    finally:
        await release_connection(conn)


# =========================================================
# HTTP (with API call tracking)
# =========================================================
async def fetch_json(session, url, token, conn=None, params=None):
    """Fetch JSON with optional API call tracking and query parameters."""
    start = time.time()
    status_code = 0
    error_msg = None

    try:
        # Debug logging for JWT token
        log.debug(f"Using JWT token: {token[:50]}...")
        log.debug(f"Making request to: {url} with params: {params}")
        async with session.get(url, headers={"Authorization": f"Bearer {token}"}, params=params) as r:
            text = await r.text()
            status_code = r.status
            duration_ms = int((time.time() - start) * 1000)

            # Log to database if connection provided
            if conn:
                try:
                    await conn.execute("""
                        INSERT INTO api_call_metrics
                        (endpoint, status_code, duration_ms, response_size)
                        VALUES ($1, $2, $3, $4)
                    """, url, status_code, duration_ms, len(text))
                except Exception as metrics_err:
                    log.warning(f"API metrics logging failed: {metrics_err}")

            log.info(f"HTTP {r.status} ({len(text)} bytes, {duration_ms}ms) → {url}")

            if r.status != 200:
                raise Exception(f"HTTP {r.status}: {url}")

            try:
                data = json.loads(text)
            except Exception as e:
                raise Exception(f"Bad JSON {url}: {e}")

            return data

    except Exception as e:
        duration_ms = int((time.time() - start) * 1000)
        error_msg = str(e)

        # Log failed API call
        if conn:
            try:
                await conn.execute("""
                    INSERT INTO api_call_metrics
                    (endpoint, status_code, duration_ms, error)
                    VALUES ($1, $2, $3, $4)
                """, url, status_code, duration_ms, error_msg)
            except Exception as metrics_err:
                log.warning(f"API metrics logging failed for error case: {metrics_err}")

        raise

# =========================================================
# Audio Analysis + Conversion
# =========================================================
def analyze_audio_enhanced(path):
    """Enhanced audio analysis for adaptive multi-tier processing."""
    try:
        y, sr = librosa.load(path, sr=None, mono=True)

        # Existing metrics
        rms = 20 * np.log10(np.mean(librosa.feature.rms(y=y)) + 1e-9)
        centroid = librosa.feature.spectral_centroid(y=y, sr=sr).mean()
        noise_floor = np.percentile(np.abs(y), 10)

        # NEW: Enhanced metrics
        dynamic_range = np.percentile(np.abs(y), 95) - noise_floor
        zero_crossing_rate = librosa.feature.zero_crossing_rate(y).mean()

        # NEW: Quality scoring (0-100 scale)
        snr_estimate = 20 * np.log10(dynamic_range / (noise_floor + 1e-9))
        quality_score = min(100, max(0, (snr_estimate + 10) * 5))

        return {
            'quality_score': quality_score,
            'snr_estimate': snr_estimate,
            'rms': rms,
            'spectral_centroid': centroid,
            'noise_floor': noise_floor,
            'dynamic_range': dynamic_range,
            'zero_crossing_rate': zero_crossing_rate
        }
    except Exception as e:
        log.error(f"Audio analysis failed: {e}")
        # Return default values for unknown quality
        return {
            'quality_score': 50,
            'snr_estimate': 10,
            'rms': -20,
            'spectral_centroid': 3000,
            'noise_floor': 0.002,
            'dynamic_range': 0.1,
            'zero_crossing_rate': 0.1
        }

# Legacy function for backwards compatibility
def analyze_audio(path):
    """Legacy function - use analyze_audio_enhanced() instead."""
    analysis = analyze_audio_enhanced(path)
    return analysis['rms'], analysis['spectral_centroid'], analysis['noise_floor']

def build_tier1_filters(analysis):
    """Build filter chain for clean audio (quality_score > 70).

    Light processing to preserve original quality.
    """
    filters = [
        "highpass=f=300:poles=2",
        "lowpass=f=3400:poles=2",
        "afftdn=nf=-20:nt=w",
        "speechnorm=peak=0.95:expansion=2:compression=2",
        f"loudnorm=I={AUDIO_TARGET_DB}:LRA=11:TP=-1.5"
    ]
    return filters

def build_tier2_filters(analysis):
    """Build filter chain for moderate quality (40 < quality_score <= 70).

    Standard police radio processing with noise reduction and speech enhancement.
    """
    filters = [
        "adeclick=threshold=0.1",
        "highpass=f=300:poles=2",
        "afwtdn=percent=75:profile=true:adaptive=true",
        "afftdn=nf=-23:nt=w",
        "lowpass=f=3400:poles=2",
        "equalizer=f=1000:width_type=o:width=1.5:g=3",
        "speechnorm=peak=0.95:expansion=2:compression=2",
        "agate=threshold=0.02:release=100",
        f"loudnorm=I={AUDIO_TARGET_DB}:LRA=11:TP=-1.5"
    ]
    return filters

def build_tier3_filters(analysis):
    """Build filter chain for poor quality (quality_score <= 40).

    Aggressive multi-stage processing for severely degraded audio.
    """
    filters = [
        "adeclick=threshold=0.1",
        "highpass=f=300:poles=2",
        "afwtdn=percent=85:profile=true:adaptive=true:softness=2",
        "afftdn=nf=-25:nt=w:tn=true",
        "anlmdn=s=0.00005:p=0.002:r=0.006:m=15",
        "lowpass=f=3400:poles=2",
        "equalizer=f=1000:width_type=o:width=1.5:g=4",
        "acompressor=threshold=-24dB:ratio=4:attack=5:release=50:makeup=auto",
        "speechnorm=peak=0.95:expansion=3:compression=3",
        "agate=threshold=0.03:release=80",
        f"loudnorm=I={AUDIO_TARGET_DB}:LRA=11:TP=-1.5"
    ]
    return filters

def build_fallback_command(input_path, output_path):
    """Fallback command if audio analysis fails."""
    filter_chain = f"loudnorm=I={AUDIO_TARGET_DB}:LRA=11:TP=-1.5,afftdn=nf=-20"
    return [
        "ffmpeg", "-hide_banner", "-loglevel", "warning", "-y",
        "-i", input_path,
        "-ac", "1", "-ar", str(AUDIO_SR), "-c:a", "pcm_s16le",
        "-filter:a", filter_chain,
        output_path
    ]

def build_ffmpeg_command(input_path, output_path):
    """Build adaptive FFmpeg command with quality-based tier selection.

    Returns: (cmd, analysis) tuple for command execution and logging
    """
    try:
        # Analyze audio characteristics
        analysis = analyze_audio_enhanced(input_path)

        # Log analysis results
        log.info(f"📊 Audio analysis: quality={analysis['quality_score']:.0f}/100, "
                 f"SNR≈{analysis['snr_estimate']:.1f}dB, "
                 f"RMS={analysis['rms']:.1f}dB, "
                 f"noise_floor={analysis['noise_floor']:.4f}")

        # Select processing tier based on quality score
        quality_score = analysis['quality_score']
        if quality_score > 70:
            tier = "TIER1-CLEAN"
            filters = build_tier1_filters(analysis)
        elif quality_score > 40:
            tier = "TIER2-MODERATE"
            filters = build_tier2_filters(analysis)
        else:
            tier = "TIER3-POOR"
            filters = build_tier3_filters(analysis)

        log.info(f"🎯 Processing tier: {tier} ({len(filters)} filters)")

        # Build ffmpeg command
        filter_chain = ",".join(filters)
        cmd = [
            "ffmpeg", "-hide_banner", "-loglevel", "warning", "-y",
            "-i", input_path,
            "-ac", "1", "-ar", str(AUDIO_SR), "-c:a", "pcm_s16le",
            "-filter:a", filter_chain,
            output_path
        ]

        return cmd, analysis

    except Exception as e:
        log.error(f"❌ Failed to build FFmpeg command: {e}")
        # Return fallback command with analysis=None
        return build_fallback_command(input_path, output_path), None

def validate_wav_output(wav_path, expected_duration_sec=None):
    """Validate WAV file quality and integrity.

    Checks:
    - File exists and has content
    - Correct sample rate (16kHz)
    - Mono channel
    - Duration within tolerance
    - Not silent
    - Not excessively clipped

    Returns: (is_valid, message) tuple
    """
    try:
        # Check file exists and has content
        if not os.path.exists(wav_path):
            return False, "Output file not created"

        size_bytes = os.path.getsize(wav_path)
        if size_bytes < 1000:
            return False, f"Output too small: {size_bytes} bytes"

        # Load and validate audio properties
        y, sr = librosa.load(wav_path, sr=None, mono=False)

        # Check sample rate
        if sr != AUDIO_SR:
            return False, f"Wrong sample rate: {sr}Hz (expected {AUDIO_SR}Hz)"

        # Check mono
        if y.ndim > 1:
            return False, f"Wrong channels: {y.shape[0]} (expected 1)"

        # Check duration if expected is provided
        if expected_duration_sec and expected_duration_sec > 0:
            actual_duration = len(y) / sr
            duration_diff = abs(actual_duration - expected_duration_sec)
            tolerance = max(expected_duration_sec * 0.15, 0.5)  # 15% or 0.5s
            if duration_diff > tolerance:
                return False, f"Duration mismatch: {actual_duration:.1f}s vs {expected_duration_sec:.1f}s"

        # Check for silence
        max_amplitude = np.max(np.abs(y))
        if max_amplitude < 0.001:
            return False, f"Output is silent (max amplitude: {max_amplitude:.6f})"

        # Check for excessive clipping
        clipping_ratio = np.sum(np.abs(y) > 0.99) / len(y) if len(y) > 0 else 0
        if clipping_ratio > 0.02:  # More than 2% clipped
            log.warning(f"⚠️ Output has clipping: {clipping_ratio*100:.1f}% of samples")

        return True, "Valid"

    except Exception as e:
        return False, f"Validation error: {str(e)}"


def convert_to_wav(input_path, timeout_sec=None):
    """Convert MP3 to WAV with timeout, validation, and enhanced error handling.

    Args:
        input_path: Path to input MP3 file
        timeout_sec: Optional timeout in seconds (default: 2x duration or 60s min)

    Returns:
        Path to converted WAV file (input MP3 is deleted on success)

    Raises:
        Exception: On conversion failure, validation failure, or timeout
    """
    base = os.path.splitext(input_path)[0]
    output_path = f"{base}.wav"
    expected_duration = None

    try:
        # Probe input duration for timeout calculation
        probe_cmd = ['ffprobe', '-v', 'error', '-show_entries',
                     'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1',
                     input_path]
        result = subprocess.run(probe_cmd, capture_output=True, text=True, timeout=10)
        expected_duration = float(result.stdout.strip())

        # Calculate timeout (2x duration, minimum 60s)
        if not timeout_sec:
            timeout_sec = max(60, expected_duration * 2)
    except Exception as probe_err:
        log.warning(f"Could not probe input duration: {probe_err}")
        timeout_sec = timeout_sec or 60
        expected_duration = None

    # Build FFmpeg command with analysis
    cmd, analysis = build_ffmpeg_command(input_path, output_path)

    try:
        # Execute conversion with timeout protection
        log.info(f"⏱️  Converting with timeout={timeout_sec}s...")
        start_time = time.time()
        result = subprocess.run(
            cmd,
            check=True,
            timeout=timeout_sec,
            capture_output=True,
            text=True
        )
        conversion_time_ms = int((time.time() - start_time) * 1000)

        # Validate output file
        is_valid, validation_msg = validate_wav_output(output_path, expected_duration)
        if not is_valid:
            log.error(f"❌ Validation failed: {validation_msg}")
            if os.path.exists(output_path):
                os.remove(output_path)
            raise Exception(f"Output validation failed: {validation_msg}")

        # Log success
        size = os.path.getsize(output_path)
        log.info(f"✅ Converted successfully → {output_path} ({size:,} bytes, {conversion_time_ms}ms)")

        # Log analysis and tier info
        if analysis:
            log.info(f"   Quality: {analysis['quality_score']:.0f}/100, "
                    f"SNR: {analysis['snr_estimate']:.1f}dB")

        # Delete source only after successful validation
        os.remove(input_path)
        return output_path

    except subprocess.TimeoutExpired:
        log.error(f"⏱️  FFmpeg timeout after {timeout_sec}s on {input_path}")
        if os.path.exists(output_path):
            os.remove(output_path)
        raise Exception(f"Conversion timeout after {timeout_sec}s")

    except subprocess.CalledProcessError as e:
        stderr = e.stderr[:500] if e.stderr else "Unknown error"
        log.error(f"❌ FFmpeg failed: {stderr}")
        if os.path.exists(output_path):
            os.remove(output_path)
        raise Exception(f"FFmpeg error: {stderr}")

# =========================================================
# Audio Storage (Hierarchical S3 Key Structure)
# =========================================================
def _build_hierarchical_s3_key(call_uid, playlist_uuid, started_at):
    """Build hierarchical S3 key for time-partitioned storage.

    Format: calls/playlist_id={UUID}/{YYYY}/{MM}/{DD}/call_{call_uid}.wav

    Args:
        call_uid: Unique call identifier (e.g., "12345-1702500000")
        playlist_uuid: Playlist UUID for partitioning
        started_at: datetime object for time partitioning

    Returns:
        S3 key string (without bucket prefix)
    """
    return (
        f"{MINIO_BUCKET_PATH}/"
        f"playlist_id={playlist_uuid}/"
        f"{started_at.year}/"
        f"{started_at.month:02d}/"
        f"{started_at.day:02d}/"
        f"call_{call_uid}.wav"
    )


def _build_s3_metadata(call_uid, call_metadata):
    """Build S3 user metadata dict for object tagging.

    Args:
        call_uid: Unique call identifier
        call_metadata: dict with playlist_uuid, started_at, tg_id, duration_ms, feed_id

    Returns:
        Dict of string key-value pairs for S3 Metadata
    """
    started_at = call_metadata.get('started_at')
    timestamp_utc = started_at.isoformat() + "Z" if started_at else ""

    return {
        "playlist_id": str(call_metadata.get('playlist_uuid', '')),
        "timestamp_utc": timestamp_utc,
        "call_id": str(call_uid),
        "talkgroup": str(call_metadata.get('tg_id', '')),
        "duration_ms": str(call_metadata.get('duration_ms', 0)),
        "codec": "pcm_s16le",
        "source_feed": str(call_metadata.get('feed_id', ''))
    }


def _upload_with_metadata(local_path, bucket, s3_key, metadata):
    """Upload file to S3 with metadata and content type."""
    s3.upload_file(
        local_path,
        bucket,
        s3_key,
        ExtraArgs={
            'Metadata': metadata,
            'ContentType': 'audio/wav'
        }
    )


async def store_audio(session, src_url, call_uid, call_metadata=None):
    """Download, convert, and upload audio with hierarchical S3 key structure.

    Args:
        session: aiohttp session for downloading
        src_url: Source URL of audio file (M4A/MP3)
        call_uid: Unique call identifier
        call_metadata: Optional dict with playlist_uuid, started_at, tg_id, duration_ms, feed_id
                       If None, falls back to legacy flat key structure

    Returns:
        Tuple of (s3_key, s3_uri) where:
          - s3_key: Object key for database storage
          - s3_uri: Full S3 URI for logging
    """
    mp3_path = os.path.join(TEMP_DIR, f"{call_uid}.mp3")
    wav_path = None
    try:
        async with session.get(src_url) as r:
            if r.status != 200:
                raise Exception(f"Audio {r.status}")
            with open(mp3_path, "wb") as f:
                f.write(await r.read())

        try:
            loop = asyncio.get_running_loop()
            wav_path = await loop.run_in_executor(None, convert_to_wav, mp3_path)

            # Build S3 key based on whether metadata is available
            if call_metadata and call_metadata.get('playlist_uuid') and call_metadata.get('started_at'):
                # New hierarchical structure
                s3_key = _build_hierarchical_s3_key(
                    call_uid,
                    call_metadata['playlist_uuid'],
                    call_metadata['started_at']
                )
                s3_metadata = _build_s3_metadata(call_uid, call_metadata)
                await loop.run_in_executor(
                    None,
                    _upload_with_metadata,
                    wav_path, MINIO_BUCKET, s3_key, s3_metadata
                )
                log.info(f"☁️ Uploaded (hierarchical) → s3://{MINIO_BUCKET}/{s3_key}")
            else:
                # Legacy flat structure (backward compatibility)
                s3_key = f"{MINIO_BUCKET_PATH}/{os.path.basename(wav_path)}"
                await loop.run_in_executor(None, s3.upload_file, wav_path, MINIO_BUCKET, s3_key)
                log.info(f"☁️ Uploaded (legacy) → s3://{MINIO_BUCKET}/{s3_key}")

        except RuntimeError:
            # No running event loop, use blocking calls
            wav_path = convert_to_wav(mp3_path)

            if call_metadata and call_metadata.get('playlist_uuid') and call_metadata.get('started_at'):
                s3_key = _build_hierarchical_s3_key(
                    call_uid,
                    call_metadata['playlist_uuid'],
                    call_metadata['started_at']
                )
                s3_metadata = _build_s3_metadata(call_uid, call_metadata)
                _upload_with_metadata(wav_path, MINIO_BUCKET, s3_key, s3_metadata)
                log.info(f"☁️ Uploaded (hierarchical) → s3://{MINIO_BUCKET}/{s3_key}")
            else:
                s3_key = f"{MINIO_BUCKET_PATH}/{os.path.basename(wav_path)}"
                s3.upload_file(wav_path, MINIO_BUCKET, s3_key)
                log.info(f"☁️ Uploaded (legacy) → s3://{MINIO_BUCKET}/{s3_key}")

        s3_uri = f"s3://{MINIO_BUCKET}/{s3_key}"
        return s3_key, s3_uri

    finally:
        # Always clean up temp files, even on error
        for path in (mp3_path, wav_path):
            if path and os.path.exists(path):
                try:
                    os.remove(path)
                except OSError:
                    log.warning(f"Failed to remove temp file: {path}")

# =========================================================
# Inserts + Poll Logging
# =========================================================
async def quick_insert_call_metadata(conn, playlist_uuid, call):
    """Insert call metadata immediately (no audio processing) - for near real-time ingestion.

    Args:
        conn: Database connection
        playlist_uuid: UUID of the playlist (stored for hierarchical S3 path construction)
        call: Call metadata dict from Broadcastify API

    Returns:
        dict: {'status': 'inserted'|'duplicate'|'error', 'call_uid': str, 'error': str|None}
    """
    call_uid = f"{call['groupId']}-{call['ts']}"

    try:
        # Use RETURNING to verify insert success vs ON CONFLICT skip
        result = await conn.fetchrow("""
            INSERT INTO bcfy_calls_raw (
                call_uid, group_id, ts, feed_id, tg_id, tag_id, node_id, sid, site_id,
                freq, src, url, started_at, ended_at, duration_ms, size_bytes,
                fetched_at, raw_json, processed, playlist_uuid
            ) VALUES (
                $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12,
                TO_TIMESTAMP($13), TO_TIMESTAMP($14), $15, $16, NOW(), $17, FALSE, $18
            )
            ON CONFLICT(call_uid) DO NOTHING
            RETURNING call_uid
        """,
            call_uid,
            call.get("groupId"),
            call.get("ts"),
            call.get("feedId"),
            call.get("tgId"),
            call.get("tag"),
            call.get("nodeId"),
            call.get("sid"),
            call.get("siteId"),
            call.get("freq"),
            call.get("src"),
            call.get("url"),  # Original M4A URL from Broadcastify (converted to WAV)
            call.get("start_ts", call.get("ts")),
            call.get("end_ts", call.get("ts")),
            int(call.get("duration", 0) * 1000),
            call.get("size"),
            json.dumps(call),
            playlist_uuid  # Store playlist UUID for hierarchical S3 path construction
        )

        if result:
            return {'status': 'inserted', 'call_uid': call_uid, 'error': None}
        else:
            return {'status': 'duplicate', 'call_uid': call_uid, 'error': None}

    except Exception as e:
        log.error(f"INSERT failed for {call_uid}: {e}")
        return {'status': 'error', 'call_uid': call_uid, 'error': str(e)}

async def poll_start(conn, uuid):
    await conn.execute("INSERT INTO bcfy_playlist_poll_log(uuid,poll_started_at) VALUES($1,NOW());", uuid)

async def poll_end(conn, uuid, ok, notes):
    await conn.execute("""
        UPDATE bcfy_playlist_poll_log
           SET poll_ended_at=NOW(),success=$2,notes=$3
         WHERE uuid=$1 AND poll_ended_at IS NULL;
    """, uuid, ok, notes)

# =========================================================
# Live Calls Fetching (replaces group-based fetching)
# =========================================================
async def fetch_live_calls(session, token, conn, playlist_uuid, last_pos=None):
    """Fetch live calls for entire playlist using position-based polling.

    Args:
        session: aiohttp session
        token: JWT token
        conn: database connection for metrics tracking
        playlist_uuid: Broadcastify playlist UUID
        last_pos: Unix timestamp from previous lastPos response (None = last 5 minutes)

    Returns:
        dict with 'calls' list and 'lastPos' timestamp
    """
    url = f"{CALLS_BASE}/live/"
    # Convert UUID to string in case it comes from database as UUID object
    params = {"playlist_uuid": str(playlist_uuid)}

    if last_pos and last_pos > 0:
        params["pos"] = int(last_pos)  # Incremental: only new calls
    # else: returns last 5 minutes of calls (default behavior)

    data = await fetch_json(session, url, token, conn, params=params)
    return data

# =========================================================
# Playlist Processor
# =========================================================
async def process_playlist(session, token, pl):
    """Process a single playlist with its own database connection.

    Each playlist processor acquires its own connection from the pool to allow
    true parallel processing without connection conflicts.
    """
    uuid, name = pl["uuid"], pl["name"]
    log.info(f"▶️ Playlist '{name}' ({uuid})")

    # Get last position from database (stores lastPos from previous API response)
    last_pos = pl.get("last_pos", 0)

    # Acquire own connection from pool for this playlist
    conn = await get_connection()
    try:
        # Wrap poll_start in its own try/except for failure isolation
        try:
            await poll_start(conn, uuid)
        except Exception as e:
            log.error(f"❌ poll_start failed for '{name}': {e}")
            return  # Skip this playlist, don't halt others

        try:
            # Single API call for entire playlist (replaces all group calls + chunking)
            data = await fetch_live_calls(session, token, conn, uuid, last_pos)

            calls = data.get("calls", [])
            new_last_pos = data.get("lastPos")  # Unix timestamp from API

            log.info(f"Received {len(calls)} calls (lastPos: {new_last_pos})")

            # Track insert metrics
            inserted_count = 0
            duplicate_count = 0
            error_count = 0

            # Insert metadata for all calls with verification
            for call in calls:
                result = await quick_insert_call_metadata(conn, uuid, call)
                if result['status'] == 'inserted':
                    inserted_count += 1
                elif result['status'] == 'duplicate':
                    duplicate_count += 1
                else:
                    error_count += 1

            # Log batch metrics
            log.info(f"Playlist '{name}': {inserted_count} inserted, "
                     f"{duplicate_count} duplicates, {error_count} errors")

            # Log to system_logs for observability
            await conn.execute("""
                INSERT INTO system_logs (component, event_type, message, metadata)
                VALUES ($1, $2, $3, $4)
            """, 'ingestion', 'playlist_batch',
                 f"Playlist {name}: {inserted_count}/{len(calls)} inserted",
                 json.dumps({
                     'playlist_uuid': str(uuid),
                     'playlist_name': name,
                     'total_calls': len(calls),
                     'inserted': inserted_count,
                     'duplicates': duplicate_count,
                     'errors': error_count,
                     'last_pos': new_last_pos
                 }))

            # Update last_pos for next poll (critical for incremental polling)
            if new_last_pos:
                await conn.execute(
                    "UPDATE bcfy_playlists SET last_pos=$1 WHERE uuid=$2",
                    new_last_pos,
                    uuid
                )

            await poll_end(conn, uuid, True, f"Processed {len(calls)} calls ({inserted_count} new, {duplicate_count} dup), lastPos={new_last_pos}")
            log.info(f"✅ Finished playlist '{name}'")

        except Exception as e:
            log.error(f"❌ Playlist '{name}' failed: {e}")
            # Wrap poll_end in try/except to prevent exception in exception handler
            try:
                await poll_end(conn, uuid, False, str(e))
            except Exception as poll_err:
                log.error(f"❌ poll_end also failed for '{name}': {poll_err}")
    finally:
        await release_connection(conn)

# =========================================================
# Main Loop
# =========================================================
_schema_verified = False  # Module-level flag to ensure schema check runs once

async def ingest_loop():
    global _schema_verified

    # One-time schema verification at startup
    if not _schema_verified:
        await verify_schema()
        _schema_verified = True

    cycle_start = time.time()
    conn = await get_connection()  # Get from pool

    try:
        # Log cycle start
        await conn.execute("""
            INSERT INTO system_logs (component, event_type, message)
            VALUES ($1, $2, $3)
        """, 'ingestion', 'cycle_start', 'Starting ingestion cycle')

        async with aiohttp.ClientSession() as s:
            token = get_jwt_token()  # Use cached JWT token (1 hour validity, reused)
            playlists = await conn.fetch(
                "SELECT uuid,name,COALESCE(last_pos,0) AS last_pos FROM bcfy_playlists WHERE sync=TRUE;"
            )
            if not playlists:
                log.warning("No sync=TRUE playlists")
                return

            log.info(f"{len(playlists)} playlist(s) found.")

            # Get initial call count for metrics
            initial_count = await conn.fetchval("SELECT COUNT(*) FROM bcfy_calls_raw")

            # Process all playlists in parallel with failure isolation
            # Each playlist acquires its own connection from the pool
            # return_exceptions=True ensures one playlist failure doesn't halt others
            results = await asyncio.gather(
                *[process_playlist(s, token, p) for p in playlists],
                return_exceptions=True
            )

            # Log any unexpected exceptions that escaped process_playlist's error handling
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    log.error(f"Unexpected exception in playlist {playlists[i]['name']}: {result}")

            # Get final call count for metrics
            final_count = await conn.fetchval("SELECT COUNT(*) FROM bcfy_calls_raw")
            calls_processed = final_count - initial_count

        # Log cycle completion with metrics
        cycle_duration_ms = int((time.time() - cycle_start) * 1000)
        await conn.execute("""
            INSERT INTO system_logs (component, event_type, message, metadata, duration_ms)
            VALUES ($1, $2, $3, $4, $5)
        """, 'ingestion', 'cycle_complete',
             f'Processed {calls_processed} calls in {cycle_duration_ms}ms',
             json.dumps({
                 'calls_processed': calls_processed,
                 'playlists_count': len(playlists),
                 'cycle_duration_ms': cycle_duration_ms
             }),
             cycle_duration_ms)

        log.info(f"Cycle done in {cycle_duration_ms}ms ({calls_processed} new calls); sleeping {COLLECT_INTERVAL_SEC}s")
    finally:
        await release_connection(conn)  # Return to pool

# =========================================================
# Entry
# =========================================================
if __name__ == "__main__":
    try:
        asyncio.run(ingest_loop())
    except KeyboardInterrupt:
        log.warning("🛑 Stopped manually.")
    except Exception as e:
        log.exception(f"💥 Fatal: {e}")
