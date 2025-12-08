#!/bin/bash
# Deploy database schema changes

export PGPASSWORD='DuL7tZ6yKKbRmP*BWkc*JgtQi_.siE.iKiK2qskATMpKuFjAoNJhWvsCf*'

echo "Applying database schema to AWS RDS..."
docker run --rm -i \
  -e PGPASSWORD="$PGPASSWORD" \
  postgres:16 \
  psql -h police-scanner.cilycke4i4nz.us-east-1.rds.amazonaws.com \
       -U scan \
       -d scanner \
       -f - < db/init.sql

echo "Database schema applied successfully!"
