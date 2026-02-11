---
name: "Database Migration"
description: "Create, validate, and execute PostgreSQL migrations"
---

## Context

Use this skill when making changes to the PostgreSQL database schema. This includes creating new tables, adding columns, creating indexes, and modifying constraints. All schema changes must go through migration files.

## Scope

Files this agent works with:
- `db/migrations/*.sql` - Migration files (numbered sequentially)
- `db/init.sql` - Base schema reference
- `db/run_migrations.py` - Migration execution script
- `db/migration_validator.py` - Pre-migration validation

## Instructions

When invoked, follow these steps:

1. **Understand the task**
   - Identify the schema change required
   - Check existing schema in `db/init.sql` and recent migrations
   - Determine the next migration number (e.g., 011, 012)

2. **Design the migration**
   - Plan forward migration (CREATE, ALTER, etc.)
   - Document rollback steps in comments
   - Consider foreign key dependencies
   - Plan necessary indexes

3. **Write the migration file**
   - Use `BEGIN;` / `COMMIT;` transaction wrapper
   - Add `IF NOT EXISTS` guards for idempotency
   - Include `COMMENT ON TABLE/COLUMN` for documentation
   - Add rollback SQL in comments

4. **Validate**
   - Run `migration_validator.py` to check syntax
   - Verify foreign key references exist
   - Check index naming conventions

## Behaviors

- Wrap migrations in `BEGIN;` / `COMMIT;` transactions
- Use `IF NOT EXISTS` guards for idempotency
- Add `COMMENT ON TABLE/COLUMN` for documentation
- Include rollback SQL in comments (not executed)
- Number migrations sequentially: `011_*.sql`, `012_*.sql`
- Follow naming convention: `NNN_descriptive_name.sql`

## Constraints

- Never use `DROP TABLE` without explicit user confirmation
- Never modify existing migration files (create new ones instead)
- Never hardcode database credentials in migration files
- Never create migrations that lock tables for extended periods
- Never skip transaction wrapping for DDL statements

## Safety Checks

Before completing:
- [ ] Migration wrapped in BEGIN/COMMIT transaction
- [ ] IF NOT EXISTS guards prevent duplicate creation
- [ ] Foreign key references point to existing tables
- [ ] Index names follow convention: `idx_tablename_columnname`
- [ ] Rollback steps documented in comments
- [ ] No sensitive data or credentials in migration file

## Example Migration Structure

```sql
-- Migration: 011_add_alerts_table.sql
-- Purpose: Add alerts table for notification system
-- Rollback: DROP TABLE IF EXISTS alerts;

BEGIN;

CREATE TABLE IF NOT EXISTS alerts (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    message TEXT NOT NULL,
    severity VARCHAR(20) DEFAULT 'info',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    read_at TIMESTAMP WITH TIME ZONE
);

COMMENT ON TABLE alerts IS 'User notification alerts';
COMMENT ON COLUMN alerts.severity IS 'Alert level: info, warning, error';

CREATE INDEX IF NOT EXISTS idx_alerts_user_id ON alerts(user_id);
CREATE INDEX IF NOT EXISTS idx_alerts_created_at ON alerts(created_at);

COMMIT;
```
