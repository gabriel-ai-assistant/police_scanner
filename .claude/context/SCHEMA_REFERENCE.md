# Database Schema Reference

Condensed schema reference for the Police Scanner Platform.

## Core Tables

### bcfy_calls_raw (Call Metadata)
```sql
call_uid        TEXT PRIMARY KEY    -- Broadcastify call ID
group_id        INTEGER             -- Source group
feed_id         INTEGER             -- Feed ID
tg_id           INTEGER             -- Talkgroup ID
tag_id          INTEGER             -- Tag ID
url             TEXT                -- Original audio URL
started_at      TIMESTAMPTZ         -- Call start time
ended_at        TIMESTAMPTZ         -- Call end time
duration_ms     INTEGER             -- Duration in milliseconds
processed       BOOLEAN DEFAULT FALSE
playlist_uuid   UUID                -- Associated playlist
s3_key_v2       TEXT                -- S3 path (hierarchical)
error           TEXT                -- Last error message
created_at      TIMESTAMPTZ DEFAULT NOW()
```

### transcripts (Whisper Transcriptions)
```sql
id              BIGSERIAL PRIMARY KEY
call_uid        TEXT UNIQUE REFERENCES bcfy_calls_raw(call_uid)
text            TEXT                -- Full transcript text
words           JSONB               -- Word-level timestamps [{start, end, text}]
language        TEXT DEFAULT 'en'
confidence      NUMERIC DEFAULT 0
duration_seconds NUMERIC DEFAULT 0
s3_key_v2       TEXT                -- S3 path to audio
tsv             TSVECTOR            -- Full-text search vector
created_at      TIMESTAMPTZ DEFAULT NOW()
```

### processing_state (Pipeline Tracking)
```sql
id              BIGSERIAL PRIMARY KEY
call_uid        TEXT UNIQUE REFERENCES bcfy_calls_raw(call_uid)
status          TEXT CHECK (status IN ('queued','downloaded','transcribed','indexed','error'))
error           TEXT
retry_count     INTEGER DEFAULT 0
max_retries     INTEGER DEFAULT 3
created_at      TIMESTAMPTZ DEFAULT NOW()
updated_at      TIMESTAMPTZ DEFAULT NOW()
```

### bcfy_playlists (Scanner Feeds)
```sql
uuid            UUID PRIMARY KEY
name            TEXT
listeners       INTEGER
num_groups      INTEGER
groups_json     JSONB               -- Feed groups metadata
last_pos        BIGINT DEFAULT 0
sync            BOOLEAN DEFAULT FALSE
fetched_at      TIMESTAMPTZ
```

## Geographic Tables

### bcfy_countries
```sql
coid            INTEGER PRIMARY KEY
country_code    TEXT
country_name    TEXT
iso_alpha2      TEXT
sync            BOOLEAN DEFAULT FALSE
```

### bcfy_states
```sql
stid            INTEGER PRIMARY KEY
coid            INTEGER REFERENCES bcfy_countries(coid) ON DELETE CASCADE
state_code      TEXT
state_name      TEXT
```

### bcfy_counties
```sql
cntid           INTEGER PRIMARY KEY
stid            INTEGER REFERENCES bcfy_states(stid) ON DELETE CASCADE
coid            INTEGER REFERENCES bcfy_countries(coid) ON DELETE CASCADE
county_name     TEXT
lat             NUMERIC
lon             NUMERIC
fips            TEXT
timezone_str    TEXT
```

## Key Indexes

```sql
-- Call queries
idx_calls_feed_time       ON bcfy_calls_raw(feed_id, started_at DESC)
idx_calls_unprocessed     ON bcfy_calls_raw(started_at DESC) WHERE processed = FALSE
idx_calls_playlist_time   ON bcfy_calls_raw(playlist_uuid, started_at DESC)

-- Transcript search
idx_transcripts_fts       ON transcripts USING GIN(tsv)
idx_transcripts_time      ON transcripts(created_at DESC)

-- Pipeline
idx_processing_status     ON processing_state(status, updated_at) WHERE status NOT IN ('indexed')
```

## Common Queries

### Recent Calls
```sql
SELECT * FROM bcfy_calls_raw
WHERE started_at > NOW() - INTERVAL '24 hours'
ORDER BY started_at DESC
LIMIT 100;
```

### Unprocessed Calls
```sql
SELECT * FROM bcfy_calls_raw
WHERE processed = FALSE
ORDER BY started_at ASC
LIMIT 50;
```

### Transcript Search
```sql
SELECT * FROM transcripts
WHERE tsv @@ plainto_tsquery('english', $1)
ORDER BY created_at DESC
LIMIT 20;
```

### Pipeline Status
```sql
SELECT status, COUNT(*)
FROM processing_state
GROUP BY status;
```

### Call with Transcript
```sql
SELECT c.*, t.text, t.confidence
FROM bcfy_calls_raw c
LEFT JOIN transcripts t ON c.call_uid = t.call_uid
WHERE c.started_at > NOW() - INTERVAL '1 hour';
```

## Type Mappings

| PostgreSQL | Python | TypeScript |
|------------|--------|------------|
| TEXT | str | string |
| INTEGER | int | number |
| BIGINT | int | number |
| NUMERIC | Decimal/float | number |
| BOOLEAN | bool | boolean |
| TIMESTAMPTZ | datetime | string (ISO) |
| JSONB | dict/list | object/array |
| UUID | UUID/str | string |
