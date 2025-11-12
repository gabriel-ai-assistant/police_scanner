import os, json, tempfile, psycopg2, boto3, whisper, meilisearch
from celery import Celery

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
model = whisper.load_model(os.getenv("WHISPER_MODEL","small"))
mc = meilisearch.Client(os.getenv("MEILI_HOST"), os.getenv("MEILI_MASTER_KEY"))
idx = mc.index("transcripts")

@app.task(name="worker.transcribe")
def transcribe(s3_key: str, recording_id: int):
    with tempfile.NamedTemporaryFile(suffix=".mp3") as tmp:
        s3.download_file(BUCKET, s3_key, tmp.name)
        result = model.transcribe(tmp.name, language=os.getenv("LANGUAGE", None))

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
