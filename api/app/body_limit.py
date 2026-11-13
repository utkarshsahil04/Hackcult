"""Stop reading a request body once it passes a hard cap, before any multipart parsing.

The routes' own size checks run only after Starlette has received (and spooled) the whole upload,
so without this a client could still push an unbounded body at the server.
"""

from starlette.exceptions import HTTPException

from app.errors import error_response

MAX_BODY_BYTES = 7 * 1024 * 1024  # the 6 MB photo limit plus multipart overhead


class BodyLimitMiddleware:
    def __init__(self, app, max_bytes: int = MAX_BODY_BYTES):
        self.app, self.max_bytes = app, max_bytes

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        length = dict(scope["headers"]).get(b"content-length", b"")
        if length.isdigit() and int(length) > self.max_bytes:  # declared too big: refuse unread
            await error_response(413, *_TOO_LARGE)(scope, receive, send)
            return
        received = 0

        async def limited_receive():
            nonlocal received
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > self.max_bytes:  # chunked or lying about its size
                    # FastAPI re-raises HTTPException from body parsing, so the API's error envelope applies
                    raise HTTPException(status_code=413)
            return message

        await self.app(scope, limited_receive, send)


_TOO_LARGE = ("PAYLOAD_TOO_LARGE", "The upload is too large.", "Send a photo under 6 MB.")
