# app/core/middleware.py
"""
Middleware for automatic session management.
"""
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from app.core.database import SessionLocal
from app.core import session as session_utils


class SessionMiddleware(BaseHTTPMiddleware):
    """
    Middleware that automatically manages sessions via cookies.

    - Reads session ID from cookie
    - Validates session
    - Creates new session if none or invalid
    - Sets session cookie in response
    - Attaches session to request state for use in endpoints
    """

    async def dispatch(self, request: Request, call_next):
        # Skip session handling for health checks and OpenAPI docs
        if request.url.path in ["/health", "/health/db", "/docs", "/redoc", "/openapi.json"]:
            return await call_next(request)

        # Get session ID from cookie
        session_id = request.cookies.get(session_utils.SESSION_COOKIE_NAME)

        # Get or create session
        db = SessionLocal()
        try:
            session = session_utils.get_or_create_session(db, session_id)

            # Attach session to request state for use in endpoints
            request.state.session = session
            request.state.session_id = session.session_id
            request.state.db = db

            # Process the request
            response = await call_next(request)

            # Set session cookie in response (secure, httponly)
            # The cookie will be sent with every subsequent request
            response.set_cookie(
                key=session_utils.SESSION_COOKIE_NAME,
                value=session.session_id,
                max_age=session_utils.SESSION_TTL_DAYS * 24 * 60 * 60,  # Convert days to seconds
                httponly=True,  # Prevent JavaScript access (XSS protection)
                secure=False,  # Set to True in production with HTTPS
                samesite="lax"  # CSRF protection
            )

            return response

        finally:
            db.close()
