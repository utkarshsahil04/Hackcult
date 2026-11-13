import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger("raahein.api")

_DEFAULTS = {
    400: ("BAD_REQUEST", "The request was malformed.", "Check the parameters and body."),
    401: ("UNAUTHORIZED", "Missing or invalid token.", "Sign in and retry."),
    403: ("FORBIDDEN", "You are not allowed to do this.", "Use an account with access."),
    404: ("NOT_FOUND", "Resource not found.", "Check the path and id."),
    405: ("METHOD_NOT_ALLOWED", "Method not allowed.", "Check the HTTP method."),
    413: ("PAYLOAD_TOO_LARGE", "The upload is too large.", "Send a photo under 6 MB."),
    429: ("RATE_LIMITED", "Too many requests.", "Wait and retry after the Retry-After period."),
    500: ("INTERNAL_ERROR", "Something went wrong on our side.", "Retry shortly."),
    502: ("UPSTREAM_UNAVAILABLE", "An upstream service failed.", "Retry shortly."),
}


class AppError(Exception):
    def __init__(self, status_code: int, code: str, message: str, hint: str = ""):
        self.status_code = status_code
        self.code = code
        self.message = message
        self.hint = hint


def error_response(status: int, code: str, message: str, hint: str, headers=None):
    return JSONResponse(
        status_code=status,
        content={"error": {"code": code, "message": message, "hint": hint}},
        headers=headers,
    )


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def app_error(_: Request, exc: AppError):
        return error_response(exc.status_code, exc.code, exc.message, exc.hint)

    @app.exception_handler(StarletteHTTPException)
    async def http_error(_: Request, exc: StarletteHTTPException):
        code, message, hint = _DEFAULTS.get(
            exc.status_code, ("ERROR", str(exc.detail), "See the API docs.")
        )
        return error_response(exc.status_code, code, message, hint, exc.headers)

    @app.exception_handler(RequestValidationError)
    async def validation_error(_: Request, exc: RequestValidationError):
        first = exc.errors()[0] if exc.errors() else {}
        where = ".".join(str(p) for p in first.get("loc", []))
        return error_response(
            400, "VALIDATION_ERROR", f"Invalid input at '{where}'.", first.get("msg", "Fix the input.")
        )

    @app.exception_handler(Exception)
    async def unhandled(_: Request, exc: Exception):
        logger.exception("Unhandled error", exc_info=exc)
        code, message, hint = _DEFAULTS[500]
        return error_response(500, code, message, hint)