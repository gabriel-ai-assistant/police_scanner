#!/usr/bin/env python3
"""
Broadcastify Calls Downloader – Chunked Initial Sync Version
Performs full 30-day historical sync in ≤8-hour chunks
and logs each poll in bcfy_playlist_poll_log.
"""

import asyncio, aiohttp, asyncpg, os, json, time, jwt, boto3, logging
from botocore.client import Config
from datetime import datetime, timedelta
from dotenv import load_dotenv

# ---------- Logging ----------
logging.basicConfig(level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S")
log = logging.getLogger("bcfy_ingest")

# ---------- Environment ----------
load_dotenv()
PGUSER, PGPASSWORD, PGDATABASE = os.getenv("PGUSER"), os.getenv("PGPASSWORD"), os.getenv("PGDATABASE")
PGHOST, PGPORT = os.getenv("PGHOST","localhost"), os.getenv("PGPORT","5432")
DB_URL=f"postgresql://{PGUSER}:{PGPASSWORD}@{PGHOST}:{PGPORT}/{PGDATABASE}"

BCFY_BASE=os.getenv("BCFY_BASE_URL","https://api.bcfy.io")
CALLS_BASE=f"{BCFY_BASE}/calls/v1"
COLLECT_INTERVAL_SEC=int(os.getenv("COLLECT_INTERVAL_SEC","30"))

MINIO_ENDPOINT=os.getenv("MINIO_ENDPOINT","localhost:9000")
MINIO_ROOT_USER=os.getenv("MINIO_ROOT_USER","admin")
MINIO_ROOT_PASSWORD=os.getenv("MINIO_ROOT_PASSWORD","adminadmin")
MINIO_BUCKET=os.getenv("MINIO_BUCKET","feeds")
MINIO_USE_SSL=os.getenv("MINIO_USE_SSL","false").lower()=="true"

TEMP_DIR=os.path.join(os.getcwd(),"tmp_audio")
os.makedirs(TEMP_DIR,exist_ok=True)
log.info(f"Temp audio directory: {TEMP_DIR}")

# ---------- JWT ----------
def get_jwt():
    header={"alg":"HS256","typ":"JWT","kid":os.getenv("BCFY_API_KEY_ID")}
    payload={"iss":os.getenv("BCFY_APP_ID"),"iat":int(time.time()),"exp":int(time.time())+3600}
    return jwt.encode(payload,os.getenv("BCFY_API_KEY"),algorithm="HS256",headers=header)

# ---------- MinIO ----------
log.info(f"Connecting to MinIO endpoint: {MINIO_ENDPOINT}")
s3=boto3.client("s3",
    endpoint_url=f"http{'s' if MINIO_USE_SSL else ''}://{MINIO_ENDPOINT}",
    aws_access_key_id=MINIO_ROOT_USER,
    aws_secret_access_key=MINIO_ROOT_PASSWORD,
    config=Config(signature_version="s3v4"),
    region_name="us-east-1")
try: s3.head_bucket(Bucket=MINIO_BUCKET)
except Exception: s3.create_bucket(Bucket=MINIO_BUCKET)

# ---------- DB ----------
async def get_db(): return await asyncpg.connect(DB_URL)

# ---------- HTTP ----------
async def fetch_json(session,url,token):
    async with session.get(url,headers={"Authorization":f"Bearer {token}"}) as r:
        t=await r.text()
        try: d=json.loads(t)
        except Exception as e: raise Exception(f"Bad JSON {url}: {e}")
        log.info(f"HTTP {r.status} ({len(t)} bytes) → {url}")
        if r.status!=200: raise Exception(f"HTTP {r.status}: {url}")
        log.debug(json.dumps(d,indent=2)[:800])
        return d

# ---------- Audio ----------
async def store_audio(session,src_url,call_uid):
    f=f"{call_uid}.mp3"; p=os.path.join(TEMP_DIR,f)
    async with session.get(src_url) as r:
        if r.status!=200: raise Exception(f"Audio {r.status}")
        with open(p,"wb") as o:o.write(await r.read())
    s3.upload_file(p,MINIO_BUCKET,f"calls/{f}"); os.remove(p)
    return f"s3://{MINIO_BUCKET}/calls/{f}"

# ---------- Inserts ----------
async def insert_call(conn,uuid,call,url):
    cid=f"{call['groupId']}-{call['ts']}"
    await conn.execute("""
        INSERT INTO bcfy_calls_raw
        (call_uid,group_id,ts,node_id,sid,site_id,freq,src,url,
         started_at,ended_at,duration_ms,fetched_at,raw_json)
        VALUES($1,$2,$3,$4,$5,$6,$7,$8,$9,TO_TIMESTAMP($10),
               TO_TIMESTAMP($11),($12*1000),NOW(),$13)
        ON CONFLICT(call_uid) DO NOTHING;
    """,cid,call.get("groupId"),call.get("ts"),call.get("nodeId"),
       call.get("sid"),call.get("siteId"),call.get("freq"),
       call.get("src"),url,call.get("start_ts"),call.get("end_ts"),
       call.get("duration",0),json.dumps(call))

# ---------- Poll Log ----------
async def poll_start(conn,uuid):
    await conn.execute("INSERT INTO bcfy_playlist_poll_log(uuid,poll_started_at) VALUES($1,NOW());",uuid)
async def poll_end(conn,uuid,ok,notes):
    await conn.execute("""
        UPDATE bcfy_playlist_poll_log
           SET poll_ended_at=NOW(),success=$2,notes=$3
         WHERE uuid=$1 AND poll_ended_at IS NULL;
    """,uuid,ok,notes)

# ---------- Chunked Processor ----------
async def process_playlist(conn,session,token,pl):
    uuid,name=pl["uuid"],pl["name"]
    log.info(f"▶️ Playlist '{name}' ({uuid})")
    now=int(time.time())
    row=await conn.fetchrow("SELECT COUNT(*) AS c FROM bcfy_calls_raw;")
    fresh=row["c"]==0
    start=int((datetime.now()-timedelta(days=30)).timestamp()) if fresh else now-900
    end=now
    await poll_start(conn,uuid)
    try:
        pinfo=await fetch_json(session,f"{CALLS_BASE}/playlist_get/{uuid}",token)
        groups=pinfo.get("groups",[])
        if not groups:
            await poll_end(conn,uuid,True,"no groups")
            return
        log.info(f"{len(groups)} groups found; chunking 8h windows...")
        max_span=28800
        cur=start
        while cur<end:
            chunk_end=min(cur+max_span,end)
            log.info(f"⏱ Chunk {datetime.utcfromtimestamp(cur)} → {datetime.utcfromtimestamp(chunk_end)}")
            for g in groups:
                gid=g["groupId"]
                url=f"{CALLS_BASE}/group_archives/{gid}/{cur}/{chunk_end}"
                try:
                    data=await fetch_json(session,url,token)
                    calls=data.get("calls",[])
                    log.info(f"  • {len(calls)} calls from group {gid}")
                    for c in calls:
                        s3url=await store_audio(session,c["url"],f"{c['groupId']}-{c['ts']}")
                        await insert_call(conn,uuid,c,s3url)
                except Exception as e:
                    log.warning(f"group {gid} err {e}")
            cur=chunk_end
        await poll_end(conn,uuid,True,f"full sync window={start}->{end}")
        log.info(f"✅ Finished playlist '{name}'")
    except Exception as e:
        await poll_end(conn,uuid,False,str(e))
        log.error(f"❌ Playlist '{name}' failed: {e}")

# ---------- Main Loop ----------
async def ingest_loop():
    conn=await get_db()
    async with aiohttp.ClientSession() as s:
        token=get_jwt()
        pls=await conn.fetch("SELECT uuid,name,COALESCE(last_seen,0) AS last_seen FROM bcfy_playlists WHERE sync=TRUE;")
        if not pls: log.warning("No sync=TRUE playlists"); return
        log.info(f"{len(pls)} playlist(s) found.")
        await asyncio.gather(*[process_playlist(conn,s,token,p) for p in pls])
    await conn.close()
    log.info(f"Cycle done; sleeping {COLLECT_INTERVAL_SEC}s")

# ---------- Entry ----------
if __name__=="__main__":
    try: asyncio.run(ingest_loop())
    except KeyboardInterrupt: log.warning("🛑 Stopped manually.")
    except Exception as e: log.exception(f"💥 Fatal: {e}")