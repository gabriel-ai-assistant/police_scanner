#!/usr/bin/env python3
"""Database schema analysis script for expert DBA review"""
import asyncio
import asyncpg
import json
from datetime import datetime

DATABASE_URL = "postgresql://scan:DuL7tZ6yKKbRmP*BWkc*JgtQi_.siE.iKiK2qskATMpKuFjAoNJhWvsCf*@police-scanner.cilycke4i4nz.us-east-1.rds.amazonaws.com:5432/scanner"

async def analyze_database():
    conn = await asyncpg.connect(DATABASE_URL)

    print("=" * 80)
    print("DATABASE SCHEMA ANALYSIS")
    print("=" * 80)

    # List all tables
    print("\n### TABLES ###")
    tables = await conn.fetch("""
        SELECT schemaname, tablename,
               pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size,
               pg_total_relation_size(schemaname||'.'||tablename) AS size_bytes
        FROM pg_tables
        WHERE schemaname NOT IN ('pg_catalog', 'information_schema')
        ORDER BY size_bytes DESC
    """)
    for row in tables:
        print(f"  {row['tablename']:30} | {row['size']:>12} | schema: {row['schemaname']}")

    # Get detailed schema for each table
    print("\n\n### TABLE DETAILS ###")
    for table in tables:
        tablename = table['tablename']
        print(f"\n--- {tablename} ---")

        # Columns
        columns = await conn.fetch("""
            SELECT column_name, data_type, character_maximum_length,
                   is_nullable, column_default
            FROM information_schema.columns
            WHERE table_name = $1
            ORDER BY ordinal_position
        """, tablename)

        print("Columns:")
        for col in columns:
            nullable = "NULL" if col['is_nullable'] == 'YES' else "NOT NULL"
            default = f" DEFAULT {col['column_default']}" if col['column_default'] else ""
            max_len = f"({col['character_maximum_length']})" if col['character_maximum_length'] else ""
            print(f"  - {col['column_name']:25} {col['data_type']}{max_len:15} {nullable:10}{default}")

        # Indexes
        indexes = await conn.fetch("""
            SELECT indexname, indexdef
            FROM pg_indexes
            WHERE tablename = $1
            ORDER BY indexname
        """, tablename)

        if indexes:
            print("Indexes:")
            for idx in indexes:
                print(f"  - {idx['indexname']}")

        # Foreign keys
        fkeys = await conn.fetch("""
            SELECT
                tc.constraint_name,
                kcu.column_name,
                ccu.table_name AS foreign_table_name,
                ccu.column_name AS foreign_column_name,
                rc.delete_rule,
                rc.update_rule
            FROM information_schema.table_constraints AS tc
            JOIN information_schema.key_column_usage AS kcu
                ON tc.constraint_name = kcu.constraint_name
            JOIN information_schema.constraint_column_usage AS ccu
                ON ccu.constraint_name = tc.constraint_name
            JOIN information_schema.referential_constraints AS rc
                ON rc.constraint_name = tc.constraint_name
            WHERE tc.constraint_type = 'FOREIGN KEY'
              AND tc.table_name = $1
        """, tablename)

        if fkeys:
            print("Foreign Keys:")
            for fk in fkeys:
                print(f"  - {fk['column_name']} -> {fk['foreign_table_name']}.{fk['foreign_column_name']} "
                      f"(ON DELETE {fk['delete_rule']}, ON UPDATE {fk['update_rule']})")

        # Check constraints
        checks = await conn.fetch("""
            SELECT constraint_name, check_clause
            FROM information_schema.check_constraints
            WHERE constraint_schema = 'public'
              AND constraint_name IN (
                  SELECT constraint_name
                  FROM information_schema.table_constraints
                  WHERE table_name = $1 AND constraint_type = 'CHECK'
              )
        """, tablename)

        if checks:
            print("Check Constraints:")
            for chk in checks:
                print(f"  - {chk['constraint_name']}: {chk['check_clause']}")

        # Row count
        count = await conn.fetchval(f"SELECT COUNT(*) FROM {tablename}")
        print(f"Row count: {count:,}")

    # List all functions
    print("\n\n### FUNCTIONS ###")
    functions = await conn.fetch("""
        SELECT routine_name, routine_definition
        FROM information_schema.routines
        WHERE routine_schema = 'public'
    """)
    for func in functions:
        print(f"\n{func['routine_name']}:")
        print(f"  {func['routine_definition'][:100]}...")

    # List all triggers
    print("\n\n### TRIGGERS ###")
    triggers = await conn.fetch("""
        SELECT trigger_name, event_manipulation, event_object_table, action_statement
        FROM information_schema.triggers
        WHERE trigger_schema = 'public'
    """)
    for trig in triggers:
        print(f"  {trig['trigger_name']} on {trig['event_object_table']} ({trig['event_manipulation']})")
        print(f"    Action: {trig['action_statement']}")

    # Check for missing indexes on foreign keys
    print("\n\n### INDEX ANALYSIS ###")
    print("Foreign keys without indexes (performance concern):")
    fk_analysis = await conn.fetch("""
        SELECT
            tc.table_name,
            kcu.column_name,
            ccu.table_name AS foreign_table_name
        FROM information_schema.table_constraints AS tc
        JOIN information_schema.key_column_usage AS kcu
            ON tc.constraint_name = kcu.constraint_name
        JOIN information_schema.constraint_column_usage AS ccu
            ON ccu.constraint_name = tc.constraint_name
        WHERE tc.constraint_type = 'FOREIGN KEY'
          AND NOT EXISTS (
              SELECT 1
              FROM pg_indexes
              WHERE tablename = tc.table_name
                AND indexdef LIKE '%' || kcu.column_name || '%'
          )
    """)

    if fk_analysis:
        for fk in fk_analysis:
            print(f"  ⚠️  {fk['table_name']}.{fk['column_name']} -> {fk['foreign_table_name']}")
    else:
        print("  ✅ All foreign keys have indexes")

    # Check for unused indexes
    print("\n\nIndex usage statistics (requires pg_stat_statements):")
    try:
        unused_indexes = await conn.fetch("""
            SELECT schemaname, tablename, indexname, idx_scan
            FROM pg_stat_user_indexes
            WHERE idx_scan = 0
              AND indexrelname NOT LIKE '%_pkey'
            ORDER BY pg_relation_size(indexrelid) DESC
        """)
        if unused_indexes:
            print("Potentially unused indexes:")
            for idx in unused_indexes:
                print(f"  - {idx['tablename']}.{idx['indexname']} (scans: {idx['idx_scan']})")
        else:
            print("  All indexes are being used")
    except Exception as e:
        print(f"  Unable to check: {e}")

    # Table bloat analysis
    print("\n\n### TABLE STATISTICS ###")
    stats = await conn.fetch("""
        SELECT
            schemaname,
            tablename,
            n_live_tup AS live_rows,
            n_dead_tup AS dead_rows,
            last_vacuum,
            last_autovacuum,
            last_analyze,
            last_autoanalyze
        FROM pg_stat_user_tables
        ORDER BY n_dead_tup DESC
    """)

    print("Table maintenance status:")
    for stat in stats:
        dead_pct = (stat['dead_rows'] / max(stat['live_rows'], 1)) * 100 if stat['live_rows'] else 0
        print(f"  {stat['tablename']:30} | Live: {stat['live_rows']:>8,} | Dead: {stat['dead_rows']:>8,} ({dead_pct:.1f}%)")
        if stat['last_autovacuum']:
            print(f"    Last autovacuum: {stat['last_autovacuum']}")

    await conn.close()
    print("\n" + "=" * 80)
    print("Analysis complete")

if __name__ == "__main__":
    asyncio.run(analyze_database())
