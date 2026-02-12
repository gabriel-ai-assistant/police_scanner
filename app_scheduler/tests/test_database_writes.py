#!/usr/bin/env python3
"""Database write verification tests for bcfy_calls_raw table.

Run this script to verify that database write operations work correctly:
    python test_database_writes.py

Tests:
1. test_insert_new_call - Verify new call inserts successfully
2. test_duplicate_call_handling - Verify duplicates are handled correctly
3. test_update_processed_status - Verify UPDATE affects exactly 1 row
4. test_concurrent_worker_locking - Verify FOR UPDATE SKIP LOCKED works
5. test_schema_columns_exist - Verify required columns exist
"""

import asyncio
import json
import sys
import uuid

# Add shared modules to path
sys.path.insert(0, '/app/shared_bcfy')

from db_pool import get_connection, release_connection

# Test configuration
TEST_PREFIX = "TEST_"  # Prefix for test call_uids to identify cleanup targets


async def cleanup_test_data(conn):
    """Remove any test data from previous runs."""
    result = await conn.execute("""
        DELETE FROM bcfy_calls_raw WHERE call_uid LIKE $1
    """, f"{TEST_PREFIX}%")
    deleted = int(result.split()[-1])
    if deleted > 0:
        print(f"  Cleaned up {deleted} test records")


async def test_insert_new_call():
    """Test: New call is inserted successfully and returns 'inserted' status."""
    conn = await get_connection()
    try:
        await cleanup_test_data(conn)

        # Generate unique test call
        test_call_uid = f"{TEST_PREFIX}{uuid.uuid4().hex[:16]}"
        test_playlist_uuid = uuid.uuid4()

        # Use RETURNING to verify insert (same pattern as quick_insert_call_metadata)
        # Column types: group_id=text, ts=bigint, feed_id=int, tg_id=bigint, tag_id=int,
        #               node_id=bigint, sid=bigint, site_id=bigint, freq=float, src=bigint
        result = await conn.fetchrow("""
            INSERT INTO bcfy_calls_raw (
                call_uid, group_id, ts, feed_id, tg_id, tag_id, node_id, sid, site_id,
                freq, src, url, started_at, ended_at, duration_ms, size_bytes,
                fetched_at, raw_json, processed, playlist_uuid
            ) VALUES (
                $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12,
                NOW(), NOW(), $13, $14, NOW(), $15, FALSE, $16
            )
            ON CONFLICT(call_uid) DO NOTHING
            RETURNING call_uid
        """,
            test_call_uid,
            "12345",  # group_id (text)
            1700000000,  # ts (bigint)
            1,  # feed_id (int)
            100,  # tg_id (bigint)
            1,  # tag_id (int)
            1,  # node_id (bigint)
            1,  # sid (bigint)
            1,  # site_id (bigint)
            155.0,  # freq (float/double)
            1,  # src (bigint)
            "http://test.example.com/audio.mp3",  # url (text)
            5000,  # duration_ms (bigint)
            10000,  # size_bytes (bigint)
            json.dumps({"test": True}),  # raw_json
            test_playlist_uuid  # playlist_uuid
        )

        # Verify insert was successful
        assert result is not None, "INSERT RETURNING returned None - insert failed"
        assert result['call_uid'] == test_call_uid, "RETURNING call_uid mismatch"

        # Verify record exists in database
        verify = await conn.fetchrow(
            "SELECT call_uid, processed FROM bcfy_calls_raw WHERE call_uid = $1",
            test_call_uid
        )
        assert verify is not None, "Inserted record not found in database"
        assert verify['processed'] is False, "processed should be FALSE for new insert"

        # Cleanup
        await conn.execute("DELETE FROM bcfy_calls_raw WHERE call_uid = $1", test_call_uid)

    finally:
        await release_connection(conn)


async def test_duplicate_call_handling():
    """Test: Duplicate call_uid returns None (duplicate detected)."""
    conn = await get_connection()
    try:
        await cleanup_test_data(conn)

        # Generate unique test call
        test_call_uid = f"{TEST_PREFIX}{uuid.uuid4().hex[:16]}"
        test_playlist_uuid = uuid.uuid4()

        # First insert - should succeed (group_id is text)
        result1 = await conn.fetchrow("""
            INSERT INTO bcfy_calls_raw (
                call_uid, group_id, ts, fetched_at, raw_json, processed, playlist_uuid
            ) VALUES ($1, $2, $3, NOW(), $4, FALSE, $5)
            ON CONFLICT(call_uid) DO NOTHING
            RETURNING call_uid
        """, test_call_uid, "12345", 1700000000, json.dumps({}), test_playlist_uuid)

        assert result1 is not None, "First insert should succeed"

        # Second insert with same call_uid - should return None (duplicate)
        result2 = await conn.fetchrow("""
            INSERT INTO bcfy_calls_raw (
                call_uid, group_id, ts, fetched_at, raw_json, processed, playlist_uuid
            ) VALUES ($1, $2, $3, NOW(), $4, FALSE, $5)
            ON CONFLICT(call_uid) DO NOTHING
            RETURNING call_uid
        """, test_call_uid, "12345", 1700000000, json.dumps({}), test_playlist_uuid)

        assert result2 is None, "Second insert should return None (duplicate detected)"

        # Cleanup
        await conn.execute("DELETE FROM bcfy_calls_raw WHERE call_uid = $1", test_call_uid)

    finally:
        await release_connection(conn)


