#!/usr/bin/env bash
set -euo pipefail
curl -H "Authorization: Bearer ${MEILI_MASTER_KEY}" \
     -H "Content-Type: application/json" \
     -X POST "${MEILI_HOST}/indexes" \
     -d '{"uid":"transcripts"}' || true
echo "transcripts index ensured."
