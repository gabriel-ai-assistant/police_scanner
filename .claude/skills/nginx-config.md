---
name: "Nginx Config"
description: "Configure and troubleshoot frontend web serving"
---

## Context

Use this skill when configuring Nginx for the Police Scanner frontend. This includes reverse proxy setup, caching, security headers, and SSL configuration.

## Scope

Files this agent works with:
- `frontend/nginx.conf` - Main Nginx configuration
- `frontend/Dockerfile` - Multi-stage build with Nginx

## Instructions

When invoked, follow these steps:

1. **Understand the requirement**
   - Identify if it's routing, caching, or security issue
   - Check current nginx.conf configuration
   - Review error logs if available

2. **Design the change**
   - Plan location block additions/modifications
   - Consider security header implications
   - Plan cache strategy for static assets

3. **Implement**
   - Modify nginx.conf with clear comments
   - Test configuration syntax: `nginx -t`
   - Rebuild frontend container

4. **Verify**
   - Test routing works as expected
   - Verify security headers in response
   - Check cache headers on static assets

## Behaviors

- Configure reverse proxy to API backend
- Set appropriate cache headers for static assets
- Add security headers (CSP, HSTS, X-Frame-Options)
- Configure gzip compression
- Handle SPA routing fallback (try_files $uri /index.html)

## Constraints

- Never expose internal service ports directly
- Never disable security headers without justification
- Always test config with `nginx -t` before applying
- Never remove SPA fallback (breaks client-side routing)
- Never skip gzip for text-based content

## Safety Checks

Before completing:
- [ ] Configuration passes `nginx -t` syntax check
- [ ] proxy_pass targets are reachable
- [ ] Security headers present in responses
- [ ] Static assets have cache headers
- [ ] SPA routes work (non-root URLs)

## Current Configuration Reference

```nginx
server {
    listen 80;
    server_name _;
    root /usr/share/nginx/html;
    index index.html;

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    # API reverse proxy
    location /api/ {
        proxy_pass http://app_api:8000/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Static assets with long cache
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # SPA fallback
    location / {
        try_files $uri $uri/ /index.html;
    }

    # Health check
    location /health {
        proxy_pass http://app_api:8000/api/health;
    }
}
```

## Common Additions

### Content Security Policy
```nginx
add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; font-src 'self';" always;
```

### HSTS (requires HTTPS)
```nginx
add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
```

### CORS Headers
```nginx
location /api/ {
    add_header Access-Control-Allow-Origin $http_origin always;
    add_header Access-Control-Allow-Credentials true always;
    add_header Access-Control-Allow-Methods "GET, POST, PUT, DELETE, OPTIONS" always;
    add_header Access-Control-Allow-Headers "Authorization, Content-Type" always;

    if ($request_method = OPTIONS) {
        return 204;
    }

    proxy_pass http://app_api:8000/api/;
}
```

### Gzip Configuration
```nginx
gzip on;
gzip_vary on;
gzip_min_length 1024;
gzip_types text/plain text/css application/json application/javascript text/xml application/xml;
```

## Debugging Commands

```bash
# Test config syntax
docker compose exec scanner-frontend nginx -t

# View nginx error log
docker compose exec scanner-frontend cat /var/log/nginx/error.log

# Check response headers
curl -I http://localhost/

# Check API proxy
curl -I http://localhost/api/health

# Reload config without restart
docker compose exec scanner-frontend nginx -s reload
```
