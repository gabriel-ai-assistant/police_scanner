import os, json, tempfile, psycopg2, boto3, whisper, meilisearch, logging, re
from celery import Celery
from botocore.exceptions import ClientError

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

app = Celery("scanner", broker=os.getenv("REDIS_URL"), backend=os.getenv("REDIS_URL"))
PG = dict(dbname=os.getenv("PGDATABASE"), user=os.getenv("PGUSER"),
          password=os.getenv("PGPASSWORD"), host=os.getenv("PGHOST"), port=os.getenv("PGPORT"))

s3 = boto3.client(
    "s3",
    endpoint_url=f"http://{os.getenv('MINIO_ENDPOINT')}",
    aws_access_key_id=os.getenv("MINIO_ROOT_USER"),
    aws_secret_access_key=os.getenv("MINIO_ROOT_PASSWORD"),
)
BUCKET = os.getenv("MINIO_BUCKET")
BUCKET_PATH = os.getenv("AUDIO_BUCKET_PATH", "calls")
model = whisper.load_model(os.getenv("WHISPER_MODEL","small"))
mc = meilisearch.Client(os.getenv("MEILI_HOST"), os.getenv("MEILI_MASTER_KEY"))
idx = mc.index("transcripts")


def _extract_call_uid_from_key(s3_key: str) -> str:
    """Extract call_uid from S3 key (works for both hierarchical and flat paths).

    Hierarchical: calls/playlist_id=.../year=.../call_{call_uid}.wav -> {call_uid}
    Flat: calls/{call_uid}.wav -> {call_uid}
    """
    # Try to extract from hierarchical path (call_{call_uid}.wav)
    match = re.search(r'call_([^/]+)\.wav$', s3_key)
    if match:
        return match.group(1)

    # Flat path: calls/{call_uid}.wav
    basename = os.path.basename(s3_key)
    return os.path.splitext(basename)[0]


def download_audio_with_fallback(s3_key: str, local_path: str) -> str:
    """Download audio file with dual-read fallback for backward compatibility.

    Tries primary s3_key first, falls back to legacy flat path if not found.

    Args:
        s3_key: Primary S3 object key (hierarchical or flat)
        local_path: Local file path to save downloaded audio

    Returns:
        The s3_key that was successfully used for download

    Raises:
        ClientError: If file not found in either location
    """
    try:
        # Try primary path first
        s3.download_file(BUCKET, s3_key, local_path)
        log.debug(f"Downloaded from primary path: {s3_key}")
        return s3_key
    except ClientError as e:
        if e.response['Error']['Code'] == '404' or 'NoSuchKey' in str(e):
            # Try legacy flat path
            call_uid = _extract_call_uid_from_key(s3_key)
            legacy_key = f"{BUCKET_PATH}/{call_uid}.wav"

            if legacy_key != s3_key:  # Avoid infinite loop
                log.info(f"Fallback: trying legacy path {legacy_key}")
                try:
                    s3.download_file(BUCKET, legacy_key, local_path)
                    log.info(f"Downloaded from legacy path: {legacy_key}")
                    return legacy_key
                except ClientError:
                    pass  # Fall through to re-raise original error

        log.error(f"Failed to download from both {s3_key} and legacy path")
        raise


@app.task(name="worker.transcribe")
def transcribe(s3_key: str, recording_id: int):
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        try:
            download_audio_with_fallback(s3_key, tmp.name)
            result = model.transcribe(tmp.name, language=os.getenv("LANGUAGE", None))
        finally:
            # Ensure temp file is cleaned up
            if os.path.exists(tmp.name):
                os.remove(tmp.name)

    text = (result.get("text") or "").strip()
    words = result.get("segments") or []

    conn = psycopg2.connect(**PG); conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO transcripts (recording_id, text, words) VALUES (%s, %s, %s) RETURNING id",
            (recording_id, text, json.dumps(words))
        )
        tid = cur.fetchone()[0]

    try:
        idx.add_documents([{"id": tid, "recording_id": recording_id, "text": text}])
    except Exception as e:
        print("meili index error:", e)
    return {"recording_id": recording_id, "transcript_id": tid, "chars": len(text)}
