import os, psycopg2, boto3, tempfile
from faster_whisper import WhisperModel
from datetime import datetime

DB = {
    "host": os.getenv("DB_HOST", "db"),
    "port": "5432",
    "dbname": "scanner",
    "user": "scanner",
    "password": "scanner",
}

model = WhisperModel("medium", device="cuda", compute_type="float16")
s3 = boto3.client("s3")

def get_pending_calls():
    with psycopg2.connect(**DB) as conn, conn.cursor() as cur:
        cur.execute("""
            SELECT id, s3_path
            FROM bcfy_calls_raw
            WHERE processed = false
            ORDER BY id
            LIMIT 10;
        """)
        return cur.fetchall()

def mark_processed(cur, call_id, success, error=None):
    cur.execute("""
        UPDATE bcfy_calls_raw
        SET processed=%s, last_attempt=%s, error=%s
        WHERE id=%s;
    """, (success, datetime.utcnow(), error, call_id))

def transcribe_file(call_id, s3_uri):
    bucket, key = s3_uri.replace("s3://", "").split("/", 1)
    with tempfile.NamedTemporaryFile(suffix=".mp3") as tmp:
        s3.download_file(bucket, key, tmp.name)
        segments, info = model.transcribe(tmp.name, beam_size=5)
        text = " ".join([seg.text for seg in segments])
        confidence = sum(seg.avg_logprob for seg in segments) / len(segments)
        return text, info.language, info.duration, confidence

def main():
    conn = psycopg2.connect(**DB)
    cur = conn.cursor()
    for call_id, s3_uri in get_pending_calls():
        try:
            text, lang, dur, conf = transcribe_file(call_id, s3_uri)
            cur.execute("""
                INSERT INTO transcripts (recording_id, text, language, model_name, duration_seconds, confidence)
                VALUES (%s,%s,%s,%s,%s,%s)
                ON CONFLICT (recording_id) DO NOTHING;
            """, (call_id, text, lang, "faster-whisper-medium", dur, conf))
            mark_processed(cur, call_id, True)
            conn.commit()
        except Exception as e:
            mark_processed(cur, call_id, False, str(e))
            conn.commit()
    cur.close()
    conn.close()

if __name__ == "__main__":
    main()
