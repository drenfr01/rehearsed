# Auth redesign: implementation guide

**Design doc:** [auth-redesign.md](./auth-redesign.md)

This document provides step-by-step implementation instructions for the JWT hardening changes. Steps are ordered so the codebase compiles and tests pass after each phase.

---

## Phase 1 — Backend utilities and config

These changes are foundational. Nothing depends on them yet, so they can land first.

### Step 1.1: Update `backend/app/utils/auth.py`

Replace the entire file. Key changes from current:

- Add `VALID_TOKEN_TYPES = {"user", "session"}` constant. Both `create_access_token` and `verify_token_any_type` validate against it.
- `create_access_token`: rename `thread_id` → `subject`, add required `token_type: str` and optional `extra_claims: dict`, generate `jti` via `uuid.uuid4()`, validate `token_type` against `VALID_TOKEN_TYPES`, validate `extra_claims` keys against an allow-list.
- `verify_token`: add required `expected_type: str`, reject tokens whose `type` claim doesn't match.
- Add `verify_token_any_type`: returns `(subject, token_type)` tuple; rejects unknown token types at the utility layer so callers don't need to duplicate this check.
- Keep the existing format-validation regex and `ValueError` raises — callers depend on them.

```python
import re
import uuid
from datetime import UTC, datetime, timedelta
from typing import Optional

from jose import JWTError, jwt

from app.core.config import settings
from app.core.logging import logger
from app.schemas.auth import Token

ALLOWED_EXTRA_CLAIMS = {"is_admin"}
VALID_TOKEN_TYPES = {"user", "session"}


def create_access_token(
    subject: str,
    token_type: str,
    expires_delta: Optional[timedelta] = None,
    extra_claims: Optional[dict] = None,
) -> Token:
    if token_type not in VALID_TOKEN_TYPES:
        raise ValueError(f"token_type must be one of {VALID_TOKEN_TYPES}")
    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(UTC) + timedelta(days=settings.JWT_ACCESS_TOKEN_EXPIRE_DAYS)

    to_encode = {
        "sub": subject,
        "type": token_type,
        "exp": expire,
        "iat": datetime.now(UTC),
        "jti": str(uuid.uuid4()),
    }

    if extra_claims:
        if not set(extra_claims.keys()).issubset(ALLOWED_EXTRA_CLAIMS):
            raise ValueError(f"extra_claims keys must be in {ALLOWED_EXTRA_CLAIMS}")
        to_encode.update(extra_claims)

    encoded_jwt = jwt.encode(
        to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM
    )
    return Token(access_token=encoded_jwt, expires_at=expire)


def _validate_token_format(token: str) -> None:
    if not token or not isinstance(token, str):
        logger.warning("token_invalid_format")
        raise ValueError("Token must be a non-empty string")
    if not re.match(r"^[A-Za-z0-9-_]+\.[A-Za-z0-9-_]+\.[A-Za-z0-9-_]+$", token):
        logger.warning("token_suspicious_format")
        raise ValueError("Token format is invalid - expected JWT format")


def _decode_payload(token: str) -> Optional[dict]:
    _validate_token_format(token)
    try:
        return jwt.decode(
            token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
        )
    except JWTError as e:
        logger.error("token_verification_failed", error=str(e))
        return None


def verify_token(token: str, expected_type: str) -> Optional[str]:
    payload = _decode_payload(token)
    if payload is None:
        return None
    if payload.get("type") != expected_type:
        logger.warning("token_type_mismatch", expected=expected_type, got=payload.get("type"))
        return None
    subject = payload.get("sub")
    if subject is None:
        logger.warning("token_missing_subject")
    return subject


def verify_token_any_type(token: str) -> Optional[tuple[str, str]]:
    payload = _decode_payload(token)
    if payload is None:
        return None
    token_type = payload.get("type")
    subject = payload.get("sub")
    if not token_type or not subject:
        return None
    if token_type not in VALID_TOKEN_TYPES:
        logger.warning("token_unknown_type", token_type=token_type)
        return None
    return (subject, token_type)
```

### Step 1.2: Update `backend/app/core/config.py`

Three changes in the JWT Configuration block:

1. Change the default for `JWT_ACCESS_TOKEN_EXPIRE_DAYS` from `"30"` to `"7"`.
2. Add `JWT_USER_TOKEN_EXPIRE_MINUTES`.
3. Add startup validation at the end of `__init__`.

