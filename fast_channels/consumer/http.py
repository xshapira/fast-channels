"""HTTP consumer implementations for the fast-channels framework.

This module provides base HTTP consumer classes for handling HTTP
requests with support for streaming responses and long-polling patterns.
"""

from typing import Any

from fast_channels.exceptions import StopConsumer
from fast_channels.type_defs import (
    HttpDisconnectEvent,
    HttpRequestEvent,
    HttpResponseBodyEvent,
    HttpResponseStartEvent,
)

from .base import AsyncConsumer


class AsyncHttpConsumer(AsyncConsumer):
    """
    Async HTTP consumer. Provides basic primitives for building asynchronous
    HTTP endpoints.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize the HTTP consumer with an empty body buffer.

        Args:
            *args: Positional arguments.
            **kwargs: Keyword arguments.
        """
        super().__init__(*args, **kwargs)
        self.body: list[bytes] = []

    async def send_headers(
        self, *, status: int = 200, headers: list[tuple[bytes, bytes]] | None = None
    ) -> None:
        """
        Sets the HTTP response status and headers. Headers may be provided as
        a list of tuples or as a dictionary.

        Note that the ASGI spec requires that the protocol server only starts
        sending the response to the client after ``self.send_body`` has been
        called the first time.

        Args:
            status: HTTP status code (default: 200).
            headers: Optional list of header tuples (name, value) as bytes.
        """
        if headers is None:
            headers = []

        message: HttpResponseStartEvent = {
            "type": "http.response.start",
            "status": status,
            "headers": headers,
        }
        await self.send(message)

    async def send_body(self, body: bytes, *, more_body: bool = False) -> None:
        """
        Sends a response body to the client. The method expects a bytestring.

        Set ``more_body=True`` if you want to send more body content later.
        The default behavior closes the response, and further messages on
        the channel will be ignored.

        Args:
            body: Response body as bytes.
            more_body: Whether more body content will be sent (default: False).

        Raises:
            AssertionError: If body is not bytes.
        """
        assert isinstance(body, bytes), "Body is not bytes"
        message: HttpResponseBodyEvent = {
            "type": "http.response.body",
            "body": body,
            "more_body": more_body,
        }
        await self.send(message)

    async def send_response(
        self,
        status: int,
        body: bytes,
        *,
        headers: list[tuple[bytes, bytes]] | None = None,
    ) -> None:
        """
        Sends a response to the client. This is a thin wrapper over
        ``self.send_headers`` and ``self.send_body``, and everything said
        above applies here as well. This method may only be called once.

        Args:
            status: HTTP status code.
            body: Response body as bytes.
            headers: Optional list of header tuples (name, value) as bytes.
        """
        await self.send_headers(status=status, headers=headers)
        await self.send_body(body)

    async def handle(self, body: bytes) -> None:
        """
        Receives the request body as a bytestring. Response may be composed
        using the ``self.send*`` methods; the return value of this method is
        thrown away.

        Args:
            body: The complete request body as bytes.

        Raises:
            NotImplementedError: Always raised as subclasses must implement this method.
        """
        raise NotImplementedError(
            "Subclasses of AsyncHttpConsumer must provide a handle() method."
        )

    async def disconnect(self) -> None:
        """
        Overrideable place to run disconnect handling. Do not send anything
        from here.
        """
        pass

    async def http_request(self, message: HttpRequestEvent) -> None:
        """
        Async entrypoint - concatenates body fragments and hands off control
        to ``self.handle`` when the body has been completely received.

        Args:
            message: HTTP request event containing body fragment.
        """
        if "body" in message:
            self.body.append(message["body"])
        if not message.get("more_body"):
            try:
                await self.handle(b"".join(self.body))
            finally:
                await self.disconnect()
            raise StopConsumer()

    async def http_disconnect(self, message: HttpDisconnectEvent) -> None:
        """
        Let the user do their cleanup and close the consumer.

        Args:
            message: HTTP disconnect event.
        """
        await self.disconnect()
        raise StopConsumer()
