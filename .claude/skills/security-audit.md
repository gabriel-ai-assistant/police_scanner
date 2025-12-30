---
name: "Security Audit"
description: "Identify security vulnerabilities in code, configs, and Docker"
---

## Context

Use this skill when performing security reviews of the Police Scanner codebase. This includes checking for hardcoded secrets, SQL injection, authentication issues, and Docker security.

## Scope

Files this agent works with:
- `*.py`, `*.ts`, `*.tsx` - Source code files
- `docker-compose.yml`, `Dockerfile*` - Container configuration
- `.env.example` - Environment template
- `nginx.conf` - Web server configuration
- `app_api/routers/auth.py` - Authentication logic

## Instructions

When invoked, follow these steps:

1. **Scope the audit**
   - Identify specific files or areas to review
   - Determine audit depth (quick scan vs thorough)
   - Check for known vulnerability patterns

2. **Check for common issues**
   - Hardcoded secrets (API keys, passwords)
   - SQL injection (f-strings with user input)
   - XSS vulnerabilities (unsanitized output)
   - Authentication bypasses
   - Docker security misconfigurations

3. **Document findings**
   - Severity level (critical, high, medium, low)
   - Specific file and line references
   - Remediation steps

4. **Verify fixes**
   - Confirm vulnerabilities are addressed
   - Check no new issues introduced

## Behaviors

- Check for hardcoded secrets (API keys, passwords, tokens)
- Identify SQL injection vectors (f-strings with user input)
- Review authentication/authorization logic
- Check CORS and CSP configurations
- Validate Docker security (root users, exposed ports, default creds)
- Focus on high-severity issues first

## Constraints

- Never expose actual secret values in output
- Never commit security findings to public repos
- Provide remediation steps with all findings
- Never skip auth-related code review
- Never mark audit complete without checking .env handling

## Safety Checks

Before completing:
- [ ] .env files are gitignored
- [ ] No hardcoded credentials in source code
- [ ] SQL queries use parameterized placeholders
- [ ] Session cookies have secure flags
- [ ] Docker containers don't run as root (where possible)
- [ ] No default credentials in production configs

## Vulnerability Checklist

### Code Security
```
[ ] SQL injection - Check for f-strings in SQL
[ ] XSS - Check for unsanitized user input in responses
[ ] SSRF - Check for user-controlled URLs in requests
[ ] Path traversal - Check for user input in file paths
[ ] Command injection - Check for user input in shell commands
```

### Authentication
```
[ ] Session tokens have adequate entropy
[ ] Cookies have httpOnly, secure, sameSite flags
[ ] Password hashing uses bcrypt/argon2 (not MD5/SHA1)
[ ] Rate limiting on auth endpoints
[ ] Audit logging for auth events
```

### Configuration
```
[ ] .env not committed to git
[ ] Secrets not in docker-compose.yml
[ ] Debug mode disabled in production
[ ] CORS origins explicitly configured
[ ] CSP headers set appropriately
```

### Docker
```
[ ] No --privileged containers
[ ] Non-root users where possible
[ ] No default passwords (e.g., Flower admin:changeme)
[ ] Internal services not exposed externally
[ ] Images from trusted sources
```

## Common Patterns to Flag

```python
# BAD: SQL injection risk
query = f"SELECT * FROM users WHERE id = {user_id}"

# GOOD: Parameterized query
query = "SELECT * FROM users WHERE id = $1"
await conn.fetchrow(query, user_id)

# BAD: Hardcoded secret
API_KEY = "sk_live_abc123..."

# GOOD: Environment variable
API_KEY = os.environ.get("API_KEY")

# BAD: Command injection
os.system(f"convert {user_filename} output.png")

# GOOD: Validated input
subprocess.run(["convert", validated_path, "output.png"])
```
