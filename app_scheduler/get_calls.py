#!/usr/bin/env python3
"""
Broadcastify Calls Downloader + Audio Optimizer (env-driven)
Pulls new calls, converts each MP3 → optimized 16-kHz WAV,
uploads to MinIO, and logs ingestion.
"""

import asyncio, aiohttp, asyncpg, os, json, time, jwt, boto3, logging, subprocess, sys
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
# JWT
# =========================================================
def get_jwt():
    key_id = os.getenv("BCFY_API_KEY_ID")
    key    = os.getenv("BCFY_API_KEY")
    app_id = os.getenv("BCFY_APP_ID")
    header  = {"alg": "HS256", "typ": "JWT", "kid": key_id}
    payload = {"iss": app_id, "iat": int(time.time()), "exp": int(time.time()) + 3600}
    return jwt.encode(payload, key, algorithm="HS256", headers=header)

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
async def get_db():
    return await asyncpg.connect(DB_URL)

# =========================================================
# HTTP (with API call tracking)
# =========================================================
async def fetch_json(session, url, token, conn=None, params=None):
    """Fetch JSON with optional API call tracking and query parameters."""
    start = time.time()
    status_code = 0
    error_msg = None

    try:
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
                except:
                    pass  # Don't fail fetch if logging fails

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
            except:
                pass

        raise

# =========================================================
# Audio Analysis + Conversion
# =========================================================
def analyze_audio(path):
    y, sr = librosa.load(path, sr=None, mono=True)
    rms = 20 * np.log10(np.mean(librosa.feature.rms(y=y)) + 1e-9)
    centroid = librosa.feature.spectral_centroid(y=y, sr=sr).mean()
    noise = np.percentile(np.abs(y), 10)
    return rms, centroid, noise

def build_ffmpeg_command(input_path, output_path):
    rms, centroid, noise = analyze_audio(input_path)
    afftdn = "-20"
    lowpass = "6000"
    filters = []

    if centroid > 3500:
        afftdn = "-25"
    elif centroid < 2500:
        afftdn = "-20"

    if rms < -28:
        filters.append("acompressor=ratio=3:threshold=-25dB:makeup=5dB")

    if noise > 0.002:
        filters.append(f"highpass=f=250,lowpass=f={lowpass}")

    filter_chain = f"loudnorm=I={AUDIO_TARGET_DB}:LRA=11:TP=-1,afftdn=nf={afftdn}"
    if filters:
        filter_chain += "," + ",".join(filters)

    cmd = [
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        "-i", input_path,
        "-ac", "1", "-ar", str(AUDIO_SR), "-c:a", "pcm_s16le",
        "-filter:a", filter_chain, output_path
    ]
    log.info(f"🎛️ FFmpeg command: {' '.join(cmd)}")
    return cmd

def convert_to_wav(input_path):
    base = os.path.splitext(input_path)[0]
    output_path = f"{base}.wav"
    cmd = build_ffmpeg_command(input_path, output_path)
    try:
        subprocess.run(cmd, check=True)
        if os.path.exists(output_path):
            size = os.path.getsize(output_path)
            log.info(f"🎧 Converted successfully → {output_path} ({size:,} bytes)")
        else:
            log.warning(f"⚠️ Output missing: {output_path}")
    except subprocess.CalledProcessError as e:
        log.error(f"❌ FFmpeg failed: {e}")
        raise
    os.remove(input_path)
    return output_path

# =========================================================
# Audio Storage
# =========================================================
async def store_audio(session, src_url, call_uid):
    mp3_path = os.path.join(TEMP_DIR, f"{call_uid}.mp3")
    async with session.get(src_url) as r:
        if r.status != 200:
            raise Exception(f"Audio {r.status}")
        with open(mp3_path, "wb") as f:
            f.write(await r.read())

    wav_path = convert_to_wav(mp3_path)
    s3_key = f"{MINIO_BUCKET_PATH}/{os.path.basename(wav_path)}"
    s3.upload_file(wav_path, MINIO_BUCKET, s3_key)
    log.info(f"☁️ Uploaded → s3://{MINIO_BUCKET}/{s3_key}")
    os.remove(wav_path)
    return f"s3://{MINIO_BUCKET}/{s3_key}"

