---
name: "MinIO/S3"
description: "Manage audio file storage and retrieval"
---

## Context

Use this skill when working with MinIO/S3 audio file storage. This includes debugging upload/download issues, managing presigned URLs, and organizing storage structure.

## Scope

Files this agent works with:
- `app_scheduler/audio_worker.py` - Audio upload logic
- `app_transcribe/worker.py` - Audio download for transcription
- `shared_bcfy/*.py` - S3 utility functions
- MinIO admin UI at `http://192.168.1.152:9000`

## Instructions

When invoked, follow these steps:

1. **Understand the issue**
   - Identify if it's upload or download failing
   - Check S3 key path structure
   - Verify bucket exists and is accessible

2. **Debug connectivity**
   - Test MinIO endpoint accessibility
   - Verify credentials are correct
   - Check bucket permissions

3. **Implement changes**
   - Use hierarchical key structure
   - Generate presigned URLs with appropriate expiry
   - Validate file integrity after transfer

4. **Verify**
   - Confirm file exists in expected location
   - Test presigned URL generation
   - Check file can be downloaded

## Behaviors

- Use hierarchical key structure: `calls/playlist_id={UUID}/{YYYY}/{MM}/{DD}/call_{uid}.wav`
- Generate presigned URLs for audio playback (1hr expiry)
- Validate file integrity after upload (checksum)
- Handle missing files gracefully
- Use appropriate content types for audio files

## Constraints

- Never delete files without backup verification
- Never expose MinIO credentials in URLs or responses
- Use SSL in production (MINIO_USE_SSL=true)
- Never skip file validation after upload
- Never store files with predictable public paths

## Safety Checks

Before completing:
- [ ] Bucket exists and is accessible
- [ ] Credentials not exposed in logs or responses
- [ ] Presigned URLs have reasonable expiry (1hr max for audio)
- [ ] File integrity validated after upload
- [ ] Storage space checked for large operations

## S3 Key Structure

```
feeds/                                    # Bucket name
├── calls/                                # Audio files
│   └── playlist_id={UUID}/
│       └── 2025/
│           └── 01/
│               └── 15/
│                   └── call_{uid}.wav
└── exports/                              # Exported data (if any)
    └── ...
```

## Code Patterns

```python
from minio import Minio
import os

# Initialize client
client = Minio(
    endpoint=os.getenv("MINIO_ENDPOINT"),
    access_key=os.getenv("MINIO_ROOT_USER"),
    secret_key=os.getenv("MINIO_ROOT_PASSWORD"),
    secure=os.getenv("MINIO_USE_SSL", "false").lower() == "true"
)

# Upload file
def upload_audio(local_path: str, call_uid: str, playlist_id: str) -> str:
    key = f"calls/playlist_id={playlist_id}/{date_path}/call_{call_uid}.wav"
    client.fput_object(
        bucket_name="feeds",
        object_name=key,
        file_path=local_path,
        content_type="audio/wav"
    )
    return key

# Generate presigned URL
def get_presigned_url(key: str, expires_hours: int = 1) -> str:
    return client.presigned_get_object(
        bucket_name="feeds",
        object_name=key,
        expires=timedelta(hours=expires_hours)
    )

# Download file
def download_audio(key: str, local_path: str) -> bool:
    try:
        client.fget_object("feeds", key, local_path)
        return True
    except Exception as e:
        log.error(f"Download failed: {e}")
        return False
```

## Debugging Commands

```bash
# Check MinIO health
curl http://192.168.1.152:9000/minio/health/live

# List bucket contents (using mc client)
docker run --rm minio/mc ls myminio/feeds/calls/ --recursive

# Check file exists
docker run --rm minio/mc stat myminio/feeds/calls/playlist_id=xxx/2025/01/15/call_yyy.wav

# View MinIO logs
docker logs minio-container
```

## Common Issues

| Issue | Cause | Fix |
|-------|-------|-----|
| Key not found | Wrong path format | Check key structure matches pattern |
| Access denied | Wrong credentials | Verify MINIO_ROOT_USER/PASSWORD |
| Connection refused | MinIO not running | Start MinIO container |
| Timeout | Large file + slow network | Increase timeout, use multipart |
| SSL error | Cert mismatch | Check MINIO_USE_SSL setting |
