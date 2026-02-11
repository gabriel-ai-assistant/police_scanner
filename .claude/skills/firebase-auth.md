---
name: "Firebase Auth"
description: "Implement and debug Firebase authentication flows"
---

## Context

Use this skill when working with Firebase authentication in the Police Scanner platform. This includes session management, role-based access control, and authentication debugging.

## Scope

Files this agent works with:
- `app_api/routers/auth.py` - Authentication endpoints
- `app_api/auth/dependencies.py` - Auth dependency injection
- `app_api/auth/firebase.py` - Firebase admin SDK setup
- `frontend/src/contexts/AuthContext.tsx` - Frontend auth state
- `frontend/src/api/auth.ts` - Auth API client

## Instructions

When invoked, follow these steps:

1. **Understand the issue**
   - Identify if it's frontend or backend auth issue
   - Check if session cookies are being set/sent
   - Review Firebase console for user status

2. **Debug the flow**
   - Trace token from Firebase → backend → cookie → request
   - Check CORS settings for credentials
   - Verify Firebase project ID matches

3. **Implement changes**
   - Use httpOnly cookies for session tokens
   - Log auth events to audit table
   - Handle token refresh gracefully

4. **Verify**
   - Test login/logout flow end-to-end
   - Verify protected routes enforce auth
   - Check audit logs capture events

## Behaviors

- Validate Firebase ID tokens server-side
- Set httpOnly session cookies (not localStorage)
- Use `require_auth` dependency for protected routes
- Log all auth events to `auth_audit_log` table
- Handle token refresh gracefully
- Use role-based access (user/admin)

## Constraints

- Never store tokens in frontend localStorage
- Never log full tokens (only last 8 chars for debugging)
- Never bypass auth checks even for testing
- Never expose user passwords or tokens in responses
- Never trust client-side role claims

## Safety Checks

Before completing:
- [ ] Session cookies have httpOnly=true
- [ ] Cookies have secure=true in production
- [ ] SameSite cookie attribute set appropriately
- [ ] CORS allows credentials from frontend origin
- [ ] Firebase project ID matches environment
- [ ] Audit logging captures all auth events

## Authentication Flow

```
1. Frontend: User signs in with Firebase (Google/email)
2. Frontend: Get ID token from Firebase
3. Frontend: POST /api/auth/session { idToken }
4. Backend: Verify token with Firebase Admin SDK
5. Backend: Create/update user in database
6. Backend: Set httpOnly session cookie
7. Frontend: Subsequent requests include cookie automatically
8. Backend: Validate cookie on protected routes
```

## Code Patterns

```python
# Protected route dependency
from app_api.auth.dependencies import require_auth, require_admin

@router.get("/protected")
async def protected_route(
    user: dict = Depends(require_auth),
    pool = Depends(get_pool)
):
    # user contains: id, email, role, firebase_uid
    return {"user": user["email"]}

@router.get("/admin-only")
async def admin_route(
    user: dict = Depends(require_admin),
    pool = Depends(get_pool)
):
    # Only admins reach here
    return {"admin": True}
```

```typescript
// Frontend auth context usage
const { user, isAuthenticated, isAdmin, logout } = useAuth();

if (!isAuthenticated) {
  return <Navigate to="/login" />;
}
```

## Session Cookie Configuration

```python
response.set_cookie(
    key=settings.session_cookie_name,
    value=session_token,
    httponly=True,           # Prevent XSS access
    secure=settings.cookie_secure,  # HTTPS only in prod
    samesite="lax",          # CSRF protection
    max_age=settings.session_max_age,  # 7 days default
)
```

## Debugging Commands

```bash
# Check Firebase config
docker compose exec scanner-api python -c "
from app_api.auth.firebase import firebase_app
print(firebase_app.project_id)
"

# Check user in database
psql -c "SELECT email, role, is_active FROM users WHERE email = 'user@example.com'"

# View auth audit log
psql -c "SELECT * FROM auth_audit_log ORDER BY timestamp DESC LIMIT 20"
```
