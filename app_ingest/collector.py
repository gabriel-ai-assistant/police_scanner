import os, time, uuid, requests, boto3, redis, psycopg2
from urllib.parse import urljoin

FEEDS = [x.strip() for x in os.getenv("BROADCASTIFY_FEED_IDS","").split(",") if x.strip()]
INTERVAL = int(os.getenv("COLLECT_INTERVAL_SEC", 120))
BASE = "https://example.broadcastify.local/feeds/"  # replace with real API
BUCKET = os.getenv("MINIO_BUCKET")

s3 = boto3.client(
    "s3",
    endpoint_url=f"http://{os.getenv('MINIO_ENDPOINT')}",
    aws_access_key_id=os.getenv("MINIO_ROOT_USER"),
    aws_secret_access_key=os.getenv("MINIO_ROOT_PASSWORD"),
)
r = redis.Redis.from_url(os.getenv("REDIS_URL"))
PG = dict(dbname=os.getenv("PGDATABASE"), user=os.getenv("PGUSER"),
          password=os.getenv("PGPASSWORD"), host=os.getenv("PGHOST"), port=os.getenv("PGPORT"))

while True:
    for feed_id in FEEDS:
        try:
            url = urljoin(BASE, f"{feed_id}/latest.mp3")
            resp = requests.get(url, timeout=30); resp.raise_for_status()
            key = f"feed_{feed_id}/{uuid.uuid4()}.mp3"
            s3.put_object(Bucket=BUCKET, Key=key, Body=resp.content)

            conn = psycopg2.connect(**PG); conn.autocommit = True
            with conn.cursor() as cur:
                cur.execute("INSERT INTO recordings (feed_id, s3_key) VALUES (%s, %s) RETURNING id",
                            (int(feed_id), key))
                rec_id = cur.fetchone()[0]

            # simple Celery message (use proper Celery client in prod)
            r.lpush("celery",
                    f"[[\"worker.transcribe\"],{{\"kwargs\":{{\"s3_key\":\"{key}\",\"recording_id\":{rec_id}}}}}]")
            print(f"enqueued transcription for feed {feed_id} -> {key}")
        except Exception as e:
            print("collector error:", e)
    time.sleep(INTERVAL)