# =========================================================
# Inserts + Poll Logging
# =========================================================
async def insert_call(conn, uuid, call, url):
    cid = f"{call['groupId']}-{call['ts']}"
    await conn.execute("""
        INSERT INTO bcfy_calls_raw
        (call_uid,group_id,ts,node_id,sid,site_id,freq,src,url,
         started_at,ended_at,duration_ms,fetched_at,raw_json)
        VALUES($1,$2,$3,$4,$5,$6,$7,$8,$9,TO_TIMESTAMP($10),
               TO_TIMESTAMP($11),($12*1000),NOW(),$13)
        ON CONFLICT(call_uid) DO NOTHING;
    """,
        cid, call.get("groupId"), call.get("ts"), call.get("nodeId"),
        call.get("sid"), call.get("siteId"), call.get("freq"),
        call.get("src"), url, call.get("start_ts"), call.get("end_ts"),
        call.get("duration", 0), json.dumps(call)
    )

async def quick_insert_call_metadata(conn, uuid, call):
    """Insert call metadata immediately (no audio processing) - for near real-time ingestion."""
    call_uid = f"{call['groupId']}-{call['ts']}"

    await conn.execute("""
        INSERT INTO bcfy_calls_raw (
            call_uid, group_id, ts, feed_id, tg_id, tag_id, node_id, sid, site_id,
            freq, src, url, started_at, ended_at, duration_ms, size_bytes,
            fetched_at, raw_json, processed
        ) VALUES (
            $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12,
            TO_TIMESTAMP($13), TO_TIMESTAMP($14), $15, $16, NOW(), $17, FALSE
        )
        ON CONFLICT(call_uid) DO NOTHING
    """,
        call_uid,
        call.get("groupId"),
        call.get("ts"),
        call.get("feedId"),
        call.get("tgId"),
        call.get("tagId"),
        call.get("nodeId"),
        call.get("sid"),
        call.get("siteId"),
        call.get("freq"),
        call.get("src"),
        call.get("url"),  # Original MP3 URL from Broadcastify
        call.get("start_ts", call.get("ts")),
        call.get("end_ts", call.get("ts")),
        int(call.get("duration", 0) * 1000),
        call.get("size"),
        json.dumps(call)
    )

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
    params = {"playlist_uuid": playlist_uuid}

    if last_pos and last_pos > 0:
        params["pos"] = int(last_pos)  # Incremental: only new calls
    # else: returns last 5 minutes of calls (default behavior)

    data = await fetch_json(session, url, token, conn, params=params)
    return data

# =========================================================
# Playlist Processor
# =========================================================
async def process_playlist(conn, session, token, pl):
    uuid, name = pl["uuid"], pl["name"]
    log.info(f"▶️ Playlist '{name}' ({uuid})")

    # Get last position from database (stores lastPos from previous API response)
    last_pos = pl.get("last_pos", 0)

    await poll_start(conn, uuid)

    try:
        # Single API call for entire playlist (replaces all group calls + chunking)
        data = await fetch_live_calls(session, token, conn, uuid, last_pos)

        calls = data.get("calls", [])
        new_last_pos = data.get("lastPos")  # Unix timestamp from API

        log.info(f"Received {len(calls)} calls (lastPos: {new_last_pos})")

        # Insert metadata for all calls
        for call in calls:
            await quick_insert_call_metadata(conn, uuid, call)

        # Update last_pos for next poll (critical for incremental polling)
        if new_last_pos:
            await conn.execute(
                "UPDATE bcfy_playlists SET last_pos=$1 WHERE uuid=$2",
                new_last_pos,
                uuid
            )

        await poll_end(conn, uuid, True, f"Processed {len(calls)} calls, lastPos={new_last_pos}")
        log.info(f"✅ Finished playlist '{name}'")

    except Exception as e:
        await poll_end(conn, uuid, False, str(e))
        log.error(f"❌ Playlist '{name}' failed: {e}")

# =========================================================
# Main Loop
# =========================================================
async def ingest_loop():
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

            await asyncio.gather(*[process_playlist(conn, s, token, p) for p in playlists])

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