**JWT Configuration block** — replace:

```python
# JWT Configuration
self.JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "")
self.JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
self.JWT_ACCESS_TOKEN_EXPIRE_DAYS = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_DAYS", "30"))
```

with:

```python
# JWT Configuration
self.JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "")
self.JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
self.JWT_ACCESS_TOKEN_EXPIRE_DAYS = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_DAYS", "7"))
self.JWT_USER_TOKEN_EXPIRE_MINUTES = int(os.getenv("JWT_USER_TOKEN_EXPIRE_MINUTES", "15"))
```

**Startup validation** — add at the end of `__init__`, after `self.apply_environment_settings()`:

```python
if self.ENVIRONMENT != Environment.TEST:
    if not self.JWT_SECRET_KEY or len(self.JWT_SECRET_KEY) < 32:
        raise ValueError(
            "JWT_SECRET_KEY must be set to a value of at least "
            "32 characters in non-test environments"
        )
```

**Gotcha:** Any non-test `.env` files (`backend/.env`, `.env.development`, etc.) must have a `JWT_SECRET_KEY` of at least 32 characters or the app will crash on startup. Update them before running.

### Step 1.3: Add `SessionListItem` to `backend/app/schemas/auth.py`

Add after the existing `SessionResponse` class:

```python
class SessionListItem(BaseModel):
    """Response model for session list items (no token)."""

    session_id: str = Field(..., description="The unique identifier for the chat session")
    name: str = Field(default="", description="Name of the session", max_length=100)
```

---

## Phase 2 — Backend auth routes

These changes update all `create_access_token` and `verify_token` call sites in `backend/app/api/v1/auth.py`.

### Step 2.1: Update imports

Add `verify_token_any_type` to the import from `app.utils.auth`:

```python
from app.utils.auth import (
    create_access_token,
    verify_token,
    verify_token_any_type,
)
```

Add `timedelta` to the datetime imports and `SessionListItem` to the schema imports:

```python
from datetime import timedelta

from app.schemas.auth import (
    ...
    SessionListItem,
)
```

### Step 2.2: Update `get_current_user`

Change the `verify_token` call to pass `expected_type="user"`:

```python
user_id = verify_token(token, expected_type="user")
```

No other changes to this function.

### Step 2.3: Update `get_current_session`

Change the `verify_token` call to pass `expected_type="session"`:

```python
session_id = verify_token(token, expected_type="session")
```

### Step 2.4: Add `get_current_user_from_any_token`

Add this new dependency function after `get_current_session`:

```python
async def get_current_user_from_any_token(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    database_service: DatabaseService = Depends(get_database_service),
) -> User:
    try:
        token = sanitize_string(credentials.credentials)
    except ValueError as ve:
        logger.error("token_validation_failed", error=str(ve), exc_info=True)
        raise HTTPException(
            status_code=401,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    result = verify_token_any_type(token)
    if result is None:
        raise HTTPException(
            status_code=401,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    subject, token_type = result

    if token_type == "user":
        try:
            user_id = int(subject)
        except (ValueError, TypeError):
            raise HTTPException(
                status_code=401,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        user = await database_service.users.get_user(user_id)
    elif token_type == "session":
        session = await database_service.sessions.get_session(subject)
        if session is None:
            raise HTTPException(
                status_code=401,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        user = await database_service.users.get_user(session.user_id)
    else:
        raise HTTPException(
            status_code=401,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if user is None:
        raise HTTPException(
            status_code=401,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user
```

**Key design decisions in this function:**

- The `int(subject)` conversion for user tokens is wrapped in a local try/except that returns **401** with a generic message, not 422. This avoids leaking information about the expected subject format.
- All failure branches use the same generic `"Invalid authentication credentials"` message — callers cannot distinguish between a bad token type, a non-integer subject, or a missing user/session.
- The outer `except ValueError` is narrowed to only cover `sanitize_string`, keeping error handling explicit rather than relying on a catch-all.

### Step 2.5: Update `login` handler

Pass `token_type="user"` and the shortened expiry:

```python
token = create_access_token(
    str(user.id),
    token_type="user",
    expires_delta=timedelta(minutes=settings.JWT_USER_TOKEN_EXPIRE_MINUTES),
)
```

### Step 2.6: Update `create_session` handler

