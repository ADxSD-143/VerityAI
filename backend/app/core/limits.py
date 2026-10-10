"""Process-local request limits for public analysis endpoints.

The limiter intentionally uses the socket peer address and ignores client-supplied
forwarding headers, which are spoofable unless a trusted-proxy policy is configured.
State is process-local; multiple workers do not share quotas.
"""
from __future__ import annotations

import asyncio
import json
import time
from collections import defaultdict, deque
from math import ceil
from typing import Any

PROTECTED_PATHS = {"/api/analyze", "/api/analyze-url"}


class RequestLimitsMiddleware:
    def __init__(
        self, app: Any, *, max_requests: int = 10, window_s: float = 60.0,
        max_body_bytes: int = 1_000_000, body_timeout_s: float = 5.0,
    ) -> None:
        self.app = app
        self.max_requests = max_requests
        self.window_s = window_s
        self.max_body_bytes = max_body_bytes
        self.body_timeout_s = body_timeout_s
        self._requests: dict[str, deque[float]] = defaultdict(deque)

    async def _reject(self, send: Any, status: int, code: str, message: str,
                      headers: list[tuple[bytes, bytes]] | None = None) -> None:
        body = json.dumps(
            {"error": message, "code": code, "details": {}}, separators=(",", ":")
        ).encode("utf-8")
        response_headers = [
            (b"content-type", b"application/json"),
            (b"content-length", str(len(body)).encode("ascii")),
        ]
        response_headers.extend(headers or [])
        await send({"type": "http.response.start", "status": status, "headers": response_headers})
        await send({"type": "http.response.body", "body": body})

    async def __call__(self, scope: dict, receive: Any, send: Any) -> None:
        if scope.get("type") != "http" or scope.get("path") not in PROTECTED_PATHS:
            await self.app(scope, receive, send)
            return

        client = scope.get("client")
        client_key = str(client[0]) if client else "unknown"
        now = time.monotonic()
        bucket = self._requests[client_key]
        while bucket and now - bucket[0] >= self.window_s:
            bucket.popleft()
        if len(bucket) >= self.max_requests:
            retry_after = max(1, ceil(self.window_s - (now - bucket[0])))
            await self._reject(
                send, 429, "rate_limited", "Analysis request rate limit exceeded.",
                [(b"retry-after", str(retry_after).encode("ascii"))],
            )
            return
        bucket.append(now)

        content_length = next(
            (value for key, value in scope.get("headers", []) if key.lower() == b"content-length"),
            None,
        )
        if content_length:
            try:
                declared_size = int(content_length)
            except ValueError:
                await self._reject(send, 400, "invalid_content_length", "Invalid Content-Length header.")
                return
            if declared_size < 0 or declared_size > self.max_body_bytes:
                await self._reject(
                    send, 413, "request_too_large",
                    "Request body exceeds the configured size limit.",
                )
                return

        messages: list[dict] = []
        total = 0
        while True:
            try:
                message = await asyncio.wait_for(receive(), timeout=self.body_timeout_s)
            except TimeoutError:
                await self._reject(
                    send, 408, "request_body_timeout",
                    "Request body was not received before the time limit.",
                )
                return
            if message["type"] == "http.disconnect":
                return
            if message["type"] != "http.request":
                continue
            total += len(message.get("body", b""))
            if total > self.max_body_bytes:
                await self._reject(
                    send, 413, "request_too_large",
                    "Request body exceeds the configured size limit.",
                )
                return
            messages.append(message)
            if not message.get("more_body", False):
                break

        index = 0

        async def replay_receive() -> dict:
            nonlocal index
            if index < len(messages):
                message = messages[index]
                index += 1
                return message
            return {"type": "http.request", "body": b"", "more_body": False}

        await self.app(scope, replay_receive, send)
