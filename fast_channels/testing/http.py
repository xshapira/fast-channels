"""Testing utilities for HTTP consumers.

This module provides communicators for testing HTTP consumers with
proper type annotations and helper methods.
"""

from typing import Any

from fast_channels.type_defs import ASGIApplication

from .application import ApplicationCommunicator


class HttpCommunicator(ApplicationCommunicator):
    """Enhanced HTTP communicator for testing HTTP consumers.

    This class extends ApplicationCommunicator to provide convenient
    methods for testing HTTP consumers and handling HTTP request/response flows.
    """

    def __init__(
        self,
        application: ASGIApplication,
        path: str,
        *,
        method: str = "GET",
        body: bytes = b"",
        headers: list[tuple[bytes, bytes]] | None = None,
    ) -> None:
        """Initialize the HTTP communicator.

        Args:
            application: The ASGI application to test.
            path: The HTTP path to request.
            method: HTTP method (default: "GET").
            body: Request body as bytes (default: empty).
            headers: Optional list of header tuples (name, value) as bytes.
        """
        if headers is None:
            headers = []

        scope = {
            "type": "http",
            "asgi": {"version": "3.0"},
            "http_version": "1.1",
            "method": method,
            "path": path,
            "query_string": b"",
            "headers": headers,
        }
        super().__init__(application, scope)  # type: ignore
        self.body = body

    async def send_request(self, *, more_body: bool = False) -> None:
        """Send the HTTP request body to the application.

        Args:
            more_body: Whether more body content will be sent (default: False).
        """
        await self.send_input(
            {"type": "http.request", "body": self.body, "more_body": more_body}
        )

    async def get_response(self, timeout: float = 1) -> dict[str, Any]:
        """Get the complete HTTP response from the application.

        Args:
            timeout: Maximum time to wait for response in seconds.

        Returns:
            Dictionary containing 'status', 'headers', and 'body' keys.

        Raises:
            TimeoutError: If response is not received within timeout.
        """
        # Get the response start
        response_start = await self.receive_output(timeout)
        assert response_start["type"] == "http.response.start"

        # Get the response body (may be multiple chunks)
        body_parts: list[bytes] = []
        while True:
            response_body = await self.receive_output(timeout)
            assert response_body["type"] == "http.response.body"
            body_parts.append(response_body.get("body", b""))
            if not response_body.get("more_body", False):
                break

        return {
            "status": response_start["status"],
            "headers": response_start.get("headers", []),
            "body": b"".join(body_parts),
        }
