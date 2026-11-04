"""Bound request bodies before FastAPI parses JSON or spools multipart uploads."""

from starlette.responses import JSONResponse

MAX_REQUEST_BYTES = 8 * 1024 * 1024
MAX_MULTIPART_BYTES = 2 * 1024 * 1024


class RequestSizeLimit:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope["method"] in {"GET", "HEAD", "OPTIONS"}:
            await self.app(scope, receive, send)
            return

        content_type = dict(scope["headers"]).get(b"content-type", b"").lower()
        limit = MAX_MULTIPART_BYTES if content_type.startswith(b"multipart/") else MAX_REQUEST_BYTES
        body = bytearray()
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            chunk = message.get("body", b"")
            if len(body) + len(chunk) > limit:
                response = JSONResponse({"detail": "Request body is too large."}, status_code=413)
                await response(scope, receive, send)
                return
            body.extend(chunk)
            if not message.get("more_body", False):
                break

        async def replay():
            nonlocal body
            if body is None:
                return await receive()
            message = {"type": "http.request", "body": bytes(body), "more_body": False}
            body = None
            return message

        await self.app(scope, replay, send)
