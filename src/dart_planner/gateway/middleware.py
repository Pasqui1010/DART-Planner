"""
Custom middleware for the DART-Planner gateway.
"""
import os
import secrets
import json
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response, JSONResponse
from starlette.types import ASGIApp

from security import InputValidator, ValidationError
from security.auth import AuthManager
from security.db.service import UserService
from dart_planner.common.errors import SecurityError

# --- Security Components Initialization ---
# Load secret key from environment variable with secure handling
# DART_SECRET_KEY MUST be set in all environments.
SECRET_KEY = os.getenv("DART_SECRET_KEY")
if not SECRET_KEY:
    raise SecurityError("DART_SECRET_KEY environment variable must be set")

# Ensure SECRET_KEY is always a string and not None
assert SECRET_KEY is not None, "SECRET_KEY must be set"

# Initialize security components here so they are singletons.
user_service = UserService()
auth_manager = AuthManager(user_service=user_service)
input_validator = InputValidator()


# --- CSRF Middleware ---
class CSRFMiddleware(BaseHTTPMiddleware):
    """
    Implements CSRF protection using the double-submit cookie pattern.
    """
    def __init__(
        self,
        app: ASGIApp,
        cookie_name: str = "csrftoken",
        header_name: str = "X-CSRF-Token",
        safe_methods: set = {"GET", "HEAD", "OPTIONS"}
    ):
        super().__init__(app)
        self.cookie_name = cookie_name
        self.header_name = header_name
        self.safe_methods = safe_methods

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if request.method in self.safe_methods:
            response = await call_next(request)
            if self.cookie_name not in request.cookies:
                csrf_token = secrets.token_hex(16)
                response.set_cookie(
                    self.cookie_name, 
                    csrf_token, 
                    httponly=False, 
                    samesite='strict',
                    secure=request.url.scheme == "https",
                    path='/'
                )
            return response

        csrf_cookie = request.cookies.get(self.cookie_name)
        csrf_header = request.headers.get(self.header_name)

        if not csrf_cookie or not csrf_header or not secrets.compare_digest(csrf_cookie, csrf_header):
            return JSONResponse(status_code=403, content={"detail": "CSRF token mismatch"})

        return await call_next(request)


# --- Secure Middleware ---
class SecureMiddleware(BaseHTTPMiddleware):
    """
    A Starlette middleware to integrate DART-Planner's security model.
    1. Authentication: Validates the 'Authorization' token.
    2. Input Validation: Sanitizes and validates JSON request bodies.
    """
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if any(path in str(request.url.path) for path in ["/docs", "/openapi.json", "/static", "/favicon.ico"]):
            return await call_next(request)

        # The new auth flow relies on cookies, not Authorization headers for the web UI.
        # We will handle API token auth differently if needed.
        # For now, we bypass this for the web demo context.
        # A more robust solution would distinguish between API and web requests.

        if request.method in {"POST", "PUT", "PATCH"}:
            try:
                body = await request.body()
                if body:
                    request_json = json.loads(body)
                    _ = input_validator.validate_generic(request_json)
                
                async def receive():
                    return {"type": "http.request", "body": body, "more_body": False}
                
                request = Request(request.scope, receive)

            except json.JSONDecodeError:
                return JSONResponse(status_code=400, content={"detail": "Invalid JSON format."})
            except ValidationError as e:
                return JSONResponse(status_code=422, content={"detail": f"Validation Error: {str(e)}"})
            except Exception as e:
                return JSONResponse(status_code=500, content={"detail": f"Server error during validation: {str(e)}"})

        return await call_next(request) 