1. Change the dependency from `get_current_user` to `get_current_user_from_any_token`.
2. Pass `token_type="session"` and `extra_claims`:

```python
@router.post("/session", response_model=SessionResponse)
async def create_session(
    user: User = Depends(get_current_user_from_any_token),
    database_service: DatabaseService = Depends(get_database_service),
):
```

In the body, change the `create_access_token` call:

```python
token = create_access_token(
    session_id,
    token_type="session",
    extra_claims={"is_admin": user.is_admin},
)
```

### Step 2.7: Update `update_session_name` handler

The re-minted session token must include the `is_admin` claim so the frontend continues to show the correct UI after a rename. This requires looking up the user through the session:

```python
user = await database_service.users.get_user(session.user_id)
token = create_access_token(
    sanitized_session_id,
    token_type="session",
    extra_claims={"is_admin": user.is_admin if user else False},
)
```

If the handler does not already have `database_service` as a dependency, add `database_service: DatabaseService = Depends(get_database_service)` to its signature. The session object (needed for `session.user_id`) should already be available since the handler loads it to perform the rename.

### Step 2.8: Update `get_user_sessions` handler

1. Change dependency from `get_current_user` to `get_current_user_from_any_token`.
2. Change return type to `List[SessionListItem]`.
3. Remove the `create_access_token` call per session.

```python
@router.get("/sessions", response_model=List[SessionListItem])
async def get_user_sessions(
    user: User = Depends(get_current_user_from_any_token),
    database_service: DatabaseService = Depends(get_database_service),
):
    try:
        sessions = await database_service.sessions.get_user_sessions(user.id)
        return [
            SessionListItem(
                session_id=sanitize_string(session.id),
                name=sanitize_string(session.name),
            )
            for session in sessions
        ]
    except ValueError as ve:
        logger.error("get_sessions_validation_failed", user_id=user.id, error=str(ve), exc_info=True)
        raise HTTPException(status_code=422, detail=str(ve))
```

---

## Phase 3 — Backend admin routes

### Step 3.1: Update imports in `backend/app/api/v1/admin.py`

The `verify_token` import stays (used by the new `get_current_admin_user`). Remove `create_access_token` only if no other call site in admin.py uses it — but it is still used by `create_user` (line 315), so keep both imports.

### Step 3.2: Simplify `get_current_admin_user`

Replace the dual-path logic with a single `verify_token(token, expected_type="session")` call. Remove the `int(token_subject)` fallback branch entirely:

```python
async def get_current_admin_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    database_service: DatabaseService = Depends(get_database_service),
) -> User:
    try:
        token = sanitize_string(credentials.credentials)

        session_id = verify_token(token, expected_type="session")
        if session_id is None:
            logger.error("invalid_token", token_part=token[:10] + "...")
            raise HTTPException(
                status_code=401,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )

        session_id = sanitize_string(session_id)
        session = await database_service.sessions.get_session(session_id)
        if session is None:
            raise HTTPException(
                status_code=401,
                detail="Session not found",
                headers={"WWW-Authenticate": "Bearer"},
            )

        user = await database_service.users.get_user(session.user_id)
        if user is None:
            raise HTTPException(
                status_code=404,
                detail="User not found",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if not user.is_admin:
            logger.warning("unauthorized_admin_access_attempt", user_id=user.id)
            raise HTTPException(status_code=403, detail="Admin access required")

        return user
    except HTTPException:
        raise
    except ValueError as ve:
        logger.error("token_validation_failed", error=str(ve), exc_info=True)
        raise HTTPException(
            status_code=422,
            detail="Invalid token format",
            headers={"WWW-Authenticate": "Bearer"},
        )
```

### Step 3.3: Update admin `create_user`

Pass `token_type="user"` in the `UserResponse` token:

```python
token=create_access_token(str(user.id), token_type="user"),
```

---

## Phase 4 — Backend test fixtures

### Step 4.1: Update `backend/tests/conftest.py`

The `auth_token` and `admin_token` fixtures call `create_access_token` with the old signature. Update both:

```python
@pytest.fixture
def auth_token(test_chat_session: ChatSession) -> str:
    """Create a JWT token for a test user using session ID."""
    from app.utils.auth import create_access_token

    token = create_access_token(str(test_chat_session.id), token_type="session")
    return token.access_token


@pytest.fixture
def admin_token(test_admin_user: User, db_session: Session) -> str:
    """Create a JWT token for a test admin user using session ID."""
    from app.utils.auth import create_access_token
    import uuid

    admin_session = ChatSession(id=str(uuid.uuid4()), user_id=test_admin_user.id, name="Admin Session")
    db_session.add(admin_session)
    db_session.commit()
    db_session.refresh(admin_session)

    token = create_access_token(str(admin_session.id), token_type="session")
    return token.access_token
```