async def test_update_processed_status():
    """Test: UPDATE sets processed=TRUE and affects exactly 1 row."""
    conn = await get_connection()
    try:
        await cleanup_test_data(conn)

        # Insert test call (group_id is text)
        test_call_uid = f"{TEST_PREFIX}{uuid.uuid4().hex[:16]}"
        test_playlist_uuid = uuid.uuid4()

        await conn.execute("""
            INSERT INTO bcfy_calls_raw (
                call_uid, group_id, ts, fetched_at, raw_json, processed, playlist_uuid
            ) VALUES ($1, $2, $3, NOW(), $4, FALSE, $5)
        """, test_call_uid, "12345", 1700000000, json.dumps({}), test_playlist_uuid)

        # Run UPDATE (same pattern as audio_worker.py)
        result = await conn.execute("""
            UPDATE bcfy_calls_raw
            SET url = $1, s3_key_v2 = $2, processed = TRUE, last_attempt = NOW()
            WHERE call_uid = $3
        """, "s3://test/test.wav", "calls/test.wav", test_call_uid)

        # Verify exactly 1 row was updated (asyncpg returns "UPDATE N")
        rows_affected = int(result.split()[-1])
        assert rows_affected == 1, f"UPDATE should affect 1 row, got {rows_affected}"

        # Verify processed=TRUE
        verify = await conn.fetchrow(
            "SELECT processed, s3_key_v2 FROM bcfy_calls_raw WHERE call_uid = $1",
            test_call_uid
        )
        assert verify['processed'] is True, "processed should be TRUE after UPDATE"
        assert verify['s3_key_v2'] == "calls/test.wav", "s3_key_v2 should be set"

        # Cleanup
        await conn.execute("DELETE FROM bcfy_calls_raw WHERE call_uid = $1", test_call_uid)

    finally:
        await release_connection(conn)


async def test_concurrent_worker_locking():
    """Test: FOR UPDATE SKIP LOCKED prevents duplicate processing.

    This test simulates two concurrent workers trying to select the same unprocessed call.
    With FOR UPDATE SKIP LOCKED, only one should get the row.
    """
    conn1 = await get_connection()
    conn2 = await get_connection()
    try:
        await cleanup_test_data(conn1)

        # Insert test call (group_id is text)
        test_call_uid = f"{TEST_PREFIX}{uuid.uuid4().hex[:16]}"
        test_playlist_uuid = uuid.uuid4()

        await conn1.execute("""
            INSERT INTO bcfy_calls_raw (
                call_uid, group_id, ts, url, fetched_at, raw_json, processed, playlist_uuid
            ) VALUES ($1, $2, $3, $4, NOW(), $5, FALSE, $6)
        """, test_call_uid, "12345", 1700000000, "http://test.example.com/audio.mp3",
           json.dumps({}), test_playlist_uuid)

        # Start transaction on conn1 and lock the row
        await conn1.execute("BEGIN")
        rows1 = await conn1.fetch("""
            SELECT call_uid FROM bcfy_calls_raw
            WHERE call_uid = $1 AND processed = FALSE
            FOR UPDATE SKIP LOCKED
        """, test_call_uid)

        # conn1 should have locked the row
        assert len(rows1) == 1, f"conn1 should lock 1 row, got {len(rows1)}"

        # conn2 tries to select the same row with SKIP LOCKED
        rows2 = await conn2.fetch("""
            SELECT call_uid FROM bcfy_calls_raw
            WHERE call_uid = $1 AND processed = FALSE
            FOR UPDATE SKIP LOCKED
        """, test_call_uid)

        # conn2 should get 0 rows (row is locked by conn1)
        assert len(rows2) == 0, f"conn2 should get 0 rows (locked), got {len(rows2)}"

        # Rollback conn1 transaction
        await conn1.execute("ROLLBACK")

        # Now conn2 should be able to get the row
        rows2_after = await conn2.fetch("""
            SELECT call_uid FROM bcfy_calls_raw
            WHERE call_uid = $1 AND processed = FALSE
            FOR UPDATE SKIP LOCKED
        """, test_call_uid)

        assert len(rows2_after) == 1, f"After rollback, conn2 should get 1 row, got {len(rows2_after)}"

        # Cleanup
        await conn1.execute("DELETE FROM bcfy_calls_raw WHERE call_uid = $1", test_call_uid)

    finally:
        await release_connection(conn1)
        await release_connection(conn2)


async def test_schema_columns_exist():
    """Test: Required columns from migration 005 exist."""
    conn = await get_connection()
    try:
        result = await conn.fetch("""
            SELECT column_name FROM information_schema.columns
            WHERE table_name = 'bcfy_calls_raw'
            AND column_name IN ('playlist_uuid', 's3_key_v2')
        """)

        columns = [r['column_name'] for r in result]
        assert 'playlist_uuid' in columns, "Missing column: playlist_uuid"
        assert 's3_key_v2' in columns, "Missing column: s3_key_v2"

    finally:
        await release_connection(conn)


async def run_all_tests():
    """Run all database write tests."""
    tests = [
        ("test_insert_new_call", test_insert_new_call),
        ("test_duplicate_call_handling", test_duplicate_call_handling),
        ("test_update_processed_status", test_update_processed_status),
        ("test_concurrent_worker_locking", test_concurrent_worker_locking),
        ("test_schema_columns_exist", test_schema_columns_exist),
    ]

    print("=" * 60)
    print("Database Write Verification Tests")
    print("=" * 60)

    passed = 0
    failed = 0

    for name, test in tests:
        try:
            print(f"\nRunning: {name}...")
            await test()
            print(f"  PASS: {name}")
            passed += 1
        except AssertionError as e:
            print(f"  FAIL: {name}")
            print(f"        {e}")
            failed += 1
        except Exception as e:
            print(f"  ERROR: {name}")
            print(f"         {type(e).__name__}: {e}")
            failed += 1

    print("\n" + "=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)

    return failed == 0


if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)
