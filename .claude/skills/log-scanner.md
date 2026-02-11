---
name: "Log Scanner"
description: "Analyze container and application logs for debugging"
---

## Context

Use this skill when debugging issues by analyzing logs from Docker containers, application logs, or the system_logs database table. This is the primary tool for diagnosing production issues.

## Scope

Files and sources this agent works with:
- Container logs via: `docker compose logs <service>`
- Database logs: `system_logs` table
- Any `*.log` files in project directories

## Instructions

When invoked, follow these steps:

1. **Identify the scope**
   - Determine which service(s) to investigate
   - Establish time range for the issue
   - Identify known error messages or symptoms

2. **Gather logs**
   - Use `docker compose logs --tail=100 <service>` for recent logs
   - Filter by timestamp if issue is time-bounded
   - Check multiple related services if needed

3. **Analyze patterns**
   - Look for ERROR and WARNING levels first
   - Identify repeated error patterns
   - Trace request flow across services
   - Check for timing/resource issues

4. **Report findings**
   - Summarize root cause
   - Provide specific log excerpts
   - Suggest remediation steps

## Behaviors

- Use `docker compose logs --tail=100 <service>` for recent logs
- Filter logs by timestamp range when relevant
- Identify patterns: repeated errors, timing issues, resource exhaustion
- Correlate errors across services (scheduler → transcription → API)
- Summarize findings with root cause analysis
- Focus on ERROR and WARNING levels first

## Constraints

- Never store or output sensitive data from logs (tokens, passwords)
- Limit log retrieval to relevant time windows (avoid huge outputs)
- Focus on actionable findings, not exhaustive log dumps
- Never modify log files
- Always verify container is running before fetching logs

## Safety Checks

Before completing:
- [ ] Container running verified before log fetch
- [ ] Sensitive data (tokens, passwords) redacted from output
- [ ] Root cause identified or clearly stated as unknown
- [ ] Actionable next steps provided
- [ ] Related services checked for correlated errors

## Service Log Commands

```bash
# API logs
docker compose logs --tail=100 scanner-api

# Transcription worker logs
docker compose logs --tail=100 scanner-transcription

# Scheduler logs
docker compose logs --tail=100 app-scheduler

# All services, follow mode
docker compose logs -f --tail=50

# Filter by time (last hour)
docker compose logs --since=1h scanner-api

# Grep for errors
docker compose logs scanner-api 2>&1 | grep -i error
```

## Database Logs Query

```sql
-- Recent system logs
SELECT timestamp, component, event_type, severity, message
FROM system_logs
WHERE timestamp > NOW() - INTERVAL '1 hour'
  AND severity IN ('ERROR', 'WARNING')
ORDER BY timestamp DESC
LIMIT 50;

-- Logs by component
SELECT * FROM system_logs
WHERE component = 'transcription'
  AND timestamp > NOW() - INTERVAL '24 hours'
ORDER BY timestamp DESC;
```

## Common Error Patterns

| Pattern | Likely Cause | Investigation |
|---------|--------------|---------------|
| Connection refused | Service not running | Check container status |
| Timeout | Slow query/API | Check database/network |
| Out of memory | Resource exhaustion | Check container limits |
| Permission denied | File/S3 access | Check credentials/paths |
| Task stuck | Worker crashed | Check Celery worker logs |