### Step 4.2: Update `backend/tests/unit/test_utils/test_auth.py`

All existing tests need the `token_type` argument. Add new tests for type enforcement and `verify_token_any_type`. Rewrite the test file:

```python
import pytest
from datetime import timedelta
from jose import jwt

from app.core.config import settings
from app.utils.auth import create_access_token, verify_token, verify_token_any_type


@pytest.mark.unit
class TestCreateAccessToken:

    def test_default_expiry(self):
        token = create_access_token("test-123", token_type="session")
        assert token.access_token is not None
        assert token.expires_at is not None

    def test_custom_expiry(self):
        token = create_access_token(
            "test-123", token_type="user", expires_delta=timedelta(hours=1)
        )
        assert token.access_token is not None

    def test_payload_contains_subject_and_type(self):
        token = create_access_token("user-456", token_type="user")
        payload = jwt.decode(
            token.access_token, settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        assert payload["sub"] == "user-456"
        assert payload["type"] == "user"
        assert "jti" in payload

    def test_extra_claims_embedded(self):
        token = create_access_token(
            "sess-1", token_type="session",
            extra_claims={"is_admin": True},
        )
        payload = jwt.decode(
            token.access_token, settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        assert payload["is_admin"] is True

    def test_disallowed_extra_claims_rejected(self):
        with pytest.raises(ValueError, match="extra_claims keys must be in"):
            create_access_token(
                "sess-1", token_type="session",
                extra_claims={"sub": "evil"},
            )

    def test_invalid_token_type_rejected(self):
        with pytest.raises(ValueError, match="token_type must be one of"):
            create_access_token("test-123", token_type="admin")


@pytest.mark.unit
class TestVerifyToken:

    def test_valid_token_correct_type(self):
        token = create_access_token("sess-789", token_type="session")
        assert verify_token(token.access_token, expected_type="session") == "sess-789"

    def test_valid_token_wrong_type(self):
        token = create_access_token("sess-789", token_type="session")
        assert verify_token(token.access_token, expected_type="user") is None

    def test_expired_token(self):
        token = create_access_token(
            "sess-old", token_type="session",
            expires_delta=timedelta(seconds=-1),
        )
        assert verify_token(token.access_token, expected_type="session") is None

    def test_invalid_format(self):
        with pytest.raises(ValueError, match="Token format is invalid"):
            verify_token("not-a-jwt", expected_type="session")

    def test_empty_string(self):
        with pytest.raises(ValueError, match="Token must be a non-empty string"):
            verify_token("", expected_type="session")

    def test_none(self):
        with pytest.raises(ValueError):
            verify_token(None, expected_type="session")


@pytest.mark.unit
class TestVerifyTokenAnyType:

    def test_returns_subject_and_type_for_user(self):
        token = create_access_token("42", token_type="user")
        result = verify_token_any_type(token.access_token)
        assert result == ("42", "user")

    def test_returns_subject_and_type_for_session(self):
        token = create_access_token("abc-def", token_type="session")
        result = verify_token_any_type(token.access_token)
        assert result == ("abc-def", "session")

    def test_expired_token_returns_none(self):
        token = create_access_token(
            "old", token_type="session",
            expires_delta=timedelta(seconds=-1),
        )
        assert verify_token_any_type(token.access_token) is None

    def test_unknown_type_returns_none(self):
        """Tokens with fabricated type claims are rejected at the utility layer."""
        from jose import jwt as jose_jwt
        payload = {"sub": "42", "type": "admin", "exp": 9999999999}
        forged = jose_jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
        assert verify_token_any_type(forged) is None

    def test_invalid_format_raises(self):
        with pytest.raises(ValueError):
            verify_token_any_type("bad-token")
```

### Step 4.3: Scan for other `create_access_token` call sites

Run a project-wide search for `create_access_token` to catch any remaining callers not listed above. Known call sites:

| File | Line | Update needed |
|------|------|---------------|
| `backend/app/utils/auth.py` | definition | Done in Step 1.1 |
| `backend/app/api/v1/auth.py` | login, create_session, update_session_name, get_user_sessions | Done in Phase 2 |
| `backend/app/api/v1/admin.py` | create_user | Done in Step 3.3 |
| `backend/tests/conftest.py` | auth_token, admin_token fixtures | Done in Step 4.1 |
| `backend/tests/unit/test_utils/test_auth.py` | unit tests | Done in Step 4.2 |

---

## Phase 5 — Frontend

### Step 5.1: Update `frontend/src/app/core/services/auth.service.ts`

1. Add `decodeTokenPayload` and `readAdminFromToken` private methods.
2. Change `isAdminSignal` initialization to use `readAdminFromToken()`.
3. Update `storeSessionToken` to refresh admin signal.
4. Remove all `localStorage` reads/writes for `isAdmin`.

The `storeLoginTokens` method no longer writes `isAdmin`:

```typescript
private storeLoginTokens(token: string) {
    localStorage.setItem('token', token);
    localStorage.setItem('userToken', token);
    this.tokenSignal.set(token);
}
```

The `logout` method no longer removes `isAdmin`:

```typescript
logout() {
    localStorage.removeItem('token');
    localStorage.removeItem('userToken');
    this.tokenSignal.set(null);
    this.isAdminSignal.set(false);
    this.router.navigate(['/']);
}
```

The `login` call in `tap` passes only the token (remove the `is_admin` argument):

```typescript
this.storeLoginTokens(response.access_token);
```

Add the new methods:

```typescript
private decodeTokenPayload(token: string): Record<string, unknown> | null {
    try {
        const parts = token.split('.');
        if (parts.length !== 3) return null;
        let payload = parts[1].replace(/-/g, '+').replace(/_/g, '/');
        payload += '='.repeat((4 - (payload.length % 4)) % 4);
        return JSON.parse(atob(payload));
    } catch {
        return null;
    }
}

private readAdminFromToken(): boolean {
    const token = localStorage.getItem('token');
    if (!token) return false;
    const payload = this.decodeTokenPayload(token);
    return payload?.is_admin === true;
}
```

Update `isAdminSignal`:

```typescript
private isAdminSignal = signal<boolean>(this.readAdminFromToken());
```

Update `storeSessionToken`:

```typescript
private storeSessionToken(token: string) {
    localStorage.setItem('token', token);
    this.tokenSignal.set(token);
    this.isAdminSignal.set(this.readAdminFromToken());
}
```

### Step 5.2: Update `frontend/src/app/app.config.ts`

Change the interceptor to fall back to `token` when `userToken` is absent:

```typescript
const isSessionCreation = request.url.includes('/api/v1/auth/session')
    && request.method === 'POST';
const token = isSessionCreation
    ? (localStorage.getItem('userToken') ?? localStorage.getItem('token'))
    : localStorage.getItem('token');
```

---

## Phase 6 — Environment files and verification

### Step 6.1: Update `.env` files

Ensure every non-test `.env` file has a `JWT_SECRET_KEY` of at least 32 characters. Example:

```
JWT_SECRET_KEY=replace-this-with-a-real-secret-at-least-32-chars
```

Generate a production-grade secret with:

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(48))"
```

### Step 6.2: Manual verification checklist

Run through these flows after implementation:

| # | Flow | What to verify |
|---|------|---------------|
| 1 | **App startup** | App starts successfully; crashes if `JWT_SECRET_KEY` is missing or < 32 chars |
| 2 | **Login → session** | Login returns a user-type token; session creation returns a session-type token with `is_admin` claim |
| 3 | **Chatbot with session token** | `POST /chatbot/chat` works with session token, rejects user tokens |
| 4 | **Admin with session token** | Admin endpoints work with admin-user's session token; reject non-admin session tokens with 403 |
| 5 | **Admin with user token** | Admin endpoints reject user-type tokens with 401 |
| 6 | **Session list** | `GET /auth/sessions` works with session token; returns `SessionListItem` (no token field) |
| 7 | **Create second session** | `POST /auth/session` works with an existing session token |
| 8 | **Frontend admin UI** | Admin UI appears based on JWT `is_admin` claim, not `localStorage` |
| 9 | **User token expiry** | User tokens created at login expire after 15 minutes |
| 10 | **Old tokens rejected** | Tokens minted before this change (no `type` claim) are rejected, forcing re-login |
